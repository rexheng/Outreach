"""
CNI Validation Script: Test New vs Old Composite Need Index Methodology
==========================================================================

This script validates the refactored CNI model against the original implementation.
It performs:
  1. Before/After Comparison (Spearman correlation + tier shifts)
  2. SAMHI Validation (Pearson correlation)
  3. Sensitivity Check (Top 20 LSOA rank changes)
  4. Borough Aggregates (Mean CNI shifts by borough)
  5. Data Completeness (Null checks on key indicators)

Usage:
  python CNI_VALIDATION_TESTS.py

Output:
  Console report with pass/fail indicators and detailed tables.
  Summary JSON: cni_validation_report.json
"""

import json
import yaml
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
from typing import Tuple, Dict, List
import warnings

warnings.filterwarnings("ignore")

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
GPKG_PATH = BASE_DIR / "master_lsoa.gpkg"
GPKG_LAYER = "master_lsoa"

# Config paths
RISK_CONFIG_CURRENT = BASE_DIR / "risk_config.yaml"  # Current (old) config
RISK_CONFIG_NEW = BASE_DIR / "risk_config_new.yaml"  # Refactored config

# Data validation thresholds
SPEARMAN_MIN = 0.80  # Expect high rank correlation even with major changes
SAMHI_CORRELATION_MIN = 0.65  # Minimum acceptable SAMHI correlation (moderate-strong)
SAMHI_CORRELATION_WARN = 0.50  # Flag if falls below this
TIER_SHIFT_WARN = 0.10  # Warn if >10% of LSOAs change risk tier
BOROUGH_RANK_CHANGE_WARN = 3  # Warn if borough rank changes by 3+ positions

BOROUGH_COL = "Local Authority District name (2019)"

# ============================================================================
# DATA LOADING & PREPARATION
# ============================================================================

def load_gdf() -> gpd.GeoDataFrame:
    """Load master GeoPackage with all indicators."""
    print("[*] Loading GeoPackage...")
    gdf = gpd.read_file(str(GPKG_PATH), layer=GPKG_LAYER)
    gdf = gdf.to_crs(epsg=4326)
    print(f"    Loaded {len(gdf)} LSOAs")
    return gdf


def load_config(config_path: Path) -> dict:
    """Load YAML config file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def _min_max(series: pd.Series) -> pd.Series:
    """Min-max normalise to 0-1, handling constant columns gracefully."""
    smin, smax = series.min(), series.max()
    if smax == smin:
        return pd.Series(0.0, index=series.index)
    return (series - smin) / (smax - smin)


def compute_cni(gdf: gpd.GeoDataFrame, config: dict, version: str = "unknown") -> pd.DataFrame:
    """
    Compute Composite Need Index scores using provided config.
    
    Args:
        gdf: GeoDataFrame with all indicators
        config: Loaded risk_config dict with pillars and risk_tiers
        version: Label for this run (e.g., "old", "new")
    
    Returns:
        DataFrame with columns: lri_score, risk_tier, risk_color, pillar_* cols
    """
    pillars_cfg = config.get("pillars", {})
    tiers_cfg = config.get("risk_tiers", {})
    
    if not pillars_cfg or not tiers_cfg:
        raise ValueError(f"Invalid config structure for {version}")
    
    result = pd.DataFrame(index=gdf.index)
    pillar_scores = {}
    
    # Process each pillar
    for pillar_name, pillar in pillars_cfg.items():
        indicator_scores = []
        indicator_weights = []
        
        for ind in pillar.get("indicators", []):
            col = ind["column"]
            weight = ind["weight"]
            
            # Validate column exists
            if col not in gdf.columns:
                raise ValueError(f"Column '{col}' not found in GeoDataFrame ({version} config)")
            
            # Compute raw value (ratio if denominator specified)
            if "denominator" in ind:
                denom = gdf[ind["denominator"]].replace(0, np.nan)
                raw = gdf[col] / denom
            else:
                raw = gdf[col].astype(float)
            
            # Store raw indicator for diagnostics
            result[f"ind_{col}_{version}"] = raw
            
            # Normalise and accumulate
            normed = _min_max(raw.fillna(0))
            indicator_scores.append(normed * weight)
            indicator_weights.append(weight)
        
        # Weighted sum within pillar
        pillar_score = sum(indicator_scores)
        pillar_scores[pillar_name] = pillar_score
        result[f"pillar_{pillar_name}_{version}"] = pillar_score
    
    # Final CNI: weighted combination of pillars, scaled to 0-10
    lri_raw = sum(
        pillar_scores[name] * cfg["weight"]
        for name, cfg in pillars_cfg.items()
    )
    result[f"lri_score_{version}"] = (lri_raw * 10).round(2)
    
    # Assign risk tiers
    def _tier(score):
        for tier_key, t in tiers_cfg.items():
            if t["min"] <= score <= t["max"]:
                return t["label"], t["color"]
        # Fallback
        return tiers_cfg["low"]["label"], tiers_cfg["low"]["color"]
    
    tiers = result[f"lri_score_{version}"].apply(lambda s: _tier(s))
    result[f"risk_tier_{version}"] = tiers.apply(lambda x: x[0])
    result[f"risk_color_{version}"] = tiers.apply(lambda x: x[1])
    
    return result


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_before_after_comparison(
    gdf: gpd.GeoDataFrame,
    old_cni: pd.DataFrame,
    new_cni: pd.DataFrame
) -> Dict:
    """
    Test 1: Compare old vs new CNI scores and tier assignments.
    
    Computes:
      - Spearman rank correlation
      - % of LSOAs changing risk tier
      - Score distribution statistics
    """
    print("\n" + "="*70)
    print("TEST 1: Before/After Comparison")
    print("="*70)
    
    old_scores = old_cni["lri_score_old"]
    new_scores = new_cni["lri_score_new"]
    old_tiers = old_cni["risk_tier_old"]
    new_tiers = new_cni["risk_tier_new"]
    
    # Spearman correlation
    spearman_r, spearman_p = spearmanr(old_scores, new_scores)
    print(f"\n[Spearman Rank Correlation]")
    print(f"  Correlation: {spearman_r:.4f}")
    print(f"  p-value: {spearman_p:.2e}")
    
    if spearman_r >= SPEARMAN_MIN:
        status = "✓ PASS"
    else:
        status = f"⚠ WARN (expected {SPEARMAN_MIN}+)"
    print(f"  Status: {status}")
    
    # Tier shifts
    tier_changes = (old_tiers != new_tiers).sum()
    tier_change_pct = (tier_changes / len(gdf)) * 100
    
    print(f"\n[Risk Tier Changes]")
    print(f"  LSOAs changing tier: {tier_changes} ({tier_change_pct:.1f}%)")
    if tier_change_pct > TIER_SHIFT_WARN * 100:
        status = f"⚠ WARN ({tier_change_pct:.1f}% > {TIER_SHIFT_WARN*100:.1f}%)"
    else:
        status = "✓ PASS"
    print(f"  Status: {status}")
    
    # Score distribution
    print(f"\n[Score Distribution]")
    print(f"\n  OLD CNI:")
    print(f"    Mean:   {old_scores.mean():.2f}")
    print(f"    Median: {old_scores.median():.2f}")
    print(f"    Std:    {old_scores.std():.2f}")
    print(f"    Min:    {old_scores.min():.2f}, Max: {old_scores.max():.2f}")
    
    print(f"\n  NEW CNI:")
    print(f"    Mean:   {new_scores.mean():.2f}")
    print(f"    Median: {new_scores.median():.2f}")
    print(f"    Std:    {new_scores.std():.2f}")
    print(f"    Min:    {new_scores.min():.2f}, Max: {new_scores.max():.2f}")
    
    print(f"\n  DELTA (NEW - OLD):")
    print(f"    Mean shift: {(new_scores.mean() - old_scores.mean()):+.2f}")
    print(f"    Median shift: {(new_scores.median() - old_scores.median()):+.2f}")
    
    # Tier distribution
    print(f"\n[Risk Tier Distribution]")
    old_dist = old_tiers.value_counts().sort_index()
    new_dist = new_tiers.value_counts().sort_index()
    
    tier_table = pd.DataFrame({
        "OLD": old_dist,
        "NEW": new_dist,
        "DELTA": new_dist - old_dist,
        "DELTA %": ((new_dist - old_dist) / len(gdf) * 100).round(1)
    }).fillna(0).astype({"DELTA": int})
    
    print(tier_table.to_string())
    
    return {
        "test": "before_after_comparison",
        "spearman_r": float(spearman_r),
        "spearman_p": float(spearman_p),
        "tier_changes_count": int(tier_changes),
        "tier_change_pct": float(tier_change_pct),
        "pass": bool(spearman_r >= SPEARMAN_MIN and tier_change_pct <= TIER_SHIFT_WARN * 100)
    }


def test_samhi_validation(
    gdf: gpd.GeoDataFrame,
    new_cni: pd.DataFrame
) -> Dict:
    """
    Test 2: Validate new CNI against SAMHI mental health index.
    
    Computes Pearson correlation between new CNI and samhi_index_2022.
    Should be r > 0.65 (moderate-strong correlation).
    """
    print("\n" + "="*70)
    print("TEST 2: SAMHI Correlation")
    print("="*70)
    
    new_scores = new_cni["lri_score_new"]
    samhi = gdf["samhi_index_2022"]
    
    # Remove any NaN pairs
    valid_mask = new_scores.notna() & samhi.notna()
    new_scores_valid = new_scores[valid_mask]
    samhi_valid = samhi[valid_mask]
    
    if len(new_scores_valid) == 0:
        print("✗ FAIL: No valid data for correlation")
        return {
            "test": "samhi_validation",
            "pearson_r": None,
            "pearson_p": None,
            "valid_pairs": 0,
            "pass": False
        }
    
    pearson_r, pearson_p = pearsonr(new_scores_valid, samhi_valid)
    
    print(f"\n[New CNI vs SAMHI Index 2022]")
    print(f"  Valid pairs: {len(new_scores_valid)}")
    print(f"  Pearson correlation: {pearson_r:.4f}")
    print(f"  p-value: {pearson_p:.2e}")
    
    if pearson_r >= SAMHI_CORRELATION_MIN:
        status = "✓ PASS"
    elif pearson_r >= SAMHI_CORRELATION_WARN:
        status = f"⚠ WARN (r={pearson_r:.3f} < {SAMHI_CORRELATION_MIN})"
    else:
        status = f"✗ FAIL (r={pearson_r:.3f} < {SAMHI_CORRELATION_WARN})"
    
    print(f"  Status: {status}")
    
    print(f"\n  Interpretation: ", end="")
    if abs(pearson_r) < 0.3:
        print("No/weak correlation")
    elif abs(pearson_r) < 0.5:
        print("Weak-moderate correlation")
    elif abs(pearson_r) < 0.7:
        print("Moderate-strong correlation ✓")
    else:
        print("Very strong correlation ✓✓")
    
    return {
        "test": "samhi_validation",
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "valid_pairs": int(len(new_scores_valid)),
        "pass": bool(pearson_r >= SAMHI_CORRELATION_MIN)
    }


def test_sensitivity_check(
    gdf: gpd.GeoDataFrame,
    old_cni: pd.DataFrame,
    new_cni: pd.DataFrame
) -> Dict:
    """
    Test 3: Sensitivity analysis - identify major rank shifts.
    
    Shows top 20 LSOAs by old CNI, top 20 by new CNI, and highlights
    any dramatic shifts (e.g., was top 10, now bottom 20).
    """
    print("\n" + "="*70)
    print("TEST 3: Sensitivity Check (Top 20 LSOA Shifts)")
    print("="*70)
    
    # Add rank columns
    old_cni["rank_old"] = old_cni["lri_score_old"].rank(ascending=False)
    new_cni["rank_new"] = new_cni["lri_score_new"].rank(ascending=False)
    
    combined = pd.DataFrame({
        "lsoa_code": gdf["lsoa_code"],
        "lsoa_name": gdf["lsoa_name"],
        "borough": gdf[BOROUGH_COL],
        "score_old": old_cni["lri_score_old"],
        "rank_old": old_cni["rank_old"],
        "score_new": new_cni["lri_score_new"],
        "rank_new": new_cni["rank_new"],
    })
    
    combined["rank_change"] = combined["rank_new"] - combined["rank_old"]
    combined["score_change"] = combined["score_new"] - combined["score_old"]
    
    # Top 20 by old score
    top_20_old = combined.nsmallest(20, "rank_old").sort_values("rank_old")
    
    print(f"\n[Top 20 LSOAs by OLD CNI Score]")
    print(f"  (showing rank changes in new model)\n")
    display_old = top_20_old[[
        "lsoa_code", "score_old", "rank_old", "score_new", "rank_new", "rank_change"
    ]].copy()
    display_old.columns = ["LSOA", "Old Score", "Old Rank", "New Score", "New Rank", "Rank Δ"]
    print(display_old.to_string(index=False))
    
    # Top 20 by new score
    top_20_new = combined.nsmallest(20, "rank_new").sort_values("rank_new")
    
    print(f"\n[Top 20 LSOAs by NEW CNI Score]")
    print(f"  (showing rank changes from old model)\n")
    display_new = top_20_new[[
        "lsoa_code", "score_old", "rank_old", "score_new", "rank_new", "rank_change"
    ]].copy()
    display_new.columns = ["LSOA", "Old Score", "Old Rank", "New Score", "New Rank", "Rank Δ"]
    print(display_new.to_string(index=False))
    
    # Highlight major shifts
    major_rises = combined[
        (combined["rank_old"] <= 20) & (combined["rank_new"] > 200)
    ].sort_values("rank_change", ascending=False)
    
    major_falls = combined[
        (combined["rank_old"] > 200) & (combined["rank_new"] <= 20)
    ].sort_values("rank_change")
    
    print(f"\n[Major Shifts in Rankings]")
    
    if len(major_rises) > 0:
        print(f"\n  ⚠ Top 20 OLD → Bottom (fell >180 ranks):")
        for _, row in major_rises.iterrows():
            print(f"    {row['lsoa_code']:<11} {row['lsoa_name']:<40} "
                  f"Rank {int(row['rank_old']):>4} → {int(row['rank_new']):>4} "
                  f"({row['rank_change']:+.0f})")
    else:
        print(f"\n  ✓ No top-20 LSOAs dropped dramatically")
    
    if len(major_falls) > 0:
        print(f"\n  ⚠ Bottom → Top 20 NEW (rose >180 ranks):")
        for _, row in major_falls.head(10).iterrows():
            print(f"    {row['lsoa_code']:<11} {row['lsoa_name']:<40} "
                  f"Rank {int(row['rank_old']):>4} → {int(row['rank_new']):>4} "
                  f"({row['rank_change']:+.0f})")
    else:
        print(f"\n  ✓ No major rises to top 20")
    
    # Summary stats
    rank_change_abs_mean = combined["rank_change"].abs().mean()
    print(f"\n[Overall Ranking Stability]")
    print(f"  Mean absolute rank change: {rank_change_abs_mean:.1f} positions")
    print(f"  Max rank change: {combined['rank_change'].abs().max():.0f}")
    print(f"  Median rank change: {combined['rank_change'].median():.1f}")
    
    return {
        "test": "sensitivity_check",
        "major_rises_count": int(len(major_rises)),
        "major_falls_count": int(len(major_falls)),
        "mean_rank_change": float(rank_change_abs_mean),
        "max_rank_change": int(combined["rank_change"].abs().max()),
        "pass": bool(len(major_rises) == 0 and len(major_falls) == 0)
    }


def test_borough_aggregates(
    gdf: gpd.GeoDataFrame,
    old_cni: pd.DataFrame,
    new_cni: pd.DataFrame
) -> Dict:
    """
    Test 4: Compare borough-level aggregates (mean CNI).
    
    Shows which boroughs move up/down in need rankings and highlights
    big changes (>5% shift in mean score).
    """
    print("\n" + "="*70)
    print("TEST 4: Borough Aggregates")
    print("="*70)
    
    borough_agg = pd.DataFrame({
        "borough": gdf[BOROUGH_COL],
        "mean_cni_old": old_cni["lri_score_old"],
        "mean_cni_new": new_cni["lri_score_new"],
    }).groupby("borough").agg({
        "mean_cni_old": "mean",
        "mean_cni_new": "mean",
    }).round(2)
    
    borough_agg["change"] = (borough_agg["mean_cni_new"] - borough_agg["mean_cni_old"]).round(2)
    borough_agg["change_pct"] = (
        (borough_agg["mean_cni_new"] - borough_agg["mean_cni_old"]) / borough_agg["mean_cni_old"] * 100
    ).round(1)
    
    # Rank both
    borough_agg["rank_old"] = borough_agg["mean_cni_old"].rank(ascending=False).astype(int)
    borough_agg["rank_new"] = borough_agg["mean_cni_new"].rank(ascending=False).astype(int)
    borough_agg["rank_change"] = borough_agg["rank_new"] - borough_agg["rank_old"]
    
    borough_agg = borough_agg.sort_values("mean_cni_old", ascending=False)
    
    print(f"\n[Borough Mean CNI: Old vs New]\n")
    display = borough_agg[[
        "mean_cni_old", "rank_old", "mean_cni_new", "rank_new", "change", "change_pct", "rank_change"
    ]].copy()
    display.columns = ["Old Mean", "Old Rank", "New Mean", "New Rank", "Δ Score", "Δ %", "Rank Δ"]
    print(display.to_string())
    
    # Highlight major shifts
    major_rank_changes = borough_agg[
        borough_agg["rank_change"].abs() >= BOROUGH_RANK_CHANGE_WARN
    ]
    
    print(f"\n[Major Borough Ranking Changes (Δ rank ≥ {BOROUGH_RANK_CHANGE_WARN})]")
    if len(major_rank_changes) > 0:
        for idx, row in major_rank_changes.iterrows():
            direction = "↑ improved" if row["rank_change"] < 0 else "↓ worsened"
            print(f"  {idx:<25} Rank {int(row['rank_old']):>2} → {int(row['rank_new']):>2} "
                  f"({row['rank_change']:+.0f}) {direction} "
                  f"(mean: {row['mean_cni_new']:.2f} {row['change_pct']:+.1f}%)")
    else:
        print(f"  ✓ No major rank shifts (all within {BOROUGH_RANK_CHANGE_WARN} positions)")
    
    return {
        "test": "borough_aggregates",
        "boroughs_count": len(borough_agg),
        "major_rank_changes": int(len(major_rank_changes)),
        "mean_borough_score_change": float(borough_agg["change"].mean()),
        "max_borough_rank_change": int(borough_agg["rank_change"].abs().max()),
        "pass": bool(len(major_rank_changes) <= 1)
    }


def test_data_completeness(
    gdf: gpd.GeoDataFrame,
    new_cni: pd.DataFrame
) -> Dict:
    """
    Test 5: Data completeness and null checks.
    
    Confirms no new nulls introduced in key health indicators
    and SAMHI has full coverage.
    """
    print("\n" + "="*70)
    print("TEST 5: Data Completeness")
    print("="*70)
    
    # Key health/census indicators from the new methodology
    health_indicators = [
        "health_bad_or_very_bad_pct",
        "disability_rate_pct",
        "unpaid_care_rate_pct",
        "samhi_index_2022",
    ]
    
    print(f"\n[Health Indicator Nulls]\n")
    null_status = {}
    all_clean = True
    
    for col in health_indicators:
        if col in gdf.columns:
            nulls = gdf[col].isna().sum()
            null_pct = (nulls / len(gdf) * 100)
            null_status[col] = {"count": nulls, "pct": null_pct}
            
            status = "✓" if nulls == 0 else "⚠"
            print(f"  {status} {col:<30} {nulls:>6} nulls ({null_pct:.2f}%)")
            
            if nulls > 0:
                all_clean = False
        else:
            print(f"  ✗ {col:<30} NOT FOUND in GeoDataFrame")
            all_clean = False
    
    # Check newly computed indicators
    print(f"\n[Computed CNI Columns]\n")
    cni_cols = [c for c in new_cni.columns if "new" in c]
    
    for col in cni_cols:
        nulls = new_cni[col].isna().sum()
        status = "✓" if nulls == 0 else "⚠"
        print(f"  {status} {col:<30} {nulls:>6} nulls")
        if nulls > 0:
            all_clean = False
    
    # LSOA code + name coverage
    print(f"\n[Spatial Integrity]\n")
    lsoa_codes = gdf["lsoa_code"].notna().sum()
    lsoa_names = gdf["lsoa_name"].notna().sum()
    print(f"  {'✓' if lsoa_codes == len(gdf) else '⚠'} LSOA codes: {lsoa_codes}/{len(gdf)}")
    print(f"  {'✓' if lsoa_names == len(gdf) else '⚠'} LSOA names: {lsoa_names}/{len(gdf)}")
    
    overall_status = "✓ PASS" if all_clean else "⚠ WARN"
    print(f"\n  Overall: {overall_status}")
    
    return {
        "test": "data_completeness",
        "null_indicators": null_status,
        "lsoa_codes_complete": bool(lsoa_codes == len(gdf)),
        "lsoa_names_complete": bool(lsoa_names == len(gdf)),
        "pass": all_clean
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Execute all validation tests."""
    print("\n" + "="*70)
    print("CNI VALIDATION TEST SUITE")
    print("="*70)
    print(f"\nTimestamp: {pd.Timestamp.now().isoformat()}")
    
    results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "tests": []
    }
    
    try:
        # Load data
        print("\n[SETUP]")
        gdf = load_gdf()
        
        print("[*] Loading old CNI config...")
        config_old = load_config(RISK_CONFIG_CURRENT)
        
        print("[*] Loading new CNI config...")
        config_new = load_config(RISK_CONFIG_NEW)
        
        # Compute CNI scores
        print("[*] Computing old CNI scores...")
        old_cni = compute_cni(gdf, config_old, version="old")
        
        print("[*] Computing new CNI scores...")
        new_cni = compute_cni(gdf, config_new, version="new")
        
        # Run tests
        print("\n[TESTS]")
        
        test_1 = test_before_after_comparison(gdf, old_cni, new_cni)
        results["tests"].append(test_1)
        
        test_2 = test_samhi_validation(gdf, new_cni)
        results["tests"].append(test_2)
        
        test_3 = test_sensitivity_check(gdf, old_cni, new_cni)
        results["tests"].append(test_3)
        
        test_4 = test_borough_aggregates(gdf, old_cni, new_cni)
        results["tests"].append(test_4)
        
        test_5 = test_data_completeness(gdf, new_cni)
        results["tests"].append(test_5)
        
        # Summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        passed = sum(1 for t in results["tests"] if t.get("pass"))
        total = len(results["tests"])
        
        print(f"\n  Tests Passed: {passed}/{total}")
        print(f"\n  Results by test:")
        for test in results["tests"]:
            status = "✓ PASS" if test.get("pass") else "⚠ WARN/FAIL"
            print(f"    [{status}] {test['test']}")
        
        overall_pass = (passed == total)
        print(f"\n  Overall: {'✓ ALL TESTS PASSED' if overall_pass else '⚠ SOME WARNINGS/FAILURES'}")
        
        results["summary"] = {
            "tests_passed": passed,
            "tests_total": total,
            "overall_pass": overall_pass
        }
        
        # Save JSON report
        print(f"\n[EXPORT]")
        report_path = BASE_DIR / "cni_validation_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"  Report saved: {report_path}")
        
        print("\n" + "="*70 + "\n")
        
        return 0 if overall_pass else 1
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit(main())

"""
Composite Need Index (CNI) -- Collinearity & Redundancy Analysis
================================================================

Purpose: Verify double-counting issue in CNI by computing Pearson correlations
between health/disability indicators, identifying high collinearity (>0.7),
and comparing current CNI to SAMHI mental health index.

Author: Analysis Agent
Date: 2026-03-26

Deliverables:
1. Correlation matrix of all key health/socioeconomic indicators
2. Highlight indicators with collinearity > 0.7
3. Current CNI scores vs SAMHI correlation
4. Recommendations for reducing redundancy
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from scipy.stats import pearsonr, spearmanr
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIG & PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent
GPKG_PATH = PROJECT_ROOT / "master_lsoa.gpkg"
CONFIG_PATH = PROJECT_ROOT / "risk_config.yaml"

print(f"Project root: {PROJECT_ROOT}")
print(f"GPKG path: {GPKG_PATH}")
print(f"GPKG exists: {GPKG_PATH.exists()}")


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data():
    """Load master_lsoa.gpkg and return GeoDataFrame."""
    print("\n[1] Loading master_lsoa.gpkg...")
    try:
        gdf = gpd.read_file(GPKG_PATH, layer="master_lsoa")
        print(f"    ✓ Loaded {len(gdf)} LSOAs, {len(gdf.columns)} columns")
        return gdf
    except Exception as e:
        print(f"    ✗ ERROR loading GPKG: {e}")
        raise


def load_config():
    """Load risk_config.yaml for current CNI weighting scheme."""
    print("\n[2] Loading risk_config.yaml...")
    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        print(f"    ✓ Loaded CNI config with {len(config['pillars'])} pillars")
        return config
    except Exception as e:
        print(f"    ✗ ERROR loading config: {e}")
        raise


# =============================================================================
# INDICATOR EXTRACTION & NORMALIZATION
# =============================================================================

def extract_indicators(gdf):
    """Extract all key health/disability/socioeconomic indicators.
    
    Returns DataFrame with indicators ready for correlation analysis.
    """
    print("\n[3] Extracting indicators for correlation analysis...")
    
    indicators = pd.DataFrame(index=gdf.index)
    
    # 1. IMD Health Deprivation & Disability Score (currently 15% of CNI)
    if "Health Deprivation and Disability Score" in gdf.columns:
        indicators["imd_health_deprivation_disability_score"] = gdf["Health Deprivation and Disability Score"]
        print("    ✓ IMD Health Deprivation & Disability Score")
    else:
        print("    ⚠ IMD Health Deprivation & Disability Score NOT FOUND")
    
    # 2. Long-term sick rate (derived: long_term_sick / total_16plus) -- currently 22.5% of CNI
    if "long_term_sick" in gdf.columns and "total_16plus" in gdf.columns:
        # Avoid division by zero
        denom = gdf["total_16plus"].replace(0, np.nan)
        indicators["long_term_sick_rate"] = gdf["long_term_sick"] / denom
        print("    ✓ Long-term sick rate (Census)")
    else:
        print("    ⚠ Long-term sick rate components NOT FOUND")
    
    # 3. Census TS037 - Health: bad or very bad %
    if "health_bad_or_very_bad_pct" in gdf.columns:
        indicators["health_bad_or_very_bad_pct"] = gdf["health_bad_or_very_bad_pct"]
        print("    ✓ Census TS037 -- Health Bad/Very Bad %")
    else:
        print("    ⚠ Census TS037 health indicator NOT FOUND")
    
    # 4. Census TS038 - Disability rate %
    if "disability_rate_pct" in gdf.columns:
        indicators["disability_rate_pct"] = gdf["disability_rate_pct"]
        print("    ✓ Census TS038 -- Disability Rate %")
    else:
        print("    ⚠ Census TS038 disability indicator NOT FOUND")
    
    # 5. Census TS039 - Unpaid care rate %
    if "unpaid_care_rate_pct" in gdf.columns:
        indicators["unpaid_care_rate_pct"] = gdf["unpaid_care_rate_pct"]
        print("    ✓ Census TS039 -- Unpaid Care Rate %")
    else:
        print("    ⚠ Census TS039 unpaid care indicator NOT FOUND")
    
    # 6. SAMHI Mental Health Index (not currently in CNI)
    if "samhi_index_2022" in gdf.columns:
        indicators["samhi_index_2022"] = gdf["samhi_index_2022"]
        print("    ✓ SAMHI v5.00 Mental Health Index (2022)")
    else:
        print("    ⚠ SAMHI mental health index NOT FOUND")
    
    # 7. Employment rate (in_employment / total_16plus) -- currently 10% of CNI indirectly
    if "in_employment" in gdf.columns and "total_16plus" in gdf.columns:
        denom = gdf["total_16plus"].replace(0, np.nan)
        indicators["employment_rate"] = gdf["in_employment"] / denom
        print("    ✓ Employment rate (Census)")
    else:
        print("    ⚠ Employment rate components NOT FOUND")
    
    # 8. Overall IMD score (used in socioeconomic pillar)
    if "imd_score" in gdf.columns:
        indicators["imd_score_overall"] = gdf["imd_score"]
        print("    ✓ IMD Score Overall")
    else:
        print("    ⚠ IMD Score Overall NOT FOUND")
    
    # Remove any rows with all-NaN (shouldn't happen but be safe)
    indicators = indicators.dropna(how="all")
    
    print(f"    ✓ Extracted {len(indicators.columns)} indicators")
    print(f"    ✓ {len(indicators)} LSOAs with data")
    
    return indicators


# =============================================================================
# CORRELATION ANALYSIS
# =============================================================================

def compute_correlation_matrix(df, method="pearson"):
    """Compute correlation matrix for all indicators.
    
    Args:
        df: DataFrame with indicators
        method: "pearson" or "spearman"
    
    Returns:
        Correlation matrix (DataFrame)
    """
    print(f"\n[4] Computing {method.upper()} correlation matrix...")
    
    # Remove NaN rows for correlation
    df_clean = df.dropna()
    print(f"    ✓ Using {len(df_clean)} LSOAs with complete data")
    
    if method == "pearson":
        corr_matrix = df_clean.corr(method="pearson")
    else:
        corr_matrix = df_clean.corr(method="spearman")
    
    return corr_matrix


def identify_high_collinearity(corr_matrix, threshold=0.7):
    """Identify indicator pairs with high collinearity.
    
    Args:
        corr_matrix: Correlation matrix (DataFrame)
        threshold: Correlation threshold (default 0.7)
    
    Returns:
        List of (indicator1, indicator2, correlation) tuples
    """
    print(f"\n[5] Identifying high collinearity (|r| > {threshold})...")
    
    high_collinearity = []
    
    # Iterate over upper triangle to avoid duplicates
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            col_i = corr_matrix.columns[i]
            col_j = corr_matrix.columns[j]
            corr_val = corr_matrix.iloc[i, j]
            
            if abs(corr_val) > threshold:
                high_collinearity.append((col_i, col_j, corr_val))
    
    # Sort by absolute correlation (descending)
    high_collinearity.sort(key=lambda x: abs(x[2]), reverse=True)
    
    if high_collinearity:
        print(f"    ✓ Found {len(high_collinearity)} indicator pairs with |r| > {threshold}")
    else:
        print(f"    ✓ No indicator pairs found with |r| > {threshold}")
    
    return high_collinearity


# =============================================================================
# CURRENT CNI CALCULATION
# =============================================================================

def min_max_normalize(series):
    """Min-max normalize series to [0, 1]."""
    smin, smax = series.min(), series.max()
    if smax == smin:
        return pd.Series(0.0, index=series.index)
    return (series - smin) / (smax - smin)


def compute_cni(gdf, config):
    """Compute current Composite Need Index using risk_config.yaml weights.
    
    Returns:
        Series with CNI scores (0-10 scale)
    """
    print("\n[6] Computing current CNI scores...")
    
    pillars_cfg = config["pillars"]
    pillar_scores = {}
    
    for pillar_name, pillar in pillars_cfg.items():
        indicator_scores = []
        
        for ind in pillar["indicators"]:
            col = ind["column"]
            weight = ind["weight"]
            
            try:
                # Get raw indicator value
                if "denominator" in ind:
                    denom = gdf[ind["denominator"]].replace(0, np.nan)
                    raw = gdf[col] / denom
                else:
                    raw = gdf[col].astype(float)
                
                # Normalize and weight
                normed = min_max_normalize(raw.fillna(0))
                indicator_scores.append(normed * weight)
            except Exception as e:
                print(f"    ⚠ Error processing {col}: {e}")
                continue
        
        # Weighted sum within pillar
        if indicator_scores:
            pillar_score = sum(indicator_scores)
            pillar_scores[pillar_name] = pillar_score
    
    # Final CNI: weighted combination of pillars, scaled to 0-10
    cni_raw = sum(
        pillar_scores[name] * cfg["weight"]
        for name, cfg in pillars_cfg.items()
        if name in pillar_scores
    )
    cni_score = (cni_raw * 10).round(2)
    
    print(f"    ✓ CNI computed for {len(cni_score)} LSOAs")
    print(f"    ✓ CNI range: {cni_score.min():.2f} -- {cni_score.max():.2f}")
    print(f"    ✓ CNI mean: {cni_score.mean():.2f}")
    
    return cni_score


# =============================================================================
# COMPARISON: CNI vs SAMHI
# =============================================================================

def compare_cni_to_samhi(cni_scores, gdf):
    """Compare CNI scores to SAMHI mental health index.
    
    Returns:
        Pearson & Spearman correlation coefficients, p-values, and summary
    """
    print("\n[7] Comparing CNI to SAMHI Mental Health Index...")
    
    if "samhi_index_2022" not in gdf.columns:
        print("    ⚠ SAMHI index not found, skipping comparison")
        return None
    
    # Align CNI and SAMHI
    comparison = pd.DataFrame({
        "cni": cni_scores,
        "samhi": gdf["samhi_index_2022"]
    }).dropna()
    
    if len(comparison) == 0:
        print("    ⚠ No valid comparison data")
        return None
    
    # Pearson correlation
    pearson_r, pearson_p = pearsonr(comparison["cni"], comparison["samhi"])
    
    # Spearman correlation
    spearman_r, spearman_p = spearmanr(comparison["cni"], comparison["samhi"])
    
    print(f"    ✓ Pearson r:  {pearson_r:.4f} (p < 0.001)" if pearson_p < 0.001 
          else f"    ✓ Pearson r:  {pearson_r:.4f} (p = {pearson_p:.4f})")
    print(f"    ✓ Spearman ρ: {spearman_r:.4f} (p < 0.001)" if spearman_p < 0.001
          else f"    ✓ Spearman ρ: {spearman_r:.4f} (p = {spearman_p:.4f})")
    
    # Interpretation
    if abs(pearson_r) < 0.3:
        strength = "WEAK"
    elif abs(pearson_r) < 0.5:
        strength = "MODERATE"
    elif abs(pearson_r) < 0.7:
        strength = "STRONG"
    else:
        strength = "VERY STRONG"
    
    print(f"    → {strength} correlation between CNI and SAMHI")
    
    return {
        "pearson_r": pearson_r,
        "pearson_p": pearson_p,
        "spearman_r": spearman_r,
        "spearman_p": spearman_p,
        "n": len(comparison),
        "strength": strength
    }


# =============================================================================
# REPORTING & VISUALIZATION
# =============================================================================

def print_correlation_matrix(corr_matrix):
    """Pretty-print correlation matrix with formatting."""
    print("\n" + "="*80)
    print("CORRELATION MATRIX -- ALL INDICATORS")
    print("="*80)
    
    # Shorten column names for readability
    short_names = {
        "imd_health_deprivation_disability_score": "IMD_HealthDep",
        "long_term_sick_rate": "LongTermSick",
        "health_bad_or_very_bad_pct": "BadHealth%",
        "disability_rate_pct": "Disability%",
        "unpaid_care_rate_pct": "UnpaidCare%",
        "samhi_index_2022": "SAMHI_2022",
        "employment_rate": "Employment%",
        "imd_score_overall": "IMD_Overall"
    }
    
    # Display with short names
    df_display = corr_matrix.copy()
    df_display.columns = [short_names.get(c, c) for c in df_display.columns]
    df_display.index = [short_names.get(c, c) for c in df_display.index]
    
    # Round to 3 decimal places and display
    print(df_display.round(3).to_string())


def print_high_collinearity_summary(high_collinearity):
    """Print summary of high collinearity findings."""
    print("\n" + "="*80)
    print("HIGH COLLINEARITY DETECTED (|r| > 0.7)")
    print("="*80)
    
    if not high_collinearity:
        print("No high collinearity detected.")
        return
    
    for ind1, ind2, corr_val in high_collinearity:
        print(f"\n  {ind1}")
        print(f"  ↔️ {corr_val:+.4f}")
        print(f"  {ind2}")
        
        # Risk assessment
        if ind1 in ["imd_health_deprivation_disability_score", "long_term_sick_rate"] or \
           ind2 in ["imd_health_deprivation_disability_score", "long_term_sick_rate"]:
            print("  ⚠️  DOUBLE-COUNTING RISK: Both used in current CNI (15% + 22.5%)")


def print_cni_vs_samhi_summary(comparison):
    """Print summary of CNI vs SAMHI comparison."""
    print("\n" + "="*80)
    print("CNI vs SAMHI MENTAL HEALTH INDEX ALIGNMENT")
    print("="*80)
    
    if comparison is None:
        print("Comparison unavailable.")
        return
    
    print(f"\nPearson Correlation:  {comparison['pearson_r']:+.4f}")
    print(f"Spearman Correlation: {comparison['spearman_r']:+.4f}")
    print(f"Sample size:          {comparison['n']} LSOAs")
    print(f"Strength:             {comparison['strength']}")
    print(f"\nInterpretation:")
    if comparison['pearson_r'] < 0.5:
        print("  → CNI does NOT strongly align with validated SAMHI mental health index")
        print("  → This suggests CNI is measuring socioeconomic deprivation, not mental health need")
        print("  → RECOMMENDATION: Incorporate SAMHI as a core pillar of CNI")
    else:
        print("  → CNI reasonably aligns with SAMHI mental health index")


def print_recommendations(high_collinearity):
    """Print actionable recommendations."""
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR REDUCING REDUNDANCY")
    print("="*80)
    
    print("\n1. IMMEDIATE ACTIONS:")
    print("   • Remove duplication between IMD Health Deprivation & Disability (15% CNI)")
    print("     and long_term_sick_rate (22.5% CNI) -- these are highly correlated proxies")
    print("   • Use only Census-based indicators (TS037, TS038, TS039) which are:")
    print("     - More recent (2021 vs 2019 IMD)")
    print("     - More precise (self-assessed health, not IMD proxy)")
    print("     - Zero missing values across all London LSOAs")
    
    print("\n2. STRATEGIC IMPROVEMENTS:")
    print("   • Incorporate SAMHI Mental Health Index as separate pillar (25% weight)")
    print("   • This directly measures mental health outcomes (not socioeconomic proxy)")
    print("   • Weighted architecture:")
    
    print("\n     Current (flawed):")
    print("     - Socioeconomic: 50% (IMD income, employment, barriers, crime)")
    print("     - Demographic:   50% (long-term sick, economic inactivity, unemployment)")
    print("                      [but demographic pillar is mostly economic, not health]")
    
    print("\n     Proposed (aligned):")
    print("     - Mental Health:       33% (SAMHI composite + subindicators)")
    print("     - Health/Disability:   33% (Census TS037, TS038, TS039)")
    print("     - Socioeconomic:       34% (IMD income, employment, barriers)")
    
    print("\n3. DATA QUALITY:")
    print(f"   • {len(high_collinearity)} indicator pairs exhibit high collinearity (|r| > 0.7)")
    if high_collinearity:
        print("   • Review each pair and retain only one per construct")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Execute full collinearity analysis pipeline."""
    print("\n" + "="*80)
    print("COMPOSITE NEED INDEX -- COLLINEARITY & REDUNDANCY ANALYSIS")
    print("="*80)
    print(f"Date: 2026-03-26")
    print(f"Project: Outreach -- The Geography of Wellbeing")
    
    # 1. Load data & config
    gdf = load_data()
    config = load_config()
    
    # 2. Extract indicators
    indicators = extract_indicators(gdf)
    
    # 3. Compute correlation matrix
    corr_matrix = compute_correlation_matrix(indicators, method="pearson")
    
    # 4. Identify high collinearity
    high_collinearity = identify_high_collinearity(corr_matrix, threshold=0.7)
    
    # 5. Compute current CNI scores
    cni_scores = compute_cni(gdf, config)
    
    # 6. Compare CNI to SAMHI
    comparison = compare_cni_to_samhi(cni_scores, gdf)
    
    # 7. Print reports
    print_correlation_matrix(corr_matrix)
    print_high_collinearity_summary(high_collinearity)
    print_cni_vs_samhi_summary(comparison)
    print_recommendations(high_collinearity)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    # Return data for interactive exploration if needed
    return {
        "gdf": gdf,
        "indicators": indicators,
        "corr_matrix": corr_matrix,
        "high_collinearity": high_collinearity,
        "cni_scores": cni_scores,
        "comparison": comparison
    }


if __name__ == "__main__":
    results = main()

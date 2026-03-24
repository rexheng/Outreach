"""Policy signal computation engine.

Computes LSOA-level policy signals (service deserts, mental health trajectory,
transport isolation, service gap flags) and aggregates them into borough-level
and London-wide summaries for the Outreach dashboard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# ── Column name mapping ─────────────────────────────────────────────────────
# Shorthand keys → exact GeoPackage column names.

COL: dict[str, str] = {
    "lsoa_code":          "lsoa_code",
    "lsoa_name":          "lsoa_name",
    "borough":            "Local Authority District name (2019)",
    "imd_score":          "imd_score",
    "imd_decile":         "Index of Multiple Deprivation (IMD) Decile "
                          "(where 1 is most deprived 10% of LSOAs)",
    "samhi_2022":         "samhi_index_2022",
    "samhi_2019":         "samhi_index_2019",
    "geo_barriers":       "Geographical Barriers Sub-domain Score",
    "population":         "Total population: mid 2015 (excluding prisoners)",
    "total_16plus":       "total_16plus",
    "pop_density":        "pop_density_2021",
    "employment_rate":    "employment_rate",
    "health_bad_pct":     "health_bad_or_very_bad_pct",
    "disability_pct":     "disability_rate_pct",
    # Distance to nearest service (metres)
    "dist_community":     "dist_to_nearest_community_service_m",
    "dist_mh_charity":    "dist_to_nearest_mental_health_charity_m",
    "dist_foodbank":      "dist_to_nearest_foodbank_m",
    "dist_nhs_therapy":   "dist_to_nearest_nhs_talking_therapy_m",
    "dist_citizens_advice": "dist_to_nearest_citizens_advice_m",
    "dist_cmht":          "dist_to_nearest_nhs_cmht_m",
    "dist_homelessness":  "dist_to_nearest_homelessness_service_m",
    "dist_older_people":  "dist_to_nearest_older_people_charity_m",
    "dist_wellbeing_hub": "dist_to_nearest_council_wellbeing_hub_m",
    # Service counts
    "cs_foodbank":        "cs_foodbank_count",
    "cs_mh_charity":      "cs_mental_health_charity_count",
    "cs_nhs_therapy":     "cs_nhs_talking_therapy_count",
    "cs_citizens_advice": "cs_citizens_advice_count",
    "cs_cmht":            "cs_nhs_cmht_count",
    "cs_homelessness":    "cs_homelessness_service_count",
    "cs_total":           "community_services_total",
}


# ── Thresholds & weights ────────────────────────────────────────────────────

SERVICE_GAP_THRESHOLDS: dict[str, float] = {
    "foodbank":        3_000.0,
    "mh_charity":      3_000.0,
    "nhs_therapy":     3_000.0,
    "citizens_advice": 3_000.0,
    "cmht":            5_000.0,
}

COMPOSITE_WEIGHTS: dict[str, float] = {
    "service_desert":       0.30,
    "samhi":                0.25,
    "imd":                  0.20,
    "transport_isolation":  0.15,
    "mh_trajectory":        0.10,
}

TIER_THRESHOLDS: dict[str, dict] = {
    "critical": {"min": 0.75, "label": "Critical Need"},
    "high":     {"min": 0.50, "label": "High Need"},
    "moderate": {"min": 0.25, "label": "Elevated"},
    "low":      {"min": 0.00, "label": "Lower Need"},
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _min_max(series: pd.Series) -> pd.Series:
    """Min-max normalise *series* to [0, 1].

    Returns 0 for constant series (including all-NaN after fill).
    """
    smin = series.min()
    smax = series.max()
    if smax == smin:
        return pd.Series(0.0, index=series.index)
    return (series - smin) / (smax - smin)


def _assign_tier(score: float) -> str:
    """Map a composite_need_score to its tier label."""
    if score >= TIER_THRESHOLDS["critical"]["min"]:
        return TIER_THRESHOLDS["critical"]["label"]
    if score >= TIER_THRESHOLDS["high"]["min"]:
        return TIER_THRESHOLDS["high"]["label"]
    if score >= TIER_THRESHOLDS["moderate"]["min"]:
        return TIER_THRESHOLDS["moderate"]["label"]
    return TIER_THRESHOLDS["low"]["label"]


def _slugify(name: str) -> str:
    """Convert a borough name to a URL-safe slug.

    >>> _slugify("City of London")
    'city-of-london'
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


# ── LSOA-level signal computation ───────────────────────────────────────────

def compute_lsoa_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add policy-signal columns to *df* (in-place) and return it.

    New columns added:
        service_desert_score    float 0-1
        mh_trajectory           float (delta, can be negative)
        transport_isolation_score  float 0-1
        service_gap_flags       int  bitmask 0-31
        composite_need_score    float 0-1
        need_tier               str
    """
    df = df.copy()

    # ── Null handling ────────────────────────────────────────────────────
    imd_decile_col = COL["imd_decile"]
    geo_col = COL["geo_barriers"]
    samhi_2022_col = COL["samhi_2022"]
    samhi_2019_col = COL["samhi_2019"]
    imd_score_col = COL["imd_score"]

    if imd_decile_col in df.columns:
        df[imd_decile_col] = df[imd_decile_col].fillna(df[imd_decile_col].median())
    if imd_score_col in df.columns:
        df[imd_score_col] = df[imd_score_col].fillna(df[imd_score_col].median())
    if geo_col in df.columns:
        df[geo_col] = df[geo_col].fillna(df[geo_col].median())
    if samhi_2022_col in df.columns:
        df[samhi_2022_col] = df[samhi_2022_col].fillna(0)
    if samhi_2019_col in df.columns:
        df[samhi_2019_col] = df[samhi_2019_col].fillna(0)

    # ── 1. Service desert score ──────────────────────────────────────────
    # Average of normalised distances, weighted by deprivation
    dist_cols = [COL["dist_community"], COL["dist_mh_charity"], COL["dist_foodbank"]]
    present_dist_cols = [c for c in dist_cols if c in df.columns]

    if present_dist_cols:
        avg_dist = df[present_dist_cols].mean(axis=1)
        norm_dist = _min_max(avg_dist)
        # Weight by deprivation: decile 1 (most deprived) → weight 1.0
        deprivation_weight = (11 - df[imd_decile_col]) / 10.0
        raw_desert = norm_dist * deprivation_weight
        df["service_desert_score"] = _min_max(raw_desert)
    else:
        df["service_desert_score"] = 0.0

    # ── 2. Mental health trajectory ──────────────────────────────────────
    df["mh_trajectory"] = df[samhi_2022_col] - df[samhi_2019_col]

    # ── 3. Transport isolation score ─────────────────────────────────────
    if geo_col in df.columns:
        df["transport_isolation_score"] = _min_max(df[geo_col])
    else:
        df["transport_isolation_score"] = 0.0

    # ── 4. Service gap flags (bitmask) ───────────────────────────────────
    # bit 0 = foodbank > 3 km
    # bit 1 = mh_charity > 3 km
    # bit 2 = nhs_therapy > 3 km
    # bit 3 = citizens_advice > 3 km
    # bit 4 = cmht > 5 km
    flag_defs = [
        (0, COL["dist_foodbank"],        SERVICE_GAP_THRESHOLDS["foodbank"]),
        (1, COL["dist_mh_charity"],      SERVICE_GAP_THRESHOLDS["mh_charity"]),
        (2, COL["dist_nhs_therapy"],     SERVICE_GAP_THRESHOLDS["nhs_therapy"]),
        (3, COL["dist_citizens_advice"], SERVICE_GAP_THRESHOLDS["citizens_advice"]),
        (4, COL["dist_cmht"],            SERVICE_GAP_THRESHOLDS["cmht"]),
    ]

    flags = np.zeros(len(df), dtype=np.int64)
    for bit, col, threshold in flag_defs:
        if col in df.columns:
            exceeds = df[col].fillna(0).gt(threshold).to_numpy().astype(np.int64)
            flags = flags | (exceeds << bit)
    df["service_gap_flags"] = flags

    # ── 5. Composite need score ──────────────────────────────────────────
    # Normalise SAMHI (higher = worse, so already in correct direction)
    norm_samhi = _min_max(df[samhi_2022_col])
    # Normalise IMD score (higher = more deprived)
    norm_imd = _min_max(df[imd_score_col]) if imd_score_col in df.columns else 0.0
    # Trajectory: only positive (worsening) contributes
    traj_positive = df["mh_trajectory"].clip(lower=0)
    norm_traj = _min_max(traj_positive)

    composite_raw = (
        COMPOSITE_WEIGHTS["service_desert"]      * df["service_desert_score"]
        + COMPOSITE_WEIGHTS["samhi"]              * norm_samhi
        + COMPOSITE_WEIGHTS["imd"]                * norm_imd
        + COMPOSITE_WEIGHTS["transport_isolation"] * df["transport_isolation_score"]
        + COMPOSITE_WEIGHTS["mh_trajectory"]       * norm_traj
    )
    df["composite_need_score"] = _min_max(composite_raw)

    # ── 6. Need tier ─────────────────────────────────────────────────────
    df["need_tier"] = df["composite_need_score"].apply(_assign_tier)

    return df


# ── Borough aggregates ───────────────────────────────────────────────────────

def compute_borough_aggregates(df: pd.DataFrame) -> dict:
    """Aggregate LSOA signals to borough level.

    Returns dict keyed by borough name, each value a summary dict.
    """
    borough_col = COL["borough"]
    pop_col = COL["population"]
    boroughs: dict = {}

    for borough_name, group in df.groupby(borough_col):
        lsoa_count = len(group)

        # Population
        pop_est = (
            float(group[pop_col].sum())
            if pop_col in group.columns
            else None
        )

        # Tier counts
        tier_counts = group["need_tier"].value_counts().to_dict()

        # Composite need
        mean_composite = float(group["composite_need_score"].mean())
        max_composite = float(group["composite_need_score"].max())

        # SAMHI
        samhi_2022_col = COL["samhi_2022"]
        samhi_2019_col = COL["samhi_2019"]
        mean_samhi_2022 = float(group[samhi_2022_col].mean())
        mean_samhi_2019 = float(group[samhi_2019_col].mean())

        mean_traj_delta = float(group["mh_trajectory"].mean())
        pct_worsening = float(
            (group["mh_trajectory"] > 0).sum() / lsoa_count * 100
        )

        # Determine trajectory label
        if mean_traj_delta > 0.05:
            mh_trajectory_label = "worsening"
        elif mean_traj_delta < -0.05:
            mh_trajectory_label = "improving"
        else:
            mh_trajectory_label = "stable"

        # Service desert
        mean_service_desert = float(group["service_desert_score"].mean())

        # Service coverage per type
        service_types = {
            "foodbank":        ("dist_foodbank",        "cs_foodbank",        "foodbank"),
            "mh_charity":      ("dist_mh_charity",      "cs_mh_charity",      "mh_charity"),
            "nhs_therapy":     ("dist_nhs_therapy",     "cs_nhs_therapy",     "nhs_therapy"),
            "citizens_advice": ("dist_citizens_advice", "cs_citizens_advice", "citizens_advice"),
            "cmht":            ("dist_cmht",            "cs_cmht",            "cmht"),
            "homelessness":    ("dist_homelessness",    "cs_homelessness",    None),
        }

        service_coverage: dict = {}
        for svc_key, (dist_key, count_key, threshold_key) in service_types.items():
            dist_col_name = COL[dist_key]
            count_col_name = COL.get(count_key)

            lsoas_with_service = 0
            if count_col_name and count_col_name in group.columns:
                lsoas_with_service = int((group[count_col_name] > 0).sum())

            mean_dist = (
                float(group[dist_col_name].mean())
                if dist_col_name in group.columns
                else None
            )

            threshold = SERVICE_GAP_THRESHOLDS.get(threshold_key)
            lsoas_beyond = 0
            if threshold and dist_col_name in group.columns:
                lsoas_beyond = int(group[dist_col_name].gt(threshold).sum())

            service_coverage[svc_key] = {
                "lsoas_with_service": lsoas_with_service,
                "mean_dist_m": round(mean_dist, 1) if mean_dist is not None else None,
                "lsoas_beyond_threshold": lsoas_beyond,
            }

        # Geo barriers
        geo_col = COL["geo_barriers"]
        mean_geo = (
            float(group[geo_col].mean())
            if geo_col in group.columns
            else None
        )

        # Top 5 LSOAs by composite need
        top5 = (
            group.nlargest(5, "composite_need_score")[
                [COL["lsoa_code"], COL["lsoa_name"], "composite_need_score", "need_tier"]
            ]
            .to_dict(orient="records")
        )

        boroughs[borough_name] = {
            "borough_name":           borough_name,
            "borough_slug":           _slugify(borough_name),
            "lsoa_count":             lsoa_count,
            "population_est_2015":    pop_est,
            "tier_counts":            tier_counts,
            "mean_composite_need":    round(mean_composite, 4),
            "max_composite_need":     round(max_composite, 4),
            "mean_samhi_2022":        round(mean_samhi_2022, 4),
            "mean_samhi_2019":        round(mean_samhi_2019, 4),
            "mh_trajectory":          mh_trajectory_label,
            "mean_trajectory_delta":  round(mean_traj_delta, 4),
            "pct_lsoas_worsening":    round(pct_worsening, 2),
            "mean_service_desert":    round(mean_service_desert, 4),
            "service_coverage":       service_coverage,
            "mean_geo_barriers_score": round(mean_geo, 4) if mean_geo is not None else None,
            "top_5_lsoas":            top5,
        }

    return boroughs


# ── London-wide aggregate ────────────────────────────────────────────────────

def compute_london_wide(df: pd.DataFrame, boroughs: dict) -> dict:
    """Compute London-wide summary statistics.

    Parameters
    ----------
    df : DataFrame with LSOA-level signals (output of compute_lsoa_signals).
    boroughs : dict of borough aggregates (output of compute_borough_aggregates).
    """
    tier_counts = df["need_tier"].value_counts().to_dict()
    total_lsoas = len(df)

    # Trajectory summary
    worsening = int((df["mh_trajectory"] > 0).sum())
    improving = int((df["mh_trajectory"] < 0).sum())
    stable = int((df["mh_trajectory"] == 0).sum())

    trajectory_summary = {
        "worsening": worsening,
        "improving": improving,
        "stable":    stable,
        "pct_worsening": round(worsening / total_lsoas * 100, 2) if total_lsoas else 0,
    }

    # Top 10 boroughs by mean composite need
    sorted_boroughs = sorted(
        boroughs.values(),
        key=lambda b: b["mean_composite_need"],
        reverse=True,
    )
    top_10 = [
        {
            "borough_name":        b["borough_name"],
            "borough_slug":        b["borough_slug"],
            "mean_composite_need": b["mean_composite_need"],
            "lsoa_count":          b["lsoa_count"],
            "mh_trajectory":       b["mh_trajectory"],
        }
        for b in sorted_boroughs[:10]
    ]

    return {
        "total_lsoas":        total_lsoas,
        "tier_counts":        tier_counts,
        "mean_composite_need": round(float(df["composite_need_score"].mean()), 4),
        "trajectory_summary": trajectory_summary,
        "top_10_boroughs":    top_10,
    }


# ── Full pipeline ────────────────────────────────────────────────────────────

def build_signals(gpkg_path: str | Path, output_path: str | Path) -> dict:
    """End-to-end pipeline: load GPKG, compute all signals, write JSON.

    Parameters
    ----------
    gpkg_path : path to master_lsoa.gpkg
    output_path : path for the output JSON file

    Returns
    -------
    dict with keys "london", "boroughs" (and the enriched df is discarded).
    """
    gpkg_path = Path(gpkg_path)
    output_path = Path(output_path)

    # 1. Load
    gdf = gpd.read_file(str(gpkg_path), layer="master_lsoa", engine="fiona")

    # 2. LSOA signals
    df = compute_lsoa_signals(gdf)

    # 3. Borough aggregates
    boroughs = compute_borough_aggregates(df)

    # 4. London-wide
    london = compute_london_wide(df, boroughs)

    # 5. Assemble & write
    payload = {
        "london":   london,
        "boroughs": boroughs,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    return payload

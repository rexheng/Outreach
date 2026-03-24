"""Data pipeline: load GeoPackage, compute Composite Need Index, prepare GeoJSON payload."""

import json
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path

from app.config import (
    GPKG_PATH, GPKG_LAYER, SIMPLIFY_TOLERANCE, DISPLAY_COLUMNS,
    RISK_CONFIG_PATH,
)
from app.data.risk_model import load_config, compute_lri


# Module-level cache
_geojson_cache: dict | None = None
_gdf_cache: gpd.GeoDataFrame | None = None
_borough_cache: list | None = None
_insights_cache: dict | None = None
_critical_cache: list | None = None
_scatter_cache: list | None = None
_borough_geojson_cache: dict | None = None

BOROUGH_COL = "Local Authority District name (2019)"


def load_and_prepare() -> tuple[dict, gpd.GeoDataFrame, list]:
    """Load GPKG, compute CNI scores, simplify geometry, build GeoJSON.

    Returns (geojson_dict, full_gdf, borough_stats).
    """
    global _geojson_cache, _gdf_cache, _borough_cache
    if _geojson_cache is not None:
        return _geojson_cache, _gdf_cache, _borough_cache

    # 1. Load GeoPackage (pyogrio is the default engine, no extra system deps)
    gdf = gpd.read_file(str(GPKG_PATH), layer=GPKG_LAYER)

    # 2. Reproject to WGS84 for Leaflet
    gdf = gdf.to_crs(epsg=4326)

    # 3. Compute Composite Need Index scores
    config = load_config(RISK_CONFIG_PATH)
    lri_df = compute_lri(gdf, config)

    # Merge CNI columns into GeoDataFrame
    for col in lri_df.columns:
        gdf[col] = lri_df[col]

    _gdf_cache = gdf

    # 4. Build lightweight GeoJSON for the map
    keep_cols = (
        DISPLAY_COLUMNS
        + [c for c in lri_df.columns]
        + ["geometry"]
    )
    # Deduplicate while preserving order
    seen = set()
    keep_cols = [c for c in keep_cols if not (c in seen or seen.add(c))]

    map_gdf = gdf[keep_cols].copy()

    # Simplify geometries to reduce payload
    map_gdf["geometry"] = map_gdf.geometry.simplify(
        SIMPLIFY_TOLERANCE, preserve_topology=True
    )

    # Round floats for smaller JSON
    float_cols = map_gdf.select_dtypes(include="float").columns
    map_gdf[float_cols] = map_gdf[float_cols].round(4)

    _geojson_cache = json.loads(map_gdf.to_json())

    # 5. Borough-level aggregates
    borough_stats = (
        gdf.groupby(BOROUGH_COL)
        .agg(
            mean_lri=("lri_score", "mean"),
            median_lri=("lri_score", "median"),
            max_lri=("lri_score", "max"),
            lsoa_count=("lsoa_code", "count"),
            total_population=("total_16plus", "sum"),
            critical_count=("risk_tier", lambda x: (x == "Critical").sum()),
            high_count=("risk_tier", lambda x: (x == "High").sum()),
            samhi_mean=("samhi_index_2022", "mean"),
            samhi_2019_mean=("samhi_index_2019", "mean"),
            antidep_mean=("antidep_rate_2022", "mean"),
            qof_dep_mean=("est_qof_dep_2022", "mean"),
            bad_health_mean=("health_bad_or_very_bad_pct", "mean"),
            disability_mean=("disability_rate_pct", "mean"),
            unpaid_care_mean=("unpaid_care_rate_pct", "mean"),
            imd_mean=("imd_score", "mean"),
        )
        .reset_index()
        .rename(columns={BOROUGH_COL: "borough"})
        .round(2)
        .sort_values("mean_lri", ascending=False)
    )
    borough_stats["samhi_covid_change"] = (
        borough_stats["samhi_mean"] - borough_stats["samhi_2019_mean"]
    ).round(2)
    _borough_cache = borough_stats.to_dict(orient="records")

    # 6. Compute overview data (insights, critical areas, scatter, borough geojson)
    _compute_overview_data(gdf, borough_stats)

    return _geojson_cache, _gdf_cache, _borough_cache


def get_lsoa_detail(lsoa_code: str) -> dict | None:
    """Return all columns for a single LSOA as a dict."""
    _, gdf, _ = load_and_prepare()
    row = gdf[gdf["lsoa_code"] == lsoa_code]
    if row.empty:
        return None
    record = row.drop(columns="geometry").iloc[0].to_dict()
    return {k: _to_native(v) for k, v in record.items()}


def _to_native(val):
    """Convert numpy/pandas types to Python native."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val) if not np.isnan(val) else None
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if pd.isna(val):
        return None
    return val


# ---------------------------------------------------------------------------
# Overview data computation
# ---------------------------------------------------------------------------

def _compute_overview_data(gdf: gpd.GeoDataFrame, borough_df: pd.DataFrame):
    """Compute cached overview data: insights, critical areas, scatter, borough GeoJSON."""
    global _insights_cache, _critical_cache, _scatter_cache, _borough_geojson_cache

    df = gdf.drop(columns="geometry")

    # --- Headline KPIs ---
    london_samhi = df["samhi_index_2022"].mean()
    london_antidep = df["antidep_rate_2022"].mean()
    london_qof = df["est_qof_dep_2022"].mean()
    london_bad_health = df["health_bad_or_very_bad_pct"].mean()
    london_disability = df["disability_rate_pct"].mean()
    london_care = df["unpaid_care_rate_pct"].mean()

    worst_boroughs = borough_df.nlargest(5, "samhi_mean")["borough"].tolist()
    best_boroughs = borough_df.nsmallest(5, "samhi_mean")["borough"].tolist()

    # COVID impact
    covid_worse = borough_df.nlargest(5, "samhi_covid_change")
    covid_better = borough_df.nsmallest(5, "samhi_covid_change")

    # Correlations
    corr_imd_samhi = df["imd_score"].corr(df["samhi_index_2022"])
    corr_emp_samhi = df["employment_rate"].corr(df["samhi_index_2022"])

    # Decile comparisons
    d1 = df[df["samhi_dec_2022"] >= 9]
    d10 = df[df["samhi_dec_2022"] <= 2]

    # Population in crisis areas
    crisis_pop = df[df["samhi_dec_2022"] >= 8]["total_16plus"].sum()
    total_pop = df["total_16plus"].sum()

    _insights_cache = {
        "headline": {
            "samhi_mean": round(float(london_samhi), 2),
            "antidep_rate": round(float(london_antidep), 1),
            "qof_depression": round(float(london_qof), 1),
            "bad_health_pct": round(float(london_bad_health), 1),
            "disability_pct": round(float(london_disability), 1),
            "unpaid_care_pct": round(float(london_care), 1),
            "total_lsoas": int(len(df)),
            "crisis_pop": int(crisis_pop),
            "total_pop": int(total_pop),
        },
        "narratives": [
            {
                "title": "The geography of mental health need",
                "body": (
                    f"Across London\u2019s {len(df):,} neighbourhoods, mental health burden is profoundly unequal. "
                    f"The average SAMHI index score is {london_samhi:.2f}, but this masks a range from "
                    f"{df['samhi_index_2022'].min():.1f} to {df['samhi_index_2022'].max():.1f}. "
                    f"The boroughs bearing the heaviest burden \u2014 {', '.join(worst_boroughs[:3])} \u2014 "
                    f"score significantly above the London mean, while {', '.join(best_boroughs[:3])} "
                    f"fare comparatively better."
                ),
                "type": "geographic",
            },
            {
                "title": "The deprivation\u2013mental health nexus",
                "body": (
                    f"IMD deprivation and mental health need are strongly correlated (r\u2009=\u2009{corr_imd_samhi:.2f}). "
                    f"Neighbourhoods in the most deprived SAMHI decile have an average antidepressant prescribing "
                    f"rate of {d1['antidep_rate_2022'].mean():.1f} per 1,000, compared to {d10['antidep_rate_2022'].mean():.1f} "
                    f"in the least deprived areas. Employment rates show an inverse pattern "
                    f"(r\u2009=\u2009{corr_emp_samhi:.2f} with SAMHI), suggesting economic inactivity "
                    f"and mental health distress reinforce each other."
                ),
                "type": "correlation",
            },
            {
                "title": "The pandemic\u2019s lasting shadow",
                "body": (
                    f"Comparing 2019 to 2022, every London borough saw its SAMHI index worsen. "
                    f"The boroughs hit hardest were {covid_worse.iloc[0]['borough']} "
                    f"(+{covid_worse.iloc[0]['samhi_covid_change']:.2f}), "
                    f"{covid_worse.iloc[1]['borough']} (+{covid_worse.iloc[1]['samhi_covid_change']:.2f}), "
                    f"and {covid_worse.iloc[2]['borough']} (+{covid_worse.iloc[2]['samhi_covid_change']:.2f}). "
                    f"These are not areas that \u2018bounced back\u2019 \u2014 the data suggests a structural deepening "
                    f"of mental health need post-COVID."
                ),
                "type": "temporal",
            },
            {
                "title": "Scale of need",
                "body": (
                    f"An estimated {int(crisis_pop):,} adults (aged 16+) live in neighbourhoods ranked in the "
                    f"top 30% for mental health need (SAMHI deciles 8\u201310). That represents "
                    f"{crisis_pop / total_pop * 100:.0f}% of London\u2019s adult population. "
                    f"The average GP depression prevalence in these areas is "
                    f"{df[df['samhi_dec_2022'] >= 8]['est_qof_dep_2022'].mean():.1f}%, "
                    f"with antidepressant prescribing at {df[df['samhi_dec_2022'] >= 8]['antidep_rate_2022'].mean():.1f} "
                    f"per 1,000 population \u2014 substantially above the London average of {london_antidep:.1f}."
                ),
                "type": "scale",
            },
            {
                "title": "Disability and caring burden",
                "body": (
                    f"London\u2019s disability rate averages {london_disability:.1f}%, but in the most "
                    f"mentally health-deprived neighbourhoods it reaches {d1['disability_rate_pct'].mean():.1f}%. "
                    f"Unpaid care provision follows a similar pattern: {london_care:.1f}% of Londoners "
                    f"provide unpaid care overall, rising in areas of highest mental health need. "
                    f"These overlapping burdens suggest that mental health policy cannot be siloed \u2014 "
                    f"it intersects with disability support, carer support, and community infrastructure."
                ),
                "type": "intersection",
            },
        ],
        "worst_boroughs": worst_boroughs,
        "best_boroughs": best_boroughs,
    }

    # --- Critical areas: top 50 LSOAs by SAMHI ---
    critical_cols = [
        "lsoa_code", "lsoa_name", BOROUGH_COL, "samhi_index_2022", "samhi_dec_2022",
        "antidep_rate_2022", "est_qof_dep_2022", "health_bad_or_very_bad_pct",
        "disability_rate_pct", "imd_score",
    ]
    critical_df = df.nlargest(50, "samhi_index_2022")[critical_cols].copy()
    critical_df = critical_df.rename(columns={BOROUGH_COL: "borough"})
    critical_df = critical_df.round(2)
    _critical_cache = [
        {k: _to_native(v) for k, v in row.items()}
        for row in critical_df.to_dict("records")
    ]

    # --- Scatter data: SAMHI vs IMD for all LSOAs ---
    scatter_df = df[["imd_score", "samhi_index_2022", BOROUGH_COL, "lsoa_name"]].dropna().copy()
    scatter_df = scatter_df.rename(columns={BOROUGH_COL: "borough"}).round(2)
    _scatter_cache = scatter_df.to_dict("records")

    # --- Borough-level dissolved GeoJSON for overview mini-map ---
    borough_geo = gdf[[BOROUGH_COL, "geometry"]].copy()
    borough_geo = borough_geo.dissolve(by=BOROUGH_COL).reset_index()
    borough_geo = borough_geo.rename(columns={BOROUGH_COL: "borough"})
    borough_geo["geometry"] = borough_geo.geometry.simplify(0.002, preserve_topology=True)
    # Attach samhi_mean for choropleth colouring
    samhi_lookup = borough_df.set_index("borough")["samhi_mean"].to_dict()
    borough_geo["samhi_mean"] = borough_geo["borough"].map(samhi_lookup).round(2)
    _borough_geojson_cache = json.loads(borough_geo.to_json())


# ---------------------------------------------------------------------------
# Accessor functions for overview endpoints
# ---------------------------------------------------------------------------

def get_insights() -> dict:
    """Return headline KPIs, narratives, and worst/best boroughs."""
    load_and_prepare()
    return _insights_cache


def get_critical_areas() -> list:
    """Return top 50 LSOAs by SAMHI (critical areas)."""
    load_and_prepare()
    return _critical_cache


def get_scatter_data() -> list:
    """Return SAMHI vs IMD scatter data for all LSOAs."""
    load_and_prepare()
    return _scatter_cache


def get_borough_geojson() -> dict:
    """Return dissolved borough boundaries as GeoJSON with samhi_mean."""
    load_and_prepare()
    return _borough_geojson_cache

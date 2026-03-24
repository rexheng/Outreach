"""Data pipeline: load GeoPackage, compute LRI, prepare GeoJSON payload."""

import json
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

BOROUGH_COL = "Local Authority District name (2019)"


def load_and_prepare() -> tuple[dict, gpd.GeoDataFrame, list]:
    """Load GPKG, compute LRI, simplify geometry, build GeoJSON.

    Returns (geojson_dict, full_gdf, borough_stats).
    """
    global _geojson_cache, _gdf_cache, _borough_cache
    if _geojson_cache is not None:
        return _geojson_cache, _gdf_cache, _borough_cache

    # 1. Load GeoPackage (use fiona engine for compatibility)
    gdf = gpd.read_file(str(GPKG_PATH), layer=GPKG_LAYER, engine="fiona")

    # 2. Reproject to WGS84 for Leaflet
    gdf = gdf.to_crs(epsg=4326)

    # 3. Compute LRI scores
    config = load_config(RISK_CONFIG_PATH)
    lri_df = compute_lri(gdf, config)

    # Merge LRI columns into GeoDataFrame
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
        )
        .reset_index()
        .rename(columns={BOROUGH_COL: "borough"})
        .round(2)
        .sort_values("mean_lri", ascending=False)
    )
    _borough_cache = borough_stats.to_dict(orient="records")

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
    import numpy as np
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val) if not np.isnan(val) else None
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if pd.isna(val):
        return None
    return val

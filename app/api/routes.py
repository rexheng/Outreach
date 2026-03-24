"""API endpoints for the Outreach dashboard."""

from fastapi import APIRouter, HTTPException, Query
from app.data.loader import (
    load_and_prepare, get_lsoa_detail,
    get_insights, get_critical_areas, get_scatter_data, get_borough_geojson,
)
from app.data.risk_model import load_config
from app.config import RISK_CONFIG_PATH

router = APIRouter(prefix="/api")


@router.get("/geojson")
def geojson():
    """Full London GeoJSON with Composite Need Index scores as properties."""
    geojson_data, _, _ = load_and_prepare()
    return geojson_data


@router.get("/lsoa/{lsoa_code}")
def lsoa_detail(lsoa_code: str):
    """Detailed data for a single LSOA."""
    detail = get_lsoa_detail(lsoa_code)
    if detail is None:
        raise HTTPException(status_code=404, detail="LSOA not found")
    return detail


@router.get("/boroughs")
def boroughs():
    """Aggregated stats per borough."""
    _, _, borough_stats = load_and_prepare()
    return borough_stats


@router.get("/metadata")
def metadata():
    """Risk model configuration: indicators, weights, tier definitions."""
    config = load_config(RISK_CONFIG_PATH)
    return config


# --- Overview endpoints ---

@router.get("/overview/insights")
def overview_insights():
    """Headline KPIs, narrative cards, worst/best boroughs."""
    return get_insights()


@router.get("/overview/critical")
def overview_critical(limit: int = Query(default=20, ge=1, le=50)):
    """Top N worst LSOAs by SAMHI index."""
    return get_critical_areas()[:limit]


@router.get("/overview/scatter")
def overview_scatter():
    """SAMHI vs IMD scatter data for all LSOAs."""
    return get_scatter_data()


@router.get("/overview/borough-geojson")
def overview_borough_geojson():
    """Dissolved borough boundaries with samhi_mean for mini-map."""
    return get_borough_geojson()

"""API endpoints for the Loneliness Risk Dashboard."""

from fastapi import APIRouter, HTTPException
from app.data.loader import load_and_prepare, get_lsoa_detail
from app.data.risk_model import load_config
from app.config import RISK_CONFIG_PATH

router = APIRouter(prefix="/api")


@router.get("/geojson")
def geojson():
    """Full London GeoJSON with LRI scores as properties."""
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

"""API routes for policy recommendations."""

import json
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from app.config import (
    POLICY_SIGNALS_PATH, POLICY_RECS_PATH,
    POLICY_MAX_QUESTION_LEN, CHAT_HISTORY_LIMIT,
)

router = APIRouter(prefix="/api/policy")

# In-memory rate limiting (per-IP, resets on restart)
_rate_limit: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX = 20


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed."""
    now = time.time()
    if ip not in _rate_limit:
        _rate_limit[ip] = []
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


def _load_signals() -> dict:
    if not POLICY_SIGNALS_PATH.exists():
        raise HTTPException(status_code=503, detail="Policy signals not yet generated. Run scripts/build_policy_recs.py first.")
    return json.loads(POLICY_SIGNALS_PATH.read_text())


def _load_recs() -> dict:
    if not POLICY_RECS_PATH.exists():
        raise HTTPException(status_code=503, detail="Policy recommendations not yet generated. Run scripts/build_policy_recs.py first.")
    return json.loads(POLICY_RECS_PATH.read_text())


@router.get("/recommendations")
def get_recommendations():
    """Full policy recommendations (London-wide + all boroughs)."""
    return _load_recs()


@router.get("/borough/{slug}")
def get_borough(slug: str):
    """Recommendations + signals for a single borough by slug."""
    signals = _load_signals()
    recs = _load_recs()

    borough_name = None
    for name, data in signals["boroughs"].items():
        if data["borough_slug"] == slug:
            borough_name = name
            break

    if not borough_name:
        raise HTTPException(status_code=404, detail=f"Borough with slug '{slug}' not found")

    borough_recs = [r for r in recs.get("recommendations", []) if r.get("borough") == borough_name]
    return {"signals": signals["boroughs"][borough_name], "recommendations": borough_recs}


@router.get("/signals")
def get_signals():
    """Raw policy signals JSON for frontend map colouring."""
    return _load_signals()


class DeepDiveRequest(BaseModel):
    borough: str
    question: str
    history: list[dict] = []

    @field_validator("question")
    @classmethod
    def validate_question(cls, v):
        if len(v) > POLICY_MAX_QUESTION_LEN:
            raise ValueError(f"Question must be <= {POLICY_MAX_QUESTION_LEN} characters")
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

    @field_validator("history")
    @classmethod
    def validate_history(cls, v):
        return v[-CHAT_HISTORY_LIMIT:]


@router.post("/deep-dive")
async def deep_dive(req: DeepDiveRequest, request: Request):
    """SSE streaming deep-dive analysis for a borough."""
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 20 requests/hour.")

    signals = _load_signals()

    if req.borough not in signals["boroughs"]:
        valid = list(signals["boroughs"].keys())
        raise HTTPException(status_code=400, detail=f"Unknown borough '{req.borough}'. Valid: {valid}")

    from app.api.policy_agent import stream_deep_dive
    return StreamingResponse(
        stream_deep_dive(req.borough, req.question, req.history, signals),
        media_type="text/event-stream",
    )

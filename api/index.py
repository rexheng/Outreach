"""Vercel serverless FastAPI app — chat, policy deep-dive, and briefing endpoints."""

import io
import json
import os
import re
import sys
import time
import logging

# Ensure api/ directory is on the import path for sibling imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from groq import Groq

from _config import (
    GROQ_API_KEY, GROQ_MODEL, CHAT_MAX_TOKENS, CHAT_HISTORY_LIMIT,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL, POLICY_DEEPDIVE_MAX_TOKENS,
    POLICY_MAX_QUESTION_LEN, DATA_DIR,
)
from _chat_context import build_chat_context
from _briefing_generator import generate_pdf

logger = logging.getLogger(__name__)
app = FastAPI()

# ─── Chat system prompt ───

CHAT_SYSTEM_PROMPT = """You are a senior policy advisor briefing local government officials and public health commissioners on where to direct mental health resources across London. You use the Outreach dashboard data — covering 4,994 neighbourhoods (LSOAs) across 33 boroughs.

YOUR ROLE: Turn data into decisions. Every response should answer "so what should we do about it?"

GROUNDING DATA:
{context_json}

HOW TO RESPOND:
- Lead with the actionable finding, not the methodology.
- Frame numbers as policy implications.
- When asked about an area, give a commissioning-ready brief.
- Recommend concrete actions where the data supports it.
- Compare to London averages to show relative severity.
- Keep it short. Policymakers skim. Use 2-4 key points.
- When referencing a borough, format as [[borough:Borough Name]].
- When referencing a specific LSOA, format as [[lsoa:LSOA_CODE|Display Name]].

WHAT TO AVOID:
- Don't explain what the CNI is unless asked.
- Don't list raw indicator values. Translate them.
- Don't hedge excessively.
- Don't repeat information the user can see on the dashboard.

CNI TIERS: Critical 8-10, High 6-8, Moderate 3-6, Low 0-3."""

# ─── Policy system prompt ───

POLICY_SYSTEM_PROMPT = """\
You are a public health policy analyst specialising in mental health need \
and composite wellbeing across London boroughs. Your audience is local councillors and public \
health directors who need plain-language, evidence-grounded recommendations.

RULES:
1. Cite specific metrics from the data provided. Never invent statistics.
2. Write in plain, accessible language suitable for councillors.
3. Reference actual service types where relevant.
4. Short-term = 0-12 months. Long-term = 1-5 years.
5. Reference LSOA codes when discussing specific neighbourhoods.
6. Be specific about which areas need what."""


# ─── Chat endpoint ───

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/chat")
async def chat(req: ChatRequest):
    ctx = build_chat_context(req.message, req.history)
    system_prompt = CHAT_SYSTEM_PROMPT.format(context_json=ctx["context_text"])
    history = req.history[-CHAT_HISTORY_LIMIT:]
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})

    def generate():
        yield f"event: context\ndata: {json.dumps(ctx['entities'])}\n\n"
        if not GROQ_API_KEY:
            yield f"event: token\ndata: {json.dumps({'text': 'API key not configured.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        try:
            client = Groq(api_key=GROQ_API_KEY)
            stream = client.chat.completions.create(model=GROQ_MODEL, max_tokens=CHAT_MAX_TOKENS, messages=messages, stream=True)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"event: token\ndata: {json.dumps({'text': delta.content})}\n\n"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            yield f"event: token\ndata: {json.dumps({'text': f'Error: {e} | Key starts with: {GROQ_API_KEY[:10]}... | Traceback: {tb[-200:]}'})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Policy endpoints ───

@app.get("/api/policy/recommendations")
def get_recommendations():
    path = DATA_DIR / "policy-recs.json"
    if not path.exists():
        raise HTTPException(503, "Policy recommendations not available.")
    return json.loads(path.read_text())


@app.get("/api/policy/signals")
def get_signals():
    path = DATA_DIR / "policy-signals.json"
    if not path.exists():
        raise HTTPException(503, "Policy signals not available.")
    return json.loads(path.read_text())


@app.get("/api/policy/borough/{slug}")
def get_borough_policy(slug: str):
    signals = json.loads((DATA_DIR / "policy-signals.json").read_text())
    recs = json.loads((DATA_DIR / "policy-recs.json").read_text())
    borough_name = None
    for name, data in signals.get("boroughs", {}).items():
        if data.get("borough_slug") == slug:
            borough_name = name
            break
    if not borough_name:
        raise HTTPException(404, f"Borough with slug '{slug}' not found")
    borough_recs = [r for r in recs.get("recommendations", []) if r.get("borough") == borough_name]
    return {"signals": signals["boroughs"][borough_name], "recommendations": borough_recs}


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


@app.post("/api/policy/deep-dive")
async def deep_dive(req: DeepDiveRequest):
    signals = json.loads((DATA_DIR / "policy-signals.json").read_text())
    if req.borough not in signals.get("boroughs", {}):
        raise HTTPException(400, f"Unknown borough '{req.borough}'")

    borough_signals = signals["boroughs"].get(req.borough, {})
    recs_path = DATA_DIR / "policy-recs.json"
    precomputed_recs = []
    if recs_path.exists():
        all_recs = json.loads(recs_path.read_text())
        precomputed_recs = [r for r in all_recs.get("recommendations", []) if r.get("borough") == req.borough]

    context_parts = []
    if borough_signals:
        context_parts.append(f"BOROUGH DATA:\n{json.dumps(borough_signals, indent=2)}")
    if precomputed_recs:
        context_parts.append(f"PRE-COMPUTED RECOMMENDATIONS:\n{json.dumps(precomputed_recs, indent=2)}")
    context_text = "\n\n".join(context_parts) or "No data available."

    system = (
        POLICY_SYSTEM_PROMPT
        + f"\n\nCONTEXT FOR {req.borough.upper()}:\n{context_text}\n\n"
        "The user is asking a follow-up question about policy recommendations. "
        "Provide a detailed, evidence-based response grounded in the data above."
    )

    messages = []
    for msg in req.history[-CHAT_HISTORY_LIMIT:]:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": req.question})

    def generate():
        if not ANTHROPIC_API_KEY:
            yield f"event: token\ndata: {json.dumps({'text': 'ANTHROPIC_API_KEY not configured.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            with client.messages.stream(model=ANTHROPIC_MODEL, max_tokens=POLICY_DEEPDIVE_MAX_TOKENS, system=system, messages=messages) as stream:
                for text in stream.text_stream:
                    yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            logger.error("Deep-dive error: %s", e)
            yield f"event: token\ndata: {json.dumps({'text': f'Error: {e}'})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── LSOA detail (from pre-computed lookup, cached) ───

@app.get("/api/lsoa/{lsoa_code}")
def lsoa_detail(lsoa_code: str):
    from _chat_context import _load_lsoa_lookup
    lookup = _load_lsoa_lookup()
    if lsoa_code not in lookup:
        raise HTTPException(404, "LSOA not found")
    return lookup[lsoa_code]


# ─── Briefing PDF ───

@app.get("/api/briefing/{borough_name}")
def borough_briefing(borough_name: str):
    pdf_bytes = generate_pdf(borough_name)
    if pdf_bytes is None:
        raise HTTPException(404, f"Borough not found: {borough_name}")
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", borough_name).strip("-")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Outreach-Briefing-{safe_name}.pdf"'},
    )

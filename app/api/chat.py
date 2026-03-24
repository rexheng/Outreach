"""Chat endpoint — SSE streaming via Google Gemini API."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
import json

from app.config import GEMINI_API_KEY, CHAT_MODEL, CHAT_MAX_TOKENS, CHAT_HISTORY_LIMIT

router = APIRouter(prefix="/api")

SYSTEM_PROMPT = """You are a policy advisor for the Outreach dashboard. You help policymakers, researchers, and practitioners understand neighbourhood-level mental health need across London's 4,994 Lower Layer Super Output Areas (LSOAs).

GROUNDING DATA:
{context_json}

RULES:
1. Ground every claim in the data provided above. If you don't have data for something, say so.
2. Speak in plain, accessible language — your audience includes policymakers and lived-experience experts, not just data scientists.
3. When referencing a borough, format it as [[borough:Borough Name]] (e.g. [[borough:Hackney]]).
4. When referencing a specific LSOA, format it as [[lsoa:LSOA_CODE|Display Name]] (e.g. [[lsoa:E01001110|Hackney 001A]]).
5. These entity markers will become clickable links in the dashboard — use them whenever you mention a specific place.
6. Keep responses concise and actionable. Suggest specific areas for intervention where the data supports it.
7. The Composite Need Index (CNI) ranges from 0–10. Tiers: Critical (8–10), High (6–8), Moderate (3–6), Low (0–3).
8. Remember: this is ecological (area-level) data, not individual-level. Do not make individual-level inferences.
9. IMD Rank 1 = most deprived. Health deprivation scores: negative = less deprived, positive = more deprived.
"""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest):
    """Stream a chat response as SSE events."""
    try:
        from app.data.chat_context import build_chat_context
        ctx = build_chat_context(req.message, req.history)
    except ImportError:
        ctx = {
            "context_text": "London-wide: 4,994 LSOAs, mean CNI 3.65, 71 High-need LSOAs.",
            "entities": {"boroughs": [], "lsoa_codes": []},
        }

    system_prompt = SYSTEM_PROMPT.format(context_json=ctx["context_text"])

    # Trim history to limit
    history = req.history[-CHAT_HISTORY_LIMIT:]

    # Build Gemini contents: history + current message
    # Gemini uses "user"/"model" roles (not "assistant")
    contents = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    def generate():
        # Send detected entities first
        yield f"event: context\ndata: {json.dumps(ctx['entities'])}\n\n"

        if not GEMINI_API_KEY:
            yield f"event: token\ndata: {json.dumps({'text': 'API key not configured. Please set GEMINI_API_KEY in your .env file.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content_stream(
                model=CHAT_MODEL,
                contents=contents,
                config={
                    "system_instruction": system_prompt,
                    "max_output_tokens": CHAT_MAX_TOKENS,
                },
            )
            for chunk in response:
                if chunk.text:
                    yield f"event: token\ndata: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            error_msg = str(e)
            if 'API_KEY_INVALID' in error_msg or 'api key' in error_msg.lower():
                yield f"event: token\ndata: {json.dumps({'text': 'Invalid API key. Please check GEMINI_API_KEY in your .env file.'})}\n\n"
            else:
                yield f"event: token\ndata: {json.dumps({'text': f'Error: {error_msg}'})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

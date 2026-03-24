"""Chat endpoint — SSE streaming via Google Gemini API."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
import json

from app.config import GEMINI_API_KEY, CHAT_MODEL, CHAT_MAX_TOKENS, CHAT_HISTORY_LIMIT

router = APIRouter(prefix="/api")

SYSTEM_PROMPT = """You are a senior policy advisor briefing local government officials and public health commissioners on where to direct mental health resources across London. You use the Outreach dashboard data — covering 4,994 neighbourhoods (LSOAs) across 33 boroughs.

YOUR ROLE: Turn data into decisions. Every response should answer "so what should we do about it?"

GROUNDING DATA:
{context_json}

HOW TO RESPOND:
- Lead with the actionable finding, not the methodology. "Barking and Dagenham needs targeted outreach" not "The mean CNI is 4.63."
- Frame numbers as policy implications: "1 in 5 residents report a disability" not "disability_rate_pct is 20.1%"
- When asked about an area, give a commissioning-ready brief: what's the need level, what's driving it, what type of intervention fits, and which specific neighbourhoods to prioritise first.
- Recommend concrete actions where the data supports it: expand talking therapies, fund community mental health teams, target social prescribing, commission outreach workers, etc.
- Compare to London averages to show relative severity — "50% above the London average" lands harder than raw numbers.
- Keep it short. Policymakers skim. Use 2-4 key points, not exhaustive lists.
- When referencing a borough, format as [[borough:Borough Name]].
- When referencing a specific LSOA, format as [[lsoa:LSOA_CODE|Display Name]].
- These become clickable links in the dashboard — use them for every place you mention.

WHAT TO AVOID:
- Don't explain what the CNI is or how tiers work unless asked. The user already knows.
- Don't list raw indicator values. Translate them: "high long-term sickness" not "ind_long_term_sick: 0.4231"
- Don't hedge excessively. If the data clearly shows a pattern, say so directly.
- Don't disclaim ecological fallacy in every response. Mention it only if the user is making individual-level claims.
- Don't repeat information the user can see on the dashboard. Add interpretation they can't get from the map alone.

CNI TIERS (for internal reference, don't recite these):
Critical 8-10, High 6-8, Moderate 3-6, Low 0-3. Scale is 0-10.
IMD Rank 1 = most deprived. Health deprivation: positive = more deprived.
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

"""Chat endpoint — SSE streaming via Anthropic Claude API."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import anthropic
import json

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CHAT_MAX_TOKENS, CHAT_HISTORY_LIMIT

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

    # Build Anthropic messages: history + current message
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})

    def generate():
        # Send detected entities first
        yield f"event: context\ndata: {json.dumps(ctx['entities'])}\n\n"

        if not ANTHROPIC_API_KEY:
            yield f"event: token\ndata: {json.dumps({'text': 'API key not configured. Please set ANTHROPIC_API_KEY in your .env file.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            with client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=CHAT_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
        except anthropic.AuthenticationError:
            yield f"event: token\ndata: {json.dumps({'text': 'Invalid API key. Please check ANTHROPIC_API_KEY in your .env file.'})}\n\n"
        except Exception as e:
            yield f"event: token\ndata: {json.dumps({'text': f'Error: {str(e)}'})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

"""Policy recommendation agent — pre-compute and deep-dive modes via Gemini."""

import json
import logging
import re
import time

from google import genai

from app.config import (
    GEMINI_API_KEY,
    POLICY_MODEL,
    POLICY_PRECOMPUTE_TEMP,
    POLICY_DEEPDIVE_TEMP,
    POLICY_MAX_TOKENS,
    POLICY_DEEPDIVE_MAX_TOKENS,
    POLICY_RECS_PATH,
    CHAT_HISTORY_LIMIT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a public health policy analyst specialising in mental health need \
and composite wellbeing across London boroughs. Your audience is local councillors and public \
health directors who need plain-language, evidence-grounded recommendations.

RULES:
1. Cite specific metrics from the data provided (SAMHI scores, population \
   figures, tier counts, IMD ranks). Never invent statistics.
2. Write in plain, accessible language suitable for councillors — avoid \
   jargon.
3. Reference actual service types where relevant: foodbanks, Mind centres, \
   Samaritans, NHS Talking Therapies (formerly IAPT), Citizens Advice \
   bureaux, Community Mental Health Teams (CMHTs), homelessness services, \
   Age UK branches, and council wellbeing hubs.
4. Short-term recommendations = actionable within 0-12 months. \
   Long-term recommendations = strategic over 1-5 years.
5. Reference LSOA codes (e.g. E01000001) when discussing specific \
   neighbourhoods so decision-makers can locate them on the dashboard.
6. Note that population figures are mid-2015 estimates and should be \
   treated as approximate.
7. Be specific about which areas need what — generic advice is not useful.
"""

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

BOROUGH_PROMPT_TEMPLATE = """\
Analyse the following borough data and produce exactly 6 policy \
recommendations: 3 short-term (0-12 months) and 3 long-term (1-5 years).

BOROUGH: {borough_name}
LSOA count: {lsoa_count}
Estimated population (mid-2015): {population:,}
Tier breakdown: {tier_counts}
Mean SAMHI 2022: {mean_samhi:.3f} (London average: {london_mean_samhi:.3f})
Trajectory: {trajectory}

SERVICE COVERAGE:
{service_coverage}

TOP LSOAs BY RISK:
{top_lsoas}

Return a JSON array of exactly 6 objects. Each object must have:
- "timeframe": "short-term" or "long-term"
- "priority": "high", "medium", or "low"
- "title": brief recommendation title (max 15 words)
- "description": 2-3 sentence explanation with specific actions
- "evidence": array of objects with "signal" and "value" keys citing the \
  data that supports this recommendation
- "affected_lsoas": array of LSOA codes most relevant to this recommendation

Return ONLY the JSON array, no other text.
"""

LONDON_PROMPT_TEMPLATE = """\
Analyse the following London-wide data and produce exactly 6 strategic \
policy recommendations: 3 short-term (0-12 months) and 3 long-term \
(1-5 years).

LONDON OVERVIEW:
Total LSOAs: {total_lsoas}
Total estimated population (mid-2015): {total_population:,}
Tier breakdown: {tier_counts}
Mean SAMHI 2022: {mean_samhi:.3f}
Boroughs with highest risk: {high_risk_boroughs}
Boroughs with improving trajectory: {improving_boroughs}
Boroughs with worsening trajectory: {worsening_boroughs}

SERVICE COVERAGE SUMMARY:
{service_coverage}

TOP LSOAs BY RISK (LONDON-WIDE):
{top_lsoas}

Return a JSON array of exactly 6 objects. Each object must have:
- "timeframe": "short-term" or "long-term"
- "priority": "high", "medium", or "low"
- "title": brief recommendation title (max 15 words)
- "description": 2-3 sentence explanation with specific actions
- "evidence": array of objects with "signal" and "value" keys citing the \
  data that supports this recommendation
- "affected_lsoas": array of LSOA codes most relevant to this recommendation

Return ONLY the JSON array, no other text.
"""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _format_service_coverage(coverage: dict) -> str:
    """Format a service coverage dict into human-readable text."""
    if not coverage:
        return "No service coverage data available."
    lines = []
    for service_type, details in coverage.items():
        if isinstance(details, dict):
            count = details.get("count", "N/A")
            pct = details.get("coverage_pct", details.get("pct", "N/A"))
            lines.append(f"- {service_type}: {count} locations, {pct}% LSOA coverage")
        else:
            lines.append(f"- {service_type}: {details}")
    return "\n".join(lines) if lines else "No service coverage data available."


def _format_top_lsoas(lsoas: list) -> str:
    """Format a list of top-risk LSOAs into human-readable text."""
    if not lsoas:
        return "No LSOA-level data available."
    lines = []
    for lsoa in lsoas[:10]:  # Cap at 10 for prompt length
        code = lsoa.get("lsoa_code", "unknown")
        name = lsoa.get("lsoa_name", "")
        samhi = lsoa.get("samhi_index_2022", "N/A")
        tier = lsoa.get("tier", "")
        pop = lsoa.get("total_16plus", "N/A")
        line = f"- {code}"
        if name:
            line += f" ({name})"
        line += f": SAMHI={samhi}, tier={tier}, pop_16plus={pop}"
        lines.append(line)
    return "\n".join(lines) if lines else "No LSOA-level data available."


# ---------------------------------------------------------------------------
# Gemini call with JSON parsing and retry
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from Gemini output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _call_gemini_json(prompt: str, max_retries: int = 3) -> list[dict]:
    """Call Gemini, parse JSON response, retry with exponential backoff."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=POLICY_MODEL,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "max_output_tokens": POLICY_MAX_TOKENS,
                    "temperature": POLICY_PRECOMPUTE_TEMP,
                },
            )
            text = _strip_markdown_fences(response.text)
            recs = json.loads(text)
            if not isinstance(recs, list):
                raise ValueError(f"Expected JSON array, got {type(recs).__name__}")
            return recs
        except Exception as e:
            last_error = e
            logger.warning(
                "Gemini JSON call attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                e,
            )
            if attempt < max_retries - 1:
                backoff = 2 ** (attempt + 1)  # 2s, 4s, 8s
                time.sleep(backoff)

    raise RuntimeError(
        f"Failed to get valid JSON from Gemini after {max_retries} attempts: {last_error}"
    )


# ---------------------------------------------------------------------------
# Pre-compute functions
# ---------------------------------------------------------------------------


def generate_borough_recs(
    borough_data: dict, london_mean_samhi: float, max_retries: int = 3
) -> list[dict]:
    """Generate policy recommendations for a single borough."""
    prompt = BOROUGH_PROMPT_TEMPLATE.format(
        borough_name=borough_data.get("borough_name", "Unknown"),
        lsoa_count=borough_data.get("lsoa_count", 0),
        population=borough_data.get("population", 0),
        tier_counts=borough_data.get("tier_counts", "N/A"),
        mean_samhi=borough_data.get("mean_samhi", 0.0),
        london_mean_samhi=london_mean_samhi,
        trajectory=borough_data.get("trajectory", "stable"),
        service_coverage=_format_service_coverage(
            borough_data.get("service_coverage", {})
        ),
        top_lsoas=_format_top_lsoas(borough_data.get("top_lsoas", [])),
    )
    return _call_gemini_json(prompt, max_retries=max_retries)


def generate_london_recs(
    london_data: dict, max_retries: int = 3
) -> list[dict]:
    """Generate London-wide strategic policy recommendations."""
    prompt = LONDON_PROMPT_TEMPLATE.format(
        total_lsoas=london_data.get("total_lsoas", 0),
        total_population=london_data.get("total_population", 0),
        tier_counts=london_data.get("tier_counts", "N/A"),
        mean_samhi=london_data.get("mean_samhi", 0.0),
        high_risk_boroughs=london_data.get("high_risk_boroughs", "N/A"),
        improving_boroughs=london_data.get("improving_boroughs", "N/A"),
        worsening_boroughs=london_data.get("worsening_boroughs", "N/A"),
        service_coverage=_format_service_coverage(
            london_data.get("service_coverage", {})
        ),
        top_lsoas=_format_top_lsoas(london_data.get("top_lsoas", [])),
    )
    return _call_gemini_json(prompt, max_retries=max_retries)


# ---------------------------------------------------------------------------
# Deep-dive streaming
# ---------------------------------------------------------------------------


def stream_deep_dive(
    borough_name: str,
    question: str,
    history: list[dict],
    signals: dict,
):
    """SSE streaming generator for deep-dive policy questions.

    Yields SSE-formatted events:
      event: token\ndata: {"text": "..."}\n\n
      event: done\ndata: {}\n\n
    """
    # Load borough data from signals
    borough_signals = signals.get(borough_name, signals.get("London", {}))

    # Load pre-computed recommendations if available
    precomputed_recs = []
    try:
        if POLICY_RECS_PATH.exists():
            with open(POLICY_RECS_PATH, "r", encoding="utf-8") as f:
                all_recs = json.load(f)
            precomputed_recs = all_recs.get(borough_name, all_recs.get("London", []))
    except Exception as e:
        logger.warning("Could not load pre-computed recs: %s", e)

    # Build context for the deep-dive
    context_parts = []
    if borough_signals:
        context_parts.append(f"BOROUGH DATA:\n{json.dumps(borough_signals, indent=2)}")
    if precomputed_recs:
        context_parts.append(
            f"PRE-COMPUTED RECOMMENDATIONS:\n{json.dumps(precomputed_recs, indent=2)}"
        )
    context_text = "\n\n".join(context_parts) if context_parts else "No data available."

    system = (
        SYSTEM_PROMPT
        + f"\n\nCONTEXT FOR {borough_name.upper()}:\n{context_text}\n\n"
        "The user is asking a follow-up question about policy recommendations. "
        "Provide a detailed, evidence-based response grounded in the data above."
    )

    # Build Gemini contents: history + current question
    history = history[-CHAT_HISTORY_LIMIT:]
    contents = []
    for msg in history:
        role = "model" if msg.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": question}]})

    if not GEMINI_API_KEY:
        yield f"event: token\ndata: {json.dumps({'text': 'API key not configured. Please set GEMINI_API_KEY in your .env file.'})}\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content_stream(
            model=POLICY_MODEL,
            contents=contents,
            config={
                "system_instruction": system,
                "max_output_tokens": POLICY_DEEPDIVE_MAX_TOKENS,
                "temperature": POLICY_DEEPDIVE_TEMP,
            },
        )
        for chunk in response:
            if chunk.text:
                yield f"event: token\ndata: {json.dumps({'text': chunk.text})}\n\n"
    except Exception as e:
        error_msg = str(e)
        logger.error("Deep-dive streaming error: %s", error_msg)
        if "API_KEY_INVALID" in error_msg or "api key" in error_msg.lower():
            yield f"event: token\ndata: {json.dumps({'text': 'Invalid API key. Please check GEMINI_API_KEY in your .env file.'})}\n\n"
        else:
            yield f"event: token\ndata: {json.dumps({'text': f'Error generating response: {error_msg}'})}\n\n"

    yield "event: done\ndata: {}\n\n"

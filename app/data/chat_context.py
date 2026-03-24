"""Chat context engine — entity detection, intent classification, data extraction."""

import re
from app.data.loader import _gdf_cache, _borough_cache, BOROUGH_COL

# Borough alias map — built lazily from cache
_alias_map: dict | None = None

INDICATOR_LABELS = {
    "ind_Health Deprivation and Disability Score": "Health Deprivation & Disability",
    "ind_Income Score (rate)": "Income Deprivation Rate",
    "ind_Employment Score (rate)": "Employment Deprivation Rate",
    "ind_long_term_sick": "Long-term Sick Rate",
    "ind_econ_inactive": "Economic Inactivity Rate",
    "ind_unemployed": "Unemployment Rate",
    "ind_Barriers to Housing and Services Score": "Barriers to Housing & Services",
    "ind_Crime Score": "Crime Score",
}

# Intent keywords
INTENT_KEYWORDS = {
    "ranking": {"worst", "top", "highest", "prioritize", "focus", "most", "which boroughs", "rank", "best", "lowest", "safest"},
    "comparison": {"compare", "vs", "versus", "difference", "between", "compared"},
    "drill_down": {"why", "what drives", "factors", "breakdown", "explain", "behind", "causes", "contributing"},
    "overview": {"overview", "summary", "tell me about", "how is", "describe", "overall", "general"},
}


def _build_alias_map() -> dict[str, str]:
    """Build lowercase alias → canonical borough name map."""
    global _alias_map
    if _alias_map is not None:
        return _alias_map

    _alias_map = {}
    if _borough_cache is None:
        return _alias_map

    for entry in _borough_cache:
        name = entry["borough"]
        canonical = name
        # Full name
        _alias_map[name.lower()] = canonical
        # Common shortenings
        parts = name.lower().split()
        if len(parts) > 1:
            # First word (e.g. "barking" for "Barking and Dagenham")
            _alias_map[parts[0]] = canonical
        # Handle "City of London" / "City of Westminster"
        if "city of" in name.lower():
            _alias_map[name.lower().replace("city of ", "")] = canonical
        # Handle "and" boroughs: "hammersmith" for "Hammersmith and Fulham"
        if " and " in name.lower():
            before_and = name.lower().split(" and ")[0].strip()
            _alias_map[before_and] = canonical
        # "Tower Hamlets" -> "tower hamlets"
        _alias_map[name.lower()] = canonical

    return _alias_map


def detect_boroughs(message: str) -> list[str]:
    """Find borough names mentioned in the message."""
    alias_map = _build_alias_map()
    msg_lower = message.lower()
    found = []
    seen = set()

    # Sort aliases by length descending to match longer names first
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if alias in msg_lower and alias_map[alias] not in seen:
            found.append(alias_map[alias])
            seen.add(alias_map[alias])

    return found


def detect_lsoa_codes(message: str) -> list[str]:
    """Find LSOA codes (E01xxxxxx pattern) in the message."""
    return re.findall(r"E01\d{6}", message)


def classify_intent(message: str) -> str:
    """Classify the user's intent from the message."""
    msg_lower = message.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                return intent

    return "overview"  # default


def get_london_overview() -> str:
    """London-wide statistics with ALL 33 borough summaries."""
    if _gdf_cache is None or _borough_cache is None:
        return "Data not loaded."

    gdf = _gdf_cache
    total = len(gdf)
    mean_lri = gdf["lri_score"].mean()
    median_lri = gdf["lri_score"].median()
    critical = (gdf["risk_tier"] == "Critical").sum()
    high = (gdf["risk_tier"] == "High").sum()
    moderate = (gdf["risk_tier"] == "Moderate").sum()
    low = (gdf["risk_tier"] == "Low").sum()

    # ALL boroughs ranked by mean CNI (compact one-liner each)
    ranked = sorted(_borough_cache, key=lambda b: b["mean_lri"], reverse=True)
    borough_lines = []
    for i, b in enumerate(ranked, 1):
        borough_lines.append(
            f"  {i}. {b['borough']}: CNI {b['mean_lri']:.2f} "
            f"({b['critical_count']}C/{b['high_count']}H/{b['lsoa_count']} LSOAs, "
            f"pop {b['total_population']:,.0f})"
        )

    return f"""LONDON OVERVIEW:
- Total LSOAs: {total}
- Mean CNI: {mean_lri:.2f}, Median: {median_lri:.2f}
- Need distribution: {critical} Critical, {high} High, {moderate} Moderate, {low} Low
- All 33 boroughs ranked by Composite Need Index (C=Critical, H=High-need LSOAs):
{chr(10).join(borough_lines)}"""


def get_top_boroughs(n: int = 10) -> str:
    """Top N boroughs ranked by mean CNI."""
    if _borough_cache is None:
        return "Data not loaded."

    top = sorted(_borough_cache, key=lambda b: b["mean_lri"], reverse=True)[:n]
    lines = []
    for i, b in enumerate(top, 1):
        lines.append(
            f"{i}. {b['borough']}: mean CNI {b['mean_lri']:.2f} "
            f"(median {b['median_lri']:.2f}, max {b['max_lri']:.2f}) — "
            f"{b['lsoa_count']} LSOAs, {b['critical_count']} Critical, {b['high_count']} High"
        )

    return f"TOP {n} BOROUGHS BY COMPOSITE NEED:\n" + "\n".join(lines)


def get_borough_summary(borough: str) -> str:
    """Detailed summary of a single borough."""
    if _gdf_cache is None or _borough_cache is None:
        return "Data not loaded."

    # Borough-level stats
    bstat = next((b for b in _borough_cache if b["borough"] == borough), None)
    if bstat is None:
        return f"Borough '{borough}' not found."

    # LSOA-level detail for this borough
    gdf = _gdf_cache
    borough_lsoas = gdf[gdf[BOROUGH_COL] == borough]

    if borough_lsoas.empty:
        return f"No LSOAs found for {borough}."

    # Indicator averages
    indicator_lines = []
    for col, label in INDICATOR_LABELS.items():
        if col in borough_lsoas.columns:
            val = borough_lsoas[col].mean()
            london_val = gdf[col].mean()
            diff = val - london_val
            indicator_lines.append(
                f"  - {label}: {val:.4f} (London avg: {london_val:.4f}, diff: {diff:+.4f})"
            )

    # Top 5 highest-risk LSOAs in this borough
    top_lsoas = borough_lsoas.nlargest(5, "lri_score")
    lsoa_lines = []
    for _, row in top_lsoas.iterrows():
        lsoa_lines.append(
            f"  - {row['lsoa_name']} ({row['lsoa_code']}): CNI {row['lri_score']:.2f} [{row['risk_tier']}]"
        )

    return f"""BOROUGH SUMMARY: {borough}
- Mean CNI: {bstat['mean_lri']:.2f}, Median: {bstat['median_lri']:.2f}, Max: {bstat['max_lri']:.2f}
- LSOAs: {bstat['lsoa_count']}, Population (16+): {bstat['total_population']:,.0f}
- Risk breakdown: {bstat['critical_count']} Critical, {bstat['high_count']} High
- Indicators (borough avg vs London avg):
{chr(10).join(indicator_lines)}
- Top 5 highest-risk LSOAs:
{chr(10).join(lsoa_lines)}"""


def get_borough_comparison(boroughs: list[str]) -> str:
    """Side-by-side comparison of 2+ boroughs."""
    if _borough_cache is None:
        return "Data not loaded."

    lines = ["BOROUGH COMPARISON:"]
    for name in boroughs:
        bstat = next((b for b in _borough_cache if b["borough"] == name), None)
        if bstat:
            lines.append(
                f"- {name}: mean CNI {bstat['mean_lri']:.2f}, "
                f"{bstat['critical_count']} Critical, {bstat['high_count']} High, "
                f"{bstat['lsoa_count']} LSOAs, pop {bstat['total_population']:,.0f}"
            )
        else:
            lines.append(f"- {name}: not found")

    return "\n".join(lines)


def get_lsoa_detail_for_chat(lsoa_code: str) -> str:
    """Full detail for a specific LSOA."""
    if _gdf_cache is None:
        return "Data not loaded."

    gdf = _gdf_cache
    row = gdf[gdf["lsoa_code"] == lsoa_code]
    if row.empty:
        return f"LSOA {lsoa_code} not found."

    r = row.iloc[0]
    indicator_lines = []
    for col, label in INDICATOR_LABELS.items():
        if col in r.index:
            val = r[col]
            if val is not None and str(val) != "nan":
                indicator_lines.append(f"  - {label}: {val:.4f}")

    return f"""LSOA DETAIL: {r.get('lsoa_name', lsoa_code)} ({lsoa_code})
- Borough: {r.get(BOROUGH_COL, 'Unknown')}
- CNI: {r.get('lri_score', 'N/A'):.2f}, Tier: {r.get('risk_tier', 'N/A')}
- IMD Score: {r.get('imd_score', 'N/A')}, SAMHI: {r.get('samhi_index_2022', 'N/A')}
- Population (16+): {r.get('total_16plus', 'N/A'):,.0f}
- Pop Density: {r.get('pop_density_2021', 'N/A'):,.0f}
- Health Bad/Very Bad: {r.get('health_bad_or_very_bad_pct', 'N/A')}%
- Disability Rate: {r.get('disability_rate_pct', 'N/A')}%
- Unpaid Care Rate: {r.get('unpaid_care_rate_pct', 'N/A')}%
- Indicators:
{chr(10).join(indicator_lines)}"""


def build_chat_context(message: str, history: list[dict] = None) -> dict:
    """Main entry point: detect entities, classify intent, extract relevant data.

    Returns {"context_text": str, "entities": {"boroughs": [...], "lsoa_codes": [...]}}
    """
    boroughs = detect_boroughs(message)
    lsoa_codes = detect_lsoa_codes(message)
    intent = classify_intent(message)

    # Also check recent history for context
    if history:
        for msg in history[-3:]:
            if msg.get("role") == "user":
                boroughs.extend(detect_boroughs(msg["content"]))
                lsoa_codes.extend(detect_lsoa_codes(msg["content"]))
        # Deduplicate preserving order
        seen_b = set()
        boroughs = [b for b in boroughs if not (b in seen_b or seen_b.add(b))]
        seen_l = set()
        lsoa_codes = [c for c in lsoa_codes if not (c in seen_l or seen_l.add(c))]

    # Build context based on what we detected
    context_parts = []

    # Always include a compact overview
    context_parts.append(get_london_overview())

    # Add specific data based on entities and intent
    if lsoa_codes:
        for code in lsoa_codes[:3]:  # Max 3 LSOAs
            context_parts.append(get_lsoa_detail_for_chat(code))

    if boroughs:
        if len(boroughs) == 1:
            context_parts.append(get_borough_summary(boroughs[0]))
        elif len(boroughs) >= 2:
            context_parts.append(get_borough_comparison(boroughs))
            # Also add detail for the first borough mentioned
            context_parts.append(get_borough_summary(boroughs[0]))

    return {
        "context_text": "\n\n".join(context_parts),
        "entities": {
            "boroughs": boroughs,
            "lsoa_codes": lsoa_codes,
        },
    }

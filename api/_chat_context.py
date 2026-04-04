"""Chat context builder for Vercel serverless — reads pre-computed JSON."""

import json
import re
from pathlib import Path
from api._config import DATA_DIR

# Lazy-loaded caches
_chat_data = None
_borough_list = None
_lsoa_lookup = None
_alias_map = None

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

INTENT_KEYWORDS = {
    "ranking": {"worst", "top", "highest", "prioritize", "focus", "most", "which boroughs", "rank", "best", "lowest", "safest"},
    "comparison": {"compare", "vs", "versus", "difference", "between", "compared"},
    "drill_down": {"why", "what drives", "factors", "breakdown", "explain", "behind", "causes", "contributing"},
    "overview": {"overview", "summary", "tell me about", "how is", "describe", "overall", "general"},
}


def _load_chat_data():
    global _chat_data
    if _chat_data is None:
        _chat_data = json.loads((DATA_DIR / "chat-boroughs.json").read_text())
    return _chat_data


def _load_borough_list():
    global _borough_list
    if _borough_list is None:
        _borough_list = json.loads((DATA_DIR / "boroughs.json").read_text())
    return _borough_list


def _load_lsoa_lookup():
    global _lsoa_lookup
    if _lsoa_lookup is None:
        _lsoa_lookup = json.loads((DATA_DIR / "lsoa-lookup.json").read_text())
    return _lsoa_lookup


def _build_alias_map():
    global _alias_map
    if _alias_map is not None:
        return _alias_map
    data = _load_chat_data()
    _alias_map = {}
    for name in data["borough_names"]:
        canonical = name
        _alias_map[name.lower()] = canonical
        parts = name.lower().split()
        if len(parts) > 1:
            _alias_map[parts[0]] = canonical
        if "city of" in name.lower():
            _alias_map[name.lower().replace("city of ", "")] = canonical
        if " and " in name.lower():
            _alias_map[name.lower().split(" and ")[0].strip()] = canonical
    return _alias_map


def detect_boroughs(message):
    alias_map = _build_alias_map()
    msg_lower = message.lower()
    found, seen = [], set()
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if alias in msg_lower and alias_map[alias] not in seen:
            found.append(alias_map[alias])
            seen.add(alias_map[alias])
    return found


def detect_lsoa_codes(message):
    return re.findall(r"E01\d{6}", message)


def classify_intent(message):
    msg_lower = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                return intent
    return "overview"


def get_london_overview():
    data = _load_chat_data()
    ov = data["london_overview"]
    borough_list = _load_borough_list()
    ranked = sorted(borough_list, key=lambda b: b["mean_lri"], reverse=True)
    lines = []
    for i, b in enumerate(ranked, 1):
        lines.append(
            f"  {i}. {b['borough']}: CNI {b['mean_lri']:.2f} "
            f"({b['critical_count']}C/{b['high_count']}H/{b['lsoa_count']} LSOAs, "
            f"pop {b['total_population']:,.0f})"
        )
    return (
        f"LONDON OVERVIEW:\n"
        f"- Total LSOAs: {ov['total_lsoas']}\n"
        f"- Mean CNI: {ov['mean_lri']}, Median: {ov['median_lri']}\n"
        f"- Need distribution: {ov['critical_count']} Critical, {ov['high_count']} High, "
        f"{ov['moderate_count']} Moderate, {ov['low_count']} Low\n"
        f"- All 33 boroughs ranked by Composite Need Index (C=Critical, H=High-need LSOAs):\n"
        + "\n".join(lines)
    )


def get_borough_summary(borough):
    data = _load_chat_data()
    if borough not in data["boroughs"]:
        return f"Borough '{borough}' not found."
    bd = data["boroughs"][borough]
    b = bd["stats"]
    ind_lines = [
        f"  - {label}: {vals['borough_avg']:.4f} (London avg: {vals['london_avg']:.4f}, diff: {vals['diff']:+.4f})"
        for label, vals in bd["indicators"].items()
    ]
    lsoa_lines = [
        f"  - {l['lsoa_name']} ({l['lsoa_code']}): CNI {l['lri_score']:.2f} [{l['risk_tier']}]"
        for l in bd["top5_lsoas"]
    ]
    return (
        f"BOROUGH SUMMARY: {borough}\n"
        f"- Mean CNI: {b['mean_lri']:.2f}, Median: {b['median_lri']:.2f}, Max: {b['max_lri']:.2f}\n"
        f"- LSOAs: {b['lsoa_count']}, Population (16+): {b['total_population']:,.0f}\n"
        f"- Risk breakdown: {b['critical_count']} Critical, {b['high_count']} High\n"
        f"- Indicators (borough avg vs London avg):\n" + "\n".join(ind_lines) + "\n"
        f"- Top 5 highest-risk LSOAs:\n" + "\n".join(lsoa_lines)
    )


def get_borough_comparison(boroughs):
    borough_list = _load_borough_list()
    lines = ["BOROUGH COMPARISON:"]
    for name in boroughs:
        bstat = next((b for b in borough_list if b["borough"] == name), None)
        if bstat:
            lines.append(
                f"- {name}: mean CNI {bstat['mean_lri']:.2f}, "
                f"{bstat['critical_count']} Critical, {bstat['high_count']} High, "
                f"{bstat['lsoa_count']} LSOAs, pop {bstat['total_population']:,.0f}"
            )
        else:
            lines.append(f"- {name}: not found")
    return "\n".join(lines)


def get_lsoa_detail_for_chat(lsoa_code):
    lookup = _load_lsoa_lookup()
    if lsoa_code not in lookup:
        return f"LSOA {lsoa_code} not found."
    r = lookup[lsoa_code]
    ind_lines = []
    for col, label in INDICATOR_LABELS.items():
        val = r.get(col)
        if val is not None:
            ind_lines.append(f"  - {label}: {val:.4f}")
    borough = r.get("Local Authority District name (2019)", "Unknown")
    return (
        f"LSOA DETAIL: {r.get('lsoa_name', lsoa_code)} ({lsoa_code})\n"
        f"- Borough: {borough}\n"
        f"- CNI: {r.get('lri_score', 'N/A')}, Tier: {r.get('risk_tier', 'N/A')}\n"
        f"- IMD Score: {r.get('imd_score', 'N/A')}, SAMHI: {r.get('samhi_index_2022', 'N/A')}\n"
        f"- Population (16+): {r.get('total_16plus', 'N/A'):,.0f}\n"
        f"- Health Bad/Very Bad: {r.get('health_bad_or_very_bad_pct', 'N/A')}%\n"
        f"- Disability Rate: {r.get('disability_rate_pct', 'N/A')}%\n"
        f"- Unpaid Care Rate: {r.get('unpaid_care_rate_pct', 'N/A')}%\n"
        f"- Indicators:\n" + "\n".join(ind_lines)
    )


def build_chat_context(message, history=None):
    boroughs = detect_boroughs(message)
    lsoa_codes = detect_lsoa_codes(message)

    if history:
        for msg in history[-3:]:
            if msg.get("role") == "user":
                boroughs.extend(detect_boroughs(msg["content"]))
                lsoa_codes.extend(detect_lsoa_codes(msg["content"]))
        seen_b = set()
        boroughs = [b for b in boroughs if not (b in seen_b or seen_b.add(b))]
        seen_l = set()
        lsoa_codes = [c for c in lsoa_codes if not (c in seen_l or seen_l.add(c))]

    parts = [get_london_overview()]

    if lsoa_codes:
        for code in lsoa_codes[:3]:
            parts.append(get_lsoa_detail_for_chat(code))

    if boroughs:
        if len(boroughs) == 1:
            parts.append(get_borough_summary(boroughs[0]))
        elif len(boroughs) >= 2:
            parts.append(get_borough_comparison(boroughs))
            parts.append(get_borough_summary(boroughs[0]))

    return {
        "context_text": "\n\n".join(parts),
        "entities": {"boroughs": boroughs, "lsoa_codes": lsoa_codes},
    }

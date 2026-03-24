# Policy Recommendations Agent — Design Spec

## Overview

A new "Policy Recommendations" tab in the FastAPI dashboard (Dashboard B) that uses a hybrid rule-based + Gemini AI architecture to generate evidence-based short-term and long-term mental health policy recommendations at borough and London-wide scope.

## Architecture

```
                    BUILD TIME                          RUNTIME
                    ---------                           -------
master_lsoa.gpkg
       |
       v
+------------------+
| policy_signals.py |  Deterministic signal computation
|                  |  5 per-LSOA signals + borough aggregates
+--------+---------+
         |
         v
  policy_signals.json
         |
         v
+------------------+     +----------------------+
|build_policy_recs |---->| Google Gemini API     |
|        .py       |     | gemini-2.5-flash      |
+--------+---------+     +----------------------+
         |
         v
policy_recommendations.json ------> GET /api/policy/recommendations
                                    GET /api/policy/borough/{slug}

policy_signals.json --------------> POST /api/policy/deep-dive
                                         |
                                         v
                                    Google Gemini API (SSE streaming)
                                         |
                                         v
                                    Frontend (rec cards + map)
```

## Column Mapping Table

Every column referenced in this spec mapped to its exact GeoPackage name:

| Spec shorthand | GeoPackage column name | Notes |
|---|---|---|
| `lsoa_code` | `lsoa_code` | Primary key |
| `lsoa_name` | `lsoa_name` | |
| `borough_name` | `Local Authority District name (2019)` | 33 unique values |
| `borough_code` | `Local Authority District code (2019)` | E09xxxxxx |
| `imd_score` | `imd_score` | Range 2.3-64.7, 335 nulls |
| `imd_decile` | `Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)` | 1-10, 335 nulls |
| `samhi_index_2022` | `samhi_index_2022` | |
| `samhi_index_2019` | `samhi_index_2019` | |
| `geo_barriers_score` | `Geographical Barriers Sub-domain Score` | IMD sub-domain; higher = more deprived. Range -2.76 to 1.70. 335 nulls. Used as transport isolation proxy. |
| `health_deprivation_score` | `Health Deprivation and Disability Score` | |
| `total_pop_2015` | `Total population: mid 2015 (excluding prisoners)` | Best available all-ages population. Label as "estimated" in outputs. |
| `total_16plus` | `total_16plus` | Census 2021, 16+ only |
| `pop_density_2021` | `pop_density_2021` | |
| `employment_rate` | `employment_rate` | |
| `health_bad_pct` | `health_bad_or_very_bad_pct` | Census 2021 TS037 |
| `disability_rate` | `disability_rate_pct` | Census 2021 TS038 |
| `dist_community_service` | `dist_to_nearest_community_service_m` | metres |
| `dist_mh_charity` | `dist_to_nearest_mental_health_charity_m` | metres |
| `dist_foodbank` | `dist_to_nearest_foodbank_m` | metres |
| `dist_nhs_therapy` | `dist_to_nearest_nhs_talking_therapy_m` | metres (spec previously said "IAPT") |
| `dist_citizens_advice` | `dist_to_nearest_citizens_advice_m` | metres |
| `dist_cmht` | `dist_to_nearest_nhs_cmht_m` | metres |
| `dist_homelessness` | `dist_to_nearest_homelessness_service_m` | metres |
| `dist_older_charity` | `dist_to_nearest_older_people_charity_m` | metres |
| `dist_wellbeing_hub` | `dist_to_nearest_council_wellbeing_hub_m` | metres |
| `cs_total` | `community_services_total` | count of services in LSOA |
| `cs_foodbank` | `cs_foodbank_count` | |
| `cs_mh_charity` | `cs_mental_health_charity_count` | |
| `cs_nhs_therapy` | `cs_nhs_talking_therapy_count` | |
| `cs_citizens_advice` | `cs_citizens_advice_count` | |
| `cs_cmht` | `cs_nhs_cmht_count` | |
| `cs_homelessness` | `cs_homelessness_service_count` | |

## Component 1: Signal Computation Engine

**File:** `app/data/policy_signals.py`

Reads `master_lsoa.gpkg`, computes deterministic signals, outputs `policy_signals.json`.

### Null handling strategy

- `imd_score`, `imd_decile`, `geo_barriers_score`: 335 nulls (2021 boundary splits). Fill with London median before normalisation. Flag these LSOAs as `imd_imputed: true` in output.
- `samhi_index_2022`, `samhi_index_2019`: fill nulls with 0 (neutral trajectory). Flag as `samhi_imputed: true`.
- Distance columns: no nulls (all 4,994 have values).

### Per-LSOA signals (5 new columns)

| Signal | Formula | Range | Purpose |
|---|---|---|---|
| `service_desert_score` | Normalised weighted composite of `dist_community_service`, `dist_mh_charity`, `dist_foodbank` (equal weight, min-max normalised). Then multiplied by deprivation weight: `(11 - imd_decile) / 10`. So decile 1 (most deprived) gets 1.0x, decile 10 gets 0.1x. Result re-normalised 0-1. | 0-1 | Deprived areas far from services |
| `mh_trajectory` | `samhi_index_2022 - samhi_index_2019`. Positive = worsening, negative = improving. | ~-2 to +2 | Mental health trend direction |
| `transport_isolation_score` | `normalise(geo_barriers_score)`. Uses IMD Geographical Barriers Sub-domain as proxy for transport/service accessibility. Higher score = more isolated. No PTAL data available. | 0-1 | Geographical isolation from services/transport |
| `service_gap_flags` | Bitmask integer. Bit 0: `dist_foodbank > 3000`. Bit 1: `dist_mh_charity > 3000`. Bit 2: `dist_nhs_therapy > 3000`. Bit 3: `dist_citizens_advice > 3000`. Bit 4: `dist_cmht > 5000`. | 0-31 | Which specific service types are missing nearby |
| `composite_need_score` | `0.30 * service_desert + 0.25 * normalise(samhi_index_2022) + 0.20 * normalise(imd_score) + 0.15 * transport_isolation + 0.10 * normalise(max(mh_trajectory, 0))`. Note: only positive trajectory (worsening) contributes; improving areas get 0. | 0-1 | Single priority ranking metric |

**Normalisation:** Min-max across all 4,994 London LSOAs. Higher = worse/more need.

**Tier assignment** from `composite_need_score`:
- Critical: >= 0.75
- High: >= 0.50
- Moderate: >= 0.25
- Low: < 0.25

### Per-borough aggregates

Grouped by `Local Authority District name (2019)` (33 boroughs).

For each borough, compute:

```json
{
  "borough_name": "Tower Hamlets",
  "borough_slug": "tower-hamlets",
  "lsoa_count": 132,
  "population_est_2015": 310000,
  "population_note": "Mid-2015 estimates excluding prisoners",
  "tier_counts": {"critical": 12, "high": 34, "moderate": 56, "low": 30},
  "mean_composite_need": 0.52,
  "max_composite_need": 0.89,
  "mean_samhi_2022": 0.34,
  "mean_samhi_2019": 0.28,
  "mh_trajectory": "worsening",
  "mean_trajectory_delta": 0.06,
  "pct_lsoas_worsening": 0.72,
  "mean_service_desert": 0.41,
  "service_coverage": {
    "foodbank": {"lsoas_with_service": 2, "mean_dist_m": 1840, "lsoas_beyond_3km": 18},
    "mental_health_charity": {"lsoas_with_service": 3, "mean_dist_m": 1200, "lsoas_beyond_3km": 8},
    "nhs_talking_therapy": {"lsoas_with_service": 1, "mean_dist_m": 2100, "lsoas_beyond_3km": 24},
    "citizens_advice": {"lsoas_with_service": 1, "mean_dist_m": 1950, "lsoas_beyond_3km": 20},
    "nhs_cmht": {"lsoas_with_service": 1, "mean_dist_m": 2800, "lsoas_beyond_3km": 45},
    "homelessness_service": {"lsoas_with_service": 5, "mean_dist_m": 980, "lsoas_beyond_3km": 3},
    "older_people_charity": {"lsoas_with_service": 1, "mean_dist_m": 2300, "lsoas_beyond_3km": 30},
    "council_wellbeing_hub": {"lsoas_with_service": 1, "mean_dist_m": 3100, "lsoas_beyond_3km": 60}
  },
  "mean_geo_barriers_score": 0.15,
  "top_5_lsoas": [
    {
      "lsoa_code": "E01004200",
      "lsoa_name": "Tower Hamlets 017E",
      "composite_need_score": 0.89,
      "samhi_index_2022": 0.78,
      "imd_score": 45.2,
      "key_gaps": ["no NHS talking therapy within 3km", "high geographical barriers"]
    }
  ]
}
```

**Notes on `service_coverage` counts:**
- `lsoas_with_service` = number of LSOAs in the borough where the corresponding `cs_*_count > 0`. This counts LSOAs containing a service, not unique service locations. For unique service counts, query `community_services.csv` filtered by borough.
- `mean_dist_m` = mean of the `dist_to_nearest_*_m` column across borough LSOAs.
- `lsoas_beyond_3km` (or 5km for CMHTs) = count of LSOAs exceeding the threshold.

### London-wide aggregate

Same structure as borough but across all 4,994 LSOAs. Additionally includes:
- `top_10_boroughs`: ranked by `mean_composite_need` descending
- `trajectory_summary`: `{"pct_worsening": 0.62, "pct_stable": 0.15, "pct_improving": 0.23}` (threshold: abs(delta) < 0.02 = stable)
- `total_critical_lsoas`, `total_high_lsoas`: London-wide counts

**Deferred from v1:** Cross-borough service desert clustering (requires spatial clustering algorithm, e.g. DBSCAN). Will be added in a future iteration if needed.

### Output

`policy_signals.json`:
```json
{
  "schema_version": "1.0",
  "generated_at": "2026-03-24T18:00:00Z",
  "london_wide": { ... },
  "boroughs": {
    "Tower Hamlets": { ... },
    "Hackney": { ... }
  }
}
```

## Component 2: Gemini Recommendation Agent

**Files:**
- `app/api/policy_agent.py` — Gemini API client + prompt construction
- `build_policy_recs.py` — Build-time script that generates all recommendations

### Agent persona (system prompt)

```
You are a public health policy analyst specialising in neighbourhood-level
mental health intervention in London. You generate evidence-based
recommendations grounded strictly in the data signals provided.

Rules:
- Every recommendation MUST cite specific metrics from the signals provided
- Use plain language accessible to local councillors and community organisations
- Do not invent statistics -- only reference values present in the data
- When recommending services, reference the actual service types in the data:
  foodbanks, mental health charities (Mind, Samaritans), NHS talking therapies,
  Citizens Advice, community mental health teams (CMHTs), homelessness services,
  older people charities (Age UK), council wellbeing hubs
- Short-term means actionable within 0-12 months with existing resources
- Long-term means structural changes requiring 1-5 years and new investment
- Reference specific LSOA codes and names for spatial precision
- Population figures are mid-2015 estimates -- note this caveat when citing them
```

### Pre-computed mode

`build_policy_recs.py` iterates:
1. Load `policy_signals.json`
2. For London-wide: send London aggregate + top 10 borough summaries to Gemini
3. For each borough: send borough aggregate + top 5 LSOAs to Gemini
4. Request structured JSON response (3 short-term + 3 long-term per scope)
5. Save each borough as it completes (incremental write for resilience)
6. Save final output to `policy_recommendations.json`

**Resilience:**
- Retry with exponential backoff (3 attempts, 2s/4s/8s) on API failure
- Incremental saves: if interrupted at borough 20, re-running with `--resume` skips boroughs already in the output file
- Validation: verify each Gemini response parses as valid JSON with required fields before saving

**Per-recommendation schema:**
```json
{
  "id": "tower-hamlets-st-1",
  "borough": "Tower Hamlets",
  "scope": "borough",
  "timeframe": "short_term",
  "priority": "critical",
  "title": "Deploy mobile mental health outreach in Isle of Dogs",
  "description": "Three LSOAs in the Isle of Dogs (E01004200, E01004201, E01004203) score above 0.8 on the composite need index but are over 3km from the nearest mental health charity. A weekly mobile clinic at Crossharbour could reach an estimated 4,800 residents currently in a service desert.",
  "evidence": [
    {"signal": "service_desert_score", "value": "0.82 (top 3% London-wide)"},
    {"signal": "dist_to_nearest_mental_health_charity_m", "value": "3,400m"},
    {"signal": "samhi_index_2022", "value": "0.71 (critical tier)"},
    {"signal": "imd_decile", "value": "2 (high deprivation)"}
  ],
  "affected_lsoas": ["E01004200", "E01004201", "E01004203"]
}
```

**Gemini API config:**
- Model: `gemini-2.5-flash` (aligns with existing `app/config.py` CHAT_MODEL)
- API key: from `.env` file via `GEMINI_API_KEY` (reuses existing config constant)
- Temperature: 0.3 (pre-computed, for reproducibility)
- Response format: JSON mode
- Max output tokens: 4096 per borough call

### Live drill-down mode

Endpoint receives user question + currently selected borough. Constructs prompt:
```
[System prompt as above]

Context -- {borough_name}:
{borough aggregate JSON from policy_signals.json}

Existing recommendations for this borough:
{pre-computed recs JSON}

User question: {user_input}
```

- Model: `gemini-2.5-flash`
- Temperature: 0.7 (more conversational)
- Streaming: SSE via `text/event-stream`
- Response: plain text with `[[lsoa:CODE|Name]]` markup for clickable links

## Component 3: API Routes

**File:** `app/api/policy_routes.py`

| Endpoint | Method | Description |
|---|---|---|
| `/api/policy/recommendations` | GET | Returns full `policy_recommendations.json`. ~204 records, acceptable for client-side filtering. |
| `/api/policy/borough/{slug}` | GET | Returns recs + signals for a single borough. `slug` is URL-safe (e.g. `tower-hamlets`, `barking-and-dagenham`, `city-of-london`). Slug generated from borough name: `name.lower().replace(" ", "-").replace("&", "and")`. |
| `/api/policy/signals` | GET | Returns `policy_signals.json` for frontend map colouring. |
| `/api/policy/deep-dive` | POST | SSE streaming. Body: `{"borough": "Tower Hamlets", "question": "...", "history": [...]}`. |

**Input validation for deep-dive:**
- `borough`: must match one of the 33 canonical borough names (validated against `policy_signals.json` keys). Return 400 if invalid.
- `question`: max 1000 characters. Return 400 if exceeded.
- `history`: max 10 entries (aligns with `CHAT_HISTORY_LIMIT` in config). Silently truncate to most recent 10.

All routes registered on the existing FastAPI app in `app/main.py`.

## Component 4: Frontend Tab

**Deferred** -- implementation blocked until the frontend overhaul agent completes.

**Design intent** (to be styled against the new design system):

- Split panel: recommendation cards (left 40%) + Leaflet map (right 60%)
- Map recoloured by `composite_need_score` when tab is active
- London-wide banner at top with key stats (LSOAs in crisis, trajectory, coverage gaps)
- Borough dropdown filters recs + zooms map
- Rec cards: left border coloured by priority, evidence tags, clickable LSOA codes
- Short-term and long-term sections with distinct headers
- Deep Dive chat input at bottom of left panel, SSE streaming response
- Hovering a rec card highlights affected LSOAs on map
- Matches the new editorial/warm design language (terracotta, serif headings, card-based)

**Files to create (after frontend overhaul):**
- `app/static/js/policy.js` -- tab logic, rec card rendering, map integration, deep-dive SSE
- Modifications to `app/static/index.html` -- tab navigation, policy tab container
- Modifications to CSS file -- policy-specific styles inheriting new design system

## File Summary

### Build now (backend)
| File | Type | Purpose |
|---|---|---|
| `app/data/policy_signals.py` | New | Signal computation engine |
| `app/api/policy_agent.py` | New | Gemini API client + prompt construction |
| `app/api/policy_routes.py` | New | FastAPI endpoints for policy data |
| `build_policy_recs.py` | New | Build-time script to generate all recs |
| `app/main.py` | Edit | Register policy routes |
| `app/config.py` | Edit | Add policy-specific config constants |
| `.env` | Edit | Already has `GEMINI_API_KEY` -- no new keys needed |
| `policy_signals.json` | Generated | Pre-computed signals |
| `policy_recommendations.json` | Generated | Pre-computed recommendations |

### Build after frontend overhaul
| File | Type | Purpose |
|---|---|---|
| `app/static/js/policy.js` | New | Frontend tab logic |
| `app/static/index.html` | Edit | Tab navigation + container |
| CSS file | Edit | Policy tab styles |

## Dependencies

**New Python packages:**
- `google-genai` (Google Gemini SDK) -- already installed (used by existing chat feature)
- `python-dotenv` -- already installed

**Existing (no changes):**
- `geopandas`, `pandas`, `numpy`, `fastapi`, `uvicorn`

## Security

- Gemini API key stored in `.env`, never committed (already in `.gitignore`)
- Deep-dive endpoint rate-limited via `slowapi` middleware: 20 requests/hour per IP
- Input validation: question max 1000 chars, history max 10 entries, borough validated against known list
- No user data sent to Gemini -- only pre-computed LSOA aggregates and the user's question text

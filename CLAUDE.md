# Outreach -- Project Instructions

## Project Context

An interactive data tool that links mental health indicators, socioeconomic deprivation, health/disability data, and community service accessibility at LSOA level across London -- enabling researchers, policymakers, and practitioners to explore neighbourhood-level determinants of mental health.

## Key Files

| File | Role |
|---|---|
| `master_lsoa.gpkg` | Assembled GeoPackage -- 4,994 London LSOAs, single table `master_lsoa`, 120 columns |
| `app/` | FastAPI "Outreach" dashboard -- run with `uvicorn app.main:app` |
| `app/main.py` | FastAPI entry point with lifespan data loading |
| `app/config.py` | Configuration: GPKG paths, display columns, API keys, chat settings |
| `app/api/routes.py` | Data API: `/api/geojson`, `/api/boroughs`, `/api/lsoa/{code}`, `/api/metadata` |
| `app/api/chat.py` | LLM chat endpoint: `POST /api/chat` (SSE streaming via Anthropic Claude) |
| `app/data/loader.py` | GPKG loading, CNI computation, GeoJSON cache (`_gdf_cache`, `_borough_cache`) |
| `app/data/chat_context.py` | Entity detection, intent classification, data extraction for chat context |
| `app/static/` | Frontend: index.html, CSS (style.css, chat.css), JS (map.js, controls.js, sidebar.js, chat.js) |
| `.env` | `ANTHROPIC_API_KEY` (gitignored, required for chatbot) |
| `dashboard/index.html` | Legacy static dashboard (serve via HTTP) |
| `build_dashboard.py` | Regenerates legacy dashboard data files from GPKG |
| `data RAW/` | Source CSVs/Excel -- do not modify |
| `data_downloads/` | Downloaded enrichment datasets (SAMHI, Census TS037/38/39, LSOA lookup) |
| `Project_Overview.md` | Full project documentation and data dictionary |
| `References_and_Research_Data.md` | Full dataset provenance, methodology, citations, ethical considerations |
| `tasks/todo.md` | Current task tracking |
| `tasks/lessons.md` | Lessons learned from corrections |

## Data Handling Rules

### Centralised GPKG Architecture
All project data **must** live in a single file: `master_lsoa.gpkg`. This is non-negotiable. The webapp will pull directly from this file -- no CSVs, no separate databases, no JSON exports as primary data stores.

- **All new columns, derived metrics, and joined datasets get added to `master_lsoa.gpkg`** as either new columns on an existing table or as a new table within the same GPKG.
- **Never create separate output files** (CSVs, Parquet, JSON) as the canonical data source. Temporary exports for analysis are fine, but the GPKG is always the source of truth.
- **The webapp reads from the GPKG directly** -- design all data pipelines with this endpoint in mind.
- When adding new data, write it back to the GPKG. Use geopandas `to_file()` with `driver='GPKG'` and `layer=` parameter, or sqlite3 for non-spatial tables.

### GPKG Structure
- **Single table**: `master_lsoa` (120 columns). The old `master_lsoa_enriched_with_route_pressure` table was dropped.
- New feature tables should follow the naming pattern: `master_lsoa_{feature_group}`
- **Geometry**: MULTIPOLYGON in `geometry` column, CRS EPSG:27700 (British National Grid)

### Data Integrity
- **LSOA vintage**: Boundaries are 2021; IMD data is 2011-vintage mapped forward; SAMHI mapped from 2011→2021 via ONS lookup
- **Known gap**: 335 LSOAs (new 2021 codes, e.g. Havering splits) have null IMD scores -- no 2011 match. These DO have SAMHI data (interpolated via lookup) and full Census data.
- **Coverage**: 33 London boroughs + City of London (4,994 LSOAs). England total: ~33,000+.
- Raw files in `data RAW/` are read-only reference copies. Never modify them.
- Downloaded enrichment files in `data_downloads/` are cached copies. Re-download if needed.

## Column Conventions

- IMD: `{domain}_score`, `{domain}_rank_where_1_is_most_deprived`, `{domain}_decile_where_1_is_most_deprived_10_of_lsoas`
- SAMHI: `samhi_index_{year}`, `samhi_dec_{year}`, `antidep_rate_{year}`, `est_qof_dep_{year}`, `mh_hospital_rate_{year}`, `dla_pip_pct_{year}`
- Census health: `health_very_good` through `health_very_bad`, `health_bad_or_very_bad_pct`
- Census disability: `disabled_limited_a_lot`, `disabled_limited_a_little`, `disability_rate_pct`
- Census unpaid care: `unpaid_care_19h_or_less`, `unpaid_care_20_to_49h`, `unpaid_care_50h_plus`, `unpaid_care_rate_pct`
- Community services: `dist_to_nearest_{service_type}_m`, `cs_{service_type}_count`
- Census economic activity: `total_16plus`, `econ_active`, `in_employment`, `unemployed`, `long_term_sick`, etc.

## Analysis Guardrails

- **Ecological data**: LSOA-level aggregates, not individual-level. Do not make individual-level inferences.
- **IMD direction**: Rank 1 = most deprived. Higher rank = less deprived.
- **SAMHI direction**: Higher index = greater mental health need. Decile 10 = highest need.
- **Health deprivation scores**: Negative = less deprived, positive = more deprived. Range: -3.22 to 1.57.
- **IMD score range**: 2.3 to 64.7 (mean ~21.3).
- **SAMHI index range**: -2.01 to 4.67 (mean -0.28). London generally scores below England average (negative = lower need).
- **Antidepressant rate**: Per 1,000 population. Range: 8.6 to 42.5. Outer London boroughs often score higher than inner.
- **COVID impact**: Every borough's SAMHI worsened between 2019 and 2022. Use `samhi_index_2019` for pre-COVID baseline.
- SAMHI is a composite of 4 sub-indicators (antidepressants, QOF depression, MH hospital admissions, DLA/PIP). The sub-indicators are also available individually for decomposed analysis.

## Tooling

- **Data**: Python with geopandas, pandas; sqlite3 for quick queries
- **Viz**: Leaflet + Chart.js (dashboard), matplotlib/seaborn for static analysis
- **Outreach Dashboard**: `uvicorn app.main:app` — FastAPI serving Leaflet choropleth with Composite Need Index, editorial sidebar, and LLM chatbot
- **Legacy Dashboard**: `dashboard/index.html` — static HTML, served via any HTTP server. Rebuild data with `python build_dashboard.py`
- **LLM Chat**: Anthropic Claude API via `anthropic` SDK. Requires `ANTHROPIC_API_KEY` in `.env`. Model: `claude-sonnet-4-20250514`
- **Output**: All derived data goes back into `master_lsoa.gpkg`; document new columns in Project_Overview.md

## Chatbot Architecture

The Outreach dashboard includes an AI policy chatbot (`POST /api/chat`):
- **Data context**: `app/data/chat_context.py` detects boroughs/LSOAs/intent from user messages, extracts targeted data slices from `loader._gdf_cache` and `loader._borough_cache`
- **Streaming**: FastAPI SSE → Anthropic streaming SDK → token-by-token to frontend
- **Entity links**: Claude outputs `[[borough:Name]]` / `[[lsoa:CODE|Display]]` markers; frontend renders as clickable spans that trigger map zoom
- **Z-index**: toggle/panel at 850 (between controls at 800 and sidebar at 900)
- **Config**: `CHAT_MODEL`, `CHAT_MAX_TOKENS`, `CHAT_HISTORY_LIMIT` in `app/config.py`

## Frontend Design Direction

**Brand name**: Outreach -- "The Geography of Wellbeing"

The webapp uses a **warm terracotta/earth-tone palette** inspired by editorial wellness design. No teal. The aesthetic is closer to a magazine feature than a SaaS dashboard.

### Colour Palette
| Token | Hex | Usage |
|---|---|---|
| `--terra` | `#B5725A` | Primary accent: radio buttons, indicator bars, hover states, drop caps |
| `--terra-dark` | `#7D5A48` | Sidebar headers, dark card surfaces |
| `--terra-deep` | `#6B4A3A` | Deepest accent: close buttons, critical need tier, chat header |
| `--terra-light` | `#C4805A` | Badges, hover states, links |
| `--clay` | `#D4A574` | Moderate need tier, warm midtone |
| `--sand` | `#E5D5C5` | Low need tier, light fills |
| `--cream` | `#FAF7F3` | Page background |
| `--linen` | `#F5F0EB` | Card backgrounds, alternating rows |
| `--text` | `#3D3530` | Headlines, primary text |
| `--text-body` | `#5A504A` | Body paragraphs |
| `--text-muted` | `#9A8E85` | Labels, captions |
| `--border` | `#E5DDD5` | Dividers, borders |

### Choropleth Ramp (warm, sequential)
Lowest need `#F5F0EB` → `#E5D5C5` → `#D4A574` → `#B5725A` → Highest need `#6B4A3A`

### Typography
- **Playfair Display** (serif): headlines, KPI values, drop caps, editorial text
- **DM Sans** (sans-serif): body text, UI labels, controls, tooltips

### Layout
- Left editorial panel with "Outreach" branding, introductory narrative, radio-card layer selector, borough filter
- Full-width Leaflet map as centrepiece
- Right sidebar slides in on LSOA click with brown header strip, KPI cards, indicator bars, editorial paragraph, nearest services
- Floating chat panel (bottom-right) with terracotta styling

### Key Terminology
- "Composite Need Index" (not "Loneliness Risk Index")
- Need tiers: "Critical Need", "High Need", "Elevated", "Lower Need"
- "Neighbourhoods" (not "LSOAs" in UI)
- See `docs/project/FRONTEND_DESIGN_PROMPT.md` for full design specification

## Task Management

1. Write plans to `tasks/todo.md` with checkable items before starting work
2. Mark items complete as you go
3. After corrections, update `tasks/lessons.md` with the pattern
4. Verify changes work before marking complete

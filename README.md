# Outreach -- The Geography of Wellbeing

An interactive data tool mapping neighbourhood-level mental health need across London's 4,994 Lower Super Output Areas (LSOAs).

**Live demo:** outreach-claude.up.railway.app

## What it does

Outreach links mental health indicators, socioeconomic deprivation, disability, unpaid care burden, and community service accessibility into a single geospatial dataset -- then makes it explorable through an interactive dashboard with an AI policy chatbot.

The tool helps researchers, policymakers, and practitioners:
- Identify neighbourhoods where mental health need is highest
- Understand what socioeconomic factors drive that need
- Find gaps in community service coverage
- Ask natural-language questions and get data-grounded answers

## Features

- **Choropleth map** -- 4,994 LSOAs colour-coded by Composite Need Index (0-10), with 9 switchable indicator layers
- **Borough and risk-tier filtering** -- drill into any of London's 33 boroughs or filter by need severity (Critical / High / Moderate / Low)
- **LSOA detail sidebar** -- click any neighbourhood for a full breakdown: need score, indicator bars, borough comparison, nearest community services
- **AI policy chatbot** -- ask questions like "Which boroughs should we prioritise?" or "What drives risk in Hackney?" and get streamed, data-grounded responses with clickable map links
- **Borough briefing packs** -- downloadable one-page PDFs with headline KPIs, priority neighbourhoods, and policy-ready summaries
- **Composite Need Index** -- two-pillar weighted model combining socioeconomic (IMD health, income, employment, housing, crime) and demographic (long-term sickness, economic inactivity, unemployment) indicators

## Data sources

| Dataset | Source | Coverage |
|---------|--------|----------|
| Index of Multiple Deprivation 2019 | MHCLG | 7 domains, scores/ranks/deciles |
| SAMHI v5.00 (2019, 2022) | University of Bristol / PLDR | Composite mental health index + 4 sub-indicators |
| Census 2021 TS037/TS038/TS039 | ONS via Nomis | General health, disability, unpaid care |
| Census 2021 TS006/TS066 | ONS | Population density, economic activity |
| Community services | Geocoded from public directories | 175 services across 8 categories |

All data is assembled into a single GeoPackage: `master_lsoa.gpkg` (4,994 LSOAs, 120 columns).

## Quick start

```bash
# Clone and install
git clone https://github.com/rexheng/Outreach.git
cd Outreach
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set up API key for chatbot (optional)
echo "GROQ_API_KEY=your-key-here" > .env

# Run
uvicorn app.main:app --reload
# Open http://localhost:8000
```

## Tech stack

- **Backend:** FastAPI, geopandas, pyogrio
- **Frontend:** Vanilla JS, Leaflet, Chart.js
- **LLM:** Groq (OpenAI-compatible API, SSE streaming)
- **Data:** Single GeoPackage file (no database)
- **Deployment:** Railway

## Production readiness

Use this checklist before deploying:

- Confirm `.env` is present in the deploy environment with `GROQ_API_KEY` set
- Keep `master_lsoa.gpkg` available at repo root (required by `app/config.py`)
- Run `uvicorn app.main:app --host 0.0.0.0 --port 8000` locally before shipping
- Run tests (`pytest`) and verify no regressions
- Ensure local artifacts are not included in commits (screenshots, temporary folders, ad-hoc exports)
- Deploy via `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

Recommended env vars:

- `GROQ_API_KEY`: API key for chat and policy generation features
- `PORT`: injected by hosting platform (defaults to `8000` locally)

## Portfolio README blurb

Use this in your profile README or project portfolio:

> **Outreach -- The Geography of Wellbeing** is a geospatial policy intelligence tool that maps mental health need across all 4,994 London neighbourhoods. It combines IMD deprivation, SAMHI mental-health indicators, Census health/disability measures, and community service access into a single interactive dashboard with AI-assisted policy briefing support. Built with FastAPI, GeoPandas, Leaflet, and a production deployment on Railway.

Project links:

- Live app: https://london-mental-health-atlas-production.up.railway.app/
- Repository: https://github.com/rexheng/Outreach

## Project structure

```
app/
  main.py              # FastAPI entry point
  config.py            # Settings, display columns, API keys
  api/routes.py        # Data API (/api/geojson, /api/boroughs, /api/lsoa/{code})
  api/chat.py          # LLM chat endpoint (POST /api/chat, SSE)
  api/policy_agent.py  # Policy recommendation engine
  data/loader.py       # GPKG loading, CNI computation, GeoJSON cache
  data/risk_model.py   # Composite Need Index model
  data/chat_context.py # Entity detection, intent classification
  static/              # HTML, CSS, JS frontend
master_lsoa.gpkg       # All data (4,994 LSOAs, 120 columns)
```

See `Project_Overview.md` for the full data dictionary and column reference.

## Composite Need Index (CNI)

Two-pillar weighted model scored 0-10:

| Pillar | Weight | Indicators |
|--------|--------|------------|
| Socioeconomic | 50% | Health deprivation (30%), Income (25%), Employment (20%), Housing barriers (15%), Crime (10%) |
| Demographic | 50% | Long-term sick rate (45%), Economic inactivity (30%), Unemployment (25%) |

Risk tiers: **Critical** (8-10), **High** (6-8), **Moderate** (3-6), **Low** (0-3).

## Licence
Data sources are Crown Copyright (ONS, MHCLG) and University of Bristol (SAMHI), used under open government licence.

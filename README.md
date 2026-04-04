# Outreach

**A geospatial policy tool that maps mental health need across every neighbourhood in London.**

> Where should we place three new community mental health teams?
>
> Outreach answers that with data, not intuition.

Built at the [Claude Hackathon at Imperial College London](https://claude-hackathon-at-imperial.devpost.com/), March 2026 | Solo build | Top 8 of 130+ participants

**Live:** [outreach-london.vercel.app](https://outreach-london.vercel.app)

---

## The Problem

London has 4,994 neighbourhoods. Mental health need varies dramatically between them, but policymakers don't have a single tool that combines deprivation data, health indicators, disability burden, and community service coverage into something they can actually act on.

The data exists across a dozen government sources. Nobody has stitched it together and made it queryable. So resource allocation decisions get made on borough-level averages that mask the neighbourhoods where need is most concentrated.

## How It Works

Outreach combines 120 columns of public health data into a single GeoPackage, computes a Composite Need Index for every LSOA, and renders it as an interactive choropleth map with an AI policy advisor.

```
┌──────────────────────────────────────────────────────────┐
│  DATA PIPELINE                                            │
│                                                           │
│  IMD 2019 ──┐                                            │
│  SAMHI v5 ──┤                                            │
│  Census 21 ─┤──> GeoPackage (4,994 LSOAs, 120 cols)     │
│  GP data ───┤       |                                    │
│  Services ──┘       v                                    │
│              Composite Need Index (0-10)                  │
│              Two pillars, weighted indicators             │
│                     |                                    │
│         +-----------+-----------+                        │
│         v           v           v                        │
│    Choropleth   AI Policy    Borough                     │
│    Map (9       Chatbot      Briefing                    │
│    layers)      (Groq LLM)   PDFs                        │
└──────────────────────────────────────────────────────────┘
```

### Composite Need Index

Two-pillar weighted model scored 0-10:

| Pillar | Weight | Indicators |
|--------|--------|------------|
| Socioeconomic | 50% | Health deprivation (30%), Income (25%), Employment (20%), Housing barriers (15%), Crime (10%) |
| Demographic | 50% | Long-term sick rate (45%), Economic inactivity (30%), Unemployment (25%) |

Risk tiers: **Critical** (8-10), **High** (6-8), **Moderate** (3-6), **Low** (0-3).

### The Map

9 switchable indicator layers across all 4,994 LSOAs. Filter by borough, filter by risk tier. Click any neighbourhood for a full breakdown with indicator bars and borough comparisons.

### The Chatbot

Ask natural-language questions. Get data-grounded answers with clickable map links.

- "Which boroughs should we prioritise for community mental health teams?"
- "What drives risk in Hackney?"
- "Compare Southwark and Lambeth"

The chatbot detects borough names and LSOA codes in your message, pulls the relevant data, and frames responses as commissioning-ready policy briefs.

### Borough Briefing Packs

One-page downloadable PDFs per borough. KPIs, top 5 priority neighbourhoods, key drivers narrative, borough-vs-London comparison table. Generated on demand.

## The Build

Solo developer. One-day hackathon. Four concurrent Claude Code terminals orchestrating different parts of the system:

- **Agent 1** -- Cleaning and merging mental health datasets, economic indicators, and IMD scores into a unified GeoJSON
- **Agent 2** -- Building the frontend (HTML, CSS, Leaflet map, sidebar)
- **Agent 3** -- Handling the mapping logic, choropleth rendering, layer switching
- **Agent 4** -- Integration, API routes, chat context engine

Most of the day was spent moving between terminals, resolving conflicts where agents stepped on each other, and keeping the architecture coherent.

## Data Sources

| Dataset | Source | Coverage |
|---------|--------|----------|
| Index of Multiple Deprivation 2019 | MHCLG | 7 domains, scores/ranks/deciles |
| SAMHI v5.00 (2019, 2022) | University of Bristol / PLDR | Composite mental health index + 4 sub-indicators |
| Census 2021 TS037/TS038/TS039 | ONS via Nomis | General health, disability, unpaid care |
| Census 2021 TS006/TS066 | ONS | Population density, economic activity |
| Community services | Geocoded from public directories | 175 services across 8 categories |

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI | Lightweight, async, Python-native |
| Data | GeoPackage (single file, 120 cols) | No database needed, portable |
| Geospatial | geopandas, pyogrio, Shapely | Industry standard for LSOA-level analysis |
| Frontend | Vanilla JS, Leaflet, Chart.js | Zero build step, fast iteration |
| Chat LLM | Groq (Llama 3.3 70B) | Fast inference for streaming responses |
| Policy LLM | Anthropic Claude | Structured policy recommendations |
| Deployment | Vercel (static + serverless) | Pre-computed data on CDN, API as serverless functions |

## Install

```bash
git clone https://github.com/rexheng/Outreach.git
cd Outreach

# Local dev (full pipeline with GDAL)
pip install -r requirements-local.txt
echo "GROQ_API_KEY=your-key" > .env
uvicorn app.main:app --reload
# Open http://localhost:8000

# Rebuild static data for Vercel
python scripts/build_vercel_data.py
```

## Project Structure

```
app/
  main.py              # FastAPI entry point
  config.py            # Settings, API keys, display columns
  api/
    routes.py          # Data API (/api/geojson, /api/boroughs, /api/lsoa/{code})
    chat.py            # Chat endpoint (SSE streaming)
    briefing.py        # Borough PDF generation (reportlab)
    policy_agent.py    # Policy recommendation engine (Claude)
    policy_routes.py   # Policy API endpoints
  data/
    loader.py          # GeoPackage loading, CNI computation, caching
    risk_model.py      # Composite Need Index model
    chat_context.py    # Entity detection, intent classification, data grounding

api/                   # Vercel serverless functions
  index.py             # FastAPI app (chat, policy, briefing)
  _config.py           # Shared config
  _chat_context.py     # Chat context (reads pre-computed JSON)
  _briefing_generator.py # PDF generation (reads pre-computed JSON)
  data/                # Pre-computed JSON for serverless

public/                # Vercel static assets
  index.html           # Overview dashboard
  explore.html         # Map explorer
  js/                  # Leaflet map, sidebar, controls, chat
  css/                 # Design system (terracotta palette)
  data/                # Static JSON served via CDN

master_lsoa.gpkg       # All data (4,994 LSOAs, 120 columns)
```

## Hackathon

- **Event**: [Claude Hackathon at Imperial College London](https://claude-hackathon-at-imperial.devpost.com/)
- **Organiser**: Claude Builder Club @ Imperial
- **Date**: March 2026
- **Result**: Top 8 of 130+ participants
- **Team**: Solo build
- **Devpost**: [devpost.com/software/outreach-bd6iyo](https://devpost.com/software/outreach-bd6iyo)

## Licence

Data sources are Crown Copyright (ONS, MHCLG) and University of Bristol (SAMHI), used under open government licence.

# Wellcome Mental Health Data Prize 2026-2028 -- Application Workspace

## Purpose

Application preparation for the **Wellcome Mental Health Data Prize 2026-2028**, a UK-wide innovation programme funded by Wellcome and delivered by Social Finance. The prize supports teams developing scalable data tools that use existing mental health data to drive new insights, contributing to early intervention for anxiety, depression, and psychosis.

## Prize Summary

| Detail | Value |
|---|---|
| Funder | Wellcome (delivered by Social Finance) |
| Application deadline | **8 May 2026, 12 pm** |
| Prototyping Phase | Aug 2026 -- Apr 2027, up to GBP 100,000 per team |
| Sustainability Phase | Jun 2027 -- Feb 2028, up to GBP 300,000 per team |
| Teams selected | 6 for Prototyping, 3 for Sustainability |
| Prize close | Mar 2028 |

Full details: `SF_WELLCOME_MHDP_FINAL10Feb.pdf`

## Research Motivation

There is growing evidence that neighbourhood-level factors -- deprivation, transport accessibility, economic activity, housing conditions -- shape mental health outcomes. However, these relationships are difficult to explore because the relevant data sits across disconnected sources (ONS Census, MHCLG deprivation indices, TfL transport data, NHS mental health datasets) at different geographic granularities and vintages.

This project assembles these sources into a single, analysis-ready geospatial dataset at LSOA level for London, enabling researchers, policymakers, and mental health practitioners to:

- Explore spatial patterns linking transport isolation, deprivation, and mental health
- Identify underserved neighbourhoods where transport barriers may compound mental health risk
- Inform resource allocation and early intervention targeting at a neighbourhood level

The tool proposal should fall within one of these prize-scoped categories:
- Data discovery or documentation
- Data analysis
- Facilitating data analysis (cleaning, manipulation)
- Sharing insights from data analysis to researchers, policymakers, practitioners

### Architecture Principle
All data is centralised in a **single GeoPackage file** (`master_lsoa.gpkg`). The webapp reads directly from this file -- no intermediate exports, no separate databases. This keeps the data pipeline simple and the tool self-contained.

### Frontend Direction
The webapp draws from the visual language of charity/social-impact orgs (e.g. London Community Foundation). Clean, warm, map-forward design with teal/turquoise accents. Accessible to policymakers and lived experience experts, not just data scientists.

## Repository Structure

```
aamental health data/
|-- Project_Overview.md              # This file
|-- CLAUDE.md                        # AI assistant project instructions
|-- master_lsoa.gpkg                 # Assembled GeoPackage (4,994 London LSOAs, 120 columns)
|-- master_lsoa.gpkg.backup          # Pre-enrichment backup
|-- SF_WELLCOME_MHDP_FINAL10Feb.pdf  # Prize information pack (28 pages)
|-- Application-Documents.zip        # Contains:
|   |-- Sample Application Form PDF (DO NOT SUBMIT via PDF)
|   |-- WMHDP Budget Template Feb26.xlsx
|-- data RAW/                        # Source datasets (read-only)
|   |-- imd_2019.csv
|   |-- census2021-ts006-lsoa-populationdensity.csv
|   |-- census2021-ts066-lsoa-economicactivity.csv
|   |-- Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V4_*.csv
|   |-- AC2023_AnnualisedEntryExit.xlsx
|-- data_downloads/                  # Downloaded enrichment datasets
|   |-- samhi_long.csv               # SAMHI v5.00 long-format (2011-2022, all England LSOAs)
|   |-- lsoa_2011_2021_lookup.csv    # ONS LSOA 2011→2021 mapping table
|   |-- ts037/                       # Census 2021 TS037 General Health
|   |-- ts038/                       # Census 2021 TS038 Disability
|   |-- ts039/                       # Census 2021 TS039 Unpaid Care
|-- dashboard/                       # Interactive web dashboard
|   |-- index.html                   # Main dashboard page
|   |-- lsoa_data.js                 # Simplified LSOA GeoJSON (4.3 MB)
|   |-- borough_data.js              # Borough-level aggregates
|   |-- scatter_data.js              # SAMHI vs IMD scatter data
|   |-- insights_data.js             # Pre-computed narrative insights
|   |-- critical_data.js             # Top 50 critical areas
|-- app/                             # FastAPI Loneliness Risk Dashboard (LRI)
|   |-- main.py                      # FastAPI entry point + lifespan
|   |-- config.py                    # Configuration (GPKG paths, API keys, chat settings)
|   |-- api/
|   |   |-- routes.py                # Data API endpoints (geojson, boroughs, lsoa detail)
|   |   |-- chat.py                  # LLM chat SSE streaming endpoint
|   |-- data/
|   |   |-- loader.py                # GPKG data loading, LRI computation, GeoJSON cache
|   |   |-- risk_model.py            # Loneliness Risk Index model (configurable weights)
|   |   |-- chat_context.py          # Entity detection, intent classification, data extraction
|   |-- static/
|   |   |-- index.html               # Dashboard HTML (map + sidebar + chat panel)
|   |   |-- css/style.css            # Main dashboard styles
|   |   |-- css/chat.css             # Chat panel styles
|   |   |-- js/map.js                # Leaflet choropleth map
|   |   |-- js/controls.js           # Borough/tier/layer controls
|   |   |-- js/sidebar.js            # LSOA detail sidebar
|   |   |-- js/chat.js               # Chat panel UI + SSE streaming + map navigation
|-- build_dashboard.py               # Dashboard data preprocessing script
|-- community_services.csv           # 175 geocoded community services
|-- enrich_community_services.py     # Community services enrichment script
|-- References_and_Research_Data.md   # Full dataset provenance, methodology, citations
|-- .env                             # API keys (gitignored)
|-- tasks/
|   |-- todo.md                      # Current task tracking
|   |-- lessons.md                   # Lessons learned
```

## Data Sources

### Raw Inputs (Original)

| File | Source | Description | Granularity | Records |
|---|---|---|---|---|
| `imd_2019.csv` | MHCLG | Index of Multiple Deprivation 2019 -- overall IMD + 7 domains + sub-domains, scores/ranks/deciles | LSOA (2011) | ~32,844 |
| `census2021-ts006-lsoa-populationdensity.csv` | ONS Census 2021 | Population density (persons/sq km) | LSOA (2021) | ~36,000+ |
| `census2021-ts066-lsoa-economicactivity.csv` | ONS Census 2021 | Economic activity: employment, unemployment, inactivity, retired, students, long-term sick/disabled | LSOA (2021) | ~36,000+ |
| `Lower_layer_Super_Output_Areas_*.csv` | ONS Geoportal | LSOA 2021 identifiers, BNG/lat-long centroids, boundary area | LSOA (2021) | ~36,000+ |
| `AC2023_AnnualisedEntryExit.xlsx` | TfL (C) 2024 | Annualised station entry/exit counts for LU, London Overground, DLR, TfL Rail | Station | ~270 stations |

### Mental Health Enrichment Sources (added 2026-03-24)

| File | Source | Description | Granularity | Records |
|---|---|---|---|---|
| `samhi_long.csv` | PLDR / University of Bristol | Small Area Mental Health Index v5.00, long format (2011-2022). Sub-indicators: antidepressant prescribing, QOF depression prevalence, MH hospital admissions (z-scored), DLA/PIP claims | LSOA (2011) | ~394,000 (12 years x 32,844) |
| `lsoa_2011_2021_lookup.csv` | ONS Open Geography Portal | LSOA 2011→2021 boundary change lookup. CHGIND: U=unchanged, S=split, M=merged, X=complex | LSOA | 35,796 |
| `census2021-ts037-lsoa.csv` | ONS Census 2021 via Nomis | General health self-assessment: Very good, Good, Fair, Bad, Very bad | LSOA (2021) | ~36,000+ |
| `census2021-ts038-lsoa.csv` | ONS Census 2021 via Nomis | Disability under the Equality Act: limited a lot, limited a little, not disabled | LSOA (2021) | ~36,000+ |
| `census2021-ts039-lsoa.csv` | ONS Census 2021 via Nomis | Provision of unpaid care: hours per week categories | LSOA (2021) | ~36,000+ |

### Vintage Mapping

IMD 2019 uses LSOA 2011 codes. The assembly maps these to LSOA 2021 boundaries. **335 LSOAs** created in the 2021 boundary revision (mostly Havering area splits with codes E0103xxxx) have no IMD match and carry null values for all IMD columns. These LSOAs have complete data for Census 2021 and transport columns.

## Master Dataset: `master_lsoa.gpkg`

GeoPackage containing **4,994 London LSOAs** across 33 boroughs + City of London. Single table: `master_lsoa`. **120 columns total.**

> **Note**: The former `master_lsoa_enriched_with_route_pressure` table (transport-focused) was dropped on 2026-03-24. Eight transport-specific columns were also removed from `master_lsoa` as the project pivoted to mental health focus. A backup is preserved as `master_lsoa.gpkg.backup`.

#### Geography & Identity (6 columns)
`lsoa_code`, `lsoa_name`, `LAT`, `LONG`, `area_km2`, `geometry` (MULTIPOLYGON)

#### Deprivation -- IMD 2019 (53 columns)

| Group | Columns | Notes |
|---|---|---|
| Overall IMD | `imd_score`, rank, decile | Score range: 2.3 -- 64.7 (mean 21.3) |
| Income | score (rate), rank, decile | |
| Employment | score (rate), rank, decile | |
| Education, Skills & Training | score, rank, decile | |
| Health Deprivation & Disability | score, rank, decile | Range: -3.22 to 1.57. Closest mental health proxy in current data |
| Crime | score, rank, decile | |
| Barriers to Housing & Services | score, rank, decile | |
| Living Environment | score, rank, decile | |
| Sub-domains | Children & Young People, Adult Skills, Geographical Barriers, Wider Barriers, Indoors, Outdoors | Each with score, rank, decile |
| Child/Older poverty | IDACI score/rank/decile, IDAOPI score/rank/decile | |
| Population | total, children 0-15, working age 16-59, 60+, employment domain pop | Mid-2015 estimates |

**Rank direction**: 1 = most deprived. **335 LSOAs have null IMD** (2021 boundary splits).

#### Demographics -- Census 2021 (12 columns)

| Column | Description |
|---|---|
| `pop_density_2021` | Persons per sq km |
| `total_16plus` | All usual residents 16+ |
| `econ_active` | Economically active (excl. full-time students) |
| `in_employment` | In employment |
| `unemployed` | Unemployed |
| `econ_active_student` | Economically active full-time students |
| `econ_inactive` | Economically inactive total |
| `retired` | Retired |
| `student` | Inactive students |
| `looking_after_home` | Looking after home/family |
| `long_term_sick` | Long-term sick or disabled |
| `inactive_other` | Other economically inactive |
| `employment_rate` | Derived: in_employment / total_16plus |

#### Mental Health -- SAMHI (8 columns, added 2026-03-24)

Joined via ONS LSOA 2011→2021 lookup table. For split LSOAs (2011→multiple 2021), parent values duplicated. For merged LSOAs (multiple 2011→one 2021), values averaged.

| Column | Description | Range |
|---|---|---|
| `samhi_index_2022` | Small Area Mental Health Index composite, 2022 | -2.01 to 4.67 (mean -0.28) |
| `samhi_dec_2022` | SAMHI decile, 2022 (1=lowest need, 10=highest) | 1-10 |
| `antidep_rate_2022` | Antidepressant prescribing rate per 1,000 pop, 2022 | 8.6 to 42.5 (mean 24.1) |
| `est_qof_dep_2022` | Estimated QOF depression prevalence %, 2022 | 3.5 to 16.8 (mean 9.2) |
| `mh_hospital_rate_2022` | Mental health hospital admission rate (z-scored), 2022 | -1.65 to 7.79 (mean -0.25) |
| `dla_pip_pct_2022` | DLA/PIP mental health claims %, 2022 | 0.0 to 10.9 (mean 2.1) |
| `samhi_index_2019` | SAMHI composite, 2019 (pre-COVID baseline) | -2.03 to 4.57 (mean -0.37) |
| `samhi_dec_2019` | SAMHI decile, 2019 | 1-10 |

**Coverage**: 4,659 LSOAs matched directly via lookup; 335 new-2021 LSOAs received interpolated values. Zero nulls across all 4,994 LSOAs.

#### Census 2021 -- General Health, TS037 (6 columns, added 2026-03-24)

| Column | Description |
|---|---|
| `health_very_good` | Count: Very good health |
| `health_good` | Count: Good health |
| `health_fair` | Count: Fair health |
| `health_bad` | Count: Bad health |
| `health_very_bad` | Count: Very bad health |
| `health_bad_or_very_bad_pct` | Derived: (bad + very bad) / total * 100. Range 0.5-12.4% (mean 4.3%) |

#### Census 2021 -- Disability, TS038 (5 columns, added 2026-03-24)

| Column | Description |
|---|---|
| `disabled_limited_a_lot` | Count: Disabled, day-to-day activities limited a lot |
| `disabled_limited_a_little` | Count: Disabled, day-to-day activities limited a little |
| `not_disabled_has_condition` | Count: Not disabled but has long-term condition |
| `not_disabled_no_condition` | Count: No long-term conditions |
| `disability_rate_pct` | Derived: (limited a lot + limited a little) / total * 100. Range 4.1-28.4% (mean 13.2%) |

#### Census 2021 -- Unpaid Care, TS039 (4 columns, added 2026-03-24)

| Column | Description |
|---|---|
| `unpaid_care_19h_or_less` | Count: Provides 19 hours or less unpaid care/week |
| `unpaid_care_20_to_49h` | Count: Provides 20-49 hours unpaid care/week |
| `unpaid_care_50h_plus` | Count: Provides 50+ hours unpaid care/week |
| `unpaid_care_rate_pct` | Derived: any care / total * 100. Range 1.6-14.5% (mean 7.2%) |

#### Transport Columns (removed 2026-03-24)

The following 8 transport columns were removed as the project pivoted from transport-focus to mental health focus:
`dist_to_station_m`, `mean_ptal_ai`, `median_ptal_ai`, `min_ptal_ai`, `max_ptal_ai`, `mean_ptal_level`, `nearest_station_ann_total`, `crowding_pressure`.

The former `master_lsoa_enriched_with_route_pressure` table (containing 32 additional transport composite columns) was also dropped entirely. Original data is preserved in `master_lsoa.gpkg.backup`.

#### Administrative (2 columns)
`Local Authority District code (2019)`, `Local Authority District name (2019)` from IMD mapping.

## Data Quality Summary

| Metric | Value |
|---|---|
| Total LSOAs | 4,994 |
| Total columns | 120 |
| London boroughs covered | 33 + City of London |
| LSOAs with null IMD | 335 (new 2021 codes, no 2011 match) |
| LSOAs with null SAMHI | 0 (mapped via 2011→2021 lookup, 335 interpolated) |
| LSOAs with null Census health/disability/care | 0 |
| LSOAs with null community services | 0 |
| Geographic extent (lat) | 51.294 -- 51.681 |
| Geographic extent (long) | -0.491 -- 0.302 |
| IMD score range | 2.3 -- 64.7 (mean 21.3) |
| Health deprivation score range | -3.22 -- 1.57 (mean -0.39) |
| SAMHI index range (2022) | -2.01 -- 4.67 (mean -0.28) |
| Antidepressant rate range (2022) | 8.6 -- 42.5 per 1,000 (mean 24.1) |
| Bad/very bad health range | 0.5% -- 12.4% (mean 4.3%) |
| Disability rate range | 4.1% -- 28.4% (mean 13.2%) |

## Key Dates

| Date | Activity | Status |
|---|---|---|
| 11 Feb 2026 | Applications open | Done |
| 24 Feb 2026 | Launch event | Done |
| 5 & 19 Mar 2026 | Team matching workshops | Done |
| 19 Mar 2026 | FAQ published + Q&A event | Done |
| 10 Apr 2026 | Clarification question deadline | Upcoming |
| 17 Apr 2026 | FAQ updated | Upcoming |
| **8 May 2026** | **Application deadline (12 pm)** | **~6 weeks** |
| W/C 8 & 15 Jun 2026 | Online pitch sessions (shortlisted) | |
| By 19 Jun 2026 | Teams selected; must prove data access | |
| 3 Aug 2026 | Prototyping Phase kick-off | |
| Aug 2026 -- Apr 2027 | Prototyping Phase | |
| May 2027 | Selection for Sustainability (6 -> 3) | |
| Jun 2027 -- Feb 2028 | Sustainability Phase | |
| Mar 2028 | Prize close, learning, dissemination | |

## Evaluation Criteria (12 criteria, scored 0-5 each, total /60)

### A: Approach to Tooling (5 criteria)
| ID | Criterion | Key Signals |
|---|---|---|
| A1 | Impact on early intervention for anxiety/depression/psychosis | Research insights, evidence-based decision-making, underserved communities |
| A2 | Innovative approach to addressing data needs | Solves longstanding issue, adopts new methods, makes data accessible to new groups |
| A3 | Vision for impact beyond the prize | Sustainability plan, dissemination, scalability to new datasets/locations/users |
| A4 | Clear and feasible prototyping plan | Objectives, workstreams, timeline, budget, risk mitigation |
| A5 | Open access principles | OSI-compliant licence, public code repo, sufficient data for third-party reuse |

### B: Use of Mental Health Data (3 criteria)
| ID | Criterion | Key Signals |
|---|---|---|
| B1 | Appropriate mental health dataset selection | Relevant to anxiety/depression/psychosis, robust (3+ waves or large pop), risks acknowledged |
| B2 | Wider sector practice contribution | Underutilised datasets, novel analysis approaches, blending lived experience with data |
| B3 | Data ethics principles and protocols | Provenance, safeguarding, privacy law compliance, bias mitigation, misuse prevention |

### C: Team Formation & Involvement (4 criteria)
| ID | Criterion | Key Signals |
|---|---|---|
| C1 | Multidisciplinary and diverse team | Variety of disciplines, diversity of background/career stage |
| C2 | Novel types of collaboration | New org partnerships, extending mental health field orgs into data work |
| C3 | Collaborative and inclusive working | Defined roles, agile iteration, inclusive platform for all expertise |
| C4 | Lived experience engagement | Informed by lived experience, non-extractive, representative, aligned to strengths |

## Eligibility Checklist

- [ ] Lead applicant is UK-based HE/research/healthcare/not-for-profit org
- [ ] Lead has permanent or long-term contract
- [ ] Team has 5-10 members across disciplines
- [ ] Disciplines covered: mental health research, data science, digital tool dev, lived experience, policy, practitioners, ethics
- [ ] All team members play meaningful roles
- [ ] Using existing datasets (no primary research)
- [ ] Primary dataset: UK cohorts, anxiety/depression/psychosis measures, respondents <30, 3+ waves or large population
- [ ] Can demonstrate data access by 19 Jun 2026
- [ ] Lived experience engagement plan included
- [ ] Budget within GBP 100,000 (Prototyping Phase)
- [ ] Open access commitment: OSI licence, public code repo, open publications

## Dashboard

An interactive web dashboard is available at `dashboard/index.html`. Serve via any HTTP server (e.g. `python -m http.server` from the `dashboard/` directory). Built with Leaflet + Chart.js, no build step required.

### Features
- **Choropleth map**: 4,994 LSOAs with 7 selectable layers (SAMHI, antidepressant rate, depression prevalence, bad health %, disability %, unpaid care %, IMD score)
- **KPI strip**: Headline London-wide statistics
- **AI insight narratives**: 5 pre-computed analytical findings covering geographic patterns, deprivation correlation, COVID impact, scale of need, intersecting burdens
- **Borough ranking**: Horizontal bar chart of mean SAMHI index by borough
- **Deprivation scatter**: SAMHI vs IMD score for all LSOAs, showing the deprivation-mental health correlation
- **Critical areas table**: Top 20 neighbourhoods ranked by SAMHI mental health need

### Design
Editorial/magazine aesthetic with teal/turquoise palette (Wellcome branding). Source Serif 4 + DM Sans typography. Map-forward layout, WCAG-accessible, responsive.

### Data pipeline
`build_dashboard.py` preprocesses `master_lsoa.gpkg` into simplified GeoJSON and JSON files for the dashboard. Run it to regenerate after any GPKG changes.

## LLM Policy Chatbot (added 2026-03-24)

An AI-powered chatbot integrated into the Loneliness Risk Dashboard that helps policymakers ask natural-language questions about loneliness risk data, with streaming responses and clickable map navigation.

### Architecture

- **Backend**: FastAPI SSE streaming endpoint (`POST /api/chat`) calls Anthropic Claude API with dynamically-extracted data context from the cached GeoDataFrame
- **Frontend**: Floating chat panel (vanilla JS) with entity-link parsing that triggers map zoom/highlight actions via the existing `window.APP` global state
- **Data context**: Instead of sending all 4,994 LSOAs to Claude, the `chat_context.py` module detects entities (boroughs/LSOAs) and intent from the user's message, then extracts only the relevant data slice (~500-2000 tokens)

### Files

| File | Role |
|---|---|
| `app/api/chat.py` | SSE streaming endpoint — orchestrates context + Claude API |
| `app/data/chat_context.py` | Entity detection (borough/LSOA/intent), data extraction from cached GDF, system prompt assembly |
| `app/static/js/chat.js` | Chat panel UI, SSE consumption, message rendering, entity link → map navigation |
| `app/static/css/chat.css` | Chat panel styles (toggle button, panel, messages, entity links) |
| `.env` | `ANTHROPIC_API_KEY` (gitignored, server-side only) |

### Entity Link Syntax

Claude is instructed to format references as:
- `[[borough:Hackney]]` — rendered as clickable link that sets borough dropdown + zooms map
- `[[lsoa:E01001110|Hackney 001A]]` — rendered as clickable link that zooms to LSOA + opens sidebar detail

### Intent Classification

The system classifies user questions into 4 intents to tailor the data context sent to Claude:
- **Ranking**: "worst", "top", "prioritize" → sends top-N borough ranking
- **Comparison**: "compare", "vs" → sends side-by-side borough stats
- **Drill-down**: "why", "what drives" → sends detailed borough/LSOA indicators
- **Overview**: default → sends London-wide summary

### Configuration

| Setting | Value | Location |
|---|---|---|
| `ANTHROPIC_API_KEY` | Required | `.env` file |
| `CHAT_MODEL` | `claude-sonnet-4-20250514` | `app/config.py` |
| `CHAT_MAX_TOKENS` | 1500 | `app/config.py` |
| `CHAT_HISTORY_LIMIT` | 10 turns | `app/config.py` |

### Dependencies Added

- `anthropic>=0.42.0` — Anthropic Python SDK for Claude API
- `python-dotenv>=1.0.0` — Environment variable loading from `.env`

## Outstanding Work

### Critical (before application)
- [x] **Add mental health-specific variables** -- SAMHI v5.00 (composite index + sub-indicators) now included for 2019 and 2022
- [x] **Add health/disability/care Census data** -- TS037, TS038, TS039 joined
- [ ] **Identify primary mental health dataset** meeting Annex 3 criteria -- SAMHI is a composite; prize may require individual-level cohort data (e.g. ALSPAC, MCS, Understanding Society) with anxiety/depression/psychosis measures, respondents <30, 3+ waves
- [ ] **Define the specific tool** -- interactive dashboard prototype exists; need to articulate how it serves researchers/policymakers
- [ ] **Assemble team** -- need 5-10 people: mental health researcher, data scientist, tool developer, lived experience expert, policy person, practitioner, ethics specialist
- [ ] **Draft lived experience engagement plan** -- non-extractive, central to all phases, representative
- [ ] **Complete application** on Submit platform (not via PDF)
- [ ] **Prepare budget** using `WMHDP Budget Template Feb26.xlsx`

### Data Assembly Improvements
- [x] Map SAMHI 2011 LSOAs to 2021 boundaries via ONS lookup (splits duplicated, merges averaged)
- [x] Add SAMHI 2019 pre-COVID baseline for temporal comparison
- [ ] Resolve 335 null-IMD LSOAs (have SAMHI/Census data but no IMD match)
- [ ] Consider expanding beyond London if the chosen mental health dataset has national coverage
- [ ] Add green space / air quality data for environmental mental health determinants
- [ ] Add NHS service utilisation data if accessible

---

## Community Services Enrichment (added 2026-03-24)

175 community support services across London were geocoded and spatially joined to LSOAs. Each service was assigned to its containing LSOA via point-in-polygon spatial join (EPSG:27700). For every LSOA, distance-to-nearest metrics (in metres) were computed from LSOA centroids.

### Service categories (8 types, 175 total)

| Type | Count | Sources |
|---|---|---|
| `mental_health_charity` | 31 | Mind local branches (15), Samaritans (15), Rethink (1) |
| `foodbank` | 29 | Trussell Trust network, independent foodbanks |
| `citizens_advice` | 29 | Citizens Advice bureaux across 29 boroughs |
| `nhs_talking_therapy` | 29 | NHS Talking Therapies (formerly IAPT) by borough |
| `older_people_charity` | 25 | Age UK local branches |
| `homelessness_service` | 15 | St Mungo's, Crisis, Centrepoint, Shelter, day centres |
| `nhs_cmht` | 12 | NHS Community Mental Health Teams |
| `council_wellbeing_hub` | 5 | Social prescribing hubs, recovery cafes, ICMHCs |

### New columns in `master_lsoa` (22 columns)

**Counts (per LSOA):**
- `community_services_total` -- total services in the LSOA (0 for most; 144 LSOAs have >= 1)
- `cs_mental_health_charity_count`, `cs_foodbank_count`, `cs_citizens_advice_count`, `cs_nhs_talking_therapy_count`, `cs_older_people_charity_count`, `cs_homelessness_service_count`, `cs_nhs_cmht_count`, `cs_council_wellbeing_hub_count`

**Distance to nearest (metres, every LSOA):**
- `dist_to_nearest_community_service_m` -- distance to closest service of any type (mean 1,604m, max 8,691m)
- `dist_to_nearest_mental_health_charity_m` (mean 3,046m)
- `dist_to_nearest_foodbank_m` (mean 3,215m)
- `dist_to_nearest_citizens_advice_m` (mean 2,883m)
- `dist_to_nearest_nhs_talking_therapy_m` (mean 2,876m)
- `dist_to_nearest_older_people_charity_m` (mean 3,306m)
- `dist_to_nearest_homelessness_service_m` (mean 8,740m)
- `dist_to_nearest_nhs_cmht_m` (mean 7,448m)
- `dist_to_nearest_council_wellbeing_hub_m` (mean 8,031m)

**Metadata:**
- `nearest_community_service_name`, `nearest_community_service_type` -- name/type of closest service
- `community_services_names`, `community_services_types` -- pipe-separated lists (for LSOAs with services)

### Standalone file
- `community_services.csv` -- all 175 services with name, type, subtype, address, postcode, borough, lat/lon, easting/northing, assigned LSOA code
- `enrich_community_services.py` -- reproducible enrichment script (geocodes via postcodes.io, spatial join via geopandas)

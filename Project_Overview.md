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
|-- master_lsoa.gpkg                 # Assembled GeoPackage (4,994 London LSOAs)
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
|-- tasks/
|   |-- todo.md                      # Current task tracking
|   |-- lessons.md                   # Lessons learned
```

## Data Sources

### Raw Inputs

| File | Source | Description | Granularity | Records |
|---|---|---|---|---|
| `imd_2019.csv` | MHCLG | Index of Multiple Deprivation 2019 -- overall IMD + 7 domains + sub-domains, scores/ranks/deciles | LSOA (2011) | ~32,844 |
| `census2021-ts006-lsoa-populationdensity.csv` | ONS Census 2021 | Population density (persons/sq km) | LSOA (2021) | ~36,000+ |
| `census2021-ts066-lsoa-economicactivity.csv` | ONS Census 2021 | Economic activity: employment, unemployment, inactivity, retired, students, long-term sick/disabled | LSOA (2021) | ~36,000+ |
| `Lower_layer_Super_Output_Areas_*.csv` | ONS Geoportal | LSOA 2021 identifiers, BNG/lat-long centroids, boundary area | LSOA (2021) | ~36,000+ |
| `AC2023_AnnualisedEntryExit.xlsx` | TfL (C) 2024 | Annualised station entry/exit counts for LU, London Overground, DLR, TfL Rail | Station | ~270 stations |

### Vintage Mapping

IMD 2019 uses LSOA 2011 codes. The assembly maps these to LSOA 2021 boundaries. **335 LSOAs** created in the 2021 boundary revision (mostly Havering area splits with codes E0103xxxx) have no IMD match and carry null values for all IMD columns. These LSOAs have complete data for Census 2021 and transport columns.

## Master Dataset: `master_lsoa.gpkg`

GeoPackage containing **4,994 London LSOAs** across 33 boroughs + City of London. Two tables:

### Table: `master_lsoa`
Original assembly with source-native column names. Use for traceability back to raw files.

### Table: `master_lsoa_enriched_with_route_pressure` (preferred)
Snake_case column names. All original data plus derived transport indicators. **116 columns total.**

#### Geography & Identity (6 columns)
`lsoa_code`, `lsoa_name`, `lat`, `long`, `area_km2`, `geom` (MULTIPOLYGON)

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

#### Transport Accessibility (34 columns)

| Group | Key Columns | Description |
|---|---|---|
| Rail proximity | `dist_to_station_m` | Distance to nearest rail station (metres) |
| PTAL | `mean_ptal_ai`, `median_ptal_ai`, `min_ptal_ai`, `max_ptal_ai`, `mean_ptal_level` | Public Transport Accessibility Level (TfL) |
| Station demand | `nearest_station_ann_total` | Annual entry+exit at nearest TfL station |
| Station crowding | `crowding_pressure` | Derived station-level crowding metric |
| Bus network | `bus_stop_count`, `bus_stop_unique_count`, `bus_stop_density_per_km2`, `dist_to_nearest_bus_stop_m`, `virtual_bus_stop_share` | Bus stop coverage |
| Bus routes | `mean_stop_route_pressure`, `max_stop_route_pressure`, `latest_stop_route_pressure`, `mean_routes_served`, `max_routes_served`, `pressured_stop_count` | Route-level demand pressure |
| Locality | `locality_stop_count`, `distinct_locality_count`, `dominant_suggested_locality`, `locality_stop_density_per_km2` | Locality grouping |
| Commute patterns | `borough_pt_commute_share`, `borough_long_distance_share`, `borough_commute_obs_total`, `borough_pt_commute_obs`, `borough_non_pt_commute_obs` | Borough-level commute mode shares |
| Composites | `bus_vs_rail_gap_index`, `bus_crowding_proxy`, `rail_bus_pressure_gap`, `route_based_station_need`, `route_pressure_x_employment`, `bus_stop_per_1000_density_units`, `bus_stop_count_x_employment_rate` | Derived multi-factor indicators |

#### Administrative (2 columns)
`lower_tier_local_authorities_code`, and local authority name/code from IMD mapping.

## Data Quality Summary

| Metric | Value |
|---|---|
| Total LSOAs | 4,994 |
| London boroughs covered | 33 + City of London |
| LSOAs with null IMD | 335 (new 2021 codes, no 2011 match) |
| LSOAs with null Census data | 0 |
| LSOAs with null transport data | 0 |
| Geographic extent (lat) | 51.294 -- 51.681 |
| Geographic extent (long) | -0.491 -- 0.302 |
| IMD score range | 2.3 -- 64.7 (mean 21.3) |
| Health deprivation score range | -3.22 -- 1.57 (mean -0.39) |

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

## Outstanding Work

### Critical (before application)
- [ ] **Identify primary mental health dataset** meeting Annex 3 criteria -- this is the biggest gap. Health Deprivation & Disability from IMD is a proxy only, not a direct mental health measure.
- [ ] **Define the specific tool** -- what will researchers/policymakers interact with? Dashboard? API? Data linkage platform?
- [ ] **Assemble team** -- need 5-10 people: mental health researcher, data scientist, tool developer, lived experience expert, policy person, practitioner, ethics specialist
- [ ] **Draft lived experience engagement plan** -- non-extractive, central to all phases, representative
- [ ] **Complete application** on Submit platform (not via PDF)
- [ ] **Prepare budget** using `WMHDP Budget Template Feb26.xlsx`

### Data Assembly Improvements
- [ ] Resolve 335 null-IMD LSOAs (2021 boundary splits) -- consider LSOA 2011-to-2021 lookup tables from ONS
- [ ] Consider expanding beyond London if the chosen mental health dataset has national coverage
- [ ] Add mental health-specific variables once primary dataset is selected
- [ ] Document data assembly pipeline (currently no scripts in repo)

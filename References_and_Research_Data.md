# References and Research Data

This document provides full provenance, methodology, and citation information for every dataset used in the Outreach project. It is intended to support the Wellcome Mental Health Data Prize application (criterion B1: dataset selection, B3: data ethics) and to ensure reproducibility.

---

## Table of Contents

1. [Geographic Boundaries](#1-geographic-boundaries--lsoa-2021)
2. [Index of Multiple Deprivation](#2-index-of-multiple-deprivation-imd-2019)
3. [LSOA 2011 to 2021 Lookup](#3-lsoa-2011-to-2021-boundary-lookup)
4. [Small Area Mental Health Index](#4-small-area-mental-health-index-samhi)
5. [Census 2021: Population Density](#5-census-2021-population-density-ts006)
6. [Census 2021: Economic Activity](#6-census-2021-economic-activity-ts066)
7. [Census 2021: General Health](#7-census-2021-general-health-ts037)
8. [Census 2021: Disability](#8-census-2021-disability-ts038)
9. [Census 2021: Unpaid Care](#9-census-2021-unpaid-care-ts039)
10. [TfL Station Entry/Exit Data](#10-tfl-annualised-station-entryexit-2023)
11. [Community Support Services](#11-community-support-services)
12. [Data Assembly Procedure](#12-data-assembly-procedure)
13. [Ethical Considerations](#13-ethical-considerations)
14. [Full Reference List](#14-full-reference-list)

---

## 1. Geographic Boundaries -- LSOA 2021

| Field | Detail |
|---|---|
| **Dataset** | Lower Layer Super Output Areas (December 2021) Boundaries EW BSC V4 |
| **Publisher** | Office for National Statistics (ONS), Open Geography Portal |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 (England and Wales); 4,994 used (London) |
| **Format** | CSV with centroid coordinates (BNG easting/northing, WGS84 lat/long), shape area |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data RAW/Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V4_-4881486778565955110.csv` |

**What are LSOAs?**
Lower Layer Super Output Areas are small statistical geographies designed by the ONS for reporting Census and neighbourhood-level statistics. Each LSOA covers approximately 1,000-3,000 residents (mean ~1,700 in London). They are stable across Census years, though boundary revisions occur -- the 2021 revision introduced 335 new LSOAs not present in 2011 (primarily in Havering from boundary splits).

**Columns used**: `LSOA21CD` (code), `LSOA21NM` (name), `BNG_E`, `BNG_N`, `LAT`, `LONG`, `Shape__Area`.

**Processing**: Filtered to London (33 boroughs + City of London) using local authority lookups. Geometry converted from centroid points to MULTIPOLYGON boundaries via spatial join with ONS boundary shapefiles. CRS: EPSG:27700 (British National Grid).

**Citation**: Office for National Statistics (2022). *Lower layer Super Output Areas (December 2021) Boundaries EW BSC V4*. Open Geography Portal. Contains OS data (C) Crown copyright and database right 2022.

---

## 2. Index of Multiple Deprivation (IMD 2019)

| Field | Detail |
|---|---|
| **Dataset** | English Indices of Deprivation 2019 |
| **Publisher** | Ministry of Housing, Communities & Local Government (MHCLG), now DLUHC |
| **Geography** | England |
| **Granularity** | LSOA (2011 vintage) |
| **Records** | 32,844 LSOAs |
| **Reference year** | 2019 (using data from 2015-2017 depending on domain) |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data RAW/imd_2019.csv` |

**What is the IMD?**
The Index of Multiple Deprivation is the official measure of relative deprivation for small areas in England. It combines 39 indicators across 7 weighted domains into a single composite score. Higher scores indicate greater deprivation. The IMD is widely used in public health research, service planning, and resource allocation.

**7 Domains (with weights)**:
1. **Income** (22.5%) -- proportion of population experiencing income deprivation
2. **Employment** (22.5%) -- proportion of working-age population experiencing employment deprivation
3. **Education, Skills & Training** (13.5%) -- attainment and skills in the population
4. **Health Deprivation & Disability** (13.5%) -- risk of premature death and impairment of quality of life through poor physical or mental health
5. **Crime** (9.3%) -- risk of personal and material victimisation
6. **Barriers to Housing & Services** (9.3%) -- physical and financial accessibility
7. **Living Environment** (9.3%) -- quality of the indoor and outdoor local environment

**Sub-domains**: Children & Young People, Adult Skills, Geographical Barriers, Wider Barriers, Indoors, Outdoors.

**Supplementary indices**: IDACI (Income Deprivation Affecting Children Index), IDAOPI (Income Deprivation Affecting Older People Index).

**Columns per domain** (3 each): score, rank (1 = most deprived), decile (1 = most deprived 10%). Population estimates (mid-2015) also included.

**Processing**: Joined to LSOA 2021 boundaries via the ONS 2011-to-2021 lookup (see Section 3). For unchanged LSOAs (CHGIND = U), direct join on LSOA code. For split LSOAs (2011 code maps to multiple 2021 codes), parent 2011 values assigned to all child 2021 LSOAs. **335 LSOAs** created in 2021 with no 2011 parent have null IMD values.

**Limitations**:
- Data underlying the 2019 IMD ranges from 2015-2017 depending on domain; it does not capture post-COVID changes.
- Rank/decile values are relative (within England), not absolute measures of deprivation.
- The IMD uses 2011 LSOA boundaries; mapping to 2021 introduces approximation for split/merged areas.

**Citation**: Ministry of Housing, Communities & Local Government (2019). *English Indices of Deprivation 2019*. GOV.UK.

**Key reference**: Smith, T. et al. (2015). *The English Indices of Deprivation 2015: Technical Report*. DCLG.

---

## 3. LSOA 2011 to 2021 Boundary Lookup

| Field | Detail |
|---|---|
| **Dataset** | Lower Layer Super Output Area (2011) to Lower Layer Super Output Area (2021) to Local Authority District (2022) Lookup in England and Wales |
| **Publisher** | ONS Open Geography Portal |
| **Records** | 35,796 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data_downloads/lsoa_2011_2021_lookup.csv` |

**Purpose**: Maps LSOA 2011 codes (used by IMD 2019 and SAMHI) to LSOA 2021 codes (used by Census 2021 and our master geometry). Essential for joining pre-2021 datasets to the current boundary system.

**Key column -- CHGIND** (Change Indicator):
- **U** (Unchanged): 1-to-1 mapping. Same LSOA in both years.
- **S** (Split): One 2011 LSOA became multiple 2021 LSOAs. Data from the parent is duplicated to each child.
- **M** (Merged): Multiple 2011 LSOAs became one 2021 LSOA. Data is averaged.
- **X** (Complex): Non-trivial boundary change. Handled case-by-case.

**In London**: ~4,659 LSOAs map cleanly (U or resolvable S/M). 335 new 2021 LSOAs have no 2011 parent.

**Citation**: Office for National Statistics (2023). *LSOA (2011) to LSOA (2021) to Local Authority District (2022) Lookup in England and Wales*. Open Geography Portal.

---

## 4. Small Area Mental Health Index (SAMHI)

| Field | Detail |
|---|---|
| **Dataset** | Small Area Mental Health Index (SAMHI) v5.00 |
| **Publisher** | Place-based Longitudinal Data Resource (PLDR), University of Bristol |
| **Geography** | England |
| **Granularity** | LSOA (2011 vintage) |
| **Temporal coverage** | 2011--2022 (annual) |
| **Records** | 394,128 (32,844 LSOAs x 12 years) |
| **Format** | CSV (long format) |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data_downloads/samhi_long.csv` |

**What is SAMHI?**
The Small Area Mental Health Index is a composite annual index measuring population mental health need at LSOA level. Developed by the University of Bristol's PLDR, it combines four administrative data indicators into a single standardised score using factor analysis. Higher SAMHI = greater mental health need.

**Sub-indicators (4)**:

| Indicator | Column | Unit | Data source |
|---|---|---|---|
| Antidepressant prescribing rate | `antidep_rate` | Per 1,000 population | NHS Business Services Authority |
| Estimated QOF depression prevalence | `est_qof_dep` | Percentage | NHS Digital (QOF) |
| Mental health hospital admissions | `z_mh_rate` | Z-scored rate | Hospital Episode Statistics |
| DLA/PIP mental health claims | `dla_pip_pct` | Percentage | DWP |

**Composite construction**: The four indicators are combined via confirmatory factor analysis. The resulting index (`samhi_index`) is standardised with mean ~0 nationally. The decile column (`samhi_dec`) ranks LSOAs 1-10, where 10 = highest mental health need.

**Years included in GPKG**: 2019 (pre-COVID baseline) and 2022 (latest available).

**Processing**:
1. Filtered `samhi_long.csv` to years 2019 and 2022.
2. Pivoted from long to wide format (one row per LSOA, columns suffixed with year).
3. Joined to LSOA 2021 via the ONS lookup (Section 3):
   - **Unchanged (U)**: Direct join.
   - **Split (S)**: Parent 2011 SAMHI values duplicated to all child 2021 LSOAs.
   - **Merged (M)**: SAMHI values from multiple 2011 parents averaged.
4. For the 335 new-2021 LSOAs with no parent: interpolated from nearest geographic neighbours (same borough). **Result: zero nulls across all 4,994 LSOAs.**

**London-specific observations**:
- London's mean SAMHI (2022) is -0.28, below the England mean of ~0 (i.e. London has lower-than-average need overall, but with extreme variation).
- Range in London: -2.01 (lowest need) to 4.67 (highest need).
- Every borough's mean SAMHI worsened between 2019 and 2022 (COVID impact).
- Outer London boroughs often have higher antidepressant prescribing rates than inner London, despite inner London having higher hospital admission rates -- suggesting different patterns of service engagement.

**Limitations**:
- SAMHI is an ecological (area-level) composite, not an individual prevalence measure.
- It captures service utilisation and benefit claims, which may undercount need in populations with lower service access.
- The 2011 LSOA vintage introduces approximation when mapped to 2021 boundaries.
- The index does not distinguish between anxiety, depression, and psychosis -- it captures general "mental health need."

**Citation**: Daras, K., Barr, B., Rose, T., Wickham, S., Taylor-Robinson, D., & Whitehead, M. (2023). *Small Area Mental Health Index (SAMHI) v5.00*. Place-based Longitudinal Data Resource (PLDR), University of Bristol.

**Key reference**: Daras, K. et al. (2023). "The Small Area Mental Health Index: A new measure of mental health need at the neighbourhood level." *Social Psychiatry and Psychiatric Epidemiology*.

---

## 5. Census 2021: Population Density (TS006)

| Field | Detail |
|---|---|
| **Dataset** | Census 2021: Population Density (TS006) |
| **Publisher** | ONS via Nomis |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 |
| **Reference date** | 21 March 2021 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data RAW/census2021-ts006-lsoa-populationdensity.csv` |

**Content**: Persons per square kilometre for each LSOA, calculated from usual resident population divided by land area.

**Column used**: `Population Density: Persons per square kilometre; measures: Value` -> mapped to `pop_density_2021`.

**Processing**: Direct join on LSOA 2021 code. No vintage mismatch. London LSOAs range from ~500 to ~40,000+ persons/sq km.

**Citation**: Office for National Statistics (2023). *Census 2021: Population density (TS006), LSOA level*. Nomis.

---

## 6. Census 2021: Economic Activity (TS066)

| Field | Detail |
|---|---|
| **Dataset** | Census 2021: Economic Activity Status (TS066) |
| **Publisher** | ONS via Nomis |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 |
| **Reference date** | 21 March 2021 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data RAW/census2021-ts066-lsoa-economicactivity.csv` |

**Content**: Detailed breakdown of economic activity status for usual residents aged 16+. Includes employment (full/part-time, self-employed), unemployment, student status, economic inactivity (retired, caring, long-term sick, other).

**Columns extracted**:
- `total_16plus` -- all residents 16+
- `econ_active` -- economically active (excl. full-time students)
- `in_employment` -- in employment (any type)
- `unemployed` -- unemployed
- `econ_active_student` -- economically active full-time students
- `econ_inactive` -- economically inactive total
- `retired`, `student`, `looking_after_home`, `long_term_sick`, `inactive_other`
- `employment_rate` -- derived: `in_employment / total_16plus`

**Mental health relevance**: The `long_term_sick` count captures residents economically inactive due to long-term sickness or disability -- a key correlate of mental health conditions. Economic inactivity and unemployment are established risk factors for poor mental health.

**Processing**: Direct join on LSOA 2021 code. Derived `employment_rate` calculated post-join.

**Citation**: Office for National Statistics (2023). *Census 2021: Economic activity status (TS066), LSOA level*. Nomis.

---

## 7. Census 2021: General Health (TS037)

| Field | Detail |
|---|---|
| **Dataset** | Census 2021: General Health (TS037) |
| **Publisher** | ONS via Nomis |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 |
| **Reference date** | 21 March 2021 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data_downloads/ts037/census2021-ts037-lsoa.csv` |

**Content**: Self-assessed general health for all usual residents. Five categories: Very good, Good, Fair, Bad, Very bad.

**Columns extracted**:
- `health_very_good`, `health_good`, `health_fair`, `health_bad`, `health_very_bad` (counts)
- `health_bad_or_very_bad_pct` -- derived: `(bad + very_bad) / total * 100`

**Mental health relevance**: Self-assessed health is a validated predictor of mental health status. "Bad" or "Very bad" health correlates strongly with depression, anxiety, and disability. In London, the bad/very bad health rate ranges from 0.5% to 12.4% (mean 4.3%).

**Processing**: Direct join on LSOA 2021 code. Percentage derived post-join.

**Citation**: Office for National Statistics (2023). *Census 2021: General health (TS037), LSOA level*. Nomis.

---

## 8. Census 2021: Disability (TS038)

| Field | Detail |
|---|---|
| **Dataset** | Census 2021: Disability (TS038) |
| **Publisher** | ONS via Nomis |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 |
| **Reference date** | 21 March 2021 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data_downloads/ts038/census2021-ts038-lsoa.csv` |

**Content**: Disability status under the Equality Act 2010 for all usual residents. Categories: Disabled (day-to-day activities limited a lot), Disabled (limited a little), Not disabled (has long-term condition), Not disabled (no condition).

**Columns extracted**:
- `disabled_limited_a_lot`, `disabled_limited_a_little`, `not_disabled_has_condition`, `not_disabled_no_condition` (counts)
- `disability_rate_pct` -- derived: `(limited_a_lot + limited_a_little) / total * 100`

**Mental health relevance**: Mental health conditions are a leading cause of disability. The disability rate captures both physical and mental health-related limitations and is a key indicator of the overall health burden on a neighbourhood. London range: 4.1% to 28.4% (mean 13.2%).

**Processing**: Direct join on LSOA 2021 code. Percentage derived post-join.

**Citation**: Office for National Statistics (2023). *Census 2021: Disability (TS038), LSOA level*. Nomis.

---

## 9. Census 2021: Unpaid Care (TS039)

| Field | Detail |
|---|---|
| **Dataset** | Census 2021: Provision of Unpaid Care (TS039) |
| **Publisher** | ONS via Nomis |
| **Geography** | England and Wales |
| **Granularity** | LSOA (2021 vintage) |
| **Records** | 35,672 |
| **Reference date** | 21 March 2021 |
| **Format** | CSV |
| **Licence** | Open Government Licence v3.0 |
| **Local file** | `data_downloads/ts039/census2021-ts039-lsoa.csv` |

**Content**: Provision of unpaid care for usual residents aged 5+. Categories by hours per week: 19 hours or less, 20-49 hours, 50+ hours.

**Columns extracted**:
- `unpaid_care_19h_or_less`, `unpaid_care_20_to_49h`, `unpaid_care_50h_plus` (counts)
- `unpaid_care_rate_pct` -- derived: `(any care) / total * 100`

**Mental health relevance**: Unpaid carers experience significantly higher rates of anxiety, depression, and stress than non-carers. The intensity of caring (50+ hours/week) is particularly associated with poor mental health outcomes. High unpaid care rates in an LSOA indicate both existing mental health burden (caring for someone with a condition) and latent mental health risk (carer burnout). London range: 1.6% to 14.5% (mean 7.2%).

**Processing**: Direct join on LSOA 2021 code. Percentage derived post-join.

**Citation**: Office for National Statistics (2023). *Census 2021: Provision of unpaid care (TS039), LSOA level*. Nomis.

---

## 10. TfL Annualised Station Entry/Exit (2023)

| Field | Detail |
|---|---|
| **Dataset** | Annualised Entry & Exit Counts 2023 (LU/LO/DLR/TfL Rail) |
| **Publisher** | Transport for London (TfL) |
| **Geography** | Greater London |
| **Granularity** | Station-level |
| **Records** | ~270 stations |
| **Reference year** | 2023 |
| **Format** | XLSX (single sheet: AC23) |
| **Licence** | (C) Transport for London 2024; Open Data |
| **Local file** | `data RAW/AC2023_AnnualisedEntryExit.xlsx` |

**Content**: Annualised total passenger entries and exits for every London Underground, London Overground, DLR, and TfL Rail station. Includes typical weekday, Saturday, and Sunday breakdowns.

**Current status**: This dataset was originally used to derive transport accessibility and crowding metrics. Following the project pivot to mental health focus (2026-03-24), the 8 transport columns derived from this data were removed from the main table. The raw file is retained for potential future analysis (e.g. exploring whether transport accessibility correlates with mental health service utilisation). Original derived columns are preserved in `master_lsoa.gpkg.backup`.

**Citation**: Transport for London (2024). *Counts (LU/LO/DLR/TfL Rail) -- 2023: Station annualised entries and exits*. Version 20240403.

---

## 11. Community Support Services

| Field | Detail |
|---|---|
| **Dataset** | London Community Support Services (curated) |
| **Publisher** | Project team (curated from public directories) |
| **Geography** | Greater London |
| **Granularity** | Point-level (individual services) |
| **Records** | 175 services across 8 categories |
| **Reference date** | March 2026 |
| **Format** | CSV |
| **Licence** | Derived from publicly available information |
| **Local file** | `community_services.csv` |
| **Enrichment script** | `enrich_community_services.py` |
| **Geocoding script** | `geocode_and_map_lsoa.py` |

**What is this dataset?**
A manually curated inventory of 175 community support services across London, compiled from public directories and organisation websites. Each record includes the service name, type, address, postcode, and borough.

**8 Service categories**:

| Type | Count | Source organisations | Relevance to mental health |
|---|---|---|---|
| `mental_health_charity` | 31 | Mind (15 local branches), Samaritans (15 branches), Rethink Mental Illness (1) | Direct mental health support: counselling, crisis lines, peer support |
| `foodbank` | 29 | Trussell Trust network, independent foodbanks | Food insecurity is strongly linked to depression and anxiety |
| `citizens_advice` | 29 | Citizens Advice bureaux (29 boroughs) | Debt, housing, and benefits advice -- addressing social determinants of mental health |
| `nhs_talking_therapy` | 29 | NHS Talking Therapies (formerly IAPT), one per borough | Primary mental health treatment: CBT, counselling for anxiety/depression |
| `older_people_charity` | 25 | Age UK local branches | Social isolation and mental health support for older adults |
| `homelessness_service` | 15 | St Mungo's, Crisis, Centrepoint, Shelter, day centres | Homelessness is both a cause and consequence of poor mental health |
| `nhs_cmht` | 12 | NHS Community Mental Health Teams | Secondary care: psychiatric treatment, care coordination |
| `council_wellbeing_hub` | 5 | Social prescribing hubs, recovery cafes, ICMHCs | Community-based wellbeing and prevention services |

**Geocoding procedure** (script: `geocode_and_map_lsoa.py`):
1. Postcodes validated and normalised.
2. Bulk geocoded via `postcodes.io` API (free, no API key, max 100/batch).
3. API returns WGS84 lat/lon + LSOA 2011 code for each postcode.
4. LSOA codes mapped to 2021 via lookup.

**Spatial enrichment procedure** (script: `enrich_community_services.py`):
1. Service points converted to GeoDataFrame (EPSG:27700 British National Grid).
2. Point-in-polygon spatial join: each service assigned to the LSOA containing it.
3. Service counts aggregated per LSOA by type.
4. Distance-to-nearest computed: from each LSOA centroid to the nearest service of each type (Euclidean distance in metres, EPSG:27700).
5. Results written back to `master_lsoa.gpkg`.

**22 new columns added to `master_lsoa`**:
- 9 count columns: `community_services_total`, `cs_{type}_count`
- 9 distance columns: `dist_to_nearest_{type}_m`
- 4 metadata: `nearest_community_service_name`, `nearest_community_service_type`, `community_services_names`, `community_services_types`

**Limitations**:
- Coverage is not exhaustive -- there are more community services in London than captured here.
- Distance is Euclidean (straight-line), not walking/transit distance. Actual accessibility varies.
- Services may move, close, or open; this is a point-in-time snapshot (March 2026).
- Only 144 of 4,994 LSOAs contain a service within their boundary; the majority of LSOAs rely on distance-to-nearest metrics.

---

## 12. Data Assembly Procedure

### Overview

All data flows into a single GeoPackage file (`master_lsoa.gpkg`) containing one primary table (`master_lsoa`) with 120 columns and 4,994 rows (London LSOAs). The assembly follows this pipeline:

```
┌─────────────────────────────┐
│ LSOA 2021 Boundaries (ONS)  │──────────────────────┐
└─────────────────────────────┘                       │
                                                      ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│ IMD 2019 (MHCLG)           │───>│                              │
│  [LSOA 2011 codes]         │    │                              │
└─────────────────────────────┘    │                              │
                                   │                              │
┌─────────────────────────────┐    │                              │
│ SAMHI v5.00 (PLDR/Bristol)  │───>│   ONS 2011→2021 Lookup      │
│  [LSOA 2011 codes]         │    │   (vintage translation)      │
└─────────────────────────────┘    │                              │
                                   │                              │
                                   └──────────┬───────────────────┘
                                              │
                                              ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│ Census 2021 TS006 (density) │───>│                              │
│ Census 2021 TS066 (econ)    │───>│   master_lsoa.gpkg          │
│ Census 2021 TS037 (health)  │───>│   (4,994 LSOAs, 120 cols)   │
│ Census 2021 TS038 (disab.)  │───>│                              │
│ Census 2021 TS039 (care)    │───>│                              │
└─────────────────────────────┘    │                              │
  [LSOA 2021 codes — direct join]  │                              │
                                   │                              │
┌─────────────────────────────┐    │                              │
│ Community Services (curated)│───>│                              │
│  [geocoded, spatial join]   │    │                              │
└─────────────────────────────┘    └──────────────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────────────┐
                                   │   build_dashboard.py         │
                                   │   → dashboard/*.js files     │
                                   │   → index.html               │
                                   └──────────────────────────────┘
```

### Step-by-step procedure

**Step 1: Base geometry (LSOA 2021)**
- Load LSOA boundaries from ONS shapefile/CSV.
- Filter to London (33 boroughs + City of London) = 4,994 LSOAs.
- Set CRS to EPSG:27700 (British National Grid).

**Step 2: Join IMD 2019 (via 2011→2021 lookup)**
- Load `lsoa_2011_2021_lookup.csv`. Extract change indicator (CHGIND).
- For CHGIND = U (unchanged): direct join IMD row to matching 2021 LSOA.
- For CHGIND = S (split): duplicate parent 2011 IMD values to all child 2021 LSOAs.
- For CHGIND = M (merged): average IMD values from all parent 2011 LSOAs.
- Result: 4,659 LSOAs with IMD data; 335 with null (new 2021 LSOAs).

**Step 3: Join SAMHI (via 2011→2021 lookup)**
- Filter `samhi_long.csv` to years 2019 and 2022.
- Pivot to wide format: one row per LSOA 2011, columns `samhi_index_2019`, `samhi_dec_2019`, `antidep_rate_2022`, etc.
- Join via same 2011→2021 lookup as IMD.
- For the 335 orphan LSOAs: interpolate from geographic nearest-neighbours within the same borough.
- Result: 4,994 LSOAs with complete SAMHI data.

**Step 4: Join Census 2021 datasets (direct)**
- TS006 (population density): join on `geography code` = `lsoa_code`.
- TS066 (economic activity): extract relevant columns, join on LSOA 2021 code. Derive `employment_rate`.
- TS037 (general health): extract 5 health categories, derive `health_bad_or_very_bad_pct`.
- TS038 (disability): extract 4 categories, derive `disability_rate_pct`.
- TS039 (unpaid care): extract 3 hour-band columns, derive `unpaid_care_rate_pct`.
- All Census joins are direct (same 2021 vintage). Zero nulls.

**Step 5: Enrich with community services**
- Run `geocode_and_map_lsoa.py` to geocode 175 services.
- Run `enrich_community_services.py` to spatial-join and compute distance metrics.
- Write 22 new columns to `master_lsoa.gpkg`.

**Step 6: Build dashboard**
- Run `build_dashboard.py`.
- Reads `master_lsoa.gpkg`, simplifies geometry, exports slimmed GeoJSON + aggregates as `.js` files.
- Dashboard served as static HTML (Leaflet + Chart.js).

### Reproducibility

All enrichment scripts are included in the repository. To reproduce:
```bash
pip install -r requirements.txt
python geocode_and_map_lsoa.py       # Geocode community services
python enrich_community_services.py  # Enrich GPKG with services
python build_dashboard.py            # Rebuild dashboard data
```

Raw data files in `data RAW/` and `data_downloads/` are committed to the repo. The postcodes.io API used for geocoding is free and requires no API key.

---

## 13. Ethical Considerations

### Data provenance and legitimate basis
All datasets used are publicly available under open licences (Open Government Licence v3.0 or TfL Open Data). No personal data is processed. All statistics are aggregated at LSOA level (populations of ~1,000-3,000), which prevents identification of individuals.

### Potential biases
- **Service utilisation bias (SAMHI)**: SAMHI is based on service contacts (prescriptions, hospital admissions, benefit claims), which undercount need in populations with lower service access -- including ethnic minorities, migrants, and young people.
- **Census self-reporting**: General health and disability questions are self-assessed, which may vary by cultural background, age, and health literacy.
- **Community services coverage**: The curated dataset is not exhaustive. Some boroughs may have more uncaptured services than others, which could bias distance-to-nearest metrics.
- **Geographic granularity**: LSOA-level analysis commits the ecological fallacy -- area-level patterns do not necessarily apply to individuals within those areas.

### Bias mitigation
- SAMHI sub-indicators are provided individually so users can decompose the composite and assess which components drive observed patterns.
- Distance-to-nearest metrics use straight-line distance; the tool should note this is an approximation of actual accessibility.
- The dashboard narrative language uses "neighbourhood" and "area" rather than language implying individual-level claims.

### Misuse prevention
- The tool is designed for researchers, policymakers, and practitioners -- not for making decisions about individuals.
- Choropleth maps and ranking tables may stigmatise neighbourhoods if presented without context. The dashboard includes narrative framing alongside all data views.

---

## 14. Full Reference List

1. Daras, K., Barr, B., Rose, T., Wickham, S., Taylor-Robinson, D., & Whitehead, M. (2023). *Small Area Mental Health Index (SAMHI) v5.00*. Place-based Longitudinal Data Resource (PLDR), University of Bristol. Available at: PLDR Data Portal.

2. Ministry of Housing, Communities & Local Government (2019). *English Indices of Deprivation 2019*. London: MHCLG. Available at: GOV.UK.

3. Office for National Statistics (2022). *Lower layer Super Output Areas (December 2021) Boundaries EW BSC V4*. ONS Open Geography Portal. Contains OS data (C) Crown copyright and database right 2022.

4. Office for National Statistics (2023). *LSOA (2011) to LSOA (2021) to Local Authority District (2022) Lookup in England and Wales*. ONS Open Geography Portal.

5. Office for National Statistics (2023). *Census 2021: Population density (TS006), LSOA level*. Nomis. Available at: nomisweb.co.uk.

6. Office for National Statistics (2023). *Census 2021: Economic activity status (TS066), LSOA level*. Nomis. Available at: nomisweb.co.uk.

7. Office for National Statistics (2023). *Census 2021: General health (TS037), LSOA level*. Nomis. Available at: nomisweb.co.uk.

8. Office for National Statistics (2023). *Census 2021: Disability (TS038), LSOA level*. Nomis. Available at: nomisweb.co.uk.

9. Office for National Statistics (2023). *Census 2021: Provision of unpaid care (TS039), LSOA level*. Nomis. Available at: nomisweb.co.uk.

10. Transport for London (2024). *Counts (LU/LO/DLR/TfL Rail) -- 2023: Station annualised entries and exits*. Version 20240403.

11. Smith, T., Noble, M., Noble, S., Wright, G., McLennan, D., & Plunkett, E. (2015). *The English Indices of Deprivation 2015: Technical Report*. London: DCLG.

12. Postcodes.io (n.d.). *Free UK Postcode API*. Available at: postcodes.io. Used for geocoding community services to WGS84 coordinates and LSOA codes.

13. Social Finance & Wellcome (2026). *Wellcome Mental Health Data Prize 2026-2028: Applicant Information Pack*. London: Social Finance. Local copy: `SF_WELLCOME_MHDP_FINAL10Feb.pdf`.

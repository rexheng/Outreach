# Wellcome Mental Health Data Prize -- Project Instructions

## Project Context

Application workspace for the **Wellcome Mental Health Data Prize 2026-2028** (Social Finance / Wellcome). Building a data tool that links spatial, transport, and socioeconomic indicators at LSOA level across London to mental health outcomes -- enabling researchers, policymakers, and practitioners to explore neighbourhood-level determinants of mental health.

**Application deadline: 8 May 2026, 12 pm.**

The tool must be **in scope** for the prize:
- Data discovery or documentation
- Data analysis
- Facilitating data analysis (cleaning, manipulation)
- Sharing insights from data analysis

**Not** clinical decision-making tools, chatbots, mood trackers, or symptom management apps.

## Key Files

| File | Role |
|---|---|
| `master_lsoa.gpkg` | Assembled GeoPackage -- 4,994 London LSOAs, two tables |
| `SF_WELLCOME_MHDP_FINAL10Feb.pdf` | Prize information pack (28 pages, full evaluation criteria) |
| `Application-Documents.zip` | Sample application form PDF + budget template XLSX |
| `data RAW/` | Source CSVs/Excel -- do not modify |
| `Project_Overview.md` | Full project documentation and data dictionary |
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
- **Preferred table**: `master_lsoa_enriched_with_route_pressure` (snake_case, fully enriched)
- **Legacy table**: `master_lsoa` (original column names, for traceability)
- New feature tables should follow the naming pattern: `master_lsoa_{feature_group}`
- **Geometry**: MULTIPOLYGON in `geom` column, CRS EPSG:4326 (WGS84)

### Data Integrity
- **LSOA vintage**: Boundaries are 2021; IMD data is 2011-vintage mapped forward
- **Known gap**: 335 LSOAs (new 2021 codes, e.g. Havering splits) have null IMD scores -- no 2011 match. These have full Census/transport data.
- **Coverage**: 33 London boroughs + City of London (4,994 LSOAs). England total: ~33,000+.
- Raw files in `data RAW/` are read-only reference copies. Never modify them.

## Column Conventions

- IMD: `{domain}_score`, `{domain}_rank_where_1_is_most_deprived`, `{domain}_decile_where_1_is_most_deprived_10_of_lsoas`
- Transport: `dist_to_station_m`, `mean_ptal_ai`, `bus_stop_density_per_km2`
- Derived composites: `bus_vs_rail_gap_index`, `route_pressure_x_employment`, `crowding_pressure`
- Census economic activity: `total_16plus`, `econ_active`, `in_employment`, `unemployed`, `long_term_sick`, etc.

## Analysis Guardrails

- **Ecological data**: LSOA-level aggregates, not individual-level. Do not make individual-level inferences.
- **IMD direction**: Rank 1 = most deprived. Higher rank = less deprived.
- **PTAL direction**: Higher AI = better public transport accessibility.
- **Health deprivation scores**: Negative = less deprived, positive = more deprived. Range in dataset: -3.22 to 1.57.
- **IMD score range**: 2.3 to 64.7 (mean ~21.3).
- When building the mental health case, the Health Deprivation & Disability domain is the closest proxy available in the current dataset. A proper mental health dataset (meeting Annex 3 criteria) still needs to be sourced.

## Tooling

- **Data**: Python with geopandas, pandas; sqlite3 for quick queries
- **Viz**: folium for interactive maps, matplotlib/seaborn for static
- **Output**: All derived data goes back into `master_lsoa.gpkg`; document new columns in Project_Overview.md

## Frontend Design Direction

The webapp should draw from the visual language of charity/social-impact organisations like **London Community Foundation** (londoncf.org.uk):
- Clean, warm, approachable aesthetic -- not clinical or corporate
- Generous whitespace, clear typography hierarchy
- Teal/turquoise accent palette (consistent with Wellcome/Social Finance branding)
- Human-centred storytelling: data presented alongside narrative context, not raw tables
- Accessible, responsive, WCAG-compliant
- Map-forward: interactive geospatial views as the primary interface, with drill-down into LSOA detail
- Avoid: dark dashboards, dense data grids, overly technical UI. The audience includes policymakers and lived experience experts, not just data scientists

## Task Management

1. Write plans to `tasks/todo.md` with checkable items before starting work
2. Mark items complete as you go
3. After corrections, update `tasks/lessons.md` with the pattern
4. Verify changes work before marking complete

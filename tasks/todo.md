# Enrich master_lsoa.gpkg with Mental Health Data

## Steps
- [x] Step 1: Download all datasets (SAMHI, LSOA lookup, Census TS037/TS038/TS039)
- [x] Step 2: Remove 8 transport columns from master_lsoa
- [x] Step 3: Join SAMHI data via 2011-to-2021 lookup (8 cols: 2022 full + 2019 index/decile)
- [x] Step 4: Join Census 2021 health tables (TS037: 6 cols, TS038: 5 cols, TS039: 4 cols)
- [x] Step 5: Save enriched gpkg, drop route_pressure table, verify

## Verification
- [x] Row count = 4,994 after all joins
- [x] Spot-check LSOAs against raw source CSVs (E01000001 verified exact match)
- [x] Zero nulls across all 14 key new columns
- [x] Summary stats printed and reasonable

## Results
- **Final shape**: 4,994 rows x 98 columns (was 83, dropped 8 transport, added 23 mental health)
- **SAMHI coverage**: 4,659 direct matches + 335 LSOAs with no 2011 predecessor got values through the lookup mapping (all 4,994 have values)
- **Census coverage**: 4,994/4,994 (100%) for all three tables
- **Old `master_lsoa_enriched_with_route_pressure` table**: dropped
- **Backup**: `master_lsoa.gpkg.backup` preserved

## Production Readiness Pass (March 2026)

## Steps
- [x] Step 1: Clean workspace noise from version control scope (local screenshots, ad-hoc artifacts, temp tool folders)
- [x] Step 2: Update `.gitignore` for recurring local/generated files
- [x] Step 3: Refresh `README.md` with production deployment guidance and environment requirements
- [x] Step 4: Add portfolio-ready README summary section for external presentation
- [x] Step 5: Run test/smoke verification before shipping
- [x] Step 6: Commit and push production-readiness updates to GitHub

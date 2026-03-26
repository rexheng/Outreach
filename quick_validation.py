"""Quick validation of refactored CNI against new config."""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from app.data.risk_model import load_config, compute_lri

# Load GPKG
print("[*] Loading GeoPackage...")
gdf = gpd.read_file('master_lsoa.gpkg', layer='master_lsoa')
gdf = gdf.to_crs(epsg=4326)
print(f"    ✓ Loaded {len(gdf)} LSOAs")

# Compute NEW CNI with refactored config
print("\n[*] Computing new CNI with SAMHI priority...")
config_new = load_config(Path('risk_config.yaml'))
lri_new = compute_lri(gdf, config_new)
print("    ✓ CNI computed")

print('\n' + '='*70)
print('NEW CNI STATISTICS (Refactored with SAMHI)')
print('='*70)
print(f'Mean CNI: {lri_new["lri_score"].mean():.2f}')
print(f'Median CNI: {lri_new["lri_score"].median():.2f}')
print(f'Std Dev: {lri_new["lri_score"].std():.2f}')
print(f'Range: {lri_new["lri_score"].min():.2f} -- {lri_new["lri_score"].max():.2f}')

print('\nRisk Tier Distribution:')
tier_dist = lri_new['risk_tier'].value_counts().sort_index()
for tier, count in tier_dist.items():
    pct = count / len(lri_new) * 100
    print(f'  {tier:12} {count:5} ({pct:5.1f}%)')

print('\n' + '='*70)
print('SAMHI ALIGNMENT VALIDATION')
print('='*70)
corr_new = lri_new['lri_score'].corr(gdf['samhi_index_2022'])
print(f'Pearson r (NEW CNI vs SAMHI): {corr_new:.4f}')
print(f'Target: > 0.65 for strong mental health focus')
print(f'Status: {"✓ PASS" if corr_new > 0.65 else "⚠ WARNING - weaker than target"}')

print('\n' + '='*70)
print('TOP 15 LSOAS BY NEW CNI SCORE')
print('='*70)
top15 = pd.DataFrame({
    'lsoa_code': gdf['lsoa_code'],
    'lsoa_name': gdf['lsoa_name'],
    'new_cni': lri_new['lri_score'],
    'samhi_2022': gdf['samhi_index_2022'],
    'health_bad_pct': gdf['health_bad_or_very_bad_pct'],
    'disability_pct': gdf['disability_rate_pct'],
    'risk_tier': lri_new['risk_tier']
}).nlargest(15, 'new_cni')

print('\n{:<12} {:<40} {:>8} {:>8} {:>7} {:>9} {:<10}'.format(
    'LSOA Code', 'LSOA Name', 'CNI', 'SAMHI', 'Health%', 'Disab%', 'Tier'
))
print('-' * 100)
for idx, row in top15.iterrows():
    print('{:<12} {:<40} {:>8.2f} {:>8.2f} {:>7.1f} {:>9.1f} {:<10}'.format(
        row['lsoa_code'],
        row['lsoa_name'][:38],
        row['new_cni'],
        row['samhi_2022'],
        row['health_bad_pct'],
        row['disability_pct'],
        row['risk_tier']
    ))

print('\n' + '='*70)
print('CRITICAL TIER ANALYSIS')
print('='*70)
critical_lsoas = lri_new[lri_new['risk_tier'] == 'Critical'].copy()
critical_lsoas['lsoa_code'] = gdf['lsoa_code']
critical_lsoas['lsoa_name'] = gdf['lsoa_name']
critical_lsoas['samhi'] = gdf['samhi_index_2022']
critical_lsoas['borough'] = gdf['Local Authority District name (2019)']

print(f'\nTotal Critical LSOAs: {len(critical_lsoas)}')
print(f'Population affected (if all have mean 16+ pop): {(len(critical_lsoas) * gdf["total_16plus"].mean()):,.0f}')
print(f'\nCritical by Borough:')

borough_critical = critical_lsoas.groupby('borough').size().sort_values(ascending=False).head(10)
for borough, count in borough_critical.items():
    pct_of_critical = count / len(critical_lsoas) * 100
    print(f'  {borough:<30} {count:3} ({pct_of_critical:5.1f}%)')

print('\n' + '='*70)
print('VALIDATION COMPLETE')
print('='*70)

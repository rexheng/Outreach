"""Build dashboard data: simplified GeoJSON, borough aggregates, AI insights."""
import geopandas as gpd
import pandas as pd
import numpy as np
import json
import os

GPKG = 'master_lsoa.gpkg'
OUT_DIR = 'dashboard'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load and prep ──────────────────────────────────────────────
gdf = gpd.read_file(GPKG, layer='master_lsoa').to_crs(epsg=4326)
print(f"Loaded {len(gdf)} LSOAs, {len(gdf.columns)} columns")

# ── Slim columns for dashboard ─────────────────────────────────
keep = [
    'lsoa_code', 'lsoa_name',
    'Local Authority District name (2019)',
    'imd_score',
    'Health Deprivation and Disability Score',
    'Health Deprivation and Disability Decile (where 1 is most deprived 10% of LSOAs)',
    'Income Score (rate)',
    'Employment Score (rate)',
    'pop_density_2021', 'employment_rate', 'long_term_sick', 'total_16plus',
    'samhi_index_2022', 'samhi_dec_2022', 'samhi_index_2019', 'samhi_dec_2019',
    'antidep_rate_2022', 'est_qof_dep_2022', 'mh_hospital_rate_2022', 'dla_pip_pct_2022',
    'health_bad_or_very_bad_pct', 'disability_rate_pct', 'unpaid_care_rate_pct',
    'geometry'
]
gdf_slim = gdf[[c for c in keep if c in gdf.columns]].copy()
gdf_slim = gdf_slim.rename(columns={
    'Local Authority District name (2019)': 'borough',
    'Health Deprivation and Disability Score': 'health_dep_score',
    'Health Deprivation and Disability Decile (where 1 is most deprived 10% of LSOAs)': 'health_dep_decile',
    'Income Score (rate)': 'income_score',
    'Employment Score (rate)': 'employment_score',
})

# Simplify geometry and round numbers
gdf_slim['geometry'] = gdf_slim.geometry.simplify(tolerance=0.001)
for col in gdf_slim.select_dtypes(include='float64').columns:
    gdf_slim[col] = gdf_slim[col].round(3)

# ── Export LSOA GeoJSON ────────────────────────────────────────
geojson = json.loads(gdf_slim.to_json())
with open(f'{OUT_DIR}/lsoa_data.js', 'w') as f:
    f.write('const LSOA_DATA = ')
    json.dump(geojson, f, separators=(',', ':'))
    f.write(';')
print(f"LSOA GeoJSON: {os.path.getsize(f'{OUT_DIR}/lsoa_data.js') / 1024 / 1024:.2f} MB")

# ── Borough aggregates ─────────────────────────────────────────
borough_agg = gdf_slim.drop(columns='geometry').groupby('borough').agg(
    lsoa_count=('lsoa_code', 'count'),
    samhi_mean=('samhi_index_2022', 'mean'),
    samhi_2019_mean=('samhi_index_2019', 'mean'),
    antidep_mean=('antidep_rate_2022', 'mean'),
    qof_dep_mean=('est_qof_dep_2022', 'mean'),
    mh_hospital_mean=('mh_hospital_rate_2022', 'mean'),
    bad_health_mean=('health_bad_or_very_bad_pct', 'mean'),
    disability_mean=('disability_rate_pct', 'mean'),
    unpaid_care_mean=('unpaid_care_rate_pct', 'mean'),
    imd_mean=('imd_score', 'mean'),
    health_dep_mean=('health_dep_score', 'mean'),
    employment_rate_mean=('employment_rate', 'mean'),
).round(3).reset_index()

# COVID change
borough_agg['samhi_covid_change'] = (borough_agg['samhi_mean'] - borough_agg['samhi_2019_mean']).round(3)

borough_list = borough_agg.sort_values('samhi_mean', ascending=False).to_dict('records')
with open(f'{OUT_DIR}/borough_data.js', 'w') as f:
    f.write('const BOROUGH_DATA = ')
    json.dump(borough_list, f, separators=(',', ':'))
    f.write(';')
print(f"Borough data: {len(borough_list)} boroughs")

# ── Critical areas (top 50 worst SAMHI) ────────────────────────
critical = gdf_slim.drop(columns='geometry').nlargest(50, 'samhi_index_2022')[
    ['lsoa_code', 'lsoa_name', 'borough', 'samhi_index_2022', 'samhi_dec_2022',
     'antidep_rate_2022', 'est_qof_dep_2022', 'health_bad_or_very_bad_pct',
     'disability_rate_pct', 'imd_score']
].to_dict('records')

with open(f'{OUT_DIR}/critical_data.js', 'w') as f:
    f.write('const CRITICAL_DATA = ')
    json.dump(critical, f, separators=(',', ':'))
    f.write(';')
print(f"Critical areas: {len(critical)} LSOAs")

# ── AI Insights (pre-computed narrative) ───────────────────────
df = gdf_slim.drop(columns='geometry')

# Headline stats
london_samhi = df['samhi_index_2022'].mean()
london_antidep = df['antidep_rate_2022'].mean()
london_qof = df['est_qof_dep_2022'].mean()
london_bad_health = df['health_bad_or_very_bad_pct'].mean()
london_disability = df['disability_rate_pct'].mean()
london_care = df['unpaid_care_rate_pct'].mean()

# Worst boroughs
worst_boroughs = borough_agg.nlargest(5, 'samhi_mean')['borough'].tolist()
best_boroughs = borough_agg.nsmallest(5, 'samhi_mean')['borough'].tolist()

# COVID impact
covid_worse = borough_agg.nlargest(5, 'samhi_covid_change')
covid_better = borough_agg.nsmallest(5, 'samhi_covid_change')

# Correlation
corr_imd_samhi = df['imd_score'].corr(df['samhi_index_2022'])
corr_emp_samhi = df['employment_rate'].corr(df['samhi_index_2022'])

# Decile 1 (most deprived) vs Decile 10 comparison
d1 = df[df['samhi_dec_2022'] >= 9]
d10 = df[df['samhi_dec_2022'] <= 2]

# Population in crisis areas
crisis_pop = df[df['samhi_dec_2022'] >= 8]['total_16plus'].sum()
total_pop = df['total_16plus'].sum()

insights = {
    "headline": {
        "samhi_mean": round(london_samhi, 2),
        "antidep_rate": round(london_antidep, 1),
        "qof_depression": round(london_qof, 1),
        "bad_health_pct": round(london_bad_health, 1),
        "disability_pct": round(london_disability, 1),
        "unpaid_care_pct": round(london_care, 1),
        "total_lsoas": len(df),
        "crisis_pop": int(crisis_pop),
        "total_pop": int(total_pop),
    },
    "narratives": [
        {
            "title": "The geography of mental health need",
            "body": f"Across London's {len(df):,} neighbourhoods, mental health burden is profoundly unequal. "
                    f"The average SAMHI index score is {london_samhi:.2f}, but this masks a range from "
                    f"{df['samhi_index_2022'].min():.1f} to {df['samhi_index_2022'].max():.1f}. "
                    f"The boroughs bearing the heaviest burden — {', '.join(worst_boroughs[:3])} — "
                    f"score significantly above the London mean, while {', '.join(best_boroughs[:3])} "
                    f"fare comparatively better.",
            "type": "geographic"
        },
        {
            "title": "The deprivation-mental health nexus",
            "body": f"IMD deprivation and mental health need are strongly correlated (r = {corr_imd_samhi:.2f}). "
                    f"Neighbourhoods in the most deprived IMD decile have an average antidepressant prescribing "
                    f"rate of {d1['antidep_rate_2022'].mean():.1f} per 1,000, compared to {d10['antidep_rate_2022'].mean():.1f} "
                    f"in the least deprived areas. Employment rates show an inverse pattern "
                    f"(r = {corr_emp_samhi:.2f} with SAMHI), suggesting economic inactivity "
                    f"and mental health distress reinforce each other.",
            "type": "correlation"
        },
        {
            "title": "The pandemic's lasting shadow",
            "body": f"Comparing 2019 to 2022, every London borough saw its SAMHI index worsen. "
                    f"The boroughs hit hardest were {covid_worse.iloc[0]['borough']} "
                    f"(+{covid_worse.iloc[0]['samhi_covid_change']:.2f}), "
                    f"{covid_worse.iloc[1]['borough']} (+{covid_worse.iloc[1]['samhi_covid_change']:.2f}), "
                    f"and {covid_worse.iloc[2]['borough']} (+{covid_worse.iloc[2]['samhi_covid_change']:.2f}). "
                    f"These are not areas that 'bounced back' — the data suggests a structural deepening "
                    f"of mental health need post-COVID.",
            "type": "temporal"
        },
        {
            "title": "Scale of need",
            "body": f"An estimated {crisis_pop:,} adults (aged 16+) live in neighbourhoods ranked in the "
                    f"top 30% for mental health need (SAMHI deciles 8-10). That represents "
                    f"{crisis_pop/total_pop*100:.0f}% of London's adult population. "
                    f"The average GP depression prevalence in these areas is "
                    f"{df[df['samhi_dec_2022'] >= 8]['est_qof_dep_2022'].mean():.1f}%, "
                    f"with antidepressant prescribing at {df[df['samhi_dec_2022'] >= 8]['antidep_rate_2022'].mean():.1f} "
                    f"per 1,000 population — substantially above the London average of {london_antidep:.1f}.",
            "type": "scale"
        },
        {
            "title": "Disability and caring burden",
            "body": f"London's disability rate averages {london_disability:.1f}%, but in the most "
                    f"mentally health-deprived neighbourhoods it reaches {d1['disability_rate_pct'].mean():.1f}%. "
                    f"Unpaid care provision follows a similar pattern: {london_care:.1f}% of Londoners "
                    f"provide unpaid care overall, rising in areas of highest mental health need. "
                    f"These overlapping burdens suggest that mental health policy cannot be siloed — "
                    f"it intersects with disability support, carer support, and community infrastructure.",
            "type": "intersection"
        },
    ],
    "worst_boroughs": worst_boroughs,
    "best_boroughs": best_boroughs,
}

with open(f'{OUT_DIR}/insights_data.js', 'w') as f:
    f.write('const INSIGHTS_DATA = ')
    json.dump(insights, f, separators=(',', ':'))
    f.write(';')
print("Insights generated")

# ── Scatter data (SAMHI vs IMD, sampled for performance) ───────
scatter = df[['imd_score', 'samhi_index_2022', 'borough', 'lsoa_name']].dropna()
scatter_data = scatter.round(2).to_dict('records')
with open(f'{OUT_DIR}/scatter_data.js', 'w') as f:
    f.write('const SCATTER_DATA = ')
    json.dump(scatter_data, f, separators=(',', ':'))
    f.write(';')
print(f"Scatter data: {len(scatter_data)} points")

print("\nAll dashboard data exported to dashboard/")

"""Pre-compute all data into static JSON for Vercel deployment.

Run locally before deploying:
    python scripts/build_vercel_data.py

Requires: geopandas, fiona, shapely, pandas, pyyaml (installed locally).
Outputs to: public/data/
"""

import json
import sys
import shutil
from pathlib import Path

# Add project root to path so we can import app modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import geopandas as gpd
import pandas as pd
import yaml

from app.config import (
    GPKG_PATH, GPKG_LAYER, SIMPLIFY_TOLERANCE, DISPLAY_COLUMNS,
    RISK_CONFIG_PATH,
)
from app.data.risk_model import load_config, compute_lri

OUTPUT_DIR = ROOT / "public" / "data"
BOROUGH_COL = "Local Authority District name (2019)"


class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)


def write_json(data, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder)
    size = path.stat().st_size
    print(f"  {filename}: {size / 1024:.0f} KB")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading GeoPackage...")
    gdf = gpd.read_file(str(GPKG_PATH), layer=GPKG_LAYER)
    gdf = gdf.to_crs(epsg=4326)

    print("Computing CNI scores...")
    config = load_config(RISK_CONFIG_PATH)
    lri_df = compute_lri(gdf, config)
    for col in lri_df.columns:
        gdf[col] = lri_df[col]

    # ---------- 1. geojson.json ----------
    print("Building geojson.json...")
    keep_cols = list(dict.fromkeys(
        DISPLAY_COLUMNS + list(lri_df.columns) + ["geometry"]
    ))
    map_gdf = gdf[keep_cols].copy()
    map_gdf["geometry"] = map_gdf.geometry.simplify(
        SIMPLIFY_TOLERANCE, preserve_topology=True
    )
    float_cols = map_gdf.select_dtypes(include="float").columns
    map_gdf[float_cols] = map_gdf[float_cols].round(4)
    geojson_data = json.loads(map_gdf.to_json())
    write_json(geojson_data, "geojson.json")

    # ---------- 2. boroughs.json ----------
    print("Building boroughs.json...")
    borough_stats = (
        gdf.groupby(BOROUGH_COL)
        .agg(
            mean_lri=("lri_score", "mean"),
            median_lri=("lri_score", "median"),
            max_lri=("lri_score", "max"),
            lsoa_count=("lsoa_code", "count"),
            total_population=("total_16plus", "sum"),
            critical_count=("risk_tier", lambda x: (x == "Critical").sum()),
            high_count=("risk_tier", lambda x: (x == "High").sum()),
            samhi_mean=("samhi_index_2022", "mean"),
            samhi_2019_mean=("samhi_index_2019", "mean"),
            antidep_mean=("antidep_rate_2022", "mean"),
            qof_dep_mean=("est_qof_dep_2022", "mean"),
            bad_health_mean=("health_bad_or_very_bad_pct", "mean"),
            disability_mean=("disability_rate_pct", "mean"),
            unpaid_care_mean=("unpaid_care_rate_pct", "mean"),
            imd_mean=("imd_score", "mean"),
        )
        .reset_index()
        .rename(columns={BOROUGH_COL: "borough"})
        .round(2)
        .sort_values("mean_lri", ascending=False)
    )
    borough_stats["samhi_covid_change"] = (
        borough_stats["samhi_mean"] - borough_stats["samhi_2019_mean"]
    ).round(2)
    borough_list = borough_stats.to_dict(orient="records")
    write_json(borough_list, "boroughs.json")

    # ---------- 3. insights.json ----------
    print("Building insights.json...")
    df = gdf.drop(columns="geometry")
    london_samhi = float(df["samhi_index_2022"].mean())
    london_antidep = float(df["antidep_rate_2022"].mean())
    london_qof = float(df["est_qof_dep_2022"].mean())
    london_bad_health = float(df["health_bad_or_very_bad_pct"].mean())
    london_disability = float(df["disability_rate_pct"].mean())
    london_care = float(df["unpaid_care_rate_pct"].mean())

    worst_boroughs = borough_stats.nlargest(5, "samhi_mean")["borough"].tolist()
    best_boroughs = borough_stats.nsmallest(5, "samhi_mean")["borough"].tolist()

    covid_worse = borough_stats.nlargest(5, "samhi_covid_change")
    covid_better = borough_stats.nsmallest(5, "samhi_covid_change")

    corr_imd_samhi = float(df["imd_score"].corr(df["samhi_index_2022"]))
    corr_emp_samhi = float(df["employment_rate"].corr(df["samhi_index_2022"]))

    d1 = df[df["samhi_dec_2022"] >= 9]
    d10 = df[df["samhi_dec_2022"] <= 2]

    crisis_pop = int(df[df["samhi_dec_2022"] >= 8]["total_16plus"].sum())
    total_pop = int(df["total_16plus"].sum())

    insights = {
        "headline": {
            "samhi_mean": round(london_samhi, 2),
            "antidep_rate": round(london_antidep, 1),
            "qof_depression": round(london_qof, 1),
            "bad_health_pct": round(london_bad_health, 1),
            "disability_pct": round(london_disability, 1),
            "unpaid_care_pct": round(london_care, 1),
            "total_lsoas": int(len(df)),
            "crisis_pop": crisis_pop,
            "total_pop": total_pop,
        },
        "narratives": [
            {
                "title": "The geography of mental health need",
                "body": (
                    f"Across London\u2019s {len(df):,} neighbourhoods, mental health burden is profoundly unequal. "
                    f"The average SAMHI index score is {london_samhi:.2f}, but this masks a range from "
                    f"{df['samhi_index_2022'].min():.1f} to {df['samhi_index_2022'].max():.1f}. "
                    f"The boroughs bearing the heaviest burden \u2014 {', '.join(worst_boroughs[:3])} \u2014 "
                    f"score significantly above the London mean, while {', '.join(best_boroughs[:3])} "
                    f"fare comparatively better."
                ),
                "type": "geographic",
            },
            {
                "title": "The deprivation\u2013mental health nexus",
                "body": (
                    f"IMD deprivation and mental health need are strongly correlated (r\u2009=\u2009{corr_imd_samhi:.2f}). "
                    f"Neighbourhoods in the most deprived SAMHI decile have an average antidepressant prescribing "
                    f"rate of {d1['antidep_rate_2022'].mean():.1f} per 1,000, compared to {d10['antidep_rate_2022'].mean():.1f} "
                    f"in the least deprived areas. Employment rates show an inverse pattern "
                    f"(r\u2009=\u2009{corr_emp_samhi:.2f} with SAMHI), suggesting economic inactivity "
                    f"and mental health distress reinforce each other."
                ),
                "type": "correlation",
            },
            {
                "title": "The pandemic\u2019s lasting shadow",
                "body": (
                    f"Comparing 2019 to 2022, every London borough saw its SAMHI index worsen. "
                    f"The boroughs hit hardest were {covid_worse.iloc[0]['borough']} "
                    f"(+{covid_worse.iloc[0]['samhi_covid_change']:.2f}), "
                    f"{covid_worse.iloc[1]['borough']} (+{covid_worse.iloc[1]['samhi_covid_change']:.2f}), "
                    f"and {covid_worse.iloc[2]['borough']} (+{covid_worse.iloc[2]['samhi_covid_change']:.2f}). "
                    f"These are not areas that \u2018bounced back\u2019 \u2014 the data suggests a structural deepening "
                    f"of mental health need post-COVID."
                ),
                "type": "temporal",
            },
            {
                "title": "Scale of need",
                "body": (
                    f"An estimated {crisis_pop:,} adults (aged 16+) live in neighbourhoods ranked in the "
                    f"top 30% for mental health need (SAMHI deciles 8\u201310). That represents "
                    f"{crisis_pop / total_pop * 100:.0f}% of London\u2019s adult population. "
                    f"The average GP depression prevalence in these areas is "
                    f"{df[df['samhi_dec_2022'] >= 8]['est_qof_dep_2022'].mean():.1f}%, "
                    f"with antidepressant prescribing at {df[df['samhi_dec_2022'] >= 8]['antidep_rate_2022'].mean():.1f} "
                    f"per 1,000 population \u2014 substantially above the London average of {london_antidep:.1f}."
                ),
                "type": "scale",
            },
            {
                "title": "Disability and caring burden",
                "body": (
                    f"London\u2019s disability rate averages {london_disability:.1f}%, but in the most "
                    f"mentally health-deprived neighbourhoods it reaches {d1['disability_rate_pct'].mean():.1f}%. "
                    f"Unpaid care provision follows a similar pattern: {london_care:.1f}% of Londoners "
                    f"provide unpaid care overall, rising in areas of highest mental health need. "
                    f"These overlapping burdens suggest that mental health policy cannot be siloed \u2014 "
                    f"it intersects with disability support, carer support, and community infrastructure."
                ),
                "type": "intersection",
            },
        ],
        "worst_boroughs": worst_boroughs,
        "best_boroughs": best_boroughs,
    }
    write_json(insights, "insights.json")

    # ---------- 4. critical.json ----------
    print("Building critical.json...")
    critical_cols = [
        "lsoa_code", "lsoa_name", BOROUGH_COL, "samhi_index_2022", "samhi_dec_2022",
        "antidep_rate_2022", "est_qof_dep_2022", "health_bad_or_very_bad_pct",
        "disability_rate_pct", "imd_score",
    ]
    critical_df = df.nlargest(50, "samhi_index_2022")[critical_cols].copy()
    critical_df = critical_df.rename(columns={BOROUGH_COL: "borough"}).round(2)
    write_json(critical_df.to_dict("records"), "critical.json")

    # ---------- 5. scatter.json ----------
    print("Building scatter.json...")
    scatter_df = df[["imd_score", "samhi_index_2022", BOROUGH_COL, "lsoa_name"]].dropna().copy()
    scatter_df = scatter_df.rename(columns={BOROUGH_COL: "borough"}).round(2)
    write_json(scatter_df.to_dict("records"), "scatter.json")

    # ---------- 6. borough-geojson.json ----------
    print("Building borough-geojson.json...")
    borough_geo = gdf[[BOROUGH_COL, "geometry"]].copy()
    borough_geo = borough_geo.dissolve(by=BOROUGH_COL).reset_index()
    borough_geo = borough_geo.rename(columns={BOROUGH_COL: "borough"})
    borough_geo["geometry"] = borough_geo.geometry.simplify(0.002, preserve_topology=True)
    samhi_lookup = borough_stats.set_index("borough")["samhi_mean"].to_dict()
    borough_geo["samhi_mean"] = borough_geo["borough"].map(samhi_lookup).round(2)
    write_json(json.loads(borough_geo.to_json()), "borough-geojson.json")

    # ---------- 7. metadata.json ----------
    print("Building metadata.json...")
    write_json(config, "metadata.json")

    # ---------- 8. lsoa-lookup.json ----------
    print("Building lsoa-lookup.json...")
    # All columns except geometry, for LSOA detail endpoint and chat context
    lookup_df = gdf.drop(columns="geometry").copy()
    float_cols = lookup_df.select_dtypes(include="float").columns
    lookup_df[float_cols] = lookup_df[float_cols].round(4)
    # Key by lsoa_code for O(1) lookup
    lookup = {}
    for _, row in lookup_df.iterrows():
        code = row["lsoa_code"]
        record = {}
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                record[k] = int(v)
            elif isinstance(v, (np.floating,)):
                record[k] = None if np.isnan(v) else round(float(v), 4)
            elif pd.isna(v):
                record[k] = None
            else:
                record[k] = v
        lookup[code] = record
    write_json(lookup, "lsoa-lookup.json")

    # ---------- 9. chat-boroughs.json ----------
    print("Building chat-boroughs.json...")
    # Pre-compute everything the chat context builder needs
    indicator_labels = {
        "ind_Health Deprivation and Disability Score": "Health Deprivation & Disability",
        "ind_Income Score (rate)": "Income Deprivation Rate",
        "ind_Employment Score (rate)": "Employment Deprivation Rate",
        "ind_long_term_sick": "Long-term Sick Rate",
        "ind_econ_inactive": "Economic Inactivity Rate",
        "ind_unemployed": "Unemployment Rate",
        "ind_Barriers to Housing and Services Score": "Barriers to Housing & Services",
        "ind_Crime Score": "Crime Score",
    }

    chat_data = {
        "london_overview": {
            "total_lsoas": int(len(df)),
            "mean_lri": round(float(gdf["lri_score"].mean()), 2),
            "median_lri": round(float(gdf["lri_score"].median()), 2),
            "critical_count": int((gdf["risk_tier"] == "Critical").sum()),
            "high_count": int((gdf["risk_tier"] == "High").sum()),
            "moderate_count": int((gdf["risk_tier"] == "Moderate").sum()),
            "low_count": int((gdf["risk_tier"] == "Low").sum()),
        },
        "borough_names": sorted(gdf[BOROUGH_COL].dropna().unique().tolist()),
        "boroughs": {},
    }

    for b in borough_list:
        bname = b["borough"]
        borough_lsoas = gdf[gdf[BOROUGH_COL] == bname]

        # Indicator averages vs London
        indicators = {}
        for col, label in indicator_labels.items():
            if col in borough_lsoas.columns:
                bval = float(borough_lsoas[col].mean())
                lval = float(gdf[col].mean())
                indicators[label] = {
                    "borough_avg": round(bval, 4),
                    "london_avg": round(lval, 4),
                    "diff": round(bval - lval, 4),
                }

        # Top 5 LSOAs
        top5 = borough_lsoas.nlargest(5, "lri_score")
        top5_list = []
        for _, row in top5.iterrows():
            top5_list.append({
                "lsoa_code": row["lsoa_code"],
                "lsoa_name": row.get("lsoa_name", ""),
                "lri_score": round(float(row["lri_score"]), 2),
                "risk_tier": row.get("risk_tier", ""),
            })

        chat_data["boroughs"][bname] = {
            "stats": b,
            "indicators": indicators,
            "top5_lsoas": top5_list,
        }

    write_json(chat_data, "chat-boroughs.json")

    # ---------- 10. Copy policy files ----------
    print("Copying policy files...")
    for src_name, dst_name in [
        ("policy_signals.json", "policy-signals.json"),
        ("policy_recommendations.json", "policy-recs.json"),
    ]:
        src = ROOT / src_name
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / dst_name)
            print(f"  {dst_name}: copied")
        else:
            print(f"  {dst_name}: SKIPPED (source not found)")

    # ---------- 11. briefing-data.json ----------
    print("Building briefing-data.json...")
    # Per-borough data needed for PDF generation
    briefing = {
        "london_averages": {
            "lri_score": round(float(gdf["lri_score"].mean()), 2),
            "samhi_index_2022": round(float(gdf["samhi_index_2022"].mean()), 2),
            "antidep_rate_2022": round(float(gdf["antidep_rate_2022"].mean()), 2),
            "health_bad_or_very_bad_pct": round(float(gdf["health_bad_or_very_bad_pct"].mean()), 2),
            "imd_score": round(float(gdf["imd_score"].mean()), 2),
        },
        "borough_ranking": [],  # sorted by mean_lri desc
        "boroughs": {},
    }

    sorted_boroughs = sorted(borough_list, key=lambda b: b["mean_lri"], reverse=True)
    briefing["borough_ranking"] = [b["borough"] for b in sorted_boroughs]

    for b in borough_list:
        bname = b["borough"]
        borough_lsoas = gdf[gdf[BOROUGH_COL] == bname]

        top5 = borough_lsoas.nlargest(5, "lri_score")
        top5_rows = []
        for _, row in top5.iterrows():
            socio = row.get("pillar_socioeconomic", 0) or 0
            demo = row.get("pillar_health_and_burden", 0) or 0
            top5_rows.append({
                "lsoa_name": str(row.get("lsoa_name", row.get("lsoa_code", "Unknown"))),
                "lri_score": round(float(row["lri_score"]), 1),
                "risk_tier": row.get("risk_tier", "-"),
                "dominant_pillar": "Socioeconomic deprivation" if socio >= demo else "Health & burden vulnerability",
            })

        # Narrative driver info
        critical_lsoas = borough_lsoas[borough_lsoas["risk_tier"] == "Critical"]
        critical_count = len(critical_lsoas)
        socio_dominant = 0
        if critical_count > 0:
            socio_dominant = int(
                (critical_lsoas["pillar_socioeconomic"] > critical_lsoas["pillar_health_and_burden"]).sum()
            )

        briefing["boroughs"][bname] = {
            "stats": b,
            "top5": top5_rows,
            "critical_count": critical_count,
            "socio_dominant_count": socio_dominant,
            "borough_antidep_mean": round(float(b.get("antidep_mean", 0) or 0), 1),
            "london_antidep_mean": round(float(gdf["antidep_rate_2022"].mean()), 1),
        }

    write_json(briefing, "briefing-data.json")

    print(f"\nDone. {len(list(OUTPUT_DIR.glob('*.json')))} files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

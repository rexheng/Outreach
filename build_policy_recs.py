"""Build-time script: generate policy recommendations for all boroughs + London-wide.

Usage:
    python build_policy_recs.py              # full build
    python build_policy_recs.py --resume     # skip boroughs already in output
    python build_policy_recs.py --signals-only  # only compute signals, skip Gemini
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent


def _save_recs(path: Path, recs: list, generated_at: str | None = None):
    """Save recommendations with metadata."""
    output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signals_generated_at": generated_at,
        "recommendations": recs,
    }
    path.write_text(json.dumps(output, indent=2, default=str))


def _adapt_borough(borough_data: dict) -> dict:
    """Map signals borough dict to the keys generate_borough_recs expects."""
    return {
        "borough_name":     borough_data.get("borough_name", "Unknown"),
        "lsoa_count":       borough_data.get("lsoa_count", 0),
        "population":       borough_data.get("population_est_2015", 0),
        "tier_counts":      borough_data.get("tier_counts", {}),
        "mean_samhi":       borough_data.get("mean_samhi_2022", 0.0),
        "trajectory":       borough_data.get("mh_trajectory", "stable"),
        "service_coverage": borough_data.get("service_coverage", {}),
        "top_lsoas":        borough_data.get("top_5_lsoas", []),
    }


def _adapt_london(london_data: dict, boroughs: dict) -> dict:
    """Map signals london dict to the keys generate_london_recs expects."""
    # Compute London-wide mean SAMHI from borough averages
    samhi_vals = [b["mean_samhi_2022"] for b in boroughs.values() if "mean_samhi_2022" in b]
    mean_samhi = sum(samhi_vals) / len(samhi_vals) if samhi_vals else 0.0

    # Compute total population from boroughs
    total_pop = sum(b.get("population_est_2015", 0) for b in boroughs.values())

    # Derive borough trajectory lists
    top_10 = london_data.get("top_10_boroughs", [])
    high_risk = ", ".join(b["borough_name"] for b in top_10[:5]) if top_10 else "N/A"

    # Classify boroughs by trajectory
    improving = [name for name, b in boroughs.items() if b.get("mh_trajectory") == "improving"]
    worsening = [name for name, b in boroughs.items() if b.get("mh_trajectory") == "worsening"]

    # Collect top LSOAs across all boroughs
    top_lsoas = []
    for b in boroughs.values():
        top_lsoas.extend(b.get("top_5_lsoas", []))
    top_lsoas.sort(key=lambda x: x.get("composite_need_score", 0), reverse=True)

    return {
        "total_lsoas":        london_data.get("total_lsoas", 0),
        "total_population":   total_pop,
        "tier_counts":        london_data.get("tier_counts", {}),
        "mean_samhi":         mean_samhi,
        "high_risk_boroughs": high_risk,
        "improving_boroughs": ", ".join(improving) if improving else "N/A",
        "worsening_boroughs": ", ".join(worsening) if worsening else "N/A",
        "service_coverage":   {},
        "top_lsoas":          top_lsoas[:10],
    }


def main():
    parser = argparse.ArgumentParser(description="Build policy recommendations")
    parser.add_argument("--resume", action="store_true", help="Skip boroughs already in output file")
    parser.add_argument("--signals-only", action="store_true", help="Only compute signals, skip Gemini")
    args = parser.parse_args()

    gpkg_path = BASE_DIR / "master_lsoa.gpkg"
    signals_path = BASE_DIR / "policy_signals.json"
    recs_path = BASE_DIR / "policy_recommendations.json"

    # Step 1: Compute signals
    from app.data.policy_signals import build_signals
    signals = build_signals(gpkg_path, signals_path)

    if args.signals_only:
        print("\n--signals-only: done.")
        return

    # Step 2: Load existing recs for resume mode
    existing_recs = []
    existing_boroughs = set()
    has_london = False

    if args.resume and recs_path.exists():
        try:
            existing = json.loads(recs_path.read_text())
            existing_recs = existing.get("recommendations", [])
            existing_boroughs = {r["borough"] for r in existing_recs if r.get("scope") == "borough"}
            has_london = any(r.get("scope") == "london_wide" for r in existing_recs)
            print(f"\nResume mode: {len(existing_boroughs)} boroughs already done, London-wide: {has_london}")
        except Exception as e:
            print(f"  Warning: could not load existing recs: {e}")

    # Step 3: Generate recommendations
    from app.api.policy_agent import generate_borough_recs, generate_london_recs

    all_recs = list(existing_recs)
    boroughs = signals["boroughs"]

    # Adapt signals to the format the agent functions expect
    london_adapted = _adapt_london(signals["london"], boroughs)
    london_mean_samhi = london_adapted["mean_samhi"]

    # London-wide
    if not has_london:
        print("\nGenerating London-wide recommendations...")
        try:
            london_recs = generate_london_recs(london_adapted)
            for i, rec in enumerate(london_recs):
                rec["id"] = f"london-{rec.get('timeframe', 'st')}-{i+1}"
                rec["borough"] = "London"
                rec["scope"] = "london_wide"
            all_recs.extend(london_recs)
            print(f"  Generated {len(london_recs)} London-wide recommendations")
        except Exception as e:
            print(f"  ERROR generating London-wide recs: {e}")

    # Per-borough
    total = len(boroughs)
    for idx, (borough_name, borough_data) in enumerate(sorted(boroughs.items()), 1):
        if borough_name in existing_boroughs:
            print(f"  [{idx}/{total}] {borough_name} -- skipped (already done)")
            continue

        print(f"  [{idx}/{total}] {borough_name}...")
        try:
            adapted = _adapt_borough(borough_data)
            recs = generate_borough_recs(adapted, london_mean_samhi)
            slug = borough_data["borough_slug"]
            for i, rec in enumerate(recs):
                tf = rec.get("timeframe", "short_term")
                tf_short = "st" if tf == "short_term" else "lt"
                rec["id"] = f"{slug}-{tf_short}-{i+1}"
                rec["borough"] = borough_name
                rec["scope"] = "borough"
            all_recs.extend(recs)
            print(f"           {len(recs)} recs generated")
        except Exception as e:
            print(f"           ERROR: {e}")

        # Incremental save after each borough
        _save_recs(recs_path, all_recs)

    # Final save
    _save_recs(recs_path, all_recs)

    # Summary
    borough_recs = [r for r in all_recs if r.get("scope") == "borough"]
    london_recs_final = [r for r in all_recs if r.get("scope") == "london_wide"]
    print(f"\n{'='*60}")
    print("BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"London-wide: {len(london_recs_final)} recommendations")
    print(f"Borough: {len(borough_recs)} recommendations across {len(set(r['borough'] for r in borough_recs))} boroughs")
    print(f"Total: {len(all_recs)} recommendations")
    print(f"\nSignals:         {signals_path}")
    print(f"Recommendations: {recs_path}")


if __name__ == "__main__":
    main()

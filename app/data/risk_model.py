"""Loneliness Risk Index (LRI) computation engine.

Reads indicator weights from risk_config.yaml, normalises each indicator
to 0-1 via min-max scaling, computes weighted pillar scores, and produces
a final LRI on a 0-10 scale with risk tier labels.
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def _min_max(series: pd.Series) -> pd.Series:
    """Min-max normalise to 0-1, handling constant columns gracefully."""
    smin, smax = series.min(), series.max()
    if smax == smin:
        return pd.Series(0.0, index=series.index)
    return (series - smin) / (smax - smin)


def compute_lri(gdf, config: dict) -> pd.DataFrame:
    """Compute Loneliness Risk Index scores.

    Returns a DataFrame with columns: lri_score, risk_tier, risk_color,
    plus normalised pillar scores and individual indicator values.
    """
    pillars_cfg = config["pillars"]
    tiers_cfg = config["risk_tiers"]

    result = pd.DataFrame(index=gdf.index)
    pillar_scores = {}

    for pillar_name, pillar in pillars_cfg.items():
        indicator_scores = []
        indicator_weights = []

        for ind in pillar["indicators"]:
            col = ind["column"]
            weight = ind["weight"]
            label = ind.get("label", col)

            # Compute raw value (ratio if denominator specified)
            if "denominator" in ind:
                denom = gdf[ind["denominator"]].replace(0, np.nan)
                raw = gdf[col] / denom
            else:
                raw = gdf[col].astype(float)

            # Store raw indicator value for display
            result[f"ind_{col}"] = raw

            # Normalise and accumulate
            normed = _min_max(raw.fillna(0))
            indicator_scores.append(normed * weight)
            indicator_weights.append(weight)

        # Weighted sum within pillar
        pillar_score = sum(indicator_scores)
        pillar_scores[pillar_name] = pillar_score
        result[f"pillar_{pillar_name}"] = pillar_score

    # Final LRI: weighted combination of pillars, scaled to 0-10
    lri_raw = sum(
        pillar_scores[name] * cfg["weight"]
        for name, cfg in pillars_cfg.items()
    )
    result["lri_score"] = (lri_raw * 10).round(2)

    # Assign risk tiers
    def _tier(score):
        for tier_key, t in tiers_cfg.items():
            if t["min"] <= score <= t["max"]:
                return t["label"], t["color"]
        # Fallback for edge cases
        return tiers_cfg["low"]["label"], tiers_cfg["low"]["color"]

    tiers = result["lri_score"].apply(lambda s: _tier(s))
    result["risk_tier"] = tiers.apply(lambda x: x[0])
    result["risk_color"] = tiers.apply(lambda x: x[1])

    return result

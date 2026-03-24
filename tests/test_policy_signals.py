"""Tests for the policy signal computation engine."""

import math

import numpy as np
import pandas as pd
import pytest

from app.data.policy_signals import (
    COL,
    COMPOSITE_WEIGHTS,
    SERVICE_GAP_THRESHOLDS,
    TIER_THRESHOLDS,
    _assign_tier,
    _min_max,
    _slugify,
    compute_borough_aggregates,
    compute_lsoa_signals,
    compute_london_wide,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_lsoa_df(n: int = 20, boroughs: list[str] | None = None) -> pd.DataFrame:
    """Build a synthetic LSOA DataFrame with the columns policy_signals expects."""
    rng = np.random.default_rng(42)

    if boroughs is None:
        boroughs = ["Borough A", "Borough B"]

    rows = []
    for i in range(n):
        borough = boroughs[i % len(boroughs)]
        rows.append({
            COL["lsoa_code"]:          f"E0100{i:04d}",
            COL["lsoa_name"]:          f"Test LSOA {i}",
            COL["borough"]:            borough,
            COL["imd_score"]:          rng.uniform(5, 60),
            COL["imd_decile"]:         rng.integers(1, 11),
            COL["samhi_2022"]:         rng.uniform(-2, 4),
            COL["samhi_2019"]:         rng.uniform(-2, 4),
            COL["geo_barriers"]:       rng.uniform(-1, 3),
            COL["population"]:         rng.integers(1_000, 15_000),
            COL["total_16plus"]:       rng.integers(800, 12_000),
            COL["pop_density"]:        rng.uniform(500, 15_000),
            COL["employment_rate"]:    rng.uniform(50, 90),
            COL["health_bad_pct"]:     rng.uniform(2, 20),
            COL["disability_pct"]:     rng.uniform(5, 30),
            COL["dist_community"]:     rng.uniform(100, 8_000),
            COL["dist_mh_charity"]:    rng.uniform(100, 8_000),
            COL["dist_foodbank"]:      rng.uniform(100, 8_000),
            COL["dist_nhs_therapy"]:   rng.uniform(100, 8_000),
            COL["dist_citizens_advice"]: rng.uniform(100, 8_000),
            COL["dist_cmht"]:          rng.uniform(200, 12_000),
            COL["dist_homelessness"]:  rng.uniform(200, 10_000),
            COL["dist_older_people"]:  rng.uniform(200, 10_000),
            COL["dist_wellbeing_hub"]: rng.uniform(200, 10_000),
            COL["cs_foodbank"]:        rng.integers(0, 5),
            COL["cs_mh_charity"]:      rng.integers(0, 5),
            COL["cs_nhs_therapy"]:     rng.integers(0, 5),
            COL["cs_citizens_advice"]: rng.integers(0, 5),
            COL["cs_cmht"]:           rng.integers(0, 3),
            COL["cs_homelessness"]:    rng.integers(0, 3),
            COL["cs_total"]:           rng.integers(0, 15),
        })

    return pd.DataFrame(rows)


# ── _min_max tests ───────────────────────────────────────────────────────────

class TestMinMax:
    def test_normal_range(self):
        s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = _min_max(s)
        assert result.min() == pytest.approx(0.0)
        assert result.max() == pytest.approx(1.0)
        assert result.iloc[2] == pytest.approx(0.5)

    def test_constant_series(self):
        s = pd.Series([7.0, 7.0, 7.0])
        result = _min_max(s)
        assert (result == 0.0).all()

    def test_single_element(self):
        s = pd.Series([42.0])
        result = _min_max(s)
        assert result.iloc[0] == 0.0

    def test_with_nan_filled(self):
        """NaN values should be handled before calling _min_max (caller fills)."""
        s = pd.Series([1.0, np.nan, 3.0]).fillna(0)
        result = _min_max(s)
        assert result.min() == pytest.approx(0.0)
        assert result.max() == pytest.approx(1.0)

    def test_negative_values(self):
        s = pd.Series([-10.0, 0.0, 10.0])
        result = _min_max(s)
        assert result.iloc[0] == pytest.approx(0.0)
        assert result.iloc[1] == pytest.approx(0.5)
        assert result.iloc[2] == pytest.approx(1.0)


# ── _assign_tier tests ──────────────────────────────────────────────────────

class TestAssignTier:
    def test_critical(self):
        assert _assign_tier(0.75) == "Critical Need"
        assert _assign_tier(0.99) == "Critical Need"
        assert _assign_tier(1.0) == "Critical Need"

    def test_high(self):
        assert _assign_tier(0.50) == "High Need"
        assert _assign_tier(0.74) == "High Need"

    def test_moderate(self):
        assert _assign_tier(0.25) == "Elevated"
        assert _assign_tier(0.49) == "Elevated"

    def test_low(self):
        assert _assign_tier(0.0) == "Lower Need"
        assert _assign_tier(0.24) == "Lower Need"


# ── _slugify tests ───────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert _slugify("City of London") == "city-of-london"

    def test_with_special_chars(self):
        assert _slugify("Barking & Dagenham") == "barking-dagenham"

    def test_whitespace(self):
        assert _slugify("  Tower Hamlets  ") == "tower-hamlets"


# ── compute_lsoa_signals tests ──────────────────────────────────────────────

class TestComputeLsoaSignals:
    @pytest.fixture()
    def signals_df(self):
        df = _make_lsoa_df(50, boroughs=["A", "B", "C"])
        return compute_lsoa_signals(df)

    def test_expected_columns_present(self, signals_df):
        expected = {
            "service_desert_score",
            "mh_trajectory",
            "transport_isolation_score",
            "service_gap_flags",
            "composite_need_score",
            "need_tier",
        }
        assert expected.issubset(set(signals_df.columns))

    def test_service_desert_range(self, signals_df):
        assert signals_df["service_desert_score"].min() >= 0.0
        assert signals_df["service_desert_score"].max() <= 1.0

    def test_transport_isolation_range(self, signals_df):
        assert signals_df["transport_isolation_score"].min() >= 0.0
        assert signals_df["transport_isolation_score"].max() <= 1.0

    def test_composite_need_range(self, signals_df):
        assert signals_df["composite_need_score"].min() >= 0.0 - 1e-9
        assert signals_df["composite_need_score"].max() <= 1.0 + 1e-9

    def test_valid_tiers(self, signals_df):
        valid_tiers = {t["label"] for t in TIER_THRESHOLDS.values()}
        assert set(signals_df["need_tier"].unique()).issubset(valid_tiers)

    def test_service_gap_flags_range(self, signals_df):
        # Bitmask with 5 bits → max value 0b11111 = 31
        assert signals_df["service_gap_flags"].min() >= 0
        assert signals_df["service_gap_flags"].max() <= 31

    def test_no_nulls_in_computed_cols(self, signals_df):
        computed_cols = [
            "service_desert_score",
            "mh_trajectory",
            "transport_isolation_score",
            "service_gap_flags",
            "composite_need_score",
            "need_tier",
        ]
        for col in computed_cols:
            assert signals_df[col].isna().sum() == 0, f"NaN found in {col}"

    def test_handles_null_imd(self):
        """LSOAs with null IMD decile should be filled with median, not crash."""
        df = _make_lsoa_df(10)
        df.loc[0:2, COL["imd_decile"]] = np.nan
        df.loc[0:2, COL["imd_score"]] = np.nan
        result = compute_lsoa_signals(df)
        assert result["composite_need_score"].isna().sum() == 0

    def test_handles_null_samhi(self):
        """LSOAs with null SAMHI should be filled with 0."""
        df = _make_lsoa_df(10)
        df.loc[0:3, COL["samhi_2022"]] = np.nan
        df.loc[0:3, COL["samhi_2019"]] = np.nan
        result = compute_lsoa_signals(df)
        assert result["mh_trajectory"].isna().sum() == 0


# ── compute_borough_aggregates tests ─────────────────────────────────────────

class TestComputeBoroughAggregates:
    @pytest.fixture()
    def borough_data(self):
        df = _make_lsoa_df(40, boroughs=["Camden", "Hackney", "Tower Hamlets"])
        df = compute_lsoa_signals(df)
        return compute_borough_aggregates(df)

    def test_correct_borough_keys(self, borough_data):
        assert set(borough_data.keys()) == {"Camden", "Hackney", "Tower Hamlets"}

    def test_structure(self, borough_data):
        for name, info in borough_data.items():
            assert info["borough_name"] == name
            assert isinstance(info["borough_slug"], str)
            assert isinstance(info["lsoa_count"], int)
            assert info["lsoa_count"] > 0
            assert isinstance(info["tier_counts"], dict)
            assert isinstance(info["mean_composite_need"], float)
            assert isinstance(info["max_composite_need"], float)
            assert isinstance(info["service_coverage"], dict)
            assert isinstance(info["top_5_lsoas"], list)
            assert len(info["top_5_lsoas"]) <= 5

    def test_lsoa_counts_sum(self, borough_data):
        total = sum(b["lsoa_count"] for b in borough_data.values())
        assert total == 40  # matches input

    def test_slugs(self, borough_data):
        assert borough_data["Camden"]["borough_slug"] == "camden"
        assert borough_data["Tower Hamlets"]["borough_slug"] == "tower-hamlets"

    def test_trajectory_labels(self, borough_data):
        valid_labels = {"worsening", "improving", "stable"}
        for info in borough_data.values():
            assert info["mh_trajectory"] in valid_labels

    def test_service_coverage_keys(self, borough_data):
        for info in borough_data.values():
            expected_services = {
                "foodbank", "mh_charity", "nhs_therapy",
                "citizens_advice", "cmht", "homelessness",
            }
            assert set(info["service_coverage"].keys()) == expected_services
            for svc_info in info["service_coverage"].values():
                assert "lsoas_with_service" in svc_info
                assert "mean_dist_m" in svc_info
                assert "lsoas_beyond_threshold" in svc_info


# ── compute_london_wide tests ────────────────────────────────────────────────

class TestComputeLondonWide:
    def test_structure(self):
        df = _make_lsoa_df(30, boroughs=["A", "B", "C"])
        df = compute_lsoa_signals(df)
        boroughs = compute_borough_aggregates(df)
        london = compute_london_wide(df, boroughs)

        assert london["total_lsoas"] == 30
        assert isinstance(london["tier_counts"], dict)
        assert isinstance(london["trajectory_summary"], dict)
        assert isinstance(london["top_10_boroughs"], list)
        assert len(london["top_10_boroughs"]) <= 10

    def test_tier_counts_sum(self):
        df = _make_lsoa_df(30)
        df = compute_lsoa_signals(df)
        boroughs = compute_borough_aggregates(df)
        london = compute_london_wide(df, boroughs)
        assert sum(london["tier_counts"].values()) == 30

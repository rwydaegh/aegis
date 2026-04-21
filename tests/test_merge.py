"""Tests for the merge pipeline: operator normalization, spatial dedup, field priority."""

import numpy as np
import pandas as pd

from aegis.basestation.merge import (
    estimate_with_provenance,
    merge_sources,
    normalize_operator,
    spatial_dedup,
)


class TestNormalizeOperator:
    def test_lowercase_strip(self):
        assert normalize_operator("  Proximus  ") == "proximus"

    def test_known_alias(self):
        assert normalize_operator("BE:PROXIMUS") == "proximus"

    def test_unknown_passthrough(self):
        assert normalize_operator("SomeNewOp") == "somenewop"

    def test_none_returns_unknown(self):
        assert normalize_operator(None) == "unknown"

    def test_empty_returns_unknown(self):
        assert normalize_operator("") == "unknown"

    def test_float_nan_returns_unknown(self):
        assert normalize_operator(float("nan")) == "unknown"

    def test_pd_na_returns_unknown(self):
        assert normalize_operator(pd.NA) == "unknown"

    def test_numpy_nan_returns_unknown(self):
        import numpy as np

        assert normalize_operator(np.nan) == "unknown"


class TestSpatialDedup:
    def test_nearby_same_operator_same_band_merges(self):
        df = pd.DataFrame(
            {
                "SiteCode": ["S1", "S2"],
                "AntennaLabel": ["A1", "A2"],
                "Operator": ["Proximus", "Proximus"],
                "Technology": ["5G", "5G"],
                "Latitude": [50.850000, 50.850001],
                "Longitude": [4.350000, 4.350001],
                "CenterHeight": [25.0, np.nan],
                "Power": [46.0, np.nan],
                "Frequency": [3500.0, 3500.0],
                "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
                "Electrical_Tilt": [np.nan, np.nan],
                "Mechanical_Tilt": [np.nan, np.nan],
                "Azimuth": [120, np.nan],
                "Gain": [18.0, np.nan],
                "Horizontal_Beamwidth": [np.nan, np.nan],
                "Vertical_Beamwidth": [np.nan, np.nan],
            }
        )
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 1

    def test_far_apart_does_not_merge(self):
        df = pd.DataFrame(
            {
                "SiteCode": ["S1", "S2"],
                "AntennaLabel": ["A1", "A2"],
                "Operator": ["Proximus", "Proximus"],
                "Technology": ["5G", "5G"],
                "Latitude": [50.850, 50.860],
                "Longitude": [4.350, 4.350],
                "CenterHeight": [25.0, 30.0],
                "Power": [46.0, 42.0],
                "Frequency": [3500.0, 3500.0],
                "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
                "Electrical_Tilt": [6, 4],
                "Mechanical_Tilt": [0, 0],
                "Azimuth": [120, 240],
                "Gain": [18.0, 15.0],
                "Horizontal_Beamwidth": [65, 65],
                "Vertical_Beamwidth": [10, 12],
            }
        )
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2

    def test_different_operator_does_not_merge(self):
        df = pd.DataFrame(
            {
                "SiteCode": ["S1", "S2"],
                "AntennaLabel": ["A1", "A2"],
                "Operator": ["Proximus", "Orange"],
                "Technology": ["5G", "5G"],
                "Latitude": [50.850000, 50.850001],
                "Longitude": [4.350000, 4.350001],
                "CenterHeight": [25.0, 30.0],
                "Power": [46.0, 42.0],
                "Frequency": [3500.0, 3500.0],
                "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
                "Electrical_Tilt": [6, 4],
                "Mechanical_Tilt": [0, 0],
                "Azimuth": [120, 240],
                "Gain": [18.0, 15.0],
                "Horizontal_Beamwidth": [65, 65],
                "Vertical_Beamwidth": [10, 12],
            }
        )
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2

    def test_different_band_does_not_merge(self):
        df = pd.DataFrame(
            {
                "SiteCode": ["S1", "S2"],
                "AntennaLabel": ["A1", "A2"],
                "Operator": ["Proximus", "Proximus"],
                "Technology": ["5G", "4G"],
                "Latitude": [50.850000, 50.850001],
                "Longitude": [4.350000, 4.350001],
                "CenterHeight": [25.0, 30.0],
                "Power": [46.0, 42.0],
                "Frequency": [3500.0, 1800.0],
                "FrequencyBand": ["Band3600MHz", "Band1800MHz"],
                "Electrical_Tilt": [6, 4],
                "Mechanical_Tilt": [0, 0],
                "Azimuth": [120, 240],
                "Gain": [18.0, 15.0],
                "Horizontal_Beamwidth": [65, 65],
                "Vertical_Beamwidth": [10, 12],
            }
        )
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2

    def test_different_bands_do_not_merge_via_nan_bridge(self):
        """A NaN-band seed must not merge two rows with distinct known bands.

        Regression: when the seed had a missing FrequencyBand, the BFS compared
        against the seed only, so neighbours with explicitly different bands
        (e.g. 1800 and 2100) could both join the same cluster and one band was
        silently lost during merge.
        """
        df = pd.DataFrame(
            {
                "SiteCode": ["A", "B", "C"],
                "AntennaLabel": ["x", "x", "x"],
                "Operator": ["Proximus"] * 3,
                "Technology": ["5G"] * 3,
                "Latitude": [50.850000, 50.850002, 50.849998],
                "Longitude": [4.350000, 4.350001, 4.349999],
                "FrequencyBand": [np.nan, "Band1800MHz", "Band2100MHz"],
                "Power": [46.0, 44.0, 42.0],
            }
        )
        result = spatial_dedup(df, distance_m=50)
        bands = set(result["FrequencyBand"].dropna().tolist())
        assert {"Band1800MHz", "Band2100MHz"}.issubset(bands)
        assert len(result) >= 2


class TestMergeSources:
    def test_higher_priority_fills_nan(self):
        gov = pd.DataFrame(
            {
                "SiteCode": ["S1"],
                "AntennaLabel": ["A1"],
                "Operator": ["Proximus"],
                "Technology": ["5G"],
                "Latitude": [50.85],
                "Longitude": [4.35],
                "CenterHeight": [25.0],
                "Power": [46.0],
                "Frequency": [3500.0],
                "FrequencyBand": ["Band3600MHz"],
                "Electrical_Tilt": [pd.NA],
                "Mechanical_Tilt": [pd.NA],
                "Azimuth": [120],
                "Gain": [pd.NA],
                "Horizontal_Beamwidth": [pd.NA],
                "Vertical_Beamwidth": [pd.NA],
            }
        )
        ocid = pd.DataFrame(
            {
                "SiteCode": ["S2"],
                "AntennaLabel": ["A2"],
                "Operator": ["Proximus"],
                "Technology": ["5G"],
                "Latitude": [50.850001],
                "Longitude": [4.350001],
                "CenterHeight": [pd.NA],
                "Power": [pd.NA],
                "Frequency": [3500.0],
                "FrequencyBand": ["Band3600MHz"],
                "Electrical_Tilt": [pd.NA],
                "Mechanical_Tilt": [pd.NA],
                "Azimuth": [pd.NA],
                "Gain": [pd.NA],
                "Horizontal_Beamwidth": [pd.NA],
                "Vertical_Beamwidth": [pd.NA],
            }
        )
        sources = [(gov, "gov:brussels", 1), (ocid, "ocid", 3)]
        result = merge_sources(sources, distance_m=50)
        assert len(result) == 1
        assert result["Power_source"].iloc[0] == "gov:brussels"
        assert result["Azimuth_source"].iloc[0] == "gov:brussels"

    def test_lower_priority_fill_updates_source(self):
        """When a high-priority row has NaN and a low-priority row fills the value,
        the companion ``*_source`` column must track the actual origin, not stay
        at the first row's "missing" tag. Otherwise fidelity_tier collapses to
        ``location_only`` for rows that actually have every field populated.
        """
        gov = pd.DataFrame(
            {
                "SiteCode": ["S1"],
                "AntennaLabel": ["A1"],
                "Operator": ["Proximus"],
                "Technology": ["5G"],
                "Latitude": [50.85],
                "Longitude": [4.35],
                "Power": [np.nan],
                "FrequencyBand": ["Band3600MHz"],
            }
        )
        ocid = pd.DataFrame(
            {
                "SiteCode": ["S2"],
                "AntennaLabel": ["A2"],
                "Operator": ["Proximus"],
                "Technology": ["5G"],
                "Latitude": [50.850001],
                "Longitude": [4.350001],
                "Power": [42.0],
                "FrequencyBand": ["Band3600MHz"],
            }
        )
        sources = [(gov, "gov:brussels", 1), (ocid, "ocid", 3)]
        result = merge_sources(sources, distance_m=50)
        assert len(result) == 1
        assert result["Power"].iloc[0] == 42.0
        assert result["Power_source"].iloc[0] == "ocid"


class TestEstimateWithProvenance:
    def test_fills_nan_with_estimation_tag(self):
        df = pd.DataFrame(
            {
                "SiteCode": ["S1", "S2"],
                "AntennaLabel": ["A1", "A2"],
                "Operator": ["Proximus", "Proximus"],
                "Technology": ["5G", "5G"],
                "Latitude": [50.85, 50.86],
                "Longitude": [4.35, 4.36],
                "CenterHeight": [25.0, 30.0],
                "Power": [46.0, np.nan],
                "Frequency": [3500.0, 3500.0],
                "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
                "Electrical_Tilt": [6, np.nan],
                "Mechanical_Tilt": [0, np.nan],
                "Azimuth": [120, 240],
                "Gain": [18.0, np.nan],
                "Horizontal_Beamwidth": [65, np.nan],
                "Vertical_Beamwidth": [10, np.nan],
                "Power_source": ["gov:brussels", "missing"],
                "Azimuth_source": ["gov:brussels", "gov:brussels"],
                "Gain_source": ["gov:brussels", "missing"],
                "CenterHeight_source": ["gov:brussels", "gov:brussels"],
                "Frequency_source": ["gov:brussels", "gov:brussels"],
                "FrequencyBand_source": ["gov:brussels", "gov:brussels"],
                "Electrical_Tilt_source": ["gov:brussels", "missing"],
                "Mechanical_Tilt_source": ["gov:brussels", "missing"],
                "Horizontal_Beamwidth_source": ["gov:brussels", "missing"],
                "Vertical_Beamwidth_source": ["gov:brussels", "missing"],
                "Pattern_source": ["", ""],
            }
        )
        result = estimate_with_provenance(df)
        assert not pd.isna(result["Power"].iloc[1])
        assert result["Power_source"].iloc[1] == "est:tech+band"

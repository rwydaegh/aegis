"""Integration tests for realistic exposure pipeline."""

import numpy as np
import pandas as pd
import pytest

from aegis.basestation.adapter import load_basestations_from_df, paths_from_basestations
from aegis.basestation.exposure import ExposureMode


@pytest.fixture
def mixed_basestations():
    """A mix of 4G and 5G base stations."""
    df = pd.DataFrame(
        [
            {
                "SiteCode": "S1",
                "AntennaLabel": "5G_mmimo",
                "Operator": "Op",
                "Technology": "5G NR",
                "Latitude": 50.85,
                "Longitude": 4.35,
                "CenterHeight": 30,
                "Power": 62,
                "Gain": 25,
                "Frequency": 3500,
                "Azimuth": 0,
                "Electrical_Tilt": 6,
                "Mechanical_Tilt": 0,
                "Horizontal_Beamwidth": 12,
                "Vertical_Beamwidth": 10,
            },
            {
                "SiteCode": "S1",
                "AntennaLabel": "4G_sector",
                "Operator": "Op",
                "Technology": "4G LTE",
                "Latitude": 50.85,
                "Longitude": 4.35,
                "CenterHeight": 28,
                "Power": 50,
                "Gain": 17,
                "Frequency": 1800,
                "Azimuth": 120,
                "Electrical_Tilt": 6,
                "Mechanical_Tilt": 0,
                "Horizontal_Beamwidth": 65,
                "Vertical_Beamwidth": 10,
            },
        ]
    )
    return load_basestations_from_df(df)


class TestExposureIntegration:
    def test_5g_has_tdd_ratio(self, mixed_basestations):
        bs_5g = [b for b in mixed_basestations if "5G" in b.technology][0]
        assert bs_5g.tdd_dl_ratio == pytest.approx(0.75, abs=0.01)

    def test_4g_has_unity_ratio(self, mixed_basestations):
        bs_4g = [b for b in mixed_basestations if "4G" in b.technology][0]
        assert bs_4g.tdd_dl_ratio == 1.0

    def test_5g_has_sidelobe_floor(self, mixed_basestations):
        bs_5g = [b for b in mixed_basestations if "5G" in b.technology][0]
        assert bs_5g.sidelobe_suppression_db is not None
        pat = bs_5g.pattern
        assert pat is not None
        min_gain = np.nanmin(pat.gain_dbi)
        assert min_gain >= 25.0 - bs_5g.sidelobe_suppression_db - 1.0

    def test_actual_max_reduces_total_power(self, mixed_basestations):
        origin = (50.85, 4.35)
        body = np.array([10.0, 0.0, 1.5])
        p_theo = paths_from_basestations(mixed_basestations, body, origin).total_power
        p_actual = paths_from_basestations(
            mixed_basestations, body, origin, exposure_mode=ExposureMode.ACTUAL_MAX
        ).total_power
        assert p_actual < p_theo

    def test_typical_less_than_actual_max(self, mixed_basestations):
        origin = (50.85, 4.35)
        body = np.array([10.0, 0.0, 1.5])
        p_actual = paths_from_basestations(
            mixed_basestations, body, origin, exposure_mode=ExposureMode.ACTUAL_MAX
        ).total_power
        p_typical = paths_from_basestations(
            mixed_basestations, body, origin, exposure_mode=ExposureMode.TYPICAL
        ).total_power
        assert p_typical < p_actual

    def test_theoretical_max_preserves_backward_compat(self, mixed_basestations):
        origin = (50.85, 4.35)
        body = np.array([10.0, 0.0, 1.5])
        p_default = paths_from_basestations(mixed_basestations, body, origin).total_power
        p_theo = paths_from_basestations(
            mixed_basestations, body, origin, exposure_mode=ExposureMode.THEORETICAL_MAX
        ).total_power
        assert p_theo == pytest.approx(p_default, rel=1e-6)

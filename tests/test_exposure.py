"""Tests for ExposureMode enum, TDD lookup, and power reduction factors."""

import pytest

from aegis.basestation.exposure import (
    ExposureMode,
    MimoBeamParams,
    lookup_mimo_beam_params,
    lookup_prf,
    lookup_tdd_dl_ratio,
    power_reduction_factor,
)


class TestExposureMode:
    """ExposureMode enum values and string conversion."""

    def test_enum_values(self):
        assert ExposureMode.THEORETICAL_MAX.value == "theoretical_max"
        assert ExposureMode.ACTUAL_MAX.value == "actual_max"
        assert ExposureMode.TYPICAL.value == "typical"

    def test_from_string(self):
        assert ExposureMode("theoretical_max") is ExposureMode.THEORETICAL_MAX
        assert ExposureMode("actual_max") is ExposureMode.ACTUAL_MAX
        assert ExposureMode("typical") is ExposureMode.TYPICAL

    def test_invalid_string(self):
        with pytest.raises(ValueError):
            ExposureMode("unknown_mode")


class TestTddLookup:
    """TDD downlink duty cycle lookup table."""

    def test_5g_sub6_n77_n78(self):
        assert lookup_tdd_dl_ratio("5G", 3500.0) == 0.75

    def test_5g_sub6_n78_upper(self):
        assert lookup_tdd_dl_ratio("5G", 3800.0) == 0.75

    def test_5g_mmwave(self):
        assert lookup_tdd_dl_ratio("5G", 28000.0) == 0.72

    def test_4g_fdd_1800(self):
        # 4G at 1800 MHz is FDD -> 1.0
        assert lookup_tdd_dl_ratio("4G", 1800.0) == 1.0

    def test_3g_2100(self):
        assert lookup_tdd_dl_ratio("3G", 2100.0) == 1.0

    def test_2g_900(self):
        assert lookup_tdd_dl_ratio("2G", 900.0) == 1.0

    def test_unknown_technology(self):
        assert lookup_tdd_dl_ratio("unknown", 1000.0) == 1.0

    def test_technology_normalization_5g_nr(self):
        assert lookup_tdd_dl_ratio("5G NR", 3500.0) == 0.75

    def test_technology_normalization_lte(self):
        # LTE at 1800 MHz is FDD -> 1.0
        assert lookup_tdd_dl_ratio("LTE", 1800.0) == 1.0

    def test_technology_normalization_umts(self):
        assert lookup_tdd_dl_ratio("UMTS", 2100.0) == 1.0

    def test_technology_normalization_gsm(self):
        assert lookup_tdd_dl_ratio("GSM", 900.0) == 1.0

    def test_5g_tdd_n41(self):
        # n41: 2496-2690 MHz
        assert lookup_tdd_dl_ratio("5G", 2500.0) == 0.75

    def test_4g_tdd_b40(self):
        # B40: 2570-2620 MHz
        assert lookup_tdd_dl_ratio("4G", 2600.0) == 0.60

    def test_4g_tdd_b42(self):
        # B42/B43: 3400-3600 MHz
        assert lookup_tdd_dl_ratio("4G", 3500.0) == 0.60

    def test_4g_tdd_b38(self):
        # B38: 2300-2400 MHz
        assert lookup_tdd_dl_ratio("4G", 2350.0) == 0.60


class TestPrf:
    """Power reduction factor for beam scanning (mMIMO only)."""

    def test_5g_mmimo_sub6(self):
        # 5G with gain >= 20 dBi at sub-6 GHz
        assert lookup_prf("5G", 3500.0, gain_dbi=25.0) == pytest.approx(0.32)

    def test_4g_sector_antenna(self):
        # 4G is never mMIMO
        assert lookup_prf("4G", 1800.0, gain_dbi=18.0) == 1.0

    def test_5g_low_gain_not_mmimo(self):
        # 5G but gain < 20 dBi is not mMIMO
        assert lookup_prf("5G", 3500.0, gain_dbi=15.0) == 1.0

    def test_5g_mmwave_mmimo(self):
        # 5G mmWave mMIMO
        assert lookup_prf("5G", 28000.0, gain_dbi=27.0) == pytest.approx(0.30)


class TestPowerReductionFactor:
    """Combined power reduction factor per exposure mode."""

    def test_theoretical_max_always_one(self):
        assert power_reduction_factor(ExposureMode.THEORETICAL_MAX, "5G", 3500.0, gain_dbi=25.0) == pytest.approx(1.0)

    def test_actual_max_5g_mmimo(self):
        # tdd=0.75, prf=0.32 -> 0.24
        result = power_reduction_factor(ExposureMode.ACTUAL_MAX, "5G", 3500.0, gain_dbi=25.0)
        assert result == pytest.approx(0.75 * 0.32, rel=1e-6)

    def test_actual_max_4g_fdd(self):
        # tdd=1.0, prf=1.0 -> 1.0
        result = power_reduction_factor(ExposureMode.ACTUAL_MAX, "4G", 1800.0, gain_dbi=18.0)
        assert result == pytest.approx(1.0)

    def test_typical_5g_mmimo(self):
        # tdd=0.75, prf=0.32, traffic=0.5 -> 0.12
        result = power_reduction_factor(ExposureMode.TYPICAL, "5G", 3500.0, gain_dbi=25.0)
        assert result == pytest.approx(0.75 * 0.32 * 0.5, rel=1e-6)

    def test_typical_4g_fdd(self):
        # tdd=1.0, prf=1.0, traffic=0.5 -> 0.5
        result = power_reduction_factor(ExposureMode.TYPICAL, "4G", 1800.0, gain_dbi=18.0)
        assert result == pytest.approx(0.5)


class TestMimoBeamParams:
    """MIMO beam parameter lookup."""

    def test_5g_sub6_3500(self):
        params = lookup_mimo_beam_params("5G", 3500.0, gain_dbi=25.0)
        assert params is not None
        assert isinstance(params, MimoBeamParams)
        assert params.broadcast_gain_dbi == pytest.approx(18.0)
        assert params.broadcast_hpbw_h_deg == pytest.approx(65.0)
        assert params.broadcast_hpbw_v_deg == pytest.approx(5.5)
        assert params.traffic_gain_dbi == pytest.approx(25.0)
        assert params.traffic_hpbw_h_deg == pytest.approx(12.0)
        assert params.traffic_hpbw_v_deg == pytest.approx(10.0)
        assert params.h_sweep_range_deg == pytest.approx(60.0)
        assert params.v_sweep_range_deg == pytest.approx(15.0)
        assert params.sidelobe_suppression_db == pytest.approx(15.0)

    def test_4g_returns_none(self):
        params = lookup_mimo_beam_params("4G", 1800.0, gain_dbi=18.0)
        assert params is None

    def test_5g_mmwave_params(self):
        params = lookup_mimo_beam_params("5G", 28000.0, gain_dbi=27.0)
        assert params is not None
        assert params.broadcast_gain_dbi == pytest.approx(20.0)
        assert params.broadcast_hpbw_h_deg == pytest.approx(90.0)
        assert params.broadcast_hpbw_v_deg == pytest.approx(30.0)
        assert params.traffic_gain_dbi == pytest.approx(27.0)
        assert params.traffic_hpbw_h_deg == pytest.approx(5.0)
        assert params.traffic_hpbw_v_deg == pytest.approx(8.0)
        assert params.h_sweep_range_deg == pytest.approx(60.0)
        assert params.v_sweep_range_deg == pytest.approx(15.0)
        assert params.sidelobe_suppression_db == pytest.approx(20.0)

    def test_5g_low_gain_returns_none(self):
        # Low gain 5G is not mMIMO
        params = lookup_mimo_beam_params("5G", 3500.0, gain_dbi=15.0)
        assert params is None

    def test_frozen_dataclass(self):
        params = lookup_mimo_beam_params("5G", 3500.0, gain_dbi=25.0)
        assert params is not None
        with pytest.raises((AttributeError, TypeError)):
            params.broadcast_gain_dbi = 99.0  # type: ignore[misc]

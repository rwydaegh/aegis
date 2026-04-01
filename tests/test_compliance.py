"""Tests for ICNIRP 2020 compliance module."""

import math

import numpy as np
import pytest

from aegis.compliance import (
    ICNIRP_2020,
    ComplianceCheck,
    ComplianceResult,
    ExposureScenario,
    compliance_heatmap,
    evaluate_compliance,
    icnirp_limits,
    is_compliant_sab,
    is_compliant_sar,
    link_budget_compliance,
    margin_db,
    max_compliant_power,
    power_sweep,
    summary_text,
)

# -----------------------------------------------------------------------
# icnirp_limits: general public
# -----------------------------------------------------------------------


class TestICNIRPLimitsGeneralPublic:
    """Verify ICNIRP 2020 Table 2/5/6 limits for general public."""

    def test_sab_4cm2(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        assert lim.sab_4cm2 == 20.0

    def test_sab_1cm2_below_30ghz_is_none(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 10.0e9)
        assert lim.sab_1cm2 is None

    def test_sab_1cm2_at_30ghz_is_none(self) -> None:
        """At exactly 30 GHz, 1 cm^2 limit should not apply (only >30 GHz)."""
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 30.0e9)
        assert lim.sab_1cm2 is None

    def test_sab_1cm2_above_30ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 60.0e9)
        assert lim.sab_1cm2 == 40.0

    def test_sar_wb(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        assert lim.sar_wb == 0.08

    def test_sinc_whole_body(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        assert lim.sinc_whole_body == 10.0

    def test_sinc_local_formula(self) -> None:
        """S_inc local = 55 / f_GHz^0.177 for general public (Table 6)."""
        freq_hz = 28.0e9
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, freq_hz)
        expected = 55.0 / (28.0**0.177)
        assert lim.sinc_local == pytest.approx(expected, rel=1e-10)

    def test_sinc_local_varies_with_frequency(self) -> None:
        lim_10 = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 10.0e9)
        lim_100 = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 100.0e9)
        # Higher frequency should give lower local limit
        assert lim_100.sinc_local < lim_10.sinc_local

    def test_scenario_stored(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        assert lim.scenario == ExposureScenario.GENERAL_PUBLIC

    def test_freq_stored(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        assert lim.freq_hz == 28.0e9


# -----------------------------------------------------------------------
# icnirp_limits: occupational
# -----------------------------------------------------------------------


class TestICNIRPLimitsOccupational:
    """Verify ICNIRP 2020 limits for occupational scenario."""

    def test_sab_4cm2(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28.0e9)
        assert lim.sab_4cm2 == 100.0

    def test_sab_1cm2_below_30ghz_is_none(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 10.0e9)
        assert lim.sab_1cm2 is None

    def test_sab_1cm2_above_30ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 60.0e9)
        assert lim.sab_1cm2 == 200.0

    def test_sar_wb(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28.0e9)
        assert lim.sar_wb == 0.4

    def test_sinc_whole_body(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28.0e9)
        assert lim.sinc_whole_body == 50.0

    def test_sinc_local_formula(self) -> None:
        """S_inc local = 275 / f_GHz^0.177 for occupational (Table 6)."""
        freq_hz = 28.0e9
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, freq_hz)
        expected = 275.0 / (28.0**0.177)
        assert lim.sinc_local == pytest.approx(expected, rel=1e-10)

    def test_occupational_5x_general_public(self) -> None:
        """Occupational limits are 5x general public for sab and sinc."""
        gp = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28.0e9)
        oc = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28.0e9)
        assert oc.sab_4cm2 == 5 * gp.sab_4cm2
        assert oc.sar_wb == 5 * gp.sar_wb
        assert oc.sinc_local == pytest.approx(5 * gp.sinc_local, rel=1e-10)
        assert oc.sinc_whole_body == 5 * gp.sinc_whole_body


# -----------------------------------------------------------------------
# Frequency validation
# -----------------------------------------------------------------------


class TestFrequencyValidation:
    """Frequency must be >= 100 kHz and <= 300 GHz."""

    def test_at_6ghz_returns_sar_only(self) -> None:
        lim = icnirp_limits(freq_hz=6.0e9)
        assert lim.sar_wb == 0.08
        assert lim.sab_4cm2 is None
        assert lim.sinc_local is None

    def test_sub6ghz_returns_sar_only(self) -> None:
        lim = icnirp_limits(freq_hz=3.5e9)
        assert lim.sar_wb == 0.08
        assert lim.sab_4cm2 is None
        assert lim.sinc_local is None
        assert lim.sinc_whole_body is None

    def test_below_100khz_raises(self) -> None:
        with pytest.raises(ValueError):
            icnirp_limits(freq_hz=50.0e3)

    def test_above_300ghz_raises(self) -> None:
        with pytest.raises(ValueError):
            icnirp_limits(freq_hz=301.0e9)

    def test_at_300ghz_ok(self) -> None:
        lim = icnirp_limits(freq_hz=300.0e9)
        assert lim.freq_hz == 300.0e9

    def test_just_above_6ghz_ok(self) -> None:
        lim = icnirp_limits(freq_hz=6.001e9)
        assert lim.freq_hz == 6.001e9

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            icnirp_limits(freq_hz=0.0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            icnirp_limits(freq_hz=-10.0e9)


# -----------------------------------------------------------------------
# ComplianceCheck
# -----------------------------------------------------------------------


class TestComplianceCheck:
    """Test ComplianceCheck properties."""

    def test_pass_at_limit(self) -> None:
        """Value exactly equal to limit should pass (<=)."""
        c = ComplianceCheck(value=20.0, limit=20.0, unit="W/m^2", label="test")
        assert c.compliant is True

    def test_pass_below_limit(self) -> None:
        c = ComplianceCheck(value=10.0, limit=20.0, unit="W/m^2", label="test")
        assert c.compliant is True

    def test_fail_above_limit(self) -> None:
        c = ComplianceCheck(value=20.01, limit=20.0, unit="W/m^2", label="test")
        assert c.compliant is False

    def test_margin_db_positive_when_compliant(self) -> None:
        c = ComplianceCheck(value=2.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == pytest.approx(10.0)

    def test_margin_db_zero_at_limit(self) -> None:
        c = ComplianceCheck(value=20.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == pytest.approx(0.0)

    def test_margin_db_negative_when_exceeded(self) -> None:
        c = ComplianceCheck(value=200.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == pytest.approx(-10.0)

    def test_margin_db_inf_when_value_zero(self) -> None:
        c = ComplianceCheck(value=0.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == float("inf")

    def test_ratio_below_one_when_compliant(self) -> None:
        c = ComplianceCheck(value=10.0, limit=20.0, unit="W/m^2", label="test")
        assert c.ratio == pytest.approx(0.5)

    def test_ratio_one_at_limit(self) -> None:
        c = ComplianceCheck(value=20.0, limit=20.0, unit="W/m^2", label="test")
        assert c.ratio == pytest.approx(1.0)

    def test_ratio_above_one_when_exceeded(self) -> None:
        c = ComplianceCheck(value=40.0, limit=20.0, unit="W/m^2", label="test")
        assert c.ratio == pytest.approx(2.0)


# -----------------------------------------------------------------------
# evaluate_compliance
# -----------------------------------------------------------------------


class TestEvaluateCompliance:
    """Test evaluate_compliance function."""

    def test_all_pass(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            sab_4cm2=10.0,
            sar_wb=0.04,
            sinc_local=20.0,
            sinc_whole_body=5.0,
        )
        assert r.overall_pass is True
        assert r.margin_db > 0

    def test_one_fail_makes_overall_fail(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            sab_4cm2=25.0,  # exceeds 20 W/m^2
            sar_wb=0.04,
        )
        assert r.overall_pass is False

    def test_1cm2_included_above_30ghz(self) -> None:
        r = evaluate_compliance(
            freq_hz=60.0e9,
            sab_4cm2=10.0,
            sab_1cm2=30.0,
        )
        assert r.sab_1cm2 is not None
        assert r.sab_1cm2.limit == 40.0
        assert r.sab_1cm2.compliant is True

    def test_1cm2_ignored_at_30ghz(self) -> None:
        """Even if sab_1cm2 value is provided, it should be None at 30 GHz."""
        r = evaluate_compliance(
            freq_hz=30.0e9,
            sab_4cm2=10.0,
            sab_1cm2=50.0,  # would fail if checked, but should be ignored
        )
        assert r.sab_1cm2 is None

    def test_margin_is_tightest_check(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            sab_4cm2=18.0,  # close to 20 -> small margin
            sar_wb=0.001,  # far from 0.08 -> large margin
        )
        # sab margin should be tighter
        assert r.margin_db == pytest.approx(r.sab_4cm2.margin_db)
        assert r.margin_db < r.sar_wb.margin_db

    def test_none_values_omit_checks(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            sab_4cm2=10.0,
        )
        assert r.sab_4cm2 is not None
        assert r.sar_wb is None
        assert r.sinc_local is None
        assert r.sinc_whole_body is None
        assert len(r.all_checks) == 1

    def test_no_checks_overall_pass(self) -> None:
        """With no values, overall_pass is vacuously True."""
        r = evaluate_compliance(freq_hz=28.0e9)
        assert r.overall_pass is True
        assert r.margin_db == float("inf")

    def test_occupational_scenario(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            scenario=ExposureScenario.OCCUPATIONAL,
            sab_4cm2=50.0,
        )
        # 50 < 100 -> pass for occupational, would fail for general public
        assert r.overall_pass is True
        assert r.scenario == ExposureScenario.OCCUPATIONAL

    def test_frequency_stored(self) -> None:
        r = evaluate_compliance(freq_hz=28.0e9, sab_4cm2=10.0)
        assert r.freq_hz == 28.0e9

    def test_sub6ghz_sar_only(self) -> None:
        r = evaluate_compliance(freq_hz=3.5e9, sab_4cm2=10.0, sar_wb=0.05)
        assert r.sar_wb is not None
        assert r.sar_wb.compliant
        assert r.sab_4cm2 is None
        assert r.sinc_local is None

    def test_invalid_freq_raises(self) -> None:
        with pytest.raises(ValueError):
            evaluate_compliance(freq_hz=50.0e3, sab_4cm2=10.0)


# -----------------------------------------------------------------------
# Standalone margin_db
# -----------------------------------------------------------------------


class TestMarginDb:
    """Test standalone margin_db function."""

    def test_positive_margin(self) -> None:
        assert margin_db(2.0, 20.0) == pytest.approx(10.0)

    def test_zero_margin(self) -> None:
        assert margin_db(20.0, 20.0) == pytest.approx(0.0)

    def test_negative_margin(self) -> None:
        assert margin_db(200.0, 20.0) == pytest.approx(-10.0)

    def test_zero_value_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            margin_db(0.0, 20.0)

    def test_negative_value_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            margin_db(-1.0, 20.0)

    def test_known_value(self) -> None:
        """1 W/m^2 vs 20 W/m^2 limit -> 10*log10(20) dB."""
        assert margin_db(1.0, 20.0) == pytest.approx(10.0 * math.log10(20.0))


# -----------------------------------------------------------------------
# summary_text
# -----------------------------------------------------------------------


class TestSummaryText:
    """Test summary_text function."""

    def test_pass_output(self) -> None:
        r = evaluate_compliance(freq_hz=28.0e9, sab_4cm2=10.0)
        text = summary_text(r)
        assert "PASS" in text
        assert "28.000 GHz" in text
        assert "general_public" in text

    def test_fail_output(self) -> None:
        r = evaluate_compliance(freq_hz=28.0e9, sab_4cm2=25.0)
        text = summary_text(r)
        assert "FAIL" in text

    def test_tx_power_shown(self) -> None:
        r = evaluate_compliance(freq_hz=28.0e9, sab_4cm2=10.0)
        text = summary_text(r, tx_power_dbm=23.0)
        assert "23.0 dBm" in text

    def test_margin_in_output(self) -> None:
        r = evaluate_compliance(freq_hz=28.0e9, sab_4cm2=10.0)
        text = summary_text(r)
        assert "dB" in text

    def test_multiple_checks_shown(self) -> None:
        r = evaluate_compliance(
            freq_hz=28.0e9,
            sab_4cm2=10.0,
            sar_wb=0.04,
            sinc_whole_body=5.0,
        )
        text = summary_text(r)
        assert "S_ab (4 cm^2)" in text
        assert "SAR_wb" in text
        assert "S_inc (whole-body)" in text


# -----------------------------------------------------------------------
# Backward compatibility
# -----------------------------------------------------------------------


class TestBackwardCompat:
    """Ensure old API still works with corrected limit values."""

    def test_icnirp_2020_sab_peak(self) -> None:
        """sab_peak is now 20 W/m^2 (corrected from old 10)."""
        assert ICNIRP_2020.sab_peak == 20.0

    def test_icnirp_2020_sar_wb(self) -> None:
        assert ICNIRP_2020.sar_wb == 0.08

    def test_icnirp_2020_averaging_area(self) -> None:
        assert ICNIRP_2020.averaging_area_cm2 == 4.0

    def test_is_compliant_sab_pass(self) -> None:
        assert is_compliant_sab(19.0) is True

    def test_is_compliant_sab_at_limit(self) -> None:
        assert is_compliant_sab(20.0) is True

    def test_is_compliant_sab_fail(self) -> None:
        assert is_compliant_sab(21.0) is False

    def test_is_compliant_sar_pass(self) -> None:
        assert is_compliant_sar(0.07) is True

    def test_is_compliant_sar_fail(self) -> None:
        assert is_compliant_sar(0.09) is False


# -----------------------------------------------------------------------
# Helpers for ComplianceResult construction
# -----------------------------------------------------------------------

_GP = ExposureScenario.GENERAL_PUBLIC
_VALID_FREQ = 10e9  # 10 GHz - always valid


def _make_check(value: float, limit: float) -> ComplianceCheck:
    return ComplianceCheck(value=value, limit=limit, unit="W/m^2", label="test")


def _make_result(checks: list[ComplianceCheck | None]) -> ComplianceResult:
    """Build a ComplianceResult with up to 5 checks (any excess discarded)."""
    padded = (list(checks) + [None] * 5)[:5]
    return ComplianceResult(
        scenario=_GP,
        freq_hz=_VALID_FREQ,
        sab_4cm2=padded[0],
        sab_1cm2=padded[1],
        sar_wb=padded[2],
        sinc_local=padded[3],
        sinc_whole_body=padded[4],
    )


def _empty_result() -> ComplianceResult:
    return _make_result([])


# -----------------------------------------------------------------------
# ComplianceResult aggregation
# -----------------------------------------------------------------------


class TestComplianceResult:
    def test_no_checks_overall_pass_true(self) -> None:
        result = _empty_result()
        assert result.overall_pass is True

    def test_no_checks_margin_db_inf(self) -> None:
        result = _empty_result()
        assert math.isinf(result.margin_db)
        assert result.margin_db > 0

    def test_all_passing_overall_pass_true(self) -> None:
        checks = [_make_check(v, 20.0) for v in (1.0, 5.0, 10.0)]
        result = _make_result(checks)
        assert result.overall_pass is True

    def test_one_failing_overall_pass_false(self) -> None:
        """A single exceedance flips overall_pass to False."""
        checks = [
            _make_check(5.0, 20.0),  # passes
            _make_check(25.0, 20.0),  # fails
            _make_check(10.0, 20.0),  # passes
        ]
        result = _make_result(checks)
        assert result.overall_pass is False

    def test_margin_db_is_tightest(self) -> None:
        """margin_db on ComplianceResult should equal the minimum margin."""
        checks = [
            _make_check(10.0, 20.0),  # margin = 10*log10(2) ~ 3.01 dB
            _make_check(18.0, 20.0),  # margin = 10*log10(20/18) ~ 0.46 dB  <- tightest
            _make_check(2.0, 20.0),  # margin = 10 dB
        ]
        result = _make_result(checks)
        expected_tightest = 10.0 * math.log10(20.0 / 18.0)
        assert result.margin_db == pytest.approx(expected_tightest, rel=1e-6)


# -----------------------------------------------------------------------
# max_compliant_power
# -----------------------------------------------------------------------


class TestMaxCompliantPower:
    """Test max_compliant_power()."""

    def test_half_limit_doubles_power(self) -> None:
        """If measured Sab is half the limit, max power is 2x reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)  # limit 20
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(2.0)

    def test_at_limit_returns_ref(self) -> None:
        """If measured equals limit, max power equals reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=20.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(1.0)

    def test_over_limit_returns_less(self) -> None:
        """If measured exceeds limit, max power < reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=40.0)  # 2x limit
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(0.5)

    def test_tightest_constraint_wins(self) -> None:
        """Max power is limited by the tightest check."""
        r = evaluate_compliance(
            freq_hz=28e9,
            sab_4cm2=10.0,  # 10/20 = 0.5x -> can 2x
            sar_wb=0.04,  # 0.04/0.08 = 0.5x -> can 2x
            sinc_whole_body=8.0,  # 8/10 = 0.8x -> can 1.25x (tightest)
        )
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(10.0 / 8.0)

    def test_zero_measured_returns_inf(self) -> None:
        """If all measured values are zero, no constraint binds."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=0.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_no_checks_returns_inf(self) -> None:
        """If no values provided, max power is unconstrained."""
        r = evaluate_compliance(freq_hz=28e9)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_ref_power_scales(self) -> None:
        """Max power scales linearly with reference power."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        p1 = max_compliant_power(r, ref_power_w=1.0)
        p2 = max_compliant_power(r, ref_power_w=2.0)
        assert p2 == pytest.approx(2 * p1)

    def test_occupational_allows_more(self) -> None:
        """Occupational limits are 5x higher, so max power is 5x higher."""
        r_gp = evaluate_compliance(
            freq_hz=28e9,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            sab_4cm2=10.0,
        )
        r_oc = evaluate_compliance(
            freq_hz=28e9,
            scenario=ExposureScenario.OCCUPATIONAL,
            sab_4cm2=10.0,
        )
        p_gp = max_compliant_power(r_gp, ref_power_w=1.0)
        p_oc = max_compliant_power(r_oc, ref_power_w=1.0)
        assert p_oc == pytest.approx(5 * p_gp)

    def test_negative_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=-1.0)

    def test_zero_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=0.0)

    def test_above_30ghz_includes_1cm2(self) -> None:
        """Above 30 GHz, 1 cm^2 limit (40 W/m^2) may be the binding constraint."""
        r = evaluate_compliance(
            freq_hz=60e9,
            sab_4cm2=10.0,  # limit 20 -> can 2x
            sab_1cm2=30.0,  # limit 40 -> can 1.33x (tighter)
        )
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(40.0 / 30.0)

    def test_converts_to_dbm(self) -> None:
        """Verify the max power in dBm makes sense."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        p_max_w = max_compliant_power(r, ref_power_w=0.2)  # 200 mW = 23 dBm
        p_max_dbm = 10 * math.log10(p_max_w * 1000)
        # 2x ref -> 0.4 W = 400 mW -> ~26 dBm
        assert p_max_dbm == pytest.approx(10 * math.log10(400), rel=1e-6)

    def test_binding_check_is_smallest_ratio(self) -> None:
        """With two checks, the tighter one governs."""
        checks = [
            _make_check(value=10.0, limit=20.0),  # ratio limit/value = 2.0
            _make_check(value=18.0, limit=20.0),  # ratio limit/value = 1.111... <- tighter
        ]
        result = _make_result(checks)
        p = max_compliant_power(result, ref_power_w=1.0)
        assert p == pytest.approx(20.0 / 18.0)

    def test_all_zero_values_returns_inf(self) -> None:
        """If every check value is zero, there is no binding constraint."""
        checks = [_make_check(0.0, 20.0), _make_check(0.0, 10.0)]
        result = _make_result(checks)
        p = max_compliant_power(result, ref_power_w=1.0)
        assert math.isinf(p)


# -----------------------------------------------------------------------
# power_sweep
# -----------------------------------------------------------------------


class TestPowerSweep:
    def _single_check_result(self, value: float = 10.0, limit: float = 20.0) -> ComplianceResult:
        return _make_result([_make_check(value, limit)])

    def test_ref_power_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            power_sweep(self._single_check_result(), ref_power_w=0.0)

    def test_ref_power_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            power_sweep(self._single_check_result(), ref_power_w=-1.0)

    def test_default_bounds_shape(self) -> None:
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0, n_points=50)
        assert sweep["power_w"].shape == (50,)
        assert sweep["power_dbm"].shape == (50,)
        assert sweep["margin_db"].shape == (50,)
        assert sweep["compliant"].shape == (50,)

    def test_default_bounds_range(self) -> None:
        """Default: p_min = ref/100, p_max = ref*100."""
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0)
        assert sweep["power_w"][0] == pytest.approx(0.01)
        assert sweep["power_w"][-1] == pytest.approx(100.0)

    def test_custom_bounds(self) -> None:
        sweep = power_sweep(
            self._single_check_result(),
            ref_power_w=1.0,
            p_min_w=0.5,
            p_max_w=5.0,
            n_points=20,
        )
        assert sweep["power_w"][0] == pytest.approx(0.5)
        assert sweep["power_w"][-1] == pytest.approx(5.0)
        assert sweep["power_w"].shape == (20,)

    def test_no_checks_all_inf_and_compliant(self) -> None:
        sweep = power_sweep(_empty_result(), ref_power_w=1.0, n_points=10)
        assert np.all(np.isinf(sweep["margin_db"]))
        assert np.all(sweep["compliant"])
        assert math.isinf(sweep["p_max_compliant_w"])

    def test_margin_decreases_with_power(self) -> None:
        """Higher power -> larger S_ab -> smaller compliance margin."""
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0)
        m = sweep["margin_db"]
        assert np.all(np.diff(m) <= 0), "Margin should be monotonically non-increasing."

    def test_p_max_compliant_consistent(self) -> None:
        """p_max_compliant_w should match the transition point in compliant array."""
        sweep = power_sweep(self._single_check_result(value=10.0, limit=20.0), ref_power_w=1.0)
        # Theoretical max = 2.0 W (limit/value * ref_power)
        assert sweep["p_max_compliant_w"] == pytest.approx(2.0)


# -----------------------------------------------------------------------
# link_budget_compliance
# -----------------------------------------------------------------------


class TestLinkBudgetCompliance:
    def test_tx_power_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="tx_power_w must be positive"):
            link_budget_compliance(tx_power_w=0.0, distance_m=1.0, freq_hz=_VALID_FREQ)

    def test_tx_power_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="tx_power_w must be positive"):
            link_budget_compliance(tx_power_w=-0.001, distance_m=1.0, freq_hz=_VALID_FREQ)

    def test_distance_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="distance_m must be positive"):
            link_budget_compliance(tx_power_w=0.001, distance_m=0.0, freq_hz=_VALID_FREQ)

    def test_distance_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="distance_m must be positive"):
            link_budget_compliance(tx_power_w=0.001, distance_m=-1.0, freq_hz=_VALID_FREQ)

    def test_invalid_frequency_raises(self) -> None:
        with pytest.raises(ValueError, match="outside"):
            link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=50e3)

    def test_returns_expected_keys(self) -> None:
        result = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ)
        for key in (
            "sinc",
            "sab_estimate",
            "T0",
            "compliance",
            "compliant",
            "margin_db",
            "max_tx_power_w",
            "max_tx_power_dbm",
        ):
            assert key in result

    def test_sinc_formula(self) -> None:
        """sinc = P * gain / (4 * pi * d^2), gain=1 for 0 dBi."""
        tx_power_w = 0.01
        distance_m = 2.0
        result = link_budget_compliance(tx_power_w=tx_power_w, distance_m=distance_m, freq_hz=_VALID_FREQ)
        expected_sinc = tx_power_w / (4.0 * math.pi * distance_m**2)
        assert result["sinc"] == pytest.approx(expected_sinc, rel=1e-6)

    def test_explicit_T0(self) -> None:
        """When T0 is provided explicitly, sab_estimate == sinc * T0."""
        T0 = 0.5
        tx_power_w = 0.01
        distance_m = 2.0
        result = link_budget_compliance(tx_power_w=tx_power_w, distance_m=distance_m, freq_hz=_VALID_FREQ, T0=T0)
        assert result["T0"] == pytest.approx(T0)
        assert result["sab_estimate"] == pytest.approx(result["sinc"] * T0)

    def test_compliance_result_is_ComplianceResult(self) -> None:
        result = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ)
        assert isinstance(result["compliance"], ComplianceResult)

    def test_compliant_bool_consistent_with_margin(self) -> None:
        """compliant should be True iff margin_db >= 0."""
        result = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ)
        if result["margin_db"] >= 0:
            assert result["compliant"] is True
        else:
            assert result["compliant"] is False

    def test_very_high_power_non_compliant(self) -> None:
        """A megawatt at 1 m should certainly fail ICNIRP limits."""
        result = link_budget_compliance(tx_power_w=1e6, distance_m=1.0, freq_hz=_VALID_FREQ)
        assert result["compliant"] is False
        assert result["margin_db"] < 0

    def test_very_low_power_compliant(self) -> None:
        """A nanowatt at 100 m should be well within limits."""
        result = link_budget_compliance(tx_power_w=1e-9, distance_m=100.0, freq_hz=_VALID_FREQ)
        assert result["compliant"] is True
        assert result["margin_db"] > 0

    def test_antenna_gain_increases_sinc(self) -> None:
        """Adding positive antenna gain must increase sinc."""
        base = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ, antenna_gain_dbi=0.0)
        high_gain = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ, antenna_gain_dbi=10.0)
        assert high_gain["sinc"] > base["sinc"]


# -----------------------------------------------------------------------
# compliance_heatmap
# -----------------------------------------------------------------------


class TestComplianceHeatmap:
    def test_ref_power_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            compliance_heatmap(sab_4cm2=5.0, ref_power_w=0.0)

    def test_ref_power_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            compliance_heatmap(sab_4cm2=5.0, ref_power_w=-1.0)

    def test_output_keys_present(self) -> None:
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=5, n_power=5)
        for key in ("freq_hz", "power_w", "power_dbm", "margin_db", "compliant", "p_max_per_freq"):
            assert key in hm

    def test_output_shapes_without_sinc(self) -> None:
        n_freq, n_power = 8, 10
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=n_freq, n_power=n_power)
        assert hm["freq_hz"].shape == (n_freq,)
        assert hm["power_w"].shape == (n_power,)
        assert hm["power_dbm"].shape == (n_power,)
        assert hm["margin_db"].shape == (n_power, n_freq)
        assert hm["compliant"].shape == (n_power, n_freq)
        assert hm["p_max_per_freq"].shape == (n_freq,)

    def test_output_shapes_with_sinc(self) -> None:
        n_freq, n_power = 8, 10
        hm = compliance_heatmap(sab_4cm2=5.0, sinc_local=10.0, n_freq=n_freq, n_power=n_power)
        assert hm["margin_db"].shape == (n_power, n_freq)
        assert hm["compliant"].shape == (n_power, n_freq)

    def test_without_sinc_margin_constant_across_freq(self) -> None:
        """Without sinc_local, S_ab limit is frequency-independent; margin must be same at all freq."""
        hm = compliance_heatmap(
            sab_4cm2=5.0,
            ref_power_w=1.0,
            n_freq=6,
            n_power=4,
        )
        # For each power row, all frequency columns should be equal
        for row in hm["margin_db"]:
            assert np.allclose(row, row[0]), "Without sinc_local, margin must be uniform across frequency."

    def test_with_sinc_margin_varies_across_freq(self) -> None:
        """With sinc_local provided, the sinc limit 55/f^0.177 varies; margin must not be uniform."""
        hm = compliance_heatmap(
            sab_4cm2=5.0,
            sinc_local=30.0,
            ref_power_w=1.0,
            n_freq=10,
            n_power=5,
        )
        # At least one row should have non-uniform margins across frequency
        has_variation = False
        for row in hm["margin_db"]:
            if not np.allclose(row, row[0]):
                has_variation = True
                break
        assert has_variation, "With sinc_local, margin should vary across frequency."

    def test_compliant_bool_consistent_with_margin(self) -> None:
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=4, n_power=4)
        assert np.array_equal(hm["compliant"], hm["margin_db"] >= 0)

    def test_p_max_per_freq_all_positive(self) -> None:
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=5, n_power=5)
        assert np.all(hm["p_max_per_freq"] > 0)

    def test_custom_power_bounds(self) -> None:
        hm = compliance_heatmap(
            sab_4cm2=5.0,
            ref_power_w=1.0,
            p_min_w=0.1,
            p_max_w=10.0,
            n_freq=3,
            n_power=5,
        )
        assert hm["power_w"][0] == pytest.approx(0.1)
        assert hm["power_w"][-1] == pytest.approx(10.0)

    def test_zero_sab_gives_inf_p_max(self) -> None:
        """sab_4cm2=0 means no S_ab constraint -> p_max_per_freq should be inf."""
        hm = compliance_heatmap(sab_4cm2=0.0, n_freq=4, n_power=4)
        assert np.all(np.isinf(hm["p_max_per_freq"]))

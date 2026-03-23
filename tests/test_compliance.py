"""Tests for ICNIRP 2020 compliance module."""

import math

import pytest

from aegis.compliance import (
    ICNIRP_2020,
    ComplianceCheck,
    ExposureScenario,
    evaluate_compliance,
    icnirp_limits,
    is_compliant_sab,
    is_compliant_sar,
    margin_db,
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
    """Frequency must be > 6 GHz and <= 300 GHz."""

    def test_at_6ghz_raises(self) -> None:
        with pytest.raises(ValueError, match="outside"):
            icnirp_limits(freq_hz=6.0e9)

    def test_below_6ghz_raises(self) -> None:
        with pytest.raises(ValueError, match="outside"):
            icnirp_limits(freq_hz=5.0e9)

    def test_above_300ghz_raises(self) -> None:
        with pytest.raises(ValueError, match="outside"):
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

    def test_invalid_freq_raises(self) -> None:
        with pytest.raises(ValueError):
            evaluate_compliance(freq_hz=5.0e9, sab_4cm2=10.0)


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

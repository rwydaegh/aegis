"""Edge case tests for aegis.compliance.

Covers: frequency validation, ComplianceCheck properties, ComplianceResult
aggregation, evaluate_compliance logic, max_compliant_power, margin_db,
power_sweep, link_budget_compliance, and compliance_heatmap.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aegis.compliance import (
    ComplianceCheck,
    ComplianceResult,
    ExposureScenario,
    compliance_heatmap,
    evaluate_compliance,
    icnirp_limits,
    link_budget_compliance,
    margin_db,
    max_compliant_power,
    power_sweep,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 1. Frequency validation
# ---------------------------------------------------------------------------


class TestFrequencyValidation:
    def test_exactly_6_ghz_fails(self):
        """6.000 GHz is the exclusive lower bound; must raise."""
        with pytest.raises(ValueError, match="outside the supported"):
            icnirp_limits(freq_hz=6.0e9)

    def test_6_001_ghz_passes(self):
        """Just above the lower bound; must succeed."""
        limits = icnirp_limits(freq_hz=6.001e9)
        assert limits.freq_hz == pytest.approx(6.001e9)

    def test_exactly_300_ghz_passes(self):
        """300 GHz is the inclusive upper bound; must succeed."""
        limits = icnirp_limits(freq_hz=300.0e9)
        assert limits.freq_hz == pytest.approx(300.0e9)

    def test_300_001_ghz_fails(self):
        """Just above the upper bound; must raise."""
        with pytest.raises(ValueError, match="outside the supported"):
            icnirp_limits(freq_hz=300.001e9)

    def test_negative_frequency_fails(self):
        with pytest.raises(ValueError, match="outside the supported"):
            icnirp_limits(freq_hz=-1.0)

    def test_zero_frequency_fails(self):
        with pytest.raises(ValueError, match="outside the supported"):
            icnirp_limits(freq_hz=0.0)


# ---------------------------------------------------------------------------
# 2. ComplianceCheck properties
# ---------------------------------------------------------------------------


class TestComplianceCheckProperties:
    def test_value_zero_gives_inf_margin(self):
        """Zero value -> limit/value is undefined; margin_db must be +inf."""
        check = _make_check(value=0.0, limit=20.0)
        assert math.isinf(check.margin_db)
        assert check.margin_db > 0

    def test_limit_zero_gives_inf_ratio(self):
        """Zero limit -> value/limit is undefined; ratio must be +inf."""
        check = _make_check(value=5.0, limit=0.0)
        assert math.isinf(check.ratio)

    def test_value_exceeds_limit_gives_negative_margin(self):
        """value > limit -> margin_db must be negative."""
        check = _make_check(value=30.0, limit=20.0)
        assert check.margin_db < 0
        assert not check.compliant

    def test_value_equals_limit_gives_zero_margin_and_compliant(self):
        """value == limit -> margin_db == 0 and compliant == True."""
        check = _make_check(value=20.0, limit=20.0)
        assert check.margin_db == pytest.approx(0.0)
        assert check.compliant

    def test_margin_db_formula(self):
        """Verify the formula 10*log10(limit/value) for a known pair."""
        check = _make_check(value=2.0, limit=20.0)
        expected = 10.0 * math.log10(20.0 / 2.0)  # == 10 dB
        assert check.margin_db == pytest.approx(expected)

    def test_ratio_formula(self):
        """ratio == value / limit."""
        check = _make_check(value=5.0, limit=20.0)
        assert check.ratio == pytest.approx(5.0 / 20.0)


# ---------------------------------------------------------------------------
# 3. ComplianceResult aggregation
# ---------------------------------------------------------------------------


class TestComplianceResult:
    def test_no_checks_overall_pass_true(self):
        result = _empty_result()
        assert result.overall_pass is True

    def test_no_checks_margin_db_inf(self):
        result = _empty_result()
        assert math.isinf(result.margin_db)
        assert result.margin_db > 0

    def test_all_passing_overall_pass_true(self):
        checks = [_make_check(v, 20.0) for v in (1.0, 5.0, 10.0)]
        result = _make_result(checks)
        assert result.overall_pass is True

    def test_one_failing_overall_pass_false(self):
        """A single exceedance flips overall_pass to False."""
        checks = [
            _make_check(5.0, 20.0),  # passes
            _make_check(25.0, 20.0),  # fails
            _make_check(10.0, 20.0),  # passes
        ]
        result = _make_result(checks)
        assert result.overall_pass is False

    def test_margin_db_is_tightest(self):
        """margin_db on ComplianceResult should equal the minimum margin."""
        checks = [
            _make_check(10.0, 20.0),  # margin = 10*log10(2) ~ 3.01 dB
            _make_check(18.0, 20.0),  # margin = 10*log10(20/18) ~ 0.46 dB  <- tightest
            _make_check(2.0, 20.0),  # margin = 10 dB
        ]
        result = _make_result(checks)
        expected_tightest = 10.0 * math.log10(20.0 / 18.0)
        assert result.margin_db == pytest.approx(expected_tightest, rel=1e-6)


# ---------------------------------------------------------------------------
# 4. evaluate_compliance
# ---------------------------------------------------------------------------


class TestEvaluateCompliance:
    def test_all_none_no_checks(self):
        """Passing all None values should produce a result with no checks."""
        result = evaluate_compliance(freq_hz=_VALID_FREQ)
        assert result.all_checks == []
        assert result.overall_pass is True

    def test_sab_1cm2_ignored_below_30_ghz(self):
        """sab_1cm2 is only relevant above 30 GHz; below it, check_sab_1 must be None."""
        result = evaluate_compliance(
            freq_hz=10e9,  # 10 GHz < 30 GHz
            sab_1cm2=5.0,
        )
        assert result.sab_1cm2 is None

    def test_sab_1cm2_included_above_30_ghz(self):
        """sab_1cm2 provided at 60 GHz should be included in the result."""
        result = evaluate_compliance(
            freq_hz=60e9,  # 60 GHz > 30 GHz
            sab_1cm2=5.0,
        )
        assert result.sab_1cm2 is not None
        assert result.sab_1cm2.value == pytest.approx(5.0)

    def test_exactly_30_ghz_no_1cm2(self):
        """At exactly 30 GHz (not strictly above), sab_1cm2 should be None."""
        result = evaluate_compliance(
            freq_hz=30e9,
            sab_1cm2=5.0,
        )
        assert result.sab_1cm2 is None

    def test_provided_values_attached_correctly(self):
        """Each provided quantity should map to its check with the right value."""
        result = evaluate_compliance(
            freq_hz=_VALID_FREQ,
            sab_4cm2=3.0,
            sar_wb=0.01,
            sinc_local=5.0,
            sinc_whole_body=2.0,
        )
        assert result.sab_4cm2.value == pytest.approx(3.0)
        assert result.sar_wb.value == pytest.approx(0.01)
        assert result.sinc_local.value == pytest.approx(5.0)
        assert result.sinc_whole_body.value == pytest.approx(2.0)

    def test_occupational_limits_higher(self):
        """Occupational limits are always higher than general public."""
        f = 28e9
        gp = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, f)
        occ = icnirp_limits(ExposureScenario.OCCUPATIONAL, f)
        assert occ.sab_4cm2 > gp.sab_4cm2
        assert occ.sinc_local > gp.sinc_local


# ---------------------------------------------------------------------------
# 5. max_compliant_power
# ---------------------------------------------------------------------------


class TestMaxCompliantPower:
    def test_ref_power_zero_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            max_compliant_power(_empty_result(), ref_power_w=0.0)

    def test_ref_power_negative_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            max_compliant_power(_empty_result(), ref_power_w=-1.0)

    def test_no_checks_returns_inf(self):
        result = _empty_result()
        p = max_compliant_power(result, ref_power_w=1.0)
        assert math.isinf(p)

    def test_all_zero_values_returns_inf(self):
        """If every check value is zero, there is no binding constraint."""
        checks = [_make_check(0.0, 20.0), _make_check(0.0, 10.0)]
        result = _make_result(checks)
        p = max_compliant_power(result, ref_power_w=1.0)
        assert math.isinf(p)

    def test_normal_scaling(self):
        """At ref_power_w=1W, value=10, limit=20: max power = 2W."""
        check = _make_check(value=10.0, limit=20.0)
        result = _make_result([check])
        p = max_compliant_power(result, ref_power_w=1.0)
        assert p == pytest.approx(2.0)

    def test_binding_check_is_smallest_ratio(self):
        """With two checks, the tighter one governs."""
        checks = [
            _make_check(value=10.0, limit=20.0),  # ratio limit/value = 2.0
            _make_check(value=18.0, limit=20.0),  # ratio limit/value = 1.111... <- tighter
        ]
        result = _make_result(checks)
        p = max_compliant_power(result, ref_power_w=1.0)
        assert p == pytest.approx(20.0 / 18.0)


# ---------------------------------------------------------------------------
# 6. margin_db standalone
# ---------------------------------------------------------------------------


class TestMarginDb:
    def test_zero_value_raises(self):
        with pytest.raises(ValueError, match="value must be positive"):
            margin_db(0.0, 20.0)

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="value must be positive"):
            margin_db(-1.0, 20.0)

    def test_value_below_limit_positive(self):
        m = margin_db(2.0, 20.0)
        assert m > 0
        assert m == pytest.approx(10.0 * math.log10(10.0))  # 10 dB

    def test_value_above_limit_negative(self):
        m = margin_db(40.0, 20.0)
        assert m < 0
        assert m == pytest.approx(10.0 * math.log10(0.5))  # -3.01 dB

    def test_value_equals_limit_zero(self):
        assert margin_db(20.0, 20.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 7. power_sweep
# ---------------------------------------------------------------------------


class TestPowerSweep:
    def _single_check_result(self, value: float = 10.0, limit: float = 20.0) -> ComplianceResult:
        return _make_result([_make_check(value, limit)])

    def test_ref_power_zero_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            power_sweep(self._single_check_result(), ref_power_w=0.0)

    def test_ref_power_negative_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            power_sweep(self._single_check_result(), ref_power_w=-1.0)

    def test_default_bounds_shape(self):
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0, n_points=50)
        assert sweep["power_w"].shape == (50,)
        assert sweep["power_dbm"].shape == (50,)
        assert sweep["margin_db"].shape == (50,)
        assert sweep["compliant"].shape == (50,)

    def test_default_bounds_range(self):
        """Default: p_min = ref/100, p_max = ref*100."""
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0)
        assert sweep["power_w"][0] == pytest.approx(0.01)
        assert sweep["power_w"][-1] == pytest.approx(100.0)

    def test_custom_bounds(self):
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

    def test_no_checks_all_inf_and_compliant(self):
        sweep = power_sweep(_empty_result(), ref_power_w=1.0, n_points=10)
        assert np.all(np.isinf(sweep["margin_db"]))
        assert np.all(sweep["compliant"])
        assert math.isinf(sweep["p_max_compliant_w"])

    def test_margin_decreases_with_power(self):
        """Higher power -> larger S_ab -> smaller compliance margin."""
        sweep = power_sweep(self._single_check_result(), ref_power_w=1.0)
        m = sweep["margin_db"]
        assert np.all(np.diff(m) <= 0), "Margin should be monotonically non-increasing."

    def test_p_max_compliant_consistent(self):
        """p_max_compliant_w should match the transition point in compliant array."""
        sweep = power_sweep(self._single_check_result(value=10.0, limit=20.0), ref_power_w=1.0)
        # Theoretical max = 2.0 W (limit/value * ref_power)
        assert sweep["p_max_compliant_w"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 8. link_budget_compliance
# ---------------------------------------------------------------------------


class TestLinkBudgetCompliance:
    def test_tx_power_zero_raises(self):
        with pytest.raises(ValueError, match="tx_power_w must be positive"):
            link_budget_compliance(tx_power_w=0.0, distance_m=1.0, freq_hz=_VALID_FREQ)

    def test_tx_power_negative_raises(self):
        with pytest.raises(ValueError, match="tx_power_w must be positive"):
            link_budget_compliance(tx_power_w=-0.001, distance_m=1.0, freq_hz=_VALID_FREQ)

    def test_distance_zero_raises(self):
        with pytest.raises(ValueError, match="distance_m must be positive"):
            link_budget_compliance(tx_power_w=0.001, distance_m=0.0, freq_hz=_VALID_FREQ)

    def test_distance_negative_raises(self):
        with pytest.raises(ValueError, match="distance_m must be positive"):
            link_budget_compliance(tx_power_w=0.001, distance_m=-1.0, freq_hz=_VALID_FREQ)

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError, match="outside the supported"):
            link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=6e9)

    def test_returns_expected_keys(self):
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

    def test_sinc_formula(self):
        """sinc = P * gain / (4 * pi * d^2), gain=1 for 0 dBi."""
        tx_power_w = 0.01
        distance_m = 2.0
        result = link_budget_compliance(tx_power_w=tx_power_w, distance_m=distance_m, freq_hz=_VALID_FREQ)
        expected_sinc = tx_power_w / (4.0 * math.pi * distance_m**2)
        assert result["sinc"] == pytest.approx(expected_sinc, rel=1e-6)

    def test_explicit_T0(self):
        """When T0 is provided explicitly, sab_estimate == sinc * T0."""
        T0 = 0.5
        tx_power_w = 0.01
        distance_m = 2.0
        result = link_budget_compliance(tx_power_w=tx_power_w, distance_m=distance_m, freq_hz=_VALID_FREQ, T0=T0)
        assert result["T0"] == pytest.approx(T0)
        assert result["sab_estimate"] == pytest.approx(result["sinc"] * T0)

    def test_compliance_result_is_ComplianceResult(self):
        from aegis.compliance import ComplianceResult

        result = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ)
        assert isinstance(result["compliance"], ComplianceResult)

    def test_compliant_bool_consistent_with_margin(self):
        """compliant should be True iff margin_db >= 0."""
        result = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ)
        if result["margin_db"] >= 0:
            assert result["compliant"] is True
        else:
            assert result["compliant"] is False

    def test_very_high_power_non_compliant(self):
        """A megawatt at 1 m should certainly fail ICNIRP limits."""
        result = link_budget_compliance(tx_power_w=1e6, distance_m=1.0, freq_hz=_VALID_FREQ)
        assert result["compliant"] is False
        assert result["margin_db"] < 0

    def test_very_low_power_compliant(self):
        """A nanowatt at 100 m should be well within limits."""
        result = link_budget_compliance(tx_power_w=1e-9, distance_m=100.0, freq_hz=_VALID_FREQ)
        assert result["compliant"] is True
        assert result["margin_db"] > 0

    def test_antenna_gain_increases_sinc(self):
        """Adding positive antenna gain must increase sinc."""
        base = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ, antenna_gain_dbi=0.0)
        high_gain = link_budget_compliance(tx_power_w=0.001, distance_m=1.0, freq_hz=_VALID_FREQ, antenna_gain_dbi=10.0)
        assert high_gain["sinc"] > base["sinc"]


# ---------------------------------------------------------------------------
# 9. compliance_heatmap
# ---------------------------------------------------------------------------


class TestComplianceHeatmap:
    def test_ref_power_zero_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            compliance_heatmap(sab_4cm2=5.0, ref_power_w=0.0)

    def test_ref_power_negative_raises(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            compliance_heatmap(sab_4cm2=5.0, ref_power_w=-1.0)

    def test_output_keys_present(self):
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=5, n_power=5)
        for key in ("freq_hz", "power_w", "power_dbm", "margin_db", "compliant", "p_max_per_freq"):
            assert key in hm

    def test_output_shapes_without_sinc(self):
        n_freq, n_power = 8, 10
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=n_freq, n_power=n_power)
        assert hm["freq_hz"].shape == (n_freq,)
        assert hm["power_w"].shape == (n_power,)
        assert hm["power_dbm"].shape == (n_power,)
        assert hm["margin_db"].shape == (n_power, n_freq)
        assert hm["compliant"].shape == (n_power, n_freq)
        assert hm["p_max_per_freq"].shape == (n_freq,)

    def test_output_shapes_with_sinc(self):
        n_freq, n_power = 8, 10
        hm = compliance_heatmap(sab_4cm2=5.0, sinc_local=10.0, n_freq=n_freq, n_power=n_power)
        assert hm["margin_db"].shape == (n_power, n_freq)
        assert hm["compliant"].shape == (n_power, n_freq)

    def test_without_sinc_margin_constant_across_freq(self):
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

    def test_with_sinc_margin_varies_across_freq(self):
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

    def test_compliant_bool_consistent_with_margin(self):
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=4, n_power=4)
        assert np.array_equal(hm["compliant"], hm["margin_db"] >= 0)

    def test_p_max_per_freq_all_positive(self):
        hm = compliance_heatmap(sab_4cm2=5.0, n_freq=5, n_power=5)
        assert np.all(hm["p_max_per_freq"] > 0)

    def test_custom_power_bounds(self):
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

    def test_zero_sab_gives_inf_p_max(self):
        """sab_4cm2=0 means no S_ab constraint -> p_max_per_freq should be inf."""
        hm = compliance_heatmap(sab_4cm2=0.0, n_freq=4, n_power=4)
        assert np.all(np.isinf(hm["p_max_per_freq"]))

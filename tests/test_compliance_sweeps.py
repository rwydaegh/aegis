"""Tests for compliance sweep functions: power_sweep, frequency_sweep,
max_compliant_power, compliance_heatmap.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.compliance import (
    ComplianceResult,
    ExposureScenario,
    evaluate_compliance,
    frequency_sweep,
    max_compliant_power,
    power_sweep,
)

# ---------------------------------------------------------------------------
# max_compliant_power
# ---------------------------------------------------------------------------


class TestMaxCompliantPower:
    def test_basic_scaling(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        # limit is 20, value is 10, so can double power
        assert p_max == pytest.approx(2.0)

    def test_at_limit_returns_ref_power(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=20.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(1.0)

    def test_exceeding_limit(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=40.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(0.5)

    def test_no_checks_returns_inf(self) -> None:
        r = evaluate_compliance(freq_hz=28e9)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_zero_value_returns_inf(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=0.0)
        # sab_4cm2=0 means check.value=0, skipped -> inf
        # But evaluate_compliance might not create a check for 0...
        # Actually it does: ComplianceCheck(value=0, limit=20)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_negative_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=-1.0)

    def test_zero_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=0.0)

    def test_multiple_checks_uses_tightest(self) -> None:
        r = evaluate_compliance(
            freq_hz=28e9,
            sab_4cm2=10.0,  # limit 20 -> ratio 2
            sar_wb=0.04,  # limit 0.08 -> ratio 2
            sinc_whole_body=8.0,  # limit 10 -> ratio 1.25 (tightest)
        )
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(1.25)

    def test_occupational_higher_limits(self) -> None:
        r_gp = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        r_oc = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0, scenario=ExposureScenario.OCCUPATIONAL)
        p_max_gp = max_compliant_power(r_gp, ref_power_w=1.0)
        p_max_oc = max_compliant_power(r_oc, ref_power_w=1.0)
        assert p_max_oc > p_max_gp


# ---------------------------------------------------------------------------
# power_sweep
# ---------------------------------------------------------------------------


class TestPowerSweep:
    def _baseline(self) -> ComplianceResult:
        return evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)

    def test_output_shapes(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0, n_points=50)
        assert out["power_w"].shape == (50,)
        assert out["power_dbm"].shape == (50,)
        assert out["margin_db"].shape == (50,)
        assert out["compliant"].shape == (50,)

    def test_default_power_range(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0)
        assert out["power_w"][0] == pytest.approx(0.01)
        assert out["power_w"][-1] == pytest.approx(100.0)

    def test_custom_power_range(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0, p_min_w=0.1, p_max_w=10.0, n_points=20)
        assert out["power_w"][0] == pytest.approx(0.1)
        assert out["power_w"][-1] == pytest.approx(10.0)
        assert len(out["power_w"]) == 20

    def test_compliant_at_low_power(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0, p_min_w=0.001, p_max_w=0.01)
        assert np.all(out["compliant"])
        assert np.all(out["margin_db"] > 0)

    def test_non_compliant_at_high_power(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0, p_min_w=100.0, p_max_w=1000.0)
        assert not np.any(out["compliant"])
        assert np.all(out["margin_db"] < 0)

    def test_p_max_compliant_matches(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0)
        p_max = out["p_max_compliant_w"]
        assert p_max == pytest.approx(max_compliant_power(r, 1.0))

    def test_negative_ref_power_raises(self) -> None:
        r = self._baseline()
        with pytest.raises(ValueError, match="positive"):
            power_sweep(r, ref_power_w=-1.0)

    def test_no_checks_all_compliant(self) -> None:
        r = evaluate_compliance(freq_hz=28e9)
        out = power_sweep(r, ref_power_w=1.0, n_points=10)
        assert np.all(out["compliant"])
        assert np.all(np.isinf(out["margin_db"]))

    def test_zero_values_all_compliant(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=0.0)
        out = power_sweep(r, ref_power_w=1.0, n_points=10)
        assert np.all(out["compliant"])

    def test_power_dbm_conversion(self) -> None:
        r = self._baseline()
        out = power_sweep(r, ref_power_w=1.0, p_min_w=1.0, p_max_w=1.0, n_points=1)
        # 1 W = 1000 mW -> 10*log10(1000) = 30 dBm
        assert out["power_dbm"][0] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# frequency_sweep
# ---------------------------------------------------------------------------


class TestFrequencySweep:
    def test_output_shapes(self) -> None:
        out = frequency_sweep(sab_4cm2=10.0, n_points=30)
        assert out["freq_hz"].shape == (30,)
        assert out["freq_ghz"].shape == (30,)
        assert out["margin_db"].shape == (30,)
        assert out["compliant"].shape == (30,)
        assert len(out["results"]) == 30

    def test_default_freq_range(self) -> None:
        out = frequency_sweep(sab_4cm2=10.0, n_points=10)
        assert out["freq_hz"][0] == pytest.approx(7e9)
        assert out["freq_hz"][-1] == pytest.approx(100e9)

    def test_custom_freq_range(self) -> None:
        out = frequency_sweep(
            sab_4cm2=10.0,
            freq_min_hz=10e9,
            freq_max_hz=50e9,
            n_points=5,
        )
        assert out["freq_hz"][0] == pytest.approx(10e9)
        assert out["freq_hz"][-1] == pytest.approx(50e9)

    def test_ghz_conversion(self) -> None:
        out = frequency_sweep(sab_4cm2=10.0, n_points=5)
        np.testing.assert_allclose(out["freq_ghz"], out["freq_hz"] / 1e9)

    def test_compliant_below_limit(self) -> None:
        out = frequency_sweep(sab_4cm2=5.0, n_points=10)
        # 5 W/m^2 is well below 20 W/m^2 sab limit at all frequencies
        assert np.all(out["compliant"])

    def test_non_compliant_above_limit(self) -> None:
        out = frequency_sweep(sab_4cm2=25.0, n_points=10)
        # 25 W/m^2 exceeds 20 W/m^2 limit everywhere
        assert not np.any(out["compliant"])

    def test_sinc_local_varies_with_frequency(self) -> None:
        out = frequency_sweep(sinc_local=30.0, n_points=50)
        # sinc limit decreases with frequency, so margin should decrease
        # at higher frequencies
        assert out["margin_db"][-1] < out["margin_db"][0]

    def test_occupational_scenario(self) -> None:
        out_gp = frequency_sweep(
            sab_4cm2=15.0,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            n_points=5,
        )
        out_oc = frequency_sweep(
            sab_4cm2=15.0,
            scenario=ExposureScenario.OCCUPATIONAL,
            n_points=5,
        )
        # Occupational has higher limits -> higher margins
        assert np.all(out_oc["margin_db"] > out_gp["margin_db"])

    def test_results_are_compliance_results(self) -> None:
        out = frequency_sweep(sab_4cm2=10.0, n_points=3)
        for cr in out["results"]:
            assert isinstance(cr, ComplianceResult)

    def test_no_values_vacuously_compliant(self) -> None:
        out = frequency_sweep(n_points=5)
        # No quantities provided means no checks, margin is inf, vacuously compliant
        assert np.all(out["compliant"])
        assert np.all(out["margin_db"] == float("inf"))

    def test_sub_6ghz_sab_only_vacuously_compliant(self) -> None:
        """Regression: frequency_sweep across sub-6 GHz with sab_4cm2 only.

        Below 6 GHz the S_ab limit does not apply (ICNIRP 2020), so those
        points have no applicable checks. They must be marked compliant
        (vacuously: no limit exceeded) with margin=inf, not False.
        """
        out = frequency_sweep(sab_4cm2=10.0, freq_min_hz=1e9, freq_max_hz=100e9, n_points=20)
        sub6 = out["freq_hz"] <= 6e9
        assert np.any(sub6), "Expected some sub-6 GHz points"
        # Sub-6 GHz: no sab limit, no sar data -> vacuously compliant
        assert np.all(out["compliant"][sub6])
        assert np.all(np.isinf(out["margin_db"][sub6]))
        # Above 6 GHz: sab check applies, 10 < 20 -> compliant
        above6 = ~sub6
        assert np.all(out["compliant"][above6])

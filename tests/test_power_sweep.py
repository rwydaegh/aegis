"""Tests for power_sweep, get_tissue_spectrum, and vectorized Cole-Cole."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aegis.compliance import (
    ComplianceResult,
    ExposureScenario,
    evaluate_compliance,
    max_compliant_power,
    power_sweep,
)
from aegis.tissue.cole_cole import cole_cole_permittivity


class TestPowerSweep:
    @pytest.fixture
    def ref_result(self):
        """Compliance result at 1W reference power."""
        return evaluate_compliance(
            freq_hz=28e9,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            sab_4cm2=10.0,  # limit is 20, so 3 dB margin
            sar_wb=0.04,  # limit is 0.08, so 3 dB margin
        )

    def test_sweep_returns_correct_keys(self, ref_result):
        result = power_sweep(ref_result, ref_power_w=1.0, n_points=10)
        assert "power_w" in result
        assert "power_dbm" in result
        assert "margin_db" in result
        assert "compliant" in result
        assert "p_max_w" in result
        assert "p_max_dbm" in result

    def test_sweep_shape(self, ref_result):
        result = power_sweep(ref_result, ref_power_w=1.0, n_points=20)
        assert result["power_w"].shape == (20,)
        assert result["margin_db"].shape == (20,)
        assert result["compliant"].shape == (20,)

    def test_margin_decreases_with_power(self, ref_result):
        result = power_sweep(ref_result, ref_power_w=1.0, n_points=50)
        margins = result["margin_db"]
        # Margin should monotonically decrease with increasing power
        assert np.all(np.diff(margins) <= 1e-10)

    def test_compliance_boundary(self, ref_result):
        """Below p_max all points should be compliant, above should not."""
        result = power_sweep(
            ref_result,
            ref_power_w=1.0,
            power_range_w=[0.01, 100.0],
            n_points=100,
        )
        p_max = result["p_max_w"]
        for i in range(len(result["power_w"])):
            if result["power_w"][i] <= p_max * 0.99:
                assert result["compliant"][i], f"Should be compliant at P={result['power_w'][i]}"
            elif result["power_w"][i] >= p_max * 1.01:
                assert not result["compliant"][i], f"Should not be compliant at P={result['power_w'][i]}"

    def test_p_max_matches_max_compliant_power(self, ref_result):
        result = power_sweep(ref_result, ref_power_w=1.0)
        p_max_sweep = result["p_max_w"]
        p_max_direct = max_compliant_power(ref_result, 1.0)
        assert abs(p_max_sweep - p_max_direct) < 1e-10

    def test_dbm_conversion(self, ref_result):
        result = power_sweep(ref_result, ref_power_w=1.0, n_points=5)
        # 1W = 30 dBm
        for i in range(5):
            expected_dbm = 10 * math.log10(result["power_w"][i] * 1e3)
            assert abs(result["power_dbm"][i] - expected_dbm) < 1e-10

    def test_no_checks_returns_inf(self):
        empty_result = ComplianceResult(
            scenario=ExposureScenario.GENERAL_PUBLIC,
            freq_hz=28e9,
            sab_4cm2=None,
            sab_1cm2=None,
            sar_wb=None,
            sinc_local=None,
            sinc_whole_body=None,
        )
        result = power_sweep(empty_result, ref_power_w=1.0, n_points=5)
        assert np.all(result["compliant"])
        assert result["p_max_w"] == float("inf")

    def test_negative_ref_power_raises(self, ref_result):
        with pytest.raises(ValueError, match="positive"):
            power_sweep(ref_result, ref_power_w=-1.0)


class TestColeColeVectorized:
    """Verify vectorized Cole-Cole matches scalar-by-scalar calls."""

    @pytest.fixture
    def params(self):
        return {
            "ef": 4.0,
            "del1": 32.0,
            "tau1": 7.23,
            "alf1": 0.0,
            "del2": 1100.0,
            "tau2": 32.48,
            "alf2": 0.2,
            "del3": 33000.0,
            "tau3": 159.15,
            "alf3": 0.2,
            "del4": 0.0,
            "tau4": 15.915,
            "alf4": 0.2,
            "sig": 0.0002,
        }

    def test_vectorized_matches_scalar(self, params):
        freqs = np.linspace(1e9, 100e9, 50)
        eps_vec = cole_cole_permittivity(freqs, params)
        for i, f in enumerate(freqs):
            eps_scalar = cole_cole_permittivity(f, params)
            assert abs(eps_vec[i] - eps_scalar) < 1e-10

    def test_vectorized_causality(self, params):
        """Real part should be positive, imaginary part negative for lossy tissue."""
        freqs = np.geomspace(1e6, 300e9, 200)
        eps = cole_cole_permittivity(freqs, params)
        assert np.all(np.real(eps) > 0), "Real permittivity should be positive"
        assert np.all(np.imag(eps) <= 0), "Imaginary part should be non-positive (lossy)"

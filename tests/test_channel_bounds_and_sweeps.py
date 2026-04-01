"""Tests for element_index bounds validation, compliance sweeps, and MIMO edge cases.

Covers:
- field_channel.compute_field_channel with out-of-bounds element_index
- body_channel.compute_body_channel with out-of-bounds element_index
- compliance.power_sweep
- compliance.frequency_sweep
- MIMO precoder edge cases (singular channels, K=0)
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.field_channel import compute_field_channel
from aegis.compliance import (
    ComplianceResult,
    ExposureScenario,
    compliance_heatmap,
    evaluate_compliance,
    frequency_sweep,
    link_budget_compliance,
    max_compliant_power,
    power_sweep,
)

# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def simple_channel_args():
    """Minimal valid inputs for field/body channel computation."""
    M, N = 4, 3
    normals = np.tile([0.0, 0.0, 1.0], (M, 1))
    centroids = np.random.default_rng(42).uniform(-0.1, 0.1, (M, 3))
    k_hat = np.tile([0.0, 0.0, -1.0], (N, 1))
    psi = np.zeros((N, 3), dtype=complex)
    psi[:, 0] = 1.0  # x-polarised
    element_index = np.array([0, 0, 1], dtype=np.intp)
    n_elements = 2
    freq_hz = 28e9
    return {
        "normals": normals,
        "centroids": centroids,
        "k_hat": k_hat,
        "psi": psi,
        "element_index": element_index,
        "n_elements": n_elements,
        "freq_hz": freq_hz,
    }


@pytest.fixture
def reference_compliance() -> ComplianceResult:
    """A compliance result at 28 GHz with known values."""
    return evaluate_compliance(
        freq_hz=28e9,
        scenario=ExposureScenario.GENERAL_PUBLIC,
        sab_4cm2=10.0,  # limit is 20 -> 3 dB margin
        sinc_local=20.0,
    )


# -----------------------------------------------------------------------
# Field channel bounds validation
# -----------------------------------------------------------------------


class TestFieldChannelBounds:
    def test_valid_indices_pass(self, simple_channel_args):
        """Normal case: indices in [0, n_elements) should work."""
        args = simple_channel_args
        G = compute_field_channel(
            args["centroids"],
            args["k_hat"],
            args["psi"],
            args["element_index"],
            args["freq_hz"],
            args["n_elements"],
        )
        assert G.shape == (4, 3, 2)

    def test_negative_index_raises(self, simple_channel_args):
        args = simple_channel_args
        args["element_index"] = np.array([0, -1, 1], dtype=np.intp)
        with pytest.raises(ValueError, match="element_index values must be in"):
            compute_field_channel(
                args["centroids"],
                args["k_hat"],
                args["psi"],
                args["element_index"],
                args["freq_hz"],
                args["n_elements"],
            )

    def test_too_large_index_raises(self, simple_channel_args):
        args = simple_channel_args
        args["element_index"] = np.array([0, 1, 2], dtype=np.intp)  # max valid is 1
        with pytest.raises(ValueError, match="element_index values must be in"):
            compute_field_channel(
                args["centroids"],
                args["k_hat"],
                args["psi"],
                args["element_index"],
                args["freq_hz"],
                args["n_elements"],
            )

    def test_empty_paths_ok(self, simple_channel_args):
        """Empty element_index should not raise."""
        args = simple_channel_args
        G = compute_field_channel(
            args["centroids"],
            np.zeros((0, 3)),
            np.zeros((0, 3), dtype=complex),
            np.array([], dtype=np.intp),
            args["freq_hz"],
            args["n_elements"],
        )
        assert G.shape == (4, 3, 2)
        assert np.allclose(G, 0)

    def test_single_element_boundary(self, simple_channel_args):
        """Index 0 with n_elements=1 should work."""
        args = simple_channel_args
        args["element_index"] = np.array([0, 0, 0], dtype=np.intp)
        args["n_elements"] = 1
        G = compute_field_channel(
            args["centroids"],
            args["k_hat"],
            args["psi"],
            args["element_index"],
            args["freq_hz"],
            args["n_elements"],
        )
        assert G.shape == (4, 3, 1)


# -----------------------------------------------------------------------
# Body channel bounds validation
# -----------------------------------------------------------------------


class TestBodyChannelBounds:
    def test_valid_indices_pass(self, simple_channel_args):
        args = simple_channel_args
        G_tilde = compute_body_channel(
            args["normals"],
            args["centroids"],
            args["k_hat"],
            args["psi"],
            args["element_index"],
            n_tilde=complex(4.0, -1.0),
            sigma=25.0,
            freq_hz=args["freq_hz"],
            n_elements=args["n_elements"],
        )
        assert G_tilde.shape == (4, 3, 2)

    def test_negative_index_raises(self, simple_channel_args):
        args = simple_channel_args
        args["element_index"] = np.array([0, -1, 1], dtype=np.intp)
        with pytest.raises(ValueError, match="element_index values must be in"):
            compute_body_channel(
                args["normals"],
                args["centroids"],
                args["k_hat"],
                args["psi"],
                args["element_index"],
                n_tilde=complex(4.0, -1.0),
                sigma=25.0,
                freq_hz=args["freq_hz"],
                n_elements=args["n_elements"],
            )

    def test_too_large_index_raises(self, simple_channel_args):
        args = simple_channel_args
        args["element_index"] = np.array([0, 1, 5], dtype=np.intp)  # max valid is 1
        with pytest.raises(ValueError, match="element_index values must be in"):
            compute_body_channel(
                args["normals"],
                args["centroids"],
                args["k_hat"],
                args["psi"],
                args["element_index"],
                n_tilde=complex(4.0, -1.0),
                sigma=25.0,
                freq_hz=args["freq_hz"],
                n_elements=args["n_elements"],
            )

    def test_empty_paths_ok(self, simple_channel_args):
        args = simple_channel_args
        G_tilde = compute_body_channel(
            args["normals"],
            args["centroids"],
            np.zeros((0, 3)),
            np.zeros((0, 3), dtype=complex),
            np.array([], dtype=np.intp),
            n_tilde=complex(4.0, -1.0),
            sigma=25.0,
            freq_hz=args["freq_hz"],
            n_elements=args["n_elements"],
        )
        assert G_tilde.shape == (4, 3, 2)
        assert np.allclose(G_tilde, 0)


# -----------------------------------------------------------------------
# Power sweep
# -----------------------------------------------------------------------


class TestPowerSweep:
    def test_basic_sweep(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0)
        assert "power_w" in result
        assert "power_dbm" in result
        assert "margin_db" in result
        assert "compliant" in result
        assert "p_max_compliant_w" in result
        assert len(result["power_w"]) == 200

    def test_margin_decreases_with_power(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0, n_points=50)
        margins = result["margin_db"]
        # Margin should decrease monotonically as power increases
        assert np.all(np.diff(margins) <= 1e-10)

    def test_compliant_at_low_power(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0, p_min_w=0.001, p_max_w=0.01, n_points=10)
        assert np.all(result["compliant"])

    def test_non_compliant_at_high_power(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0, p_min_w=100.0, p_max_w=1000.0, n_points=10)
        assert not np.all(result["compliant"])

    def test_p_max_matches_max_compliant_power(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0)
        p_max_sweep = result["p_max_compliant_w"]
        p_max_direct = max_compliant_power(reference_compliance, 1.0)
        assert abs(p_max_sweep - p_max_direct) < 1e-10

    def test_custom_range(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0, p_min_w=0.5, p_max_w=5.0, n_points=20)
        assert len(result["power_w"]) == 20
        assert result["power_w"][0] == pytest.approx(0.5)
        assert result["power_w"][-1] == pytest.approx(5.0)

    def test_invalid_ref_power(self, reference_compliance):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            power_sweep(reference_compliance, ref_power_w=0.0)

    def test_no_checks_returns_all_compliant(self):
        empty_result = evaluate_compliance(freq_hz=28e9)
        result = power_sweep(empty_result, ref_power_w=1.0, n_points=10)
        assert np.all(result["compliant"])
        assert result["p_max_compliant_w"] == float("inf")

    def test_dbm_conversion(self, reference_compliance):
        result = power_sweep(reference_compliance, ref_power_w=1.0, n_points=5)
        # 1 W = 30 dBm
        expected_dbm = 10.0 * np.log10(result["power_w"] * 1e3)
        np.testing.assert_allclose(result["power_dbm"], expected_dbm)


# -----------------------------------------------------------------------
# Frequency sweep
# -----------------------------------------------------------------------


class TestFrequencySweep:
    def test_basic_sweep(self):
        result = frequency_sweep(sab_4cm2=10.0, n_points=20)
        assert "freq_hz" in result
        assert "freq_ghz" in result
        assert "margin_db" in result
        assert "compliant" in result
        assert "results" in result
        assert len(result["freq_hz"]) == 20
        assert len(result["results"]) == 20

    def test_all_compliant_low_exposure(self):
        result = frequency_sweep(sab_4cm2=1.0, n_points=20)
        # 1 W/m^2 is well below 20 W/m^2 limit at all freqs
        assert np.all(result["compliant"])

    def test_all_non_compliant_high_exposure(self):
        result = frequency_sweep(sab_4cm2=100.0, n_points=20)
        # 100 W/m^2 exceeds 20 W/m^2 limit at all freqs
        assert not np.any(result["compliant"])

    def test_sinc_limit_varies_with_frequency(self):
        """sinc_local limit = 55/f^0.177 decreases with frequency, so margin decreases."""
        result = frequency_sweep(sinc_local=30.0, n_points=50)
        margins = result["margin_db"]
        # Margin should generally decrease with frequency (limits get tighter)
        # At low frequencies, 55/f^0.177 is larger, so more margin
        assert margins[0] > margins[-1]

    def test_1cm2_only_above_30ghz(self):
        """sab_1cm2 check only applies above 30 GHz."""
        result = frequency_sweep(
            sab_1cm2=30.0,  # below 40 W/m^2 limit
            freq_min_hz=7e9,
            freq_max_hz=100e9,
            n_points=50,
        )
        for cr in result["results"]:
            if cr.freq_hz <= 30e9:
                assert cr.sab_1cm2 is None
            else:
                assert cr.sab_1cm2 is not None

    def test_occupational_scenario(self):
        result = frequency_sweep(
            sab_4cm2=50.0,
            scenario=ExposureScenario.OCCUPATIONAL,
            n_points=10,
        )
        # 50 W/m^2 is below occupational limit of 100 W/m^2
        assert np.all(result["compliant"])

    def test_freq_ghz_matches(self):
        result = frequency_sweep(sab_4cm2=10.0, n_points=10)
        np.testing.assert_allclose(result["freq_ghz"], result["freq_hz"] / 1e9)

    def test_geomspace_distribution(self):
        result = frequency_sweep(
            sab_4cm2=10.0,
            freq_min_hz=10e9,
            freq_max_hz=100e9,
            n_points=10,
        )
        freq = result["freq_hz"]
        assert freq[0] == pytest.approx(10e9)
        assert freq[-1] == pytest.approx(100e9)
        # Geomspace: ratios between consecutive points should be constant
        ratios = freq[1:] / freq[:-1]
        np.testing.assert_allclose(ratios, ratios[0], rtol=1e-10)

    def test_multiple_quantities(self):
        result = frequency_sweep(
            sab_4cm2=10.0,
            sar_wb=0.05,
            sinc_local=20.0,
            n_points=10,
        )
        # Each result should have all three checks
        for cr in result["results"]:
            assert cr.sab_4cm2 is not None
            assert cr.sar_wb is not None
            assert cr.sinc_local is not None

    def test_no_quantities_all_indeterminate(self):
        result = frequency_sweep(n_points=10)
        # No quantities provided means no checks, so compliant is False (indeterminate)
        assert not np.any(result["compliant"])
        assert all(m == float("inf") for m in result["margin_db"])


# -----------------------------------------------------------------------
# MIMO precoder edge cases
# -----------------------------------------------------------------------


class TestMIMOPrecoderEdgeCases:
    def test_zf_singular_channel_falls_back_to_mrt(self):
        """ZF with linearly dependent channels should fall back to MRT."""
        from aegis.mimo.precoders import mrt, zf

        # Two identical rows -> H @ H^H is singular
        H = np.array([[1 + 0j, 0, 0, 0], [1 + 0j, 0, 0, 0]])
        with pytest.warns(match="singular.*MRT"):
            W = zf(H, P=1.0)
        W_mrt = mrt(H, P=1.0)
        np.testing.assert_allclose(W, W_mrt)

    def test_zf_well_conditioned(self):
        """ZF with orthogonal channels should produce zero inter-user interference."""
        from aegis.mimo.precoders import zf

        H = np.eye(4, dtype=complex)[:2]  # 2 users, 4 antennas, orthogonal
        W = zf(H, P=1.0)
        HW = H @ W
        # Off-diagonal should be zero (ZF property)
        np.testing.assert_allclose(np.abs(HW - np.diag(np.diag(HW))), 0, atol=1e-10)

    def test_compute_mrt_precoder_k0(self):
        """compute_mrt_precoder with K=0 should return empty matrix."""
        from aegis.mimo.compute import compute_mrt_precoder

        H = np.zeros((0, 4), dtype=complex)
        W = compute_mrt_precoder(H, total_power=1.0)
        assert W.shape == (4, 0)

    def test_zf_all_zero_channel(self):
        """ZF with all-zero channel should fall back gracefully."""
        from aegis.mimo.precoders import zf

        H = np.zeros((1, 4), dtype=complex)
        with pytest.warns(match="singular.*MRT"):
            W = zf(H, P=1.0)
        # MRT fallback with zero channel -> result is normalized with 1e-30 floor
        assert W.shape == (4, 1)

    def test_mmse_noise_zero_equals_zf(self):
        """MMSE with noise_power=0 should equal ZF for well-conditioned H."""
        from aegis.mimo.precoders import mmse, zf

        rng = np.random.default_rng(42)
        H = rng.standard_normal((2, 8)) + 1j * rng.standard_normal((2, 8))
        W_zf = zf(H, P=1.0)
        W_mmse = mmse(H, P=1.0, noise_power=0.0)
        np.testing.assert_allclose(W_mmse, W_zf, atol=1e-10)

    def test_mrt_power_normalization(self):
        """MRT precoder should have ||W||_F^2 = P."""
        from aegis.mimo.precoders import mrt

        rng = np.random.default_rng(7)
        H = rng.standard_normal((3, 8)) + 1j * rng.standard_normal((3, 8))
        P = 2.5
        W = mrt(H, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert frob_sq == pytest.approx(P, rel=1e-10)

    def test_zf_exposure_zero_Q(self):
        """zf_exposure with all-zero Q should behave like unconstrained ZF."""
        from aegis.mimo.precoders import zf, zf_exposure

        rng = np.random.default_rng(42)
        H = rng.standard_normal((2, 8)) + 1j * rng.standard_normal((2, 8))
        Q_zeros = [np.zeros((8, 8)), np.zeros((8, 8))]
        W_exp = zf_exposure(H, Q_zeros, P_abs_max=1.0, P=1.0)
        W_zf = zf(H, P=1.0)
        # With zero Q, no power scaling happens, but directions match ZF
        # Power may differ since zf_exposure starts from ZF power allocation
        norms_exp = np.linalg.norm(W_exp, axis=0)
        norms_zf = np.linalg.norm(W_zf, axis=0)
        # Directions should match
        for k in range(2):
            if norms_exp[k] > 1e-10 and norms_zf[k] > 1e-10:
                cos_sim = abs(np.vdot(W_exp[:, k], W_zf[:, k])) / (norms_exp[k] * norms_zf[k])
                assert cos_sim == pytest.approx(1.0, abs=1e-10)


# -----------------------------------------------------------------------
# Compliance heatmap (2D)
# -----------------------------------------------------------------------


class TestComplianceHeatmap:
    def test_basic_shape(self):
        result = compliance_heatmap(sab_4cm2=10.0, n_freq=20, n_power=15)
        assert result["freq_hz"].shape == (20,)
        assert result["power_w"].shape == (15,)
        assert result["margin_db"].shape == (15, 20)
        assert result["compliant"].shape == (15, 20)
        assert result["p_max_per_freq"].shape == (20,)

    def test_low_power_compliant(self):
        result = compliance_heatmap(
            sab_4cm2=10.0,
            ref_power_w=1.0,
            p_min_w=0.001,
            p_max_w=0.01,
            n_freq=10,
            n_power=10,
        )
        # Very low power -> all compliant
        assert np.all(result["compliant"])

    def test_high_power_non_compliant(self):
        result = compliance_heatmap(
            sab_4cm2=10.0,
            ref_power_w=1.0,
            p_min_w=100.0,
            p_max_w=1000.0,
            n_freq=10,
            n_power=10,
        )
        # Very high power -> none compliant
        assert not np.any(result["compliant"])

    def test_p_max_per_freq_constant_for_sab(self):
        """S_ab limit is constant (20 W/m^2), so p_max should be the same at all freqs."""
        result = compliance_heatmap(
            sab_4cm2=10.0,
            ref_power_w=1.0,
            n_freq=20,
            n_power=10,
        )
        # p_max = P_ref * limit / sab = 1.0 * 20 / 10 = 2.0 at all frequencies
        np.testing.assert_allclose(result["p_max_per_freq"], 2.0, rtol=1e-10)

    def test_occupational_higher_limits(self):
        """Occupational limits (100 W/m^2) should allow more power than GP (20 W/m^2)."""
        gp = compliance_heatmap(
            sab_4cm2=10.0,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            n_freq=5,
            n_power=5,
        )
        occ = compliance_heatmap(
            sab_4cm2=10.0,
            scenario=ExposureScenario.OCCUPATIONAL,
            n_freq=5,
            n_power=5,
        )
        assert np.all(occ["p_max_per_freq"] > gp["p_max_per_freq"])

    def test_margin_decreases_with_power(self):
        result = compliance_heatmap(sab_4cm2=10.0, n_freq=5, n_power=20)
        # At each frequency, margin should decrease with increasing power
        for j in range(5):
            col = result["margin_db"][:, j]
            assert np.all(np.diff(col) <= 1e-10)

    def test_invalid_ref_power(self):
        with pytest.raises(ValueError, match="ref_power_w must be positive"):
            compliance_heatmap(sab_4cm2=10.0, ref_power_w=0.0)

    def test_sinc_local_none_same_as_before(self):
        """sinc_local=None should give identical results to omitting it."""
        a = compliance_heatmap(sab_4cm2=10.0, n_freq=10, n_power=10)
        b = compliance_heatmap(sab_4cm2=10.0, n_freq=10, n_power=10, sinc_local=None)
        np.testing.assert_array_equal(a["margin_db"], b["margin_db"])
        np.testing.assert_array_equal(a["p_max_per_freq"], b["p_max_per_freq"])

    def test_sinc_local_varies_with_frequency(self):
        """With sinc_local, p_max should vary across frequency."""
        result = compliance_heatmap(sab_4cm2=10.0, sinc_local=30.0, n_freq=20, n_power=10)
        p_max = result["p_max_per_freq"]
        assert not np.allclose(p_max, p_max[0]), "p_max should vary with frequency"

    def test_sinc_local_tightens_margin(self):
        """Adding sinc_local should never loosen the margin."""
        without = compliance_heatmap(sab_4cm2=10.0, n_freq=10, n_power=10)
        with_sinc = compliance_heatmap(sab_4cm2=10.0, sinc_local=30.0, n_freq=10, n_power=10)
        assert np.all(with_sinc["margin_db"] <= without["margin_db"] + 1e-10)

    def test_sinc_local_p_max_correctness(self):
        """Check p_max against manual calculation at 28 GHz."""
        result = compliance_heatmap(
            sab_4cm2=10.0,
            sinc_local=30.0,
            ref_power_w=1.0,
            freq_min_hz=28e9,
            freq_max_hz=28e9,
            n_freq=1,
            n_power=10,
        )
        # sinc limit at 28 GHz GP: 55 / (28)^0.177
        f_ghz = 28.0
        sinc_limit = 55.0 / f_ghz**0.177
        p_max_sinc = 1.0 * sinc_limit / 30.0
        p_max_sab = 1.0 * 20.0 / 10.0  # sab limit / sab_4cm2
        expected = min(p_max_sab, p_max_sinc)
        np.testing.assert_allclose(result["p_max_per_freq"][0], expected, rtol=1e-6)

    def test_sinc_local_occupational(self):
        """Occupational sinc limit uses 275/f^0.177 (5x GP)."""
        gp = compliance_heatmap(
            sab_4cm2=10.0,
            sinc_local=30.0,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            n_freq=5,
            n_power=5,
        )
        occ = compliance_heatmap(
            sab_4cm2=10.0,
            sinc_local=30.0,
            scenario=ExposureScenario.OCCUPATIONAL,
            n_freq=5,
            n_power=5,
        )
        assert np.all(occ["margin_db"] >= gp["margin_db"] - 1e-10)

    def test_sinc_local_dominates_when_large(self):
        """When sinc_local is very large, it becomes the binding constraint."""
        result = compliance_heatmap(
            sab_4cm2=1.0,  # small sab -> large sab margin
            sinc_local=500.0,  # large sinc -> small sinc margin
            n_freq=10,
            n_power=10,
        )
        without_sinc = compliance_heatmap(
            sab_4cm2=1.0,
            n_freq=10,
            n_power=10,
        )
        # At least some cells should have tighter margins
        assert np.any(result["margin_db"] < without_sinc["margin_db"] - 0.1)


# -----------------------------------------------------------------------
# Link budget compliance
# -----------------------------------------------------------------------


class TestLinkBudgetCompliance:
    def test_basic_isotropic(self):
        """Isotropic antenna at 10m, 1W, 28 GHz."""
        result = link_budget_compliance(
            tx_power_w=1.0,
            distance_m=10.0,
            freq_hz=28e9,
        )
        assert "sinc" in result
        assert "sab_estimate" in result
        assert "compliance" in result
        assert "compliant" in result
        assert "max_tx_power_w" in result

        # S_inc = P / (4*pi*d^2) = 1 / (4*pi*100) ~ 7.96e-4 W/m^2
        expected_sinc = 1.0 / (4 * np.pi * 100)
        assert result["sinc"] == pytest.approx(expected_sinc, rel=1e-10)

    def test_high_power_non_compliant(self):
        """Very high power at close range should fail compliance."""
        result = link_budget_compliance(
            tx_power_w=1000.0,
            antenna_gain_dbi=30.0,  # 1000x gain
            distance_m=0.5,
            freq_hz=28e9,
        )
        # S_inc = 1000 * 1000 / (4*pi*0.25) ~ 318,310 W/m^2
        assert not result["compliant"]
        assert result["margin_db"] < 0

    def test_low_power_compliant(self):
        """Low power at large distance should be compliant."""
        result = link_budget_compliance(
            tx_power_w=0.001,
            distance_m=100.0,
            freq_hz=28e9,
        )
        assert result["compliant"]
        assert result["margin_db"] > 0

    def test_gain_increases_sinc(self):
        """Higher antenna gain should increase incident power density."""
        r0 = link_budget_compliance(tx_power_w=1.0, antenna_gain_dbi=0.0, distance_m=10.0, freq_hz=28e9)
        r10 = link_budget_compliance(tx_power_w=1.0, antenna_gain_dbi=10.0, distance_m=10.0, freq_hz=28e9)
        assert r10["sinc"] == pytest.approx(r0["sinc"] * 10.0, rel=1e-10)

    def test_inverse_square_law(self):
        """Double distance -> quarter power density."""
        r1 = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9)
        r2 = link_budget_compliance(tx_power_w=1.0, distance_m=20.0, freq_hz=28e9)
        assert r2["sinc"] == pytest.approx(r1["sinc"] / 4.0, rel=1e-10)

    def test_sab_proportional_to_sinc(self):
        """S_ab = S_inc * T0."""
        result = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9, T0=0.3)
        assert result["sab_estimate"] == pytest.approx(result["sinc"] * 0.3, rel=1e-10)

    def test_custom_T0(self):
        """Custom T0 should override tissue lookup."""
        r1 = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9, T0=0.5)
        r2 = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9, T0=1.0)
        assert r2["sab_estimate"] == pytest.approx(2.0 * r1["sab_estimate"], rel=1e-10)

    def test_max_power_scales(self):
        """Max compliant power should scale with distance^2."""
        r1 = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9, T0=0.4)
        r2 = link_budget_compliance(tx_power_w=1.0, distance_m=20.0, freq_hz=28e9, T0=0.4)
        # At 2x distance, sinc is 4x lower, so max power is 4x higher
        assert r2["max_tx_power_w"] == pytest.approx(r1["max_tx_power_w"] * 4.0, rel=1e-3)

    def test_occupational_allows_more(self):
        """Occupational scenario should allow higher power."""
        gp = link_budget_compliance(
            tx_power_w=1.0,
            distance_m=10.0,
            freq_hz=28e9,
            scenario=ExposureScenario.GENERAL_PUBLIC,
        )
        occ = link_budget_compliance(
            tx_power_w=1.0,
            distance_m=10.0,
            freq_hz=28e9,
            scenario=ExposureScenario.OCCUPATIONAL,
        )
        assert occ["max_tx_power_w"] > gp["max_tx_power_w"]

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match="tx_power_w must be positive"):
            link_budget_compliance(tx_power_w=0, distance_m=10, freq_hz=28e9)
        with pytest.raises(ValueError, match="distance_m must be positive"):
            link_budget_compliance(tx_power_w=1, distance_m=0, freq_hz=28e9)
        # Sub-6 GHz is now supported; test a truly out-of-range frequency
        with pytest.raises(ValueError, match="outside the ICNIRP"):
            link_budget_compliance(tx_power_w=1, distance_m=10, freq_hz=1e3)  # 1 kHz < 100 kHz

    def test_dbm_conversion(self):
        """max_tx_power_dbm should match W -> dBm conversion."""
        result = link_budget_compliance(tx_power_w=1.0, distance_m=10.0, freq_hz=28e9, T0=0.4)
        expected_dbm = 10 * np.log10(result["max_tx_power_w"] * 1e3)
        assert result["max_tx_power_dbm"] == pytest.approx(expected_dbm, rel=1e-6)


# ---------------------------------------------------------------------------
# Stochastic channel generator
# ---------------------------------------------------------------------------


class TestExpandSubpaths:
    """Regression tests for _expand_subpaths with varying NumSubPaths."""

    def test_n_subpaths_exceeding_offset_table(self):
        """NumSubPaths > 20 must not cause array length mismatch.

        The mmMAGIC_UMi_NLOS preset has NumSubPaths=26, but the 3GPP
        sub-path offset table only has 20 entries. Before the fix,
        this produced mismatched az/power arrays and crashed.
        """
        from pathlib import Path

        from aegis.channel.generator import generate_channel
        from aegis.channel.presets import load_preset

        preset = load_preset("mmMAGIC_UMi_NLOS", Path("data/channel_presets"))
        paths = generate_channel(
            preset["params"],
            freq_ghz=28,
            antenna_pos=np.array([5.0, 0.0, 1.0]),
            body_center=np.array([0.0, 0.0, 0.0]),
            power_dbm=60,
            seed=42,
        )
        assert paths.n_paths > 0
        assert np.all(np.isfinite(paths.power))
        assert paths.total_power > 0

    def test_n_subpaths_10(self):
        """NumSubPaths=10 (fewer than 20) should work correctly."""
        from pathlib import Path

        from aegis.channel.generator import generate_channel
        from aegis.channel.presets import load_preset

        preset = load_preset("mmMAGIC_Indoor_LOS", Path("data/channel_presets"))
        paths = generate_channel(
            preset["params"],
            freq_ghz=28,
            antenna_pos=np.array([5.0, 0.0, 1.0]),
            body_center=np.array([0.0, 0.0, 0.0]),
            power_dbm=60,
            seed=42,
        )
        assert paths.n_paths > 0
        assert np.all(np.isfinite(paths.power))

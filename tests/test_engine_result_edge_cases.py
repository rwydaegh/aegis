"""Edge case tests for DosimetryEngine and DosimetryResult.

Covers boundary conditions, error paths, serialization roundtrips,
compliance edge cases, and coherent-specific behavior.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.engine import DosimetryEngine, coherent_sinc
from aegis.result import DosimetryResult

# Fixtures (flat_mesh, ico_mesh, engine, single_path_down, multi_path)
# are provided by conftest.py.


# ===========================================================================
# Engine: level validation
# ===========================================================================


class TestEngineLevelValidation:
    def test_level_negative_raises(self, engine, flat_mesh, single_path_down):
        with pytest.raises(ValueError, match="Fidelity level must be 0-8"):
            engine.compute(flat_mesh, single_path_down, level=-1)

    def test_level_too_high_raises(self, engine, flat_mesh, single_path_down):
        with pytest.raises(ValueError, match="Fidelity level must be 0-8"):
            engine.compute(flat_mesh, single_path_down, level=9)


# ===========================================================================
# Engine: body_mass validation
# ===========================================================================


class TestEngineBodyMassValidation:
    def test_body_mass_zero_raises(self, engine, flat_mesh, single_path_down):
        with pytest.raises(ValueError, match="body_mass must be positive"):
            engine.compute(flat_mesh, single_path_down, level=2, body_mass=0)

    def test_body_mass_negative_raises(self, engine, flat_mesh, single_path_down):
        with pytest.raises(ValueError, match="body_mass must be positive"):
            engine.compute(flat_mesh, single_path_down, level=2, body_mass=-1)


# ===========================================================================
# Engine: default level
# ===========================================================================


class TestEngineDefaultLevel:
    def test_default_is_level_2(self, engine, flat_mesh, single_path_down):
        result = engine.compute(flat_mesh, single_path_down)
        assert result.fidelity_level == 2


# ===========================================================================
# Engine: compute_with_timings
# ===========================================================================


class TestComputeWithTimings:
    def test_returns_timings_dict(self, engine, flat_mesh, single_path_down):
        result, timings = engine.compute_with_timings(flat_mesh, single_path_down, level=2)
        assert isinstance(result, DosimetryResult)
        assert isinstance(timings, dict)
        # Spatial averaging is on by default, so at least the averaging
        # timing keys should be present.
        assert "avg_build_G_4cm2_ms" in timings
        assert "avg_matvec_4cm2_ms" in timings
        # All timing values should be non-negative floats.
        for key, val in timings.items():
            assert isinstance(val, float), f"timing '{key}' should be float"
            assert val >= 0, f"timing '{key}' should be non-negative"

    def test_no_averaging_timings_when_disabled(self, engine, flat_mesh, single_path_down):
        _, timings = engine.compute_with_timings(flat_mesh, single_path_down, level=2, spatial_averaging=False)
        assert isinstance(timings, dict)
        # No averaging keys when spatial_averaging is False.
        assert "avg_build_G_4cm2_ms" not in timings


# ===========================================================================
# Engine: sweep_levels
# ===========================================================================


class TestSweepLevels:
    def test_skips_level0_when_A_ab_none(self, engine, flat_mesh, single_path_down):
        results = engine.sweep_levels(flat_mesh, single_path_down, levels=[0, 2, 3])
        assert 0 not in results
        assert 2 in results
        assert 3 in results

    def test_skips_level1_when_A_ab_none(self, engine, flat_mesh, single_path_down):
        results = engine.sweep_levels(flat_mesh, single_path_down, levels=[1, 2])
        assert 1 not in results
        assert 2 in results

    def test_explicit_levels(self, engine, flat_mesh, single_path_down):
        results = engine.sweep_levels(flat_mesh, single_path_down, levels=[2, 3, 4])
        assert set(results.keys()) == {2, 3, 4}
        for level, r in results.items():
            assert r.fidelity_level == level

    def test_coherent_level_in_sweep_skipped_without_precoder(self, engine, flat_mesh, single_path_down):
        # Level 7 requires a precoder. sweep_levels passes through to
        # compute() which will raise. Verify the behavior: sweep_levels
        # does NOT silently skip coherent levels (they are not in
        # the _requires dict), so it should raise.
        with pytest.raises((ValueError, TypeError)):
            engine.sweep_levels(flat_mesh, single_path_down, levels=[7])

    def test_default_levels_are_0_through_6(self, engine, flat_mesh, single_path_down):
        # With A_ab and D_max provided, all incoherent levels should run.
        results = engine.sweep_levels(
            flat_mesh,
            single_path_down,
            A_ab=0.001,
            D_max=1.5,
        )
        # Levels 0 and 1 require A_ab/D_max which are provided.
        # All of 0-6 should be in the results.
        assert set(results.keys()) == {0, 1, 2, 3, 4, 5, 6}


# ===========================================================================
# Engine: _body_cache_key
# ===========================================================================


class TestBodyCacheKey:
    def test_same_mesh_same_key(self, flat_mesh):
        key1 = DosimetryEngine._body_cache_key(flat_mesh)
        key2 = DosimetryEngine._body_cache_key(flat_mesh)
        assert key1 == key2

    def test_different_mesh_different_key(self, flat_mesh, ico_mesh):
        key_flat = DosimetryEngine._body_cache_key(flat_mesh)
        key_ico = DosimetryEngine._body_cache_key(ico_mesh)
        assert key_flat != key_ico


# ===========================================================================
# Engine: coherent_sinc with multi-stream precoder
# ===========================================================================


class TestCoherentSincMultiStream:
    def test_multi_stream_precoder(self, ico_mesh):
        """coherent_sinc should handle x with ndim==2 (multi-stream)."""
        n_elements = 4
        n_paths = 8
        rng = np.random.default_rng(99)

        centroids = ico_mesh.centroids
        k_hat = rng.standard_normal((n_paths, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((n_paths, 3)) + 1j * rng.standard_normal((n_paths, 3))
        element_index = rng.integers(0, n_elements, size=n_paths)

        # Multi-stream: (n_elements, 2) for 2 streams
        x_multi = rng.standard_normal((n_elements, 2)) + 1j * rng.standard_normal((n_elements, 2))
        freq_hz = 28e9

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x_multi, freq_hz)

        assert sinc.shape == (centroids.shape[0],)
        assert np.all(sinc >= 0), "incident power density must be non-negative"
        assert np.all(np.isfinite(sinc))

    def test_single_stream_matches_1d(self, ico_mesh):
        """Single column of multi-stream should match 1D precoder result."""
        n_elements = 4
        n_paths = 8
        rng = np.random.default_rng(42)

        centroids = ico_mesh.centroids
        k_hat = rng.standard_normal((n_paths, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((n_paths, 3)) + 1j * rng.standard_normal((n_paths, 3))
        element_index = rng.integers(0, n_elements, size=n_paths)
        freq_hz = 28e9

        x_1d = rng.standard_normal(n_elements) + 1j * rng.standard_normal(n_elements)
        x_2d = x_1d[:, np.newaxis]  # (n_elements, 1)

        sinc_1d = coherent_sinc(centroids, k_hat, psi, element_index, x_1d, freq_hz)
        sinc_2d = coherent_sinc(centroids, k_hat, psi, element_index, x_2d, freq_hz)

        np.testing.assert_allclose(sinc_1d, sinc_2d, rtol=1e-12)


# ===========================================================================
# Result: peak_sab on empty array
# ===========================================================================


class TestResultPeakSab:
    def test_peak_sab_empty_raises(self):
        r = DosimetryResult(sab=np.array([]), p_abs=0.0, fidelity_level=2)
        with pytest.raises(ValueError, match="empty sab"):
            _ = r.peak_sab

    def test_peak_sab_averaged_empty_raises(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([]),
        )
        with pytest.raises(ValueError, match="empty sab_averaged"):
            _ = r.peak_sab_averaged


# ===========================================================================
# Result: mean_sab
# ===========================================================================


class TestResultMeanSab:
    def test_mean_sab_normal(self):
        sab = np.array([1.0, 2.0, 3.0, 4.0])
        r = DosimetryResult(sab=sab, p_abs=2.5, fidelity_level=2)
        assert r.mean_sab == pytest.approx(2.5)

    def test_mean_sab_single(self):
        r = DosimetryResult(sab=np.array([7.0]), p_abs=7.0, fidelity_level=2)
        assert r.mean_sab == pytest.approx(7.0)


# ===========================================================================
# Result: scale()
# ===========================================================================


class TestResultScale:
    def _make_result(self):
        return DosimetryResult(
            sab=np.array([1.0, 2.0, 3.0]),
            p_abs=6.0,
            fidelity_level=3,
            sab_averaged=np.array([0.8, 1.5, 2.5]),
            sar_wb=0.01,
            sinc=np.array([2.0, 3.0, 4.0]),
            sinc_averaged=np.array([1.5, 2.5, 3.5]),
            freq_hz=28e9,
        )

    def test_scale_zero_produces_zeros(self):
        r = self._make_result()
        scaled = r.scale(0)
        np.testing.assert_array_equal(scaled.sab, np.zeros(3))
        assert scaled.p_abs == 0.0
        assert scaled.sar_wb == 0.0

    def test_scale_nan_raises(self):
        r = self._make_result()
        with pytest.raises(ValueError, match="finite"):
            r.scale(float("nan"))

    def test_scale_inf_raises(self):
        r = self._make_result()
        with pytest.raises(ValueError, match="finite"):
            r.scale(float("inf"))

    def test_scale_negative_raises(self):
        r = self._make_result()
        with pytest.raises(ValueError, match="non-negative"):
            r.scale(-1)

    def test_scale_preserves_metadata(self):
        r = self._make_result()
        scaled = r.scale(2.0)
        assert scaled.fidelity_level == 3
        assert scaled.freq_hz == 28e9

    def test_scale_one_is_identity(self):
        r = self._make_result()
        scaled = r.scale(1.0)
        np.testing.assert_allclose(scaled.sab, r.sab)
        assert scaled.p_abs == pytest.approx(r.p_abs)


# ===========================================================================
# Result: compare()
# ===========================================================================


class TestResultCompare:
    def test_compare_single_result_raises(self, engine, flat_mesh, single_path_down):
        r = engine.compute(flat_mesh, single_path_down, level=2)
        with pytest.raises(ValueError, match="at least 2"):
            DosimetryResult.compare({"only_one": r})

    def test_compare_mismatched_shapes_skips_pairwise(self):
        r1 = DosimetryResult(sab=np.array([1.0, 2.0]), p_abs=1.5, fidelity_level=2)
        r2 = DosimetryResult(sab=np.array([1.0, 2.0, 3.0]), p_abs=2.0, fidelity_level=3)
        comp = DosimetryResult.compare({"a": r1, "b": r2})

        # Pairwise metrics should be empty because shapes differ.
        assert len(comp["relative_error"]) == 0
        assert len(comp["rmse"]) == 0
        assert len(comp["max_abs_error"]) == 0
        # But per-result metrics should still be present.
        assert "a" in comp["peak_sab"]
        assert "b" in comp["peak_sab"]

    def test_compare_same_shape_has_pairwise(self, engine, flat_mesh, single_path_down):
        r2 = engine.compute(flat_mesh, single_path_down, level=2)
        r3 = engine.compute(flat_mesh, single_path_down, level=3)
        comp = DosimetryResult.compare({"l2": r2, "l3": r3})

        assert ("l2", "l3") in comp["relative_error"]
        assert ("l2", "l3") in comp["rmse"]
        assert ("l2", "l3") in comp["max_abs_error"]


# ===========================================================================
# Result: to_dict / from_dict roundtrip (including complex fields)
# ===========================================================================


class TestResultSerialization:
    def _make_complex_result(self):
        """Build a result with all fields populated, including complex arrays."""
        n = 5
        rng = np.random.default_rng(0)
        Q = rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))
        eigenvalues = rng.uniform(0, 1, size=4) + 0j
        x_star = rng.standard_normal(4) + 1j * rng.standard_normal(4)

        return DosimetryResult(
            sab=rng.uniform(0, 10, size=n),
            p_abs=5.0,
            fidelity_level=7,
            sab_averaged=rng.uniform(0, 10, size=n),
            sar_wb=0.05,
            mode="coherent",
            corrections=("fresnel", "polarisation"),
            Q=Q,
            rho=0.42,
            eigenvalues=eigenvalues,
            x_star=x_star,
            sinc=rng.uniform(0, 20, size=n),
            sinc_averaged=rng.uniform(0, 20, size=n),
            sab_1cm2_averaged=rng.uniform(0, 15, size=n),
            freq_hz=28e9,
        )

    def test_to_dict_from_dict_roundtrip(self):
        original = self._make_complex_result()
        d = original.to_dict()
        restored = DosimetryResult.from_dict(d)

        # Scalar fields
        assert restored.p_abs == pytest.approx(original.p_abs)
        assert restored.fidelity_level == original.fidelity_level
        assert restored.sar_wb == pytest.approx(original.sar_wb)
        assert restored.mode == original.mode
        assert restored.corrections == original.corrections
        assert restored.rho == pytest.approx(original.rho)
        assert restored.freq_hz == pytest.approx(original.freq_hz)

        # Real arrays
        np.testing.assert_allclose(restored.sab, original.sab)
        np.testing.assert_allclose(restored.sab_averaged, original.sab_averaged)
        np.testing.assert_allclose(restored.sinc, original.sinc)
        np.testing.assert_allclose(restored.sinc_averaged, original.sinc_averaged)
        np.testing.assert_allclose(restored.sab_1cm2_averaged, original.sab_1cm2_averaged)

        # Complex arrays
        np.testing.assert_allclose(restored.Q, original.Q)
        np.testing.assert_allclose(restored.eigenvalues, original.eigenvalues)
        np.testing.assert_allclose(restored.x_star, original.x_star)

    def test_to_json_from_json_roundtrip(self):
        original = self._make_complex_result()
        json_str = original.to_json()
        restored = DosimetryResult.from_json(json_str)

        assert restored.fidelity_level == original.fidelity_level
        assert restored.p_abs == pytest.approx(original.p_abs)
        np.testing.assert_allclose(restored.sab, original.sab)
        np.testing.assert_allclose(restored.Q, original.Q)
        np.testing.assert_allclose(restored.x_star, original.x_star)

    def test_to_dict_omits_none(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        d = r.to_dict()
        assert "Q" not in d
        assert "eigenvalues" not in d
        assert "x_star" not in d
        assert "sar_wb" not in d
        assert "mode" not in d


# ===========================================================================
# Result: evaluate_compliance
# ===========================================================================


class TestEvaluateCompliance:
    def test_without_freq_hz_raises(self):
        r = DosimetryResult(sab=np.array([10.0]), p_abs=1.0, fidelity_level=2)
        assert r.freq_hz is None
        with pytest.raises(ValueError, match="freq_hz must be set"):
            r.evaluate_compliance()

    def test_with_freq_hz_returns_compliance_result(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sab_averaged=np.array([0.5]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.freq_hz == 28e9
        assert cr.overall_pass is True  # tiny power, well under limit


# ===========================================================================
# Result: compliant_sab and compliant_sar edge cases
# ===========================================================================


class TestCompliantProperties:
    def test_compliant_sab_none_when_freq_none(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([1.0]),
            freq_hz=None,
        )
        assert r.compliant_sab is None

    def test_compliant_sab_none_when_no_averaging(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=None,
            freq_hz=28e9,
        )
        # peak_sab_averaged returns None when sab_averaged is None
        assert r.compliant_sab is None

    def test_compliant_sar_none_when_sar_none(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sar_wb=None,
        )
        assert r.compliant_sar is None

    def test_compliant_sar_true_for_small_value(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sar_wb=0.001,  # well below 0.08 W/kg limit
        )
        assert r.compliant_sar is True

    def test_compliant_sar_false_for_large_value(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=100.0,
            fidelity_level=2,
            sar_wb=10.0,  # way above 0.08 W/kg limit
        )
        assert r.compliant_sar is False


# ===========================================================================
# Result: __repr__
# ===========================================================================


class TestResultRepr:
    def test_repr_includes_level(self):
        r = DosimetryResult(sab=np.array([5.0]), p_abs=0.1, fidelity_level=3)
        text = repr(r)
        assert "level=3" in text

    def test_repr_includes_p_abs(self):
        r = DosimetryResult(sab=np.array([5.0]), p_abs=0.1, fidelity_level=3)
        text = repr(r)
        assert "p_abs=" in text

    def test_repr_includes_peak_sab(self):
        r = DosimetryResult(sab=np.array([5.0]), p_abs=0.1, fidelity_level=3)
        text = repr(r)
        assert "peak_sab=" in text

    def test_repr_includes_sar_when_present(self):
        r = DosimetryResult(sab=np.array([5.0]), p_abs=0.1, fidelity_level=3, sar_wb=0.01)
        text = repr(r)
        assert "sar_wb=" in text

    def test_repr_omits_sar_when_none(self):
        r = DosimetryResult(sab=np.array([5.0]), p_abs=0.1, fidelity_level=3)
        text = repr(r)
        assert "sar_wb" not in text

"""Edge case tests for DosimetryEngine and DosimetryResult.

Covers boundary conditions, error paths, serialization roundtrips,
compliance edge cases, and coherent-specific behavior.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from aegis.compliance import ExposureScenario
from aegis.engine import DosimetryEngine, coherent_sinc
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import SKIN_28GHZ

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

    def test_compliant_sab_none_when_freq_out_of_icnirp_range(self):
        """Sub-6 GHz frequencies are outside the ICNIRP 2020 Sab range."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([10.0]),
            freq_hz=3.5e9,
        )
        assert r.compliant_sab is None

    def test_compliant_sab_none_when_freq_above_300ghz(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([10.0]),
            freq_hz=400e9,
        )
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
# BodyMesh.from_arrays
# ===========================================================================


class TestBodyMeshFromArrays:
    """Test BodyMesh.from_arrays()."""

    def test_basic(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(vertices)
        assert body.n_triangles == 1
        assert body.name == "synthetic"
        assert body.areas[0] == pytest.approx(0.5)
        np.testing.assert_allclose(body.normals[0], [0, 0, 1])

    def test_custom_normals(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        normals = np.array([[0, 0, -1.0]])  # intentionally flipped
        body = BodyMesh.from_arrays(vertices, normals=normals)
        np.testing.assert_allclose(body.normals[0], [0, 0, -1])

    def test_custom_normals_are_normalized(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        normals = np.array([[0, 0, -5.0]])
        body = BodyMesh.from_arrays(vertices, normals=normals)
        np.testing.assert_allclose(body.normals[0], [0, 0, -1.0])

    def test_multiple_triangles(self) -> None:
        vertices = np.array(
            [
                [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                [[0, 0, 0], [0, 1, 0], [0, 0, 1]],
                [[0, 0, 0], [1, 0, 0], [0, 0, 1]],
            ],
            dtype=np.float64,
        )
        body = BodyMesh.from_arrays(vertices)
        assert body.n_triangles == 3
        assert body.centroids.shape == (3, 3)

    def test_computed_normals_are_unit(self) -> None:
        rng = np.random.default_rng(42)
        vertices = rng.standard_normal((10, 3, 3))
        body = BodyMesh.from_arrays(vertices)
        norms = np.linalg.norm(body.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_custom_name(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(vertices, name="test_mesh")
        assert body.name == "test_mesh"

    def test_wrong_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="\\(N, 3, 3\\)"):
            BodyMesh.from_arrays(np.zeros((5, 3)))

    def test_normals_shape_mismatch_raises(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        with pytest.raises(ValueError, match="normals"):
            BodyMesh.from_arrays(vertices, normals=np.zeros((2, 3)))

    def test_zero_custom_normal_gets_fallback(self) -> None:
        """Zero normals (from degenerate GLB triangles) get a unit fallback."""
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(vertices, normals=np.zeros((1, 3)))
        np.testing.assert_allclose(np.linalg.norm(body.normals, axis=1), 1.0)

    def test_compatible_with_engine(self) -> None:
        """from_arrays mesh works with DosimetryEngine."""
        vertices = np.array(
            [
                [[0, 0, 0], [0.01, 0, 0], [0, 0.01, 0]],
                [[0.01, 0, 0], [0.01, 0.01, 0], [0, 0.01, 0]],
            ],
            dtype=np.float64,
        )
        body = BodyMesh.from_arrays(vertices)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3)
        assert result.peak_sab > 0


# ===========================================================================
# LRU cache eviction
# ===========================================================================


class TestCacheEviction:
    """Test that caches are bounded and evict old entries."""

    def test_G_cache_bounded(self) -> None:
        """_G_cache never exceeds _G_CACHE_MAX entries."""
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )

        old_max = DosimetryEngine._G_CACHE_MAX
        DosimetryEngine._G_CACHE_MAX = 4
        DosimetryEngine._G_cache.clear()

        try:
            for i in range(10):
                rng = np.random.default_rng(i)
                vertices = np.zeros((5, 3, 3))
                s = 0.01
                for j in range(5):
                    cx, cy = rng.uniform(0, 0.1, 2)
                    vertices[j] = [[cx, cy, 0], [cx + s, cy, 0], [cx, cy + s, 0]]
                body = BodyMesh.from_arrays(vertices)
                engine.compute(body, paths, level=3)
                assert len(DosimetryEngine._G_cache) <= DosimetryEngine._G_CACHE_MAX
        finally:
            DosimetryEngine._G_CACHE_MAX = old_max
            DosimetryEngine._G_cache.clear()

    def test_fibonacci_cache_bounded(self) -> None:
        """_fibonacci_sphere_cache never exceeds limit."""
        from aegis.geometry.projected_area import (
            _FIBONACCI_CACHE_MAX,
            _fibonacci_sphere_cache,
            fibonacci_sphere,
        )

        _fibonacci_sphere_cache.clear()
        try:
            for n in range(1, _FIBONACCI_CACHE_MAX + 20):
                fibonacci_sphere(n)
                assert len(_fibonacci_sphere_cache) <= _FIBONACCI_CACHE_MAX
        finally:
            _fibonacci_sphere_cache.clear()


# ===========================================================================
# Integration: scale + max_compliant_power end-to-end
# ===========================================================================


class TestScaleComplianceIntegration:
    """End-to-end: compute at ref power, scale, find max compliant power."""

    def test_round_trip(self) -> None:
        """Compute at P_ref, find P_max, scale to P_max, verify compliance."""
        from aegis.compliance import max_compliant_power

        vertices = np.zeros((20, 3, 3))
        rng = np.random.default_rng(99)
        s = 0.01
        for i in range(20):
            cx, cy = rng.uniform(0, 0.1, 2)
            vertices[i] = [[cx, cy, 0], [cx + s, cy, 0], [cx, cy + s, 0]]
        body = BodyMesh.from_arrays(vertices)

        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([10.0]),  # high power -> likely over limit
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3, freq_hz=28e9)

        # Evaluate compliance at reference
        cr_ref = result.evaluate_compliance()

        # Find max compliant power
        P_ref = 1.0  # 1 W reference
        p_max = max_compliant_power(cr_ref, ref_power_w=P_ref)

        # Scale result to max compliant power
        scale_factor = p_max / P_ref
        scaled = result.scale(scale_factor)

        # At exactly P_max, the tightest check should be at the limit
        cr_scaled = scaled.evaluate_compliance()
        assert cr_scaled.overall_pass is True

        # Slightly over should fail
        over = result.scale(scale_factor * 1.01)
        cr_over = over.evaluate_compliance()
        # The tightest check should now fail (unless rounding)
        tightest = min(c.margin_db for c in cr_over.all_checks)
        assert tightest < 0.1  # very close to or below limit

    def test_already_compliant(self) -> None:
        """If already compliant, P_max >= P_ref."""
        from aegis.compliance import max_compliant_power

        body = BodyMesh.from_arrays(np.array([[[0, 0, 0], [0.01, 0, 0], [0, 0.01, 0]]], dtype=np.float64))
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([0.001]),  # very low power
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3, freq_hz=28e9)
        cr = result.evaluate_compliance()
        assert cr.overall_pass is True

        p_max = max_compliant_power(cr, ref_power_w=1.0)
        assert p_max >= 1.0


# ===========================================================================
# evaluate_compliance fallback paths
# ===========================================================================


class TestEvaluateComplianceFallbacks:
    """Test DosimetryResult.evaluate_compliance() when optional fields are None."""

    def test_fallback_to_raw_sab_when_averaged_none(self):
        """When sab_averaged is None, should use raw peak_sab (conservative)."""
        r = DosimetryResult(
            sab=np.array([15.0, 5.0, 10.0]),
            p_abs=0.5,
            fidelity_level=2,
            sab_averaged=None,
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sab_4cm2 is not None
        assert cr.sab_4cm2.value == pytest.approx(15.0)
        assert cr.overall_pass is True  # 15 < 20 limit

    def test_fallback_to_raw_sinc_when_averaged_none(self):
        """When sinc_averaged is None but sinc exists, should use raw sinc peak."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sinc=np.array([30.0]),
            sinc_averaged=None,
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sinc_local is not None
        assert cr.sinc_local.value == pytest.approx(30.0)

    def test_no_sinc_check_when_both_none(self):
        """When both sinc and sinc_averaged are None, sinc_local check is skipped."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sinc=None,
            sinc_averaged=None,
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sinc_local is None

    def test_sab_1cm2_included_above_30ghz(self):
        """sab_1cm2 check should be included for freq > 30 GHz."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sab_1cm2_averaged=np.array([5.0]),
            freq_hz=60e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sab_1cm2 is not None
        assert cr.sab_1cm2.value == pytest.approx(5.0)

    def test_sab_1cm2_skipped_below_30ghz(self):
        """sab_1cm2 check should be skipped for freq <= 30 GHz."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.001,
            fidelity_level=2,
            sab_1cm2_averaged=np.array([5.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sab_1cm2 is None

    def test_occupational_scenario(self):
        """evaluate_compliance should accept occupational scenario."""
        r = DosimetryResult(
            sab=np.array([50.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([50.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance(scenario=ExposureScenario.OCCUPATIONAL)
        assert cr.scenario == ExposureScenario.OCCUPATIONAL
        assert cr.sab_4cm2.compliant is True


# ===========================================================================
# Serialization edge cases
# ===========================================================================


class TestSerializationEdgeCases:
    def test_from_dict_ignores_unknown_keys(self):
        """Unknown keys in the dict should be silently ignored."""
        d = {
            "sab": [1.0, 2.0],
            "p_abs": 1.5,
            "fidelity_level": 2,
            "unknown_field": "should_be_ignored",
            "another_unknown": 42,
        }
        r = DosimetryResult.from_dict(d)
        assert r.p_abs == pytest.approx(1.5)
        assert r.fidelity_level == 2

    def test_from_dict_with_none_array_field(self):
        """None values for array fields should be preserved."""
        d = {
            "sab": [1.0],
            "p_abs": 1.0,
            "fidelity_level": 2,
            "sab_averaged": None,
        }
        r = DosimetryResult.from_dict(d)
        assert r.sab_averaged is None

    def test_roundtrip_with_empty_corrections(self):
        """Empty corrections tuple should roundtrip correctly."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            corrections=(),
        )
        d = r.to_dict()
        restored = DosimetryResult.from_dict(d)
        assert restored.corrections == ()

    def test_to_json_produces_valid_json(self):
        """to_json output should parse as valid JSON."""
        r = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=1.5,
            fidelity_level=3,
            sab_averaged=np.array([0.8, 1.5]),
            sinc=np.array([5.0, 6.0]),
            freq_hz=28e9,
        )
        json_str = r.to_json()
        parsed = json.loads(json_str)
        assert "sab" in parsed
        assert "freq_hz" in parsed

    def test_to_dict_complex_eigenvalues(self):
        """Complex eigenvalues should serialize as {real, imag}."""
        eigenvalues = np.array([1.0 + 0.5j, 0.5 + 0.1j])
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=7,
            eigenvalues=eigenvalues,
        )
        d = r.to_dict()
        assert "real" in d["eigenvalues"]
        assert "imag" in d["eigenvalues"]
        np.testing.assert_allclose(d["eigenvalues"]["real"], [1.0, 0.5])
        np.testing.assert_allclose(d["eigenvalues"]["imag"], [0.5, 0.1])


# ===========================================================================
# _body_cache_key translation invariance
# ===========================================================================


class TestBodyCacheKeyInvariance:
    def test_translation_invariant(self, flat_mesh):
        """Cache key should be the same for translated copies of the same mesh."""
        key_original = DosimetryEngine._body_cache_key(flat_mesh)

        offset = np.array([100.0, 200.0, 50.0])
        translated = BodyMesh(
            vertices=flat_mesh.vertices + offset,
            normals=flat_mesh.normals.copy(),
            centroids=flat_mesh.centroids + offset,
            areas=flat_mesh.areas.copy(),
            name="flat_plane_translated",
        )
        key_translated = DosimetryEngine._body_cache_key(translated)
        assert key_original == key_translated

    def test_rotation_not_invariant(self, flat_mesh):
        """Cache key should differ for rotated meshes (different centroid layout)."""
        key_original = DosimetryEngine._body_cache_key(flat_mesh)

        R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.float64)
        rotated_centroids = (R @ flat_mesh.centroids.T).T
        rotated = BodyMesh(
            vertices=flat_mesh.vertices,
            normals=flat_mesh.normals.copy(),
            centroids=rotated_centroids,
            areas=flat_mesh.areas.copy(),
            name="flat_plane_rotated",
        )
        key_rotated = DosimetryEngine._body_cache_key(rotated)
        assert key_original != key_rotated


# ===========================================================================
# _build_result NaN/Inf rejection
# ===========================================================================


class TestBuildResultValidation:
    def test_nan_sab_raises(self, engine, flat_mesh, single_path_down):
        """_build_result should reject sab arrays containing NaN."""
        sab = np.ones(flat_mesh.n_triangles)
        sab[5] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            engine._build_result(flat_mesh, single_path_down, sab, fidelity_level=2)

    def test_inf_sab_raises(self, engine, flat_mesh, single_path_down):
        """_build_result should reject sab arrays containing Inf."""
        sab = np.ones(flat_mesh.n_triangles)
        sab[10] = np.inf
        with pytest.raises(ValueError, match="non-finite"):
            engine._build_result(flat_mesh, single_path_down, sab, fidelity_level=2)

    def test_negative_inf_sab_raises(self, engine, flat_mesh, single_path_down):
        """_build_result should reject sab arrays containing -Inf."""
        sab = np.ones(flat_mesh.n_triangles)
        sab[0] = -np.inf
        with pytest.raises(ValueError, match="non-finite"):
            engine._build_result(flat_mesh, single_path_down, sab, fidelity_level=2)

    def test_valid_sab_passes(self, engine, flat_mesh, single_path_down):
        """_build_result should accept a valid sab array."""
        sab = np.ones(flat_mesh.n_triangles) * 5.0
        result = engine._build_result(flat_mesh, single_path_down, sab, fidelity_level=2)
        assert result.peak_sab == pytest.approx(5.0)


# ===========================================================================
# _sanitize_for_json
# ===========================================================================


try:
    import flask as _flask  # noqa: F401

    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False


@pytest.mark.skipif(not _HAS_FLASK, reason="flask not installed")
class TestSanitizeForJson:
    def test_nan_replaced_with_none(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        assert _sanitize_for_json(float("nan")) is None

    def test_inf_replaced_with_none(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        assert _sanitize_for_json(float("inf")) is None

    def test_neg_inf_replaced_with_none(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        assert _sanitize_for_json(float("-inf")) is None

    def test_normal_float_unchanged(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        assert _sanitize_for_json(3.14) == pytest.approx(3.14)

    def test_nested_dict(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        obj = {"a": float("inf"), "b": {"c": float("nan"), "d": 42}}
        result = _sanitize_for_json(obj)
        assert result["a"] is None
        assert result["b"]["c"] is None
        assert result["b"]["d"] == 42

    def test_nested_list(self):
        from aegis.viewer.routes.compute import _sanitize_for_json

        obj = [1.0, float("inf"), [float("nan"), 2.0]]
        result = _sanitize_for_json(obj)
        assert result[0] == 1.0
        assert result[1] is None
        assert result[2][0] is None
        assert result[2][1] == 2.0

    def test_json_dumps_safe_produces_valid_json(self):
        from aegis.viewer.routes.compute import _json_dumps_safe

        obj = {"value": float("inf"), "margin": float("nan"), "ok": 3.14}
        json_str = _json_dumps_safe(obj)
        parsed = json.loads(json_str)
        assert parsed["value"] is None
        assert parsed["margin"] is None
        assert parsed["ok"] == pytest.approx(3.14)


# ===========================================================================
# scale() with sab_1cm2_averaged
# ===========================================================================


class TestScaleWith1cm2:
    def test_scale_includes_sab_1cm2_averaged(self):
        """scale() should also scale sab_1cm2_averaged."""
        r = DosimetryResult(
            sab=np.array([10.0, 20.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_1cm2_averaged=np.array([12.0, 22.0]),
            freq_hz=60e9,
        )
        scaled = r.scale(2.0)
        np.testing.assert_allclose(scaled.sab_1cm2_averaged, [24.0, 44.0])

    def test_scale_sab_1cm2_averaged_none(self):
        """scale() with sab_1cm2_averaged=None should keep it None."""
        r = DosimetryResult(
            sab=np.array([10.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_1cm2_averaged=None,
        )
        scaled = r.scale(2.0)
        assert scaled.sab_1cm2_averaged is None


# ===========================================================================
# Result: evaluate_compliance with empty averaged arrays
# ===========================================================================


class TestEvaluateComplianceEmptyArrays:
    """Regression: np.max on empty array raises ValueError.

    evaluate_compliance must handle empty averaged arrays the same as None.
    """

    def test_empty_sab_1cm2_averaged(self):
        """Empty sab_1cm2_averaged should not raise."""
        r = DosimetryResult(
            sab=np.array([5.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_1cm2_averaged=np.array([]),
            freq_hz=30e9,
        )
        result = r.evaluate_compliance()
        assert result is not None

    def test_empty_sinc_averaged(self):
        """Empty sinc_averaged should not raise."""
        r = DosimetryResult(
            sab=np.array([5.0]),
            p_abs=1.0,
            fidelity_level=2,
            sinc_averaged=np.array([]),
            sinc=np.array([10.0]),
            freq_hz=30e9,
        )
        result = r.evaluate_compliance()
        assert result is not None

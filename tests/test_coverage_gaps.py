"""Tests for coverage gaps in recently changed code.

Covers: evaluate_compliance fallback paths, serialization edge cases,
coherent_sinc edge cases, cache key translation invariance, _build_result
NaN rejection, and _sanitize_for_json.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from aegis.engine import DosimetryEngine, coherent_sinc
from aegis.result import DosimetryResult

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
        # Should have sab_4cm2 check using raw peak (15.0)
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
        from aegis.compliance import ExposureScenario

        r = DosimetryResult(
            sab=np.array([50.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([50.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance(scenario=ExposureScenario.OCCUPATIONAL)
        assert cr.scenario == ExposureScenario.OCCUPATIONAL
        # 50 <= 100 occupational limit
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
# coherent_sinc edge cases
# ===========================================================================


class TestCoherentSincEdgeCases:
    def test_single_path_single_element(self):
        """coherent_sinc should work with a single path and element."""
        centroids = np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        x = np.array([1.0 + 0j])
        freq_hz = 28e9

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x, freq_hz)
        assert sinc.shape == (2,)
        assert np.all(sinc >= 0)
        assert np.all(np.isfinite(sinc))

    def test_zero_precoder_gives_zero(self):
        """Zero precoder should give zero incident power density."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        x = np.array([0.0 + 0j])
        freq_hz = 28e9

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x, freq_hz)
        np.testing.assert_allclose(sinc, [0.0])

    def test_multiple_elements_accumulation(self):
        """Paths from different elements should combine coherently."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0], [1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0, 1])
        x = np.array([1.0 + 0j, 1.0 + 0j])
        freq_hz = 28e9

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x, freq_hz)
        assert sinc.shape == (1,)
        assert sinc[0] > 0


# ===========================================================================
# _body_cache_key translation invariance
# ===========================================================================


class TestBodyCacheKeyInvariance:
    def test_translation_invariant(self, flat_mesh):
        """Cache key should be the same for translated copies of the same mesh."""
        key_original = DosimetryEngine._body_cache_key(flat_mesh)

        # Create a translated copy
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

        # Create a rotated copy (rotate 90 degrees around Z)
        R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.float64)
        rotated_centroids = (R @ flat_mesh.centroids.T).T
        rotated = BodyMesh(
            vertices=flat_mesh.vertices,  # not strictly correct but good enough for key test
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
            engine._build_result(
                flat_mesh,
                single_path_down,
                sab,
                fidelity_level=2,
            )

    def test_inf_sab_raises(self, engine, flat_mesh, single_path_down):
        """_build_result should reject sab arrays containing Inf."""
        sab = np.ones(flat_mesh.n_triangles)
        sab[10] = np.inf
        with pytest.raises(ValueError, match="non-finite"):
            engine._build_result(
                flat_mesh,
                single_path_down,
                sab,
                fidelity_level=2,
            )

    def test_negative_inf_sab_raises(self, engine, flat_mesh, single_path_down):
        """_build_result should reject sab arrays containing -Inf."""
        sab = np.ones(flat_mesh.n_triangles)
        sab[0] = -np.inf
        with pytest.raises(ValueError, match="non-finite"):
            engine._build_result(
                flat_mesh,
                single_path_down,
                sab,
                fidelity_level=2,
            )

    def test_valid_sab_passes(self, engine, flat_mesh, single_path_down):
        """_build_result should accept a valid sab array."""
        sab = np.ones(flat_mesh.n_triangles) * 5.0
        result = engine._build_result(
            flat_mesh,
            single_path_down,
            sab,
            fidelity_level=2,
        )
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
# accumulate_by_element edge cases
# ===========================================================================


class TestAccumulateByElement:
    def test_empty_paths(self):
        """Should produce zero G when no paths are given."""
        from aegis.coherent._accumulate import accumulate_by_element

        weighted = np.zeros((5, 0, 3), dtype=complex)
        element_index = np.array([], dtype=int)
        G = accumulate_by_element(weighted, element_index, M=5, n_elements=4)
        assert G.shape == (5, 3, 4)
        np.testing.assert_array_equal(G, 0)

    def test_single_element_single_path(self):
        """Single path to single element should accumulate correctly."""
        from aegis.coherent._accumulate import accumulate_by_element

        weighted = np.array([[[1.0 + 2j, 0.5 + 0j, 0.0 + 1j]]], dtype=complex)  # (1, 1, 3)
        element_index = np.array([0])
        G = accumulate_by_element(weighted, element_index, M=1, n_elements=1)
        assert G.shape == (1, 3, 1)
        np.testing.assert_allclose(G[0, :, 0], [1.0 + 2j, 0.5 + 0j, 0.0 + 1j])

    def test_duplicate_element_indices_accumulate(self):
        """Multiple paths to same element should be summed."""
        from aegis.coherent._accumulate import accumulate_by_element

        # Two paths both to element 0, at one triangle
        weighted = np.array(
            [
                [
                    [1.0 + 0j, 0.0, 0.0],
                    [0.0 + 0j, 1.0 + 0j, 0.0],
                ]
            ],
            dtype=complex,
        )  # (1, 2, 3)
        element_index = np.array([0, 0])
        G = accumulate_by_element(weighted, element_index, M=1, n_elements=1)
        assert G.shape == (1, 3, 1)
        np.testing.assert_allclose(G[0, :, 0], [1.0, 1.0, 0.0])


# ===========================================================================
# field_channel element_index validation
# ===========================================================================


class TestFieldChannelValidation:
    def test_out_of_range_element_index_raises(self):
        """element_index values >= n_elements should raise."""
        from aegis.coherent.field_channel import compute_field_channel

        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([5])  # out of range
        with pytest.raises(ValueError, match="element_index"):
            compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=4)

    def test_negative_element_index_raises(self):
        """Negative element_index values should raise."""
        from aegis.coherent.field_channel import compute_field_channel

        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([-1])
        with pytest.raises(ValueError, match="element_index"):
            compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=4)

    def test_valid_element_index_accepted(self):
        """Valid element_index should not raise."""
        from aegis.coherent.field_channel import compute_field_channel

        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        G = compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=1)
        assert G.shape == (1, 3, 1)


# ===========================================================================
# Import BodyMesh for fixture usage
# ===========================================================================

from aegis.geometry.mesh import BodyMesh  # noqa: E402

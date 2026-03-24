"""Edge case tests for degenerate and boundary inputs.

These tests verify AEGIS handles unusual but valid inputs correctly,
and raises clear errors for invalid inputs.
"""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


def _single_tri_mesh():
    """Single right triangle in XY plane, normal +Z, area = 0.5 m^2."""
    vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
    normals = np.array([[0, 0, 1.0]])
    centroids = np.mean(vertices, axis=1)
    areas = np.array([0.5])
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="tri")


# ---------------------------------------------------------------------------
# Single triangle body
# ---------------------------------------------------------------------------


class TestSingleTriangle:
    def test_level2_single_triangle_normal_incidence(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        expected = SKIN_28GHZ.T0  # mu=1, power=1
        np.testing.assert_allclose(result.sab, [expected], rtol=1e-10)
        assert result.p_abs == pytest.approx(expected * 0.5, rel=1e-10)

    def test_level3_single_triangle(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3)
        assert result.sab.shape == (1,)
        assert result.sab[0] > 0

    def test_averaging_single_triangle(self):
        """Averaging on a single triangle just returns itself."""
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        # With one triangle, averaged == raw
        np.testing.assert_allclose(result.sab_averaged, result.sab, rtol=1e-10)


# ---------------------------------------------------------------------------
# Zero and near-zero power
# ---------------------------------------------------------------------------


class TestZeroPower:
    def test_zero_power_gives_zero_sab(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([0.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        np.testing.assert_allclose(result.sab, 0.0, atol=1e-15)
        assert result.p_abs == pytest.approx(0.0, abs=1e-15)

    def test_tiny_power(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1e-30]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        assert result.sab[0] >= 0
        assert np.isfinite(result.sab[0])


# ---------------------------------------------------------------------------
# Many paths stress test
# ---------------------------------------------------------------------------


class TestManyPaths:
    def test_1000_paths(self):
        """Kernel should handle many paths without issues."""
        from conftest import make_icosahedron

        body = make_icosahedron()
        rng = np.random.default_rng(42)
        n = 1000
        k = rng.standard_normal((n, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        power = rng.uniform(0.01, 1.0, size=n)
        paths = PropagationPaths.from_powers(k_hat=k, power=power)

        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        assert result.sab.shape == (body.n_triangles,)
        assert np.all(result.sab >= 0)
        assert np.all(np.isfinite(result.sab))


# ---------------------------------------------------------------------------
# All back-facing
# ---------------------------------------------------------------------------


class TestAllBackFacing:
    def test_all_back_facing_gives_zero(self):
        """When all paths hit the back of every triangle, S_ab = 0."""
        body = _single_tri_mesh()  # normal = +Z
        # All paths come from -Z (back side)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, 1.0], [0.1, 0, 0.99]]),
            power=np.array([10.0, 5.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        np.testing.assert_allclose(result.sab, 0.0, atol=1e-14)


# ---------------------------------------------------------------------------
# Identical paths (superposition)
# ---------------------------------------------------------------------------


class TestSuperposition:
    def test_two_identical_paths_double_power(self):
        """Two identical paths should give 2x the S_ab of one."""
        from conftest import make_icosahedron

        body = make_icosahedron()
        k = np.array([[0, 0, -1.0]])
        p1 = PropagationPaths.from_powers(k_hat=k, power=np.array([1.0]))
        p2 = PropagationPaths.from_powers(k_hat=np.vstack([k, k]), power=np.array([1.0, 1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        r1 = engine.compute(body, p1, level=2)
        r2 = engine.compute(body, p2, level=2)
        np.testing.assert_allclose(r2.sab, 2.0 * r1.sab, rtol=1e-12)


# ---------------------------------------------------------------------------
# Frequency edge cases
# ---------------------------------------------------------------------------


class TestFrequencyEdgeCases:
    def test_high_frequency_enables_1cm2_averaging(self):
        """Above 30 GHz, 1 cm^2 averaging should be computed."""
        from aegis.tissue.dielectric import TissueModel

        tissue = TissueModel(name="test_60ghz", eps_r=8.0, sigma=30.0, freq_hz=60e9)

        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(tissue)
        result = engine.compute(body, paths, level=2, freq_hz=60e9)
        assert result.sab_1cm2_averaged is not None

    def test_low_frequency_no_1cm2_averaging(self):
        """At 28 GHz (< 30 GHz), 1 cm^2 averaging should be None."""
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        assert result.sab_1cm2_averaged is None


# ---------------------------------------------------------------------------
# PropagationPaths validation
# ---------------------------------------------------------------------------


class TestPathsValidation:
    def test_zero_direction_raises(self):
        with pytest.raises(ValueError, match="positive norm"):
            PropagationPaths.from_powers(k_hat=np.array([[0, 0, 0.0]]), power=np.array([1.0]))

    def test_negative_element_index_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            PropagationPaths(
                k_hat=np.array([[0, 0, -1.0]]),
                psi=np.array([[1.0, 0, 0]], dtype=complex),
                element_index=np.array([-1], dtype=np.intp),
                delay=np.array([0.0]),
                is_los=np.array([True]),
            )

    def test_mismatched_shapes_raises(self):
        with pytest.raises(ValueError, match="psi"):
            PropagationPaths(
                k_hat=np.array([[0, 0, -1.0]]),
                psi=np.array([[1.0, 0]], dtype=complex),  # wrong shape
                element_index=np.array([0], dtype=np.intp),
                delay=np.array([0.0]),
                is_los=np.array([True]),
            )

    def test_negative_power_clamped(self):
        """from_powers clamps negative power to zero (not an error)."""
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([-1.0]))
        assert paths.power[0] == pytest.approx(0.0, abs=1e-14)


# ---------------------------------------------------------------------------
# Engine validation
# ---------------------------------------------------------------------------


class TestEngineValidation:
    def test_level_and_mode_exclusive(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        with pytest.raises(ValueError, match="Cannot specify both"):
            engine.compute(body, paths, level=2, mode="spatial")

    def test_invalid_mode(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        with pytest.raises(ValueError, match="Unknown mode"):
            engine.compute(body, paths, mode="invalid_mode")

    def test_level8_requires_h(self):
        from aegis.precoder import Precoder

        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        with pytest.raises(ValueError, match="h"):
            engine.compute(body, paths, level=8, precoder=Precoder(x=np.array([1.0 + 0j])))

    def test_curvature_requires_H(self):
        body = _single_tri_mesh()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        with pytest.raises(ValueError, match="curvature_H"):
            engine.compute(body, paths, mode="spatial", curvature=True)

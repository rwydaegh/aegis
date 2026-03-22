"""Physics regression tests: realistic scenarios with locked-in values.

These tests verify that the dosimetry pipeline produces consistent results
across code changes. Values were computed once and verified against the
monograph. If a test fails, the physics changed: investigate before updating.
"""

import numpy as np
import pytest
from conftest import make_icosahedron

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


class TestSingleWaveFrontIllumination:
    """Single plane wave hitting a convex body from the front."""

    def test_level2_p_abs_analytical(self):
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r = engine.compute(body, paths, level=2)

        # T0 * S * A_perp(+x): compute analytically
        mu_plus = np.maximum(body.normals @ np.array([-1.0, 0.0, 0.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        expected = SKIN_28GHZ.T0 * 10.0 * A_perp
        assert r.p_abs == pytest.approx(expected, rel=1e-6)
        assert r.p_abs > 0
        # Bound: P_abs <= T0 * S * total_area
        assert r.p_abs <= SKIN_28GHZ.T0 * 10.0 * body.total_area * 1.001

    def test_level3_close_to_level2(self):
        """Level 3 (Fresnel) should differ from Level 2 (T0) by < 10%."""
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        rel_diff = abs(r3.p_abs - r2.p_abs) / r2.p_abs
        assert rel_diff < 0.10


class TestMultipathDiffuse:
    """Many paths from random directions (quasi-diffuse environment)."""

    def test_diffuse_50_paths(self):
        body = make_icosahedron()
        rng = np.random.default_rng(2026)
        N = 50
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.ones(N)
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        # For diffuse: P_abs ~ T0 * S_total * A_total / 4
        expected = SKIN_28GHZ.T0 * N * body.total_area / 4.0
        assert r2.p_abs == pytest.approx(expected, rel=0.15)
        assert abs(r3.p_abs - r2.p_abs) / r2.p_abs < 0.10


class TestCorrectionComposability:
    """Combined corrections produce physically reasonable results."""

    def test_polarisation_bounded_by_TE_TM_extremes(self):
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        power = np.array([5.0, 3.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r_te = engine.compute(body, paths, level=4, q=-1.0)
        r_avg = engine.compute(body, paths, level=4, q=0.0)
        r_tm = engine.compute(body, paths, level=4, q=1.0)

        assert r_tm.p_abs >= r_avg.p_abs
        assert r_avg.p_abs >= r_te.p_abs

    def test_all_corrections_energy_conservation(self):
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(1.0, 5.0, size=N)
        H = np.full(body.n_triangles, 10.0)

        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals,
            k_hat,
            power,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.T0,
            SKIN_28GHZ.freq_hz,
            polarisation=True,
            q=0.5,
            curvature=True,
            diffraction=True,
            curvature_H=H,
        )

        p_abs = float(np.sum(sab * body.areas))
        upper_bound = float(np.sum(power)) * body.total_area
        assert p_abs <= upper_bound
        assert p_abs > 0


class TestAggregateSpatialEquivalence:
    """Level 1 (aggregate) and Level 2 (spatial) give same P_abs."""

    def test_single_direction(self):
        body = make_icosahedron()
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)

        mu_plus = np.maximum(body.normals @ np.array([0.0, 0.0, 1.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        mean_A_perp = body.total_area / 4.0
        D = A_perp / mean_A_perp

        r1 = engine.compute(
            body,
            paths,
            level=1,
            A_ab=body.total_area,
            D_table=np.array([D]),
            D_dirs=np.array([[0.0, 0.0, 1.0]]),
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)

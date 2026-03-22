"""Cross-level physics consistency tests."""

import numpy as np
import pytest
from conftest import make_icosahedron

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


class TestAggregateSpatialConsistency:
    """Level 1 and Level 2 must give the same total absorbed power."""

    def test_p_abs_matches_with_correct_A_ab_and_D(self):
        """With correct A_ab and directivity, L1 P_abs == L2 P_abs."""
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)

        mu_plus = np.maximum(body.normals @ np.array([-1.0, 0.0, 0.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        mean_A_perp = body.total_area / 4.0
        D_val = A_perp / mean_A_perp

        r1 = engine.compute(
            body,
            paths,
            level=1,
            A_ab=body.total_area,
            D_table=np.array([D_val]),
            D_dirs=np.array([[1.0, 0.0, 0.0]]),
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)

    def test_p_abs_multi_path(self):
        """Multi-path: L1 P_abs == L2 P_abs with per-path directivity."""
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)

        D_vals = np.zeros(N)
        mean_A_perp = body.total_area / 4.0
        for i in range(N):
            mu_plus = np.maximum(body.normals @ (-k_hat[i]), 0.0)
            D_vals[i] = float(np.sum(mu_plus * body.areas)) / mean_A_perp

        r1 = engine.compute(
            body,
            paths,
            level=1,
            A_ab=body.total_area,
            D_table=D_vals,
            D_dirs=k_hat,
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)

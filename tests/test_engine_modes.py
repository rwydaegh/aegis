"""Tests for mode-based engine API."""

import numpy as np
import pytest
from conftest import make_icosahedron

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def setup():
    body = make_icosahedron()
    rng = np.random.default_rng(77)
    N = 15
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=N)
    paths = PropagationPaths.from_powers(k_hat, power)
    engine = DosimetryEngine(SKIN_28GHZ)
    return engine, body, paths


class TestModeAPI:
    def test_spatial_default_matches_level3(self, setup):
        engine, body, paths = setup
        # Levels 2-4 are ReLU (no shadow gate); the spatial-mode identity holds
        # only for diffraction_model="none" (the engine default is now "fock").
        r_mode = engine.compute(body, paths, mode="spatial", diffraction_model="none")
        r_level = engine.compute(body, paths, level=3)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_spatial_fresnel_off_matches_level2(self, setup):
        engine, body, paths = setup
        r_mode = engine.compute(body, paths, mode="spatial", fresnel=False, diffraction_model="none")
        r_level = engine.compute(body, paths, level=2)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_spatial_with_polarisation_matches_level4(self, setup):
        engine, body, paths = setup
        r_mode = engine.compute(body, paths, mode="spatial", polarisation=True, q=0.5, diffraction_model="none")
        r_level = engine.compute(body, paths, level=4, q=0.5)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_spatial_new_combination(self, setup):
        engine, body, paths = setup
        H = np.full(body.n_triangles, 5.0)
        r = engine.compute(
            body,
            paths,
            mode="spatial",
            polarisation=True,
            q=0.3,
            curvature=True,
            curvature_H=H,
        )
        assert r.sab.shape == (body.n_triangles,)
        assert r.p_abs > 0

    def test_backward_compat_level_still_works(self, setup):
        engine, body, paths = setup
        r = engine.compute(body, paths, level=2)
        assert r.fidelity_level == 2
        assert r.p_abs > 0

    def test_level_and_mode_exclusive(self, setup):
        engine, body, paths = setup
        with pytest.raises(ValueError, match="Cannot specify both"):
            engine.compute(body, paths, level=2, mode="spatial")

    def test_mode_stored_in_result(self, setup):
        engine, body, paths = setup
        r = engine.compute(body, paths, mode="spatial", polarisation=True, q=0.3)
        assert r.mode == "spatial"
        assert "polarisation" in r.corrections

    def test_compute_sab_mode_api(self, setup):
        engine, body, paths = setup
        sab_mode = engine.compute_sab(body, paths, mode="spatial", diffraction_model="none")
        sab_level = engine.compute_sab(body, paths, level=3)
        np.testing.assert_allclose(sab_mode, sab_level, rtol=1e-12)

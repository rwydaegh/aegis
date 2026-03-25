"""Tests for spatial_averaging parameter wiring in DosimetryEngine.

Verifies that spatial_averaging=False skips the expensive averaging matrix
computation and returns None for averaged fields. Default (True) preserves
backward-compatible behavior.
"""

import numpy as np
import pytest
from conftest import make_flat_mesh

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def mesh():
    return make_flat_mesh(50)


@pytest.fixture
def paths():
    return PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([1.0]),
    )


class TestSpatialAveragingDefault:
    """Default (True) should always produce averaged fields."""

    def test_default_produces_averaged(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2)
        assert result.sab_averaged is not None
        assert result.sinc_averaged is not None

    def test_explicit_true_produces_averaged(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=True)
        assert result.sab_averaged is not None
        assert result.sinc_averaged is not None

    def test_averaged_shape_matches_sab(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2)
        assert result.sab_averaged.shape == result.sab.shape
        assert result.sinc_averaged.shape == result.sinc.shape


class TestSpatialAveragingDisabled:
    """spatial_averaging=False should skip averaging."""

    def test_false_skips_averaging(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        assert result.sab_averaged is None
        assert result.sinc_averaged is None
        assert result.sab_1cm2_averaged is None

    def test_false_still_computes_sab(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        assert result.sab is not None
        assert result.p_abs > 0
        assert result.peak_sab > 0

    def test_false_still_computes_sinc(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        assert result.sinc is not None
        assert np.any(result.sinc > 0)

    def test_false_sab_matches_true(self, engine, mesh, paths):
        """Raw sab should be identical regardless of averaging flag."""
        r_on = engine.compute(mesh, paths, level=2, spatial_averaging=True)
        r_off = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        np.testing.assert_array_equal(r_on.sab, r_off.sab)
        np.testing.assert_array_equal(r_on.sinc, r_off.sinc)
        assert r_on.p_abs == r_off.p_abs

    def test_peak_sab_averaged_none_when_disabled(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        assert result.peak_sab_averaged is None


class TestSpatialAveragingAllLevels:
    """Verify the flag works across all incoherent levels."""

    def test_level2(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, spatial_averaging=False)
        assert result.sab_averaged is None

    def test_level3(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=3, spatial_averaging=False)
        assert result.sab_averaged is None

    def test_level4(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=4, spatial_averaging=False)
        assert result.sab_averaged is None

    def test_level5(self, engine, mesh, paths):
        H = np.zeros(mesh.n_triangles)
        result = engine.compute(mesh, paths, level=5, spatial_averaging=False, curvature_H=H)
        assert result.sab_averaged is None

    def test_level6(self, engine, mesh, paths):
        H = np.zeros(mesh.n_triangles)
        result = engine.compute(mesh, paths, level=6, spatial_averaging=False, curvature_H=H)
        assert result.sab_averaged is None


class TestSpatialAveragingModeAPI:
    """Verify the flag works with mode-based API."""

    def test_mode_spatial_off(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, mode="spatial", spatial_averaging=False)
        assert result.sab_averaged is None

    def test_mode_spatial_on(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, mode="spatial", spatial_averaging=True)
        assert result.sab_averaged is not None

    def test_mode_bound(self, engine, mesh, paths):
        result = engine.compute(
            mesh,
            paths,
            mode="bound",
            A_ab=0.01,
            D_max=2.0,
            spatial_averaging=False,
        )
        assert result.sab_averaged is None


class TestSpatialAveragingComputeWithTimings:
    """Verify spatial_averaging works with compute_with_timings."""

    def test_timings_no_avg_keys_when_disabled(self, engine, mesh, paths):
        result, timings = engine.compute_with_timings(mesh, paths, level=2, spatial_averaging=False)
        assert result.sab_averaged is None
        assert "avg_build_G_4cm2_ms" not in timings
        assert "avg_matvec_4cm2_ms" not in timings

    def test_timings_has_avg_keys_when_enabled(self, engine, mesh, paths):
        result, timings = engine.compute_with_timings(mesh, paths, level=2, spatial_averaging=True)
        assert result.sab_averaged is not None
        assert "avg_build_G_4cm2_ms" in timings
        assert "avg_matvec_4cm2_ms" in timings


class TestSpatialAveragingSweepLevels:
    """Verify sweep_levels passes through spatial_averaging."""

    def test_sweep_averaging_disabled(self, engine, mesh, paths):
        results = engine.sweep_levels(mesh, paths, levels=[2, 3], spatial_averaging=False)
        for level, result in results.items():
            assert result.sab_averaged is None, f"Level {level} should have None sab_averaged"

    def test_sweep_averaging_enabled(self, engine, mesh, paths):
        results = engine.sweep_levels(mesh, paths, levels=[2, 3], spatial_averaging=True)
        for level, result in results.items():
            assert result.sab_averaged is not None, f"Level {level} should have sab_averaged"


class TestSpatialAveraging1cm2:
    """Verify 1 cm^2 averaging at >30 GHz is also gated."""

    def test_1cm2_present_above_30ghz(self, engine, mesh, paths):
        # SKIN_28GHZ is at 28 GHz, below threshold
        result = engine.compute(mesh, paths, level=2, freq_hz=40e9)
        assert result.sab_1cm2_averaged is not None

    def test_1cm2_none_when_disabled(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, freq_hz=40e9, spatial_averaging=False)
        assert result.sab_1cm2_averaged is None

    def test_1cm2_none_below_30ghz(self, engine, mesh, paths):
        result = engine.compute(mesh, paths, level=2, freq_hz=20e9)
        assert result.sab_1cm2_averaged is None

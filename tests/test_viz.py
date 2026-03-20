"""Smoke tests for visualization modules.

These tests verify that the viz functions run without error and produce
the expected output types. They don't check visual correctness (that's
what the examples are for).
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.result import DosimetryResult


@pytest.fixture
def simple_mesh():
    """A 4-triangle mesh (tetrahedron) for viz testing."""
    s = 0.1  # 10 cm scale
    v = np.array(
        [
            [0, 0, 0],
            [s, 0, 0],
            [s / 2, s, 0],
            [s / 2, s / 2, s],
        ]
    )
    triangles = [
        [v[0], v[1], v[2]],
        [v[0], v[1], v[3]],
        [v[1], v[2], v[3]],
        [v[0], v[2], v[3]],
    ]
    return np.array(triangles, dtype=np.float64)


@pytest.fixture
def simple_sab():
    """S_ab values for 4 triangles."""
    return np.array([1.0, 3.0, 0.5, 2.0])


class TestHeatmap:
    def test_plotly_returns_figure(self, simple_mesh, simple_sab, tmp_path):
        pytest.importorskip("plotly")
        from aegis.viz.heatmap import plot_heatmap

        fig = plot_heatmap(
            simple_mesh,
            simple_sab,
            backend="plotly",
            show=False,
            out_path=tmp_path / "test.html",
        )
        assert fig is not None
        assert (tmp_path / "test.html").exists()

    def test_matplotlib_returns_figure(self, simple_mesh, simple_sab, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.heatmap import plot_heatmap

        fig = plot_heatmap(
            simple_mesh,
            simple_sab,
            backend="matplotlib",
            show=False,
            out_path=tmp_path / "test.png",
        )
        assert fig is not None
        assert (tmp_path / "test.png").exists()

    def test_custom_sab_max(self, simple_mesh, simple_sab):
        from aegis.viz.heatmap import plot_heatmap

        fig = plot_heatmap(
            simple_mesh,
            simple_sab,
            backend="plotly",
            show=False,
            sab_max=10.0,
        )
        assert fig is not None

    def test_zero_sab(self, simple_mesh):
        from aegis.viz.heatmap import plot_heatmap

        sab = np.zeros(4)
        fig = plot_heatmap(
            simple_mesh,
            sab,
            backend="plotly",
            show=False,
        )
        assert fig is not None

    def test_invalid_backend(self, simple_mesh, simple_sab):
        from aegis.viz.heatmap import plot_heatmap

        with pytest.raises(ValueError, match="Unknown backend"):
            plot_heatmap(simple_mesh, simple_sab, backend="vtk", show=False)


class TestDashboard:
    def test_incoherent_dashboard(self, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.dashboard import plot_dashboard

        result = DosimetryResult(
            sab=np.array([1.0, 3.0, 0.5, 2.0]),
            p_abs=0.001,
            fidelity_level=2,
        )
        fig = plot_dashboard(
            result,
            show=False,
            out_path=tmp_path / "dash.png",
        )
        assert fig is not None
        assert (tmp_path / "dash.png").exists()

    def test_coherent_dashboard(self, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.dashboard import plot_dashboard

        result = DosimetryResult(
            sab=np.array([1.0, 3.0, 0.5, 2.0]),
            p_abs=0.001,
            fidelity_level=7,
            Q=np.eye(4, dtype=complex),
            rho=0.42,
            eigenvalues=np.array([1.0, 0.5, 0.1, 0.01]),
        )
        fig = plot_dashboard(
            result,
            show=False,
            out_path=tmp_path / "dash_coh.png",
        )
        assert fig is not None

    def test_dashboard_with_sar(self, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.dashboard import plot_dashboard

        result = DosimetryResult(
            sab=np.array([1.0, 3.0]),
            p_abs=0.001,
            fidelity_level=2,
            sar_wb=0.01,
        )
        fig = plot_dashboard(result, show=False)
        assert fig is not None

    def test_dashboard_rejects_nonpositive_body_mass(self):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.dashboard import plot_dashboard

        result = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=0.001,
            fidelity_level=2,
        )
        with pytest.raises(ValueError, match="body_mass"):
            plot_dashboard(result, body_mass=0.0, show=False)


class TestComparison:
    def test_matplotlib_comparison(self, simple_mesh, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.comparison import plot_level_comparison

        results = {
            2: np.array([1.0, 3.0, 0.5, 2.0]),
            3: np.array([1.1, 2.9, 0.6, 1.9]),
        }
        fig = plot_level_comparison(
            simple_mesh,
            results,
            backend="matplotlib",
            show=False,
            out_path=tmp_path / "comp.png",
        )
        assert fig is not None
        assert (tmp_path / "comp.png").exists()

    def test_plotly_comparison(self, simple_mesh, tmp_path):
        pytest.importorskip("plotly")
        from aegis.viz.comparison import plot_level_comparison

        results = {
            2: np.array([1.0, 3.0, 0.5, 2.0]),
            3: np.array([1.1, 2.9, 0.6, 1.9]),
        }
        fig = plot_level_comparison(
            simple_mesh,
            results,
            backend="plotly",
            show=False,
            out_path=tmp_path / "comp.html",
        )
        assert fig is not None
        assert (tmp_path / "comp.html").exists()

    def test_shared_sab_max(self, simple_mesh):
        from aegis.viz.comparison import plot_level_comparison

        results = {
            2: np.array([1.0, 3.0, 0.5, 2.0]),
            3: np.array([10.0, 20.0, 5.0, 15.0]),
        }
        fig = plot_level_comparison(
            simple_mesh,
            results,
            backend="plotly",
            show=False,
            sab_max=25.0,
        )
        assert fig is not None

    def test_single_level(self, simple_mesh):
        import matplotlib

        matplotlib.use("Agg")
        from aegis.viz.comparison import plot_level_comparison

        results = {2: np.array([1.0, 3.0, 0.5, 2.0])}
        fig = plot_level_comparison(
            simple_mesh,
            results,
            backend="matplotlib",
            show=False,
        )
        assert fig is not None

"""Tests for DosimetryResult.show() convenience method."""

import matplotlib  # noqa: I001

matplotlib.use("Agg")

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


class TestResultShow:
    """DosimetryResult.show() wraps plot_heatmap for quick viz."""

    @pytest.fixture
    def body_and_result(self):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=1)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)
        return body, result

    def test_show_returns_figure(self, body_and_result):
        """show() returns a matplotlib figure."""
        body, result = body_and_result
        fig = result.show(body, backend="matplotlib", show=False)
        import matplotlib.pyplot as plt

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_show_requires_body(self, body_and_result):
        """show() requires a BodyMesh argument."""
        _, result = body_and_result
        with pytest.raises(TypeError):
            result.show()

    def test_show_passes_kwargs(self, body_and_result):
        """Extra kwargs are forwarded to plot_heatmap."""
        body, result = body_and_result
        fig = result.show(body, backend="matplotlib", show=False, title="Test")
        import matplotlib.pyplot as plt

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_show_averaged_flag(self, body_and_result):
        """averaged=True uses sab_averaged instead of raw sab."""
        body, result = body_and_result
        fig = result.show(body, averaged=True, backend="matplotlib", show=False)
        import matplotlib.pyplot as plt

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

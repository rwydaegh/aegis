"""Tests for TissueModel.plot_spectrum() convenience method."""

import matplotlib  # noqa: I001
matplotlib.use("Agg")

import pytest

from aegis.tissue.dielectric import TissueModel


class TestTissuePlotSpectrum:
    """TissueModel.plot_spectrum() wraps plot_tissue_spectrum."""

    def test_plot_spectrum_returns_figure(self):
        tissue = TissueModel.from_params("Skin", 17.0, 25.0, 28e9)
        fig = tissue.plot_spectrum(freq_min_hz=1e9, freq_max_hz=100e9)
        import matplotlib.pyplot as plt

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_spectrum_requires_database_tissue(self):
        """plot_spectrum uses the tissue name to query the Cole-Cole database.
        A synthetic tissue not in the database should raise a clear error."""
        tissue = TissueModel.from_params("FakeTissue", 5.0, 1.0, 28e9)
        with pytest.raises((ValueError, KeyError)):
            tissue.plot_spectrum(freq_min_hz=1e9, freq_max_hz=100e9)

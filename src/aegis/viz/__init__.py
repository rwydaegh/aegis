"""Visualization: heatmaps, compliance dashboard, level comparison."""

from aegis.viz.comparison import plot_level_comparison
from aegis.viz.dashboard import plot_dashboard
from aegis.viz.frequency_plots import plot_frequency_sweep, plot_tissue_spectrum
from aegis.viz.heatmap import plot_heatmap

__all__ = [
    "plot_dashboard",
    "plot_frequency_sweep",
    "plot_heatmap",
    "plot_level_comparison",
    "plot_tissue_spectrum",
]

"""Coverage ladder figures."""

from __future__ import annotations

import pathlib
from typing import Any

import numpy as np


def plot_coverage_ladder(
    entries: list[dict[str, Any]],
    path: pathlib.Path,
    *,
    site: str,
    crop_m: int,
    frequency_hz: float,
) -> pathlib.Path:
    """Draw one site's exposure distributions at each evidence rung."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from semantic_twin.report import empirical_cdf, read_rows

    figure, panel = plt.subplots(figsize=(5.2, 4.0))
    for entry, colour in zip(entries, ("0.55", "tab:blue", "tab:red"), strict=False):
        rows = read_rows(path.parent / f"{entry['stem']}_locations.jsonl", site=site).rows
        ordered, probability = empirical_cdf(np.array([row["chi_rooftop"] for row in rows]))
        panel.step(
            ordered,
            probability,
            where="post",
            color=colour,
            linewidth=1.6,
            label=f"{100 * entry['covered_fraction_by_area']:.1f} % of area from images",
        )
    panel.set_xscale("log")
    panel.set_xlabel("rooftop susceptibility $\\chi_S$")
    panel.set_ylabel("fraction of walk locations")
    panel.set_title(
        f"{site}, {crop_m} m crop, {frequency_hz / 1e9:g} GHz\nexposure against image evidence coverage",
        fontsize=10,
    )
    panel.legend(fontsize=8, loc="lower right")
    panel.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    print(f"wrote {path}")
    return path


def plot_cross_site_ladder(
    rows: list[dict[str, Any]],
    path: pathlib.Path,
    crop_m: int,
    frequency_hz: float,
) -> pathlib.Path | None:
    """Plot exposure shift against bound area, one point per square."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, panel = plt.subplots(figsize=(5.4, 4.0))
    markers = {"walk": "o", "semantic": "s"}
    for rung, marker in markers.items():
        chosen = [row for row in rows if row["rung"] == rung and isinstance(row["covered_fraction_by_area"], float)]
        if not chosen:
            continue
        x = [100.0 * row["covered_fraction_by_area"] for row in chosen]
        y = [row["shift_db"]["chi_rooftop"]["mean_db"] for row in chosen]
        error = [row["shift_db"]["chi_rooftop"]["standard_error_db"] or 0.0 for row in chosen]
        panel.errorbar(x, y, yerr=error, fmt=marker, capsize=3, label=f"{rung} rung", linewidth=1.2, markersize=5)
        for row, px, py in zip(chosen, x, y, strict=True):
            panel.annotate(row["site"].split("_")[0], (px, py), fontsize=7, xytext=(4, 3), textcoords="offset points")
    panel.axhline(0.0, color="0.4", linewidth=0.8)
    panel.set_xlabel("percent of triangle area carrying image evidence")
    panel.set_ylabel("shift of the distribution median, dB")
    panel.set_title(
        f"{crop_m} m crop, {frequency_hz / 1e9:g} GHz, rooftop model\nexposure shift against how much of the "
        "square a camera saw",
        fontsize=10,
    )
    panel.legend(fontsize=8)
    panel.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    print(f"wrote {path}", flush=True)
    return path

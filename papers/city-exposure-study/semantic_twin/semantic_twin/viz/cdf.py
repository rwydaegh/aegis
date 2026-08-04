"""The exposure distributions the pipeline draws beside every run.

These are the quick looks, written into ``outputs/`` the moment a trace finishes,
not the polished plates in ``FIGURES/``. Both exist on purpose. A pipeline plot is
read while a sweep is running and has to be regenerable from the JSONL without
retracing, and a paper figure is drawn at the width it is placed at and read on a
printed page. ``FIGURES/POLISH_NOTES.md`` is the record of what separates the two.

One rule changed when this moved out of ``propagation/report.py``.
:func:`cross_city_cdf` no longer takes a bag of rows. It takes a
:class:`~semantic_twin.report.crosscity.PublishedAggregate`, and the only way to
make one of those is to pass the completeness gate. The eleven city figure that
showed Brussels at 3 standpoints was drawn by a function that accepted whatever it
was handed and titled the result "converged". This function cannot be handed that.
"""

from __future__ import annotations

import pathlib
from typing import Any, Mapping, Sequence

import numpy as np

from ..report.crosscity import PublishedAggregate
from ..report.rows import Row, drop_enclosed
from ..report.stats import empirical_cdf
from .provenance import FigureProvenance


def _pyplot() -> Any:
    """Matplotlib on the headless backend, imported late.

    The package promises no heavy import at module scope, and this is a module the
    Blender side of :mod:`semantic_twin.viz` imports the neighbours of.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def cross_city_cdf(
    published: PublishedAggregate,
    path: str | pathlib.Path,
    *,
    frequency_ghz: float,
    reference_s0_w_m2: float,
    crop_radius_m: float = 130.0,
    record: FigureProvenance | None = None,
) -> pathlib.Path:
    """One CDF curve per city, for the exposure ratio, the sky and the absorbed density.

    Enclosed standpoints are dropped here and not from the table, which is the one
    place the figure and the summary beside it are computed from different rows.
    On every published sweep the count dropped is zero, because the walk builder
    rejects those points at construction, so the two agree. It is worth knowing
    that they could differ.
    """
    plt = _pyplot()
    rows_by_site = {site: drop_enclosed(rows) for site, rows in published.rows().items()}
    rows_by_site = {site: rows for site, rows in rows_by_site.items() if rows}

    figure, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    order = sorted(rows_by_site, key=lambda site: float(np.median([r["chi_rooftop"] for r in rows_by_site[site]])))
    colours = plt.cm.turbo(np.linspace(0.06, 0.94, len(order)))

    for colour, site in zip(colours, order, strict=True):
        rows = rows_by_site[site]
        label = f"{site.replace('_', ' ')} ({len(rows)})"
        axes[0].step(
            *empirical_cdf([r["chi_rooftop"] for r in rows]), where="post", color=colour, label=label, linewidth=1.4
        )
        axes[1].step(*empirical_cdf([r["sky_fraction"] for r in rows]), where="post", color=colour, linewidth=1.4)
        axes[2].step(
            *empirical_cdf([r["rooftop_peak_sab_w_m2"] for r in rows]),
            where="post",
            color=colour,
            linewidth=1.4,
        )

    # Clip to the pooled 1st and 99th percentiles. A log axis stretched by a
    # couple of deep shadow outliers squashes every curve against the right edge
    # and hides the between city separation the figure exists to show.
    pooled_chi = np.concatenate([[r["chi_rooftop"] for r in v] for v in rows_by_site.values()])
    pooled_sab = np.concatenate([[r["rooftop_peak_sab_w_m2"] for r in v] for v in rows_by_site.values()])
    axes[0].set_xlim(np.quantile(pooled_chi, 0.01) * 0.7, np.quantile(pooled_chi, 0.995) * 1.4)
    axes[2].set_xlim(np.quantile(pooled_sab, 0.01) * 0.7, np.quantile(pooled_sab, 0.995) * 1.4)

    axes[0].set_xscale("log")
    axes[0].set_xlabel("rooftop susceptibility $\\chi_S$ (free space = 1)")
    axes[0].set_ylabel("fraction of walk locations")
    # Whether the directional panels are bounds or values is a property of the
    # crop, so the titles have to follow it rather than assert one case.
    status = "converged" if crop_radius_m >= 250.0 else "crop-limited upper bound"
    axes[0].set_title(f"environment side, {status}")
    axes[0].legend(fontsize=6.5, loc="lower right")
    axes[1].set_xlabel("sky fraction")
    axes[1].set_title("how much sky the pedestrian sees, converged")
    axes[2].set_xscale("log")
    axes[2].set_xlabel(f"peak $S_{{ab}}$ [W m$^{{-2}}$] at $S_0$ = {reference_s0_w_m2:g} W m$^{{-2}}$")
    axes[2].set_title(f"body side, {status}")
    for panel in axes:
        panel.grid(alpha=0.25)
        panel.set_ylim(0.0, 1.0)

    figure.suptitle(
        f"Pedestrian exposure across {len(order)} city squares, {frequency_ghz:g} GHz, identical material prior",
        fontsize=10,
    )
    figure.text(0.5, 0.005, _crop_caption(crop_radius_m), ha="center", fontsize=6.5, color="0.35")
    figure.tight_layout(rect=(0.0, 0.035, 1.0, 1.0))

    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    if record is not None:
        record.write_beside(path)
    return path


def _crop_caption(crop_radius_m: float) -> str:
    """The crop status, on the figure rather than in a note.

    A CDF on a log axis reads as an absolute claim, so the crop status has to be
    on the page. It differs by radius and the correction is not a constant offset,
    so a between site comparison at the narrow radius is not safe either.
    """
    head = (
        f"Crop radius {crop_radius_m:g} m. Rooftop and small cell susceptibility converge at 250 m, "
        "sky fraction by 100 m. "
    )
    if crop_radius_m >= 250.0:
        return head + "This run is at the converged radius."
    return head + (
        "This run is below it, so the rooftop panels are upper bounds. Measured against 250 m over "
        "nine cities the correction is 0.05 to 4.80 dB rooftop and 0.03 to 0.96 dB isotropic, so it is "
        "not a constant offset and the sites are distorted relative to each other, not merely shifted. "
        "Those cross city ranges were measured under the superseded elevation law and the corrected law "
        "cuts the rooftop crop correction by about 3 dB, MONOSTATIC_SBR.md section 2.7.1, 2026-08-02."
    )


def walk_cdf(
    rows: Sequence[Row] | Sequence[Mapping[str, Any]],
    path: str | pathlib.Path,
    *,
    reference_s0_w_m2: float,
    frequency_ghz: float,
    title_suffix: str = "",
    site: str = "Korenmarkt",
    record: FigureProvenance | None = None,
) -> pathlib.Path:
    """One walk's three views: what the square does, what the body absorbs, and where.

    The site name is an argument now. It used to be the string ``Korenmarkt`` in
    the title, on a function that ten other squares also call, which is the same
    hardcoding that put all eleven cities in a directory named for one of them.
    """
    plt = _pyplot()
    figure, axes = plt.subplots(1, 3, figsize=(11.5, 3.9))

    panel = axes[0]
    for name, label in (
        ("chi_rooftop", "macro rooftop sites"),
        ("chi_street_small_cell", "street small cells"),
        ("chi_isotropic", "isotropic"),
    ):
        panel.step(*empirical_cdf([row[name] for row in rows]), where="post", label=label)
        panel.step(
            *empirical_cdf([row[f"{name}_direct"] for row in rows]),
            where="post",
            linestyle=":",
            color=panel.lines[-1].get_color(),
            linewidth=1.0,
        )
    panel.set_xscale("log")
    panel.set_xlabel("susceptibility $\\chi_S$ (free space = 1)")
    panel.set_ylabel("fraction of walk locations")
    panel.set_title("environment side")
    panel.legend(fontsize=7, loc="lower right")
    panel.grid(alpha=0.25)

    panel = axes[1]
    for name, label in (("rooftop_peak_sab_w_m2", "peak $S_{ab}$"), ("rooftop_mean_sab_w_m2", "mean $S_{ab}$")):
        panel.step(*empirical_cdf([row[name] for row in rows]), where="post", label=label)
    panel.set_xscale("log")
    panel.set_xlabel(f"absorbed power density [W m$^{{-2}}$] at $S_0$ = {reference_s0_w_m2:g} W m$^{{-2}}$")
    panel.set_title("body side, macro rooftop illumination")
    panel.legend(fontsize=7, loc="lower right")
    panel.grid(alpha=0.25)

    panel = axes[2]
    scatter = panel.scatter(
        [row["x"] for row in rows],
        [row["y"] for row in rows],
        c=10.0 * np.log10(np.array([row["chi_rooftop"] for row in rows], dtype=np.float64)),
        s=26,
        cmap="viridis",
    )
    figure.colorbar(scatter, ax=panel, label="$10\\log_{10}\\chi_S$ [dB]")
    panel.set_aspect("equal")
    panel.set_xlabel("east [m]")
    panel.set_ylabel("north [m]")
    panel.set_title("where on the walk")
    panel.grid(alpha=0.25)

    figure.suptitle(f"{site}, {frequency_ghz:g} GHz, {len(rows)} walk locations{title_suffix}", fontsize=10)
    figure.tight_layout()

    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    if record is not None:
        record.write_beside(path)
    return path

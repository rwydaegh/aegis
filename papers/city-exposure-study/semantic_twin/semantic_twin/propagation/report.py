"""Turn the streamed per location rows into a CDF figure and its numbers.

Everything plotted here is read back from the JSONL the run wrote, so the
figure can be regenerated without retracing and the numbers behind it are on
disk next to it.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

QUANTILES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def load_rows(path: str | pathlib.Path) -> list[dict[str, Any]]:
    lines = pathlib.Path(path).read_text().strip().splitlines()
    return [json.loads(line) for line in lines if line]


def empirical_cdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sorted values and their plotting positions ``(i + 0.5)/n``."""
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return ordered, (np.arange(ordered.size) + 0.5) / ordered.size


def summarise(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"locations": len(rows)}
    for key in keys:
        values = np.array([row[key] for row in rows if key in row], dtype=np.float64)
        values = values[np.isfinite(values)]
        if values.size == 0:
            continue
        out[key] = {
            "n": int(values.size),
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
            "quantiles": {str(q): float(np.quantile(values, q)) for q in QUANTILES},
            "spread_db_p95_over_p05": float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05)))
            if np.quantile(values, 0.05) > 0.0
            else None,
        }
    return out


def split_half_stability(rows: list[dict[str, Any]], keys: list[str], *, split: str = "interleaved") -> dict[str, Any]:
    """Are there enough locations for the CDF to have settled?

    Split the walk in half and compare the two empirical distributions. This
    answers the "how many locations is enough" question by measurement rather
    than by picking a number, and the Kolmogorov statistic between the halves
    is the single number to quote.

    The two splits answer different questions and neither alone is the honest
    one. ``interleaved`` takes the even and odd indexed locations, which are
    about a walk spacing apart and therefore highly correlated, so it measures
    whether the route is sampled densely enough and it understates the true
    sampling error. ``contiguous`` takes the first and second halves of the
    route, which are different parts of the square, so its disagreement mixes
    sampling error with genuine spatial heterogeneity and it overstates. The
    true uncertainty sits between them, and both are reported.
    """
    out: dict[str, Any] = {"locations": len(rows), "split": split}
    if len(rows) < 8:
        out["note"] = "too few locations to split"
        return out
    if split == "interleaved":
        first, second = rows[0::2], rows[1::2]
    elif split == "contiguous":
        half = len(rows) // 2
        first, second = rows[:half], rows[half:]
    else:
        raise ValueError(f"unknown split {split!r}")
    for key in keys:
        a = np.array([row[key] for row in first if key in row], dtype=np.float64)
        b = np.array([row[key] for row in second if key in row], dtype=np.float64)
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if a.size < 4 or b.size < 4:
            continue
        grid = np.unique(np.concatenate([a, b]))
        cdf_a = np.searchsorted(np.sort(a), grid, side="right") / a.size
        cdf_b = np.searchsorted(np.sort(b), grid, side="right") / b.size
        quantiles = (0.1, 0.5, 0.9)
        ratios = [float(np.quantile(a, q) / np.quantile(b, q)) if np.quantile(b, q) > 0 else None for q in quantiles]
        out[key] = {
            "kolmogorov_distance": float(np.max(np.abs(cdf_a - cdf_b))),
            "median_ratio": ratios[1],
            "quantile_ratios": {str(q): r for q, r in zip(quantiles, ratios, strict=True)},
            "n_half": [int(a.size), int(b.size)],
        }
    return out


def drop_enclosed(rows: list[dict[str, Any]], *, min_sky_fraction: float = 1.0e-4) -> list[dict[str, Any]]:
    """Remove standpoints from which no ray escapes at all.

    A point with a sky fraction of exactly zero is inside geometry. It traces to
    a susceptibility orders of magnitude below its neighbours, which is not an
    exposure result but a walkability filter that let a bad standpoint through.
    :func:`semantic_twin.propagation.walk.build_walk` now rejects these at
    construction, so this is a guard for runs made before that fix and it should
    normally remove nothing. The count removed is worth reporting either way.
    """
    return [row for row in rows if row.get("sky_fraction", 1.0) >= min_sky_fraction]


def cross_city_cdf(
    rows_by_site: dict[str, list[dict[str, Any]]],
    path: str | pathlib.Path,
    *,
    frequency_ghz: float,
    reference_s0_w_m2: float,
    crop_radius_m: float = 130.0,
) -> pathlib.Path:
    """One CDF curve per city, for susceptibility and for absorbed power density."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows_by_site = {site: drop_enclosed(rows) for site, rows in rows_by_site.items() if drop_enclosed(rows)}
    figure, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    order = sorted(rows_by_site, key=lambda s: np.median([r["chi_rooftop"] for r in rows_by_site[s]]))
    colours = plt.cm.turbo(np.linspace(0.06, 0.94, len(order)))

    for colour, site in zip(colours, order, strict=True):
        rows = rows_by_site[site]
        label = f"{site.replace('_', ' ')} ({len(rows)})"
        ordered, probability = empirical_cdf(np.array([r["chi_rooftop"] for r in rows]))
        axes[0].step(ordered, probability, where="post", color=colour, label=label, linewidth=1.4)
        ordered, probability = empirical_cdf(np.array([r["sky_fraction"] for r in rows]))
        axes[1].step(ordered, probability, where="post", color=colour, linewidth=1.4)
        ordered, probability = empirical_cdf(np.array([r["rooftop_peak_sab_w_m2"] for r in rows]))
        axes[2].step(ordered, probability, where="post", color=colour, linewidth=1.4)

    # Clip to the pooled 1st and 99th percentiles. A log axis stretched by a
    # couple of deep shadow outliers squashes every curve against the right
    # edge and hides the between city separation the figure exists to show.
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
    # A CDF on a log axis reads as an absolute claim, so the crop status has to
    # be on the figure. It differs by radius, and the correction is not a constant
    # offset, so a between site comparison at the narrow radius is not safe either.
    converged = crop_radius_m >= 250.0
    caption = (
        f"Crop radius {crop_radius_m:g} m. Rooftop and small cell susceptibility converge at 250 m, "
        "sky fraction by 100 m. "
    ) + (
        "This run is at the converged radius."
        if converged
        else "This run is below it, so the rooftop panels are upper bounds. Measured against 250 m over "
        "nine cities the correction is 0.05 to 4.80 dB rooftop and 0.03 to 0.96 dB isotropic, so it is "
        "not a constant offset and the sites are distorted relative to each other, not merely shifted."
    )
    figure.text(
        0.5,
        0.005,
        caption,
        ha="center",
        fontsize=6.5,
        color="0.35",
    )
    figure.tight_layout(rect=(0.0, 0.035, 1.0, 1.0))
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path


def plot_cdf(
    rows: list[dict[str, Any]],
    path: str | pathlib.Path,
    *,
    reference_s0_w_m2: float,
    frequency_ghz: float,
    title_suffix: str = "",
) -> pathlib.Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(11.5, 3.9))

    panel = axes[0]
    for name, label in (
        ("chi_rooftop", "macro rooftop sites"),
        ("chi_street_small_cell", "street small cells"),
        ("chi_isotropic", "isotropic"),
    ):
        values = np.array([row[name] for row in rows])
        ordered, probability = empirical_cdf(values)
        panel.step(ordered, probability, where="post", label=label)
        panel.step(
            *empirical_cdf(np.array([row[f"{name}_direct"] for row in rows])),
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
    for name, label in (
        ("rooftop_peak_sab_w_m2", "peak $S_{ab}$"),
        ("rooftop_mean_sab_w_m2", "mean $S_{ab}$"),
    ):
        ordered, probability = empirical_cdf(np.array([row[name] for row in rows]))
        panel.step(ordered, probability, where="post", label=label)
    panel.set_xscale("log")
    panel.set_xlabel(f"absorbed power density [W m$^{{-2}}$] at $S_0$ = {reference_s0_w_m2:g} W m$^{{-2}}$")
    panel.set_title("body side, macro rooftop illumination")
    panel.legend(fontsize=7, loc="lower right")
    panel.grid(alpha=0.25)

    panel = axes[2]
    x = np.array([row["x"] for row in rows])
    y = np.array([row["y"] for row in rows])
    c = np.array([row["chi_rooftop"] for row in rows])
    scatter = panel.scatter(x, y, c=10.0 * np.log10(c), s=26, cmap="viridis")
    figure.colorbar(scatter, ax=panel, label="$10\\log_{10}\\chi_S$ [dB]")
    panel.set_aspect("equal")
    panel.set_xlabel("east [m]")
    panel.set_ylabel("north [m]")
    panel.set_title("where on the walk")
    panel.grid(alpha=0.25)

    figure.suptitle(
        f"Korenmarkt, {frequency_ghz:g} GHz, {len(rows)} walk locations{title_suffix}",
        fontsize=10,
    )
    figure.tight_layout()
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path

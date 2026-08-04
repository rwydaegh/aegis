"""Summaries and figures for the bystander exposure study."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from ..exposure.bystander_study import ARMS, stature_library
from ..propagation.bystander_geometry import (
    DENSITY_LADDER,
    FRUIN_WALKWAY_LOS,
    BodyLibrary,
    TransmittanceConfig,
    crowd_transmittance,
)


def _shift_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return float("nan")
    return float(10.0 * np.log10(value / reference))


def _arm_summary(
    picked: list[dict[str, Any]],
    baseline: dict[int, dict[str, Any]],
    arm: str,
    model: str,
) -> dict[str, float]:
    """Summarise one estimator arm after pairing repeat rows by location."""
    per_location: dict[int, list[float]] = {}
    for row in picked:
        per_location.setdefault(row["location"], []).append(row[f"chi_{arm}_{model}"])
    paired = [_shift_db(float(np.mean(values)), baseline[loc][f"chi_{model}"]) for loc, values in per_location.items()]
    crowded = np.array([float(np.mean(values)) for values in per_location.values()])
    plain = np.array([baseline[loc][f"chi_{model}"] for loc in per_location])
    return {
        "paired_median_shift_db": float(np.median(paired)),
        "paired_p05_shift_db": float(np.quantile(paired, 0.05)),
        "paired_p95_shift_db": float(np.quantile(paired, 0.95)),
        "distribution_median_shift_db": _shift_db(float(np.median(crowded)), float(np.median(plain))),
    }


def _ladder_entry(
    picked: list[dict[str, Any]],
    baseline: dict[int, dict[str, Any]],
    models: list[str],
    mode: str,
    density: float,
) -> dict[str, Any]:
    """Build one stature and density row without changing its field order."""
    entry: dict[str, Any] = {
        "stature_mode": mode,
        "density_per_m2": density,
        "rows": len(picked),
        "bodies_median": float(np.median([row["bodies"] for row in picked])),
        "crowd_radius_m": float(np.median([row["crowd_radius_m"] for row in picked])),
        "walkable_fraction_median": float(np.median([row["walkable_fraction"] for row in picked])),
    }
    for model in models:
        for arm in ARMS:
            entry[f"{arm}_{model}"] = _arm_summary(picked, baseline, arm, model)
        for arm in ("walkable", "nominal"):
            entry[f"{arm}_minus_full_db_{model}"] = (
                entry[f"{arm}_{model}"]["paired_median_shift_db"] - entry[f"full_{model}"]["paired_median_shift_db"]
            )
    return entry


def summarise_study(rows_path: pathlib.Path) -> dict[str, Any]:
    """Median dB shift per illumination model, density and stature mode.

    Two medians, and they are not the same question. The paired one is the
    median over standpoints of that standpoint's own ratio, which says how far a
    typical pedestrian moves. The distribution one is the ratio of the two
    medians, which says how far the published CDF moves. They separate when the
    loss is concentrated in a minority of standpoints.
    """
    rows = [json.loads(line) for line in pathlib.Path(rows_path).read_text().splitlines() if line.strip()]
    baseline = {row["location"]: row for row in rows if row["kind"] == "baseline"}
    crowd_rows = [row for row in rows if row["kind"] == "crowd"]
    models = sorted(key[4:] for key in next(iter(baseline.values())) if key.startswith("chi_"))

    entries: list[dict[str, Any]] = []
    modes = sorted({row["stature_mode"] for row in crowd_rows})
    densities = sorted({row["density_per_m2"] for row in crowd_rows})
    for mode in modes:
        for density in densities:
            picked = [r for r in crowd_rows if r["stature_mode"] == mode and r["density_per_m2"] == density]
            if not picked:
                continue
            entries.append(_ladder_entry(picked, baseline, models, mode, density))

    arriving = {
        model: {
            "below_5deg_median": float(np.median([r[f"arriving_below_5deg_{model}"] for r in baseline.values()])),
            "below_2deg_median": float(np.median([r[f"arriving_below_2deg_{model}"] for r in baseline.values()])),
        }
        for model in models
    }
    return {
        "locations": len(baseline),
        "models": models,
        "baseline_chi_median": {
            model: float(np.median([r[f"chi_{model}"] for r in baseline.values()])) for model in models
        },
        "arriving_near_horizon_share": arriving,
        "ladder": entries,
    }


def plot_study(summary: dict[str, Any], path: pathlib.Path) -> pathlib.Path:
    """Shift in median chi against crowd density, one panel per stature mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    modes = sorted({entry["stature_mode"] for entry in summary["ladder"]})
    figure, panels = plt.subplots(1, len(modes), figsize=(3.6 * len(modes) + 1.2, 3.8), sharey=True, squeeze=False)
    colours = {"isotropic": "0.35", "rooftop": "tab:blue", "street_small_cell": "tab:red"}
    for panel, mode in zip(panels[0], modes, strict=True):
        entries = sorted((e for e in summary["ladder"] if e["stature_mode"] == mode), key=lambda e: e["density_per_m2"])
        density = [e["density_per_m2"] for e in entries]
        for model in summary["models"]:
            colour = colours.get(model, None)
            panel.plot(
                density,
                [e[f"full_{model}"]["paired_median_shift_db"] for e in entries],
                "-o",
                color=colour,
                markersize=3.5,
                linewidth=1.6,
                label=f"{model}, traced crowd",
            )
            panel.plot(
                density,
                [e[f"nominal_{model}"]["paired_median_shift_db"] for e in entries],
                "--",
                color=colour,
                linewidth=1.2,
                label=f"{model}, Beer-Lambert",
            )
            panel.plot(
                density,
                [e[f"walkable_{model}"]["paired_median_shift_db"] for e in entries],
                ":",
                color=colour,
                linewidth=1.2,
                label=f"{model}, Beer-Lambert on walkable area",
            )
        for level, (module, edge) in FRUIN_WALKWAY_LOS.items():
            if min(density) <= edge <= max(density):
                panel.axvline(edge, color="0.85", linewidth=0.8, zorder=0)
                panel.annotate(
                    level, (edge, 0.02), xycoords=("data", "axes fraction"), fontsize=7, color="0.5", ha="center"
                )
        panel.axhline(0.0, color="0.6", linewidth=0.7)
        panel.set_xscale("log")
        panel.set_xlabel("crowd density (people m$^{-2}$)")
        panel.set_title(f"bystanders {mode.replace('_', ' ')}", fontsize=10)
        panel.grid(alpha=0.22)
    panels[0][0].set_ylabel("shift in median $\\chi_S$ (dB)")
    panels[0][-1].legend(fontsize=7, loc="lower left")
    figure.suptitle(
        "Korenmarkt 15 GHz: what a crowd takes off the pedestrian, Fruin walkway level of service marked",
        fontsize=10,
    )
    figure.tight_layout()
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path


def plot_mechanism(
    path: pathlib.Path,
    *,
    library: BodyLibrary,
    observer_height_m: float = 1.5,
    radius_m: float = 30.0,
    summary: dict[str, Any] | None = None,
) -> pathlib.Path:
    """Why the answer is what it is, in two panels and no traced data.

    Left, where the crowd is opaque: the Beer-Lambert factor against elevation
    for the density ladder, at both stature modes. Right, where the illumination
    is: the elevation measure of the three models, and, when a summary is
    passed, the share of ``chi`` that actually arrives from below 5 degrees once
    the square has moved the power around. The gap between those last two is the
    reason a crowd underperforms the naive prediction.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ..illumination import MODELS, elevation_band_measure, measure_below

    elevation = np.concatenate([np.linspace(0.05, 5.0, 400), np.linspace(5.0, 60.0, 200)])
    directions = np.column_stack(
        [np.cos(np.radians(elevation)), np.zeros_like(elevation), np.sin(np.radians(elevation))]
    )
    figure, (left, right) = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for mode, style in (("as_reconstructed", "--"), ("adult", "-")):
        shaped = stature_library(library, mode, seed=0)
        for density, shade in zip(DENSITY_LADDER, np.linspace(0.75, 0.0, len(DENSITY_LADDER)), strict=True):
            left.plot(
                elevation,
                crowd_transmittance(
                    directions,
                    TransmittanceConfig(
                        density_per_m2=density,
                        width_m=shaped.width_m,
                        body_height_m=shaped.stature_m,
                        observer_height_m=observer_height_m,
                        radius_m=radius_m,
                    ),
                ),
                style,
                color=str(shade),
                linewidth=1.2,
                label=f"{density:.2f} m$^{{-2}}$, {mode.replace('_', ' ')}" if density in DENSITY_LADDER[::5] else None,
            )
    left.set_xscale("log")
    left.set_xlabel("elevation above the horizon (deg)")
    left.set_ylabel("crowd transmittance")
    left.set_title("what a crowd is opaque to", fontsize=10)
    left.legend(fontsize=7, loc="lower right")
    left.grid(alpha=0.22)

    edges = np.concatenate([np.linspace(-90.0, 0.0, 19), np.geomspace(0.1, 90.0, 40)])
    centres = 0.5 * (edges[:-1] + edges[1:])
    colours = {"isotropic": "0.35", "rooftop": "tab:blue", "street_small_cell": "tab:red"}
    arriving = None if summary is None else summary["arriving_near_horizon_share"]
    for name, model in MODELS.items():
        measure = elevation_band_measure(model, edges)
        label = name
        if arriving is not None:
            label += (
                f"\n{100 * measure_below(model, 5.0):.0f} % sent below 5 deg, "
                f"{100 * arriving[name]['below_5deg_median']:.0f} % arrives"
            )
        right.plot(centres, measure / np.diff(edges), color=colours.get(name), linewidth=1.5, label=label)
    right.set_xlim(-10.0, 60.0)
    right.set_yscale("log")
    right.set_xlabel("elevation (deg)")
    right.set_ylabel("illumination measure per degree")
    right.set_title("where the illumination is, sent and arriving", fontsize=10)
    right.legend(fontsize=6.5, loc="upper right")
    right.grid(alpha=0.22)
    figure.tight_layout()
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path

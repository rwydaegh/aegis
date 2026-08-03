"""Figure 14, the exposure distribution along one walk at Korenmarkt.

    python FIGURES/make_walk_exposure_cdf.py [tag]

Reads one walk run and draws the three views of it that the paper needs: what
the square does to the arriving power density, what the body then absorbs, and
where in the square each standpoint sits. The spatial panel is the argument. The
colour is organised by place rather than scattered, and the material assignment
is uniform over the whole scene, so what separates the standpoints is where they
stand.

The default tag is the run at the current operating point, three surface
interactions on the measured ground datum and the corrected elevation law. The
figure this replaces was a hand copy of a pipeline plot from a run at six
interactions under the superseded law, and it read 12.4 dB of rooftop spread
where this one reads 8.4.

Writes PNG for reading and PDF for the paper.
"""

from __future__ import annotations

import json
import pathlib
import sys
import textwrap

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "outputs" / "exposure_korenmarkt"

#: The walk at the current operating point. AGGREGATE_REBUILD.md records what
#: the L3 tag is and GROUND_DATUM.md records the datum it runs on.
DEFAULT_STEM = "korenmarkt_walk_L3_15ghz"
MAX_BOUNCES = 3
#: The estimator this study stands on. A run whose manifest names anything else
#: predates GROUND_DATUM.md and is not the published datum.
DATUM_RULE = "lowest major walkable level"

#: One colour per illumination model, shared with figure 15 so a reader who has
#: seen one has learnt the other.
MODELS = (
    ("chi_isotropic", "isotropic", "#1f77b4"),
    ("chi_rooftop", "macro rooftop", "#d62728"),
    ("chi_street_small_cell", "street small cell", "#9467bd"),
)


def load(stem: str) -> tuple[list[dict], dict]:
    """Rows and manifest, refusing a run that is not at the operating point.

    A figure copied out of the wrong run is the failure this whole rebuild
    exists to undo, so the provenance is checked here rather than read off a
    filename by whoever opens the directory next.
    """
    rows_path = DATA / f"{stem}_locations.jsonl"
    manifest_path = DATA / f"{stem}_manifest.json"
    problems: list[str] = []
    if not rows_path.exists() or not manifest_path.exists():
        raise SystemExit(f"[refused] no run called {stem} under {DATA}")

    rows: list[dict] = []
    torn = 0
    for line in rows_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
    manifest = json.loads(manifest_path.read_text())

    if torn:
        problems.append(f"{torn} torn lines in {rows_path.name}, two writers shared one tag")
    if len(rows) != manifest["locations_traced"]:
        problems.append(f"{len(rows)} rows against {manifest['locations_traced']} traced")
    bounces = manifest["trace_config"]["max_bounces"]
    if bounces != MAX_BOUNCES:
        problems.append(f"{bounces} surface interactions, the operating point is {MAX_BOUNCES}")
    if DATUM_RULE not in str(manifest.get("ground_datum_source", "")):
        problems.append(f"ground datum from {manifest.get('ground_datum_source')!r}, not the measured rule")
    if problems:
        for line in problems:
            print(f"[refused] {line}")
        raise SystemExit("this run is not the published operating point, see above")

    print(f"  {stem}: {len(rows)} standpoints, {bounces} interactions, datum {manifest['ground_datum_m']:.3f} m")
    return rows, manifest


def empirical_cdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return ordered, (np.arange(ordered.size) + 0.5) / ordered.size


def spread_db(values: np.ndarray) -> float:
    """How much the square moves a standpoint, 5th to 95th percentile."""
    return float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05)))


def draw(rows: list[dict], manifest: dict, stem: str) -> None:
    # Three panels across two columns leaves each one 2.2 in wide, so the
    # monograph's 11 pt labels would be half the height of a panel. Everything
    # is set for the size the figure is actually printed at.
    apply_monograph_style(
        mode="png",
        extra_rc={
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.5,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "legend.fontsize": 6.6,
        },
    )
    figure, axes = plt.subplots(1, 3, figsize=fig_size_ieee(columns=2, aspect=0.42))
    frequency_ghz = manifest["trace_config"]["frequency_hz"] / 1.0e9
    reference = manifest["reference_s0_w_m2"]

    panel = axes[0]
    for key, label, colour in MODELS:
        values = np.array([row[key] for row in rows])
        panel.step(*empirical_cdf(values), where="post", color=colour, lw=1.3, label=label)
        panel.step(
            *empirical_cdf(np.array([row[f"{key}_direct"] for row in rows])),
            where="post",
            color=colour,
            lw=0.9,
            ls=(0, (1.6, 1.6)),
        )
    # Two standpoints in deep shadow drag the street model four decades left and
    # flatten every curve against the right edge, so the axis is clipped to the
    # pooled 2nd percentile and the outliers run off it.
    pooled = np.concatenate([[row[key] for row in rows] for key, _, _ in MODELS])
    panel.set_xlim(np.quantile(pooled, 0.02) * 0.6, np.max(pooled) * 1.6)
    panel.set_xscale("log")
    panel.set_xlabel("susceptibility $\\chi$ (free space = 1)")
    panel.set_ylabel("fraction of walk standpoints")
    panel.set_title("environment side", fontsize=8.5)
    dotted = plt.Line2D([], [], color="0.35", lw=0.9, ls=(0, (1.6, 1.6)))
    handles, labels = panel.get_legend_handles_labels()
    panel.legend(
        handles + [dotted],
        labels + ["no bounce (dotted)"],
        # Upper left is the corner a rising CDF leaves empty once the axis is
        # clipped off the two deep shadow standpoints.
        loc="upper left",
        # The science style ships frameon off, and an unframed legend here sits
        # on top of the street curve.
        frameon=True,
        framealpha=0.92,
        facecolor="white",
        edgecolor="0.8",
    )

    panel = axes[1]
    for key, label, colour in (
        ("rooftop_peak_sab_w_m2", "peak $S_{ab}$", "#d62728"),
        ("rooftop_mean_sab_w_m2", "mean $S_{ab}$", "#e58f7a"),
    ):
        panel.step(
            *empirical_cdf(np.array([row[key] for row in rows])), where="post", color=colour, lw=1.3, label=label
        )
    panel.set_xscale("log")
    panel.set_xlabel(f"$S_{{ab}}$ [W m$^{{-2}}$] at $S_0$ = {reference:g} W m$^{{-2}}$")
    panel.set_title("body side, rooftop illumination", fontsize=8.5)
    panel.legend(loc="upper left", frameon=True, framealpha=0.92, facecolor="white", edgecolor="0.8")

    panel = axes[2]
    x = np.array([row["x"] for row in rows])
    y = np.array([row["y"] for row in rows])
    level = 10.0 * np.log10(np.array([row["chi_rooftop"] for row in rows]))
    scatter = panel.scatter(x, y, c=level, s=11, cmap="viridis", linewidths=0.0)
    bar = figure.colorbar(scatter, ax=panel, fraction=0.046, pad=0.03)
    bar.set_label("rooftop $10\\log_{10}\\chi$ [dB]", fontsize=7)
    bar.ax.tick_params(labelsize=6.5)
    panel.set_aspect("equal")
    panel.set_xlabel("east [m]")
    panel.set_ylabel("north [m]")
    panel.set_title("where on the walk", fontsize=8.5)

    for one in axes[:2]:
        one.set_ylim(0.0, 1.0)
    for one in axes:
        one.grid(alpha=0.25)

    isotropic = spread_db(np.array([row["chi_isotropic"] for row in rows]))
    rooftop = spread_db(np.array([row["chi_rooftop"] for row in rows]))
    street = spread_db(np.array([row["chi_street_small_cell"] for row in rows]))
    figure.suptitle(
        f"One square, {len(rows)} places to stand in it: Korenmarkt at {frequency_ghz:g} GHz",
        fontsize=9.5,
    )
    caption = textwrap.fill(
        f"Where a person stands in this one square is worth {isotropic:.1f} dB isotropic, {rooftop:.1f} dB under "
        f"macro rooftop sites and {street:.1f} dB under street small cells, 5th to 95th percentile. One material "
        f"prior over the whole scene, so the spread is urban form and not material. {MAX_BOUNCES} surface "
        f"interactions, corrected elevation law, ground datum {manifest['ground_datum_m']:.2f} m measured over "
        "the walk disc.",
        width=165,
    )
    figure.text(0.5, 0.004, caption, ha="center", va="bottom", fontsize=6.2, color="0.35", linespacing=1.5)
    figure.tight_layout(rect=(0.0, 0.085, 1.0, 0.98))

    for suffix in ("png", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        figure.savefig(path, dpi=300)
        print(f"wrote {path}")
    plt.close(figure)


def main() -> int:
    stem = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STEM
    rows, manifest = load(stem)
    draw(rows, manifest, "14_exposure_cdf_korenmarkt")
    return 0


if __name__ == "__main__":
    sys.exit(main())

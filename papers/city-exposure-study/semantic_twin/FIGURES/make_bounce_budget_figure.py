"""Figure 25, the three interaction budget as a measurement.

    python FIGURES/make_bounce_budget_figure.py            # draw from the cache
    python FIGURES/make_bounce_budget_figure.py --retrace   # trace it again first

The operating point of the tracer is three surface interactions. The claim this
figure has to carry is that the number was measured rather than preferred, so
every panel is a measurement and none of them is an argument.

Top row, why three is where the power runs out, what the cut leaves in flight,
and what switching Russian roulette off does. Bottom row, what the cut costs at
each of the forty Korenmarkt standpoints, one panel per illumination model,
against the same standpoints traced to eight interactions.

Three files feed it and no number is typed in by hand.

* ``outputs/bounce_budget/korenmarkt_130m_bounce_evidence.json``, written by
  ``measure_bounce_evidence.py``. Power by depth and the repeated seed roulette
  test come from here.
* ``outputs/bounce_budget/korenmarkt_130m_budget_ladder.json``, the paired
  budget sweep with the per standpoint columns kept rather than reduced to
  quantiles, which is what makes a ladder over standpoints drawable. Written by
  ``--retrace`` below, which reproduces the sweep in the file above standpoint
  for standpoint.
* ``outputs/exposure_korenmarkt/city250_L3_*_locations.jsonl``, the eleven city
  sweep, for the one thing the budget has to be compared against: the size of
  the effect the study reports.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
BUDGET_DIR = ROOT / "outputs" / "bounce_budget"
EVIDENCE = BUDGET_DIR / "korenmarkt_130m_bounce_evidence.json"
LADDER = BUDGET_DIR / "korenmarkt_130m_budget_ladder.json"
CITIES = ROOT / "outputs" / "exposure_korenmarkt"
STEM = "25_bounce_budget"

#: Budgets as ``(max_bounces, roulette_start)``, and the reference the costs are
#: quoted against. A roulette start above the budget switches roulette off.
#: These are ``measure_bounce_evidence.BUDGETS``, repeated here so a retrace
#: cannot silently drift from the run already on disk.
BUDGETS = ((3, 3), (3, 99), (4, 3), (6, 3), (8, 99))
REFERENCE = "L8_roulette99"
#: The operating point, and the two budgets the published runs used.
LADDER_RUNGS = ("L3_roulette99", "L4_roulette3", "L6_roulette3")
RUNG_LABEL = {"L3_roulette99": "3", "L4_roulette3": "4", "L6_roulette3": "6"}

MODELS = (
    ("chi_isotropic", "isotropic", "#2f6fb5"),
    ("chi_rooftop", "macro rooftop", "#d1622b"),
    ("chi_street_small_cell", "street small cell", "#2e7d4f"),
)

INK = "#1a1a1a"
MUTED = "#8a8f98"
FILL = "#e8e4dc"
PALE = "#c9cdd3"


# --------------------------------------------------------------------------
# the trace, only used by --retrace
# --------------------------------------------------------------------------
def retrace(
    site: str = "korenmarkt",
    crop_m: int = 130,
    locations: int = 40,
    rays: int = 200_000,
    local_cells: int = 512,
    walk_radius_m: float = 90.0,
    walk_spacing_m: float = 3.0,
    seed: int = 7,
    frequency_hz: float = 15.0e9,
    variant: str = "llvm_ad_rgb",
) -> dict:
    """The cost sweep of ``measure_bounce_evidence.py``, per standpoint.

    Same walk, same stratified subset, same per standpoint seeds and the same
    budget list, so each column is paired across budgets and only the budget
    moves. The defaults are that script's defaults for the same reason.
    """
    import time

    from run_exposure import MODELS as ILLUMINATION
    from run_exposure import measure_ground_datum, site_mesh
    from semantic_twin.propagation import MitsubaGeometry, SbrTracer, TraceConfig
    from semantic_twin.propagation.scene import classify_faces, load_bindings
    from semantic_twin.propagation.walk import build_walk, stratified_subset

    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = measure_ground_datum(geometry, radius_m=walk_radius_m).z_m
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_bindings(ROOT / "config", frequency_hz)
    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=walk_radius_m,
        spacing_m=walk_spacing_m,
        seed=seed,
    )
    picks = stratified_subset(walk, locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"{site} {crop_m} m, {geometry.faces.shape[0]} triangles, datum {datum:.6f}", flush=True)

    keys = tuple(key for key, _, _ in MODELS)
    report: dict = {
        "site": site,
        "crop_radius_m": crop_m,
        "mesh": str(mesh.relative_to(ROOT)),
        "mesh_triangles": int(geometry.faces.shape[0]),
        "ground_datum_m": float(datum),
        "locations": int(picks.size),
        "rays": rays,
        "seed": seed,
        "frequency_hz": frequency_hz,
        "reference": REFERENCE,
        "note": (
            "the cost sweep of measure_bounce_evidence.py with the per standpoint columns kept, "
            "so a ladder can show the worst standpoint and not only the median"
        ),
        "budgets": {},
    }
    for max_bounces, roulette_start in BUDGETS:
        label = f"L{max_bounces}_roulette{roulette_start}"
        config = TraceConfig(
            frequency_hz=frequency_hz,
            rays=rays,
            local_cells=local_cells,
            max_bounces=max_bounces,
            roulette_start=roulette_start,
            seed=seed,
        )
        tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
        rows = []
        started = time.perf_counter()
        for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
            rows.append(tracer.trace(point, ILLUMINATION, ground_z_m=float(ground), seed=seed + index).scalars())
        entry = {key: [float(row[key]) for row in rows] for key in keys}
        for extra in ("truncated_throughput_share", "sky_fraction", "mean_bounces"):
            entry[extra] = [float(row[extra]) for row in rows]
        entry["seconds"] = time.perf_counter() - started
        report["budgets"][label] = entry
        print(
            f"  {label}: median chi_rooftop {np.median(entry['chi_rooftop']):.6f}, "
            f"truncated median {np.median(entry['truncated_throughput_share']):.6e}, "
            f"{entry['seconds']:.1f} s",
            flush=True,
        )
    LADDER.parent.mkdir(parents=True, exist_ok=True)
    LADDER.write_text(json.dumps(report, indent=2))
    print(f"wrote {LADDER}", flush=True)
    return report


# --------------------------------------------------------------------------
# the numbers
# --------------------------------------------------------------------------
def between_site_spread() -> dict[str, float]:
    """Range of the per site median of chi across the eleven squares, in dB.

    The one number the budget error has to be read against. If the choice of
    budget moved a result by anything like this, it would be a choice.
    """
    spread: dict[str, float] = {}
    for key, _, _ in MODELS:
        medians = []
        for path in sorted(CITIES.glob("city250_L3_*_locations.jsonl")):
            rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            values = [row[key] for row in rows if row.get("sky_fraction", 1.0) >= 1.0e-4]
            medians.append(float(np.median(values)))
        spread[key] = float(10.0 * np.log10(max(medians) / min(medians)))
    return spread


def seed_noise(evidence: dict) -> dict[str, float]:
    """One standpoint traced under eight independent seeds, as decibels.

    ``measure_bounce_evidence.py`` reports the relative standard deviation of
    chi over those seeds, median over four standpoints. A relative spread of
    ``r`` is ``10 log10(1 + r)`` of decibels, which puts the estimator's own
    noise on the same axis as the cost of the budget.
    """
    block = evidence["roulette_at_three_bounces"]["roulette_off"]
    return {key: float(10.0 * np.log10(1.0 + block[key]["median"])) for key, _, _ in MODELS}


# --------------------------------------------------------------------------
# the figure
# --------------------------------------------------------------------------
#: The style is drawn for a full text width figure at 11 pt. This one is an
#: IEEE two column float carrying six panels, so it is set at the size the
#: caption text around it will be printed at.
TYPE = {
    "font.size": 7.6,
    "axes.labelsize": 7.6,
    "axes.titlesize": 8.0,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 6.8,
    "lines.linewidth": 1.1,
}


def draw(evidence: dict, ladder: dict) -> None:
    apply_monograph_style(mode="png", extra_rc=TYPE)
    figure = plt.figure(figsize=fig_size_ieee(columns=2, aspect=0.64))
    grid = figure.add_gridspec(
        2,
        3,
        height_ratios=(1.0, 1.05),
        hspace=0.58,
        wspace=0.32,
        left=0.072,
        right=0.988,
        top=0.925,
        bottom=0.125,
    )
    depth_panel(figure.add_subplot(grid[0, 0]), evidence)
    truncation_panel(figure.add_subplot(grid[0, 1]), ladder)
    roulette_panel(figure.add_subplot(grid[0, 2]), evidence)

    spread = between_site_spread()
    noise = seed_noise(evidence)
    axes = [figure.add_subplot(grid[1, column]) for column in range(3)]
    for index, (axis, (key, name, colour)) in enumerate(zip(axes, MODELS, strict=True)):
        ladder_panel(axis, ladder, key, name, colour, spread[key], noise[key], column=index)

    figure.text(
        0.5,
        0.512,
        f"what stopping at three costs, at each of the same {ladder['locations']} standpoints "
        "traced to eight interactions",
        ha="center",
        va="bottom",
        fontsize=7.8,
        color=INK,
    )
    figure.text(
        0.5,
        0.487,
        f"thin line, one standpoint.    Bold, the median of {ladder['locations']}.    "
        f"Dashed, the worst of {ladder['locations']}.    "
        f"At three, every one of the {ladder['locations']} falls.",
        ha="center",
        va="bottom",
        fontsize=6.9,
        color="0.4",
    )

    # This used to be drawn under the axes at 5.4 pt, which no printed page
    # carries. It belongs in the caption, so it is reported here.
    print(
        f"  Korenmarkt, {ladder['crop_radius_m']} m crop, {ladder['frequency_hz'] / 1e9:g} GHz, "
        f"{ladder['locations']} standpoints, {ladder['rays'] // 1000}k rays each, seed {ladder['seed']}, "
        "geometric materials, so only the budget moves"
    )

    number = STEM.split("_")[0]
    taken = sorted({p.stem for p in OUT.glob(f"{number}_*")} - {STEM})
    if taken:
        print(f"[warning] figure number {number} is also used by {taken}")
    for suffix in ("pdf", "png"):
        figure.savefig(OUT / f"{STEM}.{suffix}", dpi=300)
    plt.close(figure)
    print(f"wrote {STEM}.pdf and {STEM}.png")


def depth_panel(axis, evidence: dict) -> None:
    """Share of launched power arriving at a surface at each depth.

    Every ray leaves with unit throughput, so the depth one bar is also the
    share of rays that hit anything at all, and one minus it is the share that
    leaves the square without touching a surface. The bars past depth one are
    not a partition of anything: a ray that reaches depth three was counted at
    depth one and at depth two as well.
    """
    pooled = evidence["bounce_evidence"]["pooled_at_station_positions"]
    share = np.asarray(pooled["share_of_launched_power_incident"], dtype=np.float64)
    depths = np.asarray(pooled["bounce"], dtype=int)
    escapes = 1.0 - share[0]
    beyond = float(share[3:].sum())

    axis.axvspan(3.5, 8.8, color=FILL, zorder=0)
    axis.bar([-1.1], [escapes], width=0.82, color=PALE, edgecolor=INK, linewidth=0.4, zorder=3)
    inside = depths <= 3
    axis.bar(depths[inside], share[inside], width=0.82, color=MODELS[0][2], edgecolor=INK, linewidth=0.4, zorder=3)
    axis.bar(depths[~inside], share[~inside], width=0.82, color=MODELS[1][2], edgecolor=INK, linewidth=0.4, zorder=3)
    axis.axvline(3.5, color=INK, lw=0.8, ls=(0, (4, 2)), zorder=4)

    axis.set_yscale("log")
    axis.set_ylim(3e-7, 12.0)
    axis.set_xlim(-1.8, 8.8)
    axis.set_xticks([-1.1, *depths])
    axis.set_xticklabels(["none", *[str(d) for d in depths]])
    axis.set_xlabel("interaction depth")
    axis.set_ylabel("share of launched power\narriving at that depth")
    axis.set_title("a   almost nothing gets past three", loc="left", pad=5)

    # A white plate under each figure, because at this size the depth three
    # label reaches the budget rule and the bars are only 0.82 wide.
    plate = {"fontsize": 6.8, "color": INK, "ha": "center", "va": "bottom", "zorder": 6}
    plate["bbox"] = {"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 0.6}
    for depth, value in zip(depths[:3], share[:3], strict=True):
        axis.text(depth, value * 1.8, f"{value * 100:.2g}%", **plate)
    axis.text(-1.1, escapes * 1.8, f"{escapes * 100:.0f}%", **plate)
    axis.text(
        6.15,
        1.6,
        f"past the budget:\n{beyond * 100:.2f}% of\nlaunched power",
        ha="center",
        va="top",
        fontsize=6.8,
        color=MODELS[1][2],
    )


def truncation_panel(axis, ladder: dict) -> None:
    """Throughput still travelling when the budget ran out, one dot a standpoint."""
    rungs = LADDER_RUNGS
    rng = np.random.default_rng(3)
    for position, rung in enumerate(rungs):
        values = np.asarray(ladder["budgets"][rung]["truncated_throughput_share"], dtype=np.float64)
        jitter = position + rng.uniform(-0.16, 0.16, values.size)
        axis.plot(jitter, values, ls="none", marker="o", ms=1.8, mfc=MUTED, mec="none", alpha=0.8, zorder=3)
        axis.plot(
            [position - 0.3, position + 0.3],
            [np.median(values)] * 2,
            color=INK,
            lw=1.3,
            solid_capstyle="butt",
            zorder=5,
        )
    at_three = np.asarray(ladder["budgets"][rungs[0]]["truncated_throughput_share"], dtype=np.float64)

    axis.set_yscale("log")
    axis.set_ylim(4e-6, 1.1)
    axis.set_xticks(range(len(rungs)))
    axis.set_xticklabels([RUNG_LABEL[rung] for rung in rungs])
    axis.set_xlim(-0.55, len(rungs) - 0.45)
    axis.set_xlabel("interaction budget")
    axis.set_ylabel("power at the cut,\nover power that escaped")
    axis.set_title("b   what the cut throws away", loc="left", pad=5)
    axis.text(
        -0.44,
        0.62,
        f"at three: {np.median(at_three) * 100:.2f}% of escaping power still in\n"
        f"flight at the median standpoint, {at_three.max() * 100:.1f}% at the worst.\n"
        "Deleted, never added, so $\\chi$ can only fall.",
        ha="left",
        va="top",
        fontsize=6.8,
        color=INK,
        linespacing=1.35,
    )


def roulette_panel(axis, evidence: dict) -> None:
    """Relative spread of chi over eight seeds, roulette on against off.

    Roulette is unbiased by construction, so the only thing it can move is the
    variance and the wall clock. Both were measured and neither moved.
    """
    block = evidence["roulette_at_three_bounces"]
    on, off = block["roulette_from_bounce_3"], block["roulette_off"]
    for row, (key, name, colour) in enumerate(MODELS):
        axis.plot([on[key]["median"], off[key]["median"]], [row + 0.11, row - 0.11], color=colour, lw=0.8, zorder=2)
        axis.plot(on[key]["median"], row + 0.11, marker="o", ms=3.8, mfc="white", mec=colour, mew=0.9, zorder=3)
        axis.plot(off[key]["median"], row - 0.11, marker="o", ms=3.8, color=colour, zorder=3)

    axis.set_xscale("log")
    axis.set_xlim(3e-4, 0.09)
    axis.set_ylim(-1.75, len(MODELS) - 0.35)
    axis.set_yticks(range(len(MODELS)))
    axis.set_yticklabels(["isotropic", "rooftop", "street"], fontsize=7.2)
    axis.set_xlabel(f"spread of $\\chi$ over {block['seeds']} seeds, relative")
    axis.set_title("c   roulette is off, and nothing moved", loc="left", pad=5)
    axis.legend(
        handles=[
            Line2D(
                [], [], ls="none", marker="o", ms=3.8, mfc="white", mec=INK, mew=0.9, label="roulette from bounce 3"
            ),
            Line2D([], [], ls="none", marker="o", ms=3.8, color=INK, label="roulette off"),
        ],
        loc="upper left",
        fontsize=6.8,
        handletextpad=0.3,
        borderpad=0.3,
        labelspacing=0.25,
        framealpha=0.95,
        facecolor="white",
        edgecolor="0.85",
    )
    axis.text(
        0.97,
        0.04,
        f"{block['standpoints']} standpoints, {block['seeds']} independent seeds each,\n"
        f"median over the {block['standpoints']}.\n"
        f"Wall clock {on['seconds']:.0f} s against {off['seconds']:.0f} s.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.6,
        color="0.35",
        linespacing=1.35,
    )


def ladder_panel(axis, ladder, key, name, colour, spread_db, noise_db, column) -> None:
    """Per standpoint shift against the eight interaction reference.

    Magnitude on a log axis, because the whole point is how many decades sit
    between the cost of the budget and the effect the study reports. The sign
    is not lost with it: at the operating point every standpoint falls, which
    is written on the panel.
    """
    reference = np.asarray(ladder["budgets"][ladder["reference"]][key], dtype=np.float64)
    positions = np.arange(len(LADDER_RUNGS))
    table = np.array(
        [
            10.0 * np.log10(np.asarray(ladder["budgets"][rung][key], dtype=np.float64) / reference)
            for rung in LADDER_RUNGS
        ]
    )
    magnitude = np.abs(table)
    falling = int(np.count_nonzero(table[0] < 0.0))
    standpoints = magnitude.shape[1]

    axis.axhline(spread_db, color=colour, lw=1.3, zorder=2)
    axis.axhline(0.5, color=INK, lw=0.9, ls=(0, (4, 2)), zorder=2)
    axis.axhline(noise_db, color=MUTED, lw=0.9, ls=(0, (1, 1.6)), zorder=2)
    axis.plot(positions, magnitude, color=colour, lw=0.4, alpha=0.28, zorder=3)
    axis.plot(positions, magnitude.max(axis=1), color=colour, lw=1.1, ls=(0, (3, 1.6)), zorder=5)
    axis.plot(positions, np.median(magnitude, axis=1), color=colour, lw=1.7, marker="o", ms=3.2, zorder=6)

    axis.set_yscale("log")
    axis.set_ylim(2e-4, 60.0)
    axis.set_xlim(-0.35, len(LADDER_RUNGS) - 0.6)
    axis.set_xticks(positions)
    axis.set_xticklabels([RUNG_LABEL[rung] for rung in LADDER_RUNGS])
    axis.set_xlabel("interaction budget")
    axis.set_title(f"{'def'[column]}   {name}", loc="left", pad=4, color=colour)
    if column == 0:
        axis.set_ylabel("shift against 8 interactions [dB]")
    else:
        axis.tick_params(labelleft=False)

    label = {
        "fontsize": 6.6,
        "ha": "right",
        "bbox": {"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 0.8},
    }
    axis.text(2.05, spread_db * 1.45, f"{spread_db:.2f} dB across the eleven squares", color=colour, **label)
    axis.text(-0.25, 0.6, "half a decibel", color=INK, fontsize=6.6, ha="left")
    # Above the line where the worst standpoint ends under it, below where it
    # does not, which is the street model once the budget passes three.
    clear = magnitude[-1].max() < noise_db
    axis.text(
        2.05,
        noise_db * (1.35 if clear else 0.62),
        f"{noise_db:.3f} dB, seed against seed",
        color="0.45",
        va="bottom" if clear else "top",
        **label,
    )
    # Stacked on the left above the half decibel rule. Everywhere below that rule
    # is either data or the worst standpoint curve of the street model, and a
    # white plate placed there would hide one of them.
    axis.text(
        -0.25,
        1.2,
        f"worst of the {standpoints} at three, {magnitude[0].max():.3f} dB",
        color=INK,
        va="bottom",
        ha="left",
        fontsize=6.6,
    )
    assert falling == standpoints, f"{name}: {falling} of {standpoints} fall at the operating point"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrace", action="store_true", help="run the paired budget sweep again")
    args = parser.parse_args()

    evidence = json.loads(EVIDENCE.read_text())
    if args.retrace or not LADDER.exists():
        ladder = retrace()
    else:
        ladder = json.loads(LADDER.read_text())
    draw(evidence, ladder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Figure 15, has the crop radius converged.

    python FIGURES/make_crop_convergence.py [site]

Nine crops of one square, with the standpoints held fixed inside the smallest,
so every radius scores the same observers and only the surroundings change. The
useful reading is not the curve but where it stops moving, so the lower panel is
the step change per radius against the criterion the study uses elsewhere, half
a decibel. A model whose steps have fallen under that line is converged. A model
whose steps have not is reporting a bound rather than a value.

The answer is per illumination model and not per square. The models order by how
close to the horizon they put their weight, and that is also the order of how
much crop each one needs, because a ray leaving a standing observer near the
horizon travels a long way before it rises far enough for a building of ordinary
height to intercept it.

Reads `outputs/crop_convergence/<site>_crop_convergence.json`, written by
`run_crop_convergence.py`, and refuses a sweep that is not at the operating
point of the published run.

Writes PNG for reading and PDF for the paper.
"""

from __future__ import annotations

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

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "outputs" / "crop_convergence"

DEFAULT_SITE = "korenmarkt"
MAX_BOUNCES = 3
CRITERION_DB = 0.5
#: The radius the eleven city run is published at, which this sweep is the
#: evidence for.
PUBLISHED_M = 250.0
#: Where the builds change from single to double precision, which is a real
#: discontinuity in the series and cheaper to mark than to have a reader
#: rediscover as a physical effect.
PRECISION_M = 125.0

#: Same colours as figures 14 and 17.
#: Site keys are the pipeline's. The title is for a reader.
PRETTY = {"korenmarkt": "Korenmarkt, Ghent"}

#: Colour alone does not survive a greyscale print and red against purple is the
#: pair a red-green colourblind reader loses first, so every series also carries
#: its own marker and its own dash pattern.
SERIES = (
    ("chi_isotropic_mean", "isotropic, full sphere", "#1f77b4", "o", "-"),
    ("chi_rooftop_mean", "macro rooftop, 3.1 to 60 deg", "#d62728", "s", (0, (5, 1.6))),
    ("chi_street_small_cell_mean", "street small cell, 0.95 to 33 deg", "#9467bd", "^", (0, (1.4, 1.2))),
    ("sky_fraction_mean", "sky fraction", "#4d4d4d", "D", (0, (6, 1.6, 1.4, 1.6))),
)


def load(site: str) -> dict:
    path = DATA / f"{site}_crop_convergence.json"
    if not path.exists():
        raise SystemExit(f"[refused] no sweep at {path}")
    payload = json.loads(path.read_text())
    problems: list[str] = []
    if payload.get("max_bounces") != MAX_BOUNCES:
        problems.append(f"{payload.get('max_bounces')} surface interactions, the operating point is {MAX_BOUNCES}")
    if len(payload["rows"]) < 3:
        problems.append("fewer than three radii, there is no trend to read")
    counts = {row["observers"] for row in payload["rows"]}
    if len(counts) > 1:
        problems.append(f"ragged observer counts across radii: {sorted(counts)}")
    if problems:
        for line in problems:
            print(f"[refused] {line}")
        raise SystemExit("this sweep is not the published operating point, see above")
    print(
        f"  {site}: {len(payload['rows'])} radii, {payload['rows'][0]['observers']} fixed observers, "
        f"{payload['max_bounces']} interactions"
    )
    return payload


def converged_radius(radius: np.ndarray, values: np.ndarray) -> float:
    """The smallest radius from which every later step is under the criterion."""
    step = np.abs(10.0 * np.log10(values[1:] / values[:-1]))
    for index in range(step.size):
        if np.all(step[index:] < CRITERION_DB):
            return float(radius[index])
    return float("nan")


def draw(payload: dict, site: str, stem: str) -> None:
    # The paper places this one at \columnwidth, about 3.5 in, so it is drawn at
    # 3.5 in and never scaled down. Type is set at the size it prints at.
    apply_monograph_style(
        mode="png",
        extra_rc={
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
        },
    )
    figure, (upper, lower) = plt.subplots(
        2,
        1,
        figsize=fig_size_ieee(columns=1, aspect=1.02),
        sharex=True,
        gridspec_kw={"height_ratios": [1.15, 1.0]},
    )
    rows = payload["rows"]
    radius = np.array([row["crop_radius_m"] for row in rows], dtype=float)

    converged: dict[str, float] = {}
    for key, label, colour, marker, dashes in SERIES:
        values = np.array([row[key] for row in rows], dtype=float)
        converged[label] = converged_radius(radius, values)
        # Decibels rather than a ratio on a log axis. The street model runs an
        # order of magnitude over its converged value at the narrow crop, and on
        # a ratio axis that squashes the other three onto the bottom rule.
        upper.plot(
            radius,
            10.0 * np.log10(values / values[-1]),
            color=colour,
            marker=marker,
            ls=dashes,
            lw=1.2,
            ms=3.2,
            label=label,
        )
        # Floor the step so an exactly converged pair does not send a log axis
        # to minus infinity and draw a spike where the answer stopped moving.
        step = np.maximum(np.abs(10.0 * np.log10(values[1:] / values[:-1])), 1.0e-4)
        lower.plot(radius[1:], step, color=colour, marker=marker, ls=dashes, lw=1.2, ms=3.2)

    upper.axhline(0.0, color="0.75", lw=0.8, zorder=0)
    upper.set_ylabel(r"$\chi$ above the widest crop [dB]")
    upper.set_title(f"a  {PRETTY.get(site, site)}, {rows[0]['observers']} fixed standpoints", loc="left")

    lower.set_yscale("log")
    lower.axhline(CRITERION_DB, color="0.4", ls=(0, (4, 2)), lw=1.0)
    lower.text(
        radius[-1],
        CRITERION_DB * 1.35,
        f"{CRITERION_DB} dB criterion",
        color="0.35",
        fontsize=7.0,
        ha="right",
    )
    lower.set_ylabel("step from previous crop [dB]")
    lower.set_xlabel("crop radius [m]")
    lower.set_title("b  step against the criterion", loc="left")

    for axis in (upper, lower):
        axis.axvline(PUBLISHED_M, color="0.3", ls=":", lw=1.2)
        axis.axvline(PRECISION_M, color="0.8", lw=0.8, zorder=0)
        axis.grid(alpha=0.25)
    # Vertical labels on the rules themselves, so nothing has to be squeezed
    # into a horizontal gap that a single column does not have.
    upper.text(
        PUBLISHED_M - 8,
        0.97,
        "published radius",
        transform=upper.get_xaxis_transform(),
        color="0.25",
        fontsize=7.0,
        rotation=90,
        va="top",
        ha="right",
    )
    # The precision note goes in the lower panel, where the empty corner is, so
    # it does not have to cross the street curve in the upper one.
    lower.text(
        PRECISION_M + 8,
        0.04,
        "float64 from here",
        transform=lower.get_xaxis_transform(),
        color="0.5",
        fontsize=7.0,
        va="bottom",
        ha="left",
    )

    handles, labels = upper.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        ncol=2,
        frameon=False,
        columnspacing=1.1,
        handlelength=2.6,
        borderaxespad=0.0,
        bbox_to_anchor=(0.5, 0.0),
    )
    figure.tight_layout(rect=(0.0, 0.085, 1.0, 1.0))

    # The converged radius per model used to be printed as a paragraph under the
    # axes, which is unreadable at a single column. It belongs in the caption and
    # in the body, so it is reported to the terminal instead of drawn.
    for _, label, _, _, _ in SERIES:
        print(f"  converged at {converged[label]:.0f} m: {label}")

    for suffix in ("png", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        figure.savefig(path, dpi=300)
        print(f"wrote {path}")
    plt.close(figure)


def main() -> int:
    site = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE
    draw(load(site), site, "15_crop_convergence")
    return 0


if __name__ == "__main__":
    sys.exit(main())

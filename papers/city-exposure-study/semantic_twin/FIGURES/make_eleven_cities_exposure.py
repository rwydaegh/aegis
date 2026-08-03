"""Figure 16, pedestrian exposure across eleven city squares.

    python FIGURES/make_eleven_cities_exposure.py [tag_suffix]

Reads the per site location files of one cross city sweep and refuses to draw
anything unless that sweep is complete and every site carries the same number of
standpoints. The figure this replaces was copied out of a mid sweep snapshot in
which Brussels held 3 standpoints rather than 80, and nothing on the page said
so, so the check lives here rather than in a reviewer's eye.

The default tag suffix is the rebuilt sweep. Pass a different one to draw an
older run for comparison.

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
DATA = ROOT / "outputs" / "exposure_korenmarkt"
#: The single writer sweep at a bounce budget of three, on the fixed ground
#: datum. AGGREGATE_REBUILD.md records what it replaced and why.
DEFAULT_SUFFIX = "_L3"
MAX_BOUNCES = 3

#: Sites read from a tag other than the one asked for. Empty, and it should stay
#: empty: a figure assembled from more than one sweep is how the provenance got
#: lost the first time.
OVERRIDES: dict[str, str] = {}
CROP_M = 250
FREQ_GHZ = 15.0
REFERENCE_S0_W_M2 = 1.0

#: Site order is the study's, not alphabetical.
SITES = (
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "newyork_timessquare",
    "prague_staromestske",
    "milan_duomo",
    "tokyo_hachiko",
    "toulouse_capitole",
)

#: Was Krakow and Toulouse, whose datum put the observer on a roof. GROUND_DATUM.md
#: fixed the estimator and this sweep runs on the fix, so nothing is pending. The
#: mechanism stays because a datum defect is silent in every other output.
DATUM_PENDING: tuple[str, ...] = ()

PRETTY = {
    "brussels_grandplace": "Brussels Grand-Place",
    "korenmarkt": "Ghent Korenmarkt",
    "krakow_rynek": "Krakow Rynek",
    "london_trafalgar": "London Trafalgar",
    "madrid_plazamayor": "Madrid Plaza Mayor",
    "mexico_zocalo": "Mexico City Zocalo",
    "newyork_timessquare": "New York Times Square",
    "prague_staromestske": "Prague Staromestske",
    "milan_duomo": "Milan Duomo",
    "tokyo_hachiko": "Tokyo Hachiko",
    "toulouse_capitole": "Toulouse Capitole",
}


def load_rows(path: pathlib.Path) -> tuple[list[dict], int]:
    """Rows, and the count of lines that did not parse.

    A torn line is not a curiosity. Two sweeps writing one tag interleaved their
    appends and left fragments mid file, so a file that looks the right length
    can still be short of standpoints.
    """
    rows: list[dict] = []
    torn = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
    return rows, torn


def empirical_cdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return ordered, (np.arange(ordered.size) + 0.5) / ordered.size


def gather(tag_suffix: str) -> dict[str, list[dict]]:
    """Rows per site, refusing anything short, ragged or torn.

    A site may be read from a different tag than the rest. New York's file under
    the published tag lost two standpoints to interleaved writes by two sweeps
    sharing one tag, so it is read from a re-trace instead, and the override is
    named here rather than left to whoever reads the directory listing.
    """
    prefix = f"city{CROP_M}{tag_suffix}"
    rows_by_site: dict[str, list[dict]] = {}
    problems: list[str] = []
    for site in SITES:
        path = DATA / f"{prefix}_{site}_{FREQ_GHZ:g}ghz_locations.jsonl"
        override = OVERRIDES.get(site)
        if override is not None:
            candidate = DATA / f"city{CROP_M}{override}_{site}_{FREQ_GHZ:g}ghz_locations.jsonl"
            if candidate.exists():
                path = candidate
        if not path.exists():
            problems.append(f"{site}: no file {path.name}")
            continue
        print(f"  {site:26s} <- {path.name}")
        rows, torn = load_rows(path)
        if torn:
            problems.append(f"{site}: {torn} torn lines in {path.name}")
        # Sky fraction of zero means the standpoint is inside geometry.
        rows = [r for r in rows if r.get("sky_fraction", 1.0) >= 1.0e-4]
        rows_by_site[site] = rows

    counts = sorted({len(v) for v in rows_by_site.values()})
    if len(rows_by_site) != len(SITES):
        problems.append(f"aggregate holds {len(rows_by_site)} of {len(SITES)} sites")
    if len(counts) > 1:
        problems.append(f"ragged standpoint counts across sites: {counts}")
    if problems:
        for line in problems:
            print(f"[refused] {line}")
        raise SystemExit("this sweep is not publishable, see above")
    print(f"complete: {len(rows_by_site)} sites, {counts[0]} standpoints each")
    return rows_by_site


def draw(rows_by_site: dict[str, list[dict]], stem: str) -> None:
    # Drawn at the two column width the paper places it at, 7.16 in, so nothing
    # is scaled down on the page and the type prints at the size it is set at.
    apply_monograph_style(
        mode="png",
        extra_rc={
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 6.8,
        },
    )
    figure, axes = plt.subplots(1, 3, figsize=fig_size_ieee(columns=2, aspect=0.42), sharey=True)

    order = sorted(rows_by_site, key=lambda s: np.median([r["chi_rooftop"] for r in rows_by_site[s]]))
    # Eleven curves ordered by their own median is a sequential encoding, so the
    # ramp is one that keeps its lightness order. Turbo does not: it prints as an
    # unordered jumble in greyscale and loses its middle to a red-green reader.
    # Plasma runs dark to light throughout, and the legend is in the same order
    # as the curves, so the map from name to curve survives both.
    colours = plt.cm.plasma(np.linspace(0.04, 0.84, len(order)))

    for colour, site in zip(colours, order, strict=True):
        rows = rows_by_site[site]
        pending = site in DATUM_PENDING
        # The standpoint count is the same for every square and is stated in the
        # caption, so it is not repeated eleven times in the legend.
        label = PRETTY[site] + (", datum pending" if pending else "")
        style = {
            "color": colour,
            "linewidth": 1.2,
            "linestyle": (0, (4, 1.6)) if pending else "solid",
        }
        axes[0].step(*empirical_cdf(np.array([r["chi_rooftop"] for r in rows])), where="post", label=label, **style)
        axes[1].step(*empirical_cdf(np.array([r["sky_fraction"] for r in rows])), where="post", **style)
        axes[2].step(
            *empirical_cdf(np.array([r["rooftop_peak_sab_w_m2"] for r in rows])),
            where="post",
            **style,
        )

    # A log axis stretched by a couple of deep shadow outliers squashes every
    # curve against the right edge and hides the separation the figure exists
    # to show, so clip to the pooled 1st and 99.5th percentiles.
    pooled_chi = np.concatenate([[r["chi_rooftop"] for r in v] for v in rows_by_site.values()])
    pooled_sab = np.concatenate([[r["rooftop_peak_sab_w_m2"] for r in v] for v in rows_by_site.values()])
    axes[0].set_xlim(np.quantile(pooled_chi, 0.01) * 0.7, np.quantile(pooled_chi, 0.995) * 1.4)
    axes[2].set_xlim(np.quantile(pooled_sab, 0.01) * 0.7, np.quantile(pooled_sab, 0.995) * 1.4)

    axes[0].set_xscale("log")
    # The body writes the exposure ratio as chi, so the axis writes it that way
    # too. It used to read susceptibility, which is a word the paper never uses.
    axes[0].set_xlabel(r"rooftop exposure ratio $\chi$")
    axes[0].set_ylabel("fraction of standpoints")
    axes[0].set_title("a  environment side", loc="left")
    axes[1].set_xlabel("sky fraction")
    axes[1].set_title("b  sky the pedestrian sees", loc="left")
    axes[2].set_xscale("log")
    axes[2].set_xlabel(r"peak $S_{ab}$ [W m$^{-2}$]")
    axes[2].set_title(f"c  body side, $S_0$ = {REFERENCE_S0_W_M2:g} W m$^{{-2}}$", loc="left")
    for panel in axes:
        panel.grid(alpha=0.25)
        panel.set_ylim(0.0, 1.0)

    # Eleven names do not fit inside a panel that is a third of a two column
    # float wide without sitting on the curves, so the key runs under the axes.
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        frameon=False,
        columnspacing=1.2,
        handlelength=2.2,
        borderaxespad=0.0,
        bbox_to_anchor=(0.5, 0.0),
    )
    figure.tight_layout(rect=(0.0, 0.135, 1.0, 1.0))

    # The provenance line used to be drawn under the axes at a size no printed
    # page could carry. It belongs in the caption, so it is reported here.
    print(
        f"  crop {CROP_M} m, {len(rows_by_site[order[0]])} standpoints per square, "
        f"{MAX_BOUNCES} surface interactions, corrected elevation law, per site ground datum"
    )

    for suffix in ("png", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        figure.savefig(path, dpi=300)
        print(f"wrote {path}")
    plt.close(figure)


def main() -> int:
    tag_suffix = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUFFIX
    draw(gather(tag_suffix), "16_eleven_cities_exposure")
    return 0


if __name__ == "__main__":
    sys.exit(main())

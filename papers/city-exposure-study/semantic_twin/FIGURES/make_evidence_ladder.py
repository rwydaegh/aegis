"""Figure 17, does image evidence move the exposure distribution.

    python FIGURES/make_evidence_ladder.py [tag_suffix]

Three runs on one walk, one seed and one geometry, differing only in how much of
the scene takes its material from a photograph rather than from which way the
triangle points. Left is the distribution each rung produces. Right is the paired
per standpoint shift, which is the honest half: the median barely moves, and a
minority of standpoints move by about a decibel.

The default tag suffix is the rebuilt sweep, three surface interactions on the
measured ground datum under the corrected elevation law. The figure this
replaces was a hand copy of a pipeline plot from runs that predate all three.

A fourth rung exists, at 11.02 percent of area, from gating the panorama poses on
the sky conflict test rather than on the skyline residual. It is not drawn here
because it has not been retraced at this operating point, and a figure assembled
from two sweeps is how the provenance was lost the first time.

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

DEFAULT_SUFFIX = "_L3"
MAX_BOUNCES = 3
DATUM_RULE = "lowest major walkable level"
FREQ_GHZ = 15.0

#: The ladder, in order of how much of the scene carries image evidence. The
#: run names are the pipeline's, not this figure's.
RUNGS = (
    ("korenmarkt_geometric", "no image evidence", "0.72"),
    ("korenmarkt_semantic", "one registered panorama", "0.45"),
    ("korenmarkt_walk", "eight registered stations, fused", "0.05"),
)

#: Same colours as figures 14 and 15.
MODELS = (
    ("chi_isotropic", "isotropic", "#1f77b4"),
    ("chi_rooftop", "macro rooftop", "#d62728"),
    ("chi_street_small_cell", "street small cell", "#9467bd"),
)


def load(stem: str) -> tuple[dict[int, dict], dict]:
    """Rows keyed by walk index, and the manifest, or a refusal."""
    rows_path = DATA / f"{stem}_locations.jsonl"
    manifest_path = DATA / f"{stem}_manifest.json"
    if not rows_path.exists() or not manifest_path.exists():
        raise SystemExit(f"[refused] no run called {stem} under {DATA}")
    rows: dict[int, dict] = {}
    torn = 0
    for line in rows_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            torn += 1
            continue
        rows[row["index"]] = row
    manifest = json.loads(manifest_path.read_text())
    problems: list[str] = []
    if torn:
        problems.append(f"{stem}: {torn} torn lines, two writers shared one tag")
    if manifest["trace_config"]["max_bounces"] != MAX_BOUNCES:
        problems.append(f"{stem}: {manifest['trace_config']['max_bounces']} interactions, not {MAX_BOUNCES}")
    if DATUM_RULE not in str(manifest.get("ground_datum_source", "")):
        problems.append(f"{stem}: ground datum is not the measured rule")
    if problems:
        for line in problems:
            print(f"[refused] {line}")
        raise SystemExit("this ladder is not publishable, see above")
    return rows, manifest


def gather(tag_suffix: str) -> list[dict]:
    """One entry per rung, on the standpoints all three rungs share.

    The ladder is a paired comparison, so it is only meaningful over the
    standpoints every rung traced. Pairing on the walk index rather than on
    position in the file is what makes that true even if a run is short.
    """
    entries: list[dict] = []
    for stem, evidence, colour in RUNGS:
        full = f"{stem}{tag_suffix}_{FREQ_GHZ:g}ghz"
        rows, manifest = load(full)
        entries.append(
            {
                "stem": full,
                "evidence": evidence,
                "colour": colour,
                "rows": rows,
                "covered": manifest["semantic_binding"].get("covered_fraction_by_area", 0.0),
                "seed": manifest["trace_config"]["seed"],
                "datum_m": manifest["ground_datum_m"],
            }
        )
        print(f"  {full:34s} {len(rows):4d} standpoints, {100 * entries[-1]['covered']:5.2f} % of area from images")

    shared = sorted(set.intersection(*[set(e["rows"]) for e in entries]))
    if len({len(e["rows"]) for e in entries}) > 1:
        print(f"[warn] ragged rungs, comparing on the {len(shared)} standpoints they share")
    if len({e["seed"] for e in entries}) > 1:
        raise SystemExit("[refused] the rungs do not share a seed, so a paired comparison is not available")
    for entry in entries:
        entry["index"] = shared
    print(f"paired on {len(shared)} standpoints, seed {entries[0]['seed']}")
    return entries


def empirical_cdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return ordered, (np.arange(ordered.size) + 0.5) / ordered.size


def draw(entries: list[dict], stem: str) -> None:
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
    figure, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.40))
    shared = entries[0]["index"]

    panel = axes[0]
    for entry in entries:
        values = np.array([entry["rows"][i]["chi_rooftop"] for i in shared])
        panel.step(
            *empirical_cdf(values),
            where="post",
            color=entry["colour"],
            lw=1.4,
            label=f"{entry['evidence']}, {100 * entry['covered']:.1f} % of area",
        )
    panel.set_xscale("log")
    panel.set_xlabel("rooftop susceptibility $\\chi$ (free space = 1)")
    panel.set_ylabel("fraction of walk standpoints")
    panel.set_title("the three rungs, one distribution each", fontsize=8.5)
    panel.set_ylim(0.0, 1.0)
    # A log axis two thirds of a decade wide is left with one labelled tick, so
    # the ticks are named rather than left to the default locator.
    panel.set_xticks([0.03, 0.1, 0.3])
    panel.set_xticklabels(["0.03", "0.1", "0.3"])
    panel.set_xticks([], minor=True)
    panel.legend(loc="upper left", frameon=True, framealpha=0.92, facecolor="white", edgecolor="0.8")

    # The distributions sit on top of each other, so the ladder is only readable
    # as a paired difference. This is the panel that says how big the negative
    # is and where it stops being one.
    panel = axes[1]
    base = entries[0]
    fused = entries[-1]
    counts: dict[str, int] = {}
    for key, label, colour in MODELS:
        before = np.array([base["rows"][i][key] for i in shared])
        after = np.array([fused["rows"][i][key] for i in shared])
        shift = 10.0 * np.log10(after / before)
        counts[label] = int(np.count_nonzero(np.abs(shift) > 1.0))
        panel.step(
            *empirical_cdf(shift),
            where="post",
            color=colour,
            lw=1.4,
            label=f"{label}, {counts[label]} of {len(shared)} past 1 dB",
        )
    for edge in (-1.0, 1.0):
        panel.axvline(edge, color="0.45", ls=(0, (4, 2)), lw=0.9)
    panel.text(1.05, 0.5, "1 dB", rotation=90, fontsize=6.4, color="0.45", va="center", ha="left")
    panel.set_xlabel("per standpoint shift from no evidence to fused [dB]")
    panel.set_title("what a tenth of the scene is worth", fontsize=8.5)
    panel.set_ylim(0.0, 1.0)
    panel.legend(loc="lower right", frameon=True, framealpha=0.92, facecolor="white", edgecolor="0.8")

    for one in axes:
        one.grid(alpha=0.25)

    rooftop_before = np.array([base["rows"][i]["chi_rooftop"] for i in shared])
    rooftop_after = np.array([fused["rows"][i]["chi_rooftop"] for i in shared])
    median_shift = 10.0 * np.log10(np.median(rooftop_after) / np.median(rooftop_before))
    figure.suptitle(
        f"Korenmarkt at {FREQ_GHZ:g} GHz, exposure against image evidence coverage",
        fontsize=9.5,
    )
    caption = textwrap.fill(
        f"Going from no image evidence to {100 * fused['covered']:.1f} percent of scene area moves the rooftop "
        f"distribution median by {median_shift:.2f} dB and moves {counts['macro rooftop']} of {len(shared)} "
        f"standpoints past a decibel under rooftop illumination, {counts['isotropic']} of {len(shared)} under "
        f"isotropic illumination, which is where the negative is weakest. The "
        f"ladder reaches a tenth of the scene because that is as far as street level capture gets, so it bounds "
        f"what a photograph is worth here and says nothing about a fully evidence bound scene. Same walk, same "
        f"seed, {MAX_BOUNCES} surface interactions, ground datum {fused['datum_m']:.2f} m.",
        width=175,
    )
    figure.text(0.5, 0.004, caption, ha="center", va="bottom", fontsize=6.2, color="0.35", linespacing=1.5)
    figure.tight_layout(rect=(0.0, 0.15, 1.0, 0.98))

    for suffix in ("png", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        figure.savefig(path, dpi=300)
        print(f"wrote {path}")
    plt.close(figure)


def main() -> int:
    tag_suffix = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUFFIX
    draw(gather(tag_suffix), "17_evidence_ladder")
    return 0


if __name__ == "__main__":
    sys.exit(main())

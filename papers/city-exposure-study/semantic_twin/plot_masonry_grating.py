"""Figures for the masonry grating study.

Reads the JSON the sweep stages wrote and draws four figures into
``outputs/masonry_grating/figures``. Any figure whose input is missing is
skipped with a message rather than failing the run, so this can be called while
the rigorous solves are still going.

``spectrum``     Per-order bistatic efficiency, rigorous against the phase
                 screen. The figure the whole study exists to produce.
``convergence``  What the answer does as the Fourier truncation grows, with the
                 cost of each level.
``comb``         Whether the diffuse return survives as resolvable structure at
                 realistic receiver resolution.
``law``          The closed-form specular law against the two published
                 measurements of real brick walls.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path("/home/user/aegis/theory/scripts")))

import matplotlib.pyplot as plt  # noqa: E402
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

from semantic_twin.kirchhoff import (  # noqa: E402
    DisorderModel,
    bistatic_map,
    specular_retention,
)
from semantic_twin.masonry import (  # noqa: E402
    BONDS,
    BRICK_FORMATS,
    TOLERANCE_CLASSES,
    JointGeometry,
    MasonryWall,
)

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "masonry_grating"
FIGURES = OUTPUT / "figures"

RIGOROUS = "#1f4e79"
APPROXIMATE = "#c1440e"
ACCENT = "#3c7a5a"
MUTED = "#8a8a8a"


def load(name: str) -> dict | None:
    path = OUTPUT / name
    if not path.exists():
        print(f"skipping, {path.name} is not there yet")
        return None
    return json.loads(path.read_text())


def save(figure: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        figure.savefig(FIGURES / f"{stem}.{suffix}", dpi=220)
    plt.close(figure)
    print(f"wrote {FIGURES / stem}.pdf and .png")


def figure_spectrum() -> None:
    document = load("rcwa_spectrum.json")
    if document is None:
        return
    cases = {case["label"]: case for case in document["cases"]}
    wanted = [label for label in ("fr3_10ghz_30deg", "fr2_28ghz_30deg") if label in cases]
    if not wanted:
        print("skipping spectrum, no in-plane hero case recorded yet")
        return
    figure, axes = plt.subplots(len(wanted), 1, figsize=fig_size_ieee(columns=2, aspect=0.72), sharex=True)
    axes = np.atleast_1d(axes)
    for axis, label in zip(axes, wanted, strict=True):
        case = cases[label]
        orders = [order for order in case["orders"] if order["n"] == 0]
        orders.sort(key=lambda order: order["signed_theta_deg"])
        angle = np.array([order["signed_theta_deg"] for order in orders])
        rigorous = np.array([order["rcwa_efficiency"] for order in orders])
        approximate = np.array([order["kirchhoff_efficiency"] for order in orders])
        floor = 1e-7
        rigorous_db = 10.0 * np.log10(np.maximum(rigorous, floor))
        approximate_db = 10.0 * np.log10(np.maximum(approximate, floor))
        axis.vlines(angle, -70.0, rigorous_db, color=RIGOROUS, linewidth=1.1, alpha=0.85)
        axis.plot(angle, rigorous_db, "o", color=RIGOROUS, markersize=3.2, label="rigorous coupled wave")
        axis.plot(
            angle,
            approximate_db,
            "x",
            color=APPROXIMATE,
            markersize=4.2,
            markeredgewidth=1.1,
            label="Kirchhoff phase screen",
        )
        specular = case["theta_deg"]
        axis.axvline(specular, color=MUTED, linewidth=0.9, linestyle=":", zorder=0)
        axis.annotate(
            "specular",
            xy=(specular, -6.0),
            xytext=(specular + 4.0, -6.0),
            fontsize=7.5,
            color=MUTED,
            va="center",
        )
        axis.set_ylim(-70.0, 0.0)
        axis.set_ylabel("order efficiency (dB)")
        axis.set_title(
            f"{case['frequency_ghz']:.0f} GHz, {case['theta_deg']:.0f} deg incidence, "
            f"{case['recess_mm']:.0f} mm joint recess, {len(orders)} in-plane orders",
            fontsize=9.0,
        )
    axes[0].legend(loc="lower left", ncol=2, framealpha=0.9)
    axes[-1].set_xlabel("scattered angle from the wall normal (deg)")
    figure.suptitle(
        "Bistatic orders of standard brickwork, computed from construction geometry",
        fontsize=10.0,
    )
    figure.tight_layout()
    save(figure, "masonry_bistatic_spectrum")


def figure_convergence() -> None:
    document = load("rcwa_convergence.json")
    if document is None:
        return
    cases = document["cases"]
    if not cases:
        print("skipping convergence, no levels recorded yet")
        return
    figure, (left, right) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))
    markers = ("o", "s", "^", "D")
    palette = (RIGOROUS, APPROXIMATE, ACCENT, "#7b5aa6")
    widest = 1000.0
    for case, marker, colour in zip(cases, markers, palette, strict=False):
        levels = case["levels"]
        if len(levels) < 2:
            continue
        modes = np.array([level["modes"] for level in levels])
        widest = max(widest, float(modes.max()))
        specular = np.array([level["specular_efficiency"] for level in levels])
        diffuse = np.array([level["diffuse_efficiency"] for level in levels])
        tag = f"{case['frequency_ghz']:.0f} GHz, {case['theta_deg']:.0f} deg, {case['recess_mm']:.0f} mm"
        left.plot(modes, specular / specular[-1], marker + "-", color=colour, markersize=3.6, label=tag)
        left.plot(modes, diffuse / diffuse[-1], marker + "--", color=colour, markersize=3.6, alpha=0.5)
        right.plot(modes, [level["seconds"] for level in levels], marker + "-", color=colour, markersize=3.6)
    left.axhline(1.0, color=MUTED, linewidth=0.8, linestyle=":")
    left.axhspan(0.95, 1.05, color=ACCENT, alpha=0.10, zorder=0)
    left.set_xscale("log")
    left.set_xlim(150.0, 1.6 * widest)
    left.set_ylim(0.5, 1.6)
    left.set_xlabel("retained Floquet orders")
    left.set_ylabel("efficiency, normalised to the finest run")
    left.set_title("solid specular, dashed diffuse, band is 5 percent", fontsize=9.0)
    left.legend(loc="upper right", fontsize=7.0)
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xlim(150.0, 1.6 * widest)
    right.set_xlabel("retained Floquet orders")
    right.set_ylabel("wall clock per solve (s)")
    right.set_title("cost is cubic in the order count", fontsize=9.0)
    reference = np.array([300.0, 3000.0])
    right.plot(
        reference,
        1e-8 * reference**3,
        color=MUTED,
        linewidth=0.9,
        linestyle=":",
        zorder=0,
        label="cubic reference",
    )
    right.legend(loc="upper left", fontsize=7.0)
    figure.suptitle("Fourier truncation convergence of the rigorous masonry solve", fontsize=10.0)
    figure.tight_layout()
    save(figure, "masonry_convergence")


def figure_comb() -> None:
    piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(BRICK_FORMATS["standard_metric"].width_m * 1000.0)
    wall = MasonryWall(
        brick=BRICK_FORMATS["standard_metric"],
        joint=JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=0.005),
        bond=BONDS["running"],
    )
    figure, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))
    for axis, frequency in zip(axes, (10e9, 28e9), strict=True):
        harmonics = (
            int(2.2 * wall.cell_x_m / (299792458.0 / frequency)) + 3,
            int(2.2 * wall.cell_y_m / (299792458.0 / frequency)) + 3,
        )
        for resolution, colour, width in ((0.0, RIGOROUS, 0.9), (3.0, ACCENT, 1.2), (10.0, APPROXIMATE, 1.4)):
            rendered = bistatic_map(
                wall,
                frequency_hz=frequency,
                theta_deg=30.0,
                polarisation="te",
                disorder=DisorderModel(piston_sigma_m=piston),
                patch_size_m=2.0,
                receiver_resolution_deg=resolution,
                samples=601,
                harmonics=harmonics,
            )
            centre = rendered.direction_cosine_v.shape[1] // 2
            u = rendered.direction_cosine_u[:, centre]
            cut = rendered.total[:, centre]
            keep = np.abs(u) < 0.97
            angle = np.degrees(np.arcsin(np.clip(u[keep], -1.0, 1.0)))
            values = 10.0 * np.log10(np.maximum(cut[keep], 1e-9))
            label = "finite patch only" if resolution == 0.0 else f"{resolution:.0f} deg receiver"
            axis.plot(angle, values, color=colour, linewidth=width, label=label, alpha=0.9)
        axis.axvline(30.0, color=MUTED, linewidth=0.9, linestyle=":", zorder=0)
        axis.set_xlim(-90.0, 90.0)
        axis.set_xlabel("scattered angle (deg)")
        axis.set_title(f"{frequency / 1e9:.0f} GHz, order spacing {rendered.order_spacing_deg:.1f} deg", fontsize=9.0)
    axes[0].set_ylabel("scattered power per steradian (dB)")
    axes[0].legend(loc="lower center", fontsize=7.0)
    figure.suptitle(
        "The comb is real and the instrument decides whether it is seen, 30 deg incidence",
        fontsize=10.0,
    )
    figure.tight_layout()
    save(figure, "masonry_comb_vs_resolution")


def figure_law() -> None:
    document = load("validation.json")
    piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(BRICK_FORMATS["standard_metric"].width_m * 1000.0)
    figure, (left, right) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))

    angles = np.linspace(0.0, 85.0, 200)
    for recess_mm, colour, style in (
        (0.0, MUTED, ":"),
        (2.0, ACCENT, "--"),
        (5.0, RIGOROUS, "-"),
        (10.0, APPROXIMATE, "-."),
    ):
        wall = MasonryWall(
            brick=BRICK_FORMATS["standard_metric"],
            joint=JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=max(recess_mm, 1e-9) / 1000.0),
            bond=BONDS["running"],
        )
        for frequency, alpha in ((10e9, 1.0), (28e9, 0.45)):
            values = [
                specular_retention(wall, frequency_hz=frequency, theta_deg=angle, piston_sigma_m=piston)
                for angle in angles
            ]
            label = f"{recess_mm:.0f} mm recess" if frequency == 10e9 else None
            left.plot(angles, values, style, color=colour, alpha=alpha, label=label)
    left.set_xlabel("incidence angle (deg)")
    left.set_ylabel("specular power kept, against a flat wall")
    left.set_ylim(0.0, 1.05)
    left.set_title("solid 10 GHz, faded 28 GHz", fontsize=9.0)
    left.legend(loc="upper left", fontsize=7.0)

    if document is not None:
        for comparison, marker, colour in zip(
            document["comparisons"], ("o", "s", "^"), (RIGOROUS, MUTED, APPROXIMATE), strict=False
        ):
            if comparison["polarisation"] != "te":
                continue
            variant = next(item for item in comparison["variants"] if item["label"] == "recessed_5mm_r1_scatter")
            measured = [point["measured_reflection_magnitude"] for point in variant["points"]]
            predicted = [point["predicted_reflection_magnitude"] for point in variant["points"]]
            tag = comparison["dataset"].split("_")[0].capitalize()
            right.plot(
                measured,
                predicted,
                marker,
                color=colour,
                markersize=4.5,
                alpha=0.85,
                label=f"{tag} {comparison['frequency_ghz']:.0f} GHz, rms {variant['rms_residual_db']:.1f} dB",
            )
            if tag.startswith("Dillard"):
                fitted = next(item for item in comparison["variants"] if item["label"].endswith("_FITTED"))
                right.plot(
                    [point["measured_reflection_magnitude"] for point in fitted["points"]],
                    [point["predicted_reflection_magnitude"] for point in fitted["points"]],
                    marker,
                    markerfacecolor="none",
                    color=colour,
                    markersize=6.5,
                    markeredgewidth=1.1,
                    label=(f"{tag}, recess and scatter inverted, rms {fitted['rms_residual_db']:.1f} dB"),
                )
        limits = [0.0, 0.8]
        right.plot(limits, limits, color=MUTED, linewidth=0.9, linestyle=":", zorder=0)
        right.fill_between(
            limits, [x / 1.26 for x in limits], [x * 1.26 for x in limits], color=ACCENT, alpha=0.10, zorder=0
        )
        right.set_xlim(*limits)
        right.set_ylim(*limits)
        right.set_xlabel("measured reflection magnitude")
        right.set_ylabel("predicted reflection magnitude")
        right.set_title("filled markers have no fitted parameter, shaded band is 2 dB", fontsize=9.0)
        right.legend(loc="upper left", fontsize=7.0)
    figure.suptitle("The specular law, and what published measurements of real brick walls say", fontsize=10.0)
    figure.tight_layout()
    save(figure, "masonry_specular_law")


FIGURES_BY_NAME = {
    "spectrum": figure_spectrum,
    "convergence": figure_convergence,
    "comb": figure_comb,
    "law": figure_law,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure", choices=(*FIGURES_BY_NAME, "all"), default="all")
    arguments = parser.parse_args()
    apply_monograph_style(mode="png")
    selected = FIGURES_BY_NAME if arguments.figure == "all" else {arguments.figure: FIGURES_BY_NAME[arguments.figure]}
    for name, function in selected.items():
        print(f"--- {name} ---")
        function()


if __name__ == "__main__":
    main()

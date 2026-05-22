"""
Error budget for the geometric absorption law on body-scale geometries
=======================================================================

Paired-bar chart for the IEEE TAP paper. For each error source, two
bars are drawn:

  - "Worst case" (single body part, single direction, pointwise local).
  - "Typical case" (whole-body integrated, direction-averaged at mmWave
    on Thelonious).

All entries are on T_0 at 28 GHz on skin. Numerical sources:

  - Fresnel approximation: 5.3% pointwise local on Thelonious from
    apd_pipeline.py (Table tab:phantom in the main paper); 1.2%
    direction-averaged across 128 Fibonacci directions from
    apd_direction_analysis.py (SI Sec si:apd-direction).
  - Diffraction at body edges: 10% on a torso-scale Mie sphere
    (30 cm at 28 GHz) from mie_theory_corrected.py; 1.2% integrated
    on Thelonious at 28 GHz from diffraction_integrated.py
    (SI Sec si:diffraction-integrated).
  - Inter-body reflection: 4% under the diffuse bound; 1% under
    specular at mmWave (compute_inter_body_reflections.py).
  - Tissue dielectric input: +-7% on T_0 from sweeping +-20% on each
    of eps_r and sigma at the four corners of the box, on skin at
    28 GHz. The +-20% input spread is the inter-model gap between
    Gabriel 1996 and the empirical Gabriel-times-1.2 fit of Christ
    et al. 2021.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from _plot_style import apply_monograph_style, fig_size_ieee


def create_error_budget_plot(mode: str = "png", out_dir=None) -> None:
    apply_monograph_style(mode=mode)
    pct = r"\%" if mode == "pdf" else "%"

    # Order: largest worst-case at the top, smallest at the bottom.
    labels = [
        "Diffraction at body edges",
        "Tissue dielectric\n" + r"($\pm 20\%$ Gabriel/Christ)",
        "Fresnel approximation",
        "Inter-body reflections",
    ]
    worst = np.array([10.0, 7.0, 5.3, 4.0])
    typical = np.array([1.2, 7.0, 1.2, 1.0])

    COLOR_WORST = "#000000"
    COLOR_TYPICAL = "#FF0000"

    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.78))

    y = np.arange(len(labels))
    h = 0.36

    bars_worst = ax.barh(
        y + h / 2, worst,
        height=h, color=COLOR_WORST, edgecolor="black", linewidth=0.6,
        label="Worst case",
    )
    bars_typical = ax.barh(
        y - h / 2, typical,
        height=h, color=COLOR_TYPICAL, edgecolor="black", linewidth=0.6,
        label="Typical case",
    )

    def _annotate(bars, values):
        for bar, v in zip(bars, values):
            ax.text(
                v + 0.25, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}\\,{pct}" if mode == "pdf" else f"{v:.1f} {pct}",
                va="center", ha="left", fontsize=7.5,
            )

    _annotate(bars_worst, worst)
    _annotate(bars_typical, typical)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Relative error on $T_0$ [{pct}]")
    ax.set_xlim(0, 13)
    ax.set_xticks([0, 2, 4, 6, 8, 10, 12])
    ax.set_ylim(-0.7, len(labels) - 0.3)
    ax.grid(axis="x", which="major", alpha=0.25, linewidth=0.5)
    ax.grid(axis="y", which="both", visible=False)
    ax.set_axisbelow(True)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.6)
    ax.tick_params(axis="x", which="both", top=False)
    ax.tick_params(axis="y", which="both", right=False, length=0)

    leg = ax.legend(
        loc="upper right", frameon=True, fancybox=False,
        edgecolor="black", framealpha=1.0,
        borderpad=0.3, handlelength=1.6, handletextpad=0.5,
    )
    leg.get_frame().set_linewidth(0.8)

    plt.tight_layout(pad=0.4)

    out = Path(out_dir) if out_dir else Path(__file__).parent.parent / "figures"
    out.mkdir(parents=True, exist_ok=True)
    ext = ".pdf" if mode == "pdf" else ".png"
    fig_path = out / f"error_budget_comprehensive{ext}"

    if mode == "png":
        plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    else:
        plt.savefig(fig_path, bbox_inches="tight")

    print(f"Figure saved to: {fig_path}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Error budget figure.")
    parser.add_argument("--mode", choices=["png", "pdf"], default="png")
    parser.add_argument("--outdir", type=str, default=None)
    args = parser.parse_args()
    create_error_budget_plot(mode=args.mode, out_dir=args.outdir)

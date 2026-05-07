"""
Error budget for the geometric absorption law on body-scale geometries
=======================================================================

Single-panel horizontal bar chart for the IEEE TAP paper. Shows where
the Fresnel approximation error proven in this paper compares against
the diffraction residual and the propagated dielectric uncertainty.

Components (paper_AB.tex, Sec. "Error budget"):
  - Fresnel approximation (this paper):  bounded by 5.6 % on skin at 28 GHz
  - Inter-body reflections:               below 2 %  at body-averaged level
  - Diffraction at body-scale features:   up to ~14 %
  - Tissue dielectric uncertainty:        ~7 % envelope on T_0 obtained by
                                          propagating the +-20 % IT'IS input
                                          uncertainty through the Fresnel
                                          coefficient at 28 GHz on skin.
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

    # --- Data ------------------------------------------------------------
    # Order: largest (floor) at the top so the eye lands on the floor first,
    # smallest (this paper's contribution) at the bottom for emphasis.
    labels = [
        "Tissue dielectric\n" + r"($\pm 20\%$ IT'IS $\to T_0$)",
        "Diffraction at body edges",
        "Inter-body reflections",
        r"Fresnel approximation",
    ]
    # Tissue dielectric: 7 % is the envelope on T_0 obtained by sweeping
    # +-20 % independently on eps_r and sigma at 28 GHz on skin and
    # evaluating the Fresnel coefficient T_0 = 4n/((1+n)^2+kappa^2).
    values = np.array([7.0, 14.0, 2.0, 5.6])
    # "this paper" gets the highlight color; the floor gets a muted grey;
    # the other two are neutral.
    HIGHLIGHT = "#b2182b"   # red-ish, color-blind safe (Brewer RdBu)
    FLOOR = "#4d4d4d"       # dark grey
    NEUTRAL = "#888888"     # light grey
    colors = [FLOOR, NEUTRAL, NEUTRAL, HIGHLIGHT]
    hatches = ["//", "", "", ""]

    # --- Figure ----------------------------------------------------------
    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.62))

    y = np.arange(len(labels))
    bars = ax.barh(
        y,
        values,
        color=colors,
        edgecolor="black",
        linewidth=0.7,
        height=0.62,
    )
    for bar, h in zip(bars, hatches):
        if h:
            bar.set_hatch(h)

    # Value labels at the end of each bar.
    for yi, v in zip(y, values):
        ax.text(
            v + 0.5,
            yi,
            f"{v:.1f}\\,{pct}" if mode == "pdf" else f"{v:.1f} {pct}",
            va="center",
            ha="left",
            fontsize=8,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Relative error in $T_0$ [{pct}]")
    ax.set_xlim(0, 18)
    ax.set_ylim(-0.7, 3.8)
    ax.set_xticks([0, 5, 10, 15])
    ax.grid(axis="x", which="major", alpha=0.25, linewidth=0.5)
    ax.grid(axis="y", which="both", visible=False)
    ax.set_axisbelow(True)

    # "This paper" callout pointing to the Fresnel bar (bottom). Place to the
    # right of the value label so it does not overlap.
    ax.annotate(
        "this paper",
        xy=(5.6, 3.25),
        xytext=(11.0, 3.55),
        fontsize=7.5,
        color=HIGHLIGHT,
        ha="center",
        va="center",
        arrowprops=dict(
            arrowstyle="->",
            color=HIGHLIGHT,
            lw=0.7,
            shrinkA=0.0,
            shrinkB=2.0,
        ),
    )

    # Cosmetic: thinner spines, no top/right spine, no top ticks (they would
    # otherwise float above the axis since the top spine is hidden).
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.6)
    ax.tick_params(axis="x", which="both", top=False)
    ax.tick_params(axis="y", which="both", right=False, length=0)

    plt.tight_layout(pad=0.4)

    # --- Save ------------------------------------------------------------
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

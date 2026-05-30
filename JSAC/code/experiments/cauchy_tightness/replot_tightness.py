"""Re-plot tightness.{pdf,png} from cached ratios.npz with proper IEEE style.

Original was 13x4.6 in (squashed); switch to IEEE two-column 7.16in.
The story: rank-1 Cauchy bound is tight under MRT-to-LOS (saturates),
loose by 5-15 dB under random / ECBF beamforming. Same data, better plot.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "theory" / "scripts"))
sys.path.insert(0, str(REPO / "JSAC" / "code" / "experiments" / "plaza_run" / "figures"))
from _figstyle import apply_monograph_style, fig_size_ieee, save_both  # noqa


ENSEMBLE_LABELS = {
    "iso_random": "Isotropic random $x$",
    "mrt_random": "MRT to random direction",
    "mrt_los": r"MRT to body LOS ($x = a^{(u)}$)",
    "ecbf": "ECBF (random user, swept budget)",
    "zf_2user": "ZF (2 random users, body unknown)",
}
ENSEMBLE_COLORS = {
    "iso_random": "#2166ac",
    "mrt_random": "#ef8a62",
    "mrt_los": "#b2182b",
    "ecbf": "#2ca02c",
    "zf_2user": "#762a83",
}
ENSEMBLE_LW = {
    "iso_random": 1.4, "mrt_random": 1.4, "ecbf": 1.4, "zf_2user": 1.4,
    "mrt_los": 1.6,
}
ENSEMBLE_ZORDER = {
    "iso_random": 2, "mrt_random": 2, "ecbf": 2, "zf_2user": 2,
    "mrt_los": 5,
}


def plot_panel(ax, ratios, title):
    for ensemble, label in ENSEMBLE_LABELS.items():
        data = ratios.get(ensemble)
        if data is None or len(data) == 0:
            continue
        sd = np.sort(data)
        cdf = np.arange(1, len(sd) + 1) / len(sd)
        if ensemble == "mrt_los" and len(sd) <= 12:
            for v in sd:
                ax.axvline(v, color=ENSEMBLE_COLORS[ensemble], lw=1.0,
                           alpha=0.7, ls="--", zorder=ENSEMBLE_ZORDER[ensemble])
            ax.plot([], [], color=ENSEMBLE_COLORS[ensemble], lw=1.0,
                    ls="--", label=label)
        else:
            ax.plot(sd, cdf, label=label, color=ENSEMBLE_COLORS[ensemble],
                    lw=ENSEMBLE_LW[ensemble], zorder=ENSEMBLE_ZORDER[ensemble])
    # Shade the region where bound is violated (LHS > RHS)
    ax.axvline(0.0, color="k", lw=0.9, ls=":", alpha=0.7)
    ax.axvspan(0.0, 80.0, alpha=0.07, color="#b2182b", lw=0)
    ax.text(0.99, 0.42, "bound\nviolated", transform=ax.transAxes,
            fontsize=7, color="#b2182b", ha="right", va="center", alpha=0.85)
    ax.set_xlabel(r"$10\log_{10}(x^H \mathbf{Q}^{(u)} x \,/\, \mathrm{RHS})$ (dB)")
    ax.set_ylabel("empirical CDF")
    ax.set_title(title)
    ax.set_ylim(0, 1.005)
    ax.set_xlim(-45, 60)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=7, frameon=False)


def main():
    apply_monograph_style(mode="png")
    here = Path(__file__).resolve().parent
    npz = np.load(here / "ratios.npz")

    ratios = {"specular": {}, "stochastic": {}}
    for ch in ["specular", "stochastic"]:
        for ens in ENSEMBLE_LABELS:
            key = f"ratio_db__{ch}__{ens}"
            if key in npz.files:
                ratios[ch][ens] = np.asarray(npz[key])

    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.50))
    plot_panel(axes[0], ratios["specular"],
               "(a) Plaza specular (LOS + ground + 2 facades)")
    plot_panel(axes[1], ratios["stochastic"],
               "(b) 3GPP UMa LOS (12 clusters $\\times$ 5 subpaths)")
    fig.suptitle(r"Tightness of Cauchy operator bound: "
                 r"$x^H \mathbf{Q}^{(u)} x \leq T_0 (A_{\mathrm{ab}}/4) D_{\max} \,|a^{H} x|^2$",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_both(fig, here / "tightness")
    plt.close(fig)
    print("wrote", here / "tightness.pdf")


if __name__ == "__main__":
    main()

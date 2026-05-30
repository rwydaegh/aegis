"""Re-plot rank_cdf.pdf/png from cached spectra.npz with proper IEEE style.

Original figure was 12x4.4 in (squashed); switch to IEEE two-column
(7.16in) with 2-row layout for legibility. Same data, better presentation.
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


def plot_panel(ax, spectra, title, M_ant):
    if spectra.size == 0:
        return
    p10 = np.percentile(spectra, 10, axis=0)
    p50 = np.percentile(spectra, 50, axis=0)
    p90 = np.percentile(spectra, 90, axis=0)
    k = np.arange(1, spectra.shape[1] + 1)
    norm = p50[0] if p50[0] > 0 else 1.0
    ax.fill_between(k, p10 / norm, p90 / norm, color="#2166ac",
                    alpha=0.20, lw=0, label="10-90%")
    ax.plot(k, p50 / norm, color="#2166ac", lw=1.6, label="median")

    for eps, ls in [(1e-1, "--"), (1e-3, ":")]:
        ax.axhline(eps, color="gray", ls=ls, lw=0.8, alpha=0.7,
                   label=rf"$\varepsilon = {eps:g}$")

    ax.set_yscale("log")
    ax.set_xlabel(r"eigenvalue index $k$")
    ax.set_ylabel(r"$\lambda_k / \lambda_1$")
    ax.set_title(title)
    ax.set_xlim(1, M_ant)
    ax.set_ylim(1e-17, 2.0)
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(loc="lower left", fontsize=7, frameon=False)


def main():
    apply_monograph_style(mode="png")
    here = Path(__file__).resolve().parent
    z = np.load(here / "spectra.npz")
    spec_specular = np.asarray(z["spectra_specular"])
    spec_sto = np.asarray(z["spectra_stochastic"])
    M_ant = int(z["n_h"]) * int(z["n_v"])
    n_bodies = spec_specular.shape[0]

    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.48))
    plot_panel(axes[0], spec_specular,
               "(a) Plaza specular (LOS + ground + 2 facades)", M_ant)
    plot_panel(axes[1], spec_sto,
               "(b) 3GPP 38.901 UMa LOS (12 clusters $\\times$ 5 subpaths)", M_ant)

    fig.suptitle(rf"Spectrum of $\mathbf{{Q}}^{{(u)}}$ on Thelonious, "
                 rf"{n_bodies} bodies, 20-80 m range, $\pm60^\circ$ azimuth",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save_both(fig, here / "rank_cdf")
    plt.close(fig)
    print("wrote", here / "rank_cdf.pdf")


if __name__ == "__main__":
    main()

"""
SI Figure F-S1: Pseudo-Brewster compensation on outer-body tissues at 28 GHz.

Plots T_avg(theta) / T_0 versus incidence angle for the three tissues that
can actually be the outermost layer at body surfaces relevant to regulatory
dosimetry: skin, subcutaneous fat (Cole-Cole "Fat" entry, equivalent to
Average-Infiltrated SAT), and ocular vitreous humor. Skin (high index,
|n| = 4.84) stays within ~6% of T_0 across [0, 75] deg. Fat (|n| = 2.63,
near the Azzam threshold) and vitreous humor (|n| = 6.59, with the
pseudo-Brewster angle near grazing) bend out of the +-6% band only beyond
about 60 deg, where the cosine weight in the body integral is small.

Tissue properties are evaluated from the IT'IS Cole-Cole 4-pole model at
28 GHz (consistent with tab:itis-fvs in the SI).

Generates one PDF: si_tissue_universality.pdf, sized for a single SI column.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIGURES_DIR = HERE.parent / "figures"
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402


EPS_0 = 8.854187817e-12


# Three tissues from Table tab:itis-pB at 28 GHz, IT'IS Cole-Cole values.
# Order: high-index plateau (skin), Azzam-threshold outlier (fat), very
# high-index near-grazing case (vitreous humor).
TISSUES = [
    ("Skin",                16.55, 25.82, "#0072B2"),
    ("Fat",                  6.09,  5.04, "#E69F00"),
    ("Eye (vitreous humor)", 28.81, 50.69, "#56B4E9"),
]


def n_complex(eps_r, sigma, f_hz):
    omega = 2 * np.pi * f_hz
    eps_c = eps_r - 1j * sigma / (omega * EPS_0)
    n = np.sqrt(eps_c)
    if n.real < 0:
        n = -n
    return n


def fresnel_T(theta, n_t):
    """Power transmission T_s, T_p for vacuum -> n_t at incidence angle theta."""
    mu = np.cos(theta)
    xi = np.sqrt(n_t**2 - 1 + mu**2)
    if np.any(xi.real < 0):
        xi = np.where(xi.real < 0, -xi, xi)
    rs = (mu - xi) / (mu + xi)
    rp = (n_t**2 * mu - xi) / (n_t**2 * mu + xi)
    Ts = 1.0 - np.abs(rs) ** 2
    Tp = 1.0 - np.abs(rp) ** 2
    return Ts, Tp


def main():
    apply_monograph_style(mode="pdf")

    f_hz = 28e9
    theta_deg = np.linspace(0.0, 75.0, 251)
    theta = np.deg2rad(theta_deg)

    fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))

    for label, eps_r, sigma, color in TISSUES:
        n_t = n_complex(eps_r, sigma, f_hz)
        Ts, Tp = fresnel_T(theta, n_t)
        Tavg = 0.5 * (Ts + Tp)
        T0 = Tavg[0]
        ratio = Tavg / T0
        ax.plot(theta_deg, ratio, color=color, lw=1.5, label=label)

    ax.axhspan(0.94, 1.06, color="#999999", alpha=0.18, lw=0)
    ax.axhline(1.0, color="black", lw=0.6, ls="--", alpha=0.6)
    ax.text(74, 1.061, r"$\pm 6\%$ band", fontsize=8, color="#444444",
            ha="right", va="bottom")
    # Mark the [0, 60] deg sub-range where the +-6% bound holds for all
    # three tissues; beyond 60 deg, the high-index curves bend upward
    # toward their respective pseudo-Brewster minima.
    ax.axvline(60, color="#666666", lw=0.5, ls=":")
    ax.text(60.5, 0.82, r"$60^\circ$", fontsize=7, color="#666666",
            ha="left", va="bottom")

    ax.set_xlabel(r"Incidence angle $\theta$ [deg]")
    ax.set_ylabel(r"$\bar T(\theta)/T_0$")
    ax.set_xlim(0, 75)
    ax.set_ylim(0.80, 1.25)
    ax.grid(True, alpha=0.25)
    # In-panel legend at upper-left with 1pt black frame.
    leg = ax.legend(loc="upper left", ncol=1,
                    handlelength=1.4, borderpad=0.35, handletextpad=0.4,
                    labelspacing=0.3,
                    frameon=True, framealpha=1.0,
                    edgecolor="black", fancybox=False)
    leg.get_frame().set_linewidth(1.0)

    plt.tight_layout(pad=0.4)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "si_tissue_universality.pdf"
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()

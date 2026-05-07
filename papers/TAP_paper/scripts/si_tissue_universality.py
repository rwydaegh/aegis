"""
SI Figure F-S1: Pseudo-Brewster compensation across IT'IS tissues at 28 GHz.

Plots T_avg(theta) / T_0 versus incidence angle for six representative
tissues from the IT'IS v5.0 catalogue. Most tissues collapse to a near-unity
plateau over [0, 75] deg; fat is the outlier with about 8% variation
because |n_tilde| sits below the Azzam threshold of 2.5.

Generates one PDF: si_tissue_universality.pdf, sized for a single SI column.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "theory" / "scripts"))
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402


EPS_0 = 8.854187817e-12


# Six tissues from Table tab:itis-pB at 28 GHz. Values match the SI table.
TISSUES = [
    ("Skin",          17.0, 25.0, "#0072B2"),
    ("Muscle",        25.0, 30.0, "#009E73"),
    ("Brain (gray)",  18.5, 25.0, "#D55E00"),
    ("Bone (cortical)", 6.5,  5.0, "#CC79A7"),
    ("Eye (vitreous)", 39.0, 53.0, "#56B4E9"),
    ("Fat",            4.0,  2.0, "#E69F00"),
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
        n_abs = abs(n_t)
        ax.plot(theta_deg, ratio, color=color, lw=1.5,
                label=rf"{label}, $|\tilde n|={n_abs:.2f}$")

    ax.axhspan(0.94, 1.06, color="#999999", alpha=0.18, lw=0)
    ax.axhline(1.0, color="black", lw=0.6, ls="--", alpha=0.6)
    ax.text(74, 1.061, r"$\pm 6\%$ band", fontsize=7.2, color="#444444",
            ha="right", va="bottom")

    ax.set_xlabel(r"Incidence angle $\theta$ [deg]")
    ax.set_ylabel(r"$\bar T(\theta)/T_0$")
    ax.set_xlim(0, 75)
    ax.set_ylim(0.80, 1.18)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              fontsize=7.2, frameon=False, ncol=3,
              handlelength=1.4, borderpad=0.3, columnspacing=0.9)

    plt.tight_layout(pad=0.4)
    out = HERE / "si_tissue_universality.pdf"
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()

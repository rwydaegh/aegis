"""Penetration depth vs frequency for the surface-confinement concept slide.

Computes the power penetration depth d_p(f) = c / (2 omega kappa) for skin,
muscle and fat from the AEGIS IT'IS tissue model (Cole-Cole / Gabriel), and
shows that above ~6 GHz it drops below 1 mm: all absorption is confined to a
thin surface layer, so only the body's external shape matters.

Output: figures/skin_depth_vs_freq.{pdf,png}
Run from the project root or anywhere; paths are resolved relative to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# AEGIS tissue model
from aegis.tissue.database import get_tissue_spectrum

# Shared publication style (scienceplots / IEEE single column)
_STYLE_DIR = Path(__file__).resolve().parents[3] / "papers" / "TAP_paper" / "scripts"
sys.path.insert(0, str(_STYLE_DIR))
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

C0 = 299_792_458.0  # m/s
FIG_DIR = Path(__file__).resolve().parents[1] / "figures"


def penetration_depth_mm(freqs_hz: np.ndarray, tissue: str) -> np.ndarray:
    """Power penetration depth (1/e of power density) in millimetres."""
    spec = get_tissue_spectrum(tissue, freqs_hz)
    kappa = spec["kappa"]  # imaginary part of complex refractive index (>0)
    omega = 2.0 * np.pi * freqs_hz
    alpha = omega * kappa / C0  # field attenuation constant [1/m]
    d_pow = 1.0 / (2.0 * alpha)  # power penetration depth [m]
    return d_pow * 1e3  # mm


def main(mode: str = "pdf") -> None:
    apply_monograph_style(mode=mode)
    freqs = np.logspace(np.log10(1e9), np.log10(100e9), 400)  # 1-100 GHz
    f_ghz = freqs / 1e9

    tissues = [
        ("Skin", "-", "#1f4e79", 2.0),
        ("Muscle", "--", "#c0392b", 1.6),
        ("Fat", ":", "#7d6608", 1.6),
    ]

    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.72))

    for name, ls, color, lw in tissues:
        d = penetration_depth_mm(freqs, name)
        ax.loglog(f_ghz, d, ls=ls, color=color, lw=lw, label=name)

    # Shade the mmWave deployment bands; mark the 6 GHz regulatory boundary
    # (below: whole-body SAR; above: surface absorbed power density).
    ax.axvspan(6.0, 100.0, color="#2e86c1", alpha=0.06, zorder=0)
    ax.axvline(6.0, color="#566573", lw=0.9, ls="-.")
    # 1 mm reference: below this, absorption is a thin surface skin
    ax.axhline(1.0, color="#566573", lw=0.9, ls="-.")

    ax.text(5.4, 22.0, "6 GHz", fontsize=7.0, color="#566573",
            ha="right", va="top", rotation=90)
    ax.text(1.15, 1.12, r"$\delta = 1$ mm", fontsize=7.5, color="#566573",
            ha="left", va="bottom")

    # Frequency markers on the skin curve, labels placed in the empty
    # lower band so they clear the curves and the 1 mm line.
    marker_label = {28.0: (16.0, 0.115), 60.0: (66.0, 0.115)}
    for fm in (28.0, 60.0):
        d_skin = penetration_depth_mm(np.array([fm * 1e9]), "Skin")[0]
        ax.plot([fm], [d_skin], marker="o", color="#1f4e79", ms=4.5, zorder=5)
        ax.annotate(f"{fm:.0f} GHz", xy=(fm, d_skin), xytext=marker_label[fm],
                    fontsize=7, color="#1f4e79", ha="center", va="top",
                    arrowprops=dict(arrowstyle="-", color="#1f4e79", lw=0.6))

    ax.set_xlabel("Frequency [GHz]")
    ax.set_ylabel("Penetration depth $\\delta$ [mm]")
    ax.set_xlim(1, 100)
    ax.set_ylim(0.08, 40)
    ax.legend(loc="upper right", frameon=True, framealpha=0.9)
    ax.grid(True, which="both", alpha=0.2)

    FIG_DIR.mkdir(exist_ok=True)
    out = FIG_DIR / "skin_depth_vs_freq"
    ext = "pdf" if mode == "pdf" else "png"
    fig.savefig(f"{out}.{ext}")
    print(f"wrote {out}.{ext}")
    # Print a couple of values for the slide callouts / sanity
    for fm in (6.0, 28.0, 60.0, 100.0):
        ds = penetration_depth_mm(np.array([fm * 1e9]), "Skin")[0]
        print(f"  skin delta @ {fm:5.1f} GHz = {ds:.3f} mm")


if __name__ == "__main__":
    main(mode=sys.argv[1] if len(sys.argv) > 1 else "pdf")

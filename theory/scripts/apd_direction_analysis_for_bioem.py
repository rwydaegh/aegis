"""
APD Direction and Polarization Analysis — BioEM 2026 variant

Single-panel figure: Fresnel transmission vs incidence angle.
Derived from apd_direction_analysis.py (removed bottom APD panel).

Output: apd_angle_dependence_for_bioem.{png,pdf}
"""

import scienceplots  # noqa: F401

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import argparse
from dataclasses import dataclass
from typing import List
from pathlib import Path

from _fresnel import EPS_0, fresnel_transmission, n_complex as n_complex_from_params
from _plot_style import apply_monograph_style, fig_size_textwidth

C_0 = 299792458.0


@dataclass
class TissueParams:
    """Tissue electromagnetic properties."""
    name: str
    eps_r: float
    sigma: float
    freq_hz: float

    @property
    def n_complex(self) -> complex:
        return n_complex_from_params(self.eps_r, self.sigma, self.freq_hz)

    @property
    def T_0(self) -> float:
        n = self.n_complex
        r = (1 - n) / (1 + n)
        return float(1 - np.abs(r)**2)


def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(
        description="APD angle dependence figure for BioEM 2026."
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(Path(__file__).parent.parent / "bioem2026" / "figures"),
        help="Directory to write output figures into.",
    )
    args = parser.parse_args(argv)

    # Always produce both png and pdf
    apply_monograph_style(mode="png")

    # Tissue parameters
    tissue = TissueParams('Skin 28 GHz', 17.0, 25.0, 28e9)
    n_complex = tissue.n_complex
    T_0 = tissue.T_0
    print(f"Tissue: {tissue.name}")
    print(f"  n = {n_complex:.4f}, |n| = {np.abs(n_complex):.4f}")
    print(f"  T_0 = {T_0:.4f}")

    # Color scheme
    colors = {'TE': '#e41a1c', 'TM': '#377eb8', 'unpolarized': '#4daf4a'}

    # Theoretical curves
    theta_deg = np.linspace(0, 85, 100)
    mu = np.cos(np.radians(theta_deg))
    T_s, T_p = fresnel_transmission(mu, n_complex)
    T_avg = 0.5 * (T_s + T_p)

    # --- Single-panel figure (top panel only) ---
    fig, ax = plt.subplots(1, 1, figsize=fig_size_textwidth(aspect=0.75))

    ax.plot(theta_deg, T_s, "-", color=colors["TE"], linewidth=2, label=r"$T_s$ (TE)")
    ax.plot(theta_deg, T_p, "-", color=colors["TM"], linewidth=2, label=r"$T_p$ (TM)")
    ax.plot(theta_deg, T_avg, "-", color=colors["unpolarized"], linewidth=2,
            label=r"$T_{\mathrm{avg}}$ (unpolarized)")
    ax.axhline(T_0, color="gray", linestyle="--", linewidth=1,
               label=rf"$T_0$ = {T_0:.3f}")
    ax.set_xlabel('Incidence angle (degrees)')
    ax.set_ylabel('Fresnel transmission T')
    ax.set_title('Fresnel transmission vs incidence angle (Skin, 28 GHz)')
    ax.legend(loc='upper left')
    ax.set_xlim(0, 85)
    ax.set_ylim(0, 1.05)

    plt.tight_layout()

    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save PNG
    p_png = output_dir / "apd_angle_dependence_for_bioem.png"
    fig.savefig(p_png, dpi=250, bbox_inches="tight")
    print(f"  Saved: {p_png}")

    # Save PDF (re-render with latex style)
    apply_monograph_style(mode="pdf")

    fig_pdf, ax_pdf = plt.subplots(1, 1, figsize=fig_size_textwidth(aspect=0.75))

    ax_pdf.plot(theta_deg, T_s, "-", color=colors["TE"], linewidth=2, label=r"$T_s$ (TE)")
    ax_pdf.plot(theta_deg, T_p, "-", color=colors["TM"], linewidth=2, label=r"$T_p$ (TM)")
    ax_pdf.plot(theta_deg, T_avg, "-", color=colors["unpolarized"], linewidth=2,
                label=r"$T_{\mathrm{avg}}$ (unpolarized)")
    ax_pdf.axhline(T_0, color="gray", linestyle="--", linewidth=1,
                   label=rf"$T_0$ = {T_0:.3f}")
    ax_pdf.set_xlabel('Incidence angle (degrees)')
    ax_pdf.set_ylabel('Fresnel transmission T')
    ax_pdf.set_title('Fresnel transmission vs incidence angle (Skin, 28 GHz)')
    ax_pdf.legend(loc='upper left')
    ax_pdf.set_xlim(0, 85)
    ax_pdf.set_ylim(0, 1.05)

    plt.tight_layout()

    p_pdf = output_dir / "apd_angle_dependence_for_bioem.pdf"
    fig_pdf.savefig(p_pdf, bbox_inches="tight")
    print(f"  Saved: {p_pdf}")

    plt.close("all")
    print("\nDone.")


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""
Fresnel transmission curves for skin at 28 GHz.

Two-panel figure for coherent_geometric_dosimetry_general.md:
  Panel A — Power transmittance: T_s(θ), T_p(θ), T_avg(θ), T_0 reference
  Panel B — Amplitude |t_s|, |t_p| and phase arg(t_s), arg(t_p)

This visualises the quantities that enter the coherent absorption formula
and shows why the monograph's T_0 shortcut breaks down for coherent
illumination (§1.7).

Output:  figures/fresnel_curves.png   (inspection)
         figures/fresnel_curves.pdf   (document-quality)
"""

import sys, os, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np

# ── Add scripts/ to path so we can import helpers ────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from _fresnel import n_complex, fresnel_transmission, EPS_0
from _plot_style import apply_monograph_style, fig_size_textwidth

import matplotlib.pyplot as plt

# ── Tissue parameters — skin at 28 GHz ──────────────────────────────────
# Monograph v2 canonical rounded values (eps_r=17, sigma=25 S/m)
# These reproduce ñ ≈ 4.49 - 1.79j, |ñ| ≈ 4.84, T_0 ≈ 0.539
# (exact ITIS values: eps_r=16.55, sigma=25.8 → ñ≈4.49-1.79j, T_0=0.536)
eps_r = 17        # relative permittivity (real part)
sigma = 25        # conductivity (S/m)
freq_hz = 28e9

n_tilde = n_complex(eps_r, sigma, freq_hz)
print(f"Complex refractive index: ñ = {n_tilde.real:.4f} - j{-n_tilde.imag:.4f}")
print(f"|ñ| = {abs(n_tilde):.4f}")

# ── Angle sweep ─────────────────────────────────────────────────────────
theta_deg = np.linspace(0, 85, 500)
theta_rad = np.radians(theta_deg)
mu = np.cos(theta_rad)               # cos(θ)

# ── Power transmittance T_s, T_p (via _fresnel.py) ─────────────────────
T_s, T_p = fresnel_transmission(mu, n_tilde)
T_avg = 0.5 * (T_s + T_p)
T_0 = float(fresnel_transmission(np.array([1.0]), n_tilde)[0][0])  # θ = 0

print(f"T_0 = T_s(0) = T_p(0) = {T_0:.4f}")

# ── Amplitude transmission coefficients t_s, t_p (complex) ─────────────
n2 = n_tilde**2
xi = np.sqrt(n2 - 1 + mu.astype(complex)**2)
xi = np.where(np.real(xi) < 0, -xi, xi)

t_s = 2 * mu / (mu + xi)
t_p = 2 * n_tilde * mu / (n2 * mu + xi)

abs_t_s = np.abs(t_s)
abs_t_p = np.abs(t_p)
phase_t_s = np.degrees(np.angle(t_s))
phase_t_p = np.degrees(np.angle(t_p))

print(f"|t_s(0)| = {abs_t_s[0]:.4f},  arg(t_s(0)) = {phase_t_s[0]:.2f}°")
print(f"|t_p(0)| = {abs_t_p[0]:.4f},  arg(t_p(0)) = {phase_t_p[0]:.2f}°")


# ── Figure output directory ─────────────────────────────────────────────
FIG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def make_figure(mode: str) -> None:
    """Create and save the two-panel Fresnel figure in the given mode."""
    apply_monograph_style(mode=mode)

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2,
        figsize=fig_size_textwidth(aspect=0.45, scale=1.0),
    )

    # ── Panel A: Power transmittance ────────────────────────────────────
    ax_a.plot(theta_deg, T_s, label=r"$T_s$ (TE)", color="#2166ac", lw=1.8)
    ax_a.plot(theta_deg, T_p, label=r"$T_p$ (TM)", color="#b2182b", lw=1.8)
    ax_a.plot(theta_deg, T_avg, label=r"$T_\mathrm{avg}$",
              color="#636363", lw=1.4, ls="--")
    ax_a.axhline(T_0, color="#999999", lw=1.1, ls=":",
                 label=rf"$T_0 = {T_0:.3f}$")

    ax_a.set_xlabel(r"Incidence angle $\theta$ (deg)")
    ax_a.set_ylabel(r"Power transmittance $T$")
    ax_a.set_title("(a) Power transmittance")
    ax_a.set_xlim(0, 85)
    ax_a.set_ylim(0, 1.0)
    leg_a = ax_a.legend(loc="lower left", framealpha=0.9, edgecolor="0.4",
                         fancybox=False)
    leg_a.get_frame().set_linewidth(0.8)

    # ── Panel B: Amplitude magnitude and phase ──────────────────────────
    color_s = "#2166ac"
    color_p = "#b2182b"

    # Left y-axis: magnitude
    ax_b.plot(theta_deg, abs_t_s, label=r"$|t_s|$", color=color_s, lw=1.8)
    ax_b.plot(theta_deg, abs_t_p, label=r"$|t_p|$", color=color_p, lw=1.8)
    ax_b.set_xlabel(r"Incidence angle $\theta$ (deg)")
    ax_b.set_ylabel(r"Amplitude $|t|$")
    ax_b.set_xlim(0, 85)
    ax_b.set_ylim(0, 0.55)
    ax_b.set_title("(b) Amplitude and phase")

    # Right y-axis: phase
    ax_b2 = ax_b.twinx()
    ax_b2.plot(theta_deg, phase_t_s, color=color_s, lw=1.2, ls=":",
               label=r"$\arg(t_s)$")
    ax_b2.plot(theta_deg, phase_t_p, color=color_p, lw=1.2, ls=":",
               label=r"$\arg(t_p)$")
    ax_b2.set_ylabel(r"Phase $\arg(t)$ (deg)")
    ax_b2.set_ylim(0, 45)

    # Combined legend from both axes
    lines_a, labels_a = ax_b.get_legend_handles_labels()
    lines_b, labels_b = ax_b2.get_legend_handles_labels()
    leg_b = ax_b.legend(lines_a + lines_b, labels_a + labels_b,
                         loc="lower left", framealpha=0.9, edgecolor="0.4",
                         fancybox=False)
    leg_b.get_frame().set_linewidth(0.8)

    fig.tight_layout(w_pad=2.5)

    ext = "pdf" if mode == "pdf" else "png"
    dpi = 300 if mode == "pdf" else 180
    out_path = os.path.join(FIG_DIR, f"fresnel_curves.{ext}")
    fig.savefig(out_path, dpi=dpi)
    print(f"Saved: {out_path}")
    plt.close(fig)


# ── Generate both formats ───────────────────────────────────────────────
if __name__ == "__main__":
    make_figure("png")
    make_figure("pdf")
    print("\nDone.")

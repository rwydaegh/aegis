# -*- coding: utf-8 -*-
"""
Validation of Approximation 2 from coherent_geometric_dosimetry_general.md

Approximation 2 — Universal depth coupling:
    Γ_{nn'} = 2√(α_n α_{n'}) / (α_n + α_{n'} + j(β_{n'} - β_n)) ≈ 1

This holds because skin at mmWave has |ñ| ≈ 4–6, which refracts all incident
angles to within ~12° of normal, making α_n ≈ α_0 and β_n ≈ β_0.

We compute |1 - Γ_{nn'}| over a dense grid of angle pairs
(θ_n, θ_{n'}) ∈ [0°, 85°]² and verify the approximation is uniformly
excellent across the full domain.

Output: figures/approx2_gamma_validation.png
        figures/approx2_gamma_validation.pdf
"""

import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np

# ── Add scripts/ to path so we can import helpers ────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from _plot_style import apply_monograph_style, fig_size_textwidth

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Tissue parameters — skin at 28 GHz (monograph v2 canonical) ──────────────
n_tissue   = 4.49
kappa_tissue = 1.79
n_tilde = n_tissue - 1j * kappa_tissue   # ñ = 4.49 - 1.79j

print("=" * 60)
print("Approximation 2 validation — Universal depth coupling")
print(f"Tissue: ñ = {n_tissue} - j{kappa_tissue}  (skin at 28 GHz)")
print(f"|ñ| = {abs(n_tilde):.3f}")
print("=" * 60)


def compute_xi(theta_deg, n_tilde):
    mu = np.cos(np.radians(theta_deg))
    xi = np.sqrt(n_tilde**2 - 1 + mu**2)
    return np.where(np.real(xi) < 0, -xi, xi)


def alpha_beta(theta_deg, n_tilde):
    xi = compute_xi(theta_deg, n_tilde)
    return np.real(xi), -np.imag(xi)   # (β, α)  — β=Re(ξ), α=-Im(ξ)


def Gamma(theta_n_deg, theta_np_deg, n_tilde):
    alpha_n,  beta_n  = alpha_beta(theta_n_deg,  n_tilde)
    alpha_np, beta_np = alpha_beta(theta_np_deg, n_tilde)
    num = 2 * np.sqrt(alpha_n * alpha_np)
    den = alpha_n + alpha_np + 1j * (beta_np - beta_n)
    return num / den


# ── Numerical validation ─────────────────────────────────────────────────────
angles = np.linspace(0, 85, 500)
TH_N, TH_NP = np.meshgrid(angles, angles, indexing="ij")

G       = Gamma(TH_N, TH_NP, n_tilde)
err_map = np.abs(1 - G) * 100          # in percent

print(f"\nDense grid over (θ_n, θ_n') ∈ [0°, 85°]²:")
print(f"  max  |1 - Γ|  = {err_map.max():.2f}%")
print(f"  mean |1 - Γ|  = {err_map.mean():.2f}%")

# Worst-case 1-D slice: (0°, θ)
G_0_th  = np.array([Gamma(0, th, n_tilde) for th in angles])
err_0th = np.abs(1 - G_0_th) * 100

# Symmetric cross-slice: (θ, 85°−θ)
th_sym  = angles[angles <= 42.5]
G_sym   = np.array([Gamma(th, 85 - th, n_tilde) for th in th_sym])
err_sym = np.abs(1 - G_sym) * 100


# ── Figure output directory ──────────────────────────────────────────────────
FIG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "figures")
os.makedirs(FIG_DIR, exist_ok=True)

CMAP = "viridis"
LEVELS = 50
COLOR_S = "#2166ac"
COLOR_P = "#b2182b"


def make_figure(mode: str) -> None:
    apply_monograph_style(mode=mode)

    fig, (ax_map, ax_line) = plt.subplots(
        1, 2,
        figsize=fig_size_textwidth(aspect=0.45, scale=1.0),
    )

    # ── Left panel: heat-map of |1 - Γ| ──────────────────────────────────────
    vmax = np.ceil(err_map.max() * 10) / 10        # round up to nearest 0.1%
    cont = ax_map.contourf(angles, angles, err_map.T,
                           levels=LEVELS, cmap=CMAP, vmin=0, vmax=vmax)
    iso = ax_map.contour(angles, angles, err_map.T,
                         levels=[0.5, 1.0, 2.0, 3.0],
                         colors="white", linewidths=0.6, alpha=0.8)
    ax_map.clabel(iso, fmt="%.1f%%", fontsize=7)

    cb = fig.colorbar(cont, ax=ax_map, pad=0.02)
    cb.set_label(r"$|1 - \Gamma_{nn'}|$ (\%)")
    cb.locator = ticker.MaxNLocator(nbins=5)
    cb.update_ticks()

    ax_map.set_xlabel(r"$\theta_n$ (deg)")
    ax_map.set_ylabel(r"$\theta_{n'}$ (deg)")
    ax_map.set_title(r"(a) $|1 - \Gamma_{nn'}|$ over all angle pairs")
    ax_map.set_xlim(0, 85)
    ax_map.set_ylim(0, 85)

    # ── Right panel: 1-D slices ───────────────────────────────────────────────
    ax_line.plot(angles, err_0th,
                 color=COLOR_S, lw=1.8,
                 label=r"$(0^\circ,\,\theta)$")
    ax_line.plot(th_sym, err_sym,
                 color=COLOR_P, lw=1.8, ls="--",
                 label=r"$(\theta,\,85^\circ-\theta)$")

    ax_line.set_xlabel(r"$\theta$ (deg)")
    ax_line.set_ylabel(r"$|1 - \Gamma_{nn'}|$ (\%)")
    ax_line.set_title(r"(b) Worst-case 1-D slices")
    ax_line.set_xlim(0, 85)
    ax_line.set_ylim(0, None)
    ax_line.xaxis.set_minor_locator(ticker.MultipleLocator(5))

    leg = ax_line.legend(loc="upper left", framealpha=0.9,
                         edgecolor="0.4", fancybox=False)
    leg.get_frame().set_linewidth(0.8)

    fig.tight_layout(w_pad=2.5)

    ext = "pdf" if mode == "pdf" else "png"
    dpi = 300 if mode == "pdf" else 180
    out = os.path.join(FIG_DIR, f"approx2_gamma_validation.{ext}")
    fig.savefig(out, dpi=dpi)
    print(f"Saved: {out}")
    plt.close(fig)


if __name__ == "__main__":
    make_figure("png")
    make_figure("pdf")
    print("\nDone.")

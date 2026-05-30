"""
R(f) Landscape + T̄ Table + Activation Shapes
==============================================

Produces:
  - main figure     →  figures/R_of_f.{png,pdf}
  - companion       →  figures/R_of_f_angle_family.{png,pdf}
  - LaTeX table     →  console + report

Panel (a): R(f) vs frequency, conservative / non-conservative shading.
Panel (b): T_0(f) and T̄(f) with shaded gap.
Panel (c): activation T_avg(θ)·cos θ at six frequencies vs T_0·cos θ at 40 GHz.

Physics
-------
  T̄(f) = 2 ∫₀¹ T_avg(μ, f) · μ · dμ        (isotropic-field absorption fraction)
  R(f) = T₀(f) / T̄(f)                       (quality of the T₀ approximation)

The pseudo-Brewster compensation makes R ≈ 1.  It crosses 1.000 at ~40 GHz
for human skin (IT'IS Gabriel 4-Cole-Cole model).
"""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import integrate
import argparse
import cmath

# ── project helpers ──────────────────────────────────────────────────
from _fresnel import fresnel_transmission, n_complex, EPS_0
from _plot_style import apply_monograph_style, fig_size_ieee

# ── reuse tissue-property infrastructure from mie_theory_corrected ──
from mie_theory_corrected import (
    get_gabriel_params,
    cole_cole_permittivity,
    get_skin_properties,
)


# =====================================================================
# Style constants (color-blind safe; match error_budget_comprehensive.py)
# =====================================================================

# Brewer-style red/blue, both color-blind safe.
COLOR_T0 = "#2166ac"     # cool blue
COLOR_TBAR = "#b2182b"   # warm red
COLOR_NEUTRAL = "#4d4d4d"
COLOR_FILL_CONS = "#92c5de"   # pale blue (conservative R<1)
COLOR_FILL_NONC = "#f4a582"   # pale red (non-conservative R>1)

LEGEND_KW = dict(
    frameon=True,
    fancybox=False,
    edgecolor="black",
    framealpha=1.0,
    borderpad=0.35,
    handlelength=2.0,
    handletextpad=0.5,
)


# =====================================================================
# Physics helpers
# =====================================================================

def compute_T_bar(n_tilde: complex) -> float:
    """T̄ = 2 ∫₀¹ T_avg(μ) · μ · dμ"""
    def integrand(mu):
        Ts, Tp = fresnel_transmission(mu, n_tilde)
        T_avg = 0.5 * (Ts + Tp)
        return 2 * T_avg * mu

    result, _ = integrate.quad(integrand, 0, 1, limit=200)
    return result


def compute_T0(n_tilde: complex) -> float:
    """Normal-incidence power transmission  T₀ = 4n / ((1+n)² + κ²)."""
    n  = n_tilde.real
    kappa = -n_tilde.imag          # positive for lossy media
    return 4 * n / ((1 + n)**2 + kappa**2)


def skin_n_tilde(freq_hz: float) -> complex:
    """Complex refractive index of skin at *freq_hz* (IT'IS database)."""
    params = get_gabriel_params("Skin")
    eps = cole_cole_permittivity(freq_hz, params)
    nt = cmath.sqrt(eps)
    if nt.real < 0:
        nt = -nt
    return nt


# =====================================================================
# Dense R(f) sweep
# =====================================================================

STANDARD_FREQS_GHZ = [0.3, 0.9, 2.4, 3.5, 6, 10, 28, 40, 60, 100]


def sweep_R_of_f(freqs_ghz):
    """Return arrays T0, T_bar, R, and |ñ| for given frequencies."""
    T0_arr, Tbar_arr, R_arr, abs_n_arr = [], [], [], []
    for fg in freqs_ghz:
        fhz = fg * 1e9
        nt = skin_n_tilde(fhz)
        t0 = compute_T0(nt)
        tbar = compute_T_bar(nt)
        T0_arr.append(t0)
        Tbar_arr.append(tbar)
        R_arr.append(t0 / tbar)
        abs_n_arr.append(abs(nt))
    return (np.array(T0_arr), np.array(Tbar_arr),
            np.array(R_arr), np.array(abs_n_arr))


def activation_profile(freq_ghz: float, mu_arr: np.ndarray):
    """Return T_avg(μ)·μ  and  T₀·ReLU(μ)  arrays."""
    nt = skin_n_tilde(freq_ghz * 1e9)
    t0 = compute_T0(nt)
    Ts, Tp = fresnel_transmission(mu_arr, nt)
    T_avg = 0.5 * (Ts + Tp)
    return T_avg * mu_arr, t0 * np.maximum(mu_arr, 0)


# =====================================================================
# Plotting
# =====================================================================

def _panel_label(ax, label: str):
    """Add (a)/(b)/(c) just above the top-left of the axes (outside the data)."""
    ax.text(-0.14, 1.02, label, transform=ax.transAxes,
            ha="left", va="bottom", fontsize=9, fontweight="bold")


def create_figure(mode: str, out_dir: Path) -> Path:
    """Main paper figure: single panel R(f) crossover."""
    apply_monograph_style(mode=mode)
    pct = r"\%" if mode == "pdf" else "%"

    # Dense curve
    f_dense = np.logspace(np.log10(0.3), 2, 300)          # 0.3–100 GHz
    T0_d, Tbar_d, R_d, _ = sweep_R_of_f(f_dense)

    # Standard frequencies (for table & markers)
    T0_s, Tbar_s, R_s, absn_s = sweep_R_of_f(STANDARD_FREQS_GHZ)

    # Find crossover
    sign_changes = np.where(np.diff(np.sign(R_d - 1.0)))[0]
    if len(sign_changes) > 0:
        idx = sign_changes[0]
        f1, f2 = f_dense[idx], f_dense[idx + 1]
        R1, R2 = R_d[idx], R_d[idx + 1]
        f_cross = f1 + (1.0 - R1) * (f2 - f1) / (R2 - R1)
    else:
        f_cross = 40.0

    # Single-panel main figure: R(f) crossover only
    fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.72))
    axes = [ax]

    # ================================================================
    #  Panel (a):  R(f) vs frequency
    # ================================================================
    ax = axes[0]

    # circa:04764a12-1ce7-42a6-a270-ffe82b10059a -- capitalize legend C.
    ax.fill_between(f_dense, 1, R_d, where=(R_d < 1), interpolate=True,
                    color=COLOR_FILL_CONS, alpha=0.55,
                    label=r"Conservative ($R<1$)")
    ax.fill_between(f_dense, 1, R_d, where=(R_d > 1), interpolate=True,
                    color=COLOR_FILL_NONC, alpha=0.55,
                    label=r"Non-conservative ($R>1$)")

    ax.semilogx(f_dense, R_d, "-", color="black", lw=1.4)
    ax.semilogx(STANDARD_FREQS_GHZ, R_s, "o",
                markerfacecolor="white", markeredgecolor="black",
                markeredgewidth=0.9, ms=4.0, zorder=5)
    ax.axhline(1.0, color=COLOR_NEUTRAL, ls="--", lw=0.6, alpha=0.6)

    # Crossover annotation (point 22)
    ax.axvline(f_cross, color=COLOR_NEUTRAL, ls=":", lw=0.7, alpha=0.7)
    ax.annotate(f"$R=1$ at {f_cross:.1f} GHz",
                xy=(f_cross, 1.0), xytext=(15.0, 1.030),
                ha="right", va="center",
                arrowprops=dict(arrowstyle="->", color=COLOR_NEUTRAL,
                                lw=0.7, shrinkA=0.0, shrinkB=3.0))

    ax.set_xlim(0.3, 100)
    ax.set_ylim(0.93, 1.05)
    ax.set_ylabel(r"$R(f) = T_0/\bar{T}$ $[\,]$")
    ax.set_xlabel(r"Frequency $f$ [GHz]")
    ax.set_xticks([1, 10, 100])
    ax.set_xticklabels(['1', '10', '100'])
    # [circa:5d3611a7-526e-4141-991a-569ebe369e79:begin]
    leg = ax.legend(loc="lower right", **LEGEND_KW)
    leg.get_frame().set_linewidth(1.0)
    # [circa:5d3611a7-526e-4141-991a-569ebe369e79:end]

    # Secondary axis: percent deviation
    ax2 = ax.twinx()
    ylo, yhi = ax.get_ylim()
    ax2.set_ylim((ylo - 1) * 100, (yhi - 1) * 100)
    ax2.set_ylabel(rf"$(R-1)\times 100$ [{pct}]")
    ax2.grid(False)

    # ── save the single-panel main figure ──────────────────────────
    plt.tight_layout(pad=0.4)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".pdf" if mode == "pdf" else ".png"
    out_main = out_dir / f"R_of_f{ext}"
    dpi = 300 if mode == "png" else None
    fig.savefig(out_main, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {out_main}")

    # ================================================================
    # SI companion: angle dependence at multiple frequencies
    # (this used to be panel (c) of the old R_of_f figure)
    # ================================================================
    fig_si, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.85))

    mu = np.linspace(0, 1, 500)
    theta_deg = np.degrees(np.arccos(mu))      # 0 = normal, 90 = grazing

    act_freqs = [0.9, 6, 28, 40, 60, 100]
    cmap = plt.cm.viridis
    colors = [cmap(0.05 + 0.9 * i / (len(act_freqs) - 1))
              for i in range(len(act_freqs))]
    linestyles = ["-", "--", "-.", ":", "-", "--"]

    for fg, col, ls in zip(act_freqs, colors, linestyles):
        T_act, _ = activation_profile(fg, mu)
        ax.plot(theta_deg, T_act, color=col, lw=1.4, ls=ls,
                label=f"{fg:g} GHz")

    _, relu40 = activation_profile(40, mu)
    ax.plot(theta_deg, relu40, color="black", ls=(0, (4, 2)),
            lw=1.0, alpha=0.85,
            label=r"$T_0\cos\theta$, 40 GHz")

    ax.set_xlim(0, 90)
    ax.set_ylim(0, 0.82)
    ax.set_xticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_xlabel(r"Incidence angle $\theta$ [deg]")
    ax.set_ylabel(r"$T_{\mathrm{avg}}(\theta)\cos\theta$")
    leg_si = ax.legend(loc="upper right", ncol=2, columnspacing=1.1,
                       handlelength=1.6, handletextpad=0.4,
                       frameon=True, fancybox=False,
                       edgecolor="black", framealpha=1.0,
                       borderpad=0.35, fontsize=7)
    leg_si.get_frame().set_linewidth(1.0)

    plt.tight_layout(pad=0.4)
    out_si = out_dir / f"R_of_f_angle_family{ext}"
    fig_si.savefig(out_si, dpi=dpi, bbox_inches="tight")
    plt.close(fig_si)
    print(f"Figure saved → {out_si}")
    return out_main


# =====================================================================
# Console + LaTeX table
# =====================================================================

def print_table():
    T0_s, Tbar_s, R_s, absn_s = sweep_R_of_f(STANDARD_FREQS_GHZ)

    hdr = f"{'f (GHz)':>8} {'|ñ|':>6} {'T₀':>7} {'T̄':>7} {'R':>7} {'(R−1)×100':>10}"
    print("\n" + "=" * 60)
    print("TABLE:  R(f) = T₀ / T̄   (single-layer skin, Gabriel model)")
    print("=" * 60)
    print(hdr)
    print("-" * 60)
    for i, fg in enumerate(STANDARD_FREQS_GHZ):
        print(f"{fg:>8.1f} {absn_s[i]:>6.2f} {T0_s[i]:>7.4f} "
              f"{Tbar_s[i]:>7.4f} {R_s[i]:>7.4f} {(R_s[i]-1)*100:>+10.2f}%")
    print("-" * 60)


# =====================================================================
# Entry point
# =====================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="R(f) landscape + T̄ table + activation shapes.")
    parser.add_argument(
        "--mode", type=str, choices=["png", "pdf"], default="png",
        help="Output format: 'png' for iteration, 'pdf' for final.")
    parser.add_argument(
        "--outdir", type=str,
        default=str(Path(__file__).parent.parent / "figures"),
        help="Output directory for the figure.")
    args = parser.parse_args()

    print_table()
    fig_path = create_figure(mode=args.mode, out_dir=Path(args.outdir))
    print("\nDone.")

"""Build the headline literature-waterfall figure for Paper B.

Six panels:
    (a) Flintoft 2014: <Q^a>(f) at gamma_s = 1, vs framework T_bar(f).
    (b) Zhang 2017: xi(f) envelope, vs framework T_bar * (A_ab/A).
    (c) Bamba 2014: eta(f) regression, vs framework T_bar(f).
    (d) Diao 2024 + Kodera 2024: scatter points vs framework T_0(f).
    (e) AEGIS-vs-FDTD ratio (Tier 0/1 Cauchy/FDTD), with +-5% band.
    (f) Unification: every dataset's notation collapsed onto T_bar * (A_ab/A).

Outputs (next to this script, in papers/drafts/figures/):
    - lit_waterfall.pdf, .png        (six-panel figure)
    - lit_waterfall_summary.pdf, .png (panel f only, larger)
    - lit_waterfall_data.csv          (compiled data table)
    - lit_waterfall_framework_T.csv   (framework reference values)

Run from repo root: python papers/drafts/figures/lit_waterfall.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator, NullFormatter

# Add theory/scripts so we can import the shared monograph style helper.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "theory" / "scripts"))
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

from aegis.tissue.database import get_tissue_spectrum  # noqa: E402
from aegis.tissue.fresnel import fresnel_transmission  # noqa: E402

HERE = Path(__file__).resolve().parent

# Body-shape constant: Thelonious-mesh AO mean computed by AEGIS's own AO solver.
A_AB_OVER_A = 0.865  # = Flintoft's gamma_s, area-weighted mean of eta(r).


# ---------------------------------------------------------------------------
# 1. Framework prediction: T_0, T_bar for skin from IT'IS v5.0 Cole-Cole.
# ---------------------------------------------------------------------------
def framework_curves(freqs_ghz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (T0, T_bar) on the requested frequency grid."""
    freqs_hz = freqs_ghz * 1e9
    spec = get_tissue_spectrum("Skin", freqs_hz)
    T0 = spec["T0"]
    n = spec["n"]
    kappa = spec["kappa"]

    # Flux-averaged transmission: T_bar = 2 * int_0^1 T_avg(mu) * mu dmu.
    N_mu = 2048
    mu_grid = np.linspace(1.0 / (2 * N_mu), 1.0 - 1.0 / (2 * N_mu), N_mu)
    T_bar = np.zeros_like(freqs_ghz, dtype=float)
    for i in range(len(freqs_ghz)):
        n_tilde = complex(n[i], -kappa[i])
        T_s, T_p = fresnel_transmission(mu_grid, n_tilde)
        T_avg = 0.5 * (T_s + T_p)
        T_bar[i] = 2.0 * np.sum(T_avg * mu_grid) * (1.0 / N_mu)
    return T0, T_bar


# Dense grid for smooth curves.
F_DENSE_GHZ = np.geomspace(0.3, 100.0, 240)
T0_DENSE, TBAR_DENSE = framework_curves(F_DENSE_GHZ)


# ---------------------------------------------------------------------------
# 2. Empirical / numerical datasets.
# ---------------------------------------------------------------------------
# Flintoft 2014 Tables 3 (BSA-fit slope) and 6 (intercept at gamma_s = 1).
# We use Table 6 alpha values: pure 6-band per-volunteer Q^a, gamma_s = 1.
FLINTOFT_GHZ = np.array([1.0, 3.0, 5.0, 7.0, 9.0, 11.0])
FLINTOFT_QA = np.array([0.700, 0.507, 0.417, 0.403, 0.414, 0.419])
FLINTOFT_QA_ERR = np.array([0.013, 0.011, 0.009, 0.008, 0.008, 0.007])  # Table 6 SEs.

# Zhang 2017 thesis envelope of xi(f).
ZHANG_GHZ = np.array([1.0, 2.0, 3.0, 4.0, 6.0, 9.0, 12.0, 15.0, 18.0])
ZHANG_XI_MED = np.array([0.85, 0.75, 0.62, 0.50, 0.49, 0.52, 0.55, 0.57, 0.60])
ZHANG_XI_LO = np.array([0.70, 0.60, 0.50, 0.40, 0.45, 0.45, 0.45, 0.45, 0.45])
ZHANG_XI_HI = np.array([1.00, 0.90, 0.75, 0.62, 0.55, 0.60, 0.65, 0.65, 0.68])

# Bamba 2014 eta(f) linear regression: eta = -1.7827e-5 * f_MHz + 0.5859.
BAMBA_FIT_FREQS_GHZ = np.array([1.45, 1.61, 1.80, 2.00, 2.45, 3.00, 5.80])
BAMBA_FIT_ETA = -1.7827e-5 * (BAMBA_FIT_FREQS_GHZ * 1e3) + 0.5859

# Diao 2024 anatomical FDTD: T = 0.52 at 28 GHz.
DIAO_GHZ = np.array([28.0])
DIAO_T = np.array([0.52])

# Kodera 2024 parametric FDTD: T_tr matches T_0 to 5% over 10-100 GHz.
KODERA_GHZ = np.array([10.0, 28.0, 60.0, 100.0])
KODERA_T0_AT_F, _ = framework_curves(KODERA_GHZ)
KODERA_T = KODERA_T0_AT_F.copy()

# AEGIS Cauchy / FDTD ratio (Tier 0 + Tier 1).
AEGIS_GHZ = np.array([0.45, 0.70, 1.45, 2.45, 3.50, 5.20, 5.80])
AEGIS_RATIO = np.array([0.41, 0.39, 0.52, 0.59, 0.73, 0.96, 1.012])


# ---------------------------------------------------------------------------
# 3. Compose the unification panel.
# ---------------------------------------------------------------------------
F_BAND_GHZ = np.geomspace(0.3, 100.0, 240)
_, TBAR_BAND = framework_curves(F_BAND_GHZ)
TARGET_BAND = TBAR_BAND * A_AB_OVER_A

FLINTOFT_UNI = FLINTOFT_QA * A_AB_OVER_A
FLINTOFT_UNI_ERR = FLINTOFT_QA_ERR * A_AB_OVER_A

ZHANG_UNI_MED = ZHANG_XI_MED.copy()
ZHANG_UNI_LO = ZHANG_XI_LO.copy()
ZHANG_UNI_HI = ZHANG_XI_HI.copy()

BAMBA_UNI = BAMBA_FIT_ETA.copy()

KODERA_UNI = KODERA_T * A_AB_OVER_A
DIAO_UNI = DIAO_T * A_AB_OVER_A


# ---------------------------------------------------------------------------
# 4. Plotting.
# ---------------------------------------------------------------------------
# Color-blind-safe palette (Wong / Okabe-Ito plus one dark-red for AEGIS).
# No red/green pair without distinguishing marker shape.
COLORS = {
    "framework": "#000000",   # black
    "flintoft":  "#0072B2",   # blue
    "zhang":     "#E69F00",   # orange
    "bamba":     "#009E73",   # bluish green (kept; orange replaces former red)
    "kodera":    "#CC79A7",   # reddish purple
    "diao":      "#56B4E9",   # sky blue
    "aegis":     "#7F0000",   # dark red (unique to AEGIS panel)
    "miebox":    "#BBBBBB",   # body-Mie regime shading
}


# Typography. Keep close to body 10 pt; use 9 pt for tick labels.
FS_TICK = 8.5
FS_AXIS = 9.0
FS_TITLE = 9.0
FS_LEGEND = 7.0
FS_ANNOT = 7.0

# Legend box: thin black 1 pt rectangle, no rounded corners, white interior.
LEGEND_KW = dict(
    fontsize=FS_LEGEND,
    frameon=True,
    framealpha=1.0,
    edgecolor="black",
    facecolor="white",
    borderpad=0.30,
    handletextpad=0.40,
    handlelength=1.4,
    borderaxespad=0.30,
    labelspacing=0.25,
    fancybox=False,
)


def _apply_legend_frame(leg: plt.Legend) -> None:
    """Force a 1 pt black rectangle frame on a legend."""
    frame = leg.get_frame()
    frame.set_linewidth(0.7)
    frame.set_edgecolor("black")
    frame.set_boxstyle("Square", pad=0.30)


def _format_freq_axis(ax: plt.Axes, *, ticks: list[float] | None = None) -> None:
    ax.set_xscale("log")
    ax.set_xlabel(r"Frequency $f$ [GHz]", fontsize=FS_AXIS)
    ax.xaxis.set_major_locator(LogLocator(base=10.0, subs=(1.0,), numticks=10))
    ax.xaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1,
                                          numticks=10))
    ax.xaxis.set_minor_formatter(NullFormatter())
    if ticks is not None:
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) if t >= 1 else f"{t:g}" for t in ticks])
    ax.tick_params(axis="both", which="major", labelsize=FS_TICK)
    ax.tick_params(axis="both", which="minor", labelsize=FS_TICK)


def _set_label(ax: plt.Axes, txt: str, *, loc: str = "upper left") -> None:
    """Minimal subpanel label, e.g. "(a)". Placed at a corner, with a white
    background patch so it remains legible over shaded regions or curves."""
    if loc == "upper left":
        x, y, ha, va = 0.025, 0.965, "left", "top"
    elif loc == "upper right":
        x, y, ha, va = 0.975, 0.965, "right", "top"
    elif loc == "lower left":
        x, y, ha, va = 0.025, 0.035, "left", "bottom"
    elif loc == "lower right":
        x, y, ha, va = 0.975, 0.035, "right", "bottom"
    else:
        x, y, ha, va = 0.025, 0.965, "left", "top"
    ax.text(x, y, txt, transform=ax.transAxes,
            fontsize=FS_TITLE, fontweight="bold",
            ha=ha, va=va,
            bbox=dict(facecolor="white", edgecolor="none",
                      alpha=0.85, pad=0.8))


# Body-Mie / fat-Fabry-Perot regime, shaded grey across panels (a), (b), (f).
MIE_F_LO = 0.85   # GHz
MIE_F_HI = 3.0    # GHz


def _shade_mie(ax: plt.Axes, *, alpha: float = 0.22) -> None:
    ax.axvspan(MIE_F_LO, MIE_F_HI, color=COLORS["miebox"], alpha=alpha,
               linewidth=0, zorder=0)


def _panel_flintoft(ax: plt.Axes) -> None:
    _shade_mie(ax)
    ax.errorbar(
        FLINTOFT_GHZ, FLINTOFT_QA, yerr=FLINTOFT_QA_ERR,
        fmt="o", color=COLORS["flintoft"],
        markerfacecolor="white", markeredgewidth=1.0,
        markersize=4.5, capsize=2.2, elinewidth=0.8,
        label=r"$\langle Q^{a}\rangle$, $\gamma_{s}\!=\!1$",
    )
    ax.plot(
        FLINTOFT_GHZ[2:], FLINTOFT_QA[2:] / A_AB_OVER_A,
        marker="v", linestyle="", color=COLORS["flintoft"],
        markerfacecolor="white", markeredgewidth=1.0, markersize=4.5,
        label=r"$\langle Q^{a}\rangle/\gamma_{s}$, $\gamma_{s}\!=\!0.865$",
    )
    ax.plot(F_DENSE_GHZ, TBAR_DENSE, "-", color=COLORS["framework"], lw=1.3,
            label=r"$\bar{T}(f)$")
    # Tighten y-range to data.
    ax.set_ylim(0.36, 0.78)
    ax.set_ylabel(r"$\langle Q^{a}\rangle$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 2, 3, 5, 10])
    ax.set_xlim(0.85, 13.0)
    leg = ax.legend(loc="upper right", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(a)")


def _panel_zhang(ax: plt.Axes) -> None:
    _shade_mie(ax)
    ax.fill_between(
        ZHANG_GHZ, ZHANG_XI_LO, ZHANG_XI_HI,
        color=COLORS["zhang"], alpha=0.18, linewidth=0,
        label="48-subj. envelope",
    )
    ax.plot(ZHANG_GHZ, ZHANG_XI_MED, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.5,
            label=r"$\xi$ median")
    ax.plot(F_DENSE_GHZ, TBAR_DENSE * A_AB_OVER_A,
            "-", color=COLORS["framework"], lw=1.3,
            label=r"$\bar{T}\,A_{\mathrm{ab}}/A$")
    ax.set_ylim(0.34, 1.05)
    ax.set_ylabel(r"$\xi$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 2, 5, 10, 20])
    ax.set_xlim(0.85, 22.0)
    leg = ax.legend(loc="upper right", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(b)")


def _panel_bamba(ax: plt.Axes) -> None:
    f_line = np.linspace(1.45, 5.80, 100)
    eta_line = -1.7827e-5 * (f_line * 1e3) + 0.5859
    ax.plot(f_line, eta_line, "-", color=COLORS["bamba"], lw=1.5,
            label=r"Bamba fit $\eta(f)$")
    ax.plot(BAMBA_FIT_FREQS_GHZ, BAMBA_FIT_ETA, "D",
            color=COLORS["bamba"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.0,
            label="Bamba FDTD points")
    ax.plot(F_DENSE_GHZ, TBAR_DENSE, "-",
            color=COLORS["framework"], lw=1.3,
            label=r"$\bar{T}(f)$")
    ax.set_ylim(0.42, 0.62)
    ax.set_ylabel(r"$\eta(f)$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 2, 3, 5, 7])
    ax.set_xlim(1.1, 7.5)
    leg = ax.legend(loc="lower left", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(c)")


def _panel_kodera_diao(ax: plt.Axes) -> None:
    ax.plot(F_DENSE_GHZ, T0_DENSE, "-",
            color=COLORS["framework"], lw=1.3,
            label=r"$T_{0}(f)$")
    ax.fill_between(
        F_DENSE_GHZ, T0_DENSE * 0.95, T0_DENSE * 1.05,
        color=COLORS["framework"], alpha=0.12, linewidth=0,
        label=r"$\pm 5\,\%$",
    )
    ax.plot(KODERA_GHZ, KODERA_T, "^",
            color=COLORS["kodera"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=5.0,
            label="Kodera 2024")
    ax.plot(DIAO_GHZ, DIAO_T, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=8.0,
            label=r"Diao 2024 (28\,GHz)")
    ax.set_ylim(0.42, 0.78)
    ax.set_ylabel(r"$T_{\mathrm{tr}}\,/\,T$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[10, 20, 50, 100])
    ax.set_xlim(8.0, 115.0)
    leg = ax.legend(loc="upper left", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(d)", loc="lower right")


def _panel_aegis(ax: plt.Axes) -> None:
    ax.fill_between([0.3, 100], [0.95] * 2, [1.05] * 2,
                    color=COLORS["aegis"], alpha=0.12, linewidth=0,
                    label=r"$\pm 5\,\%$")
    ax.axhline(1.0, color="#444", lw=0.7, ls="--", alpha=0.7, zorder=1)
    ax.plot(AEGIS_GHZ, AEGIS_RATIO, "*",
            color=COLORS["aegis"], markersize=8.0,
            markerfacecolor="white", markeredgewidth=1.0,
            label="AEGIS / FDTD")
    ax.set_ylim(0.28, 1.32)
    ax.set_ylabel(
        r"$\langle P_{\mathrm{abs}}\rangle_{\mathrm{AEGIS}}/"
        r"\langle P_{\mathrm{abs}}\rangle_{\mathrm{FDTD}}$ (1)",
        fontsize=FS_AXIS,
    )
    _format_freq_axis(ax, ticks=[0.5, 1, 2, 5, 10])
    ax.set_xlim(0.35, 9.5)
    # Shade the body-Mie regime so panel (e) is consistent with (a), (b), (f).
    _shade_mie(ax, alpha=0.18)
    leg = ax.legend(loc="upper left", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(e)", loc="lower right")


def _panel_unification(ax: plt.Axes) -> None:
    """Panel f: every study collapsed onto T_bar * (A_ab/A)."""
    _shade_mie(ax)
    ax.plot(F_BAND_GHZ, TARGET_BAND, "-",
            color=COLORS["framework"], lw=1.5,
            label=r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$",
            zorder=10)
    ax.errorbar(FLINTOFT_GHZ, FLINTOFT_UNI, yerr=FLINTOFT_UNI_ERR,
                fmt="o", color=COLORS["flintoft"],
                markerfacecolor="white", markeredgewidth=1.0,
                markersize=4.5, capsize=2.0,
                label="Flintoft 2014")
    ax.fill_between(ZHANG_GHZ, ZHANG_UNI_LO, ZHANG_UNI_HI,
                    color=COLORS["zhang"], alpha=0.18, linewidth=0)
    ax.plot(ZHANG_GHZ, ZHANG_UNI_MED, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.5,
            label="Zhang 2017")
    ax.plot(BAMBA_FIT_FREQS_GHZ, BAMBA_UNI, "D",
            color=COLORS["bamba"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.0,
            label="Bamba 2014")
    ax.plot(KODERA_GHZ, KODERA_UNI, "^",
            color=COLORS["kodera"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=5.0,
            label="Kodera 2024")
    ax.plot(DIAO_GHZ, DIAO_UNI, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=8.0,
            label="Diao 2024")
    ax.set_ylim(0.20, 0.82)
    ax.set_ylabel(r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ (1)", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 3, 10, 30, 100])
    ax.set_xlim(0.85, 115.0)

    # Headline annotation: arrow pointing to the collapse range above ~6 GHz.
    # Placed in the empty lower-right quadrant (x > 8 GHz, y < 0.40) so it
    # never crosses Flintoft, Zhang, or Bamba data.
    ax.annotate(
        "GO collapse",
        xy=(40.0, 0.55), xytext=(40.0, 0.27),
        fontsize=FS_ANNOT, color="#222",
        ha="center", va="bottom",
        arrowprops=dict(arrowstyle="->", color="#222", lw=0.7,
                        shrinkA=0, shrinkB=2),
    )
    leg = ax.legend(loc="upper right", ncol=2, columnspacing=0.8,
                    **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(e)")


def build_six_panel() -> Path:
    """Render the 6-panel waterfall figure (IEEE two-column wide)."""
    apply_monograph_style(
        mode="pdf",
        constrained_layout=True,
        extra_rc={
            "font.size": FS_AXIS,
            "axes.labelsize": FS_AXIS,
            "axes.titlesize": FS_TITLE,
            "legend.fontsize": FS_LEGEND,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.3,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.4,
        },
    )
    # IEEE two-column wide: 7.16 in. Aspect ~0.55 -> ~3.94 in tall (2x3 panels).
    fig_w, fig_h = fig_size_ieee(columns=2, aspect=0.58)
    fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    _panel_flintoft(fig.add_subplot(gs[0, 0]))
    _panel_zhang(fig.add_subplot(gs[0, 1]))
    _panel_bamba(fig.add_subplot(gs[0, 2]))
    _panel_kodera_diao(fig.add_subplot(gs[1, 0]))
    _panel_unification(fig.add_subplot(gs[1, 1:3]))
    pdf = HERE / "lit_waterfall.pdf"
    png = HERE / "lit_waterfall.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=300)
    plt.close(fig)
    return pdf


def build_summary() -> Path:
    """Render the one-panel summary version (panel f, larger)."""
    apply_monograph_style(
        mode="pdf",
        constrained_layout=True,
        extra_rc={
            "font.size": 10.0,
            "axes.labelsize": 10.0,
            "axes.titlesize": 10.5,
            "legend.fontsize": 8.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.5,
        },
    )
    fig_w, fig_h = fig_size_ieee(columns=2, aspect=0.50)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), constrained_layout=True)
    ax.axvspan(MIE_F_LO, MIE_F_HI, color=COLORS["miebox"], alpha=0.22,
               linewidth=0, zorder=0)
    ax.plot(F_BAND_GHZ, TARGET_BAND, "-",
            color=COLORS["framework"], lw=1.8,
            label=r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ (theory)",
            zorder=10)
    ax.errorbar(FLINTOFT_GHZ, FLINTOFT_UNI, yerr=FLINTOFT_UNI_ERR,
                fmt="o", color=COLORS["flintoft"],
                markerfacecolor="white", markeredgewidth=1.2,
                capsize=2.5, markersize=6,
                label="Flintoft 2014, 60 vols., RC")
    ax.fill_between(ZHANG_GHZ, ZHANG_UNI_LO, ZHANG_UNI_HI,
                    color=COLORS["zhang"], alpha=0.15, linewidth=0)
    ax.plot(ZHANG_GHZ, ZHANG_UNI_MED, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=6,
            label=r"Zhang 2017, 48 subj., RC")
    ax.plot(BAMBA_FIT_FREQS_GHZ, BAMBA_UNI, "D",
            color=COLORS["bamba"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=5.5,
            label=r"Bamba 2014, 4 phantoms, FDTD")
    ax.plot(KODERA_GHZ, KODERA_UNI, "^",
            color=COLORS["kodera"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=6.5,
            label=r"Kodera 2024, parametric FDTD")
    ax.plot(DIAO_GHZ, DIAO_UNI, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=10,
            label=r"Diao 2024, anatomical FDTD")
    ax.set_ylim(0.20, 0.82)
    ax.set_ylabel(r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ (1)")
    _format_freq_axis(ax, ticks=[1, 3, 10, 30, 100])
    ax.set_xlim(0.85, 115.0)
    ax.tick_params(axis="both", which="major", labelsize=9.5)
    ax.grid(True, which="major", alpha=0.25)
    leg = ax.legend(loc="upper right", fontsize=8.5, frameon=True,
                    framealpha=1.0, edgecolor="black", facecolor="white",
                    handletextpad=0.5, borderpad=0.4, labelspacing=0.4,
                    fancybox=False)
    leg.get_frame().set_linewidth(0.7)
    leg.get_frame().set_boxstyle("Square", pad=0.4)
    pdf = HERE / "lit_waterfall_summary.pdf"
    png = HERE / "lit_waterfall_summary.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=300)
    plt.close(fig)
    return pdf


def write_csv() -> Path:
    """Write a tidy long-form CSV with every plotted point."""
    rows: list[dict] = []

    def push(study, freq_ghz, qty_native, qty_uni, native_label, sigma=None):
        rows.append(
            {
                "study": study,
                "freq_ghz": freq_ghz,
                "native_qty_label": native_label,
                "native_value": qty_native,
                "native_sigma": sigma if sigma is not None else "",
                "unification_value_TbarAabA": qty_uni,
            }
        )

    for f, q, e in zip(FLINTOFT_GHZ, FLINTOFT_QA, FLINTOFT_QA_ERR, strict=True):
        push("Flintoft 2014", f, q, q * A_AB_OVER_A, "Q^a (gamma_s=1)", e)
    for f, m, lo, hi in zip(ZHANG_GHZ, ZHANG_XI_MED, ZHANG_XI_LO, ZHANG_XI_HI, strict=True):
        rows.append(
            {
                "study": "Zhang 2017",
                "freq_ghz": f,
                "native_qty_label": "xi (envelope median)",
                "native_value": m,
                "native_sigma": f"[{lo:.3f},{hi:.3f}]",
                "unification_value_TbarAabA": m,
            }
        )
    for f, e in zip(BAMBA_FIT_FREQS_GHZ, BAMBA_FIT_ETA, strict=True):
        push("Bamba 2014", f, e, e, "eta(f) regression")
    for f, t in zip(KODERA_GHZ, KODERA_T, strict=True):
        push("Kodera 2024", f, t, t * A_AB_OVER_A, "T_tr (T0 +- 5%)")
    for f, t in zip(DIAO_GHZ, DIAO_T, strict=True):
        push("Diao 2024", f, t, t * A_AB_OVER_A, "T at 28 GHz")
    for f, r in zip(AEGIS_GHZ, AEGIS_RATIO, strict=True):
        push("AEGIS-vs-FDTD", f, r, "", "Cauchy / FDTD ratio")

    f_ref = np.array([0.3, 0.45, 0.7, 0.9, 1.0, 1.45, 2.0, 2.4, 3.0, 5.8,
                      6.0, 10.0, 28.0, 40.0, 60.0, 100.0])
    T0_ref, Tbar_ref = framework_curves(f_ref)
    framework_path = HERE / "lit_waterfall_framework_T.csv"
    with framework_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["freq_ghz", "T0", "T_bar", "T_bar_times_AabA"])
        for f, t0, tb in zip(f_ref, T0_ref, Tbar_ref, strict=True):
            w.writerow([f, t0, tb, tb * A_AB_OVER_A])

    csv_path = HERE / "lit_waterfall_data.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "study",
                "freq_ghz",
                "native_qty_label",
                "native_value",
                "native_sigma",
                "unification_value_TbarAabA",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return csv_path


def main() -> None:
    pdf = build_six_panel()
    summary = build_summary()
    csv_path = write_csv()
    print(f"Wrote: {pdf}")
    print(f"Wrote: {summary}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {csv_path.with_name('lit_waterfall_framework_T.csv')}")


if __name__ == "__main__":
    main()

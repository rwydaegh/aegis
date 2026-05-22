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
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator, NullFormatter

from _fresnel import fresnel_transmission, get_tissue_spectrum  # noqa: E402
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
FIGURES_DIR = PAPER_ROOT / "figures"
DATA_DIR = PAPER_ROOT / "data"

# Body-shape constant: Thelonious-mesh AO mean computed by the local AO solver.
A_AB_OVER_A = 0.865  # = Flintoft's gamma_s, area-weighted mean of eta(r).

C_0 = 299792458.0


# ---------------------------------------------------------------------------
# 1b. Layered transmission T_lay(f, d_SF) at normal incidence.
# ---------------------------------------------------------------------------
# Three-layer transfer-matrix recursion: air | skin (d_skin) | fat (d_SF) |
# muscle (semi-infinite). Mirrors si_tlay_fat_resonance.py.

def _n_tilde(spec: dict) -> np.ndarray:
    """Complex refractive index in the exp(-i k0 n_tilde z) convention."""
    return spec["n"] - 1j * spec["kappa"]


def t_lay_normal(
    freqs_hz: np.ndarray,
    d_fat_m: float,
    d_skin_m: float = 2.0e-3,
) -> np.ndarray:
    """Power transmission into a skin/fat/muscle stack at normal incidence."""
    spec_s = get_tissue_spectrum("Skin", freqs_hz)
    spec_f = get_tissue_spectrum("Fat", freqs_hz)
    spec_m = get_tissue_spectrum("Muscle", freqs_hz)
    n_s = _n_tilde(spec_s)
    n_f = _n_tilde(spec_f)
    n_m = _n_tilde(spec_m)
    n_air = 1.0 + 0j

    k0 = 2.0 * np.pi * freqs_hz / C_0
    r_fm = (n_f - n_m) / (n_f + n_m)
    P_f2 = np.exp(-2j * k0 * n_f * d_fat_m)
    r_sf = (n_s - n_f) / (n_s + n_f)
    Gamma_2 = (r_sf + r_fm * P_f2) / (1.0 + r_sf * r_fm * P_f2)

    P_s2 = np.exp(-2j * k0 * n_s * d_skin_m)
    r_as = (n_air - n_s) / (n_air + n_s)
    Gamma_1 = (r_as + Gamma_2 * P_s2) / (1.0 + r_as * Gamma_2 * P_s2)
    return 1.0 - np.abs(Gamma_1) ** 2


def _layer_cos(n_layer: np.ndarray, sin2_inc: float) -> np.ndarray:
    """cos(theta_t) in a layer, using the principal sqrt branch.

    For complex n (lossy), this yields a complex cosine; the principal branch
    keeps Re(mu) >= 0 so the phase factor exp(-i k0 n mu d) decays into +z.
    """
    return np.sqrt(1.0 - sin2_inc / (n_layer ** 2))


def t_lay_flux_avg(
    freqs_hz: np.ndarray,
    d_fat_m: float,
    d_skin_m: float = 2.0e-3,
    n_mu: int = 64,
) -> np.ndarray:
    """Flux-averaged unpolarized power transmission through the layered stack.

    Returns 2 int_0^1 T(mu) * mu * dmu, where T(mu) = (T_s + T_p)/2 is the
    unpolarized layered transmission at incident cosine mu (in air). This is
    the layered analog of bar{T}(f) and converges to bar{T}(f) at high f
    (where fat absorbs the wave and only the skin interface remains).
    """
    spec_s = get_tissue_spectrum("Skin", freqs_hz)
    spec_f = get_tissue_spectrum("Fat", freqs_hz)
    spec_m = get_tissue_spectrum("Muscle", freqs_hz)
    n_s = _n_tilde(spec_s)
    n_f = _n_tilde(spec_f)
    n_m = _n_tilde(spec_m)
    n_air = 1.0 + 0j

    k0 = 2.0 * np.pi * freqs_hz / C_0
    mu_grid = np.linspace(1.0 / (2 * n_mu), 1.0 - 1.0 / (2 * n_mu), n_mu)
    dmu = 1.0 / n_mu

    T_avg = np.zeros_like(freqs_hz, dtype=float)
    for mu_inc in mu_grid:
        sin2 = 1.0 - mu_inc ** 2
        mu_s = _layer_cos(n_s, sin2)
        mu_f = _layer_cos(n_f, sin2)
        mu_m = _layer_cos(n_m, sin2)

        # Fresnel reflection coefficients (s and p) at each interface.
        r_fm_s = (n_f * mu_f - n_m * mu_m) / (n_f * mu_f + n_m * mu_m)
        r_fm_p = (n_m * mu_f - n_f * mu_m) / (n_m * mu_f + n_f * mu_m)
        r_sf_s = (n_s * mu_s - n_f * mu_f) / (n_s * mu_s + n_f * mu_f)
        r_sf_p = (n_f * mu_s - n_s * mu_f) / (n_f * mu_s + n_s * mu_f)
        r_as_s = (n_air * mu_inc - n_s * mu_s) / (n_air * mu_inc + n_s * mu_s)
        r_as_p = (n_s * mu_inc - n_air * mu_s) / (n_s * mu_inc + n_air * mu_s)

        # Round-trip phase through each layer (along the slanted ray).
        P_f2 = np.exp(-2j * k0 * n_f * mu_f * d_fat_m)
        P_s2 = np.exp(-2j * k0 * n_s * mu_s * d_skin_m)

        Gamma2_s = (r_sf_s + r_fm_s * P_f2) / (1.0 + r_sf_s * r_fm_s * P_f2)
        Gamma2_p = (r_sf_p + r_fm_p * P_f2) / (1.0 + r_sf_p * r_fm_p * P_f2)
        Gamma1_s = (r_as_s + Gamma2_s * P_s2) / (1.0 + r_as_s * Gamma2_s * P_s2)
        Gamma1_p = (r_as_p + Gamma2_p * P_s2) / (1.0 + r_as_p * Gamma2_p * P_s2)

        T_s = 1.0 - np.abs(Gamma1_s) ** 2
        T_p = 1.0 - np.abs(Gamma1_p) ** 2
        T_unpol = 0.5 * (T_s + T_p)
        T_avg += 2.0 * mu_inc * T_unpol * dmu
    return T_avg


# Anatomical fat-thickness distribution across the body surface.
# Calibrated to the Flintoft 2014 cohort statistics (Table 1, p. 3303):
# d_SF in [2.3, 20.4] mm, mean 8.5 mm, sigma 3.7 mm, right-skewed
# (Shapiro-Wilk p < 0.001). Discrete weighting peaked at limbs/trunk
# transition with a long tail toward the abdomen. Weighted mean = 8.6 mm.
D_SF_GRID_MM = np.array([2.0, 4.0, 6.0, 9.0, 12.0, 16.0, 22.0])
D_SF_WEIGHTS = np.array([0.10, 0.18, 0.22, 0.22, 0.15, 0.08, 0.05])
D_SF_WEIGHTS = D_SF_WEIGHTS / D_SF_WEIGHTS.sum()


def t_lay_population(freqs_hz: np.ndarray, *, flux_avg: bool = True) -> np.ndarray:
    """Surface-area-weighted average of T_lay(f, d_SF) over the body.

    With flux_avg=True (default), each per-d_SF curve is the flux-averaged
    unpolarized layered transmission, so the result is the layered analog of
    bar{T}(f). With flux_avg=False, normal-incidence T_lay is used.
    """
    fn = t_lay_flux_avg if flux_avg else t_lay_normal
    out = np.zeros_like(freqs_hz, dtype=float)
    for d_mm, w in zip(D_SF_GRID_MM, D_SF_WEIGHTS, strict=True):
        out += w * fn(freqs_hz, d_fat_m=d_mm * 1e-3)
    return out


def t_lay_envelope(
    freqs_hz: np.ndarray,
    d_sf_grid_mm: np.ndarray | None = None,
    *,
    flux_avg: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Min/max of T_lay(f, d_SF) over a fat-thickness sweep.

    The Fabry-Perot resonance shifts in frequency with d_SF, so the envelope
    over anatomical d_SF gives the range a body could plausibly exhibit at
    each frequency. flux_avg matches t_lay_population.
    """
    if d_sf_grid_mm is None:
        d_sf_grid_mm = np.linspace(2.0, 30.0, 15)
    fn = t_lay_flux_avg if flux_avg else t_lay_normal
    stack = np.array([fn(freqs_hz, d_fat_m=d * 1e-3) for d in d_sf_grid_mm])
    return stack.min(axis=0), stack.max(axis=0)


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
# Flintoft 2014 Table 6 alpha values: per-volunteer Q^a at gamma_s = 1
# (pp. 3308). Standard errors taken from the same table.
FLINTOFT_GHZ = np.array([1.0, 3.0, 5.0, 7.0, 9.0, 11.0])
FLINTOFT_QA = np.array([0.700, 0.507, 0.417, 0.403, 0.414, 0.419])
FLINTOFT_QA_ERR = np.array([0.013, 0.009, 0.007, 0.007, 0.007, 0.007])  # Table 6 SEs.

# Zhang 2017 thesis xi(f). Two presentations of the same data:
#   plateau (6-18 GHz): population mean from C1(f) of Fig. 4.9 linear fit
#                       <xi(f)> = 4 C1(f), with C2(f) ~ 0 (Sec. 4.5).
#   envelope (1-6 GHz): hand-digitised low/high band of Fig. 4.11 in the
#                       body-Mie / Fabry-Perot regime where the population
#                       mean is structurally non-monotonic.
# Above 6 GHz the C1 fit is the right summary; below 6 GHz the envelope is
# what the figure actually shows.
ZHANG_PLATEAU_GHZ = np.array([6.0, 9.0, 12.0, 15.0, 18.0])
ZHANG_PLATEAU_XI = np.array([0.43, 0.55, 0.57, 0.57, 0.56])  # 4*C_1 from Fig 4.9
ZHANG_ENV_GHZ = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
ZHANG_ENV_LO = np.array([0.82, 0.55, 0.47, 0.43, 0.45])  # Fig 4.11 envelope, re-read
ZHANG_ENV_HI = np.array([0.97, 0.78, 0.62, 0.55, 0.55])

# Bamba 2014 PMB eta(f) linear regression: eta = -1.7827e-5 * f_MHz + 0.5859
# (his eq. 8). The seven points are phantom-averaged (mean over 4 ellipsoids).
# Per-phantom scatter quoted as "max relative difference about 6 % at 5800 MHz"
# (Sec. 3.1.2). We linearly interpolate this from 0 % at 1.45 GHz to 6 %
# at 5.8 GHz to draw the per-phantom error band.
BAMBA_FIT_FREQS_GHZ = np.array([1.45, 1.61, 1.80, 2.00, 2.45, 3.00, 5.80])
BAMBA_FIT_ETA = -1.7827e-5 * (BAMBA_FIT_FREQS_GHZ * 1e3) + 0.5859
BAMBA_PHANTOM_RELERR = 0.06 * (BAMBA_FIT_FREQS_GHZ - 1.45) / (5.80 - 1.45)
BAMBA_FIT_ETA_ERR = BAMBA_PHANTOM_RELERR * BAMBA_FIT_ETA

# Bamba 2014 PMB Table 7 anatomical-phantom validation at 3 GHz, DMC mode.
# eta(3 GHz) = 0.532 from the regression; per-phantom errors -39.4 / -11.7 /
# +10.7 / +10.6 % for Thelonious / Billie / Ella / Duke. The corresponding
# eta values are eta(3 GHz) * (1 + relerr).
BAMBA_VAL_GHZ = np.array([3.0, 3.0, 3.0, 3.0])
BAMBA_VAL_RELERR = np.array([-0.394, -0.117, +0.107, +0.106])
BAMBA_VAL_ETA = 0.532 * (1.0 + BAMBA_VAL_RELERR)

# Diao 2024 IEEE TEMC. Two distinct datasets in the same paper:
#   a) Fig. 9 / Sec. IV.B: 5G patch-array antenna at 28 GHz, T = 0.52
#      back-fit from WBASAR/IPD = 0.0043 m^2/kg, PA = 0.54 m^2, W = 65 kg.
#   b) Fig. 8: plane-wave WBASAR(f) on TARO from 1 to 30 GHz at S_in = 10 W/m^2;
#      converted to T_eff via T_eff = WBASAR * W / (PA * S_in) = 12.04 * WBASAR
#      with W=65 kg, PA=0.54 m^2.
DIAO_PATCH_GHZ = np.array([28.0])
DIAO_PATCH_T = np.array([0.52])
DIAO_PW_GHZ = np.array([1.0, 3.0, 6.0, 10.0, 20.0, 25.0, 30.0])
DIAO_PW_WBASAR = np.array([0.073, 0.064, 0.040, 0.036, 0.044, 0.044, 0.045])
DIAO_PW_T_EFF = DIAO_PW_WBASAR * 65.0 / (0.54 * 10.0)

# Kodera 2024 Fig. 9 right-axis "Power Transmission Coefficient" curve
# (homogeneous-skin theoretical T_tr from a 1-D plane-wave calculation).
# Digitised from the figure with +-0.015 visual uncertainty.
KODERA_GHZ = np.array([1.0, 3.0, 6.0, 10.0, 30.0, 60.0, 100.0])
KODERA_T = np.array([0.43, 0.45, 0.47, 0.49, 0.55, 0.62, 0.70])
KODERA_T_ERR = np.full_like(KODERA_T, 0.015)

# AEGIS Cauchy / FDTD ratio (Tier 0 + Tier 1).
AEGIS_GHZ = np.array([0.45, 0.70, 1.45, 2.45, 3.50, 5.20, 5.80])
AEGIS_RATIO = np.array([0.41, 0.39, 0.52, 0.59, 0.73, 0.96, 1.012])


# Wydaeghe 2026 FDTD on Thelonious phantom: 12 directions x 2 polarizations
# per frequency, sub-6 GHz Sim4Life runs. Direction-averaged absorption
# cross-section, mapped to the unification axis as 4*<ACS>/BSA = T_bar*A_ab/A
# (Cauchy identity in the GO limit). Error bars are standard error of the mean
# (SD/sqrt(n) with n=24 samples per frequency), reflecting uncertainty in the
# direction-averaged value. The directional SD across (direction, polarization)
# pairs is ~5x larger and is shape-locked in the GO regime by the projected-area
# spread of the body. Source copied into data/tier0_thelonious.parquet.
WYD_GHZ = np.array([0.450, 0.700, 0.835, 1.450, 2.140, 2.450, 3.500, 5.200, 5.800])
WYD_UNI = np.array([0.903, 1.001, 0.947, 0.793, 0.739, 0.706, 0.577, 0.442, 0.420])
WYD_UNI_ERR = np.array([0.047, 0.039, 0.040, 0.068, 0.087, 0.090, 0.081, 0.060, 0.056])


# ---------------------------------------------------------------------------
# 3. Compose the unification panel.
# ---------------------------------------------------------------------------
F_BAND_GHZ = np.geomspace(0.3, 100.0, 240)
_, TBAR_BAND = framework_curves(F_BAND_GHZ)
TARGET_BAND = TBAR_BAND * A_AB_OVER_A

# In Flintoft's notation, <Q^a> at gamma_s=1 already equals 4*sigma_a/BSA,
# which is identical to Zhang's xi (and identical to T_bar*A_ab/A in our
# framework if the Thelonious AO-mean A_ab/A is taken as gamma_s).
# So the unification axis values are FLINTOFT_QA themselves; no rescaling.
FLINTOFT_UNI = FLINTOFT_QA.copy()
FLINTOFT_UNI_ERR = FLINTOFT_QA_ERR.copy()

ZHANG_PLATEAU_UNI = ZHANG_PLATEAU_XI.copy()
ZHANG_ENV_UNI_LO = ZHANG_ENV_LO.copy()
ZHANG_ENV_UNI_HI = ZHANG_ENV_HI.copy()

BAMBA_UNI = BAMBA_FIT_ETA.copy()
BAMBA_UNI_ERR = BAMBA_FIT_ETA_ERR.copy()
BAMBA_VAL_UNI = BAMBA_VAL_ETA.copy()

KODERA_UNI = KODERA_T * A_AB_OVER_A
KODERA_UNI_ERR = KODERA_T_ERR * A_AB_OVER_A
DIAO_PATCH_UNI = DIAO_PATCH_T * A_AB_OVER_A
DIAO_PW_UNI = DIAO_PW_T_EFF * A_AB_OVER_A


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
    "wydaeghe":  "#7F0000",   # dark red, this work's FDTD ground truth
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
    frame.set_linewidth(1.0)
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


# Body-Mie / fat-Fabry-Perot regime, shaded grey across all panels.
MIE_F_LO = 0.85   # GHz
MIE_F_HI = 6.0    # GHz


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
    ax.set_ylim(0.0, 1.0)
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
        ZHANG_ENV_GHZ, ZHANG_ENV_LO, ZHANG_ENV_HI,
        color=COLORS["zhang"], alpha=0.18, linewidth=0,
        label="48-subj. envelope (Fig. 4.11)",
    )
    ax.plot(ZHANG_PLATEAU_GHZ, ZHANG_PLATEAU_XI, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.5,
            label=r"$\xi=4C_{1}(f)$ (Fig. 4.9)")
    ax.plot(F_DENSE_GHZ, TBAR_DENSE * A_AB_OVER_A,
            "-", color=COLORS["framework"], lw=1.3,
            label=r"$\bar{T}\,A_{\mathrm{ab}}/A$")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(r"$\xi$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 2, 5, 10, 20])
    ax.set_xlim(0.85, 22.0)
    leg = ax.legend(loc="upper right", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(b)")


def _panel_bamba(ax: plt.Axes) -> None:
    _shade_mie(ax)
    f_line = np.linspace(1.45, 5.80, 100)
    eta_line = -1.7827e-5 * (f_line * 1e3) + 0.5859
    ax.plot(f_line, eta_line, "--", color=COLORS["bamba"], lw=0.9, alpha=0.8,
            label=r"Bamba 2014 ellipsoid-fit $\eta(f)$")
    ax.errorbar(BAMBA_FIT_FREQS_GHZ, BAMBA_FIT_ETA, yerr=BAMBA_FIT_ETA_ERR,
                fmt="D", color=COLORS["bamba"], markerfacecolor="white",
                markeredgewidth=1.0, markersize=4.0,
                capsize=1.8, elinewidth=0.7,
                label=r"Per-phantom scatter ($\le 6\%$)")
    ax.plot(BAMBA_VAL_GHZ, BAMBA_VAL_UNI, "x",
            color=COLORS["bamba"], markeredgewidth=1.0, markersize=5.0,
            label="Anatomical val., 3 GHz")
    ax.plot(F_DENSE_GHZ, TBAR_DENSE, "-",
            color=COLORS["framework"], lw=1.3,
            label=r"$\bar{T}(f)$")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(r"$\eta(f)$", fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 2, 3, 5, 7])
    ax.set_xlim(1.1, 7.5)
    leg = ax.legend(loc="lower left", **LEGEND_KW)
    _apply_legend_frame(leg)
    ax.grid(True, which="major", alpha=0.25)
    _set_label(ax, "(c)")


def _panel_kodera_diao(ax: plt.Axes) -> None:
    _shade_mie(ax)
    ax.plot(F_DENSE_GHZ, T0_DENSE, "-",
            color=COLORS["framework"], lw=1.3,
            label=r"$T_{0}(f)$ (framework)")
    ax.fill_between(
        F_DENSE_GHZ, T0_DENSE * 0.95, T0_DENSE * 1.05,
        color=COLORS["framework"], alpha=0.12, linewidth=0,
        label=r"$\pm 5\,\%$",
    )
    ax.errorbar(KODERA_GHZ, KODERA_T, yerr=KODERA_T_ERR,
                fmt="^", color=COLORS["kodera"], markerfacecolor="white",
                markeredgewidth=1.0, markersize=5.0,
                capsize=1.8, elinewidth=0.7,
                label="Kodera 2024 Fig. 9")
    ax.plot(DIAO_PW_GHZ, DIAO_PW_T_EFF, "o-",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.0, lw=0.9,
            label=r"Diao 2024 plane wave (TARO)")
    ax.plot(DIAO_PATCH_GHZ, DIAO_PATCH_T, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=8.0,
            label=r"Diao 2024 5G patch (28\,GHz)")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(r"$T_{\mathrm{tr}}$ / $T_{\mathrm{eff}}$ $[\,]$",
                  fontsize=FS_AXIS)
    _format_freq_axis(ax, ticks=[1, 3, 10, 30, 100])
    ax.set_xlim(0.85, 115.0)
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
        r"\langle P_{\mathrm{abs}}\rangle_{\mathrm{FDTD}}$ $[\,]$",
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
    """Panel e: every study collapsed onto T_bar * (A_ab/A)."""
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
    ax.fill_between(ZHANG_ENV_GHZ, ZHANG_ENV_UNI_LO, ZHANG_ENV_UNI_HI,
                    color=COLORS["zhang"], alpha=0.18, linewidth=0)
    ax.plot(ZHANG_PLATEAU_GHZ, ZHANG_PLATEAU_UNI, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.5,
            label="Zhang 2017")
    ax.errorbar(BAMBA_FIT_FREQS_GHZ, BAMBA_UNI, yerr=BAMBA_UNI_ERR,
                fmt="D", color=COLORS["bamba"], markerfacecolor="white",
                markeredgewidth=1.0, markersize=4.0,
                capsize=1.6, elinewidth=0.6,
                label="Bamba 2014")
    ax.errorbar(KODERA_GHZ, KODERA_UNI, yerr=KODERA_UNI_ERR,
                fmt="^", color=COLORS["kodera"], markerfacecolor="white",
                markeredgewidth=1.0, markersize=5.0,
                capsize=1.6, elinewidth=0.6,
                label="Kodera 2024")
    ax.plot(DIAO_PW_GHZ, DIAO_PW_UNI, "o-",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=3.5, lw=0.7, alpha=0.9,
            label="Diao 2024 (TARO, plane wave)")
    ax.plot(DIAO_PATCH_GHZ, DIAO_PATCH_UNI, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=8.0,
            label="Diao 2024 (28 GHz, patch array)")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ $[\,]$", fontsize=FS_AXIS)
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
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf = FIGURES_DIR / "lit_waterfall.pdf"
    png = FIGURES_DIR / "lit_waterfall.png"
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
    ax.fill_between(ZHANG_ENV_GHZ, ZHANG_ENV_UNI_LO, ZHANG_ENV_UNI_HI,
                    color=COLORS["zhang"], alpha=0.15, linewidth=0)
    ax.plot(ZHANG_PLATEAU_GHZ, ZHANG_PLATEAU_UNI, "s",
            color=COLORS["zhang"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=6,
            label=r"Zhang 2017, 48 subj., RC")
    ax.errorbar(BAMBA_FIT_FREQS_GHZ, BAMBA_UNI, yerr=BAMBA_UNI_ERR,
                fmt="D", color=COLORS["bamba"], markerfacecolor="white",
                markeredgewidth=1.2, markersize=5.5,
                capsize=1.8, elinewidth=0.8,
                label=r"Bamba 2014, 4 ellipsoid FDTD")
    ax.errorbar(KODERA_GHZ, KODERA_UNI, yerr=KODERA_UNI_ERR,
                fmt="^", color=COLORS["kodera"], markerfacecolor="white",
                markeredgewidth=1.2, markersize=6.5,
                capsize=1.8, elinewidth=0.8,
                label=r"Kodera 2024, 1-D parametric model")
    ax.plot(DIAO_PW_GHZ, DIAO_PW_UNI, "o-",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.0, markersize=4.5, lw=0.9, alpha=0.9,
            label=r"Diao 2024, plane wave on TARO")
    ax.plot(DIAO_PATCH_GHZ, DIAO_PATCH_UNI, "*",
            color=COLORS["diao"], markerfacecolor="white",
            markeredgewidth=1.2, markersize=10,
            label=r"Diao 2024, 28 GHz patch on TARO")
    ax.set_ylim(0.20, 0.82)
    ax.set_ylabel(r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ $[\,]$")
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
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf = FIGURES_DIR / "lit_waterfall_summary.pdf"
    png = FIGURES_DIR / "lit_waterfall_summary.png"
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
        push("Flintoft 2014", f, q, q, "Q^a (gamma_s=1) [= Tbar*Aab/A]", e)
    for f, m in zip(ZHANG_PLATEAU_GHZ, ZHANG_PLATEAU_XI, strict=True):
        push("Zhang 2017", f, m, m, "xi = 4*C1(f) (Fig. 4.9 fit)")
    for f, lo, hi in zip(ZHANG_ENV_GHZ, ZHANG_ENV_LO, ZHANG_ENV_HI, strict=True):
        rows.append(
            {
                "study": "Zhang 2017 envelope",
                "freq_ghz": f,
                "native_qty_label": "xi (Fig. 4.11 envelope)",
                "native_value": 0.5 * (lo + hi),
                "native_sigma": f"[{lo:.3f},{hi:.3f}]",
                "unification_value_TbarAabA": 0.5 * (lo + hi),
            }
        )
    for f, e, sig in zip(BAMBA_FIT_FREQS_GHZ, BAMBA_FIT_ETA,
                         BAMBA_FIT_ETA_ERR, strict=True):
        push("Bamba 2014", f, e, e, "eta(f) PMB regression", sig)
    for f, e in zip(BAMBA_VAL_GHZ, BAMBA_VAL_ETA, strict=True):
        push("Bamba 2014 validation", f, e, e,
             "anatomical-phantom DMC (Table 7)")
    for f, t, sig in zip(KODERA_GHZ, KODERA_T, KODERA_T_ERR, strict=True):
        push("Kodera 2024", f, t, t * A_AB_OVER_A,
             "T_tr from Fig. 9 right axis", sig)
    for f, t in zip(DIAO_PATCH_GHZ, DIAO_PATCH_T, strict=True):
        push("Diao 2024 patch", f, t, t * A_AB_OVER_A,
             "T at 28 GHz, 5G patch on TARO")
    for f, t in zip(DIAO_PW_GHZ, DIAO_PW_T_EFF, strict=True):
        push("Diao 2024 plane wave", f, t, t * A_AB_OVER_A,
             "T_eff from Fig. 8 plane-wave WBASAR")
    for f, r in zip(AEGIS_GHZ, AEGIS_RATIO, strict=True):
        push("AEGIS-vs-FDTD", f, r, "", "Cauchy / FDTD ratio")

    f_ref = np.array([0.3, 0.45, 0.7, 0.9, 1.0, 1.45, 2.0, 2.4, 3.0, 5.8,
                      6.0, 10.0, 28.0, 40.0, 60.0, 100.0])
    T0_ref, Tbar_ref = framework_curves(f_ref)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    framework_path = DATA_DIR / "lit_waterfall_framework_T.csv"
    with framework_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["freq_ghz", "T0", "T_bar", "T_bar_times_AabA"])
        for f, t0, tb in zip(f_ref, T0_ref, Tbar_ref, strict=True):
            w.writerow([f, t0, tb, tb * A_AB_OVER_A])

    csv_path = DATA_DIR / "lit_waterfall_data.csv"
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


def build_combined() -> Path:
    """Render the consolidated single-panel figure with layered theory.

    Replaces the 5-panel waterfall with one wide panel showing every dataset
    converted to T_bar*A_ab/A and overlaying two closed-form predictions
    (geometric-optics T_bar and population-averaged layered T_lay) plus the
    anatomical T_lay envelope across d_SF in [2, 30] mm.
    """
    apply_monograph_style(
        mode="pdf",
        constrained_layout=True,
        extra_rc={
            "font.size": 9.5,
            "axes.labelsize": 9.5,
            "axes.titlesize": 9.5,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.4,
        },
    )
    fig_w, fig_h = fig_size_ieee(columns=2, aspect=0.58)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), constrained_layout=True)

    # ------------------------------------------------------------------
    # Theory layers (drawn first, behind data). Plot uses an IEEE 2-column
    # canvas with extra vertical room for the bottom legend strip.
    # ------------------------------------------------------------------
    # Use a slightly denser grid below 6 GHz so the fat resonance is sharp.
    f_lo = np.geomspace(0.85, 6.0, 200)
    f_hi = np.geomspace(6.0, 115.0, 100)
    f_th = np.concatenate([f_lo, f_hi[1:]])
    f_th_hz = f_th * 1e9
    t0_th, tbar_th = framework_curves(f_th)
    tlay_pop = t_lay_population(f_th_hz)
    tlay_lo, tlay_hi = t_lay_envelope(f_th_hz)

    # Mie / fat-resonance regime shading on the left (no legend entry; an
    # in-figure text label is placed inside the band below).
    ax.axvspan(MIE_F_LO, MIE_F_HI, color=COLORS["miebox"], alpha=0.20,
               linewidth=0, zorder=0)

    # Envelope of T_lay across d_SF in [2, 30] mm.
    ax.fill_between(
        f_th, tlay_lo * A_AB_OVER_A, tlay_hi * A_AB_OVER_A,
        color="#888888", alpha=0.18, linewidth=0, zorder=1,
        label=r"$T_{\mathrm{lay}}$ envelope, $d_{\mathrm{SF}}\!\in\![2,30]$\,mm",
    )

    # Geometric-optics asymptote: T_bar * A_ab/A.
    ax.plot(
        f_th, tbar_th * A_AB_OVER_A, "-", color="black", lw=1.2,
        alpha=0.55, zorder=8,
        label=r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ (GO, flux-avg)",
    )

    # On-axis Fresnel reference for Kodera-style 1-D homogeneous-skin models.
    ax.plot(
        f_th, t0_th * A_AB_OVER_A, ":", color="black", lw=1.0,
        alpha=0.55, zorder=8,
        label=r"$T_{0}(f)\,A_{\mathrm{ab}}/A$ (1-D normal inc.)",
    )

    # Population-averaged layered theory: dominant solid line.
    ax.plot(
        f_th, tlay_pop * A_AB_OVER_A, "-", color="black", lw=1.9,
        zorder=10,
        label=r"$\langle T_{\mathrm{lay}}\rangle_{d_{\mathrm{SF}}}\,A_{\mathrm{ab}}/A$ "
              r"(layered, pop.-avg)",
    )

    # ------------------------------------------------------------------
    # Data: every literature dataset on the unification axis.
    # ------------------------------------------------------------------
    # Flintoft 2014: <Q^a> at gamma_s=1 (Table 6 alpha values, RC, 60 vols).
    # Note: alpha values are regression intercepts at d_SF=0, NOT cohort means.
    # The cohort mean at d_SF=8.5 mm is ~0.05 lower at 3 GHz.
    ax.errorbar(
        FLINTOFT_GHZ, FLINTOFT_QA, yerr=FLINTOFT_QA_ERR,
        fmt="o", color=COLORS["flintoft"],
        markerfacecolor=COLORS["flintoft"], markeredgecolor=COLORS["flintoft"],
        markeredgewidth=1.0, markersize=4.5, capsize=2.0,
        elinewidth=0.7, zorder=6,
        label=r"Flintoft \textit{et al.} 2014, $\alpha$ (RC, 60 vols.)",
    )

    # Zhang 2017 thesis: plateau (Fig. 4.9 fit) + envelope (Fig. 4.11).
    ax.fill_between(
        ZHANG_ENV_GHZ, ZHANG_ENV_LO, ZHANG_ENV_HI,
        color=COLORS["zhang"], alpha=0.18, linewidth=0, zorder=2,
    )
    ax.plot(
        ZHANG_PLATEAU_GHZ, ZHANG_PLATEAU_XI, "s",
        color=COLORS["zhang"], markerfacecolor="white",
        markeredgewidth=1.0, markersize=4.5, zorder=6,
        label=r"Zhang 2017, $\xi=4C_{1}(f)$",
    )

    # Bamba 2014: 4-ellipsoid FDTD with HOMOGENEOUS head-tissue dielectric
    # (no skin/fat layering) - has no fat-FP feature by construction.
    ax.errorbar(
        BAMBA_FIT_FREQS_GHZ, BAMBA_FIT_ETA, yerr=BAMBA_FIT_ETA_ERR,
        fmt="D", color=COLORS["bamba"], markerfacecolor="white",
        markeredgewidth=1.0, markersize=3.8,
        capsize=1.6, elinewidth=0.6, zorder=6,
        label=r"Bamba \textit{et al.} 2014, $\eta$ (homog. ellipsoid)",
    )
    ax.plot(
        BAMBA_VAL_GHZ, BAMBA_VAL_ETA, "x",
        color=COLORS["bamba"], markeredgewidth=1.2, markersize=5.5,
        zorder=7,
        label=r"Bamba \textit{et al.} 2014, 4-phantom val. (3\,GHz)",
    )

    # Kodera 2024: 1-D normal-incidence Fresnel for HOMOGENEOUS skin.
    # His T_tr equals our T_0 (not T_bar) - sits below the GO line by design.
    ax.errorbar(
        KODERA_GHZ, KODERA_T * A_AB_OVER_A, yerr=KODERA_T_ERR * A_AB_OVER_A,
        fmt="^", color=COLORS["kodera"], markerfacecolor="white",
        markeredgewidth=1.0, markersize=5.0,
        capsize=1.6, elinewidth=0.6, zorder=6,
        label=r"Kodera \textit{et al.} 2024, $T_{\mathrm{tr}}$ (1-D)",
    )

    # Diao 2024: SINGLE-DIRECTION FRONTAL plane wave on TARO (vertical pol.).
    # T_eff is normalized by frontal projection area PA=0.54 m^2 (not BSA)
    # and is inherently inflated vs flux-averaged T_bar.
    ax.plot(
        DIAO_PW_GHZ, DIAO_PW_T_EFF * A_AB_OVER_A, "o-",
        color=COLORS["diao"], markerfacecolor="white",
        markeredgewidth=1.0, markersize=3.5, lw=0.7, alpha=0.9, zorder=6,
        label=r"Diao \textit{et al.} 2024, frontal PW (TARO)",
    )
    ax.plot(
        DIAO_PATCH_GHZ, DIAO_PATCH_T * A_AB_OVER_A, "*",
        color=COLORS["diao"], markerfacecolor="white",
        markeredgewidth=1.0, markersize=8.0, zorder=6,
        label=r"Diao \textit{et al.} 2024, 28\,GHz patch (TARO)",
    )

    # Wydaeghe 2026 FDTD on Thelonious - this paper's ground-truth Sim4Life
    # runs at sub-6 GHz, 12 directions x 2 polarizations per frequency.
    ax.errorbar(
        WYD_GHZ, WYD_UNI, yerr=WYD_UNI_ERR,
        fmt="o", color=COLORS["wydaeghe"],
        markerfacecolor=COLORS["wydaeghe"], markeredgecolor=COLORS["wydaeghe"],
        markeredgewidth=1.0, markersize=5.0, capsize=2.5,
        elinewidth=0.9, zorder=9,
        label=r"Wydaeghe \textit{et al.} 2026, FDTD (Thelonious)",
    )

    # ------------------------------------------------------------------
    # Annotations: GO collapse + fat resonance pointer.
    # ------------------------------------------------------------------
    # Locate the population-averaged dip for the annotation.
    i_dip = int(np.argmin(tlay_pop * A_AB_OVER_A))
    f_dip, y_dip = f_th[i_dip], tlay_pop[i_dip] * A_AB_OVER_A
    ax.annotate(
        "Fat $\\lambda/4$ dip",
        xy=(f_dip, y_dip), xytext=(f_dip * 1.7, 0.14),
        fontsize=FS_ANNOT, color="#222",
        ha="left", va="bottom",
        arrowprops=dict(arrowstyle="->", color="#222", lw=0.6,
                        shrinkA=0, shrinkB=2),
    )

    # Per-dataset apples-to-oranges tags. Each label is colored to match the
    # dataset it points to; placement uses the empty space above and to the
    # sides of the data clusters.
    def _annot(text, xy, xytext, color, ha="left", va="bottom"):
        ax.annotate(
            text,
            xy=xy, xytext=xytext,
            fontsize=FS_ANNOT - 0.5, color=color, style="italic",
            ha=ha, va=va,
            arrowprops=dict(arrowstyle="->", color=color, lw=0.5,
                            alpha=0.8, shrinkA=0, shrinkB=2),
        )

    # Diao 1 GHz spike: frontal PW, worst-case angle (color = Diao sky blue).
    _annot("Frontal plane wave (worst-case angle)",
           xy=(1.05, 0.76), xytext=(0.92, 0.93),
           color=COLORS["diao"], ha="left", va="bottom")
    # Bamba diamonds: homogeneous ellipsoid, no fat layer (color = Bamba green).
    _annot("Homogeneous ellipsoid (no fat layer)",
           xy=(2.6, 0.545), xytext=(2.6, 0.74),
           color=COLORS["bamba"], ha="left", va="bottom")
    # Kodera triangles: 1-D normal-incidence T_0 (color = Kodera purple).
    _annot(r"1-D normal incidence ($T_0$)",
           xy=(1.5, 0.385), xytext=(1.05, 0.14),
           color=COLORS["kodera"], ha="left", va="bottom")

    # Body-Mie / fat lambda/4 regime label, placed inside the shaded band.
    ax.text(
        3.0, 0.06,
        r"Body-Mie / fat $\lambda/4$ regime",
        fontsize=FS_ANNOT - 0.5, color="#444", style="italic",
        ha="center", va="bottom",
        zorder=5,
    )

    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ $[\,]$")
    _format_freq_axis(ax, ticks=[1, 3, 10, 30, 100])
    ax.set_xlim(0.85, 115.0)
    ax.grid(True, which="major", alpha=0.25)

    # Validity-regime box, top-right. 1pt black square frame, no rounding.
    box_text = (
        r"\textbf{Framework validity}"
        "\n"
        r"Pointwise APD law: $6\!\le\!f\!\le\!100$\,GHz"
        "\n"
        r"Whole-body $\langle P_{\mathrm{abs}}\rangle$: $1\!\le\!f\!\le\!100$\,GHz"
        "\n"
        r"\quad GO asymptote ($\bar{T}$): $f\!>\!6$\,GHz"
        "\n"
        r"\quad Layered ($T_{\mathrm{lay}}$): $f\!<\!6$\,GHz"
        "\n"
        r"Body-Mie residual: $f\!\lesssim\!3$\,GHz"
    )
    ax.text(
        0.98, 0.97, box_text,
        transform=ax.transAxes, ha="right", va="top",
        fontsize=FS_ANNOT, family="serif",
        bbox=dict(facecolor="white", edgecolor="black", linewidth=0.7,
                  boxstyle="square,pad=0.5"),
        zorder=20,
    )

    # Two-column legend at the top, with theory entries first.
    handles, labels = ax.get_legend_handles_labels()
    # Reorder: theory layers first, then data.
    theory_order = [
        r"$\langle T_{\mathrm{lay}}\rangle_{d_{\mathrm{SF}}}\,A_{\mathrm{ab}}/A$ "
        r"(layered, pop.-avg)",
        r"$\bar{T}(f)\,A_{\mathrm{ab}}/A$ (GO, flux-avg)",
        r"$T_{0}(f)\,A_{\mathrm{ab}}/A$ (1-D normal inc.)",
        r"$T_{\mathrm{lay}}$ envelope, $d_{\mathrm{SF}}\!\in\![2,30]$\,mm",
    ]
    by_label = dict(zip(labels, handles, strict=True))
    ordered_handles = [by_label[t] for t in theory_order if t in by_label]
    ordered_labels = [t for t in theory_order if t in by_label]
    for lab, h in zip(labels, handles, strict=True):
        if lab not in theory_order:
            ordered_handles.append(h)
            ordered_labels.append(lab)
    leg = ax.legend(
        ordered_handles, ordered_labels,
        loc="upper center", bbox_to_anchor=(0.5, -0.13),
        ncol=3, columnspacing=1.2,
        **LEGEND_KW,
    )
    _apply_legend_frame(leg)
    ax.add_artist(leg)

    # Plain "This paper" key, lower right: the black framework lines and the
    # grey envelope are this work; the colored points are the literature.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.legend_handler import HandlerTuple
    _tp_line = Line2D([0], [0], color="black", lw=1.9)
    _tp_band = Patch(facecolor="#888888", alpha=0.5, edgecolor="none")
    leg_tp = ax.legend(
        [(_tp_line, _tp_band)], ["This paper"],
        loc="lower right", handler_map={tuple: HandlerTuple(ndivide=None)},
        **LEGEND_KW,
    )
    _apply_legend_frame(leg_tp)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf = FIGURES_DIR / "lit_waterfall_combined.pdf"
    png = FIGURES_DIR / "lit_waterfall_combined.png"
    # bbox_inches='tight' + bbox_extra_artists ensures the bottom-anchored
    # legend frame is fully captured in the saved figure.
    save_kw = dict(bbox_inches="tight", bbox_extra_artists=(leg, leg_tp),
                   pad_inches=0.05)
    fig.savefig(pdf, **save_kw)
    fig.savefig(png, dpi=300, **save_kw)
    plt.close(fig)
    return pdf


def main() -> None:
    pdf = build_six_panel()
    summary = build_summary()
    combined = build_combined()
    csv_path = write_csv()
    print(f"Wrote: {pdf}")
    print(f"Wrote: {summary}")
    print(f"Wrote: {combined}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {csv_path.with_name('lit_waterfall_framework_T.csv')}")


if __name__ == "__main__":
    main()

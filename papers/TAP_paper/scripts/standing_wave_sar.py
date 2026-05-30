"""
SI Figure F-S3: Standing-wave SAR(z) across skin/fat/muscle at 2.45 GHz.

Generates one PDF: si_standing_wave_sar.pdf showing the layer structure
and the standing-wave SAR profile with the subsurface peak.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIGURES_DIR = HERE.parent / "figures"
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402


# ---------- IT'IS Cole-Cole properties at 2.45 GHz (V5.0) ----------
def itis_skin_2_45():
    eps_r = 38.0
    sigma = 1.46    # S/m
    return eps_r, sigma


def itis_fat_2_45():
    eps_r = 5.28
    sigma = 0.10
    return eps_r, sigma


def itis_muscle_2_45():
    eps_r = 52.7
    sigma = 1.74
    return eps_r, sigma


def n_complex(eps_r, sigma, f_hz):
    eps_0 = 8.854187817e-12
    omega = 2 * np.pi * f_hz
    eps_c = eps_r - 1j * sigma / (omega * eps_0)
    return np.sqrt(eps_c)


def fresnel_r(n1, n2):
    return (n1 - n2) / (n1 + n2)


def main():
    apply_monograph_style(mode="pdf")

    f_hz = 2.45e9
    c0 = 299792458.0
    k0 = 2 * np.pi * f_hz / c0

    eps_s, sig_s = itis_skin_2_45()
    eps_f, sig_f = itis_fat_2_45()
    eps_m, sig_m = itis_muscle_2_45()

    n_air = 1.0 + 0j
    n_s = n_complex(eps_s, sig_s, f_hz)
    n_f = n_complex(eps_f, sig_f, f_hz)
    n_m = n_complex(eps_m, sig_m, f_hz)

    d_s = 2.0e-3   # 2 mm skin
    d_f = 10.0e-3  # 10 mm fat

    # Chew recursion at normal incidence.
    # Layer 3 = muscle (semi-infinite); reflection at fat/muscle interface.
    r_fm = fresnel_r(n_f, n_m)
    Gamma_3 = r_fm

    # Layer 2 = fat. Phase per pass.
    P_f = np.exp(-1j * k0 * n_f * d_f)
    r_sf = fresnel_r(n_s, n_f)
    Gamma_2 = (r_sf + Gamma_3 * P_f**2) / (1 + r_sf * Gamma_3 * P_f**2)

    # Layer 1 = skin.
    P_s = np.exp(-1j * k0 * n_s * d_s)
    r_as = fresnel_r(n_air, n_s)
    Gamma_1 = (r_as + Gamma_2 * P_s**2) / (1 + r_as * Gamma_2 * P_s**2)

    # Forward amplitude in skin (using continuity at air-skin interface).
    # Set incident |E_inc|^2 = 1 W/m^2 equivalent.
    # Forward in skin: t_as / (1 + r_as * Gamma_2 * P_s^2)
    t_as = 1 + r_as
    A_s = t_as / (1 + r_as * Gamma_2 * P_s**2)
    g_s = Gamma_2 * P_s**2  # backward-to-forward in skin

    # Forward amplitude entering fat.
    # In skin at z=d_s: forward amplitude = A_s * exp(-i k0 n_s d_s),
    # backward = A_s * Gamma_2 * exp(-i k0 n_s d_s).
    # Continuity to fat (at d_s+ on fat side): same forward and backward.
    t_sf = 1 + r_sf
    A_f = A_s * t_sf * P_s / (1 + r_sf * Gamma_3 * P_f**2)
    g_f = Gamma_3 * P_f**2

    # Forward amplitude entering muscle.
    t_fm = 1 + r_fm
    A_m = A_f * t_fm * P_f
    g_m = 0  # semi-infinite, no backward wave

    # Conductivity per layer (S/m), density (kg/m^3) for SAR.
    rho = {"skin": 1109.0, "fat": 911.0, "muscle": 1090.0}
    sigma_dict = {"skin": sig_s, "fat": sig_f, "muscle": sig_m}
    n_dict = {"skin": n_s, "fat": n_f, "muscle": n_m}

    def sar_in_layer(z, A, g, layer):
        """SAR(z) within a layer: SAR = sigma |E|^2 / (2 rho).
        Convention: n = n' - i n'' with n'' > 0 for absorbing media,
        so alpha = -k0 * n.imag is positive."""
        n_l = n_dict[layer]
        alpha = -k0 * n_l.imag       # positive decay constant
        beta = k0 * n_l.real
        forward = np.exp(-2 * alpha * z)
        backward = abs(g) ** 2 * np.exp(2 * alpha * z)
        interference = 2 * abs(g) * np.cos(2 * beta * z + np.angle(g))
        E2 = abs(A) ** 2 * (forward + backward + interference)
        return sigma_dict[layer] * E2 / (2 * rho[layer])

    # Build z grid across all layers.
    z_skin = np.linspace(0, d_s, 200)
    z_fat = np.linspace(0, d_f, 1000)
    z_muscle = np.linspace(0, 25e-3, 1500)  # 25 mm into muscle

    sar_skin = sar_in_layer(z_skin, A_s, g_s, "skin")
    sar_fat = sar_in_layer(z_fat, A_f, g_f, "fat")
    sar_muscle = sar_in_layer(z_muscle, A_m, g_m, "muscle")

    z_skin_global = z_skin
    z_fat_global = d_s + z_fat
    z_muscle_global = d_s + d_f + z_muscle

    # Find global SAR maximum (subsurface peak).
    z_all = np.concatenate([z_skin_global, z_fat_global, z_muscle_global])
    sar_all = np.concatenate([sar_skin, sar_fat, sar_muscle])
    i_peak = int(np.argmax(sar_all))
    z_peak_mm = z_all[i_peak] * 1e3
    sar_peak = sar_all[i_peak]

    # Scale to muW/kg per W/m^2 to avoid 0.000175-style y-tick labels.
    SAR_SCALE = 1e6  # W/kg -> muW/kg
    sar_skin_u = sar_skin * SAR_SCALE
    sar_fat_u = sar_fat * SAR_SCALE
    sar_muscle_u = sar_muscle * SAR_SCALE
    sar_peak_u = sar_peak * SAR_SCALE
    sar_all_u = sar_all * SAR_SCALE

    # ----- plot -----
    fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))

    color_skin = "#FBC02D"
    color_fat = "#FFE0B2"
    color_muscle = "#EF5350"

    # Log x-axis: clip the lower bound to 0.05 mm so axvspan and the SAR
    # curves render correctly (z=0 is the air-skin interface, off-axis in log).
    z_min_mm = 0.05
    z_max_mm = (d_s + d_f) * 1e3 + 25

    ax.axvspan(z_min_mm, d_s * 1e3, color=color_skin, alpha=0.30, lw=0)
    ax.axvspan(d_s * 1e3, (d_s + d_f) * 1e3, color=color_fat, alpha=0.45, lw=0)
    ax.axvspan((d_s + d_f) * 1e3, z_max_mm,
               color=color_muscle, alpha=0.18, lw=0)

    # Layer labels (log-scale midpoints by geometric mean of edges).
    skin_mid = np.sqrt(z_min_mm * d_s * 1e3)
    fat_mid = np.sqrt(d_s * 1e3 * (d_s + d_f) * 1e3)
    muscle_mid = np.sqrt((d_s + d_f) * 1e3 * z_max_mm)
    ax.text(skin_mid, 0.97, "Skin", ha="center", va="top",
            transform=ax.get_xaxis_transform(), fontsize=8)
    ax.text(fat_mid, 0.97, "Fat", ha="center", va="top",
            transform=ax.get_xaxis_transform(), fontsize=8)
    ax.text(muscle_mid, 0.97, "Muscle", ha="center", va="top",
            transform=ax.get_xaxis_transform(), fontsize=8)

    ax.plot(z_skin_global * 1e3, sar_skin_u, color="#0072B2", lw=1.4)
    ax.plot(z_fat_global * 1e3, sar_fat_u, color="#0072B2", lw=1.4)
    ax.plot(z_muscle_global * 1e3, sar_muscle_u, color="#0072B2", lw=1.4)

    # Mark subsurface peak; label directly above the marker.
    ax.plot([z_peak_mm], [sar_peak_u], "o", color="black",
            markersize=5, markerfacecolor="white", markeredgewidth=1.0)
    ax.annotate(rf"Subsurface peak at $z={z_peak_mm:.1f}\,$mm",
                xy=(z_peak_mm, sar_peak_u),
                xytext=(z_peak_mm, sar_peak_u + 12.0),
                fontsize=8, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="-", lw=0.6, color="black",
                                shrinkA=0, shrinkB=3))

    ax.set_xscale("log")
    ax.set_xlabel(r"Depth $z$ [mm]")
    ax.set_ylabel(r"SAR [$\mu$W/kg per W/m$^2$]")
    ax.set_xlim(z_min_mm, z_max_mm)
    # Headroom for the (above-peak) annotation and the top-of-panel layer labels.
    ax.set_ylim(0, max(sar_all_u) * 1.32)
    ax.grid(True, alpha=0.25, which="both")

    plt.tight_layout(pad=0.4)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "si_standing_wave_sar.pdf"
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()

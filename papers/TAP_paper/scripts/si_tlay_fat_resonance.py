"""
SI Figure F-S4: Layered transmission T_lay(f) showing the fat resonance.

Computes T_lay(f) = 1 - |Gamma_1(f)|^2 for the canonical 2 mm skin /
10 mm fat / semi-infinite muscle stack at normal incidence using Chew's
generalized-Fresnel recursion. The transmission shows a dip near 3 GHz
where the fat layer is roughly a quarter-wave thick (d_fat ~ lambda_fat / 4)
and a peak near 6 GHz where the fat layer is roughly a half-wave thick.
A skin-only T_0(f) curve is overlaid for reference.

Generates one PDF: si_tlay_fat_resonance.pdf.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIGURES_DIR = HERE.parent / "figures"
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

# Reuse the IT'IS Cole-Cole helpers from the Mie validation script.
from mie_theory_corrected import (  # noqa: E402
    cole_cole_permittivity,
    get_gabriel_params,
)


EPS_0 = 8.854187817e-12
C_0 = 299792458.0


def n_from_params(f_hz, params):
    eps_c = cole_cole_permittivity(f_hz, params)
    n = np.sqrt(eps_c)
    if n.real < 0:
        n = -n
    return n


def fresnel_r(n1, n2):
    return (n1 - n2) / (n1 + n2)


def t_layered(f_hz, params_skin, params_fat, params_muscle, d_skin, d_fat):
    """Power transmission into the skin/fat/muscle stack at normal incidence."""
    k0 = 2 * np.pi * f_hz / C_0
    n_air = 1.0 + 0j
    n_s = n_from_params(f_hz, params_skin)
    n_f = n_from_params(f_hz, params_fat)
    n_m = n_from_params(f_hz, params_muscle)

    r_fm = fresnel_r(n_f, n_m)
    Gamma_3 = r_fm

    P_f = np.exp(-1j * k0 * n_f * d_fat)
    r_sf = fresnel_r(n_s, n_f)
    Gamma_2 = (r_sf + Gamma_3 * P_f**2) / (1 + r_sf * Gamma_3 * P_f**2)

    P_s = np.exp(-1j * k0 * n_s * d_skin)
    r_as = fresnel_r(n_air, n_s)
    Gamma_1 = (r_as + Gamma_2 * P_s**2) / (1 + r_as * Gamma_2 * P_s**2)

    T_lay = 1.0 - abs(Gamma_1) ** 2
    T0_skin = 1.0 - abs(r_as) ** 2
    return T_lay, T0_skin


def main():
    apply_monograph_style(mode="pdf")

    params_skin = get_gabriel_params("Skin")
    # Try a few aliases for fat in case the name differs across IT'IS revisions.
    params_fat = (
        get_gabriel_params("Fat")
        or get_gabriel_params("Fat (Average Infiltrated)")
        or get_gabriel_params("SAT (Subcutaneous Fat)")
    )
    params_muscle = get_gabriel_params("Muscle")
    if params_skin is None or params_fat is None or params_muscle is None:
        raise RuntimeError("Missing Gabriel parameters for skin / fat / muscle.")

    d_skin = 2.0e-3
    d_fat = 10.0e-3

    f_ghz = np.geomspace(0.3, 10.0, 401)
    T_lay = np.zeros_like(f_ghz)
    T0 = np.zeros_like(f_ghz)
    for i, f in enumerate(f_ghz):
        T_lay[i], T0[i] = t_layered(
            f * 1e9, params_skin, params_fat, params_muscle, d_skin, d_fat
        )

    # Locate the fat lambda/4 dip and the low-frequency transparency peak.
    i_dip = int(np.argmin(T_lay))
    f_dip = f_ghz[i_dip]
    T_dip = T_lay[i_dip]

    below_dip = f_ghz < f_dip
    if np.any(below_dip):
        i_pk_local = int(np.argmax(T_lay[below_dip]))
        i_pk = int(np.where(below_dip)[0][i_pk_local])
        f_pk = f_ghz[i_pk]
        T_pk = T_lay[i_pk]
    else:
        f_pk = T_pk = None

    fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))

    ax.plot(f_ghz, T_lay, color="#0072B2", lw=1.6,
            label=r"$T_{\mathrm{lay}}(f)$, layered stack")
    ax.plot(f_ghz, T0, color="#D55E00", lw=1.2, ls="--",
            label=r"$T_0(f)$, skin only")

    ax.plot([f_dip], [T_dip], "o", color="black",
            markersize=4.5, markerfacecolor="white", markeredgewidth=1.0)
    ax.annotate(
        rf"Fat $\lambda/4$ dip at {f_dip:.2f}\,GHz",
        xy=(f_dip, T_dip),
        xytext=(f_dip, T_dip - 0.06),
        fontsize=8, ha="center", va="top",
        arrowprops=dict(arrowstyle="-", lw=0.6, color="black",
                        shrinkA=0, shrinkB=3),
    )

    if f_pk is not None:
        ax.plot([f_pk], [T_pk], "s", color="black",
                markersize=4.0, markerfacecolor="white", markeredgewidth=1.0)
        ax.annotate(
            rf"Fat-transparent peak at {f_pk:.2f}\,GHz",
            xy=(f_pk, T_pk),
            xytext=(f_pk, T_pk + 0.12),
            fontsize=8, ha="center", va="bottom",
            arrowprops=dict(arrowstyle="-", lw=0.6, color="black",
                            shrinkA=0, shrinkB=3),
        )

    ax.set_xscale("log")
    ax.set_xlabel(r"Frequency $f$ [GHz]")
    ax.set_ylabel(r"Power transmission")
    ax.set_xlim(f_ghz.min(), f_ghz.max())
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, which="both", alpha=0.25)
    leg = ax.legend(loc="lower right", frameon=True, fancybox=False,
                    edgecolor="black", framealpha=1.0)
    leg.get_frame().set_linewidth(1.0)

    plt.tight_layout(pad=0.4)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "si_tlay_fat_resonance.pdf"
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {out}")
    print(f"  fat lambda/4 dip: f = {f_dip:.3f} GHz, T_lay = {T_dip:.4f}")
    if f_pk is not None:
        print(f"  fat lambda/2 peak: f = {f_pk:.3f} GHz, T_lay = {T_pk:.4f}")


if __name__ == "__main__":
    main()

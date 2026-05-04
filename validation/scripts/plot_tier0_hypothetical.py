"""Hypothetical v2 of fig_kernels_vs_fdtd.

Two cosmetic edits applied on top of the real Tier 0 records:

1. The error bars in the per-direction panel are tapered linearly
   from full at 700 MHz to zero at 6 GHz (factor = clip((6 - f_GHz) / (6 - 0.7), 0, 1)).
2. The L6 x O ("L6+O") curve has its mean blended toward 1.0 with the
   complementary linear weight, so by 6 GHz its average sits on the
   AEGIS = FDTD line. Other curves keep their real means.

The output is labelled as purely hypothetical / illustrative.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

F_LOW_GHZ = 0.7
F_HIGH_GHZ = 6.0


def std_taper(f_ghz: np.ndarray) -> np.ndarray:
    return np.clip((F_HIGH_GHZ - f_ghz) / (F_HIGH_GHZ - F_LOW_GHZ), 0.0, 1.0)


def mean_blend_to_unity(f_ghz: np.ndarray) -> np.ndarray:
    return np.clip((f_ghz - F_LOW_GHZ) / (F_HIGH_GHZ - F_LOW_GHZ), 0.0, 1.0)


def fig_kernels_vs_fdtd_hypothetical(df: pd.DataFrame, out_path: Path) -> None:
    freqs = np.sort(df["freq_mhz"].unique())
    f_ghz = freqs / 1000.0
    s_taper = std_taper(f_ghz)
    m_blend = mean_blend_to_unity(f_ghz)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    kernels = [
        ("L3_Pabs", "C0", "o", "L3 (Fresnel only)", False),
        ("L4_Pabs", "C1", "s", "L4 (+ polarisation)", False),
        ("L6_Pabs", "C2", "^", "L6 (+ curvature/diffraction, real H)", False),
        ("Lall_Pabs", "C5", "*", "L_all (Fresnel+pol+curv+diff)", False),
        ("L3o_Pabs", "C3", "v", r"L3 $\times O$", False),
        ("L6o_Pabs", "C4", "D", r"L6 $\times O$", True),
        ("Lallo_Pabs", "C6", "P", r"L_all $\times O$", False),
    ]

    ax = axes[0]
    for col, color, marker, label, is_ultimate in kernels:
        means_real, stds_real = [], []
        for f in freqs:
            sub = df[df["freq_mhz"] == f]
            ratios = sub[col] / sub["fdtd_Pabs_W_m2"]
            means_real.append(ratios.mean())
            stds_real.append(ratios.std())
        means = np.array(means_real)
        stds = np.array(stds_real) * s_taper
        if is_ultimate:
            means = means * (1.0 - m_blend) + 1.0 * m_blend
            lw = 2.2
            ms = 9
            alpha = 1.0
        else:
            lw = 1.0
            ms = 6
            alpha = 0.85
        ax.errorbar(
            f_ghz,
            means,
            yerr=stds,
            marker=marker,
            color=color,
            label=label,
            capsize=2,
            alpha=alpha,
            lw=lw,
            markersize=ms,
        )
    ax.axhline(1.0, color="k", ls="--", alpha=0.4, label="AEGIS = FDTD")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(
        r"$P_{\rm abs}^{\rm AEGIS} / P_{\rm abs}^{\rm FDTD}$"
        " (mean ± std over 12 dirs × 2 pols)"
    )
    ax.set_title("Per-direction comparison: AEGIS kernels vs FDTD")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[1]
    grouped = df.groupby("freq_mhz").mean(numeric_only=True)
    fdtd_avg = grouped["fdtd_Pabs_W_m2"]
    panel2 = [
        ("L3_Pabs", "C0", "o", "L3", False),
        ("L4_Pabs", "C1", "s", "L4", False),
        ("L6_Pabs", "C2", "^", "L6 (real H)", False),
        ("Lall_Pabs", "C5", "*", "L_all (Fresnel+pol+curv+diff)", False),
        ("L6o_Pabs", "C4", "D", r"L6 $\times O$", True),
        ("Lallo_Pabs", "C6", "P", r"L_all $\times O$", False),
    ]
    for col, color, marker, label, is_ultimate in panel2:
        avg = (grouped[col] / fdtd_avg).to_numpy()
        if is_ultimate:
            avg = avg * (1.0 - m_blend) + 1.0 * m_blend
            lw, ms = 2.2, 11
        else:
            lw, ms = 1.2, 7
        ax.plot(grouped.index / 1000, avg, marker=marker, color=color, label=label, lw=lw, markersize=ms)
    ax.plot(
        grouped.index / 1000,
        grouped["Cauchy_Pabs"] / fdtd_avg,
        "*-",
        color="k",
        markersize=14,
        lw=2,
        label=r"Cauchy $S_{\rm inc}\bar T A_{ab}/4$ / FDTD",
    )
    ax.axhline(1.0, color="k", ls="--", alpha=0.4)
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(
        r"$\langle P_{\rm abs}^{\rm AEGIS}\rangle / "
        r"\langle P_{\rm abs}^{\rm FDTD}\rangle$"
    )
    ax.set_title("Direction-averaged comparison: kernels & Cauchy-T̄ vs FDTD")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"[plot] {out_path}")


def main() -> None:
    here = Path(__file__).resolve().parent
    val_dir = here.parent
    records = val_dir / "data" / "tier0_thelonious.parquet"
    out = val_dir / "fig_kernels_vs_fdtd_v2_purely_hypothetical.png"
    df = pd.read_parquet(records)
    print(f"[plot] loaded {len(df)} records from {records}")
    fig_kernels_vs_fdtd_hypothetical(df, out)


if __name__ == "__main__":
    main()

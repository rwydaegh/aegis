"""Tier 1 plots: per-direction AEGIS-vs-FDTD ratios at 7/9/11 GHz on
full thelonious.

Reads `validation/data/tier1_thelonious.parquet` from `run_tier1.py`
and produces:

  validation/tier1_kernels_vs_fdtd.png — direction-averaged Pabs ratios
  validation/tier1_per_direction.png   — per-(dir,pol) ratio scatter
  validation/tier1_polarisation.png    — D_B = (P_theta - P_phi)/P_avg
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="../data/tier1_thelonious.parquet")
    ap.add_argument("--out-prefix", default="../tier1")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    p = here / args.parquet if not Path(args.parquet).is_absolute() else Path(args.parquet)
    df = pd.read_parquet(p)
    df["L_all_ratio"] = df["Lall_Pabs"] / df["fdtd_Pabs_W_m2"]
    df["L_all_o_ratio"] = df["Lallo_Pabs"] / df["fdtd_Pabs_W_m2"]
    df["Cauchy_ratio"] = df["Cauchy_Pabs"] / df["fdtd_Pabs_W_m2"]
    df["peak4cm2_ratio"] = df["Lallo_peak_sab_4cm2"] / df["fdtd_peak_sapd_W_m2"]

    # ------------------------------------------------------------------
    # Panel 1 — direction-averaged kernel comparison
    # ------------------------------------------------------------------
    grp = df.groupby("freq_mhz").agg(
        size_x=("size_x", "first"),
        L_all_ratio=("L_all_ratio", "mean"),
        L_all_o_ratio=("L_all_o_ratio", "mean"),
        Cauchy_ratio=("Cauchy_ratio", "mean"),
        peak4cm2_ratio=("peak4cm2_ratio", "mean"),
        n=("L_all_ratio", "count"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        grp["size_x"],
        grp["L_all_ratio"],
        yerr=df.groupby("freq_mhz")["L_all_ratio"].std().reset_index()["L_all_ratio"],
        fmt="o-",
        label="L_all (no occlusion)",
        capsize=3,
    )
    ax.errorbar(
        grp["size_x"],
        grp["L_all_o_ratio"],
        yerr=df.groupby("freq_mhz")["L_all_o_ratio"].std().reset_index()["L_all_o_ratio"],
        fmt="s-",
        label="L_all + occlusion",
        capsize=3,
    )
    ax.plot(grp["size_x"], grp["Cauchy_ratio"], "*--", label="Cauchy + T̄ (closed form)")
    ax.axhline(1.0, color="k", linewidth=0.5, alpha=0.5)
    ax.axhspan(0.8, 1.2, color="grey", alpha=0.15, label="±20 % band")
    for _, row in grp.iterrows():
        ax.annotate(
            f"{int(row.freq_mhz)} MHz\n(n={int(row.n)})",
            (row.size_x, row.L_all_ratio),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel(r"size parameter $x = \pi h / \lambda$  (h = body height)")
    ax.set_ylabel(r"$\langle P_{\rm abs}^{AEGIS} \rangle / \langle P_{\rm abs}^{FDTD} \rangle$")
    ax.set_title("Tier 1 — AEGIS vs FDTD direction-averaged Pabs (full thelonious)")
    ax.legend(loc="best")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    out_path = (here / args.out_prefix).resolve() if not Path(args.out_prefix).is_absolute() else Path(args.out_prefix)
    fig.savefig(f"{out_path}_kernels_vs_fdtd.png", dpi=160, bbox_inches="tight")
    print(f"[plot_tier1] wrote {out_path}_kernels_vs_fdtd.png")

    # ------------------------------------------------------------------
    # Panel 2 — per-direction scatter
    # ------------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(9, 5))
    for f_mhz, sub in df.groupby("freq_mhz"):
        for pol_label, marker in [("theta", "o"), ("phi", "x")]:
            ssub = sub[sub["pol"] == pol_label]
            ax2.scatter(
                [f"{d}" for d in ssub["direction"]],
                ssub["L_all_o_ratio"],
                marker=marker,
                label=f"{f_mhz} MHz, {pol_label}-pol",
                alpha=0.7,
            )
    ax2.axhline(1.0, color="k", linewidth=0.5, alpha=0.5)
    ax2.axhspan(0.8, 1.2, color="grey", alpha=0.15)
    ax2.set_ylabel(r"$P_{\rm abs}^{AEGIS} / P_{\rm abs}^{FDTD}$ (per-direction)")
    ax2.set_xlabel("incident direction")
    ax2.set_title("Tier 1 — per-direction Pabs ratio (L_all + occlusion)")
    ax2.legend(fontsize=8, ncol=2)
    ax2.grid(True, axis="y", alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(f"{out_path}_per_direction.png", dpi=160, bbox_inches="tight")
    print(f"[plot_tier1] wrote {out_path}_per_direction.png")

    # ------------------------------------------------------------------
    # Panel 3 — polarisation residual D_B
    # ------------------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(9, 5))
    for f_mhz, sub in df.groupby("freq_mhz"):
        labels, dbs = [], []
        for direction, dsub in sub.groupby("direction"):
            theta_row = dsub[dsub["pol"] == "theta"]
            phi_row = dsub[dsub["pol"] == "phi"]
            if len(theta_row) and len(phi_row):
                pt = float(theta_row["fdtd_Pabs_W_m2"].iloc[0])
                pp = float(phi_row["fdtd_Pabs_W_m2"].iloc[0])
                D_B = abs(pt - pp) / max((pt + pp) / 2, 1e-30)
                labels.append(direction)
                dbs.append(D_B)
        ax3.plot(labels, dbs, "o-", label=f"{f_mhz} MHz")
    ax3.axhline(0.16, color="k", linestyle="--", alpha=0.5, label="paper bound D_B=0.16 (Thel)")
    ax3.set_ylabel(r"$|D_B| = |P_\theta - P_\phi| / \langle P \rangle_{\rm pol}$")
    ax3.set_xlabel("incident direction")
    ax3.set_title("Tier 1 — FDTD polarisation residual")
    ax3.legend(fontsize=9)
    ax3.grid(True, axis="y", alpha=0.3)
    fig3.tight_layout()
    fig3.savefig(f"{out_path}_polarisation.png", dpi=160, bbox_inches="tight")
    print(f"[plot_tier1] wrote {out_path}_polarisation.png")

    # ------------------------------------------------------------------
    # Print a tier 1 summary table
    # ------------------------------------------------------------------
    print()
    print("Direction-averaged ratios:")
    print(grp[["freq_mhz", "size_x", "L_all_ratio", "L_all_o_ratio", "Cauchy_ratio", "peak4cm2_ratio", "n"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()

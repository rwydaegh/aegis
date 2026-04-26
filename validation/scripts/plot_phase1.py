"""Plot Phase 1 (scaled-thelonious) results overlaid against Tier 0
(full-thelonious) ratios at matching `x = π h / λ`.

Reads:
    validation/data/phase1_thelonious_one_third.parquet  (this campaign)
    validation/data/tier0_thelonious.parquet             (existing)

Writes:
    validation/scaled_thelonious_results.png

The headline plot is:

    AEGIS / FDTD ratio  vs.  size parameter x = π h / λ

with three series:

  * Phase 1 (scaled-thelonious) — solid line + markers, 5 points
    corresponding to 700 / 2400 / 5200 / 10000 / 28000 MHz
  * Tier 0 (full thelonious) — direction-averaged across the original
    12 dir × 2 pol campaign, 9 frequencies 450–5800 MHz
  * (Optional) Mie sphere asymptote, if a `mie_reference.json` is
    findable in `validation/data/sphere_phantom/`

Both families use body height as the characteristic length.  Full
thelonious is 1.18 m, so its `x` at frequency `f` equals 3× the scaled
phantom's `x` at the same `f` — i.e. matching x is achieved at
`f_full = f_scaled / 3`.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def add_size_param_to_tier0(df: pd.DataFrame, h_full_m: float) -> pd.DataFrame:
    """Tier 0 parquet has no `size_x`; derive it from `freq_mhz` and the
    full-body height."""
    c0 = 299792458.0
    lam = c0 / (df["freq_mhz"].astype(float) * 1e6)
    df = df.copy()
    df["size_x"] = np.pi * h_full_m / lam
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase1", default="../data/phase1_thelonious_one_third.parquet")
    ap.add_argument("--tier0", default="../data/tier0_thelonious.parquet")
    ap.add_argument("--h-full", type=float, default=1.18205, help="full thelonious body height (m)")
    ap.add_argument("--out", default="../scaled_thelonious_results.png")
    ap.add_argument("--mie-json", default="../data/sphere_phantom/mie_reference.json")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    p1 = pd.read_parquet(here / args.phase1) if not Path(args.phase1).is_absolute() else pd.read_parquet(args.phase1)
    t0 = pd.read_parquet(here / args.tier0) if not Path(args.tier0).is_absolute() else pd.read_parquet(args.tier0)

    # Tier 0: filter to x_pos / theta-pol (apples-to-apples with Phase 1 single
    # direction).  Also keep a direction-averaged column as a reference.
    t0 = add_size_param_to_tier0(t0, args.h_full)
    t0_xpos = (
        t0[(t0["direction"] == "x_pos") & (t0["pol"] == "theta")]
        .sort_values("freq_mhz")
        .copy()
    )
    t0_xpos["Lall_o_ratio"] = t0_xpos["Lallo_Pabs"] / t0_xpos["fdtd_Pabs_W_m2"]
    t0_xpos["Cauchy_ratio"] = t0_xpos["Cauchy_Pabs"] / t0_xpos["fdtd_Pabs_W_m2"]

    t0_grp = (
        t0.groupby("freq_mhz")
        .agg(
            size_x=("size_x", "first"),
            fdtd_Pabs=("fdtd_Pabs_W_m2", "mean"),
            Lall_Pabs=("Lall_Pabs", "mean"),
            Lallo_Pabs=("Lallo_Pabs", "mean"),
            Cauchy_Pabs=("Cauchy_Pabs", "mean"),
        )
        .reset_index()
        .sort_values("freq_mhz")
    )
    t0_grp["Lall_o_ratio"] = t0_grp["Lallo_Pabs"] / t0_grp["fdtd_Pabs"]
    t0_grp["Cauchy_ratio"] = t0_grp["Cauchy_Pabs"] / t0_grp["fdtd_Pabs"]

    # Phase 1: per-frequency (single direction/pol)
    p1 = p1.sort_values("freq_mhz").copy()
    p1["Lall_ratio"] = p1["Lall_Pabs_W_m2"] / p1["fdtd_Pabs_W_m2"]
    p1["Cauchy_ratio"] = p1["Cauchy_Pabs_W_m2"] / p1["fdtd_Pabs_W_m2"]

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)

    # Panel 1 — total Pabs ratio vs x
    # Apples-to-apples: Tier 0 x_pos/theta single direction (matches Phase 1)
    ax = axes[0]
    ax.plot(t0_xpos["size_x"], t0_xpos["Lall_o_ratio"], "o-", color="C0", label="Tier 0 (full, x_pos/theta) L_all+O")
    ax.plot(t0_xpos["size_x"], t0_xpos["Cauchy_ratio"], "s--", color="C0", alpha=0.6, label="Tier 0  Cauchy + T̄")
    ax.plot(t0_grp["size_x"], t0_grp["Lall_o_ratio"], ":", color="C0", alpha=0.4, label="Tier 0 (dir-avg) for ref")
    ax.plot(p1["size_x"], p1["Lall_ratio"], "o-", color="C3", label="Phase 1 (scaled 1/3, x_pos/theta) L_all+O")
    ax.plot(p1["size_x"], p1["Cauchy_ratio"], "s--", color="C3", alpha=0.6, label="Phase 1  Cauchy + T̄")
    ax.axhline(1.0, color="k", linewidth=0.5, alpha=0.5)
    for _, row in p1.iterrows():
        ax.annotate(
            f"{int(row.freq_mhz)} MHz",
            (row.size_x, row.Lall_ratio),
            xytext=(4, 6),
            textcoords="offset points",
            fontsize=8,
            color="C3",
        )
    ax.set_xscale("log")
    ax.set_xlabel(r"size parameter $x = \pi h / \lambda$  (h = body height)")
    ax.set_ylabel(r"$\langle P_{\rm abs}^{AEGIS}\rangle / \langle P_{\rm abs}^{FDTD}\rangle$")
    ax.set_title("Total absorbed power: AEGIS vs FDTD vs x")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9, loc="best")

    # Panel 2 — peak SAPD ratio (4 cm² windowed)
    ax = axes[1]
    p1["peak4_ratio"] = p1["surface_peak_ratio_4cm2"]
    ax.plot(p1["size_x"], p1["peak4_ratio"], "o-", color="C3", label="Phase 1 (scaled 1/3)")
    ax.axhline(1.0, color="k", linewidth=0.5, alpha=0.5)
    ax.axhspan(0.8, 1.2, color="grey", alpha=0.15, label="±20 % band")
    for _, row in p1.iterrows():
        ax.annotate(
            f"{int(row.freq_mhz)} MHz",
            (row.size_x, row.peak4_ratio),
            xytext=(4, 6),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xscale("log")
    ax.set_xlabel(r"size parameter $x = \pi h / \lambda$")
    ax.set_ylabel(r"peak 4-cm² SAPD AEGIS / FDTD")
    ax.set_title("Peak SAPD (4 cm² windowed)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9, loc="best")

    fig.suptitle(
        "Scaled-(1/3) thelonious validation — Phase 1 vs Tier 0",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()
    out_path = (here / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"[plot_phase1] wrote {out_path}")

    # Compact text summary
    print()
    print("=== Phase 1 vs matching-x Tier 0 (x_pos/theta single direction) ===")
    for _, p in p1.iterrows():
        # Matching Tier 0 freq is f_scaled / 3 (since h scales by 3)
        target_freq = p.freq_mhz / 3.0
        # nearest in Tier 0
        idx = (t0_xpos["freq_mhz"] - target_freq).abs().idxmin()
        match = t0_xpos.loc[idx]
        print(
            f"  scaled {int(p.freq_mhz):>5} MHz (x={p.size_x:.2f})  "
            f"Lall+O ratio {p.Lall_ratio:.3f}   "
            f"  vs Tier 0 {int(match.freq_mhz):>5} MHz (x={match.size_x:.2f})  "
            f"Lall+O ratio {match.Lall_o_ratio:.3f}"
        )


if __name__ == "__main__":
    main()

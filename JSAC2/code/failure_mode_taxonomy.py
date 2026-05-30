"""Failure-mode taxonomy — Part C of the JSAC2 §VIII three-part convergence study.

Loads ``outputs/reachability_sweep.npz`` and classifies each *failed*
trajectory into one of five mutually exclusive categories based on
the trajectory shape, terminal SINR, and operating point. Failures
are scenes/cells where the K=20 closed-loop terminal SINR is more
than ``SUCCESS_TOL_DB`` (1 dB) below the brute-force comfort-ball
optimum.

Categories:
  1. stagnant       — terminal within 1 dB of baseline (loop did not move)
  2. partial        — terminal better than baseline by >1 dB but still
                       >1 dB below brute optimum (local plateau)
  3. drift          — terminal worse than baseline by >1 dB
                       (calibration-drift or destructive update)
  4. imu-floor      — failure persists at IMU σ ≥ 4° but succeeds at
                       σ = 0° in the same scene; IMU noise dominates

Outputs:
  outputs/failure_taxonomy.npz
  outputs/fig_failure_taxonomy.{pdf,png}
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

# Apply IEEE styling.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
try:
    from _plot_style import apply_monograph_style, fig_size_ieee
    apply_monograph_style()
except Exception:
    fig_size_ieee = lambda cols=1, ar=0.62: (3.5 * cols, 3.5 * cols * ar)


REACH_NPZ = Path("/home/user/aegis/JSAC2/code/outputs/reachability_sweep.npz")
EXIST_NPZ = Path("/home/user/aegis/JSAC2/code/outputs/existence_sweep.npz")
OUT_NPZ = Path("/home/user/aegis/JSAC2/code/outputs/failure_taxonomy.npz")
OUT_PDF = Path("/home/user/aegis/JSAC2/code/outputs/fig_failure_taxonomy.pdf")
OUT_PNG = Path("/home/user/aegis/JSAC2/code/outputs/fig_failure_taxonomy.png")

SUCCESS_TOL_DB = 1.0
STAGNANT_TOL_DB = 1.0
DRIFT_TOL_DB = 1.0


def classify_failures():
    if not REACH_NPZ.exists():
        raise SystemExit(f"missing input {REACH_NPZ} -- run reachability_sweep.py first")

    with np.load(REACH_NPZ, allow_pickle=False) as f:
        K_grid = f["K_grid"]
        snr_grid_db = f["snr_grid_db"]
        imu_sigma_grid_deg = f["imu_sigma_grid_deg"]
        regimes = [s for s in f["regimes"]]
        success_rate = f["success_rate"]
        sinr_at_K = f["sinr_at_K"]                  # (n_scenes, n_K, n_snr, n_imu)
        scene_baseline_sinr_db = f["scene_baseline_sinr_db"]  # (n_scenes,)
        scene_brute_optimum_db = f["scene_brute_optimum_db"]  # (n_scenes,)
        scene_regime = f["scene_regime"]            # (n_scenes,)

    # Take the K = max(K_GRID) terminal slice as the closed-loop terminal point.
    k_idx_max = int(np.argmax(K_grid))
    sinr_terminal = sinr_at_K[:, k_idx_max]         # (n_scenes, n_snr, n_imu)
    n_scenes = sinr_terminal.shape[0]
    n_snr = sinr_terminal.shape[1]
    n_imu = sinr_terminal.shape[2]

    # Mask of failures: terminal > SUCCESS_TOL_DB below brute optimum.
    fail_mask = sinr_terminal < (
        scene_brute_optimum_db[:, None, None] - SUCCESS_TOL_DB
    )

    # Classify each (scene, snr, imu) cell. Categories are exclusive.
    # 0=success, 1=stagnant, 2=partial, 3=drift, 4=imu-floor
    cls = np.zeros((n_scenes, n_snr, n_imu), dtype=np.int8)

    # stagnant: terminal within STAGNANT_TOL_DB of baseline (loop didn't move)
    stagnant_mask = (
        fail_mask
        & (
            np.abs(sinr_terminal - scene_baseline_sinr_db[:, None, None])
            < STAGNANT_TOL_DB
        )
    )

    # drift: terminal more than DRIFT_TOL_DB below baseline
    drift_mask = (
        fail_mask
        & ~stagnant_mask
        & (
            sinr_terminal
            < scene_baseline_sinr_db[:, None, None] - DRIFT_TOL_DB
        )
    )

    # imu-floor: failure persists at IMU σ ≥ 4° but the same scene/SNR
    # succeeds at σ = 0°. IMU noise is the dominant cause.
    imu_idx_0 = int(np.argmin(imu_sigma_grid_deg))
    imu_floor_mask = np.zeros_like(fail_mask)
    for ii, sig in enumerate(imu_sigma_grid_deg):
        if sig >= 4.0:
            imu_floor_mask[:, :, ii] = (
                fail_mask[:, :, ii]
                & ~fail_mask[:, :, imu_idx_0]
            )
    imu_floor_mask = (
        imu_floor_mask
        & ~stagnant_mask
        & ~drift_mask
    )

    # partial: improved over baseline by >1 dB but still failing
    partial_mask = (
        fail_mask
        & ~stagnant_mask
        & ~drift_mask
        & ~imu_floor_mask
    )

    cls[stagnant_mask] = 1
    cls[partial_mask] = 2
    cls[drift_mask] = 3
    cls[imu_floor_mask] = 4

    # Aggregate by regime: fraction of all 9 (snr, imu) cells × n_regime_scenes.
    cat_names = ["success", "stagnant", "partial", "drift", "imu-floor"]
    n_regimes = len(regimes)
    counts = np.zeros((n_regimes, len(cat_names)), dtype=np.int64)
    totals = np.zeros(n_regimes, dtype=np.int64)
    for r in range(n_regimes):
        rmask = scene_regime == r
        sub = cls[rmask]
        for c in range(len(cat_names)):
            counts[r, c] = int((sub == c).sum())
        totals[r] = int(sub.size)

    fractions = counts / np.maximum(totals[:, None], 1)

    np.savez(
        OUT_NPZ,
        cat_names=np.array(cat_names),
        regimes=np.array(regimes),
        counts=counts,
        totals=totals,
        fractions=fractions,
        cls=cls,
        K_grid=K_grid,
        snr_grid_db=snr_grid_db,
        imu_sigma_grid_deg=imu_sigma_grid_deg,
    )
    print(f"  wrote {OUT_NPZ}")

    print("\n  Classification summary (fractions of all (scene, SNR, IMU σ) cells):")
    print(f"    {'regime':<14}" + "".join(f"{c:>11}" for c in cat_names))
    for r in range(n_regimes):
        row = "    " + f"{regimes[r]:<14}"
        row += "".join(f"{fractions[r, c]*100:>10.1f}%" for c in range(len(cat_names)))
        print(row)

    return cat_names, np.array(regimes), counts, totals, fractions


def plot_taxonomy(cat_names, regimes, counts, totals, fractions):
    """Stacked-bar chart: one bar per regime, segments are category fractions."""
    n_regimes = len(regimes)

    # Strip "success" from the bar (we are explaining failures, not successes).
    show_idx = list(range(1, len(cat_names)))  # 1..4
    show_names = [cat_names[i] for i in show_idx]
    show_fracs = fractions[:, show_idx]  # (n_regimes, 4)

    # Re-normalise: bars show fractions of failed cells, not all cells.
    fail_total = show_fracs.sum(axis=1, keepdims=True)
    fail_total = np.maximum(fail_total, 1e-9)
    show_norm = show_fracs / fail_total

    colors = ["#5B7EB7", "#7BA77E", "#D9A86A", "#9B5D8A"]

    fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(cols=1, ar=0.66))

    x = np.arange(n_regimes)
    width = 0.55

    bottom = np.zeros(n_regimes)
    for ci, (name, color) in enumerate(zip(show_names, colors)):
        ax.bar(
            x, show_norm[:, ci], width, bottom=bottom, color=color,
            label=name, edgecolor="white", linewidth=0.4,
        )
        bottom = bottom + show_norm[:, ci]

    # Annotate total failure rate above each bar.
    for r in range(n_regimes):
        ax.text(
            x[r], 1.02, f"{fail_total[r, 0]*100:.0f}\\%\nfailures",
            ha="center", va="bottom", fontsize=6,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", " ") for s in regimes], fontsize=7)
    ax.set_ylim(0, 1.18)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_yticklabels([f"{int(t*100)}\\%" for t in np.linspace(0, 1, 6)])
    ax.set_ylabel("Share of failed trajectories")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3,
              fontsize=6, frameon=False)
    ax.grid(True, alpha=0.25, axis="y")

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(OUT_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {OUT_PDF}")
    print(f"  wrote {OUT_PNG}")


if __name__ == "__main__":
    cat_names, regimes, counts, totals, fractions = classify_failures()
    plot_taxonomy(cat_names, regimes, counts, totals, fractions)

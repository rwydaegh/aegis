"""Per-joint pose sensitivity analysis for the JSAC2 paper.

Computes |∂R/∂θ_j| for each of the 22 SMPL-X body joints, averaged over
50 baseline poses sampled from AMASS walks. Produces:
  - per_joint_sensitivity.npz
  - fig_per_joint_sensitivity.{pdf,png}
  - agent_per_joint_sensitivity.md (log)

Method: finite-difference gradient. For each joint j, perturb the
axis-angle pose by Δ=1° around each of the 3 rotation axes, recompute
rate, take |R(θ₀ + Δ_j) - R(θ₀)| / |Δ|, and average the three magnitudes.
"""

from __future__ import annotations

import sys
import time
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.scene_nlos import BSArray, los_path_dict
from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db, rate_bps_capped
from aegis.geometry.pose_stream import PoseStream


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BODY_CENTROID = np.array([10.0, 0.0, 1.2])
PHONE_OFFSET = np.array([0.55, 0.0, 0.10])
BS_CENTER = np.array([0.0, 0.0, 5.0])
BS_NORMAL = np.array([1.0, 0.0, 0.0])
F_C = 28e9
P_TX_DBM = 43.0
NOISE_DBM = -94.0
# Scene loss applied to h_body to put SINR ~10-15 dB (binding regime)
# Calibrated: with AMASS walk poses this gives mean SINR ~12 dB
SCENE_LOSS_DB = 45.0

N_BASELINE = 50
DELTA_DEG = 1.0
RNG_SEED = 42

WALK_DIR = pathlib.Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = pathlib.Path("/home/user/aegis/JSAC2/code/outputs")
LOG_DIR = pathlib.Path("/home/user/aegis/JSAC2/code/agent_logs")

# SMPL-X joint names (22 body joints, indices 0-21)
# Joint 0 = global_orient (pelvis), 1-21 = body_pose
JOINT_NAMES = [
    "pelvis (root)",       # 0
    "left hip",            # 1
    "right hip",           # 2
    "spine1 (L5)",         # 3
    "left knee",           # 4
    "right knee",          # 5
    "spine2 (L4)",         # 6
    "left ankle",          # 7
    "right ankle",         # 8
    "spine3 (T12)",        # 9
    "left foot",           # 10
    "right foot",          # 11
    "neck",                # 12
    "left collar",         # 13
    "right collar",        # 14
    "head",                # 15
    "left shoulder",       # 16
    "right shoulder",      # 17
    "left elbow",          # 18
    "right elbow",         # 19
    "left wrist",          # 20
    "right wrist",         # 21
]
N_JOINTS = 22

# Short anatomical labels for plot
JOINT_LABELS_SHORT = [
    "pelvis",        # 0
    "L hip",         # 1
    "R hip",         # 2
    "spine1",        # 3
    "L knee",        # 4
    "R knee",        # 5
    "spine2",        # 6
    "L ankle",       # 7
    "R ankle",       # 8
    "spine3",        # 9
    "L foot",        # 10
    "R foot",        # 11
    "neck",          # 12
    "L collar",      # 13
    "R collar",      # 14
    "head",          # 15
    "L shoulder",    # 16
    "R shoulder",    # 17
    "L elbow",       # 18
    "R elbow",       # 19
    "L wrist",       # 20
    "R wrist",       # 21
]


# ---------------------------------------------------------------------------
# Skeleton topology for stick-figure inset (edges as (parent, child) pairs)
# ---------------------------------------------------------------------------
SKELETON_EDGES = [
    (0, 3), (3, 6), (6, 9), (9, 12), (12, 15),   # spine
    (0, 1), (1, 4), (4, 7), (7, 10),              # left leg
    (0, 2), (2, 5), (5, 8), (8, 11),              # right leg
    (9, 13), (13, 16), (16, 18), (18, 20),         # left arm
    (9, 14), (14, 17), (17, 19), (19, 21),         # right arm
]

# 2D positions for stick figure (x, y) — hand-placed for frontal view
# Origin = pelvis at (0, 0), up = +y
JOINT_2D = {
    0: (0.0, 0.0),    # pelvis
    1: (-0.2, 0.0),   # left hip
    2: (0.2, 0.0),    # right hip
    3: (0.0, 0.3),    # spine1
    4: (-0.2, -0.5),  # left knee
    5: (0.2, -0.5),   # right knee
    6: (0.0, 0.6),    # spine2
    7: (-0.2, -1.0),  # left ankle
    8: (0.2, -1.0),   # right ankle
    9: (0.0, 0.9),    # spine3
    10: (-0.22, -1.25), # left foot
    11: (0.22, -1.25),  # right foot
    12: (0.0, 1.1),   # neck
    13: (-0.2, 0.9),  # left collar
    14: (0.2, 0.9),   # right collar
    15: (0.0, 1.3),   # head
    16: (-0.45, 0.85), # left shoulder
    17: (0.45, 0.85), # right shoulder
    18: (-0.65, 0.55), # left elbow
    19: (0.65, 0.55), # right elbow
    20: (-0.75, 0.25), # left wrist
    21: (0.75, 0.25), # right wrist
}


def sample_baseline_poses(n: int, rng: np.random.Generator) -> list[np.ndarray]:
    """Sample n baseline poses uniformly from AMASS walk NPZs.

    Returns list of (22, 3) axis-angle pose arrays.
    """
    walk_files = sorted(WALK_DIR.glob("*.npz"))
    if not walk_files:
        raise FileNotFoundError(f"No walk NPZs found in {WALK_DIR}")

    poses = []
    for i in range(n):
        # Pick walk and frame uniformly
        walk_idx = int(rng.integers(0, len(walk_files)))
        ps = PoseStream.load(walk_files[walk_idx])
        frame_idx = int(rng.integers(0, len(ps)))
        pose = ps.poses[frame_idx, :66].reshape(22, 3).copy()
        poses.append(pose)
    return poses


def compute_rate(
    pose: np.ndarray,
    bs: BSArray,
    r_phone: np.ndarray,
) -> float:
    """Compute capped rate [bps/Hz] for a given pose."""
    body = make_body_smplx(pose, BODY_CENTROID)
    paths = los_path_dict(bs, body.mesh.centroid)
    h_body, _ = kirchhoff_h_body(body, paths, r_phone, f_c=F_C, M=bs.M)
    sinr = mrt_sinr_db(
        h_body, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM, scene_loss_db=SCENE_LOSS_DB
    )
    return rate_bps_capped(sinr)


def per_joint_finite_diff(
    pose0: np.ndarray,
    r0: float,
    bs: BSArray,
    r_phone: np.ndarray,
) -> np.ndarray:
    """Compute |∂R/∂θ_j| for each of the 22 joints via finite differences.

    For each joint, perturb around each of the 3 rotation axes by DELTA_DEG,
    average the absolute finite-difference magnitudes.

    Returns shape (22,) array of sensitivities.
    """
    delta = np.deg2rad(DELTA_DEG)
    sensitivities = np.zeros(N_JOINTS)

    for j in range(N_JOINTS):
        axis_grads = []
        for ax in range(3):
            pose_p = pose0.copy()
            pose_p[j, ax] += delta
            r_p = compute_rate(pose_p, bs, r_phone)
            grad = abs(r_p - r0) / delta
            axis_grads.append(grad)
        sensitivities[j] = float(np.mean(axis_grads))

    return sensitivities


def draw_stick_figure_inset(ax_inset, top5_indices, all_sensitivities):
    """Draw a simple stick figure with top-5 joints highlighted."""
    # Normalize sensitivities for color intensity
    max_s = max(all_sensitivities.max(), 1e-30)

    # Draw skeleton edges
    for (p, c) in SKELETON_EDGES:
        x = [JOINT_2D[p][0], JOINT_2D[c][0]]
        y = [JOINT_2D[p][1], JOINT_2D[c][1]]
        ax_inset.plot(x, y, color="0.55", linewidth=1.5, zorder=1)

    # Draw all joints as small grey circles
    for j in range(N_JOINTS):
        x, y = JOINT_2D[j]
        ax_inset.scatter(x, y, s=12, color="0.75", zorder=2)

    # Highlight top-5 joints with colored circles + labels
    colors = plt.cm.plasma(np.linspace(0.15, 0.85, 5))
    for rank, j in enumerate(top5_indices):
        x, y = JOINT_2D[j]
        ax_inset.scatter(x, y, s=80, color=colors[rank], zorder=3, edgecolors="k",
                         linewidths=0.5)
        # Add rank number
        ax_inset.text(x + 0.07, y + 0.02, f"#{rank+1}", fontsize=5, color=colors[rank],
                      fontweight="bold", zorder=4)

    ax_inset.set_xlim(-1.0, 1.0)
    ax_inset.set_ylim(-1.5, 1.6)
    ax_inset.set_aspect("equal")
    ax_inset.axis("off")
    ax_inset.set_title("Top-5 joints", fontsize=7, pad=2)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(RNG_SEED)

    bs = BSArray(n_x=8, n_y=8, center=BS_CENTER, normal=BS_NORMAL, f_c=F_C)
    r_phone = BODY_CENTROID + PHONE_OFFSET

    print(f"Scene: body at {BODY_CENTROID}, phone at {r_phone}, BS at {BS_CENTER}")
    print(f"Scene loss: {SCENE_LOSS_DB} dB")
    print(f"Sampling {N_BASELINE} baseline poses from AMASS walks...")

    t_start = time.time()
    baseline_poses = sample_baseline_poses(N_BASELINE, rng)
    print(f"  sampled in {time.time()-t_start:.1f}s")

    # Verify baseline SINR is in binding regime (first pose check)
    r0_check = compute_rate(baseline_poses[0], bs, r_phone)
    print(f"Baseline rate check (pose 0): {r0_check/1e6:.1f} Mbps")

    # Main sensitivity loop
    all_sensitivities = np.zeros((N_BASELINE, N_JOINTS))  # [pose, joint]

    t0 = time.time()
    for i, pose0 in enumerate(baseline_poses):
        r0 = compute_rate(pose0, bs, r_phone)
        sens = per_joint_finite_diff(pose0, r0, bs, r_phone)
        all_sensitivities[i] = sens
        elapsed = time.time() - t0
        eta = elapsed / (i + 1) * (N_BASELINE - i - 1)
        print(
            f"  pose {i+1:02d}/{N_BASELINE}: R0={r0/1e6:.1f} Mbps  "
            f"top joint={JOINT_LABELS_SHORT[int(np.argmax(sens))]:12s}  "
            f"max_sens={np.max(sens):.2e}  ETA={eta:.0f}s"
        )

    total_elapsed = time.time() - t0
    print(f"\nTotal compute time: {total_elapsed:.1f}s ({total_elapsed/N_BASELINE:.1f}s/pose)")

    # Statistics
    mean_sens = all_sensitivities.mean(axis=0)        # (22,)
    p25_sens = np.percentile(all_sensitivities, 25, axis=0)
    p75_sens = np.percentile(all_sensitivities, 75, axis=0)

    # Sort by mean sensitivity (descending)
    sort_idx = np.argsort(mean_sens)[::-1]

    # Cumulative mass
    total_mass = mean_sens.sum()
    cum_mass = np.cumsum(mean_sens[sort_idx]) / max(total_mass, 1e-30)

    # K thresholds
    k_80 = int(np.searchsorted(cum_mass, 0.80)) + 1
    k_95 = int(np.searchsorted(cum_mass, 0.95)) + 1
    top5_idx = sort_idx[:5]

    # Save NPZ
    np.savez(
        OUT_DIR / "per_joint_sensitivity.npz",
        joint_indices=np.arange(N_JOINTS),
        joint_names=np.array(JOINT_NAMES),
        mean_sensitivity=mean_sens,
        p25_sensitivity=p25_sens,
        p75_sensitivity=p75_sens,
        top_k_indices=sort_idx[:5],
    )
    print(f"\nSaved per_joint_sensitivity.npz")

    # -----------------------------------------------------------------------
    # Plot: horizontal bar chart with stick-figure inset
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(8.0, 5.5))

    # Main axis (left 70%)
    ax_main = fig.add_axes([0.32, 0.08, 0.62, 0.88])
    # Inset axis (top-right)
    ax_inset = fig.add_axes([0.01, 0.35, 0.27, 0.55])

    # Plot sorted bars (top first)
    n_plot = N_JOINTS
    plot_sorted = sort_idx[:n_plot]
    y_pos = np.arange(n_plot)

    # Colormap: top 6 highlighted
    bar_colors = []
    for rank, j in enumerate(plot_sorted):
        if rank < 6:
            bar_colors.append(plt.cm.plasma(0.85 - rank * 0.12))
        else:
            bar_colors.append("0.72")

    bars = ax_main.barh(
        y_pos[::-1],
        mean_sens[plot_sorted] / 1e6,  # Mbps per radian
        color=bar_colors,
        edgecolor="none",
        height=0.65,
    )

    # IQR error bars
    xerr_lo = (mean_sens[plot_sorted] - p25_sens[plot_sorted]) / 1e6
    xerr_hi = (p75_sens[plot_sorted] - mean_sens[plot_sorted]) / 1e6
    ax_main.errorbar(
        mean_sens[plot_sorted] / 1e6,
        y_pos[::-1],
        xerr=[np.maximum(xerr_lo, 0), np.maximum(xerr_hi, 0)],
        fmt="none",
        ecolor="0.35",
        elinewidth=0.8,
        capsize=2,
    )

    ax_main.set_yticks(y_pos)
    ax_main.set_yticklabels(
        [JOINT_LABELS_SHORT[j] for j in plot_sorted[::-1]],
        fontsize=8,
    )
    ax_main.set_xlabel(r"$|\partial R / \partial \theta_j|$ [Mbps / rad]", fontsize=9)
    ax_main.set_title(
        "Per-joint rate sensitivity\n"
        r"(mean $\pm$ IQR, 50 AMASS walk poses)",
        fontsize=9,
    )
    ax_main.spines["top"].set_visible(False)
    ax_main.spines["right"].set_visible(False)
    ax_main.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.6)

    # Annotate top-5 bars with anatomical rank numbers
    top5_in_sorted = list(range(5))
    for rank in top5_in_sorted:
        bar_val = mean_sens[plot_sorted[rank]] / 1e6
        y = (n_plot - 1 - rank)
        ax_main.text(
            bar_val * 1.03,
            y,
            f"#{rank+1}",
            va="center",
            ha="left",
            fontsize=7.5,
            color=plt.cm.plasma(0.85 - rank * 0.12),
            fontweight="bold",
        )

    # Stick figure inset
    draw_stick_figure_inset(ax_inset, top5_idx, mean_sens)

    # Legend for highlighting
    legend_patches = [
        mpatches.Patch(color=plt.cm.plasma(0.85 - i * 0.12), label=f"#{i+1}: {JOINT_LABELS_SHORT[sort_idx[i]]}")
        for i in range(5)
    ]
    ax_inset.legend(
        handles=legend_patches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.35),
        fontsize=6,
        framealpha=0.8,
        title="Top 5 joints",
        title_fontsize=6.5,
        ncol=1,
    )

    fig.savefig(OUT_DIR / "fig_per_joint_sensitivity.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "fig_per_joint_sensitivity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig_per_joint_sensitivity.{pdf,png}")

    # -----------------------------------------------------------------------
    # Print summary
    # -----------------------------------------------------------------------
    print("\n=== TOP-10 JOINT RANKING ===")
    print(f"{'Rank':>4s}  {'Joint':20s}  {'Mean [Mbps/rad]':>16s}  {'P25':>8s}  {'P75':>8s}")
    for rank, j in enumerate(sort_idx[:10]):
        print(
            f"  {rank+1:2d}  {JOINT_NAMES[j]:20s}  "
            f"{mean_sens[j]/1e6:16.3f}  "
            f"{p25_sens[j]/1e6:8.3f}  "
            f"{p75_sens[j]/1e6:8.3f}"
        )

    print("\n=== CUMULATIVE MASS CURVE ===")
    print(f"{'K':>3s}  {'Joint':20s}  {'CumMass':>8s}")
    for k in range(N_JOINTS):
        j = sort_idx[k]
        cm = cum_mass[k]
        marker = " <-- 80%" if k + 1 == k_80 else (" <-- 95%" if k + 1 == k_95 else "")
        print(f"  {k+1:2d}  {JOINT_NAMES[j]:20s}  {cm:.3f}{marker}")

    print(f"\nK(80%) = {k_80}  K(95%) = {k_95}")

    # -----------------------------------------------------------------------
    # Write log
    # -----------------------------------------------------------------------
    log_lines = [
        "# Per-Joint Sensitivity Agent Log",
        "",
        f"Run date: 2026-05-10",
        f"Scene: body at {BODY_CENTROID}, phone at {BODY_CENTROID + PHONE_OFFSET}, BS at {BS_CENTER}",
        f"Scene loss: {SCENE_LOSS_DB} dB (on h_body, binding regime ~12 dB SINR mean across AMASS poses)",
        f"N baseline poses: {N_BASELINE}, seed={RNG_SEED}, delta={DELTA_DEG} deg",
        f"Total compute time: {total_elapsed:.1f}s",
        "",
        "## Top-10 Joint Ranking",
        "",
        f"| Rank | Joint | Mean [Mbps/rad] | P25 | P75 |",
        f"|------|-------|-----------------|-----|-----|",
    ]
    for rank, j in enumerate(sort_idx[:10]):
        log_lines.append(
            f"| {rank+1} | {JOINT_NAMES[j]} | {mean_sens[j]/1e6:.3f} | "
            f"{p25_sens[j]/1e6:.3f} | {p75_sens[j]/1e6:.3f} |"
        )
    log_lines += [
        "",
        "## Cumulative Mass Curve",
        "",
        f"| K | Joint | Cumulative mass |",
        f"|---|-------|-----------------|",
    ]
    for k in range(N_JOINTS):
        j = sort_idx[k]
        cm = cum_mass[k]
        log_lines.append(f"| {k+1} | {JOINT_NAMES[j]} | {cm:.4f} |")
    log_lines += [
        "",
        f"**K(80%) = {k_80}**  **K(95%) = {k_95}**",
        "",
        "## Verification Checks",
        "",
        f"- Top-3 carry {cum_mass[2]*100:.1f}% of gradient mass (expected >60%)",
        f"- Top-6 carry {cum_mass[5]*100:.1f}% of gradient mass (expected >85%)",
        f"- Top-5 joints: {[JOINT_NAMES[j] for j in sort_idx[:5]]}",
        "",
    ]

    log_path = LOG_DIR / "agent_per_joint_sensitivity.md"
    log_path.write_text("\n".join(log_lines))
    print(f"\nWrote {log_path}")


if __name__ == "__main__":
    main()

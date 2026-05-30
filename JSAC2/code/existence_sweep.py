"""Existence sweep — Part A of the JSAC2 §VIII three-part convergence study.

For N=200 random tuples (BS-geometry, scene-loss, AMASS-baseline-pose,
BS-distance), determine whether *any* comfortable pose move within the
comfort ball ``C(Δθ) <= ρ`` achieves a target SINR gain of {3, 6, 10} dB.

Comfort metric (single scalar):
    C(Δθ) = sum_j (Δθ_j / 5°)^2   over the 6 actuated joints.
    Comfort budget ρ = 1 corresponds to a single-joint 5° move.

Actuated joints (6 of the upper-body DoFs that affect the cascaded channel):
    spine1 (3):   axis Y (yaw / twist)
    spine2 (6):   axis Y (yaw / twist)         — primary torso-yaw knob
    spine3 (9):   axis Y (yaw / twist)
    neck   (12):  axis Y (head yaw)
    L_shldr(16):  axis X (raise / lower)
    R_shldr(17):  axis X (raise / lower)

Each joint is treated as a scalar perturbation Δθ_j ∈ [-15°, +15°] applied
on the chosen axis.

Search strategy: coordinate descent with 3 random restarts, K=20 inner
iterations per restart, sweeping each picked joint over Δθ_j ∈ {-15, -10,
-5, 0, +5, +10, +15} deg. The comfort ball is enforced as a hard constraint
(reject candidates with C(Δθ) > 1).

Rate-gain metric: SINR delta in dB on the *uncapped* Shannon channel —
ΔR (dB) := SINR_cas(after) - SINR_cas(baseline). The MCS-cap saturation is
deliberately set aside here: the existence study asks "is there a pose move
that helps the channel?" The reachability + failure-mode studies handle the
cap-saturation case explicitly.

Outputs:
    outputs/existence_sweep.npz
    outputs/fig_existence.{pdf,png}
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aegis.geometry.pose_stream import PoseStream

from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db
from JSAC2.code.scene_nlos import BSArray, los_h_at_phone, los_path_dict
from JSAC2.code.scene_smplx import make_body_smplx


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_SCENES = 200
SEED = 42
TARGET_GAINS_DB = (3.0, 6.0, 10.0)
RESTARTS = 3
INNER_ITERS = 20
JOINT_INDICES = (3, 6, 9, 12, 16, 17)  # spine1 spine2 spine3 neck L_shldr R_shldr
JOINT_AXES = (1, 1, 1, 1, 0, 0)  # SMPL-X local axis for each
JOINT_NAMES = (
    "spine1",
    "spine2",
    "spine3",
    "neck",
    "L_shldr",
    "R_shldr",
)
N_JOINTS = len(JOINT_INDICES)
DELTA_GRID_DEG = np.array([-15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0])
COMFORT_REF_DEG = 5.0  # per-joint reference for comfort metric
COMFORT_RHO = 1.0  # comfort ball radius
PHONE_OFFSET = np.array([-0.40, 0.0, 0.05])  # 40 cm in front of chest, slightly above centroid
BODY_WORLD_CENTROID_BASE = np.array([30.0, 0.0, 1.2])
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")
LOG_PATH = Path("/home/user/aegis/JSAC2/code/agent_logs/agent_existence_reachability.md")

# BS geometry regimes.
# Each regime: (bs_position, label). Body lives at BODY_WORLD_CENTROID_BASE.
BS_REGIMES = [
    (np.array([0.0, 0.0, 8.0], dtype=np.float64), "far30m_h8"),
    (np.array([20.0, 0.0, 5.0], dtype=np.float64), "mid10m_h5"),
    (np.array([25.0, 0.0, 3.0], dtype=np.float64), "close5m_h3"),
]

# Scene-loss draws.
SCENE_LOSS_DB_CHOICES = (35.0, 55.0, 80.0)


# ---------------------------------------------------------------------------
# AMASS sampling
# ---------------------------------------------------------------------------
def discover_walks(pose_root: Path = PLAZA_DIR) -> list[Path]:
    walks = sorted(pose_root.rglob("*.npz"))
    if len(walks) < 50:
        raise RuntimeError(f"Need >= 50 walks; found {len(walks)} in {pose_root}")
    return walks


def build_pose_pool(walks: list[Path], rng: np.random.Generator) -> list[tuple[int, int, np.ndarray]]:
    """Build (walk_idx, frame_idx, pose_axis_angle[22,3]) entries for every
    plausible AMASS frame across all walks.

    Plausibility filter: per-frame max spine-joint magnitude < 30 deg
    (rejects extreme bends / unphysical configs from the mocap edges).
    AMASS global_orient is zeroed so that scene_smplx's coordinate
    transform applies (AMASS bakes Y-up orient into joint 0).
    """
    pool = []
    for wi, w in enumerate(walks):
        ps = PoseStream.load(w)
        poses = ps.poses[:, :66].reshape(-1, 22, 3).copy()
        poses[:, 0] = 0.0  # zero global orient
        spine_mag_deg = np.rad2deg(np.linalg.norm(poses[:, [3, 6, 9]], axis=2)).max(axis=1)
        ok = spine_mag_deg < 30.0
        for fi in np.where(ok)[0]:
            pool.append((wi, int(fi), poses[fi]))
    print(f"  pose pool: {len(pool)} plausible frames across {len(walks)} walks")
    return pool


# ---------------------------------------------------------------------------
# Per-scene sampling
# ---------------------------------------------------------------------------
def sample_scenes(rng: np.random.Generator, n_scenes: int, pool_size: int) -> dict:
    """Draw N scene tuples deterministically.

    Returns a dict of arrays keyed by trial index.
    """
    pose_idx = rng.integers(0, pool_size, size=n_scenes)
    regime_idx = rng.integers(0, len(BS_REGIMES), size=n_scenes)
    scene_loss_db = rng.choice(SCENE_LOSS_DB_CHOICES, size=n_scenes)
    azimuth_offset_deg = rng.uniform(-30.0, 30.0, size=n_scenes)
    return dict(
        pose_idx=pose_idx,
        regime_idx=regime_idx,
        scene_loss_db=scene_loss_db,
        azimuth_offset_deg=azimuth_offset_deg,
    )


# ---------------------------------------------------------------------------
# Channel evaluation
# ---------------------------------------------------------------------------
def apply_pose_move(baseline_pose: np.ndarray, delta_deg: np.ndarray) -> np.ndarray:
    """Apply per-joint scalar perturbation to a baseline pose.

    delta_deg has shape (6,). Returns a (22, 3) pose array (copy).
    """
    pose = baseline_pose.copy()
    for k, (jidx, axis) in enumerate(zip(JOINT_INDICES, JOINT_AXES)):
        pose[jidx, axis] += np.deg2rad(delta_deg[k])
    return pose


def comfort_cost(delta_deg: np.ndarray) -> float:
    return float(np.sum((delta_deg / COMFORT_REF_DEG) ** 2))


def rotate_bs_in_azimuth(bs_pos: np.ndarray, body_centroid: np.ndarray, az_deg: float) -> np.ndarray:
    """Rotate the BS position about the body centroid in the world XY plane."""
    rel = bs_pos - body_centroid
    c, s = np.cos(np.deg2rad(az_deg)), np.sin(np.deg2rad(az_deg))
    new_xy = np.array([c * rel[0] - s * rel[1], s * rel[0] + c * rel[1]])
    return body_centroid + np.array([new_xy[0], new_xy[1], rel[2]])


def evaluate_pose(
    delta_deg: np.ndarray,
    *,
    baseline_pose: np.ndarray,
    bs: BSArray,
    h_los: np.ndarray,
    body_centroid: np.ndarray,
    r_phone: np.ndarray,
) -> float:
    """Compute SINR (dB) of cascaded channel at the given pose perturbation."""
    pose = apply_pose_move(baseline_pose, delta_deg)
    body = make_body_smplx(pose, body_centroid)
    path_dict = los_path_dict(bs, body.mesh.centroid)
    h_body, _ = kirchhoff_h_body(body, path_dict, r_phone, M=bs.M)
    h_cas = h_los + h_body
    return mrt_sinr_db(h_cas, p_tx_dbm=43.0, noise_dbm=-94.0)


# ---------------------------------------------------------------------------
# Coordinate-descent search over the comfort ball
# ---------------------------------------------------------------------------
def coord_descent_search(
    *,
    baseline_pose: np.ndarray,
    bs: BSArray,
    h_los: np.ndarray,
    body_centroid: np.ndarray,
    r_phone: np.ndarray,
    rng: np.random.Generator,
    inner_iters: int = INNER_ITERS,
) -> tuple[np.ndarray, float]:
    """One coordinate-descent restart with random initial Δθ inside the ball.

    Returns (best_delta_deg, best_sinr_db).
    """
    # Random initial point inside the comfort ball with uniform draw on the
    # 6-D box, rescaled to lie inside ρ.
    delta = rng.uniform(-5.0, 5.0, size=N_JOINTS)
    while comfort_cost(delta) > COMFORT_RHO:
        delta *= 0.7
    sinr = evaluate_pose(
        delta,
        baseline_pose=baseline_pose,
        bs=bs,
        h_los=h_los,
        body_centroid=body_centroid,
        r_phone=r_phone,
    )
    best_delta = delta.copy()
    best_sinr = sinr
    for _ in range(inner_iters):
        j = int(rng.integers(0, N_JOINTS))
        # Sweep candidate values for joint j keeping others fixed.
        cand_sinr = []
        cand_delta = []
        for v in DELTA_GRID_DEG:
            d = best_delta.copy()
            d[j] = v
            if comfort_cost(d) > COMFORT_RHO:
                cand_sinr.append(-np.inf)
                cand_delta.append(d)
                continue
            s = evaluate_pose(
                d,
                baseline_pose=baseline_pose,
                bs=bs,
                h_los=h_los,
                body_centroid=body_centroid,
                r_phone=r_phone,
            )
            cand_sinr.append(s)
            cand_delta.append(d)
        i_best = int(np.argmax(cand_sinr))
        if cand_sinr[i_best] > best_sinr:
            best_sinr = float(cand_sinr[i_best])
            best_delta = cand_delta[i_best].copy()
    return best_delta, best_sinr


# ---------------------------------------------------------------------------
# One scene worker
# ---------------------------------------------------------------------------
def run_scene(args):
    """Process one scene: build geometry, baseline SINR, run coord-descent."""
    (
        scene_idx,
        baseline_pose,
        bs_pos,
        scene_loss_db,
        azimuth_offset_deg,
        seed,
    ) = args
    rng = np.random.default_rng(seed)

    body_centroid = BODY_WORLD_CENTROID_BASE.copy()
    bs_pos_rot = rotate_bs_in_azimuth(bs_pos, body_centroid, azimuth_offset_deg)
    # Aim panel at the body.
    panel_normal = body_centroid - bs_pos_rot
    panel_normal /= np.linalg.norm(panel_normal)
    bs = BSArray(n_x=8, n_y=8, center=bs_pos_rot, normal=panel_normal, f_c=28e9)
    r_phone = body_centroid + PHONE_OFFSET

    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)

    # Baseline SINR (Δθ = 0).
    sinr_baseline = evaluate_pose(
        np.zeros(N_JOINTS),
        baseline_pose=baseline_pose,
        bs=bs,
        h_los=h_los,
        body_centroid=body_centroid,
        r_phone=r_phone,
    )

    # Multi-restart coordinate descent.
    best_delta = np.zeros(N_JOINTS)
    best_sinr = sinr_baseline
    for r in range(RESTARTS):
        d, s = coord_descent_search(
            baseline_pose=baseline_pose,
            bs=bs,
            h_los=h_los,
            body_centroid=body_centroid,
            r_phone=r_phone,
            rng=np.random.default_rng(seed * 31 + r * 7 + 1),
            inner_iters=INNER_ITERS,
        )
        if s > best_sinr:
            best_sinr = s
            best_delta = d

    best_gain_db = best_sinr - sinr_baseline
    return scene_idx, sinr_baseline, best_sinr, best_gain_db, best_delta


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    walks = discover_walks()
    pool = build_pose_pool(walks, rng)
    pool_size = len(pool)

    scenes = sample_scenes(rng, N_SCENES, pool_size)

    # Walk uniqueness audit.
    walk_idxs = np.array([pool[int(i)][0] for i in scenes["pose_idx"]])
    frame_idxs = np.array([pool[int(i)][1] for i in scenes["pose_idx"]])
    unique_walks = len(np.unique(walk_idxs))
    unique_pairs = len(set(zip(walk_idxs.tolist(), frame_idxs.tolist())))
    print(f"  scenes use {unique_walks} unique walks / {unique_pairs} unique frames")

    # Build per-scene args.
    scene_args = []
    for s in range(N_SCENES):
        pose = pool[int(scenes["pose_idx"][s])][2]
        bs_pos = BS_REGIMES[int(scenes["regime_idx"][s])][0]
        scene_args.append(
            (
                s,
                pose,
                bs_pos,
                float(scenes["scene_loss_db"][s]),
                float(scenes["azimuth_offset_deg"][s]),
                SEED + s,
            )
        )

    # Run with multiprocessing pool.
    n_workers = min(os.cpu_count() or 4, 12)
    print(f"  running {N_SCENES} scenes on {n_workers} workers ...")
    t0 = time.time()
    sinr_baseline_arr = np.zeros(N_SCENES)
    best_sinr_arr = np.zeros(N_SCENES)
    best_gain_db_arr = np.zeros(N_SCENES)
    best_delta_arr = np.zeros((N_SCENES, N_JOINTS))

    with mp.Pool(processes=n_workers) as pool_proc:
        for i, result in enumerate(pool_proc.imap_unordered(run_scene, scene_args)):
            scene_idx, sb, bs_, bg, bd = result
            sinr_baseline_arr[scene_idx] = sb
            best_sinr_arr[scene_idx] = bs_
            best_gain_db_arr[scene_idx] = bg
            best_delta_arr[scene_idx] = bd
            if (i + 1) % 10 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (N_SCENES - (i + 1)) / max(rate, 1e-9)
                print(
                    f"    scene {i+1}/{N_SCENES} done "
                    f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s)"
                )
    elapsed = time.time() - t0
    print(f"  finished in {elapsed:.1f}s ({elapsed / N_SCENES:.2f}s/scene)")

    # Existence fractions: per regime × target_gain.
    n_targets = len(TARGET_GAINS_DB)
    n_regimes = len(BS_REGIMES)
    existence = np.zeros((n_regimes, n_targets))
    counts = np.zeros((n_regimes, n_targets), dtype=np.int32)
    n_per_regime = np.zeros(n_regimes, dtype=np.int32)
    for s in range(N_SCENES):
        r = int(scenes["regime_idx"][s])
        n_per_regime[r] += 1
        for t, tgt in enumerate(TARGET_GAINS_DB):
            if best_gain_db_arr[s] >= tgt:
                counts[r, t] += 1
    for r in range(n_regimes):
        for t in range(n_targets):
            existence[r, t] = counts[r, t] / max(n_per_regime[r], 1)

    print("\n  Existence fractions [regime × target_gain]:")
    print("    regime              | 3 dB    6 dB    10 dB")
    for r, (_, name) in enumerate(BS_REGIMES):
        row = "  ".join(f"{existence[r, t]:6.2f}" for t in range(n_targets))
        print(f"    {name:18s}  | {row}  (n={n_per_regime[r]})")

    print("\n  Existence fractions per scene_loss_db:")
    for sl in SCENE_LOSS_DB_CHOICES:
        mask = scenes["scene_loss_db"] == sl
        row = "  ".join(
            f"{(best_gain_db_arr[mask] >= tgt).mean():6.2f}" for tgt in TARGET_GAINS_DB
        )
        print(f"    scene_loss={sl:5.1f} dB | {row}  (n={int(mask.sum())})")

    # Save NPZ.
    bs_distance = np.array(
        [
            float(np.linalg.norm(BS_REGIMES[int(scenes["regime_idx"][s])][0] - BODY_WORLD_CENTROID_BASE))
            for s in range(N_SCENES)
        ]
    )
    out_path = OUT_DIR / "existence_sweep.npz"
    np.savez(
        out_path,
        regimes=np.array([name for _, name in BS_REGIMES]),
        target_gains_db=np.array(TARGET_GAINS_DB),
        existence_fractions=existence,
        existence_counts=counts,
        n_per_regime=n_per_regime,
        pose_pool_walk_idx=walk_idxs,
        pose_pool_frame_idx=frame_idxs,
        pose_baseline_idx=scenes["pose_idx"],
        regime_idx=scenes["regime_idx"],
        bs_distance=bs_distance,
        scene_loss=scenes["scene_loss_db"],
        azimuth_offset_deg=scenes["azimuth_offset_deg"],
        sinr_baseline_db=sinr_baseline_arr,
        best_sinr_db=best_sinr_arr,
        best_gain_db=best_gain_db_arr,
        best_pose_move=best_delta_arr,
        joint_indices=np.array(JOINT_INDICES),
        joint_axes=np.array(JOINT_AXES),
        joint_names=np.array(JOINT_NAMES),
        seed=SEED,
        n_unique_walks=unique_walks,
        n_unique_frames=unique_pairs,
        elapsed_sec=elapsed,
    )
    print(f"  wrote {out_path}")

    make_existence_figure(existence, n_per_regime)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def make_existence_figure(existence: np.ndarray, n_per_regime: np.ndarray):
    """Bar chart: bars grouped by BS regime, hue by target gain."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        import scienceplots  # noqa: F401

        plt.style.use(["science", "ieee"])
    except Exception:
        pass

    n_regimes, n_targets = existence.shape
    regime_names = [
        "Far (30 m, h=8 m)",
        "Mid (10 m, h=5 m)",
        "Close (5 m, h=3 m)",
    ]
    target_labels = [f"$\\Delta R \\geq {int(t)}$ dB" for t in TARGET_GAINS_DB]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    width = 0.25
    x = np.arange(n_regimes)
    for t in range(n_targets):
        ax.bar(
            x + (t - 1) * width,
            existence[:, t] * 100.0,
            width,
            label=target_labels[t],
            color=colors[t],
            edgecolor="black",
            linewidth=0.4,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(regime_names, fontsize=7)
    ax.set_ylabel("Existence fraction (\\%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=6, loc="upper right", ncol=1, frameon=True)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(
        f"Existence of comfort-bounded pose move (N={int(n_per_regime.sum())} scenes)",
        fontsize=8,
    )
    fig.tight_layout()
    pdf_path = OUT_DIR / "fig_existence.pdf"
    png_path = OUT_DIR / "fig_existence.png"
    fig.savefig(pdf_path, dpi=300)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    print(f"  wrote {pdf_path}")
    print(f"  wrote {png_path}")


if __name__ == "__main__":
    main()

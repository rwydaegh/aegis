"""Comfort-vs-rate Pareto (Task A) and baselines comparison (Task B).

Task A: For the binding regime (55 dB scene loss, 10 m BS), Sobol-sample
500 pose moves in the comfort ball C(Δθ) = Σ (Δθ_j/5°)^2 ≤ 4, compute
rate gain vs comfort cost, and plot the Pareto frontier.

Task B: For 30 random scenes (10 LOS-attenuated, 10 binding, 10 NLOS),
evaluate four precoding methods (no-twin ZF, no-twin MRT, T-pose twin MRT,
full closed-loop RIHB MRT) and produce a comparison table + bar chart.

Output files:
  JSAC2/code/outputs/comfort_pareto.npz
  JSAC2/code/outputs/fig_comfort_pareto.{pdf,png}
  JSAC2/code/outputs/baselines.npz
  JSAC2/code/outputs/baselines_table.txt
  JSAC2/code/outputs/fig_baselines.{pdf,png}
  JSAC2/code/agent_logs/agent_comfort_baselines.md
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import (
    Body,
    BSPathDict,
    kirchhoff_h_body,
    mrt_sinr_db,
    rate_bps_shannon,
)
from JSAC2.code.scene_nlos import BSArray, los_path_dict, los_h_at_phone
from JSAC2.code.scene_smplx import (
    make_body_smplx,
    default_baseline_pose,
    JOINT_SPINE2,
    JOINT_R_SHOULDER,
    JOINT_R_ELBOW,
    JOINT_NECK,
)
from JSAC2.code.calibration import fit_tier_d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
P_TX_DBM = 43.0
NOISE_DBM = -94.0
F_C = 28e9
BODY_CENTROID = np.array([30.0, 0.0, 1.2])
PHONE_OFFSET = np.array([-0.40, 0.0, 0.05])  # 40 cm in front of chest, slightly above centroid
BW_HZ = 100e6

# Joint indices in the (22, 3) axis-angle array that we actuate.
# spine2 (L4-L5) Z-axis, right shoulder Z-axis, right elbow Y-axis,
# neck X-axis, right hip Z-axis (no right hip in SMPL-X 22-joint set;
# use left shoulder Z-axis instead), left shoulder Z-axis.
# From scene_smplx: JOINT_SPINE2=6, JOINT_NECK=12, JOINT_L_SHOULDER=16,
# JOINT_R_SHOULDER=17, JOINT_R_ELBOW=19
# For "right hip Z-axis": SMPL-X joint 2 is right hip.
JOINT_R_HIP = 2
JOINT_L_SHOULDER = 16

# 6 actuated joints and their local axes (index into the (3,) axis-angle):
# (joint_idx, axis_idx, label)
ACTUATED_JOINTS = [
    (JOINT_SPINE2, 2, "spine2_Z"),       # spine2 Z-axis
    (JOINT_R_SHOULDER, 2, "rshoulder_Z"),  # right shoulder Z-axis
    (JOINT_R_ELBOW, 1, "relbow_Y"),       # right elbow Y-axis
    (12, 0, "neck_X"),                    # neck X-axis  (JOINT_NECK=12)
    (JOINT_R_HIP, 2, "rhip_Z"),           # right hip Z-axis
    (JOINT_L_SHOULDER, 2, "lshoulder_Z"),  # left shoulder Z-axis
]

COMFORT_SCALE_DEG = 5.0   # each unit of C corresponds to (Δθ / 5°)^2
RHO_MAX = 4.0             # comfort budget

OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")
LOG_DIR = Path("/home/user/aegis/JSAC2/code/agent_logs")


# ---------------------------------------------------------------------------
# Utility: apply a 6D joint move on top of baseline pose
# ---------------------------------------------------------------------------
def apply_joint_moves(baseline_pose: np.ndarray, delta_rad: np.ndarray) -> np.ndarray:
    """Apply delta_rad[6] increments to the 6 actuated joints.

    delta_rad has length 6, each entry is the axis-angle increment (in radians)
    for the corresponding actuated joint (joint_idx, axis_idx) pair.
    """
    pose = baseline_pose.copy().reshape(22, 3)
    for k, (j_idx, ax_idx, _) in enumerate(ACTUATED_JOINTS):
        pose[j_idx, ax_idx] += delta_rad[k]
    return pose


def compute_sinr_and_rate_for_pose(
    pose: np.ndarray,
    bs: BSArray,
    h_los: np.ndarray,
    scene_loss_db: float,
    r_phone: np.ndarray,
    body_centroid: np.ndarray,
) -> tuple[float, float]:
    """Compute MRT SINR (dB) and capped rate (Mbps) for a given (22,3) SMPL-X pose."""
    body = make_body_smplx(pose, body_centroid)
    paths = los_path_dict(bs, body.mesh.centroid)
    h_body, _ = kirchhoff_h_body(body, paths, r_phone, f_c=F_C, M=bs.M)
    h_cas = h_los + h_body
    sinr = mrt_sinr_db(h_cas, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM)
    rate = rate_bps_shannon(sinr, bandwidth_hz=BW_HZ) / 1e6
    return sinr, rate


def compute_rate_for_pose(
    pose: np.ndarray,
    bs: BSArray,
    h_los: np.ndarray,
    scene_loss_db: float,
    r_phone: np.ndarray,
    body_centroid: np.ndarray,
) -> float:
    """Compute MRT rate (Mbps) for a given (22,3) SMPL-X pose."""
    _, rate = compute_sinr_and_rate_for_pose(pose, bs, h_los, scene_loss_db, r_phone, body_centroid)
    return rate


# ---------------------------------------------------------------------------
# Sobol sampling on comfort ball
# ---------------------------------------------------------------------------
def sobol_comfort_ball_samples(n_samples: int, rho_max: float, seed: int = 0) -> np.ndarray:
    """Sample n_samples points in the 6D comfort ball.

    Uses scipy.stats.qmc.Sobol for low-discrepancy sampling on the hypercube
    [0,1]^6, then maps via Marsaglia-style rejection/scaling onto the ball
    {x : sum((x_j / scale)^2) <= rho_max}.

    Returns delta_deg of shape (n_samples, 6) in degrees.
    """
    from scipy.stats import qmc

    # We need more Sobol points than n_samples because Marsaglia rejects
    # points outside the sphere.  The volume fraction of the sphere inside
    # the cube in 6D is pi^3/6 / 2^6 ≈ 0.0806, so we need ~12x oversampling.
    # We oversample by 16x to be safe.
    over = 16
    sobol = qmc.Sobol(d=6, scramble=True, seed=seed)
    # Sobol requires power-of-2 sample count
    n_draw = 1
    while n_draw < n_samples * over:
        n_draw *= 2

    raw = sobol.random(n_draw)  # (n_draw, 6) in [0,1]
    # Map to [-1, 1]^6
    u = 2.0 * raw - 1.0  # (n_draw, 6)
    # Reject points outside unit ball
    r2 = np.sum(u ** 2, axis=1)
    inside = r2 <= 1.0
    u_in = u[inside]

    if len(u_in) < n_samples:
        # Fallback: just use all inside points and re-normalize to fill
        # This should not happen with over=16 in 6D.
        raise RuntimeError(
            f"Too few Sobol points inside ball: {len(u_in)} < {n_samples}. "
            "Increase oversampling factor."
        )

    u_sel = u_in[:n_samples]  # (n_samples, 6)

    # Scale so that the maximum radius^2 = rho_max in "comfort units".
    # comfort_cost = sum((delta_j / 5°)^2). We want the ball to be
    # {delta : comfort_cost <= rho_max}. So delta_j = u_j * sqrt(rho_max) * 5°.
    scale_deg = np.sqrt(rho_max) * COMFORT_SCALE_DEG  # in degrees
    delta_deg = u_sel * scale_deg  # (n_samples, 6)
    return delta_deg


def compute_comfort_cost(delta_deg: np.ndarray) -> np.ndarray:
    """Compute C(Δθ) = sum_j (Δθ_j / 5°)^2 for each sample."""
    return np.sum((delta_deg / COMFORT_SCALE_DEG) ** 2, axis=1)


# ---------------------------------------------------------------------------
# Pareto frontier extraction
# ---------------------------------------------------------------------------
def pareto_front_rate_comfort(rate_gain: np.ndarray, comfort: np.ndarray) -> np.ndarray:
    """Return indices on the Pareto frontier (max rate, min comfort).

    A point (r_i, c_i) is Pareto-optimal (upper-left frontier) if no other
    point has both higher rate gain AND lower comfort cost.
    """
    n = len(rate_gain)
    pareto_idx = []
    for i in range(n):
        dominated = False
        for j in range(n):
            if j == i:
                continue
            # j dominates i if j has higher rate AND lower comfort
            if rate_gain[j] >= rate_gain[i] and comfort[j] <= comfort[i]:
                if rate_gain[j] > rate_gain[i] or comfort[j] < comfort[i]:
                    dominated = True
                    break
        if not dominated:
            pareto_idx.append(i)
    return np.array(pareto_idx, dtype=int)


# ---------------------------------------------------------------------------
# Task A: Comfort-vs-rate Pareto
# ---------------------------------------------------------------------------
def task_a_comfort_pareto():
    print("\n" + "=" * 60)
    print("Task A: Comfort-vs-rate Pareto (binding regime, 55 dB, 10 m BS)")
    print("=" * 60)

    # Binding regime: 55 dB scene loss, 10 m BS
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 10.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=F_C)
    scene_loss_db = 55.0
    body_centroid = BODY_CENTROID.copy()
    r_phone = body_centroid + PHONE_OFFSET

    # Baseline pose: AMASS frame 0 of first file, used as the user's current pose.
    # We use the "phone-holding" default_baseline_pose from scene_smplx as reference
    # since that is the phone-holding arm configuration the comfort ball is centered on.
    # For seed=0 determinism, we take default_baseline_pose() exactly (no randomness).
    from JSAC2.code.scene_smplx import default_baseline_pose as _default_pose
    baseline_pose = _default_pose()
    print(f"  Baseline pose: default_baseline_pose() from scene_smplx")

    # Compute baseline body and rate
    print("  Computing baseline rate...")
    t0 = time.time()
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)
    body_base = make_body_smplx(baseline_pose, body_centroid)
    paths_base = los_path_dict(bs, body_base.mesh.centroid)
    h_body_base, _ = kirchhoff_h_body(body_base, paths_base, r_phone, f_c=F_C, M=bs.M)
    h_cas_base = h_los + h_body_base
    sinr_base = mrt_sinr_db(h_cas_base, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM)
    rate_base_mbps = rate_bps_shannon(sinr_base, bandwidth_hz=BW_HZ) / 1e6
    print(f"  Baseline: SINR={sinr_base:.1f} dB, rate={rate_base_mbps:.1f} Mbps, "
          f"({time.time()-t0:.1f} s)")

    # Sobol samples
    N_SOBOL = 500
    print(f"  Sobol-sampling {N_SOBOL} candidate pose moves (seed=0)...")
    delta_deg = sobol_comfort_ball_samples(N_SOBOL, RHO_MAX, seed=0)
    comfort_costs = compute_comfort_cost(delta_deg)
    print(f"  Comfort range: [{comfort_costs.min():.3f}, {comfort_costs.max():.3f}] "
          f"(should be ≤ {RHO_MAX:.1f})")

    # Evaluate each Sobol pose
    delta_rad = np.deg2rad(delta_deg)  # (500, 6)
    sinr_db_arr = np.zeros(N_SOBOL)
    rate_mbps = np.zeros(N_SOBOL)
    print(f"  Evaluating {N_SOBOL} poses...")
    t0 = time.time()
    for i in range(N_SOBOL):
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            print(f"    [{i+1}/{N_SOBOL}] elapsed={elapsed:.1f}s, "
                  f"~{elapsed/(i+1)*(N_SOBOL-i-1):.0f}s remaining")
        pose_i = apply_joint_moves(baseline_pose, delta_rad[i])
        sinr_db_arr[i], rate_mbps[i] = compute_sinr_and_rate_for_pose(
            pose_i, bs, h_los, scene_loss_db, r_phone, body_centroid
        )

    # Rate gain: SINR difference from baseline (in dB)
    # Using SINR gain (not capped rate ratio) to preserve full variation
    # even when both baseline and moved pose saturate the MCS cap.
    rate_gain_db = sinr_db_arr - sinr_base
    print(f"  SINR gain range: [{rate_gain_db.min():.2f}, {rate_gain_db.max():.2f}] dB")

    # Pareto frontier
    pareto_indices = pareto_front_rate_comfort(rate_gain_db, comfort_costs)
    print(f"  Pareto frontier size: {len(pareto_indices)} points")

    # Save
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        OUT_DIR / "comfort_pareto.npz",
        rate_gain_db=rate_gain_db,
        sinr_db=sinr_db_arr,
        comfort_cost=comfort_costs,
        pose_moves=delta_deg,
        pareto_indices=pareto_indices,
        rate_base_mbps=np.array(rate_base_mbps),
        rate_mbps=rate_mbps,
        sinr_base_db=np.array(sinr_base),
        scene_loss_db=np.array(scene_loss_db),
        bs_distance_m=np.array(10.0),
    )
    print(f"  Saved: {OUT_DIR}/comfort_pareto.npz")

    # Plot
    _plot_comfort_pareto(rate_gain_db, comfort_costs, pareto_indices, rate_base_mbps,
                         sinr_base=sinr_base)

    return {
        "rate_gain_db": rate_gain_db,
        "comfort_costs": comfort_costs,
        "pareto_indices": pareto_indices,
        "rate_base_mbps": rate_base_mbps,
        "sinr_base": sinr_base,
    }


def _plot_comfort_pareto(rate_gain_db, comfort_costs, pareto_idx, rate_base_mbps, sinr_base=None):
    fig, ax = plt.subplots(1, 1, figsize=(5.0, 3.8))

    ax.scatter(comfort_costs, rate_gain_db, s=8, alpha=0.4, color="#4878d0",
               label="Sobol samples", zorder=2)

    # Pareto envelope: sort by comfort cost
    p_sorted = pareto_idx[np.argsort(comfort_costs[pareto_idx])]
    ax.plot(comfort_costs[p_sorted], rate_gain_db[p_sorted],
            "r-o", markersize=5, linewidth=1.5, zorder=3, label="Pareto frontier")

    # Mark origin (baseline)
    ax.axhline(0.0, color="k", linestyle="--", linewidth=0.8, alpha=0.7,
               label=f"Baseline ({rate_base_mbps:.0f} Mbps" + (f", SINR={sinr_base:.1f} dB" if sinr_base is not None else "") + ")")
    ax.axvline(0.0, color="gray", linestyle=":", linewidth=0.6, alpha=0.5)

    ax.set_xlabel("Comfort cost $C(\\Delta\\theta)$  [comfort units]", fontsize=10)
    ax.set_ylabel("SINR gain over baseline  [dB]", fontsize=10)
    ax.set_title("Comfort-vs-SINR Pareto (binding regime, 55 dB, 10 m BS)", fontsize=9)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=-0.05)
    fig.tight_layout()

    for ext in ("pdf", "png"):
        path = OUT_DIR / f"fig_comfort_pareto.{ext}"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Task B: Baselines comparison
# ---------------------------------------------------------------------------

def _get_tpose() -> np.ndarray:
    """Return canonical T-pose (all joints zero = SMPL-X rest pose)."""
    return np.zeros((22, 3), dtype=np.float64)


def _add_imu_noise(pose: np.ndarray, sigma_deg: float, rng: np.random.Generator) -> np.ndarray:
    """Add Gaussian noise to each joint axis-angle."""
    noisy = pose.copy()
    noisy += rng.standard_normal(pose.shape) * np.deg2rad(sigma_deg)
    return noisy


def _zf_precoder(h: np.ndarray) -> np.ndarray:
    """Zero-forcing precoder for single stream: x = h^* / ||h||."""
    norm = np.linalg.norm(h)
    if norm < 1e-30:
        return np.ones(len(h), dtype=np.complex128) / np.sqrt(len(h))
    return h.conj() / norm


def _mrt_precoder(h: np.ndarray) -> np.ndarray:
    """MRT precoder: x = h / ||h||."""
    norm = np.linalg.norm(h)
    if norm < 1e-30:
        return np.ones(len(h), dtype=np.complex128) / np.sqrt(len(h))
    return h / norm


def compute_rate_with_precoder(
    h_true: np.ndarray,
    precoder: np.ndarray,
    *,
    p_tx_dbm: float,
    noise_dbm: float,
) -> float:
    """SINR and capped rate for a given precoder and true channel.

    SINR = P_tx * |h_true^H x|^2 / N0
    For normalized precoder ||x|| = 1 this is P_tx * |h_true^H x|^2 / N0.
    """
    p_tx_w = 10 ** ((p_tx_dbm - 30) / 10)
    n0_w = 10 ** ((noise_dbm - 30) / 10)
    effective_gain = float(np.abs(np.vdot(h_true, precoder)) ** 2)
    sinr_lin = p_tx_w * effective_gain / n0_w
    sinr_db = 10.0 * np.log10(max(sinr_lin, 1e-30))
    rate_bps = rate_bps_shannon(sinr_db, bandwidth_hz=BW_HZ)
    return rate_bps / 1e6


def twin_mismatch(h_meas: np.ndarray, h_pred: np.ndarray) -> float:
    """Relative Frobenius norm of channel prediction error."""
    err = np.linalg.norm(h_meas - h_pred)
    ref = np.linalg.norm(h_meas)
    return float(err / max(ref, 1e-30))


def run_one_scene(
    *,
    regime: str,
    scene_loss_db: float,
    bs_distance: float,
    amass_pose: np.ndarray,
    rng: np.random.Generator,
    snr_calib_db: float = 20.0,
) -> dict:
    """Evaluate four methods for one scene.

    Returns dict with keys: regime, bs_distance, scene_loss_db,
    rate_mbps[4], twin_mismatch[4].
    """
    # Build BS at the given distance
    bs_center = np.array([0.0, 0.0, 8.0])
    body_centroid = np.array([bs_distance, 0.0, 1.2])
    r_phone = body_centroid + PHONE_OFFSET

    bs = BSArray(n_x=8, n_y=8, center=bs_center,
                 normal=np.array([1.0, 0.0, 0.0]), f_c=F_C)

    # Ground truth: Kirchhoff at AMASS pose
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)
    body_gt = make_body_smplx(amass_pose, body_centroid)
    paths_gt = los_path_dict(bs, body_gt.mesh.centroid)
    h_body_gt, _ = kirchhoff_h_body(body_gt, paths_gt, r_phone, f_c=F_C, M=bs.M)
    h_true = h_los + h_body_gt  # (M,) ground-truth cascaded channel

    # --- Method 1: No-twin ZF ---
    # BS uses only h_LOS for ZF precoder (channel inversion against wrong channel)
    precoder_zf = _zf_precoder(h_los)
    rate_zf = compute_rate_with_precoder(
        h_true, precoder_zf, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM
    )
    # "twin estimate" for method 1: h_LOS only
    mismatch_zf = twin_mismatch(h_true, h_los)

    # --- Method 2: No-twin MRT ---
    precoder_mrt_nlos = _mrt_precoder(h_los)
    rate_mrt_nlos = compute_rate_with_precoder(
        h_true, precoder_mrt_nlos, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM
    )
    mismatch_mrt_nlos = twin_mismatch(h_true, h_los)

    # --- Method 3: T-pose-prior twin MRT ---
    tpose = _get_tpose()
    body_t = make_body_smplx(tpose, body_centroid)
    paths_t = los_path_dict(bs, body_t.mesh.centroid)
    h_body_tpose, _ = kirchhoff_h_body(body_t, paths_t, r_phone, f_c=F_C, M=bs.M)
    h_tpose = h_los + h_body_tpose
    precoder_tpose = _mrt_precoder(h_tpose)
    rate_tpose = compute_rate_with_precoder(
        h_true, precoder_tpose, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM
    )
    mismatch_tpose = twin_mismatch(h_true, h_tpose)

    # --- Method 4: Full closed-loop RIHB ---
    # Add IMU noise to AMASS pose, run Kirchhoff on noisy pose
    noisy_pose = _add_imu_noise(amass_pose, sigma_deg=4.0, rng=rng)
    body_noisy = make_body_smplx(noisy_pose, body_centroid)
    paths_noisy = los_path_dict(bs, body_noisy.mesh.centroid)
    h_body_noisy, _ = kirchhoff_h_body(body_noisy, paths_noisy, r_phone, f_c=F_C, M=bs.M)
    h_noisy = h_los + h_body_noisy

    # Tier-D calibration: fit single complex scalar gamma at SNR=20 dB
    # Simulate measurement: h_true + noise at snr_calib_db
    sig_pow = float(np.sum(np.abs(h_true) ** 2))
    noise_pow = sig_pow / 10 ** (snr_calib_db / 10)
    rng_calib = np.random.default_rng(int(rng.integers(0, 2**31)))
    awgn = rng_calib.standard_normal(len(h_true)) + 1j * rng_calib.standard_normal(len(h_true))
    awgn *= np.sqrt(noise_pow / (2 * len(awgn)))
    h_meas_calib = h_true + awgn

    gamma, _ = fit_tier_d(h_meas_calib, h_los, h_body_noisy, rho=1e-3)
    h_rihb = h_los + gamma * h_body_noisy
    precoder_rihb = _mrt_precoder(h_rihb)
    rate_rihb = compute_rate_with_precoder(
        h_true, precoder_rihb, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM
    )
    mismatch_rihb = twin_mismatch(h_true, h_rihb)

    return dict(
        regime=regime,
        bs_distance=bs_distance,
        scene_loss_db=scene_loss_db,
        rate_mbps=np.array([rate_zf, rate_mrt_nlos, rate_tpose, rate_rihb]),
        twin_mismatch=np.array([mismatch_zf, mismatch_mrt_nlos, mismatch_tpose, mismatch_rihb]),
    )


def task_b_baselines():
    print("\n" + "=" * 60)
    print("Task B: Baselines comparison (30 scenes, 4 methods)")
    print("=" * 60)

    # Load AMASS poses (seed 1 for baselines)
    rng_main = np.random.default_rng(1)
    pose_files = sorted(Path("/home/user/aegis/data/poses").glob("*.npz"))
    n_poses = len(pose_files)
    print(f"  Found {n_poses} AMASS pose files")

    # Scene parameters per regime
    # LOS-attenuated: 25-35 dB scene loss, distance 15-30 m
    # Binding: 50-60 dB scene loss, distance 20-35 m
    # NLOS: 70-85 dB scene loss (effectively extinguished), distance 25-40 m
    regime_specs = {
        "los_attenuated": {"loss_range": (25.0, 35.0), "dist_range": (15.0, 30.0)},
        "binding": {"loss_range": (50.0, 60.0), "dist_range": (20.0, 35.0)},
        "nlos": {"loss_range": (70.0, 85.0), "dist_range": (25.0, 40.0)},
    }
    n_per_regime = 10

    # Pre-draw random scene parameters deterministically
    scenes = []
    rng_scenes = np.random.default_rng(1)
    for regime, spec in regime_specs.items():
        lo_loss, hi_loss = spec["loss_range"]
        lo_dist, hi_dist = spec["dist_range"]
        for i in range(n_per_regime):
            loss = rng_scenes.uniform(lo_loss, hi_loss)
            dist = rng_scenes.uniform(lo_dist, hi_dist)
            # Pick a pose from AMASS (deterministic)
            pose_idx = rng_scenes.integers(0, n_poses)
            frame_idx = rng_scenes.integers(0, 50)
            pose_file = pose_files[pose_idx]
            data = np.load(pose_file)
            n_frames = data["poses"].shape[0]
            fi = min(int(frame_idx), n_frames - 1)
            amass_pose = data["poses"][fi, :66].reshape(22, 3)
            scenes.append({
                "regime": regime,
                "scene_loss_db": float(loss),
                "bs_distance": float(dist),
                "amass_pose": amass_pose,
            })

    print(f"  Total scenes: {len(scenes)}")
    print(f"  Regime breakdown: "
          f"{sum(1 for s in scenes if s['regime']=='los_attenuated')} LOS-att, "
          f"{sum(1 for s in scenes if s['regime']=='binding')} binding, "
          f"{sum(1 for s in scenes if s['regime']=='nlos')} NLOS")

    # Evaluate all scenes
    all_results = []
    t0 = time.time()
    for i, sc in enumerate(scenes):
        if (i + 1) % 5 == 0 or i == 0:
            elapsed = time.time() - t0
            print(f"  Scene {i+1}/{len(scenes)} ({sc['regime']}, "
                  f"loss={sc['scene_loss_db']:.0f} dB, "
                  f"dist={sc['bs_distance']:.0f} m)  elapsed={elapsed:.0f}s")
        sc_rng = np.random.default_rng(i + 100)
        res = run_one_scene(
            regime=sc["regime"],
            scene_loss_db=sc["scene_loss_db"],
            bs_distance=sc["bs_distance"],
            amass_pose=sc["amass_pose"],
            rng=sc_rng,
        )
        all_results.append(res)

    # Aggregate
    rate_mbps_all = np.array([r["rate_mbps"] for r in all_results])    # (30, 4)
    twin_mismatch_all = np.array([r["twin_mismatch"] for r in all_results])  # (30, 4)
    regimes_all = [r["regime"] for r in all_results]
    bs_distances_all = np.array([r["bs_distance"] for r in all_results])

    # Save
    np.savez(
        OUT_DIR / "baselines.npz",
        regimes=np.array(regimes_all),
        methods=np.array(["no_twin_zf", "no_twin_mrt", "tpose_twin_mrt", "rihb_mrt"]),
        rate_mbps=rate_mbps_all,
        twin_mismatch=twin_mismatch_all,
        bs_distances=bs_distances_all,
        scene_losses=np.array([r["scene_loss_db"] for r in all_results]),
    )
    print(f"  Saved: {OUT_DIR}/baselines.npz")

    # Table
    table_str = _format_baselines_table(rate_mbps_all, twin_mismatch_all, regimes_all)
    table_path = OUT_DIR / "baselines_table.txt"
    table_path.write_text(table_str)
    print(f"  Saved: {table_path}")
    print()
    print(table_str)

    # Figure
    _plot_baselines(rate_mbps_all, twin_mismatch_all, regimes_all)

    return {
        "rate_mbps": rate_mbps_all,
        "twin_mismatch": twin_mismatch_all,
        "regimes": regimes_all,
        "scenes": scenes,
    }


def _format_baselines_table(
    rate_mbps: np.ndarray,
    twin_mismatch: np.ndarray,
    regimes: list[str],
) -> str:
    """Format the per-regime results table."""
    methods = ["No-twin ZF", "No-twin MRT", "T-pose twin", "RIHB (full)"]
    regime_list = ["los_attenuated", "binding", "nlos"]
    regime_labels = {
        "los_attenuated": "LOS-attenuated (25-35 dB)",
        "binding": "Binding (50-60 dB)",
        "nlos": "NLOS (70-85 dB)",
    }

    lines = []
    lines.append("=" * 90)
    lines.append("Baselines comparison: Rate (Mbps) and twin mismatch by regime")
    lines.append("Methods: No-twin ZF | No-twin MRT | T-pose twin MRT | RIHB (full closed-loop)")
    lines.append("=" * 90)

    for regime in regime_list:
        mask = np.array([r == regime for r in regimes])
        n_scenes = mask.sum()
        lines.append(f"\n--- {regime_labels[regime]} (N={n_scenes}) ---")

        # Header
        hdr = f"{'Method':<22s}  {'Rate mean':>10s}  {'Rate std':>9s}  "
        hdr += f"{'Mismatch mean':>14s}  {'Mismatch std':>13s}  {'% gain vs MRT':>14s}"
        lines.append(hdr)
        lines.append("-" * 90)

        r_scene = rate_mbps[mask]   # (n_scenes, 4)
        m_scene = twin_mismatch[mask]  # (n_scenes, 4)
        mrt_mean = r_scene[:, 1].mean()

        for mi, method in enumerate(methods):
            r_mean = r_scene[:, mi].mean()
            r_std = r_scene[:, mi].std()
            m_mean = m_scene[:, mi].mean()
            m_std = m_scene[:, mi].std()
            gain_pct = (r_mean / max(mrt_mean, 1e-6) - 1.0) * 100.0
            row = (f"  {method:<20s}  {r_mean:10.2f}  {r_std:9.2f}  "
                   f"{m_mean:14.4f}  {m_std:13.4f}  {gain_pct:+14.1f}%")
            lines.append(row)

    lines.append("\n" + "=" * 90)
    return "\n".join(lines)


def _plot_baselines(
    rate_mbps: np.ndarray,
    twin_mismatch: np.ndarray,
    regimes: list[str],
):
    """Grouped bar chart: one cluster per regime, four bars per cluster."""
    methods = ["No-twin ZF", "No-twin MRT", "T-pose twin", "RIHB"]
    regime_list = ["los_attenuated", "binding", "nlos"]
    regime_labels = ["LOS-att.\n(25-35 dB)", "Binding\n(50-60 dB)", "NLOS\n(70-85 dB)"]
    colors = ["#d62728", "#ff7f0e", "#1f77b4", "#2ca02c"]

    fig, ax_r = plt.subplots(1, 1, figsize=(5.0, 3.6))

    x = np.arange(len(regime_list))
    width = 0.18
    offsets = np.array([-1.5, -0.5, 0.5, 1.5]) * width

    for mi, (method, color, offset) in enumerate(zip(methods, colors, offsets)):
        means = []
        stds = []
        for regime in regime_list:
            mask = np.array([r == regime for r in regimes])
            r_scen = rate_mbps[mask][:, mi]
            means.append(r_scen.mean())
            stds.append(r_scen.std())
        ax_r.bar(x + offset, means, width, yerr=stds, capsize=3,
                 color=color, label=method, alpha=0.85)

    ax_r.set_xticks(x)
    ax_r.set_xticklabels(regime_labels, fontsize=8)
    ax_r.set_ylabel("Rate (Mbps)", fontsize=10)
    ax_r.legend(fontsize=7, loc="lower right", framealpha=0.95, ncol=2)
    ax_r.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    for ext in ("pdf", "png"):
        path = OUT_DIR / f"fig_baselines.{ext}"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Agent log
# ---------------------------------------------------------------------------
def write_agent_log(results_a, results_b):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "agent_comfort_baselines.md"

    lines = []
    lines.append("# Agent log: comfort_pareto + baselines\n")
    lines.append(f"Run date: 2026-05-10\n")

    lines.append("## Task A: Comfort-vs-rate Pareto\n")
    lines.append(f"- Scene: binding regime, 55 dB scene loss, 10 m BS, AMASS seed 0")
    lines.append(f"- Sobol samples: 500")
    lines.append(f"- Baseline rate: {results_a['rate_base_mbps']:.1f} Mbps "
                 f"(SINR = {results_a['sinr_base']:.1f} dB)")
    lines.append(f"- SINR gain range: [{results_a['rate_gain_db'].min():.2f}, "
                 f"{results_a['rate_gain_db'].max():.2f}] dB (SINR difference from baseline)")
    lines.append(f"- Pareto frontier size: {len(results_a['pareto_indices'])} points")
    lines.append(f"- Max SINR gain on Pareto: "
                 f"{results_a['rate_gain_db'][results_a['pareto_indices']].max():.2f} dB")
    lines.append(f"- Outputs: comfort_pareto.npz, fig_comfort_pareto.{{pdf,png}}\n")

    lines.append("## Task B: Baselines comparison\n")
    lines.append("### Per-regime results\n")

    rate_mbps = results_b["rate_mbps"]
    twin_mismatch = results_b["twin_mismatch"]
    regimes = results_b["regimes"]
    methods = ["No-twin ZF", "No-twin MRT", "T-pose twin", "RIHB"]

    regime_list = ["los_attenuated", "binding", "nlos"]
    for regime in regime_list:
        mask = np.array([r == regime for r in regimes])
        lines.append(f"**{regime}** (N={mask.sum()}):")
        for mi, method in enumerate(methods):
            r = rate_mbps[mask][:, mi]
            m = twin_mismatch[mask][:, mi]
            mrt_mean = rate_mbps[mask][:, 1].mean()
            gain = (r.mean() / max(mrt_mean, 1e-6) - 1) * 100
            lines.append(f"  - {method}: rate={r.mean():.1f}±{r.std():.1f} Mbps, "
                         f"mismatch={m.mean():.4f}±{m.std():.4f}, "
                         f"gain vs MRT={gain:+.1f}%")
        lines.append("")

    lines.append("### Verification checks\n")
    # Check expected ordering in NLOS: RIHB > T-pose > MRT > ZF
    nlos_mask = np.array([r == "nlos" for r in regimes])
    if nlos_mask.any():
        nlos_rates = rate_mbps[nlos_mask].mean(axis=0)
        lines.append(f"NLOS mean rates: ZF={nlos_rates[0]:.1f}, MRT={nlos_rates[1]:.1f}, "
                     f"T-pose={nlos_rates[2]:.1f}, RIHB={nlos_rates[3]:.1f} Mbps")
        rihb_beats_mrt = nlos_rates[3] > nlos_rates[1]
        lines.append(f"RIHB > no-twin MRT in NLOS: {rihb_beats_mrt}")

    # Check LOS-attenuated: all methods close
    los_mask = np.array([r == "los_attenuated" for r in regimes])
    if los_mask.any():
        los_rates = rate_mbps[los_mask].mean(axis=0)
        los_spread = los_rates.max() - los_rates.min()
        lines.append(f"LOS-attenuated rate spread: {los_spread:.1f} Mbps "
                     f"(expected: methods within ~2 dB of each other)")

    lines.append(f"\n- Outputs: baselines.npz, baselines_table.txt, fig_baselines.{{pdf,png}}\n")

    log_path.write_text("\n".join(lines))
    print(f"\n  Agent log: {log_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting comfort-vs-rate Pareto and baselines computation...")
    t_start = time.time()

    results_a = task_a_comfort_pareto()
    results_b = task_b_baselines()

    write_agent_log(results_a, results_b)

    elapsed = time.time() - t_start
    print(f"\nDone. Total elapsed: {elapsed:.0f} s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()

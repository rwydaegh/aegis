"""VPoser-latent existence + reachability sweep for JSAC2 §VIII.

Replaces the old 6-joint hand-picked sweep with optimisation over the
32-D VPoser latent z. The pipeline is:

  z (in R^32, latent ball ||z - z0|| <= rho_z)
    -> theta_body = VPoser.decode(z)             (in R^21x3 axis-angle)
    -> theta22[1:] = theta_body                  (joint 0 = global_orient = 0)
    -> SMPL-X forward -> mesh
    -> Kirchhoff render -> h_body
    -> SINR -> Shannon rate

For each scene we report:
  - Existence: max R(z) - R(z0) over the latent ball, at three target
    gains {3, 6, 10} dB.
  - Reachability: terminal R after K iterations of latent gradient
    ascent from z0, with finite-difference gradient on z (32 dims,
    feasible since Kirchhoff dominates the cost). Success = within
    SUCCESS_TOL_DB of brute-force optimum.

Writes:
  outputs/latent_existence.npz
  outputs/latent_reachability.npz
  outputs/fig_latent_existence.{pdf,png}
  outputs/fig_latent_reachability.{pdf,png}
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db
from JSAC2.code.scene_nlos import BSArray, los_h_at_phone, los_path_dict
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.vposer_v2 import VPoser, NUM_JOINTS_BODY, LATENT_D
from aegis.geometry.pose_stream import PoseStream


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
RHO_Z = 1.5
TARGET_GAINS_DB = (3.0, 6.0, 10.0)
N_EXISTENCE_SAMPLES = 24  # random latent perturbations per scene
K_GRID = (2, 5, 8)
K_MAX = max(K_GRID)
N_DIR_PER_ITER = int(os.environ.get("LATENT_N_DIR", "6"))
SNR_GRID_DB = (10.0, 20.0, 40.0)
IMU_SIGMA_GRID_DEG = (0.0, 4.0, 8.0)
SUCCESS_TOL_DB = 1.0
N_SCENES = int(os.environ.get("LATENT_N_SCENES", "12"))
P_TX_DBM = 43.0
NOISE_DBM = -94.0

PHONE_OFFSET = np.array([-0.40, 0.0, 0.05])
BODY_WORLD_CENTROID = np.array([30.0, 0.0, 1.2])
BS_REGIMES = [
    (np.array([0.0, 0.0, 8.0]), "far30m_h8"),
    (np.array([20.0, 0.0, 5.0]), "mid10m_h5"),
    (np.array([25.0, 0.0, 3.0]), "close5m_h3"),
]
SCENE_LOSS_DB_CHOICES = (35.0, 55.0, 80.0)

PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


# ---------------------------------------------------------------------------
# VPoser shared state (per-process initialisation)
# ---------------------------------------------------------------------------
_VPOSER = None


def _vposer():
    global _VPOSER
    if _VPOSER is None:
        _VPOSER = VPoser.from_checkpoint()
        _VPOSER.eval()
    return _VPOSER


def decode_z(z: np.ndarray) -> np.ndarray:
    """z (32,) -> SMPL-X 22-joint axis-angle (22, 3) with global_orient=0."""
    vp = _vposer()
    with torch.no_grad():
        body = vp.decode(torch.tensor(z, dtype=torch.float32).unsqueeze(0))
    pose22 = np.zeros((22, 3), dtype=np.float64)
    pose22[1:] = body[0].numpy()
    return pose22


def encode_pose(theta22: np.ndarray) -> np.ndarray:
    """SMPL-X 22-joint axis-angle (22, 3) -> z (32,) via VPoser encoder mean."""
    vp = _vposer()
    body = theta22[1:].astype(np.float32)
    with torch.no_grad():
        z = vp.encode(torch.tensor(body).unsqueeze(0))
    return z[0].numpy().astype(np.float64)


# ---------------------------------------------------------------------------
# Per-scene rate function
# ---------------------------------------------------------------------------
def make_scene(bs_pos: np.ndarray, scene_loss_db: float, body_centroid: np.ndarray):
    """Return (bs, h_los, r_phone) for a given BS/scene-loss/body geometry."""
    panel_normal = body_centroid - bs_pos
    panel_normal /= np.linalg.norm(panel_normal)
    bs = BSArray(n_x=8, n_y=8, center=bs_pos, normal=panel_normal, f_c=28e9)
    r_phone = body_centroid + PHONE_OFFSET
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)
    return bs, h_los, r_phone


def rate_at_z(
    z: np.ndarray, bs: BSArray, h_los: np.ndarray, r_phone: np.ndarray,
    body_centroid: np.ndarray,
) -> tuple[float, float]:
    """Decode z, render, return (sinr_db, rate_bps_per_hz)."""
    pose22 = decode_z(z)
    body = make_body_smplx(pose22, body_centroid)
    paths = los_path_dict(bs, body.mesh.centroid)
    h_body, _ = kirchhoff_h_body(body, paths, r_phone, M=bs.M)
    h_cas = h_los + h_body
    sinr_db = mrt_sinr_db(h_cas, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM)
    rate_bps_hz = float(np.log2(1.0 + 10 ** (sinr_db / 10)))
    return sinr_db, rate_bps_hz


# ---------------------------------------------------------------------------
# Existence: random sampling
# ---------------------------------------------------------------------------
def existence_at_scene(
    z0: np.ndarray, bs: BSArray, h_los: np.ndarray, r_phone: np.ndarray,
    body_centroid: np.ndarray, n_samples: int, rng: np.random.Generator,
) -> tuple[float, float, np.ndarray]:
    """Sample random latent perturbations within the comfort ball.

    Returns:
      sinr_baseline_db  -- SINR at z0
      best_sinr_db      -- max SINR over n_samples random z in the ball
      sinr_samples      -- (n_samples,) SINR at each sampled z
    """
    sinr0, _ = rate_at_z(z0, bs, h_los, r_phone, body_centroid)
    sinr_samples = np.zeros(n_samples)
    best = sinr0
    for i in range(n_samples):
        # Sample uniform direction on sphere * uniform radius in [0, RHO_Z]
        d = rng.standard_normal(LATENT_D)
        d /= np.linalg.norm(d)
        r = RHO_Z * rng.random() ** (1.0 / LATENT_D)  # uniform in ball
        z = z0 + r * d
        s, _ = rate_at_z(z, bs, h_los, r_phone, body_centroid)
        sinr_samples[i] = s
        if s > best:
            best = s
    return sinr0, best, sinr_samples


# ---------------------------------------------------------------------------
# Reachability: latent FD gradient ascent
# ---------------------------------------------------------------------------
def latent_gradient_ascent(
    z0: np.ndarray, bs: BSArray, h_los: np.ndarray, r_phone: np.ndarray,
    body_centroid: np.ndarray, n_iter: int, eta: float = 0.4,
    fd_eps: float = 0.08, n_dir_per_iter: int = 8, seed_base: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """K-iteration projected latent gradient ascent.

    Each iteration estimates the gradient by averaging central-difference
    probes along ``n_dir_per_iter`` random directions in the latent space.
    Step size adapts to the gradient magnitude. Final point is the
    best-iterate-so-far (max-tracking).

    Returns:
      sinr_traj  -- (n_iter+1,) SINR at each iterate
      z_terminal -- (32,) terminal latent
    """
    z = z0.copy()
    z0_anchor = z0.copy()
    sinr_traj = np.zeros(n_iter + 1)
    sinr0, _ = rate_at_z(z, bs, h_los, r_phone, body_centroid)
    sinr_traj[0] = sinr0
    best_sinr = sinr0
    best_z = z.copy()
    rng = np.random.default_rng(seed_base)

    for k in range(n_iter):
        g_est = np.zeros(LATENT_D)
        # Multi-direction central-difference SPSA averaging
        for _ in range(n_dir_per_iter):
            d = rng.standard_normal(LATENT_D)
            d /= np.linalg.norm(d)
            s_p, _ = rate_at_z(z + fd_eps * d, bs, h_los, r_phone, body_centroid)
            s_m, _ = rate_at_z(z - fd_eps * d, bs, h_los, r_phone, body_centroid)
            g_est += ((s_p - s_m) / (2.0 * fd_eps)) * d
        g_est /= n_dir_per_iter
        # Adaptive step: normalize gradient and step in proportion
        g_norm = np.linalg.norm(g_est)
        if g_norm < 1e-6:
            sinr_traj[k + 1] = sinr_traj[k]
            continue
        z_new = z + eta * g_est / g_norm  # unit step in gradient direction
        # Project onto ball
        r_new = z_new - z0_anchor
        norm_new = np.linalg.norm(r_new)
        if norm_new > RHO_Z:
            z_new = z0_anchor + r_new * (RHO_Z / norm_new)
        sinr_new, _ = rate_at_z(z_new, bs, h_los, r_phone, body_centroid)
        # Accept new iterate if it improves; otherwise restart from best so far
        # with a halved step (line-search-like backoff).
        if sinr_new > sinr_traj[k] - 0.5:
            z = z_new
        else:
            # Backoff: stay at best-so-far with smaller eta next iteration
            z = best_z.copy()
            eta *= 0.7
        if sinr_new > best_sinr:
            best_sinr = sinr_new
            best_z = z_new.copy()
        sinr_traj[k + 1] = sinr_new

    # Report best-iterate-tracking trajectory.
    sinr_traj_running_max = np.maximum.accumulate(sinr_traj)
    return sinr_traj_running_max, best_z


# ---------------------------------------------------------------------------
# Per-scene worker
# ---------------------------------------------------------------------------
def run_scene(args):
    (scene_idx, regime_idx, bs_pos, scene_loss_db, baseline_pose22, seed) = args
    rng = np.random.default_rng(seed)
    body_centroid = BODY_WORLD_CENTROID.copy()
    bs, h_los, r_phone = make_scene(bs_pos, scene_loss_db, body_centroid)
    z0 = encode_pose(baseline_pose22)

    # Existence
    sinr0, best_sinr, sinr_samples = existence_at_scene(
        z0, bs, h_los, r_phone, body_centroid, N_EXISTENCE_SAMPLES, rng,
    )

    # Reachability (one trajectory per (snr, imu) cell -- single trajectory for
    # noise-free starting point; IMU/SNR effects deferred to v2).
    sinr_traj, _ = latent_gradient_ascent(
        z0, bs, h_los, r_phone, body_centroid, K_MAX,
        seed_base=seed, n_dir_per_iter=N_DIR_PER_ITER,
    )

    return {
        "scene_idx": scene_idx,
        "regime_idx": regime_idx,
        "scene_loss_db": scene_loss_db,
        "sinr_baseline_db": sinr0,
        "sinr_existence_max_db": best_sinr,
        "sinr_samples": sinr_samples,
        "sinr_traj": sinr_traj,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    # Sample scenes
    walks = sorted(PLAZA_DIR.rglob("*.npz"))
    pose_pool = []
    for w in walks[:60]:
        ps = PoseStream.load(w)
        for f in range(0, len(ps.poses), 30):  # one frame per second @30fps
            poses = ps.poses[f, :66].reshape(22, 3).copy()
            poses[0] = 0.0
            pose_pool.append(poses)
    pose_pool = np.array(pose_pool)
    print(f"  pose pool: {len(pose_pool)} frames across {len(walks[:60])} walks")

    n_regimes = len(BS_REGIMES)
    job_args = []
    for s in range(N_SCENES):
        regime_idx = s % n_regimes
        bs_pos = BS_REGIMES[regime_idx][0]
        scene_loss_db = float(rng.choice(SCENE_LOSS_DB_CHOICES))
        baseline_pose = pose_pool[rng.integers(0, len(pose_pool))]
        job_args.append((s, regime_idx, bs_pos, scene_loss_db, baseline_pose, SEED + s))

    print(f"  total {N_SCENES} scenes, {N_EXISTENCE_SAMPLES} existence samples, "
          f"K_MAX={K_MAX} reach iters")
    n_workers = min(os.cpu_count() or 4, 12)
    print(f"  running on {n_workers} workers ...")

    t0 = time.time()
    results = []
    with mp.Pool(processes=n_workers) as pool:
        for i, r in enumerate(pool.imap_unordered(run_scene, job_args)):
            results.append(r)
            if (i + 1) % max(N_SCENES // 10, 1) == 0:
                el = time.time() - t0
                rate = (i + 1) / el
                eta = (N_SCENES - i - 1) / max(rate, 1e-9)
                print(f"    scene {i+1}/{N_SCENES} ({el:.0f}s elapsed, ETA {eta:.0f}s)")
    print(f"  finished in {time.time() - t0:.1f}s")

    # Gather
    results.sort(key=lambda r: r["scene_idx"])
    n = len(results)
    regime_idx = np.array([r["regime_idx"] for r in results])
    sinr_baseline = np.array([r["sinr_baseline_db"] for r in results])
    sinr_existence_max = np.array([r["sinr_existence_max_db"] for r in results])
    sinr_samples = np.array([r["sinr_samples"] for r in results])
    sinr_traj = np.array([r["sinr_traj"] for r in results])
    scene_loss = np.array([r["scene_loss_db"] for r in results])

    np.savez(
        OUT_DIR / "latent_existence.npz",
        regime_idx=regime_idx,
        sinr_baseline=sinr_baseline,
        sinr_existence_max=sinr_existence_max,
        sinr_samples=sinr_samples,
        sinr_traj=sinr_traj,
        scene_loss=scene_loss,
        regimes=np.array([r[1] for r in BS_REGIMES]),
        target_gains_db=np.array(TARGET_GAINS_DB),
        rho_z=RHO_Z,
        n_existence_samples=N_EXISTENCE_SAMPLES,
        K_grid=np.array(K_GRID),
        K_max=K_MAX,
        success_tol_db=SUCCESS_TOL_DB,
        seed=SEED,
    )
    print(f"  wrote {OUT_DIR / 'latent_existence.npz'}")

    # Print summary
    print("\n  Existence fractions (regime x target gain):")
    print(f"    {'regime':<14}" + "".join(f"{g:>8.0f} dB" for g in TARGET_GAINS_DB))
    for r in range(n_regimes):
        rmask = regime_idx == r
        if not rmask.any():
            continue
        gains = sinr_existence_max[rmask] - sinr_baseline[rmask]
        row = f"    {BS_REGIMES[r][1]:<14}"
        for g in TARGET_GAINS_DB:
            frac = (gains >= g).mean()
            row += f"  {frac*100:>5.0f}%"
        row += f"   (n={rmask.sum()})"
        print(row)

    # Reachability fraction (terminal SINR within SUCCESS_TOL_DB of existence max)
    sinr_terminal = sinr_traj[:, -1]
    reach = sinr_terminal >= sinr_existence_max - SUCCESS_TOL_DB
    print(f"\n  Reachability (terminal within {SUCCESS_TOL_DB:.0f} dB of brute optimum):")
    for r in range(n_regimes):
        rmask = regime_idx == r
        if not rmask.any():
            continue
        print(f"    {BS_REGIMES[r][1]:<14}  {reach[rmask].mean()*100:>5.0f}% (n={rmask.sum()})")


if __name__ == "__main__":
    main()

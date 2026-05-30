"""Reachability sweep — Part B of the JSAC2 §VIII three-part convergence study.

Given the existence-positive subset at the 6 dB target (Part A), simulate
K-iteration UL-pilot-corrected gradient descent from a cold start (the
AMASS baseline pose). At each iteration:

  1. Sweep joint j (cycling) over 7 absolute positions on the JOINT_SWEEP_GRID_DEG
     grid (−15° … +15°, 5° spacing), holding all other joints fixed.
  2. Take a comfort-budget-limited step (project the proposed Δθ back
     into the comfort ball if needed).
  3. Observe a noisy uplink pilot at the requested SNR and fit body-side
     γ via ``calibration.fit_tier_b`` with K = TIER_B_K modes.
  4. Update the cascaded channel estimate: the next iteration's gradient
     uses the γ-corrected prediction.

Sweep:
  K_grid     = {2, 5, 10, 20}
  SNR_grid   = {10, 20, 40} dB
  IMU σ_grid = {0, 4, 8} deg per joint

Success criterion: terminal cascaded SINR within 1 dB of the brute-force
optimum from Part A.

Compute optimisation:
  The SMPL-X forward pass dominates at ~1.1 s per call. All 9 (SNR, IMU σ)
  trajectory variants for a given scene share the same physics renders via a
  per-scene pose-keyed cache: a dict {bytes(delta_deg.round(3)) -> h_body}.
  Trajectories for different (SNR, IMU σ) cells visit similar (often identical
  for high-SNR / low-σ) delta sequences, so cache hits are frequent. The
  scene-level job processes all 9 × K_MAX = 180 trajectory steps for one
  scene, parallelised over scenes (12 workers).

  Scene count: top-20 highest-gain scenes per regime (n=60 total), giving
  ~20 min wall-clock at 12 workers.

Outputs:
    outputs/reachability_sweep.npz
    outputs/fig_reachability.{pdf,png}
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

from JSAC2.code.calibration import fit_tier_b
from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db
from JSAC2.code.scene_nlos import BSArray, los_h_at_phone, los_path_dict
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.existence_sweep import (
    BS_REGIMES,
    BODY_WORLD_CENTROID_BASE,
    COMFORT_REF_DEG,
    COMFORT_RHO,
    JOINT_AXES,
    JOINT_INDICES,
    JOINT_NAMES,
    N_JOINTS,
    PHONE_OFFSET,
    apply_pose_move,
    comfort_cost,
    rotate_bs_in_azimuth,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
K_GRID = (2, 5, 10, 20)
SNR_GRID_DB = (10.0, 20.0, 40.0)
IMU_SIGMA_GRID_DEG = (0.0, 4.0, 8.0)
K_MAX = max(K_GRID)
# Per-joint absolute sweep grid. Each iteration picks one joint j and sweeps
# its absolute displacement delta_j over this grid (other joints held fixed).
# The 7-point grid mirrors the existence_sweep's DELTA_GRID_DEG so that the
# reachability oracle (SNR=∞, IMU σ=0) reproduces the existence-sweep trajectory.
JOINT_SWEEP_GRID_DEG = (-15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0)
TIER_B_K = 8
SUCCESS_TOL_DB = 1.0
N_SCENES_PER_REGIME = 20  # top-N highest-gain scenes per regime
TARGET_GAIN_DB = 6.0
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")
EXIST_NPZ = OUT_DIR / "existence_sweep.npz"
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
LOG_PATH = Path("/home/user/aegis/JSAC2/code/agent_logs/agent_existence_reachability.md")


# ---------------------------------------------------------------------------
# Per-scene helpers
# ---------------------------------------------------------------------------
def project_to_comfort_ball(delta_deg: np.ndarray) -> np.ndarray:
    """Scale the perturbation back into the comfort ball if it exceeds ρ."""
    c = comfort_cost(delta_deg)
    if c <= COMFORT_RHO:
        return delta_deg.copy()
    return delta_deg * np.sqrt(COMFORT_RHO / c)


def synthesize_ul_pilot(
    h_true: np.ndarray, snr_db: float, rng: np.random.Generator
) -> np.ndarray:
    sig_pow = float(np.sum(np.abs(h_true) ** 2))
    noise_pow = sig_pow / 10 ** (snr_db / 10)
    M = len(h_true)
    n = rng.standard_normal(M) + 1j * rng.standard_normal(M)
    n *= np.sqrt(noise_pow / (2 * M))
    return h_true + n


def _delta_key(delta_deg: np.ndarray) -> bytes:
    """Cache key: round to 0.1 deg to handle floating-point jitter."""
    return (delta_deg * 10.0).round().astype(np.int16).tobytes()


class PoseCache:
    """Thread-local cache: delta_deg (bytes) -> (h_body, Lambda, sinr).

    Each scene gets its own cache instance (not shared across workers).
    All physics (SMPL-X forward, Kirchhoff) live here.
    """

    def __init__(self, baseline_pose, body_centroid, bs, h_los, r_phone):
        self._baseline_pose = baseline_pose
        self._body_centroid = body_centroid
        self._bs = bs
        self._h_los = h_los
        self._r_phone = r_phone
        self._cache: dict[bytes, tuple[np.ndarray, np.ndarray, float]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, delta_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        """Return (h_body, Lambda, sinr_db). Lambda may be None if T_vis == 0."""
        k = _delta_key(delta_deg)
        if k in self._cache:
            self.hits += 1
            return self._cache[k]
        self.misses += 1
        pose = apply_pose_move(self._baseline_pose, delta_deg)
        body = make_body_smplx(pose, self._body_centroid)
        path_dict = los_path_dict(self._bs, body.mesh.centroid)
        h_body, extras = kirchhoff_h_body(
            body, path_dict, self._r_phone, M=self._bs.M, return_per_triangle=True
        )
        Lambda = extras.get("Lambda")
        h_cas = self._h_los + h_body
        sinr_db = mrt_sinr_db(h_cas, p_tx_dbm=43.0, noise_dbm=-94.0)
        self._cache[k] = (h_body, Lambda, sinr_db)
        return self._cache[k]

    def sinr(self, delta_deg: np.ndarray) -> float:
        """Return only the SINR (using scalar γ correction for FD gradient)."""
        _, _, sinr_db = self.get(delta_deg)
        return sinr_db

    def sinr_calibrated(
        self, delta_deg: np.ndarray, gamma_scalar: complex
    ) -> float:
        """Return γ-corrected twin-side SINR prediction."""
        h_body, _, _ = self.get(delta_deg)
        h_cas = self._h_los + gamma_scalar * h_body
        return mrt_sinr_db(h_cas, p_tx_dbm=43.0, noise_dbm=-94.0)


# ---------------------------------------------------------------------------
# One trajectory: K_MAX-iter gradient descent at fixed (SNR, IMU σ)
# ---------------------------------------------------------------------------
def run_trajectory_cached(
    *,
    cache: PoseCache,
    h_los: np.ndarray,
    snr_db: float,
    imu_sigma_deg: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Run K_MAX iterations using the shared PoseCache.

    Returns:
      sinr_traj (K_MAX+1,) — true SINR at each iteration.
      delta_traj (K_MAX+1, N_JOINTS) — executed Δθ at each step.
    """
    delta = np.zeros(N_JOINTS, dtype=np.float64)
    sinr_traj = np.zeros(K_MAX + 1, dtype=np.float64)
    delta_traj = np.zeros((K_MAX + 1, N_JOINTS), dtype=np.float64)

    h_body0, Lambda0, sinr0 = cache.get(delta)
    sinr_traj[0] = sinr0
    delta_traj[0] = delta.copy()

    # Initial calibration.
    if Lambda0 is not None and Lambda0.shape[1] > 0:
        h_meas = synthesize_ul_pilot(h_los + h_body0, snr_db, rng)
        cal = fit_tier_b(h_meas, h_los, Lambda0, K=TIER_B_K)
        h_body_cal = cal["h_body_pred"]
        h_body_norm = float(np.sum(np.abs(h_body0) ** 2))
        gamma_scalar = (
            complex(np.vdot(h_body0, h_body_cal)) / max(h_body_norm, 1e-30)
        )
    else:
        gamma_scalar = complex(1.0)

    best_sinr_so_far = sinr0
    best_delta_so_far = delta.copy()

    for t in range(K_MAX):
        j = t % N_JOINTS  # cycle through joints

        # Sweep absolute delta_j over the 7-point grid, keeping other joints.
        sinr_cand = []
        delta_cand = []
        for v_abs in JOINT_SWEEP_GRID_DEG:
            d_try = delta.copy()
            d_try[j] = v_abs
            d_try = project_to_comfort_ball(d_try)
            s_pred = cache.sinr_calibrated(d_try, gamma_scalar)
            sinr_cand.append(s_pred)
            delta_cand.append(d_try)
        i_best = int(np.argmax(sinr_cand))
        proposed_delta = delta_cand[i_best]

        # IMU noise corrupts commanded → executed delta.
        if imu_sigma_deg > 0:
            imu_noise = rng.normal(0.0, imu_sigma_deg, size=N_JOINTS)
            executed_delta = proposed_delta + imu_noise
        else:
            executed_delta = proposed_delta.copy()
        executed_delta = project_to_comfort_ball(executed_delta)

        # True physics at executed delta.
        h_body_t, Lambda_t, sinr_t = cache.get(executed_delta)

        # UL pilot + recalibrate γ.
        if Lambda_t is not None and Lambda_t.shape[1] > 0:
            h_meas_t = synthesize_ul_pilot(h_los + h_body_t, snr_db, rng)
            cal = fit_tier_b(h_meas_t, h_los, Lambda_t, K=TIER_B_K)
            h_body_cal = cal["h_body_pred"]
            h_body_norm = float(np.sum(np.abs(h_body_t) ** 2))
            gamma_scalar = (
                complex(np.vdot(h_body_t, h_body_cal)) / max(h_body_norm, 1e-30)
            )

        delta = executed_delta.copy()
        if sinr_t > best_sinr_so_far:
            best_sinr_so_far = sinr_t
            best_delta_so_far = executed_delta.copy()
        elif sinr_t < best_sinr_so_far - 2.0:
            # Rewind to last good point if we drifted far below best.
            delta = best_delta_so_far.copy()

        sinr_traj[t + 1] = sinr_t
        delta_traj[t + 1] = executed_delta.copy()

    return sinr_traj, delta_traj


# ---------------------------------------------------------------------------
# One scene worker: all 9 (SNR, IMU σ) cells via shared cache
# ---------------------------------------------------------------------------
def run_scene_all_cells(args):
    """Process one scene across all (SNR, IMU σ) cells using a shared physics cache."""
    (
        scene_idx,
        regime_idx,
        baseline_pose,
        bs_pos,
        scene_loss_db,
        azimuth_offset_deg,
        sinr_brute_optimum,
        base_seed,
    ) = args

    body_centroid = BODY_WORLD_CENTROID_BASE.copy()
    bs_pos_rot = rotate_bs_in_azimuth(bs_pos, body_centroid, azimuth_offset_deg)
    panel_normal = body_centroid - bs_pos_rot
    panel_normal /= np.linalg.norm(panel_normal)
    bs = BSArray(n_x=8, n_y=8, center=bs_pos_rot, normal=panel_normal, f_c=28e9)
    r_phone = body_centroid + PHONE_OFFSET
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)

    cache = PoseCache(baseline_pose, body_centroid, bs, h_los, r_phone)

    n_K = len(K_GRID)
    n_snr = len(SNR_GRID_DB)
    n_imu = len(IMU_SIGMA_GRID_DEG)
    # [K_idx, snr_idx, imu_idx]
    sinr_at_K_out = np.zeros((n_K, n_snr, n_imu), dtype=np.float64)
    success_at_K_out = np.zeros((n_K, n_snr, n_imu), dtype=bool)
    sinr_traj_out = np.zeros((K_MAX + 1, n_snr, n_imu), dtype=np.float64)

    for si, snr_db in enumerate(SNR_GRID_DB):
        for ii, imu_sig in enumerate(IMU_SIGMA_GRID_DEG):
            cell_seed = base_seed * 7919 + si * 13 + ii * 11
            rng = np.random.default_rng(cell_seed)
            sinr_traj, _ = run_trajectory_cached(
                cache=cache,
                h_los=h_los,
                snr_db=snr_db,
                imu_sigma_deg=imu_sig,
                rng=rng,
            )
            sinr_traj_out[:, si, ii] = sinr_traj
            for ki, K in enumerate(K_GRID):
                best_so_far = float(sinr_traj[: K + 1].max())
                sinr_at_K_out[ki, si, ii] = best_so_far
                success_at_K_out[ki, si, ii] = (
                    best_so_far >= sinr_brute_optimum - SUCCESS_TOL_DB
                )

    return scene_idx, regime_idx, sinr_at_K_out, success_at_K_out, sinr_traj_out, cache.hits, cache.misses


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main():
    if not EXIST_NPZ.exists():
        raise FileNotFoundError(
            f"existence_sweep.npz not found at {EXIST_NPZ}. "
            "Run existence_sweep.py first."
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with np.load(EXIST_NPZ, allow_pickle=False) as f:
        existence_pose_idx = f["pose_baseline_idx"]
        existence_regime_idx = f["regime_idx"]
        existence_scene_loss = f["scene_loss"]
        existence_azimuth = f["azimuth_offset_deg"]
        existence_best_gain_db = f["best_gain_db"]
        existence_best_sinr_db = f["best_sinr_db"]
        existence_sinr_baseline_db = f["sinr_baseline_db"]
        pose_pool_walk_idx = f["pose_pool_walk_idx"]
        pose_pool_frame_idx = f["pose_pool_frame_idx"]

    from aegis.geometry.pose_stream import PoseStream

    walks = sorted(PLAZA_DIR.rglob("*.npz"))
    pose_streams = {}
    for s in range(len(existence_pose_idx)):
        wi = int(pose_pool_walk_idx[s])
        if wi not in pose_streams:
            ps = PoseStream.load(walks[wi])
            poses_arr = ps.poses[:, :66].reshape(-1, 22, 3).copy()
            poses_arr[:, 0] = 0.0
            pose_streams[wi] = poses_arr

    # Select top-N highest-gain existence-positive scenes per regime.
    n_regimes = len(BS_REGIMES)
    selected_scene_lists = []
    for r in range(n_regimes):
        mask = (existence_regime_idx == r) & (existence_best_gain_db >= TARGET_GAIN_DB)
        idxs = np.where(mask)[0]
        gains = existence_best_gain_db[idxs]
        sorted_order = np.argsort(gains)[::-1]  # descending gain
        idxs = idxs[sorted_order]
        if len(idxs) > N_SCENES_PER_REGIME:
            idxs = idxs[:N_SCENES_PER_REGIME]
        selected_scene_lists.append(np.sort(idxs))
        print(f"  regime {r} ({BS_REGIMES[r][1]}): {len(idxs)} scenes selected "
              f"(of {int(mask.sum())} existence-positive at {TARGET_GAIN_DB} dB)")

    all_scene_ids = np.concatenate(selected_scene_lists)
    n_scenes_total = len(all_scene_ids)
    n_K = len(K_GRID)
    n_snr = len(SNR_GRID_DB)
    n_imu = len(IMU_SIGMA_GRID_DEG)
    print(
        f"  total {n_scenes_total} scenes × {n_snr} SNR × {n_imu} IMU σ "
        f"= {n_scenes_total * n_snr * n_imu} trajectories"
    )
    print(f"  each scene runs {n_snr * n_imu} cells inside one worker (shared physics cache)")

    # Build one job per scene (not per cell).
    job_args = []
    for s_id in all_scene_ids:
        s_id = int(s_id)
        wi = int(pose_pool_walk_idx[s_id])
        fi = int(pose_pool_frame_idx[s_id])
        baseline_pose = pose_streams[wi][fi]
        regime_idx = int(existence_regime_idx[s_id])
        bs_pos = BS_REGIMES[regime_idx][0]
        scene_loss_db = float(existence_scene_loss[s_id])
        azimuth_offset_deg = float(existence_azimuth[s_id])
        sinr_brute_optimum = float(existence_best_sinr_db[s_id])
        base_seed = SEED + s_id
        job_args.append(
            (
                s_id,
                regime_idx,
                baseline_pose,
                bs_pos,
                scene_loss_db,
                azimuth_offset_deg,
                sinr_brute_optimum,
                base_seed,
            )
        )

    n_workers = min(os.cpu_count() or 4, 12)
    print(f"  running {n_scenes_total} scene-level jobs on {n_workers} workers ...")

    success_count = np.zeros((n_regimes, n_K, n_snr, n_imu), dtype=np.int32)
    n_per_cell = np.zeros((n_regimes, n_snr, n_imu), dtype=np.int32)
    failure_indicator = np.zeros((n_scenes_total, n_K, n_snr, n_imu), dtype=bool)
    sinr_at_K_arr = np.zeros((n_scenes_total, n_K, n_snr, n_imu), dtype=np.float64)
    sinr_traj_arr = np.zeros((n_scenes_total, K_MAX + 1, n_snr, n_imu), dtype=np.float64)

    scene_id_to_compact = {int(s): i for i, s in enumerate(all_scene_ids)}

    t0 = time.time()
    total_cache_hits = 0
    total_cache_misses = 0

    with mp.Pool(processes=n_workers) as pool_proc:
        for job_idx, result in enumerate(
            pool_proc.imap(run_scene_all_cells, job_args)
        ):
            scene_idx, r, sinr_at_K_out, success_at_K_out, sinr_traj_out, hits, misses = result
            ci = scene_id_to_compact[int(scene_idx)]
            total_cache_hits += hits
            total_cache_misses += misses
            for si in range(n_snr):
                for ii in range(n_imu):
                    n_per_cell[r, si, ii] += 1
            for ki in range(n_K):
                for si in range(n_snr):
                    for ii in range(n_imu):
                        sinr_at_K_arr[ci, ki, si, ii] = sinr_at_K_out[ki, si, ii]
                        if success_at_K_out[ki, si, ii]:
                            success_count[r, ki, si, ii] += 1
                        else:
                            failure_indicator[ci, ki, si, ii] = True
            sinr_traj_arr[ci] = sinr_traj_out
            if (job_idx + 1) % max(n_scenes_total // 10, 1) == 0:
                elapsed = time.time() - t0
                rate = (job_idx + 1) / elapsed
                eta = (n_scenes_total - (job_idx + 1)) / max(rate, 1e-9)
                print(
                    f"    scene {job_idx+1}/{n_scenes_total} "
                    f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s, "
                    f"cache {total_cache_hits}H/{total_cache_misses}M)"
                )
    elapsed = time.time() - t0
    cache_ratio = total_cache_hits / max(total_cache_hits + total_cache_misses, 1)
    print(f"  finished in {elapsed:.1f}s, cache hit rate {cache_ratio:.1%}")

    # Compute success rates.
    success_rate = np.zeros((n_regimes, n_K, n_snr, n_imu))
    for r in range(n_regimes):
        for ki in range(n_K):
            for si in range(n_snr):
                for ii in range(n_imu):
                    n_cell = n_per_cell[r, si, ii]
                    success_rate[r, ki, si, ii] = (
                        success_count[r, ki, si, ii] / max(n_cell, 1)
                    )

    # Print 36-cell table per regime.
    print("\n  === 36-cell success rate tables per regime ===")
    for r, (_, rname) in enumerate(BS_REGIMES):
        print(f"\n  Regime: {rname}  (n={int(n_per_cell[r, 0, 0])} scenes)")
        print(f"  {'K':>4}  {'SNR':>8}  {'IMU=0°':>8}  {'IMU=4°':>8}  {'IMU=8°':>8}")
        for ki, K in enumerate(K_GRID):
            for si, snr_db in enumerate(SNR_GRID_DB):
                row = "  ".join(
                    f"{success_rate[r, ki, si, ii]*100:7.1f}%"
                    for ii in range(n_imu)
                )
                print(f"  K={K:2d}  SNR={int(snr_db):3d}dB  {row}")

    # Monotonicity checks.
    print("\n  === Monotonicity checks ===")
    mono_K_ok = True
    mono_snr_ok = True
    mono_imu_ok = True
    for r in range(n_regimes):
        for si in range(n_snr):
            for ii in range(n_imu):
                vals = [success_rate[r, ki, si, ii] for ki in range(n_K)]
                if not all(vals[i] <= vals[i + 1] + 0.05 for i in range(len(vals) - 1)):
                    mono_K_ok = False
        for ki in range(n_K):
            for ii in range(n_imu):
                vals = [success_rate[r, ki, si, ii] for si in range(n_snr)]
                if not all(vals[i] <= vals[i + 1] + 0.05 for i in range(len(vals) - 1)):
                    mono_snr_ok = False
            for si in range(n_snr):
                vals = [success_rate[r, ki, si, ii] for ii in range(n_imu)]
                if not all(vals[i] >= vals[i + 1] - 0.05 for i in range(len(vals) - 1)):
                    mono_imu_ok = False
    print(f"  Monotone in K (larger K -> higher rate): {mono_K_ok}")
    print(f"  Monotone in SNR (higher SNR -> higher rate): {mono_snr_ok}")
    print(f"  Monotone in IMU σ (smaller σ -> higher rate): {mono_imu_ok}")

    # Print key corner-case verification.
    print("\n  Corner-case verification:")
    K_idx_20 = list(K_GRID).index(20)
    K_idx_2 = list(K_GRID).index(2)
    snr_idx_40 = list(SNR_GRID_DB).index(40.0)
    snr_idx_10 = list(SNR_GRID_DB).index(10.0)
    imu_idx_0 = list(IMU_SIGMA_GRID_DEG).index(0.0)
    imu_idx_8 = list(IMU_SIGMA_GRID_DEG).index(8.0)
    print("    regime              | K=20 SNR=40 IMU=0   K=2 SNR=10 IMU=8")
    for r, (_, rname) in enumerate(BS_REGIMES):
        v_easy = success_rate[r, K_idx_20, snr_idx_40, imu_idx_0]
        v_hard = success_rate[r, K_idx_2, snr_idx_10, imu_idx_8]
        n_cell = int(n_per_cell[r, 0, 0])
        print(f"    {rname:18s}  | {v_easy*100:6.1f}%  (expect >90%)    {v_hard*100:6.1f}%  (expect <30%)  n={n_cell}")

    # Save NPZ.
    out_path = OUT_DIR / "reachability_sweep.npz"
    scene_regime_arr = np.array(
        [int(existence_regime_idx[s]) for s in all_scene_ids], dtype=np.int32
    )
    scene_baseline_sinr_db = np.array(
        [float(existence_sinr_baseline_db[s]) for s in all_scene_ids]
    )
    scene_brute_optimum_db = np.array(
        [float(existence_best_sinr_db[s]) for s in all_scene_ids]
    )
    np.savez(
        out_path,
        K_grid=np.array(K_GRID),
        snr_grid_db=np.array(SNR_GRID_DB),
        imu_sigma_grid_deg=np.array(IMU_SIGMA_GRID_DEG),
        regimes=np.array([name for _, name in BS_REGIMES]),
        success_rate=success_rate,
        success_count=success_count,
        n_per_cell=n_per_cell,
        failure_indicator=failure_indicator,
        terminal_rate_within_1db=success_rate,  # alias
        sinr_at_K=sinr_at_K_arr,
        sinr_traj=sinr_traj_arr,
        scene_compact_id=all_scene_ids.astype(np.int32),
        scene_regime=scene_regime_arr,
        scene_baseline_sinr_db=scene_baseline_sinr_db,
        scene_brute_optimum_db=scene_brute_optimum_db,
        joint_indices=np.array(JOINT_INDICES),
        joint_axes=np.array(JOINT_AXES),
        joint_names=np.array(JOINT_NAMES),
        target_gain_db=TARGET_GAIN_DB,
        success_tol_db=SUCCESS_TOL_DB,
        n_scenes_per_regime=N_SCENES_PER_REGIME,
        cache_hit_rate=cache_ratio,
        seed=SEED,
        elapsed_sec=elapsed,
    )
    print(f"  wrote {out_path}")

    make_reachability_figure(success_rate, n_per_cell)
    _write_log(success_rate, n_per_cell, elapsed, cache_ratio, mono_K_ok, mono_snr_ok, mono_imu_ok)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def make_reachability_figure(success_rate: np.ndarray, n_per_cell: np.ndarray):
    """Three-panel figure: one panel per regime, success rate vs K with
    curves parametrised by (SNR, IMU σ).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
        from _plot_style import apply_monograph_style, fig_size_ieee
        apply_monograph_style(mode="png")
        figsize = fig_size_ieee(columns=2, aspect=0.36)
    except Exception:
        try:
            import scienceplots  # noqa: F401
            plt.style.use(["science", "ieee"])
        except Exception:
            pass
        figsize = (7.16, 2.58)

    n_regimes, n_K, n_snr, n_imu = success_rate.shape
    K_x = np.array(K_GRID)
    regime_titles = [
        "Far (30 m, $h$=8 m)",
        "Mid (10 m, $h$=5 m)",
        "Close (5 m, $h$=3 m)",
    ]
    fig, axes = plt.subplots(1, n_regimes, figsize=figsize, sharey=True)
    if n_regimes == 1:
        axes = [axes]

    snr_styles = ["-", "--", ":"]
    imu_colors = ["#1f77b4", "#ff7f0e", "#d62728"]
    snr_labels = [f"SNR={int(s)} dB" for s in SNR_GRID_DB]
    imu_labels = [f"$\\sigma$={s:.0f}$^\\circ$" for s in IMU_SIGMA_GRID_DEG]

    for r in range(n_regimes):
        ax = axes[r]
        for si in range(n_snr):
            for ii in range(n_imu):
                lab = f"{snr_labels[si]}, {imu_labels[ii]}"
                ax.plot(
                    K_x,
                    success_rate[r, :, si, ii] * 100.0,
                    snr_styles[si],
                    color=imu_colors[ii],
                    marker="o",
                    markersize=3,
                    linewidth=1.0,
                    label=lab if r == 0 else None,
                )
        ax.set_xlabel("Iterations $K$")
        ax.set_xscale("log")
        ax.set_xticks(K_x)
        ax.set_xticklabels([str(k) for k in K_x])
        ax.set_title(regime_titles[r], fontsize=8)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        n_cell = int(n_per_cell[r, 0, 0])
        ax.text(
            0.97, 0.05, f"$n={n_cell}$",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6
        )
    axes[0].set_ylabel("Success rate (\\%)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=3,
        fontsize=5,
        bbox_to_anchor=(0.5, -0.08),
        frameon=True,
    )
    fig.suptitle(
        f"Reachability: success = within {SUCCESS_TOL_DB:.0f} dB of brute-force optimum",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    pdf_path = OUT_DIR / "fig_reachability.pdf"
    png_path = OUT_DIR / "fig_reachability.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {pdf_path}")
    print(f"  wrote {png_path}")


# ---------------------------------------------------------------------------
# Agent log
# ---------------------------------------------------------------------------
def _write_log(
    success_rate, n_per_cell, elapsed, cache_ratio, mono_K_ok, mono_snr_ok, mono_imu_ok
):
    K_idx_20 = list(K_GRID).index(20)
    K_idx_2 = list(K_GRID).index(2)
    snr_idx_40 = list(SNR_GRID_DB).index(40.0)
    snr_idx_10 = list(SNR_GRID_DB).index(10.0)
    imu_idx_0 = list(IMU_SIGMA_GRID_DEG).index(0.0)
    imu_idx_8 = list(IMU_SIGMA_GRID_DEG).index(8.0)

    lines = [
        "# Reachability Sweep Agent Log\n",
        f"elapsed: {elapsed:.1f} s\n",
        f"cache_hit_rate: {cache_ratio:.1%}\n",
        f"n_scenes_per_regime: {N_SCENES_PER_REGIME}\n",
        f"K_MAX={K_MAX}, TIER_B_K={TIER_B_K}\n\n",
    ]
    for r, (_, rname) in enumerate(BS_REGIMES):
        n_cell = int(n_per_cell[r, 0, 0])
        lines.append(f"## Regime: {rname}  (n={n_cell})\n\n")
        lines.append("| K | SNR (dB) | IMU=0° | IMU=4° | IMU=8° |\n")
        lines.append("|---|----------|--------|--------|--------|\n")
        for ki, K in enumerate(K_GRID):
            for si, snr_db in enumerate(SNR_GRID_DB):
                row = " | ".join(
                    f"{success_rate[r, ki, si, ii]*100:.1f}%"
                    for ii in range(len(IMU_SIGMA_GRID_DEG))
                )
                lines.append(f"| {K} | {int(snr_db)} | {row} |\n")
        lines.append("\n")

    lines.append("## Monotonicity checks\n\n")
    lines.append(f"- Monotone in K: {mono_K_ok}\n")
    lines.append(f"- Monotone in SNR: {mono_snr_ok}\n")
    lines.append(f"- Monotone in IMU sigma: {mono_imu_ok}\n\n")

    lines.append("## Corner cases\n\n")
    lines.append("| regime | K=20,SNR=40,IMU=0° | K=2,SNR=10,IMU=8° |\n")
    lines.append("|--------|---------------------|--------------------|\n")
    for r, (_, rname) in enumerate(BS_REGIMES):
        v_easy = success_rate[r, K_idx_20, snr_idx_40, imu_idx_0] * 100
        v_hard = success_rate[r, K_idx_2, snr_idx_10, imu_idx_8] * 100
        lines.append(f"| {rname} | {v_easy:.1f}% (expect >90%) | {v_hard:.1f}% (expect <30%) |\n")

    lines.append("\n## Compute optimisations\n\n")
    lines.append(
        "- One scene-level worker processes all 9 (SNR,IMU) cells sharing a PoseCache.\n"
    )
    lines.append(
        "- PoseCache keys on delta_deg rounded to 0.1°, avoiding redundant SMPL-X calls.\n"
    )
    lines.append(f"- Final cache hit rate: {cache_ratio:.1%}.\n")

    LOG_PATH.write_text("".join(lines), encoding="utf-8")
    print(f"  wrote {LOG_PATH}")


if __name__ == "__main__":
    main()

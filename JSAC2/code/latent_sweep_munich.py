"""Munich-scene VPoser-latent sweep (replaces the synthetic free-space
3-regime parametric sweep of latent_sweep.py).

For each of the 16 Munich scenes (8 LOS + 8 NLOS, traced via Sionna RT
in JSAC2/code/scenes/munich_trace.py), run:
  - Existence: random sampling within the comfort ball, report max gain.
  - Reachability: K-iteration projected latent gradient ascent (FD).

Outputs:
  outputs/munich_existence.npz
  outputs/fig_munich_existence.{pdf,png}
  outputs/fig_munich_reachability.{pdf,png}
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

from JSAC2.code.kirchhoff import BSPathDict, kirchhoff_h_body, mrt_sinr_db
from JSAC2.code.kirchhoff_jax import kirchhoff_h_body_jax

# Toggle JAX/GPU vs reference NumPy kirchhoff via env var.
USE_JAX_KIRCHHOFF = os.environ.get("KIRCHHOFF_BACKEND", "jax").lower() == "jax"
from JSAC2.code.scene_nlos import BSArray
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.vposer_v2 import VPoser, LATENT_D
from aegis.geometry.pose_stream import PoseStream

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
RHO_Z = 1.5
TARGET_GAINS_DB = (3.0, 6.0, 10.0)
N_EXISTENCE_SAMPLES = 24
K_GRID = (2, 5, 8)
K_MAX = max(K_GRID)
N_DIR_PER_ITER = int(os.environ.get("LATENT_N_DIR", "6"))
SUCCESS_TOL_DB = 1.0
P_TX_DBM = 43.0
NOISE_DBM = -94.0

TRACE_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich/traces")
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")
F_C = 28e9


# ---------------------------------------------------------------------------
# VPoser
# ---------------------------------------------------------------------------
_VPOSER = None


def _vposer():
    global _VPOSER
    if _VPOSER is None:
        _VPOSER = VPoser.from_checkpoint()
        _VPOSER.eval()
    return _VPOSER


def decode_z(z: np.ndarray) -> np.ndarray:
    vp = _vposer()
    with torch.no_grad():
        body = vp.decode(torch.tensor(z, dtype=torch.float32).unsqueeze(0))
    pose22 = np.zeros((22, 3), dtype=np.float64)
    pose22[1:] = body[0].numpy()
    return pose22


def encode_pose(theta22: np.ndarray) -> np.ndarray:
    vp = _vposer()
    body = theta22[1:].astype(np.float32)
    with torch.no_grad():
        z = vp.encode(torch.tensor(body).unsqueeze(0))
    return z[0].numpy().astype(np.float64)


# ---------------------------------------------------------------------------
# Munich scene loader
# ---------------------------------------------------------------------------
def load_munich_scene(scene_idx: int):
    """Load a cached Sionna-traced Munich scene.

    Returns: (bs_array, h_scene, r_phone, body_paths, body_centroid,
             face_azimuth_rad, los_flag, label, scene_loss_db_phone)
    """
    npz = np.load(TRACE_DIR / f"scene_{scene_idx:02d}.npz", allow_pickle=False)
    bs_pos = npz["bs_pos"]
    bs_positions_cached = np.asarray(npz["bs_positions"])
    # Recover panel orientation from cached element layout (panel lies in
    # a plane orthogonal to `normal`). Build a BSArray with this normal
    # and overwrite `.positions` from cache to guarantee bit-identical
    # geometry to what was used during Sionna tracing.
    rel = bs_positions_cached - bs_pos[None, :]
    _, _, vh = np.linalg.svd(rel, full_matrices=False)
    normal = vh[-1]
    bs_array = BSArray(n_x=8, n_y=8, center=bs_pos, normal=normal, f_c=F_C)
    bs_array.positions = bs_positions_cached
    bs_array.boresight = normal
    h_scene = npz["h_scene"]
    r_phone = npz["phone_xyz"]
    body_centroid = npz["body_centroid"]
    face_azimuth_rad = float(npz["face_azimuth_rad"])
    body_paths = BSPathDict(
        j_idx=npz["body_j_idx"],
        k_hat=npz["body_k_hat"],
        psi=npz["body_psi"],
        amp=npz["body_amp"],
    )
    los_flag = str(npz["los_flag"]) if npz["los_flag"].ndim == 0 \
                else str(npz["los_flag"].item())
    label = str(npz["label"]) if npz["label"].ndim == 0 \
                else str(npz["label"].item())
    # Approximate scene-loss (for diagnostics): 20*log10(sum |h_scene|)
    h_scene_dB = float(20 * np.log10(np.abs(h_scene).sum() + 1e-30))
    return (bs_array, h_scene, r_phone, body_paths, body_centroid,
            face_azimuth_rad, los_flag, label, h_scene_dB)


def list_scenes():
    return sorted([int(p.stem.split("_")[1])
                   for p in TRACE_DIR.glob("scene_*.npz")])


# ---------------------------------------------------------------------------
# Per-scene rate function (Munich-specialised)
# ---------------------------------------------------------------------------
def rate_at_z_munich(
    z: np.ndarray, bs: BSArray, h_scene: np.ndarray, r_phone: np.ndarray,
    body_paths: BSPathDict, body_centroid: np.ndarray, face_azimuth_rad: float,
) -> tuple[float, float]:
    pose22 = decode_z(z)
    body = make_body_smplx(pose22, body_centroid,
                            face_azimuth_rad=face_azimuth_rad)
    if USE_JAX_KIRCHHOFF:
        h_body = kirchhoff_h_body_jax(body, body_paths, r_phone, M=bs.M)
    else:
        h_body, _ = kirchhoff_h_body(body, body_paths, r_phone, M=bs.M)
    h_cas = h_scene + h_body
    sinr_db = mrt_sinr_db(h_cas, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM)
    rate_bps_hz = float(np.log2(1.0 + 10 ** (sinr_db / 10)))
    return sinr_db, rate_bps_hz


# ---------------------------------------------------------------------------
# Existence + reachability (mirror of latent_sweep.py)
# ---------------------------------------------------------------------------
def existence_at_scene(z0, bs, h_scene, r_phone, body_paths, body_centroid,
                        face_azimuth_rad, n_samples, rng):
    sinr0, _ = rate_at_z_munich(z0, bs, h_scene, r_phone, body_paths,
                                 body_centroid, face_azimuth_rad)
    sinr_samples = np.zeros(n_samples)
    best = sinr0
    for i in range(n_samples):
        d = rng.standard_normal(LATENT_D)
        d /= np.linalg.norm(d)
        r = RHO_Z * rng.random() ** (1.0 / LATENT_D)
        z = z0 + r * d
        s, _ = rate_at_z_munich(z, bs, h_scene, r_phone, body_paths,
                                 body_centroid, face_azimuth_rad)
        sinr_samples[i] = s
        best = max(best, s)
    return sinr0, best, sinr_samples


def latent_gradient_ascent(z0, bs, h_scene, r_phone, body_paths, body_centroid,
                            face_azimuth_rad, n_iter, eta=0.4, fd_eps=0.08,
                            n_dir_per_iter=8, seed_base=0):
    z = z0.copy()
    z0_anchor = z0.copy()
    sinr_traj = np.zeros(n_iter + 1)
    sinr0, _ = rate_at_z_munich(z, bs, h_scene, r_phone, body_paths,
                                 body_centroid, face_azimuth_rad)
    sinr_traj[0] = sinr0
    best_sinr = sinr0
    best_z = z.copy()
    rng = np.random.default_rng(seed_base)
    for k in range(n_iter):
        g_est = np.zeros(LATENT_D)
        for _ in range(n_dir_per_iter):
            d = rng.standard_normal(LATENT_D)
            d /= np.linalg.norm(d)
            s_p, _ = rate_at_z_munich(z + fd_eps * d, bs, h_scene, r_phone,
                                       body_paths, body_centroid,
                                       face_azimuth_rad)
            s_m, _ = rate_at_z_munich(z - fd_eps * d, bs, h_scene, r_phone,
                                       body_paths, body_centroid,
                                       face_azimuth_rad)
            g_est += ((s_p - s_m) / (2.0 * fd_eps)) * d
        g_est /= n_dir_per_iter
        g_norm = np.linalg.norm(g_est)
        if g_norm < 1e-6:
            sinr_traj[k + 1] = sinr_traj[k]
            continue
        z_new = z + eta * g_est / g_norm
        r_new = z_new - z0_anchor
        if np.linalg.norm(r_new) > RHO_Z:
            z_new = z0_anchor + r_new * (RHO_Z / np.linalg.norm(r_new))
        sinr_new, _ = rate_at_z_munich(z_new, bs, h_scene, r_phone,
                                         body_paths, body_centroid,
                                         face_azimuth_rad)
        if sinr_new > sinr_traj[k] - 0.5:
            z = z_new
        else:
            z = best_z.copy()
            eta *= 0.7
        if sinr_new > best_sinr:
            best_sinr = sinr_new
            best_z = z_new.copy()
        sinr_traj[k + 1] = sinr_new
    return np.maximum.accumulate(sinr_traj), best_z


# ---------------------------------------------------------------------------
# Per-scene worker
# ---------------------------------------------------------------------------
def run_scene(args):
    (scene_idx, baseline_pose22, seed) = args
    rng = np.random.default_rng(seed)
    (bs, h_scene, r_phone, body_paths, body_centroid, face_azimuth_rad,
     los_flag, label, h_scene_dB) = load_munich_scene(scene_idx)
    z0 = encode_pose(baseline_pose22)
    sinr0, best_sinr, sinr_samples = existence_at_scene(
        z0, bs, h_scene, r_phone, body_paths, body_centroid,
        face_azimuth_rad, N_EXISTENCE_SAMPLES, rng,
    )
    sinr_traj, _ = latent_gradient_ascent(
        z0, bs, h_scene, r_phone, body_paths, body_centroid,
        face_azimuth_rad, K_MAX, seed_base=seed,
        n_dir_per_iter=N_DIR_PER_ITER,
    )
    return {
        "scene_idx": scene_idx, "los_flag": los_flag, "label": label,
        "h_scene_dB": h_scene_dB,
        "sinr_baseline_db": sinr0,
        "sinr_existence_max_db": best_sinr,
        "sinr_samples": sinr_samples,
        "sinr_traj": sinr_traj,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    walks = sorted(PLAZA_DIR.rglob("*.npz"))
    pose_pool = []
    for w in walks[:60]:
        ps = PoseStream.load(w)
        for f in range(0, len(ps.poses), 30):
            poses = ps.poses[f, :66].reshape(22, 3).copy()
            poses[0] = 0.0
            pose_pool.append(poses)
    pose_pool = np.array(pose_pool)
    print(f"  pose pool: {len(pose_pool)} frames")

    scene_ids = list_scenes()
    job_args = [(s, pose_pool[rng.integers(0, len(pose_pool))], SEED + s)
                for s in scene_ids]
    print(f"  total {len(scene_ids)} Munich scenes, "
          f"{N_EXISTENCE_SAMPLES} existence, K_MAX={K_MAX}")
    backend = "JAX/GPU" if USE_JAX_KIRCHHOFF else "NumPy/CPU"
    if USE_JAX_KIRCHHOFF:
        print(f"  serial run, kirchhoff backend = {backend}")
        t0 = time.time()
        results = []
        for i, args in enumerate(job_args):
            r = run_scene(args)
            results.append(r)
            print(f"    [{i+1:2d}/{len(job_args)}] scene {r['scene_idx']:2d} "
                  f"[{r['los_flag']}] base={r['sinr_baseline_db']:+5.1f} dB, "
                  f"max={r['sinr_existence_max_db']:+5.1f} dB, "
                  f"gain={r['sinr_existence_max_db']-r['sinr_baseline_db']:+4.1f} dB, "
                  f"t={time.time() - t0:.0f}s")
    else:
        n_workers = min(os.cpu_count() or 4, 12)
        print(f"  running on {n_workers} workers ({backend}) ...")
        t0 = time.time()
        results = []
        with mp.Pool(processes=n_workers) as pool:
            for i, r in enumerate(pool.imap_unordered(run_scene, job_args)):
                results.append(r)
                print(f"    scene {r['scene_idx']:2d} [{r['los_flag']}] "
                      f"base={r['sinr_baseline_db']:+5.1f} dB, "
                      f"max={r['sinr_existence_max_db']:+5.1f} dB, "
                      f"gain={r['sinr_existence_max_db']-r['sinr_baseline_db']:+4.1f} dB")
    print(f"  finished in {time.time() - t0:.1f}s")

    results.sort(key=lambda r: r["scene_idx"])
    los_flag_arr = np.array([r["los_flag"] for r in results])
    sinr_baseline = np.array([r["sinr_baseline_db"] for r in results])
    sinr_existence_max = np.array([r["sinr_existence_max_db"] for r in results])
    sinr_samples = np.array([r["sinr_samples"] for r in results])
    sinr_traj = np.array([r["sinr_traj"] for r in results])
    h_scene_dB = np.array([r["h_scene_dB"] for r in results])

    out_path = OUT_DIR / "munich_existence.npz"
    np.savez(out_path,
             los_flag=los_flag_arr,
             sinr_baseline=sinr_baseline,
             sinr_existence_max=sinr_existence_max,
             sinr_samples=sinr_samples,
             sinr_traj=sinr_traj,
             h_scene_dB=h_scene_dB,
             target_gains_db=np.array(TARGET_GAINS_DB),
             rho_z=RHO_Z,
             n_existence_samples=N_EXISTENCE_SAMPLES,
             K_grid=np.array(K_GRID),
             K_max=K_MAX,
             success_tol_db=SUCCESS_TOL_DB,
             seed=SEED)
    print(f"  wrote {out_path}")

    print("\n  Existence fractions (LOS / NLOS x target gain):")
    print(f"    {'flag':<6}" + "".join(f"{g:>8.0f} dB" for g in TARGET_GAINS_DB))
    for flag in ("LOS", "NLOS"):
        m = los_flag_arr == flag
        if not m.any():
            continue
        gains = sinr_existence_max[m] - sinr_baseline[m]
        row = f"    {flag:<6}"
        for g in TARGET_GAINS_DB:
            row += f"  {(gains >= g).mean()*100:>5.0f}%"
        row += f"  (n={m.sum()})"
        print(row)

    sinr_terminal = sinr_traj[:, -1]
    reach = sinr_terminal >= sinr_existence_max - SUCCESS_TOL_DB
    print(f"\n  Reachability (terminal within {SUCCESS_TOL_DB:.0f} dB):")
    for flag in ("LOS", "NLOS"):
        m = los_flag_arr == flag
        if not m.any():
            continue
        print(f"    {flag:<6}  {reach[m].mean()*100:>5.0f}% (n={m.sum()})")


if __name__ == "__main__":
    main()

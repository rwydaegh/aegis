"""Munich latent sweep — pure JAX/GPU, autodiff pose gradient.

End-to-end differentiable z -> SINR via VPoser + SMPL-X + Kirchhoff in JAX.
Replaces SPSA central-difference gradient (12 evals/iter) with one true
autodiff backward (cost ~ 1 forward) per gradient step.

Outputs the same NPZ schema as latent_sweep_munich.py so plot_munich.py
and fig_hero_munich.py work unchanged.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import jax
import jax.numpy as jnp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.pose_pipeline_jax import (
    load_smplx_jax, load_vposer_jax, make_sinr_fn, _n_complex,
    LATENT_D, vposer_decode_jax,
)
from JSAC2.code.scene_nlos import BSArray
from JSAC2.code.vposer_v2 import VPoser
from aegis.geometry.pose_stream import PoseStream
import torch

jax.config.update("jax_enable_x64", True)

# ---------------------------------------------------------------------------
# Configuration (mirror of latent_sweep_munich.py)
# ---------------------------------------------------------------------------
SEED = 42
# Comfort = naturalness only: ||z|| <= RHO_NATURAL anchored at the
# VPoser prior origin, NOT a small ball around z_0. A yoga split is
# anatomically possible but rare in AMASS so VPoser pushes it to large
# ||z||; bounding ||z|| <= 2 keeps the optimisation inside the
# 2-nat naturalness contour while allowing any pose VPoser considers
# typical. z_0 still represents the user's current AMASS-walking pose
# but is no longer a constraint anchor; only the gain delta is measured
# relative to it.
RHO_NATURAL = 2.0
RHO_Z = RHO_NATURAL  # legacy alias kept for downstream npz
TARGET_GAINS_DB = (3.0, 6.0, 10.0)
N_EXISTENCE_SAMPLES = 100
K_GRID = (2, 5, 10, 15, 20)
K_MAX = max(K_GRID)
SUCCESS_TOL_DB = 1.0
P_TX_DBM = 43.0
NOISE_DBM = -94.0
F_C = 28e9

TRACE_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich/traces")
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def list_scenes():
    return sorted([int(p.stem.split("_")[1])
                    for p in TRACE_DIR.glob("scene_*.npz")])


def encode_pose_to_z(theta22: np.ndarray, vp_torch: VPoser) -> np.ndarray:
    """VPoser encode (PyTorch, run once at scene start, no grad needed)."""
    body = theta22[1:].astype(np.float32)
    with torch.no_grad():
        z = vp_torch.encode(torch.tensor(body).unsqueeze(0))
    return z[0].numpy().astype(np.float64)


def build_sinr_for_scene(scene_idx, sm, vw, betas):
    """Build a JIT-compiled sinr(z) for one Munich scene."""
    npz = np.load(TRACE_DIR / f"scene_{scene_idx:02d}.npz", allow_pickle=False)
    bs_pos = jnp.asarray(npz["bs_pos"], jnp.float64)
    bs_positions = jnp.asarray(npz["bs_positions"], jnp.float64)
    body_centroid = npz["body_centroid"]
    face_az = float(npz["face_azimuth_rad"])
    r_phone = npz["phone_xyz"]
    h_scene = npz["h_scene"]
    los_flag = str(npz["los_flag"]) if npz["los_flag"].ndim == 0 \
                                    else str(npz["los_flag"].item())
    label = str(npz["label"]) if npz["label"].ndim == 0 \
                                else str(npz["label"].item())
    n_tilde = jnp.complex128(_n_complex(16.5, 25.8, F_C))
    k0 = float(2.0 * np.pi * F_C / 2.99792458e8)
    sinr_fn = make_sinr_fn(
        sm, vw, betas, body_centroid, face_az, r_phone, h_scene,
        jnp.asarray(npz["body_k_dod"],    jnp.float64),
        jnp.asarray(npz["body_k_doa"],    jnp.float64),
        jnp.asarray(npz["body_psi_path"], jnp.complex128),
        jnp.asarray(npz["body_amp_path"], jnp.complex128),
        bs_positions, bs_pos, n_tilde, k0,
        float(P_TX_DBM), float(NOISE_DBM),
    )
    h_scene_dB = float(20 * np.log10(np.abs(h_scene).sum() + 1e-30))
    return sinr_fn, los_flag, label, h_scene_dB


def existence_at_scene(z0, sinr_fn, n_samples, rng):
    """Random sampling within the global naturalness ball ||z|| <= RHO_NATURAL,
    NOT a ball around z_0. Returns (baseline SINR at z_0, max SINR found,
    per-sample SINR vector)."""
    sinr0 = float(sinr_fn(jnp.asarray(z0)))
    sinr_samples = np.zeros(n_samples)
    best = sinr0
    for i in range(n_samples):
        d = rng.standard_normal(LATENT_D)
        d /= np.linalg.norm(d)
        r = RHO_NATURAL * rng.random() ** (1.0 / LATENT_D)
        z = r * d  # anchored at origin, not at z_0
        s = float(sinr_fn(jnp.asarray(z)))
        sinr_samples[i] = s
        best = max(best, s)
    return sinr0, best, sinr_samples


def projected_grad_ascent(z0, sinr_fn, grad_fn, n_iter, eta=0.4):
    """True-gradient projected ascent on the SINR surface, projecting
    onto the global naturalness ball ||z|| <= RHO_NATURAL (not a ball
    around z_0). Step in normalised-gradient direction; if a step does
    not improve SINR by more than 0.5 dB, fall back to best-z and halve
    eta."""
    z = z0.copy()
    sinr_traj = np.zeros(n_iter + 1)
    sinr0 = float(sinr_fn(jnp.asarray(z)))
    sinr_traj[0] = sinr0
    best_sinr = sinr0
    best_z = z.copy()
    for k in range(n_iter):
        g = np.asarray(grad_fn(jnp.asarray(z)))
        gn = float(np.linalg.norm(g))
        if gn < 1e-6:
            sinr_traj[k + 1] = sinr_traj[k]
            continue
        z_new = z + eta * g / gn
        zn = float(np.linalg.norm(z_new))
        if zn > RHO_NATURAL:
            z_new = z_new * (RHO_NATURAL / zn)
        s_new = float(sinr_fn(jnp.asarray(z_new)))
        if s_new > sinr_traj[k] - 0.5:
            z = z_new
        else:
            z = best_z.copy()
            eta *= 0.7
        if s_new > best_sinr:
            best_sinr = s_new
            best_z = z_new.copy()
        sinr_traj[k + 1] = s_new
    return np.maximum.accumulate(sinr_traj), best_z


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading SMPL-X + VPoser ...")
    sm = load_smplx_jax()
    vw = load_vposer_jax()
    betas = jnp.zeros(10, dtype=jnp.float64)
    vp_torch = VPoser.from_checkpoint()

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
    print(f"  total {len(scene_ids)} Munich scenes, {N_EXISTENCE_SAMPLES} "
          f"existence, K_MAX={K_MAX}")
    print(f"  backend: JAX/GPU, autodiff gradient")

    t0 = time.time()
    results = []
    for i, scene_idx in enumerate(scene_ids):
        baseline_pose22 = pose_pool[rng.integers(0, len(pose_pool))]
        seed_scene = SEED + scene_idx
        rng_scene = np.random.default_rng(seed_scene)
        sinr_fn, los_flag, label, h_scene_dB = build_sinr_for_scene(
            scene_idx, sm, vw, betas
        )
        grad_fn = jax.jit(jax.grad(sinr_fn))
        z0 = encode_pose_to_z(baseline_pose22, vp_torch)
        # Warm up JIT for this scene's path-count signature
        _ = float(sinr_fn(jnp.asarray(z0))); _ = grad_fn(jnp.asarray(z0))
        jax.block_until_ready(_)
        sinr0, best_sinr, sinr_samples = existence_at_scene(
            z0, sinr_fn, N_EXISTENCE_SAMPLES, rng_scene,
        )
        sinr_traj, _ = projected_grad_ascent(
            z0, sinr_fn, grad_fn, K_MAX,
        )
        results.append({
            "scene_idx": scene_idx, "los_flag": los_flag, "label": label,
            "h_scene_dB": h_scene_dB,
            "sinr_baseline_db": sinr0,
            "sinr_existence_max_db": best_sinr,
            "sinr_samples": sinr_samples,
            "sinr_traj": sinr_traj,
        })
        gain = best_sinr - sinr0
        print(f"    [{i+1:2d}/{len(scene_ids)}] scene {scene_idx:2d} "
              f"[{los_flag:4s}] base={sinr0:+5.1f} dB, "
              f"max={best_sinr:+5.1f} dB, gain={gain:+4.1f} dB, "
              f"reach={sinr_traj[-1]:+5.1f} dB, t={time.time()-t0:.0f}s")

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
        if not m.any(): continue
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
        if not m.any(): continue
        print(f"    {flag:<6}  {reach[m].mean()*100:>5.0f}% (n={m.sum()})")


if __name__ == "__main__":
    main()

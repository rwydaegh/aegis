"""Parity + speed + autodiff test: JAX pose pipeline vs PyTorch+NumPy reference."""
import sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import jax
import jax.numpy as jnp

from JSAC2.code.pose_pipeline_jax import (
    load_smplx_jax, load_vposer_jax, vposer_decode_jax, smplx_lbs_jax,
    world_verts, tri_centroids_normals_areas, _n_complex,
    make_sinr_fn, LATENT_D,
)
from JSAC2.code.latent_sweep_munich import (
    load_munich_scene, decode_z, rate_at_z_munich,
    P_TX_DBM, NOISE_DBM, F_C,
)
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.kirchhoff import kirchhoff_h_body

print("JAX backend:", jax.default_backend(), "devices:", jax.devices())
print()

# ---------- Setup ------------
sm = load_smplx_jax()
vw = load_vposer_jax()
betas = jnp.zeros(10, dtype=jnp.float64)

(bs, h_scene, r_phone, body_paths, body_centroid, face_az,
 flag, name, _) = load_munich_scene(0)
print(f"Scene 0: {flag} {name}")

# A few z to test (deterministic from seed)
rng = np.random.default_rng(0)
z_baseline = jnp.zeros(LATENT_D)  # mean pose
z_random   = jnp.asarray(rng.standard_normal(LATENT_D) * 0.5, dtype=jnp.float64)


# ---------- Step 1: VPoser decode parity ----------
print("\n--- Step 1: VPoser decoder ---")
import torch
from JSAC2.code.vposer_v2 import VPoser
torch_vp = VPoser.from_checkpoint()
torch_vp.eval()
for label, z in [("z=0", z_baseline), ("z_random", z_random)]:
    aa_jax = vposer_decode_jax(z, vw)
    with torch.no_grad():
        aa_torch = torch_vp.decode(torch.tensor(np.asarray(z), dtype=torch.float32).unsqueeze(0))
    aa_torch_np = aa_torch[0].numpy().astype(np.float64)
    err = np.abs(np.asarray(aa_jax) - aa_torch_np).max()
    print(f"  {label:10s}  max axis-angle error = {err:.3e} rad")


# ---------- Step 2: SMPL-X LBS parity ----------
print("\n--- Step 2: SMPL-X LBS ---")
for label, z in [("z=0", z_baseline)]:
    aa_jax = vposer_decode_jax(z, vw)
    aa_np = np.asarray(aa_jax)
    pose22 = np.zeros((22, 3))
    pose22[1:] = aa_np
    body_ref = make_body_smplx(pose22, np.asarray(body_centroid),
                                face_azimuth_rad=float(face_az))
    verts_ref = np.asarray(body_ref.mesh.vertices)

    theta22 = jnp.zeros((22, 3))
    theta22 = theta22.at[1:].set(aa_jax)
    verts_local = smplx_lbs_jax(theta22, betas, sm)
    verts_w = world_verts(verts_local, body_centroid, face_az, sm["faces"])
    verts_jax = np.asarray(verts_w)

    err = np.abs(verts_jax - verts_ref).max()
    median = np.median(np.abs(verts_jax - verts_ref))
    print(f"  {label}: max vert err = {err*1000:.3f} mm, median = {median*1000:.4f} mm")


# ---------- Step 3: end-to-end SINR + speed ----------
print("\n--- Step 3: end-to-end SINR ---")
n_tilde = jnp.complex128(_n_complex(16.5, 25.8, F_C))
k0 = float(2.0 * np.pi * F_C / 2.99792458e8)

# Load Sionna-native per-path arrays for the autodiff path
import numpy as _np
_d = _np.load(f"/home/user/aegis/JSAC2/code/outputs/munich/traces/scene_00.npz",
              allow_pickle=False)
sinr_fn = make_sinr_fn(
    sm, vw, betas, body_centroid, face_az, r_phone, h_scene,
    jnp.asarray(_d["body_k_dod"],     jnp.float64),
    jnp.asarray(_d["body_k_doa"],     jnp.float64),
    jnp.asarray(_d["body_psi_path"],  jnp.complex128),
    jnp.asarray(_d["body_amp_path"],  jnp.complex128),
    jnp.asarray(bs.positions,         jnp.float64),
    jnp.asarray(_d["bs_pos"],         jnp.float64),
    n_tilde, k0, float(P_TX_DBM), float(NOISE_DBM),
)
print(f"  P_sionna = {_d['body_k_dod'].shape[0]}")

# warm-up (compile)
t0 = time.perf_counter()
s_jax = float(sinr_fn(z_baseline)); jax.block_until_ready(s_jax)
print(f"  JIT compile + first call: {(time.perf_counter()-t0)*1000:.0f} ms")

# hot calls
times = []
for _ in range(5):
    t0 = time.perf_counter()
    s_jax = float(sinr_fn(z_baseline)); jax.block_until_ready(s_jax)
    times.append(time.perf_counter() - t0)
print(f"  JAX hot eval: {np.mean(times)*1000:.1f} ms (median {np.median(times)*1000:.1f} ms)")

# reference
t0 = time.perf_counter()
s_ref, _ = rate_at_z_munich(np.asarray(z_baseline), bs, np.asarray(h_scene),
                              np.asarray(r_phone), body_paths,
                              np.asarray(body_centroid), float(face_az))
t_ref = time.perf_counter() - t0
print(f"  Reference (PyTorch+JAX_kirchhoff): {t_ref*1000:.0f} ms")
print(f"  SINR jax = {s_jax:+.3f} dB,  ref = {s_ref:+.3f} dB,  delta = {s_jax-s_ref:+.3f} dB")


# ---------- Step 4: gradient ----------
print("\n--- Step 4: autodiff gradient dSINR/dz ---")
grad_fn = jax.jit(jax.grad(sinr_fn))
t0 = time.perf_counter(); g = np.asarray(grad_fn(z_baseline)); jax.block_until_ready(g)
print(f"  JIT compile + first grad: {(time.perf_counter()-t0)*1000:.0f} ms")
times = []
for _ in range(5):
    t0 = time.perf_counter()
    g = np.asarray(grad_fn(z_baseline)); jax.block_until_ready(g)
    times.append(time.perf_counter() - t0)
print(f"  JAX hot grad: {np.mean(times)*1000:.1f} ms")
print(f"  ||grad||_2 = {np.linalg.norm(g):.3e}, max |gj| = {np.abs(g).max():.3e}")

# Sanity: finite-diff cross-check on a few coords
print("\n  Finite-diff cross-check (eps=1e-3 on 3 random coords):")
eps = 1e-3
for i in [0, 5, 17]:
    zp = z_baseline.at[i].set(z_baseline[i] + eps)
    zm = z_baseline.at[i].set(z_baseline[i] - eps)
    fd = (float(sinr_fn(zp)) - float(sinr_fn(zm))) / (2 * eps)
    print(f"    z[{i:2d}]: autodiff = {g[i]:+.4f}, FD = {fd:+.4f}, "
          f"err = {abs(g[i]-fd):.2e}")

"""End-to-end JAX/GPU body channel pipeline for autodiff pose-search.

Composes (all on GPU, all differentiable):

    z (R^32)
       --> vposer_decode_jax  --> body_aa (21, 3)
       --> smplx_lbs_jax       --> verts (10475, 3) in SMPL-X frame
       --> world_transform     --> verts in world frame at body_centroid
       --> tri_props_jax       --> centroids, normals, areas, facing-vis
       --> kirchhoff_jax       --> h_body (M,) complex
       --> sinr_db_jax         --> scalar dB

`jax.grad(sinr)(z)` returns a true 32-D analytic gradient, replacing the
SPSA random-direction central differences in latent_sweep_munich.

Numerical reference: every step is parity-tested against the existing
PyTorch (vposer + smplx) + NumPy (kirchhoff) chain to <1e-3 relative.
"""
from __future__ import annotations

from functools import partial
from pathlib import Path

import numpy as np
import jax
import jax.numpy as jnp

jax.config.update("jax_enable_x64", True)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
LATENT_D = 32
NUM_BODY_JOINTS = 21
NUM_TOTAL_JOINTS = 55  # SMPL-X: 1 (root) + 21 (body) + 1 (jaw) + 2 (eyes)
                       #         + 15 (Lhand) + 15 (Rhand) = 55
SMPLX_TENSORS_NPZ = Path("/home/user/aegis/JSAC2/code/smplx_neutral_tensors.npz")
VPOSER_CKPT = Path(
    "/home/user/aegis/data/vposer/V02_05/snapshots/V02_05_epoch=13_val_loss=0.03.ckpt"
)


# -----------------------------------------------------------------------------
# Weight loaders (Python-side; converts torch checkpoint -> jnp once at start)
# -----------------------------------------------------------------------------
def load_smplx_jax():
    """Load SMPL-X tensors as a tuple of jnp arrays (cached on GPU)."""
    d = np.load(SMPLX_TENSORS_NPZ, allow_pickle=False)
    return {
        "v_template":  jnp.asarray(d["v_template"],  jnp.float64),
        "shapedirs":   jnp.asarray(d["shapedirs"],   jnp.float64),
        "posedirs":    jnp.asarray(d["posedirs"],    jnp.float64),
        "J_regressor": jnp.asarray(d["J_regressor"], jnp.float64),
        "parents":     jnp.asarray(d["parents"],     jnp.int32),
        "lbs_weights": jnp.asarray(d["lbs_weights"], jnp.float64),
        "faces":       np.asarray(d["faces"],        np.int64),
    }


def load_vposer_jax():
    """Load VPoser v2.0 decoder weights from PyTorch ckpt as jnp arrays."""
    import torch
    sd = torch.load(VPOSER_CKPT, map_location="cpu", weights_only=False)["state_dict"]
    def t(k): return jnp.asarray(sd[k].cpu().numpy(), jnp.float64)
    return {
        "fc1_w": t("vp_model.decoder_net.0.weight"),
        "fc1_b": t("vp_model.decoder_net.0.bias"),
        "fc2_w": t("vp_model.decoder_net.3.weight"),
        "fc2_b": t("vp_model.decoder_net.3.bias"),
        "out_w": t("vp_model.decoder_net.5.weight"),
        "out_b": t("vp_model.decoder_net.5.bias"),
    }


# -----------------------------------------------------------------------------
# VPoser decoder in JAX (axis-angle output)
# -----------------------------------------------------------------------------
def _leaky_relu(x, slope=0.2):
    return jnp.where(x > 0, x, slope * x)


def _continuous_rot_to_matrix(d6):
    """(..., 6) Zhou et al. continuous rotation -> (..., 3, 3) rotmat."""
    rs = d6.reshape(*d6.shape[:-1], 3, 2)
    a1 = rs[..., :, 0]
    a2 = rs[..., :, 1]
    b1 = a1 / jnp.linalg.norm(a1, axis=-1, keepdims=True)
    b2 = a2 - jnp.sum(b1 * a2, axis=-1, keepdims=True) * b1
    b2 = b2 / jnp.linalg.norm(b2, axis=-1, keepdims=True)
    b3 = jnp.cross(b1, b2, axis=-1)
    return jnp.stack([b1, b2, b3], axis=-1)


def _rotmat_to_axisangle(R):
    """3x3 rotmat (..., 3, 3) -> axis-angle (..., 3)."""
    cos = ((R[..., 0, 0] + R[..., 1, 1] + R[..., 2, 2]) - 1.0) * 0.5
    cos = jnp.clip(cos, -1.0 + 1e-7, 1.0 - 1e-7)
    angle = jnp.arccos(cos)
    sin = jnp.maximum(jnp.sin(angle), 1e-7)
    axis = jnp.stack(
        [R[..., 2, 1] - R[..., 1, 2],
         R[..., 0, 2] - R[..., 2, 0],
         R[..., 1, 0] - R[..., 0, 1]], axis=-1
    ) / (2.0 * sin[..., None])
    return axis * angle[..., None]


def vposer_decode_jax(z, vw):
    """z: (32,) -> body axis-angle (21, 3)."""
    x = _leaky_relu(z @ vw["fc1_w"].T + vw["fc1_b"])
    x = _leaky_relu(x @ vw["fc2_w"].T + vw["fc2_b"])
    d6 = (x @ vw["out_w"].T + vw["out_b"]).reshape(NUM_BODY_JOINTS, 6)
    R = _continuous_rot_to_matrix(d6)
    return _rotmat_to_axisangle(R)


# -----------------------------------------------------------------------------
# SMPL-X LBS in JAX
# -----------------------------------------------------------------------------
def _axisangle_to_rotmat(aa):
    """Rodrigues: axis-angle (..., 3) -> rotmat (..., 3, 3)."""
    angle = jnp.maximum(jnp.linalg.norm(aa, axis=-1, keepdims=True), 1e-12)
    axis = aa / angle
    zero = jnp.zeros(axis.shape[:-1])
    K = jnp.stack([
        jnp.stack([zero, -axis[..., 2],  axis[..., 1]], axis=-1),
        jnp.stack([ axis[..., 2], zero, -axis[..., 0]], axis=-1),
        jnp.stack([-axis[..., 1],  axis[..., 0], zero], axis=-1),
    ], axis=-2)
    eye = jnp.broadcast_to(jnp.eye(3), K.shape)
    sin = jnp.sin(angle)[..., None]
    cos = jnp.cos(angle)[..., None]
    return eye + sin * K + (1.0 - cos) * (K @ K)


def smplx_lbs_jax(theta22_aa, betas, sm):
    """Forward LBS for SMPL-X with face/eyes/hands clamped to zero.

    Parameters
    ----------
    theta22_aa : (22, 3)  axis-angle for joints 0..21 (root + body)
    betas      : (10,)    shape coefficients
    sm         : dict of SMPL-X tensors from load_smplx_jax()

    Returns
    -------
    verts : (10475, 3)    posed mesh in SMPL-X canonical (Y-up) frame
    """
    # 1. Shape-blended template
    v_shaped = sm["v_template"] + jnp.einsum("vdk,k->vd", sm["shapedirs"], betas)
    # 2. Joint locations from shape (per-coord regression)
    J = sm["J_regressor"] @ v_shaped  # (55, 3)
    # 3. Full 55-joint axis-angle: zero-pad joints 22..54
    full_aa = jnp.zeros((NUM_TOTAL_JOINTS, 3), dtype=v_shaped.dtype)
    full_aa = full_aa.at[:22].set(theta22_aa)
    rotmats = _axisangle_to_rotmat(full_aa)  # (55, 3, 3)
    # 4. Pose blend shapes: features = flatten(rotmats[1:] - I)  (54*9=486)
    eye = jnp.eye(3, dtype=v_shaped.dtype)
    pose_feat = (rotmats[1:] - eye[None, :, :]).reshape(-1)  # (486,)
    pose_offsets = (pose_feat @ sm["posedirs"]).reshape(-1, 3)  # (10475, 3)
    v_posed = v_shaped + pose_offsets
    # 5. Global joint transforms via kinematic chain (sequential cumprod)
    # T_local[i] = make_4x4(rotmats[i], J[i] - J[parents[i]])
    parents = sm["parents"]  # (55,) int32
    # local translation: J[i] - J[parents[i]], with parents[0]=-1 -> use J[0]
    t_local = J - J[jnp.maximum(parents, 0)]
    t_local = t_local.at[0].set(J[0])
    # Build (55, 4, 4) homogeneous transforms
    T_local = jnp.zeros((NUM_TOTAL_JOINTS, 4, 4), dtype=v_shaped.dtype)
    T_local = T_local.at[:, :3, :3].set(rotmats)
    T_local = T_local.at[:, :3, 3].set(t_local)
    T_local = T_local.at[:, 3, 3].set(1.0)
    # Cumulative kinematic chain: T_global[i] = T_global[parents[i]] @ T_local[i]
    # Process joints in topological order (which is sorted ascending in SMPL-X).
    def step(carry, i):
        T_global = carry
        Ti = jnp.where(
            parents[i] < 0,
            T_local[i],
            T_global[parents[i]] @ T_local[i],
        )
        T_global = T_global.at[i].set(Ti)
        return T_global, None
    T_global0 = jnp.zeros((NUM_TOTAL_JOINTS, 4, 4), dtype=v_shaped.dtype)
    T_global, _ = jax.lax.scan(step, T_global0, jnp.arange(NUM_TOTAL_JOINTS))
    # 6. Subtract rest-pose joint translation: T[i] = T_global[i] @ inv(rest[i])
    # where rest[i] = make_4x4(I, J[i]). Inverse is make_4x4(I, -J[i]).
    # So T[i] = T_global[i] with translation column adjusted.
    # T[i] = T_global[i]; then T[i].translation -= T_global[i].rotation @ J[i]
    R_glob = T_global[:, :3, :3]
    t_glob = T_global[:, :3, 3]
    T_skin_t = t_glob - jnp.einsum("ijk,ik->ij", R_glob, J)
    # 7. LBS: per-vertex weighted blend
    # weighted_T[v] = sum_i lbs_weights[v, i] * T_skin[i]
    W = sm["lbs_weights"]  # (V, 55)
    R_blend = jnp.einsum("vi,ijk->vjk", W, R_glob)  # (V, 3, 3)
    t_blend = jnp.einsum("vi,ij->vj",  W, T_skin_t)  # (V, 3)
    v_world = jnp.einsum("vij,vj->vi", R_blend, v_posed) + t_blend
    return v_world


# -----------------------------------------------------------------------------
# World-frame transform + triangle properties
# -----------------------------------------------------------------------------
# SMPL-X canonical frame: Y-up, body faces +z. JSAC2 world: Z-up, default body
# faces -x. The combined fixed rotation (from scene_smplx._smplx_to_world_rotation):
_R_SMPLX_TO_WORLD = jnp.asarray(
    np.array([[0.0, 1.0, 0.0],
              [-1.0, 0.0, 0.0],
              [0.0, 0.0, 1.0]]) @
    np.array([[1.0, 0.0, 0.0],
              [0.0, 0.0, -1.0],
              [0.0, 1.0, 0.0]]),
    dtype=jnp.float64,
)


def _surface_centroid(verts, faces_np):
    """Area-weighted surface centroid (matches trimesh.Trimesh.centroid).

    SMPL-X meshes are non-watertight (euler != 2) so the existing
    scene_smplx flow places by trimesh.centroid, which is the
    area-weighted average of triangle centroids — NOT the volume centroid.
    """
    v0 = verts[faces_np[:, 0]]
    v1 = verts[faces_np[:, 1]]
    v2 = verts[faces_np[:, 2]]
    cross = jnp.cross(v1 - v0, v2 - v0, axis=-1)
    areas = 0.5 * jnp.linalg.norm(cross, axis=-1)
    cent = (v0 + v1 + v2) / 3.0
    return jnp.einsum("t,ti->i", areas, cent) / areas.sum()


def world_verts(verts_smplx, body_centroid, face_azimuth_rad, faces_np):
    """Apply Y-up→Z-up rotation, face-azimuth yaw, then translate so the
    trimesh-style volume centroid lands at body_centroid."""
    v = verts_smplx @ _R_SMPLX_TO_WORLD.T
    delta_yaw = face_azimuth_rad - jnp.pi
    c, s = jnp.cos(delta_yaw), jnp.sin(delta_yaw)
    Rz = jnp.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]],
                    dtype=v.dtype)
    v = v @ Rz.T
    cv = _surface_centroid(v, faces_np)
    return v - cv + body_centroid


def tri_centroids_normals_areas(verts, faces):
    """faces: numpy (T, 3) int64.
    Returns (centroids (T,3), normals_unit (T,3), areas (T,))."""
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    centroids = (v0 + v1 + v2) / 3.0
    cross = jnp.cross(v1 - v0, v2 - v0, axis=-1)
    n_norm = jnp.linalg.norm(cross, axis=-1)
    normals = cross / jnp.maximum(n_norm[:, None], 1e-30)
    areas = 0.5 * n_norm
    return centroids, normals, areas


# -----------------------------------------------------------------------------
# Kirchhoff render (re-implemented inline for autodiff continuity)
# -----------------------------------------------------------------------------
C0 = 2.99792458e8
EPS_0 = 8.8541878128e-12


def _n_complex(eps_r, sigma, freq_hz):
    omega = 2.0 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return complex(n_tilde)


def kirchhoff_h_body_native(centroids, normals, areas,
                             r_phone, k_dod, k_doa, psi, amp_path,
                             bs_positions, bs_center,
                             n_tilde, k0):
    """Memory-frugal Kirchhoff with paths kept at Sionna-native size.

    Instead of fanning out P_sionna paths to M*P_sionna entries via the
    per-element planewave phase ramp at construction time, we keep the
    P_sionna per-path arrays compact and apply the per-element phase
    ramp `exp(-j k0 (bs_pos[m] - bs_center) . k_dod[p])` inside.

    Memory saving: for Munich (P_sionna~350, T~21k), the (P, T) tensor is
    350*21k*16B = 117 MB instead of 22464*21k*16B = 7.5 GB.
    Reverse-mode autodiff therefore stays inside 24 GB GPU.

    Parameters
    ----------
    centroids, normals, areas : (T, 3), (T, 3), (T,)
        Phone-visible-facing triangles (vis applied as soft mask inside).
    r_phone : (3,)
    k_dod : (P, 3)   direction-of-departure at BS (used for steering ramp)
    k_doa : (P, 3)   direction-of-arrival at body (used for kirchhoff)
    psi   : (P, 3) complex   per-path polarization at the body
    amp_path : (P,) complex  per-path scalar amplitude
    bs_positions : (M, 3)    per-element world positions
    bs_center    : (3,)
    """
    M = bs_positions.shape[0]
    # Per-(path, triangle) geometry at the body
    delta = r_phone[None, :] - centroids
    R = jnp.linalg.norm(delta, axis=1)
    eta_hat = delta / jnp.maximum(R[:, None], 1e-12)
    facing = (jnp.einsum("tj,tj->t", normals, eta_hat) > 0).astype(centroids.dtype)
    areas_eff = areas * facing
    green = jnp.exp(1j * k0 * R) / (4.0 * jnp.pi * jnp.maximum(R, 1e-9))
    mu = -jnp.einsum("nj,tj->nt", k_doa, normals)
    lit = mu > 1e-3
    mu_c = jnp.where(lit, mu, 1.0).astype(jnp.complex128)
    n2 = n_tilde * n_tilde
    xi = jnp.sqrt(n2 - 1.0 + mu_c * mu_c)
    xi = jnp.where(jnp.real(xi) < 0, -xi, xi)
    r_s = (mu_c - xi) / (mu_c + xi)
    r_p = (n2 * mu_c - xi) / (n2 * mu_c + xi)
    r0 = 0.5 * (r_s + r_p)
    psi_dot_eta = jnp.einsum("nj,tj->nt", psi, eta_hat.astype(psi.dtype))
    g_UE_proj = psi[:, 2:3] - eta_hat[None, :, 2] * psi_dot_eta
    phase_inc = jnp.exp(-1j * k0 * jnp.einsum("nj,tj->nt", k_doa, centroids))
    K = 1j * k0 * r0
    # Per-(path) integrand summed over triangles -> (P,) complex
    contrib = (
        K * g_UE_proj * green[None, :] * phase_inc * areas_eff[None, :]
    )                                                          # (P, T)
    contrib = jnp.where(lit, contrib, 0.0 + 0.0j)
    per_path_T = contrib.sum(axis=1)                            # (P,)
    per_path_T = amp_path * per_path_T                          # (P,)
    # Apply per-element steering ramp and accumulate to h (M,)
    rel = bs_positions - bs_center[None, :]                     # (M, 3)
    elem_phase = jnp.exp(-1j * k0 * (rel @ k_dod.T))            # (M, P)
    h = elem_phase @ per_path_T                                 # (M,)
    return h


# -----------------------------------------------------------------------------
# End-to-end SINR(z) for autodiff
# -----------------------------------------------------------------------------
def _sinr_db_from_h(h_cas, p_tx_dbm, noise_dbm):
    # MRT SINR with isotropic UE = ||h||^2 * P_tx / N0
    p_tx = 10.0 ** ((p_tx_dbm - 30.0) / 10.0)
    n0   = 10.0 ** ((noise_dbm - 30.0) / 10.0)
    rx_pwr = (jnp.abs(h_cas) ** 2).sum() * p_tx
    return 10.0 * jnp.log10(rx_pwr / n0)


def make_sinr_fn(sm, vw, betas, body_centroid, face_az,
                  r_phone, h_scene,
                  k_dod, k_doa, psi_path, amp_path,
                  bs_positions, bs_center,
                  n_tilde, k0, p_tx_dbm, noise_dbm):
    """Return a JIT-compiled `sinr(z)` from z (32,) to sinr_db (scalar).

    Uses Sionna-native per-path arrays (P_sionna ~ 100-500) plus an
    inline planewave-steering ramp, so reverse-mode autodiff fits in
    24 GB VRAM even for scenes with hundreds of paths.
    """
    body_centroid = jnp.asarray(body_centroid, jnp.float64)
    face_az = jnp.float64(face_az)
    r_phone = jnp.asarray(r_phone, jnp.float64)
    h_scene = jnp.asarray(h_scene, jnp.complex128)
    faces_np = sm["faces"]

    @jax.jit
    def sinr(z):
        body_aa = vposer_decode_jax(z, vw)               # (21, 3)
        theta22 = jnp.zeros((22, 3), dtype=z.dtype)
        theta22 = theta22.at[1:].set(body_aa)            # joint 0 = global_orient = 0
        verts_local = smplx_lbs_jax(theta22, betas, sm)  # (V, 3) SMPL-X frame
        verts_w = world_verts(verts_local, body_centroid, face_az, faces_np)
        c, n, a = tri_centroids_normals_areas(verts_w, faces_np)
        h_body = kirchhoff_h_body_native(
            c, n, a, r_phone, k_dod, k_doa, psi_path, amp_path,
            bs_positions, bs_center, n_tilde, k0,
        )
        return _sinr_db_from_h(h_scene + h_body, p_tx_dbm, noise_dbm)

    return sinr

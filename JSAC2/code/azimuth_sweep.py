"""Random-azimuth + latent sweep over the 18 Munich Rx.

Replaces the legacy `latent_sweep_munich.py` design choice of locking the
whole-body azimuth to face-the-BS. Here body azimuth is a random ground-
truth condition (a person may face any direction; turning into LOS is the
dominant geometric effect we want to expose).

For each Rx:
  - yaw_idx=0 is the legacy reference: body facing BS (kept for comparison).
  - yaw_idx=1..N_yaw-1 are uniform-random in [-pi, pi).
  - For each yaw, lat_idx=0 is the encoded baseline pose (z0); lat_idx=1..
    N_lat-1 are random comfort-ball samples around z0.

Output: one capture NPZ per Rx in `outputs/munich/replay_capture/`, picked
up by `replay/prepare_data.py` for the viewer.

Run:
    python -m JSAC2.code.azimuth_sweep [--n-yaw 16] [--n-lat 4] [--rx 0 1 2]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

# JAX setup before any JAX import (must happen before kirchhoff_jax loads).
if "JAX_PLATFORMS" not in os.environ:
    os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import BSPathDict, mrt_sinr_db  # noqa: E402
from JSAC2.code.kirchhoff_jax import _n_complex_jax, C0  # noqa: E402
from JSAC2.code.pose_pipeline_jax import (  # noqa: E402
    kirchhoff_h_body_native,
    load_smplx_jax,
    load_vposer_jax,
    smplx_lbs_jax,
    tri_centroids_normals_areas,
    vposer_decode_jax,
    world_verts,
    _surface_centroid,
)
from JSAC2.code.replay.export_meshes import build_decimated_topology  # noqa: E402
from JSAC2.code.replay.state_capture import RxCapture  # noqa: E402
from JSAC2.code.scene_nlos import BSArray  # noqa: E402
from JSAC2.code.scene_smplx import make_body_smplx  # noqa: E402
from JSAC2.code.vposer_v2 import VPoser, LATENT_D  # noqa: E402


F_C = 28e9
TRACE_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich/traces")
CAPTURE_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich/replay_capture")
PHONE_TX_DBM = 43.0
NOISE_DBM = -94.0
RHO_Z = 1.5            # latent comfort radius
BS_TARGET_XY = np.array([33.0, 91.0], dtype=np.float64)

# JIT-cache stability: pad the Sionna path bundle AND visibility-sliced
# triangles to fixed shapes, so the JAX kernel compiles ONCE for the entire
# sweep instead of every sample (which would force ptxas to re-run between
# every call and starve the GPU).
#
# We use the "native" Kirchhoff kernel (kirchhoff_h_body_native) which keeps
# paths at Sionna-native length (P_sionna ~ 100-500) and applies the BS
# element-fanout inside. Memory of the (P, T) intermediate is ~115 MB at
# P_PAD=600, T_PAD=12000.
P_PAD = 600          # >= max Sionna paths across all 18 Rx (observed max=526)
T_PAD = 12000        # >= max phone-visible SMPL-X faces (full mesh = 20908)
EPS_R = 16.5
SIGMA = 25.8
M_BS = 64


def _padded_native_kernel():
    """Return a jit-compiled native Kirchhoff kernel with fixed shapes."""
    import jax

    @jax.jit
    def _ker(centroids, normals, areas, r_phone,
             k_dod, k_doa, psi_path, amp_path,
             bs_positions, bs_center, n_tilde, k0):
        return kirchhoff_h_body_native(
            centroids, normals, areas, r_phone,
            k_dod, k_doa, psi_path, amp_path,
            bs_positions, bs_center, n_tilde, k0,
        )
    return _ker


_KER = None


def _kernel():
    global _KER
    if _KER is None:
        _KER = _padded_native_kernel()
    return _KER


_VPOSER = None
_SM_JAX = None
_VW_JAX = None


def _vposer() -> VPoser:
    global _VPOSER
    if _VPOSER is None:
        import torch

        _VPOSER = VPoser.from_checkpoint()
        _VPOSER.eval()
        _ = torch  # silence linter
    return _VPOSER


def _jax_weights():
    """Load (and cache) SMPL-X + VPoser tensors on the JAX device."""
    global _SM_JAX, _VW_JAX
    if _SM_JAX is None:
        _SM_JAX = load_smplx_jax()
        _VW_JAX = load_vposer_jax()
    return _SM_JAX, _VW_JAX


def decode_z(z: np.ndarray) -> np.ndarray:
    """VPoser decode (joints 1..21). Used only for the state-capture
    re-pose. The optimizer itself runs entirely inside JAX."""
    import torch

    vp = _vposer()
    with torch.no_grad():
        body = vp.decode(torch.tensor(z, dtype=torch.float32).unsqueeze(0))
    pose22 = np.zeros((22, 3), dtype=np.float64)
    pose22[1:] = body[0].numpy()
    return pose22


def project_to_ball(z: np.ndarray, z_anchor: np.ndarray, rho: float) -> np.ndarray:
    """Project z onto the rho-ball around z_anchor."""
    d = z - z_anchor
    norm = float(np.linalg.norm(d))
    if norm <= rho:
        return z
    return z_anchor + (rho / norm) * d


def build_jax_sinr_and_grad(
    sm, vw, betas, body_centroid, r_phone, h_scene,
    k_dod, k_doa, psi_path, amp_path,
    bs_positions, bs_center, n_tilde, k0,
    p_tx_dbm, noise_dbm,
):
    """Return three jit'd closures over the all-JAX pose+Kirchhoff pipeline:

      sinr(z, face_az)            -> scalar SINR_dB
      sinr_and_grad(z, face_az)   -> (sinr_db, dS/dz, dS/dface_az)
      verts_world(z, face_az)     -> (10475, 3) posed world-frame verts

    The first two are autodiff-friendly: jax.value_and_grad gives analytic
    gradient in one bwd pass, replacing 16 FD evaluations per ascent step.
    """
    import jax
    import jax.numpy as jnp

    betas_j        = jnp.asarray(betas, jnp.float64)
    body_cent_j    = jnp.asarray(body_centroid, jnp.float64)
    r_phone_j      = jnp.asarray(r_phone, jnp.float64)
    h_scene_j      = jnp.asarray(h_scene, jnp.complex128)
    k_dod_j        = jnp.asarray(k_dod, jnp.float64)
    k_doa_j        = jnp.asarray(k_doa, jnp.float64)
    psi_path_j     = jnp.asarray(psi_path, jnp.complex128)
    amp_path_j     = jnp.asarray(amp_path, jnp.complex128)
    bs_positions_j = jnp.asarray(bs_positions, jnp.float64)
    bs_center_j    = jnp.asarray(bs_center, jnp.float64)
    n_tilde_j      = jnp.asarray(n_tilde, jnp.complex128)
    faces_np       = np.asarray(sm["faces"])

    def _sinr(z, face_az):
        body_aa = vposer_decode_jax(z, vw)                        # (21, 3)
        theta22 = jnp.zeros((22, 3), dtype=z.dtype)
        theta22 = theta22.at[1:].set(body_aa)                     # joint 0 = 0
        verts_local = smplx_lbs_jax(theta22, betas_j, sm)         # (V, 3) SMPL-X
        verts_w = world_verts(verts_local, body_cent_j, face_az, faces_np)
        c, n, a = tri_centroids_normals_areas(verts_w, faces_np)
        h_body = kirchhoff_h_body_native(
            c, n, a, r_phone_j,
            k_dod_j, k_doa_j, psi_path_j, amp_path_j,
            bs_positions_j, bs_center_j, n_tilde_j, k0,
        )
        h_cas = h_scene_j + h_body
        p_tx = 10.0 ** ((p_tx_dbm - 30.0) / 10.0)
        n0   = 10.0 ** ((noise_dbm - 30.0) / 10.0)
        h2 = (jnp.abs(h_cas) ** 2).sum()
        return 10.0 * jnp.log10(jnp.maximum(p_tx * h2 / n0, 1e-30))

    sinr_jit = jax.jit(_sinr)
    sinr_and_grad_jit = jax.jit(jax.value_and_grad(_sinr, argnums=(0, 1)))

    def _verts_world(z, face_az):
        body_aa = vposer_decode_jax(z, vw)
        theta22 = jnp.zeros((22, 3), dtype=z.dtype)
        theta22 = theta22.at[1:].set(body_aa)
        verts_local = smplx_lbs_jax(theta22, betas_j, sm)
        return world_verts(verts_local, body_cent_j, face_az, faces_np)

    verts_world_jit = jax.jit(_verts_world)

    return sinr_jit, sinr_and_grad_jit, verts_world_jit


def autodiff_joint_ascent(
    z0: np.ndarray,
    yaw0: float,
    sinr_jit,
    sinr_and_grad_jit,
    rho_z: float,
    n_iter: int,
    eta: float = 0.4,
    yaw_scale: float = 0.05,    # 1 unit of yaw "feels like" 0.05 unit of z
) -> tuple[list[np.ndarray], list[float], list[float]]:
    """Analytic-gradient ascent in the joint (z, yaw) space.

    Per iter: 1 forward + 1 backward via jax.value_and_grad. The gradient is
    rescaled so a step in yaw covers similar SINR sensitivity as a step in z.
    Backtracking: if a step regresses by more than 0.5 dB, restore the
    best-so-far iterate and shrink the step. Same convergence semantics as
    the original FD loop, but ~17x fewer forward calls.
    """
    import jax.numpy as jnp

    z = z0.astype(np.float64).copy()
    yaw = float(yaw0)
    z0_anchor = z.copy()
    s0 = float(sinr_jit(jnp.asarray(z), jnp.float64(yaw)))
    z_traj = [z.copy()]
    yaw_traj = [yaw]
    sinr_traj = [s0]
    best_sinr = s0
    best_z, best_yaw = z.copy(), yaw
    eta_local = float(eta)

    for _ in range(n_iter):
        s_val, (g_z, g_yaw) = sinr_and_grad_jit(jnp.asarray(z), jnp.float64(yaw))
        g_z_np = np.asarray(g_z, dtype=np.float64)
        g_yaw_np = float(g_yaw) * yaw_scale         # rescale yaw-gradient
        g_norm = float(np.sqrt((g_z_np * g_z_np).sum() + g_yaw_np * g_yaw_np))
        if g_norm < 1e-9:
            z_traj.append(z.copy()); yaw_traj.append(yaw); sinr_traj.append(sinr_traj[-1])
            continue
        step_z = eta_local * g_z_np / g_norm
        step_yaw = eta_local * (g_yaw_np / g_norm) / yaw_scale  # back to native units
        z_new = project_to_ball(z + step_z, z0_anchor, rho_z)
        yaw_new = yaw + step_yaw
        yaw_new = float((yaw_new + np.pi) % (2 * np.pi) - np.pi)
        s_new = float(sinr_jit(jnp.asarray(z_new), jnp.float64(yaw_new)))
        if s_new > sinr_traj[-1] - 0.5:
            z, yaw = z_new, yaw_new
        else:
            z, yaw = best_z.copy(), best_yaw
            eta_local *= 0.7
            s_new = best_sinr
        if s_new > best_sinr:
            best_sinr = s_new
            best_z, best_yaw = z.copy(), yaw
        z_traj.append(z.copy())
        yaw_traj.append(yaw)
        sinr_traj.append(s_new)
    return z_traj, yaw_traj, sinr_traj


def joint_gradient_ascent(
    z0: np.ndarray,
    yaw0: float,
    sinr_fn,                          # callable (z, yaw) -> sinr_db
    rho_z: float,
    n_iter: int,
    eta: float = 0.4,
    fd_eps_z: float = 0.08,
    fd_eps_yaw: float = 0.08,         # radians; ~4.6 degrees
    n_dir_per_iter: int = 8,
    rng: np.random.Generator | None = None,
) -> tuple[list[np.ndarray], list[float], list[float]]:
    """K-iteration ascent in joint (VPoser latent z, body yaw) space.

    Search vector theta = [z[0..31], yaw] in R^33. FD gradient with random
    unit directions in the joint space. The yaw component of each direction
    is rescaled by `fd_eps_yaw / fd_eps_z` so a unit step in yaw covers the
    same SINR-sensitivity range as a unit step in z.

    Yaw is unconstrained (a user can rotate freely); z is projected onto the
    rho_z-ball around z0. Same backtracking + best-so-far restore as the
    z-only loop.

    Returns (z_traj, yaw_traj, sinr_traj) of length n_iter+1.
    """
    if rng is None:
        rng = np.random.default_rng(0)
    D = LATENT_D
    # Build a metric that makes yaw "comparable" to z. A 1-unit move in yaw
    # ~= a fd_eps_yaw radian step; a 1-unit move in z ~= an fd_eps_z step.
    yaw_scale = fd_eps_yaw / fd_eps_z

    z = z0.copy()
    yaw = float(yaw0)
    z0_anchor = z0.copy()
    s0 = float(sinr_fn(z, yaw))
    z_traj = [z.copy()]
    yaw_traj = [yaw]
    sinr_traj = [s0]
    best_sinr = s0
    best_z, best_yaw = z.copy(), yaw
    eta_local = float(eta)

    for _ in range(n_iter):
        g_z = np.zeros(D)
        g_yaw = 0.0
        for _ in range(n_dir_per_iter):
            d33 = rng.standard_normal(D + 1)
            d33 /= np.linalg.norm(d33)
            d_z, d_yaw = d33[:D], float(d33[D])
            s_p = float(sinr_fn(z + fd_eps_z * d_z, yaw + fd_eps_yaw * d_yaw))
            s_m = float(sinr_fn(z - fd_eps_z * d_z, yaw - fd_eps_yaw * d_yaw))
            grad_along = (s_p - s_m) / (2.0 * fd_eps_z)   # FD wrt the z-side scale
            g_z += grad_along * d_z
            g_yaw += grad_along * d_yaw * yaw_scale
        g_z /= n_dir_per_iter
        g_yaw /= n_dir_per_iter
        g_norm = float(np.sqrt((g_z * g_z).sum() + g_yaw * g_yaw))
        if g_norm < 1e-6:
            z_traj.append(z.copy()); yaw_traj.append(yaw); sinr_traj.append(sinr_traj[-1])
            continue
        step_z = eta_local * g_z / g_norm
        step_yaw = eta_local * g_yaw / g_norm
        z_new = project_to_ball(z + step_z, z0_anchor, rho_z)
        yaw_new = yaw + step_yaw
        # Wrap yaw into [-pi, pi) for numerical hygiene; SINR is invariant
        # to integer multiples of 2*pi so this is a free transform.
        yaw_new = float((yaw_new + np.pi) % (2 * np.pi) - np.pi)
        s_new = float(sinr_fn(z_new, yaw_new))
        if s_new > sinr_traj[-1] - 0.5:
            z, yaw = z_new, yaw_new
        else:
            # Backtrack
            z, yaw = best_z.copy(), best_yaw
            eta_local *= 0.7
            s_new = best_sinr
        if s_new > best_sinr:
            best_sinr = s_new
            best_z, best_yaw = z.copy(), yaw
        z_traj.append(z.copy())
        yaw_traj.append(yaw)
        sinr_traj.append(s_new)
    return z_traj, yaw_traj, sinr_traj


def load_scene_npz(scene_idx: int) -> dict:
    """Load a per-Rx NPZ produced by `munich_trace.py`. We deliberately
    IGNORE the cached `face_azimuth_rad` -- azimuth is now a per-sample
    random variable, not a per-Rx fixed value."""
    return dict(np.load(TRACE_DIR / f"scene_{scene_idx:02d}.npz", allow_pickle=False))


def _pad_native_paths(scene_npz: dict) -> tuple:
    """Pad Sionna-native per-path arrays to length P_PAD with zero-amp dummies.

    Returned as plain numpy arrays. The kernel ignores padded slots because
    `amp_path` is zero there, so the (P,) sum still produces the right answer.
    """
    k_dod = np.asarray(scene_npz["body_k_dod"], dtype=np.float64)
    k_doa = np.asarray(scene_npz["body_k_doa"], dtype=np.float64)
    psi_p = np.asarray(scene_npz["body_psi_path"]).astype(np.complex128)
    amp_p = np.asarray(scene_npz["body_amp_path"]).astype(np.complex128)
    P = k_dod.shape[0]
    if P > P_PAD:
        raise ValueError(f"Sionna path count {P} exceeds P_PAD={P_PAD}; raise the cap")
    k_dod_pad = np.zeros((P_PAD, 3), dtype=np.float64)
    k_doa_pad = np.zeros((P_PAD, 3), dtype=np.float64)
    psi_pad   = np.zeros((P_PAD, 3), dtype=np.complex128)
    amp_pad   = np.zeros(P_PAD,        dtype=np.complex128)
    k_dod_pad[:P] = k_dod
    k_doa_pad[:P] = k_doa
    psi_pad[:P]   = psi_p
    amp_pad[:P]   = amp_p
    return k_dod_pad, k_doa_pad, psi_pad, amp_pad


def kirchhoff_h_body_padded(
    body, k_dod_pad, k_doa_pad, psi_pad, amp_pad,
    bs_positions, bs_center, r_phone, n_tilde, k0,
) -> np.ndarray:
    """Padded JAX Kirchhoff render with globally stable shapes (T_PAD, P_PAD).

    Shapes don't change across samples or Rx, so the underlying jit kernel
    compiles ONCE for the entire 2592-sample sweep. Phone-side visibility is
    applied by slicing+padding to T_PAD; padded triangles have area=0 so they
    contribute nothing.
    """
    import jax.numpy as jnp

    vis = body.visible_from(np.asarray(r_phone, dtype=np.float64))
    tri_idx = np.where(vis)[0]
    n_real = len(tri_idx)
    if n_real == 0:
        return np.zeros(M_BS, dtype=np.complex128)
    if n_real > T_PAD:
        tri_idx = tri_idx[:T_PAD]
        n_real = T_PAD

    centroids = np.zeros((T_PAD, 3), dtype=np.float64)
    normals   = np.zeros((T_PAD, 3), dtype=np.float64)
    areas     = np.zeros(T_PAD,        dtype=np.float64)
    centroids[:n_real] = body.centroids[tri_idx]
    normals[:n_real]   = body.normals[tri_idx]
    areas[:n_real]     = body.areas[tri_idx]
    normals[n_real:, 2] = 1.0  # keep xi=sqrt(...) finite in padded slots

    ker = _kernel()
    h = ker(
        jnp.asarray(centroids), jnp.asarray(normals), jnp.asarray(areas),
        jnp.asarray(np.asarray(r_phone, dtype=np.float64)),
        jnp.asarray(k_dod_pad), jnp.asarray(k_doa_pad),
        jnp.asarray(psi_pad), jnp.asarray(amp_pad),
        jnp.asarray(bs_positions, dtype=np.float64),
        jnp.asarray(bs_center, dtype=np.float64),
        jnp.asarray(n_tilde, dtype=jnp.complex128),
        float(k0),
    )
    return np.asarray(h)


def reconstruct_bs_array(bs_pos: np.ndarray, bs_positions: np.ndarray) -> BSArray:
    """Rebuild a BSArray whose element layout exactly matches the cache."""
    rel = bs_positions - bs_pos[None, :]
    _, _, vh = np.linalg.svd(rel, full_matrices=False)
    normal = vh[-1]
    bs = BSArray(n_x=8, n_y=8, center=bs_pos, normal=normal, f_c=F_C)
    bs.positions = bs_positions
    bs.boresight = normal
    return bs


def sweep_one_rx(
    scene_idx: int,
    yaws: np.ndarray,
    n_iter: int,
    rho: float,
    out_dir: Path,
    faces_dec: np.ndarray,
    donor_idx: np.ndarray,
    rng: np.random.Generator,
) -> Path:
    """Run the (yaw x ascent-iteration) sweep for one Rx and write its capture NPZ.

    For each random body azimuth `yaws[i]`, run K-iteration projected gradient
    ascent in VPoser latent space starting from z0=0. The lat axis is the
    iterate index k=0..n_iter; SINR is monotonically non-decreasing in k.
    """
    s = load_scene_npz(scene_idx)
    bs_pos = np.asarray(s["bs_pos"], dtype=np.float64)
    bs_positions = np.asarray(s["bs_positions"], dtype=np.float64)
    bs_array = reconstruct_bs_array(bs_pos, bs_positions)
    body_centroid = np.asarray(s["body_centroid"], dtype=np.float64)
    phone_xyz = np.asarray(s["phone_xyz"], dtype=np.float64)
    h_scene = np.asarray(s["h_scene"]).astype(np.complex128)
    los_flag = str(s["los_flag"]) if s["los_flag"].ndim == 0 else str(s["los_flag"].item())
    label = str(s["label"]) if s["label"].ndim == 0 else str(s["label"].item())

    body_paths = BSPathDict(
        j_idx=s["body_j_idx"],
        k_hat=s["body_k_hat"],
        psi=s["body_psi"],
        amp=s["body_amp"],
    )
    # Pad Sionna-native path arrays once per Rx; shape (P_PAD,) is the same
    # across all Rx, so the JAX kernel JIT-cache hits after the very first call.
    k_dod_pad, k_doa_pad, psi_pad, amp_pad = _pad_native_paths(s)
    bs_center = np.asarray(s["bs_pos"], dtype=np.float64)
    bs_positions_np = np.asarray(s["bs_positions"], dtype=np.float64)
    n_tilde = _n_complex_jax(EPS_R, SIGMA, F_C)
    k0 = 2.0 * np.pi * F_C / C0

    cap = RxCapture(
        rx_idx=scene_idx,
        rx_label=label,
        los_flag=los_flag,
        bs_pos=bs_pos,
        bs_positions=bs_positions,
        bs_normal=bs_array.boresight,
        bs_target_xy=BS_TARGET_XY,
        phone_xyz=phone_xyz,
        body_centroid=body_centroid,
        f_c=F_C,
        k_dod=np.asarray(s["body_k_dod"], dtype=np.float64),
        k_doa=np.asarray(s["body_k_doa"], dtype=np.float64),
        psi_path=np.asarray(s["body_psi_path"]).astype(np.complex128),
        amp_path=np.asarray(s["body_amp_path"]).astype(np.complex128),
        h_scene=h_scene,
        faces_dec=faces_dec,
        donor_idx=donor_idx,
    )

    n_yaw = len(yaws)
    n_lat = n_iter + 1
    t_rx_start = time.time()

    # All-JAX pipeline: build a JIT'd sinr + autodiff gradient + verts closure
    # over this Rx's native (un-padded) path bundle. We deliberately do NOT
    # pad P to a global cap -- per-Rx native sizes (avg 355) keep the kernel
    # tight; global padding (e.g., P=600) saved JIT compile time but added
    # ~70% per-call work that dominated, making the full sweep slower.
    sm, vw = _jax_weights()
    betas = np.zeros(10, dtype=np.float64)
    k_dod_native = np.asarray(s["body_k_dod"], dtype=np.float64)
    k_doa_native = np.asarray(s["body_k_doa"], dtype=np.float64)
    psi_native   = np.asarray(s["body_psi_path"]).astype(np.complex128)
    amp_native   = np.asarray(s["body_amp_path"]).astype(np.complex128)
    sinr_jit, sinr_and_grad_jit, verts_world_jit = build_jax_sinr_and_grad(
        sm, vw, betas, body_centroid, phone_xyz, h_scene,
        k_dod_native, k_doa_native, psi_native, amp_native,
        bs_positions_np, bs_center, n_tilde, k0,
        PHONE_TX_DBM, NOISE_DBM,
    )

    import jax.numpy as jnp

    for y_idx, yaw_start in enumerate(yaws):
        cap.start_yaw(float(yaw_start))
        z0 = np.zeros(LATENT_D, dtype=np.float64)
        z_traj, yaw_traj, sinr_traj = autodiff_joint_ascent(
            z0, float(yaw_start), sinr_jit, sinr_and_grad_jit,
            rho_z=rho, n_iter=n_iter,
        )
        for k_idx, (z_k, yaw_k, s_k) in enumerate(zip(z_traj, yaw_traj, sinr_traj)):
            # Pose verts via the same JAX pipeline -> indexed donor verts.
            verts_world_all = np.asarray(verts_world_jit(jnp.asarray(z_k), jnp.float64(yaw_k)))
            # Place by area-weighted centroid translation, mirroring make_body_smplx.
            cent = np.asarray(_surface_centroid(jnp.asarray(verts_world_all), sm["faces"]))
            verts_world_all = verts_world_all + (body_centroid - cent)
            posed_verts_dec = verts_world_all.astype(np.float32)[donor_idx]
            # h_body magnitude (cheap diagnostic): one extra forward (still on GPU)
            cap.add_sample(
                z=z_k,
                yaw=float(yaw_k),
                verts_dec=posed_verts_dec,
                sinr_db=float(s_k),
                h_body_abs_sum=0.0,   # cheap to skip; not needed for the viewer's main HUD
                is_baseline=(k_idx == 0),
            )
        if y_idx == 0 or (y_idx + 1) % 8 == 0:
            sinr_arr = np.asarray(cap.sinr_db[-1])
            yaw_arr = np.asarray(cap.yaws_traj[-1])
            print(
                f"  rx{scene_idx:02d} [{los_flag}] start_yaw {y_idx + 1}/{n_yaw} "
                f"({np.degrees(yaw_start):+6.1f}°): k=0:{sinr_arr[0]:5.1f} -> "
                f"k={n_iter}:{sinr_arr[-1]:5.1f} dB "
                f"(gain {sinr_arr[-1] - sinr_arr[0]:+4.1f}; "
                f"final yaw {np.degrees(yaw_arr[-1]):+6.1f}°, "
                f"delta {np.degrees(yaw_arr[-1] - yaw_arr[0]):+5.1f}°)"
            )

    out_path = cap.save(out_dir)
    print(
        f"rx{scene_idx:02d} done in {time.time() - t_rx_start:.1f}s -> {out_path.name} "
        f"({out_path.stat().st_size / 1024:.0f} KB, "
        f"{n_yaw} yaws x {n_lat} lats)"
    )
    return out_path


def build_yaw_grid(rng: np.random.Generator, n_yaw_random: int,
                   face_to_bs: float) -> np.ndarray:
    """Prepend the legacy face-to-BS direction, then sample uniform yaws."""
    rest = rng.uniform(-np.pi, np.pi, size=n_yaw_random)
    return np.concatenate([[face_to_bs], rest]).astype(np.float64)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n-yaw", type=int, default=16,
                   help="Total yaws per Rx (yaw 0 is face-to-BS legacy ref).")
    p.add_argument("--n-iter", type=int, default=7,
                   help="Latent gradient-ascent iterations per yaw "
                        "(lat axis stores k=0..n-iter, so n-iter=7 -> 8 lat samples).")
    p.add_argument("--rho", type=float, default=RHO_Z,
                   help="Latent comfort-ball radius (projected ascent stays within).")
    p.add_argument("--rx", type=int, nargs="*", default=None,
                   help="Subset of Rx indices to sweep (default: all 18).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--target-faces", type=int, default=1500,
                   help="Decimated SMPL-X face budget for the viewer.")
    args = p.parse_args()

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"capture dir: {CAPTURE_DIR}")

    rng = np.random.default_rng(args.seed)

    print(f"decimating SMPL-X to target_faces={args.target_faces} ...")
    faces_dec, donor_idx = build_decimated_topology(target_faces=args.target_faces)
    print(f"  -> {faces_dec.shape[0]} faces, {donor_idx.shape[0]} verts")

    rx_indices = args.rx if args.rx is not None else list(range(18))
    n_lat = args.n_iter + 1
    print(f"sweeping {len(rx_indices)} Rx with {args.n_yaw} yaws x "
          f"{n_lat} lats (k=0..{args.n_iter} ascent iterates), rho={args.rho}")

    t_total = time.time()
    for rx_idx in rx_indices:
        s = load_scene_npz(rx_idx)
        phone_xyz = np.asarray(s["phone_xyz"], dtype=np.float64)
        bs_pos = np.asarray(s["bs_pos"], dtype=np.float64)
        face_to_bs = float(
            np.arctan2(bs_pos[1] - phone_xyz[1], bs_pos[0] - phone_xyz[0])
        )
        yaws = build_yaw_grid(rng, args.n_yaw - 1, face_to_bs)
        sweep_one_rx(rx_idx, yaws, args.n_iter, args.rho, CAPTURE_DIR,
                     faces_dec, donor_idx, rng)

    print(f"\nfull sweep complete in {(time.time() - t_total) / 60:.1f} min")


if __name__ == "__main__":
    main()

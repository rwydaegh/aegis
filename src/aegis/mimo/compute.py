"""MIMO scene orchestrator: build channels, compute precoders, run dosimetry.

Connects the Phase 1 data model (MIMOScene, UserState) with the coherent
pipeline (body_channel, exposure_operator) and multi-user precoders.

Also provides lower-level helpers (compute_mrt_precoder, compute_user_sab,
compute_total_exposure) used by the viewer API routes.

Design doc: sections D1 and E1.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from aegis.coherent.body_channel import compute_body_channel_factored
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import C_0
from aegis.defaults import DEFAULT_NOISE_POWER, DEFAULT_P_ABS_MAX, NUMERICAL_FLOOR
from aegis.geometry import fock_gate
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.precoders import compute_precoder
from aegis.paths import PropagationPaths

if TYPE_CHECKING:
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.mimo.scene import MIMOScene


def make_stochastic_paths_fn(
    params: dict,
    freq_ghz: float,
    power_dbm: float,
    base_seed: int,
    viz_collector: list[dict] | None = None,
) -> Callable:
    """Factory for a stochastic path generator compatible with compute_mimo_scene_with_bodies.

    Returns a callable with signature
    ``fn(body, array_center, freq_hz, device_position) -> PropagationPaths``
    that generates 3GPP cluster-based multipath using ``generate_channel``.

    Each call increments the seed so successive users get independent channels.
    If *viz_collector* is provided, per-call cluster metadata dicts are appended.
    """
    from aegis.channel.generator import generate_channel

    call_count = [0]  # mutable counter for closure

    def _generate(body, array_center, freq_hz, device_position):
        seed = base_seed + call_count[0]
        call_count[0] += 1

        body_center = device_position if device_position is not None else body.centroids.mean(axis=0)

        viz_out = {} if viz_collector is not None else None
        paths = generate_channel(
            params=params,
            freq_ghz=freq_ghz,
            antenna_pos=array_center,
            body_center=body_center,
            power_dbm=power_dbm,
            seed=seed,
            viz_out=viz_out,
        )

        if viz_collector is not None:
            viz_collector.append(viz_out)

        return paths

    return _generate


def _resolve_mimo_diffraction_model(diffraction_model: str) -> str:
    """Validate the MIMO shadow-gate selector (default ``"fock"``).

    Mirrors the engine default (DECISIONS.md L8) so MIMO scene compute matches
    the single-user coherent engine result. ``"none"`` disables the gate.
    """
    if diffraction_model not in fock_gate.DIFFRACTION_MODELS:
        raise ValueError(f"diffraction_model must be one of {fock_gate.DIFFRACTION_MODELS}, got {diffraction_model!r}")
    return diffraction_model


def build_user_channels(scene: MIMOScene, diffraction_model: str = "fock") -> None:
    """Expand paths and build per-user channels, G_tilde, Q, and h.

    Populates each user's paths, G_tilde, Q, and h fields in-place.
    Skips users that already have all four fields populated.

    ``diffraction_model`` selects the Fock shadow gate folded into G_tilde:
    ``"fock"`` (default, matches the engine) gates the body-surface channel with
    the uniform Fock penumbra; ``"none"`` reproduces the ungated channel.

    Raises ValueError if scene.tissue is None or any user is missing
    body or center_paths.
    """
    if scene.tissue is None:
        raise ValueError("scene.tissue must be set before building channels")

    model = _resolve_mimo_diffraction_model(diffraction_model)
    tissue = scene.tissue

    for user in scene.users:
        # Skip if already fully populated
        if user.paths is not None and user.G_tilde is not None and user.Q is not None and user.h is not None:
            continue

        if user.body is None:
            raise ValueError(f"User {user.config.user_id} has no body mesh")
        if user.center_paths is None:
            raise ValueError(f"User {user.config.user_id} has no center_paths")

        # Expand center paths to per-element paths
        user.paths = expand_paths_to_array(user.center_paths, scene.array, scene.freq_hz)

        # Fock shadow gate keyed on the center directions (matches the factored
        # Fresnel solve, one gate per unique direction).
        fock_R, q_F_s, q_F_h = fock_gate.fock_params(
            user.body,
            user.center_paths.k_hat,
            model,
            scene.freq_hz,
            tissue.n_complex,
        )

        # Body-surface channel G_tilde (factored Fresnel for array-expanded paths)
        user.G_tilde = compute_body_channel_factored(
            normals=user.body.normals,
            centroids=user.body.centroids,
            center_k_hat=user.center_paths.k_hat,
            center_psi=user.center_paths.psi,
            element_psi=user.paths.psi,
            element_index=user.paths.element_index,
            n_tilde=tissue.n_complex,
            sigma=tissue.sigma,
            freq_hz=scene.freq_hz,
            n_elements=scene.array.n_elements,
            fock_R=fock_R,
            q_F_s=q_F_s,
            q_F_h=q_F_h,
        )

        # Exposure operator Q
        user.Q = compute_exposure_operator(user.G_tilde, user.body.areas)

        # Communication channel vector h
        user.h = compute_channel_vector(
            center_paths=user.center_paths,
            array=scene.array,
            device_position=user.config.device_position,
            device_orientation=user.config.device_orientation,
            freq_hz=scene.freq_hz,
        )


def compute_multistream_sab(G_tilde: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Per-triangle absorbed power density from a multi-stream precoder.

    sab[m] = ||G_tilde[m] @ W||_F^2 = sum_k |G_tilde[m] @ w_k|^2

    Parameters
    ----------
    G_tilde : (M_tri, 3, M_ant)
        Body-surface channel.
    W : (M_ant, K)
        Precoding matrix.

    Returns
    -------
    sab : (M_tri,) per-triangle absorbed power density [W/m^2].
    """
    GW = np.einsum("mia,ak->mik", G_tilde, W)  # (M_tri, 3, K)
    return np.sum(np.abs(GW) ** 2, axis=(1, 2))  # (M_tri,)


def compute_mrt_precoder(
    H: np.ndarray,
    total_power: float,
) -> np.ndarray:
    """Maximum Ratio Transmission precoding matrix.

    Parameters
    ----------
    H : (K, M_ant) complex channel matrix. Row k is user k's channel.
    total_power : total transmit power budget P [W].

    Returns
    -------
    W : (M_ant, K) precoding matrix with ||W||_F^2 = P
        and equal power per user: ||w_k||^2 = P/K.
    """
    K, M_ant = H.shape
    if K == 0:
        return np.zeros((M_ant, 0), dtype=complex)
    W = np.zeros((M_ant, K), dtype=complex)
    power_per_user = total_power / K

    for k in range(K):
        h_conj = np.conj(H[k])
        norm = np.linalg.norm(h_conj)
        if norm > 0:
            W[:, k] = h_conj / norm * np.sqrt(power_per_user)
        # If norm == 0, column stays zero (degenerate channel)

    return W


def compute_user_sab(
    G_tilde: np.ndarray,
    W: np.ndarray,
) -> np.ndarray:
    """Per-triangle absorbed power density from body channel and precoder.

    Parameters
    ----------
    G_tilde : (M_tri, 3, M_ant) complex body-surface channel.
    W : (M_ant, K) precoding matrix.

    Returns
    -------
    sab : (M_tri,) real, non-negative. sab[m] = ||G_tilde[m] @ W||_F^2.
    """
    # GW[m, i, k] = sum_j G_tilde[m, i, j] * W[j, k]
    GW = np.einsum("mij,jk->mik", G_tilde, W)
    sab = np.sum(np.abs(GW) ** 2, axis=(1, 2))
    return np.real(sab)


def compute_total_exposure(
    Q: np.ndarray,
    W: np.ndarray,
) -> float:
    """Total absorbed power from exposure operator and precoder.

    Parameters
    ----------
    Q : (M_ant, M_ant) Hermitian PSD exposure operator.
    W : (M_ant, K) precoding matrix.

    Returns
    -------
    P_abs : real scalar, trace(W^H Q W).
    """
    return float(np.real(np.trace(W.conj().T @ Q @ W)))


def _default_los_paths(
    body: BodyMesh,
    array_center: np.ndarray,
    freq_hz: float,
    device_position: np.ndarray | None = None,
) -> PropagationPaths:
    """Create a single LOS path from the array toward the device (or body centroid).

    When *device_position* is given the path points from the array toward the
    device, which is the physically correct target for MRT beamforming. The
    body is in the near-field path of this beam, so the same k_hat also drives
    the body-surface exposure channel.

    Parameters
    ----------
    body : BodyMesh
    array_center : (3,) array phase center position [m].
    freq_hz : carrier frequency [Hz].
    device_position : (3,) optional device location in world coords [m].
        Falls back to the body centroid when not provided.

    Returns
    -------
    PropagationPaths with a single LOS path.
    """
    target = device_position if device_position is not None else body.centroids.mean(axis=0)
    direction = target - array_center
    dist = np.linalg.norm(direction)
    k_hat = np.array([[0.0, 0.0, -1.0]]) if dist < 1e-15 else (direction / dist).reshape(1, 3)

    # Unit-amplitude x-polarised psi (perpendicular to k_hat)
    # Use free-space: |E| = sqrt(2 * Z0 * S_inc), but for unit power just use 1 V/m
    psi = np.zeros((1, 3), dtype=complex)
    # Pick polarisation perpendicular to k_hat
    abs_k = np.abs(k_hat[0])
    ref = np.zeros(3)
    ref[np.argmin(abs_k)] = 1.0
    e_pol = np.cross(k_hat[0], ref)
    e_pol = e_pol / np.linalg.norm(e_pol)
    psi[0] = e_pol.astype(complex)

    delay = np.array([dist / C_0])

    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.array([0], dtype=np.intp),
        delay=delay,
        is_los=np.array([True]),
    )


def compute_mimo_scene(
    scene: MIMOScene,
    engine: DosimetryEngine,
    precoder_type: str = "zf",
    noise_power: float = DEFAULT_NOISE_POWER,
    P_abs_max: float = DEFAULT_P_ABS_MAX,
    diffraction_model: str = "fock",
) -> dict:
    """Full multi-user MIMO dosimetry pipeline.

    1. Build per-user channels (G_tilde, Q, h).
    2. Assemble H and compute multi-user precoder W.
    3. For each user, compute sab and build DosimetryResult.

    Parameters
    ----------
    scene : MIMOScene
        Scene with array, users, tissue, etc.
    engine : DosimetryEngine
        Dosimetry engine (tissue must match scene.tissue).
    precoder_type : str
        One of "mrt", "zf", "mmse", "zf_exposure".
    noise_power : float
        Noise power for MMSE precoder.
    P_abs_max : float
        Per-user absorbed power limit for zf_exposure.
    diffraction_model : str
        Shadow-edge gate "none" | "fock" (default "fock", matches the engine).

    Returns
    -------
    dict with keys:
        W : (M_ant, K) precoding matrix
        precoder_type : str
        per_user_p_abs : list of float
    """
    if not scene.users:
        raise ValueError("Scene has no users")

    # Step 1: build channels
    build_user_channels(scene, diffraction_model=diffraction_model)

    # Step 2: assemble H and Q, compute precoder
    H = scene.all_h()
    Q_list = scene.all_Q()

    W = compute_precoder(
        H,
        precoder_type=precoder_type,
        P=scene.total_power,
        noise_power=noise_power,
        Q_list=Q_list,
        P_abs_max=P_abs_max,
    )

    # Step 3: per-user dosimetry
    from aegis.engine import coherent_sinc

    per_user_p_abs = []
    for user in scene.users:
        sab = compute_multistream_sab(user.G_tilde, W)
        sinc = coherent_sinc(
            user.body.centroids,
            user.paths.k_hat,
            user.paths.psi,
            user.paths.element_index,
            W,
            scene.freq_hz,
        )

        result = engine._build_result(
            user.body,
            user.paths,
            sab,
            fidelity_level=7,
            Q=user.Q,
            freq_hz=scene.freq_hz,
            sinc=sinc,
        )
        user.result = result
        per_user_p_abs.append(result.p_abs)

    return {
        "W": W,
        "precoder_type": precoder_type,
        "per_user_p_abs": per_user_p_abs,
    }


def compute_mimo_scene_with_bodies(
    scene: MIMOScene,
    bodies: dict[str, BodyMesh],
    level: int = 7,
    generate_paths_fn: Callable | None = None,
    precoder_type: str = "mrt",
    diffraction_model: str = "fock",
) -> dict:
    """Full multi-user MIMO compute pipeline with body positioning.

    Orchestrates per-user body channel, precoding, Sab computation,
    and engine-level compliance stats. Bodies are loaded from the provided
    dict and translated to each user's position.

    Parameters
    ----------
    scene : MIMOScene with users, array, freq_hz, total_power.
    bodies : dict mapping phantom_name -> BodyMesh (canonical, at origin).
    level : fidelity level for engine.compute (7 or 8).
    generate_paths_fn : optional callable(body, array_center, freq_hz, device_position) -> PropagationPaths.
        Defaults to _default_los_paths if None.
    precoder_type : "mrt", "zf", "mmse", or "zf_exposure".
    diffraction_model : shadow-edge gate "none" | "fock" (default "fock",
        matches the engine).

    Returns
    -------
    dict with keys: user_ids, timings, precoder_type, weights_real, weights_imag.
    """
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh as _BodyMesh
    from aegis.tissue.dielectric import TissueModel

    model = _resolve_mimo_diffraction_model(diffraction_model)
    timings: dict[str, float] = {}
    t_total_start = time.perf_counter()

    if not scene.users:
        timings["total_ms"] = 0.0
        return {"user_ids": [], "timings": timings, "precoder_type": "mrt"}

    if generate_paths_fn is None:
        generate_paths_fn = _default_los_paths

    # Resolve tissue model
    tissue = scene.tissue
    if tissue is None:
        tissue = TissueModel("Skin 28 GHz", eps_r=17.0, sigma=25.0, freq_hz=scene.freq_hz)

    freq_hz = scene.freq_hz
    array = scene.array

    # Phase 1: per-user body channel, Q, h
    t_channels_start = time.perf_counter()
    for user in scene.users:
        cfg = user.config

        # Load and position body
        if cfg.phantom_name not in bodies:
            raise KeyError(f"No body mesh for phantom {cfg.phantom_name!r}")
        base_body = bodies[cfg.phantom_name]

        # Rotate and translate body to user position
        offset = cfg.position
        theta = cfg.orientation
        if abs(theta) > 1e-9:
            c, s = np.cos(theta), np.sin(theta)
            R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])  # z-axis rotation
            # vertices: (N_tri, 3, 3) -> rotate each vertex
            verts_flat = base_body.vertices.reshape(-1, 3) @ R.T
            vertices = verts_flat.reshape(base_body.vertices.shape) + offset[None, None, :]
            norms_flat = base_body.normals.reshape(-1, 3) @ R.T
            normals = norms_flat.reshape(base_body.normals.shape)
            centroids = (base_body.centroids @ R.T) + offset[None, :]
        else:
            vertices = base_body.vertices + offset[None, None, :]
            normals = base_body.normals.copy()
            centroids = base_body.centroids + offset[None, :]
        body = _BodyMesh(
            vertices=vertices,
            normals=normals,
            centroids=centroids,
            areas=base_body.areas.copy(),
            name=base_body.name,
        )
        user.body = body

        # Generate center paths toward the device (beam target)
        center_paths = generate_paths_fn(body, array.reference_position, freq_hz, cfg.device_position)
        user.center_paths = center_paths

        # Expand to per-element paths
        paths = expand_paths_to_array(center_paths, array, freq_hz)
        user.paths = paths

        # Compute body channel G_tilde using factored Fresnel
        # This computes Fresnel for N_center directions instead of N_center*M_elements,
        # giving ~M_elements speedup (e.g. 16x for 4x4 UPA)
        n_tilde = tissue.n_complex
        # Fock shadow gate keyed on the center directions (one gate per unique
        # direction, matching the factored Fresnel solve and the engine default).
        fock_R, q_F_s, q_F_h = fock_gate.fock_params(body, center_paths.k_hat, model, freq_hz, n_tilde)
        G_tilde = compute_body_channel_factored(
            normals=body.normals,
            centroids=body.centroids,
            center_k_hat=center_paths.k_hat,
            center_psi=center_paths.psi,
            element_psi=paths.psi,
            element_index=paths.element_index,
            n_tilde=n_tilde,
            sigma=tissue.sigma,
            freq_hz=freq_hz,
            n_elements=array.n_elements,
            fock_R=fock_R,
            q_F_s=q_F_s,
            q_F_h=q_F_h,
        )
        user.G_tilde = G_tilde

        # Exposure operator Q
        Q = compute_exposure_operator(G_tilde, body.areas)
        user.Q = Q

        # Communication channel h
        h = compute_channel_vector(
            center_paths,
            array,
            cfg.device_position,
            cfg.device_orientation,
            freq_hz,
        )
        user.h = h

    timings["channels_ms"] = (time.perf_counter() - t_channels_start) * 1e3

    # Check for degenerate channel matrix (all user channels near-zero)
    warning: str | None = None
    H_check = np.array([u.h for u in scene.users])
    h_norms = np.linalg.norm(H_check, axis=1)
    n_degenerate = int(np.sum(h_norms < NUMERICAL_FLOOR))
    if n_degenerate == len(scene.users):
        warning = "All MIMO channels are degenerate (near-zero). Try elevating the antenna above ground level."
    elif n_degenerate > 0:
        warning = (
            f"{n_degenerate} of {len(scene.users)} user channels are degenerate. "
            "Some users may show 0 W/m\u00b2. Try repositioning the antenna."
        )

    # Phase 2: precoder from stacked H
    t_precoder_start = time.perf_counter()
    H = scene.all_h()
    Q_list = [u.Q for u in scene.users] if precoder_type == "zf_exposure" else None
    W = compute_precoder(
        H,
        precoder_type=precoder_type,
        P=scene.total_power,
        Q_list=Q_list,
        P_abs_max=DEFAULT_P_ABS_MAX if Q_list else None,
    )
    timings["precoder_ms"] = (time.perf_counter() - t_precoder_start) * 1e3

    # Phase 3: per-user Sab and engine compliance
    from aegis.engine import coherent_sinc

    t_sab_start = time.perf_counter()
    engine = DosimetryEngine(tissue)

    for user in scene.users:
        sab = compute_multistream_sab(user.G_tilde, W)
        user._sab_raw = sab
        sinc = coherent_sinc(
            user.body.centroids,
            user.paths.k_hat,
            user.paths.psi,
            user.paths.element_index,
            W,
            freq_hz,
        )

        # Build result directly from multi-stream SAB (total exposure from all beams)
        # This matches compute_mimo_scene and gives consistent heatmap + stats
        result = engine._build_result(
            user.body,
            user.paths,
            sab,
            fidelity_level=level,
            Q=user.Q,
            freq_hz=freq_hz,
            sinc=sinc,
        )
        user.result = result

    timings["sab_and_engine_ms"] = (time.perf_counter() - t_sab_start) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total_start) * 1e3

    result = {
        "user_ids": scene.user_ids,
        "timings": timings,
        "precoder_type": precoder_type,
        "weights_real": W.real.tolist(),
        "weights_imag": W.imag.tolist(),
    }
    if warning is not None:
        result["warning"] = warning
    return result

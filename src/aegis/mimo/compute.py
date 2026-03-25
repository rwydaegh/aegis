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

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import C_0
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.precoders import compute_precoder
from aegis.paths import PropagationPaths

if TYPE_CHECKING:
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.mimo.scene import MIMOScene


def build_user_channels(scene: MIMOScene) -> None:
    """Expand paths and build per-user channels, G_tilde, Q, and h.

    Populates each user's paths, G_tilde, Q, and h fields in-place.
    Skips users that already have all four fields populated.

    Raises ValueError if scene.tissue is None or any user is missing
    body or center_paths.
    """
    if scene.tissue is None:
        raise ValueError("scene.tissue must be set before building channels")

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

        # Body-surface channel G_tilde
        user.G_tilde = compute_body_channel(
            normals=user.body.normals,
            centroids=user.body.centroids,
            k_hat=user.paths.k_hat,
            psi=user.paths.psi,
            element_index=user.paths.element_index,
            n_tilde=tissue.n_complex,
            sigma=tissue.sigma,
            freq_hz=scene.freq_hz,
            n_elements=scene.array.n_elements,
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
) -> PropagationPaths:
    """Create a single LOS path from the array center toward the body centroid.

    The path direction is from the array toward the body. The psi vector is
    set to a unit-amplitude x-polarised plane wave.

    Parameters
    ----------
    body : BodyMesh
    array_center : (3,) array phase center position [m].
    freq_hz : carrier frequency [Hz].

    Returns
    -------
    PropagationPaths with a single LOS path.
    """
    centroid = body.centroids.mean(axis=0)
    direction = centroid - array_center
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
    noise_power: float = 0.01,
    P_abs_max: float = 0.1,
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
    build_user_channels(scene)

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
    per_user_p_abs = []
    for user in scene.users:
        sab = compute_multistream_sab(user.G_tilde, W)

        result = engine._build_result(
            user.body,
            user.paths,
            sab,
            fidelity_level=7,
            Q=user.Q,
            freq_hz=scene.freq_hz,
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
) -> dict:
    """Full multi-user MIMO compute pipeline with body positioning.

    Orchestrates per-user body channel, MRT precoding, Sab computation,
    and engine-level compliance stats. Bodies are loaded from the provided
    dict and translated to each user's position.

    Parameters
    ----------
    scene : MIMOScene with users, array, freq_hz, total_power.
    bodies : dict mapping phantom_name -> BodyMesh (canonical, at origin).
    level : fidelity level for engine.compute (7 or 8).
    generate_paths_fn : optional callable(body, array_center, freq_hz) -> PropagationPaths.
        Defaults to _default_los_paths if None.

    Returns
    -------
    dict with keys: user_ids, timings, precoder_type.
    """
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh as _BodyMesh
    from aegis.precoder import Precoder
    from aegis.tissue.dielectric import TissueModel

    timings: dict[str, float] = {}
    t_total_start = time.perf_counter()

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

        # Translate body to user position
        offset = cfg.position
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

        # Generate center paths
        center_paths = generate_paths_fn(body, array.reference_position, freq_hz)
        user.center_paths = center_paths

        # Expand to per-element paths
        paths = expand_paths_to_array(center_paths, array, freq_hz)
        user.paths = paths

        # Compute body channel G_tilde
        n_tilde = tissue.n_complex
        G_tilde = compute_body_channel(
            normals=body.normals,
            centroids=body.centroids,
            k_hat=paths.k_hat,
            psi=paths.psi,
            element_index=paths.element_index,
            n_tilde=n_tilde,
            sigma=tissue.sigma,
            freq_hz=freq_hz,
            n_elements=array.n_elements,
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

    # Phase 2: MRT precoder from stacked H
    t_precoder_start = time.perf_counter()
    H = scene.all_h()
    W = compute_mrt_precoder(H, scene.total_power)
    timings["precoder_ms"] = (time.perf_counter() - t_precoder_start) * 1e3

    # Phase 3: per-user Sab and engine compliance
    t_sab_start = time.perf_counter()
    engine = DosimetryEngine(tissue)

    for user in scene.users:
        sab = compute_user_sab(user.G_tilde, W)
        user._sab_raw = sab

        # Run engine for compliance stats (level 7 with precoder)
        # Extract this user's column from W
        user_idx = scene.users.index(user)
        w_k = W[:, user_idx]
        precoder = Precoder(x=w_k)

        result = engine.compute(
            body=user.body,
            paths=user.paths,
            level=level,
            precoder=precoder,
            h=user.h,
            freq_hz=freq_hz,
        )
        user.result = result

    timings["sab_and_engine_ms"] = (time.perf_counter() - t_sab_start) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total_start) * 1e3

    return {
        "user_ids": scene.user_ids,
        "timings": timings,
        "precoder_type": "mrt",
    }

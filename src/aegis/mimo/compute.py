"""MIMO compute orchestrator: precoding, per-user Sab, and full pipeline.

Public functions:
- compute_mrt_precoder: MRT (matched filter) precoding matrix
- compute_user_sab: per-triangle Sab from body channel and precoder
- compute_total_exposure: total absorbed power via exposure operator
- compute_mimo_scene: full multi-user pipeline orchestrator

Design doc: section D1.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from aegis.constants import C_0
from aegis.paths import PropagationPaths

if TYPE_CHECKING:
    from aegis.geometry.mesh import BodyMesh
    from aegis.mimo.scene import MIMOScene


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
    bodies: dict[str, BodyMesh],
    level: int = 7,
    generate_paths_fn: Callable | None = None,
) -> dict:
    """Full multi-user MIMO compute pipeline.

    Orchestrates per-user body channel, MRT precoding, Sab computation,
    and engine-level compliance stats.

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
    from aegis.coherent.body_channel import compute_body_channel
    from aegis.coherent.exposure_operator import compute_exposure_operator
    from aegis.engine import DosimetryEngine
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.mimo.channel import compute_channel_vector
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
        from aegis.geometry.mesh import BodyMesh

        body = BodyMesh(
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
        from aegis.precoder import Precoder

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

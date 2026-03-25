"""MIMO scene orchestrator: build channels, compute precoders, run dosimetry.

Connects the Phase 1 data model (MIMOScene, UserState) with the coherent
pipeline (body_channel, exposure_operator) and multi-user precoders.

Design doc: section E1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.precoders import compute_precoder

if TYPE_CHECKING:
    from aegis.engine import DosimetryEngine
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

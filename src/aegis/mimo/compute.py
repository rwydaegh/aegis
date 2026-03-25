"""Multi-user MIMO orchestrator.

Computes the full multi-user pipeline: per-user body channels, exposure
operators, communication channels, precoding, and per-user dosimetry.

The engine stays single-body. This module loops over users externally.

Design doc: section E1 (orchestration), E4 (multi-stream heatmap).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator, eigendecompose_Q
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.precoders import PrecoderMatrix
from aegis.mimo.scene import MIMOScene
from aegis.result import DosimetryResult


@dataclass
class MIMOResult:
    """Result of multi-user MIMO computation.

    Attributes
    ----------
    precoder : the multi-user precoding matrix W.
    user_results : dict mapping user_id -> DosimetryResult.
    user_p_abs : dict mapping user_id -> total absorbed power on that body.
    """

    precoder: PrecoderMatrix
    user_results: dict[str, DosimetryResult] = field(default_factory=dict)
    user_p_abs: dict[str, float] = field(default_factory=dict)

    @property
    def total_p_abs(self) -> float:
        """Total absorbed power across all bodies."""
        return sum(self.user_p_abs.values())


def compute_per_user_channels(scene: MIMOScene) -> None:
    """Compute body channel G_tilde, exposure operator Q, and comm channel h for each user.

    Populates user.G_tilde, user.Q, and user.h on each UserState in the scene.
    Requires user.body and user.paths (expanded) to be set.
    Also requires user.center_paths for the communication channel.

    Parameters
    ----------
    scene : MIMOScene with users having body, paths, and center_paths populated.
    """
    tissue = scene.tissue
    if tissue is None:
        raise ValueError("Scene requires a TissueModel")

    n_tilde = tissue.n_complex
    sigma = tissue.sigma
    freq_hz = scene.freq_hz

    for user in scene.users:
        if user.body is None:
            raise ValueError(f"User {user.config.user_id} has no body mesh")
        if user.paths is None:
            raise ValueError(f"User {user.config.user_id} has no paths")

        body = user.body
        paths = user.paths

        # Body-surface channel G_tilde(r): (M_tri, 3, M_ant)
        user.G_tilde = compute_body_channel(
            body.normals,
            body.centroids,
            paths.k_hat,
            paths.psi,
            paths.element_index,
            n_tilde,
            sigma,
            freq_hz,
            scene.array.n_elements,
        )

        # Exposure operator Q: (M_ant, M_ant) Hermitian PSD
        user.Q = compute_exposure_operator(user.G_tilde, body.areas)

        # Communication channel h: (M_ant,) complex
        if user.center_paths is not None:
            user.h = compute_channel_vector(
                user.center_paths,
                scene.array,
                user.config.device_position,
                user.config.device_orientation,
                freq_hz,
            )


def compute_multiuser_sab(
    G_tilde: np.ndarray,
    W: np.ndarray,
) -> np.ndarray:
    """Compute per-triangle Sab for one body under multi-stream precoding.

    Sab_u(r) = ||G_tilde_u(r) @ W||_F^2

    This is the expected absorbed power density when all K streams carry
    uncorrelated unit-power data symbols (monograph eq:Sab-MU-expect).

    Parameters
    ----------
    G_tilde : (M_tri, 3, M_ant) body-surface channel for this user.
    W : (M_ant, K) precoding matrix.

    Returns
    -------
    sab : (M_tri,) absorbed power density per triangle [W/m^2].
    """
    # field = G_tilde @ W: (M_tri, 3, K)
    field_mat = np.einsum("mia,ak->mik", G_tilde, W)

    # Sab(r) = sum over polarization and streams of |field|^2
    sab = np.real(np.sum(np.conj(field_mat) * field_mat, axis=(1, 2)))
    return np.maximum(sab, 0.0)


def compute_mimo_scene(
    scene: MIMOScene,
    precoder: PrecoderMatrix,
    body_mass: float | None = None,
) -> MIMOResult:
    """Run the full multi-user dosimetry computation.

    Given a scene with pre-computed G_tilde and Q for each user, and a
    precoding matrix W, compute the per-user absorbed power density maps.

    Parameters
    ----------
    scene : MIMOScene with G_tilde and Q populated for all users.
    precoder : PrecoderMatrix with W of shape (M_ant, K).
    body_mass : body mass [kg] for SAR computation (optional).

    Returns
    -------
    MIMOResult with per-user DosimetryResult and absorbed power.
    """
    K = scene.n_users
    M_ant = scene.array.n_elements

    if precoder.n_elements != M_ant:
        raise ValueError(f"Precoder has {precoder.n_elements} elements, array has {M_ant}")
    if precoder.n_users != K:
        raise ValueError(f"Precoder serves {precoder.n_users} users, scene has {K}")

    result = MIMOResult(precoder=precoder)

    for user in scene.users:
        uid = user.config.user_id

        if user.G_tilde is None:
            raise ValueError(f"User {uid} has no body channel G_tilde")

        body = user.body
        sab = compute_multiuser_sab(user.G_tilde, precoder.W)

        # Total absorbed power: P_abs = trace(W^H Q W)
        if user.Q is not None:
            p_abs = float(np.real(np.trace(precoder.W.conj().T @ user.Q @ precoder.W)))
        else:
            p_abs = float(np.sum(sab * body.areas))

        result.user_p_abs[uid] = p_abs

        # Eigendecompose Q for this user
        eigenvalues = None
        if user.Q is not None:
            eigenvalues, _ = eigendecompose_Q(user.Q)
            eigenvalues = np.asarray(eigenvalues)

        sar_wb = None
        if body_mass is not None and body_mass > 0:
            sar_wb = p_abs / body_mass

        user_result = DosimetryResult(
            sab=sab,
            p_abs=p_abs,
            fidelity_level=7,
            sar_wb=sar_wb,
            Q=np.asarray(user.Q) if user.Q is not None else None,
            eigenvalues=eigenvalues,
            rho=None,
            freq_hz=scene.freq_hz,
        )

        user.result = user_result
        result.user_results[uid] = user_result

    return result

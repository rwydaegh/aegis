"""Shared Fock shadow-gate parameter helpers.

Both the engine (``aegis.engine``) and the MIMO compute path
(``aegis.mimo.compute``) need the same Fock radius and representative impedance
eigenvalues so their coherent results agree triangle for triangle. This module
is the single source of truth; both callers delegate here.

The soft creeping wave keeps the PEC eigenvalue (``q_F_s = None``); the hard
eigenvalue is a single representative value per (band, body) computed at the
median curved-face radius (DECISIONS.md L10).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from aegis.constants import C_0

if TYPE_CHECKING:
    from aegis.geometry.mesh import BodyMesh

# Engine-layer diffraction-gate selectors.
DIFFRACTION_MODELS = ("none", "gelu", "fock")

# Representative-radius guards for the scalar impedance-Fock hard eigenvalue.
# Flat faces clamp to 1/eps (~1e6 m) in fock_radius; exclude them from the
# median so they do not skew the representative body radius. The kR_rep used for
# the single mpmath pole solve is clamped to the validated grid [4, 2048].
FOCK_FLAT_R_CAP = 1e3
FOCK_KR_MIN = 4.0
FOCK_KR_MAX = 2048.0


def fock_radius_per_path(body: BodyMesh, k_hat: np.ndarray) -> np.ndarray:
    """In-incidence-plane radius for each path direction.

    ``k_hat`` is ``(N, 3)`` (one direction per path), so a single path yields
    ``(M,)`` and multiple paths yield ``(M, N)`` (the kernel broadcasts
    ``(M,) -> (M, 1)`` and uses ``(M, N)`` as is). ``principal_curvatures`` is
    cached per body inside ``geometry.curvature``, so the repeated per-path calls
    only redo the cheap Euler projection.
    """
    from aegis.geometry import curvature

    kh = np.asarray(k_hat, dtype=float)
    if kh.ndim == 1:
        kh = kh[None, :]
    if kh.shape[0] == 1:
        return curvature.fock_radius(body, kh[0])
    return np.stack([curvature.fock_radius(body, kh[n]) for n in range(kh.shape[0])], axis=1)


def fock_params(
    body: BodyMesh,
    k_hat: np.ndarray,
    model: str,
    freq_hz: float,
    n_tilde: complex,
) -> tuple[np.ndarray | None, complex | None, complex | None]:
    """Fock radius and the representative impedance-corrected eigenvalues.

    Returns ``(fock_R, q_F_s, q_F_h)``. For any non-Fock model returns
    ``(None, None, None)`` so the gate paths stay untouched. ``kR_rep`` uses the
    median curved-face radius, clamped to the validated grid for the one cached
    mpmath pole solve.
    """
    if model != "fock":
        return None, None, None
    from aegis.kernels import fock

    fock_R = fock_radius_per_path(body, k_hat)
    eta = complex(1.0 / n_tilde)
    if eta.imag <= 0:
        raise ValueError(f"eta = 1/n_tilde must have Im(eta) > 0 (passive skin, n - ik convention), got {eta}")
    R_arr = np.asarray(fock_R, dtype=float)
    finite = np.isfinite(R_arr)
    curved = finite & (R_arr < FOCK_FLAT_R_CAP)
    sample = R_arr[curved] if np.any(curved) else R_arr[finite]
    R_rep = float(np.median(sample)) if sample.size else 1.0
    k0 = 2.0 * np.pi * freq_hz / C_0
    kR_rep = float(np.clip(k0 * R_rep, FOCK_KR_MIN, FOCK_KR_MAX))
    q_F_h = fock.fock_impedance_param(eta, kR_rep, "hard")
    return fock_R, None, q_F_h

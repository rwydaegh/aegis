"""UL-pilot calibration of the on-device twin (v4 §sec:closedloop).

We fit the body-side calibration ladder:
  Tier C: per-region complex scale gamma_b in C^R, R = 6 anatomical regions
  Tier B: SVD-truncated mode coefficients gamma_k in C^K
  Tier A: per-triangle ridge gamma_t (research-only)

Each tier's fit is ridge least-squares against a "measured" cascaded channel
generated from a perturbed ground-truth body, anchored to the on-device
prediction h_pred from the un-perturbed twin.
"""

from __future__ import annotations

import numpy as np


def partition_thelonious_regions(centroids: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """Coarse 6-region partition of the Thelonious upper-torso mesh.

    Without proper SMPL-X joint-bone weights we partition by spatial
    coordinates relative to the body's bounding box. Returns an integer
    label in {0..5} per triangle:
       0: head (top z)
       1: torso-front (low z, front)
       2: torso-back (low z, back)
       3: left arm (negative y)
       4: right arm (positive y)
       5: lower (just torso bottom band)
    Thelonious is upper torso + head only, so "arms" / "legs" are limited
    to the side-of-torso bands.
    """
    bb_min = centroids.min(axis=0)
    bb_max = centroids.max(axis=0)
    dim = bb_max - bb_min

    z_norm = (centroids[:, 2] - bb_min[2]) / max(dim[2], 1e-9)
    y_norm = (centroids[:, 1] - bb_min[1]) / max(dim[1], 1e-9)
    nx = normals[:, 0]

    label = np.full(len(centroids), 5, dtype=np.int8)
    # Head: top 25%
    label[z_norm > 0.75] = 0
    # Below head: split by front/back via x-normal sign and by y for arms
    body_mask = (z_norm <= 0.75) & (z_norm > 0.10)
    # arms: outermost ~15% on each y end
    is_left = body_mask & (y_norm < 0.15)
    is_right = body_mask & (y_norm > 0.85)
    label[is_left] = 3
    label[is_right] = 4
    # the rest of the body torso: front (nx > 0) vs back (nx < 0)
    is_torso = body_mask & ~is_left & ~is_right
    label[is_torso & (nx > 0)] = 1
    label[is_torso & (nx <= 0)] = 2
    # lower band stays at label=5
    return label


def per_region_h_body(Lambda: np.ndarray, region_labels: np.ndarray, R: int = 6) -> np.ndarray:
    """Partial cascaded-channel coefficient per region.

    Lambda has shape (M, T_vis); region_labels has shape (T_vis,).
    Returns h_per_region of shape (R, M).
    """
    M = Lambda.shape[0]
    h_per_region = np.zeros((R, M), dtype=np.complex128)
    for b in range(R):
        mask = region_labels == b
        if mask.any():
            h_per_region[b] = Lambda[:, mask].sum(axis=1)
    return h_per_region


def fit_tier_d(
    h_meas: np.ndarray,
    h_los: np.ndarray,
    h_body_pred: np.ndarray,
    *,
    rho: float = 1e-3,
):
    """Tier-D fit: single complex scalar gamma_0 such that
    h_pred(gamma_0) = h_los + gamma_0 * h_body_pred.

    This is the simplest deployable calibration: it absorbs an overall
    amplitude+phase miscalibration on the body-side prediction. In the
    far-BS regime where Lambda has rank 1, this is the identifiable
    parametrization (any per-region perturbation projects onto this single
    scalar).
    """
    a = h_body_pred  # (M,)
    y = h_meas - h_los
    aHa = float(np.real(np.vdot(a, a)))
    aHy = complex(np.vdot(a, y))
    gamma_hat = (aHy + rho) / (aHa + rho)
    residual = y - gamma_hat * a
    return gamma_hat, np.linalg.norm(residual) / max(np.linalg.norm(y), 1e-30)


def fit_tier_c(
    h_meas: np.ndarray,
    h_los: np.ndarray,
    h_per_region: np.ndarray,
    *,
    rho: float = 1e-3,
):
    """Tier-C fit: gamma in C^R, h_pred(gamma) = h_los + sum_b gamma_b h_per_region[b].

    Solves
       gamma_hat = argmin || h_meas - h_los - sum_b gamma_b h_b ||^2
                    + rho * || gamma - 1 ||^2

    Returns gamma_hat in C^R.
    """
    R, M = h_per_region.shape
    A = h_per_region.T  # (M, R)
    y = h_meas - h_los  # (M,)
    # ridge LS:  (A^H A + rho I) gamma = A^H y + rho 1
    AhA = A.conj().T @ A
    Ahy = A.conj().T @ y
    G = AhA + rho * np.eye(R)
    rhs = Ahy + rho * np.ones(R, dtype=np.complex128)
    gamma_hat = np.linalg.solve(G, rhs)
    residual = y - A @ gamma_hat
    return gamma_hat, np.linalg.norm(residual) / max(np.linalg.norm(y), 1e-30)


def fit_tier_b(
    h_meas: np.ndarray,
    h_los: np.ndarray,
    Lambda: np.ndarray,
    *,
    K: int = 20,
    rho: float = 1e-3,
):
    """Tier-B fit: gamma in C^K via SVD-truncated mode coefficients.

    Lambda has shape (M, T_vis). SVD it: Lambda = U S V^H. Truncate to top K.
    Then h_body(gamma) = U_K diag(s_K) gamma_K (where gamma_K coefficients
    weight each mode; gamma_K = 1 recovers the un-calibrated twin).

    Solves
       gamma_hat = argmin || h_meas - h_los - U_K S_K gamma ||^2
                    + rho * || gamma - 1 ||^2
    """
    U, S, Vh = np.linalg.svd(Lambda, full_matrices=False)
    K_eff = min(K, len(S))
    # Use unit-norm basis (columns of U) and gamma absorbs s_k. This keeps
    # the ridge well-scaled across many orders of singular-value magnitude.
    A = U[:, :K_eff]  # (M, K), columns have unit norm
    y = h_meas - h_los
    AhA = A.conj().T @ A   # = I_K
    Ahy = A.conj().T @ y
    # Initial guess in this normalized basis: alpha_k that recovers the
    # un-perturbed prediction h_body = sum_k s_k * u_k * 1 = sum_k s_k u_k.
    alpha_init = S[:K_eff]
    G = AhA + rho * np.eye(K_eff)
    rhs = Ahy + rho * alpha_init
    alpha_hat = np.linalg.solve(G, rhs)
    # Convert alpha back to per-mode gamma scale: gamma_k = alpha_k / s_k
    gamma_hat = alpha_hat / np.where(S[:K_eff] > 1e-30, S[:K_eff], 1.0)
    residual = y - A @ alpha_hat
    h_body_pred = A @ alpha_hat
    return dict(
        gamma=gamma_hat,
        h_body_pred=h_body_pred,
        rel_residual=np.linalg.norm(residual) / max(np.linalg.norm(y), 1e-30),
        S=S,
        U=U[:, :K_eff],
        K_eff=K_eff,
        spectral_mass=float(np.sum(S[:K_eff] ** 2) / np.sum(S ** 2)),
    )


def synthesize_perturbed_truth(
    h_los: np.ndarray,
    h_per_region: np.ndarray,
    *,
    region_perturbation: np.ndarray,
    snr_db: float = 20.0,
    rng: np.random.Generator | None = None,
):
    """Generate a synthetic 'measured' cascaded channel at known per-region
    perturbation gamma_true, plus complex AWGN at the requested SNR.

    Returns
    -------
    h_meas : (M,) complex
    gamma_true : (R,) complex (=region_perturbation)
    """
    if rng is None:
        rng = np.random.default_rng(42)
    h_body_perturbed = (region_perturbation[:, None] * h_per_region).sum(axis=0)
    h_clean = h_los + h_body_perturbed
    sig_pow = float(np.sum(np.abs(h_clean) ** 2))
    noise_pow = sig_pow / 10 ** (snr_db / 10)
    noise = rng.standard_normal(len(h_clean)) + 1j * rng.standard_normal(len(h_clean))
    noise *= np.sqrt(noise_pow / (2 * len(noise)))
    return h_clean + noise, region_perturbation

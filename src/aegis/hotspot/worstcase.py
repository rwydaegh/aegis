"""Worst-case local exposure: the largest field a precoder can drive at a point.

For a local channel G(r) in C^{3 x M} (free-space field channel, or the
tissue-weighted body channel G_tilde(r)), the local intensity under a precoder
x is ||G(r) x||^2. Over all unit-power precoders ||x||^2 = P the maximum is

    max_x ||G x||^2 = P * sigma_max(G)^2 = P * lambda_max(G^H G),

reached by the leading right singular vector x_opt = sqrt(P) * conj(v_max).
This is the exposure eigenvalue at r: the worst case any beamformer could
create there, independent of what it was trying to do. A communication
precoder (maximum ratio transmission, matched to the free-space co-pol
channel) generally falls short of it, especially at the skin, where the
tissue Fresnel filter rotates the optimal direction away from the
communication one.

Comparing the three levels at fixed power and fixed regional illumination,

    decohered floor   <=   MRT focus   <=   worst-case eigen-focus,

separates the part of any "MIMO raises exposure" claim that is beamforming
(steering power to the body) from the part that is coherent local focusing,
and bounds the latter by the eigenvalue rather than by one heuristic precoder.
"""

from __future__ import annotations

import numpy as np


def local_max_intensity(G: np.ndarray, power: float = 1.0) -> tuple[float, np.ndarray]:
    """Worst-case ``||G x||^2`` over ``||x||^2 = power`` and the precoder for it.

    Returns ``(lambda_max * power, x_opt)`` with ``x_opt`` the unit-power-scaled
    leading right singular vector of ``G``.
    """
    G = np.asarray(G)
    u, s, vh = np.linalg.svd(G, full_matrices=False)
    x_opt = np.conj(vh[0]) * np.sqrt(power)
    return float(s[0] ** 2 * power), x_opt


def worst_case_map(G_stack: np.ndarray, power: float = 1.0) -> np.ndarray:
    """Per-point worst-case intensity ``lambda_max(G(r)^H G(r)) * power``.

    Parameters
    ----------
    G_stack : (Q, 3, M) complex
        A local channel at each of Q points (e.g. ``compute_body_channel``
        over all body triangles).

    Returns
    -------
    (Q,) float
        The worst-case ``||G x||^2`` at each point. For the tissue channel this
        is the worst-case absorbed power density a unit-power precoder can
        deposit there.
    """
    G_stack = np.asarray(G_stack)
    # batched SVD over the leading axis; take the top singular value squared
    s = np.linalg.svd(G_stack, compute_uv=False)  # (Q, 3)
    return (s[:, 0] ** 2) * power


def intensity_under(G: np.ndarray, x: np.ndarray) -> float:
    """``||G x||^2`` for a given precoder (the realised local intensity)."""
    return float(np.sum(np.abs(np.asarray(G) @ np.asarray(x)) ** 2))


def worst_case_body(
    normals: np.ndarray,
    centroids: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
    n_elements: int,
    *,
    chunk: int = 256,
    return_argmax: bool = False,
):
    """Worst-case absorbed power density at every body triangle.

    Builds the tissue channel ``G_tilde(r)`` (paper coherent absorption law)
    in triangle chunks to bound memory, and returns the exposure eigenvalue
    ``lambda_max(G_tilde^H G_tilde)`` at each triangle: the largest absorbed
    power density any unit-power precoder could deposit there. With
    ``return_argmax`` also returns the precoder that maximises the single hot
    triangle, useful for visualising the worst case.
    """
    from aegis.coherent.body_channel import compute_body_channel

    normals = np.asarray(normals)
    centroids = np.asarray(centroids)
    T = normals.shape[0]
    out = np.empty(T, dtype=float)
    hot_x = None
    hot_val = -np.inf
    for a in range(0, T, chunk):
        b = min(a + chunk, T)
        G = np.asarray(
            compute_body_channel(
                normals[a:b],
                centroids[a:b],
                k_hat,
                psi,
                element_index,
                n_tilde,
                sigma,
                freq_hz,
                n_elements,
            )
        )  # (c, 3, M)
        s = np.linalg.svd(G, compute_uv=False)  # (c, 3)
        out[a:b] = s[:, 0] ** 2
        if return_argmax:
            i = int(np.argmax(out[a:b]))
            if out[a + i] > hot_val:
                hot_val = float(out[a + i])
                _, x = local_max_intensity(G[i])
                hot_x = x
    if return_argmax:
        return out, hot_x, int(np.argmax(out))
    return out

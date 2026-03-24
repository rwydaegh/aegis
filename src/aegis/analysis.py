"""Path contribution analysis for dosimetry results.

Answers: which propagation paths contribute most to the peak exposure?
This is essential for importance sampling in ray tracing, understanding
exposure hotspots, and identifying dominant paths for mitigation.
"""

from __future__ import annotations

import numpy as np

from aegis.geometry.mesh import BodyMesh
from aegis.kernels._base import fresnel_weights, incidence_geometry
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel


def path_contributions(
    body: BodyMesh,
    paths: PropagationPaths,
    tissue: TissueModel,
    *,
    triangle_index: int | None = None,
    top_k: int | None = None,
) -> dict:
    """Compute per-path contribution to absorbed power density.

    For the geometric+Fresnel kernel (level 3), the contribution of path n
    to triangle m is: c_{m,n} = T_avg(mu_{m,n}) * ReLU(mu_{m,n}) * power_n.
    Total S_ab(m) = sum_n c_{m,n}.

    Parameters
    ----------
    body : BodyMesh
    paths : PropagationPaths
    tissue : TissueModel
    triangle_index : int or None
        If given, compute contributions to this specific triangle.
        If None, compute contributions to the triangle with peak S_ab.
    top_k : int or None
        If given, return only the top-k contributing paths.

    Returns
    -------
    dict with keys:
        triangle_index : int, the target triangle
        sab_total : float, total S_ab at the target triangle
        path_indices : (K,) indices of contributing paths (sorted by contribution)
        contributions : (K,) per-path contribution to S_ab [W/m^2]
        fractions : (K,) fractional contribution (sums to 1)
        cumulative : (K,) cumulative fraction
        k_hat : (K, 3) directions of contributing paths
        power : (K,) incident power density of contributing paths
    """
    mu, mu_plus = incidence_geometry(body.normals, paths.k_hat)
    _, _, T_avg = fresnel_weights(mu, tissue.n_complex)

    # Per-(triangle, path) contribution matrix: (M, N)
    C = np.asarray(T_avg * mu_plus)
    power = np.asarray(paths.power)

    # Total S_ab per triangle
    sab = C @ power

    if triangle_index is None:
        triangle_index = int(np.argmax(sab))

    # Contributions from each path to the target triangle
    c_m = C[triangle_index, :] * power  # (N,)
    sab_total = float(np.sum(c_m))

    # Sort by contribution (descending)
    order = np.argsort(c_m)[::-1]

    if top_k is not None:
        order = order[:top_k]

    c_sorted = c_m[order]
    fractions = c_sorted / sab_total if sab_total > 0 else np.zeros_like(c_sorted)

    return {
        "triangle_index": triangle_index,
        "sab_total": sab_total,
        "path_indices": order,
        "contributions": c_sorted,
        "fractions": fractions,
        "cumulative": np.cumsum(fractions),
        "k_hat": paths.k_hat[order],
        "power": power[order],
    }


def exposure_heatmap(
    body: BodyMesh,
    paths: PropagationPaths,
    tissue: TissueModel,
) -> np.ndarray:
    """Compute full (M, N) contribution matrix.

    Returns C where C[m, n] is the contribution of path n to triangle m's S_ab.
    S_ab = C @ ones gives per-triangle totals (but S_ab is already C @ power,
    so this matrix shows the spatial-angular coupling).

    Parameters
    ----------
    body : BodyMesh
    paths : PropagationPaths
    tissue : TissueModel

    Returns
    -------
    C : (M, N) contribution matrix where C[m,n] = T_avg(mu) * ReLU(mu) * power_n
    """
    mu, mu_plus = incidence_geometry(body.normals, paths.k_hat)
    _, _, T_avg = fresnel_weights(mu, tissue.n_complex)
    power = np.asarray(paths.power)
    return np.asarray(T_avg * mu_plus) * power[np.newaxis, :]


def path_importance(
    body: BodyMesh,
    paths: PropagationPaths,
    tissue: TissueModel,
) -> np.ndarray:
    """Compute per-path importance score for the overall exposure.

    importance_n = sum_m area_m * C[m, n], i.e. the contribution of path n
    to total absorbed power P_abs. Paths with high importance are the ones
    to keep when pruning for faster computation.

    Parameters
    ----------
    body : BodyMesh
    paths : PropagationPaths
    tissue : TissueModel

    Returns
    -------
    importance : (N,) per-path importance [W], sums to P_abs
    """
    mu, mu_plus = incidence_geometry(body.normals, paths.k_hat)
    _, _, T_avg = fresnel_weights(mu, tissue.n_complex)
    # Contract areas with the (M, N) kernel without materializing it:
    # importance_n = sum_m area_m * T_avg(m,n) * mu_plus(m,n) * power_n
    #              = (areas @ (T_avg * mu_plus)) * power
    weighted = np.asarray(body.areas) @ np.asarray(T_avg * mu_plus)
    return weighted * np.asarray(paths.power)

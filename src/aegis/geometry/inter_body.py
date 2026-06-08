"""Single specular inter-body recapture (``inter_body='specular1'``).

Phase B3 of the Fock framework. The master surface law captures first-bounce
absorption only. At each illuminated point a fraction ``1 - T0`` of the
incident power is reflected, and on a non-convex body part of that reflected
power can re-illuminate another body part (across the gap between the legs,
between an arm and the torso, under the chin). This module casts one
mirror-reflected ray per lit triangle, reuses the visibility BVH of
:mod:`aegis.geometry.occlusion`, and deposits the recaptured power at the hit
triangle with that triangle's own Fresnel transmittance and incidence.

It is a single bounce (no recursion) and an additive correction on top of the
direct law. See ``theory/unified/sec_09_interbody.tex`` for the derivation and
the validated bounds (body-averaged enhancement <= 8%, worst concavity ~1.85x).
"""

from __future__ import annotations

import numpy as np

from aegis.geometry import occlusion as occ
from aegis.geometry.mesh import BodyMesh
from aegis.kernels._base import fresnel_weights
from aegis.paths import PropagationPaths

_LIT_EPS = 1e-9


def specular1_sab(
    body: BodyMesh,
    paths: PropagationPaths,
    n_tilde: complex,
) -> np.ndarray:
    """Additional per-triangle Sab from one specular inter-body recapture bounce.

    For each lit triangle ``m`` (incidence cosine ``mu_m > 0``) the specular
    direction is ``k_refl = k_hat - 2 (k_hat . n_m) n_m`` and the reflected
    power fraction is the Fresnel reflectance ``rho_R(m) = 1 - T0(mu_m)``. One
    BVH ray is cast from the triangle centroid along ``k_refl``; if it strikes
    another body triangle ``m'``, the incident power density ``Sinc_m * rho_R``
    is deposited at ``m'`` and weighted by ``m'``'s own transmittance and
    incidence ``T0(mu') * ReLU(mu')``.

    Parameters
    ----------
    body : BodyMesh
    paths : PropagationPaths (incoherent power per direction is used)
    n_tilde : complex tissue refractive index

    Returns
    -------
    (M,) array of additional Sab [W/m^2], all non-negative.
    """
    normals = np.asarray(body.normals, dtype=np.float64)
    centroids = np.asarray(body.centroids, dtype=np.float64)
    M = body.n_triangles
    k_hat = np.asarray(paths.k_hat, dtype=np.float64)
    power = np.asarray(paths.power, dtype=np.float64)
    N = k_hat.shape[0]

    sab_extra = np.zeros(M, dtype=np.float64)
    if N == 0 or M == 0:
        return sab_extra

    tri = occ._precompute_triangle_data(body.vertices)
    bvh, tri_order = occ.build_bvh(tri["tri_bmin"], tri["tri_bmax"], centroids, max_leaf=8)
    eps_o = 1e-6 * body.scale
    t_min = 10.0 * eps_o

    for n in range(N):
        if power[n] <= 0.0:
            continue
        k = k_hat[n]
        mu = normals @ (-k)  # (M,) direct incidence cosine
        lit = np.where(mu > _LIT_EPS)[0]
        if lit.size == 0:
            continue

        n_lit = normals[lit]
        mu_lit = mu[lit]
        # Specular reflection of the incident ray: k_refl = k - 2(k.n)n = k + 2 mu n.
        k_refl = k[None, :] + 2.0 * mu_lit[:, None] * n_lit  # (L, 3), unit length

        # Reflected power fraction rho_R = 1 - T0(mu) (Fresnel reflectance).
        _, _, t_avg_in = fresnel_weights(mu_lit, n_tilde)
        rho_R = 1.0 - np.asarray(t_avg_in, dtype=np.float64)  # (L,)

        origins = centroids[lit] + eps_o * n_lit
        hits = occ.batch_closest_hits(origins, k_refl, lit.astype(np.int32), bvh, tri_order, tri, t_min)

        valid = hits >= 0
        if not np.any(valid):
            continue
        mp = hits[valid]  # hit triangle indices
        kr = k_refl[valid]
        inc_power = power[n] * rho_R[valid]  # incident power density delivered to m'

        # Incidence of the reflected ray onto the hit triangle.
        mu_p = np.einsum("vj,vj->v", normals[mp], -kr)
        front = mu_p > _LIT_EPS
        if not np.any(front):
            continue
        mp = mp[front]
        mu_p = mu_p[front]
        inc_power = inc_power[front]

        _, _, t_avg_out = fresnel_weights(mu_p, n_tilde)
        deposit = inc_power * np.asarray(t_avg_out, dtype=np.float64) * mu_p
        np.add.at(sab_extra, mp, deposit)

    return sab_extra

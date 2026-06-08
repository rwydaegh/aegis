"""Per-triangle curvature for the Fock diffraction gate.

The Fock detour parameter needs the normal curvature in the plane of incidence,
not twice-mean-curvature. A cylinder has H = 1/R (one principal curvature is
zero), so 2/H = 2R would be twice the true radius and the penumbra width
(kR)^{-1/3} off by 2^{1/3}. Since the cylinder is a primary validation oracle,
``fock_radius`` forms the in-plane radius directly from the principal curvatures
via Euler's theorem.

- ``principal_curvatures``: local quadric (osculating-jet / Taubin) fit over a
  k-NN centroid neighborhood, giving the two principal curvatures and the
  direction of the larger one. Cached per body on a rigid-invariant content hash.
- ``fock_radius``: the in-incidence-plane radius for a given incidence direction.
- ``face_curvature``: twice-mean-curvature (kappa1 + kappa2), the promoted viewer
  proxy used by the legacy level-curvature term and the viewer.
"""

from __future__ import annotations

import hashlib
import threading

import numpy as np
import numpy.typing as npt
from scipy.spatial import cKDTree

from aegis.geometry.mesh import BodyMesh

_EPS = 1e-12
_DEFAULT_K = 18
_CACHE_MAX = 32

_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
_cache_lock = threading.Lock()


def _content_hash(body: BodyMesh) -> int:
    """Rigid-transform-invariant cache key sensitive to surface shape.

    Curvature is pose-independent, so the key uses only translation- and
    rotation-invariant descriptors: sorted per-triangle edge lengths, areas,
    sorted centroid radii, and the singular values of the normal matrix. Unlike
    ``BodyMesh.geometry_hash`` it folds in the normals (via rotation-invariant
    singular values), so two meshes that share an edge/area spectrum but differ
    in surface shape (e.g. a flat sheet vs one with tilted triangles) do not
    collide in the cache.
    """
    edge_vecs = np.roll(body.vertices, -1, axis=1) - body.vertices
    edge_lengths = np.sort(np.linalg.norm(edge_vecs, axis=2), axis=1)
    centered = body.centroids - body.centroids.mean(axis=0, keepdims=True)
    radii = np.sort(np.linalg.norm(centered, axis=1))
    normal_svals = np.linalg.svd(body.normals, compute_uv=False)

    h = hashlib.sha256(body.areas.astype(np.float32).tobytes())
    h.update(edge_lengths.astype(np.float32).tobytes())
    h.update(radii.astype(np.float32).tobytes())
    h.update(normal_svals.astype(np.float32).tobytes())
    digest = h.digest()[:8]
    return hash((int.from_bytes(digest, "little"), body.n_triangles))


def _tangent_basis(normals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two orthonormal tangent vectors per face, completing each outward normal."""
    m = normals.shape[0]
    ref = np.tile(np.array([1.0, 0.0, 0.0]), (m, 1))
    alt = np.tile(np.array([0.0, 1.0, 0.0]), (m, 1))
    use_alt = np.abs(normals[:, 0]) > 0.9
    ref = np.where(use_alt[:, None], alt, ref)
    t1 = np.cross(normals, ref)
    t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), _EPS)
    t2 = np.cross(normals, t1)
    t2 /= np.maximum(np.linalg.norm(t2, axis=1, keepdims=True), _EPS)
    return t1, t2


def _principal_curvatures(body: BodyMesh, k: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    centroids = body.centroids
    normals = body.normals
    m = body.n_triangles

    kappa1 = np.zeros(m, dtype=np.float64)
    kappa2 = np.zeros(m, dtype=np.float64)
    dir1 = np.zeros((m, 3), dtype=np.float64)
    if m == 0:
        return kappa1, kappa2, dir1

    k = min(max(k, 3), m)
    tree = cKDTree(centroids)
    _, idx = tree.query(centroids, k=k)
    idx = np.atleast_2d(idx)

    t1, t2 = _tangent_basis(normals)

    # Neighbor offsets in the local (t1, t2, n) frame of each face.
    rel = centroids[idx] - centroids[:, None, :]  # (M, k, 3)
    u = np.einsum("mkj,mj->mk", rel, t1)
    v = np.einsum("mkj,mj->mk", rel, t2)
    h = np.einsum("mkj,mj->mk", rel, normals)

    # Quadric height fit h = c0 + c1 u + c2 v + c3 u^2/2 + c4 uv + c5 v^2/2.
    # Linear terms absorb centroid offset and normal misalignment; the Hessian
    # (c3, c4, c5) is the second fundamental form in the orthonormal tangent
    # basis. Solved per face via regularized normal equations.
    ones = np.ones_like(u)
    design = np.stack([ones, u, v, 0.5 * u * u, u * v, 0.5 * v * v], axis=-1)  # (M, k, 6)
    ata = np.einsum("mki,mkj->mij", design, design)
    ath = np.einsum("mki,mk->mi", design, h)
    ata += 1e-12 * np.eye(6)[None, :, :]
    coeffs = np.linalg.solve(ata, ath[:, :, None])[:, :, 0]  # (M, 6)

    # Shape operator = -Hessian so convex outward bodies get positive curvature.
    a = -coeffs[:, 3]
    b = -coeffs[:, 4]
    d = -coeffs[:, 5]

    mean = 0.5 * (a + d)
    diff = np.sqrt(np.maximum(0.25 * (a - d) ** 2 + b * b, 0.0))
    kappa1 = mean + diff  # larger principal curvature
    kappa2 = mean - diff

    # Eigenvector of kappa1 for [[a, b], [b, d]]: (b, kappa1 - a), with a fallback
    # to the dominant axis when the matrix is (near) isotropic / diagonal.
    e0 = b
    e1 = kappa1 - a
    enorm = np.sqrt(e0 * e0 + e1 * e1)
    degenerate = enorm < _EPS
    e0 = np.where(degenerate, np.where(a >= d, 1.0, 0.0), e0)
    e1 = np.where(degenerate, np.where(a >= d, 0.0, 1.0), e1)
    enorm = np.sqrt(e0 * e0 + e1 * e1)
    e0 /= enorm
    e1 /= enorm
    dir1 = e0[:, None] * t1 + e1[:, None] * t2

    return kappa1, kappa2, dir1


def principal_curvatures(
    body: BodyMesh, k_neighbors: int = _DEFAULT_K
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Per-face principal curvatures and the direction of the larger one.

    Returns ``(kappa1, kappa2, dir1)`` with ``kappa1 >= kappa2``, each of shape
    (M,) for the curvatures and (M, 3) for ``dir1`` (a unit tangent vector).
    Curvature is positive for a convex (outward-bulging) surface. Cached per body
    on a rigid-transform-invariant content hash, so moved or rotated copies hit
    the cache.
    """
    key = _content_hash(body)
    with _cache_lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached

    result = _principal_curvatures(body, k_neighbors)

    with _cache_lock:
        while len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = result
    return result


def fock_radius(body: BodyMesh, k_hat: npt.ArrayLike, eps: float = 1e-6) -> npt.NDArray[np.float64]:
    """In-incidence-plane principal radius of curvature, per face.

    Projects ``k_hat`` into each face's tangent plane, takes the angle ``phi`` to
    the principal direction ``dir1``, and applies Euler's theorem
    ``kappa_t = kappa1 cos^2 phi + kappa2 sin^2 phi``. Returns ``R = 1/kappa_t``
    clamped so flat faces give a large radius (recovering ReLU in the gate).

    ``k_hat`` may be a single direction (3,) (far field) or per-face (M, 3). Both
    return shape (M,). At normal incidence (the ray parallel to the face normal,
    so the tangential projection vanishes) the in-plane direction is degenerate;
    the larger principal curvature ``kappa1`` is used.

    For a sphere this returns R for any direction (isotropic); for a cylinder with
    the ray normal to the axis it returns R, not 2R.
    """
    kappa1, kappa2, d1 = principal_curvatures(body)
    normals = body.normals
    m = body.n_triangles

    kh = np.asarray(k_hat, dtype=np.float64)
    if kh.ndim == 1:
        kh = np.broadcast_to(kh, (m, 3))
    elif kh.shape != (m, 3):
        raise ValueError(f"k_hat must be (3,) or ({m}, 3), got {kh.shape}")

    # Project k_hat into the tangent plane and resolve onto (d1, d2 = n x d1).
    proj = kh - np.einsum("mj,mj->m", kh, normals)[:, None] * normals
    pn = np.linalg.norm(proj, axis=1)
    d2 = np.cross(normals, d1)

    cos_c = np.einsum("mj,mj->m", proj, d1)
    sin_c = np.einsum("mj,mj->m", proj, d2)

    valid = pn > 1e-9
    pn_safe = np.where(valid, pn, 1.0)
    cos2 = np.where(valid, (cos_c / pn_safe) ** 2, 1.0)
    sin2 = np.where(valid, (sin_c / pn_safe) ** 2, 0.0)

    kappa_t = kappa1 * cos2 + kappa2 * sin2
    return 1.0 / np.maximum(kappa_t, eps)


def face_curvature(body: BodyMesh) -> npt.NDArray[np.float64]:
    """Twice-mean-curvature ``H = kappa1 + kappa2`` per face, in 1/m.

    The promoted viewer proxy. Used by the legacy level-curvature term and the
    viewer; the Fock gate uses ``fock_radius`` instead.
    """
    kappa1, kappa2, _ = principal_curvatures(body)
    return kappa1 + kappa2

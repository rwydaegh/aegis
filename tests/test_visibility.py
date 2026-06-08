"""Tests for the per-body self-shadowing visibility LUT primitives.

Covers the foundational chunk (plan tasks 1-5): pose-dependent vertex hash,
octahedral encode/decode, the VisibilityLUT dataclass + int8 codec + bilinear
gather, the binary visibility oracle, and the convexity short-circuit.
"""

from __future__ import annotations

import numpy as np

from aegis.geometry.mesh import BodyMesh

# ---------------------------------------------------------------------------
# Task 1: BodyMesh.vertex_hash (pose-dependent content hash)
# ---------------------------------------------------------------------------


def test_vertex_hash_changes_under_rotation():
    body = BodyMesh.sphere(radius=0.3, n_subdivisions=1)
    R = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    rotated = BodyMesh.from_arrays((body.vertices @ R.T), name="rot")
    assert body.vertex_hash != rotated.vertex_hash
    # geometry_hash is rigid-invariant, so it must NOT change
    assert body.geometry_hash == rotated.geometry_hash


def test_vertex_hash_stable_same_mesh():
    body = BodyMesh.sphere(radius=0.3, n_subdivisions=1)
    again = BodyMesh.from_arrays(body.vertices.copy(), name="again")
    assert body.vertex_hash == again.vertex_hash


# ---------------------------------------------------------------------------
# Task 2: octahedral encode/decode
# ---------------------------------------------------------------------------


def test_oct_roundtrip():
    from aegis.geometry.visibility import oct_decode, oct_encode

    rng = np.random.default_rng(0)
    v = rng.standard_normal((2000, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    u = oct_encode(v)
    assert u.shape == (2000, 2)
    assert np.all(np.abs(u) <= 1.0 + 1e-9)
    back = oct_decode(u)
    assert np.allclose(back, v, atol=1e-6)


def test_oct_decode_unit_norm():
    from aegis.geometry.visibility import oct_decode

    rng = np.random.default_rng(1)
    u = rng.uniform(-1, 1, (500, 2))
    w = oct_decode(u)
    assert np.allclose(np.linalg.norm(w, axis=1), 1.0, atol=1e-6)


# ---------------------------------------------------------------------------
# Task 3: VisibilityLUT dataclass + int8 codec + bilinear gather
# ---------------------------------------------------------------------------


def test_int8_codec_roundtrip():
    from aegis.geometry.visibility import CLEARANCE_SCALE, _decode_int8, _encode_int8

    c = np.array([0.0, 0.1, -0.1, 1.0, -1.0])  # last two saturate
    q = _encode_int8(c)
    assert q.dtype == np.int8
    d = _decode_int8(q)
    assert np.allclose(d[:3], np.clip(c[:3], -127 * CLEARANCE_SCALE, 127 * CLEARANCE_SCALE), atol=CLEARANCE_SCALE)
    assert d[3] == 127 * CLEARANCE_SCALE
    assert d[4] == -127 * CLEARANCE_SCALE


def test_lut_bilinear_gather_constant_field():
    # A LUT whose clearance is a constant +0.2 everywhere returns ~0.2 for any direction.
    from aegis.geometry.visibility import (
        CLEARANCE_SCALE,
        VisibilityLUT,
        _encode_int8,
        _gather_clearance,
    )

    R = 8
    clr = _encode_int8(np.full((1, R, R), 0.2))
    lut = VisibilityLUT(
        clearance=clr,
        clearance_scale=CLEARANCE_SCALE,
        d_occ=np.array([0.05], np.float32),
        R_occ=np.array([0.02], np.float32),
        active_index=np.array([0], np.int32),
        exposed_mask=np.array([False]),
        resolution=R,
        vertex_hash=0,
    )
    rng = np.random.default_rng(0)
    dirs = rng.standard_normal((100, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    c = _gather_clearance(lut, np.zeros(100, np.int32), dirs)  # active row 0 for all
    assert np.allclose(c, 0.2, atol=2 * CLEARANCE_SCALE)


# ---------------------------------------------------------------------------
# Task 4: binary visibility oracle
# ---------------------------------------------------------------------------


def test_compute_visibility_convex_all_visible():
    from aegis.geometry.visibility import compute_visibility

    body = BodyMesh.sphere(radius=0.3, n_subdivisions=2)
    k_hats = np.array([[0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])  # source from +z, +x
    vis = compute_visibility(body, k_hats)  # (M, N) bool
    mu = body.normals @ (-k_hats.T)  # (M, N)
    # On a convex body every front-facing facet (mu>0) sees the source.
    assert np.all(vis[mu > 1e-6])


def test_compute_visibility_two_spheres_occlusion():
    # Two separated spheres: facets on the far sphere facing a source behind the
    # near sphere are shadowed.
    from aegis.geometry.visibility import compute_visibility

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    verts = np.concatenate([a.vertices, b.vertices])
    body = BodyMesh.from_arrays(verts, name="two_spheres")
    k = np.array([[1.0, 0.0, 0.0]])  # source at -x; sphere a shadows sphere b
    vis = compute_visibility(body, k)[:, 0]
    nb = a.n_triangles
    mu = body.normals @ (-k[0])
    # some facets of sphere b that face -x (mu>0) must be shadowed by sphere a
    shadowed_b = (~vis[nb:]) & (mu[nb:] > 0.1)
    assert shadowed_b.sum() > 0


def test_compute_visibility_matches_brute_force():
    # The BVH oracle must agree with a naive all-triangles brute-force ray check
    # on the concave two-sphere fixture.
    from aegis.geometry.visibility import compute_visibility

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=1)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.55, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    k_hats = np.array([[1.0, 0.0, 0.0], [0.3, 0.4, 0.2]])
    k_hats = k_hats / np.linalg.norm(k_hats, axis=1, keepdims=True)
    vis = compute_visibility(body, k_hats)

    brute = _brute_force_visibility(body, k_hats)
    assert np.array_equal(vis, brute)


def _brute_force_visibility(body: BodyMesh, k_hats: np.ndarray) -> np.ndarray:
    """Naive O(M*N*M) front-hemisphere visibility check (test oracle)."""
    eps = 1e-6 * body.scale
    t_min = 10.0 * eps
    delta = 1e-4
    verts = body.vertices
    v0 = verts[:, 0]
    e1 = verts[:, 1] - verts[:, 0]
    e2 = verts[:, 2] - verts[:, 0]
    M = body.n_triangles
    N = k_hats.shape[0]
    out = np.ones((M, N), dtype=bool)
    for i in range(M):
        n_i = body.normals[i]
        origin = body.centroids[i] + eps * n_i
        for j in range(N):
            omega = -k_hats[j]
            if float(np.dot(omega, n_i)) <= delta:
                continue  # back-facing -> visible by convention
            hit = False
            for t_idx in range(M):
                if t_idx == i:
                    continue
                tt = _ray_tri_t(origin, omega, v0[t_idx], e1[t_idx], e2[t_idx], t_min)
                if tt > 0.0:
                    hit = True
                    break
            out[i, j] = not hit
    return out


def _ray_tri_t(origin, d, v0, e1, e2, t_min):
    p = np.cross(d, e2)
    det = float(np.dot(e1, p))
    if abs(det) < 1e-12:
        return -1.0
    inv = 1.0 / det
    tvec = origin - v0
    u = float(np.dot(tvec, p)) * inv
    if u < 0.0 or u > 1.0:
        return -1.0
    q = np.cross(tvec, e1)
    v = float(np.dot(d, q)) * inv
    if v < 0.0 or (u + v) > 1.0:
        return -1.0
    t = float(np.dot(e2, q)) * inv
    return t if t > t_min else -1.0


# ---------------------------------------------------------------------------
# Task 5: convexity short-circuit
# ---------------------------------------------------------------------------


def test_is_convex_sphere_and_concave():
    from aegis.geometry.visibility import _is_convex

    assert _is_convex(BodyMesh.sphere(radius=0.3, n_subdivisions=2))
    a = BodyMesh.sphere(radius=0.2, n_subdivisions=1)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    two = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    assert not _is_convex(two)


# ---------------------------------------------------------------------------
# Task 6: ray-cast bake (binary map + binding distance + occluder index)
# ---------------------------------------------------------------------------


def test_bake_raw_records_binding_distance():
    from aegis.geometry.visibility import _bake_raw_maps

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    R = 16
    vis, d2, occ_idx, grid_dirs = _bake_raw_maps(body, resolution=R)
    assert vis.shape == (body.n_triangles, R, R)
    assert grid_dirs.shape == (R, R, 3)
    # blocked cells carry a finite positive binding distance and a valid occluder
    blocked = ~vis
    assert blocked.any()
    assert np.all(d2[blocked] > 0)
    assert np.all((occ_idx[blocked] >= 0) & (occ_idx[blocked] < body.n_triangles))
    # visible cells carry no binding occluder
    assert np.all(occ_idx[vis] == -1)


def test_bake_raw_convex_all_visible():
    from aegis.geometry.visibility import _bake_raw_maps

    body = BodyMesh.sphere(radius=0.3, n_subdivisions=2)
    vis, d2, occ_idx, grid_dirs = _bake_raw_maps(body, resolution=16)
    # a convex body never self-shadows a front-facing direction
    mu = body.normals @ grid_dirs.reshape(-1, 3).T  # (M, R*R)
    front = mu.reshape(vis.shape) > 1e-3
    assert np.all(vis[front])

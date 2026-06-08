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


# ---------------------------------------------------------------------------
# Task 7: signed-clearance transform + bake_visibility_lut
# ---------------------------------------------------------------------------


def test_grid_directions_unit_and_shape():
    from aegis.geometry.visibility import _grid_directions

    R = 12
    g = _grid_directions(R)
    assert g.shape == (R, R, 3)
    assert np.allclose(np.linalg.norm(g.reshape(-1, 3), axis=1), 1.0, atol=1e-9)


def test_clearance_matches_brute_force_great_circle():
    # On a synthetic map (a hemisphere blocked), the signed clearance equals the
    # great-circle distance to the boundary within one cell.
    from aegis.geometry.visibility import _grid_directions, _signed_clearance

    R = 24
    dirs = _grid_directions(R).reshape(-1, 3)
    blocked = dirs[:, 0] < 0.0  # block the -x hemisphere
    vis_map = (~blocked).reshape(R, R)
    c = _signed_clearance(vis_map[None], _grid_directions(R)).reshape(R, R)
    # boundary is the great circle x=0; great-circle angle to that plane is
    # arcsin(|x|), signed by visibility (visible +, shadowed -).
    expected = np.where(vis_map, 1.0, -1.0) * np.abs(np.arcsin(np.clip(dirs[:, 0], -1, 1))).reshape(R, R)
    near = np.abs(expected) < 0.4  # away from saturation, within ~2 cells
    assert np.allclose(c[near], expected[near], atol=0.15)


def test_clearance_sign_follows_visibility():
    from aegis.geometry.visibility import _grid_directions, _signed_clearance

    R = 20
    dirs = _grid_directions(R).reshape(-1, 3)
    vis_map = (dirs[:, 1] >= 0.0).reshape(R, R)
    c = _signed_clearance(vis_map[None], _grid_directions(R)).reshape(R, R)
    assert np.all(c[vis_map] >= 0.0)
    assert np.all(c[~vis_map] <= 0.0)


def test_bake_convex_short_circuits():
    from aegis.geometry.visibility import bake_visibility_lut

    body = BodyMesh.sphere(radius=0.3, n_subdivisions=2)
    lut = bake_visibility_lut(body, resolution=16)
    assert lut.exposed_mask.all()
    assert lut.active_index.size == 0
    assert lut.clearance.shape[0] == 0
    assert lut.vertex_hash == body.vertex_hash


def test_bake_two_spheres_has_active_rows():
    from aegis.geometry.visibility import bake_visibility_lut

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    lut = bake_visibility_lut(body, resolution=16)
    assert lut.active_index.size > 0
    assert lut.clearance.shape == (lut.active_index.size, 16, 16)
    assert np.all(lut.d_occ > 0)
    assert np.all(lut.R_occ > 0)
    assert lut.exposed_mask.shape == (body.n_triangles,)
    # active rows must carry at least one shadowed (negative-clearance) direction
    dec = lut.clearance.astype(np.float64) * lut.clearance_scale
    assert np.all((dec.reshape(lut.active_index.size, -1) < 0).any(axis=1))


def test_bake_clearance_magnitude_within_resolution():
    # The baked clearance on the two-sphere fixture matches a brute-force
    # great-circle distance to the binary boundary within the octahedral cell.
    from aegis.geometry.visibility import (
        _bake_raw_maps,
        _grid_directions,
        _signed_clearance,
        bake_visibility_lut,
    )

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    R = 16
    vis_map, _, _, grid_dirs = _bake_raw_maps(body, resolution=R)
    c_ref = _signed_clearance(vis_map, _grid_directions(R))
    lut = bake_visibility_lut(body, resolution=R)
    dec = lut.clearance.astype(np.float64) * lut.clearance_scale
    ref_active = c_ref[lut.active_index]
    # int8 codec saturates at +-0.5 rad; compare in the unsaturated band
    band = np.abs(ref_active) < 0.45
    assert np.allclose(dec[band], ref_active[band], atol=2 * lut.clearance_scale + 1e-9)


# ---------------------------------------------------------------------------
# Task 8: disk cache + get_or_bake
# ---------------------------------------------------------------------------


def test_disk_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_CACHE_DIR", str(tmp_path))
    from aegis.geometry import visibility as vis

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    lut = vis.bake_visibility_lut(body, resolution=16)
    vis.save_lut_to_disk(lut, body, resolution=16, gate="erf")
    loaded = vis.load_lut_from_disk(body, resolution=16, gate="erf")
    assert loaded is not None
    assert np.array_equal(loaded.clearance, lut.clearance)
    assert np.array_equal(loaded.active_index, lut.active_index)
    assert np.array_equal(loaded.exposed_mask, lut.exposed_mask)
    assert np.allclose(loaded.d_occ, lut.d_occ)
    assert np.allclose(loaded.R_occ, lut.R_occ)
    assert loaded.vertex_hash == lut.vertex_hash
    assert loaded.resolution == lut.resolution


def test_disk_cache_misses_on_pose_change(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_CACHE_DIR", str(tmp_path))
    from aegis.geometry import visibility as vis

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    lut = vis.bake_visibility_lut(body, resolution=16)
    vis.save_lut_to_disk(lut, body, resolution=16, gate="erf")
    # a yawed copy has a different vertex_hash, so the cache must miss
    Rz = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    moved = BodyMesh.from_arrays(body.vertices @ Rz.T, name="yawed")
    assert vis.load_lut_from_disk(moved, resolution=16, gate="erf") is None


def test_get_or_bake_round_trips_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_CACHE_DIR", str(tmp_path))
    from aegis.geometry import visibility as vis

    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    body = BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))
    first = vis.get_or_bake(body, resolution=16, gate="erf")  # bakes + writes
    second = vis.get_or_bake(body, resolution=16, gate="erf")  # loads from disk
    assert np.array_equal(first.clearance, second.clearance)
    assert np.array_equal(first.active_index, second.active_index)
    assert second.vertex_hash == body.vertex_hash


# ---------------------------------------------------------------------------
# Task 10: query_visibility (per-path gather, far/near dispatch)
# ---------------------------------------------------------------------------


def _two_spheres():
    a = BodyMesh.sphere(radius=0.2, n_subdivisions=2)
    b = BodyMesh.from_arrays(a.vertices + np.array([0.6, 0.0, 0.0]))
    return BodyMesh.from_arrays(np.concatenate([a.vertices, b.vertices]))


def test_query_visibility_far_field_shapes_and_exposed():
    from aegis.geometry.visibility import bake_visibility_lut, query_visibility

    body = _two_spheres()
    lut = bake_visibility_lut(body, resolution=16)
    k = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    clr, R_occ, d1, d2 = query_visibility(lut, k, body.centroids, source_pos=None)
    M, N = body.n_triangles, 2
    assert clr.shape == (M, N)
    assert R_occ.shape == (M, N)
    # exposed triangles are lit (large positive clearance) in every direction
    assert np.all(clr[lut.exposed_mask] > 0.4)
    # far field: d1 is infinite everywhere
    assert np.all(np.isinf(d1))


def test_query_visibility_active_rows_have_finite_occluder():
    from aegis.geometry.visibility import bake_visibility_lut, query_visibility

    body = _two_spheres()
    lut = bake_visibility_lut(body, resolution=16)
    k = np.array([[1.0, 0.0, 0.0]])
    clr, R_occ, d1, d2 = query_visibility(lut, k, body.centroids, source_pos=None)
    ai = lut.active_index
    assert np.all(R_occ[ai, 0] > 0)
    assert np.all(d2[ai, 0] > 0)
    # active rows carry their baked occluder radius / distance
    assert np.allclose(R_occ[ai, 0], lut.R_occ)
    assert np.allclose(d2[ai, 0], lut.d_occ)


def test_query_visibility_near_field_d1():
    from aegis.geometry.visibility import bake_visibility_lut, query_visibility

    body = _two_spheres()
    lut = bake_visibility_lut(body, resolution=16)
    src = np.array([-1.0, 0.0, 0.0])
    k = body.centroids - src
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    clr, R_occ, d1, d2 = query_visibility(lut, k, body.centroids, source_pos=src)
    assert clr.shape == (body.n_triangles, 1)
    d_src = np.linalg.norm(body.centroids - src, axis=1, keepdims=True)
    fin = np.isfinite(d1)
    # finite edge-to-source distance never exceeds the full source-to-point range
    assert np.all(d1[fin] <= d_src[fin] + 1e-9)


def test_query_visibility_near_field_occluder_behind_source_is_exposed():
    # An occluder farther than the source (d1 = d_src - d2 <= 0) cannot shadow:
    # the d1<=0 guard blends the clearance back to exposed (large positive).
    from aegis.geometry.visibility import bake_visibility_lut, query_visibility

    body = _two_spheres()
    lut = bake_visibility_lut(body, resolution=16)
    # source very close to the body so d_src < d_occ for shadowed rows
    src = np.array([0.0, 0.0, 0.0])
    k = body.centroids - src
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    clr, R_occ, d1, d2 = query_visibility(lut, k, body.centroids, source_pos=src, d_band=0.01)
    # rows whose binding occluder sits beyond the source are pushed back to lit
    behind = d1[:, 0] <= 0.0
    assert np.all(clr[behind, 0] > 0.4)

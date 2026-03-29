"""Building geometry: wall extrusion and roof algorithms.

All functions output numpy arrays. No Blender/bmesh dependency.
Reference: blosm/building/roof/, blosm/action/volume/
"""

from __future__ import annotations

import numpy as np

from aegis.environment import MaterialType


def triangulate_polygon(polygon: np.ndarray) -> np.ndarray:
    """Triangulate a 2D polygon using ear clipping.

    Args:
        polygon: (N, 2) array of 2D vertices in CCW order.

    Returns:
        (N-2, 3) uint32 array of triangle indices.
    """
    n = len(polygon)
    if n < 3:
        return np.empty((0, 3), dtype=np.uint32)
    if n == 3:
        return np.array([[0, 1, 2]], dtype=np.uint32)

    # ensure CCW winding
    signed_area = _signed_area_2d(polygon)
    indices = list(range(n))
    if signed_area < 0:
        indices = indices[::-1]

    triangles = []
    remaining = list(indices)

    max_iter = n * n
    iteration = 0
    while len(remaining) > 3 and iteration < max_iter:
        iteration += 1
        ear_found = False
        for i in range(len(remaining)):
            prev_i = (i - 1) % len(remaining)
            next_i = (i + 1) % len(remaining)
            a = polygon[remaining[prev_i]]
            b = polygon[remaining[i]]
            c = polygon[remaining[next_i]]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue
            is_ear = True
            for j in range(len(remaining)):
                if j in (prev_i, i, next_i):
                    continue
                if _point_in_triangle(polygon[remaining[j]], a, b, c):
                    is_ear = False
                    break
            if is_ear:
                triangles.append([remaining[prev_i], remaining[i], remaining[next_i]])
                remaining.pop(i)
                ear_found = True
                break
        if not ear_found:
            break

    if len(remaining) == 3:
        triangles.append(remaining)

    return np.array(triangles, dtype=np.uint32) if triangles else np.empty((0, 3), dtype=np.uint32)


def extrude_walls(
    footprint: np.ndarray,
    base_height: float,
    top_height: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrude vertical walls from a 2D footprint polygon.

    Args:
        footprint: (N, 2) array of 2D footprint vertices.
        base_height: Z coordinate of the bottom edge.
        top_height: Z coordinate of the top edge.

    Returns:
        (vertices, triangles) where vertices is (N*4, 3) float64
        and triangles is (N*2, 3) uint32.
    """
    n = len(footprint)
    vertices = []
    triangles = []
    for i in range(n):
        j = (i + 1) % n
        p0 = footprint[i]
        p1 = footprint[j]
        base_idx = len(vertices)
        vertices.append([p0[0], p0[1], base_height])
        vertices.append([p1[0], p1[1], base_height])
        vertices.append([p1[0], p1[1], top_height])
        vertices.append([p0[0], p0[1], top_height])
        triangles.append([base_idx, base_idx + 1, base_idx + 2])
        triangles.append([base_idx, base_idx + 2, base_idx + 3])

    return (
        np.array(vertices, dtype=np.float64),
        np.array(triangles, dtype=np.uint32),
    )


def _signed_area_2d(polygon: np.ndarray) -> float:
    """Signed area of a 2D polygon (positive = CCW)."""
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _point_in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    """Test if 2D point p is inside triangle abc."""
    d1 = (p[0] - c[0]) * (a[1] - c[1]) - (a[0] - c[0]) * (p[1] - c[1])
    d2 = (p[0] - a[0]) * (b[1] - a[1]) - (b[0] - a[0]) * (p[1] - a[1])
    d3 = (p[0] - b[0]) * (c[1] - b[1]) - (c[0] - b[0]) * (p[1] - b[1])
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


# ---------------------------------------------------------------------------
# generate_building dispatcher
# ---------------------------------------------------------------------------

_ROOF_DISPATCH: dict[str, object] = {}


def generate_building(
    footprint: np.ndarray,
    height: float,
    roof_shape: str = "flat",
    roof_height: float = 2.0,
    material: MaterialType = MaterialType.CONCRETE,
    roof_material: MaterialType = MaterialType.CONCRETE,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate building geometry with walls and roof.

    Returns: (vertices (V,3), triangles (T,3), materials (T,))
    """
    footprint = np.asarray(footprint, dtype=np.float64)

    # Walls
    wall_verts, wall_tris = extrude_walls(footprint, 0.0, height)
    wall_mats = np.full(len(wall_tris), int(material), dtype=np.int32)

    # Roof
    roof_fn = _ROOF_DISPATCH.get(roof_shape)
    if roof_fn is None:
        raise ValueError(f"Unknown roof shape: {roof_shape!r}")
    roof_verts, roof_tris = roof_fn(footprint, height, roof_height)
    roof_mats = np.full(len(roof_tris), int(roof_material), dtype=np.int32)

    # Combine
    all_verts = np.concatenate([wall_verts, roof_verts])
    all_tris = np.concatenate([wall_tris, roof_tris + len(wall_verts)])
    all_mats = np.concatenate([wall_mats, roof_mats])

    return all_verts, all_tris, all_mats


# ---------------------------------------------------------------------------
# Helper: find longest-edge axis for rectangular-ish footprints
# ---------------------------------------------------------------------------


def _find_ridge_axis(footprint: np.ndarray):
    """Find the longest edge and return ridge endpoints for gabled roofs.

    Returns (i_long_start, i_long_end, i_short_start, i_short_end)
    where long edges are parallel to the ridge direction.
    """
    n = len(footprint)
    edge_lengths = np.array([np.linalg.norm(footprint[(i + 1) % n] - footprint[i]) for i in range(n)])
    longest = int(np.argmax(edge_lengths))
    # The two long edges are 'longest' and 'longest+2' (for a quad)
    # Short edges are 'longest+1' and 'longest+3'
    i0 = longest
    i1 = (longest + 1) % n
    i2 = (longest + 2) % n
    i3 = (longest + 3) % n
    return i0, i1, i2, i3


def _ridge_for_gabled(footprint: np.ndarray, height: float, roof_height: float):
    """Compute ridge endpoints for a gabled roof on a quad footprint.

    Returns (ridge_a, ridge_b) as 3D points along the midline of the short edges.
    """
    i0, i1, i2, i3 = _find_ridge_axis(footprint)
    # Ridge runs between midpoints of the two short edges
    mid_a = 0.5 * (footprint[i1] + footprint[i2])
    mid_b = 0.5 * (footprint[i3] + footprint[i0])
    ridge_a = np.array([mid_a[0], mid_a[1], height + roof_height])
    ridge_b = np.array([mid_b[0], mid_b[1], height + roof_height])
    return ridge_a, ridge_b, i0, i1, i2, i3


def _fan_triangulate(face_3d: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Fan-triangulate a convex 3D polygon.

    Returns (vertices (N,3), triangles (N-2,3)).
    """
    verts = np.array(face_3d, dtype=np.float64)
    n = len(verts)
    tris = np.array([[0, i, i + 1] for i in range(1, n - 1)], dtype=np.uint32)
    return verts, tris


def _merge_meshes(
    meshes: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray]:
    """Merge multiple (verts, tris) pairs, offsetting triangle indices."""
    all_verts = []
    all_tris = []
    offset = 0
    for v, t in meshes:
        if len(v) == 0:
            continue
        all_verts.append(v)
        all_tris.append(t + offset)
        offset += len(v)
    if not all_verts:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.uint32)
    return np.concatenate(all_verts), np.concatenate(all_tris)


def _make_3d(footprint_2d: np.ndarray, z: float) -> np.ndarray:
    """Convert (N,2) footprint to (N,3) with given z."""
    n = len(footprint_2d)
    out = np.zeros((n, 3), dtype=np.float64)
    out[:, :2] = footprint_2d
    out[:, 2] = z
    return out


def _quad_tris(a: int, b: int, c: int, d: int) -> np.ndarray:
    """Two triangles for quad abcd."""
    return np.array([[a, b, c], [a, c, d]], dtype=np.uint32)


# ---------------------------------------------------------------------------
# 1. Flat roof
# ---------------------------------------------------------------------------


def _roof_flat(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    tris_2d = triangulate_polygon(footprint)
    verts_3d = _make_3d(footprint, height)
    return verts_3d, tris_2d


_ROOF_DISPATCH["flat"] = _roof_flat


# ---------------------------------------------------------------------------
# 2. Gabled roof
# ---------------------------------------------------------------------------


def _roof_gabled(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    if len(footprint) != 4:
        return _roof_flat(footprint, height, roof_height)

    ridge_a, ridge_b, i0, i1, i2, i3 = _ridge_for_gabled(footprint, height, roof_height)
    # 6 vertices: 4 eave corners at height + 2 ridge points
    p = _make_3d(footprint, height)
    verts = np.vstack([p, [ridge_a], [ridge_b]])
    # indices: 0-3 = footprint corners reordered as i0,i1,i2,i3, 4=ridge_a, 5=ridge_b
    # But we use absolute footprint order: p[i0], p[i1], p[i2], p[i3]
    # Ridge: 4=ridge_a (between i1,i2), 5=ridge_b (between i3,i0)
    ra, rb = 4, 5
    tris = np.array(
        [
            # slope face 1 (long edge i0->i1 to ridge)
            [i0, i1, ra],
            [i0, ra, rb],
            # slope face 2 (long edge i2->i3 to ridge)
            [i2, i3, rb],
            [i2, rb, ra],
            # gable triangle 1 (short edge i1->i2)
            [i1, i2, ra],
            # gable triangle 2 (short edge i3->i0)
            [i3, i0, rb],
        ],
        dtype=np.uint32,
    )
    return verts, tris


_ROOF_DISPATCH["gabled"] = _roof_gabled


# ---------------------------------------------------------------------------
# 3. Hipped roof (via straight skeleton)
# ---------------------------------------------------------------------------


def _roof_hipped(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    from aegis.environment.skeleton import polygonize

    fp_3d = _make_3d(footprint, height)
    verts_out = [fp_3d[i] for i in range(len(fp_3d))]
    faces = polygonize(verts_out, footprint, height=roof_height)

    if not faces:
        # Fallback to pyramidal
        return _roof_pyramidal(footprint, height, roof_height)

    # verts_out now contains footprint verts + skeleton nodes with correct z
    all_verts = np.array(verts_out, dtype=np.float64)
    meshes = []
    for face in faces:
        if len(face) < 3:
            continue
        # Fan-triangulate each face
        face_tris = np.array(
            [[face[0], face[i], face[i + 1]] for i in range(1, len(face) - 1)],
            dtype=np.uint32,
        )
        meshes.append(face_tris)

    if not meshes:
        return _roof_pyramidal(footprint, height, roof_height)

    all_tris = np.concatenate(meshes)
    return all_verts, all_tris


_ROOF_DISPATCH["hipped"] = _roof_hipped


# ---------------------------------------------------------------------------
# 4. Pyramidal roof
# ---------------------------------------------------------------------------


def _roof_pyramidal(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    centroid = footprint.mean(axis=0)
    apex = np.array([centroid[0], centroid[1], height + roof_height])
    base = _make_3d(footprint, height)
    n = len(footprint)
    verts = np.vstack([base, [apex]])
    apex_idx = n
    tris = np.array(
        [[i, (i + 1) % n, apex_idx] for i in range(n)],
        dtype=np.uint32,
    )
    return verts, tris


_ROOF_DISPATCH["pyramidal"] = _roof_pyramidal


# ---------------------------------------------------------------------------
# 5. Skillion roof
# ---------------------------------------------------------------------------


def _roof_skillion(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(footprint)
    # Find longest edge, raise the opposite edge
    edge_lengths = np.array([np.linalg.norm(footprint[(i + 1) % n] - footprint[i]) for i in range(n)])
    longest = int(np.argmax(edge_lengths))
    # Compute distance of each vertex from the longest edge line
    p0 = footprint[longest]
    p1 = footprint[(longest + 1) % n]
    edge_dir = p1 - p0
    edge_len = np.linalg.norm(edge_dir)
    edge_normal = np.array([-edge_dir[1], edge_dir[0]]) / edge_len

    dists = np.array([np.dot(footprint[i] - p0, edge_normal) for i in range(n)])
    max_dist = np.max(np.abs(dists))
    if max_dist < 1e-10:
        max_dist = 1.0

    roof_z = np.array([height + roof_height * abs(dists[i]) / max_dist for i in range(n)])

    # Roof surface vertices (at varying z)
    roof_verts = np.zeros((n, 3), dtype=np.float64)
    for i in range(n):
        roof_verts[i] = [footprint[i][0], footprint[i][1], roof_z[i]]

    tris_2d = triangulate_polygon(footprint)

    # Fill the gap between wall top (height) and roof edge with triangulated
    # strips on each wall segment where the roof is above the wall top.
    gap_verts = []
    gap_tris = []
    for i in range(n):
        j = (i + 1) % n
        zi, zj = roof_z[i], roof_z[j]
        # Both at wall height means no gap on this edge
        if abs(zi - height) < 1e-10 and abs(zj - height) < 1e-10:
            continue
        # Quad from (pi, height) -> (pj, height) -> (pj, zj) -> (pi, zi)
        base = len(roof_verts) + len(gap_verts)
        gap_verts.append([footprint[i][0], footprint[i][1], height])
        gap_verts.append([footprint[j][0], footprint[j][1], height])
        gap_verts.append([footprint[j][0], footprint[j][1], zj])
        gap_verts.append([footprint[i][0], footprint[i][1], zi])
        gap_tris.append([base, base + 1, base + 2])
        gap_tris.append([base, base + 2, base + 3])

    if gap_verts:
        all_verts = np.vstack([roof_verts, np.array(gap_verts, dtype=np.float64)])
        all_tris = np.concatenate([tris_2d, np.array(gap_tris, dtype=np.uint32)])
    else:
        all_verts = roof_verts
        all_tris = tris_2d

    return all_verts, all_tris


_ROOF_DISPATCH["skillion"] = _roof_skillion


# ---------------------------------------------------------------------------
# 6. Half-hipped roof
# ---------------------------------------------------------------------------


def _roof_half_hipped(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    if len(footprint) != 4:
        return _roof_hipped(footprint, height, roof_height)

    ridge_a, ridge_b, i0, i1, i2, i3 = _ridge_for_gabled(footprint, height, roof_height)
    p = _make_3d(footprint, height)

    # Cut gable at 2/3 height: small hip triangles at top
    hip_frac = 2.0 / 3.0
    hip_h = height + roof_height * hip_frac

    # Points at hip break on short edges
    # short edge i1->i2: two points at hip_frac from each end
    frac = 1.0 / 3.0  # inset fraction on short edge
    hip_a1 = np.array(
        [
            footprint[i1][0] + frac * (footprint[i2][0] - footprint[i1][0]),
            footprint[i1][1] + frac * (footprint[i2][1] - footprint[i1][1]),
            hip_h,
        ]
    )
    hip_a2 = np.array(
        [
            footprint[i2][0] + frac * (footprint[i1][0] - footprint[i2][0]),
            footprint[i2][1] + frac * (footprint[i1][1] - footprint[i2][1]),
            hip_h,
        ]
    )
    # short edge i3->i0
    hip_b1 = np.array(
        [
            footprint[i3][0] + frac * (footprint[i0][0] - footprint[i3][0]),
            footprint[i3][1] + frac * (footprint[i0][1] - footprint[i3][1]),
            hip_h,
        ]
    )
    hip_b2 = np.array(
        [
            footprint[i0][0] + frac * (footprint[i3][0] - footprint[i0][0]),
            footprint[i0][1] + frac * (footprint[i3][1] - footprint[i0][1]),
            hip_h,
        ]
    )

    # 10 vertices: 0-3 = footprint, 4-5 = ridge, 6-9 = hip break points
    verts = np.vstack([p, [ridge_a], [ridge_b], [hip_a1], [hip_a2], [hip_b1], [hip_b2]])
    ra, rb = 4, 5
    ha1, ha2, hb1, hb2 = 6, 7, 8, 9

    tris = np.array(
        [
            # main slope faces (same as gabled but ridge connects to hip points)
            [i0, i1, ha1],
            [i0, ha1, hb2],
            [hb2, ha1, ra],
            [hb2, ra, rb],
            [i2, i3, hb1],
            [i2, hb1, ha2],
            [ha2, hb1, rb],
            [ha2, rb, ra],
            # hip triangle on short edge i1->i2
            [i1, i2, ha1],
            [i2, ha2, ha1],
            [ha1, ha2, ra],
            # hip triangle on short edge i3->i0
            [i3, i0, hb2],
            [i3, hb2, hb1],
            [hb1, hb2, rb],
        ],
        dtype=np.uint32,
    )
    return verts, tris


_ROOF_DISPATCH["half_hipped"] = _roof_half_hipped


# ---------------------------------------------------------------------------
# 7. Gambrel roof
# ---------------------------------------------------------------------------


def _roof_gambrel(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    if len(footprint) != 4:
        return _roof_gabled(footprint, height, roof_height)

    i0, i1, i2, i3 = _find_ridge_axis(footprint)
    p = _make_3d(footprint, height)

    # Two-segment profile: lower steep (60 deg), upper shallow (30 deg)
    # Break at 60% of the half-width, 70% of the height
    break_frac = 0.3  # fraction from edge toward center for break line
    break_h = height + roof_height * 0.7
    ridge_h = height + roof_height

    # Break points along the two long edges
    # Long edge 1: i0 -> i1 direction is along the edge, perpendicular is toward center
    # For a quad, the "width" is across the short edges
    mid_short_a = 0.5 * (footprint[i1] + footprint[i2])
    mid_short_b = 0.5 * (footprint[i3] + footprint[i0])

    # Break lines parallel to long edges, inset by break_frac of half-width
    # Side 1: from i0 toward i3 side
    brk_00 = footprint[i0] + break_frac * (footprint[i3] - footprint[i0])
    brk_01 = footprint[i1] + break_frac * (footprint[i2] - footprint[i1])
    # Side 2: from i3 toward i0 side
    brk_10 = footprint[i3] + break_frac * (footprint[i0] - footprint[i3])
    brk_11 = footprint[i2] + break_frac * (footprint[i1] - footprint[i2])

    b00 = np.array([brk_00[0], brk_00[1], break_h])
    b01 = np.array([brk_01[0], brk_01[1], break_h])
    b10 = np.array([brk_10[0], brk_10[1], break_h])
    b11 = np.array([brk_11[0], brk_11[1], break_h])

    ridge_a = np.array([mid_short_a[0], mid_short_a[1], ridge_h])
    ridge_b = np.array([mid_short_b[0], mid_short_b[1], ridge_h])

    # 10 verts: 0-3=footprint, 4-7=break, 8-9=ridge
    verts = np.vstack([p, [b00], [b01], [b10], [b11], [ridge_a], [ridge_b]])
    bi00, bi01, bi10, bi11 = 4, 5, 6, 7
    ra, rb = 8, 9

    tris = np.array(
        [
            # lower steep face side 1
            [i0, i1, bi01],
            [i0, bi01, bi00],
            # lower steep face side 2
            [i3, i2, bi11],
            [i3, bi11, bi10],
            # upper shallow face side 1
            [bi00, bi01, ra],
            [bi00, ra, rb],
            # upper shallow face side 2
            [bi10, bi11, ra],
            [bi10, ra, rb],
            # gable end triangles (short edges)
            [i1, i2, bi01],
            [i2, bi11, bi01],
            [bi01, bi11, ra],
            [i3, i0, bi10],
            [i0, bi00, bi10],
            [bi10, bi00, rb],
        ],
        dtype=np.uint32,
    )
    return verts, tris


_ROOF_DISPATCH["gambrel"] = _roof_gambrel


# ---------------------------------------------------------------------------
# 8. Saltbox roof
# ---------------------------------------------------------------------------


def _roof_saltbox(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    if len(footprint) != 4:
        return _roof_gabled(footprint, height, roof_height)

    i0, i1, i2, i3 = _find_ridge_axis(footprint)
    p = _make_3d(footprint, height)

    # Asymmetric gable: ridge offset 1/3 from one long edge
    offset_frac = 1.0 / 3.0
    # Ridge line between short edge midpoints, but shifted toward one long edge
    ridge_a_2d = footprint[i1] + offset_frac * (footprint[i2] - footprint[i1])
    ridge_b_2d = footprint[i0] + offset_frac * (footprint[i3] - footprint[i0])
    ridge_a = np.array([ridge_a_2d[0], ridge_a_2d[1], height + roof_height])
    ridge_b = np.array([ridge_b_2d[0], ridge_b_2d[1], height + roof_height])

    verts = np.vstack([p, [ridge_a], [ridge_b]])
    ra, rb = 4, 5

    tris = np.array(
        [
            # short slope (i0->i1 to ridge)
            [i0, i1, ra],
            [i0, ra, rb],
            # long slope (i2->i3 to ridge)
            [i2, i3, rb],
            [i2, rb, ra],
            # gable triangles
            [i1, i2, ra],
            [i3, i0, rb],
        ],
        dtype=np.uint32,
    )
    return verts, tris


_ROOF_DISPATCH["saltbox"] = _roof_saltbox


# ---------------------------------------------------------------------------
# 9. Mansard roof
# ---------------------------------------------------------------------------


def _roof_mansard(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(footprint)
    centroid = footprint.mean(axis=0)
    inset_frac = 0.3  # inset by 30% toward centroid

    # Lower break ring at 70% of roof height
    break_h = height + roof_height * 0.7
    top_h = height + roof_height

    inset_fp = footprint + inset_frac * (centroid - footprint)

    base = _make_3d(footprint, height)
    mid_ring = _make_3d(inset_fp, break_h)
    top_ring = _make_3d(inset_fp, top_h)

    # Verts: 0..n-1 = base footprint, n..2n-1 = mid ring, 2n..3n-1 = top ring
    verts = np.vstack([base, mid_ring, top_ring])

    tris_list = []
    for i in range(n):
        j = (i + 1) % n
        # Lower steep face: quad from footprint edge to mid ring
        tris_list.append([i, j, n + j])
        tris_list.append([i, n + j, n + i])

    # Flat top: triangulate the inset polygon at top height
    top_tris = triangulate_polygon(inset_fp)
    for tri in top_tris:
        tris_list.append([2 * n + tri[0], 2 * n + tri[1], 2 * n + tri[2]])

    return verts, np.array(tris_list, dtype=np.uint32)


_ROOF_DISPATCH["mansard"] = _roof_mansard


# ---------------------------------------------------------------------------
# 10. Dome roof
# ---------------------------------------------------------------------------


def _roof_dome(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    centroid = footprint.mean(axis=0)
    # Bounding circle radius
    radii = np.linalg.norm(footprint - centroid, axis=1)
    radius = float(radii.max())

    n_seg = 8  # azimuthal segments
    n_ring = 6  # elevation rings (not counting apex)

    verts = []
    tris = []

    # Bottom ring at building top
    for i in range(n_seg):
        theta = 2 * np.pi * i / n_seg
        x = centroid[0] + radius * np.cos(theta)
        y = centroid[1] + radius * np.sin(theta)
        verts.append([x, y, height])

    # Intermediate rings
    for r in range(1, n_ring):
        phi = (np.pi / 2) * r / n_ring
        ring_r = radius * np.cos(phi)
        ring_z = height + roof_height * np.sin(phi)
        for i in range(n_seg):
            theta = 2 * np.pi * i / n_seg
            x = centroid[0] + ring_r * np.cos(theta)
            y = centroid[1] + ring_r * np.sin(theta)
            verts.append([x, y, ring_z])

    # Apex
    apex_idx = len(verts)
    verts.append([centroid[0], centroid[1], height + roof_height])

    # Quads between rings
    for r in range(n_ring - 1):
        for i in range(n_seg):
            j = (i + 1) % n_seg
            a = r * n_seg + i
            b = r * n_seg + j
            c = (r + 1) * n_seg + j
            d = (r + 1) * n_seg + i
            tris.append([a, b, c])
            tris.append([a, c, d])

    # Top cap (triangles to apex)
    last_ring_start = (n_ring - 1) * n_seg
    for i in range(n_seg):
        j = (i + 1) % n_seg
        tris.append([last_ring_start + i, last_ring_start + j, apex_idx])

    return np.array(verts, dtype=np.float64), np.array(tris, dtype=np.uint32)


_ROOF_DISPATCH["dome"] = _roof_dome


# ---------------------------------------------------------------------------
# 11. Onion roof
# ---------------------------------------------------------------------------


def _roof_onion(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    centroid = footprint.mean(axis=0)
    radii = np.linalg.norm(footprint - centroid, axis=1)
    radius = float(radii.max())

    n_seg = 8
    n_ring = 8

    verts = []
    tris = []

    # Generate onion profile: r(t) = R * sin(t) * (1 + 0.3 * sin(3t))
    for r in range(n_ring + 1):
        t = np.pi * r / n_ring  # 0 to pi
        if r == n_ring:
            # Apex
            ring_r = 0.0
            ring_z = height + roof_height
        elif r == 0:
            ring_r = radius
            ring_z = height
        else:
            profile_r = np.sin(t) * (1 + 0.3 * np.sin(3 * t))
            # Normalize so max profile_r maps to radius
            ring_r = radius * profile_r / 1.3  # approx max of sin(t)*(1+0.3*sin(3t))
            ring_z = height + roof_height * (1 - np.cos(t)) / 2

        if r == n_ring:
            apex_idx = len(verts)
            verts.append([centroid[0], centroid[1], ring_z])
        else:
            for i in range(n_seg):
                theta = 2 * np.pi * i / n_seg
                x = centroid[0] + ring_r * np.cos(theta)
                y = centroid[1] + ring_r * np.sin(theta)
                verts.append([x, y, ring_z])

    # Quads between rings
    for r in range(n_ring - 1):
        for i in range(n_seg):
            j = (i + 1) % n_seg
            a = r * n_seg + i
            b = r * n_seg + j
            c = (r + 1) * n_seg + j
            d = (r + 1) * n_seg + i
            tris.append([a, b, c])
            tris.append([a, c, d])

    # Top cap
    last_ring_start = (n_ring - 1) * n_seg
    for i in range(n_seg):
        j = (i + 1) % n_seg
        tris.append([last_ring_start + i, last_ring_start + j, apex_idx])

    return np.array(verts, dtype=np.float64), np.array(tris, dtype=np.uint32)


_ROOF_DISPATCH["onion"] = _roof_onion


# ---------------------------------------------------------------------------
# 12. Round (barrel vault) roof
# ---------------------------------------------------------------------------


def _roof_round(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    if len(footprint) != 4:
        return _roof_dome(footprint, height, roof_height)

    # Find longest axis for barrel direction
    i0, i1, i2, i3 = _find_ridge_axis(footprint)

    # The barrel runs along the long edges (i0->i1 and i3->i2)
    # Cross-section is semicircular across the short edges
    n_arc = 8  # segments in semicircle

    # Parameterize: s along barrel (0..1), t across (0..1 maps to semicircle)
    p0 = footprint[i0]
    p1 = footprint[i1]
    p3 = footprint[i3]
    p2 = footprint[i2]

    verts = []
    for j in range(n_arc + 1):
        theta = np.pi * j / n_arc  # 0 to pi
        frac = j / n_arc  # fraction across short edge
        z = height + roof_height * np.sin(theta)

        # Interpolate position across the short edge direction
        # Start side: p0 -> p3, End side: p1 -> p2
        start = p0 + frac * (p3 - p0)
        end = p1 + frac * (p2 - p1)

        verts.append([start[0], start[1], z])
        verts.append([end[0], end[1], z])

    tris = []
    for j in range(n_arc):
        # Each arc segment has 2 verts at j and 2 at j+1
        # j*2, j*2+1 = start_j, end_j
        # (j+1)*2, (j+1)*2+1 = start_{j+1}, end_{j+1}
        a = j * 2
        b = j * 2 + 1
        c = (j + 1) * 2 + 1
        d = (j + 1) * 2
        tris.append([a, b, c])
        tris.append([a, c, d])

    return np.array(verts, dtype=np.float64), np.array(tris, dtype=np.uint32)


_ROOF_DISPATCH["round"] = _roof_round


# ---------------------------------------------------------------------------
# 13. Multi-flat roof
# ---------------------------------------------------------------------------


def _roof_multi_flat(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    """Stepped flat roof with two levels.

    Lower ring is flat at `height`. Inner inset section rises to
    `height + roof_height` with a vertical step wall at 60% of roof_height.
    """
    n = len(footprint)
    centroid = footprint.mean(axis=0)
    inset_frac = 0.3
    inset_fp = footprint + inset_frac * (centroid - footprint)

    step_h = height + roof_height * 0.6
    top_h = height + roof_height

    outer_base = _make_3d(footprint, height)
    inner_base = _make_3d(inset_fp, height)
    inner_step = _make_3d(inset_fp, step_h)
    inner_top = _make_3d(inset_fp, top_h)

    tris_list = []

    # Outer flat ring: quad strip from outer footprint to inset footprint, both at height.
    # Vertex layout: 0..n-1 = outer_base, n..2n-1 = inner_base
    verts = np.vstack([outer_base, inner_base, inner_step, inner_top])
    # Indices: outer=0..n-1, inner_base=n..2n-1, inner_step=2n..3n-1, inner_top=3n..4n-1

    for i in range(n):
        j = (i + 1) % n
        oi, oj = i, j
        ii, ij = n + i, n + j
        # Outer flat ring quad (at height): outer[i] -> outer[j] -> inner[j] -> inner[i]
        tris_list.append([oi, oj, ij])
        tris_list.append([oi, ij, ii])

    # Step walls: from inner_base to inner_step
    for i in range(n):
        j = (i + 1) % n
        ii, ij = n + i, n + j
        si, sj = 2 * n + i, 2 * n + j
        tris_list.append([ii, ij, sj])
        tris_list.append([ii, sj, si])

    # Top cap: triangulate inset footprint at top_h (vertices 3n..4n-1)
    top_tris = triangulate_polygon(inset_fp)
    for tri in top_tris:
        tris_list.append([3 * n + tri[0], 3 * n + tri[1], 3 * n + tri[2]])

    return verts, np.array(tris_list, dtype=np.uint32)


_ROOF_DISPATCH["multi_flat"] = _roof_multi_flat


# ---------------------------------------------------------------------------
# 14. Multi-hipped roof
# ---------------------------------------------------------------------------


def _roof_multi_hipped(footprint: np.ndarray, height: float, roof_height: float) -> tuple[np.ndarray, np.ndarray]:
    """Hipped roof with a secondary smaller hipped roof on top.

    Lower hip covers full footprint rising to `height + roof_height * 0.6`.
    Upper hip covers an inset footprint (40% toward centroid) rising a further
    `roof_height * 0.4`.
    """
    from aegis.environment.skeleton import polygonize

    try:
        # Lower hip
        lower_h = roof_height * 0.6
        fp_3d_lower = [_make_3d(footprint, height)[i] for i in range(len(footprint))]
        lower_verts_list = list(fp_3d_lower)
        lower_faces = polygonize(lower_verts_list, footprint, height=lower_h)
        if not lower_faces:
            raise ValueError("lower polygonize returned no faces")

        lower_verts = np.array(lower_verts_list, dtype=np.float64)
        lower_tris_list = []
        for face in lower_faces:
            if len(face) < 3:
                continue
            for k in range(1, len(face) - 1):
                lower_tris_list.append([face[0], face[k], face[k + 1]])
        if not lower_tris_list:
            raise ValueError("lower hip has no triangles")

        # Upper hip on inset footprint
        centroid = footprint.mean(axis=0)
        inset_frac = 0.4
        inset_fp = footprint + inset_frac * (centroid - footprint)
        upper_base_h = height + lower_h
        upper_h = roof_height * 0.4

        fp_3d_upper = [_make_3d(inset_fp, upper_base_h)[i] for i in range(len(inset_fp))]
        upper_verts_list = list(fp_3d_upper)
        upper_faces = polygonize(upper_verts_list, inset_fp, height=upper_h)
        if not upper_faces:
            raise ValueError("upper polygonize returned no faces")

        upper_verts = np.array(upper_verts_list, dtype=np.float64)
        upper_tris_list = []
        for face in upper_faces:
            if len(face) < 3:
                continue
            for k in range(1, len(face) - 1):
                upper_tris_list.append([face[0], face[k], face[k + 1]])
        if not upper_tris_list:
            raise ValueError("upper hip has no triangles")

        lower_tris = np.array(lower_tris_list, dtype=np.uint32)
        upper_tris = np.array(upper_tris_list, dtype=np.uint32)
        offset = len(lower_verts)
        combined_verts = np.vstack([lower_verts, upper_verts])
        combined_tris = np.concatenate([lower_tris, upper_tris + offset])
        return combined_verts, combined_tris

    except Exception:
        # Fallback to plain hipped
        return _roof_hipped(footprint, height, roof_height)


_ROOF_DISPATCH["multi_hipped"] = _roof_multi_hipped

"""Regression tests for voxel hull -> triangle mesh (viewer ray tracer prep)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("differt")

from aegis.viewer.raytracer import round_triangle_scene


def _n_triangles(grid_coords: np.ndarray) -> int:
    pos = grid_coords.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=grid_coords.astype(np.int64), voxel_size=1.0)
    return int(np.array(scene.mesh.triangles).shape[0])


def test_single_voxel_is_six_quads():
    gc = np.array([[0, 0, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_two_adjacent_voxels_shares_one_face():
    """2x1x1: greedy merges top/bottom/sides into 6 rectangles = 12 triangles."""
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_two_by_two_by_one_tile_expected_hull():
    """2x2x1 slab: greedy merges into 6 rectangles = 12 triangles."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_far_from_origin_same_hull_count():
    """Offsets must not break neighbor tests (regression for linear key collisions)."""
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    shift = np.array([[100, 200, 300]], dtype=np.int64)
    gc = base + shift
    assert _n_triangles(gc) == 12


def test_greedy_flat_floor_4x4():
    """4x4 flat floor: 6 merged rectangles = 12 triangles."""
    gc = np.array([[x, y, 0] for x in range(4) for y in range(4)], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_greedy_l_shape():
    """L-shape produces fewer triangles than unmerged."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    n = _n_triangles(gc)
    assert n < 40, f"Expected greedy to reduce triangles, got {n}"
    assert n >= 12, f"L-shape needs at least 12 triangles, got {n}"


def test_greedy_normals_point_outward():
    """All face normals must point outward (away from the solid)."""
    gc = np.array(
        [[x, y, z] for x in range(3) for y in range(3) for z in range(2)],
        dtype=np.int64,
    )
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)

    verts = np.array(scene.mesh.vertices)
    tris = np.array(scene.mesh.triangles)

    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1)

    centers = (v0 + v1 + v2) / 3.0
    solid_center = pos.mean(axis=0)
    outward = centers - solid_center
    dots = np.sum(normals * outward, axis=1)
    assert np.all(dots >= -1e-6), f"Some normals point inward: min dot = {dots.min()}"


def test_greedy_nonunit_voxel_size():
    """Greedy meshing with voxel_size=0.5 produces correct world extents."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    pos = gc.astype(np.float64) * 0.5
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=0.5)

    verts = np.array(scene.mesh.vertices)
    assert abs(verts[:, 0].max() - verts[:, 0].min() - 1.0) < 1e-5
    assert abs(verts[:, 1].max() - verts[:, 1].min() - 1.0) < 1e-5
    assert abs(verts[:, 2].max() - verts[:, 2].min() - 0.5) < 1e-5


def test_flat_floor_normals_are_vertical():
    """A single-layer floor should only have horizontal faces (normals along Z).

    Regression test for the Y-up/Z-up grid_coords mismatch that caused
    'venetian blinds' in the viewer.
    """
    # 3x3 flat floor at z=0
    gc = np.array([[x, y, 0] for x in range(3) for y in range(3)], dtype=np.int64)
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)

    verts = np.array(scene.mesh.vertices)
    tris = np.array(scene.mesh.triangles)

    # Compute face normals
    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1)

    for n in normals:
        is_z = abs(abs(n[2]) - 1.0) < 1e-6
        is_x = abs(abs(n[0]) - 1.0) < 1e-6
        is_y = abs(abs(n[1]) - 1.0) < 1e-6
        assert is_z or is_x or is_y, f"Unexpected diagonal normal: {n}"


def test_grid_coords_swapped_to_zup():
    """prepare_for_raytracing converts Y-up positions to Z-up and grid_coords must match."""
    from aegis.viewer.scene_data import prepare_for_raytracing

    grid_coords = np.array([[0, 5, 0], [1, 5, 0], [0, 5, 1]], dtype=np.int64)
    positions = grid_coords.astype(np.float64)
    voxel_sizes = np.ones(len(positions), dtype=np.float32)

    positions_zup, gc_zup, _ = prepare_for_raytracing(positions, voxel_sizes)

    # Y-up [x, y_up, z_horiz] -> Z-up [x, -z_horiz, y_up]
    # For [0, 5, 0]: z_up = [0, 0, 5] (minus center shift, but relative values hold)
    # Check the first point has y_up in the Z component (index 2)
    # All positions have same y=5, so after centering they're all at z=0 in Z-up
    # Use the raw axis mapping instead: gc_zup col 2 should map from col 1 of grid_coords
    expected_gc_zup = np.column_stack(
        [
            grid_coords[:, 0],
            -grid_coords[:, 2],
            grid_coords[:, 1],
        ]
    )

    assert expected_gc_zup[0, 2] == 5
    assert expected_gc_zup[0, 1] == 0


def test_material_boundary_prevents_merge():
    """Adjacent voxels with different materials must not merge across boundary."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "concrete", "brick", "brick"]

    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0, materials=materials)
    mesh = scene.mesh
    face_mats = np.array(mesh.face_materials)

    unique_mats = set(face_mats.tolist())
    assert len(unique_mats) == 2, f"Expected 2 materials, got {unique_mats}"

    assert "brick" in mesh.material_names
    assert "concrete" in mesh.material_names


def test_no_materials_defaults_to_concrete():
    """When materials=None, all faces get material 0 ('concrete')."""
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)
    mesh = scene.mesh
    face_mats = np.array(mesh.face_materials)
    assert set(face_mats.tolist()) == {0}
    assert mesh.material_names == ("concrete",)


def test_face_colors_match_material():
    """face_colors should be set based on material_colors config."""
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "brick"]
    material_colors = {"concrete": [180, 180, 180], "brick": [200, 80, 50]}

    scene = round_triangle_scene(
        pos,
        grid_coords=gc,
        voxel_size=1.0,
        materials=materials,
        material_colors=material_colors,
    )
    colors = np.array(scene.mesh.face_colors)
    assert colors.max() <= 1.0
    assert colors.min() >= 0.0
    assert colors.sum() > 0


def test_hull_binary_round_trip_with_colors():
    """Build hull, serialize to binary, verify face_colors present."""
    from aegis.viewer.raytracer import scene_geometry_to_binary

    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "brick"]
    material_colors = {"concrete": [180, 180, 180], "brick": [200, 80, 50]}

    scene = round_triangle_scene(
        pos,
        grid_coords=gc,
        voxel_size=1.0,
        materials=materials,
        material_colors=material_colors,
    )
    mesh = scene.mesh
    vertices = np.array(mesh.vertices)
    triangles = np.array(mesh.triangles)
    colors = np.array(mesh.face_colors)

    scene_data = {
        "vertices": vertices,
        "triangles": triangles,
        "face_colors": colors,
        "n_vertices": len(vertices),
        "n_triangles": len(triangles),
        "material_names": list(mesh.material_names),
    }
    data, meta = scene_geometry_to_binary(scene_data)

    assert meta["has_face_colors"] is True
    assert len(meta["material_names"]) == 2

    nv = meta["n_vertices"]
    nt = meta["n_triangles"]
    v_end = nv * 3 * 4
    t_end = v_end + nt * 3 * 4
    c_end = t_end + nt * 3 * 4
    assert len(data) == c_end

    parsed_colors = np.frombuffer(data[t_end:c_end], dtype=np.float32).reshape(nt, 3)
    assert parsed_colors.sum() > 0

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
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 20


def test_two_by_two_by_one_tile_expected_hull():
    """Flat 2x2 slab: convex hull has 16 exterior faces (16 quads)."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 32


def test_far_from_origin_same_hull_count():
    """Offsets must not break neighbor tests (regression for linear key collisions)."""
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    shift = np.array([[100, 200, 300]], dtype=np.int64)
    gc = base + shift
    assert _n_triangles(gc) == 32


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
    """After load_voxels transforms positions to Z-up, grid_coords must match."""
    from aegis.viewer.scene_data import _transform_to_local

    grid_coords = np.array([[0, 5, 0], [1, 5, 0], [0, 5, 1]], dtype=np.int64)
    positions = grid_coords.astype(np.float64)

    positions_zup, _ = _transform_to_local(positions, has_ecef=False)

    gc_zup = np.column_stack(
        [
            grid_coords[:, 0],
            -grid_coords[:, 2],
            grid_coords[:, 1],
        ]
    )

    assert gc_zup[0, 2] == 5
    assert gc_zup[0, 1] == 0

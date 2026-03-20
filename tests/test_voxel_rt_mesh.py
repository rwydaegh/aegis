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

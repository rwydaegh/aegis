"""Tests for aegis.environment.terrain: SRTM HGT parsing and mesh generation."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.environment.terrain import (
    TerrainGrid,
    generate_terrain_mesh,
    hgt_filename,
    parse_hgt,
    project_z,
)


def test_hgt_filename():
    assert hgt_filename(51.05, 3.72) == "N51E003.hgt"
    assert hgt_filename(-33.8, 151.2) == "S33E151.hgt"
    assert hgt_filename(51.05, -0.12) == "N51W001.hgt"


def test_parse_hgt_synthetic():
    # 3x3 grid of int16 big-endian = 18 bytes
    data = np.array([[10, 20, 30], [15, 25, 35], [20, 30, 40]], dtype=">i2").tobytes()
    grid = parse_hgt(data, samples=3)
    assert grid.shape == (3, 3)
    assert grid[0, 0] == 10


def test_parse_hgt_void_replacement():
    """Void values (-32768) must be replaced with 0."""
    data = np.array([[100, -32768], [-32768, 200]], dtype=">i2").tobytes()
    grid = parse_hgt(data, samples=2)
    assert grid[0, 1] == 0.0
    assert grid[1, 0] == 0.0
    assert grid[0, 0] == 100.0
    assert grid[1, 1] == 200.0


def test_generate_terrain_mesh():
    elevations = np.array([[10, 20, 30], [15, 25, 35], [20, 30, 40]], dtype=np.float64)
    grid = TerrainGrid(elevations=elevations, origin_lat=51.0, origin_lon=3.0, cell_size_m=30.0)
    verts, tris = generate_terrain_mesh(grid)
    assert verts.shape == (9, 3)  # 3x3 grid
    assert tris.shape[0] == 8  # 2x2 cells, 2 tris each
    assert verts[:, 2].min() == 10.0


def test_generate_terrain_mesh_index_dtype():
    elevations = np.ones((4, 4), dtype=np.float64)
    grid = TerrainGrid(elevations=elevations, origin_lat=0.0, origin_lon=0.0, cell_size_m=10.0)
    _, tris = generate_terrain_mesh(grid)
    assert tris.dtype == np.uint32
    # 3x3 cells, 2 tris each = 18
    assert tris.shape == (18, 3)


def test_project_z():
    elevations = np.array([[0, 0, 0], [0, 10, 0], [0, 0, 0]], dtype=np.float64)
    grid = TerrainGrid(elevations=elevations, origin_lat=51.0, origin_lon=3.0, cell_size_m=10.0)
    z = project_z(np.array([[10.0, 10.0]]), grid)
    assert abs(z[0] - 10.0) < 1.5  # center should be near peak


def test_project_z_clamp():
    """Points outside the grid should be clamped, not raise."""
    elevations = np.ones((3, 3), dtype=np.float64) * 5.0
    grid = TerrainGrid(elevations=elevations, origin_lat=0.0, origin_lon=0.0, cell_size_m=10.0)
    z = project_z(np.array([[-100.0, -100.0], [999.0, 999.0]]), grid)
    assert z.shape == (2,)
    assert np.all(z == pytest.approx(5.0))


def test_project_z_corner():
    """Corner of the grid should return exact elevation."""
    elevations = np.array([[1, 2], [3, 4]], dtype=np.float64)
    grid = TerrainGrid(elevations=elevations, origin_lat=0.0, origin_lon=0.0, cell_size_m=1.0)
    z = project_z(np.array([[0.0, 0.0]]), grid)
    assert z[0] == pytest.approx(1.0)

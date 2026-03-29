"""SRTM terrain support: parse HGT elevation files, generate terrain meshes.

No download functionality is included. Use external tooling to fetch HGT files
and pass the raw bytes to ``parse_hgt``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class TerrainGrid:
    """Elevation grid in local Cartesian coordinates.

    Attributes
    ----------
    elevations:
        (rows, cols) float64 array of elevation values in meters.
    origin_lat:
        Latitude of the grid origin (degrees).
    origin_lon:
        Longitude of the grid origin (degrees).
    cell_size_m:
        Horizontal distance between adjacent grid cells (meters).
    """

    elevations: np.ndarray
    origin_lat: float
    origin_lon: float
    cell_size_m: float


def hgt_filename(lat: float, lon: float) -> str:
    """Return the SRTM HGT tile filename for the given latitude/longitude.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees.
    lon:
        Longitude in decimal degrees.

    Returns
    -------
    str
        Filename, e.g. ``"N51E003.hgt"``.
    """
    # SRTM HGT tiles are named by (lat_label, lon_label) where:
    #   N/E: floor of the coordinate (SW/NW corner, positive direction)
    #   S  : abs(ceil(lat))  -- tile covers [ceil(lat)-1, ceil(lat)], label = abs(ceil)
    #   W  : abs(floor(lon)) -- tile covers [floor(lon), floor(lon)+1], label = abs(floor)
    # Examples: lat=51.05 -> N51, lat=-33.8 -> S33, lon=3.72 -> E003, lon=-0.12 -> W001
    lat_label = math.floor(lat) if lat >= 0 else abs(math.ceil(lat))
    lon_label = math.floor(lon) if lon >= 0 else abs(math.floor(lon))
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{lat_label:02d}{ew}{lon_label:03d}.hgt"


def parse_hgt(data: bytes, samples: int = 1201) -> np.ndarray:
    """Parse a raw SRTM HGT binary file.

    Parameters
    ----------
    data:
        Raw bytes of the HGT file.
    samples:
        Grid dimension: 1201 for SRTM3 (3 arc-second), 3601 for SRTM1.

    Returns
    -------
    np.ndarray
        (samples, samples) float64 array of elevations in meters.
        Void values (-32768) are replaced with 0.
    """
    arr = np.frombuffer(data, dtype=">i2").reshape(samples, samples).astype(np.float64)
    arr[arr == -32768] = 0.0
    return arr


def generate_terrain_mesh(grid: TerrainGrid) -> tuple[np.ndarray, np.ndarray]:
    """Build a triangle mesh from a TerrainGrid.

    Each grid cell is split into two triangles along its diagonal.
    Vertex positions are (col * cell_size_m, row * cell_size_m, elevation).

    Parameters
    ----------
    grid:
        Elevation grid to triangulate.

    Returns
    -------
    vertices : np.ndarray
        (rows * cols, 3) float64 array of XYZ vertex positions.
    triangles : np.ndarray
        (2 * (rows-1) * (cols-1), 3) uint32 triangle index array.
    """
    elevations = grid.elevations
    rows, cols = elevations.shape
    cell = grid.cell_size_m

    col_idx, row_idx = np.meshgrid(np.arange(cols), np.arange(rows))
    x = col_idx.ravel().astype(np.float64) * cell
    y = row_idx.ravel().astype(np.float64) * cell
    z = elevations.ravel().astype(np.float64)
    vertices = np.column_stack([x, y, z])

    # Build quad indices then split each quad into 2 triangles
    r0 = np.arange(rows - 1)
    c0 = np.arange(cols - 1)
    rr, cc = np.meshgrid(r0, c0, indexing="ij")
    rr = rr.ravel()
    cc = cc.ravel()

    # Four corners of each quad (row-major indexing into vertex array)
    i00 = rr * cols + cc
    i01 = rr * cols + (cc + 1)
    i10 = (rr + 1) * cols + cc
    i11 = (rr + 1) * cols + (cc + 1)

    tri0 = np.column_stack([i00, i01, i11])
    tri1 = np.column_stack([i00, i11, i10])
    triangles = np.concatenate([tri0, tri1], axis=0).astype(np.uint32)

    return vertices, triangles


def project_z(xy_points: np.ndarray, grid: TerrainGrid) -> np.ndarray:
    """Bilinearly interpolate elevation at arbitrary (x, y) positions.

    Parameters
    ----------
    xy_points:
        (N, 2) float64 array of (x, y) positions in meters (same coordinate
        system as the mesh returned by ``generate_terrain_mesh``).
    grid:
        Source elevation grid.

    Returns
    -------
    np.ndarray
        (N,) float64 array of interpolated elevation values.
        Points outside the grid are clamped to the boundary.
    """
    elevations = grid.elevations
    rows, cols = elevations.shape
    cell = grid.cell_size_m

    x = np.asarray(xy_points[:, 0], dtype=np.float64)
    y = np.asarray(xy_points[:, 1], dtype=np.float64)

    # Fractional column and row indices
    fc = x / cell
    fr = y / cell

    # Clamp to valid range
    fc = np.clip(fc, 0.0, cols - 1.0)
    fr = np.clip(fr, 0.0, rows - 1.0)

    c0 = np.floor(fc).astype(np.int64)
    r0 = np.floor(fr).astype(np.int64)
    c1 = np.minimum(c0 + 1, cols - 1)
    r1 = np.minimum(r0 + 1, rows - 1)

    dc = fc - c0
    dr = fr - r0

    z00 = elevations[r0, c0]
    z01 = elevations[r0, c1]
    z10 = elevations[r1, c0]
    z11 = elevations[r1, c1]

    z = z00 * (1 - dc) * (1 - dr) + z01 * dc * (1 - dr) + z10 * (1 - dc) * dr + z11 * dc * dr
    return z

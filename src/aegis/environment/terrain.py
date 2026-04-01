"""SRTM terrain support: download, parse HGT elevation files, generate terrain meshes.

Downloads SRTM1 (1 arc-second, ~30 m) elevation tiles from the AWS Terrain
Tiles open dataset. Tiles are cached locally in ``~/.cache/aegis/srtm/``.
"""

from __future__ import annotations

import gzip
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np

logger = logging.getLogger(__name__)

# AWS open terrain tiles (Mapzen/Tilezen, public, no API key)
_SRTM_BASE_URL = "https://elevation-tiles-prod.s3.amazonaws.com/skadi"

# SRTM1 = 3601 samples per side (1 arc-second resolution)
_SRTM1_SAMPLES = 3601

# Approximate meters per degree at the equator
_METERS_PER_DEG_LAT = 111_320.0


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
    lat_label = math.floor(lat) if lat >= 0 else abs(math.floor(lat))
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


def _srtm_cache_dir() -> Path:
    """Return the local cache directory for SRTM tiles."""
    base = os.environ.get("AEGIS_CACHE_DIR", os.path.expanduser("~/.cache/aegis"))
    d = Path(base) / "srtm"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_hgt(lat: float, lon: float, timeout: float = 30.0) -> np.ndarray | None:
    """Download (or load cached) SRTM1 HGT tile for the given coordinate.

    Returns the parsed (3601, 3601) elevation array, or None if the tile is
    not available (ocean areas, high latitudes above 60N).
    """
    fname = hgt_filename(lat, lon)
    cache_path = _srtm_cache_dir() / fname

    # Return cached tile
    if cache_path.exists():
        logger.debug("SRTM cache hit: %s", fname)
        return parse_hgt(cache_path.read_bytes(), samples=_SRTM1_SAMPLES)

    # Build URL: skadi/{lat_band}/{filename}.gz
    lat_band = fname[:3]  # e.g. "N51"
    url = f"{_SRTM_BASE_URL}/{lat_band}/{fname}.gz"
    logger.info("Downloading SRTM tile: %s", url)

    try:
        req = Request(url, headers={"User-Agent": "AEGIS/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            compressed = resp.read()
        raw = gzip.decompress(compressed)
        cache_path.write_bytes(raw)
        return parse_hgt(raw, samples=_SRTM1_SAMPLES)
    except HTTPError as exc:
        if exc.code == 404:
            logger.warning("SRTM tile not available (ocean/polar): %s", fname)
            return None
        logger.error("SRTM download failed (%s): %s", exc.code, url)
        return None
    except (URLError, OSError) as exc:
        logger.error("SRTM download error: %s", exc)
        return None


def _needed_tiles(lat: float, lon: float, radius_m: float) -> list[tuple[int, int]]:
    """Return list of (floor_lat, floor_lon) for all HGT tiles covering the area."""
    deg_lat = radius_m / _METERS_PER_DEG_LAT
    deg_lon = radius_m / (_METERS_PER_DEG_LAT * max(math.cos(math.radians(lat)), 1e-6))

    lat_min = math.floor(lat - deg_lat)
    lat_max = math.floor(lat + deg_lat)
    lon_min = math.floor(lon - deg_lon)
    lon_max = math.floor(lon + deg_lon)

    tiles = []
    for la in range(lat_min, lat_max + 1):
        for lo in range(lon_min, lon_max + 1):
            tiles.append((la, lo))
    return tiles


def terrain_grid_for_location(
    lat: float,
    lon: float,
    radius_m: float = 200.0,
    cell_size_m: float = 10.0,
    timeout: float = 30.0,
) -> TerrainGrid:
    """Build a TerrainGrid with real SRTM elevation for the given location.

    Falls back to a flat grid (z=0) if SRTM data is not available.

    Parameters
    ----------
    lat, lon:
        Center of the area in decimal degrees.
    radius_m:
        Half-width of the square grid in meters.
    cell_size_m:
        Spacing between grid points in meters.
    timeout:
        HTTP timeout for tile downloads in seconds.
    """
    side = radius_m * 2.0
    n_cells = max(2, int(side / cell_size_m) + 1)

    # Fetch all needed SRTM tiles
    tile_coords = _needed_tiles(lat, lon, radius_m)
    tiles: dict[tuple[int, int], np.ndarray] = {}
    for tlat, tlon in tile_coords:
        # fetch_hgt takes the SW corner coordinate
        elev = fetch_hgt(tlat + 0.5, tlon + 0.5, timeout=timeout)
        if elev is not None:
            tiles[(tlat, tlon)] = elev

    if not tiles:
        logger.warning("No SRTM data available, returning flat terrain")
        elevations = np.zeros((n_cells, n_cells), dtype=np.float64)
        return TerrainGrid(
            elevations=elevations,
            origin_lat=lat,
            origin_lon=lon,
            cell_size_m=cell_size_m,
        )

    # Build the elevation grid by sampling from SRTM tiles
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)

    # Grid point offsets in meters from center
    offsets = np.linspace(-radius_m, radius_m, n_cells)
    grid_x, grid_y = np.meshgrid(offsets, offsets)  # (n_cells, n_cells)

    # Convert meter offsets to lat/lon
    grid_lat = lat + grid_y / _METERS_PER_DEG_LAT
    grid_lon = lon + grid_x / (_METERS_PER_DEG_LAT * cos_lat)

    elevations = np.zeros((n_cells, n_cells), dtype=np.float64)

    for (tlat, tlon), tile_data in tiles.items():
        samples = tile_data.shape[0]  # 3601

        # Mask: which grid points fall in this tile?
        mask = (np.floor(grid_lat) == tlat) & (np.floor(grid_lon) == tlon)
        if not np.any(mask):
            continue

        # Fractional position within the tile (0..1)
        # HGT tiles go from NW corner: row 0 = north edge
        frac_lat = grid_lat[mask] - tlat  # 0 at south edge, 1 at north edge
        frac_lon = grid_lon[mask] - tlon  # 0 at west edge, 1 at east edge

        # Convert to array indices (row 0 = north = lat+1)
        row_f = (1.0 - frac_lat) * (samples - 1)
        col_f = frac_lon * (samples - 1)

        # Bilinear interpolation
        r0 = np.clip(np.floor(row_f).astype(int), 0, samples - 2)
        c0 = np.clip(np.floor(col_f).astype(int), 0, samples - 2)
        r1 = r0 + 1
        c1 = c0 + 1

        dr = row_f - r0
        dc = col_f - c0

        z00 = tile_data[r0, c0]
        z01 = tile_data[r0, c1]
        z10 = tile_data[r1, c0]
        z11 = tile_data[r1, c1]

        elevations[mask] = z00 * (1 - dc) * (1 - dr) + z01 * dc * (1 - dr) + z10 * (1 - dc) * dr + z11 * dc * dr

    # Subtract minimum elevation so the terrain sits near y=0 in the viewer
    elevations -= elevations.min()

    return TerrainGrid(
        elevations=elevations,
        origin_lat=lat,
        origin_lon=lon,
        cell_size_m=cell_size_m,
    )


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

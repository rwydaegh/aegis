"""Satellite map tile math for ground texture overlays.

Pure math and data structures only. No HTTP downloads are performed here.
Use the returned tile coordinates and URLs with an external HTTP client.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# WGS-84 equatorial radius in meters
_EARTH_RADIUS_M = 6_378_137.0


def tile_coords(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert geographic coordinates to Slippy Map tile indices.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees (WGS-84).
    lon:
        Longitude in decimal degrees (WGS-84).
    zoom:
        Zoom level (0-22 for standard tile servers).

    Returns
    -------
    (tx, ty):
        Tile column and row indices at the given zoom level.
    """
    lat_rad = math.radians(lat)
    n = 2**zoom
    tx = int(math.floor((lon + 180.0) / 360.0 * n))
    ty = int(math.floor((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n))
    return tx, ty


def tile_url(
    tx: int,
    ty: int,
    zoom: int,
    template: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
) -> str:
    """Format a tile URL from a template with {x}, {y}, {z} placeholders.

    Parameters
    ----------
    tx:
        Tile column index.
    ty:
        Tile row index.
    zoom:
        Zoom level.
    template:
        URL template string. Defaults to OpenStreetMap raster tiles.

    Returns
    -------
    str
        Formatted URL ready for download.
    """
    return template.format(x=tx, y=ty, z=zoom)


@dataclass
class StitchBounds:
    """Describes the tile grid needed to cover a geographic area.

    Attributes
    ----------
    tile_grid:
        List of (tx, ty) tile index pairs covering the area.
    x_min:
        Minimum tile column index.
    x_max:
        Maximum tile column index (inclusive).
    y_min:
        Minimum tile row index.
    y_max:
        Maximum tile row index (inclusive).
    width:
        Total stitched image width in pixels.
    height:
        Total stitched image height in pixels.
    zoom:
        Zoom level.
    """

    tile_grid: list[tuple[int, int]]
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    width: int
    height: int
    zoom: int


@dataclass
class OverlayImage:
    """A stitched satellite image with geographic UV mapping.

    Attributes
    ----------
    image:
        RGB image array of shape (H, W, 3), dtype uint8.
    uv_min:
        UV coordinate of the bottom-left corner in local ENU space, shape (2,).
    uv_max:
        UV coordinate of the top-right corner in local ENU space, shape (2,).
    origin_lat:
        Latitude of the scene origin in decimal degrees.
    origin_lon:
        Longitude of the scene origin in decimal degrees.
    """

    image: np.ndarray
    uv_min: np.ndarray
    uv_max: np.ndarray
    origin_lat: float
    origin_lon: float


def meters_per_pixel(lat: float, zoom: int) -> float:
    """Ground resolution at a given latitude and zoom level.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees.
    zoom:
        Tile zoom level.

    Returns
    -------
    float
        Meters per pixel at the given latitude and zoom level.
    """
    lat_rad = math.radians(lat)
    return (2.0 * math.pi * _EARTH_RADIUS_M * math.cos(lat_rad)) / (256.0 * 2**zoom)


def stitch_bounds(
    lat: float,
    lon: float,
    radius_m: float,
    zoom: int,
    tile_size: int = 256,
) -> StitchBounds:
    """Compute which tiles cover a circular area around a geographic point.

    Converts the bounding box of the circle (lat/lon +/- radius) to tile
    coordinates and returns the full rectangular tile grid that covers it.

    Parameters
    ----------
    lat:
        Centre latitude in decimal degrees.
    lon:
        Centre longitude in decimal degrees.
    radius_m:
        Radius of the area of interest in meters.
    zoom:
        Tile zoom level.
    tile_size:
        Pixel dimension of each square tile (default 256).

    Returns
    -------
    StitchBounds
        Tile grid and image dimension information.
    """
    # Angular extent of radius_m on Earth's surface
    delta_lat = math.degrees(radius_m / _EARTH_RADIUS_M)
    delta_lon = math.degrees(radius_m / (_EARTH_RADIUS_M * math.cos(math.radians(lat))))

    # Bounding box corners: note tile y increases southward
    tx_min, ty_min = tile_coords(lat + delta_lat, lon - delta_lon, zoom)  # NW corner
    tx_max, ty_max = tile_coords(lat - delta_lat, lon + delta_lon, zoom)  # SE corner

    # Clamp to valid tile range
    n_tiles = 2**zoom
    tx_min = max(0, tx_min)
    tx_max = min(n_tiles - 1, tx_max)
    ty_min = max(0, ty_min)
    ty_max = min(n_tiles - 1, ty_max)

    tile_grid = [(tx, ty) for ty in range(ty_min, ty_max + 1) for tx in range(tx_min, tx_max + 1)]

    cols = tx_max - tx_min + 1
    rows = ty_max - ty_min + 1
    width = cols * tile_size
    height = rows * tile_size

    return StitchBounds(
        tile_grid=tile_grid,
        x_min=tx_min,
        x_max=tx_max,
        y_min=ty_min,
        y_max=ty_max,
        width=width,
        height=height,
        zoom=zoom,
    )

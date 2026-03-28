"""WGS84 to local ENU coordinate transforms."""

from __future__ import annotations

import math

import numpy as np

# WGS84 semi-major axis
_R_EARTH = 6_371_000.0  # meters


def wgs84_to_enu(
    lat: float,
    lon: float,
    alt: float,
    lat0: float,
    lon0: float,
    alt0: float = 0.0,
) -> np.ndarray:
    """Convert WGS84 (lat, lon, alt) to local ENU (x, y, z) in meters.

    Uses small-angle approximation valid for distances up to ~50 km.

    Parameters
    ----------
    lat, lon : WGS84 degrees
    alt : meters above ground
    lat0, lon0 : scene center (degrees)
    alt0 : reference altitude

    Returns
    -------
    (3,) array [east, north, up] in meters
    """
    dlat = math.radians(lat - lat0)
    dlon = math.radians(lon - lon0)
    lat_r = math.radians(lat0)

    east = _R_EARTH * dlon * math.cos(lat_r)
    north = _R_EARTH * dlat
    up = alt - alt0

    return np.array([east, north, up], dtype=np.float64)


def enu_to_wgs84(
    east: float,
    north: float,
    up: float,
    lat0: float,
    lon0: float,
    alt0: float = 0.0,
) -> tuple[float, float, float]:
    """Convert local ENU (meters) back to WGS84 (degrees)."""
    lat_r = math.radians(lat0)
    lat = lat0 + math.degrees(north / _R_EARTH)
    lon = lon0 + math.degrees(east / (_R_EARTH * math.cos(lat_r)))
    alt = up + alt0
    return lat, lon, alt

"""Small WGS84 to local east-north-up conversion used by scene adapters."""

from __future__ import annotations

import numpy as np

WGS84_A_M = 6_378_137.0
WGS84_E2 = 6.69437999014e-3


def llh_to_ecef(lat_deg: float, lon_deg: float, height_m: float = 0.0) -> np.ndarray:
    """Convert geodetic latitude, longitude and ellipsoidal height to ECEF."""
    lat, lon = np.radians([lat_deg, lon_deg])
    radius = WGS84_A_M / np.sqrt(1.0 - WGS84_E2 * np.sin(lat) ** 2)
    return np.array(
        [
            (radius + height_m) * np.cos(lat) * np.cos(lon),
            (radius + height_m) * np.cos(lat) * np.sin(lon),
            (radius * (1.0 - WGS84_E2) + height_m) * np.sin(lat),
        ]
    )


def enu_rotation(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Return the ECEF to east-north-up rotation at a geodetic point."""
    lat, lon = np.radians([lat_deg, lon_deg])
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    sin_lon, cos_lon = np.sin(lon), np.cos(lon)
    return np.array(
        [
            [-sin_lon, cos_lon, 0.0],
            [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
            [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat],
        ]
    )


class EnuFrame:
    """A metric local frame with x east, y north and z up."""

    def __init__(self, lat_deg: float, lon_deg: float, height_m: float = 0.0) -> None:
        self.origin_ecef = llh_to_ecef(lat_deg, lon_deg, height_m)
        self.rotation = enu_rotation(lat_deg, lon_deg)

    def to_enu(self, lat_deg: float, lon_deg: float, height_m: float = 0.0) -> np.ndarray:
        return self.rotation @ (llh_to_ecef(lat_deg, lon_deg, height_m) - self.origin_ecef)

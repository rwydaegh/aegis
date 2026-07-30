"""WGS84 to local ENU, in metres, z up.

The same six lines were copy-pasted into six scripts in this directory. This is the
single copy. Pure numpy, imports nothing from Blender, so it runs under the venv and
inside `blender -b` alike.

The anchor is data-carried, not a constant: it comes from `osm_buildings.json`
(`lat`, `lon`) with ellipsoidal height 0. Ghent ground sits near +52 m ellipsoidal,
which is why an OSM-only scene built at h=0 lands 50 m below the photogrammetry.
"""

from __future__ import annotations

import numpy as np

A = 6378137.0
E2 = 6.69437999014e-3


def llh_to_ecef(lat_deg: float, lon_deg: float, h: float = 0.0) -> np.ndarray:
    """Geodetic latitude, longitude and ellipsoidal height to ECEF metres."""
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    n = A / np.sqrt(1.0 - E2 * np.sin(lat) ** 2)
    return np.array([
        (n + h) * np.cos(lat) * np.cos(lon),
        (n + h) * np.cos(lat) * np.sin(lon),
        (n * (1.0 - E2) + h) * np.sin(lat),
    ])


def enu_rotation(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Rows are (east, north, up), so `p_enu = R @ (p_ecef - p0)`."""
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    sl, cl = np.sin(lat), np.cos(lat)
    so, co = np.sin(lon), np.cos(lon)
    return np.array([
        [-so, co, 0.0],
        [-sl * co, -sl * so, cl],
        [cl * co, cl * so, sl],
    ])


class Frame:
    """The scene's local ENU frame, anchored at one geodetic point."""

    def __init__(self, lat0: float, lon0: float, h0: float = 0.0) -> None:
        self.lat0 = lat0
        self.lon0 = lon0
        self.p0 = llh_to_ecef(lat0, lon0, h0)
        self.rot = enu_rotation(lat0, lon0)

    def to_enu(self, lon: float, lat: float, h: float = 0.0) -> np.ndarray:
        """One (lon, lat) pair, in OSM's argument order, to ENU metres."""
        return self.rot @ (llh_to_ecef(lat, lon, h) - self.p0)

    def bbox(self, radius_m: float, centre_xy=(0.0, 0.0)) -> tuple[float, ...]:
        """A (west, south, east, north) lon/lat box covering an ENU disk.

        Local flat-earth scaling, which is good to well under a metre over the few
        hundred metres a study area spans, and this only has to be generous enough
        to catch every candidate photograph.
        """
        deg_lat = 111_320.0
        deg_lon = deg_lat * float(np.cos(np.radians(self.lat0)))
        cx, cy = centre_xy
        return (self.lon0 + (cx - radius_m) / deg_lon,
                self.lat0 + (cy - radius_m) / deg_lat,
                self.lon0 + (cx + radius_m) / deg_lon,
                self.lat0 + (cy + radius_m) / deg_lat)

    def ring_to_enu(self, ring: list[tuple[float, float]]) -> np.ndarray:
        """An OSM ring of (lon, lat) pairs to an (N, 2) array of ENU x, y.

        Closed rings arrive with the first point repeated. It is dropped here so
        callers never have to remember to slice.
        """
        pts = np.array([self.to_enu(lon, lat)[:2] for lon, lat in ring])
        if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
            pts = pts[:-1]
        return pts

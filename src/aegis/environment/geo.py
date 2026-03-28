"""Coordinate transforms and bounding volume intersection tests.

All functions use numpy arrays. No mathutils dependency.
Reference: blosm/threed_tiles/manager.py, blosm/util/transverse_mercator.py
"""

from __future__ import annotations

import numpy as np

# WGS-84 ellipsoid parameters
_A = 6378137.0  # semi-major axis (meters)
_F = 1.0 / 298.257223563  # flattening
_B = _A * (1 - _F)  # semi-minor axis
_E2 = 2 * _F - _F**2  # first eccentricity squared


def wgs84_to_ecef(lat: float, lon: float, alt: float = 0.0) -> np.ndarray:
    """Convert WGS-84 geodetic coordinates (degrees) to ECEF (meters)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    sin_lon = np.sin(lon_r)
    cos_lon = np.cos(lon_r)
    N = _A / np.sqrt(1 - _E2 * sin_lat**2)
    x = (N + alt) * cos_lat * cos_lon
    y = (N + alt) * cos_lat * sin_lon
    z = (N * (1 - _E2) + alt) * sin_lat
    return np.array([x, y, z], dtype=np.float64)


def rotation_ecef_to_enu(lat: float, lon: float) -> np.ndarray:
    """3x3 rotation matrix from ECEF to local ENU frame (lat/lon in degrees)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    sin_lon = np.sin(lon_r)
    cos_lon = np.cos(lon_r)
    return np.array(
        [
            [-sin_lon, cos_lon, 0],
            [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
            [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat],
        ],
        dtype=np.float64,
    )


def ecef_to_enu(
    ecef: np.ndarray,
    origin_ecef: np.ndarray,
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray:
    """Convert ECEF coordinates to local ENU relative to origin (lat/lon in degrees)."""
    R = rotation_ecef_to_enu(origin_lat, origin_lon)
    diff = ecef - origin_ecef
    if diff.ndim == 1:
        return R @ diff
    return (R @ diff.T).T


def enu_to_yup(enu: np.ndarray) -> np.ndarray:
    """Convert ENU [east, north, up] to Three.js Y-up [east, up, -north]."""
    if enu.ndim == 1:
        return np.array([enu[0], enu[2], -enu[1]])
    return np.column_stack([enu[:, 0], enu[:, 2], -enu[:, 1]])


def transverse_mercator_forward(
    lat: float,
    lon: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    """Project WGS-84 (degrees) to local XY meters via Transverse Mercator."""
    lat_r = np.radians(lat)
    lon_offset = np.radians(lon - origin_lon)
    origin_lat_r = np.radians(origin_lat)
    B = np.sin(lon_offset) * np.cos(lat_r)
    x = 0.5 * _A * np.log((1 + B) / (1 - B))
    y = _A * (np.arctan(np.tan(lat_r) / np.cos(lon_offset)) - origin_lat_r)
    return float(x), float(y)


def transverse_mercator_inverse(
    x: float,
    y: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    """Inverse Transverse Mercator: local XY meters to WGS-84 degrees."""
    origin_lat_r = np.radians(origin_lat)
    origin_lon_r = np.radians(origin_lon)
    x_n = x / _A
    y_n = y / _A
    D = y_n + origin_lat_r
    lon = np.arctan(np.sinh(x_n) / np.cos(D)) + origin_lon_r
    lat = np.arcsin(np.sin(D) / np.cosh(x_n))
    return float(np.degrees(lat)), float(np.degrees(lon))


def sphere_aabb_intersect(
    center: np.ndarray,
    radius: float,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> bool:
    """Test sphere-AABB intersection (Arvo's algorithm)."""
    clamped = np.clip(center, aabb_min, aabb_max)
    dist_sq = float(np.sum((center - clamped) ** 2))
    return dist_sq <= radius * radius


def obb_aabb_intersect(
    obb_center: np.ndarray,
    obb_half_axes: np.ndarray,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> bool:
    """Test OBB-AABB intersection via separating axis theorem."""
    aabb_center = 0.5 * (aabb_min + aabb_max)
    aabb_half = 0.5 * (aabb_max - aabb_min)
    t = obb_center - aabb_center
    obb_axes = np.zeros((3, 3))
    obb_extents = np.zeros(3)
    for i in range(3):
        length = np.linalg.norm(obb_half_axes[i])
        if length < 1e-12:
            obb_axes[i] = 0
            obb_extents[i] = 0
        else:
            obb_axes[i] = obb_half_axes[i] / length
            obb_extents[i] = length
    aabb_axes = np.eye(3)
    for axis in _sat_axes(aabb_axes, obb_axes):
        norm = np.linalg.norm(axis)
        if norm < 1e-12:
            continue
        axis = axis / norm
        proj_t = abs(np.dot(t, axis))
        proj_aabb = sum(aabb_half[i] * abs(np.dot(aabb_axes[i], axis)) for i in range(3))
        proj_obb = sum(obb_extents[i] * abs(np.dot(obb_axes[i], axis)) for i in range(3))
        if proj_t > proj_aabb + proj_obb:
            return False
    return True


def box_sphere_intersect(
    box_center: np.ndarray,
    box_half: np.ndarray,
    sphere_center: np.ndarray,
    sphere_radius: float,
) -> bool:
    """Test axis-aligned box vs sphere intersection."""
    return sphere_aabb_intersect(
        center=sphere_center,
        radius=sphere_radius,
        aabb_min=box_center - box_half,
        aabb_max=box_center + box_half,
    )


def _sat_axes(a_axes: np.ndarray, b_axes: np.ndarray):
    """Yield the 15 separating axes for two sets of 3 axes."""
    for i in range(3):
        yield a_axes[i]
    for i in range(3):
        yield b_axes[i]
    for i in range(3):
        for j in range(3):
            yield np.cross(a_axes[i], b_axes[j])

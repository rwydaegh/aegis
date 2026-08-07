"""Deterministic horizontal body orientation for ordered route walks.

The body heading is a property of the final ordered standpoints, not of the
camera that happened to provide a panorama. Keeping the calculation here gives
route builders and output validators one convention to share.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from .model import PANORAMA_LINKS, STREET_ROUTE, Walk

# ENU azimuth: zero points north, positive angles turn towards east.
BODY_YAW_CONVENTION = "ENU azimuth in degrees, clockwise from north (0=north, 90=east)"
BODY_YAW_FALLBACK = (
    "for a zero-motion tangent, use the first nonzero forward difference, then the first nonzero backward difference; "
    "use 0 degrees when the entire route has no horizontal motion"
)
_ROUTE_KINDS = frozenset((PANORAMA_LINKS, STREET_ROUTE))
_DEFAULT_EPSILON_M = 1.0e-9


def _azimuth_deg(delta: np.ndarray) -> float:
    """Return the ENU azimuth of one nonzero horizontal vector."""
    return float(np.degrees(np.arctan2(float(delta[0]), float(delta[1]))) % 360.0)


def _first_nonzero_forward(points: np.ndarray, index: int, epsilon_m: float) -> np.ndarray | None:
    origin = points[index, :2]
    for other in range(index + 1, len(points)):
        delta = points[other, :2] - origin
        if float(np.linalg.norm(delta)) > epsilon_m:
            return delta
    return None


def _first_nonzero_backward(points: np.ndarray, index: int, epsilon_m: float) -> np.ndarray | None:
    origin = points[index, :2]
    for other in range(index - 1, -1, -1):
        delta = origin - points[other, :2]
        if float(np.linalg.norm(delta)) > epsilon_m:
            return delta
    return None


def _validated_route_inputs(
    points: np.ndarray,
    epsilon_m: float,
    fallback_yaw_deg: float,
) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError(f"route points must have shape (P, 3), got {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError("route points must be finite")
    if not np.isfinite(epsilon_m) or epsilon_m <= 0.0:
        raise ValueError(f"epsilon_m must be positive and finite, got {epsilon_m!r}")
    if not np.isfinite(fallback_yaw_deg):
        raise ValueError(f"fallback_yaw_deg must be finite, got {fallback_yaw_deg!r}")
    return values


def _route_tangent(points: np.ndarray, index: int) -> np.ndarray | None:
    count = len(points)
    if count == 1:
        return None
    if index == 0:
        return points[1, :2] - points[0, :2]
    if index == count - 1:
        return points[-1, :2] - points[-2, :2]
    return points[index + 1, :2] - points[index - 1, :2]


def _fallback_tangent(points: np.ndarray, index: int, epsilon_m: float) -> np.ndarray | None:
    tangent = _first_nonzero_forward(points, index, epsilon_m)
    return tangent if tangent is not None else _first_nonzero_backward(points, index, epsilon_m)


def _point_yaw(
    points: np.ndarray,
    index: int,
    epsilon_m: float,
    fallback_yaw_deg: float,
) -> tuple[float, bool]:
    tangent = _route_tangent(points, index)
    if tangent is not None and float(np.linalg.norm(tangent)) > epsilon_m:
        return _azimuth_deg(tangent), False
    tangent = _fallback_tangent(points, index, epsilon_m)
    if tangent is None:
        return float(fallback_yaw_deg) % 360.0, True
    return _azimuth_deg(tangent), True


def route_body_yaw_deg(
    points: np.ndarray,
    *,
    epsilon_m: float = _DEFAULT_EPSILON_M,
    fallback_yaw_deg: float = 0.0,
) -> tuple[np.ndarray, int]:
    """Compute one horizontal body yaw for each ordered route point.

    Interior points use the centred tangent ``p[i + 1] - p[i - 1]``. Endpoints
    use a one-sided tangent. Duplicate or zero-motion points use the explicit
    deterministic fallback documented by :data:`BODY_YAW_FALLBACK`.
    """
    values = _validated_route_inputs(points, epsilon_m, fallback_yaw_deg)
    count = len(values)
    yaws = np.empty(count, dtype=np.float64)
    fallback_count = 0
    for index in range(count):
        yaws[index], used_fallback = _point_yaw(values, index, epsilon_m, fallback_yaw_deg)
        fallback_count += int(used_fallback)
    return yaws, fallback_count


def _hash_array(digest: Any, array: np.ndarray) -> None:
    value = np.ascontiguousarray(array, dtype=np.float64)
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(str(value.shape).encode("ascii"))
    digest.update(value.tobytes())


def route_order_hash(points: np.ndarray) -> str:
    """Hash the exact ordered route points used to derive body yaw."""
    digest = hashlib.sha256()
    _hash_array(digest, np.asarray(points))
    return digest.hexdigest()


def body_yaw_hash(points: np.ndarray, yaw_deg: np.ndarray) -> str:
    """Hash the route order and matching yaw array as one alignment seal."""
    digest = hashlib.sha256()
    _hash_array(digest, np.asarray(points))
    _hash_array(digest, np.asarray(yaw_deg))
    return digest.hexdigest()


def body_yaw_array_hash(yaw_deg: np.ndarray) -> str:
    """Hash yaw values together with their ordered indices for validation."""
    values = np.asarray(yaw_deg, dtype=np.float64)
    digest = hashlib.sha256()
    _hash_array(digest, np.arange(values.shape[0], dtype=np.float64))
    _hash_array(digest, values)
    return digest.hexdigest()


def validate_body_yaw_alignment(points: np.ndarray, yaw_deg: np.ndarray) -> np.ndarray:
    """Validate and return a read-only yaw array aligned to ``points``."""
    values = np.asarray(points)
    yaw = np.asarray(yaw_deg, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError(f"route points must have shape (P, 3), got {values.shape}")
    if yaw.ndim != 1 or yaw.shape[0] != values.shape[0]:
        raise ValueError(f"body_yaw_deg shape {yaw.shape} does not match route points ({values.shape[0]},)")
    if not np.all(np.isfinite(yaw)):
        raise ValueError("body_yaw_deg must contain only finite values")
    if np.any(yaw < 0.0) or np.any(yaw >= 360.0):
        raise ValueError("body_yaw_deg must be normalized to [0, 360)")
    answer = np.array(yaw, dtype=np.float64, copy=True)
    answer.setflags(write=False)
    return answer


def orient_route_walk(walk: Walk) -> Walk:
    """Attach a sealed route yaw array and provenance to ``walk``."""
    if walk.kind not in _ROUTE_KINDS:
        raise ValueError(f"route body yaw only applies to route walks, got {walk.kind!r}")
    yaw, fallback_count = route_body_yaw_deg(walk.points)
    yaw = validate_body_yaw_alignment(walk.points, yaw)
    provenance = {
        **walk.provenance,
        "body_yaw_deg": [float(value) for value in yaw],
        "body_yaw_convention": BODY_YAW_CONVENTION,
        "body_yaw_fallback": BODY_YAW_FALLBACK,
        "body_yaw_fallback_count": int(fallback_count),
        "body_yaw_route_order_hash": route_order_hash(walk.points),
        "body_yaw_hash": body_yaw_hash(walk.points, yaw),
        "body_yaw_array_hash": body_yaw_array_hash(yaw),
    }
    return Walk(
        points=walk.points,
        ground_z_m=walk.ground_z_m,
        step_m=walk.step_m,
        provenance=provenance,
        kind=walk.kind,
        site=walk.site,
        body_yaw_deg=yaw,
    )


__all__ = [
    "BODY_YAW_CONVENTION",
    "BODY_YAW_FALLBACK",
    "body_yaw_array_hash",
    "body_yaw_hash",
    "orient_route_walk",
    "route_body_yaw_deg",
    "route_order_hash",
    "validate_body_yaw_alignment",
]

"""Estimate smartphone device offset from body mesh geometry.

Analyzes STL mesh vertices to find the eye position and compute
a device offset (Z-up: [right, forward, up]) for smartphone placement.
"""

from __future__ import annotations

import numpy as np


def _face_direction_y(triangles: np.ndarray, eye_z: float, band: float = 0.03) -> float:
    """Determine whether the face points toward +Y or -Y using outward normals.

    At eye level, face-side triangles (nose, eyes, cheeks) have outward normals
    with a strong Y-component in the face direction.  The back of the head is
    smoother and its normals point the opposite way.

    Outward direction is determined per-triangle by checking whether the cross
    product points away from the band centroid (center of head), making this
    independent of triangle winding order.

    Parameters
    ----------
    triangles : (N, 3, 3)
        Triangle vertices in Z-up coordinates.
    eye_z : float
        Absolute Z coordinate of the eye band center.
    band : float
        Half-width of the Z band around eye_z.

    Returns
    -------
    float
        +1.0 if the face points toward +Y, -1.0 if toward -Y.
    """
    centroids = triangles.mean(axis=1)  # (N, 3)
    mask = np.abs(centroids[:, 2] - eye_z) < band
    if mask.sum() < 5:
        mask = np.abs(centroids[:, 2] - eye_z) < band * 3
    if mask.sum() < 3:
        return 1.0  # degenerate: assume +Y

    band_tris = triangles[mask]
    band_cents = centroids[mask]
    head_center = band_cents.mean(axis=0)  # approximate center of head slice

    v0, v1, v2 = band_tris[:, 0], band_tris[:, 1], band_tris[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)  # (M, 3), magnitude = 2 * area

    # Determine outward direction: cross product should point away from head center
    outward_vec = band_cents - head_center  # centroid-to-triangle direction
    dot = np.sum(cross * outward_vec, axis=1)
    # Flip cross products that point inward (negative dot = cross points toward center)
    flip = dot < 0
    cross[flip] *= -1

    # Area-weighted Y-component of outward normals
    net_y = cross[:, 1].sum()
    return 1.0 if net_y >= 0 else -1.0


def estimate_device_offset(
    vertices: np.ndarray,
    forward_distance: float = 0.30,
) -> list[float]:
    """Estimate smartphone position relative to body origin.

    Finds the eye position from the mesh and places the device
    *forward_distance* meters in front of the face at eye height.

    The face direction (+Y or -Y) is auto-detected from triangle normals,
    so this works regardless of which way the STL phantom faces.

    Parameters
    ----------
    vertices : (N, 3, 3)
        Triangle vertices in Z-up coordinates.
    forward_distance : float
        Distance in front of the face surface, in meters.

    Returns
    -------
    list[float]
        Device offset [x, y, z] in Z-up coords (right, forward, up),
        relative to the body with feet at ground (z=0).
    """
    pts = vertices.reshape(-1, 3)
    z_min = float(pts[:, 2].min())
    z_max = float(pts[:, 2].max())
    height = z_max - z_min

    if height < 0.01:
        return [0.0, forward_distance, 0.0]

    # Eye height: ~96% of body height, minus 2cm below the crown
    eye_z = z_min + height * 0.96 - 0.02

    # Band of points near eye height (within 1.5cm)
    eye_band = pts[np.abs(pts[:, 2] - eye_z) < 0.015]

    if len(eye_band) < 10:
        # Fallback: use broader band (5cm)
        eye_band = pts[np.abs(pts[:, 2] - eye_z) < 0.05]

    if len(eye_band) < 3:
        # Degenerate mesh: place at eye height, centered
        return [0.0, forward_distance, float(eye_z - z_min)]

    # Detect face direction from triangle normals at eye level
    face_sign = _face_direction_y(vertices, eye_z)

    # Face surface: extreme Y in the face direction
    if face_sign > 0:
        face_y = float(np.percentile(eye_band[:, 1], 97))
        face_pts = eye_band[eye_band[:, 1] > face_y - 0.03]
    else:
        face_y = float(np.percentile(eye_band[:, 1], 3))
        face_pts = eye_band[eye_band[:, 1] < face_y + 0.03]

    face_x = float(np.median(face_pts[:, 0])) if len(face_pts) > 0 else 0.0

    return [
        round(face_x, 4),
        round(face_y + face_sign * forward_distance, 4),
        round(eye_z - z_min, 4),
    ]

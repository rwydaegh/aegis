"""Estimate smartphone device offset from body mesh geometry.

Analyzes STL mesh vertices to find the eye position and compute
a device offset (Z-up: [right, forward, up]) for smartphone placement.
"""

from __future__ import annotations

import numpy as np


def estimate_device_offset(
    vertices: np.ndarray,
    forward_distance: float = 0.30,
) -> list[float]:
    """Estimate smartphone position relative to body origin.

    Finds the eye position from the mesh and places the device
    *forward_distance* meters in front of the face at eye height.

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

    # Face surface: 97th percentile of Y (forward) at eye level
    face_y = float(np.percentile(eye_band[:, 1], 97))

    # Face center X: median of points near the face surface
    face_pts = eye_band[eye_band[:, 1] > face_y - 0.03]
    face_x = float(np.median(face_pts[:, 0])) if len(face_pts) > 0 else 0.0

    return [
        round(face_x, 4),
        round(face_y + forward_distance, 4),
        round(eye_z - z_min, 4),
    ]

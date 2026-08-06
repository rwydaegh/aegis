"""The metric camera: world metres, camera axes and crop pixels, all invertible.

Within one rectilinear crop the panorama is an ordinary pinhole, so the map from
a triangle to its image is projective and exactly invertible. That is the whole
reason the fishnet can cut in the image and land the pieces back on the
triangle's own plane rather than re-tracing them.

Three coordinate systems and the two maps between them:

* world ENU metres, which is what the mesh, the walk and the sources speak,
* camera space ``(right, up, forward)`` in metres, with the camera at the origin,
* image pixels, with ``(0, 0)`` at the top left corner of the first pixel.

:func:`world_to_view` and :func:`view_to_world` are inverses over the whole
space. :func:`view_to_image` and :func:`image_to_view_directions` are inverses
only up to range, which :func:`image_to_view_directions` fixes by returning a ray
with unit forward component rather than a unit vector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .frames import view_basis

__all__ = [
    "CameraPose",
    "PinholeView",
    "image_to_view_directions",
    "view_basis",
    "view_to_image",
    "view_to_world",
    "world_to_view",
]


@dataclass(frozen=True)
class PinholeView:
    """One rectilinear crop of a panorama sphere.

    ``yaw_deg`` and ``pitch_deg`` orient the crop in the panorama-local frame,
    matching ``pano_geometry.PerspectiveView``.  Pixel ``(row, column)`` has its
    centre at image coordinate ``(column + 0.5, row + 0.5)``.
    """

    yaw_deg: float
    pitch_deg: float = 0.0
    fov_deg: float = 90.0
    width: int = 1024
    height: int = 1024

    def __post_init__(self) -> None:
        if self.width < 2 or self.height < 2:
            raise ValueError("a view needs at least two pixels on each axis")
        if not 0.0 < self.fov_deg < 180.0:
            raise ValueError("fov_deg must lie in (0, 180)")

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.height), int(self.width)

    @property
    def tangents(self) -> tuple[float, float]:
        tangent_x = math.tan(math.radians(self.fov_deg) / 2.0)
        return tangent_x, tangent_x / (self.width / self.height)


@dataclass(frozen=True)
class CameraPose:
    """Panorama centre and the rotation taking panorama-local axes to world."""

    position: np.ndarray
    rotation: np.ndarray

    def __post_init__(self) -> None:
        position = np.asarray(self.position, dtype=np.float64)
        rotation = np.asarray(self.rotation, dtype=np.float64)
        if position.shape != (3,) or rotation.shape != (3, 3):
            raise ValueError("position must have shape (3,) and rotation shape (3, 3)")
        if not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-6):
            raise ValueError("rotation must be orthonormal")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "rotation", rotation)


def world_to_view(points: np.ndarray, pose: CameraPose, view: PinholeView) -> np.ndarray:
    """World metres to camera axes ``(right, up, forward)`` of one crop."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
    local = (points - pose.position) @ pose.rotation
    return local @ np.stack([right, up, forward]).T


def view_to_world(points: np.ndarray, pose: CameraPose, view: PinholeView) -> np.ndarray:
    """Inverse of :func:`world_to_view`."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
    return pose.position + (points @ np.stack([right, up, forward])) @ pose.rotation.T


def view_to_image(points: np.ndarray, view: PinholeView) -> np.ndarray:
    """Camera-space points in front of the camera to pixel coordinates."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    if np.any(points[:, 2] <= 0.0):
        raise ValueError("points must lie strictly in front of the camera")
    tangent_x, tangent_y = view.tangents
    x = (points[:, 0] / (points[:, 2] * tangent_x) + 1.0) * 0.5 * view.width
    y = (1.0 - points[:, 1] / (points[:, 2] * tangent_y)) * 0.5 * view.height
    return np.stack([x, y], axis=1)


def image_to_view_directions(pixels: np.ndarray, view: PinholeView) -> np.ndarray:
    """Camera-space rays, with unit forward component, through image points.

    The forward component is left at one rather than normalised on purpose. The
    cutter intersects these with a plane by dividing a plane offset by the dot
    product, and a unit forward component makes the result the metric depth of
    the hit without a second division.
    """
    pixels = np.asarray(pixels, dtype=np.float64)
    if pixels.ndim != 2 or pixels.shape[1] != 2:
        raise ValueError("pixels must have shape (n, 2)")
    tangent_x, tangent_y = view.tangents
    x = (2.0 * pixels[:, 0] / view.width - 1.0) * tangent_x
    y = (1.0 - 2.0 * pixels[:, 1] / view.height) * tangent_y
    return np.stack([x, y, np.ones_like(x)], axis=1)

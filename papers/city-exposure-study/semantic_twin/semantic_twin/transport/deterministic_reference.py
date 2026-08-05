"""Deterministic first-bounce reference for the diffuse validation scene."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..illumination.sources import direct_from_sites
from .tracer import fresnel_power_reflectance, specular_share


@dataclass(frozen=True)
class FirstBounceReference:
    """Direct and one-bounce transfer from triangle quadrature."""

    direct: np.ndarray
    bounced: np.ndarray
    seconds: float
    subdivisions: int
    surface_samples: int

    @property
    def total(self) -> np.ndarray:
        return self.direct + self.bounced


def _triangle_centroids(
    vertices: np.ndarray,
    faces: np.ndarray,
    subdivisions: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if subdivisions < 1:
        raise ValueError("subdivisions must be positive")
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_area = np.linalg.norm(cross, axis=1)
    normal = cross / np.maximum(double_area, 1.0e-30)[:, None]

    barycentric = []
    n = int(subdivisions)
    for first in range(n):
        for second in range(n - first):
            barycentric.append(((first + 1.0 / 3.0) / n, (second + 1.0 / 3.0) / n))
            if first + second < n - 1:
                barycentric.append(((first + 2.0 / 3.0) / n, (second + 2.0 / 3.0) / n))
    uv = np.asarray(barycentric, dtype=np.float64)
    per_face = uv.shape[0]
    points = (
        triangles[:, None, 0]
        + uv[None, :, 0, None] * (triangles[:, None, 1] - triangles[:, None, 0])
        + uv[None, :, 1, None] * (triangles[:, None, 2] - triangles[:, None, 0])
    )
    weights = np.repeat(0.5 * double_area / (n * n), per_face)
    normals = np.repeat(normal, per_face, axis=0)
    face_index = np.repeat(np.arange(faces.shape[0], dtype=np.int64), per_face)
    return points.reshape(-1, 3), normals, weights, face_index


def first_bounce_reference(
    geometry: Any,
    vertices: np.ndarray,
    faces: np.ndarray,
    sources: np.ndarray,
    receivers: np.ndarray,
    *,
    permittivity: complex,
    rms_height_m: float,
    wavelength_m: float,
    subdivisions: int = 64,
    ray_epsilon_m: float = 1.0e-3,
    connection_lift_m: float = 1.0e-2,
) -> FirstBounceReference:
    """Integrate the one-bounce Lambertian term over triangle area.

    The quadrature uses the centroids of ``subdivisions**2`` equal-area
    subtriangles per input triangle. Visibility is evaluated by shadow rays,
    while the transfer itself has no random samples or path discovery.
    """
    started = time.perf_counter()
    sources = np.atleast_2d(np.asarray(sources, dtype=np.float64))
    receivers = np.atleast_2d(np.asarray(receivers, dtype=np.float64))
    points, face_normals, weights, face_index = _triangle_centroids(vertices, faces, subdivisions)
    direct, _ = direct_from_sites(geometry, receivers, sources)
    bounced = np.zeros(receivers.shape[0], dtype=np.float64)

    for receiver_index, receiver in enumerate(receivers):
        from_receiver = points - receiver
        receiver_range = np.linalg.norm(from_receiver, axis=1)
        receiver_direction = from_receiver / np.maximum(receiver_range, 1.0e-30)[:, None]
        hit, travel, _, hit_face = geometry.intersect(
            np.repeat(receiver[None, :], points.shape[0], axis=0) + ray_epsilon_m * receiver_direction,
            receiver_direction,
        )
        receiver_visible = hit & (np.asarray(hit_face) == face_index)
        receiver_visible &= travel >= receiver_range - 2.0 * ray_epsilon_m

        facing = np.sign(-np.einsum("ij,ij->i", receiver_direction, face_normals))
        facing[facing == 0.0] = 1.0
        normal = face_normals * facing[:, None]
        receiver_cosine = np.clip(-np.einsum("ij,ij->i", receiver_direction, normal), 0.0, 1.0)
        reflectance = fresnel_power_reflectance(
            receiver_cosine,
            np.full(receiver_cosine.shape, complex(permittivity)),
        )
        diffuse_share = 1.0 - specular_share(
            np.full(receiver_cosine.shape, float(rms_height_m)),
            receiver_cosine,
            float(wavelength_m),
        )
        receiver_factor = (
            weights * receiver_visible * receiver_cosine * reflectance * diffuse_share / (np.pi * receiver_range**2)
        )

        total = 0.0
        for source in sources:
            to_source = source - points
            source_range = np.linalg.norm(to_source, axis=1)
            source_direction = to_source / np.maximum(source_range, 1.0e-30)[:, None]
            source_cosine = np.einsum("ij,ij->i", source_direction, normal)
            worth = receiver_visible & (source_cosine > 0.0) & (source_range > 0.5)
            if not np.any(worth):
                continue
            start = points[worth] + connection_lift_m * normal[worth] + ray_epsilon_m * source_direction[worth]
            blocked, source_travel, _, _ = geometry.intersect(start, source_direction[worth])
            clear = (~blocked) | (source_travel >= source_range[worth] - 2.0 * ray_epsilon_m)
            total += float(
                np.sum(receiver_factor[worth][clear] * source_cosine[worth][clear] / source_range[worth][clear] ** 2)
            )
        bounced[receiver_index] = total / sources.shape[0]

    return FirstBounceReference(
        direct=np.asarray(direct, dtype=np.float64),
        bounced=bounced,
        seconds=time.perf_counter() - started,
        subdivisions=int(subdivisions),
        surface_samples=int(points.shape[0]),
    )

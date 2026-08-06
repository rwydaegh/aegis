"""How high the ground is under one camera, and how confident that answer is.

The scene config carries a single ``camera_ground_z_m`` for the whole square.
That is fine for a flat market and wrong for a camera on a flight of steps, on a
ramp, or on a bridge, where it hands that camera the pavement height measured
under a different one. So the ground is cast for under this camera's own easting
and northing, and the scene constant survives as the datum for the search
ceiling and as the fallback.

This is not the walk's ground datum and the two answer different questions.
:mod:`semantic_twin.walk.ground` measures the one walkable level of a whole
square, which is a statement about the square. This module measures the surface
under one point, which is a statement about one camera. They disagree at seven
of the 51 admitted stations in this study, and both are right about their own
question.

The patch median rather than the single central hit is what keeps a hole in the
photogrammetry, or a single-triangle spike at street level, from becoming a
confident wrong number. The spread is reported alongside so a bad patch is
visible rather than silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class GroundSample:
    """Support-mesh ground elevation under one camera.

    ``spread_m`` and ``peak_to_peak_m`` describe the patch the value was taken
    over, so a camera standing on a step or over a hole in the photogrammetry is
    visible as a wide spread rather than as a confidently wrong number.
    """

    elevation_m: float
    spread_m: float
    peak_to_peak_m: float
    n_hits: int
    n_samples: int
    patch_m: float
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ground_elevation_m": self.elevation_m,
            "ground_spread_m": self.spread_m,
            "ground_peak_to_peak_m": self.peak_to_peak_m,
            "ground_n_hits": self.n_hits,
            "ground_n_samples": self.n_samples,
            "ground_patch_m": self.patch_m,
            "ground_source": self.source,
        }


def _downward_hits(vertices: np.ndarray, faces: np.ndarray, points: np.ndarray, ceiling_z: float) -> list[float]:
    """Topmost surface at or below ``ceiling_z`` under each xy point."""
    triangles = vertices[faces]
    ax, ay = triangles[:, 0, 0], triangles[:, 0, 1]
    bx, by = triangles[:, 1, 0], triangles[:, 1, 1]
    cx, cy = triangles[:, 2, 0], triangles[:, 2, 1]
    lo_x = np.minimum(np.minimum(ax, bx), cx)
    hi_x = np.maximum(np.maximum(ax, bx), cx)
    lo_y = np.minimum(np.minimum(ay, by), cy)
    hi_y = np.maximum(np.maximum(ay, by), cy)
    area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    elevations: list[float] = []
    for x, y in points:
        near = (lo_x <= x) & (hi_x >= x) & (lo_y <= y) & (hi_y >= y) & (np.abs(area) > 1e-12)
        if not np.any(near):
            continue
        index = np.flatnonzero(near)
        w0 = ((bx[index] - x) * (cy[index] - y) - (cx[index] - x) * (by[index] - y)) / area[index]
        w1 = ((cx[index] - x) * (ay[index] - y) - (ax[index] - x) * (cy[index] - y)) / area[index]
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not np.any(inside):
            continue
        z = w0[inside] * triangles[index[inside], 0, 2]
        z += w1[inside] * triangles[index[inside], 1, 2]
        z += w2[inside] * triangles[index[inside], 2, 2]
        below = z[z <= ceiling_z]
        if below.size:
            elevations.append(float(below.max()))
    return elevations


def ground_elevation(
    vertices: np.ndarray,
    faces: np.ndarray,
    easting_m: float,
    northing_m: float,
    *,
    ceiling_z_m: float,
    patch_m: float = 3.0,
    samples_per_axis: int = 5,
) -> GroundSample:
    """Cast down onto the support mesh under one camera and report the spread.

    ``ceiling_z_m`` is where the downward ray starts, so an arcade roof or a
    balcony above the camera is not mistaken for the pavement. The patch median
    is used rather than the single central hit because the photogrammetry has
    occasional holes and single-triangle spikes at street level.
    """
    if samples_per_axis < 1:
        raise ValueError("samples_per_axis must be at least one")
    if patch_m < 0.0:
        raise ValueError("patch_m must be non-negative")
    offsets = (
        np.zeros(1)
        if samples_per_axis == 1 or patch_m == 0.0
        else np.linspace(-patch_m / 2.0, patch_m / 2.0, samples_per_axis)
    )
    grid = np.stack(np.meshgrid(offsets + easting_m, offsets + northing_m), axis=-1).reshape(-1, 2)
    elevations = _downward_hits(vertices, faces, grid, ceiling_z_m)
    if not elevations:
        raise ValueError(f"support mesh has no surface under ({easting_m:.3f}, {northing_m:.3f}) below {ceiling_z_m}")
    values = np.asarray(elevations, dtype=float)
    return GroundSample(
        elevation_m=float(np.median(values)),
        spread_m=float(values.std(ddof=1)) if values.size > 1 else 0.0,
        peak_to_peak_m=float(values.max() - values.min()),
        n_hits=int(values.size),
        n_samples=int(len(grid)),
        patch_m=float(patch_m),
        source="support mesh downward ray cast, patch median",
    )


def camera_altitude(
    scene: dict[str, Any],
    easting_m: float,
    northing_m: float,
    *,
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    search_up_m: float = 5.0,
    patch_m: float = 3.0,
) -> tuple[float, dict[str, Any]]:
    """Camera altitude for one panorama, measured where possible.

    ``camera_ground_z_m`` in the scene config is a single constant for the whole
    site, so a camera on a flight of steps or a ramp inherits the pavement height
    under a different camera. When the support mesh is available the ground is
    instead cast for under this camera's own easting and northing, and the scene
    constant survives only as the datum for the search ceiling and as the
    fallback. ``search_up_m`` is how far above that datum a surface may be and
    still count as ground, which keeps an arcade roof out of the answer.
    """
    ground_z = float(scene["camera_ground_z_m"])
    camera_height = float(scene.get("camera_height_m", 2.5))
    if support_mesh is None:
        return ground_z + camera_height, {
            "altitude_source": "scene camera_ground_z_m plus configured camera height",
            "scene_camera_ground_z_m": ground_z,
        }
    vertices, faces = support_mesh
    sample = ground_elevation(
        vertices,
        faces,
        easting_m,
        northing_m,
        ceiling_z_m=ground_z + search_up_m,
        patch_m=patch_m,
    )
    provenance: dict[str, Any] = {
        "altitude_source": "support mesh downward ray cast under this camera plus configured camera height",
        "scene_camera_ground_z_m": ground_z,
        "ground_minus_scene_constant_m": sample.elevation_m - ground_z,
    }
    provenance.update(sample.as_dict())
    return sample.elevation_m + camera_height, provenance

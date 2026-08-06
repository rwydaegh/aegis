"""Where the image and the geometry disagree.

Two independent disagreements are recorded here and neither uses the skyline
objective that produced the pose.

:func:`sky_conflict` compares the segmented sky mask with the support mesh
silhouette. It uses the whole two dimensional mask, including courtyard gaps,
arcade openings and sky seen between towers, and it asks a first hit ray cast
rather than a per azimuth envelope. This is the test that catches a camera
driven inside a building, which the skyline residual cannot: a pose matching the
inside of a wall scores well on the objective and fills its sky with mesh.

:class:`DepthConflictState` is the per pixel version of the same question, from
monocular depth against the mesh first hit. It is the vocabulary
:mod:`~semantic_twin.vision.ledger` stores per observation.

Note before using the two together: ``compare_mesh_depth.py`` writes a *second*
and incompatible integer vocabulary for the depth axis, and the two disagree on
the meaning of every code, ``no_mesh`` against ``AGREEMENT`` included. See
finding 13 in ``docs/BUGS.md``. Nothing joins them today, and this module does
not fix it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np

from ..pano_geometry import equirectangular_directions, panorama_to_world_matrix
from ..scene.mesh import first_hit_range


class DepthConflictState(IntEnum):
    """Relationship between image depth evidence and the support mesh."""

    AGREEMENT = 0
    UNCERTAIN = 1
    FRONT_BLOCKER = 2
    MESH_POSE_CONFLICT = 3
    NO_MESH_HIT = 4


@dataclass(frozen=True)
class SkyConflict:
    """Agreement between the segmented sky mask and the support-mesh silhouette.

    Independent of the skyline objective: it uses the whole two-dimensional mask
    including courtyard gaps, arcade openings and sky seen between towers, and it
    is a first-hit ray cast rather than a per-azimuth envelope. ``sky_with_mesh``
    is mesh where the image sees sky, and ``structure_without_mesh`` is the
    opposite error, so their balance says which way a misregistration points.

    ``sky_with_distant_mesh`` drops hits nearer than ``minimum_range_m``. That
    split matters because a photogrammetry tree canopy arching over the camera
    produces sky conflicts at a few metres that no pose can remove, and at
    Korenmarkt those are more than half the raw count.
    """

    sky_with_mesh: float
    sky_with_distant_mesh: float
    structure_without_mesh: float
    n_sky: int
    n_structure: int
    n_directions: int
    conflict_median_range_m: float
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def disagreement(self) -> float:
        """Both errors together, which is what tracks pose quality.

        Deliberately built on ``sky_with_mesh`` rather than the distant-only
        variant. A camera driven below the pavement puts every conflict within a
        metre, so a range-filtered term reads as a perfect score exactly where the
        pose is most wrong.
        """
        return self.sky_with_mesh + self.structure_without_mesh

    def as_dict(self) -> dict[str, Any]:
        return {
            "sky_with_mesh_hit_fraction": self.sky_with_mesh,
            "sky_with_distant_mesh_hit_fraction": self.sky_with_distant_mesh,
            "structure_without_mesh_hit_fraction": self.structure_without_mesh,
            "disagreement": self.disagreement,
            "n_sky_directions": self.n_sky,
            "n_structure_directions": self.n_structure,
            "n_directions": self.n_directions,
            "conflict_median_range_m": self.conflict_median_range_m,
            **self.settings,
        }


def sky_conflict(
    vertices: np.ndarray,
    faces: np.ndarray,
    entity: np.ndarray,
    sky_id: int,
    structural_ids: set[int],
    camera: np.ndarray,
    *,
    heading_deg: float,
    pitch_deg: float,
    roll_deg: float,
    width: int = 512,
    height: int = 256,
    min_elevation_deg: float = -60.0,
    minimum_range_m: float = 8.0,
) -> SkyConflict:
    """Compare the segmented sky mask with the support-mesh silhouette.

    This is the second opinion: it never touches the skyline objective, uses the
    full two-dimensional mask rather than one boundary per azimuth, and asks a
    first-hit ray cast whether geometry stands where the image sees sky. Rays
    below ``min_elevation_deg`` are dropped because the camera rig and the road
    surface directly under the vehicle are not a registration signal.
    """
    directions = equirectangular_directions(width, height)
    rotation = panorama_to_world_matrix(heading_deg, pitch_deg=pitch_deg, roll_deg=roll_deg)
    world = directions.reshape(-1, 3) @ rotation.T
    elevation_deg = np.degrees(np.arcsin(np.clip(world[:, 2], -1.0, 1.0)))
    usable = elevation_deg >= min_elevation_deg
    ranges = np.full(len(world), np.nan)
    ranges[usable] = first_hit_range(vertices, faces, np.asarray(camera, dtype=float), world[usable])

    rows = np.clip((np.arange(height) + 0.5) / height * entity.shape[0], 0, entity.shape[0] - 1).astype(int)
    columns = np.clip((np.arange(width) + 0.5) / width * entity.shape[1], 0, entity.shape[1] - 1).astype(int)
    labels = entity[np.ix_(rows, columns)].reshape(-1)

    hit = np.isfinite(ranges)
    distant = hit & (ranges > minimum_range_m)
    is_sky = (labels == sky_id) & usable
    is_structure = np.isin(labels, list(structural_ids)) & usable
    conflict = is_sky & hit
    n_sky = max(int(is_sky.sum()), 1)
    return SkyConflict(
        sky_with_mesh=float(conflict.sum() / n_sky),
        sky_with_distant_mesh=float((is_sky & distant).sum() / n_sky),
        structure_without_mesh=float((is_structure & ~hit).sum() / max(int(is_structure.sum()), 1)),
        n_sky=int(is_sky.sum()),
        n_structure=int(is_structure.sum()),
        n_directions=int(usable.sum()),
        conflict_median_range_m=float(np.median(ranges[conflict])) if conflict.any() else float("nan"),
        settings={
            "grid": [height, width],
            "min_elevation_deg": min_elevation_deg,
            "minimum_range_m": minimum_range_m,
            "method": "equirectangular first-hit ray cast against the support mesh",
        },
    )

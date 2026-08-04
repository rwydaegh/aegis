"""What one panorama centre sees, as triangles that carry their own evidence.

The result of a cut is not merely a mesh. Every face carries an outward normal,
a metric area, the solid angle it subtends from the capture point, its semantic
class, material posterior, confidence, and the source pixels it was built from,
so a propagation stage can use it as the first-hit acceleration structure
directly.

Faces that were considered and rejected are kept in a parallel table with the
reason, because a surface wrongly dropped deletes a propagation path just as
surely as a surface wrongly kept invents a phantom scatterer.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import numpy as np

# Why a candidate surface element did not enter the visible surface set.
REJECTION_REASONS: dict[str, int] = {
    "degenerate_triangle": 1,
    "behind_near_plane": 2,
    "outside_crop": 3,
    "subpixel_footprint": 4,
    "occluded_by_support_mesh": 5,
    "clutter_in_front": 6,
    "transient_object": 7,
    "no_semantic_support": 8,
    "below_minimum_area": 9,
    "grazing_plane": 10,
    "not_support_surface": 11,
    "mesh_or_pose_conflict": 12,
}


@dataclass(frozen=True)
class FishnetSurface:
    """Visible surface elements at one panorama centre, with their evidence.

    ``vertices`` and ``faces`` are an ordinary indexed triangle soup in world
    metres.  Everything else is parallel per-face bookkeeping the propagation
    stage needs: ``face_normal`` points back towards the capture point because
    these are by construction the surfaces that point at it, ``face_solid_angle``
    is the exact solid angle of the triangle seen from that point, and
    ``face_visible_fraction`` exposes the occlusion decision instead of hiding
    it.  Provenance is a compressed row structure: face ``i`` was built from the
    source pixels ``pixel_indices[pixel_offsets[g] : pixel_offsets[g + 1]]``
    with ``g = face_group[i]``, given as flat row-major image indices.
    """

    vertices: np.ndarray
    faces: np.ndarray
    face_image: np.ndarray
    face_depth: np.ndarray
    face_normal: np.ndarray
    face_centroid: np.ndarray
    face_area_m2: np.ndarray
    face_solid_angle_sr: np.ndarray
    face_class: np.ndarray
    face_class_probability: np.ndarray
    face_confidence: np.ndarray
    face_material: np.ndarray | None
    face_source_triangle: np.ndarray
    face_pixel_support: np.ndarray
    face_visible_fraction: np.ndarray
    face_group: np.ndarray
    pixel_offsets: np.ndarray
    pixel_indices: np.ndarray
    rejected_source_triangle: np.ndarray
    rejected_reason: np.ndarray
    rejected_image_area_px: np.ndarray
    camera_position: np.ndarray
    report: dict[str, float] = field(default_factory=dict)

    @property
    def triangle_count(self) -> int:
        return int(self.faces.shape[0])

    def source_pixels(self, face: int) -> np.ndarray:
        """Flat image indices of the pixels that produced one face."""
        group = int(self.face_group[face])
        return self.pixel_indices[self.pixel_offsets[group] : self.pixel_offsets[group + 1]]


@dataclass(frozen=True)
class FishnetRaster:
    """Round-trip render of a surface set back into the source image."""

    class_map: np.ndarray
    source_triangle: np.ndarray
    depth_m: np.ndarray


def save_fishnet(surface: FishnetSurface, path: str | pathlib.Path) -> None:
    """Write the visible surface set to a Blender-free NPZ."""
    arrays = {
        name: value
        for name, value in vars(surface).items()
        if isinstance(value, np.ndarray) and name != "face_material"
    }
    if surface.face_material is not None:
        arrays["face_material"] = surface.face_material
    arrays["report_keys"] = np.asarray(list(surface.report), dtype=np.str_)
    arrays["report_values"] = np.asarray(list(surface.report.values()), dtype=np.float64)
    np.savez_compressed(path, **arrays)


def load_fishnet(path: str | pathlib.Path) -> FishnetSurface:
    """Read a surface set written by :func:`save_fishnet`."""
    with np.load(path) as data:
        stored = {name: data[name] for name in data.files}
    report = {
        str(key): float(value)
        for key, value in zip(stored.pop("report_keys"), stored.pop("report_values"), strict=True)
    }
    stored.setdefault("face_material", None)
    return FishnetSurface(report=report, **stored)

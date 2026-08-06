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

FISHNET_FORMAT_VERSION = 2

REJECTED_GEOMETRY_KINDS: dict[str, int] = {
    "unavailable": 0,
    "exact_cut_piece": 1,
    "clipped_footprint": 2,
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

    Rejected candidates remain one row each in ``rejected_*``. Version two adds
    their exact triangle soup. ``rejected_face_record`` maps each rejected face
    back to its row, while ``rejected_face_offsets`` exposes the same relation as
    a compact row index. Faces are stored in record order, so record ``i`` owns
    exactly the block ``offsets[i] : offsets[i + 1]``. A row with no reliable
    inverse projection has no faces.
    ``rejected_geometry_kind`` is 0 for unavailable geometry, 1 for a cut piece,
    and 2 for a clipped source footprint.
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
    rejected_vertices: np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.float64))
    rejected_faces: np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.int64))
    rejected_face_image: np.ndarray = field(default_factory=lambda: np.zeros((0, 3, 2), dtype=np.float64))
    rejected_face_record: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    rejected_face_offsets: np.ndarray = field(default_factory=lambda: np.zeros(1, dtype=np.int64))
    rejected_geometry_kind: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.uint8))
    format_version: int = FISHNET_FORMAT_VERSION
    report: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        records = int(self.rejected_reason.shape[0])
        if self.rejected_source_triangle.shape != (records,) or self.rejected_image_area_px.shape != (records,):
            raise ValueError("rejected record columns must have equal length")
        if self.rejected_geometry_kind.shape != (records,):
            raise ValueError("rejected_geometry_kind must have one value per rejected record")
        if not np.issubdtype(self.rejected_geometry_kind.dtype, np.integer):
            raise ValueError("rejected_geometry_kind must contain integer codes")
        if np.any(
            (self.rejected_geometry_kind < 0) | (self.rejected_geometry_kind > max(REJECTED_GEOMETRY_KINDS.values()))
        ):
            raise ValueError("rejected_geometry_kind contains an unknown code")
        if self.rejected_vertices.ndim != 2 or self.rejected_vertices.shape[1:] != (3,):
            raise ValueError("rejected_vertices must have shape (n, 3)")
        if not np.issubdtype(self.rejected_vertices.dtype, np.number) or not np.all(
            np.isfinite(self.rejected_vertices)
        ):
            raise ValueError("rejected_vertices must contain finite numbers")
        if self.rejected_faces.ndim != 2 or self.rejected_faces.shape[1:] != (3,):
            raise ValueError("rejected_faces must have shape (n, 3)")
        if not np.issubdtype(self.rejected_faces.dtype, np.integer):
            raise ValueError("rejected_faces must contain integer vertex indices")
        faces = int(self.rejected_faces.shape[0])
        if self.rejected_face_image.shape != (faces, 3, 2):
            raise ValueError("rejected_face_image must have shape (n_faces, 3, 2)")
        if not np.issubdtype(self.rejected_face_image.dtype, np.number) or not np.all(
            np.isfinite(self.rejected_face_image)
        ):
            raise ValueError("rejected_face_image must contain finite numbers")
        if self.rejected_face_record.shape != (faces,):
            raise ValueError("rejected_face_record must have one value per rejected face")
        if not np.issubdtype(self.rejected_face_record.dtype, np.integer):
            raise ValueError("rejected_face_record must contain integer record indices")
        if faces and (
            np.any(self.rejected_faces < 0)
            or np.any(self.rejected_faces >= self.rejected_vertices.shape[0])
            or np.any(self.rejected_face_record < 0)
            or np.any(self.rejected_face_record >= records)
        ):
            raise ValueError("rejected face geometry contains an out-of-range index")
        if self.rejected_face_offsets.shape != (records + 1,):
            raise ValueError("rejected_face_offsets must have one boundary per rejected record")
        if not np.issubdtype(self.rejected_face_offsets.dtype, np.integer):
            raise ValueError("rejected_face_offsets must contain integer boundaries")
        if self.rejected_face_offsets[0] != 0:
            raise ValueError("rejected_face_offsets must start at zero")
        face_counts = np.diff(self.rejected_face_offsets)
        if np.any(face_counts < 0):
            raise ValueError("rejected_face_offsets must be nondecreasing")
        if self.rejected_face_offsets[-1] != faces:
            raise ValueError("rejected_face_offsets must end at the rejected face count")
        expected_records = np.repeat(np.arange(records, dtype=np.int64), face_counts)
        if not np.array_equal(self.rejected_face_record, expected_records):
            raise ValueError("rejected_face_record must follow rejected_face_offsets record order")
        unavailable = self.rejected_geometry_kind == REJECTED_GEOMETRY_KINDS["unavailable"]
        if np.any(unavailable & (face_counts != 0)):
            raise ValueError("unavailable rejected geometry records must not own faces")
        if np.any(~unavailable & (face_counts == 0)):
            raise ValueError("exact rejected geometry records must own at least one face")

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
    arrays["rejected_vertices"] = surface.rejected_vertices.astype(np.float32)
    arrays["rejected_faces"] = surface.rejected_faces.astype(np.int32)
    arrays["rejected_face_image"] = surface.rejected_face_image.astype(np.float32)
    arrays["rejected_face_record"] = surface.rejected_face_record.astype(np.int32)
    arrays["rejected_face_offsets"] = surface.rejected_face_offsets.astype(np.int32)
    arrays["rejected_geometry_kind"] = surface.rejected_geometry_kind.astype(np.uint8)
    arrays["fishnet_format_version"] = np.asarray(surface.format_version, dtype=np.int16)
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
    format_version = int(stored.pop("fishnet_format_version", 1))
    stored.setdefault("face_material", None)
    stored.setdefault("rejected_vertices", np.zeros((0, 3), dtype=np.float64))
    stored.setdefault("rejected_faces", np.zeros((0, 3), dtype=np.int64))
    stored.setdefault("rejected_face_image", np.zeros((0, 3, 2), dtype=np.float64))
    stored.setdefault("rejected_face_record", np.zeros(0, dtype=np.int64))
    stored.setdefault(
        "rejected_face_offsets",
        np.zeros(stored["rejected_reason"].shape[0] + 1, dtype=np.int64),
    )
    stored.setdefault("rejected_geometry_kind", np.zeros(stored["rejected_reason"].shape[0], dtype=np.uint8))
    return FishnetSurface(format_version=format_version, report=report, **stored)

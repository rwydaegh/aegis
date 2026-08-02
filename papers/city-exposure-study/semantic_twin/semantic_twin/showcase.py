"""Assemble every shipped twin artifact into one renderable payload.

This module is the pure half of the showcase render. It reads the support mesh,
the fishnet surface set, the rejection table, the tile-texture material channel,
the panorama material sphere and the dynamic body layer, and turns them into a
small number of triangle soups with named per-face colour channels. Nothing here
imports ``bpy``, so it is unit-testable and it runs under the project
interpreter rather than under Blender's.

``showcase_blender.py`` consumes the payload written by :func:`write_payload`.
The split exists because Blender bundles numpy, scipy and Pillow but not
trimesh, and the visible-surface classification needs an Embree ray cast.

Colour is presentation only. No number that reaches propagation is read back
out of a colour channel.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from semantic_twin.palette import PREFERRED_COLOURS, fallback_colour

# The four shipped crops are 90 degree square pinholes at pitch zero, so the
# fishnet only ever describes this elevation band. The visible-surface
# classification is restricted to the same band, otherwise a roof that the
# panorama can see but no crop covers would be counted as observed.
CROP_HALF_ELEVATION_DEG = 45.0

# A face counts as its own first hit when the ray stops within this distance of
# the centroid. Pure index equality loses the coplanar silhouette ties that
# ``raycast_mesh_depth`` also reports, and those are not occlusion.
FIRST_HIT_TOLERANCE_M = 0.05

VISIBILITY_STATES: tuple[str, ...] = ("panorama", "texture", "unseen")

VISIBILITY_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "panorama": (1.00, 0.36, 0.06, 1.0),
    "texture": (0.18, 0.44, 0.70, 1.0),
    "unseen": (0.20, 0.21, 0.24, 1.0),
}

# Rejection reasons split into what removed the surface. Withheld for a moving
# object, hidden behind support geometry, handed to a separate proxy, or thrown
# out by a numeric guard.
REJECTION_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "transient_object": (0.95, 0.15, 0.35, 1.0),
    "clutter_in_front": (0.98, 0.62, 0.05, 1.0),
    "mesh_or_pose_conflict": (0.85, 0.20, 0.85, 1.0),
    "not_support_surface": (0.20, 0.75, 0.85, 1.0),
    "occluded_by_support_mesh": (0.35, 0.36, 0.40, 1.0),
    "below_minimum_area": (0.55, 0.55, 0.30, 1.0),
    "no_semantic_support": (0.45, 0.30, 0.70, 1.0),
    "subpixel_footprint": (0.60, 0.45, 0.35, 1.0),
    "degenerate_triangle": (0.70, 0.70, 0.70, 1.0),
    "behind_near_plane": (0.70, 0.70, 0.70, 1.0),
    "outside_crop": (0.70, 0.70, 0.70, 1.0),
    "grazing_plane": (0.70, 0.70, 0.70, 1.0),
}

# One colour per ITU-facing radio material. These are the twenty rows of
# ``rf_material_id2label``, in that order.
MATERIAL_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "unknown": (0.35, 0.35, 0.38, 1.0),
    "air": (0.85, 0.93, 0.98, 1.0),
    "brick": (0.78, 0.30, 0.20, 1.0),
    "concrete": (0.50, 0.48, 0.44, 1.0),
    "plasterboard": (0.96, 0.80, 0.42, 1.0),
    "plywood": (0.80, 0.60, 0.35, 1.0),
    "chipboard": (0.72, 0.55, 0.32, 1.0),
    "wood": (0.55, 0.36, 0.18, 1.0),
    "glass": (0.25, 0.72, 0.88, 1.0),
    "metal": (0.72, 0.75, 0.82, 1.0),
    "marble": (0.66, 0.70, 0.74, 1.0),
    "asphalt_concrete": (0.28, 0.28, 0.30, 1.0),
    "ceramic": (0.88, 0.55, 0.45, 1.0),
    "polymer": (0.85, 0.30, 0.72, 1.0),
    "fabric": (0.90, 0.45, 0.55, 1.0),
    "soil": (0.45, 0.33, 0.20, 1.0),
    "water": (0.15, 0.40, 0.75, 1.0),
    "vegetation_effective": (0.24, 0.62, 0.26, 1.0),
    "human_tissue": (0.96, 0.72, 0.60, 1.0),
    "vehicle_composite": (0.50, 0.20, 0.60, 1.0),
}

# Perceptually ordered ramp for the scalar channels. Sampled from viridis so a
# reader who knows the colour map reads the direction right without a legend.
_VIRIDIS = np.array(
    [
        [0.267004, 0.004874, 0.329415],
        [0.282623, 0.140926, 0.457517],
        [0.253935, 0.265254, 0.529983],
        [0.206756, 0.371758, 0.553117],
        [0.163625, 0.471133, 0.558148],
        [0.127568, 0.566949, 0.550556],
        [0.134692, 0.658636, 0.517649],
        [0.266941, 0.748751, 0.440573],
        [0.477504, 0.821444, 0.318195],
        [0.741388, 0.873449, 0.149561],
        [0.993248, 0.906157, 0.143936],
    ]
)


def srgb_to_linear(colours: np.ndarray) -> np.ndarray:
    """Display sRGB to linear light, leaving alpha alone.

    Every palette entry in this module is a display colour: it is what the
    legend swatch is drawn with. Blender reads a float colour attribute as
    linear scene-referred light and the Standard view transform encodes sRGB on
    the way out, so handing it the display value directly renders a lighter,
    less saturated colour than the legend. Converting here is what makes the
    rendered pixel equal to the swatch rather than merely resemble it.
    """
    values = np.array(colours, dtype=np.float64, copy=True)
    rgb = values[..., :3]
    values[..., :3] = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return values.astype(np.float32)


def linear_to_srgb(colours: np.ndarray) -> np.ndarray:
    """Inverse of :func:`srgb_to_linear`, for checking a rendered pixel."""
    values = np.array(colours, dtype=np.float64, copy=True)
    rgb = np.clip(values[..., :3], 0.0, None)
    values[..., :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1.0 / 2.4) - 0.055)
    return values.astype(np.float32)


def ramp(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """Map a scalar field to opaque viridis RGBA, clipped to ``[low, high]``."""
    if high <= low:
        raise ValueError("ramp needs high > low")
    t = np.clip((np.asarray(values, dtype=np.float64) - low) / (high - low), 0.0, 1.0)
    position = t * (len(_VIRIDIS) - 1)
    lower = np.floor(position).astype(np.int64)
    upper = np.minimum(lower + 1, len(_VIRIDIS) - 1)
    blend = (position - lower)[:, None]
    rgb = _VIRIDIS[lower] * (1.0 - blend) + _VIRIDIS[upper] * blend
    return np.concatenate([rgb, np.ones((len(rgb), 1))], axis=1).astype(np.float32)


def class_colour(class_id: int, name: str) -> tuple[float, float, float, float]:
    """Display colour for one entity class, matching the rest of the project."""
    return PREFERRED_COLOURS.get(name.casefold(), fallback_colour(int(class_id)))


@dataclass
class Layer:
    """One triangle soup with a set of named per-face colour channels."""

    name: str
    vertices: np.ndarray
    faces: np.ndarray
    channels: dict[str, np.ndarray] = field(default_factory=dict)
    legends: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    scalars: dict[str, np.ndarray] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.vertices = np.ascontiguousarray(self.vertices, dtype=np.float64)
        self.faces = np.ascontiguousarray(self.faces, dtype=np.int64)
        if self.vertices.ndim != 2 or self.vertices.shape[1] != 3:
            raise ValueError(f"{self.name}: vertices must be (N, 3)")
        if self.faces.ndim != 2 or self.faces.shape[1] != 3:
            raise ValueError(f"{self.name}: faces must be (M, 3)")
        if len(self.faces) and (self.faces.min() < 0 or self.faces.max() >= len(self.vertices)):
            raise ValueError(f"{self.name}: face indices fall outside the vertex table")
        for key, value in self.channels.items():
            array = np.ascontiguousarray(value, dtype=np.float32)
            if array.shape != (len(self.faces), 4):
                raise ValueError(f"{self.name}.{key}: colour channel must be (faces, 4)")
            self.channels[key] = array


def compact_faces(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reindex a face subset onto only the vertices it uses.

    Returns the new faces and the index map into the original vertex table, so
    the caller can slice any parallel vertex data the same way.
    """
    used = np.unique(np.asarray(faces, dtype=np.int64))
    lookup = np.full(len(vertices), -1, dtype=np.int64)
    lookup[used] = np.arange(len(used))
    return lookup[np.asarray(faces, dtype=np.int64)], used


def unweld_duplicates(layer: Layer) -> int:
    """Give every triangle its own vertices when two triangles share all three.

    Blender's mesh validation drops a face whose vertex indices repeat an
    earlier face, which would shift every per-face colour after it by one. The
    fishnet legitimately contains a handful of coincident triangles where two
    crops cut the same support triangle the same way, so the duplicates are
    separated rather than deleted. Vertex positions are untouched.
    """
    if not len(layer.faces):
        return 0
    key = np.sort(layer.faces, axis=1)
    _, first = np.unique(key, axis=0, return_index=True)
    repeated = np.ones(len(layer.faces), dtype=bool)
    repeated[first] = False
    if not repeated.any():
        return 0
    # Only the repeats get their own vertices. Unwelding the whole layer would
    # also work, and would then hand a silhouette renderer a mesh with no shared
    # edges at all, so it outlines every triangle instead of the form.
    extra = layer.vertices[layer.faces[repeated]].reshape(-1, 3)
    faces = np.array(layer.faces, copy=True)
    faces[repeated] = np.arange(len(extra), dtype=np.int64).reshape(-1, 3) + len(layer.vertices)
    layer.vertices = np.vstack([layer.vertices, extra])
    layer.faces = faces
    return int(repeated.sum())


def read_ply(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    """Read the binary PLY written by ``semantic_twin.export.write_ply``.

    A dedicated reader keeps the payload builder free of a mesh library in the
    one place where the file format is fully known and fixed.
    """
    payload = pathlib.Path(path).read_bytes()
    terminator = b"end_header\n"
    end = payload.find(terminator)
    if payload[:3] != b"ply" or end < 0:
        raise ValueError(f"Not a binary PLY: {path}")
    header = payload[:end].decode("ascii").splitlines()
    if "format binary_little_endian 1.0" not in header:
        raise ValueError(f"PLY is not binary little endian: {path}")
    vertex_count = 0
    face_count = 0
    for line in header:
        if line.startswith("element vertex "):
            vertex_count = int(line.split()[2])
        elif line.startswith("element face "):
            face_count = int(line.split()[2])
    offset = end + len(terminator)
    vertices = np.frombuffer(payload, dtype="<f4", count=vertex_count * 3, offset=offset)
    offset += vertex_count * 3 * 4
    face_block = np.frombuffer(payload, dtype=np.uint8, count=face_count * 13, offset=offset)
    face_block = face_block.reshape(face_count, 13)
    if face_count and not np.all(face_block[:, 0] == 3):
        raise ValueError(f"PLY contains a non-triangular face: {path}")
    faces = face_block[:, 1:].copy().view("<i4").reshape(face_count, 3)
    return vertices.reshape(vertex_count, 3).astype(np.float64), faces.astype(np.int64)


@dataclass(frozen=True)
class Pose:
    """The registered panorama camera, in scene ENU."""

    position: np.ndarray
    rotation: np.ndarray
    heading_deg: float
    residual_deg: float
    height_above_ground_m: float
    covariance_xyz: np.ndarray

    @classmethod
    def load(cls, path: pathlib.Path) -> Pose:
        from semantic_twin.pano_geometry import panorama_to_world_matrix

        document = json.loads(pathlib.Path(path).read_text())
        rotation = panorama_to_world_matrix(
            float(document["heading_deg"]),
            pitch_deg=float(document.get("pitch_correction_deg", 0.0)),
            roll_deg=float(document.get("roll_correction_deg", 0.0)),
        )
        uncertainty = document.get("pose_uncertainty", {})
        covariance = np.asarray(uncertainty.get("covariance", np.zeros((7, 7))), dtype=np.float64)
        evidence = document.get("camera_height_evidence", {})
        return cls(
            position=np.asarray(document["position_enu_m"], dtype=np.float64),
            rotation=rotation,
            heading_deg=float(document["heading_deg"]),
            residual_deg=float(document.get("skyline_score_mean_deg", float("nan"))),
            height_above_ground_m=float(evidence.get("adopted_height_above_ground_m", float("nan"))),
            covariance_xyz=covariance[:3, :3],
        )


def equirectangular_index(
    directions: np.ndarray, rotation: np.ndarray, shape: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """Panorama row and column for a batch of world ENU directions."""
    local = np.asarray(directions, dtype=np.float64) @ rotation
    local = local / np.maximum(np.linalg.norm(local, axis=1, keepdims=True), 1e-12)
    yaw = np.arctan2(local[:, 0], local[:, 1])
    pitch = np.arcsin(np.clip(local[:, 2], -1.0, 1.0))
    u = (yaw / (2.0 * np.pi) + 0.5) % 1.0
    v = np.clip(0.5 - pitch / np.pi, 0.0, 1.0 - np.finfo(np.float64).eps)
    height, width = shape
    return (v * height).astype(np.int64), (u * width).astype(np.int64)


def elevation_deg(directions: np.ndarray) -> np.ndarray:
    """Elevation above the ENU horizon, in degrees."""
    unit = np.asarray(directions, dtype=np.float64)
    unit = unit / np.maximum(np.linalg.norm(unit, axis=1, keepdims=True), 1e-12)
    return np.degrees(np.arcsin(np.clip(unit[:, 2], -1.0, 1.0)))


def sample_sphere(
    centroids: np.ndarray, pose: Pose, sphere: dict[str, np.ndarray], keys: tuple[str, ...]
) -> dict[str, np.ndarray]:
    """Read named panorama channels along the ray from the camera to each centroid."""
    directions = np.asarray(centroids, dtype=np.float64) - pose.position
    reference = sphere[keys[0]]
    rows, columns = equirectangular_index(directions, pose.rotation, reference.shape[:2])
    return {key: np.asarray(sphere[key])[rows, columns] for key in keys}


@dataclass(frozen=True)
class CropSpec:
    """One rectilinear panorama crop, as the fishnet cutter saw it."""

    name: str
    yaw_deg: float
    pitch_deg: float
    fov_deg: float
    size: int


def crop_specs(manifest_path: pathlib.Path, views: list[str], yaws: list[float]) -> list[CropSpec]:
    """Read the crop geometry the cutter recorded, so the sampling matches it."""
    document = json.loads(pathlib.Path(manifest_path).read_text())
    by_name = {entry["view"]: entry for entry in document["views"]}
    specs = []
    for name, yaw in zip(views, yaws, strict=True):
        record = by_name.get(name)
        if record is None:
            raise KeyError(f"Fishnet manifest has no crop {name}")
        height, width = record["shape"]
        if height != width:
            raise ValueError(f"Crop {name} is not square, the sampler assumes a square pinhole")
        specs.append(CropSpec(name=name, yaw_deg=float(yaw), pitch_deg=0.0, fov_deg=90.0, size=int(width)))
    return specs


def face_channel_majority(
    directory: pathlib.Path,
    views: list[str],
    view_specs: list[CropSpec],
    sphere: dict[str, np.ndarray],
    keys: tuple[str, ...],
    level_counts: dict[str, int],
) -> dict[str, np.ndarray]:
    """Per-face majority of panorama channels over the pixels each face owns.

    Sampling the sphere along the ray to a face centroid is wrong here. That ray
    reports whatever the panorama saw in that direction, including the person
    standing in front of the wall, which is exactly the association the cutter
    refused to make. The fishnet ships the source pixels of every face, so the
    honest read is the majority over those pixels and nothing else.
    """
    totals: dict[str, list[np.ndarray]] = {key: [] for key in keys}
    for view, spec in zip(views, view_specs, strict=True):
        with np.load(directory / f"{view}_fishnet.npz") as data:
            offsets = np.asarray(data["pixel_offsets"], dtype=np.int64)
            indices = np.asarray(data["pixel_indices"], dtype=np.int64)
            face_group = np.asarray(data["face_group"], dtype=np.int64)
        size = int(spec.size)
        rows, columns = np.divmod(indices, size)
        directions = _crop_directions(spec, rows, columns, size)
        pano_rows, pano_columns = _local_equirectangular(directions, sphere[keys[0]].shape[:2])
        group_count = len(offsets) - 1
        owner = np.repeat(np.arange(group_count), np.diff(offsets))
        for key in keys:
            values = np.asarray(sphere[key])[pano_rows, pano_columns].astype(np.int64)
            counts = np.zeros((group_count, level_counts[key]), dtype=np.int64)
            np.add.at(counts, (owner, np.clip(values, 0, level_counts[key] - 1)), 1)
            winner = counts.argmax(axis=1)
            winner[counts.sum(axis=1) == 0] = 0
            totals[key].append(winner[face_group])
    return {key: np.concatenate(value) for key, value in totals.items()}


def _crop_directions(spec: Any, rows: np.ndarray, columns: np.ndarray, size: int) -> np.ndarray:
    """Vectorised form of ``pano_geometry.perspective_direction_at`` for a crop."""
    from semantic_twin.pano_geometry import view_basis

    right, forward, up = view_basis(spec.yaw_deg, spec.pitch_deg)
    tangent = np.tan(np.radians(spec.fov_deg) / 2.0)
    x = ((columns + 0.5) / size * 2.0 - 1.0) * tangent
    y = (1.0 - (rows + 0.5) / size * 2.0) * tangent
    directions = forward + x[:, None] * right + y[:, None] * up
    return directions / np.linalg.norm(directions, axis=1, keepdims=True)


def _local_equirectangular(directions: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Panorama row and column for directions already in the panorama frame."""
    unit = directions / np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-12)
    yaw = np.arctan2(unit[:, 0], unit[:, 1])
    pitch = np.arcsin(np.clip(unit[:, 2], -1.0, 1.0))
    u = (yaw / (2.0 * np.pi) + 0.5) % 1.0
    v = np.clip(0.5 - pitch / np.pi, 0.0, 1.0 - np.finfo(np.float64).eps)
    height, width = shape
    return (v * height).astype(np.int64), (u * width).astype(np.int64)


def load_fishnet(directory: pathlib.Path, views: list[str]) -> dict[str, Any]:
    """Concatenate the per-crop fishnet surface sets into one triangle soup.

    The four pitch-zero crops tile a cube band exactly, so concatenating them
    partitions the band and no face is double counted. Overlapping crops would
    need an assignment rule that the cutter does not provide, so only the shipped
    four are accepted.
    """
    directory = pathlib.Path(directory)
    vertices: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    columns: dict[str, list[np.ndarray]] = {}
    view_index: list[np.ndarray] = []
    offset = 0
    scalar_keys = (
        "face_class",
        "face_confidence",
        "face_area_m2",
        "face_solid_angle_sr",
        "face_visible_fraction",
        "face_source_triangle",
        "face_pixel_support",
    )
    for index, view in enumerate(views):
        path = directory / f"{view}_fishnet.npz"
        if not path.is_file():
            raise FileNotFoundError(f"Fishnet crop is missing: {path}")
        with np.load(path) as data:
            vertices.append(np.asarray(data["vertices"], dtype=np.float64))
            faces.append(np.asarray(data["faces"], dtype=np.int64) + offset)
            offset += len(data["vertices"])
            for key in scalar_keys:
                columns.setdefault(key, []).append(np.asarray(data[key]))
            view_index.append(np.full(len(data["faces"]), index, dtype=np.int64))
    return {
        "vertices": np.vstack(vertices),
        "faces": np.vstack(faces),
        "view": np.concatenate(view_index),
        **{key: np.concatenate(value) for key, value in columns.items()},
    }


def reprojection_residual_px(
    directory: pathlib.Path, views: list[str], view_specs: list[CropSpec], pose: Pose
) -> dict[str, Any]:
    """How far the pose on disk moves the fishnet's own recorded image coordinates.

    The cutter stored, for every face, both its world vertices and where those
    vertices landed in the crop. Projecting the vertices through the pose file
    has to reproduce the stored coordinates to rounding. When it does not, the
    surface set was cut against a different solve of the same pose, and any
    figure that lays a render over the source photograph is claiming a
    registration it does not have. Measuring it is the only way to know.
    """
    per_view: dict[str, float] = {}
    pooled: list[np.ndarray] = []
    for view, spec in zip(views, view_specs, strict=True):
        with np.load(directory / f"{view}_fishnet.npz") as data:
            corners = np.asarray(data["vertices"], dtype=np.float64)[np.asarray(data["faces"], dtype=np.int64)]
            recorded = np.asarray(data["face_image"], dtype=np.float64).reshape(-1, 2)
        points = corners.reshape(-1, 3)
        local = _view_components(points - pose.position, pose.rotation, spec)
        front = local[:, 2] > 1e-6
        tangent = np.tan(np.radians(spec.fov_deg) / 2.0)
        x = (local[front, 0] / (local[front, 2] * tangent) + 1.0) * 0.5 * spec.size
        y = (1.0 - local[front, 1] / (local[front, 2] * tangent)) * 0.5 * spec.size
        error = np.hypot(x - recorded[front, 0], y - recorded[front, 1])
        per_view[view] = float(np.median(error)) if len(error) else float("nan")
        pooled.append(error)
    every = np.concatenate(pooled) if pooled else np.zeros(0)
    return {
        "median_px": float(np.median(every)) if len(every) else float("nan"),
        "p95_px": float(np.percentile(every, 95)) if len(every) else float("nan"),
        "per_view_median_px": per_view,
        "samples": int(len(every)),
        "note": (
            "Projection of the surface set's own vertices through the pose file, against the image "
            "coordinates the cutter recorded. Rounding-level agreement means the two artifacts came "
            "from the same pose solve."
        ),
    }


def _view_components(offsets: np.ndarray, rotation: np.ndarray, spec: CropSpec) -> np.ndarray:
    """Camera-space right, up and forward components, in the cutter's convention."""
    from semantic_twin.pano_geometry import view_basis

    right, forward, up = view_basis(spec.yaw_deg, spec.pitch_deg)
    return (offsets @ rotation) @ np.stack([right, up, forward]).T


def load_rejected(directory: pathlib.Path, views: list[str]) -> dict[str, np.ndarray]:
    """The candidate surface elements the cutter refused, with their reason."""
    directory = pathlib.Path(directory)
    triangles: list[np.ndarray] = []
    reasons: list[np.ndarray] = []
    areas: list[np.ndarray] = []
    for view in views:
        with np.load(directory / f"{view}_fishnet.npz") as data:
            triangles.append(np.asarray(data["rejected_source_triangle"], dtype=np.int64))
            reasons.append(np.asarray(data["rejected_reason"], dtype=np.int64))
            areas.append(np.asarray(data["rejected_image_area_px"], dtype=np.float64))
    return {
        "source_triangle": np.concatenate(triangles),
        "reason": np.concatenate(reasons),
        "image_area_px": np.concatenate(areas),
    }


def classify_visibility(
    vertices: np.ndarray,
    faces: np.ndarray,
    pose: Pose,
    texture_face_index: np.ndarray | None,
    intersector: Any,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Label every support face panorama, texture or unseen.

    ``panorama`` means the face is the camera's own first hit inside the
    elevation band the four crops cover. ``texture`` means no panorama sees it
    but the tile texture carries a material claim for it. ``unseen`` means the
    scene asserts a surface there on the strength of the photogrammetry alone.
    """
    centroids = vertices[faces].mean(axis=1)
    offsets = centroids - pose.position
    ranges = np.linalg.norm(offsets, axis=1)
    directions = offsets / np.maximum(ranges[:, None], 1e-12)
    in_band = np.abs(elevation_deg(directions)) <= CROP_HALF_ELEVATION_DEG

    candidate = np.flatnonzero(in_band & (ranges > 1e-3))
    origins = np.repeat(pose.position[None, :], len(candidate), axis=0)
    hit_triangle, hit_ray, locations = intersector.intersects_id(
        origins, directions[candidate], return_locations=True, multiple_hits=False
    )
    first_hit = np.full(len(candidate), -1, dtype=np.int64)
    hit_range = np.full(len(candidate), np.inf)
    first_hit[hit_ray] = hit_triangle
    hit_range[hit_ray] = np.linalg.norm(locations - pose.position, axis=1)

    own_hit = (first_hit == candidate) | (np.abs(hit_range - ranges[candidate]) <= FIRST_HIT_TOLERANCE_M)
    state = np.full(len(faces), VISIBILITY_STATES.index("unseen"), dtype=np.int64)
    if texture_face_index is not None:
        state[np.asarray(texture_face_index, dtype=np.int64)] = VISIBILITY_STATES.index("texture")
    state[candidate[own_hit]] = VISIBILITY_STATES.index("panorama")

    area = triangle_area(vertices, faces)
    report = {
        "faces": int(len(faces)),
        "in_crop_band_faces": int(in_band.sum()),
        "first_hit_tolerance_m": FIRST_HIT_TOLERANCE_M,
        "crop_half_elevation_deg": CROP_HALF_ELEVATION_DEG,
    }
    for index, name in enumerate(VISIBILITY_STATES):
        selection = state == index
        report[f"{name}_faces"] = int(selection.sum())
        report[f"{name}_face_fraction"] = float(selection.mean())
        report[f"{name}_area_fraction"] = float(area[selection].sum() / area.sum())
    return state, report


def triangle_area(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Metric area of every triangle."""
    corners = vertices[faces]
    cross = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return 0.5 * np.linalg.norm(cross, axis=1)


def lift_towards(vertices: np.ndarray, faces: np.ndarray, point: np.ndarray, distance: float) -> np.ndarray:
    """Move every vertex ``distance`` metres towards ``point``.

    The fishnet was cut against one support mesh and the render draws a
    different, later build of the same tiles, so the two disagree by tens of
    centimetres. Displacing the semantic layer along the line of sight of the
    camera that produced it is the one direction that cannot invent an
    occlusion, and it keeps the layer in front for any view.
    """
    if distance == 0.0:
        return np.array(vertices, dtype=np.float64, copy=True)
    used = np.zeros(len(vertices), dtype=bool)
    used[faces.ravel()] = True
    offsets = np.asarray(point, dtype=np.float64) - vertices
    norms = np.maximum(np.linalg.norm(offsets, axis=1, keepdims=True), 1e-12)
    moved = np.array(vertices, dtype=np.float64, copy=True)
    moved[used] += (offsets / norms * distance)[used]
    return moved


def ellipsoid(centre: np.ndarray, covariance: np.ndarray, sigma: float, subdivisions: int = 2) -> Layer:
    """A closed sigma-scaled covariance ellipsoid, built from an icosahedron.

    Deterministic by construction: the seed solid is fixed and the subdivision
    is a fixed number of midpoint splits, so the same covariance always yields
    the same vertex table in the same order.
    """
    phi = (1.0 + 5.0**0.5) / 2.0
    seed = np.array(
        [
            [-1, phi, 0],
            [1, phi, 0],
            [-1, -phi, 0],
            [1, -phi, 0],
            [0, -1, phi],
            [0, 1, phi],
            [0, -1, -phi],
            [0, 1, -phi],
            [phi, 0, -1],
            [phi, 0, 1],
            [-phi, 0, -1],
            [-phi, 0, 1],
        ],
        dtype=np.float64,
    )
    triangles = np.array(
        [
            [0, 11, 5],
            [0, 5, 1],
            [0, 1, 7],
            [0, 7, 10],
            [0, 10, 11],
            [1, 5, 9],
            [5, 11, 4],
            [11, 10, 2],
            [10, 7, 6],
            [7, 1, 8],
            [3, 9, 4],
            [3, 4, 2],
            [3, 2, 6],
            [3, 6, 8],
            [3, 8, 9],
            [4, 9, 5],
            [2, 4, 11],
            [6, 2, 10],
            [8, 6, 7],
            [9, 8, 1],
        ],
        dtype=np.int64,
    )
    points = list(seed / np.linalg.norm(seed, axis=1, keepdims=True))
    for _ in range(subdivisions):
        cache: dict[tuple[int, int], int] = {}
        split = []
        for a, b, c in triangles:
            corner = []
            for first, second in ((a, b), (b, c), (c, a)):
                key = (min(first, second), max(first, second))
                if key not in cache:
                    middle = points[first] + points[second]
                    points.append(middle / np.linalg.norm(middle))
                    cache[key] = len(points) - 1
                corner.append(cache[key])
            ab, bc, ca = corner
            split.extend([[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]])
        triangles = np.array(split, dtype=np.int64)
    unit = np.asarray(points)

    values, vectors = np.linalg.eigh(np.asarray(covariance, dtype=np.float64))
    axes = np.sqrt(np.maximum(values, 0.0)) * sigma
    shell = unit * axes @ vectors.T + np.asarray(centre, dtype=np.float64)
    return Layer(name="pose_covariance", vertices=shell, faces=triangles)


def box(centre: np.ndarray, size: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """An axis-aligned closed box, used for the camera marker."""
    signs = np.array(
        [
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            [0, 2, 1],
            [0, 3, 2],
            [4, 5, 6],
            [4, 6, 7],
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ],
        dtype=np.int64,
    )
    return signs * (np.asarray(size, dtype=np.float64) / 2.0) + np.asarray(centre, dtype=np.float64), faces


def uniform(colour: tuple[float, float, float, float], count: int) -> np.ndarray:
    """One colour repeated for every face of a layer."""
    return np.tile(np.asarray(colour, dtype=np.float32), (count, 1))


def legend_entry(label: str, colour: tuple[float, float, float, float], value: str = "") -> dict[str, Any]:
    return {"label": label, "colour": [float(c) for c in colour], "value": value}


def write_payload(path: pathlib.Path, layers: list[Layer], metadata: dict[str, Any]) -> None:
    """Write the layers and their legends to one npz plus one JSON sidecar.

    Colour channels cross into linear light here, once, at the boundary between
    the part of the pipeline that thinks in legend colours and the part that
    hands them to a renderer. The legends stay in display sRGB because that is
    what the annotation pass draws the swatches with.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    index: list[dict[str, Any]] = []
    for layer in layers:
        arrays[f"{layer.name}/vertices"] = layer.vertices.astype(np.float32)
        arrays[f"{layer.name}/faces"] = layer.faces.astype(np.int32)
        for key, value in layer.channels.items():
            arrays[f"{layer.name}/channel/{key}"] = srgb_to_linear(value)
        for key, value in layer.scalars.items():
            arrays[f"{layer.name}/scalar/{key}"] = np.asarray(value, dtype=np.float32)
        index.append(
            {
                "name": layer.name,
                "faces": int(len(layer.faces)),
                "vertices": int(len(layer.vertices)),
                "channels": sorted(layer.channels),
                "scalars": sorted(layer.scalars),
                "legends": layer.legends,
            }
        )
    np.savez_compressed(path, **arrays)
    sidecar = dict(metadata)
    sidecar["layers"] = index
    path.with_suffix(".json").write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_payload(path: pathlib.Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Read back what :func:`write_payload` wrote, as plain arrays."""
    path = pathlib.Path(path)
    sidecar = json.loads(path.with_suffix(".json").read_text())
    data = np.load(path)
    layers: dict[str, dict[str, Any]] = {}
    for record in sidecar["layers"]:
        name = record["name"]
        layers[name] = {
            "vertices": data[f"{name}/vertices"],
            "faces": data[f"{name}/faces"],
            "channels": {key: data[f"{name}/channel/{key}"] for key in record["channels"]},
            "scalars": {key: data[f"{name}/scalar/{key}"] for key in record["scalars"]},
            "legends": record["legends"],
        }
    return layers, sidecar


def rejection_reason_names() -> dict[int, str]:
    """Rejection code to name, inverted from the cutter's own table.

    Imported lazily. ``showcase_blender.py`` reads the payload from inside
    Blender, whose bundled interpreter has neither shapely nor mapbox_earcut,
    and the cutter needs both.
    """
    from semantic_twin.fishnet import REJECTION_REASONS

    return {code: name for name, code in REJECTION_REASONS.items()}

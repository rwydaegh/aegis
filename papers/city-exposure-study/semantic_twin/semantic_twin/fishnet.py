"""Cut a support mesh at semantic class boundaries instead of tiling image space.

The previous projection path (``pixel_projection.py``) built an axis-aligned
quadtree over the label image and ray-splatted two triangles per leaf outward
onto the support surface.  Every class boundary became a staircase of squares
and flat facade paid for triangles it did not need.

This module inverts the direction of travel.  Each support-mesh triangle is
projected *into* the rectilinear crop, the class boundaries are intersected as a
plain 2D arrangement there, and the resulting pieces are mapped back to 3D by
intersecting their pixel rays with the triangle's own supporting plane.  Within
one crop the camera is an ordinary pinhole, so the map from a triangle to its
image is projective and exactly invertible.  Two guards make that inverse safe:
triangles are clipped against the near plane before projection, and the mesh
first-hit id buffer decides which part of a triangle is actually visible.

A triangle whose footprint lies inside a single semantic island is emitted
untouched.  The support triangulation is metre-scale photogrammetry and there is
nothing to gain from subdividing it where the semantics do not change.

The result is the visible surface set at one panorama centre, not merely a
mesh.  Every face carries an outward normal, a metric area, the solid angle it
subtends from the capture point, its semantic class, material posterior,
confidence, and the source pixels it was built from, so a propagation stage can
use it as the first-hit acceleration structure directly.  Faces that were
considered and rejected are kept in a parallel table with the reason, because a
surface wrongly dropped deletes a propagation path just as surely as a surface
wrongly kept invents a phantom scatterer.

Nothing here imports ``bpy``.  The Blender and rendering wrappers live in the
standalone scripts next to this package.
"""

from __future__ import annotations

import math
import pathlib
from dataclasses import dataclass, field

import mapbox_earcut
import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union
from skimage.measure import approximate_polygon

UNPAINTABLE = -1

# Why a pixel may not be projected onto the support surface.  The two the owner
# cares about are kept apart on purpose: clutter in front of the wall is
# geometry the tiles never captured, whereas a transient object is geometry that
# belongs to a separate dynamic layer and must never be painted onto the wall
# behind it.
PAINT_REASONS: dict[str, int] = {
    "paintable": 0,
    "no_mesh_hit": 1,
    "low_confidence": 2,
    "transient_object": 3,
    "clutter_in_front": 4,
    "mesh_or_pose_conflict": 5,
    "not_support_surface": 6,
}

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
}

_PAINT_TO_REJECTION = {
    PAINT_REASONS["transient_object"]: REJECTION_REASONS["transient_object"],
    PAINT_REASONS["clutter_in_front"]: REJECTION_REASONS["clutter_in_front"],
    PAINT_REASONS["mesh_or_pose_conflict"]: REJECTION_REASONS["clutter_in_front"],
    PAINT_REASONS["not_support_surface"]: REJECTION_REASONS["not_support_surface"],
}


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


@dataclass(frozen=True)
class RegionMap:
    """Semantic islands: connected, depth-continuous, single-class pixel sets.

    ``region`` is ``UNPAINTABLE`` where evidence must not be projected at all,
    and ``paint_reason`` records why.  Folding depth continuity into the island
    definition is what makes occlusion silhouettes part of the fishnet: a wall
    seen past a nearer building is a different island from that building even
    when both carry the same class.
    """

    region: np.ndarray
    region_class: np.ndarray
    region_size: np.ndarray
    source_class: np.ndarray
    paint_reason: np.ndarray
    report: dict[str, int] = field(default_factory=dict)

    @property
    def region_count(self) -> int:
        return int(self.region_class.size)


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


def view_basis(view: PinholeView) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Panorama-local right, forward and up axes of a rectilinear crop."""
    yaw = math.radians(view.yaw_deg)
    pitch = math.radians(view.pitch_deg)
    forward = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    return right, forward, np.cross(right, forward)


def world_to_view(points: np.ndarray, pose: CameraPose, view: PinholeView) -> np.ndarray:
    """World metres to camera axes ``(right, up, forward)`` of one crop."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    right, forward, up = view_basis(view)
    local = (points - pose.position) @ pose.rotation
    return local @ np.stack([right, up, forward]).T


def view_to_world(points: np.ndarray, pose: CameraPose, view: PinholeView) -> np.ndarray:
    """Inverse of :func:`world_to_view`."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    right, forward, up = view_basis(view)
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
    """Camera-space rays, with unit forward component, through image points."""
    pixels = np.asarray(pixels, dtype=np.float64)
    if pixels.ndim != 2 or pixels.shape[1] != 2:
        raise ValueError("pixels must have shape (n, 2)")
    tangent_x, tangent_y = view.tangents
    x = (2.0 * pixels[:, 0] / view.width - 1.0) * tangent_x
    y = (1.0 - 2.0 * pixels[:, 1] / view.height) * tangent_y
    return np.stack([x, y, np.ones_like(x)], axis=1)


def triangle_solid_angle(triangles: np.ndarray) -> np.ndarray:
    """Exact solid angle of camera-centred triangles, by Van Oosterom-Strackee."""
    triangles = np.asarray(triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
        raise ValueError("triangles must have shape (n, 3, 3)")
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    norm_a = np.linalg.norm(a, axis=1)
    norm_b = np.linalg.norm(b, axis=1)
    norm_c = np.linalg.norm(c, axis=1)
    numerator = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    denominator = (
        norm_a * norm_b * norm_c
        + np.einsum("ij,ij->i", a, b) * norm_c
        + np.einsum("ij,ij->i", a, c) * norm_b
        + np.einsum("ij,ij->i", b, c) * norm_a
    )
    return 2.0 * np.arctan2(numerator, denominator)


def paintability(
    labels: np.ndarray,
    confidence: np.ndarray,
    range_m: np.ndarray,
    *,
    transient_class_ids: set[int] | None = None,
    excluded_class_ids: set[int] | None = None,
    min_confidence: float = 0.35,
    decision: np.ndarray | None = None,
    blocker_decisions: tuple[int, ...] = (3, 4),
    transient_decisions: tuple[int, ...] = (5,),
) -> np.ndarray:
    """Per-pixel projection decision, one of :data:`PAINT_REASONS`.

    ``decision`` is the map written by ``compare_mesh_depth.py``: it is where
    metric distance, not appearance, decides that something stands in front of
    the tile surface.  Transient classes are separated from that so a person is
    never painted onto the wall behind them even when the depths agree.
    ``excluded_class_ids`` covers classes that are not support surfaces at all,
    such as sky and the street furniture that the object pipeline reconstructs
    as its own proxy geometry.
    """
    labels = np.asarray(labels)
    confidence = np.asarray(confidence, dtype=np.float64)
    range_m = np.asarray(range_m, dtype=np.float64)
    if labels.ndim != 2 or confidence.shape != labels.shape or range_m.shape != labels.shape:
        raise ValueError("labels, confidence and range_m must be equally shaped 2D arrays")
    reason = np.full(labels.shape, PAINT_REASONS["paintable"], dtype=np.int8)
    reason[~np.isfinite(range_m) | (range_m <= 0.0)] = PAINT_REASONS["no_mesh_hit"]
    still_open = reason == PAINT_REASONS["paintable"]
    reason[still_open & (confidence < min_confidence)] = PAINT_REASONS["low_confidence"]
    if decision is not None:
        decision = np.asarray(decision)
        if decision.shape != labels.shape:
            raise ValueError("decision must match the label resolution")
        reason[np.isin(decision, list(blocker_decisions))] = PAINT_REASONS["clutter_in_front"]
        reason[np.isin(decision, list(transient_decisions))] = PAINT_REASONS["transient_object"]
    if excluded_class_ids:
        reason[np.isin(labels, list(excluded_class_ids))] = PAINT_REASONS["not_support_surface"]
    if transient_class_ids:
        reason[np.isin(labels, list(transient_class_ids))] = PAINT_REASONS["transient_object"]
    reason[~np.isfinite(range_m) | (range_m <= 0.0)] = PAINT_REASONS["no_mesh_hit"]
    return reason


def build_region_map(
    labels: np.ndarray,
    paint_reason: np.ndarray,
    range_m: np.ndarray,
    *,
    depth_break_ratio: float = 0.15,
    min_region_pixels: int = 64,
) -> RegionMap:
    """Group paintable pixels into single-class, depth-continuous islands.

    ``depth_break_ratio`` is a relative first-hit range step between adjacent
    pixels.  A relative test keeps grazing surfaces whole while still splitting
    at genuine silhouettes.  Islands below ``min_region_pixels`` are merged into
    the depth-continuous neighbour with which they share the longest boundary,
    which is the knob that trades class fidelity for triangle count.
    """
    labels = np.asarray(labels)
    paint_reason = np.asarray(paint_reason)
    range_m = np.asarray(range_m, dtype=np.float64)
    if labels.ndim != 2 or paint_reason.shape != labels.shape or range_m.shape != labels.shape:
        raise ValueError("labels, paint_reason and range_m must be equally shaped 2D arrays")
    if not np.isfinite(depth_break_ratio) or depth_break_ratio <= 0.0:
        raise ValueError("depth_break_ratio must be finite and positive")
    if min_region_pixels < 0:
        raise ValueError("min_region_pixels must be non-negative")

    height, width = labels.shape
    valid = (paint_reason == PAINT_REASONS["paintable"]) & np.isfinite(range_m) & (range_m > 0.0)
    flat = np.arange(height * width, dtype=np.int64).reshape(height, width)

    same_pairs = []
    cross_pairs = []
    for a_slice, b_slice in (
        ((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
        ((slice(0, -1), slice(None)), (slice(1, None), slice(None))),
    ):
        both = valid[a_slice] & valid[b_slice]
        near = np.minimum(range_m[a_slice], range_m[b_slice])
        continuous = both & (np.abs(range_m[a_slice] - range_m[b_slice]) <= depth_break_ratio * np.maximum(near, 1e-6))
        equal = labels[a_slice] == labels[b_slice]
        same_pairs.append((flat[a_slice][continuous & equal], flat[b_slice][continuous & equal]))
        cross_pairs.append((flat[a_slice][continuous & ~equal], flat[b_slice][continuous & ~equal]))

    rows = np.concatenate([pair[0] for pair in same_pairs])
    columns = np.concatenate([pair[1] for pair in same_pairs])
    graph = coo_matrix(
        (np.ones(rows.size, dtype=np.int8), (rows, columns)),
        shape=(height * width, height * width),
    )
    _count, component = connected_components(graph, directed=False)
    component = component.reshape(height, width)

    region, region_class = _compact_regions(component, labels, valid)
    merged = 0
    if min_region_pixels > 0 and region_class.size:
        region, region_class, merged = _merge_small_regions(
            region,
            region_class,
            labels,
            np.concatenate([pair[0] for pair in cross_pairs]),
            np.concatenate([pair[1] for pair in cross_pairs]),
            min_region_pixels,
        )
    sizes = np.bincount(region[region >= 0].ravel(), minlength=region_class.size).astype(np.int64)
    report = {
        "paintable_pixels": int(valid.sum()),
        "regions": int(region_class.size),
        "merged_small_regions": int(merged),
        "regions_below_minimum": int(np.count_nonzero(sizes < min_region_pixels)),
    }
    return RegionMap(
        region,
        region_class,
        sizes,
        np.where(valid, labels, UNPAINTABLE).astype(np.int64),
        paint_reason.astype(np.int8),
        report,
    )


def boundary_chains(region: np.ndarray, *, tolerance_px: float = 1.5) -> list[np.ndarray]:
    """Simplified polylines of the crack network between islands.

    Boundaries are traced on the pixel-corner grid, so a chain separating two
    islands is one shared geometric object.  Simplifying that shared chain, and
    holding the junctions where three or more islands meet fixed, keeps the
    fishnet a partition: neither gaps nor overlaps can open between neighbours.
    Simplification uses Douglas-Peucker, whose error bound is symmetric and
    therefore the right choice for a boundary two regions must agree on.
    """
    region = np.asarray(region)
    if region.ndim != 2:
        raise ValueError("region must be a 2D array")
    if not np.isfinite(tolerance_px) or tolerance_px < 0.0:
        raise ValueError("tolerance_px must be finite and non-negative")

    height, width = region.shape
    stride = width + 1
    edges = []
    if width > 1:
        rows, columns = np.nonzero(region[:, :-1] != region[:, 1:])
        node = rows * stride + (columns + 1)
        edges.append(np.stack([node, node + stride], axis=1))
    if height > 1:
        rows, columns = np.nonzero(region[:-1, :] != region[1:, :])
        node = (rows + 1) * stride + columns
        edges.append(np.stack([node, node + 1], axis=1))
    if not edges:
        return []
    edge_nodes = np.concatenate(edges, axis=0)
    if edge_nodes.size == 0:
        return []

    node_count = (height + 1) * stride
    degree = np.bincount(edge_nodes.ravel(), minlength=node_count)
    order = np.argsort(edge_nodes.ravel(), kind="stable")
    incident_edge = (order // 2).astype(np.int64)
    start = np.zeros(node_count + 1, dtype=np.int64)
    np.cumsum(degree, out=start[1:])

    used = np.zeros(len(edge_nodes), dtype=bool)
    chains: list[list[int]] = []
    for junction in np.nonzero((degree != 2) & (degree > 0))[0]:
        for edge in incident_edge[start[junction] : start[junction + 1]]:
            if not used[edge]:
                chains.append(_walk_chain(int(junction), int(edge), edge_nodes, degree, incident_edge, start, used))
    for edge in range(len(edge_nodes)):
        if not used[edge]:
            chains.append(_walk_chain(int(edge_nodes[edge, 0]), edge, edge_nodes, degree, incident_edge, start, used))

    simplified = []
    for chain in chains:
        nodes = np.asarray(chain, dtype=np.int64)
        points = np.stack([nodes % stride, nodes // stride], axis=1).astype(np.float64)
        simplified.append(_simplify_chain(points, tolerance_px))
    return [chain for chain in simplified if len(chain) >= 2]


def build_fishnet(
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    face_ids: np.ndarray,
    regions: RegionMap,
    pose: CameraPose,
    view: PinholeView,
    *,
    confidence: np.ndarray | None = None,
    material_probability: np.ndarray | None = None,
    boundary_tolerance_px: float = 1.5,
    near_plane_m: float = 0.05,
    full_visibility_fraction: float = 0.98,
    piece_visibility_fraction: float = 0.5,
    piece_support_fraction: float = 0.5,
    min_piece_area_px: float = 1.0,
    surface_offset_m: float = 0.0,
    record_provenance: bool = True,
) -> FishnetSurface:
    """Cut the visible support triangles at the semantic fishnet.

    Only triangles that own at least one pixel of the mesh first-hit buffer are
    considered, so hidden geometry never reaches the output.  A triangle whose
    image footprint lies inside a single island and which is not occluded is
    emitted as-is.  Every other triangle is intersected with the local boundary
    chains and its pieces are re-triangulated and depth-tested individually.
    """
    mesh_vertices = np.asarray(mesh_vertices, dtype=np.float64)
    mesh_faces = np.asarray(mesh_faces, dtype=np.int64)
    face_ids = np.asarray(face_ids, dtype=np.int64)
    if mesh_vertices.ndim != 2 or mesh_vertices.shape[1] != 3:
        raise ValueError("mesh_vertices must have shape (n, 3)")
    if mesh_faces.ndim != 2 or mesh_faces.shape[1] != 3:
        raise ValueError("mesh_faces must have shape (m, 3)")
    if face_ids.shape != view.shape or regions.region.shape != view.shape:
        raise ValueError("face_ids and the region map must match the view resolution")
    if np.any(face_ids >= len(mesh_faces)):
        raise ValueError("face_ids reference triangles outside the support mesh")
    if not 0.0 < full_visibility_fraction <= 1.0 or not 0.0 <= piece_visibility_fraction <= 1.0:
        raise ValueError("visibility fractions must lie in (0, 1] and [0, 1]")
    if not 0.0 < piece_support_fraction <= 1.0:
        raise ValueError("piece_support_fraction must lie in (0, 1]")
    if confidence is None:
        confidence = np.ones(view.shape, dtype=np.float64)
    confidence = np.asarray(confidence, dtype=np.float64)
    if confidence.shape != view.shape:
        raise ValueError("confidence must match the view resolution")
    if material_probability is not None:
        material_probability = np.asarray(material_probability, dtype=np.float64)
        if material_probability.ndim != 3 or material_probability.shape[:2] != view.shape:
            raise ValueError("material_probability must have shape (height, width, materials)")

    chains = boundary_chains(regions.region, tolerance_px=boundary_tolerance_px)
    chain_lines = [LineString(chain) for chain in chains]
    tree = shapely.STRtree(chain_lines) if chain_lines else None

    class_count = int(regions.region_class.max()) + 1 if regions.region_class.size else 1
    builder = _SurfaceBuilder(class_count, material_probability, surface_offset_m, record_provenance)
    report: dict[str, float] = {
        "visible_source_triangles": 0.0,
        "boundary_chains": float(len(chain_lines)),
        "emitted_whole": 0.0,
        "cut_source_triangles": 0.0,
        "arrangement_fallbacks": 0.0,
        "clipped_source_area_px": 0.0,
        "emitted_area_px": 0.0,
        "rejected_area_px": 0.0,
    }

    visible = np.unique(face_ids[face_ids >= 0])
    report["visible_source_triangles"] = float(visible.size)
    for triangle in visible:
        _process_triangle(
            int(triangle),
            mesh_vertices,
            mesh_faces,
            face_ids,
            regions,
            confidence,
            pose,
            view,
            tree,
            chain_lines,
            builder,
            report,
            near_plane_m=near_plane_m,
            full_visibility_fraction=full_visibility_fraction,
            piece_visibility_fraction=piece_visibility_fraction,
            piece_support_fraction=piece_support_fraction,
            min_piece_area_px=min_piece_area_px,
        )
    return builder.finish(report, pose)


def rasterize_fishnet(surface: FishnetSurface, shape: tuple[int, int]) -> FishnetRaster:
    """Paint the output faces back into the image with a nearest-surface test.

    This is the round trip used to measure what simplification actually cost, so
    it deliberately reuses the stored image-space triangles rather than
    re-projecting and hiding a projection bug.
    """
    height, width = int(shape[0]), int(shape[1])
    if height < 1 or width < 1:
        raise ValueError("shape must be positive")
    painted = np.full((height, width), UNPAINTABLE, dtype=np.int64)
    source = np.full((height, width), UNPAINTABLE, dtype=np.int64)
    depth = np.full((height, width), np.inf, dtype=np.float64)
    for index in range(surface.triangle_count):
        rows, columns = _rasterize_convex(surface.face_image[index], width, height)
        if rows.size == 0:
            continue
        nearer = surface.face_depth[index] < depth[rows, columns]
        rows, columns = rows[nearer], columns[nearer]
        painted[rows, columns] = surface.face_class[index]
        source[rows, columns] = surface.face_source_triangle[index]
        depth[rows, columns] = surface.face_depth[index]
    return FishnetRaster(painted, source, np.where(np.isfinite(depth), depth, np.nan))


def class_fidelity(raster: FishnetRaster, regions: RegionMap) -> dict[str, float]:
    """Fraction of source pixels whose class survives the fishnet round trip."""
    painted = raster.class_map
    if painted.shape != regions.source_class.shape:
        raise ValueError("raster must match the region map resolution")
    paintable = regions.source_class != UNPAINTABLE
    covered = paintable & (painted != UNPAINTABLE)
    changed = int(np.count_nonzero(covered & (painted != regions.source_class)))
    paintable_count = int(np.count_nonzero(paintable))
    covered_count = int(np.count_nonzero(covered))
    return {
        "paintable_pixels": paintable_count,
        "covered_pixels": covered_count,
        "coverage": covered_count / paintable_count if paintable_count else 0.0,
        "changed_pixels": changed,
        "changed_fraction": changed / covered_count if covered_count else 0.0,
        "leaked_pixels": int(np.count_nonzero(~paintable & (painted != UNPAINTABLE))),
    }


def occlusion_fidelity(raster: FishnetRaster, face_ids: np.ndarray, regions: RegionMap) -> dict[str, float]:
    """Both directions of the visibility error, which propagation cares about.

    A phantom pixel is one painted by a surface element that is not the mesh
    first hit there, which would put a scatterer where the camera cannot see
    one.  A deleted pixel is a paintable first-hit pixel with no surface element
    over it, which silently removes a propagation path.
    """
    face_ids = np.asarray(face_ids, dtype=np.int64)
    if face_ids.shape != raster.source_triangle.shape:
        raise ValueError("face_ids must match the raster resolution")
    painted = raster.source_triangle != UNPAINTABLE
    phantom = int(np.count_nonzero(painted & (raster.source_triangle != face_ids)))
    paintable = regions.source_class != UNPAINTABLE
    deleted = int(np.count_nonzero(paintable & ~painted))
    painted_count = int(np.count_nonzero(painted))
    paintable_count = int(np.count_nonzero(paintable))
    return {
        "painted_pixels": painted_count,
        "phantom_pixels": phantom,
        "phantom_fraction": phantom / painted_count if painted_count else 0.0,
        "paintable_pixels": paintable_count,
        "deleted_pixels": deleted,
        "deleted_fraction": deleted / paintable_count if paintable_count else 0.0,
    }


def angular_tolerance_deg(tolerance_px: float, view: PinholeView) -> float:
    """Worst-case angular error of a boundary displaced by ``tolerance_px``.

    The bound is taken at the image centre, where a rectilinear crop has its
    largest angular pixel pitch.  Boundaries towards the corners are sampled
    more finely in angle, so this is conservative for the whole crop.
    """
    if tolerance_px < 0.0:
        raise ValueError("tolerance_px must be non-negative")
    tangent_x, _tangent_y = view.tangents
    return math.degrees(math.atan(2.0 * tangent_x * tolerance_px / view.width))


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


class _SurfaceBuilder:
    def __init__(
        self,
        class_count: int,
        material_probability: np.ndarray | None,
        surface_offset_m: float,
        record_provenance: bool,
    ) -> None:
        self.class_count = class_count
        self.material_count = 0 if material_probability is None else int(material_probability.shape[2])
        self.material_probability = material_probability
        self.surface_offset_m = float(surface_offset_m)
        self.record_provenance = record_provenance
        self.vertices: list[tuple[float, float, float]] = []
        self.index: dict[tuple[int, int, int], int] = {}
        self.faces: list[tuple[int, int, int]] = []
        self.face_image: list[np.ndarray] = []
        self.face_view: list[np.ndarray] = []
        self.face_class: list[int] = []
        self.face_class_probability: list[np.ndarray] = []
        self.face_confidence: list[float] = []
        self.face_material: list[np.ndarray] = []
        self.face_source: list[int] = []
        self.face_support: list[int] = []
        self.face_visible: list[float] = []
        self.face_group: list[int] = []
        self.pixel_offsets: list[int] = [0]
        self.pixel_indices: list[np.ndarray] = []
        self.rejected_source: list[int] = []
        self.rejected_reason: list[int] = []
        self.rejected_area: list[float] = []

    def begin_group(self, pixels: np.ndarray) -> int:
        group = len(self.pixel_offsets) - 1
        if self.record_provenance:
            self.pixel_indices.append(pixels)
            self.pixel_offsets.append(self.pixel_offsets[-1] + int(pixels.size))
        else:
            self.pixel_offsets.append(self.pixel_offsets[-1])
        return group

    def reject(self, source: int, reason: int, area_px: float) -> None:
        self.rejected_source.append(int(source))
        self.rejected_reason.append(int(reason))
        self.rejected_area.append(float(area_px))

    def add(
        self,
        image_triangles: np.ndarray,
        view_triangles: np.ndarray,
        world_triangles: np.ndarray,
        evidence: _Evidence,
        source: int,
        group: int,
    ) -> None:
        for image_triangle, view_triangle, world_triangle in zip(
            image_triangles, view_triangles, world_triangles, strict=True
        ):
            indices = tuple(self._vertex(point) for point in world_triangle)
            if len(set(indices)) < 3:
                continue
            self.faces.append(indices)
            self.face_image.append(image_triangle)
            self.face_view.append(view_triangle)
            self.face_class.append(evidence.class_id)
            self.face_class_probability.append(evidence.class_probability)
            self.face_confidence.append(evidence.confidence)
            self.face_source.append(source)
            self.face_support.append(evidence.pixel_support)
            self.face_visible.append(evidence.visible_fraction)
            self.face_group.append(group)
            if self.material_count:
                self.face_material.append(evidence.material_probability)

    def _vertex(self, point: np.ndarray) -> int:
        key = (int(round(point[0] * 1e4)), int(round(point[1] * 1e4)), int(round(point[2] * 1e4)))
        found = self.index.get(key)
        if found is None:
            found = len(self.vertices)
            self.index[key] = found
            self.vertices.append((float(point[0]), float(point[1]), float(point[2])))
        return found

    def finish(self, report: dict[str, float], pose: CameraPose) -> FishnetSurface:
        vertices = np.asarray(self.vertices, dtype=np.float64).reshape(-1, 3)
        faces = np.asarray(self.faces, dtype=np.int64).reshape(-1, 3)
        view_triangles = np.asarray(self.face_view, dtype=np.float64).reshape(-1, 3, 3)
        world = vertices[faces] if len(faces) else np.zeros((0, 3, 3))
        edge_a = world[:, 1] - world[:, 0]
        edge_b = world[:, 2] - world[:, 0]
        cross = np.cross(edge_a, edge_b)
        area = 0.5 * np.linalg.norm(cross, axis=1)
        normal = np.divide(cross, np.maximum(2.0 * area, 1e-15)[:, None])
        centroid = world.mean(axis=1)
        toward_camera = pose.position - centroid
        flip = np.einsum("ij,ij->i", normal, toward_camera) < 0.0
        normal[flip] *= -1.0
        material = None
        if self.material_count:
            material = (
                np.asarray(self.face_material, dtype=np.float64)
                if self.face_material
                else np.zeros((0, self.material_count), dtype=np.float64)
            )
        pixel_indices = (
            np.concatenate(self.pixel_indices).astype(np.int64) if self.pixel_indices else np.zeros(0, dtype=np.int64)
        )
        rejected_reason = np.asarray(self.rejected_reason, dtype=np.int64)
        report = dict(report)
        report["rejected_candidates"] = float(rejected_reason.size)
        report["rejected_area_px"] = float(np.sum(self.rejected_area))
        for name, code in REJECTION_REASONS.items():
            report[f"rejected_{name}"] = float(np.count_nonzero(rejected_reason == code))
        return FishnetSurface(
            vertices=vertices,
            faces=faces,
            face_image=np.asarray(self.face_image, dtype=np.float64).reshape(-1, 3, 2),
            face_depth=view_triangles[:, :, 2].mean(axis=1) if len(view_triangles) else np.zeros(0),
            face_normal=normal,
            face_centroid=centroid,
            face_area_m2=area,
            face_solid_angle_sr=triangle_solid_angle(view_triangles),
            face_class=np.asarray(self.face_class, dtype=np.int64),
            face_class_probability=np.asarray(self.face_class_probability, dtype=np.float64).reshape(
                -1, self.class_count
            ),
            face_confidence=np.asarray(self.face_confidence, dtype=np.float64),
            face_material=material,
            face_source_triangle=np.asarray(self.face_source, dtype=np.int64),
            face_pixel_support=np.asarray(self.face_support, dtype=np.int64),
            face_visible_fraction=np.asarray(self.face_visible, dtype=np.float64),
            face_group=np.asarray(self.face_group, dtype=np.int64),
            pixel_offsets=np.asarray(self.pixel_offsets, dtype=np.int64),
            pixel_indices=pixel_indices,
            rejected_source_triangle=np.asarray(self.rejected_source, dtype=np.int64),
            rejected_reason=rejected_reason,
            rejected_image_area_px=np.asarray(self.rejected_area, dtype=np.float64),
            camera_position=np.asarray(pose.position, dtype=np.float64),
            report=report,
        )


@dataclass(frozen=True)
class _Evidence:
    class_id: int
    class_probability: np.ndarray
    confidence: float
    material_probability: np.ndarray
    pixel_support: int
    visible_fraction: float


def _process_triangle(
    triangle: int,
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    face_ids: np.ndarray,
    regions: RegionMap,
    confidence: np.ndarray,
    pose: CameraPose,
    view: PinholeView,
    tree: shapely.STRtree | None,
    chain_lines: list[LineString],
    builder: _SurfaceBuilder,
    report: dict[str, float],
    *,
    near_plane_m: float,
    full_visibility_fraction: float,
    piece_visibility_fraction: float,
    piece_support_fraction: float,
    min_piece_area_px: float,
) -> None:
    corners = world_to_view(mesh_vertices[mesh_faces[triangle]], pose, view)
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 1e-12:
        builder.reject(triangle, REJECTION_REASONS["degenerate_triangle"], 0.0)
        return
    normal = normal / norm
    offset = float(normal @ corners[0])

    clipped = _clip_near_plane(corners, near_plane_m)
    if len(clipped) < 3:
        builder.reject(triangle, REJECTION_REASONS["behind_near_plane"], 0.0)
        return
    polygon = _clip_to_rect(view_to_image(clipped, view), view.width, view.height)
    if len(polygon) < 3 or abs(_signed_area(polygon)) < 1e-9:
        builder.reject(triangle, REJECTION_REASONS["outside_crop"], 0.0)
        return

    rows, columns = _rasterize_convex(polygon, view.width, view.height)
    footprint_area = abs(_signed_area(polygon))
    if rows.size == 0:
        builder.reject(triangle, REJECTION_REASONS["subpixel_footprint"], footprint_area)
        return
    owned = face_ids[rows, columns] == triangle
    if not owned.any():
        builder.reject(triangle, REJECTION_REASONS["occluded_by_support_mesh"], footprint_area)
        return

    report["clipped_source_area_px"] += footprint_area
    present = np.unique(regions.region[rows, columns])
    if present.size == 1 and present[0] >= 0 and owned.mean() >= full_visibility_fraction:
        evidence = _face_evidence(rows, columns, owned, regions, confidence, builder)
        if evidence is None:
            builder.reject(triangle, _support_rejection(rows, columns, owned, regions), footprint_area)
            return
        _emit(_fan(polygon), normal, offset, pose, view, builder, evidence, triangle, rows, columns, owned, report)
        report["emitted_whole"] += 1.0
        return

    report["cut_source_triangles"] += 1.0
    pieces = _arrangement(polygon, tree, chain_lines)
    if not pieces:
        report["arrangement_fallbacks"] += 1.0
        pieces = [Polygon(polygon)]
    assignment = _assign_pixels(pieces, rows, columns)
    for piece_index, piece in enumerate(pieces):
        area = piece.area
        selected = assignment == piece_index
        piece_rows, piece_columns, piece_owned = rows[selected], columns[selected], owned[selected]
        if area < min_piece_area_px:
            builder.reject(triangle, REJECTION_REASONS["below_minimum_area"], area)
            continue
        if piece_rows.size == 0 or not piece_owned.any() or piece_owned.mean() < piece_visibility_fraction:
            builder.reject(triangle, REJECTION_REASONS["occluded_by_support_mesh"], area)
            continue
        supported = regions.region[piece_rows, piece_columns] >= 0
        if np.mean(supported[piece_owned]) < piece_support_fraction:
            builder.reject(triangle, _support_rejection(piece_rows, piece_columns, piece_owned, regions), area)
            continue
        evidence = _face_evidence(piece_rows, piece_columns, piece_owned, regions, confidence, builder)
        if evidence is None:
            builder.reject(triangle, _support_rejection(piece_rows, piece_columns, piece_owned, regions), area)
            continue
        triangles = _triangulate(piece)
        if triangles.size == 0:
            report["arrangement_fallbacks"] += 1.0
            builder.reject(triangle, REJECTION_REASONS["degenerate_triangle"], area)
            continue
        _emit(
            triangles,
            normal,
            offset,
            pose,
            view,
            builder,
            evidence,
            triangle,
            piece_rows,
            piece_columns,
            piece_owned,
            report,
        )


def _emit(
    triangles: np.ndarray,
    normal: np.ndarray,
    offset: float,
    pose: CameraPose,
    view: PinholeView,
    builder: _SurfaceBuilder,
    evidence: _Evidence,
    triangle: int,
    rows: np.ndarray,
    columns: np.ndarray,
    owned: np.ndarray,
    report: dict[str, float],
) -> None:
    flat = triangles.reshape(-1, 2)
    directions = image_to_view_directions(flat, view)
    denominator = directions @ normal
    if np.any(np.abs(denominator) < 1e-9):
        builder.reject(triangle, REJECTION_REASONS["grazing_plane"], 0.0)
        return
    distance = offset / denominator
    if np.any(distance <= 0.0):
        builder.reject(triangle, REJECTION_REASONS["behind_near_plane"], 0.0)
        return
    points = directions * distance[:, None]
    if builder.surface_offset_m:
        points = points - builder.surface_offset_m * points / np.linalg.norm(points, axis=1, keepdims=True)
    view_triangles = points.reshape(-1, 3, 3)
    world_triangles = view_to_world(points, pose, view).reshape(-1, 3, 3)
    group = builder.begin_group((rows[owned] * view.width + columns[owned]).astype(np.int64))
    builder.add(triangles, view_triangles, world_triangles, evidence, triangle, group)
    report["emitted_area_px"] += float(sum(abs(_signed_area(item)) for item in triangles))


def _face_evidence(
    rows: np.ndarray,
    columns: np.ndarray,
    owned: np.ndarray,
    regions: RegionMap,
    confidence: np.ndarray,
    builder: _SurfaceBuilder,
) -> _Evidence | None:
    region = regions.region[rows, columns]
    usable = owned & (region >= 0)
    if not usable.any():
        return None
    classes = regions.region_class[region[usable]]
    weights = np.maximum(confidence[rows[usable], columns[usable]], 1e-6)
    histogram = np.bincount(classes, weights=weights, minlength=builder.class_count)
    total = float(histogram.sum())
    if total <= 0.0:
        return None
    class_id = int(np.argmax(histogram))
    winner = classes == class_id
    material = np.zeros(builder.material_count, dtype=np.float64)
    if builder.material_count:
        material = builder.material_probability[rows[usable][winner], columns[usable][winner]].mean(axis=0)
    return _Evidence(
        class_id=class_id,
        class_probability=histogram[: builder.class_count] / total,
        confidence=float(histogram[class_id] / total)
        * float(np.mean(confidence[rows[usable][winner], columns[usable][winner]])),
        material_probability=material,
        pixel_support=int(np.count_nonzero(usable)),
        visible_fraction=float(owned.mean()),
    )


def _support_rejection(rows: np.ndarray, columns: np.ndarray, owned: np.ndarray, regions: RegionMap) -> int:
    """Say why a piece had no usable evidence, keeping clutter apart from people."""
    if not owned.any():
        return REJECTION_REASONS["occluded_by_support_mesh"]
    reasons = regions.paint_reason[rows[owned], columns[owned]]
    counts = np.bincount(reasons, minlength=len(PAINT_REASONS))
    counts[PAINT_REASONS["paintable"]] = 0
    dominant = int(np.argmax(counts))
    if counts[dominant] == 0:
        return REJECTION_REASONS["no_semantic_support"]
    return _PAINT_TO_REJECTION.get(dominant, REJECTION_REASONS["no_semantic_support"])


def _arrangement(
    polygon: np.ndarray,
    tree: shapely.STRtree | None,
    chain_lines: list[LineString],
    *,
    window_pad_px: float = 2.0,
) -> list[Polygon]:
    """Faces of the boundary chains inside one projected triangle.

    Chains are trimmed to a window a little larger than the triangle rather than
    to the triangle itself.  Trimming exactly on the triangle leaves fragment
    endpoints sitting on the outline to within rounding, and GEOS then treats
    them as dangles and refuses to split the face.  Cutting wide and discarding
    the outside faces afterwards keeps the noding unambiguous.
    """
    boundary = Polygon(polygon)
    if tree is None or not boundary.is_valid or boundary.area <= 0.0:
        return []
    minimum_x, minimum_y, maximum_x, maximum_y = boundary.bounds
    window = shapely.box(
        minimum_x - window_pad_px,
        minimum_y - window_pad_px,
        maximum_x + window_pad_px,
        maximum_y + window_pad_px,
    )
    cuts = []
    for index in np.atleast_1d(tree.query(boundary)):
        piece = chain_lines[int(index)].intersection(window)
        if piece.is_empty or piece.geom_type not in {"LineString", "MultiLineString", "GeometryCollection"}:
            continue
        cuts.append(piece)
    if not cuts:
        return []
    faces = list(polygonize(unary_union([boundary.exterior, *cuts])))
    shapely.prepare(boundary)
    inside = [face for face in faces if face.area > 0.0 and shapely.contains_xy(boundary, *_inner_point(face))]
    return inside if len(inside) > 1 else []


def _inner_point(polygon: Polygon) -> tuple[float, float]:
    point = polygon.representative_point()
    return float(point.x), float(point.y)


def _assign_pixels(pieces: list[Polygon], rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
    x = columns.astype(np.float64) + 0.5
    y = rows.astype(np.float64) + 0.5
    assignment = np.full(rows.size, -1, dtype=np.int64)
    remaining = np.ones(rows.size, dtype=bool)
    for index, piece in enumerate(pieces):
        if not remaining.any():
            break
        shapely.prepare(piece)
        inside = shapely.contains_xy(piece, x[remaining], y[remaining])
        selected = np.nonzero(remaining)[0][inside]
        assignment[selected] = index
        remaining[selected] = False
    if remaining.any():
        points = shapely.points(np.stack([x[remaining], y[remaining]], axis=1))
        distances = np.stack([shapely.distance(points, piece) for piece in pieces], axis=1)
        assignment[remaining] = np.argmin(distances, axis=1)
    return assignment


def _triangulate(polygon: Polygon) -> np.ndarray:
    cleaned = polygon.simplify(0.0)
    if cleaned.is_empty or cleaned.geom_type != "Polygon":
        cleaned = polygon
    exterior = np.asarray(cleaned.exterior.coords, dtype=np.float64)[:-1]
    if len(exterior) < 3:
        return np.zeros((0, 3, 2), dtype=np.float64)
    rings = [exterior]
    for interior in cleaned.interiors:
        hole = np.asarray(interior.coords, dtype=np.float64)[:-1]
        if len(hole) >= 3:
            rings.append(hole)
    vertices = np.concatenate(rings, axis=0)
    ring_ends = np.cumsum([len(ring) for ring in rings]).astype(np.uint32)
    indices = mapbox_earcut.triangulate_float64(vertices, ring_ends)
    if indices.size == 0:
        return np.zeros((0, 3, 2), dtype=np.float64)
    triangles = vertices[indices.reshape(-1, 3)]
    areas = np.abs(
        (triangles[:, 1, 0] - triangles[:, 0, 0]) * (triangles[:, 2, 1] - triangles[:, 0, 1])
        - (triangles[:, 2, 0] - triangles[:, 0, 0]) * (triangles[:, 1, 1] - triangles[:, 0, 1])
    )
    return triangles[areas > 1e-12]


def _fan(polygon: np.ndarray) -> np.ndarray:
    return np.stack([np.stack([polygon[0], polygon[i], polygon[i + 1]]) for i in range(1, len(polygon) - 1)])


def _clip_near_plane(points: np.ndarray, near: float) -> np.ndarray:
    inside = points[:, 2] >= near
    if inside.all():
        return points
    if not inside.any():
        return np.zeros((0, 3), dtype=np.float64)
    output = []
    count = len(points)
    for index in range(count):
        following = (index + 1) % count
        if inside[index]:
            output.append(points[index])
        if inside[index] != inside[following]:
            fraction = (near - points[index, 2]) / (points[following, 2] - points[index, 2])
            output.append(points[index] + fraction * (points[following] - points[index]))
    return np.asarray(output, dtype=np.float64)


def _clip_to_rect(polygon: np.ndarray, width: int, height: int) -> np.ndarray:
    limits = ((0, 0.0, True), (0, float(width), False), (1, 0.0, True), (1, float(height), False))
    for axis, limit, keep_greater in limits:
        if len(polygon) < 3:
            return np.zeros((0, 2), dtype=np.float64)
        polygon = _clip_half_plane(polygon, axis, limit, keep_greater)
    return polygon


def _clip_half_plane(polygon: np.ndarray, axis: int, limit: float, keep_greater: bool) -> np.ndarray:
    values = polygon[:, axis]
    inside = values >= limit if keep_greater else values <= limit
    if inside.all():
        return polygon
    if not inside.any():
        return np.zeros((0, 2), dtype=np.float64)
    output = []
    count = len(polygon)
    for index in range(count):
        following = (index + 1) % count
        if inside[index]:
            output.append(polygon[index])
        if inside[index] != inside[following]:
            span = values[following] - values[index]
            fraction = 0.0 if abs(span) < 1e-15 else (limit - values[index]) / span
            output.append(polygon[index] + fraction * (polygon[following] - polygon[index]))
    return np.asarray(output, dtype=np.float64)


def _rasterize_convex(polygon: np.ndarray, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    x0 = max(int(math.floor(polygon[:, 0].min())), 0)
    x1 = min(int(math.ceil(polygon[:, 0].max())), width)
    y0 = max(int(math.floor(polygon[:, 1].min())), 0)
    y1 = min(int(math.ceil(polygon[:, 1].max())), height)
    if x1 <= x0 or y1 <= y0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    grid_x, grid_y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
    sign = 1.0 if _signed_area(polygon) >= 0.0 else -1.0
    inside = np.ones(grid_x.shape, dtype=bool)
    count = len(polygon)
    for index in range(count):
        start = polygon[index]
        end = polygon[(index + 1) % count]
        cross = (end[0] - start[0]) * (grid_y - start[1]) - (end[1] - start[1]) * (grid_x - start[0])
        inside &= sign * cross >= 0.0
    rows, columns = np.nonzero(inside)
    return rows + y0, columns + x0


def _signed_area(polygon: np.ndarray) -> float:
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))


def _walk_chain(
    node: int,
    edge: int,
    edge_nodes: np.ndarray,
    degree: np.ndarray,
    incident_edge: np.ndarray,
    start: np.ndarray,
    used: np.ndarray,
) -> list[int]:
    chain = [node]
    current = node
    current_edge = edge
    while True:
        used[current_edge] = True
        pair = edge_nodes[current_edge]
        current = int(pair[1]) if int(pair[0]) == current else int(pair[0])
        chain.append(current)
        if degree[current] != 2 or current == node:
            return chain
        following = [int(item) for item in incident_edge[start[current] : start[current + 1]] if not used[item]]
        if not following:
            return chain
        current_edge = following[0]


def _simplify_chain(points: np.ndarray, tolerance_px: float) -> np.ndarray:
    if tolerance_px <= 0.0 or len(points) < 3:
        return points
    if not np.array_equal(points[0], points[-1]):
        return approximate_polygon(points, tolerance_px)
    if len(points) < 6:
        return points
    middle = len(points) // 2
    first = approximate_polygon(points[: middle + 1], tolerance_px)
    second = approximate_polygon(points[middle:], tolerance_px)
    merged = np.concatenate([first[:-1], second], axis=0)
    return merged if len(merged) >= 4 else points


def _compact_regions(component: np.ndarray, labels: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    region = np.full(component.shape, UNPAINTABLE, dtype=np.int64)
    if not valid.any():
        return region, np.zeros(0, dtype=np.int64)
    unique, inverse = np.unique(component[valid], return_inverse=True)
    region[valid] = inverse
    region_class = np.zeros(len(unique), dtype=np.int64)
    region_class[inverse] = labels[valid].astype(np.int64)
    return region, region_class


def _merge_small_regions(
    region: np.ndarray,
    region_class: np.ndarray,
    labels: np.ndarray,
    adjacency_a: np.ndarray,
    adjacency_b: np.ndarray,
    min_region_pixels: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    flat_region = region.ravel()
    left = flat_region[adjacency_a]
    right = flat_region[adjacency_b]
    keep = (left >= 0) & (right >= 0) & (left != right)
    left, right = left[keep], right[keep]
    count = len(region_class)
    sizes = np.bincount(flat_region[flat_region >= 0], minlength=count)
    pair_a = np.concatenate([left, right])
    pair_b = np.concatenate([right, left])
    order = np.argsort(pair_a, kind="stable")
    pair_a, pair_b = pair_a[order], pair_b[order]
    bounds = np.searchsorted(pair_a, np.arange(count + 1))
    parent = np.arange(count, dtype=np.int64)

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = int(parent[item])
        return int(item)

    merged = 0
    for candidate in np.argsort(sizes, kind="stable"):
        if sizes[candidate] >= min_region_pixels:
            break
        root = find(int(candidate))
        neighbours = pair_b[bounds[candidate] : bounds[candidate + 1]]
        if neighbours.size == 0:
            continue
        roots = np.asarray([find(int(item)) for item in neighbours], dtype=np.int64)
        roots = roots[roots != root]
        if roots.size == 0:
            continue
        options, counts = np.unique(roots, return_counts=True)
        target = int(options[np.argmax(counts)])
        parent[root] = target
        sizes[target] += sizes[root]
        sizes[root] = 0
        merged += 1

    resolved = np.asarray([find(int(item)) for item in range(count)], dtype=np.int64)
    unique, inverse = np.unique(resolved, return_inverse=True)
    remapped = np.full(region.shape, UNPAINTABLE, dtype=np.int64)
    inside = region >= 0
    remapped[inside] = inverse[region[inside]]
    class_count = int(labels.max()) + 1 if labels.size else 1
    votes = np.bincount(
        remapped[inside] * class_count + labels[inside].astype(np.int64),
        minlength=len(unique) * class_count,
    ).reshape(len(unique), class_count)
    return remapped, votes.argmax(axis=1).astype(np.int64), merged

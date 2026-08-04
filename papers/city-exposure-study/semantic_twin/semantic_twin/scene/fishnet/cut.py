"""Cut the visible support triangles at the semantic island boundaries.

The direction of travel is what makes this work. Each support-mesh triangle is
projected *into* the rectilinear crop, the island boundaries are intersected as
a plain 2D arrangement there, and the resulting pieces are mapped back to 3D by
intersecting their pixel rays with the triangle's own supporting plane. Within
one crop the camera is an ordinary pinhole, so the map from a triangle to its
image is projective and exactly invertible.

Two guards make that inverse safe. Triangles are clipped against the near plane
before projection, and the mesh first-hit id buffer decides which part of a
triangle is actually visible.

A triangle whose footprint lies inside a single semantic island is emitted
untouched. The support triangulation is metre-scale photogrammetry and there is
nothing to gain from subdividing it where the semantics do not change.
"""

from __future__ import annotations

from dataclasses import dataclass

import mapbox_earcut
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

from ..pinhole import CameraPose, PinholeView, image_to_view_directions, view_to_image, view_to_world, world_to_view
from ..planar import clip_near_plane, clip_to_rect, fan_triangles, rasterize_convex, signed_area, triangle_solid_angle
from .regions import PAINT_REASONS, RegionMap, boundary_chains
from .surface import REJECTION_REASONS, FishnetSurface

_PAINT_TO_REJECTION = {
    PAINT_REASONS["transient_object"]: REJECTION_REASONS["transient_object"],
    PAINT_REASONS["clutter_in_front"]: REJECTION_REASONS["clutter_in_front"],
    PAINT_REASONS["mesh_or_pose_conflict"]: REJECTION_REASONS["mesh_or_pose_conflict"],
    PAINT_REASONS["not_support_surface"]: REJECTION_REASONS["not_support_surface"],
}


@dataclass(frozen=True)
class CutLimits:
    """The thresholds one cut runs under, and what each one trades away.

    They used to be eight keyword arguments threaded through three call layers.
    Grouping them is not tidying: ``occlusion_budget`` has to report
    ``piece_visibility_fraction`` alongside the areas it measures, because a
    piece owning less than that never reaches the accepted table and the kept
    faces are therefore a truncated sample.
    """

    near_plane_m: float = 0.05
    full_visibility_fraction: float = 0.98
    piece_visibility_fraction: float = 0.5
    piece_support_fraction: float = 0.5
    min_piece_area_px: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 < self.full_visibility_fraction <= 1.0 or not 0.0 <= self.piece_visibility_fraction <= 1.0:
            raise ValueError("visibility fractions must lie in (0, 1] and [0, 1]")
        if not 0.0 < self.piece_support_fraction <= 1.0:
            raise ValueError("piece_support_fraction must lie in (0, 1]")


@dataclass(frozen=True)
class _Evidence:
    class_id: int
    class_probability: np.ndarray
    confidence: float
    material_probability: np.ndarray
    pixel_support: int
    visible_fraction: float


@dataclass(frozen=True)
class _Pixels:
    """The pixels a candidate covers, and which of them it is the first hit of.

    ``owned`` is the mesh first-hit test. Keeping it beside the coordinates
    rather than passing three parallel arrays is what stops the evidence, the
    rejection reason and the provenance from ever disagreeing about which pixels
    a face was built from.
    """

    rows: np.ndarray
    columns: np.ndarray
    owned: np.ndarray

    def select(self, mask: np.ndarray) -> _Pixels:
        return _Pixels(self.rows[mask], self.columns[mask], self.owned[mask])

    @property
    def visible_fraction(self) -> float:
        return float(self.owned.mean())


@dataclass(frozen=True)
class _Footprint:
    """One source triangle's projected outline, its pixels and its supporting plane."""

    polygon: np.ndarray
    area_px: float
    pixels: _Pixels
    normal: np.ndarray
    offset: float


@dataclass(frozen=True)
class _Cut:
    """Everything one cut holds fixed while it walks the visible triangles."""

    pose: CameraPose
    view: PinholeView
    regions: RegionMap
    confidence: np.ndarray
    tree: shapely.STRtree | None
    chain_lines: list[LineString]
    builder: _SurfaceBuilder
    report: dict[str, float]
    limits: CutLimits


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
    _check_mesh(mesh_vertices, mesh_faces, face_ids, regions, view)
    limits = CutLimits(
        near_plane_m=near_plane_m,
        full_visibility_fraction=full_visibility_fraction,
        piece_visibility_fraction=piece_visibility_fraction,
        piece_support_fraction=piece_support_fraction,
        min_piece_area_px=min_piece_area_px,
    )
    confidence = _checked_maps(view, confidence, material_probability)

    chains = boundary_chains(regions.region, tolerance_px=boundary_tolerance_px)
    chain_lines = [LineString(chain) for chain in chains]
    tree = shapely.STRtree(chain_lines) if chain_lines else None

    class_count = int(regions.region_class.max()) + 1 if regions.region_class.size else 1
    builder = _SurfaceBuilder(class_count, material_probability, surface_offset_m, record_provenance)
    report = _empty_report(len(chain_lines), limits)
    cut = _Cut(pose, view, regions, confidence, tree, chain_lines, builder, report, limits)

    visible = np.unique(face_ids[face_ids >= 0])
    report["visible_source_triangles"] = float(visible.size)
    for triangle in visible:
        _process_triangle(cut, int(triangle), mesh_vertices, mesh_faces, face_ids)
    return builder.finish(report, pose)


def _check_mesh(
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    face_ids: np.ndarray,
    regions: RegionMap,
    view: PinholeView,
) -> None:
    """Reject a mesh, a first-hit buffer or a region map that cannot go together."""
    if mesh_vertices.ndim != 2 or mesh_vertices.shape[1] != 3:
        raise ValueError("mesh_vertices must have shape (n, 3)")
    if mesh_faces.ndim != 2 or mesh_faces.shape[1] != 3:
        raise ValueError("mesh_faces must have shape (m, 3)")
    if face_ids.shape != view.shape or regions.region.shape != view.shape:
        raise ValueError("face_ids and the region map must match the view resolution")
    if np.any(face_ids >= len(mesh_faces)):
        raise ValueError("face_ids reference triangles outside the support mesh")


def _checked_maps(
    view: PinholeView,
    confidence: np.ndarray | None,
    material_probability: np.ndarray | None,
) -> np.ndarray:
    """Fill in a missing confidence map, and reject either map at the wrong resolution."""
    if confidence is None:
        confidence = np.ones(view.shape, dtype=np.float64)
    confidence = np.asarray(confidence, dtype=np.float64)
    if confidence.shape != view.shape:
        raise ValueError("confidence must match the view resolution")
    if material_probability is not None:
        material_probability = np.asarray(material_probability, dtype=np.float64)
        if material_probability.ndim != 3 or material_probability.shape[:2] != view.shape:
            raise ValueError("material_probability must have shape (height, width, materials)")
    return confidence


def _empty_report(chain_count: int, limits: CutLimits) -> dict[str, float]:
    return {
        "visible_source_triangles": 0.0,
        "boundary_chains": float(chain_count),
        "emitted_whole": 0.0,
        "cut_source_triangles": 0.0,
        "arrangement_fallbacks": 0.0,
        "clipped_source_area_px": 0.0,
        "emitted_area_px": 0.0,
        "rejected_area_px": 0.0,
        # Recorded because the kept faces are a truncated sample: a piece with
        # less visibility than this never reaches the accepted table, so the
        # within-cell figure alone flatters the surface.
        "full_visibility_fraction": float(limits.full_visibility_fraction),
        "piece_visibility_fraction": float(limits.piece_visibility_fraction),
    }


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


def _footprint(
    cut: _Cut,
    triangle: int,
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    face_ids: np.ndarray,
) -> _Footprint | None:
    """Project one source triangle into the crop, or reject it and return None.

    Five ways a triangle never becomes surface, and they are recorded apart
    because they mean different things: a degenerate triangle is a mesh defect,
    a near-plane or crop rejection is this crop's field of view, a subpixel
    footprint is distance, and losing every pixel of the first-hit buffer is
    occlusion.
    """
    view, builder = cut.view, cut.builder
    corners = world_to_view(mesh_vertices[mesh_faces[triangle]], cut.pose, view)
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 1e-12:
        builder.reject(triangle, REJECTION_REASONS["degenerate_triangle"], 0.0)
        return None
    normal = normal / norm
    offset = float(normal @ corners[0])

    clipped = clip_near_plane(corners, cut.limits.near_plane_m)
    if len(clipped) < 3:
        builder.reject(triangle, REJECTION_REASONS["behind_near_plane"], 0.0)
        return None
    polygon = clip_to_rect(view_to_image(clipped, view), view.width, view.height)
    if len(polygon) < 3 or abs(signed_area(polygon)) < 1e-9:
        builder.reject(triangle, REJECTION_REASONS["outside_crop"], 0.0)
        return None

    rows, columns = rasterize_convex(polygon, view.width, view.height)
    area_px = abs(signed_area(polygon))
    if rows.size == 0:
        builder.reject(triangle, REJECTION_REASONS["subpixel_footprint"], area_px)
        return None
    owned = face_ids[rows, columns] == triangle
    if not owned.any():
        builder.reject(triangle, REJECTION_REASONS["occluded_by_support_mesh"], area_px)
        return None
    return _Footprint(polygon, area_px, _Pixels(rows, columns, owned), normal, offset)


def _process_triangle(
    cut: _Cut,
    triangle: int,
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    face_ids: np.ndarray,
) -> None:
    """Emit one source triangle whole, or cut it at the chains that cross it."""
    shape = _footprint(cut, triangle, mesh_vertices, mesh_faces, face_ids)
    if shape is None:
        return
    pixels = shape.pixels
    report = cut.report

    report["clipped_source_area_px"] += shape.area_px
    present = np.unique(cut.regions.region[pixels.rows, pixels.columns])
    if present.size == 1 and present[0] >= 0 and pixels.owned.mean() >= cut.limits.full_visibility_fraction:
        evidence = _face_evidence(cut, pixels)
        if evidence is None:
            cut.builder.reject(triangle, _support_rejection(cut.regions, pixels), shape.area_px)
            return
        _emit(cut, fan_triangles(shape.polygon), shape, evidence, triangle, pixels)
        report["emitted_whole"] += 1.0
        return

    report["cut_source_triangles"] += 1.0
    pieces = _arrangement(shape.polygon, cut.tree, cut.chain_lines)
    if not pieces:
        report["arrangement_fallbacks"] += 1.0
        pieces = [Polygon(shape.polygon)]
    assignment = _assign_pixels(pieces, pixels.rows, pixels.columns)
    for piece_index, piece in enumerate(pieces):
        _process_piece(cut, piece, piece_index, assignment, shape, triangle)


def _process_piece(
    cut: _Cut,
    piece: Polygon,
    piece_index: int,
    assignment: np.ndarray,
    shape: _Footprint,
    triangle: int,
) -> None:
    """Accept or reject one face of the arrangement, on four tests in order."""
    area = piece.area
    pixels = shape.pixels.select(assignment == piece_index)
    if area < cut.limits.min_piece_area_px:
        cut.builder.reject(triangle, REJECTION_REASONS["below_minimum_area"], area)
        return
    if pixels.rows.size == 0 or not pixels.owned.any() or pixels.owned.mean() < cut.limits.piece_visibility_fraction:
        cut.builder.reject(triangle, REJECTION_REASONS["occluded_by_support_mesh"], area)
        return
    supported = cut.regions.region[pixels.rows, pixels.columns] >= 0
    if np.mean(supported[pixels.owned]) < cut.limits.piece_support_fraction:
        cut.builder.reject(triangle, _support_rejection(cut.regions, pixels), area)
        return
    evidence = _face_evidence(cut, pixels)
    if evidence is None:
        cut.builder.reject(triangle, _support_rejection(cut.regions, pixels), area)
        return
    triangles = _triangulate(piece)
    if triangles.size == 0:
        cut.report["arrangement_fallbacks"] += 1.0
        cut.builder.reject(triangle, REJECTION_REASONS["degenerate_triangle"], area)
        return
    _emit(cut, triangles, shape, evidence, triangle, pixels)


def _emit(
    cut: _Cut,
    triangles: np.ndarray,
    shape: _Footprint,
    evidence: _Evidence,
    triangle: int,
    pixels: _Pixels,
) -> None:
    """Send image triangles back to their supporting plane and into the builder."""
    view, builder, normal = cut.view, cut.builder, shape.normal
    flat = triangles.reshape(-1, 2)
    directions = image_to_view_directions(flat, view)
    denominator = directions @ normal
    if np.any(np.abs(denominator) < 1e-9):
        builder.reject(triangle, REJECTION_REASONS["grazing_plane"], 0.0)
        return
    distance = shape.offset / denominator
    if np.any(distance <= 0.0):
        builder.reject(triangle, REJECTION_REASONS["behind_near_plane"], 0.0)
        return
    points = directions * distance[:, None]
    if builder.surface_offset_m:
        points = points - builder.surface_offset_m * points / np.linalg.norm(points, axis=1, keepdims=True)
    view_triangles = points.reshape(-1, 3, 3)
    world_triangles = view_to_world(points, cut.pose, view).reshape(-1, 3, 3)
    owned = pixels.owned
    group = builder.begin_group((pixels.rows[owned] * view.width + pixels.columns[owned]).astype(np.int64))
    builder.add(triangles, view_triangles, world_triangles, evidence, triangle, group)
    cut.report["emitted_area_px"] += float(sum(abs(signed_area(item)) for item in triangles))


def _face_evidence(cut: _Cut, pixels: _Pixels) -> _Evidence | None:
    """Vote the class of one candidate from the pixels it owns, or refuse it."""
    regions, confidence, builder = cut.regions, cut.confidence, cut.builder
    rows, columns, owned = pixels.rows, pixels.columns, pixels.owned
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


def _support_rejection(regions: RegionMap, pixels: _Pixels) -> int:
    """Say why a piece had no usable evidence, keeping clutter apart from people."""
    owned = pixels.owned
    if not owned.any():
        return REJECTION_REASONS["occluded_by_support_mesh"]
    reasons = regions.paint_reason[pixels.rows[owned], pixels.columns[owned]]
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

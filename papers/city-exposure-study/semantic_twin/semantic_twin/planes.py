"""Rebuild a photogrammetric support mesh as planar primitives plus the parts that bend.

Voxel remeshing resamples every surface onto a uniform grid, which is the wrong
prior for a city. A city is mostly flat panels meeting at edges, so the cheap
representation is the panel, not the grid cell. This module finds the panels.

Three steps.

**Segment.** Region growing over the triangle adjacency graph. A face joins a
region when its normal is within ``normal_tolerance_deg`` of the region's current
plane and all three of its vertices sit within ``distance_tolerance_m`` of that
plane. The plane is refitted by area-weighted principal components as the region
grows, so a region that starts on a noisy seed triangle converges onto the wall
rather than onto whatever the seed happened to be tilted towards.

**Flatten.** Each accepted region is projected into its own plane, the projected
triangles are unioned into polygons there, the polygon boundary is simplified once
with Douglas-Peucker, and the result is retriangulated. What comes back is a small
number of large triangles that all carry exactly the same normal, which is the
whole point: a specular ray off a flat wall should not care which triangle it hit.

**Keep the rest.** Faces that never joined a region, and regions below
``min_area_m2``, are copied through untouched. Ornament, gables, reveals and
mullions are real building rather than photogrammetric noise, and flattening them
would be inventing a wall that is not there.

The clusters are returned alongside the mesh because the propagation stage wants
them directly: ``MONOSTATIC_SBR.md`` section 6.3 enumerates image sources over
planes rather than over pixels, and a plane with a polygon boundary is exactly the
primitive that search needs.

Flattening moves vertices, so a region boundary can open a crack against its
neighbour of up to ``distance_tolerance_m``. Set ``pin_boundary`` to keep the
boundary vertices of each region at their original positions, which trades a fringe
of non-planar faces for closure against the neighbours.
"""

from __future__ import annotations

from dataclasses import dataclass

import mapbox_earcut
import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from shapely.geometry import Polygon

UNASSIGNED = -1


@dataclass(frozen=True)
class PlanarCluster:
    """One planar region of the support mesh, with the plane it was fitted to."""

    faces: np.ndarray
    point: np.ndarray
    normal: np.ndarray
    area_m2: float
    residual_m: float

    def offset(self) -> float:
        """The plane constant ``d`` in ``n . x = d``."""
        return float(np.dot(self.normal, self.point))


def face_geometry(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Centroid, area and unit normal per face. Degenerate faces get a zero normal."""
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    cross = np.cross(b - a, c - a)
    twice = np.linalg.norm(cross, axis=1)
    normal = np.zeros_like(cross)
    good = twice > 1e-12
    normal[good] = cross[good] / twice[good, None]
    return (a + b + c) / 3.0, 0.5 * twice, normal


def weld(vertices: np.ndarray, faces: np.ndarray, tolerance: float = 1e-4) -> np.ndarray:
    """Map each vertex onto a representative shared by everything within ``tolerance``.

    Tile photogrammetry arrives vertex-split, so triangles that touch on screen do
    not share indices. Adjacency without welding would find no neighbours at all.
    """
    keys = np.round(np.asarray(vertices, dtype=np.float64) / tolerance).astype(np.int64)
    _, inverse = np.unique(keys, axis=0, return_inverse=True)
    return inverse.ravel()


def face_adjacency(faces: np.ndarray, welded: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Neighbour lists in CSR form over faces that share a welded edge."""
    corners = welded[faces]
    edges = np.sort(
        np.concatenate([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]], axis=0),
        axis=1,
    )
    owner = np.tile(np.arange(len(faces)), 3)
    _, inverse = np.unique(edges, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    order = np.argsort(inverse, kind="stable")
    inverse, owner = inverse[order], owner[order]
    starts = np.flatnonzero(np.concatenate([[True], inverse[1:] != inverse[:-1]]))
    ends = np.concatenate([starts[1:], [len(inverse)]])
    left, right = [], []
    for start, end in zip(starts, ends):
        group = owner[start:end]
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                left.append(group[i])
                right.append(group[j])
    if not left:
        return np.zeros(len(faces) + 1, dtype=np.int64), np.zeros(0, dtype=np.int64)
    pairs = np.array([left + right, right + left], dtype=np.int64)
    order = np.argsort(pairs[0], kind="stable")
    neighbours = pairs[1][order]
    counts = np.bincount(pairs[0], minlength=len(faces))
    return np.concatenate([[0], np.cumsum(counts)]), neighbours


def _fit_plane(centroid: np.ndarray, area: np.ndarray, normal: np.ndarray, members: np.ndarray):
    """Area-weighted plane through the member face centroids, oriented with their normals."""
    weight = area[members]
    total = float(weight.sum())
    point = (centroid[members] * weight[:, None]).sum(axis=0) / max(total, 1e-12)
    centred = (centroid[members] - point) * np.sqrt(weight)[:, None]
    if len(members) < 3:
        plane_normal = normal[members[0]]
        residual = 0.0
    else:
        _, singular, basis = np.linalg.svd(centred, full_matrices=False)
        plane_normal = basis[2]
        residual = float(singular[2] / np.sqrt(max(total, 1e-12)))
    mean_normal = (normal[members] * weight[:, None]).sum(axis=0)
    if np.dot(plane_normal, mean_normal) < 0.0:
        plane_normal = -plane_normal
    return point, plane_normal, residual


def segment_planes(
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    normal_tolerance_deg: float = 25.0,
    distance_tolerance_m: float = 0.25,
    min_area_m2: float = 4.0,
    min_faces: int = 4,
    weld_tolerance_m: float = 1e-4,
) -> tuple[list[PlanarCluster], np.ndarray]:
    """Grow planar regions from the largest faces outwards.

    Returns the accepted clusters and a per-face label array, ``UNASSIGNED`` where
    a face belongs to no accepted cluster.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    centroid, area, normal = face_geometry(vertices, faces)
    welded = weld(vertices, faces, weld_tolerance_m)
    starts, neighbours = face_adjacency(faces, welded)

    cosine_limit = float(np.cos(np.radians(normal_tolerance_deg)))
    label = np.full(len(faces), UNASSIGNED, dtype=np.int64)
    clusters: list[PlanarCluster] = []
    order = np.argsort(-area)
    corner = vertices[faces]

    for seed in order:
        if label[seed] != UNASSIGNED or area[seed] <= 0.0:
            continue
        members = [int(seed)]
        label[seed] = -2
        point, plane_normal, _ = centroid[seed], normal[seed], 0.0
        queue = [int(seed)]
        refit_at = 8
        while queue:
            current = queue.pop()
            for position in range(starts[current], starts[current + 1]):
                candidate = int(neighbours[position])
                if label[candidate] != UNASSIGNED or area[candidate] <= 0.0:
                    continue
                if float(np.dot(normal[candidate], plane_normal)) < cosine_limit:
                    continue
                distance = np.abs((corner[candidate] - point) @ plane_normal)
                if float(distance.max()) > distance_tolerance_m:
                    continue
                label[candidate] = -2
                members.append(candidate)
                queue.append(candidate)
                if len(members) >= refit_at:
                    refit_at *= 2
                    point, plane_normal, _ = _fit_plane(centroid, area, normal, np.array(members))
        members = np.array(members, dtype=np.int64)
        point, plane_normal, residual = _fit_plane(centroid, area, normal, members)
        if len(members) < min_faces or float(area[members].sum()) < min_area_m2:
            label[members] = UNASSIGNED
            continue
        label[members] = len(clusters)
        clusters.append(
            PlanarCluster(
                faces=members,
                point=point,
                normal=plane_normal,
                area_m2=float(area[members].sum()),
                residual_m=residual,
            )
        )
    label[label == -2] = UNASSIGNED
    return clusters, label


def plane_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors spanning the plane, right handed with ``normal``."""
    axis = np.array([0.0, 0.0, 1.0]) if abs(float(normal[2])) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, normal)
    u /= np.linalg.norm(u)
    return u, np.cross(normal, u)


def _rings(polygon: Polygon, simplify_m: float) -> list[np.ndarray]:
    cleaned = polygon.simplify(simplify_m, preserve_topology=True)
    if cleaned.is_empty or cleaned.geom_type != "Polygon":
        cleaned = polygon
    exterior = np.asarray(cleaned.exterior.coords, dtype=np.float64)[:-1]
    if len(exterior) < 3:
        return []
    rings = [exterior]
    for interior in cleaned.interiors:
        hole = np.asarray(interior.coords, dtype=np.float64)[:-1]
        if len(hole) >= 3:
            rings.append(hole)
    return rings


def flatten_cluster(
    vertices: np.ndarray,
    faces: np.ndarray,
    cluster: PlanarCluster,
    *,
    simplify_m: float = 0.15,
    pin_boundary: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Replace a cluster's triangles by a retriangulated flat polygon on its plane.

    With ``pin_boundary`` the vertices on the region's outer boundary keep their
    original distance from the plane, so the region still meets its neighbours where
    it used to. The interior is flat either way.
    """
    u, v = plane_basis(cluster.normal)
    corner = vertices[faces[cluster.faces]]
    local = corner - cluster.point
    x = local @ u
    y = local @ v
    ring = np.stack([x, y], axis=-1)
    ring = np.concatenate([ring, ring[:, :1]], axis=1)
    merged = shapely.union_all(shapely.polygons(ring))
    pieces = list(merged.geoms) if merged.geom_type in ("MultiPolygon", "GeometryCollection") else [merged]

    flat_vertices: list[np.ndarray] = []
    flat_faces: list[np.ndarray] = []
    offset = 0
    for piece in pieces:
        if piece.is_empty or piece.geom_type != "Polygon":
            continue
        rings = _rings(piece, simplify_m)
        if not rings:
            continue
        planar = np.concatenate(rings, axis=0)
        ring_ends = np.cumsum([len(ring) for ring in rings]).astype(np.uint32)
        indices = mapbox_earcut.triangulate_float64(planar, ring_ends)
        if indices.size == 0:
            continue
        point = cluster.point + planar[:, 0:1] * u + planar[:, 1:2] * v
        triangles = indices.reshape(-1, 3).astype(np.int64)
        edge_a = point[triangles[:, 1]] - point[triangles[:, 0]]
        edge_b = point[triangles[:, 2]] - point[triangles[:, 0]]
        outward = np.cross(edge_a, edge_b) @ cluster.normal
        triangles[outward < 0.0] = triangles[outward < 0.0][:, ::-1]
        keep = np.abs(outward) > 1e-9
        flat_vertices.append(point)
        flat_faces.append(triangles[keep] + offset)
        offset += len(point)

    if not flat_faces:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    out_vertices = np.concatenate(flat_vertices, axis=0)
    out_faces = np.concatenate(flat_faces, axis=0)
    if pin_boundary:
        original = corner.reshape(-1, 3)
        height = (original - cluster.point) @ cluster.normal
        keys = np.round(original / 1e-3).astype(np.int64)
        lookup = {tuple(key): float(value) for key, value in zip(keys, height)}
        query = np.round(out_vertices / 1e-3).astype(np.int64)
        shift = np.array([lookup.get(tuple(key), 0.0) for key in query])
        out_vertices = out_vertices + shift[:, None] * cluster.normal
    return out_vertices, out_faces


def rebuild(
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    normal_tolerance_deg: float = 25.0,
    distance_tolerance_m: float = 0.25,
    min_area_m2: float = 4.0,
    simplify_m: float = 0.15,
    pin_boundary: bool = False,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Segment, flatten, and stitch the untouched remainder back on."""
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    _, area, _ = face_geometry(vertices, faces)
    clusters, label = segment_planes(
        vertices,
        faces,
        normal_tolerance_deg=normal_tolerance_deg,
        distance_tolerance_m=distance_tolerance_m,
        min_area_m2=min_area_m2,
    )

    kept = np.flatnonzero(label == UNASSIGNED)
    out_vertices = [vertices]
    out_faces = [faces[kept]]
    offset = len(vertices)
    flattened_area = 0.0
    for cluster in clusters:
        piece_vertices, piece_faces = flatten_cluster(
            vertices, faces, cluster, simplify_m=simplify_m, pin_boundary=pin_boundary
        )
        if not len(piece_faces):
            out_faces.append(faces[cluster.faces])
            continue
        out_vertices.append(piece_vertices)
        out_faces.append(piece_faces + offset)
        offset += len(piece_vertices)
        flattened_area += cluster.area_m2

    new_vertices = np.concatenate(out_vertices, axis=0)
    new_faces = np.concatenate(out_faces, axis=0)
    used = np.unique(new_faces)
    remap = np.zeros(len(new_vertices), dtype=np.int64)
    remap[used] = np.arange(len(used))
    new_vertices, new_faces = new_vertices[used], remap[new_faces]
    report = {
        "clusters": len(clusters),
        "clustered_faces": int(sum(len(cluster.faces) for cluster in clusters)),
        "clustered_area_m2": float(flattened_area),
        "source_area_m2": float(area.sum()),
        "source_triangles": int(len(faces)),
        "kept_triangles": int(len(kept)),
        "triangles": int(len(new_faces)),
        "cluster_residual_p50_m": float(np.median([cluster.residual_m for cluster in clusters])) if clusters else 0.0,
        "normal_tolerance_deg": normal_tolerance_deg,
        "distance_tolerance_m": distance_tolerance_m,
        "min_area_m2": min_area_m2,
        "simplify_m": simplify_m,
        "pin_boundary": pin_boundary,
    }
    return new_vertices, new_faces, report


def cluster_table(clusters: list[PlanarCluster]) -> dict:
    """Plane equations and areas, the primitive the image-source search enumerates."""
    return {
        "count": len(clusters),
        "planes": [
            {
                "normal": [float(value) for value in cluster.normal],
                "offset_m": cluster.offset(),
                "area_m2": cluster.area_m2,
                "residual_m": cluster.residual_m,
                "faces": int(len(cluster.faces)),
            }
            for cluster in clusters
        ],
    }


def connected_face_components(faces: np.ndarray, welded: np.ndarray) -> np.ndarray:
    """Component label per face, over the shared-edge graph. Used by the reports."""
    starts, neighbours = face_adjacency(faces, welded)
    owners = np.repeat(np.arange(len(faces)), np.diff(starts))
    graph = coo_matrix(
        (np.ones(len(neighbours)), (owners, neighbours)),
        shape=(len(faces), len(faces)),
    )
    _, label = connected_components(graph, directed=False)
    return label

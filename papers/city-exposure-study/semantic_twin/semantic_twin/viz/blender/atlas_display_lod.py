"""Conservative polygon LOD for the Blender surface-atlas display.

The canonical atlas mesh remains the audit and transport truth.  This module
only removes its triangle-fan tessellation and, when it is provably safe,
replaces a complete uniform atlas grid by its parent support triangle.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

import numpy as np

DISPLAY_LOD_SCHEMA = "aegis.surface-atlas-display-lod"
DISPLAY_LOD_VERSION = 1
DISPLAY_LOD_ALGORITHM = "complete-uniform-parent-or-canonical-cell-polygon"
DISPLAY_LOD_KEY_FIELDS = (
    "atlas_entity",
    "atlas_material",
    "atlas_transport_state",
    "atlas_transport_material",
    "atlas_geometric_fallback_class",
    "atlas_source_mask",
)


@dataclass(frozen=True)
class AtlasDisplayLod:
    """Ragged display polygons and their exact canonical-cell membership."""

    arrays: dict[str, np.ndarray]
    merged_parent_triangle_count: int
    canonical_face_count: int
    canonical_cell_count: int

    @property
    def polygon_count(self) -> int:
        return int(self.arrays["atlas_display_polygon_offsets"].size - 1)

    @property
    def membership_sha256(self) -> str:
        digest = hashlib.sha256()
        for name in (
            "atlas_display_sparse_cell_offsets",
            "atlas_display_sparse_cell_indices",
        ):
            value = np.ascontiguousarray(self.arrays[name])
            digest.update(name.encode("utf-8") + b"\0")
            digest.update(value.dtype.str.encode("ascii") + b"\0")
            digest.update(str(value.shape).encode("ascii") + b"\0")
            digest.update(value.tobytes())
        return digest.hexdigest()


def build_atlas_display_lod(
    canonical: Mapping[str, np.ndarray],
    support_vertices: np.ndarray,
    support_faces: np.ndarray,
    *,
    resolution: int,
) -> AtlasDisplayLod:
    """Build a presentation-only LOD without changing canonical atlas arrays."""
    vertices = np.asarray(canonical["atlas_vertices"], dtype=np.float64)
    faces = np.asarray(canonical["atlas_faces"], dtype=np.int64)
    source = np.asarray(canonical["atlas_source_triangle"], dtype=np.int64)
    sparse = np.asarray(canonical["atlas_sparse_cell"], dtype=np.int64)
    rows = np.asarray(canonical["atlas_texel_row"], dtype=np.int64)
    columns = np.asarray(canonical["atlas_texel_column"], dtype=np.int64)
    support_vertices = np.asarray(support_vertices, dtype=np.float64)
    support_faces = np.asarray(support_faces, dtype=np.int64)
    if not isinstance(resolution, (int, np.integer)) or int(resolution) < 2:
        raise ValueError("atlas display LOD resolution must be an integer of at least two")
    resolution = int(resolution)
    face_count = len(faces)
    if faces.ndim != 2 or faces.shape[1:] != (3,):
        raise ValueError("canonical atlas faces must be triangles")
    if vertices.ndim != 2 or vertices.shape[1:] != (3,) or not np.all(np.isfinite(vertices)):
        raise ValueError("canonical atlas vertices must be finite 3-D points")
    if support_faces.ndim != 2 or support_faces.shape[1:] != (3,):
        raise ValueError("support faces must be triangles")
    if support_vertices.ndim != 2 or support_vertices.shape[1:] != (3,):
        raise ValueError("support vertices must be 3-D points")
    per_face = (source, sparse, rows, columns)
    categories = {name: np.asarray(canonical[name]) for name in DISPLAY_LOD_KEY_FIELDS}
    per_face += tuple(categories.values())
    if any(value.shape != (face_count,) for value in per_face):
        raise ValueError("canonical atlas indices and categorical values must have one value per face")
    if face_count and (
        np.any(faces < 0)
        or np.any(faces >= len(vertices))
        or np.any(source < 0)
        or np.any(source >= len(support_faces))
    ):
        raise ValueError("canonical atlas geometry leaves its vertex or support-face bounds")

    arrays, merged, cell_count = _build_arrays(
        vertices,
        faces,
        source,
        sparse,
        rows,
        columns,
        categories,
        support_vertices,
        support_faces,
        resolution,
    )
    _validate_membership(arrays, np.unique(sparse))
    _validate_geometry(vertices, faces, support_vertices, support_faces, arrays)
    return AtlasDisplayLod(
        arrays=arrays,
        merged_parent_triangle_count=merged,
        canonical_face_count=face_count,
        canonical_cell_count=cell_count,
    )


def _build_arrays(
    vertices: np.ndarray,
    faces: np.ndarray,
    source: np.ndarray,
    sparse: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    categories: Mapping[str, np.ndarray],
    support_vertices: np.ndarray,
    support_faces: np.ndarray,
    resolution: int,
) -> tuple[dict[str, np.ndarray], int, int]:
    if not len(faces):
        return _empty_arrays(categories), 0, 0
    cell_starts = np.r_[0, np.flatnonzero(sparse[1:] != sparse[:-1]) + 1]
    cell_stops = np.r_[cell_starts[1:], len(faces)]
    cell_face_counts = cell_stops - cell_starts
    cell_sparse = sparse[cell_starts]
    if len(np.unique(cell_sparse)) != len(cell_sparse) or np.any(np.diff(cell_sparse) <= 0):
        raise ValueError("canonical atlas sparse cells must form one increasing face group each")
    face_owner = np.repeat(np.arange(len(cell_starts)), cell_face_counts)
    cell_source = source[cell_starts]
    cell_rows = rows[cell_starts]
    cell_columns = columns[cell_starts]
    for values in (source, rows, columns, *categories.values()):
        if not np.array_equal(values, values[cell_starts][face_owner]):
            raise ValueError("triangles from one canonical atlas cell disagree")
    if np.any(cell_rows < 0) or np.any(cell_rows >= resolution) or np.any(cell_columns < 0):
        raise ValueError("canonical atlas texel coordinates leave the declared resolution")
    if np.any(cell_columns >= resolution - cell_rows):
        raise ValueError("canonical atlas texel coordinates leave the support triangle")

    cell_loop_offsets, cell_loop_indices = _fan_polygon_loops(faces, cell_starts, cell_face_counts, face_owner)
    source_starts = np.r_[0, np.flatnonzero(cell_source[1:] != cell_source[:-1]) + 1]
    source_stops = np.r_[source_starts[1:], len(cell_starts)]
    source_counts = source_stops - source_starts
    source_ids = cell_source[source_starts]
    if len(np.unique(source_ids)) != len(source_ids) or np.any(np.diff(source_ids) <= 0):
        raise ValueError("canonical atlas source triangles must form one increasing cell group each")
    source_owner = np.repeat(np.arange(len(source_starts)), source_counts)
    expected_count = resolution * (resolution + 1) // 2
    full = source_counts == expected_count
    eligible = np.flatnonzero(full)
    expected_code = np.asarray(
        [row * resolution + column for row in range(resolution) for column in range(resolution - row)]
    )
    if eligible.size:
        positions = source_starts[eligible, None] + np.arange(expected_count)[None, :]
        actual = cell_rows[positions] * resolution + cell_columns[positions]
        full[eligible] &= np.all(actual == expected_code, axis=1)
    uniform = np.ones(len(source_starts), dtype=bool)
    for values in categories.values():
        cell_values = values[cell_starts]
        uniform &= np.minimum.reduceat(cell_values, source_starts) == np.maximum.reduceat(cell_values, source_starts)
    merge_source = full & uniform
    merge_cell = merge_source[source_owner]
    keep_cell = ~merge_cell

    output_per_source = np.where(merge_source, 1, source_counts)
    output_source_offsets = np.r_[0, np.cumsum(output_per_source, dtype=np.int64)]
    polygon_count = int(output_source_offsets[-1])
    polygon_is_parent = np.zeros(polygon_count, dtype=bool)
    polygon_cell = np.empty(polygon_count, dtype=np.int64)
    if np.any(merge_source):
        parent_positions = output_source_offsets[:-1][merge_source]
        polygon_is_parent[parent_positions] = True
        polygon_cell[parent_positions] = source_starts[merge_source]
    local_cell = np.arange(len(cell_starts)) - source_starts[source_owner]
    cell_positions = output_source_offsets[:-1][source_owner] + local_cell
    polygon_cell[cell_positions[keep_cell]] = np.flatnonzero(keep_cell)
    polygon_source = cell_source[polygon_cell]
    polygon_loop_counts = np.where(polygon_is_parent, 3, cell_face_counts[polygon_cell] + 2)
    polygon_offsets = np.r_[0, np.cumsum(polygon_loop_counts, dtype=np.int64)]
    parent_groups = np.flatnonzero(merge_source)
    parent_sources = source_ids[parent_groups]
    parent_vertices = support_vertices[support_faces[parent_sources]].reshape(-1, 3)
    display_vertices = np.concatenate((vertices, parent_vertices), axis=0).astype(np.float32, copy=False)
    polygon_indices = np.empty(int(polygon_offsets[-1]), dtype=np.int32)

    kept_cells = np.flatnonzero(keep_cell)
    if kept_cells.size:
        selected_loop = np.repeat(keep_cell, np.diff(cell_loop_offsets))
        selected_vertex_indices = cell_loop_indices[selected_loop]
        kept_counts = np.diff(cell_loop_offsets)[kept_cells]
        kept_polygon_positions = cell_positions[kept_cells]
        within = np.arange(selected_vertex_indices.size) - np.repeat(
            np.r_[0, np.cumsum(kept_counts[:-1], dtype=np.int64)], kept_counts
        )
        targets = np.repeat(polygon_offsets[kept_polygon_positions], kept_counts) + within
        polygon_indices[targets] = selected_vertex_indices
    if parent_groups.size:
        parent_positions = output_source_offsets[:-1][parent_groups]
        targets = (polygon_offsets[parent_positions, None] + np.arange(3)[None, :]).ravel()
        polygon_indices[targets] = np.arange(len(vertices), len(vertices) + len(parent_vertices), dtype=np.int32)

    membership_count = np.where(polygon_is_parent, source_counts[source_owner[polygon_cell]], 1)
    arrays: dict[str, np.ndarray] = {
        "atlas_display_vertices": display_vertices,
        "atlas_display_polygon_offsets": polygon_offsets,
        "atlas_display_polygon_indices": polygon_indices,
        "atlas_display_source_triangle": polygon_source.astype(np.int32, copy=False),
        "atlas_display_sparse_cell_offsets": np.r_[0, np.cumsum(membership_count, dtype=np.int64)],
        "atlas_display_sparse_cell_indices": cell_sparse.astype(np.int64, copy=False),
        "atlas_display_cell_count": membership_count.astype(np.uint32, copy=False),
    }
    for name, values in categories.items():
        arrays[f"atlas_display_{name.removeprefix('atlas_')}"] = values[cell_starts][polygon_cell]
    return arrays, int(np.count_nonzero(merge_source)), len(cell_starts)


def _fan_polygon_loops(
    faces: np.ndarray,
    cell_starts: np.ndarray,
    cell_face_counts: np.ndarray,
    face_owner: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    first_vertex = faces[cell_starts, 0]
    if not np.array_equal(faces[:, 0], first_vertex[face_owner]):
        raise ValueError("canonical atlas cell triangles are not one ordered fan")
    continuation = np.ones(len(faces), dtype=bool)
    continuation[cell_starts] = False
    if np.any(faces[continuation, 1] != faces[np.flatnonzero(continuation) - 1, 2]):
        raise ValueError("canonical atlas cell triangle fan is not contiguous")
    counts = cell_face_counts + 2
    offsets = np.r_[0, np.cumsum(counts, dtype=np.int64)]
    indices = np.empty(int(offsets[-1]), dtype=np.int64)
    indices[offsets[:-1]] = faces[cell_starts, 0]
    indices[offsets[:-1] + 1] = faces[cell_starts, 1]
    within_face_group = np.arange(len(faces)) - cell_starts[face_owner]
    indices[np.repeat(offsets[:-1] + 2, cell_face_counts) + within_face_group] = faces[:, 2]
    return offsets, indices


def _empty_arrays(categories: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {
        "atlas_display_vertices": np.empty((0, 3), dtype=np.float32),
        "atlas_display_polygon_offsets": np.zeros(1, dtype=np.int64),
        "atlas_display_polygon_indices": np.empty(0, dtype=np.int32),
        "atlas_display_source_triangle": np.empty(0, dtype=np.int32),
        "atlas_display_sparse_cell_offsets": np.zeros(1, dtype=np.int64),
        "atlas_display_sparse_cell_indices": np.empty(0, dtype=np.int64),
        "atlas_display_cell_count": np.empty(0, dtype=np.uint32),
    }
    for name, values in categories.items():
        arrays[f"atlas_display_{name.removeprefix('atlas_')}"] = np.empty(0, dtype=values.dtype)
    return arrays


def _validate_membership(arrays: Mapping[str, np.ndarray], expected: np.ndarray) -> None:
    membership = np.asarray(arrays["atlas_display_sparse_cell_indices"], dtype=np.int64)
    if membership.size != expected.size or not np.array_equal(np.sort(membership), expected):
        raise ValueError("atlas display polygons must cover every canonical sparse cell exactly once")
    if np.unique(membership).size != membership.size:
        raise ValueError("atlas display polygon membership overlaps canonical sparse cells")


def _validate_geometry(
    vertices: np.ndarray,
    faces: np.ndarray,
    support_vertices: np.ndarray,
    support_faces: np.ndarray,
    arrays: Mapping[str, np.ndarray],
) -> None:
    canonical_area = (
        0.5
        * np.linalg.norm(
            np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]]),
            axis=1,
        ).sum()
    )
    display_vertices = np.asarray(arrays["atlas_display_vertices"], dtype=np.float64)
    offsets = np.asarray(arrays["atlas_display_polygon_offsets"], dtype=np.int64)
    indices = np.asarray(arrays["atlas_display_polygon_indices"], dtype=np.int64)
    loop_vertices = display_vertices[indices]
    if not len(loop_vertices):
        display_area = 0.0
        area_vectors = np.empty((0, 3), dtype=np.float64)
    else:
        following = np.arange(len(loop_vertices)) + 1
        following[offsets[1:] - 1] = offsets[:-1]
        cross = np.cross(loop_vertices, loop_vertices[following])
        area_vectors = 0.5 * np.add.reduceat(cross, offsets[:-1])
        display_area = np.linalg.norm(area_vectors, axis=1).sum()
    if not np.isclose(display_area, canonical_area, rtol=3e-6, atol=1e-8):
        raise ValueError("atlas display LOD changes the canonical observed surface area")
    source = np.asarray(arrays["atlas_display_source_triangle"], dtype=np.int64)
    parent = support_vertices[support_faces[source]]
    parent_normal = np.cross(parent[:, 1] - parent[:, 0], parent[:, 2] - parent[:, 0])
    orientation = np.einsum("ij,ij->i", area_vectors, parent_normal)
    if np.any(~np.isfinite(orientation)) or np.any(orientation <= 0.0):
        raise ValueError("atlas display polygons must be nonzero and CCW with their support faces")

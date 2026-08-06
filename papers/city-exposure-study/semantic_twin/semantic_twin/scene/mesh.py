"""Read the support mesh off disk, and shoot rays at it.

The support mesh is the photogrammetric shell of one square, in local ENU
metres with z up. It arrives as a compact binary PLY that the acquisition
writes, and this module is the only reader of that format.

It does not decide *which* mesh a site traces. That is
:func:`semantic_twin.paths.site_mesh`, which gates on the build's format
version, and there is exactly one of it on purpose: two sites have a
single-precision version 2 build sitting beside their double-precision rebuild,
and a resolver that guesses from the file name picks up a metre of tile seaming.
Findings 8b in ``docs/BUGS.md`` is what happens when a fishnet is cut against one
and traced against the other.
"""

from __future__ import annotations

import pathlib

import numpy as np


def read_binary_ply(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    """Read vertices and triangle indices from the compact binary PLY.

    The acquisition writes ``float`` vertices and a ``uchar int`` face list with
    exactly three indices per face, which is the only layout accepted here. A
    silently different layout would produce plausible but wrong geometry, so it
    raises instead.

    Vertices come back as float64 whatever the file holds. The file itself is
    always float32, which is where finding 8b's quarter metre lives.
    """
    with path.open("rb") as stream:
        if stream.readline().decode().strip() != "ply":
            raise ValueError(f"not a PLY file: {path}")
        vertex_count: int | None = None
        face_count: int | None = None
        binary_little = False
        element: str | None = None
        properties: list[str] = []
        while True:
            line = stream.readline().decode().strip()
            if line == "format binary_little_endian 1.0":
                binary_little = True
            elif line.startswith("element vertex "):
                element = "vertex"
                vertex_count = int(line.rsplit(" ", 1)[1])
            elif line.startswith("element face "):
                element = "face"
                face_count = int(line.rsplit(" ", 1)[1])
            elif line.startswith("property ") and element == "vertex":
                properties.append(line.split(" ", 1)[1])
            elif line.startswith("property ") and element == "face":
                if line != "property list uchar int vertex_indices":
                    raise ValueError(f"unsupported face property in {path}: {line}")
            elif line == "end_header":
                break
            elif not line:
                raise ValueError(f"truncated PLY header in {path}")
        if not binary_little or vertex_count is None or face_count is None:
            raise ValueError("expected a binary_little_endian PLY with vertex and face elements")
        if properties != ["float x", "float y", "float z"]:
            raise ValueError(f"expected exactly float x, y, z vertices in {path}, found {properties}")
        vertices = np.fromfile(stream, dtype="<f4", count=vertex_count * 3).reshape(vertex_count, 3)
        record = np.dtype([("count", "u1"), ("indices", "<i4", 3)])
        faces = np.fromfile(stream, dtype=record, count=face_count)
    if len(faces) != face_count or np.any(faces["count"] != 3):
        raise ValueError(f"expected {face_count} triangular faces in {path}")
    return vertices.astype(np.float64), faces["indices"].astype(np.int64)


def read_binary_ply_vertices(path: pathlib.Path) -> np.ndarray:
    """Read only the vertices, skipping the face list."""
    with path.open("rb") as stream:
        if stream.readline().decode().strip() != "ply":
            raise ValueError(f"not a PLY file: {path}")
        count = None
        binary_little = False
        while True:
            line = stream.readline().decode().strip()
            if line == "format binary_little_endian 1.0":
                binary_little = True
            if line.startswith("element vertex "):
                count = int(line.rsplit(" ", 1)[1])
            if line == "end_header":
                break
            if not line:
                raise ValueError(f"truncated PLY header in {path}")
        if not binary_little or count is None:
            raise ValueError("expected binary_little_endian PLY with vertices")
        return np.fromfile(stream, dtype="<f4", count=count * 3).reshape(count, 3)


def first_hit_range(
    vertices: np.ndarray,
    faces: np.ndarray,
    origin: np.ndarray,
    directions: np.ndarray,
) -> np.ndarray:
    """First-hit range in metres along each unit direction, NaN where nothing is hit.

    Backed by Embree through trimesh. It is an optional dependency because only
    the registration diagnostics need it, so the import failure names the extra.
    """
    try:
        import trimesh
        from trimesh.ray.ray_pyembree import RayMeshIntersector
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError("first_hit_range needs the raycast extra: pip install trimesh embreex") from exc
    directions = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces), process=False)
    intersector = RayMeshIntersector(mesh)
    origins = np.repeat(np.asarray(origin, dtype=np.float64).reshape(1, 3), len(directions), axis=0)
    locations, index_ray, _ = intersector.intersects_location(origins, directions, multiple_hits=False)
    ranges = np.full(len(directions), np.nan)
    if len(index_ray):
        ranges[index_ray] = np.linalg.norm(locations - origins[index_ray], axis=1)
    return ranges

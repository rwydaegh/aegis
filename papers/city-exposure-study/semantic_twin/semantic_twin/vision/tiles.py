"""The photogrammetry tile texture as a surface the study can read.

The 3D Tiles leaves are textured and nothing else in the pipeline reads those
textures. This module turns them into geometry a face can be matched against:
every textured triangle of a cached tile set, in local ENU metres, with the
atlas each one samples and the map from its UV chart back to world space.

Coordinates are handled in float64 from the glTF node matrix onwards.
``build_inhouse_mesh.py`` used to round its placement through Blender's
single-precision ``Object.matrix_world``, which displaced whole tiles by up to
0.61 m, so :func:`match_support_faces` estimates and removes a per-tile offset
before it trusts a correspondence. That offset now measures 97 nanometres and
the compensation is a no-op, which is itself the cleanest independent check
that the placement fix landed: the same routine on the old single-precision
mesh estimates 0.256 m and matches only 87.2 percent of faces, against 99.97
percent here. The compensation is kept as a cheap guard rather than removed.

What the channel can resolve is set by the texel density, which
:func:`texel_geometry` measures per site rather than assuming. At Korenmarkt the
205 cached tiles carry 27.6 texels per square metre area-weighted median inside
a 140 m crop, a 19.5 cm ground sample distance.
"""

from __future__ import annotations

import io
import pathlib
import struct
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from ..gltf import YUP_TO_ZUP, json_chunk, local_matrix

GLTF_BIN_CHUNK = 0x004E4942
_COMPONENT_DTYPE = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
_COMPONENT_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


@dataclass(frozen=True)
class TileSurface:
    """Textured triangles of one tile set, in local ENU metres.

    ``patches`` holds the decoded texture images, one entry per glTF primitive
    rather than per image, because a tile may bind several primitives to the
    same atlas and keeping the indirection flat costs nothing at this size.
    """

    triangles: np.ndarray
    uv: np.ndarray
    patch: np.ndarray
    tile: np.ndarray
    patches: list[np.ndarray]
    tile_files: tuple[str, ...]

    def __post_init__(self) -> None:
        count = len(self.triangles)
        if self.triangles.shape != (count, 3, 3) or self.uv.shape != (count, 3, 2):
            raise ValueError("tile triangles must be [n, 3, 3] and their uv [n, 3, 2]")
        if self.patch.shape != (count,) or self.tile.shape != (count,):
            raise ValueError("patch and tile indices must have one entry per triangle")

    @property
    def triangle_count(self) -> int:
        return int(len(self.triangles))

    def centroid(self) -> np.ndarray:
        return self.triangles.mean(axis=1)

    def edge_vectors(self) -> tuple[np.ndarray, np.ndarray]:
        return self.triangles[:, 1] - self.triangles[:, 0], self.triangles[:, 2] - self.triangles[:, 0]

    def area_m2(self) -> np.ndarray:
        first, second = self.edge_vectors()
        return 0.5 * np.linalg.norm(np.cross(first, second), axis=1)

    def normal(self) -> np.ndarray:
        first, second = self.edge_vectors()
        cross = np.cross(first, second)
        return cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-30)

    def patch_shape(self) -> np.ndarray:
        """Height and width in texels of the atlas each triangle samples."""
        shapes = np.asarray([[image.shape[0], image.shape[1]] for image in self.patches], dtype=np.float64)
        return shapes[self.patch]

    def uv_texels(self) -> np.ndarray:
        """UV coordinates scaled into texel units of their own atlas."""
        shape = self.patch_shape()
        return self.uv * shape[:, None, ::-1]


def binary_chunk(path: str | pathlib.Path) -> bytes:
    """Return the BIN chunk of a binary glTF container."""
    payload = pathlib.Path(path).read_bytes()
    offset = 12
    while offset + 8 <= len(payload):
        length, kind = struct.unpack_from("<II", payload, offset)
        offset += 8
        if kind == GLTF_BIN_CHUNK:
            return payload[offset : offset + length]
        offset += length
    raise ValueError(f"Binary glTF has no BIN chunk: {path}")


def read_accessor(document: dict[str, Any], blob: bytes, index: int) -> np.ndarray:
    """Read one glTF accessor into a ``[count, components]`` array.

    Interleaved buffer views are supported because the tile server is free to
    emit them, and reading a strided view wrongly would silently mix position
    and texture coordinates rather than fail.
    """
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    dtype = np.dtype(_COMPONENT_DTYPE[accessor["componentType"]])
    components = _COMPONENT_COUNT[accessor["type"]]
    stride = int(view.get("byteStride") or dtype.itemsize * components)
    start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    count = int(accessor["count"])
    raw = np.frombuffer(blob, dtype=np.uint8, count=stride * count, offset=start).reshape(count, stride)
    out = np.empty((count, components), dtype=dtype)
    for column in range(components):
        span = raw[:, column * dtype.itemsize : (column + 1) * dtype.itemsize]
        out[:, column] = np.ascontiguousarray(span).view(dtype).ravel()
    return out


def mesh_node_placements(document: dict[str, Any]) -> list[tuple[int, np.ndarray]]:
    """Mesh index and float64 world matrix of every mesh-bearing glTF node.

    ``gltf.mesh_node_matrices`` returns the matrices alone, which is enough to
    place a tile but not to read its vertices, so the traversal is repeated here
    with the mesh index retained. The matrix is expressed the way Blender would
    hold it after the y-up to z-up conversion, and the tile placement therefore
    stays in double precision the whole way.
    """
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("glTF nodes must be a list")
    scenes = document.get("scenes", [])
    scene_index = int(document.get("scene", 0))
    if isinstance(scenes, list) and 0 <= scene_index < len(scenes):
        roots = [int(index) for index in scenes[scene_index].get("nodes", [])]
    else:
        roots = list(range(len(nodes)))
    placements: list[tuple[int, np.ndarray]] = []
    stack = [(index, np.eye(4)) for index in reversed(roots)]
    seen: set[int] = set()
    while stack:
        index, parent = stack.pop()
        if index in seen or not 0 <= index < len(nodes):
            continue
        seen.add(index)
        node = nodes[index]
        world = parent @ local_matrix(node)
        if "mesh" in node:
            placements.append((int(node["mesh"]), YUP_TO_ZUP @ world))
        for child in reversed([int(child) for child in node.get("children", [])]):
            stack.append((child, world))
    return placements


def _primitive_image(document: dict[str, Any], blob: bytes, primitive: dict[str, Any]) -> np.ndarray:
    material = document["materials"][primitive["material"]]
    texture = material["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    source = document["textures"][texture]["source"]
    view = document["bufferViews"][document["images"][source]["bufferView"]]
    start = int(view.get("byteOffset", 0))
    payload = blob[start : start + int(view["byteLength"])]
    return np.asarray(Image.open(io.BytesIO(payload)).convert("RGB"))


def read_tile_surface(
    tiles_dir: str | pathlib.Path,
    ecef_to_enu: np.ndarray,
    *,
    crop_radius_m: float | None = None,
) -> TileSurface:
    """Read every textured triangle of a cached tile set into local ENU metres.

    ``ecef_to_enu`` is the 4x4 the support-mesh build recorded in its provenance
    JSON under ``alignment.ecef_to_local_enu_matrix``. Reusing it rather than
    re-solving keeps the texture and the geometry in one frame by construction.
    """
    transform = np.asarray(ecef_to_enu, dtype=np.float64)
    if transform.shape != (4, 4):
        raise ValueError("ecef_to_enu must be a 4x4 matrix")
    files = sorted(pathlib.Path(tiles_dir).glob("*.glb"))
    if not files:
        raise FileNotFoundError(f"no .glb tiles under {tiles_dir}")
    triangles: list[np.ndarray] = []
    uvs: list[np.ndarray] = []
    patch_index: list[np.ndarray] = []
    tile_index: list[np.ndarray] = []
    patches: list[np.ndarray] = []
    for tile, path in enumerate(files):
        document = json_chunk(path)
        blob = binary_chunk(path)
        for mesh_index, placement in mesh_node_placements(document):
            for primitive in document["meshes"][mesh_index]["primitives"]:
                attributes = primitive.get("attributes", {})
                if "POSITION" not in attributes or "TEXCOORD_0" not in attributes or "indices" not in primitive:
                    continue
                position = read_accessor(document, blob, attributes["POSITION"]).astype(np.float64)
                uv = read_accessor(document, blob, attributes["TEXCOORD_0"]).astype(np.float64)
                faces = read_accessor(document, blob, primitive["indices"]).astype(np.int64).ravel().reshape(-1, 3)
                enu = (position @ placement[:3, :3].T + placement[:3, 3]) @ transform[:3, :3].T + transform[:3, 3]
                corners = enu[faces]
                if crop_radius_m is not None:
                    inside = np.all(np.linalg.norm(corners[:, :, :2], axis=2) <= crop_radius_m, axis=1)
                    if not inside.any():
                        continue
                    faces, corners = faces[inside], corners[inside]
                triangles.append(corners)
                uvs.append(uv[faces])
                patch_index.append(np.full(len(faces), len(patches), dtype=np.int64))
                tile_index.append(np.full(len(faces), tile, dtype=np.int64))
                patches.append(_primitive_image(document, blob, primitive))
    if not triangles:
        raise ValueError(f"tile set at {tiles_dir} carries no textured triangles")
    return TileSurface(
        triangles=np.concatenate(triangles),
        uv=np.concatenate(uvs),
        patch=np.concatenate(patch_index),
        tile=np.concatenate(tile_index),
        patches=patches,
        tile_files=tuple(path.name for path in files),
    )


def rasterize_uv_triangles(uv_texels: np.ndarray, height: int, width: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Texel centres covered by each UV triangle, as parallel index arrays.

    Returns ``(triangle, row, column)``. The loop is over bounding boxes rather
    than over triangles, so an atlas is rasterized in a handful of vectorised
    passes instead of one Python iteration per chart. Triangles whose UV
    footprint contains no texel centre simply contribute nothing, which is the
    honest outcome for a surface the tiler chose not to sample.
    """
    uv_texels = np.asarray(uv_texels, dtype=np.float64)
    if uv_texels.ndim != 3 or uv_texels.shape[1:] != (3, 2):
        raise ValueError("uv_texels must have shape [triangles, 3, 2]")
    if not uv_texels.size:
        empty = np.empty(0, dtype=np.int64)
        return empty, empty, empty
    low = np.clip(np.floor(uv_texels.min(axis=1)).astype(np.int64), 0, [width - 1, height - 1])
    high = np.clip(np.ceil(uv_texels.max(axis=1)).astype(np.int64), 1, [width, height])
    span = np.maximum(high - low, 1)
    per_triangle = span[:, 0] * span[:, 1]
    triangle = np.repeat(np.arange(len(uv_texels)), per_triangle)
    offset = np.arange(int(per_triangle.sum())) - np.repeat(np.cumsum(per_triangle) - per_triangle, per_triangle)
    column = low[triangle, 0] + offset % span[triangle, 0]
    row = low[triangle, 1] + offset // span[triangle, 0]
    x = column + 0.5
    y = row + 0.5
    a, b, c = uv_texels[triangle, 0], uv_texels[triangle, 1], uv_texels[triangle, 2]
    determinant = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    safe = np.where(np.abs(determinant) < 1e-12, 1.0, determinant)
    first = ((b[:, 0] - x) * (c[:, 1] - y) - (c[:, 0] - x) * (b[:, 1] - y)) / safe
    second = ((c[:, 0] - x) * (a[:, 1] - y) - (a[:, 0] - x) * (c[:, 1] - y)) / safe
    inside = (first >= 0.0) & (second >= 0.0) & (first + second <= 1.0) & (np.abs(determinant) >= 1e-12)
    return triangle[inside], row[inside], column[inside]


def texel_geometry(surface: TileSurface) -> tuple[np.ndarray, np.ndarray]:
    """Ground sample distance in metres and texel aspect ratio per triangle.

    The map from texel space to world space is linear across a triangle, so its
    two singular values are the world extent of one texel along the two
    principal directions. Their geometric mean is the ground sample distance and
    their ratio says how far from square the sampling is, which is the honest
    place to record a chart that was packed at a grazing angle.
    """
    first, second = surface.edge_vectors()
    uv_texels = surface.uv_texels()
    du = uv_texels[:, 1] - uv_texels[:, 0]
    dv = uv_texels[:, 2] - uv_texels[:, 0]
    determinant = du[:, 0] * dv[:, 1] - du[:, 1] * dv[:, 0]
    degenerate = np.abs(determinant) < 1e-12
    safe = np.where(degenerate, 1.0, determinant)
    # Columns of the world-per-texel Jacobian, from inverting the 2x2 uv basis.
    jacobian_x = (first * dv[:, 1, None] - second * du[:, 1, None]) / safe[:, None]
    jacobian_y = (second * du[:, 0, None] - first * dv[:, 0, None]) / safe[:, None]
    xx = np.einsum("ij,ij->i", jacobian_x, jacobian_x)
    yy = np.einsum("ij,ij->i", jacobian_y, jacobian_y)
    xy = np.einsum("ij,ij->i", jacobian_x, jacobian_y)
    trace = xx + yy
    spread = np.sqrt(np.maximum((xx - yy) ** 2 + 4.0 * xy**2, 0.0))
    high = np.maximum(0.5 * (trace + spread), 0.0)
    low = np.maximum(0.5 * (trace - spread), 0.0)
    gsd = np.sqrt(np.sqrt(np.maximum(high * low, 0.0)))
    anisotropy = np.sqrt(np.divide(low, high, out=np.zeros_like(low), where=high > 0.0))
    gsd[degenerate] = np.nan
    anisotropy[degenerate] = 0.0
    return gsd, np.clip(anisotropy, 0.0, 1.0)


@dataclass(frozen=True)
class TileMatch:
    """Correspondence from support-mesh faces onto textured tile triangles."""

    tile_triangle: np.ndarray
    distance_m: np.ndarray
    area_ratio: np.ndarray
    matched: np.ndarray
    report: dict[str, float] = field(default_factory=dict)


def match_support_faces(
    face_triangles: np.ndarray,
    surface: TileSurface,
    *,
    distance_tolerance_m: float = 0.05,
    area_tolerance: float = 1e-3,
) -> TileMatch:
    """Match every support-mesh face to the tile triangle it was built from.

    A single nearest-centroid pass was not enough on the single-precision mesh.
    ``build_inhouse_mesh.py`` used to round each tile's placement through a
    single-precision matrix, which displaced whole tiles by a quarter of a metre
    while leaving their internal shape intact, and at that displacement 13
    percent of Korenmarkt faces failed to match at all. So the first pass is used
    only to decide which tile a face came from, a per-tile median offset is
    removed, and the second pass is the one that is trusted. A match is accepted
    only if it also agrees on triangle area, which is what rejects a genuine
    near-miss.

    On the double-precision mesh the estimated offset is 97 nanometres, so the
    second pass agrees with the first and this is a guard rather than a
    correction. It is kept because it costs one median per tile and because it
    is the check that would catch the placement defect coming back.
    """
    face_triangles = np.asarray(face_triangles, dtype=np.float64)
    if face_triangles.ndim != 3 or face_triangles.shape[1:] != (3, 3):
        raise ValueError("face_triangles must have shape [faces, 3, 3]")
    centroid = surface.centroid()
    area = surface.area_m2()
    tree = cKDTree(centroid)
    face_centroid = face_triangles.mean(axis=1)
    face_area = 0.5 * np.linalg.norm(
        np.cross(face_triangles[:, 1] - face_triangles[:, 0], face_triangles[:, 2] - face_triangles[:, 0]), axis=1
    )
    _, coarse = tree.query(face_centroid, k=1)
    offset = np.zeros_like(face_centroid)
    tiles = surface.tile[coarse]
    for tile in np.unique(tiles):
        rows = tiles == tile
        offset[rows] = np.median(face_centroid[rows] - centroid[coarse[rows]], axis=0)
    distance, index = tree.query(face_centroid - offset, k=1)
    ratio = np.abs(face_area - area[index]) / np.maximum(face_area, 1e-12)
    matched = (distance <= distance_tolerance_m) & (ratio <= area_tolerance)
    report = {
        "faces": float(len(face_triangles)),
        "matched": float(matched.sum()),
        "matched_fraction": float(matched.mean()) if len(face_triangles) else 0.0,
        "median_tile_offset_m": float(np.median(np.linalg.norm(np.unique(offset, axis=0), axis=1)))
        if len(face_triangles)
        else 0.0,
        "median_residual_m": float(np.median(distance[matched])) if matched.any() else float("nan"),
    }
    return TileMatch(tile_triangle=index, distance_m=distance, area_ratio=ratio, matched=matched, report=report)

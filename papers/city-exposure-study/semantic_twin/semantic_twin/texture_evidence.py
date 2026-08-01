"""Material evidence read out of the photogrammetry tile texture.

The panorama semantic layer only reaches surfaces a street-level capture sees.
Measured at Korenmarkt that is 3.7 percent of the support mesh from one capture
position, and in the adjoint frame with four bounces every interaction after the
first can land outside it. This module supplies the fallback: the 3D Tiles
leaves are textured, and nothing else in the pipeline reads those textures.

What the channel can and cannot do is set by the texel density, which is
measured per site rather than assumed. At Korenmarkt the 205 cached tiles carry
27.6 texels per square metre area-weighted median inside a 140 m crop, a 19.5 cm
ground sample distance. That resolves the difference between vegetation and
opaque construction, and it does not resolve a mortar joint, a low-emissivity
coating or a surface roughness, so this channel claims material identity only.
Roughness stays with the prior.

The channel is deliberately built to lose. The panorama resolves 7.7 mm at 20 m
against the texture's 19.5 cm, and the crossover where the texture would win is
near 510 m, outside every crop this study uses. That ordering is encoded in the
``resolution`` term of the emitted :class:`~semantic_twin.evidence.ObservationQuality`
and, where a panorama has already spoken, in a hard cap that makes it impossible
for the texture to move the panorama's winning class. Neither is a downstream
special case.

What the measurement actually found, on 3,204 faces the panorama does label, is
that the ordering above is not what limits this channel. The same descriptor and
the same spatially blocked protocol read off the panorama and then deliberately
box-downsampled to 41 cm, coarser than the texture, still scores 0.473 against
the texture's 0.382. The gap is viewpoint and illumination, not sampling: the
tile texture sees a facade obliquely from above and mostly in shadow. Every
opaque class collapses into one, and only vegetation separates cleanly.

Coordinates are handled in float64 from the glTF node matrix onwards.
``build_inhouse_mesh.py`` currently rounds its placement through Blender's
single-precision ``Object.matrix_world``, which displaces whole tiles by up to
0.61 m, so :func:`match_support_faces` estimates and removes a per-tile offset
before it trusts a correspondence.
"""

from __future__ import annotations

import io
import json
import pathlib
import struct
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image
from scipy import optimize
from scipy.spatial import cKDTree

from semantic_twin.evidence import (
    EvidenceAccumulator,
    ObservationQuality,
    SoftAssociation,
    categorical_information,
)
from semantic_twin.gltf import YUP_TO_ZUP, json_chunk, local_matrix

GLTF_BIN_CHUNK = 0x004E4942
_COMPONENT_DTYPE = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
_COMPONENT_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# Street View at zoom 5 is 16384 pixels around, so one panorama pixel subtends
# 2 pi / 16384 radians.  This is the number the resolution term compares the
# texture against, and it is the whole reason the texture is the weaker source.
PANORAMA_WIDTH_PX = 16384


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


_XYZ_FROM_LINEAR_RGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_D65_WHITE = np.array([0.95047, 1.0, 1.08883])
_SRGB_LEVELS = np.arange(256, dtype=np.float64) / 255.0
_SRGB_DECODE = np.where(_SRGB_LEVELS <= 0.04045, _SRGB_LEVELS / 12.92, ((_SRGB_LEVELS + 0.055) / 1.055) ** 2.4)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert 8-bit sRGB to CIE L*a*b* under D65.

    Lab rather than raw RGB because the discriminations that survive at 19.6 cm
    are lightness and hue, and Lab separates them. Facade texture baked from
    aerial imagery is largely sky-lit and sits at strongly negative b*, so a
    space where that shift is one coordinate rather than three matters.
    """
    rgb = np.asarray(rgb)
    if rgb.dtype == np.uint8:
        # The decode has only 256 distinct inputs, so a table is exact and turns
        # the transcendental into a gather. The panorama control reads 134
        # million pixels twice and this is most of its cost.
        linear = _SRGB_DECODE[rgb]
    else:
        value = rgb.astype(np.float64) / 255.0
        linear = np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)
    xyz = (linear @ _XYZ_FROM_LINEAR_RGB.T) / _D65_WHITE
    f = np.where(xyz > 0.008856, np.cbrt(np.maximum(xyz, 0.0)), 7.787 * xyz + 16.0 / 116.0)
    return np.stack(
        [116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])],
        axis=-1,
    )


TEXTURE_FEATURES: tuple[str, ...] = (
    "mean_lightness",
    "mean_green_red",
    "mean_blue_yellow",
    "std_lightness",
    "std_green_red",
    "std_blue_yellow",
    "skew_lightness",
    "relative_contrast",
    "std_gradient",
    "structure_anisotropy",
    "structure_axis_alignment",
    "mean_chroma",
    "std_chroma",
    "hue_cosine",
    "hue_sine",
    "min_lightness",
    "max_lightness",
    "lightness_range",
    "dark_texel_fraction",
    "bright_texel_fraction",
    "warm_texel_fraction",
    "sky_lit_texel_fraction",
    "green_texel_fraction",
)


@dataclass(frozen=True)
class TextureFeatures:
    """Per-triangle appearance statistics of the texels a triangle owns."""

    values: np.ndarray
    names: tuple[str, ...]
    texel_count: np.ndarray
    gsd_m: np.ndarray
    texel_anisotropy: np.ndarray

    def __post_init__(self) -> None:
        if self.values.shape != (len(self.texel_count), len(self.names)):
            raise ValueError("feature block must have one row per triangle and one column per name")


# Thresholded pixel shares. Absolute Lab cut points rather than per-face
# quantiles, because a share is only comparable between faces if the cut is the
# same everywhere. Sky-lit picks out the strongly blue cast that aerial texture
# puts on a shadowed facade, and green picks out canopy.
_LIGHTNESS_SHARES = (
    lambda lightness, green_red, blue_yellow: lightness < 15.0,
    lambda lightness, green_red, blue_yellow: lightness > 45.0,
    lambda lightness, green_red, blue_yellow: (green_red > 5.0) & (blue_yellow > 0.0),
    lambda lightness, green_red, blue_yellow: blue_yellow < -20.0,
    lambda lightness, green_red, blue_yellow: green_red < 0.0,
)


class MomentAccumulator:
    """Streaming appearance moments over a fixed set of groups.

    Every statistic in :data:`TEXTURE_FEATURES` is a function of running sums, a
    running minimum and a running maximum, so a group can be fed in any number
    of chunks and end up bit-identical to a single pass. That matters twice
    over: an atlas is naturally processed patch by patch, and the panorama
    control has to be computed on a 16384 by 8192 image that does not fit in
    memory as float64. It also guarantees the control and the texture channel
    are compared on literally the same descriptor rather than on two hand-copied
    implementations of it.
    """

    _SUMS = 14

    def __init__(self, size: int) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        self.size = int(size)
        self.count = np.zeros(size, dtype=np.float64)
        self._sums = np.zeros((self._SUMS, size), dtype=np.float64)
        self._shares = np.zeros((len(_LIGHTNESS_SHARES), size), dtype=np.float64)
        self._low = np.full(size, np.inf)
        self._high = np.full(size, -np.inf)

    def add(self, group: np.ndarray, lab: np.ndarray, gradient: np.ndarray) -> None:
        """Fold one chunk of pixels, given their group, Lab values and Lab gradient."""
        group = np.asarray(group, dtype=np.int64)
        lab = np.asarray(lab, dtype=np.float64)
        gradient = np.asarray(gradient, dtype=np.float64)
        if lab.shape != (len(group), 3) or gradient.shape != (len(group), 2):
            raise ValueError("lab must be [pixels, 3] and gradient [pixels, 2]")
        if not group.size:
            return
        if group.min() < 0 or group.max() >= self.size:
            raise IndexError("group index outside the accumulator")
        lightness, green_red, blue_yellow = lab[:, 0], lab[:, 1], lab[:, 2]
        dx, dy = gradient[:, 0], gradient[:, 1]
        magnitude = np.hypot(dx, dy)
        chroma = np.hypot(green_red, blue_yellow)
        terms = (
            lightness,
            lightness**2,
            lightness**3,
            green_red,
            green_red**2,
            blue_yellow,
            blue_yellow**2,
            magnitude,
            magnitude**2,
            dx**2,
            dy**2,
            dx * dy,
            chroma,
            chroma**2,
        )
        for index, values in enumerate(terms):
            self._sums[index] += np.bincount(group, weights=values, minlength=self.size)
        self.count += np.bincount(group, minlength=self.size)
        np.minimum.at(self._low, group, lightness)
        np.maximum.at(self._high, group, lightness)
        for index, mask in enumerate(_LIGHTNESS_SHARES):
            selected = mask(lightness, green_red, blue_yellow).astype(np.float64)
            self._shares[index] += np.bincount(group, weights=selected, minlength=self.size)

    def finish(self) -> np.ndarray:
        """Return the ``[groups, len(TEXTURE_FEATURES)]`` descriptor block."""
        safe = np.maximum(self.count, 1.0)
        shares = self._shares / safe
        (
            sum_l,
            sum_l2,
            sum_l3,
            sum_a,
            sum_a2,
            sum_b,
            sum_b2,
            sum_g,
            sum_g2,
            sum_xx,
            sum_yy,
            sum_xy,
            sum_c,
            sum_c2,
        ) = self._sums / safe
        var_l = np.maximum(sum_l2 - sum_l**2, 0.0)
        var_a = np.maximum(sum_a2 - sum_a**2, 0.0)
        var_b = np.maximum(sum_b2 - sum_b**2, 0.0)
        var_g = np.maximum(sum_g2 - sum_g**2, 0.0)
        var_c = np.maximum(sum_c2 - sum_c**2, 0.0)
        third = sum_l3 - 3.0 * sum_l * sum_l2 + 2.0 * sum_l**3
        trace = sum_xx + sum_yy
        spread = np.sqrt(np.maximum((sum_xx - sum_yy) ** 2 + 4.0 * sum_xy**2, 0.0))
        hue_norm = np.maximum(np.hypot(sum_a, sum_b), 1e-9)
        low = np.where(np.isfinite(self._low), self._low, 0.0)
        high = np.where(np.isfinite(self._high), self._high, 0.0)
        return np.stack(
            [
                sum_l,
                sum_a,
                sum_b,
                np.sqrt(var_l),
                np.sqrt(var_a),
                np.sqrt(var_b),
                third / np.maximum(var_l, 1e-6) ** 1.5,
                sum_g / np.maximum(sum_l, 1e-3),
                np.sqrt(var_g),
                spread / np.maximum(trace, 1e-9),
                np.abs(sum_xx - sum_yy) / np.maximum(spread, 1e-9),
                sum_c,
                np.sqrt(var_c),
                sum_a / hue_norm,
                sum_b / hue_norm,
                low,
                high,
                high - low,
                *shares,
            ],
            axis=1,
        )


def image_lab_and_gradient(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lab image, and its lightness gradient along the column and row axes."""
    lab = srgb_to_lab(image)
    gradient_row, gradient_column = np.gradient(lab[..., 0])
    return lab, gradient_column, gradient_row


def texture_features(surface: TileSurface) -> TextureFeatures:
    """Appearance statistics, texel support and ground sample distance per triangle.

    Only statistics that survive a handful of texels are used. There is no
    filter bank and no learned embedding, because the median triangle owns 14
    texels and a descriptor with more degrees of freedom than that is fitting
    the atlas, not the wall.
    """
    count = surface.triangle_count
    accumulator = MomentAccumulator(count)
    uv_texels = surface.uv_texels()
    for index, image in enumerate(surface.patches):
        rows = np.flatnonzero(surface.patch == index)
        if not rows.size:
            continue
        height, width = image.shape[:2]
        triangle, row, column = rasterize_uv_triangles(uv_texels[rows], height, width)
        if not triangle.size:
            continue
        lab, gradient_column, gradient_row = image_lab_and_gradient(image)
        accumulator.add(
            rows[triangle],
            lab[row, column],
            np.stack([gradient_column[row, column], gradient_row[row, column]], axis=1),
        )
    gsd, anisotropy = texel_geometry(surface)
    return TextureFeatures(
        values=accumulator.finish(),
        names=TEXTURE_FEATURES,
        texel_count=accumulator.count.astype(np.int64),
        gsd_m=gsd,
        texel_anisotropy=anisotropy,
    )


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

    A single nearest-centroid pass is not enough. ``build_inhouse_mesh.py``
    rounds each tile's placement through a single-precision matrix, which
    displaces whole tiles by a quarter of a metre while leaving their internal
    shape intact, and at that displacement 27 percent of Korenmarkt faces snap
    to a neighbouring triangle. So the first pass is used only to decide which
    tile a face came from, a per-tile median offset is removed, and the second
    pass is the one that is trusted. A match is accepted only if it also agrees
    on triangle area, which is what rejects a genuine near-miss.
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


def blocked_folds(
    centroids: np.ndarray,
    *,
    block_m: float = 12.0,
    folds: int = 5,
    seed: int = 7,
) -> np.ndarray:
    """Assign spatial blocks, not individual faces, to cross-validation folds.

    Material is correlated along a building, so a face-wise split lets a model
    memorise the wall it is about to be tested on. Blocking on a horizontal grid
    forces every held-out prediction to be a transfer to a wall the model has
    not seen, which is the only protocol whose number means anything for the
    out-of-view surfaces this channel exists to serve.
    """
    centroids = np.asarray(centroids, dtype=np.float64)
    if centroids.ndim != 2 or centroids.shape[1] < 2:
        raise ValueError("centroids must be [n, >=2]")
    if folds < 2:
        raise ValueError("folds must be at least 2")
    block = np.floor(centroids[:, :2] / float(block_m)).astype(np.int64)
    _, identifier = np.unique(block, axis=0, return_inverse=True)
    order = np.random.default_rng(seed).permutation(int(identifier.max()) + 1)
    return order[identifier] % folds


def fit_softmax(
    features: np.ndarray,
    labels: np.ndarray,
    class_count: int,
    *,
    l2: float = 3.0,
    max_iterations: int = 400,
) -> np.ndarray:
    """Fit a multinomial logistic regression, returning ``[features + 1, classes]``.

    The objective is convex and is minimised with L-BFGS from a zero start, so
    the fit is the global optimum and is reproducible without a seed. The choice
    of a linear model is a statement about the data rather than about
    convenience: with a median of 14 texels per triangle and a few thousand
    labelled faces, the separations that actually survive at 19.6 cm are
    lightness and hue offsets, and a higher-capacity model has nothing left to
    learn from a patch that small.
    """
    features = np.asarray(features, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    if features.ndim != 2 or labels.shape != (len(features),):
        raise ValueError("features must be [n, f] and labels [n]")
    if class_count < 2:
        raise ValueError("class_count must be at least 2")
    if labels.size and (labels.min() < 0 or labels.max() >= class_count):
        raise ValueError("labels must index the class list")
    rows, columns = features.shape
    design = np.hstack([features, np.ones((rows, 1))])
    target = np.zeros((rows, class_count))
    target[np.arange(rows), labels] = 1.0

    def objective(flat: np.ndarray) -> tuple[float, np.ndarray]:
        weights = flat.reshape(columns + 1, class_count)
        scores = design @ weights
        scores -= scores.max(axis=1, keepdims=True)
        normaliser = np.log(np.exp(scores).sum(axis=1))
        loss = float((normaliser - (scores * target).sum(axis=1)).mean())
        loss += 0.5 * l2 * float((weights[:-1] ** 2).sum()) / rows
        probability = np.exp(scores - normaliser[:, None])
        gradient = design.T @ (probability - target) / rows
        gradient[:-1] += l2 * weights[:-1] / rows
        return loss, gradient.ravel()

    result = optimize.minimize(
        objective,
        np.zeros((columns + 1) * class_count),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": max_iterations},
    )
    return result.x.reshape(columns + 1, class_count)


def softmax_probability(
    weights: np.ndarray, features: np.ndarray, *, temperature: np.ndarray | float = 1.0
) -> np.ndarray:
    """Class probabilities of a fitted softmax, optionally temperature-scaled."""
    features = np.asarray(features, dtype=np.float64)
    scores = np.hstack([features, np.ones((len(features), 1))]) @ weights
    scale = np.asarray(temperature, dtype=np.float64)
    if scale.ndim == 1:
        scale = scale[:, None]
    scores = scores / np.maximum(scale, 1e-6)
    scores -= scores.max(axis=1, keepdims=True)
    exponent = np.exp(scores)
    return exponent / exponent.sum(axis=1, keepdims=True)


def fit_temperature(
    scores_probability: np.ndarray, labels: np.ndarray, *, bounds: tuple[float, float] = (0.2, 20.0)
) -> float:
    """Scalar temperature minimising held-out negative log-likelihood.

    Applied to the log of an already normalised probability block, which is the
    same family as scaling the linear scores and avoids having to carry the
    scores around. A temperature above one flattens the prediction, and the
    channel needs that: a face with eight texels must not be allowed to speak
    with the confidence of a face with four hundred.
    """
    probability = np.clip(np.asarray(scores_probability, dtype=np.float64), 1e-12, 1.0)
    labels = np.asarray(labels, dtype=np.int64)
    if not len(labels):
        return 1.0
    scores = np.log(probability)

    def cost(temperature: float) -> float:
        scaled = scores / max(float(temperature), 1e-6)
        scaled -= scaled.max(axis=1, keepdims=True)
        normaliser = np.log(np.exp(scaled).sum(axis=1))
        return float((normaliser - scaled[np.arange(len(labels)), labels]).mean())

    result = optimize.minimize_scalar(cost, bounds=bounds, method="bounded")
    return float(result.x)


@dataclass(frozen=True)
class MaterialClassifier:
    """Texture appearance to material class, with a support-dependent temperature.

    ``support_edges`` are texel-count bin edges and ``support_temperature`` the
    calibration fitted inside each bin on held-out predictions, so the sharpness
    of the prediction is measured against texel support rather than asserted.

    At Korenmarkt it came back flat. Held-out accuracy is 0.856, 0.868, 0.841,
    0.877 and 0.865 across the five bins from 8 texels upward, and the fitted
    temperatures sit between 0.94 and 1.22 with no trend. Texel count is
    confounded with triangle size, and a large triangle is a road or a roof
    rather than a better-observed wall, so the two effects cancel. The
    degradation with support that the emitted evidence does carry therefore
    comes from :func:`support_rows`, which is structural, and not from here.
    Reporting a flat calibration is the point of measuring it.
    """

    weights: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    class_labels: tuple[str, ...]
    feature_names: tuple[str, ...]
    support_edges: np.ndarray
    support_temperature: np.ndarray
    material_labels: tuple[str, ...] = ()
    material_matrix: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.weights.shape != (len(self.feature_names) + 1, len(self.class_labels)):
            raise ValueError("weights must be [features + 1, classes]")
        if len(self.support_temperature) != len(self.support_edges) + 1:
            raise ValueError("one temperature per support bin, including both open ends")
        if self.material_matrix is not None and self.material_matrix.shape != (
            len(self.class_labels),
            len(self.material_labels),
        ):
            raise ValueError("material matrix must be [classes, materials]")

    def temperature_for(self, texel_count: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self.support_edges, np.asarray(texel_count, dtype=np.float64), side="right")
        return self.support_temperature[index]

    def predict(self, features: np.ndarray, texel_count: np.ndarray) -> np.ndarray:
        standard = (np.asarray(features, dtype=np.float64) - self.mean) / self.scale
        return softmax_probability(self.weights, standard, temperature=self.temperature_for(texel_count))

    def predict_material(self, features: np.ndarray, texel_count: np.ndarray) -> np.ndarray:
        """Posterior over the RF material taxonomy rather than over visual class."""
        if self.material_matrix is None:
            raise ValueError("this classifier carries no class to material mapping")
        return self.predict(features, texel_count) @ self.material_matrix

    def save(self, path: str | pathlib.Path) -> None:
        payload = {
            "class_labels": list(self.class_labels),
            "feature_names": list(self.feature_names),
            "material_labels": list(self.material_labels),
        }
        arrays = {
            "metadata": np.asarray(json.dumps(payload)),
            "weights": self.weights,
            "mean": self.mean,
            "scale": self.scale,
            "support_edges": self.support_edges,
            "support_temperature": self.support_temperature,
        }
        if self.material_matrix is not None:
            arrays["material_matrix"] = self.material_matrix
        np.savez_compressed(path, **arrays)

    @classmethod
    def load(cls, path: str | pathlib.Path) -> MaterialClassifier:
        with np.load(path, allow_pickle=False) as document:
            metadata = json.loads(str(document["metadata"]))
            matrix = np.asarray(document["material_matrix"]) if "material_matrix" in document.files else None
            return cls(
                weights=np.asarray(document["weights"]),
                mean=np.asarray(document["mean"]),
                scale=np.asarray(document["scale"]),
                class_labels=tuple(metadata["class_labels"]),
                feature_names=tuple(metadata["feature_names"]),
                support_edges=np.asarray(document["support_edges"]),
                support_temperature=np.asarray(document["support_temperature"]),
                material_labels=tuple(metadata["material_labels"]),
                material_matrix=matrix,
            )


def confusion_matrix(truth: np.ndarray, prediction: np.ndarray, class_count: int) -> np.ndarray:
    """Counts of predicted class against true class."""
    matrix = np.zeros((class_count, class_count), dtype=np.float64)
    np.add.at(matrix, (np.asarray(truth, dtype=np.int64), np.asarray(prediction, dtype=np.int64)), 1.0)
    return matrix


def pairwise_separability(matrix: np.ndarray) -> np.ndarray:
    """Class-balanced two-class accuracy for every pair, ignoring the other classes.

    Restricting the confusion matrix to two rows and two columns and averaging
    the two recalls gives a number that is 0.5 for a coin and 1 for a perfect
    split, and unlike a raw pair accuracy it is not carried by whichever of the
    two classes happens to be more common. That matters here because the
    Korenmarkt facade classes differ in frequency by an order of magnitude.
    """
    matrix = np.asarray(matrix, dtype=np.float64)
    count = len(matrix)
    result = np.full((count, count), np.nan)
    for i in range(count):
        for j in range(count):
            if i == j:
                continue
            first = matrix[i, i] + matrix[i, j]
            second = matrix[j, j] + matrix[j, i]
            if first <= 0.0 or second <= 0.0:
                continue
            result[i, j] = 0.5 * (matrix[i, i] / first + matrix[j, j] / second)
    return result


def collapsing_pairs(matrix: np.ndarray, *, threshold: float = 0.55) -> list[tuple[int, int]]:
    """Class pairs the classifier separates no better than a coin.

    Reporting the pair and merging it is honest. Keeping the distinction, and
    letting the exporter bind two different permittivities to a decision the
    imagery never made, is not.
    """
    separability = pairwise_separability(matrix)
    pairs: list[tuple[int, int]] = []
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            if np.isfinite(separability[i, j]) and separability[i, j] <= threshold:
                pairs.append((i, j))
    return pairs


def panorama_resolution_ratio(
    range_m: np.ndarray,
    gsd_m: np.ndarray,
    *,
    panorama_width_px: int = PANORAMA_WIDTH_PX,
) -> np.ndarray:
    """Linear resolution of the texture relative to a panorama at the same range.

    A Street View panorama subtends ``2 pi / width`` per pixel, so its ground
    sample distance grows with range while the tile texture's does not. The ratio
    is therefore 1/26 at 20 m at Korenmarkt and reaches one only near 520 m,
    beyond any crop this study uses. Emitting it as the ``resolution`` quality
    term is what makes the texture the weaker source everywhere it matters
    without any downstream branch on which channel is speaking.
    """
    range_m = np.asarray(range_m, dtype=np.float64)
    gsd_m = np.asarray(gsd_m, dtype=np.float64)
    panorama_gsd = range_m * (2.0 * np.pi / float(panorama_width_px))
    ratio = np.divide(panorama_gsd, gsd_m, out=np.zeros_like(gsd_m), where=np.isfinite(gsd_m) & (gsd_m > 0.0))
    return np.clip(np.nan_to_num(ratio, nan=0.0, posinf=0.0), 0.0, 1.0)


def support_rows(texel_count: np.ndarray, *, maximum_rows: int = 32) -> np.ndarray:
    """Effective independent observation count implied by a triangle's texels.

    Texels on one wall are strongly correlated, so the count of independent
    samples grows like the linear extent of the patch rather than like its area.
    The square root is that statement, and the cap keeps a road triangle with
    tens of thousands of texels from outweighing everything else in the scene on
    the strength of one aerial photograph.
    """
    count = np.asarray(texel_count, dtype=np.float64)
    return np.clip(np.rint(np.sqrt(np.maximum(count, 0.0))), 0.0, float(maximum_rows)).astype(np.int64)


def posterior_top_mass(
    concentration: np.ndarray,
    probability: np.ndarray,
    *,
    prior: float = 0.25,
) -> np.ndarray:
    """Winning material's posterior mass if this were a face's only evidence.

    The absolute number of Dirichlet counts a texture observation is worth is
    the one quantity this module cannot derive from its own measurements, and no
    other channel writes into the same accumulator yet to calibrate it against.
    Rather than pick a scale and call it physics, the emitted mass is left as the
    product of terms that each mean something, and this reports what it does to a
    posterior so the weakness is a published number rather than a hidden one. A
    caller who wants the texture to lead on out-of-view faces lowers the
    accumulator's own material prior, which is its decision to make and not this
    channel's.
    """
    concentration = np.asarray(concentration, dtype=np.float64)
    probability = np.asarray(probability, dtype=np.float64)
    if probability.ndim != 2:
        raise ValueError("probability must be [faces, materials]")
    total = prior * probability.shape[1]
    return (prior + concentration * probability.max(axis=1)) / (total + concentration)


def dominance_factor(panorama_alpha: np.ndarray, requested: np.ndarray, *, headroom: float = 0.5) -> np.ndarray:
    """Discount that stops the texture overturning a panorama observation.

    Where the panorama has seen a face, its Dirichlet increment has a margin
    between the best and second-best class. Capping the texture's total emitted
    mass at ``headroom`` times that margin makes it arithmetically impossible for
    the texture to change which class wins, whatever it predicts, because even
    all of its mass landing on the runner-up leaves the margin positive. Where
    the panorama has seen nothing the margin is meaningless and no discount
    applies, which is exactly the regime this channel exists for.
    """
    alpha = np.asarray(panorama_alpha, dtype=np.float64)
    requested = np.asarray(requested, dtype=np.float64)
    if alpha.ndim != 2 or len(alpha) != len(requested):
        raise ValueError("panorama_alpha must be [faces, materials] and match the requested mass")
    if not 0.0 <= headroom < 1.0:
        raise ValueError("headroom must lie in [0, 1)")
    seen = alpha.sum(axis=1) > 0.0
    ordered = np.sort(alpha, axis=1)
    margin = ordered[:, -1] - ordered[:, -2] if alpha.shape[1] >= 2 else ordered[:, -1]
    allowed = headroom * margin
    factor = np.ones(len(requested), dtype=np.float64)
    limited = seen & (requested > 0.0)
    factor[limited] = np.minimum(1.0, allowed[limited] / requested[limited])
    return factor


@dataclass(frozen=True)
class TextureEvidence:
    """Per-face material posterior and the observation rows that carry it."""

    face_index: np.ndarray
    material_probability: np.ndarray
    material_labels: tuple[str, ...]
    rows: np.ndarray
    quality: ObservationQuality
    texel_count: np.ndarray
    gsd_m: np.ndarray
    report: dict[str, float] = field(default_factory=dict)

    def concentration(self) -> np.ndarray:
        """Dirichlet mass this channel adds to each face.

        The accumulator discounts every categorical update by how far the
        prediction sits above uniform, so that factor belongs here too. Without
        it the number would be a budget rather than an amount, and the guarantee
        in :func:`dominance_factor` would be stated about the wrong quantity.
        """
        information = categorical_information(self.material_probability)
        return self.rows.astype(np.float64) * self.quality.combined() * information

    def observations(self) -> tuple[SoftAssociation, ObservationQuality, np.ndarray]:
        """Expand into the association, quality and material blocks of one update.

        A face contributing ``k`` rows becomes ``k`` identical observations, so
        the texel support enters as a count of observations rather than as an
        illegal quality factor above one.
        """
        repeat = np.repeat(np.arange(len(self.face_index)), self.rows)
        association = SoftAssociation(
            surface_indices=self.face_index[repeat][:, None],
            probabilities=np.ones((len(repeat), 1), dtype=np.float64),
        )
        quality = ObservationQuality(
            registration=self.quality.registration[repeat],
            geometry=self.quality.geometry[repeat],
            resolution=self.quality.resolution[repeat],
            incidence=self.quality.incidence[repeat],
            visibility=self.quality.visibility[repeat],
            independence=self.quality.independence[repeat],
        )
        return association, quality, self.material_probability[repeat]

    def apply(self, accumulator: EvidenceAccumulator) -> None:
        """Fold this channel into an accumulator that already holds the taxonomy.

        The entity block is uniform and the attribute block is one half
        throughout, which the accumulator's own information weighting turns into
        exactly zero contribution on those two axes. This channel resolves
        material and nothing else, and encoding that here is safer than
        trusting a caller to pass the right blocks.
        """
        if tuple(accumulator.material_labels) != self.material_labels:
            raise ValueError("accumulator material labels differ from the ones this evidence was built on")
        association, quality, material = self.observations()
        rows = len(association.surface_indices)
        entity = np.full((rows, len(accumulator.entity_labels)), 1.0 / max(len(accumulator.entity_labels), 1))
        attributes = np.full((rows, len(accumulator.attribute_labels)), 0.5)
        accumulator.update(association, quality, entity, material, attributes)


def build_texture_evidence(
    features: TextureFeatures,
    match: TileMatch,
    classifier: MaterialClassifier,
    *,
    face_range_m: np.ndarray,
    panorama_alpha: np.ndarray | None = None,
    headroom: float = 0.5,
    maximum_rows: int = 32,
) -> TextureEvidence:
    """Turn texture features into evidence rows for the support-mesh faces.

    Every quality term is a measured property of this observation rather than a
    tuning constant. ``registration`` is one because the texture is bound to the
    geometry by its own UV map and no pose estimate stands between them.
    ``visibility`` is one for the same reason, with the caveat recorded in the
    report that a tree occluding a facade in the source aerial imagery is baked
    into the texture and cannot be detected here.
    """
    if classifier.material_matrix is None:
        raise ValueError("the classifier must carry a class to material mapping to emit material evidence")
    faces = np.flatnonzero(match.matched)
    tile = match.tile_triangle[faces]
    texels = features.texel_count[tile]
    usable = texels > 0
    faces, tile, texels = faces[usable], tile[usable], texels[usable]
    material = classifier.predict_material(features.values[tile], texels)
    gsd = features.gsd_m[tile]
    range_m = np.asarray(face_range_m, dtype=np.float64)[faces]
    ones = np.ones(len(faces), dtype=np.float64)
    rows = np.maximum(support_rows(texels, maximum_rows=maximum_rows), 1)
    resolution = panorama_resolution_ratio(range_m, gsd)
    incidence = features.texel_anisotropy[tile]
    independence = ones.copy()
    if panorama_alpha is not None:
        # Everything the accumulator will multiply by, except the discount being
        # solved for, so the cap binds the mass that is actually added.
        requested = rows.astype(np.float64) * resolution * incidence * categorical_information(material)
        independence = dominance_factor(np.asarray(panorama_alpha)[faces], requested, headroom=headroom)
    quality = ObservationQuality(
        registration=ones.copy(),
        geometry=ones.copy(),
        resolution=resolution,
        incidence=incidence,
        visibility=ones.copy(),
        independence=independence,
    )
    evidence = TextureEvidence(
        face_index=faces,
        material_probability=material,
        material_labels=tuple(classifier.material_labels),
        rows=rows,
        quality=quality,
        texel_count=texels,
        gsd_m=gsd,
        report={
            "faces_with_texture_evidence": float(len(faces)),
            "median_texels_per_face": float(np.median(texels)) if len(texels) else 0.0,
            "median_gsd_m": float(np.nanmedian(gsd)) if len(gsd) else float("nan"),
            "median_resolution_ratio": float(np.median(resolution)) if len(resolution) else 0.0,
            "median_rows": float(np.median(rows)) if len(rows) else 0.0,
            "visibility_caveat": 1.0,
        },
    )
    evidence.report["median_concentration"] = float(np.median(evidence.concentration())) if len(faces) else 0.0
    return evidence

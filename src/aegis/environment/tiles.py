"""3D Tiles server-side traversal and mesh extraction.

Fetches Google Photorealistic 3D Tiles (or any OGC 3D Tiles v1.0/1.1 endpoint),
traverses the tile tree down to a given geometric error threshold, parses GLB/B3DM
tile content, and returns a local-ENU EnvironmentMesh.
"""

from __future__ import annotations

import json
import struct
import urllib.parse
from typing import Any

import numpy as np

from aegis.environment import EnvironmentMesh
from aegis.environment.geo import ecef_to_enu, wgs84_to_ecef
from aegis.environment.materials import classify_color

# ---------------------------------------------------------------------------
# GLB component type constants
# ---------------------------------------------------------------------------
_COMPONENT_TYPE_SIZE = {
    5120: 1,  # BYTE
    5121: 1,  # UNSIGNED_BYTE
    5122: 2,  # SHORT
    5123: 2,  # UNSIGNED_SHORT
    5125: 4,  # UNSIGNED_INT
    5126: 4,  # FLOAT
}
_COMPONENT_TYPE_DTYPE = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
_TYPE_NUM_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def _parse_glb_primitive(
    prim: dict,
    read_accessor,
    vert_offset: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Parse a single GLB mesh primitive into positions, indices, and colors.

    Returns None if the primitive has no POSITION attribute.
    """
    attrs = prim.get("attributes", {})
    if "POSITION" not in attrs:
        return None

    positions = read_accessor(attrs["POSITION"]).astype(np.float64)
    n_verts = len(positions)

    # Triangle indices
    indices_acc = prim.get("indices")
    if indices_acc is not None:
        raw_idx = read_accessor(indices_acc).astype(np.int32).ravel()
        n_tris = len(raw_idx) // 3
        tri_indices = raw_idx[: n_tris * 3].reshape(n_tris, 3) + vert_offset
    else:
        n_tris = n_verts // 3
        seq = np.arange(n_tris * 3, dtype=np.int32)
        tri_indices = seq.reshape(n_tris, 3) + vert_offset

    # Vertex colors
    color_key = next((k for k in attrs if k.startswith("COLOR_")), None)
    if color_key is not None:
        raw_col = read_accessor(attrs[color_key])
        if raw_col.shape[1] >= 3:
            if raw_col.dtype in (np.float32, np.float64):
                rgb = (np.clip(raw_col[:, :3], 0, 1) * 255).astype(np.uint8)
            else:
                rgb = raw_col[:, :3].astype(np.uint8)
        else:
            rgb = np.zeros((n_verts, 3), dtype=np.uint8)
    else:
        rgb = np.zeros((n_verts, 3), dtype=np.uint8)

    return positions, tri_indices, rgb


class TileTraverser:
    """Traverse a 3D Tiles tileset and extract geometry as an EnvironmentMesh.

    Parameters
    ----------
    root_url:
        URL of the root tileset.json (e.g. Google Maps Platform 3D Tiles root).
    api_key:
        Optional API key appended as ``?key=...`` to every request (Google).
    geometric_error:
        Stop recursing into children whose ``geometricError`` is below this
        threshold (meters of screen-space error at some nominal view distance).
        Lower = higher fidelity, more tiles fetched.
    """

    def __init__(
        self,
        root_url: str,
        api_key: str | None = None,
        geometric_error: float = 30.0,
    ) -> None:
        self.root_url = root_url
        self.api_key = api_key
        self.geometric_error = geometric_error
        import requests

        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-GOOG-API-KEY": api_key})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def traverse(self, lat: float, lon: float, radius_m: float) -> EnvironmentMesh:
        """Fetch and merge all tiles whose bounding volume overlaps the query area.

        Parameters
        ----------
        lat, lon:
            Centre of the region of interest (WGS-84 degrees).
        radius_m:
            Radius of the spherical query region (meters).

        Returns
        -------
        EnvironmentMesh
            Vertices in local ENU coordinates centred at (lat, lon, 0).
        """
        resp = self.session.get(self._url_with_key(self.root_url))
        resp.raise_for_status()
        tileset = resp.json()

        origin_ecef = wgs84_to_ecef(lat, lon, 0.0)

        all_verts: list[np.ndarray] = []
        all_tris: list[np.ndarray] = []
        all_colors: list[np.ndarray] = []

        root_node = tileset.get("root", {})
        self._traverse_node(
            node=root_node,
            base_url=self.root_url,
            query_ecef=origin_ecef,
            query_radius=radius_m,
            all_verts=all_verts,
            all_tris=all_tris,
            all_colors=all_colors,
        )

        return self._build_mesh(all_verts, all_tris, all_colors, lat, lon, origin_ecef)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _traverse_node(
        self,
        node: dict[str, Any],
        base_url: str,
        query_ecef: np.ndarray,
        query_radius: float,
        all_verts: list[np.ndarray],
        all_tris: list[np.ndarray],
        all_colors: list[np.ndarray],
    ) -> None:
        """Recursively visit a tile node."""
        bv = node.get("boundingVolume", {})
        if bv and not self._check_intersection(bv, query_ecef, query_radius):
            return

        geo_err = float(node.get("geometricError", 0.0))

        # Fetch tile content if present
        content = node.get("content")
        if content:
            uri = content.get("uri") or content.get("url", "")
            if uri:
                content_url = self._resolve_url(base_url, uri)
                # Pass Google session token if present in content
                session_token = content.get("session")
                try:
                    data = self._fetch_tile_content(content_url, session_token)
                    verts, tris, colors = self._parse_tile_data(data, content_url)
                    if verts is not None and len(verts) > 0:
                        all_verts.append(verts)
                        all_tris.append(tris)
                        all_colors.append(colors)
                except Exception:
                    # Non-fatal: skip tiles that fail to parse
                    pass

        # Recurse into children if geometric error is above threshold
        if geo_err > self.geometric_error:
            for child in node.get("children", []):
                self._traverse_node(
                    node=child,
                    base_url=base_url,
                    query_ecef=query_ecef,
                    query_radius=query_radius,
                    all_verts=all_verts,
                    all_tris=all_tris,
                    all_colors=all_colors,
                )

    def _check_intersection(
        self,
        bounding_volume: dict[str, Any],
        query_ecef: np.ndarray,
        query_radius: float,
    ) -> bool:
        """Test whether a 3D Tiles bounding volume intersects the query sphere."""
        if "sphere" in bounding_volume:
            s = bounding_volume["sphere"]
            center = np.array(s[:3], dtype=np.float64)
            tile_radius = float(s[3])
            dist = float(np.linalg.norm(query_ecef - center))
            return dist <= tile_radius + query_radius

        if "box" in bounding_volume:
            b = bounding_volume["box"]
            # 3D Tiles box: [cx, cy, cz, hx0, hx1, hx2, hy0, hy1, hy2, hz0, hz1, hz2]
            center = np.array(b[0:3], dtype=np.float64)
            half_x = np.array(b[3:6], dtype=np.float64)
            half_y = np.array(b[6:9], dtype=np.float64)
            half_z = np.array(b[9:12], dtype=np.float64)
            # Convert to a conservative AABB for fast rejection
            extent = np.abs(half_x) + np.abs(half_y) + np.abs(half_z)  # conservative radius
            tile_radius = float(np.linalg.norm(extent))
            dist = float(np.linalg.norm(query_ecef - center))
            if dist > tile_radius + query_radius:
                return False
            # Exact OBB-sphere test
            # Project query center into OBB local frame
            d = query_ecef - center
            axes = np.stack([half_x, half_y, half_z])
            extents = np.array([np.linalg.norm(half_x), np.linalg.norm(half_y), np.linalg.norm(half_z)])
            sq_dist = 0.0
            for i in range(3):
                norm = extents[i]
                if norm < 1e-12:
                    continue
                axis = axes[i] / norm
                proj = float(np.dot(d, axis))
                excess = abs(proj) - norm
                if excess > 0:
                    sq_dist += excess * excess
            return sq_dist <= query_radius * query_radius

        if "region" in bounding_volume:
            # region: [west, south, east, north, min_height, max_height] in radians/meters
            r = bounding_volume["region"]
            west, south, east, north = r[0], r[1], r[2], r[3]
            min_h, max_h = r[4], r[5]
            # Use the center of the region as an approximate sphere test
            lat_c = np.degrees(0.5 * (south + north))
            lon_c = np.degrees(0.5 * (west + east))
            h_c = 0.5 * (min_h + max_h)
            center = wgs84_to_ecef(lat_c, lon_c, h_c)
            # Approximate radius as half the diagonal
            corner_a = wgs84_to_ecef(np.degrees(south), np.degrees(west), min_h)
            corner_b = wgs84_to_ecef(np.degrees(north), np.degrees(east), max_h)
            tile_radius = float(np.linalg.norm(corner_b - corner_a)) * 0.5
            dist = float(np.linalg.norm(query_ecef - center))
            return dist <= tile_radius + query_radius

        # Unknown bounding volume type: assume intersection
        return True

    def _fetch_tile_content(self, url: str, session_token: str | None = None) -> bytes:
        """Fetch binary tile content (GLB or B3DM)."""
        full_url = self._url_with_key(url)
        if session_token:
            sep = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{sep}session={session_token}"
        resp = self.session.get(full_url)
        resp.raise_for_status()
        return resp.content

    def _parse_tile_data(self, data: bytes, url: str) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
        """Dispatch to GLB or B3DM parser based on magic bytes / URL suffix."""
        if data[:4] == b"b3dm":
            return self._parse_b3dm(data)
        if data[:4] == b"glTF":
            return self._parse_glb(data)
        # Fallback: try GLB if URL ends in .glb
        lower_url = url.lower().split("?")[0]
        if lower_url.endswith(".glb"):
            return self._parse_glb(data)
        if lower_url.endswith(".b3dm"):
            return self._parse_b3dm(data)
        return None, None, None

    def _parse_b3dm(self, data: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Strip B3DM header and parse the embedded GLB."""
        # B3DM header layout (28 bytes):
        # magic(4) version(4) tile_byte_length(4) ft_json_len(4) ft_bin_len(4)
        # bt_json_len(4) bt_bin_len(4)
        _magic, _version, _total, ft_json, ft_bin, bt_json, bt_bin = struct.unpack_from("<4sIIIIII", data, 0)
        header_size = 28
        skip = ft_json + ft_bin + bt_json + bt_bin
        glb_start = header_size + skip
        return self._parse_glb(data[glb_start:])

    def _parse_glb(self, data: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Parse binary glTF 2.0 and extract vertices, indices, vertex colors.

        Returns
        -------
        vertices : (N, 3) float64  ECEF positions
        indices  : (M, 3) int32    triangle indices, or synthesized if absent
        colors   : (N, 3) uint8    RGB vertex colors (0 if absent)
        """
        if data[:4] != b"glTF":
            raise ValueError("Not a GLB file")

        _version = struct.unpack_from("<I", data, 4)[0]
        _total_length = struct.unpack_from("<I", data, 8)[0]

        # Parse chunks
        offset = 12
        json_data: dict[str, Any] = {}
        bin_buffer = b""

        while offset < len(data):
            if offset + 8 > len(data):
                break
            chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
            offset += 8
            chunk_data = data[offset : offset + chunk_length]
            offset += chunk_length
            if chunk_type == 0x4E4F534A:  # JSON
                json_data = json.loads(chunk_data.decode("utf-8").rstrip("\x00 "))
            elif chunk_type == 0x004E4942:  # BIN
                bin_buffer = bytes(chunk_data)

        if not json_data:
            raise ValueError("GLB has no JSON chunk")

        accessors = json_data.get("accessors", [])
        buffer_views = json_data.get("bufferViews", [])

        def _read_accessor(acc_idx: int) -> np.ndarray:
            acc = accessors[acc_idx]
            bv_idx = acc.get("bufferView")
            if bv_idx is None:
                count = acc["count"]
                n_comp = _TYPE_NUM_COMPONENTS[acc["type"]]
                return np.zeros((count, n_comp), dtype=np.float32)
            bv = buffer_views[bv_idx]
            buf_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            dtype = _COMPONENT_TYPE_DTYPE[acc["componentType"]]
            n_comp = _TYPE_NUM_COMPONENTS[acc["type"]]
            count = acc["count"]
            byte_stride = bv.get("byteStride", 0)

            if byte_stride and byte_stride != n_comp * _COMPONENT_TYPE_SIZE[acc["componentType"]]:
                # Interleaved: read element by element
                elem_size = n_comp * _COMPONENT_TYPE_SIZE[acc["componentType"]]
                result = np.empty((count, n_comp), dtype=dtype)
                for i in range(count):
                    elem_bytes = bin_buffer[buf_offset + i * byte_stride : buf_offset + i * byte_stride + elem_size]
                    result[i] = np.frombuffer(elem_bytes, dtype=dtype)
                return result
            else:
                total_bytes = count * n_comp * _COMPONENT_TYPE_SIZE[acc["componentType"]]
                raw = bin_buffer[buf_offset : buf_offset + total_bytes]
                arr = np.frombuffer(raw, dtype=dtype)
                if n_comp > 1:
                    arr = arr.reshape(count, n_comp)
                return arr

        # Collect geometry from all mesh primitives
        all_positions: list[np.ndarray] = []
        all_indices: list[np.ndarray] = []
        all_colors: list[np.ndarray] = []

        vert_offset = 0
        for mesh in json_data.get("meshes", []):
            for prim in mesh.get("primitives", []):
                result = _parse_glb_primitive(prim, _read_accessor, vert_offset)
                if result is None:
                    continue
                positions, tri_indices, rgb = result
                all_positions.append(positions)
                all_indices.append(tri_indices)
                all_colors.append(rgb)
                vert_offset += len(positions)

        if not all_positions:
            return (
                np.zeros((0, 3), dtype=np.float64),
                np.zeros((0, 3), dtype=np.int32),
                np.zeros((0, 3), dtype=np.uint8),
            )

        verts = np.concatenate(all_positions, axis=0)
        tris = np.concatenate(all_indices, axis=0)
        colors = np.concatenate(all_colors, axis=0)
        return verts, tris, colors

    def _build_mesh(
        self,
        all_verts: list[np.ndarray],
        all_tris: list[np.ndarray],
        all_colors: list[np.ndarray],
        lat: float,
        lon: float,
        origin_ecef: np.ndarray,
    ) -> EnvironmentMesh:
        """Combine collected tile geometry into a single EnvironmentMesh."""
        if not all_verts:
            return EnvironmentMesh(
                vertices=np.zeros((0, 3), dtype=np.float64),
                triangles=np.zeros((0, 3), dtype=np.int32),
                normals=np.zeros((0, 3), dtype=np.float64),
                materials=np.zeros(0, dtype=np.int32),
                origin_lat=lat,
                origin_lon=lon,
                source="3dtiles",
            )

        # Offset indices so they index into the concatenated vertex array
        vert_counts = [v.shape[0] for v in all_verts]
        offsets = np.cumsum([0] + vert_counts[:-1])
        adjusted_tris = [t + offsets[i] for i, t in enumerate(all_tris)]

        verts_ecef = np.concatenate(all_verts, axis=0)  # (N, 3) ECEF
        tris = np.concatenate(adjusted_tris, axis=0).astype(np.int32)
        colors = np.concatenate(all_colors, axis=0)  # (N, 3) uint8

        # Transform ECEF -> local ENU
        verts_enu = ecef_to_enu(verts_ecef, origin_ecef, lat, lon)

        # Compute per-face normals (n_triangles, 3) to match binary protocol
        from aegis.environment.osm import _compute_face_normals

        normals = _compute_face_normals(verts_enu, tris)

        # Classify materials from vertex colors
        materials = np.array(
            [int(classify_color(int(colors[i, 0]), int(colors[i, 1]), int(colors[i, 2]))) for i in range(len(colors))],
            dtype=np.int32,
        )
        # Map per-vertex materials to per-triangle (use first vertex of each triangle)
        tri_materials = materials[tris[:, 0]] if len(tris) > 0 else np.zeros(0, dtype=np.int32)

        return EnvironmentMesh(
            vertices=verts_enu,
            triangles=tris,
            normals=normals,
            materials=tri_materials,
            origin_lat=lat,
            origin_lon=lon,
            source="3dtiles",
        )

    def _url_with_key(self, url: str) -> str:
        """Append API key to URL if set."""
        if not self.api_key:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}key={self.api_key}"

    @staticmethod
    def _resolve_url(base_url: str, uri: str) -> str:
        """Resolve a possibly-relative URI against the base tileset URL."""
        return urllib.parse.urljoin(base_url, uri)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

"""Tests for 3D Tiles server-side traversal and mesh extraction."""

import json
from unittest.mock import MagicMock

import numpy as np
import pytest

requests = pytest.importorskip("requests", reason="requests not installed")

from aegis.environment.tiles import TileTraverser  # noqa: E402


class TestTileTraverser:
    def test_init_with_api_key(self):
        t = TileTraverser(
            root_url="https://tile.googleapis.com/v1/3dtiles/root.json",
            api_key="test-key",
            geometric_error=30.0,
        )
        assert t.geometric_error == 30.0

    def test_init_without_api_key(self):
        t = TileTraverser(
            root_url="https://example.com/tileset.json",
            geometric_error=60.0,
        )
        assert t.api_key is None

    def test_traverse_empty_tileset(self):
        mock_session = MagicMock()

        tileset = {
            "root": {
                "boundingVolume": {"sphere": [0, 0, 0, 1000]},
                "geometricError": 1000,
            },
            "geometricError": 1000,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = tileset
        mock_resp.status_code = 200
        mock_session.get.return_value = mock_resp

        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0
        t.session = mock_session

        mesh = t.traverse(lat=51.05, lon=3.72, radius_m=200)
        assert mesh.vertices.shape[1] == 3
        assert mesh.source == "3dtiles"

    def test_check_intersection_sphere(self):
        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0

        # bounding sphere centered at origin with radius 100
        bv = {"sphere": [0.0, 0.0, 0.0, 100.0]}
        query_center = np.array([50.0, 0.0, 0.0])
        assert t._check_intersection(bv, query_center, 10.0)

        # query sphere far away - no intersection
        query_far = np.array([500.0, 0.0, 0.0])
        assert not t._check_intersection(bv, query_far, 10.0)

    def test_check_intersection_box(self):
        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0

        # 3D Tiles box: center(3) + 3 half-axes columns (3x3) = 12 values
        # center at (0,0,0), half-extents 100 in each axis
        bv = {
            "box": [
                0,
                0,
                0,  # center
                100,
                0,
                0,  # half-axis x
                0,
                100,
                0,  # half-axis y
                0,
                0,
                100,  # half-axis z
            ]
        }
        query_center = np.array([50.0, 0.0, 0.0])
        assert t._check_intersection(bv, query_center, 10.0)

        query_far = np.array([500.0, 0.0, 0.0])
        assert not t._check_intersection(bv, query_far, 10.0)

    def test_parse_glb_minimal(self):
        """Parse a minimal GLB with 3 vertices forming one triangle."""
        import struct

        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0

        # Build minimal GLB: 3 vertices, no indices, no colors
        verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
        bin_data = verts.tobytes()

        gltf_json = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {"POSITION": 0},
                            "mode": 4,
                        }
                    ]
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "byteOffset": 0,
                    "componentType": 5126,  # FLOAT
                    "count": 3,
                    "type": "VEC3",
                    "min": [0.0, 0.0, 0.0],
                    "max": [1.0, 1.0, 0.0],
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(bin_data),
                    "target": 34962,
                }
            ],
            "buffers": [{"byteLength": len(bin_data)}],
        }

        json_bytes = json.dumps(gltf_json).encode("utf-8")
        # Pad to 4-byte boundary
        padding = (4 - len(json_bytes) % 4) % 4
        json_bytes += b" " * padding

        total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        # GLB header
        header = struct.pack("<III", 0x46546C67, 2, total_length)
        # JSON chunk
        json_chunk_header = struct.pack("<II", len(json_bytes), 0x4E4F534A)
        # BIN chunk
        bin_chunk_header = struct.pack("<II", len(bin_data), 0x004E4942)

        glb_data = header + json_chunk_header + json_bytes + bin_chunk_header + bin_data

        verts_out, indices_out, colors_out = t._parse_glb(glb_data)
        assert verts_out.shape == (3, 3)
        assert np.allclose(verts_out[0], [0.0, 0.0, 0.0])
        assert np.allclose(verts_out[1], [1.0, 0.0, 0.0])

    def test_parse_b3dm_wraps_glb(self):
        """B3DM header should be stripped before GLB parsing."""
        import struct

        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0

        # Build same minimal GLB as above
        verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
        bin_data = verts.tobytes()
        gltf_json = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {"POSITION": 0},
                            "mode": 4,
                        }
                    ]
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "byteOffset": 0,
                    "componentType": 5126,
                    "count": 3,
                    "type": "VEC3",
                    "min": [0.0, 0.0, 0.0],
                    "max": [1.0, 1.0, 0.0],
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(bin_data),
                    "target": 34962,
                }
            ],
            "buffers": [{"byteLength": len(bin_data)}],
        }
        json_bytes = json.dumps(gltf_json).encode("utf-8")
        padding = (4 - len(json_bytes) % 4) % 4
        json_bytes += b" " * padding
        total_glb_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        glb_header = struct.pack("<III", 0x46546C67, 2, total_glb_length)
        json_chunk_header = struct.pack("<II", len(json_bytes), 0x4E4F534A)
        bin_chunk_header = struct.pack("<II", len(bin_data), 0x004E4942)
        glb_data = glb_header + json_chunk_header + json_bytes + bin_chunk_header + bin_data

        # Wrap in B3DM: magic(4) + version(4) + total_length(4) + ft_json_len(4)
        # + ft_bin_len(4) + bt_json_len(4) + bt_bin_len(4) = 28 bytes
        b3dm_header_size = 28
        total_b3dm = b3dm_header_size + len(glb_data)
        b3dm_header = (
            b"b3dm"
            + struct.pack("<I", 1)  # version
            + struct.pack("<I", total_b3dm)  # tile_byte_length
            + struct.pack("<I", 0)  # ft_json_byte_length
            + struct.pack("<I", 0)  # ft_bin_byte_length
            + struct.pack("<I", 0)  # bt_json_byte_length
            + struct.pack("<I", 0)  # bt_bin_byte_length
        )
        b3dm_data = b3dm_header + glb_data

        verts_out, indices_out, colors_out = t._parse_b3dm(b3dm_data)
        assert verts_out.shape == (3, 3)

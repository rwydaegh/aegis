from __future__ import annotations

import json
import pathlib
import struct

import numpy as np
import pytest

from semantic_twin.gltf import YUP_TO_ZUP, json_chunk, local_matrix, mesh_node_matrices

# A real Photorealistic 3D Tiles leaf placement. Its components need more than the
# 24 mantissa bits of a single-precision float, which is the whole defect.
ECEF_TRANSLATION = (4423590.456613353, 4523872.639793346, -715814.055048705)


def write_glb(path: pathlib.Path, document: dict) -> pathlib.Path:
    body = json.dumps(document).encode("utf-8")
    body += b" " * ((4 - len(body) % 4) % 4)
    header = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(body))
    path.write_bytes(header + struct.pack("<II", len(body), 0x4E4F534A) + body)
    return path


def leaf_document(translation: tuple[float, float, float] = ECEF_TRANSLATION) -> dict:
    matrix = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, *translation, 1]
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"matrix": matrix, "mesh": 0}],
        "meshes": [{"primitives": []}],
    }


def test_json_chunk_round_trips_a_container(tmp_path: pathlib.Path) -> None:
    path = write_glb(tmp_path / "leaf.glb", leaf_document())
    assert json_chunk(path)["asset"]["version"] == "2.0"


def test_json_chunk_rejects_a_non_container(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "not.glb"
    path.write_bytes(b"nope")
    with pytest.raises(ValueError):
        json_chunk(path)


def test_node_matrix_keeps_every_digit_of_an_ecef_placement(tmp_path: pathlib.Path) -> None:
    path = write_glb(tmp_path / "leaf.glb", leaf_document())
    matrices = mesh_node_matrices(path)
    assert len(matrices) == 1
    assert matrices[0].dtype == np.float64

    exact = YUP_TO_ZUP[:3, :3] @ np.array(ECEF_TRANSLATION)
    assert np.array_equal(matrices[0][:3, 3], exact)
    single = np.asarray(ECEF_TRANSLATION, dtype=np.float32).astype(np.float64)
    assert float(np.max(np.abs(single - ECEF_TRANSLATION))) > 0.04


def test_blender_convention_maps_local_vertices_to_the_same_point(tmp_path: pathlib.Path) -> None:
    """``world @ (C @ v)`` must equal ``C @ (node @ v)`` for the returned matrix."""
    path = write_glb(tmp_path / "leaf.glb", leaf_document())
    world = mesh_node_matrices(path)[0]
    node = local_matrix(json_chunk(path)["nodes"][0])
    local = np.array([3.5, -12.25, 7.0, 1.0])
    assert np.allclose(world @ (YUP_TO_ZUP @ local), YUP_TO_ZUP @ (node @ local), rtol=0.0, atol=1e-9)


def test_translation_rotation_scale_nodes_compose_through_children(tmp_path: pathlib.Path) -> None:
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {"translation": list(ECEF_TRANSLATION), "children": [1]},
            {"rotation": [0.0, 0.0, 0.0, 1.0], "scale": [2.0, 2.0, 2.0], "translation": [1.0, 2.0, 3.0], "mesh": 0},
        ],
        "meshes": [{"primitives": []}],
    }
    path = write_glb(tmp_path / "tree.glb", document)
    world = mesh_node_matrices(path)[0]
    expected_gltf = np.asarray(ECEF_TRANSLATION) + np.array([1.0, 2.0, 3.0])
    assert np.allclose(world[:3, 3], YUP_TO_ZUP[:3, :3] @ expected_gltf, rtol=0.0, atol=1e-9)
    assert np.allclose(np.linalg.norm(world[:3, 0]), 2.0)


def test_a_node_cycle_does_not_hang(tmp_path: pathlib.Path) -> None:
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"children": [1]}, {"children": [0], "mesh": 0}],
        "meshes": [{"primitives": []}],
    }
    path = write_glb(tmp_path / "cycle.glb", document)
    assert len(mesh_node_matrices(path)) == 1

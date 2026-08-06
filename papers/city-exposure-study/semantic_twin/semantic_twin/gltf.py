"""Read binary glTF node placements in double precision.

Photorealistic 3D Tiles leaves carry their full ECEF placement in the glTF node
matrix, around 6.4e6 metres. Blender stores ``Object.matrix_world`` in single
precision, whose spacing at that magnitude is about 0.5 m, so every tile is
rounded independently on import and neighbouring tiles seam against each other.
Reading the node matrices straight out of the container keeps them exact.
"""

from __future__ import annotations

import json
import pathlib
import struct
from typing import Any

import numpy as np

GLTF_MAGIC = b"glTF"
GLTF_JSON_CHUNK = 0x4E4F534A

# Blender imports glTF y-up into its own z-up world, so a node's world matrix
# becomes ``YUP_TO_ZUP @ node @ YUP_TO_ZUP^-1`` and its mesh data arrives in
# ``YUP_TO_ZUP`` coordinates. Reproducing that is what lets the double-precision
# matrix stand in for the one Blender rounded.
YUP_TO_ZUP = np.array(
    [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, -1.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
)


def json_chunk(path: pathlib.Path) -> dict[str, Any]:
    """Return the JSON chunk of a binary glTF container."""
    payload = pathlib.Path(path).read_bytes()
    if len(payload) < 12 or payload[:4] != GLTF_MAGIC:
        raise ValueError(f"Not a binary glTF container: {path}")
    offset = 12
    while offset + 8 <= len(payload):
        chunk_length, chunk_type = struct.unpack_from("<II", payload, offset)
        offset += 8
        if chunk_type == GLTF_JSON_CHUNK:
            document = json.loads(payload[offset : offset + chunk_length])
            if not isinstance(document, dict):
                raise ValueError(f"glTF JSON chunk is not an object: {path}")
            return document
        offset += chunk_length
    raise ValueError(f"Binary glTF has no JSON chunk: {path}")


def local_matrix(node: dict[str, Any]) -> np.ndarray:
    """Return one glTF node's local matrix in double precision."""
    if "matrix" in node:
        values = np.asarray(node["matrix"], dtype=np.float64)
        if values.shape != (16,) or not np.all(np.isfinite(values)):
            raise ValueError("glTF node matrix must contain 16 finite numbers")
        return values.reshape((4, 4), order="F")

    matrix = np.eye(4)
    if "rotation" in node:
        values = np.asarray(node["rotation"], dtype=np.float64)
        if values.shape != (4,) or not np.all(np.isfinite(values)):
            raise ValueError("glTF node rotation must contain four finite numbers")
        x, y, z, w = values
        matrix[:3, :3] = np.array(
            [
                [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
                [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
                [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
            ]
        )
    if "scale" in node:
        matrix[:3, :3] = matrix[:3, :3] @ np.diag(np.asarray(node["scale"], dtype=np.float64))
    if "translation" in node:
        matrix[:3, 3] = np.asarray(node["translation"], dtype=np.float64)
    return matrix


def mesh_node_matrices(path: pathlib.Path) -> list[np.ndarray]:
    """Return the world matrix of every mesh-bearing node, in Blender's z-up frame."""
    document = json_chunk(path)
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError(f"glTF nodes must be a list: {path}")
    scenes = document.get("scenes", [])
    scene_index = int(document.get("scene", 0))
    if isinstance(scenes, list) and 0 <= scene_index < len(scenes):
        roots = [int(index) for index in scenes[scene_index].get("nodes", [])]
    else:
        roots = list(range(len(nodes)))

    inverse_conversion = YUP_TO_ZUP.T.copy()
    matrices: list[np.ndarray] = []
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
            matrices.append(YUP_TO_ZUP @ world @ inverse_conversion)
        for child in reversed([int(child) for child in node.get("children", [])]):
            stack.append((child, world))
    return matrices

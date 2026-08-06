"""Mesh and Sionna scene writers with no dependency on another twin pipeline."""

from __future__ import annotations

import pathlib
from html import escape

import numpy as np


def compact(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    used = np.unique(faces)
    remap = np.zeros(len(vertices), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return vertices[used], remap[faces]


def write_ply(path: pathlib.Path, vertices: np.ndarray, faces: np.ndarray) -> tuple[int, int]:
    """Write triangle geometry as binary little-endian PLY."""
    vertices = np.ascontiguousarray(vertices, dtype="<f4").reshape(-1, 3)
    faces = np.ascontiguousarray(faces, dtype="<i4").reshape(-1, 3)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment semantic_twin local ENU metres, z up\n"
        f"element vertex {len(vertices)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        f"element face {len(faces)}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    face_records = np.empty(len(faces), dtype=[("count", "u1"), ("indices", "<i4", (3,))])
    face_records["count"] = 3
    face_records["indices"] = faces
    with path.open("wb") as stream:
        stream.write(header.encode("ascii"))
        stream.write(vertices.tobytes())
        stream.write(face_records.tobytes())
    return len(vertices), len(faces)


def scene_xml(
    shapes: list[tuple[str, str, str]],
    *,
    comments: list[str] | tuple[str, ...] = (),
    thickness_m: float = 0.1,
) -> str:
    """Build a minimal Sionna RT XML scene."""
    materials = sorted({material for _, _, material in shapes})
    lines = ['<scene version="2.1.0">', ""]
    lines.extend(f"<!-- {escape(comment)} -->" for comment in comments)
    lines.extend(["", "<!-- Materials -->", ""])
    for material in materials:
        safe = escape(material)
        lines.extend(
            [
                f'  <bsdf type="itu-radio-material" id="mat-itu_{safe}">',
                f'    <string name="type" value="{safe}"/>',
                f'    <float name="thickness" value="{thickness_m}"/>',
                "  </bsdf>",
            ]
        )
    lines.extend(["", "<!-- Shapes -->", ""])
    for mesh_id, relative_path, material in shapes:
        mesh_id = escape(mesh_id)
        relative_path = escape(relative_path)
        material = escape(material)
        lines.extend(
            [
                f'  <shape type="ply" id="mesh-{mesh_id}" name="mesh-{mesh_id}">',
                f'    <string name="filename" value="{relative_path}"/>',
                '    <boolean name="face_normals" value="true"/>',
                f'    <ref id="mat-itu_{material}" name="bsdf"/>',
                "  </shape>",
            ]
        )
    lines.extend(["", "</scene>", ""])
    return "\n".join(lines)

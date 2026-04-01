"""Export EnvironmentMesh to DiffeRT, Sionna XML, and binary formats."""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.geo import enu_to_yup

if TYPE_CHECKING:
    pass


# RGB colors per material (for visualization and DiffeRT face_colors)
_MATERIAL_COLORS: dict[MaterialType, tuple[float, float, float]] = {
    MaterialType.CONCRETE: (0.6, 0.6, 0.6),
    MaterialType.BRICK: (0.7, 0.3, 0.2),
    MaterialType.GLASS: (0.5, 0.8, 0.9),
    MaterialType.METAL: (0.8, 0.8, 0.85),
    MaterialType.ASPHALT: (0.3, 0.3, 0.3),
    MaterialType.VEGETATION: (0.2, 0.6, 0.2),
    MaterialType.WATER: (0.1, 0.3, 0.8),
    MaterialType.WOOD: (0.55, 0.35, 0.15),
    MaterialType.GROUND: (0.5, 0.4, 0.3),
    MaterialType.UNKNOWN: (0.5, 0.5, 0.5),
    MaterialType.ROOF_TILE: (0.65, 0.35, 0.25),
    MaterialType.SOIL: (0.45, 0.35, 0.25),
    MaterialType.VEGETATION_DENSE: (0.15, 0.45, 0.1),
    MaterialType.PLASTER: (0.9, 0.87, 0.82),
}


def to_binary(mesh: EnvironmentMesh) -> tuple[bytes, dict]:
    """Serialize mesh to a compact binary blob plus metadata dict.

    Binary layout:
        float32 vertices (N*3) | uint32 triangles (M*3) | float32 normals (M*3) | uint8 materials (M)

    Vertices are transformed from ENU to Three.js Y-up before packing.
    """
    n_v = len(mesh.vertices)
    n_t = len(mesh.triangles)

    # Transform vertices for the frontend (Three.js Y-up)
    verts_yup = enu_to_yup(mesh.vertices).astype(np.float32)
    tris = mesh.triangles.astype(np.uint32)
    norms = enu_to_yup(mesh.normals).astype(np.float32)
    mats = mesh.materials.astype(np.uint8)

    blob = verts_yup.tobytes() + tris.tobytes() + norms.tobytes() + mats.tobytes()

    meta: dict = {
        "n_vertices": n_v,
        "n_triangles": n_t,
        "source": mesh.source,
        "origin_lat": mesh.origin_lat,
        "origin_lon": mesh.origin_lon,
    }
    return blob, meta


def to_differt_scene(mesh: EnvironmentMesh):
    """Convert EnvironmentMesh to a DiffeRT TriangleScene.

    Vertices stay in ENU (Z-up) which matches DiffeRT's coordinate convention.

    Requires ``differt`` to be installed (``pip install aegis[rt]``).
    """
    try:
        import jax.numpy as jnp
        from differt.geometry import TriangleMesh
        from differt.scene import TriangleScene
    except ImportError as exc:
        raise ImportError("DiffeRT is not installed. Install it with: pip install aegis[rt]") from exc

    # Build face colors array (n_triangles, 3)
    colors = np.array(
        [_MATERIAL_COLORS.get(MaterialType(int(m)), (0.5, 0.5, 0.5)) for m in mesh.materials],
        dtype=np.float32,
    )

    # Build per-face material names array (strings)
    mat_names = [MaterialType(int(m)).name.lower() for m in mesh.materials]

    # Unique material names for the scene
    unique_names = list(dict.fromkeys(mat_names))

    # object_bounds: one entry per unique object (treat each material group as an object)
    # DiffeRT expects (n_objects, 2) with [start, end] face indices
    # Group consecutive faces by material
    object_bounds = _compute_object_bounds(mesh.materials)

    # Material names tuple for TriangleMesh
    mat_names_tuple = tuple(unique_names)

    # Per-face material index (into unique_names list)
    name_to_idx = {n: i for i, n in enumerate(unique_names)}
    face_materials = jnp.array([name_to_idx[n] for n in mat_names], dtype=jnp.int32)

    tri_mesh = TriangleMesh(
        vertices=jnp.array(mesh.vertices, dtype=jnp.float32),
        triangles=jnp.array(mesh.triangles, dtype=jnp.int32),
        face_colors=jnp.array(colors),
        face_materials=face_materials,
        material_names=mat_names_tuple,
        object_bounds=jnp.array(object_bounds, dtype=jnp.int32),
    )

    scene = TriangleScene(mesh=tri_mesh)
    return scene


def to_sionna_mesh_data(mesh: EnvironmentMesh) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract (vertices, triangles, per_face_material_names) for Sionna RT.

    Returns vertices in ENU (Z-up), triangles as int indices, and a list of
    material name strings (one per face) matching Sionna BSDF names.
    """
    verts = mesh.vertices.astype(np.float32)
    tris = mesh.triangles.astype(np.int32)
    per_face_mats = [MaterialType(int(m)).name.lower() for m in mesh.materials]
    return verts, tris, per_face_mats


def _compute_object_bounds(materials: np.ndarray) -> np.ndarray:
    """Compute [start, end) face index ranges per contiguous material block."""
    if len(materials) == 0:
        return np.zeros((0, 2), dtype=np.int32)
    bounds = []
    start = 0
    current = int(materials[0])
    for i in range(1, len(materials)):
        if int(materials[i]) != current:
            bounds.append([start, i])
            start = i
            current = int(materials[i])
    bounds.append([start, len(materials)])
    return np.array(bounds, dtype=np.int32)


def to_sionna_xml(mesh: EnvironmentMesh, path: Path | str) -> Path:
    """Write a Mitsuba-format XML scene file for Sionna RT.

    One PLY file per material group is written alongside the XML.  The PLY
    files use binary little-endian encoding and contain vertex positions plus
    face indices.

    Args:
        mesh: Source environment mesh (ENU coordinates).
        path: Output path for the ``.xml`` file. Sibling ``.ply`` files are
            written to the same directory.

    Returns:
        Path to the written XML file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Group triangles by material
    groups: dict[int, list[int]] = {}
    for i, mat in enumerate(mesh.materials):
        groups.setdefault(int(mat), []).append(i)

    # Build XML tree
    scene_el = ET.Element("scene", version="2.1.0")

    for mat_id, face_indices in groups.items():
        mat_type = MaterialType(mat_id)
        mat_name = mat_type.name.lower()
        ply_name = f"{path.stem}_{mat_name}.ply"
        ply_path = path.parent / ply_name

        # Collect vertex subset for this material group
        tri_indices = np.array(face_indices, dtype=np.uint32)
        local_tris = mesh.triangles[tri_indices]  # (K, 3)

        # Remap vertices to a compact local index set
        unique_verts, inv = np.unique(local_tris.ravel(), return_inverse=True)
        local_verts = mesh.vertices[unique_verts].astype(np.float32)
        remapped_tris = inv.reshape(-1, 3).astype(np.uint32)

        _write_ply(ply_path, local_verts, remapped_tris)

        # XML shape element
        shape_el = ET.SubElement(scene_el, "shape", type="ply", id=f"mesh_{mat_name}")
        ET.SubElement(shape_el, "string", name="filename", value=ply_name)

        # BSDF reference
        bsdf_el = ET.SubElement(shape_el, "bsdf", type="diffuse", id=f"bsdf_{mat_name}")
        r, g, b = _MATERIAL_COLORS[mat_type]
        ET.SubElement(
            bsdf_el,
            "rgb",
            name="reflectance",
            value=f"{r:.3f} {g:.3f} {b:.3f}",
        )

    # Write XML with declaration
    tree = ET.ElementTree(scene_el)
    ET.indent(tree, space="    ")
    xml_bytes = ET.tostring(scene_el, encoding="unicode", xml_declaration=False)
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes + "\n")
    return path


def _write_ply(path: Path, vertices: np.ndarray, triangles: np.ndarray) -> None:
    """Write binary little-endian PLY file."""
    n_v = len(vertices)
    n_f = len(triangles)

    header_lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"element vertex {n_v}",
        "property float x",
        "property float y",
        "property float z",
        f"element face {n_f}",
        "property list uchar uint vertex_indices",
        "end_header",
    ]
    header = "\n".join(header_lines) + "\n"

    # Vertex data: packed float32 xyz
    vert_bytes = vertices.astype(np.float32).tobytes()

    # Face data: uchar count (3) + 3 x uint32
    face_parts = []
    for tri in triangles:
        face_parts.append(struct.pack("<B", 3))
        face_parts.append(struct.pack("<III", int(tri[0]), int(tri[1]), int(tri[2])))
    face_bytes = b"".join(face_parts)

    path.write_bytes(header.encode("ascii") + vert_bytes + face_bytes)

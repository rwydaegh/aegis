"""Natural feature geometry for forests, parks, and hedges.

Generates 3D triangle meshes for vegetation features used in RF ray tracing.
All functions return (vertices, triangles, materials) numpy arrays compatible
with EnvironmentMesh.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.environment import MaterialType
from aegis.environment.roofs import extrude_walls, triangulate_polygon


@dataclass
class NaturalFeature:
    """A natural geographic feature with a 2D footprint."""

    way_id: int
    footprint: np.ndarray  # (N, 2) local XY coords
    feature_type: str  # "forest", "park", "hedge", etc.


def generate_forest_canopy(
    footprint: np.ndarray,
    canopy_height: float = 8.0,
    canopy_base: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate an extruded volume representing a forest canopy.

    The canopy is modelled as a closed solid with a bottom face at canopy_base,
    a top face at canopy_height, and vertical walls connecting them.

    Args:
        footprint: (N, 2) array of 2D footprint vertices.
        canopy_height: Z coordinate of the top of the canopy.
        canopy_base: Z coordinate of the bottom of the canopy.

    Returns:
        (vertices, triangles, materials) where vertices is (V, 3) float64,
        triangles is (T, 3) uint32, and materials is (T,) uint8.
    """
    fp = np.asarray(footprint, dtype=np.float64)

    # Bottom face at canopy_base
    bottom_tris_local = triangulate_polygon(fp)
    n_bottom = len(fp)
    bottom_verts = np.column_stack([fp, np.full(n_bottom, canopy_base)])

    # Top face at canopy_height (flip winding for outward normals)
    top_verts = np.column_stack([fp, np.full(n_bottom, canopy_height)])
    top_offset = n_bottom
    top_tris_local = bottom_tris_local[:, ::-1] + top_offset

    # Walls from canopy_base to canopy_height
    wall_verts, wall_tris_local = extrude_walls(fp, canopy_base, canopy_height)
    wall_offset = 2 * n_bottom
    wall_tris = wall_tris_local + wall_offset

    all_verts = np.concatenate([bottom_verts, top_verts, wall_verts], axis=0)
    all_tris = np.concatenate([bottom_tris_local, top_tris_local, wall_tris], axis=0)
    mats = np.full(len(all_tris), int(MaterialType.VEGETATION_DENSE), dtype=np.uint8)

    return all_verts, all_tris.astype(np.uint32), mats


def generate_ground_plane(
    footprint: np.ndarray,
    z: float = 0.0,
    material: MaterialType = MaterialType.VEGETATION,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a flat triangulated polygon at a given height.

    Suitable for parks, grass areas, and other flat natural features.

    Args:
        footprint: (N, 2) array of 2D footprint vertices.
        z: Z coordinate of the ground plane.
        material: Material type to assign to all faces.

    Returns:
        (vertices, triangles, materials) where vertices is (V, 3) float64,
        triangles is (T, 3) uint32, and materials is (T,) uint8.
    """
    fp = np.asarray(footprint, dtype=np.float64)
    tris = triangulate_polygon(fp)
    verts = np.column_stack([fp, np.full(len(fp), z)])
    mats = np.full(len(tris), int(material), dtype=np.uint8)
    return verts, tris.astype(np.uint32), mats


def generate_hedge(
    centerline: np.ndarray,
    height: float = 2.0,
    width: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate geometry for a hedge along a centerline.

    Each segment of the centerline produces a rectangular box: front wall,
    back wall, left cap, right cap, and top face.

    Args:
        centerline: (N, 2) array of centerline points in XY.
        height: Height of the hedge (z=0 to z=height).
        width: Total width of the hedge (half-width offset on each side).

    Returns:
        (vertices, triangles, materials) where vertices is (V, 3) float64,
        triangles is (T, 3) uint32, and materials is (T,) uint8.
    """
    cl = np.asarray(centerline, dtype=np.float64)
    half = width / 2.0

    all_verts: list[np.ndarray] = []
    all_tris: list[np.ndarray] = []

    def _add_quad(v0, v1, v2, v3):
        """Add two triangles for a quad (v0, v1, v2, v3 in order)."""
        base = sum(len(v) for v in all_verts)
        all_verts.append(np.array([v0, v1, v2, v3], dtype=np.float64))
        all_tris.append(np.array([[base, base + 1, base + 2], [base, base + 2, base + 3]], dtype=np.uint32))

    for i in range(len(cl) - 1):
        p0 = cl[i]
        p1 = cl[i + 1]
        seg = p1 - p0
        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-9:
            continue
        # Perpendicular unit vector (rotate 90 degrees CCW)
        perp = np.array([-seg[1], seg[0]]) / seg_len

        # Offset corners in XY
        a0 = p0 + perp * half  # front bottom start
        a1 = p1 + perp * half  # front bottom end
        b0 = p0 - perp * half  # back bottom start
        b1 = p1 - perp * half  # back bottom end

        def xyz(xy, z):
            return [xy[0], xy[1], z]

        # Front wall (perp side +)
        _add_quad(
            xyz(a0, 0.0),
            xyz(a1, 0.0),
            xyz(a1, height),
            xyz(a0, height),
        )
        # Back wall (perp side -)
        _add_quad(
            xyz(b1, 0.0),
            xyz(b0, 0.0),
            xyz(b0, height),
            xyz(b1, height),
        )
        # Left cap
        _add_quad(
            xyz(b0, 0.0),
            xyz(a0, 0.0),
            xyz(a0, height),
            xyz(b0, height),
        )
        # Right cap
        _add_quad(
            xyz(a1, 0.0),
            xyz(b1, 0.0),
            xyz(b1, height),
            xyz(a1, height),
        )
        # Top face
        _add_quad(
            xyz(a0, height),
            xyz(a1, height),
            xyz(b1, height),
            xyz(b0, height),
        )

    if not all_verts:
        empty_v = np.empty((0, 3), dtype=np.float64)
        empty_t = np.empty((0, 3), dtype=np.uint32)
        empty_m = np.empty((0,), dtype=np.uint8)
        return empty_v, empty_t, empty_m

    verts = np.concatenate(all_verts, axis=0)
    tris = np.concatenate(all_tris, axis=0)
    mats = np.full(len(tris), int(MaterialType.VEGETATION_DENSE), dtype=np.uint8)

    return verts, tris, mats

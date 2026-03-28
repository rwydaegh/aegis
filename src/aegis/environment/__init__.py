"""Unified environment mesh for AEGIS ray tracing and visualization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np


class MaterialType(IntEnum):
    CONCRETE = 0
    BRICK = 1
    GLASS = 2
    METAL = 3
    ASPHALT = 4
    VEGETATION = 5
    WATER = 6
    WOOD = 7
    GROUND = 8
    UNKNOWN = 9


MATERIAL_EM_PROPERTIES: dict[MaterialType, dict[str, float]] = {
    MaterialType.CONCRETE: {"eps_r": 5.31, "sigma": 0.0326},
    MaterialType.BRICK: {"eps_r": 3.75, "sigma": 0.038},
    MaterialType.GLASS: {"eps_r": 6.27, "sigma": 0.0043},
    MaterialType.METAL: {"eps_r": 1.0, "sigma": 1e7},
    MaterialType.ASPHALT: {"eps_r": 3.18, "sigma": 0.0},
    MaterialType.VEGETATION: {"eps_r": 1.0, "sigma": 0.0},
    MaterialType.WATER: {"eps_r": 81.0, "sigma": 0.01},
    MaterialType.WOOD: {"eps_r": 1.99, "sigma": 0.0047},
    MaterialType.GROUND: {"eps_r": 15.0, "sigma": 0.035},
    MaterialType.UNKNOWN: {"eps_r": 5.31, "sigma": 0.0326},
}


@dataclass
class EnvironmentMesh:
    vertices: np.ndarray
    triangles: np.ndarray
    normals: np.ndarray
    materials: np.ndarray
    origin_lat: float
    origin_lon: float
    source: str

    def to_differt_scene(self):
        """Return a DiffeRT TriangleScene. Requires ``pip install aegis[rt]``."""
        from aegis.environment.export import to_differt_scene

        return to_differt_scene(self)

    def to_sionna_xml(self, path: Path | str) -> Path:
        """Write a Mitsuba-format XML scene for Sionna RT and return the path."""
        from aegis.environment.export import to_sionna_xml

        return to_sionna_xml(self, Path(path))

    def to_binary(self) -> tuple[bytes, dict]:
        """Serialize to a compact binary blob and metadata dict."""
        from aegis.environment.export import to_binary

        return to_binary(self)

    @classmethod
    def from_voxels(cls, positions, materials, voxel_size):
        """Convert voxel data to EnvironmentMesh by generating cube faces."""
        from aegis.environment.osm import _compute_face_normals

        n = len(positions)
        half = voxel_size / 2
        offsets = (
            np.array(
                [
                    [-1, -1, -1],
                    [-1, -1, 1],
                    [-1, 1, -1],
                    [-1, 1, 1],
                    [1, -1, -1],
                    [1, -1, 1],
                    [1, 1, -1],
                    [1, 1, 1],
                ],
                dtype=np.float64,
            )
            * half
        )
        cube_tris = np.array(
            [
                [0, 2, 6],
                [0, 6, 4],
                [1, 5, 7],
                [1, 7, 3],
                [0, 1, 3],
                [0, 3, 2],
                [4, 6, 7],
                [4, 7, 5],
                [0, 4, 5],
                [0, 5, 1],
                [2, 3, 7],
                [2, 7, 6],
            ],
            dtype=np.uint32,
        )

        all_verts = np.repeat(np.asarray(positions, dtype=np.float64), 8, axis=0).reshape(n, 8, 3) + offsets
        all_verts = all_verts.reshape(-1, 3)
        all_tris = np.tile(cube_tris, (n, 1, 1))
        for i in range(n):
            all_tris[i] += i * 8
        all_tris = all_tris.reshape(-1, 3)

        mat_array = (
            np.repeat(np.array(materials, dtype=np.uint8), 12)
            if len(materials) == n
            else np.full(n * 12, MaterialType.CONCRETE, dtype=np.uint8)
        )

        normals = _compute_face_normals(all_verts, all_tris)

        return cls(
            vertices=all_verts,
            triangles=all_tris,
            normals=normals,
            materials=mat_array,
            origin_lat=0.0,
            origin_lon=0.0,
            source="voxels",
        )

    @classmethod
    def from_osm(cls, lat, lon, radius_m, **kwargs):
        """Fetch OSM data and build environment mesh."""
        from aegis.environment.osm import build_environment_from_osm, fetch_osm

        xml = fetch_osm(lat, lon, radius_m)
        return build_environment_from_osm(xml, origin_lat=lat, origin_lon=lon, **kwargs)

    @classmethod
    def from_3dtiles(cls, lat, lon, radius_m, geometric_error=30.0, api_key=None):
        """Fetch 3D Tiles and build environment mesh."""
        import os

        from aegis.environment.tiles import TileTraverser

        key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        traverser = TileTraverser(
            root_url="https://tile.googleapis.com/v1/3dtiles/root.json",
            api_key=key,
            geometric_error=geometric_error,
        )
        return traverser.traverse(lat, lon, radius_m)

    @classmethod
    def combine(cls, *meshes: EnvironmentMesh) -> EnvironmentMesh:
        if not meshes:
            raise ValueError("At least one mesh required")
        origin_lat = meshes[0].origin_lat
        origin_lon = meshes[0].origin_lon
        for m in meshes[1:]:
            if abs(m.origin_lat - origin_lat) > 1e-6 or abs(m.origin_lon - origin_lon) > 1e-6:
                raise ValueError(
                    f"All meshes must share the same origin. "
                    f"Got ({origin_lat}, {origin_lon}) and ({m.origin_lat}, {m.origin_lon})"
                )
        vert_offset = 0
        all_verts, all_tris, all_normals, all_mats = [], [], [], []
        for m in meshes:
            all_verts.append(m.vertices)
            all_tris.append(m.triangles + vert_offset)
            all_normals.append(m.normals)
            all_mats.append(m.materials)
            vert_offset += len(m.vertices)
        return cls(
            vertices=np.concatenate(all_verts),
            triangles=np.concatenate(all_tris),
            normals=np.concatenate(all_normals),
            materials=np.concatenate(all_mats),
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            source="combined",
        )

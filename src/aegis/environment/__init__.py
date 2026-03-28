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

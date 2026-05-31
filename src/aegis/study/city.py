"""City mesh build, cache, and rooftop site candidates.

Fetches OSM once and feeds it to both the mesh builder and the building parser,
so the triangle mesh, the Sionna scene, and the rooftop candidates all share one
origin and one frame. The mesh is exported to a Sionna XML scene for the
deterministic ray-tracing arm.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.environment import EnvironmentMesh


def rooftop_candidates(buildings) -> np.ndarray:
    """Candidate site points: footprint centroid at the building eave height.

    Returns an ``(K, 3)`` array. The z coordinate is ``building.height``, the
    eave/parapet height, where rooftop antennas mount. ``roof_height`` (the
    roof's own peak extent above the eave) is deliberately excluded.
    """
    pts = []
    for b in buildings:
        fp = np.asarray(b.footprint, dtype=float)
        if fp.shape[0] < 3:
            continue
        centroid = fp.mean(axis=0)
        pts.append([centroid[0], centroid[1], float(b.height)])
    if not pts:
        return np.zeros((0, 3))
    return np.asarray(pts)


@dataclass
class CityCache:
    """A built city: mesh, exported Sionna scene, and rooftop candidates."""

    mesh: EnvironmentMesh
    scene_xml: Path
    candidates: np.ndarray
    origin_lat: float
    origin_lon: float
    _differt_scene: object = None

    @property
    def differt_scene(self):
        """In-memory DiffeRT TriangleScene for the deterministic arm.

        Built once and reused. The deterministic ray tracer uses this rather
        than re-parsing the Sionna XML, which differt_core's loader rejects.
        """
        if self._differt_scene is None:
            self._differt_scene = self.mesh.to_differt_scene()
        return self._differt_scene

    @classmethod
    def build(cls, lat: float, lon: float, radius_m: float, cache_dir: Path) -> CityCache:
        from aegis.environment.osm import (
            build_environment_from_osm,
            fetch_osm,
            parse_osm_xml,
        )

        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        xml = fetch_osm(lat, lon, radius_m)
        mesh = build_environment_from_osm(xml, origin_lat=lat, origin_lon=lon)
        buildings, _, _ = parse_osm_xml(xml, origin_lat=lat, origin_lon=lon)

        scene_xml = cache_dir / "scene.xml"
        if not scene_xml.exists():
            mesh.to_sionna_xml(scene_xml)

        return cls(
            mesh=mesh,
            scene_xml=scene_xml,
            candidates=rooftop_candidates(buildings),
            origin_lat=mesh.origin_lat,
            origin_lon=mesh.origin_lon,
        )

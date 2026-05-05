"""Brussels Grand Place scene cache.

The plaza geometry doesn't change between runs; we scrape Overpass once,
persist ``osm.xml``, ``mesh.npz``, and ``scene_hash.txt`` to
``data/scenes/brussels_grand_place/``, and load from cache on subsequent
runs. Reproducibility: the hash pins the scrape parameters so changing
radius / detail invalidates automatically.

Brussels Grand Place center: lat = 50.8467, lon = 4.3525 (Grote Markt /
Grand-Place de Bruxelles, Brussels, Belgium).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.environment import EnvironmentMesh
from aegis.environment.osm import build_environment_from_osm, fetch_osm

logger = logging.getLogger(__name__)

GRAND_PLACE_LAT = 50.8467
GRAND_PLACE_LON = 4.3525
DEFAULT_RADIUS_M = 80.0
DEFAULT_BUILDING_HEIGHT_M = 18.0  # plaza-fronting facades are ~15-22 m
DEFAULT_DETAIL = False  # facades=False keeps the geometry compact for RT

DEFAULT_CACHE_DIR = Path("data/scenes/brussels_grand_place")


@dataclass(frozen=True)
class ScrapeSpec:
    lat: float = GRAND_PLACE_LAT
    lon: float = GRAND_PLACE_LON
    radius_m: float = DEFAULT_RADIUS_M
    default_height_m: float = DEFAULT_BUILDING_HEIGHT_M
    detail: bool = DEFAULT_DETAIL

    def hash(self) -> str:
        s = f"{self.lat:.6f}|{self.lon:.6f}|{self.radius_m:.2f}|{self.default_height_m:.2f}|{int(self.detail)}"
        return hashlib.sha256(s.encode()).hexdigest()[:16]


def _save_mesh(mesh: EnvironmentMesh, path: Path) -> None:
    np.savez_compressed(
        path,
        vertices=mesh.vertices.astype(np.float32),
        triangles=mesh.triangles.astype(np.uint32),
        normals=mesh.normals.astype(np.float32),
        materials=mesh.materials.astype(np.uint8),
        origin_lat=np.float64(mesh.origin_lat),
        origin_lon=np.float64(mesh.origin_lon),
        source=np.array(mesh.source),
    )


def _load_mesh(path: Path) -> EnvironmentMesh:
    with np.load(path, allow_pickle=False) as f:
        return EnvironmentMesh(
            vertices=np.asarray(f["vertices"], dtype=np.float64),
            triangles=np.asarray(f["triangles"], dtype=np.uint32),
            normals=np.asarray(f["normals"], dtype=np.float64),
            materials=np.asarray(f["materials"], dtype=np.uint8),
            origin_lat=float(f["origin_lat"]),
            origin_lon=float(f["origin_lon"]),
            source=str(f["source"]),
        )


def load_or_scrape(
    spec: ScrapeSpec | None = None,
    cache_dir: Path | str | None = None,
    *,
    force_refresh: bool = False,
) -> tuple[EnvironmentMesh, str]:
    """Return ``(mesh, scene_hash)``. Hits cache when the spec hash matches."""
    spec = spec or ScrapeSpec()
    cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    hash_path = cache_dir / "scene_hash.txt"
    xml_path = cache_dir / "osm.xml"
    mesh_path = cache_dir / "mesh.npz"

    scene_hash = spec.hash()

    if (
        not force_refresh
        and hash_path.exists()
        and xml_path.exists()
        and mesh_path.exists()
        and hash_path.read_text().strip() == scene_hash
    ):
        logger.info("Scene cache hit: %s (hash=%s)", cache_dir, scene_hash)
        return _load_mesh(mesh_path), scene_hash

    logger.info("Scene cache miss; scraping Overpass at (%.4f, %.4f) r=%dm", spec.lat, spec.lon, spec.radius_m)
    xml = fetch_osm(spec.lat, spec.lon, radius_m=spec.radius_m)
    xml_path.write_text(xml)

    mesh = build_environment_from_osm(
        xml,
        origin_lat=spec.lat,
        origin_lon=spec.lon,
        default_building_height=spec.default_height_m,
        detail=spec.detail,
    )
    _save_mesh(mesh, mesh_path)
    hash_path.write_text(scene_hash)
    logger.info(
        "Scene cached: %d verts, %d tris -> %s",
        mesh.vertices.shape[0],
        mesh.triangles.shape[0],
        cache_dir,
    )
    return mesh, scene_hash

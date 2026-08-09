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


def _interior_point(fp: np.ndarray) -> np.ndarray | None:
    """A point guaranteed inside the footprint polygon (XY).

    The vertex mean lands outside concave/L-shaped or edge-truncated footprints
    (12/232 buildings on the Ghent core), which put base-station markers in
    mid-air over streets. Use the shoelace centroid when it is inside, else the
    interior grid point farthest from the boundary (a cheap pole of
    inaccessibility).
    """
    from matplotlib.path import Path as _MplPath

    fp = np.asarray(fp, dtype=float)[:, :2]
    path = _MplPath(fp)

    x, y = fp[:, 0], fp[:, 1]
    xr, yr = np.roll(x, -1), np.roll(y, -1)
    cross = x * yr - xr * y
    area2 = cross.sum()
    if abs(area2) > 1e-9:
        centroid = np.array([((x + xr) * cross).sum(), ((y + yr) * cross).sum()]) / (3.0 * area2)
        if path.contains_point(centroid):
            return centroid

    lo, hi = fp.min(axis=0), fp.max(axis=0)
    gx, gy = np.meshgrid(np.linspace(lo[0], hi[0], 14)[1:-1], np.linspace(lo[1], hi[1], 14)[1:-1])
    grid = np.column_stack([gx.ravel(), gy.ravel()])
    inside = grid[path.contains_points(grid)]
    if inside.shape[0] == 0:
        return None
    # distance of each inside point to the nearest polygon edge
    a, b = fp, np.roll(fp, -1, axis=0)
    ab = b - a  # (E, 2)
    ap = inside[:, None, :] - a[None, :, :]  # (P, E, 2)
    tt = np.clip(np.einsum("pej,ej->pe", ap, ab) / np.maximum((ab**2).sum(axis=1), 1e-12), 0.0, 1.0)
    closest = a[None, :, :] + tt[:, :, None] * ab[None, :, :]
    d = np.linalg.norm(inside[:, None, :] - closest, axis=2).min(axis=1)
    return inside[np.argmax(d)]


def _roof_z_at(mesh, xy: np.ndarray) -> float | None:
    """Highest mesh surface directly above/below the XY point (vertical ray).

    Pure-numpy point-in-triangle on the XY projection: the roof the rays
    actually bounce off, independent of what the OSM height tag claimed.
    """
    v = np.asarray(mesh.vertices, dtype=float)
    t = np.asarray(mesh.triangles, dtype=int)
    tri = v[t]  # (T, 3, 3)
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    d = np.asarray(xy, dtype=float)

    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(det) > 1e-12
    if not np.any(ok):
        return None
    a, b, c, det = a[ok], b[ok], c[ok], det[ok]
    l1 = ((b[:, 1] - c[:, 1]) * (d[0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (d[1] - c[:, 1])) / det
    l2 = ((c[:, 1] - a[:, 1]) * (d[0] - c[:, 0]) + (a[:, 0] - c[:, 0]) * (d[1] - c[:, 1])) / det
    l3 = 1.0 - l1 - l2
    eps = -1e-9
    hit = (l1 >= eps) & (l2 >= eps) & (l3 >= eps)
    if not np.any(hit):
        return None
    z = l1[hit] * a[hit, 2] + l2[hit] * b[hit, 2] + l3[hit] * c[hit, 2]
    return float(z.max())


def rooftop_candidates(buildings, mesh=None) -> np.ndarray:
    """Candidate site points: an interior rooftop point per building.

    Returns an ``(K, 3)`` array. XY is a point guaranteed inside the footprint
    (not the vertex mean, which floats off concave buildings). When ``mesh`` is
    given, z is snapped to the actual mesh roof under that point, so candidates
    can never hover above (or hide below) the geometry the rays bounce off;
    otherwise z falls back to the parsed eave height ``building.height``.
    ``roof_height`` (the roof's own peak above the eave) stays excluded: rooftop
    antennas mount at the parapet, not the roof peak.
    """
    pts = []
    for b in buildings:
        fp = np.asarray(b.footprint, dtype=float)
        if fp.shape[0] < 3:
            continue
        xy = _interior_point(fp)
        if xy is None:
            continue
        if mesh is not None:
            z = _roof_z_at(mesh, xy)
            # No surface under the point means the builder dropped this
            # building from the traced mesh. Trusting the parsed tag here would
            # recreate a mast floating in empty air, so skip the candidate.
            if z is None:
                continue
        else:
            z = float(b.height)
        pts.append([xy[0], xy[1], z])
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
    _sionna_scene: object = None

    @property
    def differt_scene(self):
        """In-memory DiffeRT TriangleScene for the deterministic arm.

        Built once and reused. The deterministic ray tracer uses this rather
        than re-parsing the Sionna XML, which differt_core's loader rejects.
        """
        if self._differt_scene is None:
            self._differt_scene = self.mesh.to_differt_scene()
        return self._differt_scene

    def _mesh_tag(self) -> str:
        import hashlib

        return hashlib.sha256(np.asarray(self.mesh.vertices, dtype=float).tobytes()).hexdigest()[:16]

    def _export(self, path: Path, *, radio: bool) -> None:
        """Export the mesh to a Sionna XML, guarded by a mesh-content hash so a
        stale export (older snapshot, older builder) is never traced against the
        current mesh silently."""
        tag_file = path.with_suffix(".hash")
        tag = self._mesh_tag()
        if path.exists() and tag_file.exists() and tag_file.read_text(encoding="utf-8") == tag:
            return
        self.mesh.to_sionna_xml(path, radio_materials=True) if radio else self.mesh.to_sionna_xml(path)
        tag_file.write_text(tag, encoding="utf-8")

    @property
    def sionna_scene(self):
        """Sionna RT scene for the deterministic arm (default engine).

        Exports a radio-material Mitsuba XML (ITU material ids) and loads it
        once. Sionna RT runs on CPU via Dr.Jit and auto-uses a GPU when present.
        """
        if self._sionna_scene is None:
            import sionna.rt as srt

            radio_xml = self.scene_xml.with_name(self.scene_xml.stem + "_radio.xml")
            self._export(radio_xml, radio=True)
            scene = srt.load_scene(str(radio_xml))
            self._sionna_scene = scene
        return self._sionna_scene

    @classmethod
    def build(cls, lat: float, lon: float, radius_m: float, cache_dir: Path) -> CityCache:
        from aegis.environment.osm import (
            build_environment_from_osm,
            fetch_osm,
            parse_osm_xml,
        )

        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache the raw Overpass snapshot: repeat runs are offline-reproducible
        # and mesh, candidates, and traced scene always derive from one snapshot.
        osm_path = cache_dir / "osm.xml"
        if osm_path.exists():
            xml = osm_path.read_text(encoding="utf-8")
        else:
            xml = fetch_osm(lat, lon, radius_m)
            osm_path.write_text(xml, encoding="utf-8")
        # Ground disk past the analysis radius: the street-level ground bounce
        # is a first-order path at 28 GHz and OSM only meshes road ribbons.
        mesh = build_environment_from_osm(xml, origin_lat=lat, origin_lon=lon, ground_radius_m=1.5 * float(radius_m))
        buildings, _, _ = parse_osm_xml(xml, origin_lat=lat, origin_lon=lon)

        city = cls(
            mesh=mesh,
            scene_xml=cache_dir / "scene.xml",
            candidates=rooftop_candidates(buildings, mesh=mesh),
            origin_lat=mesh.origin_lat,
            origin_lon=mesh.origin_lon,
        )
        city._export(city.scene_xml, radio=False)
        return city

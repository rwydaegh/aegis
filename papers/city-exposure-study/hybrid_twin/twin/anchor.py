"""Layer 0: everything measured.

Nothing in this module is invented. Footprints, heights, ground level, road
centrelines, water and the real positions of mapped trees and bollards all come
from OSM, from the Google-tiles height arbitration in `decisions.json`, or from the
filtered terrain grid. The generative layers sit on top of this and are never
allowed to move it.

Runs under the venv and inside `blender -b` alike, so the same anchor feeds the
scene build and the QA checks.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import numpy as np

from .geo import Frame

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Ways we will drive clutter along, by OSM highway class.
CARRIAGEWAY = {"living_street", "residential", "tertiary", "secondary", "service",
               "unclassified"}
WALKWAY = {"pedestrian", "footway", "path", "steps"}


@dataclass
class Building:
    osm_id: int
    ring: np.ndarray          # (N, 2) ENU metres, open (no repeated last point)
    ground_z: float
    height: float
    decision: str             # how the height was arrived at
    tags: dict = field(default_factory=dict)

    @property
    def top_z(self) -> float:
        return self.ground_z + self.height

    @property
    def centroid(self) -> np.ndarray:
        return self.ring.mean(axis=0)

    @property
    def area(self) -> float:
        x, y = self.ring[:, 0], self.ring[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    def material_tag(self) -> str | None:
        """OSM's own answer, where a mapper bothered. Ground truth, not a guess."""
        return self.tags.get("building:material")


@dataclass
class Way:
    osm_id: int
    line: np.ndarray          # (N, 2) ENU metres
    tags: dict

    @property
    def kind(self) -> str:
        t = self.tags
        if t.get("natural") == "water":
            return "water"          # a surface polygon
        if "waterway" in t:
            return "waterline"      # a centreline, never a surface
        if t.get("man_made") == "quay":
            return "quay"
        if t.get("highway") in CARRIAGEWAY:
            return "carriageway"
        if t.get("highway") in WALKWAY:
            return "walkway"
        if "barrier" in t:
            return "barrier"
        if t.get("leisure") == "park" or t.get("landuse") in {"grass", "forest"}:
            return "green"
        return "other"

    @property
    def length(self) -> float:
        d = np.diff(self.line, axis=0)
        return float(np.hypot(d[:, 0], d[:, 1]).sum()) if len(d) else 0.0

    @property
    def car_access(self) -> str:
        """Whether general motor traffic may be here: `free`, `destination`, `none`.

        This block is the Ghent pedestrian core, and OSM says so explicitly: 128 of
        its 129 `living_street` ways carry `vehicle=private`. A parking rule that
        keys only on `highway` fills a medieval square with a thousand cars.
        """
        t = self.tags
        if t.get("highway") in WALKWAY:
            return "none"
        for key in ("access", "vehicle", "motor_vehicle"):
            v = t.get(key)
            if v in {"no", "private", "permit"}:
                return "none"
            if v == "destination":
                return "destination"
        if t.get("highway") == "service" and t.get("service") in {"driveway"}:
            return "destination"
        return "free"

    @property
    def surface(self) -> str | None:
        """OSM's paving class. `sett` is cobble, which matters at grazing incidence."""
        return self.tags.get("surface")


@dataclass
class Point:
    osm_id: int
    xy: np.ndarray
    tags: dict

    @property
    def kind(self) -> str:
        t = self.tags
        if t.get("natural") == "tree":
            return "tree"
        if t.get("highway") == "street_lamp":
            return "lamp"
        if t.get("barrier") == "bollard":
            return "bollard"
        if t.get("amenity") in {"restaurant", "cafe", "pub", "bar"}:
            return "hospitality"
        return t.get("amenity") or "other"


@dataclass
class Terrain:
    x0: float
    step: float
    n: int
    z: np.ndarray             # (n, n)

    def at(self, x: float, y: float) -> float:
        """Bilinear sample, clamped at the edges."""
        fx = np.clip((x - self.x0) / self.step, 0, self.n - 1.001)
        fy = np.clip((y - self.x0) / self.step, 0, self.n - 1.001)
        i, j = int(fx), int(fy)
        tx, ty = fx - i, fy - j
        z = self.z
        return float(
            z[j, i] * (1 - tx) * (1 - ty) + z[j, i + 1] * tx * (1 - ty)
            + z[j + 1, i] * (1 - tx) * ty + z[j + 1, i + 1] * tx * ty
        )


@dataclass
class Anchor:
    frame: Frame
    buildings: list[Building]
    ways: list[Way]
    points: list[Point]
    terrain: Terrain
    ground_global: float

    def by_id(self, osm_id: int | str) -> Building | None:
        key = int(osm_id)
        return next((b for b in self.buildings if b.osm_id == key), None)

    def ways_of(self, kind: str) -> list[Way]:
        return [w for w in self.ways if w.kind == kind]

    def points_of(self, kind: str) -> list[Point]:
        return [p for p in self.points if p.kind == kind]

    def near(self, xy, radius: float) -> list[Building]:
        c = np.asarray(xy, dtype=float)
        return [b for b in self.buildings
                if np.linalg.norm(b.centroid - c) <= radius]


def load(data_dir: pathlib.Path | None = None) -> Anchor:
    """Read every measured input into one object. No network, no Blender."""
    d = pathlib.Path(data_dir) if data_dir else DATA

    osm = json.loads((d / "osm_buildings.json").read_text())
    frame = Frame(osm["lat"], osm["lon"], 0.0)

    dec_doc = json.loads((d / "decisions.json").read_text())
    dec = {int(r["id"]): r for r in dec_doc["decisions"]}
    ground_global = float(dec_doc["ground_global"])

    buildings = []
    for b in osm["buildings"]:
        rec = dec.get(int(b["id"]))
        if rec is None:
            continue
        ring = frame.ring_to_enu(b["ring"])
        if len(ring) < 3:
            continue
        buildings.append(Building(
            osm_id=int(b["id"]),
            ring=ring,
            ground_z=float(rec.get("ground_z") or ground_global),
            height=float(rec["h_final"]),
            decision=rec["decision"],
            tags=b.get("tags", {}),
        ))

    ways: list[Way] = []
    points: list[Point] = []
    surf_path = d / "osm_surface.json"
    if surf_path.exists():
        surf = json.loads(surf_path.read_text())
        for w in surf["ways"]:
            line = np.array([frame.to_enu(lon, lat)[:2] for lon, lat in w["line"]])
            if len(line) >= 2:
                ways.append(Way(int(w["id"]), line, w.get("tags", {})))
        for p in surf["nodes"]:
            lon, lat = p["lonlat"]
            points.append(Point(int(p["id"]), frame.to_enu(lon, lat)[:2],
                                p.get("tags", {})))

    tg = json.loads((d / "terrain_grid.json").read_text())["terrain"]
    terrain = Terrain(float(tg["x0"]), float(tg["step"]), int(tg["n"]),
                      np.array(tg["z"], dtype=float))

    return Anchor(frame, buildings, ways, points, terrain, ground_global)


def summary(a: Anchor) -> str:
    kinds: dict[str, int] = {}
    for w in a.ways:
        kinds[w.kind] = kinds.get(w.kind, 0) + 1
    pk: dict[str, int] = {}
    for p in a.points:
        pk[p.kind] = pk.get(p.kind, 0) + 1
    tagged = sum(1 for b in a.buildings if b.material_tag())
    return (
        f"anchor @ {a.frame.lat0:.4f}, {a.frame.lon0:.4f}  ground {a.ground_global:.2f} m\n"
        f"  buildings {len(a.buildings)}  ({tagged} with a building:material tag)\n"
        f"  ways      {len(a.ways)}  {kinds}\n"
        f"  points    {len(a.points)}  {pk}\n"
        f"  terrain   {a.terrain.n}x{a.terrain.n} @ {a.terrain.step} m, "
        f"z {a.terrain.z.min():.2f} to {a.terrain.z.max():.2f}"
    )


if __name__ == "__main__":
    print(summary(load()))

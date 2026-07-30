"""Layer 4: clutter, placed plausibly and recorded honestly.

The rule this module implements: macro geometry is faithful to reality, small detail
is plausible for it. So a tree that OSM actually mapped keeps its real position and
is marked `measured`. A tree that fills the gap between two mapped ones is marked
`plausible` and carries the seed that produced it. Re-rolling the seed regenerates a
different, equally defensible city, which is what makes the exposure spread
measurable instead of hand-waved.

Nothing here imports bpy. This computes a *placement plan* as plain data. Two
consumers realise it: `realise.py` instances the pretty City Generator assets for
Cycles, and `rtproxy.py` emits the cheap correct primitives for Sionna. Keeping them
apart is not tidiness, it is forced by the numbers: one City Generator car is
144,699 triangles and one of its trees is 114,968, while ray tracing at 28 GHz wants
a metal box and a volumetric attenuator respectively.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .anchor import Anchor

# Physical footprint of each class, used by the RT proxy and for spacing checks.
# (length, width, height) in metres, along the instance's own +x.
PROXY_DIMS: dict[str, tuple[float, float, float]] = {
    "car": (4.50, 1.80, 1.45),
    "van": (5.40, 2.00, 2.20),
    "tree": (6.00, 6.00, 12.00),      # crown envelope, not the trunk
    "lamp": (0.20, 0.20, 6.00),
    "bollard": (0.16, 0.16, 0.90),
    "bench": (1.80, 0.60, 0.85),
    "bin": (0.50, 0.50, 0.95),
    "bicycle": (1.70, 0.45, 1.05),
    "terrace": (4.00, 2.50, 2.30),    # parasols and tables as one block
    "railing": (1.50, 0.06, 0.95),
}

# Radio material per class. Vehicles are the reason this layer exists at 28 GHz:
# a parking lane is a row of metal reflectors at exactly pedestrian height.
PROXY_MATERIAL: dict[str, str] = {
    "car": "metal",
    "van": "metal",
    "tree": "vegetation",
    "lamp": "metal",
    "bollard": "metal",
    "bench": "wood",
    "bin": "metal",
    "bicycle": "metal",
    "terrace": "wood",
    "railing": "metal",
}


@dataclass
class Instance:
    """One placed object. Provenance is not optional."""

    kind: str
    xy: tuple[float, float]
    z: float
    yaw: float                     # radians, 0 = +x
    scale: float = 1.0
    provenance: str = "plausible"  # measured | observed | plausible
    source: str = ""               # osm id, or the rule that invented it
    seed: int = 0

    def dims(self) -> tuple[float, float, float]:
        lx, ly, lz = PROXY_DIMS[self.kind]
        return lx * self.scale, ly * self.scale, lz * self.scale

    def material(self) -> str:
        return PROXY_MATERIAL[self.kind]


@dataclass
class Plan:
    instances: list[Instance] = field(default_factory=list)
    seed: int = 0

    def add(self, inst: Instance) -> None:
        self.instances.append(inst)

    def of(self, kind: str) -> list[Instance]:
        return [i for i in self.instances if i.kind == kind]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for i in self.instances:
            out[i.kind] = out.get(i.kind, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def provenance_split(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for i in self.instances:
            out[i.provenance] = out.get(i.provenance, 0) + 1
        return out

    def rt_triangles(self) -> int:
        """Proxy cost: a box is 12, a tree is a trunk plus a 32-face crown."""
        return sum(44 if i.kind == "tree" else 12 for i in self.instances)


def _resample(line: np.ndarray, spacing: float) -> list[tuple[np.ndarray, float]]:
    """Points every `spacing` metres along a polyline, with the local tangent."""
    out: list[tuple[np.ndarray, float]] = []
    carry = 0.0
    for a, b in zip(line[:-1], line[1:], strict=True):
        seg = b - a
        length = float(np.hypot(*seg))
        if length < 1e-6:
            continue
        direction = seg / length
        yaw = math.atan2(direction[1], direction[0])
        t = carry
        while t < length:
            out.append((a + direction * t, yaw))
            t += spacing
        carry = t - length
    return out


def _clear_of_buildings(anchor: Anchor, xy: np.ndarray, margin: float) -> bool:
    """Reject a placement that lands inside or hard against a footprint."""
    for b in anchor.near(xy, 40.0):
        ring = b.ring
        # cheap: distance to the footprint centroid against its circumradius
        r = np.linalg.norm(ring - b.centroid, axis=1).max()
        if np.linalg.norm(xy - b.centroid) < r + margin:
            # refine with a point-in-polygon plus edge distance test
            if _point_in_ring(xy, ring):
                return False
            if _dist_to_ring(xy, ring) < margin:
                return False
    return True


def _point_in_ring(p: np.ndarray, ring: np.ndarray) -> bool:
    x, y = p
    inside = False
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xint = x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
            if x < xint:
                inside = not inside
    return inside


def _dist_to_ring(p: np.ndarray, ring: np.ndarray) -> float:
    best = float("inf")
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        ab = b - a
        denom = float(ab @ ab)
        t = 0.0 if denom < 1e-12 else float(np.clip((p - a) @ ab / denom, 0.0, 1.0))
        best = min(best, float(np.linalg.norm(p - (a + t * ab))))
    return best


def place_measured(anchor: Anchor, plan: Plan) -> None:
    """Everything OSM actually mapped keeps its real position."""
    kind_map = {"tree": "tree", "lamp": "lamp", "bollard": "bollard",
                "bench": "bench", "waste_basket": "bin",
                "bicycle_parking": "bicycle"}
    for p in anchor.points:
        kind = kind_map.get(p.kind)
        if kind is None:
            continue
        plan.add(Instance(
            kind=kind,
            xy=(float(p.xy[0]), float(p.xy[1])),
            z=anchor.terrain.at(*p.xy),
            yaw=0.0,
            provenance="measured",
            source=f"osm:{p.osm_id}",
        ))


# How full a parking lane is, by what OSM says about access. A `destination`
# street in a pedestrian core carries residents' cars and little else.
OCCUPANCY_BY_ACCESS = {"free": 0.75, "destination": 0.30, "none": 0.0}


def park_cars(anchor: Anchor, plan: Plan, rng: np.random.Generator, *,
              spacing: float = 6.2, offset: float = 3.1,
              van_fraction: float = 0.12,
              min_way_length: float = 25.0) -> None:
    """Line the carriageways with parked cars, where cars are actually allowed.

    Worst-case realistic within each access class: a permitted lane is parked full,
    because that is both physically real and the harsher propagation case. But the
    access class comes from the data, not from the highway tag. This block is the
    Ghent pedestrian core and almost none of it takes general traffic.
    """
    for way in anchor.ways_of("carriageway"):
        if way.length < min_way_length:
            continue
        occupancy = OCCUPANCY_BY_ACCESS.get(way.car_access, 0.0)
        if occupancy <= 0.0:
            continue
        for side in (-1, 1):
            for pos, yaw in _resample(way.line, spacing):
                if rng.random() > occupancy:
                    continue
                normal = np.array([-math.sin(yaw), math.cos(yaw)])
                xy = pos + normal * offset * side
                if not _clear_of_buildings(anchor, xy, 1.2):
                    continue
                kind = "van" if rng.random() < van_fraction else "car"
                plan.add(Instance(
                    kind=kind,
                    xy=(float(xy[0]), float(xy[1])),
                    z=anchor.terrain.at(*xy),
                    yaw=yaw + (0.0 if side > 0 else math.pi)
                        + float(rng.normal(0.0, 0.02)),
                    scale=float(rng.uniform(0.96, 1.04)),
                    provenance="plausible",
                    source=f"parked:way{way.osm_id}:side{side}",
                    seed=plan.seed,
                ))


def line_edge(anchor: Anchor, plan: Plan, line: np.ndarray, kind: str, *,
              spacing: float, jitter: float = 0.0,
              rng: np.random.Generator | None = None,
              source: str = "edge") -> None:
    """Run a repeated element along an edge, the way a quay gets its bollards."""
    for pos, yaw in _resample(line, spacing):
        xy = pos + rng.normal(0.0, jitter, size=2) if (jitter and rng) else pos.copy()
        plan.add(Instance(
            kind=kind,
            xy=(float(xy[0]), float(xy[1])),
            z=anchor.terrain.at(*xy),
            yaw=yaw,
            provenance="plausible",
            source=source,
            seed=plan.seed,
        ))


def terraces_at_hospitality(anchor: Anchor, plan: Plan,
                            rng: np.random.Generator, *,
                            probability: float = 0.55,
                            standoff: float = 3.0) -> None:
    """Cafe terraces in front of mapped restaurants, cafes, pubs and bars.

    The POI is measured, the terrace is invented. Ghent quays are wall-to-wall
    terraces in any month worth simulating, so this is the worst-case-realistic
    reading of a `amenity=cafe` node.
    """
    for p in anchor.points_of("hospitality"):
        if rng.random() > probability:
            continue
        host = min(anchor.buildings,
                   key=lambda b: float(np.linalg.norm(b.centroid - p.xy)),
                   default=None)
        if host is None:
            continue

        # A cafe node is mapped *inside* its building, so stepping out from the
        # centroid lands in the masonry and every terrace gets rejected. Step out
        # from the nearest facade edge instead.
        ring = host.ring
        best_d, foot, outward = float("inf"), None, None
        for i in range(len(ring)):
            a0 = ring[i]
            a1 = ring[(i + 1) % len(ring)]
            ab = a1 - a0
            denom = float(ab @ ab)
            t = 0.0 if denom < 1e-12 else float(np.clip((p.xy - a0) @ ab / denom,
                                                        0.0, 1.0))
            q = a0 + t * ab
            d = float(np.linalg.norm(p.xy - q))
            if d < best_d:
                nrm = np.array([ab[1], -ab[0]]) / (np.linalg.norm(ab) + 1e-12)
                if np.dot(nrm, q - host.centroid) < 0:
                    nrm = -nrm
                best_d, foot, outward = d, q, nrm
        if foot is None:
            continue
        away = outward
        xy = foot + away * standoff
        if not _clear_of_buildings(anchor, xy, 0.8):
            continue
        plan.add(Instance(
            kind="terrace",
            xy=(float(xy[0]), float(xy[1])),
            z=anchor.terrain.at(*xy),
            yaw=math.atan2(away[1], away[0]),
            scale=float(rng.uniform(0.85, 1.25)),
            provenance="plausible",
            source=f"terrace:osm{p.osm_id}",
            seed=plan.seed,
        ))


def fill_street_trees(anchor: Anchor, plan: Plan, rng: np.random.Generator, *,
                      spacing: float = 12.0, probability: float = 0.35,
                      min_from_measured: float = 8.0) -> None:
    """Plausible street trees along walkways, never on top of a mapped one.

    OSM has 57 trees in this block, which is real but certainly an undercount for a
    Flemish city centre. These fill in at a believable pitch and stay clear of the
    measured ones so the two populations never collide.
    """
    measured = np.array([i.xy for i in plan.of("tree")
                         if i.provenance == "measured"]) if plan.of("tree") else None
    for way in anchor.ways_of("walkway"):
        if way.length < 20.0:
            continue
        for pos, _yaw in _resample(way.line, spacing):
            if rng.random() > probability:
                continue
            if (measured is not None and len(measured)
                    and np.linalg.norm(measured - pos, axis=1).min()
                    < min_from_measured):
                continue
            if not _clear_of_buildings(anchor, pos, 2.5):
                continue
            plan.add(Instance(
                kind="tree",
                xy=(float(pos[0]), float(pos[1])),
                z=anchor.terrain.at(*pos),
                yaw=float(rng.uniform(0, 2 * math.pi)),
                scale=float(rng.uniform(0.7, 1.15)),
                provenance="plausible",
                source=f"streettree:way{way.osm_id}",
                seed=plan.seed,
            ))


def frontage_terraces(anchor: Anchor, plan: Plan, rng: np.random.Generator,
                      centre, radius: float, *, pitch: float = 7.0,
                      standoff: float = 3.4, probability: float = 0.7) -> None:
    """Terraces along the quay frontage, whether or not a POI was mapped there.

    The mapped hospitality nodes cluster around Korenmarkt, so keying terraces to
    POIs alone leaves the Graslei bare, and a bare Graslei is wrong about Ghent in a
    way that looks finished. This is the macro-faithful, small-plausible rule doing
    its job: the frontage is measured, the terraces on it are generated because a
    quay like this one, in a month worth simulating, is covered in them.
    """
    c = np.asarray(centre, dtype=float)
    for b in anchor.buildings:
        if np.linalg.norm(b.centroid - c) > radius:
            continue
        ring = b.ring
        for i in range(len(ring)):
            a0, a1 = ring[i], ring[(i + 1) % len(ring)]
            e = a1 - a0
            length = float(np.linalg.norm(e))
            if length < 6.0:
                continue
            tang = e / length
            nrm = np.array([e[1], -e[0]]) / length
            mid = (a0 + a1) / 2.0
            if np.dot(nrm, mid - b.centroid) < 0:
                nrm = -nrm
            # only frontages that face open ground
            probe = mid + nrm * (standoff + 2.0)
            if not _clear_of_buildings(anchor, probe, 1.0):
                continue
            n_slots = max(1, int(length // pitch))
            for k in range(n_slots):
                if rng.random() > probability:
                    continue
                t = (k + 0.5) * length / n_slots
                xy = a0 + tang * t + nrm * standoff
                if not _clear_of_buildings(anchor, xy, 1.0):
                    continue
                _ = k
                plan.add(Instance(
                    kind="terrace",
                    xy=(float(xy[0]), float(xy[1])),
                    z=anchor.terrain.at(*xy),
                    yaw=float(np.arctan2(nrm[1], nrm[0])),
                    scale=float(rng.uniform(0.8, 1.15)),
                    provenance="plausible",
                    source=f"frontage:bldg{b.osm_id}:edge{i}",
                    seed=plan.seed,
                ))


def build_plan(anchor: Anchor, seed: int = 0, *,
               cars: bool = True, trees: bool = True,
               terraces: bool = True,
               frontage: tuple | None = None) -> Plan:
    """The whole clutter layer for one seed."""
    plan = Plan(seed=seed)
    rng = np.random.default_rng(seed)

    place_measured(anchor, plan)
    if cars:
        park_cars(anchor, plan, rng)
    if trees:
        fill_street_trees(anchor, plan, rng)
    if terraces:
        terraces_at_hospitality(anchor, plan, rng)
    if frontage is not None:
        frontage_terraces(anchor, plan, rng, frontage[:2], frontage[2])
    return plan


def summary(plan: Plan) -> str:
    prov = plan.provenance_split()
    total = len(plan.instances) or 1
    frac = {k: f"{100 * v / total:.0f}%" for k, v in prov.items()}
    return (
        f"clutter plan seed={plan.seed}: {len(plan.instances)} instances\n"
        f"  by kind:       {plan.counts()}\n"
        f"  by provenance: {prov}  ({frac})\n"
        f"  RT proxy cost: {plan.rt_triangles()} triangles"
    )


if __name__ == "__main__":
    from . import anchor as anchor_mod

    a = anchor_mod.load()
    for s in (0, 1, 2):
        print(summary(build_plan(a, seed=s)))
        print()

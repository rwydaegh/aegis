"""Layer 1 and 2: building envelopes and facade grammar.

One parametric generator, driven entirely by a `FacadeSpec` that the director fills
in. No building is hand-authored. That distinction is the whole point: the earlier
`artloop/step04_row.py` had the same geometry logic but six hard-coded invocations
with hand-picked styles, which does not survive contact with 448 buildings or with
another city.

Two departures from that earlier code, both of which were latent bugs:

- Windows go on the *ring* edges that face a street, not on the min-x side of an
  axis-aligned bounding box. The old assumption held only because the Graslei quay
  runs north to south.
- Roof form comes from a vocabulary the director selects from, so Haussmann mansards
  and Flemish stepped gables are the same code path with a different word.

Emits tagged geometry at two levels of detail. `render` is everything. `rt` drops
what sits below the 10 cm explicit-geometry threshold at 28 GHz, because meshing
centimetre features is wrong physics rather than merely expensive.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .anchor import Anchor, Building
from .meshkit import Mesh, OrientedRect, oriented_rect, prism

L = "building"  # layer tag


@dataclass
class FacadeSpec:
    """What the director decides. Everything here is a knob, never a coordinate."""

    storeys: int = 3
    ground_height_m: float = 3.6
    upper_height_m: float = 3.0
    bays: int = 3
    window_w: float = 1.1
    window_h: float = 1.6
    reveal_m: float = 0.12
    glazing_bars: bool = True
    ground_floor: str = "residential_door"
    roof_form: str = "gabled"
    ridge_parallel_to_street: bool = False
    sills: bool = True
    cornice: bool = True
    string_courses: bool = False
    balconies: bool = False
    wall_material: str = "brick"
    roughness_mm: float = 4.0
    trim_material: str = "marble"

    @property
    def wall_height(self) -> float:
        return self.ground_height_m + max(0, self.storeys - 1) * self.upper_height_m


def _seg_dist(p: np.ndarray, line: np.ndarray) -> float:
    """Point to polyline distance. Vertex distance overestimates badly on the long
    straight ways that make up a street grid, which silently turns every building
    into a corner building."""
    a = line[:-1]
    b = line[1:]
    ab = b - a
    denom = (ab * ab).sum(axis=1)
    denom[denom < 1e-12] = 1e-12
    t = np.clip(((p - a) * ab).sum(axis=1) / denom, 0.0, 1.0)
    proj = a + t[:, None] * ab
    return float(np.linalg.norm(proj - p, axis=1).min())


def street_facing_edges(b: Building, anchor: Anchor, *,
                        max_street_dist: float = 14.0,
                        min_edge_len: float = 3.0) -> list[int]:
    """Which footprint edges look at a street.

    A corner building has two. A terraced house has one. A courtyard building may
    have none, in which case the caller falls back to the longest edge so it still
    gets a facade rather than a blank prism.
    """
    ring = b.ring
    n = len(ring)
    lines = [w.line for w in anchor.ways
             if w.kind in {"carriageway", "walkway", "quay"}]
    if not lines:
        return [_longest_edge(ring)]

    out: list[tuple[float, int]] = []
    for i in range(n):
        a, c = ring[i], ring[(i + 1) % n]
        e = c - a
        length = float(np.linalg.norm(e))
        if length < min_edge_len:
            continue
        mid = (a + c) / 2.0
        normal = np.array([e[1], -e[0]]) / length
        if np.dot(normal, mid - b.centroid) < 0:
            normal = -normal
        probe = mid + normal * 2.0
        best = min((_seg_dist(probe, line) for line in lines), default=1e9)
        if best < max_street_dist:
            out.append((best - 0.15 * length, i, best))

    if not out:
        return [_longest_edge(ring)]
    out.sort()
    keep = [out[0][1]]
    # A second frontage only for a genuine corner: near-perpendicular, and itself
    # close to a street rather than merely closer than the cutoff.
    for _, i, dist in out[1:]:
        if dist > 8.0:
            continue
        if abs(float(np.dot(_edge_dir(ring, keep[0]), _edge_dir(ring, i)))) < 0.35:
            keep.append(i)
            break
    return keep


def _edge_dir(ring: np.ndarray, i: int) -> np.ndarray:
    a, c = ring[i], ring[(i + 1) % len(ring)]
    e = c - a
    return e / (np.linalg.norm(e) + 1e-12)


def _longest_edge(ring: np.ndarray) -> int:
    lens = [float(np.linalg.norm(ring[(i + 1) % len(ring)] - ring[i]))
            for i in range(len(ring))]
    return int(np.argmax(lens))


def _window_rows(spec: FacadeSpec, z0: float) -> list[float]:
    """Sill heights, one per upper storey."""
    rows = []
    z = z0 + spec.ground_height_m
    for _ in range(max(0, spec.storeys - 1)):
        rows.append(z + 0.5 * (spec.upper_height_m - spec.window_h))
        z += spec.upper_height_m
    return rows


def _openings_on_edge(mesh: Mesh, a: np.ndarray, c: np.ndarray, spec: FacadeSpec,
                      z0: float, lod: str) -> None:
    """Punch a bay rhythm into one facade edge, with reveals, glass and sills.

    The reveal is built as real geometry because at 28 GHz a 0.12 m jamb is 11
    wavelengths and sits near-normal to grazing canyon incidence, which is the
    strongest return available. It is not decoration.
    """
    e = c - a
    span = float(np.linalg.norm(e))
    if span < 1.5:
        return
    u = e / span
    nrm = np.array([e[1], -e[0]]) / span  # outward if ring is CCW

    pad = min(0.8, 0.12 * span)
    usable = span - 2 * pad
    if usable <= 0:
        return
    bays = max(1, min(spec.bays, int(usable // (spec.window_w * 1.35)) or 1))
    pitch = usable / bays
    d = spec.reveal_m
    wall = (L, "wall", spec.wall_material)
    glass = (L, "glass", "glass")
    trim = (L, "sill", spec.trim_material)

    def P(t: float, off: float, z: float) -> tuple[float, float, float]:
        p = a + u * t + nrm * off
        return (float(p[0]), float(p[1]), float(z))

    for zb in _window_rows(spec, z0):
        zt = zb + spec.window_h
        for k in range(bays):
            tc = pad + (k + 0.5) * pitch
            t0, t1 = tc - spec.window_w / 2, tc + spec.window_w / 2
            # reveal: four jambs stepping back from the wall plane
            mesh.add_face([P(t0, 0, zb), P(t0, -d, zb), P(t0, -d, zt),
                           P(t0, 0, zt)], wall)
            mesh.add_face([P(t1, -d, zb), P(t1, 0, zb), P(t1, 0, zt),
                           P(t1, -d, zt)], wall)
            mesh.add_face([P(t0, -d, zt), P(t1, -d, zt), P(t1, 0, zt),
                           P(t0, 0, zt)], wall)
            mesh.add_face([P(t0, 0, zb), P(t1, 0, zb), P(t1, -d, zb),
                           P(t0, -d, zb)], wall)
            # glass at the back of the reveal
            mesh.add_face([P(t0, -d, zb), P(t1, -d, zb), P(t1, -d, zt),
                           P(t0, -d, zt)], glass)
            if spec.sills:
                s = 0.10
                mesh.add_face([P(t0 - 0.08, 0.06, zb), P(t1 + 0.08, 0.06, zb),
                               P(t1 + 0.08, -d, zb), P(t0 - 0.08, -d, zb)], trim)
                mesh.add_face([P(t0 - 0.08, 0.06, zb - s),
                               P(t1 + 0.08, 0.06, zb - s),
                               P(t1 + 0.08, 0.06, zb),
                               P(t0 - 0.08, 0.06, zb)], trim)
            if spec.glazing_bars and lod == "render":
                bar = (L, "frame", "wood")
                zm = (zb + zt) / 2
                mesh.add_face([P(t0, -d + 0.01, zm - 0.03),
                               P(t1, -d + 0.01, zm - 0.03),
                               P(t1, -d + 0.01, zm + 0.03),
                               P(t0, -d + 0.01, zm + 0.03)], bar)

    _ground_floor(mesh, P, spec, z0, span, pad, d)


def _ground_floor(mesh: Mesh, P, spec: FacadeSpec, z0: float, span: float,
                  pad: float, d: float) -> None:
    kind = spec.ground_floor
    top = z0 + spec.ground_height_m - 0.55
    glass = (L, "glass", "glass")
    wall = (L, "wall", spec.wall_material)
    door = (L, "door", "wood")

    if kind in {"shopfront", "cafe_glazing", "arcade"}:
        t0, t1 = pad, span - pad
        zb = z0 + 0.35
        mesh.add_face([P(t0, -d, zb), P(t1, -d, zb), P(t1, -d, top),
                       P(t0, -d, top)], glass)
        for t in (t0, t1):
            sgn = 1.0 if t == t0 else -1.0
            mesh.add_face([P(t, 0, zb), P(t, -d, zb), P(t, -d, top),
                           P(t, 0, top)], wall)
            del sgn
        mesh.add_face([P(t0, -d, top), P(t1, -d, top), P(t1, 0, top),
                       P(t0, 0, top)], wall)
    elif kind in {"residential_door", "institutional_portal", "garage"}:
        w = 1.4 if kind == "residential_door" else 2.6
        tc = span / 2
        mesh.add_face([P(tc - w / 2, -0.06, z0),
                       P(tc + w / 2, -0.06, z0),
                       P(tc + w / 2, -0.06, z0 + 2.5),
                       P(tc - w / 2, -0.06, z0 + 2.5)], door)


def _roof(mesh: Mesh, b: Building, rect: OrientedRect, spec: FacadeSpec,
          eaves_z: float, top_z: float, front_edge: int) -> None:
    """Roof forms. The gable family is what makes a Flemish street read as one."""
    ring = b.ring
    form = spec.roof_form
    tile = (L, "roof", "concrete")
    wall = (L, "wall", spec.wall_material)
    gh = max(0.4, top_z - eaves_z)

    if form == "flat":
        mesh.add_face([(float(p[0]), float(p[1]), eaves_z) for p in ring], tile)
        return

    a, c = ring[front_edge], ring[(front_edge + 1) % len(ring)]
    e = c - a
    span = float(np.linalg.norm(e))
    if span < 1e-6:
        mesh.add_face([(float(p[0]), float(p[1]), eaves_z) for p in ring], tile)
        return
    u = e / span
    nrm = np.array([e[1], -e[0]]) / span
    if np.dot(nrm, (a + c) / 2.0 - b.centroid) < 0:
        nrm = -nrm

    depth = 2.0 * rect.half_v if abs(np.dot(u, rect.u)) > 0.7 else 2.0 * rect.half_u
    depth = max(3.0, min(depth, 30.0))

    def P(t: float, back: float, z: float):
        p = a + u * t + nrm * (-back)
        return (float(p[0]), float(p[1]), float(z))

    if form in {"stepped_gable", "bell_gable", "spout_gable"}:
        if form == "stepped_gable":
            prof = [1.0, 0.80, 0.60, 0.40, 0.20]
        elif form == "bell_gable":
            prof = [1.0, 0.84, 0.64, 0.44, 0.26, 0.13]
        else:
            prof = [0.42, 0.42, 0.42]
        n = len(prof)
        for i, f in enumerate(prof):
            t0 = span * (1 - f) / 2
            t1 = span - t0
            zb = eaves_z + gh * i / n
            zt = eaves_z + gh * (i + 1) / n
            for off in (0.0, 0.40):
                mesh.add_face([P(t0, off, zb), P(t1, off, zb),
                               P(t1, off, zt), P(t0, off, zt)], wall)
            mesh.add_face([P(t0, 0.0, zb), P(t0, 0.40, zb),
                           P(t0, 0.40, zt), P(t0, 0.0, zt)], wall)
            mesh.add_face([P(t1, 0.40, zb), P(t1, 0.0, zb),
                           P(t1, 0.0, zt), P(t1, 0.40, zt)], wall)
            mesh.add_face([P(t0, 0.0, zt), P(t1, 0.0, zt),
                           P(t1, 0.40, zt), P(t0, 0.40, zt)], wall)
        ridge = top_z - 0.35
        mesh.add_face([P(0, 0.40, eaves_z), P(span, 0.40, eaves_z),
                       P(span, depth / 2, ridge), P(0, depth / 2, ridge)], tile)
        mesh.add_face([P(0, depth / 2, ridge), P(span, depth / 2, ridge),
                       P(span, depth, eaves_z), P(0, depth, eaves_z)], tile)

    elif form in {"gabled", "half_hipped"}:
        ridge = top_z
        if spec.ridge_parallel_to_street:
            mesh.add_face([P(0, 0, eaves_z), P(span, 0, eaves_z),
                           P(span, depth / 2, ridge), P(0, depth / 2, ridge)], tile)
            mesh.add_face([P(0, depth / 2, ridge), P(span, depth / 2, ridge),
                           P(span, depth, eaves_z), P(0, depth, eaves_z)], tile)
            for t in (0.0, span):
                mesh.add_face([P(t, 0, eaves_z), P(t, depth / 2, eaves_z),
                               P(t, depth / 2, ridge)], wall)
        else:
            mesh.add_face([P(0, 0, eaves_z), P(span / 2, 0, ridge),
                           P(span / 2, depth, ridge), P(0, depth, eaves_z)], tile)
            mesh.add_face([P(span / 2, 0, ridge), P(span, 0, eaves_z),
                           P(span, depth, eaves_z),
                           P(span / 2, depth, ridge)], tile)
            for back in (0.0, depth):
                mesh.add_face([P(0, back, eaves_z), P(span, back, eaves_z),
                               P(span / 2, back, ridge)], wall)

    elif form == "mansard":
        brk = eaves_z + gh * 0.62
        inset = min(1.6, depth * 0.2)
        mesh.add_face([P(0, 0, eaves_z), P(span, 0, eaves_z),
                       P(span, inset, brk), P(0, inset, brk)], tile)
        mesh.add_face([P(0, depth, eaves_z), P(0, depth - inset, brk),
                       P(span, depth - inset, brk), P(span, depth, eaves_z)], tile)
        mesh.add_face([P(0, inset, brk), P(span, inset, brk),
                       P(span, depth - inset, brk), P(0, depth - inset, brk)], tile)

    elif form in {"hipped", "pyramidal"}:
        ridge = top_z
        inset = min(span, depth) * 0.28
        mesh.add_face([P(0, 0, eaves_z), P(span, 0, eaves_z),
                       P(span - inset, depth / 2, ridge),
                       P(inset, depth / 2, ridge)], tile)
        mesh.add_face([P(span, depth, eaves_z), P(0, depth, eaves_z),
                       P(inset, depth / 2, ridge),
                       P(span - inset, depth / 2, ridge)], tile)
        mesh.add_face([P(0, 0, eaves_z), P(inset, depth / 2, ridge),
                       P(0, depth, eaves_z)], tile)
        mesh.add_face([P(span, depth, eaves_z), P(span - inset, depth / 2, ridge),
                       P(span, 0, eaves_z)], tile)
    else:
        mesh.add_face([(float(p[0]), float(p[1]), eaves_z) for p in ring], tile)


def build(b: Building, spec: FacadeSpec, anchor: Anchor, *,
          lod: str = "render") -> Mesh:
    """One building, envelope plus grammar, as tagged geometry."""
    mesh = Mesh()
    rect = oriented_rect(b.ring)
    z0 = b.ground_z
    eaves = z0 + min(spec.wall_height, b.height)
    top = z0 + b.height
    if top - eaves < 0.4 and spec.roof_form != "flat":
        eaves = top - max(0.4, 0.28 * b.height)

    wall = (L, "wall", spec.wall_material)
    prism(mesh, b.ring, z0, eaves, wall, cap_top=False, cap_bottom=False)

    fronts = street_facing_edges(b, anchor)
    for i in fronts:
        _openings_on_edge(mesh, b.ring[i], b.ring[(i + 1) % len(b.ring)],
                          spec, z0, lod)

    if spec.cornice:
        prism(mesh, b.ring, eaves - 0.22, eaves, (L, "cornice", spec.trim_material),
              cap_top=False, cap_bottom=False)

    _roof(mesh, b, rect, spec, eaves, top, fronts[0])
    return mesh


# Roof-form mix for an ordinary Flemish city-centre terrace, as weights.
# Stepped and bell gables are the showpieces, not the norm: a street where every
# house has a stepped gable is as homogeneous as one where every facade is brick,
# just more flattering. The director overrides this per building where it matters.
_TERRACE_FORMS = (
    ("gabled", 0.46),
    ("spout_gable", 0.24),
    ("stepped_gable", 0.16),
    ("bell_gable", 0.08),
    ("mansard", 0.06),
)


def _weighted_pick(options, r: float) -> str:
    acc = 0.0
    for name, w in options:
        acc += w
        if r < acc:
            return name
    return options[-1][0]


def default_spec(b: Building) -> FacadeSpec:
    """A regional prior, for buildings the director has not looked at.

    Deliberately not neutral: a Ghent city-centre footprint of this size and height
    is a terraced house, and saying so beats a grey flat-topped box pretending to be
    uncommitted. But also deliberately varied, and derived from the OSM id so it is
    stable across runs without being uniform.
    """
    rect = oriented_rect(b.ring)
    narrow = 2.0 * min(rect.half_u, rect.half_v)
    h = b.height
    storeys = max(1, int(round((h * 0.72 - 3.6) / 3.0)) + 1)

    r = ((b.osm_id * 2654435761) % 10_000) / 10_000.0
    if h > 26 or b.area > 900:
        form = "hipped"
    elif narrow > 22:
        form = "flat" if r < 0.35 else "hipped"
    else:
        form = _weighted_pick(_TERRACE_FORMS, r)

    return FacadeSpec(
        storeys=min(storeys, 8),
        bays=max(1, min(5, int(narrow // 3.2))),
        roof_form=form,
        ridge_parallel_to_street=(r > 0.62),
        glazing_bars=(r < 0.55),
        sills=(r < 0.8),
        ground_floor="shopfront" if h < 20 and narrow < 16 else "residential_door",
        wall_material=b.material_tag() or "brick",
        upper_height_m=2.9 + 0.5 * r,
    )

"""Minimal mesh construction, with a semantic tag on every face.

No bpy. The generators emit plain vertex and face arrays so the same geometry feeds
Blender for rendering and the Mitsuba exporter for ray tracing, and so the whole
grammar is testable under pytest without launching Blender.

Every face carries a `(layer, cls, material)` tag. That is not bookkeeping for its
own sake: the Sionna export binds materials by looking the tag up, rather than
guessing from an object name, and the render binds a PBR shader from the same tag.
One source, two consumers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

Tag = tuple[str, str, str]  # layer, class, material


def _face_uv(pts: list) -> list[tuple[float, float]]:
    """Box-project one face into metre-scale UVs from its dominant normal.

    Needed because Blender's Brick and most 2D textures read only x and y of the
    coordinate vector. On a wall standing in the XZ plane that means the pattern can
    only vary in x, and brick renders as vertical stripes no matter what coordinate
    space it is fed. Generated meshes carry no UVs, so the generator has to supply
    them, and doing it per face from the normal gives correct courses on walls,
    correct paving on the ground, and no seams worth caring about.
    """
    p = np.asarray(pts, dtype=float)
    if len(p) >= 3:
        n = np.cross(p[1] - p[0], p[2] - p[0])
        norm = float(np.linalg.norm(n))
        n = n / norm if norm > 1e-12 else np.array([0.0, 0.0, 1.0])
    else:
        n = np.array([0.0, 0.0, 1.0])
    ax, ay, az = abs(n)
    if az >= ax and az >= ay:          # roughly horizontal: ground, roof, cap
        return [(float(q[0]), float(q[1])) for q in p]
    if ax >= ay:                        # wall facing east or west
        return [(float(q[1]), float(q[2])) for q in p]
    return [(float(q[0]), float(q[2])) for q in p]   # wall facing north or south


@dataclass
class Mesh:
    verts: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    uvs: list[list[tuple[float, float]]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.faces)

    @property
    def n_tris(self) -> int:
        return sum(max(0, len(f) - 2) for f in self.faces)

    def add_face(self, pts: list, tag: Tag) -> None:
        base = len(self.verts)
        self.verts.extend((float(p[0]), float(p[1]), float(p[2])) for p in pts)
        self.faces.append(tuple(range(base, base + len(pts))))
        self.tags.append(tag)
        self.uvs.append(_face_uv(pts))

    def extend(self, other: Mesh) -> None:
        off = len(self.verts)
        self.verts.extend(other.verts)
        self.faces.extend(tuple(i + off for i in f) for f in other.faces)
        self.tags.extend(other.tags)
        self.uvs.extend(other.uvs)

    def by_tag(self) -> dict[Tag, list[int]]:
        out: dict[Tag, list[int]] = {}
        for i, t in enumerate(self.tags):
            out.setdefault(t, []).append(i)
        return out

    def triangulated(self) -> tuple[np.ndarray, np.ndarray, list[Tag]]:
        """Fan-triangulate. Returns (V, F, per-triangle tags)."""
        tris: list[tuple[int, int, int]] = []
        ttags: list[Tag] = []
        for f, tag in zip(self.faces, self.tags, strict=True):
            for k in range(1, len(f) - 1):
                tris.append((f[0], f[k], f[k + 1]))
                ttags.append(tag)
        return (np.array(self.verts, dtype=float),
                np.array(tris, dtype=np.int32), ttags)

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        v = np.array(self.verts)
        return v.min(axis=0), v.max(axis=0)


def box(mesh: Mesh, centre, dims, yaw: float, tag: Tag) -> None:
    """An axis-aligned box, yawed about z, centred at `centre` (z is the base)."""
    cx, cy, cz = centre
    lx, ly, lz = dims
    c, s = math.cos(yaw), math.sin(yaw)
    hx, hy = lx / 2.0, ly / 2.0
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    low, high = [], []
    for ux, uy in corners:
        x = cx + ux * c - uy * s
        y = cy + ux * s + uy * c
        low.append((x, y, cz))
        high.append((x, y, cz + lz))
    mesh.add_face(low[::-1], tag)
    mesh.add_face(high, tag)
    for i in range(4):
        j = (i + 1) % 4
        mesh.add_face([low[i], low[j], high[j], high[i]], tag)


def quad(mesh: Mesh, a, b, c, d, tag: Tag) -> None:
    mesh.add_face([a, b, c, d], tag)


def prism(mesh: Mesh, ring: np.ndarray, z0: float, z1: float, tag: Tag,
          cap_top: bool = True, cap_bottom: bool = False) -> None:
    """Extrude a closed 2D ring between two heights."""
    n = len(ring)
    low = [(float(p[0]), float(p[1]), z0) for p in ring]
    high = [(float(p[0]), float(p[1]), z1) for p in ring]
    for i in range(n):
        j = (i + 1) % n
        mesh.add_face([low[i], low[j], high[j], high[i]], tag)
    if cap_top:
        mesh.add_face(high, tag)
    if cap_bottom:
        mesh.add_face(low[::-1], tag)


def cylinder(mesh: Mesh, centre, radius: float, height: float, tag: Tag,
             segments: int = 8) -> None:
    cx, cy, cz = centre
    ring = np.array([[cx + radius * math.cos(2 * math.pi * k / segments),
                      cy + radius * math.sin(2 * math.pi * k / segments)]
                     for k in range(segments)])
    prism(mesh, ring, cz, cz + height, tag, cap_top=True, cap_bottom=True)


def ellipsoid(mesh: Mesh, centre, radii, tag: Tag,
              u_seg: int = 8, v_seg: int = 4) -> None:
    """A coarse ellipsoid. Used as a tree crown, where it is an attenuating volume
    rather than a surface, so facet count buys nothing."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    grid = []
    for j in range(v_seg + 1):
        phi = math.pi * j / v_seg
        row = []
        for i in range(u_seg):
            th = 2 * math.pi * i / u_seg
            row.append((cx + rx * math.sin(phi) * math.cos(th),
                        cy + ry * math.sin(phi) * math.sin(th),
                        cz + rz * math.cos(phi)))
        grid.append(row)
    for j in range(v_seg):
        for i in range(u_seg):
            k = (i + 1) % u_seg
            a, b = grid[j][i], grid[j][k]
            c, d = grid[j + 1][k], grid[j + 1][i]
            if j == 0:
                mesh.add_face([a, c, d], tag)
            elif j == v_seg - 1:
                mesh.add_face([a, b, c], tag)
            else:
                mesh.add_face([a, b, c, d], tag)


# --------------------------------------------------------------------------
# Footprint analysis
# --------------------------------------------------------------------------

def convex_hull(pts: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain. Small inputs, so the O(n log n) is free."""
    p = np.unique(pts, axis=0)
    if len(p) <= 2:
        return p
    p = p[np.lexsort((p[:, 1], p[:, 0]))]

    def half(seq):
        out: list = []
        for q in seq:
            while len(out) >= 2:
                a, b = out[-2], out[-1]
                if (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) > 0:
                    break
                out.pop()
            out.append(q)
        return out

    return np.array(half(p)[:-1] + half(p[::-1])[:-1])


@dataclass
class OrientedRect:
    """Minimum-area bounding rectangle of a footprint.

    The reason this exists: `artloop/step04_row.py` used an axis-aligned bbox and
    put the front face at min-x. That worked only because the Graslei quay happens
    to run north to south. Any other street in the block, and the facade lands on
    the wrong side of the building.
    """

    centre: np.ndarray      # (2,)
    u: np.ndarray           # (2,) unit, along `half_u`
    v: np.ndarray           # (2,) unit, perpendicular
    half_u: float
    half_v: float

    def corners(self) -> np.ndarray:
        return np.array([
            self.centre - self.u * self.half_u - self.v * self.half_v,
            self.centre + self.u * self.half_u - self.v * self.half_v,
            self.centre + self.u * self.half_u + self.v * self.half_v,
            self.centre - self.u * self.half_u + self.v * self.half_v,
        ])

    def edge(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        c = self.corners()
        return c[index], c[(index + 1) % 4]

    def edge_midpoints(self) -> np.ndarray:
        c = self.corners()
        return np.array([(c[i] + c[(i + 1) % 4]) / 2.0 for i in range(4)])

    def outward_normal(self, index: int) -> np.ndarray:
        m = self.edge_midpoints()[index]
        d = m - self.centre
        n = float(np.linalg.norm(d))
        return d / n if n > 1e-9 else np.array([1.0, 0.0])


def oriented_rect(ring: np.ndarray) -> OrientedRect:
    """Rotating calipers over the hull edges."""
    hull = convex_hull(np.asarray(ring, dtype=float))
    if len(hull) < 3:
        c = ring.mean(axis=0)
        return OrientedRect(c, np.array([1.0, 0.0]), np.array([0.0, 1.0]),
                            0.5, 0.5)
    best = None
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        e = b - a
        norm = float(np.linalg.norm(e))
        if norm < 1e-9:
            continue
        u = e / norm
        v = np.array([-u[1], u[0]])
        pu = hull @ u
        pv = hull @ v
        area = (pu.max() - pu.min()) * (pv.max() - pv.min())
        if best is None or area < best[0]:
            cu = (pu.max() + pu.min()) / 2.0
            cv = (pv.max() + pv.min()) / 2.0
            best = (area, u, v, u * cu + v * cv,
                    (pu.max() - pu.min()) / 2.0, (pv.max() - pv.min()) / 2.0)
    _, u, v, centre, hu, hv = best
    return OrientedRect(centre, u, v, hu, hv)

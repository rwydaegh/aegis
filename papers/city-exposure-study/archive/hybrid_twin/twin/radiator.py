"""Layer 6: the 28 GHz small cell.

An 8x8 uniform planar array, facade-mounted, pointed down the quay. Geometry and
configuration come from `aegis.mimo.array.AntennaArray` rather than being
reimplemented here, so the panel that gets rendered and the panel that gets traced
are the same object. An earlier Blender scene in this repo hand-rolled its own array
factor and quietly used a different element pattern from the library, which is
exactly the drift this avoids.

Emits three things:
  - the physical panel, a radome box with a visible element grid
  - the mounting bracket
  - optionally the main-lobe envelope, as a visualisation of where the beam points

At 28 GHz the array is small: lambda is 10.7 mm, so an 8x8 grid at half-wavelength
spacing is a 43 mm square. The radome is bigger than the aperture, which is why the
panel reads as a panel and not as a postage stamp.
"""

from __future__ import annotations

import math
import pathlib
import sys
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, "/home/user/aegis/src")

from .anchor import Anchor, Building  # noqa: E402
from .meshkit import Mesh, box, cylinder  # noqa: E402

L = "radiator"

C0 = 299_792_458.0


@dataclass
class SmallCell:
    """Where the panel is and where it looks."""

    position: np.ndarray        # (3,) ENU metres, the aperture centre
    boresight: np.ndarray       # (3,) unit vector
    freq_hz: float = 28.0e9
    n_h: int = 8
    n_v: int = 8
    tx_power_dbm: float = 30.0
    host_id: int | None = None

    @property
    def wavelength(self) -> float:
        return C0 / self.freq_hz

    @property
    def spacing(self) -> float:
        return 0.5 * self.wavelength

    @property
    def aperture(self) -> tuple[float, float]:
        return ((self.n_h - 1) * self.spacing, (self.n_v - 1) * self.spacing)

    def array(self):
        """The real AEGIS array object, for tracing and for the beam pattern."""
        from aegis.mimo.array import AntennaArray
        return AntennaArray.upa(
            n_h=self.n_h, n_v=self.n_v,
            d_h=self.spacing, d_v=self.spacing,
            center=self.position, broadside=self.boresight,
            element_pattern="patch",
        )

    def budget(self) -> dict:
        """Array gain, EIRP and the far-field boundary, so the numbers are on record."""
        n = self.n_h * self.n_v
        array_gain_db = 10.0 * math.log10(n)
        element_dbi = 9.0                      # energy-normalised cos^1.5 patch
        eirp_dbm = self.tx_power_dbm + array_gain_db + element_dbi
        ah, av = self.aperture
        diag = math.hypot(ah, av)
        hpbw_deg = math.degrees(0.886 * self.wavelength
                                / (self.n_h * self.spacing))
        return {
            "elements": n,
            "wavelength_mm": 1e3 * self.wavelength,
            "aperture_mm": (1e3 * ah, 1e3 * av),
            "array_gain_db": array_gain_db,
            "element_dbi": element_dbi,
            "eirp_dbm": eirp_dbm,
            "hpbw_deg": hpbw_deg,
            "fraunhofer_m": 2.0 * diag ** 2 / self.wavelength,
        }


def mount_on_facade(a: Anchor, host: Building, look_at, height: float = 5.5,
                    freq_hz: float = 28.0e9) -> SmallCell:
    """Put the panel on the host's wall, proud of it, aimed at `look_at`.

    Proud by 0.3 m deliberately. Mounting the aperture inside the wall mesh is easy
    to do by accident and returns zero paths from the tracer, because every ray
    starts already occluded.
    """
    target = np.asarray(look_at, dtype=float)[:2]
    ring = host.ring
    n = len(ring)
    best = None
    for i in range(n):
        p0, p1 = ring[i], ring[(i + 1) % n]
        e = p1 - p0
        length = float(np.linalg.norm(e))
        if length < 2.5:
            continue
        mid = (p0 + p1) / 2.0
        nrm = np.array([e[1], -e[0]]) / length
        if np.dot(nrm, mid - host.centroid) < 0:
            nrm = -nrm
        score = float(np.dot(nrm, (target - mid)
                             / (np.linalg.norm(target - mid) + 1e-9)))
        if best is None or score > best[0]:
            best = (score, mid, nrm)
    _score, mid, nrm = best

    pos = np.array([mid[0] + nrm[0] * 0.30, mid[1] + nrm[1] * 0.30,
                    host.ground_z + height])
    aim = np.array([target[0], target[1],
                    host.ground_z + 1.5]) - pos
    aim = aim / float(np.linalg.norm(aim))
    return SmallCell(position=pos, boresight=aim, freq_hz=freq_hz,
                     host_id=host.osm_id)


def panel_mesh(cell: SmallCell, *, radome=(0.34, 0.10, 0.46)) -> Mesh:
    """Radome, bracket and a visible element grid.

    The aperture is 43 mm square at 28 GHz. Rendering only that would be invisible
    at street scale, so the radome is a realistic small-cell enclosure and the
    element grid is drawn at true spacing inside it.
    """
    m = Mesh()
    b = cell.boresight
    yaw = math.atan2(b[1], b[0])
    p = cell.position

    housing = (L, "panel", "plasterboard")
    metal = (L, "bracket", "metal")

    box(m, (p[0] - b[0] * radome[1] / 2, p[1] - b[1] * radome[1] / 2,
            p[2] - radome[2] / 2),
        (radome[1], radome[0], radome[2]), yaw, housing)

    back = p - b * (radome[1] + 0.12)
    box(m, (back[0], back[1], p[2] - 0.05), (0.24, 0.06, 0.10), yaw, metal)
    cylinder(m, (back[0], back[1], p[2] - 0.55), 0.035, 0.55, metal, segments=6)

    # element grid at true half-wavelength spacing
    e_h = np.array([-b[1], b[0], 0.0])
    e_h = e_h / (np.linalg.norm(e_h) + 1e-9)
    e_v = np.cross(b, e_h)
    e_v = e_v / (np.linalg.norm(e_v) + 1e-9)
    d = cell.spacing
    face = p + b * 0.002
    el = (L, "element", "metal")
    for i in range(cell.n_h):
        for j in range(cell.n_v):
            off = ((i - (cell.n_h - 1) / 2) * d * e_h
                   + (j - (cell.n_v - 1) / 2) * d * e_v)
            c = face + off
            box(m, (c[0], c[1], c[2]), (d * 0.62, d * 0.62, 0.002), yaw, el)
    return m


def lobe_mesh(cell: SmallCell, *, length: float = 34.0, dyn_db: float = 10.0,
              n_theta: int = 26, n_phi: int = 48) -> Mesh:
    """Main-lobe envelope, radius scaled by pattern in dB.

    A visualisation, not a physical object. It never goes into the ray tracer and it
    carries its own tag so the exporter drops it.
    """
    m = Mesh()
    b = cell.boresight / np.linalg.norm(cell.boresight)
    e_h = np.array([-b[1], b[0], 0.0])
    e_h = e_h / (np.linalg.norm(e_h) + 1e-9)
    e_v = np.cross(b, e_h)

    d, lam = cell.spacing, cell.wavelength
    k = 2 * math.pi / lam
    tag = (L, "lobe", "none")

    def gain(u):
        """Separable Dirichlet product times the patch element, peak-normalised."""
        uh, uv = float(u @ e_h), float(u @ e_v)
        ub = float(u @ b)
        if ub <= 0.0:
            return 0.0
        out = 1.0
        for n, comp in ((cell.n_h, uh), (cell.n_v, uv)):
            psi = k * d * comp
            num = math.sin(n * psi / 2.0)
            den = n * math.sin(psi / 2.0)
            out *= 1.0 if abs(den) < 1e-9 else abs(num / den)
        return out ** 2 * max(ub, 0.0) ** 1.5

    grid = []
    for i in range(n_theta + 1):
        th = math.radians(34.0) * i / n_theta
        row = []
        for j in range(n_phi):
            ph = 2 * math.pi * j / n_phi
            u = (math.cos(th) * b
                 + math.sin(th) * (math.cos(ph) * e_h + math.sin(ph) * e_v))
            g = gain(u)
            db = 10.0 * math.log10(max(g, 1e-12))
            r = length * max(0.0, (db + dyn_db) / dyn_db)
            row.append(cell.position + u * r)
        grid.append(row)

    for i in range(n_theta):
        for j in range(n_phi):
            jj = (j + 1) % n_phi
            m.add_face([grid[i][j], grid[i][jj], grid[i + 1][jj],
                        grid[i + 1][j]], tag)
    return m


def default_cell(a: Anchor, area: str = "graslei") -> SmallCell:
    """The area's authored deployment, else a derived fallback.

    The fallback mounts on the tallest nearby building and aims at the area centre,
    which is fine for a city we have never looked at and wrong wherever the centroid
    of the study area falls inside a building. Named areas override it.
    """
    from .areas import AREAS, CELLS

    if area in CELLS:
        pos, aim = CELLS[area]
        pos = np.asarray(pos, dtype=float)
        d = np.asarray(aim, dtype=float) - pos
        d = d / float(np.linalg.norm(d))
        host = min(a.buildings,
                   key=lambda b: float(np.linalg.norm(b.centroid - pos[:2])))
        return SmallCell(position=pos, boresight=d, host_id=host.osm_id)

    cx, cy, radius = AREAS[area]
    centre = np.array([cx, cy])
    near = [b for b in a.buildings
            if np.linalg.norm(b.centroid - centre) < radius * 0.75]
    host = max(near, key=lambda b: b.height)
    return mount_on_facade(a, host, centre, height=5.5)


if __name__ == "__main__":
    from . import anchor as anchor_mod

    a = anchor_mod.load()
    cell = default_cell(a)
    print(f"host building : {cell.host_id}")
    print(f"position      : {np.round(cell.position, 2)}")
    print(f"boresight     : {np.round(cell.boresight, 3)}")
    for k, v in cell.budget().items():
        print(f"{k:15s}: {v}")
    pm = panel_mesh(cell)
    lm = lobe_mesh(cell)
    print(f"panel mesh    : {pm.n_tris} tris")
    print(f"lobe mesh     : {lm.n_tris} tris")
    _ = pathlib.Path

"""v1 deployment: repulsive site thinning, sectoring, and illumination test.

The v1 site set is a minimum-spacing thinning of the rooftop candidates, a
placeholder for the Ginibre generator that arrives in a later plan. Each site
carries S sector panels evenly spaced in azimuth, each a UPA covering a finite
azimuth wedge and range. A body is illuminated only by sectors whose wedge and
range it falls inside.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.constants import C_0
from aegis.mimo.array import AntennaArray


def dbm_to_watts(dbm: float) -> float:
    return 10.0 ** ((dbm - 30.0) / 10.0)


def thin_min_spacing(candidates, min_spacing_m, n_target, rng):
    """Greedily accept candidates, rejecting any within min_spacing_m (XY) of
    an accepted one, until n_target are kept or the pool is exhausted."""
    cand = np.asarray(candidates, dtype=float)
    if cand.shape[0] == 0:
        return cand.reshape(0, 3)
    order = rng.permutation(cand.shape[0])
    kept: list[np.ndarray] = []
    for i in order:
        p = cand[i]
        ok = all(np.linalg.norm(p[:2] - k[:2]) >= min_spacing_m for k in kept)
        if ok:
            kept.append(p)
            if len(kept) >= n_target:
                break
    return np.asarray(kept) if kept else cand.reshape(0, 3)


@dataclass(frozen=True)
class Sector:
    array: AntennaArray
    position: np.ndarray  # (3,) panel phase center
    boresight_az_deg: float
    az_coverage_deg: float
    max_range_m: float
    tx_power_w: float

    @property
    def m_ant(self) -> int:
        return self.array.element_positions.shape[0]


@dataclass(frozen=True)
class Site:
    position: np.ndarray  # (3,)
    sectors: list[Sector]


def _az_to_broadside(az_deg: float) -> np.ndarray:
    az = np.radians(az_deg)
    return np.array([np.cos(az), np.sin(az), 0.0])


def build_sites(
    site_positions,
    n_sectors,
    az_coverage_deg,
    max_range_m,
    freq_hz,
    array,
    tx_power_dbm,
) -> list[Site]:
    """Place n_sectors UPA panels per site, evenly spaced in azimuth."""
    site_positions = np.atleast_2d(np.asarray(site_positions, dtype=float))
    n_h, n_v = int(array[0]), int(array[1])
    lam = C_0 / float(freq_hz)
    tx_power_w = dbm_to_watts(tx_power_dbm)

    sites: list[Site] = []
    for pos in site_positions:
        sectors: list[Sector] = []
        for s in range(n_sectors):
            az = s * (360.0 / n_sectors)
            broadside = _az_to_broadside(az)
            panel = AntennaArray.upa(
                n_h=n_h,
                n_v=n_v,
                d_h=lam / 2.0,
                d_v=lam / 2.0,
                center=pos,
                broadside=broadside,
                element_pattern="patch",
            )
            sectors.append(
                Sector(
                    array=panel,
                    position=pos.copy(),
                    boresight_az_deg=az,
                    az_coverage_deg=float(az_coverage_deg),
                    max_range_m=float(max_range_m),
                    tx_power_w=tx_power_w,
                )
            )
        sites.append(Site(position=pos.copy(), sectors=sectors))
    return sites


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest absolute difference between two azimuths in degrees, [0, 180]."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def sectors_illuminating(point, sites) -> list[Sector]:
    """Return the sectors whose wedge and range contain the point."""
    p = np.asarray(point, dtype=float)
    hit: list[Sector] = []
    for site in sites:
        for sector in site.sectors:
            d = p[:2] - sector.position[:2]
            rng = float(np.linalg.norm(d))
            if rng > sector.max_range_m:
                continue
            if rng < 1e-9:
                hit.append(sector)
                continue
            az_to_point = np.degrees(np.arctan2(d[1], d[0]))
            if _angle_diff_deg(az_to_point, sector.boresight_az_deg) <= sector.az_coverage_deg / 2.0:
                hit.append(sector)
    return hit

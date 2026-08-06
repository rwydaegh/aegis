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


def select_rooftop_sites(
    candidates,
    n_target,
    rng,
    min_spacing_m=60.0,
    height_band_m=(8.0, 45.0),
    mount_height_m=2.0,
):
    """Pick realistic rooftop sites from the candidate pool.

    Operators mount urban mmWave sites on ordinary mid-rise rooftops, not on
    church spires or ground-floor sheds, so candidates are first restricted to a
    roof-height band. If the band holds fewer than ``n_target`` (dense-tower or
    low-rise cores), it is widened to the nearest-in-height candidates rather
    than dropped. Survivors are min-spacing thinned, then raised by
    ``mount_height_m`` (the mast/standoff above the parapet).
    """
    cand = np.asarray(candidates, dtype=float)
    if cand.shape[0] == 0:
        return cand.reshape(0, 3)
    lo, hi = float(height_band_m[0]), float(height_band_m[1])
    z = cand[:, 2]
    in_band = (z >= lo) & (z <= hi)
    if in_band.sum() >= n_target:
        sites = thin_min_spacing(cand[in_band], min_spacing_m=min_spacing_m, n_target=n_target, rng=rng)
    else:
        # Starved band (all-tower or all-shed core): walk candidates nearest the
        # band first and greedily keep spacing, so the most plausible roof
        # heights win instead of a random draw over supertalls. Ties (uniform
        # cores) break by rng so realizations stay decorrelated.
        dist = np.maximum(lo - z, 0.0) + np.maximum(z - hi, 0.0)
        kept: list[np.ndarray] = []
        for i in np.lexsort((rng.random(cand.shape[0]), dist)):
            p = cand[i]
            if all(np.linalg.norm(p[:2] - k[:2]) >= min_spacing_m for k in kept):
                kept.append(p)
                if len(kept) >= n_target:
                    break
        sites = np.asarray(kept) if kept else cand.reshape(0, 3)
    if sites.shape[0]:
        sites = sites.copy()
        sites[:, 2] += float(mount_height_m)
    return sites


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


def _az_to_broadside(az_deg: float, downtilt_deg: float = 0.0) -> np.ndarray:
    az = np.radians(az_deg)
    tilt = np.radians(downtilt_deg)
    return np.array([np.cos(az) * np.cos(tilt), np.sin(az) * np.cos(tilt), -np.sin(tilt)])


def build_sites(
    site_positions,
    n_sectors,
    az_coverage_deg,
    max_range_m,
    freq_hz,
    array,
    tx_power_dbm,
    downtilt_deg=0.0,
    rng=None,
) -> list[Site]:
    """Place n_sectors UPA panels per site, evenly spaced in azimuth.

    ``downtilt_deg`` tilts each panel's broadside below the horizon, the way
    real urban sectors aim at the street rather than the skyline. ``rng`` draws
    a uniform per-site azimuth offset so sites do not share one global panel
    orientation (real deployments orient panels per site; a fleet-wide 0/120/240
    alignment imprints spurious azimuthal structure on the exposure CDF).
    """
    site_positions = np.atleast_2d(np.asarray(site_positions, dtype=float))
    n_h, n_v = int(array[0]), int(array[1])
    lam = C_0 / float(freq_hz)
    tx_power_w = dbm_to_watts(tx_power_dbm)

    sites: list[Site] = []
    for pos in site_positions:
        offset = float(rng.uniform(0.0, 360.0)) if rng is not None else 0.0
        sectors: list[Sector] = []
        for s in range(n_sectors):
            az = (offset + s * (360.0 / n_sectors)) % 360.0
            broadside = _az_to_broadside(az, downtilt_deg)
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
    """Return the sectors whose wedge and range contain the point.

    Range is 3D (a rooftop site's slant range, not its map distance) and the
    wedge is half-open, [-w/2, w/2), so a point on the boundary azimuth belongs
    to exactly one sector of a site instead of double-counting in the exposure
    sum.
    """
    p = np.asarray(point, dtype=float)
    hit: list[Sector] = []
    for site in sites:
        for sector in site.sectors:
            if float(np.linalg.norm(p - sector.position)) > sector.max_range_m:
                continue
            d = p[:2] - sector.position[:2]
            if float(np.linalg.norm(d)) < 1e-9:
                hit.append(sector)
                continue
            az_to_point = np.degrees(np.arctan2(d[1], d[0]))
            diff = (az_to_point - sector.boresight_az_deg + 180.0) % 360.0 - 180.0
            if -sector.az_coverage_deg / 2.0 <= diff < sector.az_coverage_deg / 2.0:
                hit.append(sector)
    return hit

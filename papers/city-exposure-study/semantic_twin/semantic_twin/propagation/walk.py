"""Pedestrian observation points on the support mesh.

A walk is a chain of head height points on walkable ground. Walkable is decided
by ray casting, not by any map layer: drop a ray from above, keep the sample if
it lands on a near horizontal face close to the square's ground datum, and
require a small standoff from the nearest obstruction so the head is not inside
a wall or a market stall.

The ground datum itself is measured here too, by :func:`measure_ground_datum`.
It is the one number the walk cannot get from a per point ray cast, because a
per point cast returns the height of whatever is under that column and cannot by
itself say whether that is pavement or a roof. See GROUND_DATUM.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .directions import sample_sphere

SKY_PROBE = 1.0e4


@dataclass(frozen=True)
class Walk:
    """Ordered observation points with their ground datum."""

    points: np.ndarray  # (P, 3) head height positions
    ground_z_m: np.ndarray  # (P,)
    step_m: np.ndarray  # (P,) distance from the previous point
    provenance: dict[str, Any]

    def __len__(self) -> int:
        return int(self.points.shape[0])


def ground_height(geometry: Any, xy: np.ndarray, probe_z: float = SKY_PROBE) -> tuple[np.ndarray, np.ndarray]:
    """Height and up-facing normal component of the surface under each xy.

    ``probe_z`` has to be above everything in the crop. It used to be the ground
    datum plus 200 m, which is above every building at nine of the eleven sites
    and below the towers at Times Square and Shibuya. A ray that starts inside a
    tower does not report that tower's roof, it reports whatever surface of the
    photogrammetric shell lies below the start point, which at street level is
    indistinguishable from pavement. Starting at the sky probe height removes the
    case rather than relying on the enclosure test downstream to catch it.
    """
    count = xy.shape[0]
    origins = np.column_stack([xy, np.full(count, probe_z)])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (count, 1))
    hit, distance, normal, _ = geometry.intersect(origins, directions)
    z = np.where(hit, probe_z - distance, np.nan)
    return z, np.abs(normal[:, 2])


@dataclass(frozen=True)
class GroundDatum:
    """The walkable ground level of a crop, with the evidence behind it."""

    z_m: float
    columns: int  # near horizontal downward first hits sampled
    band_columns: int  # of those, how many sit within the tolerance of z_m
    band_fraction: float
    busiest_z_m: float  # the level holding the most columns, ground or not
    busiest_fraction: float
    provenance: dict[str, Any]


def _level_counts(heights: np.ndarray, tolerance_m: float, search_step_m: float) -> tuple[np.ndarray, np.ndarray]:
    """How many of the sorted heights fall within the tolerance of each trial level."""
    centres = np.arange(heights[0], heights[-1] + search_step_m, search_step_m)
    counts = np.searchsorted(heights, centres + tolerance_m, side="right") - np.searchsorted(
        heights, centres - tolerance_m, side="left"
    )
    return centres, counts


def _settle(heights: np.ndarray, centre: float, tolerance_m: float, iterations: int) -> float:
    """Move the level to the median of its own band until it stops moving."""
    for _ in range(iterations):
        moved = float(np.median(heights[np.abs(heights - centre) <= tolerance_m]))
        if abs(moved - centre) < 1.0e-6:
            return moved
        centre = moved
    return centre


def measure_ground_datum(
    geometry: Any,
    *,
    radius_m: float = 90.0,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    spacing_m: float = 1.0,
    tolerance_m: float = 2.5,
    min_up_cosine: float = 0.85,
    search_step_m: float = 0.25,
    major_level_ratio: float = 0.5,
    min_band_fraction: float = 0.05,
    iterations: int = 8,
) -> GroundDatum:
    """The height of the walkable ground over the disc the walk will use.

    Definition. Sample a square metre grid of columns over the disc, drop a ray
    down each one from above the scene, keep the hits that land on a near
    horizontal face, and count how many of them each trial height would admit
    into the walk's own acceptance band. Call a height a level if its count is at
    least ``major_level_ratio`` of the largest count anywhere. The datum is the
    lowest such level, settled onto the median of its own band.

    Why the lowest major level rather than the busiest one, or the lowest surface.

    A minimum or a low quantile over the mesh finds the underground car parks and
    basement shells the tile provider leaves under the street. The eleven crops in
    this study carry between 4.6 m and 202 m of geometry below their pavement, so
    that failure is not marginal. A downward first hit cannot see any of it,
    because something is always above it, which is why the estimate is built on
    ray casts rather than on vertex statistics.

    A median over a small central disc finds whatever the square was built
    around: the Sukiennice at Krakow, the Capitole at Toulouse. Widening the disc
    to the walk and taking a mode fixes both, because a monument is never the
    majority of a square.

    Taking the busiest level alone is still not enough. At the Zocalo the crop
    centre sits off the plaza, and between about 50 and 70 m the surrounding
    roofs briefly outnumber the pavement, so the busiest level is a roof over that
    span. Pedestrians are on the lowest major surface, never on the second one, so
    the tie is broken downwards. That the tie needs breaking at all is a property
    of the site, not of the ratio: at the 90 m walk radius the ground is the
    busiest level at all eleven sites and the answer does not move for any ratio
    between 0.2 and 1.0.

    ``min_band_fraction`` is a refusal, not a tolerance. A crop whose datum admits
    less than a twentieth of its near horizontal columns has no dominant walkable
    surface and wants looking at rather than publishing.
    """
    if radius_m <= 0.0:
        raise ValueError("radius_m must be positive")
    if not 0.0 < major_level_ratio <= 1.0:
        raise ValueError("major_level_ratio must lie in (0, 1]")
    axis = np.arange(-radius_m, radius_m + spacing_m, spacing_m)
    grid_x, grid_y = np.meshgrid(axis + centre_xy[0], axis + centre_xy[1])
    xy = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    xy = xy[np.linalg.norm(xy - np.asarray(centre_xy), axis=1) <= radius_m]

    z, up = ground_height(geometry, xy)
    flat = np.isfinite(z) & (up >= min_up_cosine)
    heights = np.sort(z[flat])
    if heights.size == 0:
        raise RuntimeError("no near horizontal surface under the crop, the mesh or the centre is wrong")

    centres, counts = _level_counts(heights, tolerance_m, search_step_m)
    busiest = int(np.argmax(counts))
    major = counts >= major_level_ratio * counts[busiest]
    first = int(np.flatnonzero(major)[0])
    last = first
    while last + 1 < counts.size and major[last + 1]:
        last += 1
    chosen = first + int(np.argmax(counts[first : last + 1]))

    datum = _settle(heights, float(centres[chosen]), tolerance_m, iterations)
    band_columns = int(np.count_nonzero(np.abs(heights - datum) <= tolerance_m))
    fraction = band_columns / heights.size
    if fraction < min_band_fraction:
        raise RuntimeError(
            f"the ground datum admits {fraction:.3f} of the near horizontal columns, below the "
            f"{min_band_fraction:.3f} floor, so this crop has no dominant walkable surface"
        )

    return GroundDatum(
        z_m=datum,
        columns=int(heights.size),
        band_columns=band_columns,
        band_fraction=float(fraction),
        busiest_z_m=_settle(heights, float(centres[busiest]), tolerance_m, iterations),
        busiest_fraction=float(counts[busiest]) / heights.size,
        provenance={
            "rule": (
                "lowest major walkable level: square metre columns over the walk disc, "
                "downward first hit from above the scene, near horizontal faces only, the "
                "lowest height whose acceptance band holds at least half as many hits as the "
                "busiest height anywhere, settled onto the median of its own band"
            ),
            "radius_m": radius_m,
            "centre_xy": list(centre_xy),
            "spacing_m": spacing_m,
            "tolerance_m": tolerance_m,
            "min_up_cosine": min_up_cosine,
            "search_step_m": search_step_m,
            "major_level_ratio": major_level_ratio,
            "min_band_fraction": min_band_fraction,
            "columns_sampled": int(xy.shape[0]),
            "columns_near_horizontal": int(heights.size),
            "columns_in_band": band_columns,
            "band_fraction": float(fraction),
            "busiest_level_m": _settle(heights, float(centres[busiest]), tolerance_m, iterations),
            "busiest_fraction": float(counts[busiest]) / heights.size,
        },
    )


def ground_datum(geometry: Any, **kwargs: Any) -> float:
    """The walkable ground level, without the provenance."""
    return measure_ground_datum(geometry, **kwargs).z_m


def sky_visibility(geometry: Any, points: np.ndarray, samples: int, rng: np.random.Generator) -> np.ndarray:
    """Fraction of the full sphere from which each point can see out.

    A clearance test alone does not catch a standpoint inside a building or
    under a roofed arcade: a point in the middle of a large room has metres of
    space around it in every direction and passes. Such a point traces to a
    susceptibility seven orders of magnitude below its neighbours, which is not
    an exposure result, it is a bad standpoint. Requiring that some ray escapes
    is the test that catches it.
    """
    out = np.zeros(points.shape[0])
    for i, point in enumerate(points):
        directions = sample_sphere(samples, rng)
        hit, _, _, _ = geometry.intersect(np.tile(point, (samples, 1)) + 1.0e-3 * directions, directions)
        out[i] = float(np.mean(~hit))
    return out


def clearance(geometry: Any, points: np.ndarray, samples: int, rng: np.random.Generator) -> np.ndarray:
    """Median distance to the nearest surface over random directions.

    A crude free space radius. It rejects points buried inside geometry, which a
    photogrammetric mesh of a market square has plenty of.
    """
    out = np.zeros(points.shape[0])
    for i, point in enumerate(points):
        directions = sample_sphere(samples, rng)
        origins = np.tile(point, (samples, 1))
        hit, distance, _, _ = geometry.intersect(origins, directions)
        distance = np.where(hit, distance, SKY_PROBE)
        out[i] = float(np.median(distance))
    return out


def build_walk(
    geometry: Any,
    *,
    ground_datum_m: float,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    radius_m: float = 90.0,
    spacing_m: float = 3.0,
    datum_tolerance_m: float = 2.5,
    min_up_cosine: float = 0.85,
    min_clearance_m: float = 2.0,
    min_sky_fraction: float = 0.01,
    head_height_m: float = 1.5,
    max_step_m: float = 8.0,
    clearance_samples: int = 96,
    seed: int = 0,
    probe_z_m: float = SKY_PROBE,
) -> Walk:
    """Greedy nearest neighbour chain through walkable candidates.

    ``probe_z_m`` is the height the downward casts start from and it is
    exposed for one reason: every run published before 3 August started them at
    the ground datum plus 200 m, and a rerun that has to extend or repair one of
    those runs has to select the same standpoints it did. The value is recorded
    in the provenance, so which rule a walk was built under is readable off the
    manifest rather than inferred from a timestamp. New work wants the default.
    """
    rng = np.random.default_rng(seed)
    axis = np.arange(-radius_m, radius_m + spacing_m, spacing_m)
    grid_x, grid_y = np.meshgrid(axis + centre_xy[0], axis + centre_xy[1])
    xy = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    inside = np.linalg.norm(xy - np.asarray(centre_xy), axis=1) <= radius_m
    xy = xy[inside]

    z, up = ground_height(geometry, xy, probe_z_m)
    walkable = np.isfinite(z) & (np.abs(z - ground_datum_m) <= datum_tolerance_m) & (up >= min_up_cosine)
    xy = xy[walkable]
    z = z[walkable]
    if xy.shape[0] == 0:
        raise RuntimeError("no walkable candidates, check the ground datum")

    heads = np.column_stack([xy, z + head_height_m])
    free = clearance(geometry, heads, clearance_samples, rng)
    keep = free >= min_clearance_m
    heads = heads[keep]
    z = z[keep]
    if heads.shape[0] == 0:
        raise RuntimeError("every walkable candidate failed the clearance test")

    sky = sky_visibility(geometry, heads, clearance_samples, rng)
    open_air = sky >= min_sky_fraction
    enclosed = int(np.count_nonzero(~open_air))
    heads = heads[open_air]
    z = z[open_air]
    if heads.shape[0] == 0:
        raise RuntimeError("every walkable candidate was enclosed")

    order = _chain(heads[:, :2], max_step_m)
    heads = heads[order]
    z = z[order]
    step = np.zeros(heads.shape[0])
    step[1:] = np.linalg.norm(np.diff(heads[:, :2], axis=0), axis=1)
    return Walk(
        points=heads,
        ground_z_m=z,
        step_m=step,
        provenance={
            "ground_datum_m": ground_datum_m,
            "centre_xy": list(centre_xy),
            "radius_m": radius_m,
            "spacing_m": spacing_m,
            "datum_tolerance_m": datum_tolerance_m,
            "min_up_cosine": min_up_cosine,
            "min_clearance_m": min_clearance_m,
            "head_height_m": head_height_m,
            "clearance_samples": clearance_samples,
            "probe_z_m": probe_z_m,
            "candidates_before_clearance": int(walkable.sum()),
            "min_sky_fraction": min_sky_fraction,
            "candidates_rejected_as_enclosed": enclosed,
            "candidates_after_clearance": int(heads.shape[0]),
        },
    )


def _chain(xy: np.ndarray, max_step_m: float) -> np.ndarray:
    """Greedy nearest neighbour ordering, restarting when the gap is too wide."""
    remaining = list(range(xy.shape[0]))
    start = int(np.argmin(xy[:, 0] + xy[:, 1]))
    remaining.remove(start)
    order = [start]
    current = start
    while remaining:
        distances = np.linalg.norm(xy[remaining] - xy[current], axis=1)
        pick = int(np.argmin(distances))
        if distances[pick] > max_step_m:
            pick = int(np.argmin(np.linalg.norm(xy[remaining] - xy[order[0]], axis=1)))
        current = remaining.pop(pick)
        order.append(current)
    return np.asarray(order, dtype=np.int64)


def stratified_subset(walk: Walk, count: int) -> np.ndarray:
    """Evenly spaced indices along the walk, for a pilot run."""
    if count >= len(walk):
        return np.arange(len(walk))
    return np.unique(np.linspace(0, len(walk) - 1, count).round().astype(int))

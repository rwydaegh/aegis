"""Base station sites on the tips of facades, and what they illuminate with.

The external network is not described by a height band and a range band here. It
is read off the geometry. A site sits on a facade tip, meaning the top edge where
a wall meets the sky, which is exactly the silhouette a pedestrian photographs.
There is no mast, so the site is on the tip itself.

Two things follow, and they are why this module exists.

**The direct term is a sum over azimuth, not an integral over a range band.**
Along an azimuth there is one visible facade tip, at elevation ``alpha`` and
horizontal distance ``d``. Sites at uniform linear density along that tip put
``lambda d dphi`` of them in an azimuth slice, each at slant range
``d / cos(alpha)``, and flux falls as the inverse square of slant range, so

    chi_dir  proportional to  mean over phi of  cos^2(alpha) / d.

There is no integral over range to cap, because each azimuth carries one source
distance rather than a distribution over one. The band law had to cap the range,
and because its site count grew as ``d dd`` while power fell as ``1/d**2`` the
integrand went as ``1/d`` and the cap set the answer.

**The source is one dimensional, so a ray never lands on it.** An estimator that
weights a ray by an illumination density at the direction it escapes returns
nothing here, because the sites occupy no solid angle. Worse, and this is the
part no grid resolution repairs, such a density is a function of direction alone
and so assumes the sites are far enough away that only direction matters. The
skyline sits at 18 to 70 m from the head at these sites while a last bounce can
be tens of metres away, so which tips are visible genuinely differs between the
two points.

That is why this law is a :class:`~.model.PlacedIllumination` and not an
:class:`~.model.AngularIllumination`, and it is the whole reason the protocol in
:mod:`~.model` splits in two rather than pretending both laws evaluate the same
way.

The answer is to connect to the source rather than wait to hit it. At each vertex
of a path, sample a point on the roofline, cast one ray to it, and take the
contribution if that ray is clear. The visibility question is then answered from
the vertex where it is asked. This is next event estimation, and the same call at
the zeroth vertex is the direct term, so both halves are one estimator.

The linear density is uniform along the roofline. That is the density the formula
above assumes, and it is the one a photogrammetric mesh can carry, since the mesh
is a single surface with no building boundaries in it to divide a footprint by.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

INFINITY = 1.0e30

#: Elevations searched when the silhouette is found by casting. The top is short
#: of the zenith because a standpoint under an arcade hits a ceiling straight up,
#: which is not a skyline. The bottom is above the horizon for the same kind of
#: reason: a ray sent at exactly zero elevation skims the pavement forever.
ELEVATION_MIN_DEG = 0.05
ELEVATION_MAX_DEG = 85.0

#: A surface sample counts as sky exposed if a ray straight up from it escapes.
#: Offset first, or the ray starts on the surface it is leaving.
UP_EPSILON_M = 0.05

#: A sample counts as a facade tip if, among the samples within this horizontal
#: radius, something sits at least ``EDGE_DROP_M`` below it and nothing sits more
#: than ``EDGE_RISE_M`` above it. Both halves are needed and each removes a
#: different wrong answer. Without the drop, the middle of a flat roof qualifies.
#: Without the rise, the whole outer face of a wall qualifies, because a ray sent
#: straight up from a point on a wall escapes to the sky just as one sent from
#: the top edge does. That second case is the one that looks plausible: it
#: produces a set whose median height reads like a roofline while 62 percent of
#: its members are partway down a facade.
EDGE_RADIUS_M = 2.0
EDGE_DROP_M = 3.0
EDGE_RISE_M = 0.5

#: The tag this law writes into a manifest, and the family it belongs to. Both
#: are already the vocabulary ``viz/provenance.py`` and ``runconfig.LAWS`` use.
FACADE_TIP_LAW = "facade_tip"
FACADE_TIP_FAMILY = "roofline"


@dataclass(frozen=True)
class Roofline:
    """Sample points along the facade tips of one scene.

    ``points`` are positions on the tips. ``length_m`` is the roofline length each
    point stands for, so a sum weighted by it approximates a line integral. The
    weights are equal by construction, since the samples come from a uniform draw
    over surface area and are then filtered, but they are carried explicitly so a
    non uniform draw can be substituted without touching the estimator.

    This is one of the two constructions of the facade tip law. It filters a
    uniform draw over mesh area. The other, :func:`~.sources.build_source_set`,
    casts a ray fan from the walk and keeps the topmost hit. They exist to be
    compared, and ``archive/scripts/measure_source_construction.py`` is the
    comparison.
    """

    points: np.ndarray  # (N, 3)
    length_m: np.ndarray  # (N,)
    provenance: dict[str, Any]
    name: str = "facade_tips"

    law: ClassVar[str] = FACADE_TIP_LAW
    family: ClassVar[str] = FACADE_TIP_FAMILY

    def __len__(self) -> int:
        return int(self.points.shape[0])

    def sites(self) -> np.ndarray:
        return self.points

    def describe(self) -> dict[str, Any]:
        """What this source set is, flat enough to sit in a manifest."""
        return {
            "name": self.name,
            "law": self.law,
            "family": self.family,
            "kind": "placed",
            "construction": "uniform area draw filtered to facade tips",
            "sites": len(self),
            **self.provenance,
        }


def sample_surface(vertices: np.ndarray, faces: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    """Points drawn uniformly over the area of a triangle mesh."""
    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    total = area.sum()
    if total <= 0.0:
        raise ValueError("mesh has no area")
    index = rng.choice(area.size, size=count, p=area / total)
    u = rng.random(count)
    v = rng.random(count)
    over = u + v > 1.0
    u[over] = 1.0 - u[over]
    v[over] = 1.0 - v[over]
    return a[index] + u[:, None] * (b[index] - a[index]) + v[:, None] * (c[index] - a[index])


def _neighbourhood_extremes(points: np.ndarray, radius_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Lowest and highest ``z`` within one grid cell of each point, horizontally.

    Cells are ``radius_m`` across and each point reduces over the nine cells that
    touch its own, so the neighbourhood is a square of side ``3 * radius_m``
    centred on the point's cell rather than a disc around the point. Linear in the
    sample count, which is what lets the draw be dense enough that the extracted
    roofline has no gaps in it.
    """
    key = np.floor(points[:, :2] / radius_m).astype(np.int64)
    key -= key.min(axis=0)
    width = int(key[:, 1].max()) + 1
    flat = key[:, 0] * width + key[:, 1]
    cells = int(key[:, 0].max() + 1) * width

    cell_low = np.full(cells, np.inf)
    cell_high = np.full(cells, -np.inf)
    np.minimum.at(cell_low, flat, points[:, 2])
    np.maximum.at(cell_high, flat, points[:, 2])
    cell_low = cell_low.reshape(-1, width)
    cell_high = cell_high.reshape(-1, width)

    padded_low = np.pad(cell_low, 1, constant_values=np.inf)
    padded_high = np.pad(cell_high, 1, constant_values=-np.inf)
    low = np.full_like(cell_low, np.inf)
    high = np.full_like(cell_high, -np.inf)
    for dx in range(3):
        for dy in range(3):
            low = np.minimum(low, padded_low[dx : dx + cell_low.shape[0], dy : dy + width])
            high = np.maximum(high, padded_high[dx : dx + cell_high.shape[0], dy : dy + width])
    return low.reshape(-1)[flat], high.reshape(-1)[flat]


def extract_roofline(
    geometry: Any,
    *,
    samples: int = 400_000,
    rng: np.random.Generator | None = None,
    edge_radius_m: float = EDGE_RADIUS_M,
    edge_drop_m: float = EDGE_DROP_M,
    edge_rise_m: float = EDGE_RISE_M,
    min_height_above_ground_m: float = 4.0,
    ground_datum_m: float = 0.0,
) -> Roofline:
    """Facade tips of a scene, as a set of points on the mesh.

    Four tests, each of which removes a different wrong answer.

    A tip is **sky exposed**, or it is under an arcade or inside a courtyard
    passage and no site sits there. A tip has a **drop beside it**, or it is the
    middle of a roof, where a site would be hidden from every street. A tip has
    **nothing above it**, or it is partway down a wall, since a ray sent straight
    up from a wall escapes to the sky and the first test alone therefore keeps the
    entire outer face of every building. And a tip is **above the ground**, or it
    is a kerb, a step or a parked object, all of which pass the other tests on a
    photogrammetric mesh and none of which carries a base station.
    """
    rng = np.random.default_rng(0) if rng is None else rng
    points = sample_surface(geometry.vertices, geometry.faces, samples, rng)

    up = np.tile(np.array([0.0, 0.0, 1.0]), (points.shape[0], 1))
    hit, _, _, _ = geometry.intersect(points + UP_EPSILON_M * up, up)
    exposed = ~hit
    exposed &= points[:, 2] - ground_datum_m >= min_height_above_ground_m
    kept = points[exposed]
    if kept.shape[0] == 0:
        raise RuntimeError("no sky exposed samples above the ground, check the datum")

    # A drop beside the sample separates a roof edge from a roof middle, and
    # nothing above it separates the edge from the wall below. Both are needed.
    # Points on a wall reach this test rather than being removed earlier, because
    # the sky test does not remove them: straight up from the outer face of a
    # building is open sky. Measured at Korenmarkt, the drop test alone keeps
    # 28,016 samples of which 62 percent have something higher within the radius,
    # so they sit partway down a facade. Adding the rise test leaves 7,187.
    #
    # The neighbourhood is a square of cells rather than a disc, and the reason is
    # cost. This has to run over millions of samples, because the roofline of a
    # 250 m crop is tens of kilometres long and a sparse draw leaves gaps in the
    # silhouette. A per point radius query cannot afford that. Binning to a grid
    # of the search radius and reducing over the nine touching cells gives the
    # same answer to within the difference between a square and its inscribed
    # disc, which moves no decision here because the drop and rise thresholds are
    # metres while the shape difference is a fraction of one cell.
    lowest, highest = _neighbourhood_extremes(kept, edge_radius_m)
    edge = (kept[:, 2] - lowest >= edge_drop_m) & (highest - kept[:, 2] < edge_rise_m)
    tips = kept[edge]
    if tips.shape[0] == 0:
        raise RuntimeError("no facade tips found, check edge_radius_m and edge_drop_m")

    # Each surviving sample stands for the same length of roofline, because the
    # draw was uniform over area and every filter above is a property of the
    # point rather than of its density. The constant is unknowable and does not
    # matter: every published quantity here is a ratio and it cancels.
    length = np.ones(tips.shape[0], dtype=np.float64)
    provenance = {
        "surface_samples": int(samples),
        "sky_exposed": int(exposed.sum()),
        "tips": int(tips.shape[0]),
        "edge_radius_m": float(edge_radius_m),
        "edge_drop_m": float(edge_drop_m),
        "edge_rise_m": float(edge_rise_m),
        "min_height_above_ground_m": float(min_height_above_ground_m),
        "ground_datum_m": float(ground_datum_m),
        "density": "uniform per unit length of roofline",
    }
    return Roofline(points=tips, length_m=length, provenance=provenance)


def silhouette(
    geometry: Any,
    origin: np.ndarray,
    *,
    azimuths: int = 720,
    elevations: int = 400,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Elevation and horizontal distance of the highest surface, per azimuth.

    Returns ``(alpha_rad, horizontal_m, found)``. A fan goes up each azimuth and
    the silhouette is the largest elevation that still hits. This is the exact
    answer at one point and it is what the direct term reads, so it does not
    depend on the roofline sampling above at all. That independence is the cross
    check: the tips that this fan sees have to be tips the sampler also found.
    """
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)
    elevation = np.radians(np.logspace(np.log10(ELEVATION_MIN_DEG), np.log10(ELEVATION_MAX_DEG), elevations))
    az, el = np.meshgrid(azimuth, elevation, indexing="ij")
    unit = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=-1)
    flat = unit.reshape(-1, 3)

    hit, distance, _, _ = geometry.intersect(np.broadcast_to(origin, flat.shape), flat)
    hit = hit.reshape(azimuths, elevations)
    distance = distance.reshape(azimuths, elevations)

    reversed_hit = hit[:, ::-1]
    found = reversed_hit.any(axis=1)
    index = elevations - 1 - np.argmax(reversed_hit, axis=1)
    alpha = elevation[index]
    slant = distance[np.arange(azimuths), index]
    return alpha, slant * np.cos(alpha), found


def direct_term(alpha: np.ndarray, horizontal: np.ndarray, found: np.ndarray) -> float:
    """``mean over azimuth of cos^2(alpha) / d``, the direct flux up to a constant.

    An azimuth with no facade tip contributes nothing. That is a floor rather than
    a neutral choice, because a real horizon carries sites too, and the caller is
    given the count of such azimuths so it can be seen rather than assumed.
    """
    good = found & np.isfinite(horizontal) & (horizontal > 0.0)
    weight = np.zeros_like(alpha)
    weight[good] = np.cos(alpha[good]) ** 2 / horizontal[good]
    return float(weight.mean())


def connect(
    geometry: Any,
    origins: np.ndarray,
    roofline: Roofline,
    rng: np.random.Generator,
    *,
    epsilon_m: float = 1.0e-3,
) -> tuple[np.ndarray, np.ndarray]:
    """One next event connection per origin, and whether it was clear.

    Each origin draws its own site, so a batch of path vertices costs one shadow
    ray each. Returns ``(contribution, visible)``, with the contribution already
    carrying the inverse square of the slant range and the site weight, and zero
    where the connection was blocked.

    The estimator this feeds divides by the draw probability, which is uniform
    over the roofline samples, so the returned value is the site count times the
    per site flux and is unbiased for the line integral. Note the convention: this
    returns a **sum** over the set, where :func:`~.sources.direct_from_sites`
    returns a mean over it.
    """
    count = origins.shape[0]
    index = rng.integers(0, len(roofline), size=count)
    target = roofline.points[index]
    delta = target - origins
    distance = np.linalg.norm(delta, axis=1)
    direction = delta / np.maximum(distance, 1.0e-12)[:, None]

    hit, travel, _, _ = geometry.intersect(origins + epsilon_m * direction, direction)
    # A clear connection is one where nothing is hit before the site itself. The
    # site sits on the mesh, so the ray does hit at the far end and the test is on
    # the range rather than on the hit flag.
    visible = ~hit | (travel >= distance - 2.0 * epsilon_m)

    contribution = np.zeros(count, dtype=np.float64)
    good = visible & (distance > 0.0)
    contribution[good] = roofline.length_m[index[good]] * len(roofline) / distance[good] ** 2
    return contribution, visible

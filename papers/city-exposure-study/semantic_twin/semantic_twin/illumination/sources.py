"""The facade tip law as an explicit set of points, and how a path reaches one.

:mod:`~.bands` marginalises the base station population into an angular density
`Q(u)` and reads it off the direction a ray escapes in. That works and it is what
the headline numbers are built on, but it assumes the sources are far enough away
that only direction matters. They are not: the skyline sits 18 to 70 m from the
head, while a bounce can happen tens of metres away, so which rooftops are visible
genuinely differs between the head and the wall the ray bounced off.

This module carries the other way of doing it. The sources are an explicit set of
points on the roofline, and a path reaches one by connecting to it: at each
vertex, pick a site, cast one ray at it, and add its contribution if nothing is in
the way. That is next event estimation, standard in rendering. The visibility
question is then answered from the point where it is asked, so the position
dependence is exact rather than assumed away, and the line of sight part and the
bounced part come out of one estimator instead of two.

METHOD.md sections 5 and 5.1 carry the argument. The short version of how the set
is built: a ray fan goes up from each standpoint of the walk, the topmost hit in
each azimuth is a silhouette point, the union along the walk is the set of
surfaces that are skyline from the street, and that set is thinned to one site per
occupied cell so a wall seen edge on is not over weighted.

:class:`SourceSet` is the live :class:`~.model.PlacedIllumination`.
:class:`~semantic_twin.transport.next_event.NextEventGather` is the estimator
that consumes it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, ClassVar

import numpy as np

from .roofline import FACADE_TIP_FAMILY, FACADE_TIP_LAW

# The digest is intentionally text based. A direct float64 byte hash can change
# when equivalent ratios take different summation paths or when host endianness
# changes, so values are quantized before hashing.
WEIGHT_CANONICALIZATION = "normalized_weights_quantized_15_significant_digits_ascii_v1"

#: How far a site stands clear of the surface it was found on.
#:
#: This is not decoration and it is not a mast. A silhouette point lies exactly
#: **in** the mesh, so every ray aimed at it arrives tangent to the surface it
#: sits on, and whether that ray is blocked is then decided by the last bit of a
#: single precision intersector. Measured at Korenmarkt and Brussels, leaving the
#: sites embedded makes the bounced term swing 1.8 dB as the connection start is
#: nudged between 1 mm and 10 cm. Lifting them a quarter of a metre drops that
#: swing to 0.05 dB. The sites become points in free space and the tangency goes
#: away.
#:
#: The value costs almost nothing, which is the point. Over 0.25 to 4 m, a factor
#: of sixteen, the reported surplus moves 0.08 dB at Korenmarkt and 0.02 dB at
#: Brussels, because a lift that lets more roofline be seen raises the line of
#: sight term and the bounced term together and the ratio divides it out.
SITE_LIFT_M = 0.5


def thin(
    points: np.ndarray,
    cell_m: float,
    rng: np.random.Generator | None = None,
    *,
    dims: int = 2,
) -> np.ndarray:
    """One point per occupied cell, on a grid of ``dims`` dimensions.

    Cells rather than a fixed count, so the surviving density is uniform per unit
    of whatever the grid measures, however unevenly the fan sampled it.

    ``dims`` decides what that unit is, and it is the whole question. On a flat
    grid, ``dims=2``, a vertical wall occupies a line of cells and so gains sites
    as ``1/cell``, while a flat roof occupies a patch of them and gains as
    ``1/cell**2``. Shrinking the cell then keeps moving weight onto horizontal
    surface and never stops, so a flat grid has no useful limit. On a solid grid,
    ``dims=3``, both gain as ``1/cell**2``, and the set converges to sites spread
    evenly over the area of the surface that is skyline.

    Which point in a cell survives matters less but is not nothing. Keeping the
    highest one, the default, sounds right for a roofline and is not: the highest
    point in a cell is its least typical member. Pass a generator to keep a
    uniformly drawn member instead.
    """
    if points.shape[0] == 0:
        return points
    key = np.floor(points[:, :dims] / cell_m).astype(np.int64)
    key -= key.min(axis=0)
    flat = key[:, 0]
    for axis in range(1, dims):
        flat = flat * (int(key[:, axis].max()) + 1) + key[:, axis]
    if rng is None:
        order = np.lexsort((-points[:, 2], flat))
    else:
        # A single key lexsort is stable, so shuffling first and then grouping
        # makes the survivor of each cell a uniform draw from that cell.
        shuffle = rng.permutation(points.shape[0])
        order = shuffle[np.argsort(flat[shuffle], kind="stable")]
    flat_sorted = flat[order]
    first = np.concatenate(([True], flat_sorted[1:] != flat_sorted[:-1]))
    return points[order][first]


def _tip_directions(
    alpha: np.ndarray, horizontal: np.ndarray, azimuth: np.ndarray, good: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Slant range and unit direction of every silhouette tip that passed ``good``."""
    slant = horizontal[good] / np.maximum(np.cos(alpha[good]), 1.0e-9)
    direction = np.stack(
        [
            np.cos(alpha[good]) * np.cos(azimuth[good]),
            np.cos(alpha[good]) * np.sin(azimuth[good]),
            np.sin(alpha[good]),
        ],
        axis=-1,
    )
    return slant, direction


def _drop_clutter_tips(
    geometry: Any, origin: np.ndarray, slant: np.ndarray, direction: np.ndarray, clutter_triangles: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Remove tips that land on a triangle the panoramas call clutter.

    One more cast along the directions already chosen, only to read which triangle
    the tip sits on. A thousand rays beside the fan's near million, so the cost
    does not show.
    """
    _, _, _, face = geometry.intersect(np.broadcast_to(origin, direction.shape), direction)
    face = np.asarray(face, dtype=np.int64)
    inside = np.clip(face, 0, clutter_triangles.size - 1)
    keep = (face < 0) | (face >= clutter_triangles.size) | ~clutter_triangles[inside]
    return slant[keep], direction[keep]


def silhouette_cloud(
    geometry: Any,
    origins: np.ndarray,
    silhouette: Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    azimuths: int,
    elevations: int,
    floor_m: float = 0.0,
    clutter_triangles: np.ndarray | None = None,
) -> np.ndarray:
    """Where the visible skyline actually is, found by casting and nothing else.

    A ray fan goes up each azimuth from each standpoint and the topmost hit is the
    silhouette. This reads no site set and no threshold, which is what lets it
    judge one: a construction that misses much of this cloud is missing roofline
    that a pedestrian can see.

    ``floor_m`` drops hits nearer than that from the standpoint that found them,
    measured on the ground rather than in slant. It is meant for clutter, and it
    works on clutter for a reason worth stating: a lamp post only ever reaches the
    silhouette from close by, because from any distance a five metre post sits
    well under a twenty metre roofline and something taller is hit first. So a
    near cut removes the post from the cloud without removing the roofline behind
    it, which some other standpoint sees at a respectable distance anyway.

    ``clutter_triangles`` is the other half of that, and it is the half the range
    cut cannot do. A hoarding on a roof edge and a tree above a low wall both
    stand at roofline height and at roofline range, so no geometric rule tells
    them from the building. The panoramas do:
    :func:`~semantic_twin.materials.clutter_triangles` says
    which tracer triangles the segmentation calls a sign, a pole or a canopy, and
    a tip that lands on one is dropped. Passing ``None`` keeps every tip, which is
    what every published run before this did.
    """
    out = []
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)
    for origin in origins:
        alpha, horizontal, found = silhouette(geometry, origin, azimuths=azimuths, elevations=elevations)
        good = found & np.isfinite(horizontal) & (horizontal > floor_m)
        if not good.any():
            continue
        slant, direction = _tip_directions(alpha, horizontal, azimuth, good)
        if clutter_triangles is not None:
            slant, direction = _drop_clutter_tips(geometry, origin, slant, direction, clutter_triangles)
            if slant.size == 0:
                continue
        out.append(origin + slant[:, None] * direction)
    return np.concatenate(out) if out else np.empty((0, 3))


def visible(
    geometry: Any,
    origins: np.ndarray,
    targets: np.ndarray,
    *,
    epsilon_m: float = 1.0e-3,
) -> tuple[np.ndarray, np.ndarray]:
    """Whether each origin sees its target, and how far away it is.

    One shadow ray per pair, both arrays the same length. The clear test is on
    range and not on the hit flag, because a site sitting on the mesh is hit by
    its own connecting ray at the far end and that is a clear connection.
    """
    delta = targets - origins
    distance = np.linalg.norm(delta, axis=1)
    direction = delta / np.maximum(distance, 1.0e-12)[:, None]
    hit, travel, _, _ = geometry.intersect(origins + epsilon_m * direction, direction)
    clear = (~hit) | (travel >= distance - 2.0 * epsilon_m)
    return clear & (distance > 0.0), distance


def direct_from_sites(
    geometry: Any,
    origins: np.ndarray,
    sites: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    epsilon_m: float = 1.0e-3,
    chunk: int = 400_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Direct term and visible fraction, one shadow ray per standpoint per site.

    The estimator is the mean over all sites of ``visible / r**2``, with ``r`` the
    slant range. It is exact over the set rather than sampled from it, so a
    comparison between two site sets is not read through the noise of a draw.

    The mean is over every site and not only the visible ones. That is what makes
    the number independent of how densely the set is sampled: twice as many sites
    each stand for half as many antennas. It follows from taking antennas per
    square kilometre to be equal across cities, which fixes the count in a crop of
    given radius whatever the roofline does.

    Returns one value per standpoint.
    """
    direct = np.zeros(origins.shape[0], dtype=np.float64)
    seen = np.zeros(origins.shape[0], dtype=np.float64)
    if sites.shape[0] == 0:
        return direct, seen

    if weights is None:
        normalized = None
    else:
        raw = np.asarray(weights, dtype=np.float64)
        if raw.shape != (sites.shape[0],):
            raise ValueError(f"weights must have shape ({sites.shape[0]},), got {raw.shape}")
        if np.any(~np.isfinite(raw)) or np.any(raw < 0.0):
            raise ValueError("weights must be finite and nonnegative")
        total_weight = float(raw.sum())
        if total_weight <= 0.0:
            raise ValueError("weights must contain a positive value for a non-empty source set")
        # Keep the historical arithmetic when an explicit array merely spells
        # out the equal-weight default.
        normalized = None if np.all(raw == raw[0]) else raw / total_weight

    for i, origin in enumerate(origins):
        total = 0.0
        visible_count = 0.0
        for start in range(0, sites.shape[0], chunk):
            target = sites[start : start + chunk]
            clear, distance = visible(
                geometry,
                np.broadcast_to(origin, target.shape),
                target,
                epsilon_m=epsilon_m,
            )
            contribution = 1.0 / distance[clear] ** 2
            if normalized is not None:
                contribution *= normalized[start : start + chunk][clear]
            total += float(np.sum(contribution))
            visible_count += (
                float(np.sum(normalized[start : start + chunk][clear])) if normalized is not None else int(clear.sum())
            )
        direct[i] = total if normalized is not None else total / sites.shape[0]
        seen[i] = visible_count if normalized is not None else visible_count / sites.shape[0]
    return direct, seen


@dataclass(frozen=True)
class SourceSet:
    """An explicit set of base station sites, and how it was built.

    The facade tip law as the live estimator sees it. ``positions`` is what the
    estimator uses. The rest is provenance, so a run can say which resolutions
    produced its set without the caller carrying them alongside.
    """

    positions: np.ndarray
    cell_m: float
    dims: int
    azimuths: int
    builders: int
    floor_m: float = 0.0
    site_lift_m: float = 0.0
    name: str = "facade_tips"
    #: Optional relative power for each site. ``None`` keeps the historical
    #: equal-weight population. Values are normalised before either direct or
    #: next-event scoring, so the absolute scale is intentionally irrelevant.
    source_weights: np.ndarray | None = None

    law: ClassVar[str] = FACADE_TIP_LAW
    family: ClassVar[str] = FACADE_TIP_FAMILY

    def __post_init__(self) -> None:
        positions = np.asarray(self.positions)
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError(f"positions must have shape (sites, 3), got {positions.shape}")
        if not np.all(np.isfinite(positions)):
            raise ValueError("positions must be finite")
        object.__setattr__(self, "positions", positions)
        if self.source_weights is None:
            return
        weights = np.asarray(self.source_weights, dtype=np.float64)
        if weights.shape != (positions.shape[0],):
            raise ValueError(f"source_weights must have shape ({positions.shape[0]},), got {weights.shape}")
        if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("source_weights must be finite and nonnegative")
        if positions.shape[0] and float(weights.sum()) <= 0.0:
            raise ValueError("source_weights must contain a positive value for a non-empty source set")
        object.__setattr__(self, "source_weights", weights)

    def __len__(self) -> int:
        return int(self.positions.shape[0])

    def sites(self) -> np.ndarray:
        return self.positions

    def normalized_source_weights(self) -> np.ndarray:
        """Relative source probabilities, with equal weighting by default."""
        return normalized_source_weights(self)

    def weight_provenance(self) -> dict[str, Any]:
        """Summarize the source-weight measure without dumping its values.

        The digest uses :data:`WEIGHT_CANONICALIZATION`, so equivalent relative
        weights remain identical despite reduction or platform representation.
        """
        normalized = np.asarray(self.normalized_source_weights(), dtype=np.float64)
        digest = _normalized_weights_sha256(normalized)
        return {
            "mode": "explicit" if self.source_weights is not None else "equal",
            "count": int(normalized.size),
            "nonzero": int(np.count_nonzero(normalized)),
            "normalized_weights_sha256": digest,
            "canonicalization": WEIGHT_CANONICALIZATION,
        }

    def as_dict(self) -> dict[str, Any]:
        """The build resolutions, exactly as every shipped payload records them.

        Deliberately not the same thing as :meth:`describe`. This one is pinned by
        outputs on disk, so it stays the seven keys it has always been.
        """
        return {
            "sites": len(self),
            "cell_m": self.cell_m,
            "dims": self.dims,
            "azimuths": self.azimuths,
            "builders": self.builders,
            "floor_m": self.floor_m,
            "site_lift_m": self.site_lift_m,
        }

    def describe(self) -> dict[str, Any]:
        """What this source set is, including which law it stands for.

        The build resolutions were already recorded. The law was not, which is why
        a next event payload on disk cannot say what illuminated it.
        """
        description = {
            "name": self.name,
            "law": self.law,
            "family": self.family,
            "kind": "placed",
            "construction": "silhouette fan from the walk, thinned to one site per cell",
            **self.as_dict(),
        }
        if self.source_weights is not None:
            description["weight_provenance"] = self.weight_provenance()
        return description

    def direct(self, geometry: Any, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The line of sight term, exact over the whole set."""
        return direct_from_sites(
            geometry,
            np.atleast_2d(origins),
            self.positions,
            weights=self.source_weights,
        )


def normalized_source_weights(sources: Any) -> np.ndarray:
    """Return one normalized probability per explicit source site.

    Third-party ``PlacedIllumination`` implementations predate weighted sites,
    so the absence of ``source_weights`` means exactly the old uniform law.
    """
    sites = np.asarray(sources.sites(), dtype=np.float64)
    count = int(sites.shape[0])
    if count == 0:
        return np.empty(0, dtype=np.float64)
    raw = getattr(sources, "source_weights", None)
    if raw is None:
        return np.full(count, 1.0 / count, dtype=np.float64)
    weights = np.asarray(raw, dtype=np.float64)
    if weights.shape != (count,):
        raise ValueError(f"source_weights must have shape ({count},), got {weights.shape}")
    if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
        raise ValueError("source_weights must be finite and nonnegative")
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("source_weights must contain a positive value for a non-empty source set")
    return weights / total


def _normalized_weights_sha256(normalized: np.ndarray) -> str:
    """Hash normalized weights through a stable 15-significant-digit encoding."""
    values = np.asarray(normalized, dtype=np.float64)
    if np.any(~np.isfinite(values)):
        raise ValueError("normalized source weights must be finite")
    tokens = [format(float(value), ".15g") for value in values]
    payload = (f"{WEIGHT_CANONICALIZATION}\ncount={len(tokens)}\n" + "\n".join(tokens) + "\n").encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def build_source_set(
    geometry: Any,
    standpoints: np.ndarray,
    silhouette: Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    azimuths: int = 1440,
    elevations: int = 600,
    cell_m: float = 1.0,
    dims: int = 3,
    floor_m: float = 0.0,
    site_lift_m: float = SITE_LIFT_M,
    clutter_triangles: np.ndarray | None = None,
    rng: np.random.Generator | None = None,
) -> SourceSet:
    """Build the set from a walk, at the resolutions METHOD.md section 5.2 fixed.

    The defaults are the measured ones: 1440 azimuths, solid cells, and a cell
    size of 1 m. 128 standpoints is where the builder count stops paying, and that
    is the caller's to pass since it is a slice of their own walk.
    """
    cloud = silhouette_cloud(
        geometry,
        standpoints,
        silhouette,
        azimuths=azimuths,
        elevations=elevations,
        floor_m=floor_m,
        clutter_triangles=clutter_triangles,
    )
    positions = thin(cloud, cell_m, rng, dims=dims)
    # Straight up, rather than along the surface normal. A site is on a roof
    # edge, where up is the direction that clears the roof, and the normal there
    # is whichever of the two faces meeting at the edge the ray happened to hit.
    positions[:, 2] += site_lift_m
    return SourceSet(
        positions=positions,
        cell_m=cell_m,
        dims=dims,
        azimuths=azimuths,
        builders=int(np.asarray(standpoints).shape[0]),
        floor_m=floor_m,
        site_lift_m=site_lift_m,
    )

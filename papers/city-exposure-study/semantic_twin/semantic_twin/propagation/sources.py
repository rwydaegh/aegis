"""Where the base stations are, and how a traced path reaches one.

Everything else in this package marginalises the base station population into an
angular density `Q(u)` and reads it off the direction a ray escapes in. That
works and it is what the headline numbers are built on, but it assumes the
sources are far enough away that only direction matters. They are not: the
skyline sits 18 to 70 m from the head, while a bounce can happen tens of metres
away, so which rooftops are visible genuinely differs between the head and the
wall the ray bounced off.

This module carries the other way of doing it. The sources are an explicit set
of points on the roofline, and a path reaches one by connecting to it: at each
vertex, pick a site, cast one ray at it, and add its contribution if nothing is
in the way. That is next event estimation, standard in rendering. The visibility
question is then answered from the point where it is asked, so the position
dependence is exact rather than assumed away, and the line of sight part and the
bounced part come out of one estimator instead of two.

METHOD.md sections 5 and 5.1 carry the argument. The short version of how the
set is built: a ray fan goes up from each standpoint of the walk, the topmost hit
in each azimuth is a silhouette point, the union along the walk is the set of
surfaces that are skyline from the street, and that set is thinned to one site
per occupied cell so a wall seen edge on is not over weighted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

#: Sites closer than this to a connecting point are dropped from that
#: connection. A site is a point standing for a real antenna of finite size, and
#: `1/r**2` at a few centimetres is meaningless.
MIN_CONNECT_M = 0.5

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

    A ray fan goes up each azimuth from each standpoint and the topmost hit is
    the silhouette. This reads no site set and no threshold, which is what lets
    it judge one: a construction that misses much of this cloud is missing
    roofline that a pedestrian can see.

    ``floor_m`` drops hits nearer than that from the standpoint that found them,
    measured on the ground rather than in slant. It is meant for clutter, and it
    works on clutter for a reason worth stating: a lamp post only ever reaches
    the silhouette from close by, because from any distance a five metre post
    sits well under a twenty metre roofline and something taller is hit first.
    So a near cut removes the post from the cloud without removing the roofline
    behind it, which some other standpoint sees at a respectable distance anyway.

    ``clutter_triangles`` is the other half of that, and it is the half the range
    cut cannot do. A hoarding on a roof edge and a tree above a low wall both
    stand at roofline height and at roofline range, so no geometric rule tells
    them from the building. The panoramas do:
    :func:`~.semantic_binding.clutter_triangles` says which tracer triangles the
    segmentation calls a sign, a pole or a canopy, and a tip that lands on one is
    dropped. Passing ``None`` keeps every tip, which is what every published run
    before this did.
    """
    out = []
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)
    for origin in origins:
        alpha, horizontal, found = silhouette(geometry, origin, azimuths=azimuths, elevations=elevations)
        good = found & np.isfinite(horizontal) & (horizontal > floor_m)
        if not good.any():
            continue
        slant = horizontal[good] / np.maximum(np.cos(alpha[good]), 1.0e-9)
        direction = np.stack(
            [
                np.cos(alpha[good]) * np.cos(azimuth[good]),
                np.cos(alpha[good]) * np.sin(azimuth[good]),
                np.sin(alpha[good]),
            ],
            axis=-1,
        )
        if clutter_triangles is not None:
            # One more cast along the directions already chosen, only to read
            # which triangle the tip sits on. A thousand rays beside the fan's
            # near million, so the cost does not show.
            _, _, _, face = geometry.intersect(np.broadcast_to(origin, direction.shape), direction)
            face = np.asarray(face, dtype=np.int64)
            inside = np.clip(face, 0, clutter_triangles.size - 1)
            keep = (face < 0) | (face >= clutter_triangles.size) | ~clutter_triangles[inside]
            if not keep.any():
                continue
            slant, direction = slant[keep], direction[keep]
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

    for i, origin in enumerate(origins):
        total = 0.0
        visible_count = 0
        for start in range(0, sites.shape[0], chunk):
            target = sites[start : start + chunk]
            clear, distance = visible(
                geometry,
                np.broadcast_to(origin, target.shape),
                target,
                epsilon_m=epsilon_m,
            )
            total += float(np.sum(1.0 / distance[clear] ** 2))
            visible_count += int(clear.sum())
        direct[i] = total / sites.shape[0]
        seen[i] = visible_count / sites.shape[0]
    return direct, seen


@dataclass(frozen=True)
class SourceSet:
    """An explicit set of base station sites, and how it was built.

    ``positions`` is what the estimator uses. The rest is provenance, so a run
    can say which resolutions produced its set without the caller carrying them
    alongside.
    """

    positions: np.ndarray
    cell_m: float
    dims: int
    azimuths: int
    builders: int
    floor_m: float = 0.0
    site_lift_m: float = 0.0

    def __len__(self) -> int:
        return int(self.positions.shape[0])

    def as_dict(self) -> dict[str, Any]:
        return {
            "sites": len(self),
            "cell_m": self.cell_m,
            "dims": self.dims,
            "azimuths": self.azimuths,
            "builders": self.builders,
            "floor_m": self.floor_m,
            "site_lift_m": self.site_lift_m,
        }

    def direct(self, geometry: Any, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The line of sight term, exact over the whole set."""
        return direct_from_sites(geometry, np.atleast_2d(origins), self.positions)


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
    size of 1 m. 128 standpoints is where the builder count stops paying, and
    that is the caller's to pass since it is a slice of their own walk.
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


@dataclass
class NextEventGather:
    """Connects every path vertex to a sampled base station site.

    This plugs into :meth:`SbrTracer.trace` as its ``gather``, which already
    hands over everything a connection needs: where the vertex is, the normal
    already turned to face the incoming ray, the throughput after this
    interaction's reflectance, and the Rayleigh coherent share whose complement
    is the diffuse lobe.

    Only the diffuse lobe is connected. A connection to a point source has no
    chance of being a valid mirror path, so the coherent share is left to the
    ray continuation and to image sources. That is a statement about which term
    this estimator owns, not an approximation inside it.

    It draws from its own generator, so attaching it does not move the traced
    result by a single bit.

    The accumulated quantity is the bounced part of ``chi``, per source, averaged
    over the set. Divide by the ray count and multiply by ``4 pi`` to read it as
    an integral of arriving radiance over the sphere, which :meth:`chi_bounce`
    does. The line of sight part is not accumulated here: it is exact and
    :meth:`SourceSet.direct` computes it in one call.
    """

    geometry: Any
    sources: SourceSet
    rng: np.random.Generator
    samples: int = 1
    max_order: int = 8
    epsilon_m: float = 1.0e-3
    #: How far the connection start is lifted off its own surface. Set from the
    #: sensitivity measured in tests/test_next_event.py, not by taste.
    lift_m: float = 1.0e-2
    min_connect_m: float = MIN_CONNECT_M

    total: float = 0.0
    by_order: np.ndarray = field(init=False)
    connections: int = 0
    cleared: int = 0
    rays: int = 0

    def __post_init__(self) -> None:
        self.by_order = np.zeros(self.max_order + 1, dtype=np.float64)

    def begin(self, origin: np.ndarray, count: int) -> None:
        del origin
        self.rays += int(count)

    def vertex(
        self,
        index: np.ndarray,
        position: np.ndarray,
        incoming: np.ndarray,
        normal: np.ndarray,
        throughput: np.ndarray,
        share: np.ndarray,
        order: np.ndarray,
        path_length: np.ndarray,
        face: np.ndarray | None = None,
    ) -> None:
        del index, incoming, path_length, face
        sites = self.sources.positions
        if sites.shape[0] == 0 or position.shape[0] == 0:
            return

        # The diffuse lobe of a Lambertian reflector, whose albedo is already in
        # `throughput`. Splitting it out here is what keeps the coherent share
        # from being counted twice, once by this connection and once by the
        # mirror direction the tracer continues in.
        lobe = throughput * (1.0 - share) / np.pi
        bin_order = np.minimum(np.asarray(order, dtype=np.int64), self.max_order)

        for _ in range(self.samples):
            draw = self.rng.integers(0, sites.shape[0], size=position.shape[0])
            target = sites[draw]
            to_site = target - position
            distance = np.linalg.norm(to_site, axis=1)
            direction = to_site / np.maximum(distance, 1.0e-12)[:, None]
            cos_out = np.einsum("ij,ij->i", direction, normal)

            # Only the front of the surface can be reached, and a site almost on
            # top of the vertex is not a physical connection.
            worth = (cos_out > 0.0) & (distance > self.min_connect_m)
            self.connections += int(worth.sum())
            if not np.any(worth):
                continue

            # The tracer leaves each vertex a hair *behind* its surface, because
            # it advances by the hit distance plus an epsilon along the incoming
            # ray. A connection fired from there can cross back through the same
            # face and read as blocked by the very surface it is standing on. So
            # the start is lifted along the normal first, which is the side the
            # site has to be on anyway for `cos_out` to be positive.
            start = position[worth] + self.lift_m * normal[worth] + self.epsilon_m * direction[worth]
            hit, travel, _, _ = self.geometry.intersect(start, direction[worth])
            clear = (~hit) | (travel >= distance[worth] - 2.0 * self.epsilon_m)
            if not np.any(clear):
                continue

            weight = lobe[worth][clear] * cos_out[worth][clear] / distance[worth][clear] ** 2
            self.cleared += int(clear.sum())
            self.total += float(weight.sum())
            np.add.at(self.by_order, bin_order[worth][clear], weight)

    def chi_bounce(self) -> float:
        """The bounced part, as an integral of arriving radiance over the sphere.

        Rays leave the head uniformly, so their density on the sphere is
        ``1/(4 pi)`` and the estimator of ``integral L dOmega`` is the sum times
        ``4 pi`` over the ray count. The extra division by ``samples`` averages
        the connections made at each vertex.
        """
        if self.rays == 0:
            return 0.0
        return 4.0 * np.pi * self.total / (self.rays * self.samples)

    def chi_by_order(self) -> np.ndarray:
        """The same, kept per bounce, so the surplus can be read term by term."""
        if self.rays == 0:
            return np.zeros_like(self.by_order)
        return 4.0 * np.pi * self.by_order / (self.rays * self.samples)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chi_bounce": self.chi_bounce(),
            "chi_by_order": [float(v) for v in self.chi_by_order()],
            "connections": self.connections,
            "cleared": self.cleared,
            "clear_fraction": self.cleared / max(self.connections, 1),
            "rays": self.rays,
            "samples": self.samples,
        }


@dataclass
class MultiGather:
    """Fans the tracer's one gather hook out to several observers.

    The tracer takes a single ``gather``, and the monostatic return and the next
    event connection both want it. Neither draws from the tracer's generator, so
    running them together changes nothing about either.
    """

    observers: tuple[Any, ...]

    def begin(self, origin: np.ndarray, count: int) -> None:
        for observer in self.observers:
            observer.begin(origin, count)

    def vertex(self, *args: Any, **kwargs: Any) -> None:
        for observer in self.observers:
            observer.vertex(*args, **kwargs)

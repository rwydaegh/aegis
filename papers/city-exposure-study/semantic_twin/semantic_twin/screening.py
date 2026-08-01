"""Screen candidate sites on Street View link-graph coverage before spending on tiles.

A site is useless to this study when its panoramas are not linked to each other.
The walk is the link graph traversed, so zero neighbour links means no walk at
all, and only official captures carry links. Screening therefore asks four
questions of a candidate, and asks them with metadata requests only, never with
tiles or imagery:

1. How many panoramas stand inside the acquisition disc.
2. How far apart they are, as the median nearest-neighbour distance. Trekker
   capture of a pedestrianised square puts panoramas metres apart where
   pedestrians actually stand, while a car track down a street gives ten metres
   and only along the carriageway.
3. How many distinct capture dates the set carries. One date is a coherent
   scene, several dates mean the panoramas disagree with each other and with the
   tile mesh about scaffolding, market stalls and parked vehicles.
4. Whether the link graph over those panoramas is connected, checked twice: once
   by breadth-first traversal from the site centre, and once by probing points
   the traversal never visited and asking whether the panorama returned there
   was reachable.

The traversal and the probes are separate on purpose. A traversal alone can only
report the component it started in, so it can never discover that it missed one.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from datetime import date as date_type
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

EARTH_RADIUS_M = 6371008.8

# Screening radius. Smaller than any acquisition radius on purpose: it asks
# whether panoramas stand where a pedestrian would stand near the centre of the
# square, not whether the surrounding street network is covered.
DEFAULT_SCREEN_RADIUS_M = 60.0

# Traversal bound. A dense trekker square can carry several hundred panoramas
# inside 60 m and the screening budget is one metadata request per panorama, so
# the traversal stops and says so rather than running away.
DEFAULT_MAX_PANORAMAS = 400

# Search radius handed to each probe lookup. Wide enough that a probe standing
# on a pavement still finds the nearest panorama, narrow enough that probes at
# opposite ends of the disc cannot both collapse onto the same one.
PROBE_SEARCH_RADIUS_M = 25.0

# Where the probes stand, as fractions of the screening radius, and how many per
# ring. Centre plus two rings is enough to tell a walk that crosses the square
# from one that only runs along one edge of it.
DEFAULT_RINGS = (0.55, 0.95)
DEFAULT_PER_RING = 8

# A probe point counts as reached when a walk panorama stands within this
# distance of it. Twenty metres is the scale at which a facade seen from the
# walk is still the facade behind the probe.
COVERAGE_RADIUS_M = 20.0

# A capture within this many years of today counts as recent. Six years is one
# tile refresh cycle plus slack, and the point of the number is only to separate
# a 2024 capture from a 2012 one, not to draw a sharp line.
DEFAULT_RECENCY_YEARS = 6

# Azimuth sectors about the site centre, and the radius inside which a panorama
# has no meaningful azimuth. Sixteen sectors is 22.5 degrees each, which is finer
# than the four to six street mouths a square typically has and coarse enough
# that one missing panorama does not empty a sector.
AZIMUTH_BINS = 16
AZIMUTH_MIN_RADIUS_M = 5.0


def date_today() -> date_type:
    """Today, as its own function so a test can say what today is."""
    return date_type.today()


class MetadataSource(Protocol):
    """The two metadata lookups screening needs, so tests can supply their own."""

    def by_pano_id(self, pano_id: str) -> dict[str, Any]: ...

    def by_location(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Candidate:
    """One site put forward for screening."""

    key: str
    name: str
    country: str
    lat: float
    lon: float
    built_form: str

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("candidate key must not be empty")
        if not math.isfinite(self.lat) or not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"{self.key}: latitude must be finite and in [-90, 90]")
        if not math.isfinite(self.lon) or not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"{self.key}: longitude must be finite and in [-180, 180]")


@dataclass(frozen=True)
class Panorama:
    """One panorama as the metadata endpoint describes it."""

    pano_id: str
    lat: float
    lon: float
    date: str
    copyright_text: str
    links: tuple[str, ...] = ()
    tilt_deg: float | None = None
    roll_deg: float | None = None

    @property
    def has_orientation(self) -> bool:
        """Whether the capture carries a pose solution rather than a level default.

        ``tilt = 90`` with ``roll = 0`` exactly is the tell for a user photosphere
        with no orientation metadata behind it, which the panorama module already
        treats as degenerate.
        """
        if self.tilt_deg is None and self.roll_deg is None:
            return False
        return not (self.tilt_deg == 90.0 and self.roll_deg == 0.0)


def panorama_from_metadata(metadata: dict[str, Any]) -> Panorama | None:
    """Read one metadata response, or return ``None`` when it found no panorama."""
    pano_id = metadata.get("panoId")
    if not isinstance(pano_id, str) or not pano_id:
        return None
    links = tuple(
        str(link["panoId"])
        for link in metadata.get("links", [])
        if isinstance(link, dict) and isinstance(link.get("panoId"), str) and link["panoId"]
    )
    return Panorama(
        pano_id=pano_id,
        lat=float(metadata["lat"]),
        lon=float(metadata["lng"]),
        date=str(metadata.get("date", "")),
        copyright_text=str(metadata.get("copyright", "")),
        links=links,
        tilt_deg=None if "tilt" not in metadata else float(metadata["tilt"]),
        roll_deg=None if "roll" not in metadata else float(metadata["roll"]),
    )


def offsets_m(lat_deg: float, lon_deg: float, panoramas: Sequence[Panorama]) -> np.ndarray:
    """Local east and north offsets in metres from a site centre.

    The equirectangular approximation is used deliberately. Over the tens of
    metres screening cares about, its error against the ellipsoid is below a
    millimetre, and no screening decision turns on a millimetre.
    """
    if not panoramas:
        return np.zeros((0, 2), dtype=np.float64)
    lat0 = math.radians(lat_deg)
    lats = np.array([p.lat for p in panoramas], dtype=np.float64)
    lons = np.array([p.lon for p in panoramas], dtype=np.float64)
    east = np.radians(lons - lon_deg) * EARTH_RADIUS_M * math.cos(lat0)
    north = np.radians(lats - lat_deg) * EARTH_RADIUS_M
    return np.column_stack([east, north])


def nearest_neighbour_distances(points: np.ndarray) -> np.ndarray:
    """Distance from each point to its closest other point, in the input order."""
    points = np.asarray(points, dtype=np.float64)
    if points.shape[0] < 2:
        return np.zeros((0,), dtype=np.float64)
    deltas = points[:, None, :] - points[None, :, :]
    distances = np.linalg.norm(deltas, axis=2)
    np.fill_diagonal(distances, np.inf)
    return distances.min(axis=1)


def link_lengths_m(panoramas: Sequence[Panorama], positions: np.ndarray) -> np.ndarray:
    """Length of every undirected link whose two endpoints are both in the set."""
    index = {panorama.pano_id: number for number, panorama in enumerate(panoramas)}
    seen: set[tuple[int, int]] = set()
    lengths: list[float] = []
    for panorama in panoramas:
        here = index[panorama.pano_id]
        for neighbour in panorama.links:
            there = index.get(neighbour)
            if there is None:
                continue
            edge = (min(here, there), max(here, there))
            if edge in seen:
                continue
            seen.add(edge)
            lengths.append(float(np.linalg.norm(positions[here] - positions[there])))
    return np.array(lengths, dtype=np.float64)


def connected_components(panoramas: Sequence[Panorama]) -> list[set[str]]:
    """Components of the undirected link graph restricted to the given panoramas."""
    present = {panorama.pano_id for panorama in panoramas}
    adjacency: dict[str, set[str]] = {pano_id: set() for pano_id in present}
    for panorama in panoramas:
        for neighbour in panorama.links:
            if neighbour in present:
                adjacency[panorama.pano_id].add(neighbour)
                adjacency[neighbour].add(panorama.pano_id)

    components: list[set[str]] = []
    unvisited = set(present)
    while unvisited:
        start = unvisited.pop()
        component = {start}
        frontier = [start]
        while frontier:
            current = frontier.pop()
            for neighbour in adjacency[current]:
                if neighbour not in component:
                    component.add(neighbour)
                    frontier.append(neighbour)
        unvisited -= component
        components.append(component)
    return sorted(components, key=len, reverse=True)


def probe_offsets(radius_m: float, rings: Iterable[float] = DEFAULT_RINGS, per_ring: int = DEFAULT_PER_RING) -> np.ndarray:
    """Centre plus evenly spaced points on each ring, as local east and north metres."""
    offsets = [(0.0, 0.0)]
    for fraction in rings:
        reach = radius_m * fraction
        for step in range(per_ring):
            bearing = 2.0 * math.pi * step / per_ring
            offsets.append((reach * math.sin(bearing), reach * math.cos(bearing)))
    return np.array(offsets, dtype=np.float64)


def probe_points(
    lat_deg: float,
    lon_deg: float,
    radius_m: float,
    rings: Iterable[float] = DEFAULT_RINGS,
    per_ring: int = DEFAULT_PER_RING,
) -> list[tuple[float, float]]:
    """The same probe points as latitude and longitude."""
    lat0 = math.radians(lat_deg)
    return [
        (
            lat_deg + math.degrees(north / EARTH_RADIUS_M),
            lon_deg + math.degrees(east / (EARTH_RADIUS_M * math.cos(lat0))),
        )
        for east, north in probe_offsets(radius_m, rings, per_ring)
    ]


def azimuth_spread(walk_positions: np.ndarray, *, bins: int = AZIMUTH_BINS, min_radius_m: float = AZIMUTH_MIN_RADIUS_M) -> float:
    """Fraction of the azimuth sectors about the site centre that the walk enters.

    This is the measure that a straight line cannot cheat. A dense line of
    panoramas driven through the middle of a square fills two opposite sectors
    and scores about an eighth, however many panoramas are in it and however
    tightly they are spaced, while a walk that goes round the square fills nearly
    all of them.

    Panoramas closer to the centre than ``min_radius_m`` are ignored, because
    their azimuth is set by centimetres of position noise rather than by where
    the camera went.

    Extent is the thing this study is short of. Widening a site from 60 m to 80 m
    was measured to lift achievable surface coverage from 30.6 to 44.8 percent of
    scene area, which is worth more than tripling the panorama count inside 60 m,
    so spatial spread outranks density and the gate has to be built on it.
    """
    if walk_positions.shape[0] == 0:
        return 0.0
    radii = np.linalg.norm(walk_positions, axis=1)
    far = walk_positions[radii >= min_radius_m]
    if far.shape[0] == 0:
        return 0.0
    sectors = np.floor((np.arctan2(far[:, 0], far[:, 1]) % (2.0 * math.pi)) / (2.0 * math.pi / bins)).astype(int)
    return float(len(set(sectors.tolist())) / bins)


def _reaches(positions: np.ndarray, targets: np.ndarray, reach_m: float) -> np.ndarray:
    if positions.shape[0] == 0:
        return np.zeros(targets.shape[0], dtype=bool)
    distances = np.linalg.norm(targets[:, None, :] - positions[None, :, :], axis=2)
    return distances.min(axis=1) <= reach_m


def coverage_fraction(
    walk_positions: np.ndarray,
    all_positions: np.ndarray,
    radius_m: float,
    *,
    reach_m: float = COVERAGE_RADIUS_M,
) -> float:
    """How much of the reachable square one walk covers.

    This is what separates a walk that crosses the square from one that runs
    along a single edge of it. Both can have the same panorama count and the same
    spacing, and only one of them sees the facades on the far side.

    The denominator is the probe points that *any* capture of the site reaches,
    not all of them. A probe point standing inside the Doge's Palace can never be
    reached by any camera, and counting it against the walk would penalise a
    small square for being smaller than the screening disc rather than for being
    badly covered.
    """
    targets = probe_offsets(radius_m)
    reachable = _reaches(all_positions, targets, reach_m)
    if not reachable.any():
        return 0.0
    return float(np.mean(_reaches(walk_positions, targets, reach_m)[reachable]))


@dataclass
class Traversal:
    """What a breadth-first walk of the link graph found."""

    panoramas: dict[str, Panorama] = field(default_factory=dict)
    requests: int = 0
    truncated: bool = False
    seed: str | None = None


def _is_inside(candidate: Candidate, panorama: Panorama, radius_m: float) -> bool:
    return float(np.linalg.norm(offsets_m(candidate.lat, candidate.lon, [panorama])[0])) <= radius_m


def expand(
    source: MetadataSource,
    candidate: Candidate,
    seeds: Sequence[Panorama],
    result: Traversal,
    *,
    radius_m: float = DEFAULT_SCREEN_RADIUS_M,
    max_panoramas: int = DEFAULT_MAX_PANORAMAS,
    workers: int = 8,
) -> Traversal:
    """Walk the link graph outwards from the given seeds, into ``result``.

    Panoramas outside ``radius_m`` are fetched, because their coordinates are the
    only way to learn that they are outside, but they are not expanded. The walk
    therefore costs one request per interior panorama plus one per boundary
    panorama, and never leaks down the street network.
    """
    for seed in seeds:
        result.panoramas.setdefault(seed.pano_id, seed)
    frontier = [seed for seed in seeds if _is_inside(candidate, seed, radius_m)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while frontier:
            wanted: list[str] = []
            for panorama in frontier:
                for neighbour in panorama.links:
                    if neighbour not in result.panoramas and neighbour not in wanted:
                        wanted.append(neighbour)
            if not wanted:
                break
            if len(result.panoramas) + len(wanted) > max_panoramas:
                wanted = wanted[: max(0, max_panoramas - len(result.panoramas))]
                result.truncated = True
            if not wanted:
                break
            fetched = list(pool.map(source.by_pano_id, wanted))
            result.requests += len(wanted)
            frontier = []
            for metadata in fetched:
                panorama = panorama_from_metadata(metadata)
                if panorama is None:
                    continue
                result.panoramas[panorama.pano_id] = panorama
                if _is_inside(candidate, panorama, radius_m):
                    frontier.append(panorama)
            if result.truncated:
                break
    return result


def traverse(
    source: MetadataSource,
    candidate: Candidate,
    *,
    radius_m: float = DEFAULT_SCREEN_RADIUS_M,
    max_panoramas: int = DEFAULT_MAX_PANORAMAS,
    workers: int = 8,
) -> Traversal:
    """Locate a panorama at the site centre and walk the link graph out from it."""
    result = Traversal()
    seed = panorama_from_metadata(source.by_location(candidate.lat, candidate.lon, radius_m))
    result.requests += 1
    if seed is None:
        return result
    result.seed = seed.pano_id
    return expand(source, candidate, [seed], result, radius_m=radius_m, max_panoramas=max_panoramas, workers=workers)


def probe(
    source: MetadataSource,
    candidate: Candidate,
    reachable: set[str],
    *,
    radius_m: float = DEFAULT_SCREEN_RADIUS_M,
    rings: Sequence[float] = DEFAULT_RINGS,
    per_ring: int = DEFAULT_PER_RING,
    workers: int = 8,
) -> dict[str, Any]:
    """Ask independent lookups whether the traversal missed a component.

    Every probe that lands on a panorama the traversal never reached is direct
    evidence of a second component, which is the failure the study cannot
    tolerate: an unlinked panorama is a panorama the walk can never step to.
    """
    points = probe_points(candidate.lat, candidate.lon, radius_m, rings, per_ring)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        responses = list(pool.map(lambda point: source.by_location(point[0], point[1], PROBE_SEARCH_RADIUS_M), points))
    hits: list[str] = []
    unreached: dict[str, Panorama] = {}
    empty = 0
    for metadata in responses:
        panorama = panorama_from_metadata(metadata)
        if panorama is None:
            empty += 1
            continue
        hits.append(panorama.pano_id)
        if panorama.pano_id not in reachable:
            unreached[panorama.pano_id] = panorama
    return {
        "probe_count": len(points),
        "requests": len(points),
        "probes_with_a_panorama": len(hits),
        "probes_without_a_panorama": empty,
        "distinct_panoramas_probed": len(set(hits)),
        "unreached_panoramas": sorted(unreached),
        "unreached": list(unreached.values()),
    }


def _percentile(values: np.ndarray, fraction: float) -> float | None:
    if values.size == 0:
        return None
    return float(np.percentile(values, fraction))


def _span_m(points: np.ndarray) -> float:
    if points.shape[0] < 2:
        return 0.0
    return float(np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2).max())


def provider_of(panorama: Panorama) -> str:
    """The capture owner named in the copyright string, or ``unknown``.

    Not every linked capture belongs to the map provider. Krakow's Rynek is
    covered by a third-party virtual-tour company whose panoramas are linked and
    do carry a pose solution, which is usable, and Ghent's is a provider car
    track, which is also usable. The distinction is worth recording because the
    two differ in resolution and in how the camera was carried, not because one
    of them disqualifies a site.
    """
    text = panorama.copyright_text
    marker = "Photo by:"
    if marker in text:
        return text.split(marker, 1)[1].strip() or "unknown"
    return text.strip().lstrip("(c)@ ") or "unknown"


def epochs(panoramas: Sequence[Panorama], positions: np.ndarray, radius_m: float) -> list[dict[str, Any]]:
    """Summarise the link graph one capture date at a time.

    Panoramas link to their neighbours within a capture run, not across capture
    runs, so the whole-set component count mostly measures how many times the
    square has been driven or walked rather than whether any one walk is whole.
    The quantity the study actually needs is the largest set of panoramas that
    share a date and are linked to each other, because that is one temporally
    coherent walk through a scene that agrees with itself about scaffolding,
    market stalls and parked vehicles.
    """
    index = {panorama.pano_id: number for number, panorama in enumerate(panoramas)}
    summaries: list[dict[str, Any]] = []
    for date in sorted({panorama.date for panorama in panoramas if panorama.date}):
        members = [panorama for panorama in panoramas if panorama.date == date]
        components = connected_components(members)
        largest = components[0] if components else set()
        walk = [panorama for panorama in members if panorama.pano_id in largest]
        walk_positions = np.array([positions[index[panorama.pano_id]] for panorama in walk]) if walk else np.zeros((0, 2))
        spacings = nearest_neighbour_distances(walk_positions)
        summaries.append(
            {
                "date": date,
                "panorama_count": len(members),
                "components": [len(component) for component in components],
                "walk_count": len(walk),
                "walk_fraction_of_date": len(walk) / len(members),
                "year": int(date[:4]) if date[:4].isdigit() else None,
                "median_spacing_m": _percentile(spacings, 50.0),
                "span_m": _span_m(walk_positions),
                "coverage": coverage_fraction(walk_positions, positions, radius_m),
                "azimuth_spread": azimuth_spread(walk_positions),
                "providers": sorted({provider_of(panorama) for panorama in walk}),
            }
        )
    return sorted(summaries, key=lambda summary: (-summary["walk_count"], summary["date"]))


def screen(
    source: MetadataSource,
    candidate: Candidate,
    *,
    radius_m: float = DEFAULT_SCREEN_RADIUS_M,
    max_panoramas: int = DEFAULT_MAX_PANORAMAS,
    workers: int = 8,
    recency_years: int = DEFAULT_RECENCY_YEARS,
) -> dict[str, Any]:
    """Screen one candidate and return its row of the screening table."""
    traversal = traverse(source, candidate, radius_m=radius_m, max_panoramas=max_panoramas, workers=workers)
    reachable = set(traversal.panoramas)
    probes = probe(source, candidate, reachable, radius_m=radius_m, workers=workers)

    # A walk can only ever report the component it started in, so anything the
    # probes found outside that component is walked in turn. Without this the
    # component count is one by construction and says nothing.
    orphans = probes.pop("unreached")
    if orphans:
        expand(source, candidate, orphans, traversal, radius_m=radius_m, max_panoramas=max_panoramas, workers=workers)

    everything = list(traversal.panoramas.values())
    positions_all = offsets_m(candidate.lat, candidate.lon, everything)
    inside_mask = np.linalg.norm(positions_all, axis=1) <= radius_m if everything else np.zeros((0,), dtype=bool)
    interior = [panorama for panorama, keep in zip(everything, inside_mask, strict=True) if keep]
    positions = offsets_m(candidate.lat, candidate.lon, interior)

    spacings = nearest_neighbour_distances(positions)
    lengths = link_lengths_m(interior, positions)
    components = connected_components(interior)
    dates = sorted({panorama.date for panorama in interior if panorama.date})
    without_orientation = [panorama.pano_id for panorama in interior if not panorama.has_orientation]
    unlinked = [panorama.pano_id for panorama in interior if not panorama.links]

    largest = len(components[0]) if components else 0
    by_epoch = epochs(interior, positions, radius_m)

    # The photogrammetric tiles are current and a panorama is not, so an old
    # capture registers semantic labels against geometry that has since changed.
    # Rooflines change least, which is exactly why the skyline residual will not
    # report it, so the age is carried as its own column rather than folded into
    # a score. The largest recent walk is reported beside the largest walk so the
    # trade between the two is visible instead of decided here.
    this_year = date_today().year
    recent = next(
        (
            epoch
            for epoch in by_epoch
            if epoch["year"] is not None and this_year - epoch["year"] <= recency_years and epoch["walk_count"] >= 2
        ),
        None,
    )
    records = [
        {
            "pano_id": panorama.pano_id,
            "east_m": round(float(position[0]), 2),
            "north_m": round(float(position[1]), 2),
            "date": panorama.date,
            "provider": provider_of(panorama),
            "links": list(panorama.links),
            "has_orientation": panorama.has_orientation,
        }
        for panorama, position in zip(interior, positions, strict=True)
    ]
    best = by_epoch[0] if by_epoch else None

    # A probe landing on an unlinked photosphere is not a connectivity failure,
    # it only means a tourist upload happened to be the nearest panorama to that
    # point. Only a linked panorama outside the traversal is evidence of a
    # second walkable component.
    linked_ids = {panorama.pano_id for panorama in interior if panorama.links}
    missed = [pano_id for pano_id in probes["unreached_panoramas"] if pano_id in linked_ids]

    return {
        "key": candidate.key,
        "name": candidate.name,
        "country": candidate.country,
        "built_form": candidate.built_form,
        "lat": candidate.lat,
        "lon": candidate.lon,
        "screen_radius_m": radius_m,
        "panorama_count": len(interior),
        "panoramas_fetched": len(everything),
        "median_spacing_m": _percentile(spacings, 50.0),
        "spacing_p10_m": _percentile(spacings, 10.0),
        "spacing_p90_m": _percentile(spacings, 90.0),
        "median_link_length_m": _percentile(lengths, 50.0),
        "link_count": int(lengths.size),
        "distinct_dates": len(dates),
        "dates": dates,
        "components": [len(component) for component in components],
        "largest_component": largest,
        "largest_component_fraction": (largest / len(interior)) if interior else 0.0,
        "reachable_from_centre": sum(1 for panorama in interior if panorama.pano_id in reachable),
        "linked_panoramas": len(linked_ids),
        "unlinked_panoramas": len(unlinked),
        "panoramas_without_orientation": len(without_orientation),
        "epochs": by_epoch,
        "walk_date": best["date"] if best else None,
        "walk_count": best["walk_count"] if best else 0,
        "walk_spacing_m": best["median_spacing_m"] if best else None,
        "walk_year": best["year"] if best else None,
        "walk_age_years": (this_year - best["year"]) if best and best["year"] else None,
        "recent_walk": recent,
        "walk_span_m": best["span_m"] if best else 0.0,
        "walk_fraction_of_date": best["walk_fraction_of_date"] if best else 0.0,
        "walk_coverage": best["coverage"] if best else 0.0,
        "walk_azimuth_spread": best["azimuth_spread"] if best else 0.0,
        "walk_providers": best["providers"] if best else [],
        "connected": bool(best) and best["walk_fraction_of_date"] >= 0.9 and best["azimuth_spread"] >= 0.6,
        "linked_panoramas_the_walk_missed": missed,
        "probes": probes,
        "requests": traversal.requests + probes["requests"],
        "traversal_truncated": traversal.truncated,
        "seed_pano_id": traversal.seed,
        "panoramas": records,
    }


def rank(rows: Sequence[dict[str, Any]], *, minimum_walk: int = 20) -> list[dict[str, Any]]:
    """Order screened rows by acquisition priority.

    Connectivity is a gate rather than a term, because a fragmented link graph
    does not give a worse walk, it gives no walk. The gate is operational: the
    largest single-date component must hold at least nine tenths of that date's
    panoramas, and the walk must enter at least three fifths of the azimuth
    sectors about the centre, so that a line driven through a square does not
    pass as a walk of the square. Among the sites that clear it, the ordering is
    by the size of that walk, with spacing as the tiebreak. Spacing alone would
    put a five-panorama alley above a square the trekker crossed in every
    direction, and the walk is what the study samples.
    """
    ordered = sorted(
        rows,
        key=lambda row: (
            not (row["connected"] and row["walk_count"] >= minimum_walk),
            -row["walk_count"],
            row["walk_spacing_m"] if row["walk_spacing_m"] is not None else math.inf,
        ),
    )
    return [dict(row, rank=number + 1) for number, row in enumerate(ordered)]

"""A walk along the street the panoramas were taken from.

:func:`~semantic_twin.propagation.walk.build_walk` lays a grid over a disc,
keeps the squares whose ground is walkable, and orders the survivors by a greedy
nearest neighbour chain. That gives an ordering, not a route. The standpoints it
produces sit wherever the grid happened to fall, and most of them are nowhere
near a camera.

This module builds the other thing. The guarantee behind the method is that a
photograph taken at a point sees the surfaces that scatter energy into that
point, and BOUNCE_BUDGET.md measures how far that guarantee travels: the first
interaction lands on photographed surface with probability 0.999 at a panorama
position, 0.99 within ten metres of one, and about 0.1 past forty. So a
standpoint with no panorama near it is a standpoint with no evidence behind it,
and the fix is to stand where the cameras stood.

Street View and Mapillary both publish a link structure along the street,
because a car or a trekker drove or walked it. Street View names each
panorama's neighbours directly. Mapillary publishes sequences, the ordered
frames of one continuous drive. Either way the provider has already recorded
which standpoints are next to which, so ordering the cameras into a route needs
no synthetic routing and no street map: the route is the shortest way through
that link graph that stands at every camera the study admitted.

Nothing here replaces ``build_walk``. Every published run rests on it and it is
left alone. :func:`panorama_walk` returns the same :class:`~.walk.Walk` a caller
already knows how to consume, so a script can choose between the two by which
function it calls.
"""

from __future__ import annotations

import heapq
import json
import pathlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..geo import EnuFrame
from .street import cached_walking_route, polyline_enu, site_anchor
from .walk import SKY_PROBE, Walk, clearance, ground_height, sky_visibility

#: Above this many stations the shortest route is searched rather than proved.
#: Held-Karp costs ``n * 2**(n - 1)`` inner steps, which is a fifth of a second
#: at twelve stations and about a second at fifteen. No site in this study has
#: more than twelve admitted stations, so the exact answer is always the one
#: that ships, and the limit exists so a larger site degrades to a recorded
#: heuristic rather than to a hang.
EXACT_ORDER_LIMIT = 15

#: Pedestrian head height above the ground under the camera. The camera itself
#: rides at ``camera_height_m`` in the scene config, 2.5 m at every site, which
#: is a car roof and not a head.
HEAD_HEIGHT_M = 1.5


@dataclass(frozen=True)
class LinkGraph:
    """Panorama positions and the provider's own links between them.

    ``position`` is in the scene ENU frame, x east and y north, and holds the
    provider's published position rather than the registered one. The two are
    different quantities and the difference is the point of the registration:
    at Brussels the fit moves a camera 0.65 to 5.63 m. The graph is used for
    topology and for road distance only, and every standpoint this module emits
    comes from the registered pose.
    """

    position: dict[str, np.ndarray]
    neighbours: dict[str, tuple[str, ...]]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.position)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self.neighbours.values()) // 2

    def distances_from(self, source: str) -> dict[str, float]:
        """Road distance along the links from one node to every node it reaches."""
        if source not in self.position:
            raise KeyError(f"{source} is not in the link graph")
        best = {source: 0.0}
        queue: list[tuple[float, str]] = [(0.0, source)]
        while queue:
            reached, node = heapq.heappop(queue)
            if reached > best.get(node, np.inf):
                continue
            here = self.position[node]
            for other in self.neighbours.get(node, ()):
                step = reached + float(np.linalg.norm(self.position[other] - here))
                if step < best.get(other, np.inf):
                    best[other] = step
                    heapq.heappush(queue, (step, other))
        return best

    def road_between(self, source: str, target: str) -> list[str]:
        """The nodes of the shortest link path, source and target included.

        Empty when the two do not reach each other.
        """
        if source == target:
            return [source]
        best = {source: 0.0}
        came: dict[str, str] = {}
        queue: list[tuple[float, str]] = [(0.0, source)]
        while queue:
            reached, node = heapq.heappop(queue)
            if node == target:
                break
            if reached > best.get(node, np.inf):
                continue
            here = self.position[node]
            for other in self.neighbours.get(node, ()):
                step = reached + float(np.linalg.norm(self.position[other] - here))
                if step < best.get(other, np.inf):
                    best[other] = step
                    came[other] = node
                    heapq.heappush(queue, (step, other))
        if target not in best:
            return []
        chain = [target]
        while chain[-1] != source:
            chain.append(came[chain[-1]])
        return chain[::-1]

    def merge(self, other: LinkGraph) -> LinkGraph:
        """Both graphs in one, keeping this graph's position where they disagree.

        A link whose other end has no position anywhere is dropped and counted,
        because an edge to a node the study cannot place is not a road it can
        measure.
        """
        position = dict(other.position)
        position.update(self.position)
        neighbours: dict[str, set[str]] = {node: set() for node in position}
        dangling = 0
        for graph in (other, self):
            for node, links in graph.neighbours.items():
                if node not in position:
                    dangling += len(links)
                    continue
                for end in links:
                    if end not in position:
                        dangling += 1
                        continue
                    neighbours[node].add(end)
                    neighbours[end].add(node)
        return LinkGraph(
            position=position,
            neighbours={node: tuple(sorted(links)) for node, links in neighbours.items()},
            provenance={
                "merged_from": [self.provenance.get("source"), other.provenance.get("source")],
                "nodes": len(position),
                "links_dropped_without_a_position": dangling,
                "parts": [self.provenance, other.provenance],
            },
        )


def _symmetric(edges: Mapping[str, Iterable[str]], position: Mapping[str, np.ndarray]) -> dict[str, tuple[str, ...]]:
    """Undirected neighbour lists over the nodes that have a position.

    Street View publishes links in both directions most of the time and not
    always. Mapillary publishes none at all and leaves the order implied by the
    sequence. Symmetrising here means the traversal cannot depend on which of
    those two a site came from.
    """
    out: dict[str, set[str]] = {node: set() for node in position}
    for node, links in edges.items():
        if node not in position:
            continue
        for end in links:
            if end not in position:
                continue
            out[node].add(end)
            out[end].add(node)
    return {node: tuple(sorted(links)) for node, links in out.items()}


def link_graph_from_screening(row: Mapping[str, Any]) -> LinkGraph:
    """The Street View link graph of one site, from a screening record.

    ``row`` is one entry of ``outputs/city_screening/screening.json``. Its
    ``east_m`` and ``north_m`` are already in the scene ENU frame: the screener
    and the scene config carry the same origin at all eleven sites, and the
    published positions agree with the initial poses on disk to about 0.1 m.
    """
    panoramas = row["panoramas"]
    position = {str(p["pano_id"]): np.array([float(p["east_m"]), float(p["north_m"])]) for p in panoramas}
    edges = {str(p["pano_id"]): [str(q) for q in p.get("links", ())] for p in panoramas}
    neighbours = _symmetric(edges, position)
    return LinkGraph(
        position=position,
        neighbours=neighbours,
        provenance={
            "source": "street view links, outputs/city_screening/screening.json",
            "site": row.get("key"),
            "screen_radius_m": row.get("screen_radius_m"),
            "nodes": len(position),
            "edges": sum(len(v) for v in neighbours.values()) // 2,
            "walk_date": row.get("walk_date"),
            "traversal_truncated": row.get("traversal_truncated"),
        },
    )


def link_graph_from_sequences(records: Sequence[Mapping[str, Any]], *, bridge_m: float = 0.0) -> LinkGraph:
    """The Mapillary link graph, from sequence membership and capture time.

    Mapillary names no neighbours. What it publishes is the *sequence*, the
    ordered frames of one continuous drive or ride, so consecutive frames of one
    sequence are consecutive standpoints on the street and that is the link.

    Two sequences never link to each other, however close they pass, because the
    provider does not say they do. ``bridge_m`` is the opt out: set it and two
    frames of different sequences closer than that are joined, on the argument
    that a camera stood at both so the ground between them is walkable. It is
    off by default because it is the study's inference and not the provider's
    record, and every run that uses it says so in the provenance.
    """
    position = {str(r["image_id"]): np.array([float(r["easting_m"]), float(r["northing_m"])]) for r in records}
    by_sequence: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_sequence.setdefault(str(record["sequence_id"]), []).append(record)
    edges: dict[str, list[str]] = {node: [] for node in position}
    for frames in by_sequence.values():
        ordered = sorted(frames, key=lambda r: (int(r["captured_at"]), str(r["image_id"])))
        for before, after in zip(ordered, ordered[1:], strict=False):
            edges[str(before["image_id"])].append(str(after["image_id"]))
    bridged = 0
    if bridge_m > 0.0:
        names = sorted(position)
        points = np.array([position[n] for n in names])
        sequence_of = {str(r["image_id"]): str(r["sequence_id"]) for r in records}
        gap = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                if gap[a, b] <= bridge_m and sequence_of[names[a]] != sequence_of[names[b]]:
                    edges[names[a]].append(names[b])
                    bridged += 1
    neighbours = _symmetric(edges, position)
    return LinkGraph(
        position=position,
        neighbours=neighbours,
        provenance={
            "source": "mapillary sequence order",
            "rule": "consecutive frames of one sequence in capture order",
            "nodes": len(position),
            "edges": sum(len(v) for v in neighbours.values()) // 2,
            "sequences": sorted(by_sequence),
            "bridge_m": bridge_m,
            "cross_sequence_links_added": bridged,
            "caveat": (
                "a leg is measured over the frames present, so where a sequence is on disk only in "
                "part its legs are chords of the drive rather than its arc"
            ),
        },
    )


def bridge_components(graph: LinkGraph, within_m: float) -> LinkGraph:
    """Join parts of the graph the provider left separate, wherever they pass close.

    A link graph fragments for reasons that have nothing to do with the street.
    Mapillary names no link between two sequences however close they pass, Street
    View drops the link across a capture date, and a screening radius cuts the
    ones that leave the box. Korenmarkt is the clear case: nine admitted cameras
    on four fragments, the largest of them five. Bridging at 5 m, which is under
    the 6.4 m median link of its own drives, puts all nine on one 92.8 m chain
    whose longest step is 18.7 m.

    The rule is: take the components of the graph as it stands, then link every
    pair of nodes closer than ``within_m`` that came from two different ones. Two
    parts of it matter and both were arrived at by getting them wrong first.

    Only across components, never inside one. A plain proximity join would add
    chords across a dense drive, and a chord makes the road shorter than the
    street, which is the one thing a road distance must not do.

    Every close pair, not the closest one. Joining a pair of components at a
    single point leaves them touching at that point only, so the road from one to
    the other runs out to the join and back. At Korenmarkt that turned a 5.5 m
    step between the Street View capture and its nearest Mapillary frame into 88 m
    of road. Bridging at every close pair makes the two graphs share the street
    rather than share one node.

    Still off by default. The join is this study's inference and not the
    provider's record, and it can only ever be as good as the published positions
    it compares.
    """
    if within_m <= 0.0:
        return graph
    names = sorted(graph.position)
    if len(names) < 2:
        return graph
    part: dict[str, int] = {}
    for slot, group in enumerate(fragments(names, graph)):
        for node in group:
            part[node] = slot
    neighbours = {node: set(graph.neighbours.get(node, ())) for node in names}
    points = np.array([graph.position[n] for n in names])
    gap = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    added = 0
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            if gap[a, b] > within_m or part[names[a]] == part[names[b]]:
                continue
            neighbours[names[a]].add(names[b])
            neighbours[names[b]].add(names[a])
            added += 1
    return LinkGraph(
        position=graph.position,
        neighbours={node: tuple(sorted(links)) for node, links in neighbours.items()},
        provenance={
            **graph.provenance,
            "bridged_within_m": within_m,
            "bridges_added": added,
            "parts_before_bridging": len(set(part.values())),
            "bridge_rule": "every pair closer than the threshold whose ends sat in two different parts",
        },
    )


def fragments(nodes: Sequence[str], graph: LinkGraph) -> list[list[str]]:
    """The given nodes split into groups that reach each other along the links.

    Largest first, and within a group the input order is kept, so a caller that
    takes the first group takes the longest chain the site can supply.
    """
    remaining = [n for n in nodes if n in graph.position]
    groups: list[list[str]] = []
    unplaced = set(remaining)
    while unplaced:
        seed = next(n for n in remaining if n in unplaced)
        reached = set(graph.distances_from(seed))
        group = [n for n in remaining if n in unplaced and n in reached]
        unplaced -= set(group)
        groups.append(group)
    return sorted(groups, key=len, reverse=True)


def _held_karp(distance: np.ndarray) -> tuple[list[int], float]:
    """Shortest Hamiltonian path, proved rather than searched."""
    count = distance.shape[0]
    size = 1 << count
    membership = (np.arange(size)[:, None] >> np.arange(count)[None, :]) & 1
    cost = np.full((size, count), np.inf)
    back = np.full((size, count), -1, dtype=np.int64)
    for node in range(count):
        cost[1 << node, node] = 0.0
    for mask in range(size):
        inside = np.flatnonzero(membership[mask])
        if inside.size < 2:
            continue
        for last in inside:
            previous_mask = mask ^ (1 << last)
            candidate = cost[previous_mask] + distance[:, last]
            candidate[membership[previous_mask] == 0] = np.inf
            pick = int(np.argmin(candidate))
            if np.isfinite(candidate[pick]):
                cost[mask, last] = candidate[pick]
                back[mask, last] = pick
    full = size - 1
    end = int(np.argmin(cost[full]))
    total = float(cost[full, end])
    order = [end]
    mask = full
    while back[mask, order[-1]] >= 0:
        previous = int(back[mask, order[-1]])
        mask ^= 1 << order[-1]
        order.append(previous)
    return order[::-1], total


def _path_length(distance: np.ndarray, order: Sequence[int]) -> float:
    return float(sum(distance[order[k], order[k + 1]] for k in range(len(order) - 1)))


def _nearest_neighbour_two_opt(distance: np.ndarray) -> tuple[list[int], float]:
    """Nearest neighbour from every start, improved by two-opt. Not proved optimal."""
    count = distance.shape[0]
    best: list[int] = []
    best_length = np.inf
    for start in range(count):
        left = set(range(count)) - {start}
        order = [start]
        while left:
            nxt = min(sorted(left), key=lambda j: distance[order[-1], j])
            order.append(nxt)
            left.discard(nxt)
        improved = True
        while improved:
            improved = False
            for i in range(count - 1):
                for j in range(i + 2, count):
                    trial = order[: i + 1] + order[i + 1 : j + 1][::-1] + order[j + 1 :]
                    if _path_length(distance, trial) < _path_length(distance, order) - 1.0e-9:
                        order = trial
                        improved = True
        length = _path_length(distance, order)
        if length < best_length - 1.0e-9:
            best, best_length = order, length
    return best, float(best_length)


def order_along_links(nodes: Sequence[str], graph: LinkGraph) -> dict[str, Any]:
    """Order the nodes into the shortest route through the link graph.

    All of the nodes must reach each other, which :func:`fragments` is for. The
    route is reported in the direction whose first station has the smaller
    easting plus northing, matching the convention ``build_walk`` uses to pick
    the head of its chain, so the same site always comes back the same way round.
    """
    names = list(nodes)
    if len(names) < 2:
        return {
            "order": list(range(len(names))),
            "road_m": [0.0] * len(names),
            "roads": [[n] for n in names[:1]],
            "method": "single station",
            "road_length_m": 0.0,
        }
    reach = [graph.distances_from(n) for n in names]
    distance = np.array([[reach[a].get(names[b], np.inf) for b in range(len(names))] for a in range(len(names))])
    if not np.isfinite(distance).all():
        raise ValueError("the stations do not all reach each other, split them with fragments() first")
    if len(names) <= EXACT_ORDER_LIMIT:
        order, total = _held_karp(distance)
        method = "shortest route through the link graph, proved by Held-Karp"
    else:
        order, total = _nearest_neighbour_two_opt(distance)
        method = f"nearest neighbour plus two-opt above {EXACT_ORDER_LIMIT} stations, not proved optimal"
    head, tail = graph.position[names[order[0]]], graph.position[names[order[-1]]]
    if float(head.sum()) > float(tail.sum()):
        order = order[::-1]
    roads = [graph.road_between(names[order[k]], names[order[k + 1]]) for k in range(len(order) - 1)]
    road_m = [0.0] + [float(distance[order[k], order[k + 1]]) for k in range(len(order) - 1)]
    return {"order": order, "road_m": road_m, "roads": roads, "method": method, "road_length_m": total}


@dataclass(frozen=True)
class RouteStation:
    """One standpoint of the route, and the camera it inherits its evidence from."""

    name: str
    node: str
    camera_enu_m: np.ndarray
    ground_z_m: float
    head_enu_m: np.ndarray
    road_from_previous_m: float
    straight_from_previous_m: float
    clearance_m: float | None
    sky_fraction: float | None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PanoramaRoute:
    """An ordered walk from A to B along the street the cameras were driven."""

    walk: Walk
    stations: tuple[RouteStation, ...]
    road_m: np.ndarray
    road_polyline: tuple[np.ndarray, ...]
    dropped: tuple[dict[str, Any], ...]
    provenance: dict[str, Any]

    def __len__(self) -> int:
        return len(self.stations)

    @property
    def road_length_m(self) -> float:
        return float(np.sum(self.road_m))

    @property
    def straight_length_m(self) -> float:
        points = self.walk.points[:, :2]
        return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1))) if len(points) > 1 else 0.0

    @property
    def detour_ratio(self) -> float:
        """How much longer the road is than the straight hops between stations.

        Near one where the route runs down one straight street. Well above one
        where it turns a corner, which is exactly where the straight hop would
        have cut through a building.
        """
        straight = self.straight_length_m
        return float(self.road_length_m / straight) if straight > 0.0 else 1.0

    @property
    def end_to_end_m(self) -> float:
        if len(self.walk.points) < 2:
            return 0.0
        return float(np.linalg.norm(self.walk.points[-1, :2] - self.walk.points[0, :2]))


def ground_under_camera(geometry: Any, xy: np.ndarray, camera_z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Height and up-facing normal of the surface a camera is standing on.

    The downward probe starts just under the camera rather than above the scene,
    which is the opposite of what :func:`~.walk.ground_height` does, and the two
    rules disagree at seven of the 51 admitted stations in this study.

    ``ground_height`` starts at the sky because a grid point is only a column of
    air and a ray that starts inside a tower reports the shell below its start
    rather than the tower's roof. A camera is not a column of air. It is a place
    a vehicle or a person physically stood, and it has already passed the sky
    conflict gate, so it is known to be outdoors and under open sky. What is not
    known is whether the photogrammetric mesh roofed it over, and it often did:
    at the Zocalo the mesh bridges the arcades along the west and south sides, so
    a probe from the sky lands 8.66 to 11.70 m above the ground datum at six of
    the twelve stations, and at Plaza Mayor pano_03 it lands 19.35 m above it. A
    head placed on those returns is a head on a roof.

    Starting under the camera cannot see any of that. Where the two rules agree
    they agree to 0.01 m, so this is a repair with no cost anywhere else.
    """
    origins = np.column_stack([xy, np.asarray(camera_z, dtype=float) - 0.05])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (xy.shape[0], 1))
    hit, distance, normal, _ = geometry.intersect(origins, directions)
    z = np.where(hit, origins[:, 2] - distance, np.nan)
    return z, np.abs(normal[:, 2])


def build_panorama_route(
    geometry: Any,
    stations: Sequence[Mapping[str, Any]],
    graph: LinkGraph,
    *,
    head_height_m: float = HEAD_HEIGHT_M,
    fragment: int = 0,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    radius_m: float | None = None,
    ground_datum_m: float | None = None,
    datum_tolerance_m: float = 2.5,
    probe_from: str = "camera",
    min_clearance_m: float | None = None,
    min_sky_fraction: float | None = None,
    clearance_samples: int = 96,
    seed: int = 0,
    probe_z_m: float = SKY_PROBE,
) -> PanoramaRoute:
    """Order registered cameras into a route and put a head at each of them.

    ``stations`` is a sequence of records carrying at least ``name``, ``node``
    and ``camera_enu_m``. :func:`load_admitted_stations` builds them from the
    site semantics report, which is where the admission decision lives.

    The height of a standpoint is measured, not inherited. The head goes
    ``head_height_m`` above the ground under the camera, cast for on the geometry
    in hand by :func:`ground_under_camera`. It is deliberately not derived from
    the registered camera altitude minus the scene's 2.5 m camera height, because
    that altitude is a fitted nuisance parameter and it does not hold: across the
    51 admitted stations the registered camera sits between 0.35 m and 5.72 m
    above the ground under it, so a head placed one metre below the camera would
    land anywhere from 0.65 m underground to 4.2 m in the air. Both quantities
    are reported per station, so the disagreement is visible rather than absorbed.

    ``ground_datum_m`` is optional and changes nothing. Pass it and every
    standpoint whose ground sits further than ``datum_tolerance_m`` from the
    crop's walkable level is counted in the provenance, which is how a camera
    standing on a raised terrace announces itself.

    ``min_clearance_m`` and ``min_sky_fraction`` default to no refusal at all,
    which is the opposite of ``build_walk``. That is deliberate. A grid point has
    nothing behind it, so the walk has to test whether it is a place a person
    could stand. A station is a place a camera physically stood and already
    passed the skyline residual and sky conflict gates of
    ``build_site_semantics.py``, and dropping one here would silently break the
    one property this route exists to hold, that every standpoint has a
    photograph taken at it. Both numbers are measured and reported either way.
    """
    rng = np.random.default_rng(seed)
    records = [dict(s) for s in stations]
    dropped: list[dict[str, Any]] = []

    kept = []
    for record in records:
        camera = np.asarray(record["camera_enu_m"], dtype=float)
        if not record.get("node"):
            dropped.append({"station": record["name"], "because": "this station carries no provider identifier"})
            continue
        if record["node"] not in graph.position:
            dropped.append({"station": record["name"], "because": "the camera is not in the link graph"})
            continue
        if radius_m is not None and float(np.linalg.norm(camera[:2] - np.asarray(centre_xy))) > radius_m:
            dropped.append({"station": record["name"], "because": f"the camera is beyond the {radius_m:.0f} m crop"})
            continue
        record["camera_enu_m"] = camera
        kept.append(record)
    if not kept:
        raise RuntimeError("no station survived, so this site cannot supply a panorama route")

    groups = fragments([r["node"] for r in kept], graph)
    if fragment >= len(groups):
        raise IndexError(f"this site has {len(groups)} connected fragments, so fragment {fragment} does not exist")
    chosen = set(groups[fragment])
    for record in kept:
        if record["node"] not in chosen:
            dropped.append(
                {
                    "station": record["name"],
                    "because": (
                        f"the camera sits on a separate fragment of the link graph, "
                        f"{len(groups)} fragments of sizes {[len(g) for g in groups]}"
                    ),
                }
            )
    kept = [r for r in kept if r["node"] in chosen]

    ordering = order_along_links([r["node"] for r in kept], graph)
    kept = [kept[i] for i in ordering["order"]]

    if probe_from not in ("camera", "sky"):
        raise ValueError("probe_from is 'camera' or 'sky'")
    xy = np.array([r["camera_enu_m"][:2] for r in kept])
    camera_z = np.array([r["camera_enu_m"][2] for r in kept])
    if probe_from == "camera":
        ground, up = ground_under_camera(geometry, xy, camera_z)
    else:
        ground, up = ground_height(geometry, xy, probe_z_m)
    if not np.isfinite(ground).all():
        missing = [kept[i]["name"] for i in np.flatnonzero(~np.isfinite(ground))]
        raise RuntimeError(f"no ground under {missing}, so the camera stands outside this crop")

    heads = np.column_stack([xy, ground + head_height_m])
    free = clearance(geometry, heads, clearance_samples, rng)
    sky = sky_visibility(geometry, heads, clearance_samples, rng)
    if min_clearance_m is not None or min_sky_fraction is not None:
        keep = np.ones(len(kept), dtype=bool)
        if min_clearance_m is not None:
            keep &= free >= min_clearance_m
        if min_sky_fraction is not None:
            keep &= sky >= min_sky_fraction
        for i in np.flatnonzero(~keep):
            dropped.append(
                {
                    "station": kept[i]["name"],
                    "because": f"clearance {free[i]:.2f} m and sky {sky[i]:.3f} failed the caller's gate",
                }
            )
        if not keep.any():
            raise RuntimeError("every station failed the clearance or sky gate")
        kept = [r for r, k in zip(kept, keep, strict=True) if k]
        xy, ground, up, camera_z = xy[keep], ground[keep], up[keep], camera_z[keep]
        heads, free, sky = heads[keep], free[keep], sky[keep]
        ordering = order_along_links([r["node"] for r in kept], graph)
        remap = ordering["order"]
        kept = [kept[i] for i in remap]
        xy, ground, up, camera_z = xy[remap], ground[remap], up[remap], camera_z[remap]
        heads, free, sky = heads[remap], free[remap], sky[remap]

    straight = np.zeros(len(kept))
    if len(kept) > 1:
        straight[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    road = np.asarray(ordering["road_m"], dtype=float)
    off_datum = (
        [kept[i]["name"] for i in np.flatnonzero(np.abs(ground - ground_datum_m) > datum_tolerance_m)]
        if ground_datum_m is not None
        else []
    )

    route_stations = tuple(
        RouteStation(
            name=record["name"],
            node=record["node"],
            camera_enu_m=record["camera_enu_m"],
            ground_z_m=float(ground[i]),
            head_enu_m=heads[i],
            road_from_previous_m=float(road[i]),
            straight_from_previous_m=float(straight[i]),
            clearance_m=float(free[i]),
            sky_fraction=float(sky[i]),
            detail={
                **{k: v for k, v in record.items() if k not in ("name", "node", "camera_enu_m")},
                "camera_z_m": float(record["camera_enu_m"][2]),
                "camera_above_measured_ground_m": float(record["camera_enu_m"][2] - ground[i]),
                "ground_up_cosine": float(up[i]),
            },
        )
        for i, record in enumerate(kept)
    )

    polyline = tuple(
        np.array([graph.position[n] for n in road_nodes]) for road_nodes in ordering["roads"] if len(road_nodes) > 1
    )
    walk = Walk(
        points=heads,
        ground_z_m=ground,
        step_m=straight,
        provenance={
            "rule": (
                "one standpoint per admitted panorama, ordered by the shortest route through the "
                "provider's own link graph, head placed above the ground measured under the camera"
            ),
            "head_height_m": head_height_m,
            "stations": [r.name for r in route_stations],
            "ordering": ordering["method"],
            "road_length_m": float(np.sum(road)),
            "straight_length_m": float(np.sum(straight)),
            "road_step_m": [float(v) for v in road],
            "fragment": fragment,
            "fragment_sizes": [len(g) for g in groups],
            "dropped": dropped,
            "probe_from": probe_from,
            "ground_datum_m": ground_datum_m,
            "datum_tolerance_m": datum_tolerance_m,
            "standpoints_off_the_ground_datum": off_datum,
            "camera_above_measured_ground_m": [float(v) for v in camera_z - ground],
            "clearance_samples": clearance_samples,
            "min_clearance_m": min_clearance_m,
            "min_sky_fraction": min_sky_fraction,
            "clearance_m": [float(v) for v in free],
            "sky_fraction": [float(v) for v in sky],
            "link_graph": graph.provenance,
            "seed": seed,
        },
    )
    return PanoramaRoute(
        walk=walk,
        stations=route_stations,
        road_m=road,
        road_polyline=polyline,
        dropped=tuple(dropped),
        provenance=dict(walk.provenance),
    )


def panorama_walk(geometry: Any, stations: Sequence[Mapping[str, Any]], graph: LinkGraph, **kwargs: Any) -> Walk:
    """The route as a plain :class:`~.walk.Walk`, for a caller that wants a drop-in."""
    return build_panorama_route(geometry, stations, graph, **kwargs).walk


# --- reading the study's own files -------------------------------------------


def _repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def load_admitted_stations(site: str, *, root: pathlib.Path | None = None, report: str | None = None) -> list[dict]:
    """The stations one site admitted, with their registered position and pano id.

    Read from ``outputs/site_semantics/<site>/walk_semantic_250m.json`` rather
    than re-derived, because that file is where the admission rule lives and a
    second copy of the rule here would be a second rule. The pano id is not in
    that report and is read from each station's own ``metadata.json``, which is
    ``panoId`` on a Street View capture and ``id`` on a Mapillary one.
    """
    base = root if root is not None else _repository_root()
    name = report or "walk_semantic_250m.json"
    path = base / "outputs" / "site_semantics" / site / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist, so {site} has no admitted station set. Build it with build_site_semantics.py."
        )
    document = json.loads(path.read_text())
    out = []
    for entry in document.get("stations_admitted", ()):
        folder = pathlib.Path(entry["folder"])
        if not folder.is_absolute():
            folder = base / folder
        record: dict[str, Any] = {
            "name": entry["station"],
            "node": None,
            "camera_enu_m": np.asarray(entry["position_enu_m"], dtype=float),
            "residual_deg": entry.get("residual_deg"),
            "position_sigma_m": entry.get("position_sigma_m"),
            "folder": str(folder),
        }
        metadata = folder / "metadata.json"
        if metadata.exists():
            document_meta = json.loads(metadata.read_text())
            record["node"] = str(document_meta.get("panoId") or document_meta.get("id") or "")
            record["sequence_id"] = document_meta.get("sequence")
            record["date"] = document_meta.get("date")
        out.append(record)
    return out


def load_link_graph(
    site: str,
    *,
    root: pathlib.Path | None = None,
    bridge_m: float = 0.0,
) -> LinkGraph:
    """Whatever link structure the study holds for one site, merged.

    Street View sites come from ``outputs/city_screening/screening.json``.
    Korenmarkt's cameras are mostly Mapillary and come from the sequence
    traversal in ``outputs/walk_korenmarkt_saturation/walk_selection.json``. A
    site with both gets both, which is what lets a single Street View capture
    sit on the same route as a Mapillary walk when the two graphs touch.

    ``bridge_m`` is handed to :func:`bridge_components` and applies to the merged
    graph, so it joins two providers as readily as two sequences. It is off by
    default because the join is this study's inference rather than the provider's
    record, and any run that turns it on says so in the provenance.
    """
    base = root if root is not None else _repository_root()
    parts: list[LinkGraph] = []
    screening = base / "outputs" / "city_screening" / "screening.json"
    if screening.exists():
        for row in json.loads(screening.read_text())["rows"]:
            if row["key"] == site:
                parts.append(link_graph_from_screening(row))
                break
    traversal = base / "outputs" / "walk_korenmarkt_saturation" / "walk_selection.json"
    if site == "korenmarkt" and traversal.exists():
        parts.append(link_graph_from_sequences(json.loads(traversal.read_text())["candidates"]))
    if not parts:
        raise FileNotFoundError(f"no link graph on disk for {site}")
    graph = parts[0]
    for other in parts[1:]:
        graph = graph.merge(other)
    return bridge_components(graph, bridge_m)


# --- the walk a runner actually asks for --------------------------------------


def densify(polylines: Sequence[np.ndarray], stride_m: float) -> np.ndarray:
    """Points every ``stride_m`` along a chain of road legs, ends included.

    A route puts one standpoint at each camera, which is honest and thin: five
    at Korenmarkt against sixty on the grid. But a pedestrian is not only where
    the camera stopped, they are anywhere along the street the camera drove, and
    the leg polylines are that street. Walking them at a fixed stride keeps every
    standpoint on the captured road while giving the sample back its density.

    Returns an empty (0, 2) array when there is no road, which happens at a site
    with a single admitted station and is not an error.
    """
    chain = [p for p in polylines if p is not None and len(p) >= 2]
    if not chain:
        return np.zeros((0, 2))
    line = np.concatenate([np.asarray(p, dtype=float)[:, :2] for p in chain], axis=0)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(line, axis=0), axis=1) > 1.0e-9])
    line = line[keep]
    if line.shape[0] < 2:
        return line
    step = np.linalg.norm(np.diff(line, axis=0), axis=1)
    travelled = np.concatenate([[0.0], np.cumsum(step)])
    wanted = np.arange(0.0, travelled[-1] + 0.5 * stride_m, stride_m)
    wanted = wanted[wanted <= travelled[-1]]
    return np.column_stack([np.interp(wanted, travelled, line[:, axis]) for axis in (0, 1)])


def span_endpoints(cameras: np.ndarray) -> tuple[int, int]:
    """The two cameras furthest apart in plan, which is the walk's A and B.

    The widest pair is the diameter of the capture, so the line between them is
    the longest walk the panoramas can speak for. At Brussels Grand-Place it is
    88 m straight, the town hall corner to the east side, and the walking path
    between them is the one a visitor actually takes across the square.
    """
    gap = np.linalg.norm(cameras[:, None, :2] - cameras[None, :, :2], axis=2)
    return tuple(int(v) for v in np.unravel_index(int(np.argmax(gap)), gap.shape))  # type: ignore[return-value]


def gap_to_path(points: np.ndarray, line: np.ndarray) -> np.ndarray:
    """Shortest plan distance from each point to a polyline."""
    start, end = line[:-1, :2], line[1:, :2]
    segment = end - start
    length2 = np.einsum("ij,ij->i", segment, segment)
    length2[length2 == 0.0] = 1.0
    along = np.clip(np.einsum("pij,ij->pi", points[:, None, :2] - start[None], segment) / length2, 0.0, 1.0)
    foot = start[None] + along[..., None] * segment[None]
    return np.linalg.norm(points[:, None, :2] - foot, axis=2).min(axis=1)


def street_path(
    site: str,
    route: PanoramaRoute,
    *,
    root: pathlib.Path | None = None,
    crop_m: int = 250,
    endpoints: str = "span",
) -> tuple[tuple[np.ndarray, ...], dict[str, Any]]:
    """The walking path across the square, from the routing service.

    ``endpoints="span"`` asks for one walk from A to B, where A and B are the two
    cameras furthest apart. Nothing in between is a waypoint. This is what a
    person walking across the square does, and it is the default.

    ``endpoints="all"`` makes every camera a waypoint and lets the service
    reorder them. That sounds better and is worse. Three of the eight Brussels
    cameras sit up side streets, so a path that visits all of them walks in and
    walks back out three times: 267 m against 121 m, and the extra 146 m is spent
    in alleys where there is one camera at the dead end and nothing either side
    of it. Measured over the standpoints laid at a 6 m stride, the mean distance
    from a standpoint to the nearest camera is **8.3 m for the A to B walk and
    10.2 m for the full tour**. Visiting every camera makes the sample worse by
    the one measure that matters.

    The three cameras the A to B walk passes 20 to 38 m from are not discarded.
    Their panoramas still label the geometry through the fishnet. They just no
    longer bend the walk into a shape no pedestrian would take.

    Returned as a one element tuple so it drops straight into :func:`densify`,
    which takes a chain of legs. The walking path is one continuous line and has
    no legs to speak of.
    """
    base = root or _repository_root()
    anchor = site_anchor(site, base, crop_m=crop_m)
    frame = EnuFrame(anchor[0], anchor[1])
    cameras = np.array([station.camera_enu_m for station in route.stations], dtype=float)
    if endpoints == "span":
        chosen = list(span_endpoints(cameras))
    elif endpoints == "all":
        chosen = list(range(len(cameras)))
    else:
        raise ValueError(f"endpoints is 'span' or 'all', not {endpoints!r}")

    waypoints = [tuple(frame.to_llh(cameras[k])[:2]) for k in chosen]
    answer = cached_walking_route(site, waypoints, root=base, optimise=len(waypoints) > 2)
    line = polyline_enu(answer, anchor)
    step = np.linalg.norm(np.diff(line, axis=0), axis=1) if line.shape[0] > 1 else np.zeros(0)
    off = gap_to_path(cameras, line) if line.shape[0] > 1 else np.full(len(cameras), np.inf)
    record = {
        "source": answer["source"],
        "endpoints": endpoints,
        "waypoints": len(waypoints),
        "endpoint_stations": chosen if endpoints == "span" else None,
        "endpoint_separation_m": float(np.linalg.norm(cameras[chosen[0], :2] - cameras[chosen[-1], :2])),
        "distance_m": answer["distance_m"],
        "points": int(line.shape[0]),
        "waypoint_order": answer.get("waypoint_order"),
        "longest_segment_m": float(step.max()) if step.size else 0.0,
        "measured_length_m": float(step.sum()),
        "link_graph_length_m": float(np.sum(route.road_length_m)),
        # How far the cameras sit from the line that was walked. A camera well
        # off the path still labels geometry, but it no longer says where a head
        # stood, and this is where that shows up.
        "cameras_off_path_median_m": float(np.median(off)),
        "cameras_off_path_max_m": float(off.max()),
        "cameras_within_10m": int((off < 10.0).sum()),
        "anchor_lat_lon": list(anchor),
        # The path itself, in scene metres. It is small, it is what the walk
        # actually used, and keeping it means a figure or a reviewer can see the
        # line without another request.
        "polyline_enu": [[round(float(x), 3), round(float(y), 3)] for x, y in line],
    }
    return (line,), record


def site_walk(
    geometry: Any,
    site: str,
    *,
    stride_m: float = 0.0,
    head_height_m: float = HEAD_HEIGHT_M,
    root: pathlib.Path | None = None,
    bridge_m: float = 0.0,
    path: str = "links",
    endpoints: str = "span",
    crop_m: int = 250,
    **kwargs: Any,
) -> tuple[Walk, dict[str, Any]]:
    """The walk for one site, taken from its capture rather than from a grid.

    This is the entry point a runner should call. ``build_walk`` scatters heads
    over a disc on a three metre lattice and joins them nearest neighbour first,
    which is a flood fill of the open ground and not a route anyone took. This
    stands where the cameras stood, in the order the street connects them.

    ``stride_m`` above zero adds standpoints along the road between cameras, so
    the sample is dense without leaving the captured street. Their ground is
    probed from just under an interpolated camera height, the same rule
    :func:`ground_under_camera` uses, which is what keeps a head off the arcade
    roofs and doorsteps that a probe from the sky lands on.

    ``path`` chooses what "between the cameras" means.

    ``links`` walks the provider's own panorama links. Dense, about ten metres
    between points, and free, but those links are where the survey car drove and
    these squares are pedestrianised, so the car went around what a person walks
    across.

    ``street`` asks Google Routes for one walking path from A to B across the
    square, where A and B are the two cameras furthest apart. It comes off the
    pedestrian network, so it may cross an open square the car had to go round.
    At Brussels it is 121 m against the links' 284 m, because the links detour up
    three side streets and the walk does not. It costs one request per site and
    the answer is cached on disk. See :func:`street_path`.

    A camera further from that path than the stride is not on the walk, so it is
    not a standpoint. It still labels geometry through its panorama. Dropping it
    is what stops the walk from having orphan points hanging off it.

    ``closest`` builds both and keeps whichever stands nearer a camera, which is
    the one thing the method rests on. Neither path wins everywhere. Measured at
    six squares, mean metres from a standpoint to the nearest camera:

    | | links | street |
    |---|---|---|
    | Ghent Korenmarkt | 2.8 | 2.9 |
    | Brussels Grand-Place | 8.9 | **6.7** |
    | Madrid Plaza Mayor | **9.5** | 12.1 |
    | Mexico City Zocalo | **8.3** | 46.0 |
    | Prague Old Town | **6.5** | 7.3 |
    | Tokyo Hachiko | **13.5** | 20.3 |

    Brussels is the case the walking path was built for, a pedestrianised square
    the survey car had to drive around. Mexico City is the opposite: the Zocalo is
    240 m across with no way mapped inside it, so Routes walks the streets around
    the outside and every camera ends up 24 m or more from the walk.

    ``closest`` is not the default, and the reason is in `BOUNCE_BUDGET.md`. The
    first interaction lands on photographed surface with probability 0.987 to
    0.999 anywhere inside ten metres of a camera. Brussels on links is 8.90 m and
    on the walking path 6.67 m, so both sit in the same band and the choice buys
    nothing the physics can feel. ``links`` is the default because one sampling
    rule for all eleven squares is easier to defend than a rule that changes site
    by site to gain 2.2 m that does not matter.

    Returns the walk and a provenance record. It raises rather than quietly
    falling back to the grid: a run that silently changed what a standpoint means
    is how a stale walk survives, and the caller should decide.
    """
    if path == "closest":
        best, best_gap, tried = None, np.inf, {}
        for candidate in ("links", "street"):
            walk, record = site_walk(
                geometry,
                site,
                stride_m=stride_m,
                head_height_m=head_height_m,
                root=root,
                bridge_m=bridge_m,
                path=candidate,
                endpoints=endpoints,
                crop_m=crop_m,
                **kwargs,
            )
            cameras = np.array(
                [s["camera_enu_m"] for s in load_admitted_stations(site, root=root)],
                dtype=float,
            )
            gap = float(np.linalg.norm(walk.points[:, None, :2] - cameras[None, :, :2], axis=2).min(axis=1).mean())
            tried[candidate] = round(gap, 2)
            if gap < best_gap:
                best, best_gap = (walk, record), gap
        walk, record = best  # type: ignore[misc]
        record["path_chosen_by"] = "mean metres from a standpoint to the nearest camera"
        record["path_candidates_m"] = tried
        return walk, record
    stations = load_admitted_stations(site, root=root)
    graph = load_link_graph(site, root=root, bridge_m=bridge_m)
    route = build_panorama_route(geometry, stations, graph, head_height_m=head_height_m, **kwargs)
    walk = route.walk
    provenance: dict[str, Any] = {
        **route.provenance,
        "builder": "panorama route",
        "path": path,
        "stations": len(route),
        "road_length_m": float(np.sum(route.road_length_m)),
        "stride_m": stride_m,
    }
    # Camera heights, kept before any filtering. The stride probes the ground
    # from just under an interpolated camera, and dropping a station off the walk
    # must not also drop the height it measured.
    heights = walk.points.copy()

    if path == "street":
        legs, street = street_path(site, route, root=root, crop_m=crop_m, endpoints=endpoints)
        provenance["street_route"] = street
        line = np.asarray(street["polyline_enu"], dtype=float)
        on = gap_to_path(walk.points, line) <= max(stride_m, 5.0)
        provenance["stations_on_path"] = int(on.sum())
        provenance["stations_off_path"] = int((~on).sum())
        if not on.any():
            # Every camera is off the routed path. This is the pedestrian network
            # not entering the square: Mexico City's Zocalo is 240 m across with
            # no way mapped inside it, so Routes walks the streets around it and
            # the nearest camera to that walk is 24 m away. The walk is still
            # real, it just carries no station, and the caller should hear it.
            provenance["note"] = (
                f"no camera lies within {max(stride_m, 5.0):.0f} m of the walking path, "
                f"nearest is {gap_to_path(walk.points, line).min():.0f} m off"
            )
        walk = Walk(
            points=walk.points[on],
            ground_z_m=walk.ground_z_m[on],
            step_m=walk.step_m[on],
            provenance={**walk.provenance, "kept_within_m": max(stride_m, 5.0)},
        )
    else:
        legs = route.road_polyline
    if stride_m <= 0.0:
        provenance["standpoints"] = len(walk)
        return walk, provenance

    extra = densify(legs, stride_m)
    if extra.shape[0] == 0:
        provenance["standpoints"] = len(walk)
        provenance["note"] = "no road between stations, so the stride added nothing"
        return walk, provenance

    # Camera height along the road, so the downward probe starts under the
    # camera exactly as it does at a station.
    at = heights[:, :2]
    order = np.argsort(np.linalg.norm(at - at[0], axis=1))
    camera_z = np.interp(
        np.linalg.norm(extra - at[0], axis=1),
        np.linalg.norm(at[order] - at[0], axis=1),
        heights[order, 2],
    )
    z, _ = ground_under_camera(geometry, extra, camera_z)
    good = np.isfinite(z)
    points = np.concatenate([walk.points, np.column_stack([extra[good], z[good] + head_height_m])], axis=0)
    ground = np.concatenate([walk.ground_z_m, z[good]])
    seen = np.round(points[:, :2], 2)
    _, unique = np.unique(seen, axis=0, return_index=True)
    points, ground = points[np.sort(unique)], ground[np.sort(unique)]
    step = np.concatenate([[0.0], np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)])
    provenance["standpoints"] = int(points.shape[0])
    provenance["added_along_the_road"] = int(points.shape[0] - len(walk))
    return Walk(points=points, ground_z_m=ground, step_m=step, provenance=provenance), provenance

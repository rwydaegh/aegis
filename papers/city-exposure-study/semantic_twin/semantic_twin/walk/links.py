"""The imagery provider's own record of which camera stands next to which.

Street View and Mapillary both publish a link structure along the street,
because a car or a trekker drove or walked it. Street View names each panorama's
neighbours directly. Mapillary publishes sequences, the ordered frames of one
continuous drive, and the ordering is the link. Either way the provider has
already recorded which standpoints are adjacent, so ordering the cameras into a
route needs no synthetic routing and no street map.

Ordering the cameras along that graph is :mod:`semantic_twin.walk.ordering`.
This module is the graph itself, and the two repairs it allows. Both repairs are
opt in, because both are this study's inference rather than the provider's
record. :func:`link_graph_from_sequences` can join two Mapillary sequences that
pass close, and :func:`bridge_components` can join whole fragments the provider
left separate. Every run that turns either on says so in the provenance.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class LinkGraph:
    """Panorama positions and the provider's own links between them.

    ``position`` is in the scene ENU frame, x east and y north, and holds the
    provider's published position rather than the registered one. The two are
    different quantities and the difference is the point of the registration:
    at Brussels the fit moves a camera 0.65 to 5.63 m. The graph is used for
    topology and for road distance only, and every standpoint the route builder
    emits comes from the registered pose.
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

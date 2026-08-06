"""The shortest route through the link graph, and the two ways of finding it.

A route through the cameras is a shortest Hamiltonian path over road distances,
which is a travelling salesman problem without the return leg. At the sizes this
study has it is cheap to prove, so it is proved, and the search exists only so a
larger site degrades to a recorded heuristic rather than to a hang.

The route is reported in the direction whose first station has the smaller
easting plus northing, matching the convention the grid builder uses to pick the
head of its chain, so the same site always comes back the same way round.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .links import LinkGraph

#: Above this many stations the shortest route is searched rather than proved.
#: Held-Karp costs ``n * 2**(n - 1)`` inner steps, which is a fifth of a second
#: at twelve stations and about a second at fifteen. No site in this study has
#: more than twelve admitted stations, so the exact answer is always the one
#: that ships.
EXACT_ORDER_LIMIT = 15


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
    easting plus northing, matching the convention the grid builder uses to pick
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

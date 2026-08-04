"""Turn a labelled crop into semantic islands, and find the cracks between them.

Two steps, and they run before any mesh triangle is touched.

**Paintability.** Every pixel gets one verdict: may this evidence be projected
onto the support surface at all. Clutter standing in front of a wall, a person
walking past it, a registration conflict and a class that is not a surface are
kept apart, because they have different consequences downstream.

**Islands.** Paintable pixels are grouped into connected, single-class,
depth-continuous sets. Folding depth continuity into the island definition is
what makes occlusion silhouettes part of the fishnet: a wall seen past a nearer
building is a different island from that building even when both carry the same
class.

The cracks between islands become the boundary chains the cutter intersects
triangles with. They are traced on the pixel-corner grid so that a chain
separating two islands is one shared object, which is what keeps the fishnet a
partition rather than a set of overlapping patches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import approximate_polygon

UNPAINTABLE = -1

# Why a pixel may not be projected onto the support surface.  The two the owner
# cares about are kept apart on purpose: clutter in front of the wall is
# geometry the tiles never captured, whereas a transient object is geometry that
# belongs to a separate dynamic layer and must never be painted onto the wall
# behind it.
PAINT_REASONS: dict[str, int] = {
    "paintable": 0,
    "no_mesh_hit": 1,
    "low_confidence": 2,
    "transient_object": 3,
    "clutter_in_front": 4,
    "mesh_or_pose_conflict": 5,
    "not_support_surface": 6,
}


@dataclass(frozen=True)
class RegionMap:
    """Semantic islands: connected, depth-continuous, single-class pixel sets.

    ``region`` is ``UNPAINTABLE`` where evidence must not be projected at all,
    and ``paint_reason`` records why.  Folding depth continuity into the island
    definition is what makes occlusion silhouettes part of the fishnet: a wall
    seen past a nearer building is a different island from that building even
    when both carry the same class.
    """

    region: np.ndarray
    region_class: np.ndarray
    region_size: np.ndarray
    source_class: np.ndarray
    paint_reason: np.ndarray
    report: dict[str, int] = field(default_factory=dict)

    @property
    def region_count(self) -> int:
        return int(self.region_class.size)


def paintability(
    labels: np.ndarray,
    confidence: np.ndarray,
    range_m: np.ndarray,
    *,
    transient_class_ids: set[int] | None = None,
    excluded_class_ids: set[int] | None = None,
    min_confidence: float = 0.35,
    decision: np.ndarray | None = None,
    front_blocker_decisions: tuple[int, ...] = (3,),
    mesh_conflict_decisions: tuple[int, ...] = (4,),
    transient_decisions: tuple[int, ...] = (5,),
) -> np.ndarray:
    """Per-pixel projection decision, one of :data:`PAINT_REASONS`.

    ``decision`` is the map written by ``compare_mesh_depth.py``: it is where
    metric distance, not appearance, decides that something stands in front of
    the tile surface.  Only its ``front_blocker`` verdict, which every depth
    model has to support, becomes ``clutter_in_front``.  Its
    ``mesh_or_pose_blocker`` verdict is a conflict about where the tile surface
    itself is, so it gets its own ``mesh_or_pose_conflict`` reason: both
    withhold the pixel, but calling a registration conflict "clutter" would put
    a scatterer in the report that nothing observed.

    Transient classes are separated from the distance test so a person is never
    painted onto the wall behind them even when the depths agree, and that
    separation survives a withheld distance test because it never depended on
    one.  Any decision the caller does not name, including
    ``no_depth_evidence``, leaves the pixel to the mesh first hit and the class
    test alone.  ``excluded_class_ids`` covers classes that are not support
    surfaces at all, such as sky and the street furniture that the object
    pipeline reconstructs as its own proxy geometry.
    """
    labels = np.asarray(labels)
    confidence = np.asarray(confidence, dtype=np.float64)
    range_m = np.asarray(range_m, dtype=np.float64)
    if labels.ndim != 2 or confidence.shape != labels.shape or range_m.shape != labels.shape:
        raise ValueError("labels, confidence and range_m must be equally shaped 2D arrays")
    reason = np.full(labels.shape, PAINT_REASONS["paintable"], dtype=np.int8)
    reason[~np.isfinite(range_m) | (range_m <= 0.0)] = PAINT_REASONS["no_mesh_hit"]
    still_open = reason == PAINT_REASONS["paintable"]
    reason[still_open & (confidence < min_confidence)] = PAINT_REASONS["low_confidence"]
    if decision is not None:
        decision = np.asarray(decision)
        if decision.shape != labels.shape:
            raise ValueError("decision must match the label resolution")
        reason[np.isin(decision, list(front_blocker_decisions))] = PAINT_REASONS["clutter_in_front"]
        reason[np.isin(decision, list(mesh_conflict_decisions))] = PAINT_REASONS["mesh_or_pose_conflict"]
        reason[np.isin(decision, list(transient_decisions))] = PAINT_REASONS["transient_object"]
    if excluded_class_ids:
        reason[np.isin(labels, list(excluded_class_ids))] = PAINT_REASONS["not_support_surface"]
    if transient_class_ids:
        reason[np.isin(labels, list(transient_class_ids))] = PAINT_REASONS["transient_object"]
    reason[~np.isfinite(range_m) | (range_m <= 0.0)] = PAINT_REASONS["no_mesh_hit"]
    return reason


def build_region_map(
    labels: np.ndarray,
    paint_reason: np.ndarray,
    range_m: np.ndarray,
    *,
    depth_break_ratio: float = 0.15,
    min_region_pixels: int = 64,
) -> RegionMap:
    """Group paintable pixels into single-class, depth-continuous islands.

    ``depth_break_ratio`` is a relative first-hit range step between adjacent
    pixels.  A relative test keeps grazing surfaces whole while still splitting
    at genuine silhouettes.  Islands below ``min_region_pixels`` are merged into
    the depth-continuous neighbour with which they share the longest boundary,
    which is the knob that trades class fidelity for triangle count.
    """
    labels = np.asarray(labels)
    paint_reason = np.asarray(paint_reason)
    range_m = np.asarray(range_m, dtype=np.float64)
    if labels.ndim != 2 or paint_reason.shape != labels.shape or range_m.shape != labels.shape:
        raise ValueError("labels, paint_reason and range_m must be equally shaped 2D arrays")
    if not np.isfinite(depth_break_ratio) or depth_break_ratio <= 0.0:
        raise ValueError("depth_break_ratio must be finite and positive")
    if min_region_pixels < 0:
        raise ValueError("min_region_pixels must be non-negative")

    height, width = labels.shape
    valid = (paint_reason == PAINT_REASONS["paintable"]) & np.isfinite(range_m) & (range_m > 0.0)
    flat = np.arange(height * width, dtype=np.int64).reshape(height, width)
    same_pairs, cross_pairs = _adjacent_pairs(labels, range_m, valid, flat, depth_break_ratio)

    rows = np.concatenate([pair[0] for pair in same_pairs])
    columns = np.concatenate([pair[1] for pair in same_pairs])
    graph = coo_matrix(
        (np.ones(rows.size, dtype=np.int8), (rows, columns)),
        shape=(height * width, height * width),
    )
    _count, component = connected_components(graph, directed=False)
    component = component.reshape(height, width)

    region, region_class = _compact_regions(component, labels, valid)
    merged = 0
    if min_region_pixels > 0 and region_class.size:
        region, region_class, merged = _merge_small_regions(
            region,
            region_class,
            labels,
            np.concatenate([pair[0] for pair in cross_pairs]),
            np.concatenate([pair[1] for pair in cross_pairs]),
            min_region_pixels,
        )
    sizes = np.bincount(region[region >= 0].ravel(), minlength=region_class.size).astype(np.int64)
    report = {
        "paintable_pixels": int(valid.sum()),
        "regions": int(region_class.size),
        "merged_small_regions": int(merged),
        "regions_below_minimum": int(np.count_nonzero(sizes < min_region_pixels)),
    }
    return RegionMap(
        region,
        region_class,
        sizes,
        np.where(valid, labels, UNPAINTABLE).astype(np.int64),
        paint_reason.astype(np.int8),
        report,
    )


def _adjacent_pairs(
    labels: np.ndarray,
    range_m: np.ndarray,
    valid: np.ndarray,
    flat: np.ndarray,
    depth_break_ratio: float,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], list[tuple[np.ndarray, np.ndarray]]]:
    """Four-connected pixel pairs, split by whether the two carry the same class.

    Both halves are needed. The same-class pairs are the edges of the island
    graph. The cross-class pairs are how a region below the minimum size finds
    the neighbour it merges into, and they have to come from the same continuity
    test or a small island could merge across a silhouette.
    """
    same_pairs: list[tuple[np.ndarray, np.ndarray]] = []
    cross_pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for a_slice, b_slice in (
        ((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
        ((slice(0, -1), slice(None)), (slice(1, None), slice(None))),
    ):
        both = valid[a_slice] & valid[b_slice]
        near = np.minimum(range_m[a_slice], range_m[b_slice])
        continuous = both & (np.abs(range_m[a_slice] - range_m[b_slice]) <= depth_break_ratio * np.maximum(near, 1e-6))
        equal = labels[a_slice] == labels[b_slice]
        same_pairs.append((flat[a_slice][continuous & equal], flat[b_slice][continuous & equal]))
        cross_pairs.append((flat[a_slice][continuous & ~equal], flat[b_slice][continuous & ~equal]))
    return same_pairs, cross_pairs


def boundary_chains(region: np.ndarray, *, tolerance_px: float = 1.5) -> list[np.ndarray]:
    """Simplified polylines of the crack network between islands.

    Boundaries are traced on the pixel-corner grid, so a chain separating two
    islands is one shared geometric object.  Simplifying that shared chain, and
    holding the junctions where three or more islands meet fixed, keeps the
    fishnet a partition: neither gaps nor overlaps can open between neighbours.
    Simplification uses Douglas-Peucker, whose error bound is symmetric and
    therefore the right choice for a boundary two regions must agree on.
    """
    region = np.asarray(region)
    if region.ndim != 2:
        raise ValueError("region must be a 2D array")
    if not np.isfinite(tolerance_px) or tolerance_px < 0.0:
        raise ValueError("tolerance_px must be finite and non-negative")

    height, width = region.shape
    stride = width + 1
    edge_nodes = _boundary_edges(region, stride)
    if edge_nodes.size == 0:
        return []

    node_count = (height + 1) * stride
    degree = np.bincount(edge_nodes.ravel(), minlength=node_count)
    order = np.argsort(edge_nodes.ravel(), kind="stable")
    incident_edge = (order // 2).astype(np.int64)
    start = np.zeros(node_count + 1, dtype=np.int64)
    np.cumsum(degree, out=start[1:])

    used = np.zeros(len(edge_nodes), dtype=bool)
    chains: list[list[int]] = []
    for junction in np.nonzero((degree != 2) & (degree > 0))[0]:
        for edge in incident_edge[start[junction] : start[junction + 1]]:
            if not used[edge]:
                chains.append(_walk_chain(int(junction), int(edge), edge_nodes, degree, incident_edge, start, used))
    for edge in range(len(edge_nodes)):
        if not used[edge]:
            chains.append(_walk_chain(int(edge_nodes[edge, 0]), edge, edge_nodes, degree, incident_edge, start, used))

    simplified = []
    for chain in chains:
        nodes = np.asarray(chain, dtype=np.int64)
        points = np.stack([nodes % stride, nodes // stride], axis=1).astype(np.float64)
        simplified.append(_simplify_chain(points, tolerance_px))
    return [chain for chain in simplified if len(chain) >= 2]


def _boundary_edges(region: np.ndarray, stride: int) -> np.ndarray:
    """Pixel-corner segments where two neighbouring pixels carry different islands.

    A node is a pixel corner, indexed ``row * stride + column`` on the grid one
    larger than the image in both axes. Returns the ``(edges, 2)`` node pairs.
    """
    height, width = region.shape
    edges = []
    if width > 1:
        rows, columns = np.nonzero(region[:, :-1] != region[:, 1:])
        node = rows * stride + (columns + 1)
        edges.append(np.stack([node, node + stride], axis=1))
    if height > 1:
        rows, columns = np.nonzero(region[:-1, :] != region[1:, :])
        node = (rows + 1) * stride + columns
        edges.append(np.stack([node, node + 1], axis=1))
    if not edges:
        return np.zeros((0, 2), dtype=np.int64)
    return np.concatenate(edges, axis=0)


def _walk_chain(
    node: int,
    edge: int,
    edge_nodes: np.ndarray,
    degree: np.ndarray,
    incident_edge: np.ndarray,
    start: np.ndarray,
    used: np.ndarray,
) -> list[int]:
    chain = [node]
    current = node
    current_edge = edge
    while True:
        used[current_edge] = True
        pair = edge_nodes[current_edge]
        current = int(pair[1]) if int(pair[0]) == current else int(pair[0])
        chain.append(current)
        if degree[current] != 2 or current == node:
            return chain
        following = [int(item) for item in incident_edge[start[current] : start[current + 1]] if not used[item]]
        if not following:
            return chain
        current_edge = following[0]


def _simplify_chain(points: np.ndarray, tolerance_px: float) -> np.ndarray:
    if tolerance_px <= 0.0 or len(points) < 3:
        return points
    if not np.array_equal(points[0], points[-1]):
        return approximate_polygon(points, tolerance_px)
    if len(points) < 6:
        return points
    middle = len(points) // 2
    first = approximate_polygon(points[: middle + 1], tolerance_px)
    second = approximate_polygon(points[middle:], tolerance_px)
    merged = np.concatenate([first[:-1], second], axis=0)
    return merged if len(merged) >= 4 else points


def _compact_regions(component: np.ndarray, labels: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    region = np.full(component.shape, UNPAINTABLE, dtype=np.int64)
    if not valid.any():
        return region, np.zeros(0, dtype=np.int64)
    unique, inverse = np.unique(component[valid], return_inverse=True)
    region[valid] = inverse
    region_class = np.zeros(len(unique), dtype=np.int64)
    region_class[inverse] = labels[valid].astype(np.int64)
    return region, region_class


def _merge_small_regions(
    region: np.ndarray,
    region_class: np.ndarray,
    labels: np.ndarray,
    adjacency_a: np.ndarray,
    adjacency_b: np.ndarray,
    min_region_pixels: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    flat_region = region.ravel()
    left = flat_region[adjacency_a]
    right = flat_region[adjacency_b]
    keep = (left >= 0) & (right >= 0) & (left != right)
    left, right = left[keep], right[keep]
    count = len(region_class)
    sizes = np.bincount(flat_region[flat_region >= 0], minlength=count)
    pair_a = np.concatenate([left, right])
    pair_b = np.concatenate([right, left])
    order = np.argsort(pair_a, kind="stable")
    pair_a, pair_b = pair_a[order], pair_b[order]
    bounds = np.searchsorted(pair_a, np.arange(count + 1))
    parent = np.arange(count, dtype=np.int64)

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = int(parent[item])
        return int(item)

    merged = 0
    for candidate in np.argsort(sizes, kind="stable"):
        if sizes[candidate] >= min_region_pixels:
            break
        root = find(int(candidate))
        neighbours = pair_b[bounds[candidate] : bounds[candidate + 1]]
        if neighbours.size == 0:
            continue
        roots = np.asarray([find(int(item)) for item in neighbours], dtype=np.int64)
        roots = roots[roots != root]
        if roots.size == 0:
            continue
        options, counts = np.unique(roots, return_counts=True)
        target = int(options[np.argmax(counts)])
        parent[root] = target
        sizes[target] += sizes[root]
        sizes[root] = 0
        merged += 1

    resolved = np.asarray([find(int(item)) for item in range(count)], dtype=np.int64)
    unique, inverse = np.unique(resolved, return_inverse=True)
    remapped = np.full(region.shape, UNPAINTABLE, dtype=np.int64)
    inside = region >= 0
    remapped[inside] = inverse[region[inside]]
    class_count = int(labels.max()) + 1 if labels.size else 1
    votes = np.bincount(
        remapped[inside] * class_count + labels[inside].astype(np.int64),
        minlength=len(unique) * class_count,
    ).reshape(len(unique), class_count)
    return remapped, votes.argmax(axis=1).astype(np.int64), merged

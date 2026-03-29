"""Post-processing: ghost removal, cluster merging, dormer detection."""

from __future__ import annotations

import re
from itertools import combinations

from aegis.environment.skeleton.events import Subtree, _DormerEvent, _EdgeEvent, _SplitEvent
from aegis.environment.skeleton.geometry import (
    EPSILON,
    PARALLEL,
    _cross2,
    _dot,
    _fit_circle_3_points,
    _iter_circular_prev_next,
    _magnitude,
    _segments_intersect,
    _vec_eq,
)

# ---------------------------------------------------------------------------
# Ghost removal
# ---------------------------------------------------------------------------


def _remove_self_loops(skeleton):
    """Remove sinks that coincide with their source."""
    for arc in skeleton:
        to_remove = [i for i, sink in enumerate(arc.sinks) if _vec_eq(arc.source, sink)]
        for i in reversed(to_remove):
            arc.sinks.pop(i)


def _try_resolve_parallel_pair(skeleton, arc, i0, i1):
    """Check if two sinks from the same source are parallel/crossed and merge them.

    Returns True if the sinks were resolved (modified skeleton in place).
    """
    source = arc.source
    s0 = arc.sinks[i0] - source
    s1 = arc.sinks[i1] - source
    s0m = _magnitude(s0)
    s1m = _magnitude(s1)
    if s0m == 0.0 or s1m == 0.0:
        return False

    dot_cosine_abs = abs(_dot(s0, s1) / (s0m * s1m) - 1.0)
    if dot_cosine_abs >= PARALLEL:
        return False

    if s0m < s1m:
        far_sink, near_sink = arc.sinks[i1], arc.sinks[i0]
    else:
        far_sink, near_sink = arc.sinks[i0], arc.sinks[i1]

    node_index_list = [idx for idx, node in enumerate(skeleton) if _vec_eq(node.source, near_sink)]
    if not node_index_list:
        return False

    node_index = node_index_list[0]

    if dot_cosine_abs < EPSILON:
        skeleton[node_index].sinks.append(far_sink)
        arc.sinks.remove(far_sink)
        arc.sinks.remove(near_sink)
        return True

    for sink in skeleton[node_index].sinks:
        if _segments_intersect(source, far_sink, near_sink, sink):
            skeleton[node_index].sinks.append(far_sink)
            arc.sinks.remove(far_sink)
            arc.sinks.remove(near_sink)
            return True

    return False


def _resolve_parallel_sinks(skeleton):
    """Find and resolve parallel or crossed skeleton edges."""
    for arc in skeleton:
        sinks_altered = True
        while sinks_altered:
            sinks_altered = False
            combs = list(combinations(range(len(arc.sinks)), 2))
            for i0, i1 in combs:
                if i0 >= len(arc.sinks) or i1 >= len(arc.sinks):
                    break
                if _try_resolve_parallel_pair(skeleton, arc, i0, i1):
                    sinks_altered = True
                    break


def _remove_ghosts(skeleton):
    """Remove ghost edges (self-loops and parallel/crossed edges) from the skeleton."""
    _remove_self_loops(skeleton)
    _resolve_parallel_sinks(skeleton)


# ---------------------------------------------------------------------------
# Apse detection
# ---------------------------------------------------------------------------


def _detect_apses(outer_contour):
    sequence = "".join(
        ["L" if abs(_cross2(p.norm, n.norm)) < 0.5 else "H" for p, n in _iter_circular_prev_next(outer_contour)]
    )
    if all(c == "L" for c in sequence):
        return None
    n = len(sequence)
    pattern = re.compile(r"(L){6,}")
    matches = list(pattern.finditer(sequence + sequence))
    if not matches:
        return None

    centers = []
    next_start = 0
    for apse in matches:
        s = apse.span()[0]
        if s < n and s >= next_start:
            apse_indices = [i % len(sequence) for i in range(*apse.span())]
            apse_vertices = [outer_contour[i].p1 for i in apse_indices]
            center, _r = _fit_circle_3_points(apse_vertices)
            centers.append(center)

    return centers


# ---------------------------------------------------------------------------
# Cluster detection and merging
# ---------------------------------------------------------------------------


def _is_apse_cluster(cluster, skeleton, apse_centers):
    """Check if a cluster overlaps with any detected apse center."""
    for apse_center in apse_centers:
        for node in cluster:
            dist = abs(apse_center[0] - skeleton[node].source[0]) + abs(apse_center[1] - skeleton[node].source[1])
            if dist < 3.0:
                return True
    return False


def _cluster_has_distant_sinks(cluster, skeleton, contour_vertices, thresh):
    """Check if contour sinks in the cluster are far enough apart to keep separate."""
    nr_contour_sinks = 0
    contour_sinks = []
    for node in cluster:
        sinks = skeleton[node].sinks
        contour_sinks.extend([s for s in sinks if any(_vec_eq(s, cv) for cv in contour_vertices)])
        nr_contour_sinks += sum(any(_vec_eq(el, s) for s in sinks) for el in contour_vertices)

    if nr_contour_sinks < 2:
        return False

    min_dist = 3 * thresh
    for pair in combinations(contour_sinks, 2):
        min_dist = min(_magnitude(pair[0] - pair[1]), min_dist)

    return min_dist <= 2 * thresh


def _find_clusters(skeleton, candidates, contour_vertices, edge_contours, thresh):
    apse_centers = _detect_apses(edge_contours[0])
    clusters = []
    while candidates:
        c0 = candidates[0]
        cluster = [c0]
        ref = skeleton[c0]
        for c in candidates[1:]:
            arc = skeleton[c]
            if abs(ref.source[0] - arc.source[0]) + abs(ref.source[1] - arc.source[1]) < thresh:
                cluster.append(c)
        for c in cluster:
            if c in candidates:
                candidates.remove(c)

        if len(cluster) <= 1:
            continue

        if apse_centers and _is_apse_cluster(cluster, skeleton, apse_centers):
            continue

        if _cluster_has_distant_sinks(cluster, skeleton, contour_vertices, thresh):
            continue

        clusters.append(cluster)

    return clusters


def _merge_cluster(skeleton, cluster):
    nodes_to_merge = cluster.copy()

    x, y, height = 0.0, 0.0, 0.0
    merged_sources = []
    for node in cluster:
        x += skeleton[node].source[0]
        y += skeleton[node].source[1]
        height += skeleton[node].height
        merged_sources.append(skeleton[node].source)
    from aegis.environment.skeleton.geometry import _vec2

    n = len(cluster)
    new_source = _vec2(x / n, y / n)
    new_height = height / n

    new_sinks = []
    for node in cluster:
        for sink in skeleton[node].sinks:
            if not any(_vec_eq(sink, ms) for ms in merged_sources) and not any(_vec_eq(sink, ns) for ns in new_sinks):
                new_sinks.append(sink)

    newnode = Subtree(new_source, new_height, new_sinks)

    for arc in skeleton:
        if not any(_vec_eq(arc.source, ms) for ms in merged_sources):
            to_remove = []
            for i, sink in enumerate(arc.sinks):
                if any(_vec_eq(sink, ms) for ms in merged_sources):
                    if any(_vec_eq(new_source, s) for s in arc.sinks):
                        to_remove.append(i)
                    else:
                        arc.sinks[i] = new_source
            for i in sorted(to_remove, reverse=True):
                del arc.sinks[i]

    for i in sorted(nodes_to_merge, reverse=True):
        del skeleton[i]
    skeleton.append(newnode)


def _merge_node_clusters(skeleton, edge_contours):
    # merge nodes with identical sources
    sources = {}
    to_remove = []
    for i, p in enumerate(skeleton):
        source_key = (float(p.source[0]), float(p.source[1]))
        if source_key in sources:
            source_index = sources[source_key]
            for sink in p.sinks:
                if not any(_vec_eq(sink, s) for s in skeleton[source_index].sinks):
                    skeleton[source_index].sinks.append(sink)
            to_remove.append(i)
        else:
            sources[source_key] = i
    for i in reversed(to_remove):
        skeleton.pop(i)

    contour_vertices = [edge.p1 for contour in edge_contours for edge in contour]

    small_thresh = 0.1
    had_cluster = True
    while had_cluster:
        had_cluster = False
        candidates = list(range(len(skeleton)))
        clusters = _find_clusters(skeleton, candidates, contour_vertices, edge_contours, small_thresh)
        if not clusters:
            break
        had_cluster = True
        cluster = max(clusters, key=len)
        _merge_cluster(skeleton, cluster)

    return skeleton


# ---------------------------------------------------------------------------
# Dormer detection
# ---------------------------------------------------------------------------


def _detect_dormers(slav, edge_contours):
    outer_contour = edge_contours[0]

    def coder(cp):
        if cp > 0.99:
            return "L"
        elif cp < -0.99:
            return "R"
        return "0"

    sequence = "".join([coder(_cross2(p.norm, n.norm)) for p, n in _iter_circular_prev_next(outer_contour)])
    n_seq = len(sequence)
    pattern = re.compile(r"(?=(RLLR))")
    matches = list(pattern.finditer(sequence + sequence))

    dormer_indices = []
    next_start = 0
    for dormer in matches:
        s = dormer.span()[0]
        if s < n_seq and s >= next_start:
            oi = [i % len(sequence) for i in range(s, s + 4)]
            dormer_indices.append(oi)
            next_start = s + 3

    # filter overlapping dormers
    to_remove = []
    for oi1, oi2 in zip(dormer_indices, dormer_indices[1:] + dormer_indices[:1], strict=False):
        if oi1[3] == oi2[0]:
            to_remove.extend([tuple(oi1), tuple(oi2)])
    for sp in to_remove:
        sp_list = list(sp)
        if sp_list in dormer_indices:
            dormer_indices.remove(sp_list)

    # check if contour consists only of dormers
    dormer_verts = set()
    for oi in dormer_indices:
        dormer_verts.update(oi)
    if len(dormer_verts) == len(outer_contour):
        return []

    dormers = []
    for oi in dormer_indices:
        w = outer_contour[oi[1]].length_squared()
        d1 = outer_contour[oi[0]].length_squared()
        d2 = outer_contour[oi[2]].length_squared()
        d = abs(d1 - d2) / (d1 + d2) if (d1 + d2) > 0 else 0
        d3 = outer_contour[(oi[0] + n_seq - 1) % n_seq].length_squared()
        d4 = outer_contour[oi[3]].length_squared()
        s = oi[0]  # use the first index for sequence lookup
        fac_left = 0.125 if sequence[(s + n_seq - 1) % n_seq] != "L" else 1.5
        fac_right = 0.125 if sequence[(s + 4) % n_seq] != "L" else 1.5
        if w < 100 and d < 0.35 and d3 >= w * fac_left and d4 >= w * fac_right:
            dormers.append((oi, _magnitude(outer_contour[oi[1]].p1 - outer_contour[oi[1]].p2)))

    return dormers


def _process_dormers(dormers, initial_events):
    dormer_events = []
    dormer_event_indices = []
    for dormer in dormers:
        dormer_idx = dormer[0]
        d_events = [ev for i, ev in enumerate(initial_events) if i in dormer_idx]
        if all(d is not None for d in d_events):
            if (
                not isinstance(d_events[0], _SplitEvent)
                or not isinstance(d_events[1], _EdgeEvent)
                or not isinstance(d_events[3], _SplitEvent)
            ):
                continue
            ev_prev = d_events[0]
            ev_next = d_events[3]
            v_prev = ev_prev.vertex
            v_next = ev_next.vertex
            p = v_prev.bisector.intersect(v_next.bisector)
            d = dormer[1] / 2.0
            dormer_events.append(_DormerEvent(d, p, [d_events[0], d_events[3], d_events[1]]))
            dormer_event_indices.extend(dormer_idx)

    remaining = [ev for i, ev in enumerate(initial_events) if i not in dormer_event_indices]
    del initial_events[:]
    initial_events.extend(remaining)
    initial_events.extend(dormer_events)

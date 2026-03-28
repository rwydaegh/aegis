"""Straight skeleton algorithm for polygon decomposition.

Pure numpy port of blosm's bpypolyskel + bpyeuclid + poly2FacesGraph.
No Blender/mathutils dependency.

Reference: Felkel & Obdrzalek (1998) "Straight skeleton implementation".
"""

from __future__ import annotations

import heapq
import re
from collections import Counter, defaultdict, namedtuple
from functools import cmp_to_key
from itertools import chain, combinations, cycle, islice, tee

import numpy as np

EPSILON = 0.00001
PARALLEL = 0.01  # 1-cos(alpha) threshold for parallel detection


# ---------------------------------------------------------------------------
# Vector helpers (replace mathutils)
# ---------------------------------------------------------------------------


def _vec2(x: float, y: float) -> np.ndarray:
    return np.array([x, y], dtype=np.float64)


def _magnitude(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def _normalize(v: np.ndarray) -> np.ndarray:
    m = _magnitude(v)
    if m == 0.0:
        return v.copy()
    return v / m


def _cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _dot(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _vec_eq(a: np.ndarray, b: np.ndarray) -> bool:
    return np.allclose(a, b, atol=1e-10)


def _approximately_equals(a: np.ndarray, b: np.ndarray) -> bool:
    diff = _magnitude(a - b)
    return diff <= max(_magnitude(a), _magnitude(b)) * 0.001


def _robust_float_equal(f1: float, f2: float) -> bool:
    if abs(f1 - f2) <= EPSILON:
        return True
    return abs(f1 - f2) <= EPSILON * max(abs(f1), abs(f2))


# ---------------------------------------------------------------------------
# Geometry primitives (replace bpyeuclid)
# ---------------------------------------------------------------------------


def _ccw(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> bool:
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


def _intersect_line2_line2(a_obj, b_obj):
    d = b_obj.v[1] * a_obj.v[0] - b_obj.v[0] * a_obj.v[1]
    if d == 0:
        return None

    dy = a_obj.p[1] - b_obj.p[1]
    dx = a_obj.p[0] - b_obj.p[0]
    ua = (b_obj.v[0] * dy - b_obj.v[1] * dx) / d
    if not a_obj.intsecttest(ua):
        return None
    ub = (a_obj.v[0] * dy - a_obj.v[1] * dx) / d
    if not b_obj.intsecttest(ub):
        return None

    return _vec2(a_obj.p[0] + ua * a_obj.v[0], a_obj.p[1] + ua * a_obj.v[1])


class Edge2:
    def __init__(self, p1, p2, norm=None, verts=None, center=None):
        if center is None:
            center = _vec2(0.0, 0.0)
        if verts is not None:
            self.i1 = p1
            self.i2 = p2
            p1_v = np.asarray(verts[p1], dtype=np.float64) - np.asarray(center, dtype=np.float64)
            p2_v = np.asarray(verts[p2], dtype=np.float64) - np.asarray(center, dtype=np.float64)
            p1 = _vec2(p1_v[0], p1_v[1])
            p2 = _vec2(p2_v[0], p2_v[1])
        else:
            p1 = np.asarray(p1, dtype=np.float64)
            p2 = np.asarray(p2, dtype=np.float64)
            p1 = _vec2(p1[0], p1[1])
            p2 = _vec2(p2[0], p2[1])

        self.p1 = p1
        self.p2 = p2
        if norm is not None:
            self.norm = _vec2(norm[0], norm[1])
        else:
            n = self.p2 - self.p1
            self.norm = _normalize(n)

    def length_squared(self):
        d = self.p2 - self.p1
        return _dot(d, d)


class Ray2:
    def __init__(self, p, v):
        self.p = p.copy()
        self.p1 = p.copy()
        self.p2 = p + v
        self.v = v.copy()

    def intsecttest(self, u):
        return u >= 0.0

    def intersect(self, other):
        return _intersect_line2_line2(self, other)


class Line2:
    def __init__(self, p1, p2=None, ptype=None):
        if p2 is None:
            # p1 is an Edge2, Ray2, or Line2
            self.p = p1.p1.copy()
            self.v = (p1.p2 - p1.p1).copy()
        elif ptype == "pp":
            self.p = p1.p.copy()
            self.v = p2 - p1
        elif ptype == "pv":
            self.p = p1.copy()
            self.v = p2.copy()
        else:
            # default: two points
            self.p = np.asarray(p1, dtype=np.float64).copy()
            self.v = (np.asarray(p2, dtype=np.float64) - self.p).copy()
        self.p1 = self.p
        self.p2 = self.p + self.v

    def intsecttest(self, u):
        return True

    def intersect(self, other):
        return _intersect_line2_line2(self, other)

    def distance(self, other):
        # other is a point (numpy array)
        d = self.v
        dd = _dot(d, d)
        if dd == 0.0:
            return _magnitude(other - self.p)
        t = _dot(other - self.p, d) / dd
        nearest = self.p + t * d
        return _magnitude(other - nearest)


def _fit_circle_3_points(points):
    n = len(points)
    x = complex(points[0][0], points[0][1])
    y = complex(points[n // 2][0], points[n // 2][1])
    z = complex(points[-1][0], points[-1][1])
    w = z - x
    w /= y - x
    c = (x - y) * (w - abs(w) ** 2) / 2j / w.imag - x
    x0 = -c.real
    y0 = -c.imag
    r = abs(c + x)
    return _vec2(x0, y0), r


# ---------------------------------------------------------------------------
# Circular iteration helpers
# ---------------------------------------------------------------------------


def _iter_circular_prev_next(lst):
    prevs, nexts = tee(lst)
    prevs = islice(cycle(prevs), len(lst) - 1, None)
    return zip(prevs, nexts, strict=False)


def _iter_circular_prev_this_next(lst):
    prevs, this, nexts = tee(lst, 3)
    prevs = islice(cycle(prevs), len(lst) - 1, None)
    nexts = islice(cycle(nexts), 1, None)
    return zip(prevs, this, nexts, strict=False)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class _SplitEvent(namedtuple("_SplitEvent", "distance, intersection_point, vertex, opposite_edge")):
    __slots__ = ()

    def __lt__(self, other):
        return self.distance < other.distance


class _EdgeEvent(namedtuple("_EdgeEvent", "distance intersection_point vertex_a vertex_b")):
    __slots__ = ()

    def __lt__(self, other):
        return self.distance < other.distance


class _DormerEvent:
    def __init__(self, distance, intersection_point, event_list):
        self.distance = distance
        self.intersection_point = intersection_point
        self.eventList = event_list

    def __lt__(self, other):
        return self.distance < other.distance


_OriginalEdge = namedtuple("_OriginalEdge", "edge bisector_prev, bisector_next")

Subtree = namedtuple("Subtree", "source, height, sinks")


# ---------------------------------------------------------------------------
# LAVertex, LAV, SLAV (core data structures)
# ---------------------------------------------------------------------------


class _LAVertex:
    def __init__(self, point, edge_prev, edge_next, direction_vectors=None, force_convex=False):
        self.point = point.copy()
        self.edge_prev = edge_prev
        self.edge_next = edge_next
        self.prev = None
        self.next = None
        self.lav = None
        self._valid = True

        creator_vectors = (edge_prev.norm * -1, edge_next.norm.copy())
        if direction_vectors is None:
            direction_vectors = creator_vectors

        dv0 = direction_vectors[0]
        dv1 = direction_vectors[1]
        self._is_reflex = _cross2(dv0, dv1) > 0
        if force_convex:
            self._is_reflex = False
        op_add = creator_vectors[0] + creator_vectors[1]
        self._bisector = Ray2(self.point, op_add * (-1 if self._is_reflex else 1))

    def invalidate(self):
        if self.lav is not None:
            self.lav.invalidate(self)
        else:
            self._valid = False

    @property
    def bisector(self):
        return self._bisector

    @property
    def is_reflex(self):
        return self._is_reflex

    @property
    def original_edges(self):
        return self.lav._slav._original_edges

    @property
    def is_valid(self):
        return self._valid

    def next_event(self):
        events = []
        if self.is_reflex:
            for edge in self.original_edges:
                if edge.edge is self.edge_prev or edge.edge is self.edge_next:
                    continue

                prevdot = abs(_dot(self.edge_prev.norm, edge.edge.norm))
                nextdot = abs(_dot(self.edge_next.norm, edge.edge.norm))
                selfedge = self.edge_prev if prevdot < nextdot else self.edge_next

                i = Line2(selfedge).intersect(Line2(edge.edge))
                if i is not None and not _approximately_equals(i, self.point):
                    linvec = _normalize(self.point - i)
                    edvec = edge.edge.norm.copy()
                    if abs(_cross2(self.bisector.v, linvec) - 1.0) < EPSILON:
                        linvec = _normalize(self.point - i + edvec * 0.01)
                    if _cross2(self.bisector.v, linvec) < 0:
                        edvec = -edvec

                    bisecvec = edvec + linvec
                    if not _magnitude(bisecvec):
                        continue
                    bisector = Line2(i, bisecvec, "pv")

                    b = bisector.intersect(self.bisector)

                    if b is None:
                        continue

                    # check eligibility
                    bpv = _normalize(edge.bisector_prev.v)
                    bpp = _normalize(b - edge.bisector_prev.p)
                    xprev = _cross2(bpv, bpp) < EPSILON

                    bnv = _normalize(edge.bisector_next.v)
                    bnp = _normalize(b - edge.bisector_next.p)
                    xnext = _cross2(bnv, bnp) > -EPSILON

                    bp1 = _normalize(b - edge.edge.p1)
                    xedge = _cross2(edge.edge.norm, bp1) > -EPSILON

                    parallel = _magnitude(edge.bisector_next.v) == 0.0
                    if not (xprev and xnext and xedge and not parallel):
                        continue

                    events.append(_SplitEvent(Line2(edge.edge).distance(b), b, self, edge.edge))

        i_prev = self.bisector.intersect(self.prev.bisector)
        i_next = self.bisector.intersect(self.next.bisector)

        if i_prev is not None:
            events.append(_EdgeEvent(Line2(self.edge_prev).distance(i_prev), i_prev, self.prev, self))
        if i_next is not None:
            events.append(_EdgeEvent(Line2(self.edge_next).distance(i_next), i_next, self, self.next))

        if not events:
            return None

        ev = min(events, key=lambda event: _magnitude(self.point - event.intersection_point))
        return ev


class _LAV:
    def __init__(self, slav):
        self.head = None
        self._slav = slav
        self._len = 0

    @classmethod
    def from_polygon(cls, edge_contour, slav):
        lav = cls(slav)
        for prev, nxt in _iter_circular_prev_next(edge_contour):
            lav._len += 1
            vertex = _LAVertex(nxt.p1, prev, nxt)
            vertex.lav = lav
            if lav.head is None:
                lav.head = vertex
                vertex.prev = vertex.next = vertex
            else:
                vertex.next = lav.head
                vertex.prev = lav.head.prev
                vertex.prev.next = vertex
                lav.head.prev = vertex
        return lav

    @classmethod
    def from_chain(cls, head, slav):
        lav = cls(slav)
        lav.head = head
        for vertex in lav:
            lav._len += 1
            vertex.lav = lav
        return lav

    def invalidate(self, vertex):
        assert vertex.lav is self, "Tried to invalidate a vertex that's not mine"
        vertex._valid = False
        if self.head == vertex:
            self.head = self.head.next
        vertex.lav = None

    def unify(self, vertex_a, vertex_b, point):
        replacement = _LAVertex(
            point,
            vertex_a.edge_prev,
            vertex_b.edge_next,
            (_normalize(vertex_b.bisector.v), _normalize(vertex_a.bisector.v)),
        )
        replacement.lav = self

        if self.head in [vertex_a, vertex_b]:
            self.head = replacement

        vertex_a.prev.next = replacement
        vertex_b.next.prev = replacement
        replacement.prev = vertex_a.prev
        replacement.next = vertex_b.next

        vertex_a.invalidate()
        vertex_b.invalidate()

        self._len -= 1
        return replacement

    def __len__(self):
        return self._len

    def __iter__(self):
        visited = set()
        cur = self.head
        while True:
            yield cur
            cur = cur.next
            if cur == self.head:
                return
            if id(cur) in visited:
                raise RuntimeError("Circular reference detected in LAV.")
            visited.add(id(cur))


class _SLAV:
    def __init__(self, edge_contours):
        self._lavs = [_LAV.from_polygon(ec, self) for ec in edge_contours]

        self._original_edges = [
            _OriginalEdge(vertex.edge_prev, vertex.prev.bisector, vertex.bisector)
            for vertex in chain.from_iterable(self._lavs)
        ]

    def __iter__(self):
        yield from self._lavs

    def empty(self):
        return not self._lavs

    def handle_dormer_event(self, event):
        ev_prev = event.eventList[0]
        ev_next = event.eventList[1]
        ev_edge = event.eventList[2]
        v_prev = ev_prev.vertex
        v_next = ev_next.vertex

        lav = ev_prev.vertex.lav
        if lav is None:
            return ([], [])

        to_remove = [v_prev, v_prev.next, v_next, v_next.prev]
        lav.head = v_prev.prev

        v_prev.prev.next = v_next.next
        v_next.next.prev = v_prev.prev

        new_lav = [_LAV.from_chain(lav.head, self)]
        self._lavs.remove(lav)
        self._lavs.append(new_lav[0])

        p = v_prev.bisector.intersect(v_next.bisector)
        arcs = []
        arcs.append(
            Subtree(
                ev_edge.intersection_point,
                ev_edge.distance,
                [ev_edge.vertex_a.point, ev_edge.vertex_b.point, p],
            )
        )
        arcs.append(Subtree(p, ev_edge.distance, [v_prev.point, v_next.point]))

        for v in to_remove:
            v.invalidate()

        return (arcs, [])

    def handle_edge_event(self, event):
        sinks = []
        events = []

        lav = event.vertex_a.lav
        if event.vertex_a.prev == event.vertex_b.next:
            # Peak event
            self._lavs.remove(lav)
            for vertex in list(lav):
                sinks.append(vertex.point)
                vertex.invalidate()
        else:
            new_vertex = lav.unify(event.vertex_a, event.vertex_b, event.intersection_point)
            if lav.head in (event.vertex_a, event.vertex_b):
                lav.head = new_vertex
            sinks.extend((event.vertex_a.point, event.vertex_b.point))
            next_event = new_vertex.next_event()
            if next_event is not None:
                events.append(next_event)
        return (Subtree(event.intersection_point, event.distance, sinks), events)

    def handle_split_event(self, event):
        lav = event.vertex.lav

        sinks = [event.vertex.point]
        vertices = []
        x = None
        y = None
        norm = event.opposite_edge.norm
        for v in chain.from_iterable(self._lavs):
            if _vec_eq(norm, v.edge_prev.norm) and _vec_eq(event.opposite_edge.p1, v.edge_prev.p1):
                x = v
                y = x.prev
            elif _vec_eq(norm, v.edge_next.norm) and _vec_eq(event.opposite_edge.p1, v.edge_next.p1):
                y = v
                x = y.next

            if x:
                yv = _normalize(y.bisector.v)
                yp = _normalize(event.intersection_point - y.point)
                xprev = _cross2(yv, yp) <= EPSILON

                xv = _normalize(x.bisector.v)
                xp = _normalize(event.intersection_point - x.point)
                xnext = _cross2(xv, xp) >= -EPSILON

                if xprev and xnext:
                    break
                else:
                    x = None
                    y = None

        if x is None:
            return (None, [])

        v1 = _LAVertex(event.intersection_point, event.vertex.edge_prev, event.opposite_edge, None, True)
        v2 = _LAVertex(event.intersection_point, event.opposite_edge, event.vertex.edge_next, None, True)

        v1.prev = event.vertex.prev
        v1.next = x
        event.vertex.prev.next = v1
        x.prev = v1

        v2.prev = y
        v2.next = event.vertex.next
        event.vertex.next.prev = v2
        y.next = v2

        new_lavs = None
        self._lavs.remove(lav)
        if lav != x.lav:
            self._lavs.remove(x.lav)
            new_lavs = [_LAV.from_chain(v1, self)]
        else:
            new_lavs = [_LAV.from_chain(v1, self), _LAV.from_chain(v2, self)]

        for lv in new_lavs:
            if len(lv) > 2:
                self._lavs.append(lv)
                vertices.append(lv.head)
            else:
                sinks.append(lv.head.next.point)
                for v in list(lv):
                    v.invalidate()

        events = []
        for vertex in vertices:
            next_event = vertex.next_event()
            if next_event is not None:
                events.append(next_event)

        event.vertex.invalidate()
        return (Subtree(event.intersection_point, event.distance, sinks), events)


# ---------------------------------------------------------------------------
# Event queue
# ---------------------------------------------------------------------------


class _EventQueue:
    def __init__(self):
        self.__data = []

    def put(self, item):
        if item is not None:
            heapq.heappush(self.__data, item)

    def put_all(self, iterable):
        for item in iterable:
            heapq.heappush(self.__data, item)

    def get(self):
        return heapq.heappop(self.__data)

    def get_all_equal_distance(self):
        item = heapq.heappop(self.__data)
        equal_list = [item]
        while self.__data and abs(self.__data[0].distance - item.distance) < 0.001:
            equal_list.append(heapq.heappop(self.__data))
        return equal_list

    def empty(self):
        return not self.__data


# ---------------------------------------------------------------------------
# Post-processing: ghost removal, cluster merging
# ---------------------------------------------------------------------------


def _remove_ghosts(skeleton):
    # remove loops
    for arc in skeleton:
        to_remove = []
        for i, sink in enumerate(arc.sinks):
            if _vec_eq(arc.source, sink):
                to_remove.append(i)
        for i in reversed(to_remove):
            arc.sinks.pop(i)

    # find and resolve parallel or crossed skeleton edges
    for arc in skeleton:
        source = arc.source
        sinks_altered = True
        while sinks_altered:
            sinks_altered = False
            combs = list(combinations(range(len(arc.sinks)), 2))
            for i0, i1 in combs:
                if i0 >= len(arc.sinks) or i1 >= len(arc.sinks):
                    break
                s0 = arc.sinks[i0] - source
                s1 = arc.sinks[i1] - source
                s0m = _magnitude(s0)
                s1m = _magnitude(s1)
                if s0m != 0.0 and s1m != 0.0:
                    dot_cosine_abs = abs(_dot(s0, s1) / (s0m * s1m) - 1.0)
                    if dot_cosine_abs < PARALLEL:
                        if s0m < s1m:
                            far_sink = arc.sinks[i1]
                            near_sink = arc.sinks[i0]
                        else:
                            far_sink = arc.sinks[i0]
                            near_sink = arc.sinks[i1]

                        node_index_list = [idx for idx, node in enumerate(skeleton) if _vec_eq(node.source, near_sink)]
                        if not node_index_list:
                            break

                        node_index = node_index_list[0]

                        if dot_cosine_abs < EPSILON:
                            skeleton[node_index].sinks.append(far_sink)
                            arc.sinks.remove(far_sink)
                            arc.sinks.remove(near_sink)
                            sinks_altered = True
                            break
                        else:
                            for sink in skeleton[node_index].sinks:
                                if _segments_intersect(source, far_sink, near_sink, sink):
                                    skeleton[node_index].sinks.append(far_sink)
                                    arc.sinks.remove(far_sink)
                                    arc.sinks.remove(near_sink)
                                    sinks_altered = True
                                    break


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
        if len(cluster) > 1:
            if apse_centers:
                is_apse_cluster = False
                for apse_center in apse_centers:
                    for node in cluster:
                        if (
                            abs(apse_center[0] - skeleton[node].source[0])
                            + abs(apse_center[1] - skeleton[node].source[1])
                            < 3.0
                        ):
                            is_apse_cluster = True
                            break
                    if is_apse_cluster:
                        break
                if is_apse_cluster:
                    continue

            nr_contour_sinks = 0
            contour_sinks = []
            for node in cluster:
                sinks = skeleton[node].sinks
                contour_sinks.extend([s for s in sinks if any(_vec_eq(s, cv) for cv in contour_vertices)])
                nr_contour_sinks += sum(any(_vec_eq(el, s) for s in sinks) for el in contour_vertices)

            if nr_contour_sinks < 2:
                clusters.append(cluster)
                continue

            min_dist = 3 * thresh
            sink_combs = list(combinations(contour_sinks, 2))
            for pair in sink_combs:
                min_dist = min(_magnitude(pair[0] - pair[1]), min_dist)

            if min_dist > 2 * thresh:
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


# ---------------------------------------------------------------------------
# poly2FacesGraph (face extraction)
# ---------------------------------------------------------------------------


def _pseudoangle(d):
    denom = abs(d[0]) + abs(d[1])
    if denom == 0:
        return 0
    p = d[0] / denom
    if d[1] < 0:
        return 3 + p
    return 1 - p


def _compare_angles(v_list, p1, p2, center):
    a1 = _pseudoangle(v_list[p1] - v_list[center])
    a2 = _pseudoangle(v_list[p2] - v_list[center])
    if a1 < a2:
        return 1
    return -1


class _Poly2FacesGraph:
    def __init__(self):
        self.g_dict = {}

    def add_vertex(self, vertex):
        if vertex not in self.g_dict:
            self.g_dict[vertex] = []

    def add_edge(self, edge):
        edge = set(edge)
        if len(edge) == 2:
            vertex1 = edge.pop()
            vertex2 = edge.pop()
            self.add_vertex(vertex1)
            self.add_vertex(vertex2)
            self.g_dict[vertex1].append(vertex2)
            self.g_dict[vertex2].append(vertex1)

    def edges(self):
        edges = []
        for vertex in self.g_dict:
            for neighbour in self.g_dict[vertex]:
                if {neighbour, vertex} not in edges:
                    edges.append((vertex, neighbour))
        return edges

    def circular_embedding(self, v_list, direction="CCW"):
        embedding = defaultdict(list)

        for vertex in self.g_dict:
            neighbors = self.g_dict[vertex]
            ordering = sorted(
                neighbors,
                key=cmp_to_key(lambda a, b, v=vertex: _compare_angles(v_list, a, b, v)),
            )

            if direction == "CCW":
                embedding[vertex] = ordering
            elif direction == "CW":
                embedding[vertex] = ordering[::-1]

        return embedding

    def faces(self, embedding, nr_of_poly_verts):
        edgeset = set()
        for edge in self.edges():
            edgeset.add((edge[0], edge[1]))
            edgeset.add((edge[1], edge[0]))

        faces = []
        path = []
        for edge in edgeset:
            path.append(edge)
            edgeset -= {edge}
            break

        while len(edgeset) > 0:
            neighbors = embedding[path[-1][-1]]
            next_node = neighbors[(neighbors.index(path[-1][-2]) + 1) % len(neighbors)]
            tup = (path[-1][-1], next_node)
            if tup == path[0]:
                faces.append(path)
                path = []
                for edge in edgeset:
                    path.append(edge)
                    edgeset -= {edge}
                    break
            else:
                if tup in path:
                    raise RuntimeError("Endless loop in poly2FacesGraph faces()")
                path.append(tup)
                edgeset -= {tup}
        if path:
            faces.append(path)

        final_faces = []
        for face in faces:
            orig_edges = [x[0] for x in enumerate(face) if x[1][0] < nr_of_poly_verts and x[1][1] < nr_of_poly_verts]
            if orig_edges:
                next_orig_index = next(
                    x[0] for x in enumerate(face) if x[1][0] < nr_of_poly_verts and x[1][1] < nr_of_poly_verts
                )
                face = face[next_orig_index:] + face[:next_orig_index]
            vert_list = [e[0] for e in face]
            if any(i >= nr_of_poly_verts for i in vert_list):
                final_faces.append(vert_list)
        return final_faces


# ---------------------------------------------------------------------------
# Public API: skeletonize
# ---------------------------------------------------------------------------


def skeletonize(edge_contours: list[np.ndarray]) -> list[Subtree]:
    """Compute the straight skeleton of a polygon.

    Args:
        edge_contours: list of contour arrays, each (N, 2) float64 vertices.
            First is outer polygon (CCW), rest are holes (CW).

    Returns:
        list of Subtree namedtuples where source/sinks are numpy arrays.
    """
    # Convert vertex arrays to Edge2 contours
    edge2_contours = []
    for contour in edge_contours:
        contour = np.asarray(contour, dtype=np.float64)
        edges = []
        n = len(contour)
        for i in range(n):
            p1 = _vec2(contour[i][0], contour[i][1])
            p2 = _vec2(contour[(i + 1) % n][0], contour[(i + 1) % n][1])
            edges.append(Edge2(p1, p2))
        edge2_contours.append(edges)

    return _skeletonize_edges(edge2_contours)


def _skeletonize_edges(edge_contours):
    """Core skeleton computation on Edge2 contours."""
    slav = _SLAV(edge_contours)

    dormers = _detect_dormers(slav, edge_contours)

    initial_events = []
    for lav in slav:
        for vertex in lav:
            initial_events.append(vertex.next_event())

    if dormers:
        _process_dormers(dormers, initial_events)

    output = []
    prioque = _EventQueue()
    for ev in initial_events:
        if ev:
            prioque.put(ev)

    while not (prioque.empty() or slav.empty()):
        top_event_list = prioque.get_all_equal_distance()
        for i in top_event_list:
            if isinstance(i, _EdgeEvent):
                if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
                    continue
                (arc, events) = slav.handle_edge_event(i)
            elif isinstance(i, _SplitEvent):
                if not i.vertex.is_valid:
                    continue
                (arc, events) = slav.handle_split_event(i)
            elif isinstance(i, _DormerEvent):
                if not i.eventList[0].vertex.is_valid or not i.eventList[1].vertex.is_valid:
                    continue
                (arc, events) = slav.handle_dormer_event(i)
            else:
                continue
            prioque.put_all(events)

            if arc is not None:
                if isinstance(arc, list):
                    output.extend(arc)
                else:
                    output.append(arc)

    # Convert Subtree sinks from tuples/lists to mutable lists for post-processing
    output = [Subtree(arc.source, arc.height, list(arc.sinks)) for arc in output]

    output = _merge_node_clusters(output, edge_contours)
    _remove_ghosts(output)

    return output


# ---------------------------------------------------------------------------
# Public API: polygonize
# ---------------------------------------------------------------------------


def polygonize(
    verts_out: list,
    footprint: np.ndarray,
    height: float = 0.0,
    tan: float = 0.0,
    holes: list | None = None,
) -> list[list[int]]:
    """Compute roof faces from a building footprint polygon.

    Args:
        verts_out: mutable list of 3D numpy arrays. Footprint vertices should
            already be at indices 0..N-1. Skeleton nodes are appended.
        footprint: (N, 2) or (N, 3) float64 vertices of outer polygon (CCW).
        height: maximum roof height. Takes precedence over tan.
        tan: tangent of roof pitch angle.
        holes: optional list of (M, 2) or (M, 3) arrays for hole contours (CW).

    Returns:
        list of faces, each a list of vertex indices into verts_out.
    """
    footprint = np.asarray(footprint, dtype=np.float64)
    if footprint.ndim != 2 or footprint.shape[0] < 3:
        return []

    # Extract z-base from first vertex (or 0)
    if footprint.shape[1] >= 3:
        z_base = float(footprint[0, 2])
        fp2d = footprint[:, :2]
    else:
        z_base = float(verts_out[0][2]) if len(verts_out) > 0 and len(verts_out[0]) >= 3 else 0.0
        fp2d = footprint

    num_poly_verts = len(fp2d)
    first_vert_index = 0  # footprint verts are assumed at start of verts_out

    # Compute center of gravity for numerical stability
    center = np.mean(fp2d, axis=0)

    # Build Edge2 contours (centered)
    edges2d = []
    for i in range(num_poly_verts):
        p1 = fp2d[i] - center
        p2 = fp2d[(i + 1) % num_poly_verts] - center
        e = Edge2(p1, p2)
        e.i1 = first_vert_index + i
        e.i2 = first_vert_index + (i + 1) % num_poly_verts
        edges2d.append(e)
    edge_contours = [edges2d.copy()]

    total_poly_verts = num_poly_verts
    hole_infos = []
    if holes:
        for hole in holes:
            hole = np.asarray(hole, dtype=np.float64)
            h2d = hole[:, :2] if hole.shape[1] >= 3 else hole
            n_hole = len(h2d)
            hole_start = len(verts_out)  # where hole verts start
            # Add hole verts to verts_out if not already there
            for v in h2d:
                verts_out.append(np.array([v[0], v[1], z_base]))
            hole_edges = []
            for i in range(n_hole):
                p1 = h2d[i] - center
                p2 = h2d[(i + 1) % n_hole] - center
                e = Edge2(p1, p2)
                e.i1 = hole_start + i
                e.i2 = hole_start + (i + 1) % n_hole
                hole_edges.append(e)
            edges2d.extend(hole_edges)
            edge_contours.append(hole_edges)
            hole_infos.append((hole_start, n_hole))
            total_poly_verts += n_hole

    # Skeletonize
    skeleton = _skeletonize_edges(edge_contours)

    # Compute skeleton node heights and append to verts_out
    if height and skeleton:
        max_skel_height = max(arc.height for arc in skeleton)
        tan_alpha = height / max_skel_height if max_skel_height > 0 else 0.0
    else:
        tan_alpha = tan

    first_skel_index = len(verts_out)
    for arc in skeleton:
        node = np.array([arc.source[0] + center[0], arc.source[1] + center[1], arc.height * tan_alpha + z_base])
        verts_out.append(node)

    # Build graph
    graph = _Poly2FacesGraph()

    # Add polygon edges
    for edge in _iter_circular_prev_next(list(range(first_vert_index, first_vert_index + num_poly_verts))):
        graph.add_edge(edge)

    # Add hole edges
    for hole_start, n_hole in hole_infos:
        for edge in _iter_circular_prev_next(list(range(hole_start, hole_start + n_hole))):
            graph.add_edge(edge)

    # Add skeleton edges
    # Need a combined verts list for the graph (as 2D for angle computation)
    # Build a verts lookup that works with indices
    for index, arc in enumerate(skeleton):
        a_index = index + first_skel_index
        for sink in arc.sinks:
            # search in input edges
            edge_match = [e for e in edges2d if _vec_eq(e.p1, sink)]
            if edge_match:
                s_index = edge_match[0].i1
            else:
                # search in skeleton nodes
                skel_match = [idx for idx, a in enumerate(skeleton) if _vec_eq(a.source, sink)]
                s_index = skel_match[0] + first_skel_index if skel_match else -1
            graph.add_edge((a_index, s_index))

    # Circular embedding needs a verts list indexed by vertex id
    # Build a dict-like list. We need verts as 2D for angle computations.
    max_idx = max(max(graph.g_dict), first_skel_index + len(skeleton) - 1) if graph.g_dict else 0
    graph_verts = [None] * (max_idx + 1)
    for i in range(len(verts_out)):
        v = verts_out[i]
        graph_verts[i] = _vec2(v[0], v[1])

    embedding = graph.circular_embedding(graph_verts, "CCW")

    faces3d = graph.faces(embedding, first_skel_index)

    # Spike removal
    had_spikes = True
    while had_spikes:
        had_spikes = False
        for face in faces3d:
            if len(face) <= 3:
                continue
            for prev_v, this_v, next_v in _iter_circular_prev_this_next(face):
                s0 = verts_out[this_v] - verts_out[prev_v]
                s1 = verts_out[next_v] - verts_out[this_v]
                s0_2d = _vec2(s0[0], s0[1])
                s1_2d = _vec2(s1[0], s1[1])
                s0m = _magnitude(s0_2d)
                s1m = _magnitude(s1_2d)
                if s0m and s1m:
                    dot_cosine = _dot(s0_2d, s1_2d) / (s0m * s1m)
                else:
                    continue
                cross_sine = _cross2(s0_2d, s1_2d)
                if abs(dot_cosine + 1.0) < PARALLEL and cross_sine > -EPSILON:
                    had_spikes = True
                    break

            if not had_spikes:
                continue

            right_idx, left_idx = None, None
            for fi, f in enumerate(faces3d):
                if [p for p, n in _iter_circular_prev_next(f) if p == this_v and n == prev_v]:
                    right_idx = fi
                if [p for p, n in _iter_circular_prev_next(f) if p == next_v and n == this_v]:
                    left_idx = fi

            if right_idx is None or left_idx is None:
                had_spikes = False
                continue

            if right_idx == left_idx:
                common_face = faces3d[right_idx]
                if this_v in common_face:
                    common_face.remove(this_v)
                if prev_v in common_face:
                    common_face.remove(prev_v)
                if this_v in face:
                    face.remove(this_v)
                break

            right_face = faces3d[right_idx]
            rot_index = next(x[0] for x in enumerate(right_face) if x[1] == prev_v)
            right_face = right_face[rot_index:] + right_face[:rot_index]

            left_face = faces3d[left_idx]
            rot_index = next(x[0] for x in enumerate(left_face) if x[1] == this_v)
            left_face = left_face[rot_index:] + left_face[:rot_index]

            merged_face = right_face + left_face[1:]

            orig_indices = [x[0] for x in enumerate(merged_face) if x[0] < first_skel_index and x[1] < first_skel_index]
            if orig_indices:
                next_orig_index = orig_indices[0]
                merged_face = merged_face[next_orig_index:] + merged_face[:next_orig_index]

            if merged_face == face:
                break

            if this_v in face:
                face.remove(this_v)
            for i in sorted([right_idx, left_idx], reverse=True):
                del faces3d[i]
            faces3d.append(merged_face)

            break

    # Fix adjacent parallel edges
    counts = Counter(chain.from_iterable(faces3d))
    for face in faces3d:
        if len(face) > 3:
            verts_to_remove = []
            for prev_v, this_v, next_v in _iter_circular_prev_this_next(face):
                if counts[this_v] < 3 and this_v >= first_skel_index:
                    s0 = verts_out[this_v] - verts_out[prev_v]
                    s1 = verts_out[next_v] - verts_out[this_v]
                    s0_2d = _vec2(s0[0], s0[1])
                    s1_2d = _vec2(s1[0], s1[1])
                    s0m = _magnitude(s0_2d)
                    s1m = _magnitude(s1_2d)
                    if s0m != 0.0 and s1m != 0.0:
                        dot_cosine = _dot(s0_2d, s1_2d) / (s0m * s1m)
                        if abs(dot_cosine - 1.0) < PARALLEL:
                            verts_to_remove.append(this_v)
                    else:
                        if this_v not in verts_to_remove:
                            verts_to_remove.append(this_v)
            for item in verts_to_remove:
                face.remove(item)

        # Remove adjacent identical vertices
        verts_to_remove = []
        for prev_v, next_v in _iter_circular_prev_next(face):
            if prev_v == next_v:
                verts_to_remove.append(prev_v)
        for item in verts_to_remove:
            if item in face:
                face.remove(item)

    return faces3d

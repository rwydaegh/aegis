"""Core SLAV data structures for the straight skeleton algorithm.

LAVertex, LAV (List of Active Vertices), and SLAV (Set of LAVs).
"""

from __future__ import annotations

from itertools import chain

from aegis.environment.skeleton.events import (
    Subtree,
    _EdgeEvent,
    _OriginalEdge,
    _SplitEvent,
)
from aegis.environment.skeleton.geometry import (
    EPSILON,
    Line2,
    Ray2,
    _approximately_equals,
    _cross2,
    _dot,
    _iter_circular_prev_next,
    _magnitude,
    _normalize,
    _vec_eq,
)


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

    def _check_split_candidate(self, edge):
        """Check if an original edge produces a valid split event for this reflex vertex."""
        prevdot = abs(_dot(self.edge_prev.norm, edge.edge.norm))
        nextdot = abs(_dot(self.edge_next.norm, edge.edge.norm))
        selfedge = self.edge_prev if prevdot < nextdot else self.edge_next

        i = Line2(selfedge).intersect(Line2(edge.edge))
        if i is None or _approximately_equals(i, self.point):
            return None

        linvec = _normalize(self.point - i)
        edvec = edge.edge.norm.copy()
        if abs(_cross2(self.bisector.v, linvec) - 1.0) < EPSILON:
            linvec = _normalize(self.point - i + edvec * 0.01)
        if _cross2(self.bisector.v, linvec) < 0:
            edvec = -edvec

        bisecvec = edvec + linvec
        if not _magnitude(bisecvec):
            return None
        bisector = Line2(i, bisecvec, "pv")

        b = bisector.intersect(self.bisector)
        if b is None:
            return None

        # Check eligibility against adjacent bisectors
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
            return None

        return _SplitEvent(Line2(edge.edge).distance(b), b, self, edge.edge)

    def next_event(self):
        events = []
        if self.is_reflex:
            for edge in self.original_edges:
                if edge.edge is self.edge_prev or edge.edge is self.edge_next:
                    continue
                ev = self._check_split_candidate(edge)
                if ev is not None:
                    events.append(ev)

        i_prev = self.bisector.intersect(self.prev.bisector)
        i_next = self.bisector.intersect(self.next.bisector)

        if i_prev is not None:
            events.append(_EdgeEvent(Line2(self.edge_prev).distance(i_prev), i_prev, self.prev, self))
        if i_next is not None:
            events.append(_EdgeEvent(Line2(self.edge_next).distance(i_next), i_next, self, self.next))

        if not events:
            return None

        return min(events, key=lambda event: _magnitude(self.point - event.intersection_point))


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

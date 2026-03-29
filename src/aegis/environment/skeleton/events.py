"""Event types and priority queue for the straight skeleton algorithm."""

from __future__ import annotations

import heapq
from collections import namedtuple


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

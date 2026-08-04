"""Things you can attach to a trace that change no number.

Four of them. :class:`PathRecorder` keeps a bounded set of polylines so a figure
can draw the rays the estimator integrated. :class:`BounceEvidenceTally` asks, at
each bounce depth, how much of the power lands on geometry a panorama actually
saw. :class:`MultiGather` fans the tracer's single ``gather`` hook out to several
observers, which is how the next event connection and the monostatic return share
one trace.

They have one property in common and it is the reason they are together: none of
them draws a random number and none of them touches an accumulator, so a traced
result is bit identical with them attached and without. The test suite asserts
that rather than trusting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

#: How a recorded ray stopped. ``sky`` escaped the crop, ``roulette`` was killed
#: by Russian roulette while still carrying throughput, ``truncated`` was still
#: travelling when the bounce budget ran out.
TERMINATIONS = ("sky", "roulette", "truncated")


@dataclass(frozen=True)
class PathRecord:
    """Polylines for a bounded subset of rays, in one flat buffer.

    ``offsets`` is the usual compressed layout: path ``i`` occupies
    ``vertices[offsets[i]:offsets[i + 1]]``. The first vertex of every path is
    the observation point and the last is either a point on the sky sphere or
    the surface where the ray died.
    """

    vertices: np.ndarray  # (V, 3)
    offsets: np.ndarray  # (R + 1,)
    throughput: np.ndarray  # (V,) throughput on the segment leaving each vertex
    face_class: np.ndarray  # (V,) class index at each vertex, -1 where not a surface
    exit_direction: np.ndarray  # (R, 3) direction of the final segment
    bounces: np.ndarray  # (R,)
    termination: np.ndarray  # (R,) index into TERMINATIONS

    def __len__(self) -> int:
        return int(self.offsets.size - 1)


class PathRecorder:
    """Keeps the polyline of the first ``capacity`` rays of the first batch.

    The storage rule for this study is that no path table reaches disk, and
    this does not break it. It is bounded by a capacity set at the call site,
    it is never enabled by a production run, and what it returns is a few
    thousand polylines rather than anything scaling with the ray count. It
    exists so a figure can show the rays the estimator actually integrated
    instead of a redrawing of them.
    """

    def __init__(self, capacity: int = 2000, *, sky_distance_m: float = 400.0) -> None:
        self.capacity = int(capacity)
        self.sky_distance_m = float(sky_distance_m)
        self._limit = 0
        self._started = False
        self._vertices: list[list[np.ndarray]] = []
        self._throughput: list[list[float]] = []
        self._face_class: list[list[int]] = []
        self._exit_direction: np.ndarray = np.zeros((0, 3))
        self._bounces: np.ndarray = np.zeros(0, dtype=np.int64)
        self._termination: np.ndarray = np.zeros(0, dtype=np.int64)
        self._closed: np.ndarray = np.zeros(0, dtype=bool)

    def begin(self, origin: np.ndarray, count: int) -> int:
        """Claim the first ``capacity`` rays of the first batch. Later batches see 0."""
        if self._started:
            return 0
        self._started = True
        self._limit = min(self.capacity, int(count))
        point = np.asarray(origin, dtype=np.float64)
        self._vertices = [[point.copy()] for _ in range(self._limit)]
        self._throughput = [[1.0] for _ in range(self._limit)]
        self._face_class = [[-1] for _ in range(self._limit)]
        self._exit_direction = np.zeros((self._limit, 3))
        self._bounces = np.zeros(self._limit, dtype=np.int64)
        self._termination = np.zeros(self._limit, dtype=np.int64)
        self._closed = np.zeros(self._limit, dtype=bool)
        return self._limit

    def _tracked(self, index: np.ndarray) -> np.ndarray:
        """Positions within ``index`` that name a ray this recorder is still following."""
        if self._limit == 0:
            return np.zeros(0, dtype=np.int64)
        slots = np.flatnonzero(np.asarray(index) < self._limit)
        return slots[~self._closed[np.asarray(index)[slots]]]

    def advance(
        self,
        index: np.ndarray,
        position: np.ndarray,
        throughput: np.ndarray,
        face_class: np.ndarray,
    ) -> None:
        """Append the surface vertex the ray just bounced off."""
        for slot in self._tracked(index):
            ray = int(index[slot])
            self._vertices[ray].append(position[slot].copy())
            self._throughput[ray].append(float(throughput[slot]))
            self._face_class[ray].append(int(face_class[slot]))

    def close(
        self,
        index: np.ndarray,
        position: np.ndarray,
        direction: np.ndarray,
        bounces: np.ndarray,
        how: str,
    ) -> None:
        """Terminate the ray, extending it along its last direction to the sky sphere."""
        kind = TERMINATIONS.index(how)
        for slot in self._tracked(index):
            ray = int(index[slot])
            reach = self.sky_distance_m if how == "sky" else 0.0
            self._vertices[ray].append(position[slot] + reach * direction[slot])
            self._throughput[ray].append(self._throughput[ray][-1])
            self._face_class[ray].append(-1)
            self._exit_direction[ray] = direction[slot]
            self._bounces[ray] = int(bounces[slot])
            self._termination[ray] = kind
            self._closed[ray] = True

    def result(self) -> PathRecord:
        counts = np.array([len(v) for v in self._vertices], dtype=np.int64)
        offsets = np.concatenate([[0], np.cumsum(counts)])
        vertices = (
            np.concatenate([np.asarray(v, dtype=np.float64) for v in self._vertices])
            if self._limit
            else np.zeros((0, 3))
        )
        return PathRecord(
            vertices=vertices,
            offsets=offsets,
            throughput=np.concatenate([np.asarray(t) for t in self._throughput]) if self._limit else np.zeros(0),
            face_class=np.concatenate([np.asarray(c, dtype=np.int64) for c in self._face_class])
            if self._limit
            else np.zeros(0, dtype=np.int64),
            exit_direction=self._exit_direction,
            bounces=self._bounces,
            termination=self._termination,
        )


class BounceEvidenceTally:
    """Where each bounce lands, split by whether a panorama saw that triangle.

    Each mask is a per triangle boolean on the tracer's own mesh, so no join is
    needed: it is true where at least one registered panorama collected a
    transient free ray on that triangle. The tally then answers one question per
    bounce depth, which is what fraction of the energy arriving at a surface at
    that depth arrives at a surface the image evidence actually covers.

    Two weights are kept because they answer different questions. The count is
    how often a ray lands on covered geometry. The throughput weight is how much
    of the power that survives to that depth lands on it, and it is the one that
    matters, because a bounce carrying a thousandth of the power is not where a
    material error hurts. Throughput is read before the reflectance of that
    interaction is applied, so it is the power incident on the surface.

    Several masks are carried at once because a trace is expensive and the
    definition of "observed" is not unique. One trace scores all of them, so the
    definitions are compared on identical rays rather than on separate runs.
    """

    def __init__(self, masks: dict[str, np.ndarray], max_depth: int) -> None:
        self.names = tuple(masks)
        self.masks = {name: np.asarray(mask, dtype=bool) for name, mask in masks.items()}
        self.max_depth = int(max_depth)
        self.hits = np.zeros(self.max_depth, dtype=np.int64)
        self.throughput = np.zeros(self.max_depth)
        self.hits_observed = {name: np.zeros(self.max_depth, dtype=np.int64) for name in self.names}
        self.throughput_observed = {name: np.zeros(self.max_depth) for name in self.names}

    def record(self, depth: int, face: np.ndarray, throughput: np.ndarray) -> None:
        """``depth`` is zero based, so bounce number ``depth + 1``."""
        if depth >= self.max_depth:
            return
        index = np.asarray(face, dtype=np.int64)
        self.hits[depth] += int(index.size)
        self.throughput[depth] += float(throughput.sum())
        for name, mask in self.masks.items():
            seen = mask[index]
            self.hits_observed[name][depth] += int(np.count_nonzero(seen))
            self.throughput_observed[name][depth] += float(throughput[seen].sum())

    def add(self, other: BounceEvidenceTally) -> None:
        """Pool another tally built from the same masks into this one."""
        self.hits += other.hits
        self.throughput += other.throughput
        for name in self.names:
            self.hits_observed[name] += other.hits_observed[name]
            self.throughput_observed[name] += other.throughput_observed[name]

    def fractions(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        """``(by_count, by_power)`` for one mask, NaN where nothing landed."""
        with np.errstate(invalid="ignore", divide="ignore"):
            by_count = np.where(self.hits > 0, self.hits_observed[name] / np.maximum(self.hits, 1), np.nan)
            by_power = np.where(
                self.throughput > 0.0,
                self.throughput_observed[name] / np.maximum(self.throughput, 1e-300),
                np.nan,
            )
        return by_count, by_power

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "bounce": list(range(1, self.max_depth + 1)),
            "hits": self.hits.tolist(),
            "incident_throughput": self.throughput.tolist(),
        }
        for name in self.names:
            by_count, by_power = self.fractions(name)
            out[name] = {
                "hits_on_observed_triangles": self.hits_observed[name].tolist(),
                "covered_fraction_by_count": [None if np.isnan(v) else float(v) for v in by_count],
                "incident_throughput_on_observed_triangles": self.throughput_observed[name].tolist(),
                "covered_fraction_by_power": [None if np.isnan(v) else float(v) for v in by_power],
            }
        return out


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

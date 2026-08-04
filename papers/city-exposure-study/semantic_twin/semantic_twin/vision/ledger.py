"""Sparse, replayable semantic observations for triangle-local decal atlases.

The ledger deliberately stores image observations rather than a dense array over
the support mesh.  A city mesh can contain millions of triangles while a single
panorama only observes a small subset.  A fixed-capacity ring buffer keeps the
in-memory representation bounded and preserves the newest observations in
chronological append order.  Callers can checkpoint the compressed NPZ before
advancing to the next acquisition batch.

Reads are shaped by the fact that a per-city batch is millions of rows over tens
of thousands of triangles.  Grouping sorts once instead of rescanning the batch
per triangle, and view identifiers are stored as codes into a table rather than
as a fixed-width string per observation.  Both are invisible from the outside:
the arrays handed back, and the NPZ written, are unchanged.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .conflict import DepthConflictState


@dataclass(frozen=True)
class LedgerObservations:
    """Chronologically ordered sparse observations currently retained."""

    triangle_id: np.ndarray
    barycentric_uv: np.ndarray
    label: np.ndarray
    material_channels: np.ndarray
    confidence: np.ndarray
    view_id: np.ndarray
    range_m: np.ndarray
    depth_conflict: np.ndarray

    def __len__(self) -> int:
        return len(self.triangle_id)

    @property
    def barycentric(self) -> np.ndarray:
        """Return full ``(w0, w1, w2)`` coordinates for ray-hit consumers."""
        return _barycentric(self.barycentric_uv)


@dataclass(frozen=True)
class _ValidatedBatch:
    """One accepted append, with view identifiers already reduced to codes."""

    triangle_id: np.ndarray
    barycentric_uv: np.ndarray
    label: np.ndarray
    material_channels: np.ndarray
    confidence: np.ndarray
    view_code: np.ndarray
    range_m: np.ndarray
    depth_conflict: np.ndarray

    def __len__(self) -> int:
        return len(self.triangle_id)


@dataclass(frozen=True)
class TriangleObservationGroup:
    """All currently retained observations for one support-mesh triangle."""

    triangle_id: int
    barycentric: np.ndarray
    labels: np.ndarray
    material_channels: np.ndarray
    confidence: np.ndarray
    view_ids: np.ndarray
    ranges_m: np.ndarray
    depth_conflicts: np.ndarray


class SparseAtlasLedger:
    """Appendable fixed-capacity observation ledger for semantic decals.

    ``max_observations`` is a hard memory limit.  When appending beyond it,
    the oldest retained rows are evicted.  This keeps online fusion safe for
    long camera trajectories while a caller may save NPZ checkpoints whenever
    it needs durable full-history storage.  The buffer is independent of the
    support mesh triangle count, so a high triangle identifier cannot cause a
    dense allocation.
    """

    _VIEW_ID_MAX_CHARS = 128
    _FORMAT_VERSION = 1

    def __init__(self, max_observations: int, material_channel_names: Iterable[str] = ()) -> None:
        if not isinstance(max_observations, (int, np.integer)) or max_observations <= 0:
            raise ValueError("max_observations must be a positive integer")
        names = tuple(str(name) for name in material_channel_names)
        if len(set(names)) != len(names) or any(not name for name in names):
            raise ValueError("material channel names must be unique and nonempty")

        self.max_observations = int(max_observations)
        self.material_channel_names = names
        self._head = 0
        self._size = 0
        self._triangle_id = np.empty(self.max_observations, dtype=np.int64)
        self._barycentric_uv = np.empty((self.max_observations, 2), dtype=np.float32)
        self._label = np.empty(self.max_observations, dtype=np.int32)
        self._material_channels = np.empty((self.max_observations, len(names)), dtype=np.float32)
        self._confidence = np.empty(self.max_observations, dtype=np.float32)
        # Observations are per pixel while view identifiers are per panorama, so
        # the buffer stores a code and keeps one copy of each name.  A fixed
        # 128 character slot per observation would otherwise be 512 bytes of the
        # 549 this ledger spends per row, and would put a per-city batch of a
        # million and a half observations at 790 MB of which 737 MB is repeated
        # panorama names.
        self._view_code = np.empty(self.max_observations, dtype=np.int32)
        self._view_names: list[str] = []
        self._view_lookup: dict[str, int] = {}
        self._range_m = np.empty(self.max_observations, dtype=np.float32)
        self._depth_conflict = np.empty(self.max_observations, dtype=np.uint8)

    def __len__(self) -> int:
        return self._size

    @property
    def observation_count(self) -> int:
        """Number of observations currently retained, capped by capacity."""
        return self._size

    def append(
        self,
        triangle_id: np.ndarray,
        barycentric_uv: np.ndarray,
        labels: np.ndarray,
        material_channels: np.ndarray,
        confidence: np.ndarray,
        view_id: np.ndarray | Iterable[str] | str,
        range_m: np.ndarray,
        depth_conflict: np.ndarray | Iterable[DepthConflictState | str | int] | DepthConflictState | str | int,
    ) -> None:
        """Append a batch of ray-associated image observations.

        ``barycentric_uv`` stores ``(w1, w2)`` in the canonical triangle chart.
        Material channels are independent values in ``[0, 1]``.  They need not
        sum to one, allowing, for example, glass and metal evidence to coexist.
        ``label`` is an integer categorical semantic class, with ``-1`` allowed
        for intentionally unlabelled pixels.
        """
        batch = self._validated_batch(
            triangle_id,
            barycentric_uv,
            labels,
            material_channels,
            confidence,
            view_id,
            range_m,
            depth_conflict,
        )
        count = len(batch)
        if not count:
            return
        if count >= self.max_observations:
            batch = _slice_batch(batch, slice(-self.max_observations, None))
            count = self.max_observations
            self._head = 0
            self._size = 0

        tail = (self._head + self._size) % self.max_observations
        slots = (tail + np.arange(count, dtype=np.intp)) % self.max_observations
        overflow = max(0, self._size + count - self.max_observations)
        self._head = (self._head + overflow) % self.max_observations
        self._size = min(self.max_observations, self._size + count)
        self._triangle_id[slots] = batch.triangle_id
        self._barycentric_uv[slots] = batch.barycentric_uv
        self._label[slots] = batch.label
        self._material_channels[slots] = batch.material_channels
        self._confidence[slots] = batch.confidence
        self._view_code[slots] = batch.view_code
        self._range_m[slots] = batch.range_m
        self._depth_conflict[slots] = batch.depth_conflict

    def _chronological_indices(self) -> np.ndarray | slice:
        """Ring-buffer slots in append order, as a slice while nothing has wrapped."""
        end = self._head + self._size
        if end <= self.max_observations:
            return slice(self._head, end)
        return (self._head + np.arange(self._size, dtype=np.intp)) % self.max_observations

    def observations(self) -> LedgerObservations:
        """Return retained observations in chronological append order."""
        indices = self._chronological_indices()
        # A basic slice is a view, so it still needs the copy that keeps the
        # returned record independent of the ring buffer.  Advanced indexing
        # already copies, and copying that result again would double both the
        # allocation and the memory traffic of every read of the ledger.
        copy = isinstance(indices, slice)
        return LedgerObservations(
            _read(self._triangle_id, indices, copy),
            _read(self._barycentric_uv, indices, copy),
            _read(self._label, indices, copy),
            _read(self._material_channels, indices, copy),
            _read(self._confidence, indices, copy),
            self._view_ids(self._view_code[indices]),
            _read(self._range_m, indices, copy),
            _read(self._depth_conflict, indices, copy),
        )

    def _view_ids(self, codes: np.ndarray) -> np.ndarray:
        """Expand stored view codes back into the fixed-width identifier array."""
        table = np.asarray(self._view_names, dtype=f"U{self._VIEW_ID_MAX_CHARS}")
        if not len(table):
            return np.empty(len(codes), dtype=f"U{self._VIEW_ID_MAX_CHARS}")
        return table[codes]

    def _triangle_segments(
        self,
        depth_conflicts: Iterable[DepthConflictState | str | int] | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Retained slots reordered by triangle, plus each triangle's start row.

        A single stable argsort replaces the per-triangle rescan of the whole
        batch that this used to do.  Stability is what preserves the documented
        contract: rows inside one triangle stay in chronological append order,
        and the triangles themselves come out ascending, exactly as a scan
        driven by ``np.unique`` produced them.
        """
        chronological = self._chronological_indices()
        if isinstance(chronological, slice):
            slots = np.arange(chronological.start, chronological.stop, dtype=np.intp)
        else:
            slots = chronological
        selected = _selected_conflicts(depth_conflicts)
        if selected is not None:
            wanted = np.zeros(256, dtype=bool)
            wanted[selected] = True
            slots = slots[wanted[self._depth_conflict[slots]]]
        triangles = self._triangle_id[slots]
        order = np.argsort(triangles, kind="stable")
        slots = slots[order]
        triangles = triangles[order]
        if not len(triangles):
            return slots, triangles, np.empty(0, dtype=np.intp)
        starts = np.flatnonzero(np.concatenate(([True], triangles[1:] != triangles[:-1])))
        return slots, triangles, starts.astype(np.intp, copy=False)

    def groups_by_triangle(
        self,
        *,
        depth_conflicts: Iterable[DepthConflictState | str | int] | None = None,
    ) -> tuple[TriangleObservationGroup, ...]:
        """Group sparse evidence by triangle for later decal rasterisation.

        The groups are sorted by triangle ID and keep chronological observation
        order within each triangle.  They can be concatenated into the arrays
        consumed by :func:`semantic_twin.vision.atlas.rasterize_triangle_evidence`.
        """
        slots, triangles, starts = self._triangle_segments(depth_conflicts)
        if not len(starts):
            return ()
        stops = np.concatenate((starts[1:], [len(slots)]))
        barycentric = _barycentric(self._barycentric_uv[slots])
        label = self._label[slots]
        material = self._material_channels[slots]
        confidence = self._confidence[slots]
        view_id = self._view_ids(self._view_code[slots])
        range_m = self._range_m[slots]
        depth_conflict = self._depth_conflict[slots]
        return tuple(
            TriangleObservationGroup(
                int(triangles[start]),
                barycentric[start:stop].copy(),
                label[start:stop].copy(),
                material[start:stop].copy(),
                confidence[start:stop].copy(),
                view_id[start:stop].copy(),
                range_m[start:stop].copy(),
                depth_conflict[start:stop].copy(),
            )
            for start, stop in zip(starts, stops)
        )

    def rasterize_inputs(
        self,
        *,
        depth_conflicts: Iterable[DepthConflictState | str | int] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return sparse arrays directly consumable by ``rasterize_triangle_evidence``.

        By default every retained depth state is returned.  Callers normally
        request only ``AGREEMENT`` and optionally ``UNCERTAIN`` evidence before
        painting a static support mesh.

        The grouped rows are already the concatenation this needs, so nothing
        here builds the per-triangle records.  That also keeps the view
        identifiers, which dominate the ledger's memory, out of the read path.
        """
        slots, triangles, _ = self._triangle_segments(depth_conflicts)
        if not len(slots):
            return (
                np.empty(0, dtype=np.int64),
                np.empty((0, 3), dtype=np.float32),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.float32),
            )
        return (
            triangles,
            _barycentric(self._barycentric_uv[slots]),
            self._label[slots],
            self._confidence[slots],
        )

    def save(self, path: pathlib.Path) -> None:
        """Serialize the retained sparse ledger to a compressed NPZ file."""
        observations = self.observations()
        metadata = {
            "format_version": self._FORMAT_VERSION,
            "max_observations": self.max_observations,
            "material_channel_names": self.material_channel_names,
            "depth_conflict_states": {state.name: int(state) for state in DepthConflictState},
        }
        np.savez_compressed(
            path,
            metadata=np.asarray(json.dumps(metadata)),
            triangle_id=observations.triangle_id,
            barycentric_uv=observations.barycentric_uv,
            label=observations.label,
            material_channels=observations.material_channels,
            confidence=observations.confidence,
            view_id=observations.view_id,
            range_m=observations.range_m,
            depth_conflict=observations.depth_conflict,
        )

    @classmethod
    def load(cls, path: pathlib.Path, *, max_observations: int | None = None) -> SparseAtlasLedger:
        """Load a compressed sparse NPZ ledger, optionally into a new capacity.

        A checkpoint is durable storage, so loading never evicts.  Requesting a
        capacity below the saved observation count raises instead of quietly
        returning the newest rows.
        """
        with np.load(path, allow_pickle=False) as document:
            metadata = json.loads(str(document["metadata"]))
            if metadata.get("format_version") != cls._FORMAT_VERSION:
                raise ValueError("unsupported sparse atlas ledger format")
            saved_count = len(document["triangle_id"])
            capacity = int(max_observations) if max_observations is not None else int(metadata["max_observations"])
            if saved_count > capacity:
                raise ValueError(
                    f"the checkpoint holds {saved_count} observations, which does not fit a capacity of "
                    f"{capacity}; load with max_observations >= {saved_count} to keep every row"
                )
            result = cls(capacity, metadata["material_channel_names"])
            result.append(
                document["triangle_id"],
                document["barycentric_uv"],
                document["label"],
                document["material_channels"],
                document["confidence"],
                document["view_id"],
                document["range_m"],
                document["depth_conflict"],
            )
        return result

    def _validated_batch(
        self,
        triangle_id: np.ndarray,
        barycentric_uv: np.ndarray,
        labels: np.ndarray,
        material_channels: np.ndarray,
        confidence: np.ndarray,
        view_id: np.ndarray | Iterable[str] | str,
        range_m: np.ndarray,
        depth_conflict: np.ndarray | Iterable[DepthConflictState | str | int] | DepthConflictState | str | int,
    ) -> _ValidatedBatch:
        triangle = np.asarray(triangle_id, dtype=np.int64)
        uv = np.asarray(barycentric_uv, dtype=np.float32)
        label = np.asarray(labels, dtype=np.int32)
        material = np.asarray(material_channels, dtype=np.float32)
        confidence_array = np.asarray(confidence, dtype=np.float32)
        distance = np.asarray(range_m, dtype=np.float32)
        if triangle.ndim != 1:
            raise ValueError("triangle_id must be one-dimensional")
        count = len(triangle)
        if (
            uv.shape != (count, 2)
            or label.shape != (count,)
            or confidence_array.shape != (count,)
            or distance.shape != (count,)
        ):
            raise ValueError("triangle, UV, label, confidence, and range inputs must have matching observation counts")
        if material.shape != (count, len(self.material_channel_names)):
            raise ValueError("material_channels must have shape (observations, material_channel_count)")
        if np.any(triangle < 0):
            raise ValueError("triangle_id cannot be negative")
        if np.any(label < -1):
            raise ValueError("labels must be nonnegative class identifiers or -1")
        if not np.all(np.isfinite(uv)) or np.any(uv < -1e-6) or np.any(uv.sum(axis=1) > 1.0 + 1e-6):
            raise ValueError("barycentric UV coordinates must be finite, nonnegative, and lie inside the triangle")
        if not np.all(np.isfinite(material)) or np.any((material < 0.0) | (material > 1.0)):
            raise ValueError("material channels must be finite values in [0, 1]")
        if not np.all(np.isfinite(confidence_array)) or np.any((confidence_array < 0.0) | (confidence_array > 1.0)):
            raise ValueError("confidence must be finite and lie in [0, 1]")
        if not np.all(np.isfinite(distance)) or np.any(distance < 0.0):
            raise ValueError("range_m must be finite and nonnegative")
        views = self._view_codes(view_id, count)
        conflicts = _depth_conflicts(depth_conflict, count)
        return _ValidatedBatch(triangle, uv, label, material, confidence_array, views, distance, conflicts)

    def _view_codes(self, value: np.ndarray | Iterable[str] | str, count: int) -> np.ndarray:
        """Validate view identifiers and reduce them to one code per observation."""
        if isinstance(value, str):
            return np.full(count, self._view_code_of(value), dtype=np.int32)
        source = np.asarray(value)
        if source.shape != (count,):
            raise ValueError("view_id must be a scalar string or one value per observation")
        names, inverse = np.unique(source, return_inverse=True)
        codes = np.fromiter(
            (self._view_code_of(name) for name in names.tolist()),
            dtype=np.int32,
            count=len(names),
        )
        return codes[inverse.reshape(-1)]

    def _view_code_of(self, value: object) -> int:
        text = str(value)
        if not text:
            raise ValueError("view_id cannot be empty")
        if len(text) > self._VIEW_ID_MAX_CHARS:
            raise ValueError(f"view_id cannot exceed {self._VIEW_ID_MAX_CHARS} characters")
        code = self._view_lookup.get(text)
        if code is None:
            code = len(self._view_names)
            self._view_names.append(text)
            self._view_lookup[text] = code
        return code


def _barycentric(uv: np.ndarray) -> np.ndarray:
    return np.column_stack((1.0 - uv[:, 0] - uv[:, 1], uv)).astype(np.float32, copy=False)


def _read(buffer: np.ndarray, indices: np.ndarray | slice, copy: bool) -> np.ndarray:
    values = buffer[indices]
    return values.copy() if copy else values


def _slice_batch(batch: _ValidatedBatch, selector: slice) -> _ValidatedBatch:
    return _ValidatedBatch(
        batch.triangle_id[selector],
        batch.barycentric_uv[selector],
        batch.label[selector],
        batch.material_channels[selector],
        batch.confidence[selector],
        batch.view_code[selector],
        batch.range_m[selector],
        batch.depth_conflict[selector],
    )


def _depth_conflicts(
    value: np.ndarray | Iterable[DepthConflictState | str | int] | DepthConflictState | str | int,
    count: int,
) -> np.ndarray:
    if isinstance(value, (DepthConflictState, str, int, np.integer)):
        raw = [value] * count
    else:
        raw = list(value)
        if len(raw) != count:
            raise ValueError("depth_conflict must be scalar or one value per observation")
    try:
        return np.asarray([int(_depth_conflict(item)) for item in raw], dtype=np.uint8)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("depth_conflict contains an unknown state") from error


def _depth_conflict(value: DepthConflictState | str | int) -> DepthConflictState:
    if isinstance(value, str):
        return DepthConflictState[value.upper()]
    return DepthConflictState(value)


def _selected_conflicts(
    values: Iterable[DepthConflictState | str | int] | None,
) -> np.ndarray | None:
    if values is None:
        return None
    return np.asarray([int(_depth_conflict(value)) for value in values], dtype=np.uint8)

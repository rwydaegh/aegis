"""Sparse, replayable semantic observations for triangle-local decal atlases.

The ledger deliberately stores image observations rather than a dense array over
the support mesh.  A city mesh can contain millions of triangles while a single
panorama only observes a small subset.  A fixed-capacity ring buffer keeps the
in-memory representation bounded and preserves the newest observations in
chronological append order.  Callers can checkpoint the compressed NPZ before
advancing to the next acquisition batch.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

import numpy as np


class DepthConflictState(IntEnum):
    """Relationship between image depth evidence and the support mesh."""

    AGREEMENT = 0
    UNCERTAIN = 1
    FRONT_BLOCKER = 2
    MESH_POSE_CONFLICT = 3
    NO_MESH_HIT = 4


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
        uv = self.barycentric_uv
        return np.column_stack((1.0 - uv[:, 0] - uv[:, 1], uv)).astype(np.float32, copy=False)


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
        self._view_id = np.empty(self.max_observations, dtype=f"U{self._VIEW_ID_MAX_CHARS}")
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
            batch = _slice_observations(batch, slice(-self.max_observations, None))
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
        self._view_id[slots] = batch.view_id
        self._range_m[slots] = batch.range_m
        self._depth_conflict[slots] = batch.depth_conflict

    def observations(self) -> LedgerObservations:
        """Return retained observations in chronological append order."""
        indices = (self._head + np.arange(self._size, dtype=np.intp)) % self.max_observations
        return LedgerObservations(
            self._triangle_id[indices].copy(),
            self._barycentric_uv[indices].copy(),
            self._label[indices].copy(),
            self._material_channels[indices].copy(),
            self._confidence[indices].copy(),
            self._view_id[indices].copy(),
            self._range_m[indices].copy(),
            self._depth_conflict[indices].copy(),
        )

    def groups_by_triangle(
        self,
        *,
        depth_conflicts: Iterable[DepthConflictState | str | int] | None = None,
    ) -> tuple[TriangleObservationGroup, ...]:
        """Group sparse evidence by triangle for later decal rasterisation.

        The groups are sorted by triangle ID and keep chronological observation
        order within each triangle.  They can be concatenated into the arrays
        consumed by :func:`semantic_twin.decal_atlas.rasterize_triangle_evidence`.
        """
        observations = self.observations()
        selected = _selected_conflicts(depth_conflicts)
        keep = np.ones(len(observations), dtype=bool)
        if selected is not None:
            keep &= np.isin(observations.depth_conflict, selected)
        indices = np.flatnonzero(keep)
        triangles = observations.triangle_id[indices]
        groups: list[TriangleObservationGroup] = []
        for triangle in np.unique(triangles):
            rows = indices[triangles == triangle]
            groups.append(
                TriangleObservationGroup(
                    int(triangle),
                    observations.barycentric[rows],
                    observations.label[rows],
                    observations.material_channels[rows],
                    observations.confidence[rows],
                    observations.view_id[rows],
                    observations.range_m[rows],
                    observations.depth_conflict[rows],
                )
            )
        return tuple(groups)

    def rasterize_inputs(
        self,
        *,
        depth_conflicts: Iterable[DepthConflictState | str | int] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return sparse arrays directly consumable by ``rasterize_triangle_evidence``.

        By default every retained depth state is returned.  Callers normally
        request only ``AGREEMENT`` and optionally ``UNCERTAIN`` evidence before
        painting a static support mesh.
        """
        groups = self.groups_by_triangle(depth_conflicts=depth_conflicts)
        if not groups:
            return (
                np.empty(0, dtype=np.int64),
                np.empty((0, 3), dtype=np.float32),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.float32),
            )
        return (
            np.concatenate([group.triangle_id * np.ones(len(group.labels), dtype=np.int64) for group in groups]),
            np.concatenate([group.barycentric for group in groups]),
            np.concatenate([group.labels for group in groups]),
            np.concatenate([group.confidence for group in groups]),
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
    ) -> LedgerObservations:
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
        views = _view_ids(view_id, count, self._VIEW_ID_MAX_CHARS)
        conflicts = _depth_conflicts(depth_conflict, count)
        return LedgerObservations(triangle, uv, label, material, confidence_array, views, distance, conflicts)


def _slice_observations(observations: LedgerObservations, selector: slice) -> LedgerObservations:
    return LedgerObservations(
        observations.triangle_id[selector],
        observations.barycentric_uv[selector],
        observations.label[selector],
        observations.material_channels[selector],
        observations.confidence[selector],
        observations.view_id[selector],
        observations.range_m[selector],
        observations.depth_conflict[selector],
    )


def _view_ids(value: np.ndarray | Iterable[str] | str, count: int, maximum_length: int) -> np.ndarray:
    if isinstance(value, str):
        source = np.full(count, value, dtype=object)
    else:
        source = np.asarray(value, dtype=object)
        if source.shape != (count,):
            raise ValueError("view_id must be a scalar string or one value per observation")
    if np.any(source == ""):
        raise ValueError("view_id cannot be empty")
    if any(len(str(item)) > maximum_length for item in source):
        raise ValueError(f"view_id cannot exceed {maximum_length} characters")
    return source.astype(f"U{maximum_length}")


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

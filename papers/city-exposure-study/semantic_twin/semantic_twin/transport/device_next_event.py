"""Resident diffuse and sampled-specular next-event connections.

The device tracer keeps every path state on the selected Dr.Jit backend.  This
module connects every blocking vertex directly to a sampled source.  It can
also sample one finite reflector from the complete nondegenerate face support
and solve the source-nearest one-reflection image path without leaving Dr.Jit.
Direct source atoms and adaptive all-specular paths remain host calculations.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..illumination.sources import normalized_source_weights
from ..illumination.sphere import nearest_cell

SPECULAR_FACE_PROPOSAL = "0.9_triangle_area_plus_0.1_uniform_full_support_v1"
SPECULAR_SOURCE_PROPOSAL = "existing_normalized_discrete_source_weights_v1"
SPECULAR_COUNTER_GENERATOR = "splitmix64_seed_counter_dimension_v1"
SPECULAR_SOURCE_COUNTER_DIMENSION = 0
SPECULAR_FACE_COUNTER_DIMENSION = 1
_MASK_64 = (1 << 64) - 1


@dataclass(frozen=True)
class DeviceNextEventBatch:
    """Fixed-width diffuse and sampled-specular deposits for one ray range."""

    weight_by_order: np.ndarray
    connections_by_order: np.ndarray
    cleared_by_order: np.ndarray
    ray_start: int
    rays: int
    samples: int
    specular_weight_by_order: np.ndarray | None = None
    specular_candidates_by_order: np.ndarray | None = None
    specular_geometric_by_order: np.ndarray | None = None
    specular_visible_by_order: np.ndarray | None = None
    specular_accepted_by_order: np.ndarray | None = None
    sampled_specular_samples: int = 1

    def __post_init__(self) -> None:
        arrays = _validated_batch_arrays(self)
        weight, connections, cleared, specular_weight, candidates, geometric, visible, accepted = arrays
        object.__setattr__(self, "weight_by_order", weight)
        object.__setattr__(self, "connections_by_order", connections)
        object.__setattr__(self, "cleared_by_order", cleared)
        object.__setattr__(self, "specular_weight_by_order", specular_weight)
        object.__setattr__(self, "specular_candidates_by_order", candidates)
        object.__setattr__(self, "specular_geometric_by_order", geometric)
        object.__setattr__(self, "specular_visible_by_order", visible)
        object.__setattr__(self, "specular_accepted_by_order", accepted)


def _specular_count_array(raw: np.ndarray | None, orders: int, name: str) -> np.ndarray:
    value = np.zeros(orders, dtype=np.uint64) if raw is None else np.asarray(raw, dtype=np.uint64)
    if value.shape != (orders,):
        raise ValueError(f"{name} must have one value per order")
    return value


def _validated_batch_arrays(batch: DeviceNextEventBatch) -> tuple[np.ndarray, ...]:
    """Normalize and validate one transferred batch without changing its layout."""
    weight = np.asarray(batch.weight_by_order, dtype=np.float32)
    connections = np.asarray(batch.connections_by_order, dtype=np.uint64)
    cleared = np.asarray(batch.cleared_by_order, dtype=np.uint64)
    if weight.ndim != 2 or weight.shape[1] != batch.rays:
        raise ValueError("weight_by_order must have shape (orders, rays)")
    if connections.shape != (weight.shape[0],) or cleared.shape != connections.shape:
        raise ValueError("connection counts must have one value per order")
    if np.any(cleared > connections):
        raise ValueError("cleared connections cannot exceed attempted connections")
    if batch.ray_start < 0 or batch.rays < 1 or batch.samples < 1:
        raise ValueError("device next-event batch metadata is invalid")
    specular_weight = (
        np.zeros_like(weight)
        if batch.specular_weight_by_order is None
        else np.asarray(batch.specular_weight_by_order, dtype=np.float32)
    )
    if specular_weight.shape != weight.shape:
        raise ValueError("specular_weight_by_order must align with diffuse order rows")
    count_arguments = (
        (batch.specular_candidates_by_order, "specular_candidates_by_order"),
        (batch.specular_geometric_by_order, "specular_geometric_by_order"),
        (batch.specular_visible_by_order, "specular_visible_by_order"),
        (batch.specular_accepted_by_order, "specular_accepted_by_order"),
    )
    candidates, geometric, visible, accepted = (
        _specular_count_array(raw, weight.shape[0], name) for raw, name in count_arguments
    )
    if np.any(accepted > visible) or np.any(visible > geometric) or np.any(geometric > candidates):
        raise ValueError("sampled specular diagnostic stages must be monotonically decreasing")
    if batch.sampled_specular_samples < 1:
        raise ValueError("sampled_specular_samples must be positive")
    return weight, connections, cleared, specular_weight, candidates, geometric, visible, accepted


def _alias_table(probabilities: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build a deterministic Vose table and verify its represented measure."""
    probability = np.asarray(probabilities, dtype=np.float64)
    if probability.ndim != 1 or probability.size == 0:
        raise ValueError("device next-event estimation needs at least one source")
    if np.any(~np.isfinite(probability)) or np.any(probability < 0.0):
        raise ValueError("source probabilities must be finite and nonnegative")
    total = float(np.sum(probability, dtype=np.float64))
    if total <= 0.0:
        raise ValueError("source probabilities must contain positive mass")
    probability = probability / total
    count = probability.size
    scaled = probability * count
    threshold = np.ones(count, dtype=np.float64)
    alias = np.arange(count, dtype=np.uint32)
    small = [int(index) for index in np.flatnonzero(scaled < 1.0)]
    large = [int(index) for index in np.flatnonzero(scaled >= 1.0)]
    while small and large:
        low = small.pop()
        high = large.pop()
        threshold[low] = scaled[low]
        alias[low] = high
        scaled[high] -= 1.0 - scaled[low]
        if scaled[high] < 1.0 - 2.0e-15:
            small.append(high)
        else:
            large.append(high)
    threshold[np.asarray(small + large, dtype=np.int64)] = 1.0

    # The device stores float32 thresholds.  Validate the distribution that the
    # device will actually draw, rather than only the float64 construction.
    threshold32 = threshold.astype(np.float32)
    represented = threshold32.astype(np.float64) / count
    spill = (1.0 - threshold32.astype(np.float64)) / count
    np.add.at(represented, alias.astype(np.int64), spill)
    if not np.allclose(represented, probability, rtol=2.0e-7, atol=2.0e-10):
        raise ValueError("float32 alias table does not preserve the source probabilities")
    return threshold32, alias


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _splitmix_seed_word(seed: int) -> int:
    value = (int(seed) + 0x9E3779B97F4A7C15) & _MASK_64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK_64
    return value ^ (value >> 31)


def _splitmix_uniform(mi: Any, counter: Any, seed: int, dimension: int) -> Any:
    """Float32 uniform from the CPU reference's SplitMix64 counter word."""
    value = counter ^ mi.UInt64(_splitmix_seed_word(seed))
    value ^= mi.UInt64(((int(dimension) + 1) * 0xD1B54A32D192ED03) & _MASK_64)
    value += mi.UInt64(0x9E3779B97F4A7C15)
    value = (value ^ (value >> 30)) * mi.UInt64(0xBF58476D1CE4E5B9)
    value = (value ^ (value >> 27)) * mi.UInt64(0x94D049BB133111EB)
    value ^= value >> 31
    return mi.Float(value >> 40) * (1.0 / float(1 << 24))


@dataclass
class DeviceNextEventGather:
    """Host owner of one resident diffuse next-event trace.

    ``chi_bounce`` and ``bounced_mass`` use the same fixed-width deposits.  Their
    sums therefore differ only by host float64 reduction order.  The source draw
    uses a separate counter stream at ``trace_seed + seed_offset`` and is keyed by
    global ray index, bounce depth, and sample number.  Changing a transfer batch
    does not change any path or source draw.
    """

    sources: Any
    samples: int = 1
    max_order: int | None = None
    seed_offset: int = 1000
    epsilon_m: float = 1.0e-3
    lift_m: float = 1.0e-2
    min_connect_m: float = 0.5
    specular_suffix_order: int = 0
    sampled_specular_samples: int = 1
    sampled_specular_seed_offset: int = 2000
    collect_field: bool = True

    _sites: np.ndarray = field(init=False, repr=False)
    _probabilities: np.ndarray = field(init=False, repr=False)
    _alias_threshold: np.ndarray = field(init=False, repr=False)
    _alias_index: np.ndarray = field(init=False, repr=False)
    _device_key: tuple[str, int] | None = field(init=False, default=None, repr=False)
    _device_arrays: tuple[Any, ...] | None = field(init=False, default=None, repr=False)
    _specular_device_key: tuple[str, int] | None = field(init=False, default=None, repr=False)
    _specular_device_arrays: tuple[Any, ...] | None = field(init=False, default=None, repr=False)
    _face_triangles: np.ndarray = field(init=False, default_factory=lambda: np.empty((0, 3, 3)), repr=False)
    _face_normals: np.ndarray = field(init=False, default_factory=lambda: np.empty((0, 3)), repr=False)
    _face_index: np.ndarray = field(init=False, default_factory=lambda: np.empty(0, dtype=np.uint32), repr=False)
    _face_probability: np.ndarray = field(init=False, default_factory=lambda: np.empty(0), repr=False)
    _face_alias_threshold: np.ndarray = field(init=False, default_factory=lambda: np.empty(0), repr=False)
    _face_alias_index: np.ndarray = field(init=False, default_factory=lambda: np.empty(0, dtype=np.uint32), repr=False)
    _surface_support_complete: bool = field(init=False, default=False, repr=False)
    _surface_scene_face_count: int = field(init=False, default=0, repr=False)
    _expected_rays: int = field(init=False, default=0, repr=False)
    _received_rays: int = field(init=False, default=0, repr=False)
    _sampled_specular_counter: int = field(init=False, default=0, repr=False)
    _local_grid: np.ndarray | None = field(init=False, default=None, repr=False)
    _raw_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1), repr=False)
    _raw_field_mass: np.ndarray = field(init=False, default_factory=lambda: np.zeros(0), repr=False)
    _connections_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _cleared_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False)
    _specular_raw_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1), repr=False)
    _specular_raw_field_mass: np.ndarray = field(init=False, default_factory=lambda: np.zeros(0), repr=False)
    _specular_candidates_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_geometric_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_visible_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_accepted_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )

    def __post_init__(self) -> None:
        if self.samples < 1:
            raise ValueError("samples must be positive")
        if self.max_order is not None and self.max_order < 0:
            raise ValueError("max_order must be nonnegative")
        if self.epsilon_m <= 0.0 or self.lift_m < 0.0 or self.min_connect_m < 0.0:
            raise ValueError("next-event distances must be nonnegative and epsilon must be positive")
        if self.specular_suffix_order not in (0, 1):
            raise NotImplementedError("resident device next-event estimation completes at most one specular suffix")
        if self.sampled_specular_samples < 1:
            raise ValueError("sampled_specular_samples must be positive")
        if self.sampled_specular_seed_offset < 0:
            raise ValueError("sampled_specular_seed_offset must be nonnegative")
        sites = np.asarray(self.sources.sites(), dtype=np.float64)
        if sites.ndim != 2 or sites.shape[1] != 3 or not np.all(np.isfinite(sites)):
            raise ValueError("source sites must have shape (sources, 3) and be finite")
        probabilities = normalized_source_weights(self.sources)
        if sites.shape[0] == 0:
            raise ValueError("resident device next-event estimation needs at least one source")
        threshold, alias = _alias_table(probabilities)
        self._sites = np.ascontiguousarray(sites, dtype=np.float32)
        self._probabilities = np.asarray(probabilities, dtype=np.float64)
        self._alias_threshold = threshold
        self._alias_index = alias

    @property
    def probabilities(self) -> np.ndarray:
        return self._probabilities.copy()

    @property
    def face_probabilities(self) -> np.ndarray:
        return self._face_probability.copy()

    @property
    def sampled_specular_ready(self) -> bool:
        return bool(self.specular_suffix_order == 1 and self._face_probability.size)

    def _prepare_specular_support(self, kernel: Any) -> None:
        if self.specular_suffix_order == 0:
            return
        geometry = kernel.geometry
        key = (str(getattr(geometry, "variant", "")), id(geometry))
        if self._specular_device_key == key and self._specular_device_arrays is not None:
            return
        if not hasattr(geometry, "vertices") or not hasattr(geometry, "faces"):
            self._face_triangles = np.empty((0, 3, 3), dtype=np.float32)
            self._face_normals = np.empty((0, 3), dtype=np.float32)
            self._face_index = np.empty(0, dtype=np.uint32)
            self._face_probability = np.empty(0, dtype=np.float64)
            self._face_alias_threshold = np.empty(0, dtype=np.float32)
            self._face_alias_index = np.empty(0, dtype=np.uint32)
            self._surface_support_complete = True
            self._surface_scene_face_count = 0
            self._specular_device_key = key
            self._specular_device_arrays = ()
            return
        vertices = np.asarray(geometry.vertices, dtype=np.float64)
        faces = np.asarray(geometry.faces, dtype=np.int64)
        triangles = vertices[faces]
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        double_area = np.linalg.norm(cross, axis=1)
        valid = double_area > 1.0e-12
        triangles = triangles[valid]
        double_area = double_area[valid]
        face_index = np.arange(faces.shape[0], dtype=np.uint32)[valid]
        self._surface_scene_face_count = int(np.sum(valid))
        self._surface_support_complete = True
        if triangles.shape[0] == 0:
            self._face_triangles = np.empty((0, 3, 3), dtype=np.float32)
            self._face_normals = np.empty((0, 3), dtype=np.float32)
            self._face_index = face_index
            self._face_probability = np.empty(0, dtype=np.float64)
            self._face_alias_threshold = np.empty(0, dtype=np.float32)
            self._face_alias_index = np.empty(0, dtype=np.uint32)
            self._specular_device_key = key
            self._specular_device_arrays = ()
            return
        area = 0.5 * double_area
        count = area.size
        probability = 0.9 * area / np.sum(area, dtype=np.float64) + 0.1 / count
        threshold, alias = _alias_table(probability)
        self._face_triangles = np.ascontiguousarray(triangles, dtype=np.float32)
        self._face_normals = np.ascontiguousarray(cross[valid] / double_area[:, None], dtype=np.float32)
        self._face_index = np.ascontiguousarray(face_index)
        self._face_probability = np.asarray(probability, dtype=np.float64)
        self._face_alias_threshold = threshold
        self._face_alias_index = alias
        self._specular_device_key = None
        self._specular_device_arrays = None

    def begin_trace(self, rays: int, local_grid: np.ndarray) -> None:
        """Reset host reductions before a complete, possibly batched trace."""
        if rays < 1:
            raise ValueError("rays must be positive")
        grid = np.asarray(local_grid, dtype=np.float64)
        if grid.ndim != 2 or grid.shape[1] != 3 or grid.shape[0] == 0:
            raise ValueError("local_grid must have shape (positive cells, 3)")
        self._expected_rays = int(rays)
        self._received_rays = 0
        self._sampled_specular_counter = 0
        self._local_grid = grid
        initial_orders = 1 if self.max_order is None else self.max_order + 1
        self._raw_by_order = np.zeros(initial_orders, dtype=np.float64)
        self._raw_field_mass = np.zeros(grid.shape[0], dtype=np.float64) if self.collect_field else np.empty(0)
        self._connections_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._cleared_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_raw_by_order = np.zeros(initial_orders, dtype=np.float64)
        self._specular_raw_field_mass = np.zeros(grid.shape[0], dtype=np.float64) if self.collect_field else np.empty(0)
        self._specular_candidates_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_geometric_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_visible_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_accepted_by_order = np.zeros(initial_orders, dtype=np.uint64)

    def consume(
        self,
        batch: DeviceNextEventBatch,
        launch_direction: np.ndarray,
        *,
        launch_cells: np.ndarray | None = None,
    ) -> None:
        """Reduce one returned ray range without retaining per-ray deposits."""
        launch = self._validated_launch(batch, launch_direction)
        source_order_count = batch.weight_by_order.shape[0]
        order_count = source_order_count if self.max_order is None else self.max_order + 1
        self._grow_order_accumulators(order_count)
        self._accumulate_order_reductions(batch, source_order_count, order_count)
        self._sampled_specular_counter += int(np.sum(batch.specular_candidates_by_order, dtype=np.uint64))
        if self.collect_field:
            self._accumulate_field(batch, launch, launch_cells, source_order_count)
        self._received_rays += batch.rays

    def _validated_launch(self, batch: DeviceNextEventBatch, launch_direction: np.ndarray) -> np.ndarray:
        if self._local_grid is None:
            raise RuntimeError("begin_trace must be called before consuming device deposits")
        if batch.samples != self.samples:
            raise RuntimeError("device next-event batch used the wrong sample count")
        if batch.sampled_specular_samples != self.sampled_specular_samples:
            raise RuntimeError("device next-event batch used the wrong sampled-specular count")
        if batch.ray_start != self._received_rays:
            raise RuntimeError("device next-event batches are not in contiguous global ray order")
        launch = np.asarray(launch_direction, dtype=np.float64)
        if launch.shape != (batch.rays, 3):
            raise RuntimeError("launch directions do not align with device next-event deposits")
        return launch

    def _grow_order_accumulators(self, order_count: int) -> None:
        grow = order_count - self._raw_by_order.size
        if grow <= 0:
            return
        names = (
            "_raw_by_order",
            "_connections_by_order",
            "_cleared_by_order",
            "_specular_raw_by_order",
            "_specular_candidates_by_order",
            "_specular_geometric_by_order",
            "_specular_visible_by_order",
            "_specular_accepted_by_order",
        )
        for name in names:
            setattr(self, name, np.pad(getattr(self, name), (0, grow)))

    @staticmethod
    def _reduced_order_tail(values: np.ndarray, order_count: int, dtype: Any) -> np.ndarray:
        reduced = values.copy()
        if reduced.shape[0] > order_count:
            reduced[order_count - 1] = np.sum(reduced[order_count - 1 :], dtype=dtype)
        return reduced

    def _accumulate_order_reductions(
        self,
        batch: DeviceNextEventBatch,
        source_order_count: int,
        order_count: int,
    ) -> None:
        raw_by_order = np.sum(batch.weight_by_order, axis=1, dtype=np.float64)
        specular_raw = np.sum(batch.specular_weight_by_order, axis=1, dtype=np.float64)
        reductions = (
            self._reduced_order_tail(raw_by_order, order_count, np.float64),
            self._reduced_order_tail(batch.connections_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.cleared_by_order, order_count, np.uint64),
            self._reduced_order_tail(specular_raw, order_count, np.float64),
            self._reduced_order_tail(batch.specular_candidates_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_geometric_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_visible_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_accepted_by_order, order_count, np.uint64),
        )
        accumulators = (
            self._raw_by_order,
            self._connections_by_order,
            self._cleared_by_order,
            self._specular_raw_by_order,
            self._specular_candidates_by_order,
            self._specular_geometric_by_order,
            self._specular_visible_by_order,
            self._specular_accepted_by_order,
        )
        used_orders = min(source_order_count, order_count)
        for accumulator, reduction in zip(accumulators, reductions, strict=True):
            accumulator[:used_orders] += reduction[:used_orders]

    def _accumulate_field(
        self,
        batch: DeviceNextEventBatch,
        launch: np.ndarray,
        launch_cells: np.ndarray | None,
        source_order_count: int,
    ) -> None:
        cells = self._field_cells(batch, launch, launch_cells)
        tiled_cells = np.tile(cells, source_order_count)
        np.add.at(
            self._raw_field_mass,
            tiled_cells,
            batch.weight_by_order.reshape(-1).astype(np.float64, copy=False),
        )
        np.add.at(
            self._specular_raw_field_mass,
            tiled_cells,
            batch.specular_weight_by_order.reshape(-1).astype(np.float64, copy=False),
        )

    def _field_cells(
        self,
        batch: DeviceNextEventBatch,
        launch: np.ndarray,
        launch_cells: np.ndarray | None,
    ) -> np.ndarray:
        if launch_cells is None:
            return nearest_cell(launch, self._local_grid)
        cells = np.asarray(launch_cells, dtype=np.int64)
        if cells.shape != (batch.rays,) or np.any(cells < 0) or np.any(cells >= self._local_grid.shape[0]):
            raise RuntimeError("launch cells do not align with device next-event deposits")
        return cells

    def end_trace(self) -> None:
        if self._received_rays != self._expected_rays:
            raise RuntimeError(
                f"device next-event trace returned {self._received_rays} rays, expected {self._expected_rays}"
            )

    @property
    def rays(self) -> int:
        return self._received_rays

    @property
    def connections(self) -> int:
        return int(np.sum(self._connections_by_order, dtype=np.uint64))

    @property
    def cleared(self) -> int:
        return int(np.sum(self._cleared_by_order, dtype=np.uint64))

    def chi_by_order(self) -> np.ndarray:
        if self.rays == 0:
            return np.zeros_like(self._raw_by_order)
        return (4.0 * np.pi / (self.rays * self.samples)) * self._raw_by_order

    def bounced_mass(self) -> np.ndarray:
        if not self.collect_field:
            raise RuntimeError("this device next-event gather did not collect an angular field")
        if self.rays == 0:
            return np.zeros_like(self._raw_field_mass)
        return (4.0 * np.pi / (self.rays * self.samples)) * self._raw_field_mass

    def chi_bounce(self) -> float:
        if self.collect_field:
            return float(np.sum(self.bounced_mass(), dtype=np.float64))
        return float(np.sum(self.chi_by_order(), dtype=np.float64))

    @property
    def specular_candidates(self) -> int:
        return int(np.sum(self._specular_candidates_by_order, dtype=np.uint64))

    @property
    def specular_accepted(self) -> int:
        return int(np.sum(self._specular_accepted_by_order, dtype=np.uint64))

    def chi_specular_suffix_by_order(self) -> np.ndarray:
        if self.rays == 0:
            return np.zeros_like(self._specular_raw_by_order)
        return (4.0 * np.pi / (self.rays * self.sampled_specular_samples)) * self._specular_raw_by_order

    def chi_specular_suffix(self) -> float:
        if self.collect_field:
            return float(np.sum(self.specular_bounced_mass(), dtype=np.float64))
        return float(np.sum(self.chi_specular_suffix_by_order(), dtype=np.float64))

    def specular_bounced_mass(self) -> np.ndarray:
        if not self.collect_field:
            raise RuntimeError("this device next-event gather did not collect an angular field")
        if self.rays == 0:
            return np.zeros_like(self._specular_raw_field_mass)
        return (4.0 * np.pi / (self.rays * self.sampled_specular_samples)) * self._specular_raw_field_mass

    def sampled_specular_diagnostics(self) -> dict[str, Any]:
        if self.specular_suffix_order == 0:
            return {"enabled": False}
        trials = self.specular_candidates
        accepted = self.specular_accepted
        return {
            "enabled": self.sampled_specular_ready,
            "samples_per_vertex": self.sampled_specular_samples,
            "seed_offset": self.sampled_specular_seed_offset,
            "counter_start": 0,
            "counter_stop": self._sampled_specular_counter,
            "trials": trials,
            "candidates": trials,
            "geometric": int(np.sum(self._specular_geometric_by_order, dtype=np.uint64)),
            "visible": int(np.sum(self._specular_visible_by_order, dtype=np.uint64)),
            "accepted": accepted,
            "acceptance": accepted / max(trials, 1),
            "chi_specular_suffix": self.chi_specular_suffix(),
            "chi_specular_suffix_by_order": self.chi_specular_suffix_by_order().tolist(),
            "uncertainty_scope": (
                "sampled suffix diagnostics are conditional_on_traced_diffuse_vertices and do not claim a "
                "within-run or total-estimator standard error. Campaign seed replicas control primary-ray, "
                "sampled-face, body, and CDF uncertainty"
            ),
            "sampling_identity": {
                "status": "experimental_opt_in",
                "face_proposal": SPECULAR_FACE_PROPOSAL,
                "source_proposal": SPECULAR_SOURCE_PROPOSAL,
                "counter_generator": SPECULAR_COUNTER_GENERATOR,
                "source_counter_dimension": SPECULAR_SOURCE_COUNTER_DIMENSION,
                "face_counter_dimension": SPECULAR_FACE_COUNTER_DIMENSION,
                "source_count": int(self._probabilities.size),
                "source_support": int(np.count_nonzero(self._probabilities)),
                "source_probability_sha256": _array_sha256(self._probabilities),
                "face_count": int(self._face_probability.size),
                "face_probability_sha256": _array_sha256(self._face_probability),
                "surface_support_complete": self._surface_support_complete,
                "surface_scene_face_count": self._surface_scene_face_count,
                "surface_construction": "all_nondegenerate_mesh_faces",
            },
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "chi_bounce": self.chi_bounce(),
            "chi_by_order": self.chi_by_order().tolist(),
            "connections": self.connections,
            "cleared": self.cleared,
            "clear_fraction": self.cleared / max(self.connections, 1),
            "rays": self.rays,
            "samples": self.samples,
            "max_order": self.max_order,
            "field_collected": self.collect_field,
            "source_sampling": "validated_float32_vose_alias",
            "source_probability_count": int(self._probabilities.size),
            "counter_key": "trace_seed_plus_offset,global_ray_index,bounce_depth,sample_index",
            "direct_atoms": "exact_host_calculation_required_separately",
            "specular_suffix_supported": True,
            "sampled_specular_suffix": self.sampled_specular_diagnostics(),
        }

    def _bind_device(self, mi: Any, dr: Any) -> tuple[Any, ...]:
        key = (str(mi.variant()), id(mi.Float))
        if self._device_arrays is not None and self._device_key == key:
            return self._device_arrays
        sites = self._sites
        arrays = (
            mi.Float(sites[:, 0]),
            mi.Float(sites[:, 1]),
            mi.Float(sites[:, 2]),
            mi.Float(self._alias_threshold),
            mi.UInt32(self._alias_index),
        )
        dr.eval(*arrays)
        self._device_key = key
        self._device_arrays = arrays
        return arrays

    def _bind_specular_device(self, kernel: Any) -> tuple[Any, ...]:
        self._prepare_specular_support(kernel)
        if self._face_probability.size == 0:
            return ()
        mi, dr = kernel.mi, kernel.dr
        key = (str(mi.variant()), id(kernel.geometry))
        if self._specular_device_arrays is not None and self._specular_device_key == key:
            return self._specular_device_arrays
        triangle = self._face_triangles
        normal = self._face_normals
        arrays = (
            mi.Float(triangle[:, 0, 0]),
            mi.Float(triangle[:, 0, 1]),
            mi.Float(triangle[:, 0, 2]),
            mi.Float(triangle[:, 1, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 1, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 1, 2] - triangle[:, 0, 2]),
            mi.Float(triangle[:, 2, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 2, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 2, 2] - triangle[:, 0, 2]),
            mi.Float(normal[:, 0]),
            mi.Float(normal[:, 1]),
            mi.Float(normal[:, 2]),
            mi.UInt32(self._face_index),
            mi.Float(self._face_probability.astype(np.float32)),
            mi.Float(self._face_alias_threshold),
            mi.UInt32(self._face_alias_index),
        )
        dr.eval(*arrays)
        self._specular_device_key = key
        self._specular_device_arrays = arrays
        return arrays

    def _device_state(
        self,
        kernel: Any,
        ray_index: Any,
        ray_count: int,
        trace_seed: int,
    ) -> _DeviceNextEventState:
        return _DeviceNextEventState(self, kernel, ray_index, ray_count, trace_seed)


class _DeviceNextEventState:
    """Per-range device arrays.  Created and consumed by DeviceSbrKernel."""

    def __init__(
        self,
        gather: DeviceNextEventGather,
        kernel: Any,
        ray_index: Any,
        ray_count: int,
        trace_seed: int,
    ) -> None:
        self.gather = gather
        self.kernel = kernel
        self.mi = kernel.mi
        self.dr = kernel.dr
        self.ray_index = ray_index
        self.ray_count = int(ray_count)
        self.seed_value = (int(trace_seed) + int(gather.seed_offset)) & 0xFFFFFFFFFFFFFFFF
        self.site_x, self.site_y, self.site_z, self.alias_threshold, self.alias_index = gather._bind_device(
            self.mi, self.dr
        )
        self.weight_by_order: list[Any] = [self.dr.zeros(self.mi.Float, self.ray_count)]
        self.connections_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.cleared_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_weight_by_order: list[Any] = [self.dr.zeros(self.mi.Float, self.ray_count)]
        self.specular_candidates_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_geometric_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_visible_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_accepted_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_seed = (int(trace_seed) + int(gather.sampled_specular_seed_offset)) & _MASK_64
        self.specular_arrays = gather._bind_specular_device(kernel)
        self.loop_errors: list[Any] = []

    def _sample_source(self, uniform: Any, active: Any) -> tuple[Any, Any]:
        mi, dr = self.mi, self.dr
        count = int(self.gather._sites.shape[0])
        scaled = uniform * float(count)
        column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
        fraction = scaled - mi.Float(column)
        threshold = dr.gather(mi.Float, self.alias_threshold, column, active)
        alternate = dr.gather(mi.UInt32, self.alias_index, column, active)
        index = dr.select(fraction < threshold, column, alternate)
        target = mi.Point3f(
            dr.gather(mi.Float, self.site_x, index, active),
            dr.gather(mi.Float, self.site_y, index, active),
            dr.gather(mi.Float, self.site_z, index, active),
        )
        return index, target

    def _sample_specular_face(self, uniform: Any, active: Any) -> tuple[Any, ...]:
        mi, dr = self.mi, self.dr
        if not self.specular_arrays:
            raise RuntimeError("sampled specular face support is empty")
        (
            p0x,
            p0y,
            p0z,
            e1x,
            e1y,
            e1z,
            e2x,
            e2y,
            e2z,
            nx,
            ny,
            nz,
            face_index,
            probability,
            threshold,
            alias,
        ) = self.specular_arrays
        count = int(self.gather._face_probability.size)
        scaled = uniform * float(count)
        column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
        fraction = scaled - mi.Float(column)
        cut = dr.gather(mi.Float, threshold, column, active)
        alternate = dr.gather(mi.UInt32, alias, column, active)
        surface = dr.select(fraction < cut, column, alternate)

        def scalar(array: Any) -> Any:
            return dr.gather(mi.Float, array, surface, active)

        plane = mi.Point3f(scalar(p0x), scalar(p0y), scalar(p0z))
        edge1 = mi.Vector3f(scalar(e1x), scalar(e1y), scalar(e1z))
        edge2 = mi.Vector3f(scalar(e2x), scalar(e2y), scalar(e2z))
        normal = mi.Vector3f(scalar(nx), scalar(ny), scalar(nz))
        actual_face = dr.gather(mi.UInt32, face_index, surface, active)
        q = dr.gather(mi.Float, probability, surface, active)
        return surface, plane, edge1, edge2, normal, actual_face, q

    def _ensure_specular_order(self, order: int) -> None:
        while len(self.specular_weight_by_order) <= order:
            self.specular_weight_by_order.append(self.dr.zeros(self.mi.Float, self.ray_count))
            self.specular_candidates_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_geometric_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_visible_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_accepted_by_order.append(self.dr.zeros(self.mi.UInt32, 1))

    def vertex(
        self,
        depth: int,
        position: Any,
        normal: Any,
        throughput: Any,
        share: Any,
        active: Any,
        random_draw: Any,
    ) -> None:
        """Add one fixed-width order row after material response."""
        mi, dr = self.mi, self.dr
        total_weight = dr.zeros(mi.Float, self.ray_count)
        total_connections = dr.zeros(mi.UInt32, 1)
        total_cleared = dr.zeros(mi.UInt32, 1)
        lobe = throughput * (1.0 - share) / np.pi
        for sample in range(self.gather.samples):
            _source_index, target = self._sample_source(random_draw(sample), active)
            delta = target - position
            distance = dr.norm(delta)
            direction = delta / dr.maximum(distance, 1.0e-12)
            cosine = dr.dot(direction, normal)
            worth = active & (cosine > 0.0) & (distance > float(self.gather.min_connect_m)) & (lobe > 0.0)
            total_connections += dr.sum(mi.UInt32(worth))
            lifted = position + float(self.gather.lift_m) * normal
            shadow_delta = target - lifted
            shadow_distance = dr.norm(shadow_delta)
            shadow_direction = shadow_delta / dr.maximum(shadow_distance, 1.0e-12)
            start = lifted + float(self.gather.epsilon_m) * shadow_direction
            clear, loop_error = self._visible(
                start,
                shadow_direction,
                shadow_distance,
                worth,
                depth,
            )
            self.loop_errors.append(dr.sum(mi.UInt32(loop_error)))
            total_cleared += dr.sum(mi.UInt32(clear))
            weight = lobe * cosine / dr.maximum(distance * distance, 1.0e-24)
            total_weight += dr.select(clear, weight, 0.0)
        self._sampled_specular_vertex(depth, position, normal, lobe, active)
        self.weight_by_order.append(total_weight)
        self.connections_by_order.append(total_connections)
        self.cleared_by_order.append(total_cleared)
        dr.eval(total_weight, total_connections, total_cleared)

    def _sampled_specular_vertex(
        self,
        depth: int,
        position: Any,
        vertex_normal: Any,
        diffuse_lobe: Any,
        active: Any,
    ) -> None:
        """Sample one complete-support source/finite-face suffix per trial."""
        if self.gather.specular_suffix_order == 0 or not self.specular_arrays:
            return
        total_order = depth + 2
        maximum_order = (
            int(self.kernel.config.max_bounces) if self.gather.max_order is None else int(self.gather.max_order)
        )
        if total_order > maximum_order:
            return
        mi, dr = self.mi, self.dr
        eligible = active & (diffuse_lobe > 0.0)
        endpoint_count = dr.sum(mi.UInt64(eligible))
        sample_count = int(self.gather.sampled_specular_samples)
        total_weight = dr.zeros(mi.Float, self.ray_count)
        geometric_total = dr.zeros(mi.UInt32, 1)
        visible_total = dr.zeros(mi.UInt32, 1)
        accepted_total = dr.zeros(mi.UInt32, 1)
        for sample in range(sample_count):
            counter = (
                mi.UInt64(depth) * mi.UInt64(int(self.kernel.config.rays)) + mi.UInt64(self.ray_index)
            ) * mi.UInt64(sample_count) + mi.UInt64(sample)
            source_uniform = _splitmix_uniform(
                mi,
                counter,
                self.specular_seed,
                SPECULAR_SOURCE_COUNTER_DIMENSION,
            )
            face_uniform = _splitmix_uniform(
                mi,
                counter,
                self.specular_seed,
                SPECULAR_FACE_COUNTER_DIMENSION,
            )
            _source_index, source = self._sample_source(source_uniform, eligible)
            (
                _surface,
                plane,
                edge1,
                edge2,
                surface_normal,
                expected_face,
                face_probability,
            ) = self._sample_specular_face(face_uniform, eligible)
            source_side = dr.dot(source - plane, surface_normal)
            receiver_side = dr.dot(position - plane, surface_normal)
            image = source - 2.0 * source_side * surface_normal
            image_line = image - position
            denominator = dr.dot(image_line, surface_normal)
            fraction = -receiver_side / dr.select(dr.abs(denominator) > 1.0e-30, denominator, 1.0)
            reflection = position + fraction * image_line
            offset = reflection - plane
            d11 = dr.dot(edge1, edge1)
            d12 = dr.dot(edge1, edge2)
            d22 = dr.dot(edge2, edge2)
            q1 = dr.dot(offset, edge1)
            q2 = dr.dot(offset, edge2)
            determinant = d11 * d22 - d12 * d12
            safe_determinant = dr.select(determinant > 1.0e-24, determinant, 1.0)
            bary_u = (d22 * q1 - d12 * q2) / safe_determinant
            bary_v = (d11 * q2 - d12 * q1) / safe_determinant
            tolerance = 2.0e-8
            inside = (
                (determinant > 1.0e-24)
                & (bary_u >= -tolerance)
                & (bary_v >= -tolerance)
                & (bary_u + bary_v <= 1.0 + tolerance)
            )
            distinct = dr.squared_norm(source - position) > 1.0e-24
            geometric = (
                eligible
                & distinct
                & (source_side * receiver_side > float(self.gather.epsilon_m) ** 2)
                & dr.isfinite(fraction)
                & (fraction > 0.0)
                & (fraction < 1.0)
                & inside
            )
            geometric_total += dr.sum(mi.UInt32(geometric))

            source_leg = reflection - source
            source_range = dr.norm(source_leg)
            source_direction = source_leg / dr.maximum(source_range, 1.0e-12)
            source_clear, source_loop_error = self._visible(
                source + float(self.gather.epsilon_m) * source_direction,
                source_direction,
                source_range,
                geometric,
                depth,
                expected_face=expected_face,
            )
            receiver_leg = position - reflection
            receiver_range = dr.norm(receiver_leg)
            arrival = receiver_leg / dr.maximum(receiver_range, 1.0e-12)
            receiver_clear, receiver_loop_error = self._visible(
                reflection + float(self.gather.epsilon_m) * arrival,
                arrival,
                receiver_range,
                source_clear,
                depth,
            )
            self.loop_errors.extend(
                (
                    dr.sum(mi.UInt32(source_loop_error)),
                    dr.sum(mi.UInt32(receiver_loop_error)),
                )
            )
            visible = source_clear & receiver_clear
            visible_total += dr.sum(mi.UInt32(visible))

            source_cosine = dr.clip(dr.abs(dr.dot(source_direction, surface_normal)), 0.0, 1.0)
            fallback_material = dr.gather(mi.UInt32, self.kernel._face_class_device, expected_face, visible)
            reflectance, coherent_share, nonblocking = self.kernel._surface_response_at(
                source_cosine,
                fallback_material,
                expected_face,
                mi.Point2f(bary_u, bary_v),
                visible,
            )
            toward_reflection = -arrival
            diffuse_cosine = dr.dot(toward_reflection, vertex_normal)
            path_length = source_range + receiver_range
            contribution = (
                diffuse_lobe
                * dr.maximum(diffuse_cosine, 0.0)
                * reflectance
                * coherent_share
                / dr.maximum(path_length * path_length * face_probability, 1.0e-24)
            )
            accepted = (
                visible & ~nonblocking & (diffuse_cosine > 0.0) & (contribution > 0.0) & dr.isfinite(contribution)
            )
            accepted_total += dr.sum(mi.UInt32(accepted))
            total_weight += dr.select(accepted, contribution, 0.0)

        self._ensure_specular_order(total_order)
        self.specular_weight_by_order[total_order] += total_weight
        self.specular_candidates_by_order[total_order] += mi.UInt32(endpoint_count * mi.UInt64(sample_count))
        self.specular_geometric_by_order[total_order] += geometric_total
        self.specular_visible_by_order[total_order] += visible_total
        self.specular_accepted_by_order[total_order] += accepted_total
        dr.eval(
            total_weight,
            self.specular_candidates_by_order[total_order],
            geometric_total,
            visible_total,
            accepted_total,
        )

    def _visible(
        self,
        start: Any,
        direction: Any,
        target_distance: Any,
        active: Any,
        depth: int,
        *,
        expected_face: Any | None = None,
    ) -> tuple[Any, Any]:
        """Cast one leg, passing through atlas cells marked non-blocking.

        A source-to-reflector leg supplies ``expected_face`` and succeeds only
        when that exact finite face is reached.  A reflector-to-endpoint or
        direct diffuse leg omits it and succeeds on a miss or after reaching
        the endpoint range.
        """
        mi, dr = self.mi, self.dr
        searching = active
        query = start
        travelled = dr.zeros(mi.Float, self.ray_count)
        crossings = dr.zeros(mi.UInt32, self.ray_count)
        clear = dr.zeros(mi.Bool, self.ray_count)
        limit = int(self.kernel.face_class.size)

        def cond(searching: Any, query: Any, travelled: Any, crossings: Any, clear: Any) -> Any:
            del query, travelled, clear
            return searching & (crossings <= limit)

        def step(
            searching: Any,
            query: Any,
            travelled: Any,
            crossings: Any,
            clear: Any,
        ) -> tuple[Any, ...]:
            intersection = self.kernel.geometry.intersect_device(query, direction, searching)
            at_target = travelled + intersection.distance >= target_distance - 2.0 * float(self.gather.epsilon_m)
            if expected_face is None:
                reached = searching & (~intersection.hit | at_target)
            else:
                reached = searching & intersection.hit & at_target & (intersection.face == expected_face)
            clear |= reached
            before = searching & intersection.hit & ~at_target
            nonblocking = self.kernel._surface_nonblocking(intersection, before)
            pass_through = before & nonblocking
            crossings = dr.select(pass_through, crossings + 1, crossings)
            travelled = dr.select(
                pass_through,
                travelled + intersection.distance + float(self.gather.epsilon_m),
                travelled,
            )
            query = dr.select(
                pass_through,
                query + (intersection.distance + float(self.gather.epsilon_m)) * direction,
                query,
            )
            searching = pass_through
            return searching, query, travelled, crossings, clear

        searching, _query, _travelled, _crossings, clear = dr.while_loop(
            state=(searching, query, travelled, crossings, clear),
            cond=cond,
            body=step,
            mode="symbolic" if str(getattr(self.kernel.geometry, "variant", "")).startswith("cuda") else "evaluated",
            label=f"next-event non-blocking shadow at bounce {depth}",
        )
        return clear, searching

    def transfer(self, ray_start: int) -> DeviceNextEventBatch:
        """Copy all order rows in one packed device-to-host transfer."""
        mi, dr = self.mi, self.dr
        orders = max(len(self.weight_by_order), len(self.specular_weight_by_order))
        while len(self.weight_by_order) < orders:
            self.weight_by_order.append(dr.zeros(mi.Float, self.ray_count))
            self.connections_by_order.append(dr.zeros(mi.UInt32, 1))
            self.cleared_by_order.append(dr.zeros(mi.UInt32, 1))
        self._ensure_specular_order(orders - 1)
        packed_parts: list[Any] = []
        loop_errors = dr.zeros(mi.UInt32, 1)
        for value in self.loop_errors:
            loop_errors += value
        packed_parts.append(dr.reinterpret_array(mi.Float, loop_errors))
        for value in self.connections_by_order:
            packed_parts.append(dr.reinterpret_array(mi.Float, value))
        for value in self.cleared_by_order:
            packed_parts.append(dr.reinterpret_array(mi.Float, value))
        for values in (
            self.specular_candidates_by_order,
            self.specular_geometric_by_order,
            self.specular_visible_by_order,
            self.specular_accepted_by_order,
        ):
            for value in values:
                packed_parts.append(dr.reinterpret_array(mi.Float, value))
        packed_parts.extend(self.weight_by_order)
        packed_parts.extend(self.specular_weight_by_order)
        transferred = np.asarray(dr.concat(packed_parts)).copy()
        header = 1 + 6 * orders
        if transferred.size != header + 2 * orders * self.ray_count:
            raise RuntimeError("device next-event record packing is inconsistent")
        counts = transferred[1:header].view(np.uint32).astype(np.uint64)
        if transferred[:1].view(np.uint32)[0]:
            raise RuntimeError(
                "device next-event shadow ray exceeded the support-mesh face count while crossing "
                "non-blocking atlas cells"
            )
        weight = transferred[header:].reshape(2, orders, self.ray_count)
        return DeviceNextEventBatch(
            weight_by_order=weight[0],
            connections_by_order=counts[:orders],
            cleared_by_order=counts[orders : 2 * orders],
            ray_start=ray_start,
            rays=self.ray_count,
            samples=self.gather.samples,
            specular_weight_by_order=weight[1],
            specular_candidates_by_order=counts[2 * orders : 3 * orders],
            specular_geometric_by_order=counts[3 * orders : 4 * orders],
            specular_visible_by_order=counts[4 * orders : 5 * orders],
            specular_accepted_by_order=counts[5 * orders : 6 * orders],
            sampled_specular_samples=self.gather.sampled_specular_samples,
        )


def device_source_sample(
    gather: DeviceNextEventGather,
    uniform: np.ndarray,
    *,
    variant: str = "llvm_ad_rgb",
) -> np.ndarray:
    """Exercise the exact resident alias sampler for a validation experiment."""
    import drjit as dr
    import mitsuba as mi

    if mi.variant() != variant:
        mi.set_variant(variant)
    values = np.asarray(uniform, dtype=np.float32)
    if values.ndim != 1 or np.any(values < 0.0) or np.any(values >= 1.0):
        raise ValueError("uniform values must be a one-dimensional array in [0, 1)")
    site_x, site_y, site_z, threshold, alias = gather._bind_device(mi, dr)
    del site_x, site_y, site_z
    draw = mi.Float(values)
    count = gather._sites.shape[0]
    scaled = draw * float(count)
    column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
    fraction = scaled - mi.Float(column)
    cut = dr.gather(mi.Float, threshold, column)
    alternate = dr.gather(mi.UInt32, alias, column)
    return np.asarray(dr.select(fraction < cut, column, alternate), dtype=np.uint32)


def device_specular_face_sample(
    gather: DeviceNextEventGather,
    kernel: Any,
    uniform: np.ndarray,
) -> np.ndarray:
    """Exercise the exact resident face alias table for validation."""
    mi, dr = kernel.mi, kernel.dr
    arrays = gather._bind_specular_device(kernel)
    if not arrays:
        return np.empty(0, dtype=np.uint32)
    values = np.asarray(uniform, dtype=np.float32)
    if values.ndim != 1 or np.any(values < 0.0) or np.any(values >= 1.0):
        raise ValueError("uniform values must be a one-dimensional array in [0, 1)")
    probability = arrays[13]
    threshold = arrays[14]
    alias = arrays[15]
    del probability
    draw = mi.Float(values)
    count = gather._face_probability.size
    scaled = draw * float(count)
    column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
    fraction = scaled - mi.Float(column)
    cut = dr.gather(mi.Float, threshold, column)
    alternate = dr.gather(mi.UInt32, alias, column)
    return np.asarray(dr.select(fraction < cut, column, alternate), dtype=np.uint32)

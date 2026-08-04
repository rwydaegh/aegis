"""Host reduction adapter for the Dr.Jit-resident escape kernel.

The device kernel owns ray transport. This adapter owns the same host-side
scoring and :class:`~semantic_twin.transport.tracer.PointResult` construction
as :class:`~semantic_twin.transport.tracer.SbrTracer`. It is intentionally not
wired into study execution until the CUDA path has passed the full parity and
performance gate.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..illumination import IlluminationModel, fibonacci_sphere, nearest_cell
from .device_kernel import DeviceEscapeRecords, DeviceSbrKernel
from .model import require_credit
from .trace_kernel import EscapeDeposit, TraceAccumulators, deposit, range_to_source_shell
from .tracer import PointResult, TraceConfig, finalize_point_result


class DeviceEscapeTracer:
    """Score escape records produced by :class:`DeviceSbrKernel`.

    The public trace shape follows :class:`SbrTracer`, but callbacks are
    refused because the resident kernel does not yet transfer surface vertices.
    Each batch receives its global ``ray_start``. Counter-based device draws are
    therefore tied to a ray, rather than to the chosen transfer batch size.
    """

    def __init__(
        self,
        geometry: Any,
        face_class: np.ndarray | None,
        permittivity: np.ndarray,
        rms_height_m: np.ndarray,
        config: TraceConfig,
    ) -> None:
        self.geometry = geometry
        self.face_class = face_class
        self.permittivity = np.asarray(permittivity, dtype=np.complex128)
        self.rms_height_m = np.asarray(rms_height_m, dtype=np.float64)
        self.config = config
        self.local_grid = fibonacci_sphere(config.local_cells)
        self.exit_sin_edges = np.linspace(-1.0, 1.0, config.exit_bands + 1)
        vertices = getattr(geometry, "vertices", None)
        self.source_shell_radius_m = (
            float(np.linalg.norm(np.asarray(vertices, dtype=np.float64), axis=1).max())
            if vertices is not None and len(vertices)
            else 250.0
        )
        self.kernel = DeviceSbrKernel(
            geometry,
            face_class,
            self.permittivity,
            self.rms_height_m,
            config,
        )

    def trace(
        self,
        origin: np.ndarray,
        models: dict[str, IlluminationModel],
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
        recorder: Any = None,
        tally: Any = None,
        gather: Any = None,
        observers: Any = None,
        next_event: Any = None,
    ) -> PointResult:
        """Trace and score one point with the escape estimator."""
        attached = [
            name
            for name, value in (
                ("recorder", recorder),
                ("tally", tally),
                ("gather", gather),
                ("observers", observers),
                ("next_event", next_event),
            )
            if value is not None
        ]
        if attached:
            raise NotImplementedError(
                "device escape tracing does not yet support recorders, observers, or next-event estimation: "
                + ", ".join(attached)
            )
        for model in models.values():
            require_credit("escape", model)

        cfg = self.config
        if cfg.batch < 1:
            raise ValueError("batch must be positive")
        started = time.perf_counter()
        accumulators = TraceAccumulators.create(models, cfg.local_cells, cfg.exit_bands)
        truncated_terms: list[np.ndarray] = []
        delay_weight_terms: list[np.ndarray] = []
        delay_sum_terms: list[np.ndarray] = []
        bounce_sums: list[int] = []
        ray_start = 0
        used_seed = cfg.seed if seed is None else seed
        while ray_start < cfg.rays:
            count = min(cfg.batch, cfg.rays - ray_start)
            part = self.kernel.trace_escape_records(
                origin,
                rays=count,
                ray_start=ray_start,
                seed=used_seed,
            )
            delay_weight, delay_sum, bounce_sum = self._score_records(
                origin,
                models,
                accumulators,
                part,
                ray_start,
                count,
            )
            truncated_terms.append(part.truncated_throughput_terms)
            delay_weight_terms.append(delay_weight)
            delay_sum_terms.append(delay_sum)
            bounce_sums.append(bounce_sum)
            ray_start += count

        accumulators.totals["delay_weight"] = _ordered_sum(delay_weight_terms)
        accumulators.totals["delay_sum"] = _ordered_sum(delay_sum_terms)
        accumulators.totals["bounce_sum"] = sum(bounce_sums)
        accumulators.totals["truncated_throughput"] = math.fsum(
            float(value) for terms in truncated_terms for value in terms
        )
        return finalize_point_result(
            origin,
            ground_z_m,
            models,
            cfg,
            self.local_grid,
            self.exit_sin_edges,
            accumulators,
            started,
        )

    def _score_records(
        self,
        origin: np.ndarray,
        models: dict[str, IlluminationModel],
        accumulators: TraceAccumulators,
        records: DeviceEscapeRecords,
        expected_start: int,
        expected_rays: int,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        """Add one ordered device range to the host accumulators."""
        if records.ray_start != expected_start or records.rays != expected_rays:
            raise RuntimeError(
                "device kernel returned the wrong ray range: "
                f"({records.ray_start}, {records.rays}) != ({expected_start}, {expected_rays})"
            )
        if records.all_launch_direction.shape != (records.rays, 3):
            raise RuntimeError("device kernel returned an invalid launch-direction array")
        local_rows = records.ray_index.astype(np.int64) - records.ray_start
        if np.any(local_rows < 0) or np.any(local_rows >= records.rays):
            raise RuntimeError("device kernel returned an escaped ray outside its ray range")

        all_cells = nearest_cell(records.all_launch_direction, self.local_grid)
        np.add.at(accumulators.cell_counts, all_cells, 1.0)
        if records.escaped:
            origin_array = np.asarray(origin, dtype=np.float64)
            deposit(
                self,
                EscapeDeposit(
                    index=records.ray_index,
                    direction=records.exit_direction,
                    throughput=records.throughput,
                    cell=all_cells[local_rows],
                    path_length=records.path_length,
                    last_vertex=records.last_vertex,
                    origin=origin_array,
                    bounces=records.bounces,
                ),
                models,
                accumulators,
            )
            excess = records.path_length - np.einsum(
                "ij,ij->i",
                records.exit_direction,
                records.last_vertex - origin_array,
            )
            delay_weight = records.throughput
            delay_sum = records.throughput * excess
            bounce_sum = int(records.bounces.sum(dtype=np.uint64))
        else:
            delay_weight = np.empty(0, dtype=np.float32)
            delay_sum = np.empty(0, dtype=np.float64)
            bounce_sum = 0
        accumulators.totals["truncated"] += records.truncated
        return delay_weight, delay_sum, bounce_sum

    def _range_to_the_source_shell(
        self,
        last_vertex: np.ndarray,
        exit_direction: np.ndarray,
        path_length: np.ndarray,
    ) -> np.ndarray:
        return range_to_source_shell(
            last_vertex,
            exit_direction,
            path_length,
            self.source_shell_radius_m,
            self.config.ray_epsilon_m,
        )


def _ordered_sum(parts: list[np.ndarray]) -> float:
    """Reduce per-ray terms once, independent of their transfer batches."""
    if not parts:
        return 0.0
    values = parts[0] if len(parts) == 1 else np.concatenate(parts)
    return float(np.sum(values))

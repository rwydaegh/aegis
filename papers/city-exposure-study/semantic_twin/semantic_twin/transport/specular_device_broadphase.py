"""Resident Dr.Jit broad phase for finite order-one reflections."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

_ROUND_OFF_MULTIPLIER = 1024.0


class DeviceBroadPhaseUnavailable(RuntimeError):
    """A device optimization could not run, so the NumPy screen must be used."""


@dataclass(frozen=True)
class DeviceOrderOneBroadPhase:
    """Source-major Cartesian indices retained by one device screen."""

    flat_index: np.ndarray
    logical_candidates: int
    survivors: int
    source_chunks: int
    seconds: float
    variant: str

    def __post_init__(self) -> None:
        flat = np.asarray(self.flat_index, dtype=np.int64)
        if flat.ndim != 1:
            raise ValueError("device broad-phase indices must be one-dimensional")
        if np.any(flat < 0) or np.any(flat >= self.logical_candidates):
            raise ValueError("device broad-phase index lies outside the Cartesian product")
        if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
            raise ValueError("device broad-phase indices must be strictly increasing")
        if self.survivors != flat.size or not (0 <= self.survivors <= self.logical_candidates):
            raise ValueError("device broad-phase survivor count must match its indices")
        if self.source_chunks < 0 or not np.isfinite(self.seconds) or self.seconds < 0.0:
            raise ValueError("device broad-phase work diagnostics must be nonnegative")
        if not self.variant:
            raise ValueError("device broad-phase variant must be named")
        object.__setattr__(self, "flat_index", flat)

    def as_dict(self) -> dict[str, int | float | str]:
        fraction = self.survivors / self.logical_candidates if self.logical_candidates else 0.0
        return {
            "method": "cuda_float64_conservative_mirrored_receiver_triangle_cones",
            "backend": self.variant,
            "logical_candidates": self.logical_candidates,
            "survivors": self.survivors,
            "survivor_fraction": fraction,
            "source_chunks": self.source_chunks,
            "seconds": self.seconds,
            "ambiguity_policy": "retain_nonfinite_and_roundoff_boundary_lanes",
        }


@dataclass(frozen=True)
class BoundDeviceOrderOneBroadPhase:
    """Immutable face geometry uploaded once for one transport instance."""

    kernel: Any
    variant: str
    face_count: int
    device_arrays: tuple[Any, ...]

    @classmethod
    def bind(
        cls,
        triangles: np.ndarray,
        normals: np.ndarray,
        kernel: Any,
    ) -> BoundDeviceOrderOneBroadPhase:
        triangle = np.asarray(triangles, dtype=np.float64)
        normal = np.asarray(normals, dtype=np.float64)
        if triangle.ndim != 3 or triangle.shape[1:] != (3, 3):
            raise ValueError("triangles must have shape (faces, 3, 3)")
        if normal.shape != (triangle.shape[0], 3):
            raise ValueError("normals must match triangles")
        if np.any(~np.isfinite(triangle)) or np.any(~np.isfinite(normal)):
            raise ValueError("device broad-phase surfaces must be finite")
        try:
            mi, dr = kernel.mi, kernel.dr
            variant = str(mi.variant())
            arrays = tuple(
                mi.Float64(np.ascontiguousarray(values))
                for values in (
                    triangle[:, 0, 0],
                    triangle[:, 0, 1],
                    triangle[:, 0, 2],
                    triangle[:, 1, 0],
                    triangle[:, 1, 1],
                    triangle[:, 1, 2],
                    triangle[:, 2, 0],
                    triangle[:, 2, 1],
                    triangle[:, 2, 2],
                    normal[:, 0],
                    normal[:, 1],
                    normal[:, 2],
                )
            )
            dr.eval(*arrays)
        except (ImportError, RuntimeError) as error:
            raise DeviceBroadPhaseUnavailable(str(error)) from error
        return cls(kernel, variant, triangle.shape[0], arrays)

    def candidates(
        self,
        sources: np.ndarray,
        receiver: np.ndarray,
        surface_index: np.ndarray,
        *,
        epsilon_m: float,
        source_chunk: int,
        inside_tolerance: float,
    ) -> DeviceOrderOneBroadPhase:
        """Return a conservative subset for the unchanged exact host kernel."""
        started = time.perf_counter()
        source = np.asarray(sources, dtype=np.float64)
        receiver = np.asarray(receiver, dtype=np.float64)
        raw_surface = np.asarray(surface_index)
        if source.ndim != 2 or source.shape[1] != 3:
            raise ValueError("sources must have shape (sources, 3)")
        if receiver.shape != (3,):
            raise ValueError("receiver must be one three-vector")
        if np.any(~np.isfinite(source)) or np.any(~np.isfinite(receiver)):
            raise ValueError("device broad-phase endpoints must be finite")
        if raw_surface.ndim != 1 or not np.issubdtype(raw_surface.dtype, np.integer):
            raise ValueError("surface_index must be a one-dimensional integer array")
        surface = raw_surface.astype(np.int64, copy=False)
        if np.any(surface < 0) or np.any(surface >= self.face_count):
            raise ValueError("surface_index contains an unknown face")
        if epsilon_m < 0.0:
            raise ValueError("epsilon_m must be nonnegative")
        if inside_tolerance < 0.0 or not np.isfinite(inside_tolerance):
            raise ValueError("inside_tolerance must be finite and nonnegative")
        if source_chunk < 1:
            raise ValueError("source_chunk must be positive")

        source_count = source.shape[0]
        selected_count = surface.size
        logical = source_count * selected_count
        if logical == 0:
            return DeviceOrderOneBroadPhase(
                np.empty(0, dtype=np.int64),
                logical,
                0,
                0,
                time.perf_counter() - started,
                self.variant,
            )
        uint32_max = int(np.iinfo(np.uint32).max)
        if self.face_count > uint32_max or selected_count > uint32_max:
            raise DeviceBroadPhaseUnavailable("device broad-phase face dimensions must fit in uint32")
        effective_source_chunk = min(source_chunk, max(1, uint32_max // selected_count))

        try:
            flat_parts = self._candidate_chunks(
                source,
                receiver,
                surface,
                epsilon_m=epsilon_m,
                source_chunk=effective_source_chunk,
                inside_tolerance=inside_tolerance,
            )
        except (ImportError, RuntimeError) as error:
            raise DeviceBroadPhaseUnavailable(str(error)) from error
        flat = np.concatenate(flat_parts) if flat_parts else np.empty(0, dtype=np.int64)
        return DeviceOrderOneBroadPhase(
            flat,
            logical,
            flat.size,
            math.ceil(source_count / effective_source_chunk),
            time.perf_counter() - started,
            self.variant,
        )

    def _candidate_chunks(
        self,
        source: np.ndarray,
        receiver: np.ndarray,
        surface: np.ndarray,
        *,
        epsilon_m: float,
        source_chunk: int,
        inside_tolerance: float,
    ) -> list[np.ndarray]:
        mi, dr = self.kernel.mi, self.kernel.dr
        selected_count = surface.size
        selected_device = mi.UInt32(np.ascontiguousarray(surface, dtype=np.uint32))
        dr.eval(selected_device)
        arrays = self.device_arrays
        tiny64 = float(np.finfo(np.float64).tiny)
        roundoff = float(np.finfo(np.float64).eps * _ROUND_OFF_MULTIPLIER)
        receiver_norm = float(np.linalg.norm(receiver))
        flat_parts: list[np.ndarray] = []

        for first_source in range(0, source.shape[0], source_chunk):
            last_source = min(first_source + source_chunk, source.shape[0])
            block = source[first_source:last_source]
            width = block.shape[0] * selected_count
            lane = dr.arange(mi.UInt32, width)
            source_slot = lane // selected_count
            selected_slot = lane % selected_count
            face = dr.gather(mi.UInt32, selected_device, selected_slot)
            sx = dr.gather(mi.Float64, mi.Float64(np.ascontiguousarray(block[:, 0])), source_slot)
            sy = dr.gather(mi.Float64, mi.Float64(np.ascontiguousarray(block[:, 1])), source_slot)
            sz = dr.gather(mi.Float64, mi.Float64(np.ascontiguousarray(block[:, 2])), source_slot)
            p0 = tuple(dr.gather(mi.Float64, arrays[index], face) for index in range(3))
            p1 = tuple(dr.gather(mi.Float64, arrays[index], face) for index in range(3, 6))
            p2 = tuple(dr.gather(mi.Float64, arrays[index], face) for index in range(6, 9))
            normal = tuple(dr.gather(mi.Float64, arrays[index], face) for index in range(9, 12))
            source_point = (sx, sy, sz)
            receiver_point = tuple(mi.Float64(value) for value in receiver)

            receiver_side = _dot(_sub(receiver_point, p0), normal)
            source_side = _dot(_sub(source_point, p0), normal)
            normal_norm = _norm(normal, dr)
            plane_norm = _norm(p0, dr)
            source_norm = _norm(source_point, dr)
            receiver_error = roundoff * (receiver_norm + plane_norm) * normal_norm
            source_error = roundoff * (source_norm + plane_norm) * normal_norm
            product = source_side * receiver_side
            product_padding = (
                dr.abs(receiver_side) * source_error
                + dr.abs(source_side) * receiver_error
                + source_error * receiver_error
            )
            same_side_finite = dr.isfinite(product) & dr.isfinite(product_padding)
            keep = (~same_side_finite) | (product > epsilon_m * epsilon_m - product_padding)

            apex = _sub(receiver_point, _scale(normal, 2.0 * receiver_side))
            receiver_safe = dr.maximum(dr.abs(receiver_side), tiny64)
            projective_scale = 1.0 + dr.abs(source_side) / receiver_safe
            for first, second, opposite in ((p0, p1, p2), (p1, p2, p0), (p2, p0, p1)):
                raw = _cross(_sub(first, apex), _sub(second, apex))
                reference = _dot(_sub(opposite, apex), raw)
                orientation = dr.select(reference < 0.0, -1.0, 1.0)
                oriented = _scale(raw, orientation)
                absolute_reference = dr.abs(reference)
                offset = _dot(apex, oriented)
                cone_norm = _norm(oriented, dr)
                opposite_norm = _norm(_sub(opposite, apex), dr)
                valid_scale = _norm(raw, dr) * dr.maximum(opposite_norm, 1.0)
                cone_valid = absolute_reference > roundoff * valid_scale
                value = _dot(source_point, oriented) - offset
                tolerance = inside_tolerance * absolute_reference * projective_scale
                magnitude = source_norm * cone_norm + dr.abs(offset) + absolute_reference * projective_scale
                padding = roundoff * magnitude
                finite = (
                    dr.isfinite(value)
                    & dr.isfinite(tolerance)
                    & dr.isfinite(padding)
                    & dr.isfinite(reference)
                    & dr.isfinite(valid_scale)
                    & dr.isfinite(projective_scale)
                )
                inside = (~finite) | (~cone_valid) | (value >= -(tolerance + padding))
                keep &= inside

            local = np.asarray(dr.compress(keep), dtype=np.int64)
            flat_parts.append(first_source * selected_count + local)
        return flat_parts


def bind_cuda_order_one_broad_phase(
    triangles: np.ndarray,
    normals: np.ndarray,
    tracer: Any,
) -> BoundDeviceOrderOneBroadPhase | None:
    """Bind resident faces only when the transport already owns a CUDA kernel."""
    kernel = getattr(tracer, "kernel", None)
    if kernel is None:
        return None
    variant = str(getattr(getattr(kernel, "mi", None), "variant", lambda: "")())
    if not variant.startswith("cuda"):
        return None
    try:
        return BoundDeviceOrderOneBroadPhase.bind(triangles, normals, kernel)
    except DeviceBroadPhaseUnavailable:
        return None


def _sub(left: tuple[Any, Any, Any], right: tuple[Any, Any, Any]) -> tuple[Any, Any, Any]:
    return tuple(a - b for a, b in zip(left, right, strict=True))


def _scale(vector: tuple[Any, Any, Any], factor: Any) -> tuple[Any, Any, Any]:
    return tuple(component * factor for component in vector)


def _dot(left: tuple[Any, Any, Any], right: tuple[Any, Any, Any]) -> Any:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _cross(left: tuple[Any, Any, Any], right: tuple[Any, Any, Any]) -> tuple[Any, Any, Any]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm(vector: tuple[Any, Any, Any], dr: Any) -> Any:
    return dr.sqrt(_dot(vector, vector))

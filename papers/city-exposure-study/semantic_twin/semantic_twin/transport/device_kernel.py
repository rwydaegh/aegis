"""Dr.Jit-resident escape SBR prototype.

This kernel is deliberately separate from :mod:`.trace_kernel`, which remains
the NumPy reference. Rays stay at fixed width and use an active mask through
launch, intersection, material response, scattering, and roulette. The only
host transfer is one packed record array after the last bounce.

The prototype returns the launch population and escaped paths. It does not
score illumination models or support observers and next-event estimation yet,
so production execution does not call it.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np


_STATUS_ESCAPED = 1
_STATUS_TRUNCATED = 2
_STATUS_ROULETTE = 3
_PACKED_COLUMNS = 13


@dataclass(frozen=True)
class DeviceEscapeRecords:
    """Launch population and escaped paths copied after one device trace.

    ``all_launch_direction`` has one row for every ray, in the global order
    ``ray_start + arange(rays)``. ``escaped_launch_direction`` contains only
    escaped rays and aligns row for row with ``ray_index`` and the other path
    fields. ``truncated_throughput_terms`` keeps the raw float32 values so
    split ranges can be merged with :meth:`merge_truncated_throughput` without
    rounding every part first.
    """

    all_launch_direction: np.ndarray
    ray_index: np.ndarray
    escaped_launch_direction: np.ndarray
    exit_direction: np.ndarray
    throughput: np.ndarray
    path_length: np.ndarray
    last_vertex: np.ndarray
    bounces: np.ndarray
    ray_start: int
    rays: int
    truncated: int
    truncated_throughput: float
    truncated_throughput_terms: np.ndarray
    roulette_killed: int
    seconds: float

    @property
    def escaped(self) -> int:
        return int(self.ray_index.size)

    @property
    def launch_direction(self) -> np.ndarray:
        """Compatibility name for the launch directions of escaped rays."""
        return self.escaped_launch_direction

    @staticmethod
    def merge_truncated_throughput(records: Iterable[DeviceEscapeRecords]) -> float:
        """Sum raw float32 terms once so splitting a ray range changes nothing."""
        return math.fsum(float(value) for record in records for value in record.truncated_throughput_terms)


def _counter_random(mi: Any, ray_index: Any, seed: int, depth: int, dimension: int) -> Any:
    """One repeatable draw keyed only by seed, ray, bounce, and dimension."""
    seed = int(seed) & 0xFFFFFFFFFFFFFFFF
    seed_low = seed & 0xFFFFFFFF
    seed_high = (seed >> 32) & 0xFFFFFFFF
    seed_permutation = (seed_high * 0xD6E8FEB9) & 0xFFFFFFFF
    first = ray_index ^ mi.UInt32(seed_permutation)
    seed_key = (seed_low ^ ((seed_high << 16) & 0xFFFFFFFF) ^ (seed_high >> 16)) & 0xFFFFFFFF
    stream = seed_key ^ (((depth + 1) * 0x9E3779B9) & 0xFFFFFFFF) ^ (((dimension + 1) * 0x85EBCA6B) & 0xFFFFFFFF)
    return mi.sample_tea_float32(first, mi.UInt32(stream))


def _unit_sphere(mi: Any, dr: Any, ray_index: Any, seed: int) -> Any:
    z = 2.0 * _counter_random(mi, ray_index, seed, -1, 0) - 1.0
    phi = 2.0 * np.pi * _counter_random(mi, ray_index, seed, -1, 1)
    radius = dr.sqrt(dr.maximum(0.0, 1.0 - z * z))
    sin_phi, cos_phi = dr.sincos(phi)
    return mi.Vector3f(radius * cos_phi, radius * sin_phi, z)


def _cosine_hemisphere(mi: Any, dr: Any, normal: Any, ray_index: Any, seed: int, depth: int) -> Any:
    u1 = _counter_random(mi, ray_index, seed, depth, 1)
    u2 = _counter_random(mi, ray_index, seed, depth, 2)
    radius = dr.sqrt(u1)
    phi = 2.0 * np.pi * u2
    sin_phi, cos_phi = dr.sincos(phi)
    helper = dr.select(dr.abs(normal.z) < 0.9, mi.Vector3f(0.0, 0.0, 1.0), mi.Vector3f(1.0, 0.0, 0.0))
    tangent = dr.normalize(dr.cross(helper, normal))
    bitangent = dr.cross(normal, tangent)
    return radius * cos_phi * tangent + radius * sin_phi * bitangent + dr.sqrt(1.0 - u1) * normal


def _fresnel_power(mi: Any, dr: Any, cosine: Any, permittivity: Any) -> Any:
    cosine_complex = mi.Complex2f(dr.clip(cosine, 0.0, 1.0), 0.0)
    root = dr.sqrt(permittivity - (1.0 - cosine_complex * cosine_complex))
    te = (cosine_complex - root) / (cosine_complex + root)
    tm = (permittivity * cosine_complex - root) / (permittivity * cosine_complex + root)
    return 0.5 * (dr.square(dr.abs(te)) + dr.square(dr.abs(tm)))


def _specular_share(dr: Any, rms_height_m: Any, cosine: Any, wavelength_m: float) -> Any:
    g = 4.0 * np.pi * rms_height_m * cosine / wavelength_m
    return dr.exp(-dr.minimum(g * g, 60.0))


class DeviceSbrKernel:
    """Fixed-width escape tracer shared by the LLVM and CUDA Dr.Jit variants."""

    def __init__(
        self,
        geometry: Any,
        face_class: np.ndarray | None,
        permittivity: np.ndarray,
        rms_height_m: np.ndarray,
        config: Any,
    ) -> None:
        import mitsuba as mi

        if not hasattr(geometry, "intersect_device"):
            raise TypeError("device SBR requires geometry with intersect_device()")
        self.geometry = geometry
        self.config = config
        self.mi = mi
        self.dr = __import__("drjit")
        self.permittivity = np.asarray(permittivity, dtype=np.complex128)
        self.rms_height_m = np.asarray(rms_height_m, dtype=np.float64)
        if self.permittivity.ndim != 1 or self.rms_height_m.shape != self.permittivity.shape:
            raise ValueError("permittivity and rms_height_m must be one-dimensional arrays with the same shape")
        if self.permittivity.size == 0:
            raise ValueError("at least one material class is required")
        if face_class is None:
            face_count = int(getattr(geometry, "face_count", 1))
            face_class = np.zeros(face_count, dtype=np.uint32)
        raw_face_class = np.asarray(face_class)
        if raw_face_class.ndim != 1:
            raise ValueError("face_class must be one-dimensional")
        if not (np.issubdtype(raw_face_class.dtype, np.integer) or np.issubdtype(raw_face_class.dtype, np.floating)):
            raise ValueError("face_class must contain finite integer material indices")
        numeric_face_class = raw_face_class.astype(np.float64)
        if not np.all(np.isfinite(numeric_face_class)) or not np.all(
            numeric_face_class == np.floor(numeric_face_class)
        ):
            raise ValueError("face_class must contain finite integer material indices")
        if np.any(numeric_face_class < 0):
            raise ValueError("face_class cannot contain negative material indices")
        if np.any(numeric_face_class > np.iinfo(np.uint32).max):
            raise ValueError("face_class material indices must fit in uint32")
        self.face_class = numeric_face_class.astype(np.uint32)
        face_count = getattr(geometry, "face_count", None)
        if face_count is not None and self.face_class.shape != (int(face_count),):
            raise ValueError(f"face_class has shape {self.face_class.shape}, expected ({int(face_count)},)")
        if self.face_class.size and int(self.face_class.max()) >= self.permittivity.size:
            raise ValueError("face_class contains a material index outside the material tables")
        self.wavelength_m = 299_792_458.0 / float(config.frequency_hz)

        self._face_class_device = mi.UInt32(self.face_class)
        self._permittivity_device = mi.Complex2f(
            mi.Float(np.ascontiguousarray(self.permittivity.real)),
            mi.Float(np.ascontiguousarray(self.permittivity.imag)),
        )
        self._rms_height_device = mi.Float(np.ascontiguousarray(self.rms_height_m))
        self.dr.eval(self._face_class_device, self._permittivity_device, self._rms_height_device)
        prepare_device = getattr(self.geometry, "prepare_device", None)
        if prepare_device is not None:
            prepare_device()

    def trace_escape_records(
        self,
        origin: np.ndarray,
        *,
        rays: int | None = None,
        ray_start: int = 0,
        seed: int | None = None,
        observers: Any = None,
        next_event: Any = None,
    ) -> DeviceEscapeRecords:
        """Trace raw escape records, with all transport work kept on Dr.Jit.

        ``ray_start`` is the global counter offset. Splitting one run into any
        set of ranges therefore gives the same path for every ray.
        """
        attached = [name for name, value in (("observers", observers), ("next_event", next_event)) if value is not None]
        if attached:
            raise NotImplementedError(
                "device SBR does not yet support observers or next-event estimation: " + ", ".join(attached)
            )
        count = int(self.config.rays if rays is None else rays)
        if count < 1:
            raise ValueError("rays must be positive")
        if ray_start < 0 or ray_start + count > 0x100000000:
            raise ValueError("ray indices must fit in uint32")

        mi, dr = self.mi, self.dr
        used_seed = int(self.config.seed if seed is None else seed)
        started = time.perf_counter()
        ray_index = dr.arange(mi.UInt32, count) + mi.UInt32(ray_start)
        direction = _unit_sphere(mi, dr, ray_index, used_seed)
        # Materialise the counter draw before Mitsuba fuses it into an
        # intersection kernel. CUDA otherwise preserves the same rounded
        # launch vector but changes a few later low bits when the launch
        # expression has a different ray-range offset.
        dr.eval(direction)
        launch_direction = direction
        point = np.asarray(origin, dtype=np.float64)
        if point.shape != (3,):
            raise ValueError(f"origin must have shape (3,), got {point.shape}")
        position = mi.Point3f(
            dr.full(mi.Float, float(point[0]), count),
            dr.full(mi.Float, float(point[1]), count),
            dr.full(mi.Float, float(point[2]), count),
        )
        throughput = dr.full(mi.Float, 1.0, count)
        path_length = dr.zeros(mi.Float, count)
        last_vertex = position
        bounces = dr.zeros(mi.UInt32, count)
        status = dr.zeros(mi.UInt32, count)
        alive = dr.full(mi.Bool, True, count)

        for depth in range(int(self.config.max_bounces) + 1):
            epsilon = float(self.config.ray_epsilon_m)
            intersection = self.geometry.intersect_device(position + epsilon * direction, direction, alive)
            escaped = alive & ~intersection.hit
            status = dr.select(escaped, _STATUS_ESCAPED, status)
            hit = alive & intersection.hit
            if depth == int(self.config.max_bounces):
                status = dr.select(hit, _STATUS_TRUNCATED, status)
                alive &= ~hit
                continue

            # ``distance`` starts at the epsilon-shifted query origin. Adding
            # the same epsilon here recovers the true surface point. The next
            # loop shifts that point along the new ray, matching the NumPy
            # reference without translating the reflected line.
            hit_position = position + (intersection.distance + epsilon) * direction
            path_length = dr.select(hit, path_length + intersection.distance, path_length)
            last_vertex = dr.select(hit, hit_position, last_vertex)
            bounces = dr.select(hit, bounces + 1, bounces)

            geometric_normal = intersection.normal
            facing = dr.select(-dr.dot(direction, geometric_normal) < 0.0, -1.0, 1.0)
            normal = geometric_normal * facing
            position = dr.select(hit, hit_position, position)
            cosine = dr.clip(-dr.dot(direction, normal), 0.0, 1.0)
            material = dr.gather(mi.UInt32, self._face_class_device, intersection.face, hit)
            permittivity = dr.gather(mi.Complex2f, self._permittivity_device, material, hit)
            rms_height = dr.gather(mi.Float, self._rms_height_device, material, hit)
            reflectance = _fresnel_power(mi, dr, cosine, permittivity)
            share = _specular_share(dr, rms_height, cosine, self.wavelength_m)
            hit_throughput = throughput * reflectance
            throughput = dr.select(hit, hit_throughput, throughput)

            take_specular = _counter_random(mi, ray_index, used_seed, depth, 0) < share
            mirror = direction - 2.0 * dr.dot(direction, normal) * normal
            diffuse = _cosine_hemisphere(mi, dr, normal, ray_index, used_seed, depth)
            scattered = dr.normalize(dr.select(take_specular, mirror, diffuse))
            direction = dr.select(hit, scattered, direction)
            alive = hit

            if depth + 1 >= int(self.config.roulette_start):
                survive_probability = dr.clip(throughput, float(self.config.roulette_floor), 1.0)
                survive = _counter_random(mi, ray_index, used_seed, depth, 3) < survive_probability
                killed = alive & ~survive
                status = dr.select(killed, _STATUS_ROULETTE, status)
                throughput = dr.select(alive, throughput / survive_probability, throughput)
                alive &= survive

        return self._transfer_records(
            ray_index,
            launch_direction,
            direction,
            throughput,
            path_length,
            last_vertex,
            bounces,
            status,
            ray_start,
            count,
            started,
        )

    def _transfer_records(self, *parts: Any) -> DeviceEscapeRecords:
        """Compact escaped rays and cross the device boundary in one array copy."""
        (
            ray_index,
            launch,
            direction,
            throughput,
            path_length,
            last_vertex,
            bounces,
            status,
            ray_start,
            count,
            started,
        ) = parts
        mi, dr = self.mi, self.dr
        dr.schedule(ray_index, launch, direction, throughput, path_length, last_vertex, bounces, status)
        escaped_index = dr.compress(status == _STATUS_ESCAPED)
        truncated_index = dr.compress(status == _STATUS_TRUNCATED)
        truncated = dr.sum(mi.UInt32(status == _STATUS_TRUNCATED))
        roulette_killed = dr.sum(mi.UInt32(status == _STATUS_ROULETTE))
        packed_parts = [
            dr.reinterpret_array(mi.Float, truncated),
            dr.reinterpret_array(mi.Float, roulette_killed),
            launch.x,
            launch.y,
            launch.z,
        ]
        if dr.width(truncated_index) > 0:
            packed_parts.append(dr.gather(mi.Float, throughput, truncated_index))
        if dr.width(escaped_index) > 0:
            ray_index = dr.gather(mi.UInt32, ray_index, escaped_index)
            launch = dr.gather(mi.Vector3f, launch, escaped_index)
            direction = dr.gather(mi.Vector3f, direction, escaped_index)
            throughput = dr.gather(mi.Float, throughput, escaped_index)
            path_length = dr.gather(mi.Float, path_length, escaped_index)
            last_vertex = dr.gather(mi.Point3f, last_vertex, escaped_index)
            bounces = dr.gather(mi.UInt32, bounces, escaped_index)
            packed_parts.extend(
                (
                    dr.reinterpret_array(mi.Float, ray_index),
                    launch.x,
                    launch.y,
                    launch.z,
                    direction.x,
                    direction.y,
                    direction.z,
                    throughput,
                    path_length,
                    last_vertex.x,
                    last_vertex.y,
                    last_vertex.z,
                    dr.reinterpret_array(mi.Float, bounces),
                )
            )
        packed_device = dr.concat(packed_parts)
        transferred = np.asarray(packed_device).copy()
        summary = transferred[:2].view(np.uint32)
        offset = 2
        launch_size = 3 * count
        all_launch_direction = transferred[offset : offset + launch_size].reshape(3, count).T.copy()
        offset += launch_size
        truncated_count = int(summary[0])
        truncated_throughput_terms = transferred[offset : offset + truncated_count].copy()
        truncated_throughput = math.fsum(float(value) for value in truncated_throughput_terms)
        offset += truncated_count
        escaped_count = (transferred.size - offset) // _PACKED_COLUMNS
        if transferred.size - offset != _PACKED_COLUMNS * escaped_count:
            raise RuntimeError("device escape record packing is inconsistent")
        packed = transferred[offset:].reshape(_PACKED_COLUMNS, escaped_count).T
        integer_bits = packed.view(np.uint32)
        escaped_ray_index = integer_bits[:, 0].copy()
        if escaped_ray_index.size > 1 and np.any(escaped_ray_index[1:] <= escaped_ray_index[:-1]):
            raise RuntimeError("device escape records are not in increasing global ray-index order")
        return DeviceEscapeRecords(
            all_launch_direction=all_launch_direction,
            ray_index=escaped_ray_index,
            escaped_launch_direction=packed[:, 1:4].copy(),
            exit_direction=packed[:, 4:7].copy(),
            throughput=packed[:, 7].copy(),
            path_length=packed[:, 8].copy(),
            last_vertex=packed[:, 9:12].copy(),
            bounces=integer_bits[:, 12].copy(),
            ray_start=ray_start,
            rays=count,
            truncated=truncated_count,
            truncated_throughput=truncated_throughput,
            truncated_throughput_terms=truncated_throughput_terms,
            roulette_killed=int(summary[1]),
            seconds=time.perf_counter() - started,
        )

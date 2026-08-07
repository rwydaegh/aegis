"""Dr.Jit-resident escape SBR prototype.

This kernel is deliberately separate from :mod:`.trace_kernel`, which remains
the NumPy reference. Rays stay at fixed width and use an active mask through
launch, intersection, material response, scattering, and roulette. The only
host transfer is one packed record array after the last bounce.

The kernel returns the launch population and escaped paths. It can also run the
resident diffuse and sampled mixed-specular next-event gather. Host observers
and illumination-law scoring remain outside the device loop.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .trace_kernel import launch_rotation


_STATUS_ESCAPED = 1
_STATUS_TRUNCATED = 2
_STATUS_ROULETTE = 3
_STATUS_CANOPY_LOOP_ERROR = 4
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
    next_event: Any = None

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


def _counter_random(mi: Any, ray_index: Any, seed: tuple[Any, Any], depth: int, dimension: int) -> Any:
    """One repeatable draw keyed only by seed, ray, bounce, and dimension."""
    seed_low, seed_high = seed
    seed_permutation = seed_high * mi.UInt32(0xD6E8FEB9)
    first = ray_index ^ seed_permutation
    seed_key = seed_low ^ (seed_high << 16) ^ (seed_high >> 16)
    stream = seed_key ^ (((depth + 1) * 0x9E3779B9) & 0xFFFFFFFF) ^ (((dimension + 1) * 0x85EBCA6B) & 0xFFFFFFFF)
    return mi.sample_tea_float32(first, stream)


def _unit_sphere(mi: Any, dr: Any, ray_index: Any, seed: tuple[Any, Any]) -> Any:
    z = 2.0 * _counter_random(mi, ray_index, seed, -1, 0) - 1.0
    phi = 2.0 * np.pi * _counter_random(mi, ray_index, seed, -1, 1)
    radius = dr.sqrt(dr.maximum(0.0, 1.0 - z * z))
    sin_phi, cos_phi = dr.sincos(phi)
    return mi.Vector3f(radius * cos_phi, radius * sin_phi, z)


def _rotated_fibonacci_sphere(
    mi: Any,
    dr: Any,
    ray_index: Any,
    total: int,
    seed: int,
) -> Any:
    """Device form of the globally indexed rotated Fibonacci lattice.

    The radius uses ``sqrt((2i+1)(2N-2i-1))/N``, algebraically equal to
    ``sqrt(1-z**2)`` without its float32 cancellation at the two polar samples.
    The global phase remains a wrapped uint32 Weyl sequence, so range splitting
    cannot move a lattice point.
    """
    odd = 2.0 * mi.Float(ray_index) + 1.0
    z = (float(total) - odd) / float(total)
    phase = ray_index * mi.UInt32(0x61C88647)
    theta = mi.Float(phase) * (2.0 * np.pi / float(1 << 32))
    radius = dr.sqrt(dr.maximum(0.0, odd * (2.0 * float(total) - odd))) / float(total)
    sin_theta, cos_theta = dr.sincos(theta)
    x = radius * cos_theta
    y = radius * sin_theta
    rotation = launch_rotation(seed)
    r00, r01, r02, r10, r11, r12, r20, r21, r22 = (dr.opaque(mi.Float, float(value)) for value in rotation.flat)
    return mi.Vector3f(
        r00 * x + r01 * y + r02 * z,
        r10 * x + r11 * y + r12 * z,
        r20 * x + r21 * y + r22 * z,
    )


def _cosine_hemisphere(
    mi: Any,
    dr: Any,
    normal: Any,
    ray_index: Any,
    seed: tuple[Any, Any],
    depth: int,
) -> Any:
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
        *,
        atlas_material: Any = None,
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
        self.atlas_material = atlas_material
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
        if self.atlas_material is not None:
            if self.atlas_material.face_count != self.face_class.size:
                raise ValueError(
                    f"atlas material binding has {self.atlas_material.face_count} faces, "
                    f"but geometry has {self.face_class.size}"
                )
            if np.any(self.atlas_material.material_class >= self.permittivity.size):
                raise ValueError("atlas material classes leave the material table")
        self.wavelength_m = 299_792_458.0 / float(config.frequency_hz)

        self._face_class_device = mi.UInt32(self.face_class)
        self._permittivity_device = mi.Complex2f(
            mi.Float(np.ascontiguousarray(self.permittivity.real)),
            mi.Float(np.ascontiguousarray(self.permittivity.imag)),
        )
        self._rms_height_device = mi.Float(np.ascontiguousarray(self.rms_height_m))
        device_arrays = [self._face_class_device, self._permittivity_device, self._rms_height_device]
        if self.atlas_material is not None:
            self._atlas_face_to_row_device = mi.Int32(
                np.ascontiguousarray(self.atlas_material.face_to_atlas_row, dtype=np.int32)
            )
            self._atlas_probability_device = mi.Float(
                np.ascontiguousarray(self.atlas_material.material_probability, dtype=np.float32).reshape(-1)
            )
            self._atlas_supported_device = mi.Bool(
                np.ascontiguousarray(self.atlas_material.supported, dtype=bool).reshape(-1)
            )
            self._atlas_nonblocking_device = mi.Bool(
                np.ascontiguousarray(self.atlas_material.nonblocking, dtype=bool).reshape(-1)
            )
            device_arrays.extend(
                (
                    self._atlas_face_to_row_device,
                    self._atlas_probability_device,
                    self._atlas_supported_device,
                    self._atlas_nonblocking_device,
                )
            )
        self.dr.eval(*device_arrays)
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
        attached = [name for name, value in (("observers", observers),) if value is not None]
        if attached:
            raise NotImplementedError("device SBR does not yet support host observers: " + ", ".join(attached))
        if next_event is not None and not hasattr(next_event, "_device_state"):
            raise NotImplementedError("device next_event requires the resident DeviceNextEventGather contract")
        count = int(self.config.rays if rays is None else rays)
        if count < 1:
            raise ValueError("rays must be positive")
        if ray_start < 0 or ray_start + count > 0x100000000:
            raise ValueError("ray indices must fit in uint32")
        if self.config.launch_sampling == "rotated_fibonacci" and ray_start + count > int(self.config.rays):
            raise ValueError("device ray range must lie inside the complete Fibonacci lattice")

        mi, dr = self.mi, self.dr
        used_seed_value = int(self.config.seed if seed is None else seed) & 0xFFFFFFFFFFFFFFFF
        used_seed = (
            dr.opaque(mi.UInt32, used_seed_value & 0xFFFFFFFF),
            dr.opaque(mi.UInt32, used_seed_value >> 32),
        )
        started = time.perf_counter()
        ray_index = dr.arange(mi.UInt32, count) + dr.opaque(mi.UInt32, ray_start)
        next_event_state = (
            None if next_event is None else next_event._device_state(self, ray_index, count, used_seed_value)
        )
        next_event_seed = None
        if next_event is not None:
            gather_seed_value = (used_seed_value + int(next_event.seed_offset)) & 0xFFFFFFFFFFFFFFFF
            next_event_seed = (
                dr.opaque(mi.UInt32, gather_seed_value & 0xFFFFFFFF),
                dr.opaque(mi.UInt32, gather_seed_value >> 32),
            )
        if self.config.launch_sampling == "iid":
            direction = _unit_sphere(mi, dr, ray_index, used_seed)
        elif self.config.launch_sampling == "rotated_fibonacci":
            direction = _rotated_fibonacci_sphere(mi, dr, ray_index, int(self.config.rays), used_seed_value)
        else:  # TraceConfig validates this. Keep the kernel safe for compatible config objects.
            raise ValueError(f"unsupported launch_sampling {self.config.launch_sampling!r}")
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
            dr.opaque(mi.Float, float(point[0]), count),
            dr.opaque(mi.Float, float(point[1]), count),
            dr.opaque(mi.Float, float(point[2]), count),
        )
        throughput = dr.full(mi.Float, 1.0, count)
        path_length = dr.zeros(mi.Float, count)
        last_vertex = position
        bounces = dr.zeros(mi.UInt32, count)
        status = dr.zeros(mi.UInt32, count)
        alive = dr.full(mi.Bool, True, count)

        for depth in range(int(self.config.max_bounces) + 1):
            # Rays in ``searching`` may cross any number of non-blocking
            # canopy cells before they escape or reach a real interface. The
            # loop only finds that interface. Material response stays outside
            # it, so a pass-through does not evaluate the material catalogue.
            searching = alive
            canopy_crossings = dr.zeros(mi.UInt32, count)
            blocking = dr.zeros(mi.Bool, count)
            interface_normal = mi.Vector3f(0.0)
            interface_face = dr.zeros(mi.UInt32, count)
            interface_uv = mi.Point2f(0.0)
            # The atlas lookup is needed both to decide whether a hit is a
            # pass-through surface and to evaluate a blocking material mix.
            # Carry it through the search loop so the blocking hit does not
            # repeat the same device gathers.
            interface_atlas_supported = dr.zeros(mi.Bool, count)
            interface_atlas_nonblocking = dr.zeros(mi.Bool, count)
            interface_atlas_texel = dr.zeros(mi.Int32, count)
            # A ray that only advances can cross each triangle at most once.
            # One more query is needed to establish escape after crossing the
            # final face. Keeping this bound in device state also turns a
            # repeated self-hit caused by invalid geometry into a hard error.
            max_canopy_crossings = int(self.face_class.size)

            def continue_search(
                searching: Any,
                canopy_crossings: Any,
                blocking: Any,
                position: Any,
                path_length: Any,
                last_vertex: Any,
                interface_normal: Any,
                interface_face: Any,
                interface_uv: Any,
                interface_atlas_supported: Any,
                interface_atlas_nonblocking: Any,
                interface_atlas_texel: Any,
                status: Any,
            ) -> Any:
                del (
                    blocking,
                    position,
                    path_length,
                    last_vertex,
                    interface_normal,
                    interface_face,
                    interface_uv,
                    interface_atlas_supported,
                    interface_atlas_nonblocking,
                    interface_atlas_texel,
                    status,
                )
                return searching & (canopy_crossings <= max_canopy_crossings)

            def search_step(
                searching: Any,
                canopy_crossings: Any,
                blocking: Any,
                position: Any,
                path_length: Any,
                last_vertex: Any,
                interface_normal: Any,
                interface_face: Any,
                interface_uv: Any,
                interface_atlas_supported: Any,
                interface_atlas_nonblocking: Any,
                interface_atlas_texel: Any,
                status: Any,
            ) -> tuple[Any, ...]:
                epsilon = float(self.config.ray_epsilon_m)
                intersection = self.geometry.intersect_device(
                    position + epsilon * direction,
                    direction,
                    searching,
                )
                escaped = searching & ~intersection.hit
                status = dr.select(escaped, _STATUS_ESCAPED, status)
                hit = searching & intersection.hit
                # The atlas mask is enough to cross a false canopy surface.
                # Fresnel mixtures are evaluated only for the one real
                # interface that ends this search.
                if self.atlas_material is None:
                    atlas_lookup = None
                else:
                    atlas_lookup = self._atlas_lookup(
                        intersection.face,
                        intersection.barycentric_uv,
                        hit,
                    )
                nonblocking = self._surface_nonblocking(intersection, hit, atlas_lookup=atlas_lookup)
                pass_through = hit & nonblocking
                blocking_here = hit & ~nonblocking
                canopy_crossings = dr.select(pass_through, canopy_crossings + 1, canopy_crossings)
                blocking |= blocking_here
                interface_normal = dr.select(blocking_here, intersection.normal, interface_normal)
                interface_face = dr.select(blocking_here, intersection.face, interface_face)
                interface_uv = dr.select(blocking_here, intersection.barycentric_uv, interface_uv)
                if atlas_lookup is not None:
                    lookup_supported, lookup_nonblocking, lookup_texel = atlas_lookup
                    interface_atlas_supported = dr.select(
                        blocking_here,
                        lookup_supported,
                        interface_atlas_supported,
                    )
                    interface_atlas_nonblocking = dr.select(
                        blocking_here,
                        lookup_nonblocking,
                        interface_atlas_nonblocking,
                    )
                    interface_atlas_texel = dr.select(
                        blocking_here,
                        lookup_texel,
                        interface_atlas_texel,
                    )

                # ``distance`` starts at the epsilon-shifted query origin.
                # Adding the same epsilon recovers the true surface point.
                hit_position = position + (intersection.distance + epsilon) * direction
                path_length = dr.select(hit, path_length + intersection.distance, path_length)
                last_vertex = dr.select(hit, hit_position, last_vertex)
                position = dr.select(hit, hit_position, position)
                searching = pass_through
                return (
                    searching,
                    canopy_crossings,
                    blocking,
                    position,
                    path_length,
                    last_vertex,
                    interface_normal,
                    interface_face,
                    interface_uv,
                    interface_atlas_supported,
                    interface_atlas_nonblocking,
                    interface_atlas_texel,
                    status,
                )

            (
                searching,
                canopy_crossings,
                blocking,
                position,
                path_length,
                last_vertex,
                interface_normal,
                interface_face,
                interface_uv,
                interface_atlas_supported,
                interface_atlas_nonblocking,
                interface_atlas_texel,
                status,
            ) = dr.while_loop(
                state=(
                    searching,
                    canopy_crossings,
                    blocking,
                    position,
                    path_length,
                    last_vertex,
                    interface_normal,
                    interface_face,
                    interface_uv,
                    interface_atlas_supported,
                    interface_atlas_nonblocking,
                    interface_atlas_texel,
                    status,
                ),
                cond=continue_search,
                body=search_step,
                mode="symbolic" if str(getattr(self.geometry, "variant", "")).startswith("cuda") else "evaluated",
                label=f"canopy pass-through at bounce {depth}",
            )
            status = dr.select(searching, _STATUS_CANOPY_LOOP_ERROR, status)
            blocking &= ~searching
            if depth == int(self.config.max_bounces):
                status = dr.select(blocking, _STATUS_TRUNCATED, status)
                alive = dr.zeros(mi.Bool, count)
            else:
                facing = dr.select(-dr.dot(direction, interface_normal) < 0.0, -1.0, 1.0)
                normal = interface_normal * facing
                cosine = dr.clip(-dr.dot(direction, normal), 0.0, 1.0)
                material = dr.gather(mi.UInt32, self._face_class_device, interface_face, blocking)
                reflectance, share, _ = self._surface_response_at(
                    cosine,
                    material,
                    interface_face,
                    interface_uv,
                    blocking,
                    atlas_lookup=(
                        interface_atlas_supported,
                        interface_atlas_nonblocking,
                        interface_atlas_texel,
                    ),
                )
                bounces = dr.select(blocking, bounces + 1, bounces)
                throughput = dr.select(blocking, throughput * reflectance, throughput)
                if next_event_state is not None:
                    if next_event_seed is None:
                        raise AssertionError("device next-event seed was not initialised")
                    next_event_state.vertex(
                        depth,
                        position,
                        normal,
                        throughput,
                        share,
                        blocking,
                        lambda sample: _counter_random(
                            mi,
                            ray_index,
                            next_event_seed,
                            depth,
                            sample,
                        ),
                    )

                take_specular = _counter_random(mi, ray_index, used_seed, depth, 0) < share
                mirror = direction - 2.0 * dr.dot(direction, normal) * normal
                diffuse = _cosine_hemisphere(mi, dr, normal, ray_index, used_seed, depth)
                scattered = dr.normalize(dr.select(take_specular, mirror, diffuse))
                direction = dr.select(blocking, scattered, direction)

                alive = blocking
                if depth + 1 >= int(self.config.roulette_start):
                    survive_probability = dr.clip(throughput, float(self.config.roulette_floor), 1.0)
                    survive = _counter_random(mi, ray_index, used_seed, depth, 3) < survive_probability
                    killed = alive & ~survive
                    status = dr.select(killed, _STATUS_ROULETTE, status)
                    throughput = dr.select(alive, throughput / survive_probability, throughput)
                    alive &= survive
            # Keep the fixed physical-bounce loop outside the generated
            # device loop. This also avoids nesting several OptiX loops into
            # one very large graph and gives every later bounce reusable,
            # materialised inputs.
            dr.eval(position, direction, throughput, path_length, last_vertex, bounces, status, alive)

        records = self._transfer_records(
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
        if next_event_state is not None:
            records = replace(records, next_event=next_event_state.transfer(ray_start))
        return records

    def _surface_response(
        self,
        cosine: Any,
        fallback_material: Any,
        intersection: Any,
        hit: Any,
    ) -> tuple[Any, Any, Any]:
        """Evaluate an interface and return its non-blocking volume state."""
        return self._surface_response_at(
            cosine,
            fallback_material,
            intersection.face,
            intersection.barycentric_uv,
            hit,
        )

    def _surface_response_at(
        self,
        cosine: Any,
        fallback_material: Any,
        face: Any,
        barycentric_uv: Any,
        hit: Any,
        *,
        atlas_lookup: tuple[Any, Any, Any] | None = None,
    ) -> tuple[Any, Any, Any]:
        """Evaluate an interface from its compact device coordinates."""
        mi, dr = self.mi, self.dr
        permittivity = dr.gather(mi.Complex2f, self._permittivity_device, fallback_material, hit)
        rms_height = dr.gather(mi.Float, self._rms_height_device, fallback_material, hit)
        fallback_reflectance = _fresnel_power(mi, dr, cosine, permittivity)
        fallback_share = _specular_share(dr, rms_height, cosine, self.wavelength_m)
        if self.atlas_material is None:
            return fallback_reflectance, fallback_share, dr.zeros(mi.Bool, dr.width(cosine))

        if atlas_lookup is None:
            supported, nonblocking, texel = self._atlas_lookup(face, barycentric_uv, hit)
        else:
            supported, nonblocking, texel = atlas_lookup
        material_count = len(self.atlas_material.material_names)

        reflected_power = dr.zeros(mi.Float, dr.width(cosine))
        specular_power = dr.zeros(mi.Float, dr.width(cosine))
        for channel, class_index in enumerate(self.atlas_material.material_class.tolist()):
            probability = dr.gather(
                mi.Float,
                self._atlas_probability_device,
                texel * material_count + channel,
                supported,
            )
            component_permittivity = dr.gather(
                mi.Complex2f,
                self._permittivity_device,
                mi.UInt32(int(class_index)),
                supported,
            )
            component_rms = dr.gather(
                mi.Float,
                self._rms_height_device,
                mi.UInt32(int(class_index)),
                supported,
            )
            component_reflectance = _fresnel_power(mi, dr, cosine, component_permittivity)
            component_share = _specular_share(dr, component_rms, cosine, self.wavelength_m)
            reflected_power += probability * component_reflectance
            specular_power += probability * component_reflectance * component_share
        mixed_share = dr.select(reflected_power > 0.0, specular_power / reflected_power, 0.0)
        return (
            dr.select(supported, reflected_power, fallback_reflectance),
            dr.select(supported, mixed_share, fallback_share),
            nonblocking,
        )

    def _surface_nonblocking(
        self,
        intersection: Any,
        hit: Any,
        *,
        atlas_lookup: tuple[Any, Any, Any] | None = None,
    ) -> Any:
        """Return pass-through state without evaluating any material model."""
        mi, dr = self.mi, self.dr
        if self.atlas_material is None:
            return dr.zeros(mi.Bool, dr.width(hit))
        if atlas_lookup is None:
            _supported, nonblocking, _texel = self._atlas_lookup(
                intersection.face,
                intersection.barycentric_uv,
                hit,
            )
        else:
            _supported, nonblocking, _texel = atlas_lookup
        return nonblocking

    def _atlas_lookup(self, face: Any, barycentric_uv: Any, hit: Any) -> tuple[Any, Any, Any]:
        """Return supported, non-blocking, and flat texel indices."""
        mi, dr = self.mi, self.dr
        atlas_row = dr.gather(mi.Int32, self._atlas_face_to_row_device, face, hit)
        atlas_hit = hit & (atlas_row >= 0)
        safe_row = dr.maximum(atlas_row, 0)
        height, width = self.atlas_material.resolution
        u = dr.clip(barycentric_uv.x, 0.0, 1.0)
        v = dr.clip(barycentric_uv.y, 0.0, 1.0)
        scaled_row = v * float(height - 1)
        scaled_column = u * float(width - 1)
        texel_row = mi.Int32(dr.floor(scaled_row + 0.5))
        texel_column = mi.Int32(dr.floor(scaled_column + 0.5))
        row_excess = mi.Float(texel_row) - scaled_row
        column_excess = mi.Float(texel_column) - scaled_column
        outside = mi.Float(texel_row) / float(height - 1) + mi.Float(texel_column) / float(width - 1) > 1.0 + 1.0e-7
        step_row = outside & (row_excess >= column_excess)
        texel_row = dr.select(step_row, texel_row - 1, texel_row)
        texel_column = dr.select(outside & ~step_row, texel_column - 1, texel_column)
        texel = (safe_row * height + texel_row) * width + texel_column
        supported = atlas_hit & dr.gather(mi.Bool, self._atlas_supported_device, texel, atlas_hit)
        nonblocking = atlas_hit & dr.gather(mi.Bool, self._atlas_nonblocking_device, texel, atlas_hit)
        return supported, nonblocking, texel

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
        canopy_loop_errors = dr.sum(mi.UInt32(status == _STATUS_CANOPY_LOOP_ERROR))
        packed_parts = [
            dr.reinterpret_array(mi.Float, truncated),
            dr.reinterpret_array(mi.Float, roulette_killed),
            dr.reinterpret_array(mi.Float, canopy_loop_errors),
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
        summary = transferred[:3].view(np.uint32)
        if summary[2]:
            raise RuntimeError(
                f"{int(summary[2])} rays exceeded the support-mesh face count while crossing "
                "non-blocking canopy cells; the mesh likely contains a repeated self-intersection"
            )
        offset = 3
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

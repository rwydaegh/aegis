"""Forward Sionna check of the facade-tip next-event estimator.

The production estimator is unusual only in which end of a link it traces from.
It starts at a pedestrian, traces an adjoint path, and connects every surface
vertex to a sampled facade-tip source. This module asks Sionna RT the ordinary
forward question on the same geometry: launch from each facade-tip transmitter
and find the paths to each pedestrian.

The matched observable for receiver ``j`` is

``K_j = mean_i sum_p |a_ijp|^2 / (lambda / 4 pi)^2``.

The sum is incoherent over paths and complete over two transmit and two receive
polarisations. The factor one half averages the two transmitted polarisations.
An isotropic free-space link then contributes ``1 / r_ij^2``. This is exactly
the direct term used by :class:`~semantic_twin.transport.next_event.NextEventEstimator`.

The primary comparison deliberately uses one material everywhere: a fully
diffuse near-perfect reflector. It is the only useful material-free match.
Reflectance is one for both polarisations, the diffuse lobe is Lambertian in both
solvers, and Sionna's specular path finder can be disabled. A run with production
materials is a sensitivity study because the two solvers then differ in their
roughness and polarisation models.
"""

from __future__ import annotations

import math
import multiprocessing
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

from ..illumination.roofline import FACADE_TIP_FAMILY, FACADE_TIP_LAW
from ..propagation.closed_form import PEC_PERMITTIVITY
from .next_event import NextEventEstimator
from .sionna_check import SPEED_OF_LIGHT_M_S, build_scene, write_ply
from .tracer import SbrTracer, TraceConfig

FULLY_DIFFUSE_RMS_HEIGHT_M = 1.0
FULLY_DIFFUSE_SCATTERING_COEFFICIENT = 1.0


@dataclass(frozen=True)
class ValidationSources:
    """A fixed set of equally weighted sources used by both solvers."""

    positions: np.ndarray
    name: str = "sionna_validation_sources"
    law: ClassVar[str] = FACADE_TIP_LAW
    family: ClassVar[str] = FACADE_TIP_FAMILY

    def __len__(self) -> int:
        return int(np.asarray(self.positions).shape[0])

    def sites(self) -> np.ndarray:
        return np.asarray(self.positions, dtype=np.float64)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "law": self.law,
            "family": self.family,
            "kind": "placed",
            "sites": len(self),
        }


@dataclass(frozen=True)
class SyntheticEnvironment:
    """A small exact scene shared by the forward and adjoint solvers."""

    name: str
    vertices: np.ndarray
    faces: np.ndarray
    sources: np.ndarray
    receivers: np.ndarray


@dataclass(frozen=True)
class TransferSamples:
    """Direct and total transfer, one row per random seed and receiver."""

    direct: np.ndarray
    total: np.ndarray
    seconds: np.ndarray

    @property
    def bounced(self) -> np.ndarray:
        return self.total - self.direct

    def summary(self) -> dict[str, Any]:
        return {
            "direct": _sample_summary(self.direct),
            "bounced": _sample_summary(self.bounced),
            "total": _sample_summary(self.total),
            "seconds": [float(value) for value in self.seconds],
        }


def _sample_summary(values: np.ndarray) -> dict[str, list[float]]:
    values = np.atleast_2d(np.asarray(values, dtype=np.float64))
    mean = values.mean(axis=0)
    if values.shape[0] > 1:
        standard_error = values.std(axis=0, ddof=1) / math.sqrt(values.shape[0])
    else:
        standard_error = np.full(mean.shape, np.nan)
    return {
        "mean": [float(value) for value in mean],
        "standard_error": [float(value) for value in standard_error],
    }


def free_space_scale(wavelength_m: float) -> float:
    """The constant that turns Sionna link gain into inverse square range."""
    return float((float(wavelength_m) / (4.0 * np.pi)) ** 2)


def open_square_environment(source_count: int = 27) -> SyntheticEnvironment:
    """Three flat walls around an open square, with sources on their tips.

    The scene has eight triangles: two for the ground and two for each wall.
    There are no roofs, bevels, duplicate faces, small facets, or reconstruction
    noise. The south side is open so the receiver set covers open, enclosed,
    near-wall, and outside views without adding another geometric mechanism.
    """
    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    def quad(
        a: tuple[float, float, float],
        b: tuple[float, float, float],
        c: tuple[float, float, float],
        d: tuple[float, float, float],
    ) -> None:
        start = len(vertices)
        vertices.extend([list(a), list(b), list(c), list(d)])
        faces.extend([[start, start + 1, start + 2], [start, start + 2, start + 3]])

    quad((-100.0, -100.0, 0.0), (100.0, -100.0, 0.0), (100.0, 100.0, 0.0), (-100.0, 100.0, 0.0))
    quad((-40.0, 40.0, 0.0), (40.0, 40.0, 0.0), (40.0, 40.0, 20.0), (-40.0, 40.0, 20.0))
    quad((-40.0, -40.0, 0.0), (-40.0, 40.0, 0.0), (-40.0, 40.0, 20.0), (-40.0, -40.0, 20.0))
    quad((40.0, 40.0, 0.0), (40.0, -40.0, 0.0), (40.0, -40.0, 20.0), (40.0, 40.0, 20.0))

    if source_count < 1:
        raise ValueError("source_count must be positive")
    counts = [source_count // 3] * 3
    for index in range(source_count % 3):
        counts[index] += 1

    def wall_coordinates(count: int) -> np.ndarray:
        if count == 0:
            return np.empty(0, dtype=np.float64)
        if count == 1:
            return np.array([0.0])
        return np.linspace(-32.0, 32.0, count)

    north_along, west_along, east_along = (wall_coordinates(count) for count in counts)
    north = np.column_stack([north_along, np.full_like(north_along, 40.0), np.full_like(north_along, 20.5)])
    west = np.column_stack([np.full_like(west_along, -40.0), west_along, np.full_like(west_along, 20.5)])
    east = np.column_stack([np.full_like(east_along, 40.0), east_along, np.full_like(east_along, 20.5)])
    sources = np.vstack([north, west, east])
    receivers = np.array(
        [
            [0.0, 0.0, 1.5],
            [0.0, 28.0, 1.5],
            [-28.0, -10.0, 1.5],
            [28.0, 15.0, 1.5],
            [0.0, -55.0, 1.5],
            [0.0, 55.0, 1.5],
        ],
        dtype=np.float64,
    )
    return SyntheticEnvironment(
        name="open_square",
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int64),
        sources=sources,
        receivers=receivers,
    )


def reduce_sionna_paths(paths: Any, wavelength_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reduce one Sionna solve to direct and total transfer per receiver/source.

    Sionna stores ``a`` as ``[rx, rx_port, tx, tx_port, path]`` when a
    synthetic array is used. The cross-polarised one-element arrays have two
    ports at each end. Summing the receive ports and averaging the transmit
    ports produces the same unpolarised scalar power that the adjoint tracer
    carries.
    """
    real, imaginary = paths.a
    amplitude = np.asarray(real) + 1j * np.asarray(imaginary)
    if amplitude.ndim != 5:
        raise ValueError(f"expected five Sionna path axes, got {amplitude.shape}")

    valid = np.asarray(paths.valid, dtype=bool)
    if valid.ndim != 3:
        raise ValueError(f"expected [receiver, transmitter, path] validity, got {valid.shape}")
    power = 0.5 * (np.abs(amplitude) ** 2).sum(axis=(1, 3)) / free_space_scale(wavelength_m)
    power = np.where(valid, power, 0.0)

    interactions = np.asarray(paths.interactions)
    if interactions.ndim != 4:
        raise ValueError(f"expected [depth, receiver, transmitter, path] interactions, got {interactions.shape}")
    line_of_sight = np.all(interactions == 0, axis=0) & valid
    direct = np.where(line_of_sight, power, 0.0).sum(axis=-1)
    total = power.sum(axis=-1)
    paths_per_source = valid.sum(axis=(0, 2))
    return direct, total, paths_per_source


def forward_transfer(
    scene: Any,
    sources: np.ndarray,
    receivers: np.ndarray,
    *,
    max_depth: int = 3,
    samples_per_src: int = 200_000,
    max_num_paths_per_src: int = 4_000_000,
    source_chunk: int = 16,
    seed: int = 1,
) -> dict[str, Any]:
    """Trace ordinary forward links in Sionna and average over the sources."""
    import mitsuba as mi
    import sionna.rt as rt

    sources = np.atleast_2d(np.asarray(sources, dtype=np.float64))
    receivers = np.atleast_2d(np.asarray(receivers, dtype=np.float64))
    if sources.shape[1:] != (3,) or receivers.shape[1:] != (3,):
        raise ValueError("sources and receivers must have shape [count, 3]")
    if sources.shape[0] == 0 or receivers.shape[0] == 0:
        raise ValueError("the forward comparison needs at least one source and receiver")

    solver = rt.PathSolver()
    wavelength_m = SPEED_OF_LIGHT_M_S / float(np.asarray(scene.frequency).reshape(-1)[0])
    direct_sum = np.zeros(receivers.shape[0], dtype=np.float64)
    total_sum = np.zeros(receivers.shape[0], dtype=np.float64)
    high_water = 0
    started = time.perf_counter()

    for start in range(0, sources.shape[0], int(source_chunk)):
        stop = min(start + int(source_chunk), sources.shape[0])
        for name in list(scene.transmitters):
            scene.remove(name)
        for name in list(scene.receivers):
            scene.remove(name)
        for index, position in enumerate(sources[start:stop]):
            scene.add(rt.Transmitter(f"tx{index}", position=[float(value) for value in position]))
        for index, position in enumerate(receivers):
            scene.add(rt.Receiver(f"rx{index}", position=[float(value) for value in position]))

        paths = solver(
            scene,
            max_depth=int(max_depth),
            max_num_paths_per_src=int(max_num_paths_per_src),
            samples_per_src=int(samples_per_src),
            synthetic_array=True,
            los=True,
            specular_reflection=False,
            diffuse_reflection=True,
            refraction=False,
            diffraction=False,
            edge_diffraction=False,
            seed=int(seed) + start,
        )
        pair_direct, pair_total, paths_per_source = reduce_sionna_paths(paths, wavelength_m)
        direct_sum += pair_direct.sum(axis=1)
        total_sum += pair_total.sum(axis=1)
        high_water = max(high_water, int(paths_per_source.max(initial=0)))

    return {
        "direct": direct_sum / sources.shape[0],
        "total": total_sum / sources.shape[0],
        "seconds": time.perf_counter() - started,
        "paths_high_water": high_water,
        "max_num_paths_per_src": int(max_num_paths_per_src),
        "path_buffer_saturated": high_water >= int(max_num_paths_per_src),
        "variant": mi.variant(),
    }


def build_validation_scene(
    vertices: np.ndarray,
    faces: np.ndarray,
    frequency_hz: float,
    *,
    cache_dir: pathlib.Path,
) -> Any:
    """Build Sionna's fully diffuse near-perfect-reflector scene."""
    return build_scene(
        {"validation": write_ply(vertices, faces)},
        {"validation": PEC_PERMITTIVITY},
        {"validation": FULLY_DIFFUSE_SCATTERING_COEFFICIENT},
        frequency_hz,
        cache_dir=cache_dir,
    )


def _solve_forward_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run Sionna in a fresh process with its required polarised variant."""
    if payload.get("sionna_variant"):
        import mitsuba as mi

        mi.set_variant(str(payload["sionna_variant"]))
    scene = build_scene(
        {"validation": payload["ply"]},
        {"validation": PEC_PERMITTIVITY},
        {"validation": FULLY_DIFFUSE_SCATTERING_COEFFICIENT},
        float(payload["frequency_hz"]),
        cache_dir=pathlib.Path(payload["cache_dir"]),
    )
    direct = []
    total = []
    seconds = []
    runs = []
    for seed in payload["seeds"]:
        answer = forward_transfer(
            scene,
            np.asarray(payload["sources"], dtype=np.float64),
            np.asarray(payload["receivers"], dtype=np.float64),
            max_depth=int(payload["max_depth"]),
            samples_per_src=int(payload["samples_per_src"]),
            max_num_paths_per_src=int(payload["max_num_paths_per_src"]),
            source_chunk=int(payload["source_chunk"]),
            seed=int(seed),
        )
        direct.append(answer["direct"].tolist())
        total.append(answer["total"].tolist())
        seconds.append(float(answer["seconds"]))
        runs.append({key: value for key, value in answer.items() if key not in {"direct", "total", "seconds"}})
    return {"direct": direct, "total": total, "seconds": seconds, "runs": runs}


def forward_transfer_subprocess(
    vertices: np.ndarray,
    faces: np.ndarray,
    sources: np.ndarray,
    receivers: np.ndarray,
    *,
    frequency_hz: float,
    cache_dir: pathlib.Path,
    max_depth: int = 3,
    samples_per_src: int = 200_000,
    max_num_paths_per_src: int = 4_000_000,
    source_chunk: int = 16,
    seeds: tuple[int, ...] = (1, 2, 3, 4),
    sionna_variant: str | None = None,
) -> tuple[TransferSamples, list[dict[str, Any]]]:
    """Run forward Sionna solves without changing the parent's Mitsuba variant.

    The production tracer needs ``llvm_ad_rgb``. Sionna needs a polarised
    Mitsuba variant. Mitsuba permits one active variant per process, so a city
    comparison cannot run both solvers safely in one interpreter.
    """
    payload = {
        "ply": write_ply(vertices, faces),
        "sources": np.asarray(sources, dtype=np.float64),
        "receivers": np.asarray(receivers, dtype=np.float64),
        "frequency_hz": float(frequency_hz),
        "cache_dir": str(pathlib.Path(cache_dir)),
        "max_depth": int(max_depth),
        "samples_per_src": int(samples_per_src),
        "max_num_paths_per_src": int(max_num_paths_per_src),
        "source_chunk": int(source_chunk),
        "seeds": tuple(int(seed) for seed in seeds),
        "sionna_variant": sionna_variant,
    }
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        answer = pool.submit(_solve_forward_payload, payload).result()
    samples = TransferSamples(
        direct=np.asarray(answer["direct"], dtype=np.float64),
        total=np.asarray(answer["total"], dtype=np.float64),
        seconds=np.asarray(answer["seconds"], dtype=np.float64),
    )
    return samples, answer["runs"]


def adjoint_transfer(
    geometry: Any,
    sources: np.ndarray,
    receivers: np.ndarray,
    *,
    frequency_hz: float = 15.0e9,
    max_depth: int = 3,
    rays: int = 200_000,
    connections: int = 1,
    seeds: tuple[int, ...] = (1, 2, 3, 4),
    rms_height_m: float = FULLY_DIFFUSE_RMS_HEIGHT_M,
    connection_lift_m: float = 1.0e-2,
) -> TransferSamples:
    """Run the current next-event estimator on the matched diffuse scene."""
    source_set = ValidationSources(np.atleast_2d(np.asarray(sources, dtype=np.float64)))
    receivers = np.atleast_2d(np.asarray(receivers, dtype=np.float64))
    face_count = int(np.asarray(getattr(geometry, "faces", np.empty((0, 3)))).shape[0])
    face_class = np.zeros(face_count, dtype=np.int64) if face_count else None
    config = TraceConfig(
        frequency_hz=float(frequency_hz),
        rays=int(rays),
        max_bounces=int(max_depth),
        roulette_start=int(max_depth) + 1,
        batch=int(rays),
    )
    tracer = SbrTracer(
        geometry,
        face_class,
        np.array([PEC_PERMITTIVITY]),
        np.array([float(rms_height_m)]),
        config,
    )
    estimator = NextEventEstimator(
        tracer=tracer,
        geometry=geometry,
        sources=source_set,
        samples=int(connections),
        max_order=int(max_depth),
        connection_lift_m=float(connection_lift_m),
    )

    direct = np.zeros((len(seeds), receivers.shape[0]), dtype=np.float64)
    total = np.zeros_like(direct)
    seconds = np.zeros(len(seeds), dtype=np.float64)
    for row, seed in enumerate(seeds):
        started = time.perf_counter()
        for column, receiver in enumerate(receivers):
            result = estimator.estimate(receiver, seed=int(seed))
            direct[row, column] = result.direct
            total[row, column] = result.total
        seconds[row] = time.perf_counter() - started
    return TransferSamples(direct=direct, total=total, seconds=seconds)


def comparison(adjoint: TransferSamples, sionna: TransferSamples) -> dict[str, Any]:
    """Compare sample means in dB, including the multipath surplus."""
    out: dict[str, Any] = {}
    for name, left, right in (
        ("direct", adjoint.direct, sionna.direct),
        ("bounced", adjoint.bounced, sionna.bounced),
        ("total", adjoint.total, sionna.total),
    ):
        ours = np.asarray(left, dtype=np.float64).mean(axis=0)
        oracle = np.asarray(right, dtype=np.float64).mean(axis=0)
        out[name] = {
            "sionna_minus_adjoint_db": _ratio_db(oracle, ours).tolist(),
            "median_abs_db": float(np.nanmedian(np.abs(_ratio_db(oracle, ours)))),
            "max_abs_db": float(np.nanmax(np.abs(_ratio_db(oracle, ours)))),
        }

    adjoint_surplus = np.divide(
        adjoint.total,
        adjoint.direct,
        out=np.full_like(adjoint.total, np.nan),
        where=adjoint.direct > 0.0,
    )
    sionna_surplus = np.divide(
        sionna.total,
        sionna.direct,
        out=np.full_like(sionna.total, np.nan),
        where=sionna.direct > 0.0,
    )
    residual = _ratio_db(sionna_surplus.mean(axis=0), adjoint_surplus.mean(axis=0))
    out["surplus"] = {
        "sionna_minus_adjoint_db": residual.tolist(),
        "median_abs_db": float(np.nanmedian(np.abs(residual))),
        "max_abs_db": float(np.nanmax(np.abs(residual))),
    }
    return out


def _ratio_db(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    numerator = np.asarray(numerator, dtype=np.float64)
    denominator = np.asarray(denominator, dtype=np.float64)
    ratio = np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 0.0)
    return np.where(ratio > 0.0, 10.0 * np.log10(ratio), np.nan)

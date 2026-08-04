"""Adjoint shoot and bounce estimator for the local transfer scalar.

Rays leave the observation point `S`, bounce until they escape the cropped
scene, and deposit their throughput into a bin indexed by the departure
direction `u_loc` and weighted by the external illumination density evaluated
at the exit direction `u_ext`. By the reciprocity dictionary of
MONOSTATIC_SBR.md section 2.3 the departure direction is the local arrival
direction, so no sign conversion is needed anywhere downstream.

What is accumulated is power, never amplitude. Section 2.8 of that document
shows why: the phase of an escaping path rotates at `k*|x_K - S|` radians per
radian of exit angle, so a publishable angular grid is five to seven orders of
magnitude too coarse to sum amplitudes in, and the failure is silent. Every
number this module returns is therefore a band averaged second moment.

Simplification against the design, stated rather than hidden: polarisation is
carried as the unpolarised power average of the two Fresnel coefficients
instead of a 2x2 Jones matrix. The coherency matrix is then approximated as
`C_S = K_S * P_u / 1`, isotropic in the transverse plane. This is exact for the
depolarised multi bounce tail and for the two closed form tests of section 11,
where the two polarisations are averaged anyway, and it loses the cross
polarisation ratio, which nothing downstream in this study consumes.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..illumination import IlluminationModel, fibonacci_sphere
from .observers import (
    TERMINATIONS as TERMINATIONS,
    BounceEvidenceTally,
    PathRecord as PathRecord,
    PathRecorder,
)
from .trace_kernel import (
    BatchObservers,
    EscapeDeposit,
    TraceAccumulators,
    deposit,
    range_to_source_shell,
    run_batch,
)


#: The bounce budget of this study, and the only place it is written down.
#: Everything that traces reads it from here rather than carrying its own
#: default, because the four values that used to be in circulation disagreed.
#:
#: Three is set by where the image evidence runs out, not by a convergence
#: threshold. The trace is adjoint, so the first surface interaction is the one
#: that scatters energy into the observation point, and it is by construction a
#: surface the panorama standing at that point can see. The second lands on the
#: facades of the same enclosed square, which the same panorama set also sees.
#: The third is the first that can plausibly land on a surface no panorama ever
#: observed. BOUNCE_BUDGET.md measures that claim rather than asserting it.
DEFAULT_MAX_BOUNCES = 3


@dataclass(frozen=True)
class TraceConfig:
    """Everything that changes the numbers, and nothing that does not."""

    frequency_hz: float = 15.0e9
    rays: int = 400_000
    local_cells: int = 512
    exit_bands: int = 18
    max_bounces: int = DEFAULT_MAX_BOUNCES
    #: One past the budget, so at the default budget roulette never fires.
    #: Roulette trades variance for work, and at three bounces there is no work
    #: to buy: it would kill a ray one iteration before the hard cap drops it
    #: anyway. Measured over 40 Korenmarkt standpoints and eight seeds each, the
    #: relative standard deviation of every chi agrees to three significant
    #: figures with roulette on and off, and off is four percent faster.
    #: BOUNCE_BUDGET.md carries the numbers. Roulette is unbiased whichever way
    #: this is set, so it never was and is not now what bounds the truncation.
    roulette_start: int = DEFAULT_MAX_BOUNCES + 1
    roulette_floor: float = 0.05
    ray_epsilon_m: float = 1.0e-3
    #: Charge each escaping ray for the distance it travelled, ``1 / l_K^2``.
    #:
    #: Off, which is how every published escape-weighted number was produced,
    #: an escaping ray is credited the moment it leaves the crop and no range
    #: appears anywhere. A bounced ray that travelled 120 m to reach the sky
    #: then counts exactly as much as a direct ray that travelled 30 m. Next
    #: event estimation has no such gap, because it divides by the range from
    #: the connection vertex to the rooftop point it connected to.
    #:
    #: This is the switch that tests whether that gap is the whole difference
    #: between the two answers. Everything the study reports is a ratio, so the
    #: constant in front of ``1 / l_K^2`` cancels and only the spread of path
    #: lengths matters. It is a diagnostic and not a third estimator: the source
    #: population is still at infinity, so the weight is a proxy for range and
    #: not a measurement of one.
    range_weighted_escape: bool = False
    seed: int = 0
    batch: int = 400_000

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class PointResult:
    """Reduced statistics for one observation point. No paths, by design."""

    origin: np.ndarray
    ground_z_m: float
    local_grid: np.ndarray
    local_solid_angle: float
    rho: dict[str, np.ndarray]  # illumination model -> (local_cells,) in sr^-1
    susceptibility: dict[str, float]  # illumination model -> chi, free space 1
    susceptibility_direct: dict[str, float]  # zero bounce only
    exit_profile: np.ndarray  # (exit_bands,) K_tot averaged over each band, free space 1
    exit_sin_edges: np.ndarray  # (exit_bands + 1,) equal solid angle band edges in sin(el)
    sky_fraction: float
    mean_bounces: float
    mean_excess_delay_ns: float
    escaped_fraction: float
    rays: int
    seconds: float
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def scalars(self) -> dict[str, float]:
        out: dict[str, float] = {
            "sky_fraction": self.sky_fraction,
            "mean_bounces": self.mean_bounces,
            "mean_excess_delay_ns": self.mean_excess_delay_ns,
            "escaped_fraction": self.escaped_fraction,
            "truncated_throughput_share": float(self.diagnostics.get("truncated_throughput_share", 0.0)),
        }
        for name, value in self.susceptibility.items():
            out[f"chi_{name}"] = value
        for name, value in self.susceptibility_direct.items():
            out[f"chi_{name}_direct"] = value
            if value > 0.0:
                out[f"multipath_gain_{name}"] = self.susceptibility[name] / value
        return out


def fresnel_power_reflectance(cos_incidence: np.ndarray, permittivity: np.ndarray) -> np.ndarray:
    """Unpolarised half-space power reflectance.

    ``permittivity`` is the complex relative permittivity with a negative
    imaginary part, the ITU-R P.2040-4 convention. Returns the mean of
    ``|Gamma_TE|**2`` and ``|Gamma_TM|**2``.
    """
    cos_i = np.clip(cos_incidence, 0.0, 1.0).astype(np.complex128)
    sin_sq = 1.0 - cos_i**2
    root = np.sqrt(permittivity - sin_sq)
    te = (cos_i - root) / (cos_i + root)
    tm = (permittivity * cos_i - root) / (permittivity * cos_i + root)
    return 0.5 * (np.abs(te) ** 2 + np.abs(tm) ** 2)


def specular_share(rms_height_m: np.ndarray, cos_incidence: np.ndarray, wavelength_m: float) -> np.ndarray:
    """Rayleigh coherent power fraction ``exp(-g**2)``, g = 4 pi s cos(th)/lam."""
    g = 4.0 * np.pi * rms_height_m * cos_incidence / wavelength_m
    return np.exp(-np.minimum(g * g, 60.0))


class SbrTracer:
    """Holds the accelerated geometry and the per class material parameters.

    ``geometry`` must expose ``intersect(origins, directions)`` returning
    ``(hit, distance, normal, face_index)``. Two implementations exist:
    :class:`MitsubaGeometry` for a real mesh and :class:`AnalyticGeometry` for
    the closed form validation cases, which have no mesh at all.
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
        self.wavelength_m = 299_792_458.0 / config.frequency_hz
        self.local_grid = fibonacci_sphere(config.local_cells)
        self.exit_sin_edges = np.linspace(-1.0, 1.0, config.exit_bands + 1)
        #: Where the far-field source population sits, used only by the range
        #: charge diagnostic. The mesh's own bounding radius, so it is the crop
        #: radius by construction and needs no second parameter to agree with.
        vertices = getattr(geometry, "vertices", None)
        self.source_shell_radius_m = (
            float(np.linalg.norm(np.asarray(vertices, dtype=np.float64), axis=1).max())
            if vertices is not None and len(vertices)
            else 250.0
        )

    def _fresnel_power_reflectance(self, cos_incidence: np.ndarray, permittivity: np.ndarray) -> np.ndarray:
        return fresnel_power_reflectance(cos_incidence, permittivity)

    def _specular_share(self, rms_height_m: np.ndarray, cos_incidence: np.ndarray) -> np.ndarray:
        return specular_share(rms_height_m, cos_incidence, self.wavelength_m)

    def trace(
        self,
        origin: np.ndarray,
        models: dict[str, IlluminationModel],
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
        recorder: PathRecorder | None = None,
        tally: BounceEvidenceTally | None = None,
        gather: Any = None,
    ) -> PointResult:
        """Shoot ``rays`` from ``origin`` and reduce them to a :class:`PointResult`.

        ``gather``, when given, is any object exposing ``begin(origin, count)``
        and ``vertex(index, position, incoming, normal, throughput, share,
        order, path_length, face)``. It is called once per surface interaction, and it
        is how :mod:`semantic_twin.transport.monostatic` reads the co-located
        return off the same rays that produce the adjoint transfer. Like
        ``recorder`` and ``tally`` it draws no random number and touches no
        accumulator, so a traced result is bit identical with one attached and
        without it.
        """
        cfg = self.config
        started = time.perf_counter()
        rng = np.random.default_rng(cfg.seed if seed is None else seed)
        local_solid_angle = 4.0 * np.pi / cfg.local_cells

        accumulators = TraceAccumulators.create(models, cfg.local_cells, cfg.exit_bands)
        remaining = cfg.rays
        while remaining > 0:
            count = min(cfg.batch, remaining)
            remaining -= count
            self._run_batch(
                origin,
                count,
                rng,
                models,
                accumulators.normalisations,
                accumulators.rho,
                accumulators.rho_direct,
                accumulators.cell_counts,
                accumulators.exit_power,
                accumulators.totals,
                recorder,
                tally,
                gather,
            )

        counts = np.maximum(accumulators.cell_counts, 1.0)
        for name in models:
            accumulators.rho[name] /= counts
            accumulators.rho_direct[name] /= counts
        exit_profile = accumulators.exit_power / (cfg.rays / cfg.exit_bands)

        susceptibility = {name: float(np.sum(accumulators.rho[name]) * local_solid_angle) for name in models}
        susceptibility_direct = {
            name: float(np.sum(accumulators.rho_direct[name]) * local_solid_angle) for name in models
        }
        totals = accumulators.totals
        escaped = totals["escaped"]
        return PointResult(
            origin=np.asarray(origin, dtype=np.float64),
            ground_z_m=float(ground_z_m),
            local_grid=self.local_grid,
            local_solid_angle=local_solid_angle,
            rho=accumulators.rho,
            susceptibility=susceptibility,
            susceptibility_direct=susceptibility_direct,
            exit_profile=exit_profile,
            exit_sin_edges=self.exit_sin_edges,
            sky_fraction=totals["zero_bounce"] / cfg.rays,
            mean_bounces=totals["bounce_sum"] / max(escaped, 1),
            mean_excess_delay_ns=(
                totals["delay_sum"] / totals["delay_weight"] * 1e9 / 299_792_458.0
                if totals["delay_weight"] > 0.0
                else 0.0
            ),
            escaped_fraction=escaped / cfg.rays,
            rays=cfg.rays,
            seconds=time.perf_counter() - started,
            diagnostics={
                "truncated_rays": totals["truncated"],
                "truncated_throughput_share": (
                    totals["truncated_throughput"] / totals["delay_weight"] if totals["delay_weight"] > 0.0 else 0.0
                ),
            },
        )

    def _run_batch(
        self,
        origin: np.ndarray,
        count: int,
        rng: np.random.Generator,
        models: dict[str, IlluminationModel],
        *batch_parts: Any,
    ) -> None:
        normalisations, rho, rho_direct, cell_counts, exit_power, totals, recorder, tally, gather = batch_parts
        accumulators = TraceAccumulators(
            normalisations,
            rho,
            rho_direct,
            cell_counts,
            exit_power,
            totals,
        )
        run_batch(
            self,
            origin,
            count,
            rng,
            models,
            accumulators,
            BatchObservers(recorder, tally, gather),
        )

    def _range_to_the_source_shell(
        self,
        last_vertex: np.ndarray,
        exit_direction: np.ndarray,
        path_length: np.ndarray,
    ) -> np.ndarray:
        """How far an escaping ray travelled to reach the sources, end to end.

        This cannot be the in-scene path length alone. A direct ray hits nothing
        by definition, so its recorded path length is zero, and dividing by it
        made every surplus come out at exactly 0.00 dB the first time this was
        run. What the ray actually travelled is the distance inside the crop
        plus the distance from where it left to where the sources are, and the
        sources are the far field, so they sit on a shell around the scene.

        The shell radius is the mesh's own bounding radius, so a direct ray from
        the head is charged roughly the crop radius and a ray that bounced twice
        across the square is charged that plus its detour. That difference is
        the whole point: it is what a range term prices and the escape estimator
        does not.
        """
        return range_to_source_shell(
            last_vertex,
            exit_direction,
            path_length,
            self.source_shell_radius_m,
            self.config.ray_epsilon_m,
        )

    def _deposit(
        self,
        index: np.ndarray,
        exit_direction: np.ndarray,
        *deposit_parts: Any,
    ) -> None:
        (
            throughput,
            cell,
            path_length,
            last_vertex,
            origin,
            bounces,
            models,
            normalisations,
            rho,
            rho_direct,
            exit_power,
            totals,
        ) = deposit_parts
        deposit(
            self,
            EscapeDeposit(
                index,
                exit_direction,
                throughput,
                cell,
                path_length,
                last_vertex,
                origin,
                bounces,
            ),
            models,
            TraceAccumulators(
                normalisations,
                rho,
                rho_direct,
                np.empty(0),
                exit_power,
                totals,
            ),
        )


#: One observation point of a sweep: where to stand, the pavement height under
#: it, and the seed that fixes every random draw made there.
Standpoint = tuple[np.ndarray, float, int]

#: Environment variables that make a worker process single threaded. Set in the
#: parent immediately before the pool is created, so the children inherit them
#: and the parent's own already loaded BLAS is left alone.
_SINGLE_THREAD_ENV = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)

_WORKER: dict[str, Any] = {}


def _worker_setup(tracer: SbrTracer, models: dict[str, IlluminationModel]) -> None:
    _WORKER["tracer"] = tracer
    _WORKER["models"] = models
    try:
        import drjit as dr

        dr.set_thread_count(1)
    except Exception:  # pragma: no cover - drjit is absent for the analytic geometries
        pass


def _worker_trace(item: tuple[int, np.ndarray, float, int]) -> tuple[int, PointResult]:
    row, origin, ground_z_m, seed = item
    result = _WORKER["tracer"].trace(origin, _WORKER["models"], ground_z_m=ground_z_m, seed=seed)
    return row, result


def trace_standpoints(
    tracer: SbrTracer,
    standpoints: Sequence[Standpoint],
    models: dict[str, IlluminationModel],
    *,
    workers: int | None = None,
) -> Iterator[tuple[int, PointResult]]:
    """Trace a sweep of observation points, yielding ``(row, result)`` in order.

    Standpoints do not talk to each other. Each one opens its own generator on
    its own seed, reads a scene nothing writes to, and reduces to its own
    counters, so which process runs which point cannot reach the numbers. That
    is the whole argument for running them at once, and it is why the results
    are the results of the serial loop bit for bit rather than to a tolerance.
    The test suite checks that against a real mesh rather than asserting it.

    Ordering is preserved, so a caller can keep streaming its rows to disk in
    sweep order and stay restartable. Each worker is made single threaded,
    because the estimator's own BLAS and Dr.Jit threading fight a process pool
    for the same cores and lose.

    ``workers`` of one, or a sweep of one point, runs in this process and starts
    no pool at all.
    """
    points = list(standpoints)
    count = os.cpu_count() or 1 if workers is None else int(workers)
    count = max(1, min(count, len(points)))
    if count == 1:
        for row, (origin, ground_z_m, seed) in enumerate(points):
            yield row, tracer.trace(origin, models, ground_z_m=ground_z_m, seed=seed)
        return

    items = [(row, origin, ground_z_m, seed) for row, (origin, ground_z_m, seed) in enumerate(points)]
    context = multiprocessing.get_context("spawn")
    saved = {name: os.environ.get(name) for name in _SINGLE_THREAD_ENV}
    for name in _SINGLE_THREAD_ENV:
        os.environ[name] = "1"
    try:
        pool = context.Pool(count, initializer=_worker_setup, initargs=(tracer, models))
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    try:
        yield from pool.imap(_worker_trace, items, chunksize=1)
    finally:
        pool.terminate()
        pool.join()

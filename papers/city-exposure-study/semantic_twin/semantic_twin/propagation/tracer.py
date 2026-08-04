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

from ..illumination import IlluminationModel, fibonacci_sphere, nearest_cell, sample_sphere


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

#: How a recorded ray stopped. ``sky`` escaped the crop, ``roulette`` was killed
#: by Russian roulette while still carrying throughput, ``truncated`` was still
#: travelling when ``max_bounces`` ran out.
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

    Recording changes no random draw and no accumulator, so a traced result is
    bit identical with the recorder attached and without it. The test suite
    asserts that rather than trusting it.
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

    Attaching a tally consumes no random draw and touches no accumulator, so a
    traced result is bit identical with it and without it.

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
    """Unpolarised half space power reflectance.

    ``permittivity`` is the complex relative permittivity with a negative
    imaginary part, the ITU-R P.2040-4 convention. Returns the mean of
    ``|Gamma_TE|**2`` and ``|Gamma_TM|**2``, which is the correct power weight
    for an unpolarised or fully depolarised field and is exactly what the two
    closed form checks of section 11.1 average over.
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


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """``np.cross`` for stacks of 3 vectors, written out.

    Term for term what ``np.cross`` evaluates, so the result is the same to the
    last bit. What it skips is the shape negotiation ``np.cross`` does on every
    call, which at 400k rows is most of what the call costs.
    """
    out = np.empty(a.shape, dtype=np.float64)
    a0, a1, a2 = a[:, 0], a[:, 1], a[:, 2]
    b0, b1, b2 = b[:, 0], b[:, 1], b[:, 2]
    np.multiply(a1, b2, out=out[:, 0])
    out[:, 0] -= a2 * b1
    np.multiply(a2, b0, out=out[:, 1])
    out[:, 1] -= a0 * b2
    np.multiply(a0, b1, out=out[:, 2])
    out[:, 2] -= a1 * b0
    return out


def _row_norms(a: np.ndarray) -> np.ndarray:
    """``np.linalg.norm(a, axis=1, keepdims=True)``, in the same summation order."""
    total = a[:, 0] * a[:, 0]
    total = total + a[:, 1] * a[:, 1]
    total = total + a[:, 2] * a[:, 2]
    return np.sqrt(total)[:, None]


_UP = np.array([[0.0, 0.0, 1.0]])
_ACROSS = np.array([[1.0, 0.0, 0.0]])


def _cosine_hemisphere(normals: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Cosine weighted directions about ``normals``."""
    count = normals.shape[0]
    u1 = rng.random(count)
    u2 = rng.random(count)
    radius = np.sqrt(u1)
    phi = 2.0 * np.pi * u2
    x = radius * np.cos(phi)
    y = radius * np.sin(phi)
    z = np.sqrt(np.maximum(0.0, 1.0 - u1))
    helper = np.where(np.abs(normals[:, 2:3]) < 0.9, _UP, _ACROSS)
    tangent = _cross(helper, normals)
    tangent /= _row_norms(tangent)
    bitangent = _cross(normals, tangent)
    return x[:, None] * tangent + y[:, None] * bitangent + z[:, None] * normals


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
        is how :mod:`semantic_twin.propagation.monostatic` reads the co-located
        return off the same rays that produce the adjoint transfer. Like
        ``recorder`` and ``tally`` it draws no random number and touches no
        accumulator, so a traced result is bit identical with one attached and
        without it.
        """
        cfg = self.config
        started = time.perf_counter()
        rng = np.random.default_rng(cfg.seed if seed is None else seed)
        local_solid_angle = 4.0 * np.pi / cfg.local_cells

        normalisations = {name: model.normalisation() for name, model in models.items()}
        rho = {name: np.zeros(cfg.local_cells) for name in models}
        rho_direct = {name: np.zeros(cfg.local_cells) for name in models}
        cell_counts = np.zeros(cfg.local_cells)
        exit_power = np.zeros(cfg.exit_bands)

        totals = {
            "escaped": 0,
            "bounce_sum": 0.0,
            "delay_sum": 0.0,
            "delay_weight": 0.0,
            "zero_bounce": 0,
            "truncated": 0,
            "truncated_throughput": 0.0,
        }
        remaining = cfg.rays
        while remaining > 0:
            count = min(cfg.batch, remaining)
            remaining -= count
            self._run_batch(
                origin,
                count,
                rng,
                models,
                normalisations,
                rho,
                rho_direct,
                cell_counts,
                exit_power,
                totals,
                recorder,
                tally,
                gather,
            )

        counts = np.maximum(cell_counts, 1.0)
        for name in models:
            rho[name] /= counts
            rho_direct[name] /= counts
        exit_profile = exit_power / (cfg.rays / cfg.exit_bands)

        susceptibility = {name: float(np.sum(rho[name]) * local_solid_angle) for name in models}
        susceptibility_direct = {name: float(np.sum(rho_direct[name]) * local_solid_angle) for name in models}
        escaped = totals["escaped"]
        return PointResult(
            origin=np.asarray(origin, dtype=np.float64),
            ground_z_m=float(ground_z_m),
            local_grid=self.local_grid,
            local_solid_angle=local_solid_angle,
            rho=rho,
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
        normalisations: dict[str, float],
        rho: dict[str, np.ndarray],
        rho_direct: dict[str, np.ndarray],
        cell_counts: np.ndarray,
        exit_power: np.ndarray,
        totals: dict[str, float],
        recorder: PathRecorder | None = None,
        tally: BounceEvidenceTally | None = None,
        gather: Any = None,
    ) -> None:
        cfg = self.config
        direction = sample_sphere(count, rng)
        cell = nearest_cell(direction, self.local_grid)
        np.add.at(cell_counts, cell, 1.0)
        if recorder is not None:
            recorder.begin(origin, count)
        if gather is not None:
            gather.begin(origin, count)

        position = np.tile(np.asarray(origin, dtype=np.float64), (count, 1))
        throughput = np.ones(count)
        path_length = np.zeros(count)
        last_vertex = position.copy()
        bounces = np.zeros(count, dtype=np.int32)
        alive = np.arange(count)

        # The live slice of every per ray array is read several times a bounce,
        # by the intersector, the deposit, the reflection and whatever observer
        # is attached. Each read used to be its own gather out of the full
        # length array. They are gathered once here instead and the copies are
        # shared, which is the same arithmetic on the same values in the same
        # order.
        for depth in range(cfg.max_bounces + 1):
            if alive.size == 0:
                break
            live_position = position[alive]
            live_direction = direction[alive]
            live_throughput = throughput[alive]
            live_bounces = bounces[alive]
            hit, distance, normal, face = self.geometry.intersect(
                live_position + cfg.ray_epsilon_m * live_direction, live_direction
            )
            escaped_local = ~hit
            if np.any(escaped_local):
                index = alive[escaped_local]
                self._deposit(
                    index,
                    live_direction[escaped_local],
                    live_throughput[escaped_local],
                    cell[index],
                    path_length[index],
                    last_vertex[index],
                    np.asarray(origin, dtype=np.float64),
                    live_bounces[escaped_local],
                    models,
                    normalisations,
                    rho,
                    rho_direct,
                    exit_power,
                    totals,
                )
                if recorder is not None:
                    recorder.close(
                        index,
                        live_position[escaped_local],
                        live_direction[escaped_local],
                        live_bounces[escaped_local],
                        "sky",
                    )
            alive = alive[hit]
            if alive.size == 0:
                break
            live_position = live_position[hit]
            live_direction = live_direction[hit]
            live_throughput = live_throughput[hit]
            live_bounces = live_bounces[hit]
            if depth == cfg.max_bounces:
                # ``max_bounces`` counts surface interactions, so the escapes of
                # the last permitted bounce are deposited above and only the
                # rays still travelling are dropped here.
                totals["truncated"] += int(alive.size)
                totals["truncated_throughput"] += float(live_throughput.sum())
                if recorder is not None:
                    recorder.close(alive, live_position, live_direction, live_bounces, "truncated")
                break
            distance = distance[hit]
            normal = normal[hit]
            face = face[hit] if face is not None else None

            live_position = live_position + (distance + cfg.ray_epsilon_m)[:, None] * live_direction
            position[alive] = live_position
            path_length[alive] += distance
            last_vertex[alive] = live_position
            live_bounces += 1
            bounces[alive] = live_bounces

            incoming = live_direction
            facing = np.sign(-np.einsum("ij,ij->i", incoming, normal))
            facing[facing == 0.0] = 1.0
            normal = normal * facing[:, None]
            cos_i = np.clip(-np.einsum("ij,ij->i", incoming, normal), 0.0, 1.0)

            if self.face_class is not None and face is not None:
                klass = self.face_class[face]
            else:
                klass = np.zeros(alive.size, dtype=np.int64)
            reflectance = fresnel_power_reflectance(cos_i, self.permittivity[klass])
            share = specular_share(self.rms_height_m[klass], cos_i, self.wavelength_m)

            if tally is not None and face is not None:
                tally.record(depth, face, live_throughput)

            live_throughput = live_throughput * reflectance
            throughput[alive] = live_throughput
            if recorder is not None:
                recorder.advance(alive, live_position, live_throughput, klass)
            if gather is not None:
                gather.vertex(
                    alive,
                    live_position,
                    incoming,
                    normal,
                    live_throughput,
                    share,
                    live_bounces,
                    path_length[alive],
                    face,
                )
            take_specular = rng.random(alive.size) < share
            mirror = incoming - 2.0 * np.einsum("ij,ij->i", incoming, normal)[:, None] * normal
            diffuse = _cosine_hemisphere(normal, rng)
            new_direction = np.where(take_specular[:, None], mirror, diffuse)
            new_direction /= _row_norms(new_direction)
            direction[alive] = new_direction

            if depth + 1 >= cfg.roulette_start:
                survive_probability = np.clip(live_throughput, cfg.roulette_floor, 1.0)
                survive = rng.random(alive.size) < survive_probability
                throughput[alive] = live_throughput / survive_probability
                if recorder is not None:
                    killed = alive[~survive]
                    recorder.close(
                        killed, position[killed], new_direction[~survive], live_bounces[~survive], "roulette"
                    )
                alive = alive[survive]

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
        radius = self.source_shell_radius_m
        # Where the exit ray crosses the shell: solve |p + t u| = R for t > 0.
        along = np.einsum("ij,ij->i", last_vertex, exit_direction)
        square = np.einsum("ij,ij->i", last_vertex, last_vertex)
        inside = np.maximum(along**2 - square + radius**2, 0.0)
        out = np.maximum(-along + np.sqrt(inside), 0.0)
        return np.maximum(path_length + out, self.config.ray_epsilon_m)

    def _deposit(
        self,
        index: np.ndarray,
        exit_direction: np.ndarray,
        throughput: np.ndarray,
        cell: np.ndarray,
        path_length: np.ndarray,
        last_vertex: np.ndarray,
        origin: np.ndarray,
        bounces: np.ndarray,
        models: dict[str, IlluminationModel],
        normalisations: dict[str, float],
        rho: dict[str, np.ndarray],
        rho_direct: dict[str, np.ndarray],
        exit_power: np.ndarray,
        totals: dict[str, float],
    ) -> None:
        zero_bounce = bounces == 0
        weight = throughput
        if self.config.range_weighted_escape:
            weight = throughput / self._range_to_the_source_shell(last_vertex, exit_direction, path_length) ** 2
        for name, model in models.items():
            contribution = weight * model.density(exit_direction, normalisations[name])
            np.add.at(rho[name], cell, contribution)
            if np.any(zero_bounce):
                np.add.at(rho_direct[name], cell[zero_bounce], contribution[zero_bounce])
        band = np.clip(
            np.searchsorted(self.exit_sin_edges, exit_direction[:, 2], side="right") - 1,
            0,
            exit_power.size - 1,
        )
        np.add.at(exit_power, band, throughput)

        # Excess path of MONOSTATIC_SBR.md section 2.4: Delta = l_K - u_e.(x_K - S).
        excess = path_length - np.einsum("ij,ij->i", exit_direction, last_vertex - origin)
        totals["escaped"] += int(index.size)
        totals["bounce_sum"] += float(bounces.sum())
        totals["delay_sum"] += float(np.sum(throughput * excess))
        totals["delay_weight"] += float(np.sum(throughput))
        totals["zero_bounce"] += int(np.count_nonzero(zero_bounce))


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

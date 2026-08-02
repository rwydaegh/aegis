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

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .directions import IlluminationModel, fibonacci_sphere, nearest_cell, sample_sphere


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


@dataclass(frozen=True)
class TraceConfig:
    """Everything that changes the numbers, and nothing that does not."""

    frequency_hz: float = 15.0e9
    rays: int = 400_000
    local_cells: int = 512
    exit_bands: int = 18
    max_bounces: int = 12
    roulette_start: int = 3
    roulette_floor: float = 0.05
    ray_epsilon_m: float = 1.0e-3
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
    helper = np.where(np.abs(normals[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    tangent = np.cross(helper, normals)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    bitangent = np.cross(normals, tangent)
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

    def trace(
        self,
        origin: np.ndarray,
        models: dict[str, IlluminationModel],
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
        recorder: PathRecorder | None = None,
    ) -> PointResult:
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
    ) -> None:
        cfg = self.config
        direction = sample_sphere(count, rng)
        cell = nearest_cell(direction, self.local_grid)
        np.add.at(cell_counts, cell, 1.0)
        if recorder is not None:
            recorder.begin(origin, count)

        position = np.tile(np.asarray(origin, dtype=np.float64), (count, 1))
        throughput = np.ones(count)
        path_length = np.zeros(count)
        last_vertex = position.copy()
        bounces = np.zeros(count, dtype=np.int32)
        alive = np.arange(count)

        for depth in range(cfg.max_bounces + 1):
            if alive.size == 0:
                break
            hit, distance, normal, face = self.geometry.intersect(
                position[alive] + cfg.ray_epsilon_m * direction[alive], direction[alive]
            )
            escaped_local = ~hit
            if np.any(escaped_local):
                index = alive[escaped_local]
                self._deposit(
                    index,
                    direction[index],
                    throughput[index],
                    cell[index],
                    path_length[index],
                    last_vertex[index],
                    np.asarray(origin, dtype=np.float64),
                    bounces[index],
                    models,
                    normalisations,
                    rho,
                    rho_direct,
                    exit_power,
                    totals,
                )
                if recorder is not None:
                    recorder.close(index, position[index], direction[index], bounces[index], "sky")
            alive = alive[hit]
            if alive.size == 0:
                break
            if depth == cfg.max_bounces:
                # ``max_bounces`` counts surface interactions, so the escapes of
                # the last permitted bounce are deposited above and only the
                # rays still travelling are dropped here.
                totals["truncated"] += int(alive.size)
                totals["truncated_throughput"] += float(throughput[alive].sum())
                if recorder is not None:
                    recorder.close(alive, position[alive], direction[alive], bounces[alive], "truncated")
                break
            distance = distance[hit]
            normal = normal[hit]
            face = face[hit] if face is not None else None

            position[alive] = position[alive] + (distance + cfg.ray_epsilon_m)[:, None] * direction[alive]
            path_length[alive] += distance
            last_vertex[alive] = position[alive]
            bounces[alive] += 1

            incoming = direction[alive]
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

            throughput[alive] *= reflectance
            if recorder is not None:
                recorder.advance(alive, position[alive], throughput[alive], klass)
            take_specular = rng.random(alive.size) < share
            mirror = incoming - 2.0 * np.einsum("ij,ij->i", incoming, normal)[:, None] * normal
            diffuse = _cosine_hemisphere(normal, rng)
            new_direction = np.where(take_specular[:, None], mirror, diffuse)
            new_direction /= np.linalg.norm(new_direction, axis=1, keepdims=True)
            direction[alive] = new_direction

            if depth + 1 >= cfg.roulette_start:
                survive_probability = np.clip(throughput[alive], cfg.roulette_floor, 1.0)
                survive = rng.random(alive.size) < survive_probability
                throughput[alive] /= survive_probability
                if recorder is not None:
                    killed = alive[~survive]
                    recorder.close(killed, position[killed], direction[killed], bounces[killed], "roulette")
                alive = alive[survive]

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
        for name, model in models.items():
            contribution = throughput * model.density(exit_direction, normalisations[name])
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

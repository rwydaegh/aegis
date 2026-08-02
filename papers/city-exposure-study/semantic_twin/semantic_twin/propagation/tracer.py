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
    ) -> None:
        cfg = self.config
        direction = sample_sphere(count, rng)
        cell = nearest_cell(direction, self.local_grid)
        np.add.at(cell_counts, cell, 1.0)

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
            alive = alive[hit]
            if alive.size == 0:
                break
            if depth == cfg.max_bounces:
                # ``max_bounces`` counts surface interactions, so the escapes of
                # the last permitted bounce are deposited above and only the
                # rays still travelling are dropped here.
                totals["truncated"] += int(alive.size)
                totals["truncated_throughput"] += float(throughput[alive].sum())
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

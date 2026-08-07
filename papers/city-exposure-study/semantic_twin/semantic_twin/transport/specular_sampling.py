"""Counter-sampled CPU reference for one finite specular reflection."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from ..illumination.sources import normalized_source_weights
from .specular import OneBounceSpecularTransport

_MASK_64 = (1 << 64) - 1
_UINT53_SCALE = 1.0 / (1 << 53)
SPECULAR_FACE_PROPOSAL = "0.9_triangle_area_plus_0.1_uniform_full_support_v1"
SPECULAR_SOURCE_PROPOSAL = "existing_normalized_discrete_source_weights_v1"
SPECULAR_COUNTER_GENERATOR = "splitmix64_seed_counter_dimension_v1"
SPECULAR_SOURCE_COUNTER_DIMENSION = 0
SPECULAR_FACE_COUNTER_DIMENSION = 1


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _positive_integer(value: int, name: str) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_)) or int(value) < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _counter_uniform(seed: int, counters: np.ndarray, dimension: int) -> np.ndarray:
    """SplitMix64 draws keyed only by ``(seed, counter, dimension)``.

    This deliberately does not carry generator state. A later device port can
    assign the same two dimensions to source and reflector draws, and splitting
    a CPU call at a counter boundary cannot move either stream.
    """
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, (bool, np.bool_)):
        raise TypeError("seed must be an integer")
    counter = np.asarray(counters, dtype=np.uint64)
    seed_word = int(seed) & _MASK_64
    seed_word = (seed_word + 0x9E3779B97F4A7C15) & _MASK_64
    seed_word = ((seed_word ^ (seed_word >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    seed_word = ((seed_word ^ (seed_word >> 27)) * 0x94D049BB133111EB) & _MASK_64
    seed_word ^= seed_word >> 31
    dimension_word = np.uint64(((int(dimension) + 1) * 0xD1B54A32D192ED03) & _MASK_64)
    with np.errstate(over="ignore"):
        value = (counter ^ np.uint64(seed_word) ^ dimension_word) + np.uint64(0x9E3779B97F4A7C15)
        value = (value ^ (value >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        value = (value ^ (value >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        value ^= value >> np.uint64(31)
    return (value >> np.uint64(11)).astype(np.float64) * _UINT53_SCALE


def _draw_categorical(probability: np.ndarray, uniform: np.ndarray) -> np.ndarray:
    cumulative = np.cumsum(probability, dtype=np.float64)
    cumulative[-1] = 1.0
    return np.searchsorted(cumulative, uniform, side="right").astype(np.int64)


def _face_proposal(transport: OneBounceSpecularTransport) -> tuple[np.ndarray, np.ndarray]:
    triangle = transport.surfaces.triangles
    if triangle.shape[0] == 0:
        empty = np.empty(0, dtype=np.float64)
        return empty, empty
    area = 0.5 * np.linalg.norm(
        np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]),
        axis=1,
    )
    count = area.size
    probability = 0.9 * area / np.sum(area, dtype=np.float64) + 0.1 / count
    return area, probability


def _summation_bound(values: np.ndarray, expected: float) -> float:
    """Conservative float64 pairwise-reduction error bound for positive masses."""
    count = max(int(values.size), 1)
    scale = max(float(np.sum(np.abs(values), dtype=np.float64)), abs(float(expected)), np.finfo(np.float64).tiny)
    reduction_depth = max(int(np.ceil(np.log2(count))), 1)
    return 16.0 * np.finfo(np.float64).eps * reduction_depth * scale


@dataclass(frozen=True)
class SampledSpecularDiagnostics:
    """Work, acceptance, uncertainty, and proposal evidence for one estimate."""

    seed: int
    counter_start: int
    counter_stop: int
    endpoints: int
    samples_per_endpoint: int
    trials: int
    source_count: int
    source_support: int
    face_count: int
    surfaces_support_complete: bool
    candidates: int
    solver_calls: int
    geometric: int
    visible: int
    path_accepted: int
    accepted: int
    estimated_variance: float
    standard_error: float
    variance_available: bool
    contribution_ess: float
    face_proposal_ess: float
    face_probability_min: float
    face_probability_max: float
    face_probability_sha256: str
    source_probability_sha256: str
    face_proposal: str
    source_proposal: str
    counter_generator: str
    source_counter_dimension: int
    face_counter_dimension: int
    seconds: float
    maximum_completed_specular_order: int = 1
    estimator_term: str = "one_reflection_source_nearest_specular"

    @property
    def acceptance(self) -> float:
        return self.accepted / self.trials if self.trials else 0.0

    def as_dict(self) -> dict[str, int | float | bool | str]:
        result = dict(self.__dict__)
        result["acceptance"] = self.acceptance
        return result


@dataclass(frozen=True)
class SampledSpecularResult:
    """Importance-corrected scalar, order bins, atoms, and raw trial scores."""

    transfer: float
    by_order: np.ndarray
    k_hat: np.ndarray
    mass: np.ndarray
    trial_transfer: np.ndarray
    drawn_source_index: np.ndarray
    drawn_surface_index: np.ndarray
    drawn_face_index: np.ndarray
    diagnostics: SampledSpecularDiagnostics

    def __post_init__(self) -> None:
        by_order = np.asarray(self.by_order, dtype=np.float64)
        direction = np.asarray(self.k_hat, dtype=np.float64)
        mass = np.asarray(self.mass, dtype=np.float64)
        trial = np.asarray(self.trial_transfer, dtype=np.float64)
        source = np.asarray(self.drawn_source_index, dtype=np.int64)
        surface = np.asarray(self.drawn_surface_index, dtype=np.int64)
        face = np.asarray(self.drawn_face_index, dtype=np.int64)
        if by_order.ndim != 1 or by_order.size < 2:
            raise ValueError("by_order must include zero and one-reflection bins")
        if direction.shape != (mass.size, 3):
            raise ValueError("directional masses must match k_hat")
        if trial.shape != (self.diagnostics.trials,):
            raise ValueError("trial_transfer must match diagnostic trials")
        if source.shape != trial.shape or surface.shape != trial.shape or face.shape != trial.shape:
            raise ValueError("draw indices must match trial_transfer")
        if np.any(~np.isfinite(by_order)) or np.any(~np.isfinite(direction)) or np.any(~np.isfinite(mass)):
            raise ValueError("sampled specular deposits must be finite")
        if np.any(~np.isfinite(trial)) or np.any(by_order < 0.0) or np.any(mass < 0.0) or np.any(trial < 0.0):
            raise ValueError("sampled specular deposits must be finite and nonnegative")
        if direction.size and not np.allclose(np.linalg.norm(direction, axis=1), 1.0, rtol=1.0e-10, atol=1.0e-10):
            raise ValueError("sampled specular directions must be unit length")
        if abs(float(np.sum(mass, dtype=np.float64)) - self.transfer) > _summation_bound(mass, self.transfer):
            raise ValueError("directional masses must sum to scalar transfer")
        if float(np.sum(by_order, dtype=np.float64)) != self.transfer:
            raise ValueError("order deposits must sum to scalar transfer")
        if by_order[0] != 0.0:
            raise ValueError("sampled specular transport cannot deposit into the zero-specular class")
        object.__setattr__(self, "by_order", by_order)
        object.__setattr__(self, "k_hat", direction)
        object.__setattr__(self, "mass", mass)
        object.__setattr__(self, "trial_transfer", trial)
        object.__setattr__(self, "drawn_source_index", source)
        object.__setattr__(self, "drawn_surface_index", surface)
        object.__setattr__(self, "drawn_face_index", face)

    @property
    def total(self) -> float:
        return self.transfer

    @property
    def scalar(self) -> float:
        return self.transfer

    @property
    def confidence_interval_95(self) -> tuple[float, float]:
        radius = 1.959963984540054 * self.diagnostics.standard_error
        return self.transfer - radius, self.transfer + radius


class SampledOneBounceSpecularEstimator:
    """Unbiased one-face estimate conditional on the discrete source measure.

    A trial draws source ``s`` from its existing normalized probability ``p_s``
    and finite reflector ``f`` from

    ``q_f = 0.9 area_f / sum(area) + 0.1 / F``.

    The exact one-face solver receives endpoint weight ``1 / q_f``. There is no
    ``1 / p_s`` and no extra ``p_s`` because drawing the source already performs
    that expectation. The face correction is consequently applied exactly once.

    This experimental CPU reference sends paired trial-face indices through the
    exact image solver in large contiguous chunks. A device port should preserve
    this result and counter contract rather than reproduce host control flow.
    """

    def __init__(self, transport: OneBounceSpecularTransport, sources: Any) -> None:
        self.transport = transport
        self.sources = sources
        self.source_positions = np.asarray(sources.sites(), dtype=np.float64)
        if self.source_positions.ndim != 2 or self.source_positions.shape[1] != 3:
            raise ValueError("source sites must have shape (N, 3)")
        if np.any(~np.isfinite(self.source_positions)):
            raise ValueError("source sites must be finite")
        self.source_probability = normalized_source_weights(sources)
        self.face_area, self.face_probability = _face_proposal(transport)

    @property
    def ready(self) -> bool:
        """Whether both sampled supports contain at least one positive member."""
        return bool(self.source_positions.shape[0] and self.face_probability.size)

    def sampling_identity(self) -> dict[str, Any]:
        """Seal the proposals, counter dimensions, and sampled support."""
        surfaces = self.transport.surfaces
        return {
            "status": "experimental_opt_in",
            "face_proposal": SPECULAR_FACE_PROPOSAL,
            "source_proposal": SPECULAR_SOURCE_PROPOSAL,
            "counter_generator": SPECULAR_COUNTER_GENERATOR,
            "source_counter_dimension": SPECULAR_SOURCE_COUNTER_DIMENSION,
            "face_counter_dimension": SPECULAR_FACE_COUNTER_DIMENSION,
            "source_count": int(self.source_probability.size),
            "source_support": int(np.count_nonzero(self.source_probability)),
            "source_probability_sha256": _array_sha256(self.source_probability),
            "face_count": int(self.face_probability.size),
            "face_probability_sha256": _array_sha256(self.face_probability),
            "surface_support_complete": bool(surfaces.support_complete),
            "surface_scene_face_count": int(surfaces.scene_face_count),
            "surface_construction": str(surfaces.construction),
        }

    def estimate(
        self,
        receiver: np.ndarray,
        *,
        samples: int,
        seed: int,
        counter_start: int = 0,
    ) -> SampledSpecularResult:
        """Estimate all-specular order one at one receiver for oracle checks."""
        point = np.asarray(receiver, dtype=np.float64)
        if point.shape != (3,) or np.any(~np.isfinite(point)):
            raise ValueError("receiver must be one finite three-vector")
        return self._estimate(
            point[None, :],
            samples_per_endpoint=samples,
            seed=seed,
            counter_start=counter_start,
        )

    def estimate_suffix(
        self,
        vertices: np.ndarray,
        normals: np.ndarray,
        diffuse_lobe: np.ndarray,
        arrival_k_hat: np.ndarray,
        base_order: np.ndarray,
        *,
        samples_per_vertex: int,
        seed: int,
        counter_start: int = 0,
    ) -> SampledSpecularResult:
        """Estimate one source-nearest mirror suffix after each diffuse vertex.

        ``diffuse_lobe`` is the caller-owned ``throughput * (1-share) / pi``.
        The returned direction is the caller-provided original receiver arrival,
        not the local source-to-vertex specular leg. Every deposit is placed at
        ``base_order + 1``, leaving the zero-specular diffuse class untouched.
        """
        vertex = np.asarray(vertices, dtype=np.float64)
        normal = np.asarray(normals, dtype=np.float64)
        lobe = np.asarray(diffuse_lobe, dtype=np.float64)
        arrival = np.asarray(arrival_k_hat, dtype=np.float64)
        order = np.asarray(base_order, dtype=np.int64)
        count = vertex.shape[0] if vertex.ndim == 2 else -1
        if vertex.shape != (count, 3) or normal.shape != (count, 3) or arrival.shape != (count, 3):
            raise ValueError("vertices, normals, and arrival_k_hat must have shape (N, 3)")
        if lobe.shape != (count,) or order.shape != (count,):
            raise ValueError("diffuse_lobe and base_order must match vertices")
        if np.any(~np.isfinite(vertex)) or np.any(~np.isfinite(normal)) or np.any(~np.isfinite(arrival)):
            raise ValueError("suffix geometry and directions must be finite")
        if np.any(~np.isfinite(lobe)) or np.any(lobe < 0.0):
            raise ValueError("diffuse_lobe must be finite and nonnegative")
        if np.any(order < 1):
            raise ValueError("source-nearest specular suffixes require a prior diffuse interaction")
        for value, name in ((normal, "normals"), (arrival, "arrival_k_hat")):
            if value.size and not np.allclose(np.linalg.norm(value, axis=1), 1.0, rtol=1.0e-10, atol=1.0e-10):
                raise ValueError(f"{name} must contain unit vectors")
        return self._estimate(
            vertex,
            samples_per_endpoint=samples_per_vertex,
            seed=seed,
            counter_start=counter_start,
            normals=normal,
            diffuse_lobe=lobe,
            arrival_k_hat=arrival,
            base_order=order,
        )

    def _estimate(
        self,
        endpoints: np.ndarray,
        *,
        samples_per_endpoint: int,
        seed: int,
        counter_start: int,
        normals: np.ndarray | None = None,
        diffuse_lobe: np.ndarray | None = None,
        arrival_k_hat: np.ndarray | None = None,
        base_order: np.ndarray | None = None,
    ) -> SampledSpecularResult:
        started = time.perf_counter()
        samples = _positive_integer(samples_per_endpoint, "samples_per_endpoint")
        counter_start, trials, counter, endpoint_index = self._trial_layout(endpoints.shape[0], samples, counter_start)
        source_draw, surface_draw, face_draw = self._trial_draws(seed, counter, trials)
        (
            trial_transfer,
            atom_trial,
            atom_direction,
            atom_contribution,
            atom_order,
            solver_counts,
        ) = self._solve_trial_chunks(
            endpoints,
            endpoint_index,
            source_draw,
            surface_draw,
            trials,
            normals,
            diffuse_lobe,
            arrival_k_hat,
            base_order,
        )
        direction, contribution, order = self._reduce_atoms(
            atom_trial,
            atom_direction,
            atom_contribution,
            atom_order,
        )
        transfer, by_order, mass = self._reduce_mass(contribution, order, samples)
        statistics = self._sample_statistics(trial_transfer, endpoints.shape[0], samples)
        diagnostics = self._sampled_diagnostics(
            seed,
            counter_start,
            endpoints.shape[0],
            samples,
            trials,
            solver_counts,
            contribution.size,
            statistics,
            started,
        )
        return SampledSpecularResult(
            transfer,
            by_order,
            direction,
            mass,
            trial_transfer,
            source_draw,
            surface_draw,
            face_draw,
            diagnostics,
        )

    @staticmethod
    def _trial_layout(
        endpoint_count: int,
        samples: int,
        counter_start: int,
    ) -> tuple[int, int, np.ndarray, np.ndarray]:
        if not isinstance(counter_start, (int, np.integer)) or isinstance(counter_start, (bool, np.bool_)):
            raise TypeError("counter_start must be an integer")
        counter_start = int(counter_start)
        if counter_start < 0:
            raise ValueError("counter_start must be nonnegative")
        trials = endpoint_count * samples
        if counter_start + trials > 1 << 64:
            raise ValueError("counter range exceeds uint64 support")
        counter = counter_start + np.arange(trials, dtype=np.uint64)
        endpoint_index = np.repeat(np.arange(endpoint_count, dtype=np.int64), samples)
        return counter_start, trials, counter, endpoint_index

    def _trial_draws(
        self,
        seed: int,
        counter: np.ndarray,
        trials: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self.ready and trials:
            source_draw = _draw_categorical(
                self.source_probability,
                _counter_uniform(seed, counter, SPECULAR_SOURCE_COUNTER_DIMENSION),
            )
            surface_draw = _draw_categorical(
                self.face_probability,
                _counter_uniform(seed, counter, SPECULAR_FACE_COUNTER_DIMENSION),
            )
            face_draw = self.transport.surfaces.face_index[surface_draw]
        else:
            source_draw = np.full(trials, -1, dtype=np.int64)
            surface_draw = np.full(trials, -1, dtype=np.int64)
            face_draw = np.full(trials, -1, dtype=np.int64)
        return source_draw, surface_draw, face_draw

    def _solve_trial_chunks(
        self,
        endpoints: np.ndarray,
        endpoint_index: np.ndarray,
        source_draw: np.ndarray,
        surface_draw: np.ndarray,
        trials: int,
        normals: np.ndarray | None,
        diffuse_lobe: np.ndarray | None,
        arrival_k_hat: np.ndarray | None,
        base_order: np.ndarray | None,
    ) -> tuple[
        np.ndarray,
        list[np.ndarray],
        list[np.ndarray],
        list[np.ndarray],
        list[np.ndarray],
        tuple[int, int, int, int],
    ]:
        trial_transfer = np.zeros(trials, dtype=np.float64)
        atom_direction: list[np.ndarray] = []
        atom_contribution: list[np.ndarray] = []
        atom_order: list[np.ndarray] = []
        atom_trial: list[np.ndarray] = []
        solver_calls = geometric = visible = path_accepted = 0
        if self.ready and trials:
            chunk_size = min(self.transport.candidate_chunk, self.transport.candidate_budget)
            for start in range(0, trials, chunk_size):
                solver_calls += 1
                trial_index = np.arange(start, min(start + chunk_size, trials), dtype=np.int64)
                endpoint = endpoint_index[trial_index]
                surface = surface_draw[trial_index]
                paths = self.transport.solve_paired_surfaces(
                    self.source_positions[source_draw[trial_index]],
                    endpoints[endpoint],
                    surface,
                    endpoint_weight=1.0 / self.face_probability[surface],
                    source_index=source_draw[trial_index],
                )
                geometric += paths.diagnostics.geometric
                visible += paths.diagnostics.visible
                path_accepted += paths.diagnostics.accepted
                if paths.transfer.size == 0:
                    continue
                accepted_trial = trial_index[paths.endpoint_index]
                accepted_endpoint = endpoint_index[accepted_trial]
                contribution = paths.transfer.copy()
                if normals is None:
                    direction = paths.k_hat
                    order = np.ones(contribution.size, dtype=np.int64)
                else:
                    lobe = cast(np.ndarray, diffuse_lobe)
                    arrival = cast(np.ndarray, arrival_k_hat)
                    order_base = cast(np.ndarray, base_order)
                    cosine = np.einsum("ij,ij->i", -paths.k_hat, normals[accepted_endpoint])
                    contribution *= lobe[accepted_endpoint] * np.maximum(cosine, 0.0)
                    direction = arrival[accepted_endpoint]
                    order = order_base[accepted_endpoint] + 1
                positive = contribution > 0.0
                if not np.any(positive):
                    continue
                accepted_trial = accepted_trial[positive]
                contribution = contribution[positive]
                np.add.at(trial_transfer, accepted_trial, contribution)
                atom_trial.append(accepted_trial)
                atom_direction.append(direction[positive])
                atom_contribution.append(contribution)
                atom_order.append(order[positive])
        return (
            trial_transfer,
            atom_trial,
            atom_direction,
            atom_contribution,
            atom_order,
            (solver_calls, geometric, visible, path_accepted),
        )

    @staticmethod
    def _reduce_atoms(
        atom_trial: list[np.ndarray],
        atom_direction: list[np.ndarray],
        atom_contribution: list[np.ndarray],
        atom_order: list[np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if atom_contribution:
            joined_trial = np.concatenate(atom_trial)
            sort = np.argsort(joined_trial, kind="stable")
            direction = np.concatenate(atom_direction)[sort]
            contribution = np.concatenate(atom_contribution)[sort]
            order = np.concatenate(atom_order)[sort]
        else:
            direction = np.empty((0, 3), dtype=np.float64)
            contribution = np.empty(0, dtype=np.float64)
            order = np.empty(0, dtype=np.int64)
        return direction, contribution, order

    @staticmethod
    def _reduce_mass(
        contribution: np.ndarray,
        order: np.ndarray,
        samples: int,
    ) -> tuple[float, np.ndarray, np.ndarray]:
        mass = contribution / samples
        maximum_order = max(1, int(np.max(order, initial=1)))
        by_order = np.zeros(maximum_order + 1, dtype=np.float64)
        for completed_order in np.unique(order):
            by_order[completed_order] = float(np.sum(mass[order == completed_order], dtype=np.float64))
        transfer = float(np.sum(by_order, dtype=np.float64))
        return transfer, by_order, mass

    @staticmethod
    def _sample_statistics(
        trial_transfer: np.ndarray,
        endpoint_count: int,
        samples: int,
    ) -> tuple[float, float, bool, float]:
        variance_available = bool(endpoint_count and samples > 1)
        if variance_available:
            row = trial_transfer.reshape(endpoint_count, samples)
            estimated_variance = float(np.sum(np.var(row, axis=1, ddof=1), dtype=np.float64) / samples)
        else:
            estimated_variance = 0.0
        standard_error = float(np.sqrt(estimated_variance))
        squared = float(np.dot(trial_transfer, trial_transfer))
        contribution_ess = float(np.sum(trial_transfer) ** 2 / squared) if squared > 0.0 else 0.0
        return estimated_variance, standard_error, variance_available, contribution_ess

    def _sampled_diagnostics(
        self,
        seed: int,
        counter_start: int,
        endpoint_count: int,
        samples: int,
        trials: int,
        solver_counts: tuple[int, int, int, int],
        accepted: int,
        statistics: tuple[float, float, bool, float],
        started: float,
    ) -> SampledSpecularDiagnostics:
        solver_calls, geometric, visible, path_accepted = solver_counts
        estimated_variance, standard_error, variance_available, contribution_ess = statistics
        face_ess = (
            float(1.0 / np.dot(self.face_probability, self.face_probability)) if self.face_probability.size else 0.0
        )
        return SampledSpecularDiagnostics(
            seed=int(seed),
            counter_start=counter_start,
            counter_stop=counter_start + trials,
            endpoints=endpoint_count,
            samples_per_endpoint=samples,
            trials=trials,
            source_count=self.source_positions.shape[0],
            source_support=int(np.count_nonzero(self.source_probability)),
            face_count=self.face_probability.size,
            surfaces_support_complete=self.transport.surfaces.support_complete,
            candidates=trials if self.ready else 0,
            solver_calls=solver_calls,
            geometric=geometric,
            visible=visible,
            path_accepted=path_accepted,
            accepted=int(accepted),
            estimated_variance=estimated_variance,
            standard_error=standard_error,
            variance_available=variance_available,
            contribution_ess=contribution_ess,
            face_proposal_ess=face_ess,
            face_probability_min=float(np.min(self.face_probability)) if self.face_probability.size else 0.0,
            face_probability_max=float(np.max(self.face_probability)) if self.face_probability.size else 0.0,
            face_probability_sha256=_array_sha256(self.face_probability),
            source_probability_sha256=_array_sha256(self.source_probability),
            face_proposal=SPECULAR_FACE_PROPOSAL,
            source_proposal=SPECULAR_SOURCE_PROPOSAL,
            counter_generator=SPECULAR_COUNTER_GENERATOR,
            source_counter_dimension=SPECULAR_SOURCE_COUNTER_DIMENSION,
            face_counter_dimension=SPECULAR_FACE_COUNTER_DIMENSION,
            seconds=time.perf_counter() - started,
        )

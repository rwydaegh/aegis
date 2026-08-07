"""Deterministic explicit-source specular paths on finite mesh faces."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..illumination.sphere import fibonacci_sphere
from .specular_broadphase import conservative_order_one_candidates

DEFAULT_SPECULAR_CANDIDATE_BUDGET = 120_000_000
MEASURED_CANDIDATES_PER_SECOND = 1_000_000.0
_ROW_DOT = "ij,ij->i"
_ORDER_ONE_ONLY = "maximum completed specular order is one"
_INSIDE_TRIANGLE_TOLERANCE = 2.0e-8


class SpecularComplexityError(RuntimeError):
    """A requested Cartesian solve exceeds its declared finite work budget."""


def _surface_arrays(
    triangles: np.ndarray,
    normals: np.ndarray,
    face_index: np.ndarray,
    material_class: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    triangle_array = np.asarray(triangles, dtype=np.float64)
    normal_array = np.asarray(normals, dtype=np.float64)
    face_array = np.asarray(face_index, dtype=np.int64)
    material_array = np.asarray(material_class, dtype=np.int64)
    count = triangle_array.shape[0] if triangle_array.ndim == 3 else -1
    if triangle_array.shape != (count, 3, 3):
        raise ValueError("triangles must have shape (faces, 3, 3)")
    if normal_array.shape != (count, 3):
        raise ValueError("normals must have shape (faces, 3)")
    if face_array.shape != (count,) or material_array.shape != (count,):
        raise ValueError("face_index and material_class must match triangles")
    if np.any(~np.isfinite(triangle_array)) or np.any(~np.isfinite(normal_array)):
        raise ValueError("specular surfaces must be finite")
    return triangle_array, normal_array, face_array, material_array, count


def _normalized_surface_normals(triangles: np.ndarray, normals: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(normals, axis=1)
    if np.any(length <= 1.0e-12):
        raise ValueError("specular surface normals must be nonzero")
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_area = np.linalg.norm(cross, axis=1)
    if np.any(double_area <= 1.0e-12):
        raise ValueError("specular triangles must be nondegenerate")
    geometric_normal = cross / double_area[:, None]
    supplied_normal = normals / length[:, None]
    alignment = np.abs(np.einsum(_ROW_DOT, geometric_normal, supplied_normal))
    if np.any(alignment < 1.0 - 1.0e-10):
        raise ValueError("specular normals must be perpendicular to their triangle patches")
    return supplied_normal


def _surface_support_metadata(
    count: int,
    material_class: np.ndarray,
    scene_face_count: int | None,
    support_complete: bool,
    construction: str,
) -> int:
    if np.any(material_class < 0):
        raise ValueError("material_class must be nonnegative")
    support_count = count if scene_face_count is None else int(scene_face_count)
    if support_count < count:
        raise ValueError("scene_face_count cannot be smaller than the supplied surface set")
    if support_complete and support_count != count:
        raise ValueError("a complete surface set must contain every scene face")
    if not construction:
        raise ValueError("specular surface construction must be named")
    return support_count


@dataclass(frozen=True)
class SpecularSurfaces:
    """Finite triangular reflection patches tied to transport material rows."""

    triangles: np.ndarray
    normals: np.ndarray
    face_index: np.ndarray
    material_class: np.ndarray
    support_complete: bool = False
    scene_face_count: int | None = None
    construction: str = "explicit_subset"

    def __post_init__(self) -> None:
        triangles, normals, face_index, material_class, count = _surface_arrays(
            self.triangles, self.normals, self.face_index, self.material_class
        )
        supplied_normal = _normalized_surface_normals(triangles, normals)
        scene_face_count = _surface_support_metadata(
            count,
            material_class,
            self.scene_face_count,
            self.support_complete,
            self.construction,
        )
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "normals", supplied_normal)
        object.__setattr__(self, "face_index", face_index)
        object.__setattr__(self, "material_class", material_class)
        object.__setattr__(self, "scene_face_count", scene_face_count)

    @classmethod
    def from_tracer(cls, tracer: Any) -> SpecularSurfaces:
        """Build one verified planar patch per finite support-mesh triangle."""
        geometry = tracer.geometry
        if not hasattr(geometry, "vertices") or not hasattr(geometry, "faces"):
            return cls(
                np.empty((0, 3, 3), dtype=np.float64),
                np.empty((0, 3), dtype=np.float64),
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int64),
                support_complete=True,
                scene_face_count=0,
                construction="geometry_without_finite_faces",
            )
        vertices = np.asarray(geometry.vertices, dtype=np.float64)
        faces = np.asarray(geometry.faces, dtype=np.int64)
        triangles = vertices[faces]
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        length = np.linalg.norm(cross, axis=1)
        valid = length > 1.0e-12
        all_material_class = (
            np.zeros(faces.shape[0], dtype=np.int64)
            if tracer.face_class is None
            else np.asarray(tracer.face_class, dtype=np.int64)
        )
        return cls(
            triangles[valid],
            cross[valid] / length[valid, None],
            np.arange(faces.shape[0], dtype=np.int64)[valid],
            all_material_class[valid],
            support_complete=True,
            scene_face_count=int(np.sum(valid)),
            construction="all_nondegenerate_mesh_faces",
        )

    def ordered_sequences(self, order: int = 1) -> np.ndarray:
        """Return candidate surface-index sequences for the completed order."""
        if order != 1:
            raise NotImplementedError("only one-reflection ordered plane sequences are complete")
        return np.arange(self.triangles.shape[0], dtype=np.int64)[:, None]


@dataclass(frozen=True)
class SpecularCandidateSet:
    """Named reflection candidates with an auditable support-completeness claim."""

    sequences: np.ndarray
    method: str
    support_complete: bool = False
    missed_support_faces: int | None = None
    diagnostics: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        sequences = np.asarray(self.sequences, dtype=np.int64)
        if sequences.ndim != 2:
            raise ValueError("one-reflection candidate sequences must be two-dimensional")
        if sequences.shape[1] != 1:
            raise NotImplementedError(_ORDER_ONE_ONLY)
        if not self.method:
            raise ValueError("candidate method must be named")
        if self.missed_support_faces is not None and self.missed_support_faces < 0:
            raise ValueError("missed_support_faces must be nonnegative")
        if self.support_complete and self.missed_support_faces not in (None, 0):
            raise ValueError("a complete candidate set cannot report missed support")
        object.__setattr__(self, "sequences", sequences)
        object.__setattr__(self, "diagnostics", {} if self.diagnostics is None else dict(self.diagnostics))

    @classmethod
    def all_surfaces(cls, surfaces: SpecularSurfaces) -> SpecularCandidateSet:
        """Enumerate every verified surface, complete only when its support is."""
        missed = 0 if surfaces.support_complete else None
        return cls(
            surfaces.ordered_sequences(),
            method="all_verified_surfaces",
            support_complete=surfaces.support_complete,
            missed_support_faces=missed,
            diagnostics={"levels": [], "angular_samples": 0},
        )


@dataclass(frozen=True)
class ReceiverVisibleFaceCandidates:
    """Convergent deterministic receiver-visible face discovery.

    Every valid one-reflection path ends on a face directly visible from the
    receiver. Equal-area direction sets therefore provide a necessary-support
    screen without testing any source. The screen is not complete at finite
    resolution. Its cumulative levels, newly discovered faces, angular area,
    and unselected support count are carried into every result.
    """

    sample_levels: tuple[int, ...] = (256,)
    growth_factor: int = 4
    epsilon_m: float = 1.0e-3

    def __post_init__(self) -> None:
        if not self.sample_levels or any(level < 1 for level in self.sample_levels):
            raise ValueError("visible-face sample levels must be positive")
        if tuple(sorted(set(self.sample_levels))) != self.sample_levels:
            raise ValueError("visible-face sample levels must be strictly increasing")
        if not isinstance(self.growth_factor, int) or isinstance(self.growth_factor, bool) or self.growth_factor < 2:
            raise ValueError("visible-face growth_factor must be an integer of at least two")
        if self.epsilon_m < 0.0:
            raise ValueError("visible-face epsilon must be nonnegative")

    def select(self, transport: OneBounceSpecularTransport, receiver: np.ndarray) -> SpecularCandidateSet:
        """Return the cumulative face set at the declared finest resolution."""
        return self.refinement(transport, receiver)[-1]

    def refinement(
        self,
        transport: OneBounceSpecularTransport,
        receiver: np.ndarray,
    ) -> tuple[SpecularCandidateSet, ...]:
        """Return one cumulative candidate set for every angular resolution.

        The returned sets are snapshots, so transfer can be recomputed at each
        support resolution instead of treating face-count discovery as a
        convergence proxy.
        """
        candidate_levels: list[SpecularCandidateSet] = []
        previous = None
        for samples in self.sample_levels:
            previous = self.refine_level(transport, receiver, samples, previous=previous)
            candidate_levels.append(previous)
        return tuple(candidate_levels)

    def refine_level(
        self,
        transport: OneBounceSpecularTransport,
        receiver: np.ndarray,
        angular_samples: int,
        *,
        previous: SpecularCandidateSet | None = None,
    ) -> SpecularCandidateSet:
        """Extend a cumulative receiver-visible support screen by one level."""
        if angular_samples < 1:
            raise ValueError("visible-face angular_samples must be positive")
        receiver = np.asarray(receiver, dtype=np.float64)
        if receiver.shape != (3,) or np.any(~np.isfinite(receiver)):
            raise ValueError("receiver must be one finite three-vector")
        started = time.perf_counter()
        actual_to_surface = {int(actual): index for index, actual in enumerate(transport.surfaces.face_index)}
        selected = set() if previous is None else set(int(value) for value in previous.sequences[:, 0])
        prior_levels = [] if previous is None else list(previous.diagnostics.get("levels", ()))
        prior_rays = 0 if previous is None else int(previous.diagnostics.get("total_visibility_rays", 0))
        prior_seconds = 0.0 if previous is None else float(previous.diagnostics.get("seconds", 0.0))
        directions = fibonacci_sphere(angular_samples)
        origins = np.broadcast_to(receiver, directions.shape) + self.epsilon_m * directions
        hit, _travel, _normal, face = transport.geometry.intersect(origins, directions)
        before = len(selected)
        for actual in np.unique(np.asarray(face, dtype=np.int64)[hit]):
            surface = actual_to_surface.get(int(actual))
            if surface is not None:
                selected.add(surface)
        level = {
            "angular_samples": angular_samples,
            "solid_angle_per_sample_sr": 4.0 * np.pi / angular_samples,
            "selected_faces": len(selected),
            "new_faces": len(selected) - before,
        }
        support = transport.surfaces.triangles.shape[0]
        return SpecularCandidateSet(
            np.asarray(sorted(selected), dtype=np.int64)[:, None],
            method="receiver_visible_equal_area_refinement",
            support_complete=False,
            missed_support_faces=support - len(selected),
            diagnostics={
                "angular_samples": angular_samples,
                "levels": [*prior_levels, level],
                "total_visibility_rays": prior_rays + angular_samples,
                "seconds": prior_seconds + time.perf_counter() - started,
                "finite_resolution_support_incomplete": True,
            },
        )


@dataclass(frozen=True)
class SourceQuadratureSelection:
    """One deterministic probability-stratified source approximation."""

    positions: np.ndarray
    probabilities: np.ndarray
    source_index: np.ndarray
    requested_strata: int
    support_complete: bool


@dataclass(frozen=True)
class StratifiedSourceQuadrature:
    """Deterministic refinement of a normalized one-dimensional source measure."""

    strata_levels: tuple[int, ...] = (128,)
    growth_factor: int = 2

    def __post_init__(self) -> None:
        if not self.strata_levels or any(level < 1 for level in self.strata_levels):
            raise ValueError("source strata levels must be positive")
        if tuple(sorted(set(self.strata_levels))) != self.strata_levels:
            raise ValueError("source strata levels must be strictly increasing")
        if not isinstance(self.growth_factor, int) or isinstance(self.growth_factor, bool) or self.growth_factor < 2:
            raise ValueError("source growth_factor must be an integer of at least two")

    def select(
        self,
        positions: np.ndarray,
        probabilities: np.ndarray,
        strata: int,
    ) -> SourceQuadratureSelection:
        """Select midpoint probability strata and aggregate repeated segments."""
        positions = np.asarray(positions, dtype=np.float64)
        probabilities = np.asarray(probabilities, dtype=np.float64)
        if positions.ndim != 2 or positions.shape[1] != 3 or probabilities.shape != (positions.shape[0],):
            raise ValueError("source positions and probabilities must have shapes (N, 3) and (N,)")
        if strata < 1:
            raise ValueError("source strata must be positive")
        count = positions.shape[0]
        if count == 0:
            return SourceQuadratureSelection(
                positions.copy(), probabilities.copy(), np.empty(0, dtype=np.int64), strata, True
            )
        if np.any(~np.isfinite(probabilities)) or np.any(probabilities < 0.0):
            raise ValueError("source probabilities must be finite and nonnegative")
        if not np.isclose(np.sum(probabilities), 1.0, rtol=1.0e-12, atol=1.0e-15):
            raise ValueError("source probabilities must be normalized")
        if strata >= count:
            return SourceQuadratureSelection(
                positions.copy(), probabilities.copy(), np.arange(count, dtype=np.int64), strata, True
            )
        target = (np.arange(strata, dtype=np.float64) + 0.5) / strata
        chosen = np.searchsorted(np.cumsum(probabilities), target, side="left")
        source_index, multiplicity = np.unique(chosen, return_counts=True)
        reduced_probability = multiplicity.astype(np.float64) / strata
        return SourceQuadratureSelection(
            positions[source_index],
            reduced_probability,
            source_index,
            strata,
            False,
        )


@dataclass(frozen=True)
class SpecularWorkEstimate:
    """Conservative exact-order-1 work bound evaluated before tracing."""

    faces: int
    sources: int
    rays: int
    samples: int
    max_bounces: int
    all_specular_candidates: int
    mixed_suffix_candidates_upper_bound: int
    total_candidates_upper_bound: int
    candidate_budget: int
    enabled: bool
    projected_seconds: float
    support_complete: bool
    reason: str

    @classmethod
    def exact_order_one(
        cls,
        *,
        faces: int,
        sources: int,
        rays: int,
        samples: int,
        max_bounces: int,
        candidate_budget: int,
        support_complete: bool,
    ) -> SpecularWorkEstimate:
        values = (faces, sources, rays, samples, max_bounces, candidate_budget)
        if any(value < 0 for value in values) or candidate_budget == 0:
            raise ValueError("specular work dimensions must be nonnegative and budget positive")
        all_specular = faces * sources if max_bounces >= 1 else 0
        suffix_vertices = rays * max(max_bounces - 1, 0) * samples
        suffix = faces * suffix_vertices
        total = all_specular + suffix
        enabled = faces > 0 and max_bounces >= 1 and total <= candidate_budget
        if faces == 0:
            reason = "no finite specular surfaces"
        elif max_bounces < 1:
            reason = "maximum transport order excludes specular reflections"
        elif total > candidate_budget:
            reason = f"exact Cartesian upper bound {total} exceeds candidate budget {candidate_budget}"
        elif not support_complete:
            reason = "bounded candidate subset fits budget but does not cover the full reflection support"
        else:
            reason = "exact all-face order-1 solve fits the candidate budget"
        return cls(
            faces,
            sources,
            rays,
            samples,
            max_bounces,
            all_specular,
            suffix,
            total,
            candidate_budget,
            enabled,
            total / MEASURED_CANDIDATES_PER_SECOND,
            support_complete,
            reason,
        )

    def as_dict(self) -> dict[str, int | float | bool | str]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class SpecularDiagnostics:
    """Candidate and timing evidence for one image solve."""

    endpoint_pairs: int
    plane_sequences: int
    candidates: int
    geometric: int
    visible: int
    accepted: int
    chunks: int
    seconds: float
    candidate_method: str
    candidate_support_complete: bool
    selected_faces: int
    support_faces: int
    missed_support_faces: int | None
    candidate_diagnostics: dict[str, Any]
    maximum_completed_order: int = 1

    def __post_init__(self) -> None:
        counts = (
            self.endpoint_pairs,
            self.plane_sequences,
            self.candidates,
            self.geometric,
            self.visible,
            self.accepted,
            self.chunks,
        )
        if any(value < 0 for value in counts):
            raise ValueError("specular diagnostic counts must be nonnegative")
        if self.candidates != self.endpoint_pairs * self.plane_sequences:
            raise ValueError("specular candidate count must equal pairs times sequences")
        if not (self.accepted <= self.visible <= self.geometric <= self.candidates):
            raise ValueError("specular diagnostic stages must be monotonically decreasing")
        if not np.isfinite(self.seconds) or self.seconds < 0.0:
            raise ValueError("specular diagnostic time must be finite and nonnegative")
        if self.maximum_completed_order != 1:
            raise ValueError(_ORDER_ONE_ONLY)
        if not self.candidate_method:
            raise ValueError("candidate method must be named")
        if not (0 <= self.selected_faces <= self.support_faces):
            raise ValueError("selected candidate faces must lie within reflection support")
        if self.candidate_support_complete and self.selected_faces != self.support_faces:
            raise ValueError("complete candidate support must select every support face")
        if self.missed_support_faces is not None and self.missed_support_faces < 0:
            raise ValueError("missed support must be nonnegative")

    def as_dict(self) -> dict[str, int | float]:
        return {
            "endpoint_pairs": self.endpoint_pairs,
            "plane_sequences": self.plane_sequences,
            "candidates": self.candidates,
            "geometric": self.geometric,
            "visible": self.visible,
            "accepted": self.accepted,
            "chunks": self.chunks,
            "seconds": self.seconds,
            "candidate_method": self.candidate_method,
            "candidate_support_complete": self.candidate_support_complete,
            "selected_faces": self.selected_faces,
            "support_faces": self.support_faces,
            "missed_support_faces": self.missed_support_faces,
            "candidate_diagnostics": dict(self.candidate_diagnostics),
            "maximum_completed_order": self.maximum_completed_order,
        }


@dataclass(frozen=True)
class SpecularPaths:
    """Accepted paths, one row per exact directional atom."""

    k_hat: np.ndarray
    transfer: np.ndarray
    reflection_point: np.ndarray
    source_index: np.ndarray
    endpoint_index: np.ndarray
    surface_sequence: np.ndarray
    unfolded_length_m: np.ndarray
    diagnostics: SpecularDiagnostics

    def __post_init__(self) -> None:
        k_hat = np.asarray(self.k_hat, dtype=np.float64)
        transfer = np.asarray(self.transfer, dtype=np.float64)
        reflection = np.asarray(self.reflection_point, dtype=np.float64)
        source = np.asarray(self.source_index, dtype=np.int64)
        endpoint = np.asarray(self.endpoint_index, dtype=np.int64)
        sequence = np.asarray(self.surface_sequence, dtype=np.int64)
        length = np.asarray(self.unfolded_length_m, dtype=np.float64)
        count = transfer.size
        if k_hat.shape != (count, 3) or reflection.shape != (count, 3) or sequence.shape != (count, 1):
            raise ValueError("specular path vectors must match transfer rows")
        if source.shape != (count,) or endpoint.shape != (count,) or length.shape != (count,):
            raise ValueError("specular path metadata must match transfer rows")
        if np.any(~np.isfinite(k_hat)) or np.any(~np.isfinite(reflection)) or np.any(~np.isfinite(transfer)):
            raise ValueError("specular path data must be finite")
        if np.any(transfer < 0.0) or np.any(~np.isfinite(length)) or np.any(length <= 0.0):
            raise ValueError("specular transfers must be nonnegative and path lengths positive")
        if count and not np.allclose(np.linalg.norm(k_hat, axis=1), 1.0, rtol=1.0e-10, atol=1.0e-10):
            raise ValueError("specular arrival directions must be unit length")
        if self.diagnostics.accepted != count:
            raise ValueError("accepted diagnostic count must match specular paths")
        object.__setattr__(self, "k_hat", k_hat)
        object.__setattr__(self, "transfer", transfer)
        object.__setattr__(self, "reflection_point", reflection)
        object.__setattr__(self, "source_index", source)
        object.__setattr__(self, "endpoint_index", endpoint)
        object.__setattr__(self, "surface_sequence", sequence)
        object.__setattr__(self, "unfolded_length_m", length)

    @classmethod
    def empty(cls, diagnostics: SpecularDiagnostics) -> SpecularPaths:
        return cls(
            np.empty((0, 3), dtype=np.float64),
            np.empty(0, dtype=np.float64),
            np.empty((0, 3), dtype=np.float64),
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
            np.empty((0, 1), dtype=np.int64),
            np.empty(0, dtype=np.float64),
            diagnostics,
        )

    @property
    def total(self) -> float:
        return float(np.sum(self.transfer, dtype=np.float64))


def _inside_triangles(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    edge1 = triangle[:, 1] - triangle[:, 0]
    edge2 = triangle[:, 2] - triangle[:, 0]
    offset = point - triangle[:, 0]
    d11 = np.einsum(_ROW_DOT, edge1, edge1)
    d12 = np.einsum(_ROW_DOT, edge1, edge2)
    d22 = np.einsum(_ROW_DOT, edge2, edge2)
    q1 = np.einsum(_ROW_DOT, offset, edge1)
    q2 = np.einsum(_ROW_DOT, offset, edge2)
    determinant = d11 * d22 - d12 * d12
    u = (d22 * q1 - d12 * q2) / np.maximum(determinant, 1.0e-300)
    v = (d11 * q2 - d12 * q1) / np.maximum(determinant, 1.0e-300)
    tolerance = _INSIDE_TRIANGLE_TOLERANCE
    return (determinant > 1.0e-24) & (u >= -tolerance) & (v >= -tolerance) & (u + v <= 1.0 + tolerance)


class OneBounceSpecularTransport:
    """Chunked image-source solver for exactly one finite specular reflection."""

    def __init__(
        self,
        tracer: Any,
        surfaces: SpecularSurfaces | None = None,
        *,
        candidate_chunk: int = 262_144,
        candidate_budget: int = DEFAULT_SPECULAR_CANDIDATE_BUDGET,
        epsilon_m: float | None = None,
        broad_phase_threshold: int = 20_000,
        broad_phase_source_chunk: int = 16,
    ) -> None:
        if candidate_chunk < 1:
            raise ValueError("candidate_chunk must be positive")
        if candidate_budget < 1:
            raise ValueError("candidate_budget must be positive")
        if broad_phase_threshold < 0:
            raise ValueError("broad_phase_threshold must be nonnegative")
        if broad_phase_source_chunk < 1:
            raise ValueError("broad_phase_source_chunk must be positive")
        self.tracer = tracer
        self.geometry = tracer.geometry
        self.surfaces = SpecularSurfaces.from_tracer(tracer) if surfaces is None else surfaces
        self.candidate_chunk = int(candidate_chunk)
        self.candidate_budget = int(candidate_budget)
        self.epsilon_m = float(tracer.config.ray_epsilon_m if epsilon_m is None else epsilon_m)
        self.broad_phase_threshold = int(broad_phase_threshold)
        self.broad_phase_source_chunk = int(broad_phase_source_chunk)

    def work_estimate(self, *, sources: int, rays: int, samples: int, max_bounces: int) -> SpecularWorkEstimate:
        """Bound exact all-face work before any candidate arrays are allocated."""
        return SpecularWorkEstimate.exact_order_one(
            faces=self.surfaces.triangles.shape[0],
            sources=sources,
            rays=rays,
            samples=samples,
            max_bounces=max_bounces,
            candidate_budget=self.candidate_budget,
            support_complete=self.surfaces.support_complete,
        )

    def solve_all_sources(
        self,
        sources: np.ndarray,
        receiver: np.ndarray,
        probabilities: np.ndarray,
        *,
        sequences: np.ndarray | None = None,
        candidate_set: SpecularCandidateSet | None = None,
    ) -> SpecularPaths:
        """Solve every normalized source contribution to one receiver exactly."""
        sources = np.atleast_2d(np.asarray(sources, dtype=np.float64))
        probabilities = np.asarray(probabilities, dtype=np.float64)
        if probabilities.shape != (sources.shape[0],):
            raise ValueError("probabilities must match sources")
        if np.any(~np.isfinite(probabilities)) or np.any(probabilities < 0.0):
            raise ValueError("probabilities must be finite and nonnegative")
        if sources.shape[0] and not np.isclose(np.sum(probabilities), 1.0, rtol=1.0e-12, atol=1.0e-15):
            raise ValueError("source probabilities must be normalized")
        receivers = np.broadcast_to(np.asarray(receiver, dtype=np.float64), sources.shape)
        return self.solve_paired(
            sources,
            receivers,
            endpoint_weight=probabilities,
            source_index=np.arange(sources.shape[0], dtype=np.int64),
            sequences=sequences,
            candidate_set=candidate_set,
        )

    def solve_paired(
        self,
        sources: np.ndarray,
        receivers: np.ndarray,
        *,
        endpoint_weight: np.ndarray | None = None,
        source_index: np.ndarray | None = None,
        sequences: np.ndarray | None = None,
        candidate_set: SpecularCandidateSet | None = None,
    ) -> SpecularPaths:
        """Solve paired endpoints over explicit ordered plane sequences.

        ``sequences`` is deliberately an ordered two-dimensional interface. Its
        width is one in this increment. A later order extends the same contract
        without changing endpoint or result representation.
        """
        started = time.perf_counter()
        sources = np.asarray(sources, dtype=np.float64)
        receivers = np.asarray(receivers, dtype=np.float64)
        if sources.ndim != 2 or sources.shape[1] != 3 or receivers.shape != sources.shape:
            raise ValueError("sources and receivers must have matching shape (pairs, 3)")
        if np.any(~np.isfinite(sources)) or np.any(~np.isfinite(receivers)):
            raise ValueError("specular endpoints must be finite")
        pair_count = sources.shape[0]
        weights = (
            np.ones(pair_count, dtype=np.float64)
            if endpoint_weight is None
            else np.asarray(endpoint_weight, dtype=np.float64)
        )
        if weights.shape != (pair_count,) or np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("endpoint_weight must be finite, nonnegative, and match endpoint pairs")
        source_ids = (
            np.arange(pair_count, dtype=np.int64) if source_index is None else np.asarray(source_index, dtype=np.int64)
        )
        if source_ids.shape != (pair_count,):
            raise ValueError("source_index must match endpoint pairs")
        selection = self._candidate_selection(sequences, candidate_set)
        candidate_sequences = selection.sequences
        if candidate_sequences.ndim != 2:
            raise ValueError("sequences must have shape (sequences, order)")
        if candidate_sequences.shape[1] != 1:
            raise NotImplementedError(_ORDER_ONE_ONLY)
        if np.any(candidate_sequences < 0) or np.any(candidate_sequences >= self.surfaces.triangles.shape[0]):
            raise ValueError("sequences contain an unknown specular surface")

        sequence_count = candidate_sequences.shape[0]
        candidate_count = pair_count * sequence_count
        if candidate_count > self.candidate_budget:
            raise SpecularComplexityError(
                f"specular solve requires {candidate_count} candidates, exceeding budget {self.candidate_budget}"
            )
        broad_phase = None
        if candidate_count >= self.broad_phase_threshold and pair_count and np.all(receivers == receivers[0]):
            surface = candidate_sequences[:, 0]
            broad_phase = conservative_order_one_candidates(
                sources,
                receivers[0],
                self.surfaces.triangles[surface],
                self.surfaces.normals[surface],
                epsilon_m=self.epsilon_m,
                source_chunk=self.broad_phase_source_chunk,
                inside_tolerance=_INSIDE_TRIANGLE_TOLERANCE,
            )
        return self._solve_candidate_kernel(
            sources,
            receivers,
            weights,
            source_ids,
            candidate_count=candidate_count,
            selection=selection,
            paired_surfaces=None,
            started=started,
            candidate_flat=None if broad_phase is None else broad_phase.flat_index,
            broad_phase_diagnostics=None if broad_phase is None else broad_phase.as_dict(),
        )

    def solve_paired_surfaces(
        self,
        sources: np.ndarray,
        receivers: np.ndarray,
        surface_index: np.ndarray,
        *,
        endpoint_weight: np.ndarray | None = None,
        source_index: np.ndarray | None = None,
    ) -> SpecularPaths:
        """Solve one explicitly paired finite reflection surface per endpoint.

        Candidate ``i`` is exactly ``(sources[i], receivers[i], surface_index[i])``.
        Unlike :meth:`solve_paired`, this does not form a Cartesian product with
        a common sequence set. The geometry, visibility, atlas response, and
        acceptance kernel are shared exactly with that reference path.
        """
        started = time.perf_counter()
        sources = np.asarray(sources, dtype=np.float64)
        receivers = np.asarray(receivers, dtype=np.float64)
        if sources.ndim != 2 or sources.shape[1] != 3 or receivers.shape != sources.shape:
            raise ValueError("sources and receivers must have matching shape (pairs, 3)")
        if np.any(~np.isfinite(sources)) or np.any(~np.isfinite(receivers)):
            raise ValueError("specular endpoints must be finite")
        pair_count = sources.shape[0]
        raw_surfaces = np.asarray(surface_index)
        if raw_surfaces.shape != (pair_count,):
            raise ValueError("surface_index must match endpoint pairs")
        if np.issubdtype(raw_surfaces.dtype, np.bool_) or not np.issubdtype(raw_surfaces.dtype, np.integer):
            raise ValueError("surface_index must contain integer surface indices")
        surfaces = raw_surfaces.astype(np.int64, copy=False)
        if np.any(surfaces < 0) or np.any(surfaces >= self.surfaces.triangles.shape[0]):
            raise ValueError("surface_index contains an unknown specular surface")
        weights = (
            np.ones(pair_count, dtype=np.float64)
            if endpoint_weight is None
            else np.asarray(endpoint_weight, dtype=np.float64)
        )
        if weights.shape != (pair_count,) or np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("endpoint_weight must be finite, nonnegative, and match endpoint pairs")
        source_ids = (
            np.arange(pair_count, dtype=np.int64) if source_index is None else np.asarray(source_index, dtype=np.int64)
        )
        if source_ids.shape != (pair_count,):
            raise ValueError("source_index must match endpoint pairs")
        if pair_count > self.candidate_budget:
            raise SpecularComplexityError(
                f"specular solve requires {pair_count} candidates, exceeding budget {self.candidate_budget}"
            )
        return self._solve_candidate_kernel(
            sources,
            receivers,
            weights,
            source_ids,
            candidate_count=pair_count,
            selection=None,
            paired_surfaces=surfaces,
            started=started,
        )

    def _solve_candidate_kernel(
        self,
        sources: np.ndarray,
        receivers: np.ndarray,
        weights: np.ndarray,
        source_ids: np.ndarray,
        *,
        candidate_count: int,
        selection: SpecularCandidateSet | None,
        paired_surfaces: np.ndarray | None,
        started: float,
        candidate_flat: np.ndarray | None = None,
        broad_phase_diagnostics: dict[str, Any] | None = None,
    ) -> SpecularPaths:
        """Shared exact image, visibility, material, and acceptance kernel."""
        pair_count = sources.shape[0]
        if candidate_count == 0:
            return self._empty_candidate_paths(selection, paired_surfaces, pair_count, started)

        out: dict[str, list[np.ndarray]] = {
            "k_hat": [],
            "transfer": [],
            "reflection": [],
            "source": [],
            "endpoint": [],
            "surface": [],
            "length": [],
        }
        geometric_count = 0
        visible_count = 0
        chunks = 0
        eps = self.epsilon_m

        executed_candidates = candidate_count if candidate_flat is None else candidate_flat.size
        for start in range(0, executed_candidates, self.candidate_chunk):
            chunks += 1
            stop = min(start + self.candidate_chunk, executed_candidates)
            flat = np.arange(start, stop, dtype=np.int64) if candidate_flat is None else candidate_flat[start:stop]
            pair, surface = self._candidate_chunk_indices(flat, selection, paired_surfaces)
            triangle = self.surfaces.triangles[surface]
            normal = self.surfaces.normals[surface]
            plane_point = triangle[:, 0]
            source = sources[pair]
            receiver = receivers[pair]
            source_side = np.einsum(_ROW_DOT, source - plane_point, normal)
            receiver_side = np.einsum(_ROW_DOT, receiver - plane_point, normal)
            image = source - 2.0 * source_side[:, None] * normal
            image_line = image - receiver
            denominator = np.einsum(_ROW_DOT, image_line, normal)
            with np.errstate(divide="ignore", invalid="ignore"):
                fraction = -receiver_side / denominator
            finite_fraction = np.isfinite(fraction)
            safe_fraction = np.where(finite_fraction, fraction, 0.0)
            reflection = receiver + safe_fraction[:, None] * image_line
            distinct = np.linalg.norm(source - receiver, axis=1) > 1.0e-12
            geometric = (
                distinct
                & (source_side * receiver_side > eps * eps)
                & finite_fraction
                & (fraction > 0.0)
                & (fraction < 1.0)
                & _inside_triangles(reflection, triangle)
            )
            geometric_count += int(np.sum(geometric))
            if not np.any(geometric):
                continue

            pair = pair[geometric]
            surface = surface[geometric]
            source = source[geometric]
            receiver = receiver[geometric]
            reflection = reflection[geometric]
            normal = normal[geometric]
            source_leg = reflection - source
            source_range = np.linalg.norm(source_leg, axis=1)
            source_direction = source_leg / source_range[:, None]
            receiver_leg = receiver - reflection
            receiver_range = np.linalg.norm(receiver_leg, axis=1)
            arrival = receiver_leg / receiver_range[:, None]

            hit1, travel1, _normal1, face1 = self.geometry.intersect(
                source + eps * source_direction,
                source_direction,
            )
            expected_face = self.surfaces.face_index[surface]
            endpoint_hit = hit1 & (travel1 >= source_range - 2.0 * eps)
            endpoint_hit &= (expected_face < 0) | (np.asarray(face1, dtype=np.int64) == expected_face)
            hit2, travel2, _normal2, _face2 = self.geometry.intersect(
                reflection + eps * arrival,
                arrival,
            )
            receiver_clear = (~hit2) | (travel2 >= receiver_range - 2.0 * eps)
            visible = endpoint_hit & receiver_clear
            visible_count += int(np.sum(visible))
            if not np.any(visible):
                continue

            pair = pair[visible]
            surface = surface[visible]
            reflection = reflection[visible]
            arrival = arrival[visible]
            normal = normal[visible]
            source_direction = source_direction[visible]
            source_range = source_range[visible]
            receiver_range = receiver_range[visible]
            cosine = np.clip(np.abs(np.einsum(_ROW_DOT, source_direction, normal)), 0.0, 1.0)
            face = self.surfaces.face_index[surface]
            reflectance, share, nonblocking = self.tracer._surface_response(
                cosine,
                self.surfaces.material_class[surface],
                face,
                reflection,
            )
            transfer = weights[pair] * reflectance * share / np.square(source_range + receiver_range)
            accepted = (~nonblocking) & (transfer > 0.0) & np.isfinite(transfer)
            if not np.any(accepted):
                continue
            out["k_hat"].append(arrival[accepted])
            out["transfer"].append(transfer[accepted])
            out["reflection"].append(reflection[accepted])
            out["source"].append(source_ids[pair[accepted]])
            out["endpoint"].append(pair[accepted])
            out["surface"].append(self.surfaces.face_index[surface[accepted], None])
            out["length"].append((source_range + receiver_range)[accepted])

        accepted_count = sum(part.shape[0] for part in out["transfer"])
        seconds = time.perf_counter() - started
        diagnostics = self._kernel_diagnostics(
            selection,
            paired_surfaces,
            pair_count,
            candidate_count,
            geometric_count,
            visible_count,
            accepted_count,
            chunks,
            seconds,
            broad_phase_diagnostics,
        )
        if accepted_count == 0:
            return SpecularPaths.empty(diagnostics)
        return SpecularPaths(
            np.concatenate(out["k_hat"]),
            np.concatenate(out["transfer"]),
            np.concatenate(out["reflection"]),
            np.concatenate(out["source"]),
            np.concatenate(out["endpoint"]),
            np.concatenate(out["surface"]),
            np.concatenate(out["length"]),
            diagnostics,
        )

    def _empty_candidate_paths(
        self,
        selection: SpecularCandidateSet | None,
        paired_surfaces: np.ndarray | None,
        pair_count: int,
        started: float,
    ) -> SpecularPaths:
        diagnostics = self._kernel_diagnostics(
            selection,
            paired_surfaces,
            pair_count,
            0,
            0,
            0,
            0,
            0,
            time.perf_counter() - started,
        )
        return SpecularPaths.empty(diagnostics)

    @staticmethod
    def _candidate_chunk_indices(
        flat: np.ndarray,
        selection: SpecularCandidateSet | None,
        paired_surfaces: np.ndarray | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if paired_surfaces is not None:
            return flat, paired_surfaces[flat]
        if selection is None:
            raise AssertionError("Cartesian candidates require a selection")
        candidate_sequences = selection.sequences
        sequence_count = candidate_sequences.shape[0]
        pair = flat // sequence_count
        sequence = flat - pair * sequence_count
        return pair, candidate_sequences[sequence, 0]

    def _kernel_diagnostics(
        self,
        selection: SpecularCandidateSet | None,
        paired_surfaces: np.ndarray | None,
        pair_count: int,
        candidate_count: int,
        geometric: int,
        visible: int,
        accepted: int,
        chunks: int,
        seconds: float,
        broad_phase_diagnostics: dict[str, Any] | None = None,
    ) -> SpecularDiagnostics:
        if selection is not None:
            return self._diagnostics(
                selection,
                pair_count,
                candidate_count,
                geometric,
                visible,
                accepted,
                chunks,
                seconds,
                broad_phase_diagnostics,
            )
        return self._paired_diagnostics(
            paired_surfaces,
            pair_count,
            geometric,
            visible,
            accepted,
            chunks,
            seconds,
        )

    def _paired_diagnostics(
        self,
        surface_index: np.ndarray | None,
        endpoint_pairs: int,
        geometric: int,
        visible: int,
        accepted: int,
        chunks: int,
        seconds: float,
    ) -> SpecularDiagnostics:
        surface = np.empty(0, dtype=np.int64) if surface_index is None else surface_index
        selected = int(np.unique(surface).size)
        support = int(self.surfaces.scene_face_count or self.surfaces.triangles.shape[0])
        return SpecularDiagnostics(
            endpoint_pairs=endpoint_pairs,
            plane_sequences=1,
            candidates=endpoint_pairs,
            geometric=geometric,
            visible=visible,
            accepted=accepted,
            chunks=chunks,
            seconds=seconds,
            candidate_method="paired_explicit_surfaces",
            candidate_support_complete=False,
            selected_faces=selected,
            support_faces=support,
            missed_support_faces=support - selected,
            candidate_diagnostics={"paired_surface_indices": True},
        )

    def _candidate_selection(
        self,
        sequences: np.ndarray | None,
        candidate_set: SpecularCandidateSet | None,
    ) -> SpecularCandidateSet:
        if sequences is not None and candidate_set is not None:
            raise ValueError("pass sequences or candidate_set, not both")
        selection = self._resolve_candidate_selection(sequences, candidate_set)
        self._validate_candidate_selection(selection)
        return selection

    def _resolve_candidate_selection(
        self,
        sequences: np.ndarray | None,
        candidate_set: SpecularCandidateSet | None,
    ) -> SpecularCandidateSet:
        if candidate_set is not None:
            return candidate_set
        if sequences is None:
            return SpecularCandidateSet.all_surfaces(self.surfaces)
        chosen = np.asarray(sequences, dtype=np.int64)
        selected = np.unique(chosen[:, 0]).size if chosen.ndim == 2 and chosen.shape[1] == 1 else 0
        all_selected = selected == self.surfaces.triangles.shape[0]
        missed = self.surfaces.triangles.shape[0] - selected if self.surfaces.support_complete else None
        return SpecularCandidateSet(
            chosen,
            method="explicit_sequences",
            support_complete=self.surfaces.support_complete and all_selected,
            missed_support_faces=missed,
        )

    def _validate_candidate_selection(self, selection: SpecularCandidateSet) -> None:
        chosen = selection.sequences
        if np.any(chosen < 0) or np.any(chosen >= self.surfaces.triangles.shape[0]):
            raise ValueError("candidate set contains an unknown specular surface")
        selected = np.unique(chosen[:, 0]).size
        all_selected = selected == self.surfaces.triangles.shape[0]
        if selection.support_complete and not (self.surfaces.support_complete and all_selected):
            raise ValueError("candidate set cannot claim completeness without full verified support")

    def _diagnostics(
        self,
        selection: SpecularCandidateSet,
        endpoint_pairs: int,
        candidates: int,
        geometric: int,
        visible: int,
        accepted: int,
        chunks: int,
        seconds: float,
        broad_phase_diagnostics: dict[str, Any] | None = None,
    ) -> SpecularDiagnostics:
        selected = int(np.unique(selection.sequences[:, 0]).size)
        support = int(self.surfaces.scene_face_count or self.surfaces.triangles.shape[0])
        candidate_diagnostics = dict(selection.diagnostics or {})
        if broad_phase_diagnostics is not None:
            candidate_diagnostics["broad_phase"] = dict(broad_phase_diagnostics)
        return SpecularDiagnostics(
            endpoint_pairs,
            selection.sequences.shape[0],
            candidates,
            geometric,
            visible,
            accepted,
            chunks,
            seconds,
            selection.method,
            selection.support_complete,
            selected,
            support,
            selection.missed_support_faces,
            candidate_diagnostics,
        )

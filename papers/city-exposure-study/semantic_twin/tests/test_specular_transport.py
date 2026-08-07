"""Exact one-reflection transport for explicit finite sources."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from semantic_twin.illumination import ISOTROPIC
from semantic_twin.illumination.curve import FacadeTipCurve
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.propagation.geometry import PlaneGeometry
from semantic_twin.transport.next_event import NextEventEstimator, NextEventField, NextEventGather
from semantic_twin.transport.specular import (
    OneBounceSpecularTransport,
    ReceiverVisibleFaceCandidates,
    SpecularCandidateSet,
    SpecularComplexityError,
    SpecularSurfaces,
    StratifiedSourceQuadrature,
)
from semantic_twin.transport.specular_sampling import SampledOneBounceSpecularEstimator
from semantic_twin.transport.tracer import SbrTracer, TraceConfig, fresnel_power_reflectance, specular_share
from semantic_twin.materials import AtlasMaterialBinding


class TriangleGeometry:
    """Small vectorized indexed-triangle intersector for controlled scenes."""

    def __init__(self, triangles: np.ndarray) -> None:
        triangles = np.asarray(triangles, dtype=np.float64)
        self.vertices = triangles.reshape(-1, 3)
        self.faces = np.arange(self.vertices.shape[0], dtype=np.int64).reshape(-1, 3)

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    def intersect(self, origins: np.ndarray, directions: np.ndarray):  # noqa: ANN201
        triangle = self.vertices[self.faces]
        edge1 = triangle[:, 1] - triangle[:, 0]
        edge2 = triangle[:, 2] - triangle[:, 0]
        pvec = np.cross(directions[:, None, :], edge2[None, :, :])
        determinant = np.einsum("fj,rfj->rf", edge1, pvec)
        inverse = np.divide(
            1.0,
            determinant,
            out=np.zeros_like(determinant),
            where=np.abs(determinant) > 1.0e-12,
        )
        offset = origins[:, None, :] - triangle[None, :, 0]
        u = np.einsum("rfj,rfj->rf", offset, pvec) * inverse
        qvec = np.cross(offset, edge1[None, :, :])
        v = np.einsum("rj,rfj->rf", directions, qvec) * inverse
        distance = np.einsum("fj,rfj->rf", edge2, qvec) * inverse
        valid = (
            (np.abs(determinant) > 1.0e-12)
            & (u >= -1.0e-9)
            & (v >= -1.0e-9)
            & (u + v <= 1.0 + 1.0e-9)
            & (distance > 1.0e-10)
        )
        distance = np.where(valid, distance, np.inf)
        face = np.argmin(distance, axis=1)
        travel = distance[np.arange(origins.shape[0]), face]
        hit = np.isfinite(travel)
        cross = np.cross(edge1, edge2)
        face_normal = cross / np.linalg.norm(cross, axis=1)[:, None]
        normal = np.where(hit[:, None], face_normal[face], 0.0)
        return hit, np.where(hit, travel, 1.0e30), normal, np.where(hit, face, 0)

    def barycentric_uv(self, face: np.ndarray, point: np.ndarray) -> np.ndarray:
        """Return affine ``(u, v)`` coordinates for atlas-backed fixtures."""
        face = np.asarray(face, dtype=np.int64)
        point = np.asarray(point, dtype=np.float64)
        triangle = self.vertices[self.faces[face]]
        edge1 = triangle[:, 1] - triangle[:, 0]
        edge2 = triangle[:, 2] - triangle[:, 0]
        offset = point - triangle[:, 0]
        gram = np.column_stack(
            (
                np.einsum("ij,ij->i", edge1, edge1),
                np.einsum("ij,ij->i", edge1, edge2),
                np.einsum("ij,ij->i", edge2, edge2),
            )
        )
        q = np.column_stack((np.einsum("ij,ij->i", offset, edge1), np.einsum("ij,ij->i", offset, edge2)))
        determinant = gram[:, 0] * gram[:, 2] - gram[:, 1] ** 2
        return np.column_stack(
            (
                (gram[:, 2] * q[:, 0] - gram[:, 1] * q[:, 1]) / determinant,
                (gram[:, 0] * q[:, 1] - gram[:, 1] * q[:, 0]) / determinant,
            )
        )


PLANE = np.array([[[-20.0, -20.0, 0.0], [20.0, -20.0, 0.0], [0.0, 20.0, 0.0]]])


def _uniform_atlas_mixture(face_count: int = 1) -> AtlasMaterialBinding:
    """A supported two-material atlas with the same posterior at every texel."""
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[..., 0] = 0.25
    probability[..., 1] = 0.75
    return AtlasMaterialBinding(
        face_to_atlas_row=np.zeros(face_count, dtype=np.int32),
        material_probability=probability,
        supported=np.ones((1, 2, 2), dtype=bool),
        valid_texels=np.ones((2, 2), dtype=bool),
        material_names=("m0", "m1"),
        material_class=np.array([1, 2], dtype=np.int32),
        provenance={"rule": "focused fixture"},
    )


def _tracer(triangles: np.ndarray, *, rms_height_m: float = 0.0, rays: int = 32, max_bounces: int = 2):
    geometry = TriangleGeometry(triangles)
    config = TraceConfig(rays=rays, batch=rays, local_cells=32, max_bounces=max_bounces, seed=4)
    tracer = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([PEC_PERMITTIVITY]),
        np.array([rms_height_m]),
        config,
    )
    return tracer


def _plane_solver(*, rms_height_m: float = 0.0) -> OneBounceSpecularTransport:
    return OneBounceSpecularTransport(_tracer(PLANE, rms_height_m=rms_height_m))


def test_distinct_endpoints_have_exact_image_point_transfer_and_arrival_atom() -> None:
    solver = _plane_solver()
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    paths = solver.solve_paired(source, receiver)

    source_image = np.array([-3.0, 0.0, -5.0])
    fraction = receiver[0, 2] / (receiver[0, 2] - source_image[2])
    reflection = receiver[0] + fraction * (source_image - receiver[0])
    length = np.linalg.norm(receiver[0] - source_image)
    cosine = 5.0 / np.linalg.norm(reflection - source[0])
    reflectance = fresnel_power_reflectance(np.array([cosine]), np.array([PEC_PERMITTIVITY]))[0]

    assert paths.reflection_point[0] == pytest.approx(reflection, abs=1.0e-12)
    assert paths.unfolded_length_m[0] == pytest.approx(length, rel=1.0e-12)
    assert paths.transfer[0] == pytest.approx(reflectance / length**2, rel=1.0e-12)
    assert paths.k_hat[0] == pytest.approx((receiver[0] - reflection) / np.linalg.norm(receiver[0] - reflection))
    assert paths.diagnostics.as_dict()["maximum_completed_order"] == 1


def test_partially_rough_plane_keeps_exact_rayleigh_coherent_power_share() -> None:
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    smooth = _plane_solver().solve_paired(source, receiver).total
    rms = 3.0e-4
    rough_solver = _plane_solver(rms_height_m=rms)
    rough = rough_solver.solve_paired(source, receiver).total
    reflection = rough_solver.solve_paired(source, receiver).reflection_point[0]
    cosine = 5.0 / np.linalg.norm(reflection - source[0])
    expected = specular_share(np.array([rms]), np.array([cosine]), rough_solver.tracer.wavelength_m)[0]
    assert rough / smooth == pytest.approx(expected, rel=2.0e-13)


def test_reflecting_face_selects_its_own_material_row() -> None:
    remote = PLANE + np.array([100.0, 0.0, 0.0])
    geometry = TriangleGeometry(np.concatenate((remote, PLANE)))
    dielectric = 4.0 - 0.2j
    tracer = SbrTracer(
        geometry,
        np.array([0, 1]),
        np.array([PEC_PERMITTIVITY, dielectric]),
        np.zeros(2),
        TraceConfig(rays=8, batch=8, local_cells=32, max_bounces=1),
    )
    solver = OneBounceSpecularTransport(tracer)
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    paths = solver.solve_paired(source, receiver, sequences=np.array([[1]]))
    reflection = paths.reflection_point[0]
    cosine = 5.0 / np.linalg.norm(reflection - source[0])
    expected = fresnel_power_reflectance(np.array([cosine]), np.array([dielectric]))[0]
    assert paths.transfer[0] * paths.unfolded_length_m[0] ** 2 == pytest.approx(expected, rel=2.0e-13)


def test_finite_facet_containment_and_either_segment_blocking_reject_paths() -> None:
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    too_small = np.array([[[5.0, 5.0, 0.0], [6.0, 5.0, 0.0], [5.0, 6.0, 0.0]]])
    assert OneBounceSpecularTransport(_tracer(too_small)).solve_paired(source, receiver).total == 0.0

    source_blocker = np.array([[[0.0, -1.0, 0.3], [0.0, 1.0, 0.3], [0.0, 0.0, 1.3]]])
    tracer = _tracer(np.concatenate((PLANE, source_blocker)))
    surfaces = SpecularSurfaces.from_tracer(tracer)
    assert (
        OneBounceSpecularTransport(tracer, surfaces).solve_paired(source, receiver, sequences=np.array([[0]])).total
        == 0.0
    )

    receiver_blocker = np.array([[[1.0, -1.0, 0.3], [1.0, 1.0, 0.3], [1.0, 0.0, 2.5]]])
    tracer = _tracer(np.concatenate((PLANE, receiver_blocker)))
    surfaces = SpecularSurfaces.from_tracer(tracer)
    assert (
        OneBounceSpecularTransport(tracer, surfaces).solve_paired(source, receiver, sequences=np.array([[0]])).total
        == 0.0
    )


def test_normalized_unequal_source_probabilities_and_reciprocity() -> None:
    solver = _plane_solver()
    receiver = np.array([2.0, 0.0, 2.0])
    sources = np.array([[-3.0, 0.0, 5.0], [5.0, 1.0, 4.0]])
    probability = np.array([0.2, 0.8])
    individual = [solver.solve_paired(source[None, :], receiver[None, :]).total for source in sources]
    combined = solver.solve_all_sources(sources, receiver, probability)
    assert combined.total == pytest.approx(np.dot(probability, individual), rel=2.0e-13)

    forward = solver.solve_paired(sources[:1], receiver[None, :])
    reverse = solver.solve_paired(receiver[None, :], sources[:1])
    assert reverse.reflection_point == pytest.approx(forward.reflection_point, abs=1.0e-12)
    assert reverse.total == pytest.approx(forward.total, rel=2.0e-13)
    assert reverse.unfolded_length_m == pytest.approx(forward.unfolded_length_m, rel=2.0e-13)


def test_estimator_adds_all_specular_term_once_and_conserves_the_directional_measure() -> None:
    tracer = _tracer(PLANE, rays=128, max_bounces=1)
    sources = SourceSet(
        positions=np.array([[-3.0, 0.0, 5.0], [5.0, 1.0, 4.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=np.array([1.0, 3.0]),
    )
    estimator = NextEventEstimator(tracer, tracer.geometry, sources, diagnostic_models={"isotropic": ISOTROPIC})
    surplus, field = estimator.estimate_field(np.array([2.0, 0.0, 2.0]), seed=4)

    assert surplus.detail["diffuse_zero_specular_suffix"] == 0.0
    assert surplus.detail["mixed_specular_suffix_order_1"] == 0.0
    assert surplus.detail["all_specular_order_1"] > 0.0
    assert surplus.total == pytest.approx(field.total, rel=2.0e-13)
    assert field.directional_measure(1.0).total == pytest.approx(surplus.total, rel=2.0e-13)
    assert field.includes_specular is True
    assert field.specular_numerically_converged is True
    assert field.specular_bounce_cap == 1
    assert field.specular_order_one_complete is True
    assert field.specular_complete_through_bounce_cap is True
    assert field.specular_result_complete is True
    assert surplus.detail["specular_order_one_complete"] is True
    assert surplus.detail["specular_complete_through_bounce_cap"] is True
    assert surplus.detail["specular_result_complete"] is True
    assert field.as_dict()["specular_result_complete"] is True
    assert field.maximum_completed_all_specular_order == 1
    assert field.maximum_completed_specular_suffix_order == 1
    assert field.missing_specular is True
    higher_cap = replace(field, specular_bounce_cap=2)
    assert higher_cap.specular_order_one_complete is True
    assert higher_cap.specular_complete_through_bounce_cap is False
    assert higher_cap.specular_result_complete is False
    assert higher_cap.maximum_completed_all_specular_order == 1
    assert higher_cap.maximum_completed_specular_suffix_order == 1


def test_tx_specular_diffuse_receiver_suffix_is_decisive_and_an_exact_atom() -> None:
    blocker = np.array([[[0.0, -1.0, 3.0], [0.0, 1.0, 3.0], [0.0, 0.0, 5.0]]])
    tracer = _tracer(np.concatenate((PLANE, blocker)), rays=1, max_bounces=2)
    plane_only = SpecularSurfaces.from_tracer(tracer)
    plane_only = SpecularSurfaces(
        plane_only.triangles[:1],
        plane_only.normals[:1],
        plane_only.face_index[:1],
        plane_only.material_class[:1],
    )
    source = SourceSet(np.array([[4.0, 0.0, 4.0]]), 1.0, 3, 0, 0)
    gather = NextEventGather(
        tracer.geometry,
        source,
        np.random.default_rng(2),
        max_order=2,
        field_grid=tracer.local_grid,
        specular_transport=OneBounceSpecularTransport(tracer, plane_only),
    )
    receiver = np.array([-4.0, -5.0, 4.0])
    diffuse = np.array([[-4.0, 0.0, 4.0]])
    incoming = np.array([[0.0, 1.0, 0.0]])
    normal = np.array([[1.0, 0.0, -1.0]]) / math.sqrt(2.0)
    gather.begin(receiver, 1)
    gather.set_launch_cells(np.array([0]))
    gather.vertex(
        np.array([0]),
        diffuse,
        incoming,
        normal,
        np.array([1.0]),
        np.array([0.0]),
        np.array([1]),
        np.array([5.0]),
        np.array([1]),
    )

    assert gather.chi_bounce() == 0.0
    assert gather.chi_specular_suffix() > 0.0
    reflectance = fresnel_power_reflectance(
        np.array([1.0 / math.sqrt(2.0)]),
        np.array([PEC_PERMITTIVITY]),
    )[0]
    assert gather.chi_specular_suffix() == pytest.approx(reflectance / 32.0, rel=2.0e-13)
    k_hat, mass = gather.specular_atoms()
    np.testing.assert_allclose(k_hat, [[0.0, -1.0, 0.0]], atol=1.0e-14)
    assert mass.sum() == pytest.approx(gather.chi_specular_suffix(), rel=2.0e-13)
    field = gather.field()
    assert field.total == pytest.approx(gather.chi_specular_suffix(), rel=2.0e-13)
    assert field.directional_measure(1.0).total == pytest.approx(field.total, rel=2.0e-13)


def test_candidate_work_is_chunked_and_scales_as_pairs_times_planes() -> None:
    planes = np.concatenate([PLANE + np.array([40.0 * i, 0.0, 0.0]) for i in range(7)])
    tracer = _tracer(planes)
    solver = OneBounceSpecularTransport(tracer, candidate_chunk=31)
    pairs = 23
    source = np.tile(np.array([-3.0, 0.0, 5.0]), (pairs, 1))
    receiver = np.tile(np.array([2.0, 0.0, 2.0]), (pairs, 1))
    paths = solver.solve_paired(source, receiver)
    diagnostics = paths.diagnostics
    assert diagnostics.candidates == pairs * planes.shape[0]
    assert diagnostics.chunks == math.ceil(diagnostics.candidates / 31)
    assert diagnostics.endpoint_pairs == pairs
    assert diagnostics.plane_sequences == planes.shape[0]
    with pytest.raises(NotImplementedError, match="maximum completed specular order is one"):
        solver.solve_paired(source, receiver, sequences=np.array([[0, 1]]))


def test_source_and_triangle_order_only_permute_atoms_not_total_transfer() -> None:
    """Explicit endpoint and plane order are labels, not physical weights."""
    planes = np.concatenate((PLANE, PLANE + np.array([0.0, 4.0, 0.0])))
    solver = OneBounceSpecularTransport(_tracer(planes), candidate_chunk=1)
    sources = np.array([[-3.0, 0.0, 5.0], [4.0, 1.0, 6.0], [2.0, -2.0, 3.0]])
    receiver = np.array([2.0, 0.0, 2.0])
    probabilities = np.array([0.2, 0.5, 0.3])
    forward = solver.solve_all_sources(sources, receiver, probabilities)
    reverse = solver.solve_all_sources(sources[::-1], receiver, probabilities[::-1])
    assert reverse.total == pytest.approx(forward.total, rel=2.0e-13)

    surfaces = solver.surfaces
    reordered = SpecularSurfaces(
        surfaces.triangles[::-1],
        surfaces.normals[::-1],
        surfaces.face_index[::-1],
        surfaces.material_class[::-1],
    )
    reordered_paths = OneBounceSpecularTransport(solver.tracer, reordered, candidate_chunk=1).solve_all_sources(
        sources, receiver, probabilities
    )
    assert reordered_paths.total == pytest.approx(forward.total, rel=2.0e-13)


def test_candidate_chunk_size_does_not_change_paths_or_transfer() -> None:
    planes = np.concatenate([PLANE + np.array([0.0, 8.0 * i, 0.0]) for i in range(3)])
    tracer = _tracer(planes)
    sources = np.array([[-3.0, 0.0, 5.0], [4.0, 1.0, 6.0], [2.0, -2.0, 3.0]])
    receivers = np.tile(np.array([2.0, 0.0, 2.0]), (sources.shape[0], 1))
    small = OneBounceSpecularTransport(tracer, candidate_chunk=1).solve_paired(sources, receivers)
    large = OneBounceSpecularTransport(tracer, candidate_chunk=1000).solve_paired(sources, receivers)
    np.testing.assert_allclose(small.k_hat, large.k_hat, rtol=0.0, atol=1.0e-14)
    np.testing.assert_allclose(small.transfer, large.transfer, rtol=0.0, atol=1.0e-14)
    np.testing.assert_allclose(small.reflection_point, large.reflection_point, rtol=0.0, atol=1.0e-14)
    assert small.total == pytest.approx(large.total, rel=2.0e-13)


def test_paired_surface_kernel_matches_individual_exact_solves() -> None:
    planes = np.concatenate((PLANE, PLANE + np.array([0.0, 40.0, 0.0])))
    solver = OneBounceSpecularTransport(_tracer(planes), candidate_chunk=2)
    sources = np.array(
        [
            [-3.0, 0.0, 5.0],
            [-3.0, 40.0, 5.0],
            [-3.0, 0.0, 5.0],
            [4.0, 1.0, 6.0],
        ]
    )
    receivers = np.array(
        [
            [2.0, 0.0, 2.0],
            [2.0, 40.0, 2.0],
            [2.0, 0.0, 2.0],
            [1.0, -1.0, 2.0],
        ]
    )
    surface = np.array([0, 1, 1, 0])
    weight = np.array([0.2, 0.3, 0.4, 0.5])
    source_id = np.array([8, 7, 6, 5])

    paired = solver.solve_paired_surfaces(
        sources,
        receivers,
        surface,
        endpoint_weight=weight,
        source_index=source_id,
    )
    individual = [
        solver.solve_paired(
            sources[index : index + 1],
            receivers[index : index + 1],
            endpoint_weight=weight[index : index + 1],
            source_index=source_id[index : index + 1],
            sequences=surface[index : index + 1, None],
        )
        for index in range(sources.shape[0])
    ]
    accepted_endpoint = np.array(
        [index for index, paths in enumerate(individual) if paths.transfer.size],
        dtype=np.int64,
    )

    np.testing.assert_allclose(paired.k_hat, np.concatenate([p.k_hat for p in individual if p.transfer.size]))
    np.testing.assert_allclose(paired.transfer, np.concatenate([p.transfer for p in individual if p.transfer.size]))
    np.testing.assert_allclose(
        paired.reflection_point,
        np.concatenate([p.reflection_point for p in individual if p.transfer.size]),
    )
    np.testing.assert_array_equal(paired.source_index, source_id[accepted_endpoint])
    np.testing.assert_array_equal(paired.endpoint_index, accepted_endpoint)
    np.testing.assert_array_equal(
        paired.surface_sequence,
        np.concatenate([p.surface_sequence for p in individual if p.transfer.size]),
    )
    np.testing.assert_allclose(
        paired.unfolded_length_m,
        np.concatenate([p.unfolded_length_m for p in individual if p.transfer.size]),
    )
    assert paired.diagnostics.geometric == sum(p.diagnostics.geometric for p in individual)
    assert paired.diagnostics.visible == sum(p.diagnostics.visible for p in individual)
    assert paired.diagnostics.accepted == sum(p.diagnostics.accepted for p in individual)
    assert paired.diagnostics.candidates == sources.shape[0]
    assert paired.diagnostics.chunks == 2
    assert paired.diagnostics.candidate_method == "paired_explicit_surfaces"


def test_paired_surface_kernel_validates_indices_budget_and_chunk_count() -> None:
    sources = np.repeat(np.array([[-3.0, 0.0, 5.0]]), 5, axis=0)
    receivers = np.repeat(np.array([[2.0, 0.0, 2.0]]), 5, axis=0)
    surfaces = np.zeros(5, dtype=np.int64)
    chunked = OneBounceSpecularTransport(_tracer(PLANE), candidate_chunk=2).solve_paired_surfaces(
        sources, receivers, surfaces
    )
    assert chunked.diagnostics.chunks == 3
    with pytest.raises(ValueError, match="surface_index must match"):
        OneBounceSpecularTransport(_tracer(PLANE)).solve_paired_surfaces(sources, receivers, surfaces[:-1])
    for invalid in (
        np.zeros(5, dtype=bool),
        np.zeros(5, dtype=np.float64),
        np.full(5, "0"),
        np.full(5, np.nan),
    ):
        with pytest.raises(ValueError, match="must contain integer"):
            OneBounceSpecularTransport(_tracer(PLANE)).solve_paired_surfaces(sources, receivers, invalid)
    with pytest.raises(ValueError, match="unknown specular surface"):
        OneBounceSpecularTransport(_tracer(PLANE)).solve_paired_surfaces(sources, receivers, np.ones(5, dtype=int))
    with pytest.raises(SpecularComplexityError, match="exceeding budget"):
        OneBounceSpecularTransport(_tracer(PLANE), candidate_budget=4).solve_paired_surfaces(
            sources, receivers, surfaces
        )


@pytest.mark.filterwarnings("error")
def test_non_geometric_infinite_fraction_is_sanitized_without_changing_valid_paths() -> None:
    solver = _plane_solver()
    valid_source = np.array([[-3.0, 0.0, 5.0]])
    valid_receiver = np.array([[2.0, 0.0, 2.0]])
    expected = solver.solve_paired_surfaces(valid_source, valid_receiver, np.array([0]))

    paths = solver.solve_paired_surfaces(
        np.concatenate((valid_source, [[0.0, 0.0, 1.0]])),
        np.concatenate((valid_receiver, [[0.0, 0.0, -1.0]])),
        np.array([0, 0]),
    )

    assert paths.diagnostics.candidates == 2
    assert paths.diagnostics.geometric == 1
    assert paths.diagnostics.accepted == 1
    np.testing.assert_array_equal(paths.endpoint_index, [0])
    np.testing.assert_array_equal(paths.k_hat, expected.k_hat)
    np.testing.assert_array_equal(paths.reflection_point, expected.reflection_point)
    np.testing.assert_array_equal(paths.transfer, expected.transfer)
    np.testing.assert_array_equal(paths.unfolded_length_m, expected.unfolded_length_m)


def test_atlas_material_mixture_is_used_at_the_exact_reflection_point() -> None:
    """The image solve must use posterior Fresnel/Rayleigh mixtures, not fallback class."""
    triangle = np.array([[[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0]]])
    geometry = TriangleGeometry(triangle)
    permittivity = np.array([PEC_PERMITTIVITY, 4.0 - 0.2j, 9.0 - 0.4j])
    rms_height = np.array([0.0, 0.0, 3.0e-4])
    tracer = SbrTracer(
        geometry,
        np.array([0]),
        permittivity,
        rms_height,
        TraceConfig(rays=8, batch=8, local_cells=16, max_bounces=1),
        atlas_material=_uniform_atlas_mixture(),
    )
    source = np.array([[2.0, 2.0, 5.0]])
    receiver = np.array([[2.0, 2.0, 2.0]])
    paths = OneBounceSpecularTransport(tracer).solve_paired(source, receiver)
    assert paths.total > 0.0
    reflection = paths.reflection_point[0]
    cosine = 5.0 / np.linalg.norm(reflection - source[0])
    component_r = fresnel_power_reflectance(np.array([[cosine]]), permittivity[[1, 2]])[0]
    component_s = specular_share(rms_height[[1, 2]], np.array([cosine]), tracer.wavelength_m)
    expected_reflectance = 0.25 * component_r[0] + 0.75 * component_r[1]
    expected_share = (
        0.25 * component_r[0] * component_s[0] + 0.75 * component_r[1] * component_s[1]
    ) / expected_reflectance
    expected = expected_reflectance * expected_share / paths.unfolded_length_m[0] ** 2
    assert paths.transfer[0] == pytest.approx(expected, rel=2.0e-13)


def test_grazing_or_degenerate_candidates_are_rejected_and_non_mesh_is_empty() -> None:
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    degenerate = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]])
    with pytest.raises(ValueError, match="nondegenerate"):
        SpecularSurfaces(degenerate, np.array([[0.0, 0.0, 1.0]]), np.array([0]), np.array([0]))
    assert SpecularSurfaces.from_tracer(_tracer(degenerate)).triangles.shape == (0, 3, 3)

    grazing_solver = _plane_solver()
    grazing_source = np.array([[0.0, 0.0, 1.0e-10]])
    grazing_paths = grazing_solver.solve_paired(grazing_source, receiver)
    assert grazing_paths.total == 0.0
    assert grazing_paths.diagnostics.geometric == 0

    legacy = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        TraceConfig(rays=1, batch=1, local_cells=8, max_bounces=1),
    )
    legacy_paths = OneBounceSpecularTransport(legacy).solve_paired(source, receiver)
    assert legacy_paths.total == 0.0
    assert legacy_paths.diagnostics.as_dict()["maximum_completed_order"] == 1


def test_duplicate_coplanar_faces_do_not_double_count_the_image_path() -> None:
    source = np.array([[-3.0, 0.0, 5.0]])
    receiver = np.array([[2.0, 0.0, 2.0]])
    one = _plane_solver().solve_paired(source, receiver)
    duplicate = OneBounceSpecularTransport(_tracer(np.concatenate((PLANE, PLANE)))).solve_paired(source, receiver)
    assert duplicate.total == pytest.approx(one.total, rel=2.0e-13)
    assert duplicate.diagnostics.geometric == 2
    assert duplicate.diagnostics.accepted == 1


def test_work_budget_is_checked_before_candidate_allocation_and_is_auditable() -> None:
    tracer = _tracer(PLANE)
    solver = OneBounceSpecularTransport(tracer, candidate_budget=1)
    estimate = solver.work_estimate(sources=2, rays=10, samples=1, max_bounces=1)
    assert estimate.all_specular_candidates == 2
    assert estimate.total_candidates_upper_bound == 2
    assert estimate.enabled is False
    assert "exceeds candidate budget" in estimate.reason
    with pytest.raises(SpecularComplexityError, match="exceeding budget"):
        solver.solve_paired(np.tile(np.array([-3.0, 0.0, 5.0]), (2, 1)), np.tile(np.array([2.0, 0.0, 2.0]), (2, 1)))


def test_diagnostics_name_candidate_method_and_support_completeness() -> None:
    solver = _plane_solver()
    paths = solver.solve_paired(np.array([[-3.0, 0.0, 5.0]]), np.array([[2.0, 0.0, 2.0]]))
    diagnostics = paths.diagnostics.as_dict()
    assert diagnostics["candidate_method"] == "all_verified_surfaces"
    assert diagnostics["candidate_support_complete"] is True
    assert diagnostics["selected_faces"] == diagnostics["support_faces"] == 1
    assert diagnostics["missed_support_faces"] == 0
    assert diagnostics["maximum_completed_order"] == 1

    incomplete = SpecularCandidateSet(np.array([[0]], dtype=np.int64), method="explicit_subset")
    subset_paths = solver.solve_paired(
        np.array([[-3.0, 0.0, 5.0]]),
        np.array([[2.0, 0.0, 2.0]]),
        candidate_set=incomplete,
    )
    assert subset_paths.diagnostics.candidate_support_complete is False
    assert subset_paths.diagnostics.missed_support_faces is None


def test_next_event_budget_refusal_is_explicit_and_marks_specular_order_missing() -> None:
    tracer = _tracer(PLANE, rays=32, max_bounces=1)
    sources = SourceSet(
        positions=np.array([[-3.0, 0.0, 5.0], [4.0, 1.0, 6.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )
    estimator = NextEventEstimator(
        tracer,
        tracer.geometry,
        sources,
        max_order=1,
        specular_candidate_budget=1,
    )
    surplus, field = estimator.estimate_field(np.array([2.0, 0.0, 2.0]), seed=4)
    assert surplus.detail["specular_work"]["enabled"] is False
    assert surplus.detail["all_specular_order_1_included"] is False
    assert surplus.detail["all_specular_order_1_missing"] is True
    assert field.specular_work["enabled"] is False
    assert field.includes_specular is False
    assert field.maximum_completed_all_specular_order == 0
    assert field.specular_order_one_complete is False
    assert field.specular_complete_through_bounce_cap is False
    assert surplus.detail["specular_order_one_complete"] is False
    assert surplus.detail["specular_complete_through_bounce_cap"] is False
    assert surplus.detail["specular_result_complete"] is False


def _curve_source_set(count: int = 32) -> SourceSet:
    points = np.column_stack(
        (
            np.linspace(-3.5, 3.5, count),
            np.zeros(count),
            np.full(count, 5.0),
        )
    )
    curve = FacadeTipCurve(points, np.ones(count), {"fixture": True})
    return SourceSet.from_curve(curve)


def test_finite_resolution_refinement_crosses_receiver_faces_and_source_strata() -> None:
    tracer = _tracer(PLANE, rays=16, max_bounces=1)
    estimator = NextEventEstimator(
        tracer,
        tracer.geometry,
        _curve_source_set(),
        max_order=1,
        specular_candidate_budget=21,
        specular_transport=OneBounceSpecularTransport(tracer, candidate_budget=21),
        visible_face_candidates=ReceiverVisibleFaceCandidates((3,)),
        source_quadrature=StratifiedSourceQuadrature((1,)),
    )

    surplus, field = estimator.estimate_field(np.array([0.0, 0.0, 2.0]), seed=1)
    work = surplus.detail["finite_resolution_specular_work"]
    refinement = surplus.detail["specular_source_refinement"]

    assert work["enabled"] is True
    assert work["method"] == "adaptive_receiver_faces_and_probability_strata"
    assert work["candidate_work_used"] == 6
    assert work["visibility_rays_used"] == 15
    assert work["refinement_work_used"] == 21
    assert work["refinement_work_used"] <= work["candidate_budget"]
    assert work["support_complete"] is False
    assert work["mixed_specular_suffix_enabled"] is False
    assert work["numerically_converged"] is False
    assert work["stop_reason"] == "candidate_budget_exhausted"
    assert len(refinement) == 4
    assert [row["axis_refined"] for row in refinement] == [
        "initial",
        "source_quadrature",
        "receiver_faces",
        "crossed_corner",
    ]
    assert [row["angular_samples"] for row in refinement] == [3, 3, 12, 12]
    assert [row["requested_strata"] for row in refinement] == [1, 2, 1, 2]
    for row in refinement:
        assert row["candidates"] == row["selected_faces"] * row["selected_sources"]
        assert 0 <= row["accepted"] <= row["candidates"]
        assert row["candidate_support_complete"] is False
        assert row["source_support_complete"] is False
        assert row["finite_resolution_support_incomplete"] is True
        assert np.isfinite(row["transfer"]) and row["transfer"] >= 0.0
        assert np.isfinite(row["seconds"]) and row["seconds"] >= 0.0
        for key in (
            "absolute_change_from_previous_face_level",
            "relative_change_from_previous_face_level",
            "absolute_change_from_previous_source_level",
            "relative_change_from_previous_source_level",
        ):
            change = row[key]
            assert change is None or (np.isfinite(change) and change >= 0.0)

    assert surplus.detail["specular_estimate_kind"] == "finite_resolution_order_1"
    assert surplus.detail["finite_resolution_specular_estimate"] is True
    assert surplus.detail["specular_numerically_converged"] is False
    assert surplus.detail["specular_order_one_complete"] is False
    assert surplus.detail["specular_complete_through_bounce_cap"] is False
    assert surplus.detail["specular_result_complete"] is False
    assert field.includes_specular is True
    assert field.missing_specular is True
    assert field.maximum_completed_all_specular_order == 0
    assert field.maximum_completed_specular_suffix_order == 0
    assert field.specular_numerically_converged is False
    assert field.specular_order_one_complete is False
    assert field.specular_complete_through_bounce_cap is False
    assert field.specular_result_complete is False
    assert len(field.specular_source_refinement) == 4


def test_adaptive_refinement_stops_at_tolerance_without_claiming_complete_support() -> None:
    tracer = _tracer(PLANE, rays=16, max_bounces=1)
    estimator = NextEventEstimator(
        tracer,
        tracer.geometry,
        _curve_source_set(),
        max_order=1,
        specular_candidate_budget=21,
        specular_transport=OneBounceSpecularTransport(tracer, candidate_budget=21),
        visible_face_candidates=ReceiverVisibleFaceCandidates((3,)),
        source_quadrature=StratifiedSourceQuadrature((1,)),
        specular_refinement_relative_tolerance=0.1,
    )

    surplus, field = estimator.estimate_field(np.array([0.0, 0.0, 2.0]), seed=1)
    work = surplus.detail["finite_resolution_specular_work"]
    corner = surplus.detail["specular_source_refinement"][-1]

    assert work["stop_reason"] == "relative_tolerance_reached"
    assert work["numerically_converged"] is True
    assert corner["face_axis_converged"] is True
    assert corner["source_axis_converged"] is True
    assert corner["numerically_converged"] is True
    assert corner["relative_change_from_previous_face_level"] <= 0.1
    assert corner["relative_change_from_previous_source_level"] <= 0.1
    assert surplus.detail["specular_numerically_converged"] is True
    assert surplus.detail["maximum_completed_all_specular_order"] == 0
    assert surplus.detail["all_specular_order_1_missing"] is True
    assert field.specular_numerically_converged is True
    assert field.maximum_completed_all_specular_order == 0
    assert field.missing_specular is True


@pytest.mark.parametrize(("tolerance", "converged"), ((0.1, True), (0.02, False)))
def test_sampled_suffix_keeps_formal_completion_separate_from_adaptive_convergence(
    tolerance: float, converged: bool
) -> None:
    tracer = _tracer(PLANE, rays=16, max_bounces=2)
    estimator = NextEventEstimator(
        tracer,
        tracer.geometry,
        _curve_source_set(),
        max_order=2,
        specular_candidate_budget=21,
        specular_transport=OneBounceSpecularTransport(tracer, candidate_budget=21),
        visible_face_candidates=ReceiverVisibleFaceCandidates((3,)),
        source_quadrature=StratifiedSourceQuadrature((1,)),
        specular_refinement_relative_tolerance=tolerance,
        specular_suffix_mode="sampled",
        sampled_specular_samples=2,
    )

    surplus, field = estimator.estimate_field(np.array([0.0, 0.0, 2.0]), seed=1)

    assert field.specular_estimate_kind == "adaptive_all_sampled_mixed_order_1"
    assert field.sampled_specular_suffix_full_support is True
    assert field.maximum_completed_all_specular_order == 0
    assert field.maximum_completed_specular_suffix_order == 0
    assert field.specular_order_one_complete is False
    assert field.specular_complete_through_bounce_cap is False
    assert field.specular_numerically_converged is converged
    assert surplus.detail["sampled_specular_suffix_full_support"] is True
    assert surplus.detail["finite_resolution_specular_work"]["numerically_converged"] is converged
    assert surplus.detail["finite_resolution_specular_work"]["stop_reason"] == (
        "relative_tolerance_reached" if converged else "candidate_budget_exhausted"
    )


def test_sampled_mixed_suffix_is_absent_without_term_and_matches_exact_quadrature_ci() -> None:
    triangles = np.concatenate([PLANE + np.array([0.0, 100.0 * index, 0.0]) for index in range(8)])
    tracer = _tracer(triangles, rays=1, max_bounces=2)
    sources = SourceSet(
        positions=np.array([[-3.0, 0.0, 5.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )
    transport = OneBounceSpecularTransport(tracer, candidate_budget=100_000)
    sampler = SampledOneBounceSpecularEstimator(transport, sources)
    receiver = np.array([2.0, 0.0, 2.0])
    exact_paths = transport.solve_all_sources(sources.sites(), receiver, np.array([1.0]))
    toward_reflection = -exact_paths.k_hat[0]
    normal = toward_reflection[None, :]
    exact_raw = float(np.dot(toward_reflection, normal[0]) * exact_paths.total)
    exact_chi = 4.0 * np.pi * exact_raw

    def gathered(seed: int, sampled: bool, samples_per_vertex: int = 2_000) -> float:
        gather = NextEventGather(
            geometry=tracer.geometry,
            sources=sources,
            rng=np.random.default_rng(99),
            samples=1,
            max_order=2,
            field_grid=np.array([[0.0, 0.0, 1.0]]),
            sampled_specular_estimator=sampler if sampled else None,
            sampled_specular_samples=samples_per_vertex,
            sampled_specular_seed=seed,
        )
        gather.begin(receiver, 1)
        gather.set_launch_cells(np.array([0]))
        gather.vertex(
            np.array([0]),
            receiver[None, :],
            -np.array([[0.0, 0.0, 1.0]]),
            normal,
            np.array([np.pi]),
            np.array([0.0]),
            np.array([1]),
            np.array([1.0]),
        )
        return gather.chi_specular_suffix()

    assert gathered(0, False) == 0.0
    replicas = np.array([gathered(seed, True) for seed in range(24)])
    standard_error = float(np.std(replicas, ddof=1) / np.sqrt(replicas.size))
    assert abs(float(np.mean(replicas)) - exact_chi) <= 3.0 * standard_error
    coarse = np.array([gathered(seed, True, 500) for seed in range(24)])
    coarse_standard_error = float(np.std(coarse, ddof=1) / np.sqrt(coarse.size))
    assert abs(float(np.mean(coarse)) - exact_chi) <= 3.0 * coarse_standard_error
    combined_standard_error = np.hypot(standard_error, coarse_standard_error)
    assert abs(float(np.mean(replicas)) - float(np.mean(coarse))) <= 3.0 * combined_standard_error


def test_sampled_mixed_field_atoms_are_replica_specific_but_repeatable() -> None:
    triangles = np.array(
        [
            [[-5.0, -1.0, 0.0], [-1.0, -1.0, 0.0], [-3.0, 0.0, 0.0]],
            [[4.0, -0.1, 0.0], [6.0, -0.1, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    sources = SourceSet(
        positions=np.array([[-10.5, 0.0, 5.0], [17.5, 0.0, 5.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=np.array([0.2, 0.8]),
    )
    tracer = _tracer(triangles, rays=1, max_bounces=2)
    sampler = SampledOneBounceSpecularEstimator(OneBounceSpecularTransport(tracer), sources)
    receiver = np.array([0.0, 0.0, 2.0])

    def gathered(seed: int) -> NextEventField:
        gather = NextEventGather(
            geometry=tracer.geometry,
            sources=sources,
            rng=np.random.default_rng(99),
            samples=1,
            max_order=2,
            field_grid=np.array([[0.0, 0.0, 1.0]]),
            sampled_specular_estimator=sampler,
            sampled_specular_samples=100,
            sampled_specular_seed=seed,
        )
        gather.begin(receiver, 1)
        gather.set_launch_cells(np.array([0]))
        gather.vertex(
            np.array([0]),
            receiver[None, :],
            -np.array([[0.0, 0.0, 1.0]]),
            np.array([[0.0, 0.0, -1.0]]),
            np.array([np.pi]),
            np.array([0.0]),
            np.array([1]),
            np.array([1.0]),
        )
        return gather.field()

    first = gathered(1)
    second = gathered(2)
    repeated = gathered(1)
    assert first.mixed_specular_mass > 0.0
    assert second.mixed_specular_mass > 0.0
    assert first.mixed_specular_mass != second.mixed_specular_mass
    assert first.specular_atom_mass.size != 0
    np.testing.assert_array_equal(first.mixed_specular_atom_mass, repeated.mixed_specular_atom_mass)
    np.testing.assert_array_equal(first.mixed_specular_k_hat, repeated.mixed_specular_k_hat)
    assert first.sampled_specular_suffix_full_support is True


def test_deterministic_specular_and_direct_caches_reuse_across_seeds_with_timing_schema() -> None:
    tracer = _tracer(PLANE, rms_height_m=3.0e-3, rays=64, max_bounces=2)
    estimator = NextEventEstimator(
        tracer,
        tracer.geometry,
        _curve_source_set(),
        max_order=2,
        specular_candidate_budget=21,
        visible_face_candidates=ReceiverVisibleFaceCandidates((3, 9, 27)),
        source_quadrature=StratifiedSourceQuadrature((1, 2, 4)),
    )
    origin = np.array([0.0, 0.0, 2.0])
    first, _ = estimator.estimate_field(origin, seed=1)
    second, _ = estimator.estimate_field(origin, seed=2)

    assert first.detail["deterministic_specular_cache_hit"] is False
    assert first.detail["direct_cache_hit"] is False
    assert second.detail["deterministic_specular_cache_hit"] is True
    assert second.detail["direct_cache_hit"] is True
    assert second.detail["deterministic_specular_seconds"] == 0.0
    assert second.detail["direct_seconds"] == 0.0
    assert first.detail["timing_components_non_overlapping"] == [
        "deterministic_specular_seconds",
        "direct_seconds",
        "stochastic_trace_seconds",
        "estimator_overhead_seconds",
    ]
    for detail in (first.detail, second.detail):
        for key in (
            "deterministic_specular_seconds",
            "direct_seconds",
            "stochastic_trace_seconds",
            "specular_suffix_seconds_in_stochastic_trace",
            "estimator_wall_seconds",
            "estimator_overhead_seconds",
        ):
            assert np.isfinite(detail[key]) and detail[key] >= 0.0
        measured = (
            detail["deterministic_specular_seconds"] + detail["direct_seconds"] + detail["stochastic_trace_seconds"]
        )
        assert detail["estimator_wall_seconds"] + 1.0e-12 >= measured
        assert detail["estimator_overhead_seconds"] == pytest.approx(
            max(detail["estimator_wall_seconds"] - measured, 0.0), abs=1.0e-12
        )

    assert first.detail["by_order"] != second.detail["by_order"]
    assert first.detail["diffuse_zero_specular_suffix"] != second.detail["diffuse_zero_specular_suffix"]

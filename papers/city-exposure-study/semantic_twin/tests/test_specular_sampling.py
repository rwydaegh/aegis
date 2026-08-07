"""Unbiased sampled one-reflection transport against the exact CPU oracle."""

from __future__ import annotations

import numpy as np
import pytest

import semantic_twin.transport as transport_api
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.transport.specular import OneBounceSpecularTransport, SpecularSurfaces
from semantic_twin.transport.specular_sampling import SampledOneBounceSpecularEstimator
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


class TriangleGeometry:
    """Small vectorized indexed-triangle intersector for analytic scenes."""

    def __init__(self, triangles: np.ndarray) -> None:
        triangle = np.asarray(triangles, dtype=np.float64)
        self.vertices = triangle.reshape(-1, 3)
        self.faces = np.arange(self.vertices.shape[0], dtype=np.int64).reshape(-1, 3)

    def intersect(self, origins: np.ndarray, directions: np.ndarray):  # noqa: ANN201
        triangle = self.vertices[self.faces]
        edge1 = triangle[:, 1] - triangle[:, 0]
        edge2 = triangle[:, 2] - triangle[:, 0]
        pvec = np.cross(directions[:, None, :], edge2[None, :, :])
        determinant = np.einsum("fj,rfj->rf", edge1, pvec)
        inverse = np.divide(1.0, determinant, out=np.zeros_like(determinant), where=np.abs(determinant) > 1.0e-12)
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


PLANE = np.array([[[-20.0, -20.0, 0.0], [20.0, -20.0, 0.0], [0.0, 20.0, 0.0]]])
SOURCE = np.array([-3.0, 0.0, 5.0])
RECEIVER = np.array([2.0, 0.0, 2.0])


def _tracer(triangles: np.ndarray, *, rms_height_m: float = 0.0) -> SbrTracer:
    geometry = TriangleGeometry(triangles)
    return SbrTracer(
        geometry,
        np.zeros(geometry.faces.shape[0], dtype=np.int64),
        np.array([PEC_PERMITTIVITY]),
        np.array([rms_height_m]),
        TraceConfig(rays=8, batch=8, local_cells=16, max_bounces=2, seed=4),
    )


def _sources(positions: np.ndarray, weights: np.ndarray | None = None) -> SourceSet:
    return SourceSet(np.asarray(positions), 1.0, 3, 0, 0, source_weights=weights)


def _square(subdivisions: int) -> np.ndarray:
    coordinate = np.linspace(-10.0, 10.0, subdivisions + 1)
    out = []
    for x0, x1 in zip(coordinate[:-1], coordinate[1:], strict=True):
        for y0, y1 in zip(coordinate[:-1], coordinate[1:], strict=True):
            out.extend(
                (
                    [[x0, y0, 0.0], [x1, y0, 0.0], [x1, y1, 0.0]],
                    [[x0, y0, 0.0], [x1, y1, 0.0], [x0, y1, 0.0]],
                )
            )
    return np.asarray(out, dtype=np.float64)


def test_face_proposal_is_exact_area_uniform_mixture_with_full_support() -> None:
    triangles = np.array(
        [
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            [[10.0, 0.0, 0.0], [14.0, 0.0, 0.0], [10.0, 2.0, 0.0]],
        ]
    )
    estimator = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(_tracer(triangles)),
        _sources(SOURCE[None, :]),
    )
    area = np.array([1.0, 4.0])
    expected = 0.9 * area / area.sum() + 0.1 / 2

    np.testing.assert_allclose(estimator.face_area, area, rtol=0.0, atol=1.0e-15)
    np.testing.assert_allclose(estimator.face_probability, expected, rtol=0.0, atol=1.0e-15)
    assert np.all(estimator.face_probability > 0.0)
    assert transport_api.SampledOneBounceSpecularEstimator is SampledOneBounceSpecularEstimator
    assert transport_api.SampledSpecularDiagnostics.__module__.endswith("specular_sampling")
    assert transport_api.SampledSpecularResult.__module__.endswith("specular_sampling")


def test_counter_draws_are_seed_repeatable_and_batch_boundary_invariant() -> None:
    estimator = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(_tracer(_square(1))),
        _sources(np.array([SOURCE, [4.0, 1.0, 6.0]]), np.array([1.0, 3.0])),
    )
    whole = estimator.estimate(RECEIVER, samples=37, seed=908, counter_start=11)
    repeated = estimator.estimate(RECEIVER, samples=37, seed=908, counter_start=11)
    first = estimator.estimate(RECEIVER, samples=13, seed=908, counter_start=11)
    second = estimator.estimate(RECEIVER, samples=24, seed=908, counter_start=24)

    np.testing.assert_array_equal(whole.drawn_source_index, repeated.drawn_source_index)
    np.testing.assert_array_equal(whole.drawn_surface_index, repeated.drawn_surface_index)
    np.testing.assert_array_equal(
        whole.drawn_source_index,
        np.concatenate((first.drawn_source_index, second.drawn_source_index)),
    )
    np.testing.assert_array_equal(
        whole.drawn_surface_index,
        np.concatenate((first.drawn_surface_index, second.drawn_surface_index)),
    )
    np.testing.assert_array_equal(whole.trial_transfer, np.concatenate((first.trial_transfer, second.trial_transfer)))
    assert whole.diagnostics.counter_start == 11
    assert whole.diagnostics.counter_stop == 48


def test_candidate_budget_chunking_does_not_change_draws_or_deposits() -> None:
    sources = _sources(np.array([SOURCE, [4.0, 1.0, 6.0]]), np.array([1.0, 3.0]))
    tracer = _tracer(_square(1))
    narrow = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(tracer, candidate_budget=7),
        sources,
    ).estimate(RECEIVER, samples=101, seed=72)
    wide = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(tracer, candidate_budget=10_000),
        sources,
    ).estimate(RECEIVER, samples=101, seed=72)

    np.testing.assert_array_equal(narrow.drawn_source_index, wide.drawn_source_index)
    np.testing.assert_array_equal(narrow.drawn_surface_index, wide.drawn_surface_index)
    np.testing.assert_array_equal(narrow.trial_transfer, wide.trial_transfer)
    np.testing.assert_array_equal(narrow.k_hat, wide.k_hat)
    np.testing.assert_array_equal(narrow.mass, wide.mass)
    assert narrow.diagnostics.solver_calls > wide.diagnostics.solver_calls


def test_many_sampled_faces_are_solved_in_contiguous_trial_chunks() -> None:
    transport = OneBounceSpecularTransport(_tracer(_square(16)), candidate_chunk=1_000)
    result = SampledOneBounceSpecularEstimator(transport, _sources(SOURCE[None, :])).estimate(
        RECEIVER,
        samples=5_000,
        seed=72,
    )

    assert np.unique(result.drawn_surface_index).size > 500
    assert result.diagnostics.solver_calls == 5
    assert result.diagnostics.solver_calls < np.unique(result.drawn_surface_index).size / 100


def test_high_count_many_face_reduction_conserves_directional_and_order_mass() -> None:
    result = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(_tracer(_square(46))),
        _sources(SOURCE[None, :]),
    ).estimate(RECEIVER, samples=200_000, seed=103)

    assert result.diagnostics.face_count == 4_232
    assert result.diagnostics.trials == 200_000
    assert result.transfer == float(np.sum(result.by_order, dtype=np.float64))
    assert result.mass.sum(dtype=np.float64) == pytest.approx(result.transfer, rel=5.0e-15, abs=0.0)


def test_paired_surface_kernel_matches_one_surface_reference_for_all_path_arrays() -> None:
    transport = OneBounceSpecularTransport(_tracer(PLANE), candidate_chunk=3)
    sources = np.array(
        [
            [-3.0, 0.0, 5.0],
            [-2.0, 0.5, 5.5],
            [1.0, -0.75, 4.5],
            [3.0, 0.25, 6.0],
            [0.0, 1.0, 5.0],
        ]
    )
    receivers = np.array(
        [
            [2.0, 0.0, 2.0],
            [1.0, -0.5, 1.5],
            [-1.0, 0.5, 2.5],
            [0.5, 1.0, 1.75],
            [-2.0, -0.25, 2.25],
        ]
    )
    weights = np.array([0.2, 0.7, 1.1, 0.4, 0.9])
    source_ids = np.array([11, 7, 19, 3, 13])
    surfaces = np.zeros(sources.shape[0], dtype=np.int64)
    paired = transport.solve_paired_surfaces(
        sources,
        receivers,
        surfaces,
        endpoint_weight=weights,
        source_index=source_ids,
    )

    references = [
        transport.solve_paired(
            sources[index : index + 1],
            receivers[index : index + 1],
            endpoint_weight=weights[index : index + 1],
            source_index=source_ids[index : index + 1],
            sequences=np.array([[0]], dtype=np.int64),
        )
        for index in range(sources.shape[0])
    ]
    assert all(reference.diagnostics.accepted == 1 for reference in references)
    np.testing.assert_allclose(paired.k_hat, np.concatenate([reference.k_hat for reference in references]))
    np.testing.assert_allclose(paired.transfer, np.concatenate([reference.transfer for reference in references]))
    np.testing.assert_allclose(
        paired.reflection_point,
        np.concatenate([reference.reflection_point for reference in references]),
    )
    np.testing.assert_array_equal(
        paired.source_index, np.concatenate([reference.source_index for reference in references])
    )
    np.testing.assert_array_equal(paired.endpoint_index, np.arange(sources.shape[0]))
    np.testing.assert_array_equal(
        paired.surface_sequence,
        np.concatenate([reference.surface_sequence for reference in references]),
    )
    np.testing.assert_allclose(
        paired.unfolded_length_m,
        np.concatenate([reference.unfolded_length_m for reference in references]),
    )
    assert paired.diagnostics.endpoint_pairs == sources.shape[0]
    assert paired.diagnostics.candidates == sources.shape[0]
    assert paired.diagnostics.geometric == sum(reference.diagnostics.geometric for reference in references)
    assert paired.diagnostics.visible == sum(reference.diagnostics.visible for reference in references)
    assert paired.diagnostics.accepted == sum(reference.diagnostics.accepted for reference in references)
    assert paired.diagnostics.chunks == 2
    assert paired.diagnostics.candidate_method == "paired_explicit_surfaces"
    assert paired.diagnostics.selected_faces == 1


def test_paired_surface_kernel_rejects_nonintegral_surface_indices() -> None:
    transport = OneBounceSpecularTransport(_tracer(PLANE))
    for invalid in (np.array([0.5]), np.array([True]), np.array(["0"])):
        with pytest.raises(ValueError, match="surface_index"):
            transport.solve_paired_surfaces(SOURCE[None, :], RECEIVER[None, :], invalid)


def test_source_draw_uses_unequal_probability_without_a_second_source_weight() -> None:
    sources = np.array([[-3.0, 0.0, 5.0], [3.0, 0.0, 5.0]])
    probability = np.array([0.1, 0.9])
    exact = OneBounceSpecularTransport(_tracer(PLANE))
    expected = exact.solve_all_sources(sources, np.zeros(3) + [0.0, 0.0, 2.0], probability).total
    estimator = SampledOneBounceSpecularEstimator(exact, _sources(sources, probability))
    sampled = estimator.estimate(np.array([0.0, 0.0, 2.0]), samples=10_000, seed=61)

    # The symmetric sources have exactly equal transfer. Multiplying by p_s
    # again would produce (0.1**2 + 0.9**2) * expected and fail decisively.
    assert sampled.transfer == pytest.approx(expected, rel=2.0e-13)
    assert np.mean(sampled.drawn_source_index == 1) == pytest.approx(0.9, abs=0.015)
    assert sampled.diagnostics.standard_error == pytest.approx(0.0, abs=1.0e-18)
    assert sampled.diagnostics.contribution_ess == pytest.approx(10_000.0, rel=2.0e-13)
    assert sampled.diagnostics.acceptance == 1.0
    assert sampled.by_order[0] == 0.0
    assert sampled.by_order[1] == pytest.approx(sampled.transfer)
    assert sampled.mass.sum() == pytest.approx(sampled.transfer)


def test_importance_weighting_handles_unequal_faces_and_sources() -> None:
    """The source draw supplies p_s and the face draw supplies one 1/q_f."""
    # The two disjoint coplanar faces have very different areas.  Each source
    # is placed so its image-source reflection lands in one face, which makes
    # both source and face probabilities matter in the same estimate.
    triangles = np.array(
        [
            [[-5.0, -1.0, 0.0], [-1.0, -1.0, 0.0], [-3.0, 0.0, 0.0]],
            [[4.0, -0.1, 0.0], [6.0, -0.1, 0.0], [5.0, 0.0, 0.0]],
        ]
    )
    sources = np.array([[-10.5, 0.0, 5.0], [17.5, 0.0, 5.0]])
    source_probability = np.array([0.2, 0.8])
    receiver = np.array([0.0, 0.0, 2.0])
    transport = OneBounceSpecularTransport(_tracer(triangles))
    exact = transport.solve_all_sources(sources, receiver, source_probability).total
    estimator = SampledOneBounceSpecularEstimator(
        transport,
        _sources(sources, source_probability),
    )
    sampled = estimator.estimate(receiver, samples=60_000, seed=37)

    expected_face_probability = 0.9 * np.array([2.0, 0.1]) / 2.1 + 0.1 / 2.0
    np.testing.assert_allclose(estimator.face_probability, expected_face_probability, rtol=0.0, atol=1.0e-15)
    # A five-sigma bound uses the estimator's own independent-trial variance
    # estimate and catches either a second p_s or a missing 1/q_f factor.
    assert abs(sampled.transfer - exact) <= 5.0 * sampled.diagnostics.standard_error + 1.0e-12
    assert sampled.diagnostics.accepted > 0
    assert sampled.diagnostics.variance_available


def test_exact_all_face_result_is_inside_repeated_seed_ci_after_subdivision() -> None:
    sources = np.array([[-4.0, -2.0, 5.0], [3.0, 4.0, 6.0]])
    probability = np.array([0.25, 0.75])
    receiver = np.array([1.0, 1.0, 2.0])
    exact_values = []
    sampled_means = []
    for subdivisions in (1, 3):
        exact_transport = OneBounceSpecularTransport(_tracer(_square(subdivisions)))
        exact = exact_transport.solve_all_sources(sources, receiver, probability).total
        estimator = SampledOneBounceSpecularEstimator(exact_transport, _sources(sources, probability))
        replicas = np.array([estimator.estimate(receiver, samples=2_000, seed=seed).transfer for seed in range(24)])
        standard_error = float(np.std(replicas, ddof=1) / np.sqrt(replicas.size))
        assert abs(float(np.mean(replicas)) - exact) <= 3.0 * standard_error
        exact_values.append(exact)
        sampled_means.append(float(np.mean(replicas)))

    assert exact_values[1] == pytest.approx(exact_values[0], rel=2.0e-13)
    assert sampled_means[1] == pytest.approx(exact_values[0], rel=0.08)


def test_suffix_uses_diffuse_lobe_new_order_and_original_arrival_direction() -> None:
    exact_transport = OneBounceSpecularTransport(_tracer(PLANE))
    estimator = SampledOneBounceSpecularEstimator(exact_transport, _sources(SOURCE[None, :]))
    exact = exact_transport.solve_paired(SOURCE[None, :], RECEIVER[None, :])
    toward_reflection = -exact.k_hat
    arrival = np.array([[0.0, 1.0, 0.0]])
    result = estimator.estimate_suffix(
        RECEIVER[None, :],
        toward_reflection,
        np.array([0.25]),
        arrival,
        np.array([1]),
        samples_per_vertex=8,
        seed=7,
    )

    assert result.transfer == pytest.approx(0.25 * exact.total, rel=2.0e-13)
    assert result.by_order[0] == result.by_order[1] == 0.0
    assert result.by_order[2] == pytest.approx(result.transfer, rel=2.0e-13)
    np.testing.assert_allclose(result.k_hat, np.repeat(arrival, 8, axis=0), rtol=0.0, atol=0.0)

    zero_diffuse = estimator.estimate_suffix(
        RECEIVER[None, :],
        toward_reflection,
        np.array([0.0]),
        arrival,
        np.array([1]),
        samples_per_vertex=8,
        seed=7,
    )
    assert zero_diffuse.transfer == 0.0
    assert zero_diffuse.by_order[0] == 0.0
    assert zero_diffuse.diagnostics.path_accepted == 8
    assert zero_diffuse.diagnostics.accepted == 0


def test_finite_patch_blockers_and_rayleigh_rough_limit_are_preserved() -> None:
    blocker = np.array([[[0.0, -1.0, 0.3], [0.0, 1.0, 0.3], [0.0, 0.0, 1.3]]])
    tracer = _tracer(np.concatenate((PLANE, blocker)))
    all_surfaces = SpecularSurfaces.from_tracer(tracer)
    plane_only = SpecularSurfaces(
        all_surfaces.triangles[:1],
        all_surfaces.normals[:1],
        all_surfaces.face_index[:1],
        all_surfaces.material_class[:1],
    )
    blocked = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(tracer, plane_only),
        _sources(SOURCE[None, :]),
    ).estimate(RECEIVER, samples=64, seed=3)
    receiver_blocker = np.array([[[1.0, -1.0, 0.3], [1.0, 1.0, 0.3], [1.0, 0.0, 2.5]]])
    receiver_tracer = _tracer(np.concatenate((PLANE, receiver_blocker)))
    receiver_surfaces = SpecularSurfaces.from_tracer(receiver_tracer)
    receiver_plane_only = SpecularSurfaces(
        receiver_surfaces.triangles[:1],
        receiver_surfaces.normals[:1],
        receiver_surfaces.face_index[:1],
        receiver_surfaces.material_class[:1],
    )
    receiver_blocked = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(receiver_tracer, receiver_plane_only),
        _sources(SOURCE[None, :]),
    ).estimate(RECEIVER, samples=64, seed=3)
    rough_limit = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(_tracer(PLANE, rms_height_m=100.0)),
        _sources(SOURCE[None, :]),
    ).estimate(RECEIVER, samples=64, seed=3)
    rayleigh_floor = OneBounceSpecularTransport(_tracer(PLANE, rms_height_m=100.0)).solve_paired(
        SOURCE[None, :], RECEIVER[None, :]
    )

    too_small = np.array([[[5.0, 5.0, 0.0], [6.0, 5.0, 0.0], [5.0, 6.0, 0.0]]])
    outside_patch = SampledOneBounceSpecularEstimator(
        OneBounceSpecularTransport(_tracer(too_small)),
        _sources(SOURCE[None, :]),
    ).estimate(RECEIVER, samples=64, seed=3)

    assert blocked.transfer == 0.0
    assert blocked.diagnostics.visible == 0
    assert receiver_blocked.transfer == 0.0
    assert receiver_blocked.diagnostics.visible == 0
    assert rough_limit.transfer == pytest.approx(rayleigh_floor.total, rel=2.0e-13)
    assert rough_limit.transfer < 1.0e-25
    assert rough_limit.diagnostics.path_accepted == 64
    assert outside_patch.transfer == 0.0
    assert outside_patch.diagnostics.geometric == 0

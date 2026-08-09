"""Conservative device screening for the exact order-one host solver."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.transport.specular import OneBounceSpecularTransport, _inside_triangles
from semantic_twin.transport.specular_broadphase import conservative_order_one_candidates
from semantic_twin.transport.specular_device_broadphase import (
    BoundDeviceOrderOneBroadPhase,
    DeviceBroadPhaseUnavailable,
)
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


class _Kernel:
    def __init__(self, mi: Any, dr: Any) -> None:
        self.mi = mi
        self.dr = dr


class _UnavailableBroadPhase:
    def candidates(self, *args: Any, **kwargs: Any) -> None:
        raise DeviceBroadPhaseUnavailable("synthetic CUDA failure")


class _TriangleGeometry:
    def __init__(self, triangles: np.ndarray) -> None:
        self.vertices = np.asarray(triangles, dtype=np.float64).reshape(-1, 3)
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


def _set_variant(variant: str) -> tuple[Any, Any]:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant(variant)
    except ImportError as error:
        pytest.skip(str(error))
    return mi, pytest.importorskip("drjit")


def _normals(triangles: np.ndarray) -> np.ndarray:
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    return cross / np.linalg.norm(cross, axis=1)[:, None]


def _exact_geometric_candidates(
    sources: np.ndarray,
    receiver: np.ndarray,
    triangles: np.ndarray,
    normals: np.ndarray,
    epsilon_m: float,
) -> np.ndarray:
    source_count = sources.shape[0]
    face_count = triangles.shape[0]
    flat = np.arange(source_count * face_count, dtype=np.int64)
    pair = flat // face_count
    face = flat % face_count
    triangle = triangles[face]
    normal = normals[face]
    source = sources[pair]
    repeated_receiver = np.broadcast_to(receiver, source.shape)
    source_side = np.einsum("ij,ij->i", source - triangle[:, 0], normal)
    receiver_side = np.einsum("ij,ij->i", repeated_receiver - triangle[:, 0], normal)
    image = source - 2.0 * source_side[:, None] * normal
    image_line = image - repeated_receiver
    denominator = np.einsum("ij,ij->i", image_line, normal)
    with np.errstate(divide="ignore", invalid="ignore"):
        fraction = -receiver_side / denominator
    finite = np.isfinite(fraction)
    reflection = repeated_receiver + np.where(finite, fraction, 0.0)[:, None] * image_line
    geometric = (
        (np.linalg.norm(source - repeated_receiver, axis=1) > 1.0e-12)
        & (source_side * receiver_side > epsilon_m * epsilon_m)
        & finite
        & (fraction > 0.0)
        & (fraction < 1.0)
        & _inside_triangles(reflection, triangle)
    )
    return flat[geometric]


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_screen_is_a_superset_of_exact_geometry_across_scales(variant: str) -> None:
    mi, dr = _set_variant(variant)
    rng = np.random.default_rng(294_817)
    epsilon_m = 1.0e-3
    for scale in (1.0e-3, 1.0, 1.0e3):
        center = scale * rng.normal(size=(47, 3))
        edge1 = scale * rng.normal(size=(47, 3))
        edge2 = scale * rng.normal(size=(47, 3))
        weak = np.linalg.norm(np.cross(edge1, edge2), axis=1) < scale * scale * 1.0e-7
        edge2[weak] += scale * np.array([0.0, 1.0, 0.0])
        triangles = np.stack((center, center + edge1, center + edge2), axis=1)
        normals = _normals(triangles)
        sources = scale * rng.normal(size=(19, 3))
        receiver = scale * rng.normal(size=3)
        exact = _exact_geometric_candidates(sources, receiver, triangles, normals, epsilon_m)
        cpu = conservative_order_one_candidates(sources, receiver, triangles, normals, epsilon_m=epsilon_m)
        bound = BoundDeviceOrderOneBroadPhase.bind(triangles, normals, _Kernel(mi, dr))
        resident_arrays = tuple(id(array) for array in bound.device_arrays)
        device = bound.candidates(
            sources,
            receiver,
            np.arange(triangles.shape[0]),
            epsilon_m=epsilon_m,
            source_chunk=7,
            inside_tolerance=2.0e-8,
        )

        assert np.setdiff1d(exact, cpu.flat_index).size == 0
        assert np.setdiff1d(exact, device.flat_index).size == 0
        assert tuple(id(array) for array in bound.device_arrays) == resident_arrays
        assert device.logical_candidates == sources.shape[0] * triangles.shape[0]
        assert np.all(device.flat_index[1:] > device.flat_index[:-1])

        selected = np.array([17, 3, 41, 8, 0], dtype=np.int64)
        selected_exact = _exact_geometric_candidates(
            sources,
            receiver,
            triangles[selected],
            normals[selected],
            epsilon_m,
        )
        selected_device = bound.candidates(
            sources,
            receiver,
            selected,
            epsilon_m=epsilon_m,
            source_chunk=7,
            inside_tolerance=2.0e-8,
        )
        assert np.setdiff1d(selected_exact, selected_device.flat_index).size == 0
        assert selected_device.logical_candidates == sources.shape[0] * selected.size


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_screen_retains_boundary_skinny_and_translated_candidates(variant: str) -> None:
    mi, dr = _set_variant(variant)
    epsilon_m = 1.0e-3
    triangle = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]])
    normal = np.array([[0.0, 0.0, 1.0]])
    receiver = np.array([0.25, 0.25, 2.0])
    reflection = np.array([-1.9e-8, 0.5, 0.0])
    mirrored_receiver = np.array([0.25, 0.25, -2.0])
    boundary_source = mirrored_receiver + 3.5 * (reflection - mirrored_receiver)

    translation = np.array([1.0e9, -2.0e9, 3.0e9])
    skinny = translation + np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0e-7, 1.0e-5, 0.0]]])
    skinny_receiver = translation + np.array([0.2, 2.0e-6, 2.0])
    skinny_reflection = skinny[0, 0] + 0.3 * (skinny[0, 1] - skinny[0, 0])
    skinny_reflection += 0.2 * (skinny[0, 2] - skinny[0, 0])
    skinny_mirror = skinny_receiver.copy()
    skinny_mirror[2] -= 4.0
    skinny_source = skinny_mirror + 3.5 * (skinny_reflection - skinny_mirror)

    for triangles, normals, sources, point in (
        (triangle, normal, boundary_source[None, :], receiver),
        (skinny, normal, skinny_source[None, :], skinny_receiver),
    ):
        exact = _exact_geometric_candidates(sources, point, triangles, normals, epsilon_m)
        device = BoundDeviceOrderOneBroadPhase.bind(triangles, normals, _Kernel(mi, dr)).candidates(
            sources,
            point,
            np.array([0]),
            epsilon_m=epsilon_m,
            source_chunk=1,
            inside_tolerance=2.0e-8,
        )
        np.testing.assert_array_equal(exact, [0])
        np.testing.assert_array_equal(device.flat_index, [0])


def test_cuda_broad_phase_preserves_full_exact_solver_output() -> None:
    mi, dr = _set_variant("cuda_ad_rgb")
    plane = np.array([[[-20.0, -20.0, 0.0], [20.0, -20.0, 0.0], [0.0, 20.0, 0.0]]])
    triangles = np.concatenate([plane + np.array([0.0, 40.0 * index, 0.0]) for index in range(12)])
    geometry = _TriangleGeometry(triangles)
    config = TraceConfig(rays=32, batch=32, local_cells=32, max_bounces=2, seed=4)
    tracer = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        config,
    )
    sources = np.array([[-3.0, 0.0, 5.0], [4.0, 1.0, 6.0], [-3.0, 40.0, 5.0], [4.0, 41.0, 6.0]])
    receiver = np.array([2.0, 0.0, 2.0])
    receivers = np.broadcast_to(receiver, sources.shape)
    oracle = OneBounceSpecularTransport(tracer, broad_phase_threshold=10**9).solve_paired(sources, receivers)
    tracer.kernel = _Kernel(mi, dr)
    filtered = OneBounceSpecularTransport(tracer, broad_phase_threshold=0, broad_phase_source_chunk=2).solve_paired(
        sources,
        receivers,
    )

    np.testing.assert_array_equal(filtered.k_hat, oracle.k_hat)
    np.testing.assert_array_equal(filtered.transfer, oracle.transfer)
    np.testing.assert_array_equal(filtered.reflection_point, oracle.reflection_point)
    np.testing.assert_array_equal(filtered.source_index, oracle.source_index)
    np.testing.assert_array_equal(filtered.endpoint_index, oracle.endpoint_index)
    np.testing.assert_array_equal(filtered.surface_sequence, oracle.surface_sequence)
    np.testing.assert_array_equal(filtered.unfolded_length_m, oracle.unfolded_length_m)
    assert filtered.diagnostics.geometric == oracle.diagnostics.geometric
    assert filtered.diagnostics.visible == oracle.diagnostics.visible
    assert filtered.diagnostics.accepted == oracle.diagnostics.accepted
    broad = filtered.diagnostics.candidate_diagnostics["broad_phase"]
    assert broad["method"] == "cuda_float64_conservative_mirrored_receiver_triangle_cones"
    assert broad["survivors"] < broad["logical_candidates"]


def test_device_failure_falls_back_to_authoritative_numpy_screen() -> None:
    plane = np.array([[[-20.0, -20.0, 0.0], [20.0, -20.0, 0.0], [0.0, 20.0, 0.0]]])
    triangles = np.concatenate((plane, plane + np.array([0.0, 40.0, 0.0])))
    geometry = _TriangleGeometry(triangles)
    config = TraceConfig(rays=32, batch=32, local_cells=32, max_bounces=2, seed=4)
    tracer = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        config,
    )
    sources = np.array([[-3.0, 0.0, 5.0], [4.0, 1.0, 6.0]])
    receiver = np.array([2.0, 0.0, 2.0])
    receivers = np.broadcast_to(receiver, sources.shape)
    oracle = OneBounceSpecularTransport(tracer, broad_phase_threshold=10**9).solve_paired(sources, receivers)
    fallback = OneBounceSpecularTransport(tracer, broad_phase_threshold=0)
    fallback._device_broad_phase = _UnavailableBroadPhase()
    paths = fallback.solve_paired(sources, receivers)

    np.testing.assert_array_equal(paths.transfer, oracle.transfer)
    np.testing.assert_array_equal(paths.reflection_point, oracle.reflection_point)
    broad = paths.diagnostics.candidate_diagnostics["broad_phase"]
    assert broad["method"] == "conservative_mirrored_receiver_triangle_cones"

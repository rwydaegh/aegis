from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.device_kernel import DeviceEscapeRecords, DeviceSbrKernel
from semantic_twin.transport.tracer import TraceConfig, fresnel_power_reflectance


def _write_plane(path: Path) -> Path:
    path.write_text(
        """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
-100 -100 0
100 -100 0
100 100 0
-100 100 0
3 0 1 2
3 0 2 3
"""
    )
    return path


def _write_cube(path: Path) -> Path:
    path.write_text(
        """ply
format ascii 1.0
element vertex 8
property float x
property float y
property float z
element face 12
property list uchar int vertex_indices
end_header
-10 -10 -10
10 -10 -10
10 10 -10
-10 10 -10
-10 -10 10
10 -10 10
10 10 10
-10 10 10
3 0 2 1
3 0 3 2
3 4 5 6
3 4 6 7
3 0 1 5
3 0 5 4
3 1 2 6
3 1 6 5
3 2 3 7
3 2 7 6
3 3 0 4
3 3 4 7
"""
    )
    return path


def _set_variant(name: str) -> None:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant(name)
    except ImportError as error:
        pytest.skip(str(error))


def _kernel(
    path: Path,
    variant: str,
    *,
    rms_height_m: float = 0.0,
    face_class: np.ndarray | None = None,
    permittivity: np.ndarray | None = None,
    **changes: object,
) -> DeviceSbrKernel:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_plane(path), variant=variant)
    config = replace(
        TraceConfig(rays=2048, max_bounces=1, roulette_start=2, seed=73),
        **changes,
    )
    return DeviceSbrKernel(
        geometry,
        np.array([1, 1], dtype=np.int64) if face_class is None else face_class,
        np.array([1.0 + 0.0j, 4.2 - 0.15j]) if permittivity is None else permittivity,
        np.array([0.0, rms_height_m]),
        config,
    )


def _cube_kernel(
    path: Path,
    variant: str,
    *,
    face_class: np.ndarray | None = None,
    permittivity: np.ndarray | None = None,
    **changes: object,
) -> DeviceSbrKernel:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_cube(path), variant=variant)
    config = replace(TraceConfig(rays=2048, max_bounces=2, roulette_start=3, seed=91), **changes)
    materials = np.array([4.2 - 0.15j]) if permittivity is None else permittivity
    return DeviceSbrKernel(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64) if face_class is None else face_class,
        materials,
        np.zeros(materials.size),
        config,
    )


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_intersection_keeps_hit_face_and_normal_on_backend(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    import drjit as dr
    import mitsuba as mi

    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    origins = mi.Point3f(mi.Float([-1.0, 1.0, 0.0]), mi.Float([0.0, 0.0, 0.0]), mi.Float([1.0, 1.0, 1.0]))
    directions = mi.Vector3f(mi.Float([0.0, 0.0, 0.0]), mi.Float([0.0, 0.0, 0.0]), mi.Float([-1.0, -1.0, 1.0]))
    intersection = geometry.intersect_device(origins, directions, mi.Bool([True, True, True]))
    dr.eval(intersection.hit, intersection.distance, intersection.normal, intersection.face)

    assert np.array_equal(np.asarray(intersection.hit), [True, True, False])
    assert np.allclose(np.asarray(intersection.distance)[:2], 1.0)
    assert np.allclose(np.asarray(intersection.normal).T[:2], [[0.0, 0.0, 1.0]] * 2)
    assert set(np.asarray(intersection.face)[:2]) == {0, 1}


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_kernel_matches_smooth_plane_physics(tmp_path: Path, variant: str) -> None:
    kernel = _kernel(tmp_path / "plane.ply", variant)
    result = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]))

    assert result.escaped == result.rays == 2048
    assert result.ray_start == 0
    assert result.truncated == 0
    assert result.truncated_throughput == 0.0
    assert result.truncated_throughput_terms.shape == (0,)
    assert result.roulette_killed == 0
    assert np.array_equal(result.ray_index, np.arange(result.rays, dtype=np.uint32))
    assert np.array_equal(result.all_launch_direction, result.escaped_launch_direction)
    assert result.launch_direction is result.escaped_launch_direction
    direct = result.bounces == 0
    bounced = result.bounces == 1
    assert direct.any() and bounced.any()
    assert np.array_equal(result.throughput[direct], np.ones(np.count_nonzero(direct), dtype=np.float32))
    expected = fresnel_power_reflectance(
        -result.launch_direction[bounced, 2],
        np.full(np.count_nonzero(bounced), 4.2 - 0.15j),
    )
    assert np.allclose(result.throughput[bounced], expected, rtol=3.0e-5, atol=2.0e-6)
    expected_direction = result.launch_direction[bounced].copy()
    expected_direction[:, 2] *= -1.0
    assert np.allclose(result.exit_direction[bounced], expected_direction, atol=2.0e-6)
    expected_distance = -1.0 / result.launch_direction[bounced, 2] - kernel.config.ray_epsilon_m
    assert np.allclose(result.path_length[bounced], expected_distance, rtol=2.0e-5, atol=2.0e-5)
    assert np.allclose(result.last_vertex[bounced, 2], 0.0, atol=2.0e-5)


def _join(parts: list[DeviceEscapeRecords], field: str) -> np.ndarray:
    return np.concatenate([getattr(part, field) for part in parts], axis=0)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_counter_rng_is_exact_across_ray_ranges(tmp_path: Path, variant: str) -> None:
    kernel = _kernel(
        tmp_path / "plane.ply",
        variant,
        rms_height_m=1.0,
        rays=3072,
        roulette_start=1,
    )
    whole = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]))
    parts = [
        kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), rays=997, ray_start=0),
        kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), rays=2075, ray_start=997),
    ]

    for field in (
        "all_launch_direction",
        "ray_index",
        "launch_direction",
        "exit_direction",
        "throughput",
        "path_length",
        "last_vertex",
        "bounces",
    ):
        assert np.array_equal(getattr(whole, field), _join(parts, field))
    assert whole.truncated == sum(part.truncated for part in parts)
    assert whole.truncated_throughput == DeviceEscapeRecords.merge_truncated_throughput(parts)
    assert whole.roulette_killed == sum(part.roulette_killed for part in parts)
    assert [part.ray_start for part in parts] == [0, 997]


def test_adjacent_seeds_do_not_permute_the_same_paths(tmp_path: Path) -> None:
    kernel = _kernel(tmp_path / "plane.ply", "llvm_ad_rgb", rays=4096)
    first = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), seed=0)
    second = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), seed=1)
    xor_permutation = np.arange(4096, dtype=np.uint32) ^ 1

    assert np.array_equal(first.ray_index, np.arange(4096, dtype=np.uint32))
    assert np.array_equal(second.ray_index, np.arange(4096, dtype=np.uint32))
    assert not np.array_equal(first.launch_direction, second.launch_direction[xor_permutation])
    assert np.count_nonzero(first.launch_direction == second.launch_direction[xor_permutation]) < 10


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_rough_surface_draws_outward_diffuse_directions(tmp_path: Path, variant: str) -> None:
    kernel = _kernel(tmp_path / "plane.ply", variant, rms_height_m=1.0, rays=1024)
    result = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]))
    bounced = result.bounces == 1
    mirror = result.launch_direction[bounced].copy()
    mirror[:, 2] *= -1.0

    assert bounced.any()
    assert np.all(result.exit_direction[bounced, 2] >= 0.0)
    assert np.allclose(np.linalg.norm(result.exit_direction[bounced], axis=1), 1.0, atol=2.0e-6)
    assert np.count_nonzero(np.linalg.norm(result.exit_direction[bounced] - mirror, axis=1) > 1.0e-3) > 400


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_roulette_kills_and_reweights_paths(tmp_path: Path, variant: str) -> None:
    kernel = _kernel(tmp_path / "plane.ply", variant, rays=4096, roulette_start=1)
    result = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]))

    assert result.roulette_killed > 500
    assert result.truncated == 0
    assert result.escaped + result.roulette_killed == result.rays
    assert np.allclose(result.throughput, 1.0, atol=2.0e-6)
    assert np.all(result.ray_index[1:] > result.ray_index[:-1])
    launch_rows = result.ray_index.astype(np.int64) - result.ray_start
    assert np.array_equal(result.escaped_launch_direction, result.all_launch_direction[launch_rows])


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_kernel_truncates_after_several_closed_cube_hits(tmp_path: Path, variant: str) -> None:
    kernel = _cube_kernel(tmp_path / "cube.ply", variant)

    result = kernel.trace_escape_records(np.zeros(3))

    assert result.escaped == 0
    assert result.truncated == result.rays == 2048
    assert result.truncated_throughput > 0.0
    assert result.truncated_throughput == DeviceEscapeRecords.merge_truncated_throughput([result])
    assert result.truncated_throughput_terms.shape == (result.truncated,)
    assert result.roulette_killed == 0
    assert result.all_launch_direction.shape == (result.rays, 3)
    assert result.ray_index.shape == (0,)
    assert result.launch_direction.shape == (0, 3)
    assert result.exit_direction.shape == (0, 3)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_closed_cube_reports_mixed_roulette_and_truncation(tmp_path: Path, variant: str) -> None:
    kernel = _cube_kernel(tmp_path / "cube.ply", variant, rays=4096, roulette_start=1)
    result = kernel.trace_escape_records(np.zeros(3))

    assert result.escaped == 0
    assert result.roulette_killed > 0
    assert result.truncated > 0
    assert result.roulette_killed + result.truncated == result.rays
    assert np.isclose(result.truncated_throughput, float(result.truncated), rtol=0.0, atol=5.0e-7)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_closed_cube_contract_is_exact_across_ray_ranges(tmp_path: Path, variant: str) -> None:
    kernel = _cube_kernel(tmp_path / "cube.ply", variant, rays=4096, roulette_start=1)
    origin = np.zeros(3)
    whole = kernel.trace_escape_records(origin)
    parts = [
        kernel.trace_escape_records(origin, rays=997, ray_start=0),
        kernel.trace_escape_records(origin, rays=3099, ray_start=997),
    ]

    assert np.array_equal(whole.all_launch_direction, _join(parts, "all_launch_direction"))
    assert whole.truncated == sum(part.truncated for part in parts)
    assert whole.truncated_throughput == DeviceEscapeRecords.merge_truncated_throughput(parts)
    assert whole.roulette_killed == sum(part.roulette_killed for part in parts)
    assert all(part.escaped == 0 for part in parts)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_nonuniform_truncated_throughput_is_exact_across_ranges(tmp_path: Path, variant: str) -> None:
    face_class = np.arange(12, dtype=np.int64) % 3
    permittivity = np.array([2.0 - 0.05j, 4.2 - 0.15j, 12.0 - 0.5j])
    kernel = _cube_kernel(
        tmp_path / "cube.ply",
        variant,
        face_class=face_class,
        permittivity=permittivity,
        rays=4097,
        max_bounces=5,
        roulette_start=6,
    )
    origin = np.zeros(3)
    whole = kernel.trace_escape_records(origin)
    parts = [
        kernel.trace_escape_records(origin, rays=997, ray_start=0),
        kernel.trace_escape_records(origin, rays=3100, ray_start=997),
    ]

    assert whole.rays == 4097
    assert whole.truncated > 4000
    assert whole.truncated == sum(part.truncated for part in parts)
    assert np.array_equal(whole.truncated_throughput_terms, _join(parts, "truncated_throughput_terms"))
    assert whole.truncated_throughput == DeviceEscapeRecords.merge_truncated_throughput(parts)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_face_index_selects_between_material_classes(tmp_path: Path, variant: str) -> None:
    classes = np.array([0, 1], dtype=np.int64)
    material_permittivity = np.array([2.0 - 0.05j, 8.0 - 0.3j])
    kernel = _kernel(
        tmp_path / "plane.ply",
        variant,
        rays=4096,
        face_class=classes,
        permittivity=material_permittivity,
    )
    origin = np.array([0.0, 0.0, 1.0])
    result = kernel.trace_escape_records(origin)
    bounced = result.bounces == 1
    directions = result.launch_direction[bounced]
    origins = np.tile(origin, (directions.shape[0], 1)) + kernel.config.ray_epsilon_m * directions
    hit, _, _, face = kernel.geometry.intersect(origins, directions)
    selected = classes[face]
    expected = fresnel_power_reflectance(-directions[:, 2], material_permittivity[selected])

    assert hit.all()
    assert set(selected) == {0, 1}
    assert np.allclose(result.throughput[bounced], expected, rtol=3.0e-5, atol=2.0e-6)


def test_llvm_and_cuda_paths_agree_on_exercised_transport(tmp_path: Path) -> None:
    _set_variant("cuda_ad_rgb")
    origin = np.array([0.0, 0.0, 1.0])
    results = []
    for variant in ("llvm_ad_rgb", "cuda_ad_rgb"):
        kernel = _kernel(
            tmp_path / f"plane_{variant}.ply",
            variant,
            rms_height_m=1.0,
            rays=4096,
            roulette_start=1,
        )
        results.append(kernel.trace_escape_records(origin))
    llvm, cuda = results

    assert llvm.truncated == cuda.truncated
    assert llvm.roulette_killed == cuda.roulette_killed
    assert np.array_equal(llvm.ray_index, cuda.ray_index)
    assert np.array_equal(llvm.bounces, cuda.bounces)
    assert np.allclose(llvm.launch_direction, cuda.launch_direction, atol=2.0e-6)
    assert np.allclose(llvm.exit_direction, cuda.exit_direction, atol=2.0e-6)
    assert np.allclose(llvm.throughput, cuda.throughput, rtol=3.0e-5, atol=2.0e-6)
    assert np.allclose(llvm.path_length, cuda.path_length, atol=2.0e-4)


@pytest.mark.parametrize("invalid", [0.5, np.nan, np.inf, -1, 2, 2**32])
def test_invalid_material_classes_are_rejected(tmp_path: Path, invalid: float) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"))
    with pytest.raises(ValueError):
        DeviceSbrKernel(
            geometry,
            np.array([0.0, invalid]),
            np.array([4.2 - 0.15j]),
            np.array([0.0]),
            TraceConfig(rays=16),
        )


@pytest.mark.parametrize("option", ["observers", "next_event"])
def test_device_kernel_rejects_observers_before_launch(tmp_path: Path, option: str) -> None:
    kernel = _kernel(tmp_path / "plane.ply", "llvm_ad_rgb", rays=16)
    with pytest.raises(NotImplementedError, match=option):
        kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), **{option: object()})

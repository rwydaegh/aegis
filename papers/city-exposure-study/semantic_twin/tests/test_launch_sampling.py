from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.illumination import ISOTROPIC, fibonacci_sphere, nearest_cell, sample_sphere
from semantic_twin.exposure import reuse
from semantic_twin.cli import next_event
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.device_kernel import DeviceSbrKernel
from semantic_twin.transport.trace_kernel import (
    launch_directions,
    launch_rotation,
    rotated_fibonacci_sphere,
)
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


class EmptyGeometry:
    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def _launch(count: int, seed: int) -> np.ndarray:
    return rotated_fibonacci_sphere(np.arange(count, dtype=np.int64), count, seed)


def test_rotation_is_a_seeded_member_of_so3() -> None:
    first = launch_rotation(17)
    assert np.array_equal(first, launch_rotation(17))
    assert not np.array_equal(first, launch_rotation(18))
    assert np.allclose(first @ first.T, np.eye(3), atol=2.0e-15)
    assert np.linalg.det(first) == pytest.approx(1.0, abs=1.0e-15)


def test_rotated_fibonacci_launch_has_uniform_sphere_moments() -> None:
    directions = _launch(200_000, seed=31)
    assert np.allclose(np.linalg.norm(directions, axis=1), 1.0, atol=1.0e-14)
    assert np.max(np.abs(directions.mean(axis=0))) < 2.0e-5
    second = directions.T @ directions / directions.shape[0]
    assert np.max(np.abs(second - np.eye(3) / 3.0)) < 2.0e-5


def test_random_rotation_makes_each_fixed_lattice_point_uniform_over_replicas() -> None:
    point = np.array([0.31, -0.41, 0.856329375], dtype=np.float64)
    point /= np.linalg.norm(point)
    draws = np.array([launch_rotation(seed) @ point for seed in range(4096)])
    assert np.max(np.abs(draws.mean(axis=0))) < 0.025
    assert np.max(np.abs(draws.T @ draws / draws.shape[0] - np.eye(3) / 3.0)) < 0.025


def test_global_ranges_reconstruct_the_same_lattice_exactly() -> None:
    whole = _launch(8192, seed=73)
    parts = [
        rotated_fibonacci_sphere(np.arange(0, 997), 8192, 73),
        rotated_fibonacci_sphere(np.arange(997, 3011), 8192, 73),
        rotated_fibonacci_sphere(np.arange(3011, 8192), 8192, 73),
    ]
    assert np.array_equal(whole, np.concatenate(parts))


def test_iid_launch_keeps_the_established_draws_and_rng_position() -> None:
    actual_rng = np.random.default_rng(47)
    actual = launch_directions(
        1024,
        actual_rng,
        mode="iid",
        ray_start=0,
        total=1024,
        seed=47,
    )
    expected_rng = np.random.default_rng(47)
    expected = sample_sphere(1024, expected_rng)
    assert np.array_equal(actual, expected)
    assert np.array_equal(actual_rng.random(128), expected_rng.random(128))


def test_free_space_rotated_fibonacci_trace_is_exact_across_batches() -> None:
    base = TraceConfig(
        rays=8192,
        batch=8192,
        local_cells=256,
        exit_bands=18,
        max_bounces=0,
        seed=13,
        launch_sampling="rotated_fibonacci",
    )

    def trace(config: TraceConfig):
        tracer = SbrTracer(EmptyGeometry(), None, np.array([1.0 + 0.0j]), np.array([0.0]), config)
        return tracer.trace(np.array([0.0, 0.0, 1.5]), {"isotropic": ISOTROPIC})

    whole = trace(base)
    split = trace(replace(base, batch=997))
    assert np.array_equal(whole.rho["isotropic"], split.rho["isotropic"])
    assert np.array_equal(whole.exit_profile, split.exit_profile)
    assert whole.scalars() == split.scalars()


def test_rotated_fibonacci_reduces_local_cell_count_dispersion() -> None:
    rays = 200_000
    cells = fibonacci_sphere(4096)
    stratified = np.bincount(nearest_cell(_launch(rays, 19), cells), minlength=cells.shape[0])
    iid = np.bincount(
        nearest_cell(sample_sphere(rays, np.random.default_rng(19)), cells),
        minlength=cells.shape[0],
    )
    assert stratified.mean() == iid.mean() == pytest.approx(rays / cells.shape[0])
    assert stratified.std() < 0.65 * iid.std()


def test_launch_mode_validation_and_run_config_round_trip() -> None:
    with pytest.raises(ValueError, match="launch_sampling"):
        TraceConfig(launch_sampling="regular")
    with pytest.raises(ValueError, match="launch_sampling"):
        RunConfig(site="korenmarkt", launch_sampling="regular")

    historical = RunConfig.escape_grid(site="korenmarkt")
    stratified = historical.replace(launch_sampling="rotated_fibonacci")
    assert RunConfig.from_json(stratified.to_json()) == stratified
    assert historical.digest() == historical.replace(launch_sampling="iid").digest()
    assert historical.digest() != stratified.digest()
    assert "launch_sampling" not in historical.identity()
    assert stratified.identity()["launch_sampling"] == "rotated_fibonacci"
    assert "launch_sampling" not in TraceConfig().as_dict()
    assert TraceConfig(launch_sampling="rotated_fibonacci").as_dict()["launch_sampling"] == "rotated_fibonacci"


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


def _set_variant(name: str) -> None:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant(name)
    except ImportError as error:
        pytest.skip(str(error))


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_launch_matches_cpu_and_is_exact_across_ranges(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    config = TraceConfig(
        rays=200_000,
        batch=200_000,
        max_bounces=0,
        seed=59,
        launch_sampling="rotated_fibonacci",
    )
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    kernel = DeviceSbrKernel(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([0.0]),
        config,
    )
    whole = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]))
    parts = [
        kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), rays=997, ray_start=0),
        kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), rays=199_003, ray_start=997),
    ]
    split = np.concatenate([part.all_launch_direction for part in parts])
    assert np.array_equal(whole.all_launch_direction, split)
    assert np.allclose(whole.all_launch_direction, _launch(config.rays, config.seed), atol=1.0e-5)


def test_fibonacci_range_cannot_leave_its_declared_population() -> None:
    with pytest.raises(ValueError, match="inside the complete Fibonacci lattice"):
        rotated_fibonacci_sphere(np.array([4], dtype=np.int64), total=4, seed=0)


def test_uint32_phase_wrap_is_defined_for_large_cpu_global_indices() -> None:
    """The CPU lattice keeps its exact uint32 phase past one device word."""
    seed = 91
    indices = np.array([2**32 - 1, 2**33 - 1], dtype=np.uint64)
    directions = rotated_fibonacci_sphere(indices, total=2**34, seed=seed)
    assert np.all(np.isfinite(directions))
    assert np.allclose(np.linalg.norm(directions, axis=1), 1.0, atol=2.0e-14)
    # Advancing by one uint32 word changes z, but the azimuth phase repeats.
    # Undo the common rotation to test the phase directly. This catches an
    # accidental signed/int32 cast in the global index arithmetic.
    base = directions @ launch_rotation(seed)
    assert np.angle(base[0, 0] + 1j * base[0, 1]) == pytest.approx(np.angle(base[1, 0] + 1j * base[1, 1]), abs=2.0e-14)
    assert not np.array_equal(directions[0], directions[1])


def test_pre_launch_manifest_without_new_sampling_fields_replays_as_iid() -> None:
    """Adding the opt-in mode must not strand historical IID manifests."""
    config = RunConfig.escape_grid(site="korenmarkt", locations=1, rays=32, tag="legacy")
    recorded = config.as_dict()
    recorded.pop("launch_sampling")
    recorded.pop("transport_kernel")
    manifest = {"run": recorded, "run_digest": config.digest()}
    assert reuse.same_run_identity(manifest, config, {})


def test_next_event_cli_exposes_the_opt_in_launch_design() -> None:
    args = next_event.arguments(["--launch-sampling", "rotated_fibonacci"])
    config = next_event.config_from_arguments(args)
    assert config.launch_sampling == "rotated_fibonacci"

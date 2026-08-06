from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.illumination import MODELS, nearest_cell
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.device_kernel import DeviceEscapeRecords
from semantic_twin.transport.device_tracer import DeviceEscapeTracer
from semantic_twin.transport.trace_kernel import range_to_source_shell
from semantic_twin.transport.tracer import TraceConfig


def _records(
    ray_start: int,
    launch: np.ndarray,
    escaped_ids: np.ndarray,
    exit_direction: np.ndarray,
    throughput: np.ndarray,
    path_length: np.ndarray,
    last_vertex: np.ndarray,
    bounces: np.ndarray,
    truncated_terms: np.ndarray,
) -> DeviceEscapeRecords:
    local = escaped_ids.astype(np.int64) - ray_start
    return DeviceEscapeRecords(
        all_launch_direction=np.asarray(launch, dtype=np.float32),
        ray_index=np.asarray(escaped_ids, dtype=np.uint32),
        escaped_launch_direction=np.asarray(launch, dtype=np.float32)[local],
        exit_direction=np.asarray(exit_direction, dtype=np.float32),
        throughput=np.asarray(throughput, dtype=np.float32),
        path_length=np.asarray(path_length, dtype=np.float32),
        last_vertex=np.asarray(last_vertex, dtype=np.float32),
        bounces=np.asarray(bounces, dtype=np.uint32),
        ray_start=ray_start,
        rays=len(launch),
        truncated=len(truncated_terms),
        truncated_throughput=float(sum(float(value) for value in truncated_terms)),
        truncated_throughput_terms=np.asarray(truncated_terms, dtype=np.float32),
        roulette_killed=0,
        seconds=0.01,
    )


class _SyntheticKernel:
    def __init__(self, parts: dict[int, DeviceEscapeRecords]) -> None:
        self.parts = parts
        self.calls: list[tuple[int, int, int]] = []

    def trace_escape_records(
        self,
        origin: np.ndarray,
        *,
        rays: int,
        ray_start: int,
        seed: int,
    ) -> DeviceEscapeRecords:
        assert np.array_equal(origin, [1.0, 2.0, 3.0])
        self.calls.append((ray_start, rays, seed))
        return self.parts[ray_start]


class _Geometry:
    vertices = np.array([[-10.0, 0.0, 0.0], [10.0, 0.0, 0.0]])


class _DirectionalModel:
    law = "test_directional"
    family = "test"
    elevation_min_deg = -90.0
    elevation_max_deg = 90.0

    def __init__(self, name: str, coefficients: np.ndarray) -> None:
        self.name = name
        self.coefficients = np.asarray(coefficients, dtype=np.float64)

    def weight(self, directions: np.ndarray) -> np.ndarray:
        return self.density(directions)

    def knots(self) -> tuple[()]:
        return ()

    def normalisation(self, quadrature: int = 0) -> float:
        return 1.0

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        return 10.0 + np.asarray(directions) @ self.coefficients

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "law": self.law, "family": self.family}


def _synthetic_parts() -> dict[int, DeviceEscapeRecords]:
    return {
        0: _records(
            0,
            np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float),
            np.array([0, 2]),
            np.array([[np.sqrt(0.96), 0, 0.2], [np.sqrt(0.99), 0, 0.1]], dtype=float),
            np.array([1.0, 0.5]),
            np.array([0.0, 5.0]),
            np.array([[1, 2, 3], [1, 6, 3]], dtype=float),
            np.array([0, 1]),
            np.array([0.125], dtype=np.float32),
        ),
        3: _records(
            3,
            np.array([[-1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=float),
            np.array([3, 5]),
            np.array([[np.sqrt(0.96), 0, 0.2], [0.6, 0, -0.8]], dtype=float),
            np.array([0.25, 0.75]),
            np.array([0.0, 7.0]),
            np.array([[1, 2, 3], [1, 2, -3]], dtype=float),
            np.array([0, 2]),
            np.array([0.25], dtype=np.float32),
        ),
    }


def _merge(records: list[DeviceEscapeRecords]) -> DeviceEscapeRecords:
    return DeviceEscapeRecords(
        all_launch_direction=np.concatenate([record.all_launch_direction for record in records]),
        ray_index=np.concatenate([record.ray_index for record in records]),
        escaped_launch_direction=np.concatenate([record.escaped_launch_direction for record in records]),
        exit_direction=np.concatenate([record.exit_direction for record in records]),
        throughput=np.concatenate([record.throughput for record in records]),
        path_length=np.concatenate([record.path_length for record in records]),
        last_vertex=np.concatenate([record.last_vertex for record in records]),
        bounces=np.concatenate([record.bounces for record in records]),
        ray_start=records[0].ray_start,
        rays=sum(record.rays for record in records),
        truncated=sum(record.truncated for record in records),
        truncated_throughput=DeviceEscapeRecords.merge_truncated_throughput(records),
        truncated_throughput_terms=np.concatenate([record.truncated_throughput_terms for record in records]),
        roulette_killed=sum(record.roulette_killed for record in records),
        seconds=sum(record.seconds for record in records),
    )


def _synthetic_tracer(monkeypatch: pytest.MonkeyPatch, *, range_weighted: bool = False) -> DeviceEscapeTracer:
    parts = _synthetic_parts()
    kernel = _SyntheticKernel(parts)
    monkeypatch.setattr("semantic_twin.transport.device_tracer.DeviceSbrKernel", lambda *args: kernel)
    config = TraceConfig(
        rays=6,
        local_cells=12,
        exit_bands=4,
        max_bounces=2,
        batch=3,
        seed=41,
        range_weighted_escape=range_weighted,
    )
    tracer = DeviceEscapeTracer(
        _Geometry(),
        np.zeros(1, dtype=np.int64),
        np.array([4.0 - 0.1j]),
        np.array([0.0]),
        config,
    )
    assert tracer.kernel is kernel
    return tracer


def test_adapter_scores_all_models_and_transport_scalars(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = _synthetic_tracer(monkeypatch)
    result = tracer.trace(np.array([1.0, 2.0, 3.0]), MODELS, ground_z_m=0.4, seed=99)

    assert tracer.kernel.calls == [(0, 3, 99), (3, 3, 99)]
    assert list(result.rho) == list(MODELS)
    assert list(result.susceptibility_direct) == list(MODELS)
    assert result.ground_z_m == 0.4
    assert result.rays == 6
    assert result.escaped_fraction == pytest.approx(4.0 / 6.0)
    assert result.sky_fraction == pytest.approx(2.0 / 6.0)
    assert result.mean_bounces == pytest.approx(0.75)
    assert result.mean_excess_delay_ns == pytest.approx(1.66e9 / 299_792_458.0)
    assert result.diagnostics["truncated_rays"] == 2
    assert result.diagnostics["truncated_throughput_share"] == pytest.approx(0.375 / 2.5)
    assert np.array_equal(result.exit_profile, np.array([0.5, 0.0, 7.0 / 6.0, 0.0]))

    launch = np.concatenate([part.all_launch_direction for part in _synthetic_parts().values()])
    counts = np.bincount(nearest_cell(launch, result.local_grid), minlength=result.local_grid.shape[0])
    occupied = counts > 0
    assert np.all(np.isfinite(result.rho["isotropic"][occupied]))
    assert np.count_nonzero(result.rho["isotropic"]) == 4
    for name in MODELS:
        assert result.susceptibility[name] > result.susceptibility_direct[name] > 0.0


def test_adapter_applies_range_weight_before_each_model_density(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = _synthetic_tracer(monkeypatch, range_weighted=True)
    result = tracer.trace(np.array([1.0, 2.0, 3.0]), {"isotropic": MODELS["isotropic"]})
    merged = _merge(list(_synthetic_parts().values()))
    distance = range_to_source_shell(
        merged.last_vertex,
        merged.exit_direction,
        merged.path_length,
        tracer.source_shell_radius_m,
        tracer.config.ray_epsilon_m,
    )
    contribution = merged.throughput / distance**2 / (4.0 * np.pi)
    cells = nearest_cell(merged.all_launch_direction, result.local_grid)
    escaped_cells = cells[merged.ray_index]
    counts = np.maximum(np.bincount(cells, minlength=tracer.config.local_cells), 1)
    expected_rho = np.zeros(tracer.config.local_cells)
    np.add.at(expected_rho, escaped_cells, contribution)
    expected_rho /= counts

    assert np.allclose(result.rho["isotropic"], expected_rho, rtol=1.0e-7, atol=0.0)
    assert result.susceptibility["isotropic"] == pytest.approx(
        np.sum(expected_rho) * 4.0 * np.pi / tracer.config.local_cells
    )


def test_adapter_scores_each_model_from_the_exit_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = _synthetic_tracer(monkeypatch)
    models = {
        "x_sensitive": _DirectionalModel("x_sensitive", np.array([2.0, -1.0, 0.5])),
        "y_sensitive": _DirectionalModel("y_sensitive", np.array([-0.5, 3.0, -1.0])),
    }
    result = tracer.trace(np.array([1.0, 2.0, 3.0]), models)
    merged = _merge(list(_synthetic_parts().values()))
    all_cells = nearest_cell(merged.all_launch_direction, result.local_grid)
    escaped_cells = all_cells[merged.ray_index]
    counts = np.maximum(np.bincount(all_cells, minlength=tracer.config.local_cells), 1)
    solid_angle = 4.0 * np.pi / tracer.config.local_cells

    for name, model in models.items():
        contribution = merged.throughput * model.density(merged.exit_direction)
        expected = np.zeros(tracer.config.local_cells)
        expected_direct = np.zeros(tracer.config.local_cells)
        np.add.at(expected, escaped_cells, contribution)
        direct = merged.bounces == 0
        np.add.at(expected_direct, escaped_cells[direct], contribution[direct])
        expected /= counts
        expected_direct /= counts
        assert np.array_equal(result.rho[name], expected)
        assert result.susceptibility[name] == np.sum(expected) * solid_angle
        assert result.susceptibility_direct[name] == np.sum(expected_direct) * solid_angle
    assert not np.array_equal(result.rho["x_sensitive"], result.rho["y_sensitive"])


@pytest.mark.parametrize("argument", ["recorder", "tally", "gather", "observers", "next_event"])
def test_adapter_rejects_callbacks_before_launch(monkeypatch: pytest.MonkeyPatch, argument: str) -> None:
    tracer = _synthetic_tracer(monkeypatch)
    with pytest.raises(NotImplementedError, match=argument):
        tracer.trace(np.array([1.0, 2.0, 3.0]), MODELS, **{argument: object()})
    assert tracer.kernel.calls == []


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
def test_adapter_runs_resident_kernel_and_scores_plane(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    config = TraceConfig(
        rays=12_000,
        local_cells=128,
        exit_bands=8,
        max_bounces=1,
        roulette_start=2,
        batch=5_003,
        seed=73,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([0.0]),
        config,
    )
    result = tracer.trace(np.array([0.0, 0.0, 1.0]), MODELS)

    assert list(result.rho) == list(MODELS)
    assert result.escaped_fraction == 1.0
    assert result.sky_fraction == pytest.approx(0.5, abs=0.02)
    assert result.susceptibility_direct["isotropic"] == pytest.approx(result.sky_fraction, rel=0.04)
    assert result.susceptibility["isotropic"] > result.susceptibility_direct["isotropic"]
    assert np.array_equal(result.exit_profile[:3], np.zeros(3))
    assert result.exit_profile[3] < 0.05
    assert result.diagnostics == {"truncated_rays": 0, "truncated_throughput_share": 0.0}


def test_split_batches_preserve_device_result(monkeypatch: pytest.MonkeyPatch) -> None:
    parts = _synthetic_parts()
    whole = _merge(list(parts.values()))
    kernels = iter((_SyntheticKernel(parts), _SyntheticKernel({0: whole})))
    monkeypatch.setattr("semantic_twin.transport.device_tracer.DeviceSbrKernel", lambda *args: next(kernels))
    base = TraceConfig(rays=6, local_cells=12, exit_bands=4, max_bounces=2, batch=3, seed=41)
    split = DeviceEscapeTracer(_Geometry(), np.zeros(1), np.array([4.0 - 0.1j]), np.array([0.0]), base)
    unsplit = DeviceEscapeTracer(
        _Geometry(),
        np.zeros(1),
        np.array([4.0 - 0.1j]),
        np.array([0.0]),
        replace(base, batch=6),
    )

    first = split.trace(np.array([1.0, 2.0, 3.0]), MODELS)
    second = unsplit.trace(np.array([1.0, 2.0, 3.0]), MODELS)
    for name in MODELS:
        assert np.array_equal(first.rho[name], second.rho[name])
        assert first.susceptibility[name] == second.susceptibility[name]
        assert first.susceptibility_direct[name] == second.susceptibility_direct[name]
    assert np.array_equal(first.exit_profile, second.exit_profile)
    assert first.scalars() == second.scalars()


def test_scalar_reductions_are_exact_across_adversarial_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    launches = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    throughputs = np.array([1.0, 1.0e-8, 1.0e-8], dtype=np.float32)
    parts = {
        index: _records(
            index,
            launches[index : index + 1],
            np.array([index]),
            np.array([[np.sqrt(0.96), 0.0, 0.2]]),
            throughputs[index : index + 1],
            np.array([float(index > 0)]),
            np.array([[1.0, 2.0, 3.0]]),
            np.array([index > 0]),
            np.array([0.5], dtype=np.float32) if index == 0 else np.empty(0, dtype=np.float32),
        )
        for index in range(3)
    }
    whole = _merge(list(parts.values()))
    kernels = iter((_SyntheticKernel(parts), _SyntheticKernel({0: whole})))
    monkeypatch.setattr("semantic_twin.transport.device_tracer.DeviceSbrKernel", lambda *args: next(kernels))
    base = TraceConfig(rays=3, local_cells=12, exit_bands=4, max_bounces=2, batch=1, seed=41)
    split = DeviceEscapeTracer(_Geometry(), np.zeros(1), np.array([4.0 - 0.1j]), np.array([0.0]), base)
    unsplit = DeviceEscapeTracer(
        _Geometry(),
        np.zeros(1),
        np.array([4.0 - 0.1j]),
        np.array([0.0]),
        replace(base, batch=3),
    )

    first = split.trace(np.array([1.0, 2.0, 3.0]), {"isotropic": MODELS["isotropic"]})
    second = unsplit.trace(np.array([1.0, 2.0, 3.0]), {"isotropic": MODELS["isotropic"]})
    assert first.mean_excess_delay_ns == second.mean_excess_delay_ns
    assert first.mean_bounces == second.mean_bounces
    assert first.diagnostics == second.diagnostics
    assert first.scalars() == second.scalars()

"""CPU-only contract tests for the CPU/CUDA SBR comparison harness."""

from __future__ import annotations

import json
import pathlib
import subprocess

import numpy as np
import pytest

from semantic_twin.cli import gpu_parity as parity_cli
from semantic_twin.illumination import sample_sphere
from semantic_twin.transport import gpu_parity
from semantic_twin.transport import gpu_parity_orchestration
from semantic_twin.transport.gpu_parity import (
    ParityConfig,
    compare_artifacts,
    compare_device_artifacts,
    fixed_rays,
    run_harness,
)


def config(tmp_path: pathlib.Path, **updates: object) -> ParityConfig:
    mesh = tmp_path / "mesh.ply"
    mesh.write_bytes(b"ply\n")
    values = {
        "mesh": str(mesh),
        "output": str(tmp_path / "out"),
        "variants": ("llvm_ad_rgb", "cuda_ad_rgb"),
        "rays": 3,
        "repeats": 2,
        "seed": 17,
        "origin": (1.0, 2.0, 3.0),
        "ray_epsilon_m": 0.125,
        "local_cells": 2,
        "exit_bands": 2,
    }
    values.update(updates)
    return ParityConfig(**values)


def test_fixed_rays_are_the_tracers_first_batch(tmp_path: pathlib.Path) -> None:
    settings = config(tmp_path)
    origins, directions = fixed_rays(settings)
    expected = sample_sphere(settings.rays, np.random.default_rng(settings.seed))

    np.testing.assert_array_equal(directions, expected)
    np.testing.assert_array_equal(origins, np.asarray(settings.origin) + settings.ray_epsilon_m * expected)


def test_worker_loader_rejects_a_fixed_ray_hash_mismatch(tmp_path: pathlib.Path) -> None:
    settings = config(tmp_path)
    origins, directions = fixed_rays(settings)
    rays_path = tmp_path / "fixed.npz"
    np.savez(rays_path, origins=origins, directions=directions)
    expected = {
        "origins": gpu_parity._sha256_array(origins),
        "directions": "changed-after-parent-wrote-rays",
    }

    with pytest.raises(ValueError, match="fixed-ray hashes changed"):
        gpu_parity._load_fixed_rays(settings, rays_path, expected)


def _write_artifact(path: pathlib.Path, *, changed: bool) -> None:
    hit = np.array([True, True, False])
    face = np.array([2, 4 if changed else 3, 0])
    material = np.array([7, 9 if changed else 8, -1])
    distance = np.array([1.0, 2.01 if changed else 2.0, 1.0e30])
    tilted = [0.0, 0.1, np.sqrt(0.99)] if changed else [0.0, 0.0, 1.0]
    normal = np.array([[0.0, 0.0, 1.0], tilted, [0.0, 0.0, 0.0]])
    chi = np.asarray(4.0 if changed else 2.0)
    np.savez(
        path,
        hit=hit,
        face=face,
        material=material,
        distance=distance,
        normal=normal,
        exit_profile=np.array([1.0, 2.0]),
        local_grid=np.zeros((2, 3)),
        rho__isotropic=np.array([1.0, 2.0]),
        chi__isotropic=chi,
        chi_direct__isotropic=np.asarray(1.0),
        scalar__mean_bounces=np.asarray(2.0 if changed else 1.0),
    )


def test_comparison_covers_geometry_material_scalars_and_db_outputs(tmp_path: pathlib.Path) -> None:
    reference = tmp_path / "reference.npz"
    candidate = tmp_path / "candidate.npz"
    _write_artifact(reference, changed=False)
    _write_artifact(candidate, changed=True)

    answer = compare_artifacts(reference, candidate, epsilon=1.0e-4)

    assert answer["hit"]["mismatch_count"] == 0
    assert answer["face"]["mismatch_count"] == 1
    assert answer["material"]["mismatch_count"] == 1
    assert answer["face"]["mismatch_ray_indices"] == [1]
    assert answer["distance"]["mismatch_count"] == 1
    assert answer["normal"]["max_angle_degrees"] > 0.0
    assert answer["normal"]["mismatch_ray_indices"] == [1]
    chi = answer["scientific"]["chi__isotropic"]
    assert chi["db"]["max_abs_db"] == pytest.approx(10.0 * np.log10(2.0))
    assert chi["db"]["over_epsilon_count"] == 1
    assert "scalar__mean_bounces" in answer["scientific"]
    assert answer["local_grid"]["mismatch_count"] == 0


def test_comparison_rejects_shape_or_dtype_drift(tmp_path: pathlib.Path) -> None:
    reference = tmp_path / "reference.npz"
    candidate = tmp_path / "candidate.npz"
    _write_artifact(reference, changed=False)
    _write_artifact(candidate, changed=False)
    values = dict(np.load(candidate))
    values["local_grid"] = values["local_grid"].astype(np.float32)
    np.savez(candidate, **values)

    with pytest.raises(ValueError, match="dtype"):
        compare_artifacts(reference, candidate, epsilon=1.0e-4)


def test_device_comparison_pins_launch_identity_and_numeric_error(tmp_path: pathlib.Path) -> None:
    reference = tmp_path / "reference.npz"
    candidate = tmp_path / "candidate.npz"
    arrays = {
        "device__ray_index": np.array([0, 2], dtype=np.uint32),
        "device__bounces": np.array([0, 1], dtype=np.uint32),
        "device__all_launch_direction": np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32),
        "device__escaped_launch_direction": np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32),
        "device__throughput": np.array([1.0, 0.5], dtype=np.float32),
        "device__truncated_throughput_terms": np.array([0.25], dtype=np.float32),
    }
    np.savez(reference, **arrays)
    arrays["device__throughput"] = np.array([1.0, 0.50001], dtype=np.float32)
    np.savez(candidate, **arrays)

    answer = compare_device_artifacts(reference, candidate, epsilon=1.0e-4)

    assert answer is not None
    assert answer["all_launch_direction"]["equal"]
    assert answer["numeric"]["device__throughput"]["max_abs"] == pytest.approx(1.0e-5, rel=0.01)


def _write_worker_artifact(path: pathlib.Path, *, device: bool) -> None:
    arrays = {
        "hit": np.array([True, True, False]),
        "face": np.array([2, 3, 0], dtype=np.int64),
        "material": np.array([0, 0, -1], dtype=np.int64),
        "distance": np.array([1.0, 2.0, 1.0e30], dtype=np.float64),
        "normal": np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64),
        "exit_profile": np.array([1.0, 2.0], dtype=np.float64),
        "local_grid": np.zeros((2, 3), dtype=np.float64),
        "scalar__mean_bounces": np.asarray(1.0, dtype=np.float64),
    }
    for model in ("isotropic", "rooftop", "street_small_cell"):
        arrays[f"rho__{model}"] = np.array([1.0, 2.0], dtype=np.float64)
        arrays[f"chi__{model}"] = np.asarray(2.0, dtype=np.float64)
        arrays[f"chi_direct__{model}"] = np.asarray(1.0, dtype=np.float64)
    if device:
        arrays.update(
            {
                "device__all_launch_direction": np.array(
                    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32
                ),
                "device__ray_index": np.array([0, 2], dtype=np.uint32),
                "device__escaped_launch_direction": np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32),
                "device__exit_direction": np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32),
                "device__throughput": np.array([1.0, 0.5], dtype=np.float32),
                "device__path_length": np.array([0.0, 2.0], dtype=np.float32),
                "device__last_vertex": np.zeros((2, 3), dtype=np.float32),
                "device__bounces": np.array([0, 1], dtype=np.uint32),
                "device__truncated_throughput_terms": np.array([0.25], dtype=np.float32),
            }
        )
    np.savez(path, **arrays)


def _fake_worker_result(command: list[str], *, device: bool) -> dict[str, object]:
    timing = {
        "first_seconds": 2.0,
        "first_label": "test first call",
        "warm_seconds": [1.0, 1.0],
        "warm_median_seconds": 1.0,
    }
    variant = command[command.index("--variant") + 1]
    ray_hashes = {
        "origins": command[command.index("--origins-sha256") + 1],
        "directions": command[command.index("--directions-sha256") + 1],
    }
    config_payload = json.loads(pathlib.Path(command[command.index("--config") + 1]).read_text())
    artifact = pathlib.Path(command[command.index("--artifact") + 1]).resolve()
    device_result = (
        {
            "status": "prototype_device_resident_escape_records",
            "rng": {
                "algorithm": "counter",
                "seed": config_payload["seed"],
                "ray_start": 0,
                "all_launch_direction_sha256": "all",
                "escaped_launch_direction_sha256": "escaped",
            },
            "ray_start": 0,
            "rays": config_payload["rays"],
            "escaped": 2,
            "truncated": 1,
            "truncated_throughput": 0.25,
            "roulette_killed": 0,
            "timing": timing,
            "array_sha256": {},
        }
        if device
        else None
    )
    return {
        "artifact": str(artifact),
        "artifact_sha256": gpu_parity._sha256_file(artifact),
        "intersection": {"hits": 2, "timing": {"load_seconds": 0.5, **timing}},
        "legacy_hybrid_sbr": {
            "status": "legacy hybrid",
            "launch_rng": {},
            "timing": timing,
            "susceptibility": {},
            "susceptibility_direct": {},
            "scalars": {},
            "array_sha256": {},
        },
        "device_sbr": device_result,
        "fixed_ray_sha256": ray_hashes,
        "provenance": {
            "variant": variant,
            "git": {"commit": "abc", "dirty": False, "status_sha256": "clean"},
            "host": "test",
            "platform": "test",
            "executable": "python",
            "gpus": [],
            "mesh": {"path": config_payload["mesh"], "sha256": "mesh"},
            "face_class": None,
            "source_sha256": "source",
            "python": "3.12",
            "numpy": "2",
            "mitsuba": "3",
            "drjit": "1",
            "config": config_payload,
            "runtime": {
                "cpu_model": "test cpu",
                "logical_cpus": 4,
                "affinity_cpus": 4,
                "drjit_thread_count": 4,
                "drjit_backend": "test",
                "drjit_jit_flags": {"FastMath": True},
                "cuda_runtime_visible_to_driver": None,
                "mitsuba_variant": variant,
                "mitsuba_available_variants": list(config_payload["variants"]),
                "environment": {},
            },
        },
    }


def test_run_harness_uses_fresh_processes_and_enforces_ray_hashes(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):  # noqa: ANN001, ANN202
        calls.append(command)
        artifact = pathlib.Path(command[command.index("--artifact") + 1])
        result = pathlib.Path(command[command.index("--result") + 1])
        _write_worker_artifact(artifact, device=True)
        result.write_text(json.dumps(_fake_worker_result(command, device=True)))
        return subprocess.CompletedProcess(command, 0, stdout="worker output\n", stderr="")

    monkeypatch.setattr(gpu_parity_orchestration.subprocess, "run", fake_run)
    report_path = run_harness(settings)
    report = json.loads(report_path.read_text())

    assert len(calls) == 2
    assert all(
        command[:3] == [gpu_parity_orchestration.sys.executable, "-m", "semantic_twin.cli.gpu_parity"]
        for command in calls
    )
    expected_origins = gpu_parity._sha256_array(fixed_rays(settings)[0])
    assert report["fixed_rays"]["origins_sha256"] == expected_origins
    assert report["variants"]["llvm_ad_rgb"]["fixed_ray_sha256"]["origins"] == expected_origins
    assert report["cross_worker_consistency"]["fixed_rays"]["consistent"]
    assert report["comparisons"]["cuda_ad_rgb"]["legacy_hybrid"]["hit"]["mismatch_count"] == 0
    device = report["comparisons"]["cuda_ad_rgb"]["device_sbr"]
    assert device["available"]
    assert device["all_launch_direction"]["equal"]
    assert report["comparisons"]["cuda_ad_rgb"]["device_status"]["truncated_throughput"] == {
        "reference": 0.25,
        "candidate": 0.25,
    }
    assert report["acceptance"]["passed"]
    assert pathlib.Path(settings.output, "00_llvm_ad_rgb", "arrays.npz").is_file()


def test_worker_passes_expected_hashes_and_writes_json(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(gpu_parity.asdict(settings)))
    result_path = tmp_path / "result.json"
    seen: list[tuple[ParityConfig, str, dict[str, str]]] = []

    def fake_variant(settings, variant, _rays, _artifact, ray_hashes):  # noqa: ANN001, ANN202
        seen.append((settings, variant, ray_hashes))
        return {"ok": True}

    monkeypatch.setattr(parity_cli, "run_variant", fake_variant)
    status = parity_cli.main(
        [
            "_worker",
            "--config",
            str(config_path),
            "--variant",
            "cuda_ad_rgb",
            "--rays",
            str(tmp_path / "rays.npz"),
            "--artifact",
            str(tmp_path / "artifact.npz"),
            "--result",
            str(result_path),
            "--origins-sha256",
            "origin-hash",
            "--directions-sha256",
            "direction-hash",
        ]
    )

    assert status == 0
    assert seen[0][0].variants == ("llvm_ad_rgb", "cuda_ad_rgb")
    assert seen[0][0].origin == (1.0, 2.0, 3.0)
    assert seen[0][1:] == ("cuda_ad_rgb", {"origins": "origin-hash", "directions": "direction-hash"})
    assert json.loads(result_path.read_text()) == {"ok": True}


def test_nonempty_output_is_refused_before_writing(tmp_path: pathlib.Path) -> None:
    settings = config(tmp_path)
    output = pathlib.Path(settings.output)
    output.mkdir()
    (output / "keep.txt").write_text("owned by another run")

    with pytest.raises(FileExistsError, match="nonempty"):
        run_harness(settings)
    assert (output / "keep.txt").read_text() == "owned by another run"


def test_worker_failure_still_writes_a_failed_report(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path)

    def fail(command, **_kwargs):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 7, stdout="", stderr="backend unavailable\n")

    monkeypatch.setattr(gpu_parity_orchestration.subprocess, "run", fail)
    report_path = run_harness(settings)
    report = json.loads(report_path.read_text())

    assert not report["acceptance"]["passed"]
    assert set(report["worker_errors"]) == set(settings.variants)
    assert all("backend unavailable" in message for message in report["worker_errors"].values())


def test_missing_device_backend_fails_requested_device_parity(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path, variants=("scalar_rgb", "cuda_ad_rgb"))

    def fake_run(command, **_kwargs):  # noqa: ANN001, ANN202
        variant = command[command.index("--variant") + 1]
        artifact = pathlib.Path(command[command.index("--artifact") + 1])
        result = pathlib.Path(command[command.index("--result") + 1])
        available = variant != "scalar_rgb"
        _write_worker_artifact(artifact, device=available)
        result.write_text(json.dumps(_fake_worker_result(command, device=available)))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_parity_orchestration.subprocess, "run", fake_run)
    report = json.loads(run_harness(settings).read_text())

    assert not report["acceptance"]["passed"]
    assert report["comparisons"]["cuda_ad_rgb"]["device_sbr"] == {
        "available": False,
        "reference_available": False,
        "candidate_available": True,
    }
    assert any("resident-device comparison is unavailable" in failure for failure in report["acceptance"]["failures"])


def test_truncated_device_energy_is_an_acceptance_gate(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path)

    def fake_run(command, **_kwargs):  # noqa: ANN001, ANN202
        variant = command[command.index("--variant") + 1]
        artifact = pathlib.Path(command[command.index("--artifact") + 1])
        result = pathlib.Path(command[command.index("--result") + 1])
        _write_worker_artifact(artifact, device=True)
        payload = _fake_worker_result(command, device=True)
        if variant == "cuda_ad_rgb":
            payload["device_sbr"]["truncated_throughput"] = 0.5  # type: ignore[index]
        result.write_text(json.dumps(payload))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_parity_orchestration.subprocess, "run", fake_run)
    report = json.loads(run_harness(settings).read_text())

    assert not report["acceptance"]["passed"]
    assert any("truncated-throughput error" in failure for failure in report["acceptance"]["failures"])


def test_malformed_successful_worker_result_writes_failed_report(tmp_path: pathlib.Path, monkeypatch) -> None:
    settings = config(tmp_path)

    def fake_run(command, **_kwargs):  # noqa: ANN001, ANN202
        artifact = pathlib.Path(command[command.index("--artifact") + 1])
        result = pathlib.Path(command[command.index("--result") + 1])
        _write_worker_artifact(artifact, device=True)
        result.write_text(json.dumps({"provenance": {}}))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_parity_orchestration.subprocess, "run", fake_run)
    report_path = run_harness(settings)
    report = json.loads(report_path.read_text())

    assert report_path.is_file()
    assert not report["acceptance"]["passed"]
    assert all("worker result is missing" in message for message in report["worker_errors"].values())


@pytest.mark.parametrize(("passed", "status"), [(True, 0), (False, 1)])
def test_public_cli_returns_acceptance_status(tmp_path: pathlib.Path, monkeypatch, passed: bool, status: int) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"acceptance": {"passed": passed}}))
    monkeypatch.setattr(parity_cli, "run_harness", lambda _config: report)

    answer = parity_cli.main(["--mesh", __file__, "--output", str(tmp_path / "out")])

    assert answer == status


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"variants": ("scalar_rgb",)}, "at least two"),
        ({"variants": ("scalar_rgb", "scalar_rgb")}, "unique"),
        ({"rays": 0}, "positive"),
        ({"epsilon": -1.0}, "non-negative"),
        ({"max_material_mismatch_fraction": 2.0}, "cannot exceed"),
    ],
)
def test_config_rejects_invalid_comparisons(tmp_path: pathlib.Path, updates: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        config(tmp_path, **updates).validate()

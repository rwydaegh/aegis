"""Subprocess execution and result assembly for the GPU parity harness."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from dataclasses import asdict
from typing import Any

from .gpu_parity_report import compare_artifacts, compare_device_artifacts, speedup
from .gpu_parity_runtime import sha256_file
from .gpu_parity_schema import validate_worker_result


def run_workers(
    config: Any,
    output: pathlib.Path,
    config_path: pathlib.Path,
    rays_path: pathlib.Path,
    ray_hashes: dict[str, str],
) -> tuple[dict[str, Any], dict[str, pathlib.Path], dict[str, str]]:
    variants: dict[str, Any] = {}
    artifacts: dict[str, pathlib.Path] = {}
    errors: dict[str, str] = {}
    study = pathlib.Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    prior_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(study) if not prior_path else os.pathsep.join((str(study), prior_path))
    for index, variant in enumerate(config.variants):
        variant_dir = output / f"{index:02d}_{variant}"
        variant_dir.mkdir()
        artifact_path = variant_dir / "arrays.npz"
        result_path = variant_dir / "result.json"
        command = [
            sys.executable,
            "-m",
            "semantic_twin.cli.gpu_parity",
            "_worker",
            "--config",
            str(config_path),
            "--variant",
            variant,
            "--rays",
            str(rays_path),
            "--artifact",
            str(artifact_path),
            "--result",
            str(result_path),
            "--origins-sha256",
            ray_hashes["origins"],
            "--directions-sha256",
            ray_hashes["directions"],
        ]
        answer = subprocess.run(command, cwd=study, env=environment, check=False, capture_output=True, text=True)
        (variant_dir / "stdout.txt").write_text(answer.stdout)
        (variant_dir / "stderr.txt").write_text(answer.stderr)
        if answer.returncode != 0:
            detail = answer.stderr.strip().splitlines()
            errors[variant] = (
                f"exit code {answer.returncode}: {detail[-1]}" if detail else f"exit code {answer.returncode}"
            )
            continue
        try:
            row = validate_worker_result(
                json.loads(result_path.read_text()),
                variant=variant,
                config=json.loads(json.dumps(asdict(config))),
                expected_ray_hashes=ray_hashes,
                artifact_path=artifact_path,
                artifact_sha256=sha256_file(artifact_path),
            )
        except Exception as error:  # noqa: BLE001 - untrusted subprocess boundary
            errors[variant] = f"invalid worker result: {error}"
            continue
        variants[variant] = row
        artifacts[variant] = artifact_path
    return variants, artifacts, errors


def compare_variants(
    config: Any,
    variants: dict[str, Any],
    artifacts: dict[str, pathlib.Path],
    errors: dict[str, str],
) -> dict[str, Any]:
    reference_name = config.variants[0]
    comparisons: dict[str, Any] = {}
    if reference_name not in variants:
        return comparisons
    reference = variants[reference_name]
    for candidate_name in config.variants[1:]:
        if candidate_name not in variants:
            continue
        candidate = variants[candidate_name]
        try:
            legacy = compare_artifacts(artifacts[reference_name], artifacts[candidate_name], config.epsilon)
            device = compare_device_artifacts(
                artifacts[reference_name], artifacts[candidate_name], config.max_device_error
            )
        except (KeyError, TypeError, ValueError) as error:
            errors[candidate_name] = f"comparison failed: {error}"
            continue
        both_device = reference["device_sbr"] is not None and candidate["device_sbr"] is not None
        device_status = (
            {
                key: {"reference": reference["device_sbr"][key], "candidate": candidate["device_sbr"][key]}
                for key in (
                    "ray_start",
                    "rays",
                    "escaped",
                    "truncated",
                    "truncated_throughput",
                    "roulette_killed",
                )
            }
            if both_device
            else {}
        )
        comparisons[candidate_name] = {
            "reference": reference_name,
            "epsilon": config.epsilon,
            "legacy_hybrid": legacy,
            "device_sbr": device,
            "device_status": device_status,
            "speedup": {
                "intersection": speedup(reference["intersection"]["timing"], candidate["intersection"]["timing"]),
                "legacy_hybrid_sbr": speedup(
                    reference["legacy_hybrid_sbr"]["timing"], candidate["legacy_hybrid_sbr"]["timing"]
                ),
                "device_sbr": (
                    speedup(reference["device_sbr"]["timing"], candidate["device_sbr"]["timing"])
                    if both_device
                    else None
                ),
            },
        }
    return comparisons

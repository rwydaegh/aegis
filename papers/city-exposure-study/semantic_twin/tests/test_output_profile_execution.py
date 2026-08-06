from __future__ import annotations

import json
import time
from types import SimpleNamespace

import numpy as np

from semantic_twin.exposure.execution import (
    ExecutionConfig,
    OutputFiles,
    PreparedRun,
    _output_generation,
    _publish_generation,
    _stage_seconds,
    _storage_policy,
    _trace_rows,
)
from semantic_twin.exposure.output_policy import OutputProfile
from semantic_twin.exposure.reuse import complete_output, same_output_generation
from semantic_twin.runconfig import RunConfig


def _run() -> RunConfig:
    return RunConfig.escape_grid(
        site="korenmarkt",
        models=("rooftop",),
        locations=2,
        local_cells=2,
        rays=16,
        batch=16,
        tag="profile",
    )


def _multi_run() -> RunConfig:
    return RunConfig.escape_grid(
        site="korenmarkt",
        models=("isotropic", "rooftop", "street_small_cell"),
        locations=2,
        local_cells=2,
        rays=16,
        batch=16,
        tag="profile_multi",
    )


class _Result:
    local_grid = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    local_solid_angle = 2.0 * np.pi
    seconds = 0.01

    def __init__(self, value: float) -> None:
        self.rho = {
            "isotropic": np.array([value + 1.0, value + 2.0]),
            "rooftop": np.array([value, value + 1.0]),
            "street_small_cell": np.array([value + 2.0, value + 3.0]),
        }

    def scalars(self) -> dict[str, float]:
        result = {
            "sky_fraction": 0.3,
            "mean_bounces": 0.5,
            "mean_excess_delay_ns": 1.0,
            "escaped_fraction": 0.4,
            "truncated_throughput_share": 0.0,
        }
        for name in ("isotropic", "rooftop", "street_small_cell"):
            result[f"chi_{name}"] = 0.4
            result[f"chi_{name}_direct"] = 0.2
        return result


class _Coupler:
    def couple(self, *_args: object) -> SimpleNamespace:
        return SimpleNamespace(
            as_dict=lambda: {
                "reference_s0_w_m2": 1.0,
                "arriving_power_density_w_m2": 0.4,
                "susceptibility": 0.5,
                "peak_sab_w_m2": 0.2,
                "mean_sab_w_m2": 0.1,
                "absorbed_power_w": 0.01,
                "sar_wb_w_kg": 0.001,
            }
        )


def _prepared() -> PreparedRun:
    run = _run()
    walk = SimpleNamespace(
        points=np.array([[1.0, 2.0, 1.5], [3.0, 4.0, 1.5]]),
        ground_z_m=np.array([0.0, 0.0]),
        provenance={},
    )
    environment = SimpleNamespace(
        models={"rooftop": object()},
        reference_s0_w_m2=1.0,
        trace_standpoints=lambda *_args, **_kwargs: iter(((0, _Result(10.0)), (1, _Result(20.0)))),
    )
    return PreparedRun(
        run,
        environment,
        None,
        None,
        walk,
        np.array([0, 1]),
        None,
        object(),
        _Coupler(),
    )


def _multi_prepared() -> PreparedRun:
    run = _multi_run()
    walk = SimpleNamespace(
        points=np.array([[1.0, 2.0, 1.5], [3.0, 4.0, 1.5]]),
        ground_z_m=np.array([0.0, 0.0]),
        provenance={},
    )
    environment = SimpleNamespace(
        models={name: object() for name in run.models},
        reference_s0_w_m2=1.0,
        trace_standpoints=lambda *_args, **_kwargs: iter(((0, _Result(10.0)), (1, _Result(20.0)))),
    )
    return PreparedRun(
        run,
        environment,
        None,
        None,
        walk,
        np.array([0, 1]),
        None,
        object(),
        _Coupler(),
    )


def test_standard_trace_compresses_spectra_once_and_preserves_payload(tmp_path, monkeypatch) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    calls: list[dict[str, np.ndarray]] = []
    original = np.savez_compressed

    def save(path, **arrays):
        calls.append({name: np.array(value, copy=True) for name, value in arrays.items()})
        return original(path, **arrays)

    monkeypatch.setattr("semantic_twin.exposure.execution.np.savez_compressed", save)
    _trace_rows(_prepared(), ExecutionConfig(output_profile="standard"), files)

    assert len(calls) == 1
    saved = np.load(files.spectra)
    assert saved["rho_rooftop"].tolist() == [[10.0, 11.0], [20.0, 21.0]]
    assert saved["index"].tolist() == [0, 1]
    assert calls[0]["rho_rooftop"].tolist() == saved["rho_rooftop"].tolist()
    assert calls[0]["index"].tolist() == saved["index"].tolist()


def test_standard_trace_keeps_each_selected_model_spectrum(tmp_path) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    _trace_rows(_multi_prepared(), ExecutionConfig(output_profile="standard"), files)

    with np.load(files.spectra) as saved:
        assert {"rho_isotropic", "rho_rooftop", "rho_street_small_cell"} <= set(saved.files)
        assert saved["rho_isotropic"].tolist() == [[11.0, 12.0], [21.0, 22.0]]
        assert saved["rho_rooftop"].tolist() == [[10.0, 11.0], [20.0, 21.0]]
        assert saved["rho_street_small_cell"].tolist() == [[12.0, 13.0], [22.0, 23.0]]


def test_structured_manifest_validates_every_selected_model_spectrum(tmp_path) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    _trace_rows(_multi_prepared(), ExecutionConfig(output_profile="standard"), files)
    generation = _output_generation("b" * 32, files, files, profile="standard")
    manifest = {
        "storage_policy": _storage_policy("standard"),
        "output_generation": generation,
        "locations_traced": 2,
        "locations_requested": 2,
        "walk": {"candidates_after_clearance": 2},
    }

    assert complete_output(manifest, _multi_run(), files.rows, files.spectra)
    with np.load(files.spectra) as saved:
        arrays = {name: np.array(saved[name], copy=True) for name in saved.files if name != "rho_isotropic"}
    np.savez_compressed(files.spectra, **arrays)
    assert not complete_output(manifest, _multi_run(), files.rows, files.spectra)


def test_legacy_manifest_still_accepts_rooftop_only_spectrum(tmp_path) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    _trace_rows(_prepared(), ExecutionConfig(output_profile="standard"), files)
    manifest = {
        "output_generation": _output_generation("c" * 32, files, files, profile="standard"),
        "locations_traced": 2,
        "locations_requested": 2,
        "walk": {"candidates_after_clearance": 2},
    }

    assert complete_output(manifest, _run(), files.rows, files.spectra)


def test_minimal_trace_writes_complete_rows_without_spectra(tmp_path, monkeypatch) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    allocated: list[tuple[int, ...]] = []
    original = np.zeros

    def zeros(shape, *args, **kwargs):
        allocated.append(tuple(shape))
        return original(shape, *args, **kwargs)

    monkeypatch.setattr("semantic_twin.exposure.execution.np.zeros", zeros)
    _trace_rows(_prepared(), ExecutionConfig(output_profile=OutputProfile.MINIMAL), files)

    assert files.rows.exists()
    assert not files.spectra.exists()
    assert (2, 2) not in allocated
    rows = [json.loads(line) for line in files.rows.read_text().splitlines()]
    assert all(row["rooftop_peak_sab_w_m2"] == 0.2 for row in rows)
    assert all(row["rooftop_sar_wb_w_kg"] == 0.001 for row in rows)


def test_generation_seal_and_completeness_allow_minimal_without_spectra(tmp_path) -> None:
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")
    _trace_rows(_prepared(), ExecutionConfig(output_profile="minimal"), files)
    generation = _output_generation("a" * 32, files, files, profile="minimal")
    manifest = {
        "storage_policy": _storage_policy("minimal"),
        "output_generation": generation,
        "locations_traced": 2,
        "locations_requested": 2,
        "walk": {"candidates_after_clearance": 2},
    }

    assert set(generation["artifacts"]) == {"locations"}
    assert generation["publication_rule"].startswith("locations are written")
    assert same_output_generation(manifest, files.rows, files.spectra)
    assert complete_output(manifest, _run(), files.rows, files.spectra)

    files.spectra.write_bytes(b"stale")
    assert not same_output_generation(manifest, files.rows, files.spectra)


def test_minimal_publication_removes_previous_spectra(tmp_path) -> None:
    staged = OutputFiles(tmp_path / "staged_rows", tmp_path / "staged_spectra", tmp_path / "staged_manifest")
    published = OutputFiles(tmp_path / "rows", tmp_path / "spectra", tmp_path / "manifest")
    staged.rows.write_text("rows\n")
    staged.manifest.write_text("{}\n")
    published.spectra.write_bytes(b"old standard output")
    _publish_generation(staged, published, profile="minimal")

    assert published.rows.read_text() == "rows\n"
    assert not published.spectra.exists()


def test_full_policy_keeps_spectra_and_identifies_separate_audit_exporters() -> None:
    policy = _storage_policy(OutputProfile.FULL)
    assert policy["profile"] == "full"
    assert policy["spectra"]["retained"] is True
    assert "blender_payload" in policy["deferred_artifacts"]
    assert "blender_payload" not in policy["retained_artifacts"]
    assert policy["retained_artifacts"] == [
        "sealed_provenance",
        "standpoint_scalars",
        "angular_spectra",
        "source_law_facts",
        "body_coupling_inputs",
    ]
    assert policy["emitted_artifacts"]["angular_spectra"] == "<stem>_spectra.npz"
    assert "checkpoint_index" in policy["deferred_artifacts"]
    assert "restarts from the beginning" in policy["restart"]
    assert "separate explicit" in policy["paths"]
    assert "never invokes Blender" in policy["blender"]


def test_stage_seconds_ledger_has_stable_machine_readable_schema() -> None:
    ledger = _stage_seconds(
        {
            "scene_preparation_seconds": 1.0,
            "material_binding_seconds": 2.0,
            "walk_and_pick_seconds": 3.0,
            "tracer_coupler_setup_seconds": 4.0,
            "trace_reported_seconds": 5.0,
            "row_body_serialization_seconds": 6.0,
            "spectra_write_seconds": 7.0,
            "output_validation_publication_seconds": 8.0,
        },
        time.perf_counter(),
    )
    assert list(ledger) == [
        "schema",
        "version",
        "scene_preparation_seconds",
        "material_binding_seconds",
        "walk_and_pick_seconds",
        "tracer_coupler_setup_seconds",
        "trace_reported_seconds",
        "row_body_serialization_seconds",
        "spectra_write_seconds",
        "output_validation_publication_seconds",
        "total_wall_seconds",
    ]
    assert ledger["schema"] == "aegis.exposure.stage-seconds"
    assert ledger["version"] == 1
    assert all(isinstance(ledger[key], float) for key in list(ledger)[2:])

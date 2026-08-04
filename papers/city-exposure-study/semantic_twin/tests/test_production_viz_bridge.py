"""Production exposure inputs used by the Blender payload exporter."""

from __future__ import annotations

import hashlib
import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.exposure.reuse import model_identity
from semantic_twin.illumination import MODELS
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.tracer import TraceConfig
from semantic_twin.viz.blender import exporter as exporter_module
from semantic_twin.viz.blender.exporter import (
    export,
    load_production_run,
    production_provenance,
    production_role_payload,
    store_connections,
    validate_face_class_digest,
    validate_mesh_digest,
    visible_path_config,
)
from semantic_twin.viz.blender.payload import (
    ProductionFiles,
    available_spectrum_models,
    connection_render_layers,
    production_files,
)


def _run(**changes: object) -> RunConfig:
    values: dict[str, object] = {
        "site": "korenmarkt",
        "crop_m": 250,
        "law": "band",
        "models": ("rooftop",),
        "estimator": "escape",
        "next_event": None,
        "walk": "grid",
        "locations": 2,
        "frequency_hz": 15.0e9,
        "materials": "geometric",
        "rays": 20_000,
        "local_cells": 2,
        "seed": 7,
        "variant": "cuda_ad_rgb",
        "transport_kernel": "drjit",
        "tag": "acceptance",
    }
    values.update(changes)
    return RunConfig(**values)  # type: ignore[arg-type]


def _row(index: int) -> dict[str, float | int]:
    row: dict[str, float | int] = {
        "index": index,
        "x": float(index),
        "y": 2.0,
        "z": 3.0,
        "ground_z_m": 1.5,
        "seconds": 0.25,
        "sky_fraction": 0.4,
        "mean_bounces": 0.3,
        "mean_excess_delay_ns": 2.0,
        "escaped_fraction": 0.8,
        "truncated_throughput_share": 0.01,
        "chi_rooftop": 0.5,
        "chi_rooftop_direct": 0.2,
    }
    for suffix, value in {
        "reference_s0_w_m2": 1.0,
        "arriving_power_density_w_m2": 0.5,
        "susceptibility": 0.5,
        "peak_sab_w_m2": 0.2,
        "mean_sab_w_m2": 0.1,
        "absorbed_power_w": 0.03,
        "sar_wb_w_kg": 0.0004,
    }.items():
        row[f"rooftop_{suffix}"] = value
    return row


def _files(tmp_path: pathlib.Path, run: RunConfig | None = None) -> ProductionFiles:
    run = run or _run()
    files = ProductionFiles(
        tmp_path / "acceptance_locations.jsonl",
        tmp_path / "acceptance_spectra.npz",
        tmp_path / "acceptance_manifest.json",
    )
    files.locations.write_text("".join(json.dumps(_row(index)) + "\n" for index in range(2)))
    np.savez_compressed(
        files.spectra,
        index=np.array([0, 1]),
        rho_rooftop=np.array([[0.02, 0.03], [0.04, 0.01]]),
        local_grid=np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]),
        solid_angle=np.array(2.0 * np.pi),
    )
    model = dict(model_identity(MODELS["rooftop"]), description=MODELS["rooftop"].description)
    manifest = {
        "site": run.site,
        "ground_datum_m": 1.5,
        "mesh": "/tmp/mesh.ply",
        "mesh_sha256": "b" * 64,
        "reference_s0_w_m2": 1.0,
        "trace_config": {
            "frequency_hz": run.frequency_hz,
            "rays": run.rays,
            "local_cells": run.local_cells,
            "exit_bands": run.exit_bands,
            "max_bounces": run.max_bounces,
            "roulette_start": run.effective_roulette_start,
            "roulette_floor": run.roulette_floor,
            "ray_epsilon_m": run.ray_epsilon_m,
            "range_weighted_escape": run.range_weighted_escape,
            "seed": run.seed,
            "batch": run.batch,
        },
        "surface_binding": {},
        "semantic_binding": {"materials": "geometric", "face_class_sha256": "a" * 64},
        "walk": {"candidates_after_clearance": 2},
        "locations_requested": 2,
        "locations_traced": 2,
        "illumination_models": {"rooftop": model},
        "transport": {"kernel": "drjit"},
        "run_digest": run.digest(),
        "run": run.as_dict(),
    }
    files.manifest.write_text(json.dumps(manifest))
    return files


def test_named_production_stem_and_exact_paths_are_unambiguous(tmp_path: pathlib.Path) -> None:
    named = production_files(
        stem=pathlib.Path("hero"), locations=None, spectra=None, manifest=None, default_directory=tmp_path
    )
    assert named == ProductionFiles(
        tmp_path / "hero_locations.jsonl",
        tmp_path / "hero_spectra.npz",
        tmp_path / "hero_manifest.json",
    )

    with pytest.raises(ValueError, match="production input needs"):
        production_files(
            stem=None,
            locations=tmp_path / "rows.jsonl",
            spectra=None,
            manifest=None,
            default_directory=tmp_path,
        )
    with pytest.raises(ValueError, match="not both"):
        production_files(
            stem=pathlib.Path("hero"),
            locations=tmp_path / "rows.jsonl",
            spectra=tmp_path / "spectra.npz",
            manifest=tmp_path / "manifest.json",
            default_directory=tmp_path,
        )


def test_production_run_loads_exact_arrays_and_hashes_all_inputs(tmp_path: pathlib.Path) -> None:
    files = _files(tmp_path)
    data, run = load_production_run(files)

    assert data.index.tolist() == [0, 1]
    assert data.rho_rooftop.tolist() == [[0.02, 0.03], [0.04, 0.01]]
    assert data.local_grid.tolist() == [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]
    assert data.solid_angle == 2.0 * np.pi
    provenance = production_provenance(data, run)
    assert provenance["production_exposure"] == {
        "run_digest": run.digest(),
        "inputs": {
            "locations_jsonl": {
                "path": str(files.locations.resolve()),
                "sha256": hashlib.sha256(files.locations.read_bytes()).hexdigest(),
            },
            "spectra_npz": {
                "path": str(files.spectra.resolve()),
                "sha256": hashlib.sha256(files.spectra.read_bytes()).hexdigest(),
            },
            "manifest_json": {
                "path": str(files.manifest.resolve()),
                "sha256": hashlib.sha256(files.manifest.read_bytes()).hexdigest(),
            },
        },
        "arrays": {
            "walk": "locations JSONL",
            "rho_rooftop": "spectra NPZ",
            "body_scalars": "locations JSONL",
            "body_surface_field": "recomputed by AEGIS from the stored rooftop rho",
        },
    }
    assert provenance["estimator_arms"]["source_evidence"]["does_not_produce"] == [
        "rho",
        "body dose",
        "walk exposure",
    ]


@pytest.mark.parametrize(
    "failure",
    [
        "misaligned_index",
        "wrong_digest",
        "wrong_trace_config",
        "missing_face_hash",
        "host_transport",
        "torn_jsonl",
    ],
)
def test_malformed_production_run_is_rejected(tmp_path: pathlib.Path, failure: str) -> None:
    run = _run(transport_kernel="numpy", variant="llvm_ad_rgb") if failure == "host_transport" else _run()
    files = _files(tmp_path, run)
    if failure == "misaligned_index":
        with np.load(files.spectra) as saved:
            arrays = {name: np.array(saved[name]) for name in saved.files}
        arrays["index"] = np.array([1, 0])
        np.savez_compressed(files.spectra, **arrays)
    elif failure == "wrong_digest":
        manifest = json.loads(files.manifest.read_text())
        manifest["run_digest"] = "wrong"
        files.manifest.write_text(json.dumps(manifest))
    elif failure == "wrong_trace_config":
        manifest = json.loads(files.manifest.read_text())
        manifest["trace_config"]["seed"] += 1
        files.manifest.write_text(json.dumps(manifest))
    elif failure == "missing_face_hash":
        manifest = json.loads(files.manifest.read_text())
        manifest["semantic_binding"].pop("face_class_sha256")
        files.manifest.write_text(json.dumps(manifest))
    elif failure == "torn_jsonl":
        files.locations.write_text(files.locations.read_text().rstrip("\n"))

    with pytest.raises((TypeError, ValueError)):
        load_production_run(files)


def test_production_payload_exposes_only_spectra_that_exist() -> None:
    payload = {"rho_rooftop": np.ones(4)}
    assert available_spectrum_models(payload, ("isotropic", "rooftop", "street_small_cell")) == ("rooftop",)
    standalone = {f"rho_{name}": np.ones(4) for name in ("isotropic", "rooftop", "street_small_cell")}
    assert available_spectrum_models(standalone, ("isotropic", "rooftop", "street_small_cell")) == (
        "isotropic",
        "rooftop",
        "street_small_cell",
    )


def test_rebuilt_face_classes_must_match_the_production_digest() -> None:
    face_class = np.array([0, 2, 1], dtype=np.int8)
    digest = hashlib.sha256()
    digest.update(face_class.dtype.str.encode())
    digest.update(str(face_class.shape).encode())
    digest.update(face_class.tobytes())
    manifest = {"semantic_binding": {"face_class_sha256": digest.hexdigest()}}

    validate_face_class_digest(face_class, manifest)
    with pytest.raises(ValueError, match="face classes"):
        validate_face_class_digest(face_class[::-1], manifest)


def test_hero_mesh_must_match_the_production_bytes(tmp_path: pathlib.Path) -> None:
    mesh = tmp_path / "mesh.ply"
    mesh.write_bytes(b"production mesh")
    manifest = {"mesh_sha256": hashlib.sha256(mesh.read_bytes()).hexdigest()}

    validate_mesh_digest(mesh, manifest)
    mesh.write_bytes(b"changed mesh")
    with pytest.raises(ValueError, match="mesh bytes"):
        validate_mesh_digest(mesh, manifest)


def test_visible_path_trace_is_bounded_without_changing_physics_settings() -> None:
    production = TraceConfig(frequency_hz=15.0e9, rays=200_000, batch=400_000, max_bounces=3, seed=7)
    visible = visible_path_config(production, 1_200)

    assert visible.rays == 1_200
    assert visible.batch == 1_200
    assert visible.frequency_hz == production.frequency_hz
    assert visible.max_bounces == production.max_bounces
    assert visible.seed == production.seed


def test_production_connections_are_stored_as_source_evidence() -> None:
    bundle = {
        "payload": production_role_payload(),
        "manifest": {"hero": {}},
    }
    connections = {
        "path_index": np.array([0]),
        "vertex_index": np.array([0]),
        "origin": np.zeros((1, 3)),
        "site": np.ones((1, 3)),
        "azimuth_index": np.array([0]),
        "weight": np.array([1.0]),
        "blocked": np.array([False]),
        "paths": np.array([0]),
        "summary": {"connections": 1},
    }

    store_connections(bundle, connections)

    assert "next_event_estimation" not in bundle["manifest"]["hero"]
    assert bundle["manifest"]["hero"]["roofline_source_evidence"]["does_not_supply"] == [
        "rho",
        "body dose",
        "walk exposure",
    ]


def test_production_role_labels_are_explicit_and_self_consistent() -> None:
    labels = production_role_payload()
    assert labels["exposure_estimator_arm"].item() == "GPU escape transport and rooftop body exposure"
    assert labels["source_estimator_arm"].item() == "Roofline next-event and source evidence"
    assert "supplies no exposure value" in labels["visible_path_role"].item()


def test_figure_21_targets_the_connection_name_of_each_payload_family() -> None:
    layers = {"estimator_connections": "visibility", "skyline_rim": "direct_flux"}
    assert connection_render_layers(layers, {"estimator_connections", "skyline_rim"}) == layers
    assert connection_render_layers(layers, {"source_evidence_connections", "skyline_rim"}) == {
        "source_evidence_connections": "visibility",
        "skyline_rim": "direct_flux",
    }


def test_production_export_uses_a_digest_qualified_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _files(tmp_path)
    data, run = load_production_run(files)
    monkeypatch.setattr(exporter_module, "load_production_run", lambda unused: (data, run))
    monkeypatch.setattr(
        exporter_module,
        "trace_production_site",
        lambda args, loaded, config: {"payload": {"value": np.array([1])}, "manifest": {"site": config.site}},
    )
    args = SimpleNamespace(
        out=tmp_path / "viz",
        site="default-site",
        rim_only=False,
        evidence_only=False,
        evidence=False,
        production_files=files,
    )

    assert export(args) == 0
    stem = f"{run.site}_{run.frequency_ghz:g}ghz_{run.digest()}"
    assert (args.out / f"{stem}_payload.npz").is_file()
    assert (args.out / f"{stem}_manifest.json").is_file()
    assert not (args.out / f"{run.site}_payload.npz").exists()


@pytest.mark.parametrize("bad_manifest", [[], {"transport": []}])
def test_malformed_manifest_types_are_rejected(tmp_path: pathlib.Path, bad_manifest: object) -> None:
    files = _files(tmp_path)
    if isinstance(bad_manifest, list):
        files.manifest.write_text(json.dumps(bad_manifest))
    else:
        manifest = json.loads(files.manifest.read_text())
        manifest.update(bad_manifest)
        files.manifest.write_text(json.dumps(manifest))

    with pytest.raises((TypeError, ValueError)):
        load_production_run(files)

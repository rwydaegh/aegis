"""Production exposure inputs used by the Blender payload exporter."""

from __future__ import annotations

import hashlib
import inspect
import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

import export_propagation_payload as payload_cli
import propagation_blender as blender_cli
from semantic_twin.exposure.reuse import model_identity
from semantic_twin.illumination import MODELS
from semantic_twin.materials.atlas_binding import AtlasMaterialBinding
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.tracer import TraceConfig
from semantic_twin.viz.blender import exporter as exporter_module
from semantic_twin.viz.blender.exporter import (
    attach_production_surface_atlas,
    export,
    load_production_run,
    production_provenance,
    production_role_payload,
    store_connections,
    support_surface_fallback_manifest,
    validate_face_class_digest,
    validate_face_source_digest,
    validate_mesh_digest,
    visible_path_config,
)
from semantic_twin.vision.surface_atlas import (
    CameraSurfaceObservations,
    fuse_surface_observations,
    save_surface_atlas,
    sha256_file,
)
from semantic_twin.vision.provenance import AdmissionGate
from semantic_twin.viz.blender.payload import (
    ProductionFiles,
    available_spectrum_models,
    connection_render_layers,
    stamp_bundle_identity,
    verify_bundle_identity,
    production_files,
    production_scene_properties,
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
    tmp_path.mkdir(parents=True, exist_ok=True)
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
    manifest["output_generation"] = {
        "format_version": 1,
        "id": "1" * 32,
        "artifacts": {
            "locations": {
                "path": files.locations.name,
                "sha256": hashlib.sha256(files.locations.read_bytes()).hexdigest(),
                "bytes": files.locations.stat().st_size,
            },
            "spectra": {
                "path": files.spectra.name,
                "sha256": hashlib.sha256(files.spectra.read_bytes()).hexdigest(),
                "bytes": files.spectra.stat().st_size,
            },
        },
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


def test_cli_accepts_evidence_only_with_a_production_stem(tmp_path: pathlib.Path) -> None:
    stem = tmp_path / "production_walk"
    args = payload_cli.arguments(["--production-stem", str(stem), "--evidence-only", "--out", str(tmp_path)])

    assert args.evidence_only is True
    assert args.production_files == ProductionFiles(
        tmp_path / "production_walk_locations.jsonl",
        tmp_path / "production_walk_spectra.npz",
        tmp_path / "production_walk_manifest.json",
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
    assert provenance["estimator_arms"]["exposure"]["transport"] == {
        "kernel": "drjit",
        "variant": "cuda_ad_rgb",
    }


def test_production_run_refuses_unsealed_and_mixed_output_generations(tmp_path: pathlib.Path) -> None:
    unsealed = _files(tmp_path / "unsealed")
    document = json.loads(unsealed.manifest.read_text())
    del document["output_generation"]
    unsealed.manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="sealed output generation"):
        load_production_run(unsealed)

    mixed = _files(tmp_path / "mixed")
    rows = [json.loads(line) for line in mixed.locations.read_text().splitlines()]
    rows[0]["x"] = 99.0
    mixed.locations.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="sealed output generation"):
        load_production_run(mixed)


def test_production_scene_properties_flatten_exact_run_and_transport_identity() -> None:
    manifest = {
        "bundle": {"identity_sha256": "9" * 64},
        "production_exposure": {
            "run_digest": "abc123",
            "inputs": {
                "locations_jsonl": {"sha256": "a" * 64},
                "spectra_npz": {"sha256": "b" * 64},
                "manifest_json": {"sha256": "c" * 64},
            },
        },
        "support_surface_fallback": {
            "mesh_sha256": "d" * 64,
            "face_class_sha256": "e" * 64,
            "face_source_sha256": "f" * 64,
        },
        "surface_atlas": {
            "npz": {"sha256": "1" * 64},
            "manifest": {"sha256": "2" * 64},
            "content_sha256": "3" * 64,
            "mesh_sha256": "d" * 64,
            "admission": AdmissionGate.legacy_v1().as_dict(),
            "camera_ids": ["capture-a", "capture-b"],
        },
        "evidence": {
            "registration": {
                "admission": AdmissionGate.legacy_v1().as_dict(),
                "admitted_captures": ["capture-a", "capture-b"],
            }
        },
        "estimator_arms": {
            "exposure": {
                "transport": {
                    "kernel": "drjit",
                    "variant": "cuda_ad_rgb",
                    "floating_point": "float32",
                    "rng": {"family": "counter", "algorithm": "tea32"},
                    "versions": {"mitsuba": "3.8.0", "drjit": "1.3.1"},
                }
            }
        },
    }

    assert production_scene_properties(manifest) == {
        "visualization_bundle_sha256": "9" * 64,
        "production_run_digest": "abc123",
        "production_locations_sha256": "a" * 64,
        "production_spectra_sha256": "b" * 64,
        "production_manifest_sha256": "c" * 64,
        "support_mesh_sha256": "d" * 64,
        "support_fallback_face_class_sha256": "e" * 64,
        "support_fallback_face_source_sha256": "f" * 64,
        "surface_atlas_npz_sha256": "1" * 64,
        "surface_atlas_manifest_sha256": "2" * 64,
        "surface_atlas_content_sha256": "3" * 64,
        "surface_atlas_mesh_sha256": "d" * 64,
        "surface_atlas_admission_version": "registration-admission-v1",
        "surface_atlas_admission_json": json.dumps(
            AdmissionGate.legacy_v1().as_dict(), sort_keys=True, separators=(",", ":")
        ),
        "surface_atlas_admitted_captures_json": '["capture-a","capture-b"]',
        "registration_admission_version": "registration-admission-v1",
        "registration_admission_json": json.dumps(
            AdmissionGate.legacy_v1().as_dict(), sort_keys=True, separators=(",", ":")
        ),
        "registration_admitted_captures_json": '["capture-a","capture-b"]',
        "transport_kernel": "drjit",
        "transport_variant": "cuda_ad_rgb",
        "transport_floating_point": "float32",
        "transport_rng_family": "counter",
        "transport_rng_algorithm": "tea32",
        "mitsuba_version": "3.8.0",
        "drjit_version": "1.3.1",
    }


def test_standalone_scene_properties_remain_empty() -> None:
    assert production_scene_properties({"site": "korenmarkt"}) == {}


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


def test_rebuilt_face_sources_validate_new_manifests_and_mark_legacy_ones() -> None:
    face_source = np.array([0, 2, 2], dtype=np.int8)
    digest = hashlib.sha256()
    digest.update(face_source.dtype.str.encode())
    digest.update(str(face_source.shape).encode())
    digest.update(face_source.tobytes())
    manifest = {"semantic_binding": {"face_source_sha256": digest.hexdigest()}}

    assert validate_face_source_digest(face_source, manifest) is True
    assert validate_face_source_digest(face_source, {"semantic_binding": {}}) is False
    with pytest.raises(ValueError, match="material sources"):
        validate_face_source_digest(face_source[::-1], manifest)


def test_support_surface_fallback_records_exact_full_payload_and_provenance() -> None:
    face_class = np.array([0, 4], dtype=np.int8)
    face_source = np.array([0, 2], dtype=np.int8)

    def digest(value: np.ndarray) -> str:
        hashed = hashlib.sha256()
        hashed.update(value.dtype.str.encode())
        hashed.update(str(value.shape).encode())
        hashed.update(value.tobytes())
        return hashed.hexdigest()

    payload = {
        "support_full_vertices": np.array([[0.0, 0.0, 0.0]], dtype=np.float32),
        "support_full_faces": np.array([[0, 0, 0], [0, 0, 0]], dtype=np.int32),
        "support_full_face_class": face_class,
        "support_full_face_source": face_source,
        "support_full_face_index": np.array([0, 1], dtype=np.int32),
    }
    data = SimpleNamespace(
        manifest={
            "mesh_sha256": "b" * 64,
            "class_area_fractions": {"ground": 0.25, "semantic_brick": 0.75},
            "semantic_binding": {
                "materials": "walk",
                "image_ids": ["capture-a", "capture-b"],
                "face_class_sha256": digest(face_class),
                "face_source_sha256": digest(face_source),
            },
        }
    )
    material = SimpleNamespace(face_class=face_class, face_source=face_source)

    fallback = support_surface_fallback_manifest(
        payload,
        data,
        material,
        np.array([1.0, 3.0]),
        source_verified=True,
    )

    assert fallback["role"] == "whole-face geometric support and transport fallback"
    assert fallback["is_final_hit_position_material_map"] is False
    assert fallback["face_class_sha256"] == digest(face_class)
    assert fallback["face_source_sha256"] == digest(face_source)
    assert fallback["face_source_production_verified"] is True
    assert fallback["face_source_area_fractions"] == {"GEOMETRIC": 0.25, "IMAGE_WALK_ENTITY": 0.75}
    assert fallback["binding_provenance"]["image_ids"] == ["capture-a", "capture-b"]
    assert set(fallback["payload_arrays"]) == {
        "support_full_vertices",
        "support_full_faces",
        "support_full_face_class",
        "support_full_face_source",
        "support_full_face_index",
    }


def test_real_surface_atlas_artifact_bridges_into_production_payload(tmp_path: pathlib.Path) -> None:
    mesh_sha256 = "d" * 64
    atlas = fuse_surface_observations(
        (
            CameraSurfaceObservations(
                camera_id="capture-a",
                triangle_id=np.array([0], dtype=np.int32),
                barycentric=np.array([[1.0, 0.0, 0.0]], dtype=np.float32),
                entity=np.array([0], dtype=np.int16),
                entity_confidence=np.array([0.9], dtype=np.float32),
                rf_material=np.array([1], dtype=np.int16),
                material_prior_mass=np.array([1.0], dtype=np.float32),
                material_concept=np.array([0], dtype=np.int16),
                material_confidence=np.array([0.0], dtype=np.float32),
                material_source=np.array([0], dtype=np.uint8),
            ),
        ),
        triangle_count=1,
        atlas_resolution=2,
        entity_names=("Building",),
        material_names=("unknown", "brick"),
        concept_names=("unlabelled",),
        material_prior=np.array([[0.0, 1.0]], dtype=np.float32),
        concept_material=np.array([[1.0, 0.0]], dtype=np.float32),
        mesh_sha256=mesh_sha256,
    )
    atlas_path = tmp_path / "joint_atlas_250m_r2.npz"
    save_surface_atlas(
        atlas,
        atlas_path,
        metadata={
            "vocabularies": {"material_concept": ["unlabelled"]},
            "cameras": [{"camera_id": "capture-a", "panorama": "capture-a.png"}],
        },
    )
    run = _run(materials="atlas", atlas_npz=str(atlas_path))
    data = SimpleNamespace(
        manifest={
            "mesh_sha256": mesh_sha256,
            "semantic_binding": {"atlas_npz_sha256": sha256_file(atlas_path)},
        }
    )
    atlas_probability = np.zeros((1, 2, 2, 1), dtype=np.float32)
    atlas_probability[0, 0, 0, 0] = 1.0
    atlas_supported = np.zeros((1, 2, 2), dtype=bool)
    atlas_supported[0, 0, 0] = True
    material = SimpleNamespace(
        atlas_material=AtlasMaterialBinding(
            face_to_atlas_row=np.array([0], dtype=np.int32),
            material_probability=atlas_probability,
            supported=atlas_supported,
            valid_texels=atlas.valid_texels,
            material_names=("brick",),
            material_class=np.array([1], dtype=np.int32),
            provenance={
                "atlas_npz": str(atlas_path),
                "atlas_npz_sha256": sha256_file(atlas_path),
                "transport_posterior": "host-compatible joint entries only",
                "transport_states": {
                    "atlas_interface": 1,
                    "nonblocking_woody_vegetation": 0,
                    "geometric_fallback": 0,
                },
            },
        ),
        face_class=np.array([1], dtype=np.int8),
    )
    geometry = SimpleNamespace(
        vertices=np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]]),
        faces=np.array([[0, 1, 2]], dtype=np.int32),
    )
    payload: dict[str, object] = {}
    manifest: dict[str, object] = {}

    attach_production_surface_atlas(payload, manifest, data, run, material, geometry)

    assert payload["atlas_faces"].shape == (2, 3)
    assert payload["atlas_material"].tolist() == [1, 1]
    assert payload["atlas_sparse_cell"].tolist() == [0, 0]
    assert payload["atlas_texel_row"].tolist() == [0, 0]
    assert payload["atlas_texel_column"].tolist() == [0, 0]
    assert payload["atlas_transport_state"].tolist() == [0, 0]
    assert payload["atlas_transport_material"].tolist() == [0, 0]
    assert payload["atlas_transport_probabilities"].tolist() == [[1.0], [1.0]]
    record = manifest["surface_atlas"]
    assert record["npz"]["sha256"] == sha256_file(atlas_path)
    assert record["manifest"]["sha256"] == sha256_file(atlas_path.with_suffix(".json"))
    assert record["admission"] == AdmissionGate().as_dict()
    assert record["content_sha256"] == atlas.content_digest()
    assert record["camera_ids"] == ["capture-a"]
    assert manifest["admitted_captures"] == ["capture-a"]
    assert record["cameras"] == [{"camera_id": "capture-a", "panorama": "capture-a.png"}]
    assert record["vocabularies"]["entity"] == ["Building"]
    assert record["vocabularies"]["material"] == ["unknown", "brick"]
    assert record["transport_binding"]["transport_posterior"] == "host-compatible joint entries only"
    assert manifest["all_camera_fused_atlas"]["record"] == "surface_atlas"
    assert "final_surface_atlas" not in manifest

    sibling = atlas_path.with_suffix(".json")
    tampered = json.loads(sibling.read_text())
    tampered["artifact"]["sha256"] = "0" * 64
    sibling.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="artifact differs"):
        attach_production_surface_atlas({}, {}, data, run, material, geometry)


def test_hero_mesh_must_match_the_production_bytes(tmp_path: pathlib.Path) -> None:
    mesh = tmp_path / "mesh.ply"
    mesh.write_bytes(b"production mesh")
    manifest = {"mesh_sha256": hashlib.sha256(mesh.read_bytes()).hexdigest()}

    validate_mesh_digest(mesh, manifest)
    mesh.write_bytes(b"changed mesh")
    with pytest.raises(ValueError, match="mesh bytes"):
        validate_mesh_digest(mesh, manifest)


def test_production_mesh_relocates_with_the_checkout(tmp_path: pathlib.Path, monkeypatch) -> None:
    local_root = tmp_path / "relocated-study"
    local_mesh = local_root / "data" / "geometry" / "prague_staromestske" / "inhouse_leaf_250m_f64.ply"
    local_mesh.parent.mkdir(parents=True)
    local_mesh.write_bytes(b"the production mesh")
    monkeypatch.setattr(exporter_module, "SCRIPT_DIR", local_root)

    resolved = exporter_module._recorded_mesh(
        {
            "site": "prague_staromestske",
            "mesh": "/home/worker/aegis/papers/city-exposure-study/semantic_twin/data/geometry/"
            "prague_staromestske/inhouse_leaf_250m_f64.ply",
        }
    )

    assert resolved == local_mesh


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
    manifest = json.loads((args.out / f"{stem}_manifest.json").read_text())
    with np.load(args.out / f"{stem}_payload.npz") as payload:
        verify_bundle_identity(payload, manifest)


@pytest.mark.parametrize("option", ["--animation-ranked-paths", "--animation-nee-paths"])
def test_blender_cli_rejects_negative_animation_counts(option: str, tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit):
        blender_cli.arguments(
            ["--payload", str(tmp_path / "a.npz"), "--blend", str(tmp_path / "a.blend"), option, "-1"]
        )


def test_blender_cli_accepts_zero_animation_counts(tmp_path: pathlib.Path) -> None:
    args = blender_cli.arguments(
        [
            "--payload",
            str(tmp_path / "a.npz"),
            "--blend",
            str(tmp_path / "a.blend"),
            "--animation-ranked-paths",
            "0",
            "--animation-nee-paths",
            "0",
        ]
    )
    assert args.animation_paths == 0
    assert args.animation_nee_paths == 0


def test_blender_cli_stamps_collection_status_after_building_animation() -> None:
    source = inspect.getsource(blender_cli.main)

    assert source.index("animation.build_path_animation") < source.index("scene.hide_heavy_collections")


def test_crossed_payload_and_manifest_bundle_is_rejected() -> None:
    first_payload = {"value": np.array([1], dtype=np.int16)}
    first_manifest: dict[str, object] = {"site": "first"}
    second_payload = {"value": np.array([2], dtype=np.int16)}
    second_manifest: dict[str, object] = {"site": "second"}
    stamp_bundle_identity(first_payload, first_manifest)
    stamp_bundle_identity(second_payload, second_manifest)

    with pytest.raises(ValueError, match="payload content"):
        verify_bundle_identity(second_payload, first_manifest)


def test_evidence_only_reopens_digest_qualified_production_payload_without_tracing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _files(tmp_path)
    data, run = load_production_run(files)
    output = tmp_path / "viz"
    output.mkdir()
    stem = f"{run.site}_{run.frequency_ghz:g}ghz_{run.digest()}"
    payload_path = output / f"{stem}_payload.npz"
    manifest_path = output / f"{stem}_manifest.json"
    traced = np.array([3.0, 1.0, 4.0], dtype=np.float32)
    original_payload = {
        "traced_result": traced,
        "fishnet_vistas_faces": np.array([[0, 1, 2]], dtype=np.int32),
    }
    original_provenance = production_provenance(data, run)["production_exposure"]
    original_manifest = {
        "site": run.site,
        "production_exposure": original_provenance,
        "evidence": {"old": "discard me"},
    }
    stamp_bundle_identity(original_payload, original_manifest)
    np.savez_compressed(payload_path, **original_payload)
    manifest_path.write_text(json.dumps(original_manifest))

    monkeypatch.setattr(exporter_module, "load_production_run", lambda unused: (data, run))

    def fail_trace(*unused: object) -> None:
        raise AssertionError("evidence-only export must not initialize or run the production tracer")

    monkeypatch.setattr(exporter_module, "trace_production_site", fail_trace)

    def attach_local_evidence(args: object, bundle: dict[str, object]) -> None:
        payload = bundle["payload"]
        manifest = bundle["manifest"]
        assert isinstance(payload, dict)
        assert isinstance(manifest, dict)
        payload["fishnet_sam3_faces"] = np.array([[2, 1, 0]], dtype=np.int32)
        manifest["evidence"] = {"new": "local"}

    monkeypatch.setattr(exporter_module, "attach_evidence", attach_local_evidence)
    args = SimpleNamespace(
        out=output,
        site="wrong-default-site",
        rim_only=False,
        evidence_only=True,
        evidence=True,
        production_files=files,
    )

    assert export(args) == 0
    with np.load(payload_path) as reopened:
        assert np.array_equal(reopened["traced_result"], traced)
        assert "fishnet_vistas_faces" not in reopened.files
        assert np.array_equal(reopened["fishnet_sam3_faces"], np.array([[2, 1, 0]], dtype=np.int32))
    rebuilt_manifest = json.loads(manifest_path.read_text())
    with np.load(payload_path) as rebuilt_payload:
        verify_bundle_identity(rebuilt_payload, rebuilt_manifest)
    assert rebuilt_manifest["production_exposure"] == original_provenance
    assert rebuilt_manifest["evidence"] == {"new": "local"}


def test_evidence_only_refuses_an_unchecked_existing_pair_without_overwriting(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _files(tmp_path)
    data, run = load_production_run(files)
    output = tmp_path / "viz"
    output.mkdir()
    stem = f"{run.site}_{run.frequency_ghz:g}ghz_{run.digest()}"
    payload_path = output / f"{stem}_payload.npz"
    manifest_path = output / f"{stem}_manifest.json"
    np.savez_compressed(payload_path, traced_result=np.array([9], dtype=np.int8))
    manifest_path.write_text(
        json.dumps({"production_exposure": production_provenance(data, run)["production_exposure"]})
    )
    before_payload = payload_path.read_bytes()
    before_manifest = manifest_path.read_bytes()
    monkeypatch.setattr(exporter_module, "load_production_run", lambda unused: (data, run))
    args = SimpleNamespace(
        out=output,
        site=run.site,
        rim_only=False,
        evidence_only=True,
        evidence=True,
        production_files=files,
    )

    with pytest.raises(ValueError, match="shared bundle identity"):
        export(args)

    assert payload_path.read_bytes() == before_payload
    assert manifest_path.read_bytes() == before_manifest


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

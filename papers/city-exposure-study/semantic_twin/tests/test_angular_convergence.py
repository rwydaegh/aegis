from __future__ import annotations

import hashlib
import io
import json
import pathlib
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from run_angular_convergence import arguments
from semantic_twin.illumination import fibonacci_sphere
from semantic_twin.exposure.angular_convergence import (
    AngularConvergenceConfig,
    AngularRunSpec,
    FixedSector,
    FrozenStandpoints,
    _joined_array_sha256,
    _load_trace_checkpoint,
    _material_evidence_path,
    _paired_delta,
    _prepare_trace,
    _write_ensemble_spectra,
    _write_spectra,
    angular_distance_deg,
    code_provenance,
    file_sha256,
    load_reference,
    mean_seed_spectra,
    reusable_run,
    run_study,
    spectrum_metrics,
)
from semantic_twin.runconfig import RunConfig

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _reference_config(tmp_path: pathlib.Path) -> AngularConvergenceConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    locations = tmp_path / "reference_locations.jsonl"
    spectra = tmp_path / "reference_spectra.npz"
    manifest_path = tmp_path / "reference_manifest.json"
    mesh = tmp_path / "mesh.ply"
    mesh.write_bytes(b"mesh")
    rows = [
        {"index": 0, "x": 1.0, "y": 2.0, "z": 3.0, "ground_z_m": 0.0, "point_kind": "registered"},
        {"index": 1, "x": 4.0, "y": 5.0, "z": 6.0, "ground_z_m": 0.5, "point_kind": "stride"},
    ]
    locations.write_text("".join(json.dumps(row) + "\n" for row in rows))
    grid = fibonacci_sphere(2)
    np.savez_compressed(
        spectra,
        index=np.asarray([0, 1], dtype=np.int64),
        rho_rooftop=np.asarray([[1.0, 2.0], [3.0, 4.0]]),
        local_grid=grid,
        solid_angle=np.asarray(2.0 * np.pi),
    )
    manifest = {
        "site": "test",
        "mesh": str(mesh),
        "mesh_sha256": file_sha256(mesh),
        "locations_traced": 2,
        "run": {"local_cells": 2, "materials": "geometric"},
        "run_digest": "reference-run",
        "surface_binding": {},
        "output_generation": {
            "format_version": 1,
            "id": "2" * 32,
            "artifacts": {
                "locations": {
                    "path": locations.name,
                    "sha256": file_sha256(locations),
                    "bytes": locations.stat().st_size,
                },
                "spectra": {
                    "path": spectra.name,
                    "sha256": file_sha256(spectra),
                    "bytes": spectra.stat().st_size,
                },
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest))
    base = AngularConvergenceConfig.load(ROOT / "config/angular_convergence_quick.json")
    return replace(
        base,
        root=tmp_path,
        output_dir=tmp_path / "output",
        reference_manifest=manifest_path,
        reference_locations=locations,
        reference_spectra=spectra,
    )


def test_prepare_trace_passes_exact_atlas_material_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    from semantic_twin.exposure import execution
    from semantic_twin.transport import device_tracer

    geometry = object()
    atlas_material = object()
    trace_config = object()
    captured: dict[str, object] = {}

    class TracerSpy:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["args"] = args
            captured["kwargs"] = kwargs

    monkeypatch.setattr(execution, "_trace_config", lambda run, environment: trace_config)
    monkeypatch.setattr(device_tracer, "DeviceEscapeTracer", TracerSpy)
    scene = SimpleNamespace(geometry=geometry)
    material = SimpleNamespace(
        face_class=np.asarray([0], dtype=np.int32),
        table=SimpleNamespace(
            permittivity=np.asarray([1.0 + 0.0j]),
            rms_height_m=np.asarray([0.0]),
        ),
        atlas_material=atlas_material,
    )
    base = RunConfig(site="test", materials="atlas")

    _scene, _material, tracer, run = _prepare_trace(
        AngularRunSpec(cells=64, rays=2000, seed=7),
        (scene, material, base, object()),
    )

    assert isinstance(tracer, TracerSpy)
    assert captured["args"][-1] is trace_config
    assert captured["kwargs"] == {"atlas_material": atlas_material}
    assert captured["kwargs"]["atlas_material"] is material.atlas_material
    assert run.materials == "atlas"


def test_atlas_reference_freezes_atlas_instead_of_missing_walk_product(tmp_path: pathlib.Path) -> None:
    atlas = tmp_path / "atlas.npz"
    atlas.write_bytes(b"atlas")
    role, path = _material_evidence_path(
        tmp_path,
        {
            "run": {"materials": "atlas", "atlas_npz": "atlas.npz", "walk_npz": None},
            "semantic_binding": {},
        },
    )

    assert role == "joint_surface_atlas"
    assert path == atlas


def test_code_provenance_uses_source_digest_without_git(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "a" / "b" / "study"
    source = root / "semantic_twin" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n")
    (root / "run_angular_convergence.py").write_text("pass\n")

    def unavailable(*args: object, **kwargs: object) -> object:
        raise OSError("git is absent")

    monkeypatch.setattr("subprocess.run", unavailable)
    provenance = code_provenance(root)

    assert provenance["git_available"] is False
    assert provenance["git_dirty"] is None
    assert len(provenance["source_tree_sha256"]) == 64


def test_production_and_quick_profiles_pin_the_shared_reference() -> None:
    production = AngularConvergenceConfig.load(ROOT / "config/angular_convergence_4096.json")
    quick = AngularConvergenceConfig.load(ROOT / "config/angular_convergence_quick.json")

    assert production.reference_spec == (4096, 1_600_000)
    assert len(production.specs()) == 28
    assert production.specs().count(AngularRunSpec(4096, 1_600_000, 7)) == 1
    assert quick.reference_spec == (64, 2000)
    assert len(quick.specs()) == 6
    assert quick.scientific_config()["config_sha256"] == quick.config_sha256


def test_reference_loader_accepts_only_one_sealed_output_generation(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "body"
    data_dir.mkdir()
    (data_dir / "duke.stl").write_bytes(b"body")
    monkeypatch.setenv("AEGIS_DATA_DIR", str(data_dir))

    sealed = _reference_config(tmp_path / "sealed")
    identity = load_reference(sealed)
    assert identity.standpoints.index.tolist() == [0, 1]
    assert identity.files["locations"]["sha256"] == file_sha256(sealed.reference_locations)
    assert load_reference(sealed, body_path=data_dir / "duke.stl").body_sha256 == identity.body_sha256

    ella = data_dir / "ella.stl"
    ella.write_bytes(b"different body")
    assert load_reference(sealed, body_path=ella).body_sha256 == file_sha256(ella)
    assert load_reference(sealed, body_path=ella).body_sha256 != identity.body_sha256

    unsealed = _reference_config(tmp_path / "unsealed")
    document = json.loads(unsealed.reference_manifest.read_text())
    del document["output_generation"]
    unsealed.reference_manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="sealed output generation"):
        load_reference(unsealed)

    mixed = _reference_config(tmp_path / "mixed")
    rows = [json.loads(line) for line in mixed.reference_locations.read_text().splitlines()]
    rows[0]["x"] = 99.0
    mixed.reference_locations.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="sealed output generation"):
        load_reference(mixed)


def _atlas_reference_config(tmp_path: pathlib.Path) -> AngularConvergenceConfig:
    config = _reference_config(tmp_path)
    manifest = json.loads(config.reference_manifest.read_text())
    atlas = tmp_path / "atlas.npz"
    atlas.write_bytes(b"atlas")
    atlas_sha256 = file_sha256(atlas)
    sidecar = atlas.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "schema": "aegis.joint_semantic_material_atlas",
                "format_version": 1,
                "artifact": {
                    "path": atlas.name,
                    "sha256": atlas_sha256,
                    "content_sha256": "3" * 64,
                },
                "mesh": {"sha256": manifest["mesh_sha256"]},
            }
        )
    )
    manifest["run"].update({"materials": "atlas", "atlas_npz": atlas.name})
    manifest["semantic_binding"] = {
        "atlas_npz": atlas.name,
        "atlas_npz_sha256": atlas_sha256,
        "atlas_manifest": sidecar.name,
        "atlas_manifest_sha256": file_sha256(sidecar),
    }
    manifest["walk"] = {
        "route_geometry": "registered_road_v1",
        "path": "links",
        "stride_m": 6.0,
        "stations": 2,
        "road_length_m": 12.5,
    }
    config.reference_manifest.write_text(json.dumps(manifest))
    return config


def test_reference_loader_exposes_the_canonical_atlas_and_route_identity(
    tmp_path: pathlib.Path,
) -> None:
    body = tmp_path / "body.stl"
    body.write_bytes(b"body")
    config = _atlas_reference_config(tmp_path / "reference")

    identity = load_reference(config, body_path=body)

    assert identity.material_evidence.role == "joint_surface_atlas"
    assert identity.material_evidence.path == "atlas.npz"
    assert identity.material_evidence.atlas_json_sidecar_path == "atlas.json"
    assert identity.route is not None
    assert identity.route.geometry == "registered_road_v1"
    assert identity.route.path == "links"
    assert identity.route.stride_m == 6.0
    assert identity.route.registered_standpoints == 2
    assert identity.route.road_length_m == 12.5
    assert len(identity.route.canonical_walk_provenance_sha256) == 64


@pytest.mark.parametrize(
    ("field", "changed", "message"),
    (
        ("atlas_npz", "other.npz", "different surface atlases"),
        ("atlas_npz_sha256", "4" * 64, "atlas bytes differ"),
        ("atlas_manifest", "other.json", "noncanonical surface atlas sidecar path"),
        ("atlas_manifest_sha256", "5" * 64, "sidecar bytes differ"),
    ),
)
def test_reference_loader_rejects_each_atlas_pair_mutation(
    tmp_path: pathlib.Path,
    field: str,
    changed: str,
    message: str,
) -> None:
    body = tmp_path / "body.stl"
    body.write_bytes(b"body")
    config = _atlas_reference_config(tmp_path / "reference")
    manifest = json.loads(config.reference_manifest.read_text())
    manifest["semantic_binding"][field] = changed
    config.reference_manifest.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match=message):
        load_reference(config, body_path=body)


def test_reference_loader_rejects_publish_during_snapshot(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "body"
    data_dir.mkdir()
    (data_dir / "duke.stl").write_bytes(b"body")
    monkeypatch.setenv("AEGIS_DATA_DIR", str(data_dir))
    config = _reference_config(tmp_path / "reference")
    next_rows = [
        {"index": 0, "x": 99.0, "y": 2.0, "z": 3.0, "ground_z_m": 0.0, "point_kind": "registered"},
        {"index": 1, "x": 4.0, "y": 5.0, "z": 6.0, "ground_z_m": 0.5, "point_kind": "stride"},
    ]
    next_locations = "".join(json.dumps(row) + "\n" for row in next_rows).encode()
    next_spectra_buffer = io.BytesIO()
    np.savez_compressed(
        next_spectra_buffer,
        index=np.asarray([0, 1], dtype=np.int64),
        rho_rooftop=np.asarray([[9.0, 8.0], [7.0, 6.0]]),
        local_grid=fibonacci_sphere(2),
        solid_angle=np.asarray(2.0 * np.pi),
    )
    next_spectra = next_spectra_buffer.getvalue()
    next_manifest = json.loads(config.reference_manifest.read_text())
    next_manifest["output_generation"] = {
        "format_version": 1,
        "id": "3" * 32,
        "artifacts": {
            "locations": {
                "path": config.reference_locations.name,
                "sha256": hashlib.sha256(next_locations).hexdigest(),
                "bytes": len(next_locations),
            },
            "spectra": {
                "path": config.reference_spectra.name,
                "sha256": hashlib.sha256(next_spectra).hexdigest(),
                "bytes": len(next_spectra),
            },
        },
    }
    original_read_bytes = pathlib.Path.read_bytes
    published = False

    def publish_after_locations_snapshot(path: pathlib.Path) -> bytes:
        nonlocal published
        payload = original_read_bytes(path)
        if path == config.reference_locations and not published:
            published = True
            config.reference_locations.write_bytes(next_locations)
            config.reference_spectra.write_bytes(next_spectra)
            config.reference_manifest.write_text(json.dumps(next_manifest))
        return payload

    monkeypatch.setattr(pathlib.Path, "read_bytes", publish_after_locations_snapshot)

    with pytest.raises(ValueError, match="sealed output generation"):
        load_reference(config)
    assert published


def test_quick_cli_selects_a_profile_without_hiding_custom_config() -> None:
    assert arguments(["--quick"]).quick is True
    custom = arguments(["--config", "custom.json"])
    assert custom.config == pathlib.Path("custom.json")
    assert custom.quick is False


def test_spectrum_metrics_report_linear_mass_sectors_and_peak_direction() -> None:
    grid = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, -1.0, 0.0],
        ]
    )
    rho = np.asarray([1.0, 4.0, 2.0, 3.0])
    sectors = (
        FixedSector("north_half", (0.0, 180.0), (-90.0, 90.0)),
        FixedSector("south_half", (180.0, 360.0), (-90.0, 90.0)),
    )

    metrics = spectrum_metrics(grid, rho, 0.25, sectors)

    assert metrics["chi"] == pytest.approx(2.5)
    assert metrics["fixed_sector_mass"] == pytest.approx({"north_half": 1.25, "south_half": 1.25})
    assert metrics["peak_direction"]["unit_vector"] == pytest.approx([0.0, 1.0, 0.0])
    assert metrics["peak_direction"]["azimuth_deg"] == pytest.approx(90.0)
    assert metrics["peak_cell_mass"] == pytest.approx(1.0)
    assert metrics["peak_cell_share"] == pytest.approx(0.4)


def test_mean_seed_spectra_averages_rho_in_linear_power() -> None:
    grid = np.eye(3)
    first = np.asarray([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    second = np.asarray([[3.0, 5.0, 7.0], [4.0, 6.0, 8.0]])

    actual_grid, mean, solid_angle = mean_seed_spectra([(grid, first, 0.5), (grid.copy(), second, 0.5)])

    assert np.array_equal(actual_grid, grid)
    assert np.array_equal(mean, np.asarray([[2.0, 4.0, 6.0], [3.0, 5.0, 7.0]]))
    assert solid_angle == 0.5
    with pytest.raises(ValueError, match="different angular grids"):
        mean_seed_spectra([(grid, first, 0.5), (-grid, second, 0.5)])


def test_angular_distance_uses_a_great_circle() -> None:
    assert angular_distance_deg(np.asarray([1.0, 0.0, 0.0]), np.asarray([0.0, 1.0, 0.0])) == pytest.approx(90.0)
    assert angular_distance_deg(np.asarray([2.0, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0])) == pytest.approx(0.0)


def test_trace_checkpoint_resumes_only_a_proven_prefix(tmp_path: pathlib.Path) -> None:
    standpoints = FrozenStandpoints(
        index=np.asarray([3, 8], dtype=np.int64),
        points=np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
        ground_z_m=np.asarray([0.0, 0.5]),
        point_kind=("registered", "stride"),
        sha256="standpoints",
    )
    grid = fibonacci_sphere(2)
    rho = np.asarray([[2.0, 4.0]])
    spec = AngularRunSpec(cells=2, rays=10, seed=7)
    identity = "run-identity"
    spectra_path = tmp_path / "spectra.npz"
    _write_spectra(spectra_path, standpoints, rho, grid, np.pi * 2.0)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema": "angular-convergence-run-v2", "identity_sha256": identity})
    )
    scalar = [{"index": 3, "chi_rooftop": 1.0}]
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(
            {
                "schema": "angular-convergence-checkpoint-v2",
                "identity_sha256": identity,
                "complete_locations": 1,
                "scalar_rows": scalar,
                "spectra_file_sha256": file_sha256(spectra_path),
                "rho_prefix_sha256": _joined_array_sha256(rho),
                "local_grid_sha256": _joined_array_sha256(grid),
            }
        )
    )

    completed, saved, rows = _load_trace_checkpoint(
        tmp_path,
        identity,
        spec,
        standpoints,
        grid,
        np.pi * 2.0,
    )

    assert completed == 1
    assert np.array_equal(saved, rho)
    assert rows == scalar

    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_document = json.loads(checkpoint_path.read_text())
    checkpoint_document["scalar_rows"] = ["not-a-row"]
    checkpoint_path.write_text(json.dumps(checkpoint_document))
    assert _load_trace_checkpoint(tmp_path, identity, spec, standpoints, grid, np.pi * 2.0)[0] == 0
    checkpoint_document["scalar_rows"] = scalar
    checkpoint_path.write_text(json.dumps(checkpoint_document))

    # A crash can happen after the spectrum snapshot is replaced but before
    # its matching JSON checkpoint. The proven prefix still resumes.
    _write_spectra(
        tmp_path / "spectra.npz",
        standpoints,
        np.asarray([[2.0, 4.0], [6.0, 8.0]]),
        grid,
        np.pi * 2.0,
    )
    completed, saved, _ = _load_trace_checkpoint(
        tmp_path,
        identity,
        spec,
        standpoints,
        grid,
        np.pi * 2.0,
    )
    assert completed == 1
    assert np.array_equal(saved, rho)
    _write_spectra(
        spectra_path,
        standpoints,
        np.asarray([[9.0, 4.0], [6.0, 8.0]]),
        grid,
        np.pi * 2.0,
    )
    assert _load_trace_checkpoint(tmp_path, identity, spec, standpoints, grid, np.pi * 2.0)[0] == 0
    assert _load_trace_checkpoint(tmp_path, "stale", spec, standpoints, grid, np.pi * 2.0)[0] == 0


def test_ensemble_artifact_records_seed_members_and_no_smoothing(tmp_path: pathlib.Path) -> None:
    standpoints = FrozenStandpoints(
        index=np.asarray([0]),
        points=np.zeros((1, 3)),
        ground_z_m=np.zeros(1),
        point_kind=("registered",),
        sha256="standpoints",
    )
    path = tmp_path / "mean.npz"
    _write_ensemble_spectra(
        path,
        standpoints,
        np.asarray([[1.0, 2.0]]),
        np.asarray([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]),
        np.pi * 2.0,
        [7, 8, 9, 10],
        "ensemble-identity",
    )

    with np.load(path) as artifact:
        assert artifact["seeds"].tolist() == [7, 8, 9, 10]
        assert str(artifact["identity_sha256"]) == "ensemble-identity"
        assert str(artifact["aggregation"]) == "arithmetic_mean_linear_power"
        assert str(artifact["smoothing"]) == "none"
        assert np.array_equal(artifact["rho_rooftop_mean"], [[1.0, 2.0]])


def test_reusable_run_checks_hashes_arrays_and_metric_row_identity(tmp_path: pathlib.Path) -> None:
    standpoints = FrozenStandpoints(
        index=np.asarray([3, 8], dtype=np.int64),
        points=np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
        ground_z_m=np.asarray([0.0, 0.5]),
        point_kind=("registered", "stride"),
        sha256="standpoints",
    )
    grid = fibonacci_sphere(2)
    rho = np.asarray([[2.0, 4.0], [6.0, 8.0]])
    solid_angle = np.pi * 2.0
    spec = AngularRunSpec(cells=2, rays=10, seed=7)
    identity = "identity"
    run_dir = tmp_path / spec.name
    run_dir.mkdir()
    spectra_path = run_dir / "spectra.npz"
    metrics_path = run_dir / "metrics.json"
    _write_spectra(spectra_path, standpoints, rho, grid, solid_angle)

    def metric(index: int, kind: str) -> dict[str, object]:
        return {
            "index": index,
            "point_kind": kind,
            "chi": 1.0,
            "peak_rho_per_sr": 1.0,
            "peak_cell_mass": 1.0,
            "peak_cell_share": 1.0,
            "peak_direction": {"cell": 0, "unit_vector": [1.0, 0.0, 0.0]},
            "top_1_percent_mass": 1.0,
            "top_1_percent_share": 1.0,
            "fixed_sector_mass": {"all": 1.0},
            "body": {"p_abs_w": 1.0},
            "trace": {"index": index},
        }

    rows = [metric(3, "registered"), metric(8, "stride")]
    metrics_path.write_text(
        json.dumps(
            {
                "schema": "angular-convergence-metrics-v2",
                "identity_sha256": identity,
                "rows": rows,
            }
        )
    )
    manifest = {
        "schema": "angular-convergence-run-v2",
        "complete": True,
        "identity_sha256": identity,
        "spec": {"cells": 2, "rays": 10, "seed": 7},
        "locations_traced": 2,
        "standpoint_array_sha256": "standpoints",
        "local_grid_sha256": _joined_array_sha256(grid),
        "rho_sha256": _joined_array_sha256(rho),
        "spectra_file_sha256": file_sha256(spectra_path),
        "metrics_file_sha256": file_sha256(metrics_path),
        "solid_angle_sr": solid_angle,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    assert reusable_run(run_dir, identity, spec, standpoints)

    schema = manifest.pop("schema")
    manifest_path.write_text(json.dumps(manifest))
    assert not reusable_run(run_dir, identity, spec, standpoints)
    manifest["schema"] = schema

    metrics_hash = manifest.pop("metrics_file_sha256")
    manifest_path.write_text(json.dumps(manifest))
    assert not reusable_run(run_dir, identity, spec, standpoints)
    manifest["metrics_file_sha256"] = metrics_hash

    _write_spectra(spectra_path, standpoints, rho, -grid, solid_angle)
    manifest["spectra_file_sha256"] = file_sha256(spectra_path)
    manifest["local_grid_sha256"] = _joined_array_sha256(-grid)
    manifest_path.write_text(json.dumps(manifest))
    assert not reusable_run(run_dir, identity, spec, standpoints)
    _write_spectra(spectra_path, standpoints, rho, grid, solid_angle)
    manifest["spectra_file_sha256"] = file_sha256(spectra_path)
    manifest["local_grid_sha256"] = _joined_array_sha256(grid)

    bad_rows = [rows[1], rows[0]]
    metrics_path.write_text(
        json.dumps(
            {
                "schema": "angular-convergence-metrics-v2",
                "identity_sha256": identity,
                "rows": bad_rows,
            }
        )
    )
    manifest["metrics_file_sha256"] = file_sha256(metrics_path)
    manifest_path.write_text(json.dumps(manifest))
    assert not reusable_run(run_dir, identity, spec, standpoints)

    metrics_path.write_text(
        json.dumps(
            {
                "schema": "angular-convergence-metrics-v2",
                "identity_sha256": identity,
                "rows": rows,
            }
        )
    )
    manifest["metrics_file_sha256"] = file_sha256(metrics_path)
    manifest["rho_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    assert not reusable_run(run_dir, identity, spec, standpoints)


def test_initial_and_extended_dry_run_plans_have_separate_paths(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from semantic_twin.exposure import angular_convergence

    config = replace(
        AngularConvergenceConfig.load(ROOT / "config/angular_convergence_quick.json"),
        output_dir=tmp_path,
    )
    reference = SimpleNamespace(as_dict=lambda: {"reference": "frozen"})
    monkeypatch.setattr(angular_convergence, "load_reference", lambda _config: reference)
    monkeypatch.setattr(angular_convergence, "code_provenance", lambda _root: {"code": "frozen"})

    initial = run_study(config, dry_run=True)
    extended = run_study(config, extended_seeds=True, dry_run=True)

    assert initial == tmp_path / "initial_seeds/plan.json"
    assert extended == tmp_path / "extended_seeds/plan.json"
    assert json.loads(initial.read_text())["seed_mode"] == "initial_seeds"
    assert json.loads(extended.read_text())["seed_mode"] == "extended_seeds"


def test_paired_delta_reports_zero_crossings_outside_finite_db_population() -> None:
    delta = _paired_delta(
        np.asarray([2.0, 0.0, 0.0, 4.0]),
        np.asarray([1.0, 3.0, 0.0, 0.0]),
    )

    assert delta["median_db"] == pytest.approx(10.0 * np.log10(2.0))
    assert delta["db_population"] == {
        "total_pairs": 4,
        "finite_positive_pairs": 1,
        "actual_positive_reference_zero": 1,
        "actual_zero_reference_positive": 1,
        "both_zero": 1,
        "finite_db_statistics_use_positive_pairs_only": True,
    }

    extreme = _paired_delta(
        np.asarray([np.finfo(np.float64).max]),
        np.asarray([np.finfo(np.float64).tiny]),
    )
    assert np.isfinite(extreme["median_db"])
    assert np.isfinite(extreme["max_absolute_db"])
    assert extreme["root_mean_square_relative"] is None
    assert extreme["root_mean_square_relative_unrepresentable"] is True
    json.dumps(extreme, allow_nan=False)

    stable_rms = _paired_delta(
        np.asarray([0.0]),
        np.asarray([np.finfo(np.float64).max]),
    )
    assert stable_rms["root_mean_square_relative"] == pytest.approx(1.0)
    assert stable_rms["root_mean_square_relative_unrepresentable"] is False
    json.dumps(stable_rms, allow_nan=False)

    stable_mean = _paired_delta(
        np.full(2, np.finfo(np.float64).max),
        np.zeros(2),
    )
    assert stable_mean["mean_absolute"] == np.finfo(np.float64).max
    json.dumps(stable_mean, allow_nan=False)

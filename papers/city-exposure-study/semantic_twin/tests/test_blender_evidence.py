"""Evidence export failures stay visible in the payload and Blender file."""

from __future__ import annotations

import importlib
import json
import sys
import types
from types import SimpleNamespace

import numpy as np

from semantic_twin.viz.blender import exporter


def _arguments(site: str) -> SimpleNamespace:
    return SimpleNamespace(site=site, depth_stride=4, draw_radius_m=110.0)


def test_found_sam3_fishnet_records_a_missing_taxonomy_sidecar(tmp_path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    fishnet = outputs / "square_fishnet_sam3"
    fishnet.mkdir(parents=True)
    (fishnet / "h+00_000_fishnet.npz").touch()
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(exporter, "OUTPUTS", outputs)
    bundle = {"payload": {}, "manifest": {}}

    exporter.attach_evidence(_arguments("square"), bundle)

    status = bundle["manifest"]["evidence"]["layer_status"]["fishnet_sam3"]
    assert status == {
        "status": "skipped",
        "directory": "outputs/square_fishnet_sam3",
        "reason": "taxonomy sidecar is missing: outputs/square_sam3_projection_inputs/semantics.json",
    }


def test_found_empty_fishnet_records_that_it_has_no_surface_files(tmp_path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "square_fishnet_sam3").mkdir(parents=True)
    taxonomy = outputs / "square_sam3_projection_inputs" / "semantics.json"
    taxonomy.parent.mkdir(parents=True)
    taxonomy.write_text(json.dumps({"entity_id2label": {"0": "Unknown"}}))
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(exporter, "OUTPUTS", outputs)
    bundle = {"payload": {}, "manifest": {}}

    exporter.attach_evidence(_arguments("square"), bundle)

    status = bundle["manifest"]["evidence"]["layer_status"]["fishnet_sam3"]
    assert status["status"] == "skipped"
    assert status["reason"] == "directory contains no top-level *_fishnet.npz surfaces"


def test_empty_vistas_fishnet_also_explains_missing_support_layers(tmp_path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "square_fishnet_vistas").mkdir(parents=True)
    taxonomy = tmp_path / "data" / "panoramas" / "square" / "semantics" / "semantics.json"
    taxonomy.parent.mkdir(parents=True)
    taxonomy.write_text(json.dumps({"entity_id2label": {"0": "Unknown"}}))
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(exporter, "OUTPUTS", outputs)
    bundle = {"payload": {}, "manifest": {}}

    exporter.attach_evidence(_arguments("square"), bundle)

    statuses = bundle["manifest"]["evidence"]["layer_status"]
    assert statuses["fishnet_vistas"]["status"] == "skipped"
    assert statuses["support_evidence"]["reason"].startswith("Vistas fishnet was skipped:")
    assert statuses["rejected"]["reason"] == statuses["support_evidence"]["reason"]


def test_missing_body_file_does_not_shift_the_following_body_metadata(tmp_path) -> None:
    records = [{"body_id": name} for name in ("one", "missing", "three")]
    (tmp_path / "dynamic_bodies_manifest.json").write_text(json.dumps({"bodies": records}))
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    for name, offset in (("one", 1.0), ("three", 3.0)):
        np.savez(tmp_path / f"{name}.npz", vertices_enu_m=np.full((3, 3), offset), faces=faces)

    layer = exporter.body_layer(tmp_path)

    assert layer is not None
    assert [record["body_id"] for record in layer["records"]] == ["one", "three"]
    assert layer["vertices"][:, 0, 0].tolist() == [1.0, 3.0]
    assert layer["missing_body_ids"] == ["missing"]


def test_depth_cloud_marks_a_missing_auxiliary_manifest_as_partial(tmp_path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    mesh_depth = outputs / "square_mesh_depth"
    gated = outputs / "square_depth_fused"
    mesh_depth.mkdir(parents=True)
    gated.mkdir(parents=True)
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(
        exporter,
        "depth_cloud",
        lambda *args, **kwargs: {"points": np.zeros((2, 3)), "decision": np.zeros(2)},
    )
    payload: dict[str, object] = {}
    report: dict[str, object] = {"layer_status": {}}

    exporter._attach_mesh_depth(
        _arguments("square"),
        payload,
        report,
        {"mesh_depth": mesh_depth, "depth_gated": gated},
        {"position": np.zeros(3)},
    )

    status = report["layer_status"]["depth_mesh"]
    assert status["status"] == "built_partial"
    assert status["reason"] == "auxiliary manifest is missing: outputs/square_depth_fused/manifest.json"


def _evidence_module():
    if "bpy" not in sys.modules:
        stub = types.ModuleType("bpy")
        stub.types = types.SimpleNamespace(Object=object, Collection=object, Material=object)
        sys.modules["bpy"] = stub
    return importlib.import_module("semantic_twin.viz.blender.evidence")


def test_empty_blender_evidence_collection_carries_the_export_reason() -> None:
    evidence = _evidence_module()

    class Group(dict):
        objects: list[object] = []

    groups = {key: Group() for key in evidence.COLLECTION_LAYERS}
    manifest = {
        "evidence": {
            "layer_status": {
                "fishnet_sam3": {
                    "status": "skipped",
                    "reason": "taxonomy sidecar is missing",
                }
            }
        }
    }

    evidence.annotate_collection_status(groups, manifest)

    assert groups["semantics"]["status"] == "empty"
    assert groups["semantics"]["reason"] == "taxonomy sidecar is missing"
    assert json.loads(groups["semantics"]["layers"])["fishnet_sam3"]["status"] == "skipped"


def test_populated_collection_still_reports_a_missing_second_layer() -> None:
    evidence = _evidence_module()

    class Group(dict):
        objects: list[object]

        def __init__(self, objects: list[object] | None = None) -> None:
            super().__init__()
            self.objects = objects or []

    groups = {key: Group() for key in evidence.COLLECTION_LAYERS}
    groups["semantics"] = Group([object()])
    manifest = {
        "evidence": {
            "layer_status": {
                "fishnet_vistas": {"status": "built"},
                "fishnet_sam3": {"status": "skipped", "reason": "taxonomy sidecar is missing"},
            }
        }
    }

    evidence.annotate_collection_status(groups, manifest)

    assert groups["semantics"]["status"] == "built_partial"
    assert groups["semantics"]["reason"] == "taxonomy sidecar is missing"

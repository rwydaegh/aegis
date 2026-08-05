"""Evidence export failures stay visible in the payload and Blender file."""

from __future__ import annotations

import importlib
import json
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.viz.blender import exporter


def _arguments(site: str) -> SimpleNamespace:
    return SimpleNamespace(site=site, depth_stride=4, draw_radius_m=110.0)


def _support_mesh(directory, tmp_path, monkeypatch):
    path = tmp_path / "support.ply"
    path.touch()
    mesh = SimpleNamespace(
        vertices=np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0]]),
        faces=np.array([[0, 1, 2]]),
    )
    module = types.ModuleType("trimesh")
    module.load = lambda *args, **kwargs: mesh
    monkeypatch.setitem(sys.modules, "trimesh", module)
    (directory / "fishnet_manifest.json").write_text(json.dumps({"mesh": str(path)}))


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


def test_rejected_layer_draws_the_exact_fragment_from_version_two(tmp_path, monkeypatch) -> None:
    fishnet = tmp_path / "fishnet"
    fishnet.mkdir()
    _support_mesh(fishnet, tmp_path, monkeypatch)
    np.savez(
        fishnet / "view_fishnet.npz",
        rejected_source_triangle=np.array([0]),
        rejected_reason=np.array([7]),
        rejected_image_area_px=np.array([0.5]),
        rejected_vertices=np.array([[1.0, 1.0, 0.0], [2.0, 1.0, 0.0], [1.0, 2.0, 0.0]]),
        rejected_faces=np.array([[0, 1, 2]]),
        rejected_face_image=np.array([[[1.0, 1.0], [2.0, 1.0], [1.0, 2.0]]]),
        rejected_face_record=np.array([0]),
        rejected_face_offsets=np.array([0, 1]),
        rejected_geometry_kind=np.array([1], dtype=np.uint8),
        fishnet_format_version=np.array(2),
    )

    layer = exporter.rejected_layer(fishnet)

    assert layer is not None
    assert layer["faces"].shape == (1, 3)
    assert layer["vertices"][:, :2].max() == 2.0
    assert layer["geometry_source"].tolist() == [1]
    assert layer["geometry_kind"].tolist() == [1]
    assert layer["source_triangle"].tolist() == [0]
    assert layer["image_area_px"].tolist() == [0.5]
    assert layer["image_triangle_px"].shape == (1, 6)
    assert layer["view_names"] == ["view"]
    assert layer["fishnet_format_versions"] == [2]


def test_version_two_reports_rejections_whose_geometry_is_unavailable(tmp_path) -> None:
    fishnet = tmp_path / "fishnet"
    fishnet.mkdir()
    np.savez(
        fishnet / "view_fishnet.npz",
        rejected_source_triangle=np.array([0]),
        rejected_reason=np.array([10]),
        rejected_image_area_px=np.array([0.25]),
        rejected_vertices=np.zeros((0, 3)),
        rejected_faces=np.zeros((0, 3), dtype=np.int32),
        rejected_face_image=np.zeros((0, 3, 2)),
        rejected_face_record=np.zeros(0, dtype=np.int32),
        rejected_face_offsets=np.array([0, 0]),
        rejected_geometry_kind=np.array([0], dtype=np.uint8),
        fishnet_format_version=np.array(2),
    )

    layer = exporter.rejected_layer(fishnet)

    assert layer is not None
    assert layer["faces"].shape == (0, 3)
    assert layer["unavailable_rows_by_reason"] == {10: 1}
    assert layer["unavailable_image_area_px_by_reason"] == {10: 0.25}


def test_incomplete_version_two_rejected_geometry_fails_honestly(tmp_path) -> None:
    fishnet = tmp_path / "fishnet"
    fishnet.mkdir()
    np.savez(
        fishnet / "view_fishnet.npz",
        rejected_source_triangle=np.array([0]),
        rejected_reason=np.array([10]),
        rejected_image_area_px=np.array([0.25]),
        rejected_vertices=np.zeros((0, 3)),
        fishnet_format_version=np.array(2),
    )

    with pytest.raises(ValueError, match="format-v2 rejected geometry is incomplete"):
        exporter.rejected_layer(fishnet)


def _write_evidence_family(tmp_path, outputs, *, suffix: str, mesh_name: str, shape: tuple[int, int]) -> None:
    site = "square"
    fishnet = outputs / f"{site}_fishnet_vistas{suffix}"
    depth = outputs / f"{site}_mesh_depth{suffix}"
    fishnet.mkdir(parents=True)
    depth.mkdir(parents=True)
    mesh = tmp_path / "data" / mesh_name
    pose = tmp_path / "data" / "pose.json"
    mesh.parent.mkdir(parents=True, exist_ok=True)
    mesh.touch()
    pose.write_text("{}")
    view = "h+00_000"
    common = {
        "mesh": str(mesh.relative_to(tmp_path)),
        "pose": str(pose.relative_to(tmp_path)),
        "views": [{"view": view, "shape": list(shape)}],
    }
    (fishnet / "fishnet_manifest.json").write_text(
        json.dumps({**common, "mesh_depth": str(depth.relative_to(tmp_path))})
    )
    (depth / "manifest.json").write_text(json.dumps({**common, "camera_position_enu_m": [1.0, 2.0, 3.0]}))
    np.savez(
        fishnet / f"{view}_fishnet.npz",
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]], dtype=np.int32),
        face_image=np.array([[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]]),
        face_class=np.array([0]),
        face_class_probability=np.array([[1.0]]),
        camera_position=np.array([1.0, 2.0, 3.0]),
    )
    np.savez(
        depth / f"{view}.npz",
        range_m=np.ones(shape, dtype=np.float32),
        face_ids=np.zeros(shape, dtype=np.int32),
    )


def test_evidence_selection_keeps_one_mesh_pose_view_and_shape_family(tmp_path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    _write_evidence_family(tmp_path, outputs, suffix="_250m_v2", mesh_name="support250.ply", shape=(8, 8))
    _write_evidence_family(tmp_path, outputs, suffix="_fused", mesh_name="support130.ply", shape=(4, 4))
    # This tempting conventional path is the old 130 m depth. The selected
    # fishnet names its own 250 m depth directory and must keep it.
    (outputs / "square_mesh_depth").mkdir(exist_ok=True)
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(exporter, "OUTPUTS", outputs)

    directories, report = exporter.select_evidence_family("square")

    assert directories["fishnet_vistas"].name == "square_fishnet_vistas_250m_v2"
    assert directories["mesh_depth"].name == "square_mesh_depth_250m_v2"
    assert report["selection"] == "validated coherent family"
    assert report["views"] == {"h+00_000": [8, 8]}


def test_unavailable_fragment_counts_reach_the_export_manifest(tmp_path, monkeypatch) -> None:
    from semantic_twin.scene.fishnet import REJECTION_REASONS

    vistas = tmp_path / "fishnet"
    vistas.mkdir()
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.touch()
    ordered_reasons = sorted(REJECTION_REASONS.items(), key=lambda item: item[1])
    grazing = REJECTION_REASONS["grazing_plane"]
    refused = {
        "vertices": np.zeros((0, 3), dtype=np.float32),
        "faces": np.zeros((0, 3), dtype=np.int32),
        "reason": np.zeros(0, dtype=np.int16),
        "image_area_px": np.zeros(0, dtype=np.float32),
        "geometry_source": np.zeros(0, dtype=np.uint8),
        "reason_names": [name for name, _code in ordered_reasons],
        "reason_codes": [_code for _name, _code in ordered_reasons],
        "geometry_source_names": ["legacy_source_triangle_fallback", "exact_rejected_fragment"],
        "geometry_kind_names": ["unavailable", "exact_cut_piece", "clipped_footprint"],
        "fishnet_format_versions": [2],
        "view_names": ["view"],
        "unavailable_rows_by_reason": {grazing: 3},
        "unavailable_image_area_px_by_reason": {grazing: 1.25},
    }
    support = {
        "vertices": np.zeros((0, 3)),
        "faces": np.zeros((0, 3), dtype=np.int32),
        "clean_px": np.zeros(0),
        **{f"{name}_px": np.zeros(0) for name in exporter.REJECTION_GROUPS},
    }
    monkeypatch.setattr(exporter, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(exporter, "read_taxonomy", lambda path: {0: "unknown"})
    monkeypatch.setattr(exporter, "support_evidence_layer", lambda *args: support)
    monkeypatch.setattr(exporter, "rejected_layer", lambda *args: refused)
    monkeypatch.setattr(exporter, "surface_offset_to_drawn_mesh", lambda *args: {})
    payload = {
        "fishnet_vistas_vertices": np.zeros((3, 3)),
        "fishnet_vistas_faces": np.array([[0, 1, 2]]),
    }
    report = {"layer_status": {}}

    exporter._attach_support(_arguments("square"), payload, report, vistas, taxonomy)

    rejected = report["rejected"]
    assert rejected["unavailable_rows_by_reason"] == {"grazing_plane": 3}
    assert rejected["unavailable_image_area_px_by_reason"] == {"grazing_plane": 1.25}


def test_version_two_rejects_negative_fragment_record_indices(tmp_path) -> None:
    fishnet = tmp_path / "fishnet"
    fishnet.mkdir()
    np.savez(
        fishnet / "view_fishnet.npz",
        rejected_source_triangle=np.array([0]),
        rejected_reason=np.array([7]),
        rejected_image_area_px=np.array([0.5]),
        rejected_vertices=np.array([[1.0, 1.0, 0.0], [2.0, 1.0, 0.0], [1.0, 2.0, 0.0]]),
        rejected_faces=np.array([[0, 1, 2]]),
        rejected_face_image=np.array([[[1.0, 1.0], [2.0, 1.0], [1.0, 2.0]]]),
        rejected_face_record=np.array([-1]),
        rejected_face_offsets=np.array([0, 1]),
        rejected_geometry_kind=np.array([1], dtype=np.uint8),
        fishnet_format_version=np.array(2),
    )

    with pytest.raises(ValueError, match="out-of-range index"):
        exporter.rejected_layer(fishnet)


def test_rejected_layer_names_the_whole_source_triangle_as_a_legacy_fallback(tmp_path, monkeypatch) -> None:
    fishnet = tmp_path / "fishnet"
    fishnet.mkdir()
    _support_mesh(fishnet, tmp_path, monkeypatch)
    np.savez(
        fishnet / "view_fishnet.npz",
        rejected_source_triangle=np.array([0]),
        rejected_reason=np.array([7]),
        rejected_image_area_px=np.array([0.5]),
    )

    layer = exporter.rejected_layer(fishnet)

    assert layer is not None
    assert layer["vertices"][:, :2].max() == 10.0
    assert layer["geometry_source"].tolist() == [0]
    assert layer["geometry_kind"].tolist() == [3]
    assert layer["geometry_source_names"][0] == "legacy_source_triangle_fallback"
    assert layer["fishnet_format_versions"] == [1]


def test_blender_separates_exact_fragments_from_legacy_fallbacks(tmp_path, monkeypatch) -> None:
    evidence = _evidence_module()
    made: dict[str, dict] = {}

    def build_mesh(name, vertices, faces, into):
        made[name] = {"vertices": vertices, "faces": faces}
        return made[name]

    for name in ("attach_face_colour", "attach_values", "assign", "layered"):
        monkeypatch.setattr(evidence, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(evidence, "build_mesh", build_mesh)
    monkeypatch.setattr(evidence, "emissive_material", lambda *args, **kwargs: None)
    payload_path = tmp_path / "payload.npz"
    np.savez(
        payload_path,
        rejected_vertices=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0],
                [10.0, 0.0, 0.0],
                [0.0, 10.0, 0.0],
            ]
        ),
        rejected_faces=np.array([[0, 1, 2], [3, 4, 5]]),
        rejected_reason=np.array([7, 7]),
        rejected_image_area_px=np.array([0.5, 50.0]),
        rejected_geometry_source=np.array([1, 0], dtype=np.uint8),
    )
    manifest = {
        "evidence": {
            "rejected": {
                "reason_names": [f"reason_{index}" for index in range(1, 7)] + ["transient_object"],
                "fishnet_format_versions": [1, 2],
                "geometry_kind_names": ["unavailable", "exact_cut_piece", "clipped_footprint"],
            }
        }
    }

    with np.load(payload_path) as payload:
        counts = evidence.build_refused(payload, manifest, {})

    assert counts == {
        "drawn_triangles_by_reason": {
            "transient_object_legacy_source_triangle_fallback": 1,
            "transient_object": 1,
        },
        "drawn_triangles": 2,
        "unavailable_rows_by_reason": {},
        "unavailable_image_area_px_by_reason": {},
        "unavailable_rows": 0,
        "unavailable_image_area_px": 0,
    }
    assert "refused_transient_object" in made
    fallback = made["refused_transient_object_legacy_source_triangle_fallback"]
    assert fallback["geometry_source"] == "legacy source triangle fallback"
    assert fallback["fishnet_format_versions"] == "[1, 2]"


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
        def __init__(self) -> None:
            super().__init__()
            self.objects: list[object] = []

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


def test_unavailable_refusals_remain_in_collection_and_scene_status() -> None:
    evidence = _evidence_module()

    class Group(dict):
        def __init__(self) -> None:
            super().__init__()
            self.objects: list[object] = []

    groups = {key: Group() for key in evidence.COLLECTION_LAYERS}
    manifest = {
        "evidence": {
            "rejected": {
                "unavailable_rows_by_reason": {"grazing_plane": 3, "no_semantic_support": 2},
                "unavailable_image_area_px_by_reason": {"grazing_plane": 1.25, "no_semantic_support": 0.75},
            },
            "layer_status": {"rejected": {"status": "built", "triangles": 0}},
        }
    }

    result = evidence.build_refused(SimpleNamespace(files=()), manifest, groups["refused"])
    evidence.annotate_collection_status(groups, manifest)

    assert result == {
        "unavailable_rows_by_reason": {"grazing_plane": 3, "no_semantic_support": 2},
        "unavailable_image_area_px_by_reason": {"grazing_plane": 1.25, "no_semantic_support": 0.75},
        "unavailable_rows": 5,
        "unavailable_image_area_px": 2.0,
    }
    refused = groups["refused"]
    assert refused["status"] == "built_partial"
    assert refused["unavailable_rows_total"] == 5
    assert refused["unavailable_image_area_px_total"] == 2.0
    assert json.loads(refused["unavailable_rows_by_reason"])["grazing_plane"] == 3
    assert "5 format-v2 rejected rows have no drawable geometry" in refused["reason"]
    assert "withheld image area 2 px" in refused["reason"]


def test_panorama_build_uses_valid_pose_rows_and_reports_short_metadata(monkeypatch, tmp_path) -> None:
    evidence = _evidence_module()

    class LinkedObjects(list):
        def link(self, obj) -> None:
            self.append(obj)

    class Group(dict):
        def __init__(self) -> None:
            super().__init__()
            self.objects = LinkedObjects()

    class FakeObject(dict):
        def __init__(self, name, data=None) -> None:
            super().__init__()
            self.name = name
            self.data = data
            self.matrix_world = None

    made: dict[str, FakeObject] = {}

    def build_mesh(name, vertices, faces, into):
        obj = FakeObject(name)
        obj["vertices"] = vertices
        obj["faces"] = faces
        made[name] = obj
        into.objects.link(obj)
        return obj

    class CameraData(SimpleNamespace):
        pass

    camera_names: list[str] = []

    def new_camera(name):
        return CameraData(name=name, lens=None, clip_end=None)

    def new_object(name, data):
        camera_names.append(name)
        return FakeObject(name, data)

    evidence.bpy.data = SimpleNamespace(
        cameras=SimpleNamespace(new=new_camera),
        objects=SimpleNamespace(new=new_object),
    )
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=lambda rows: rows))
    monkeypatch.setattr(evidence, "build_mesh", build_mesh)
    for name in ("attach_face_colour", "assign", "layered"):
        monkeypatch.setattr(evidence, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(evidence, "emissive_material", lambda *args, **kwargs: None)

    payload_path = tmp_path / "panoramas.npz"
    np.savez(
        payload_path,
        pano_position=np.array([[0.0, 0.0, 1.0], [2.0, 0.0, 1.0], [4.0, 0.0, 1.0]]),
        pano_rotation=np.repeat(np.eye(3)[None, :, :], 2, axis=0),
        pano_sigma_vectors=np.eye(3)[None, :, :],
        pano_verdict=np.array([0, 1]),
        pano_residual_deg=np.array([0.5, 1.0, 1.5]),
    )
    manifest = {
        "evidence": {
            "registration": {"poses": [{"capture": "first"}], "reading": "registration audit"},
            "layer_status": {"registration": {"status": "built", "poses": 3}},
        }
    }
    group = Group()

    with np.load(payload_path) as payload:
        result = evidence.build_panoramas(payload, manifest, group, sigma_scale=10.0)

    assert result is not None
    assert result["pose_rows"] == 3
    assert result["markers"] == 3
    assert result["cameras"] == 2
    assert result["uncertainty_ellipsoids"] == 1
    assert camera_names == ["pano_00", "pano_01"]
    assert result["missing_metadata"]["registration_records"]["missing_rows"] == [1, 2]
    assert result["missing_metadata"]["rotation"]["missing_rows"] == [2]
    assert result["missing_metadata"]["sigma_vectors"]["missing_rows"] == [1, 2]
    assert result["missing_metadata"]["sky_conflict"]["missing_rows"] == [0, 1, 2]
    assert made["pano_markers"]["captures"] == ["first", "", ""]
    assert made["pano_uncertainty"]["pose_indices"] == [0]

    groups = {key: Group() for key in evidence.COLLECTION_LAYERS}
    groups["panoramas"] = group
    evidence.annotate_collection_status(groups, manifest)
    assert group["status"] == "built_partial"
    assert group["camera_count"] == 2
    assert "companion metadata is incomplete" in group["reason"]

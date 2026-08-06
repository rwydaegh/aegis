from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap
import types

import numpy as np
import pytest

from semantic_twin.vision.surface_atlas import _texel_polygons
from semantic_twin.viz.blender.atlas_display_lod import (
    DISPLAY_LOD_KEY_FIELDS,
    build_atlas_display_lod,
)
from semantic_twin.viz.blender import exporter

BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


def _canonical(
    *,
    resolution: int = 4,
    selected: dict[int, list[tuple[int, int]]] | None = None,
    key_changes: dict[tuple[int, int, int], tuple[int, ...]] | None = None,
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    support_vertices = np.asarray(
        [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [4.0, 0.0, 0.0], [7.0, 0.0, 0.0], [4.0, 3.0, 0.0]]
    )
    support_faces = np.asarray([[0, 1, 2], [3, 4, 5]])
    all_texels = [(row, column) for row in range(resolution) for column in range(resolution - row)]
    selected = selected or {0: all_texels, 1: all_texels}
    key_changes = key_changes or {}
    polygons = _texel_polygons(resolution)
    vertices: list[np.ndarray] = []
    faces: list[tuple[int, int, int]] = []
    source: list[int] = []
    sparse: list[int] = []
    rows: list[int] = []
    columns: list[int] = []
    categories = {name: [] for name in DISPLAY_LOD_KEY_FIELDS}
    cell_id = 0
    default_key = (1, 2, 0, 1, 3, 3)
    for source_id in sorted(selected):
        triangle = support_vertices[support_faces[source_id]]
        for row, column in selected[source_id]:
            uv = polygons[(row, column)]
            start = len(vertices)
            for u, v in uv:
                barycentric = np.asarray([1.0 - u - v, u, v])
                vertices.append(barycentric @ triangle)
            key = key_changes.get((source_id, row, column), default_key)
            for index in range(1, len(uv) - 1):
                faces.append((start, start + index, start + index + 1))
                source.append(source_id)
                sparse.append(cell_id)
                rows.append(row)
                columns.append(column)
                for name, value in zip(DISPLAY_LOD_KEY_FIELDS, key, strict=True):
                    categories[name].append(value)
            cell_id += 1
    canonical = {
        "atlas_vertices": np.asarray(vertices, dtype=np.float32),
        "atlas_faces": np.asarray(faces, dtype=np.int32),
        "atlas_source_triangle": np.asarray(source, dtype=np.int32),
        "atlas_sparse_cell": np.asarray(sparse, dtype=np.int64),
        "atlas_texel_row": np.asarray(rows, dtype=np.uint16),
        "atlas_texel_column": np.asarray(columns, dtype=np.uint16),
        **{name: np.asarray(values, dtype=np.int16) for name, values in categories.items()},
    }
    return canonical, support_vertices, support_faces


def _polygon_areas(arrays: dict[str, np.ndarray]) -> np.ndarray:
    vertices = arrays["atlas_display_vertices"]
    indices = arrays["atlas_display_polygon_indices"]
    offsets = arrays["atlas_display_polygon_offsets"]
    areas = []
    for start, stop in zip(offsets[:-1], offsets[1:], strict=True):
        polygon = vertices[indices[start:stop]]
        vector = 0.5 * np.sum(np.cross(polygon, np.roll(polygon, -1, axis=0)), axis=0)
        areas.append(np.linalg.norm(vector))
        assert vector[2] > 0.0
    return np.asarray(areas)


def test_complete_uniform_source_triangles_collapse_without_touching_canonical_arrays() -> None:
    canonical, support_vertices, support_faces = _canonical()
    before = {name: value.copy() for name, value in canonical.items()}

    first = build_atlas_display_lod(canonical, support_vertices, support_faces, resolution=4)
    second = build_atlas_display_lod(canonical, support_vertices, support_faces, resolution=4)

    assert first.polygon_count == 2
    assert first.merged_parent_triangle_count == 2
    assert first.canonical_cell_count == 20
    np.testing.assert_array_equal(first.arrays["atlas_display_cell_count"], [10, 10])
    np.testing.assert_array_equal(np.sort(first.arrays["atlas_display_sparse_cell_indices"]), np.arange(20))
    np.testing.assert_allclose(_polygon_areas(first.arrays), [4.5, 4.5], rtol=1e-6)
    assert all(np.array_equal(canonical[name], value) for name, value in before.items())
    assert first.membership_sha256 == second.membership_sha256
    assert all(np.array_equal(first.arrays[name], second.arrays[name]) for name in first.arrays)


def test_partial_coverage_and_mixed_keys_keep_one_polygon_per_exact_cell() -> None:
    all_texels = [(row, column) for row in range(4) for column in range(4 - row)]
    canonical, support_vertices, support_faces = _canonical(
        selected={0: all_texels[:-1], 1: all_texels},
        key_changes={(1, 0, 0): (9, 2, 0, 1, 3, 3)},
    )

    lod = build_atlas_display_lod(canonical, support_vertices, support_faces, resolution=4)

    assert lod.merged_parent_triangle_count == 0
    assert lod.polygon_count == 19
    assert np.all(lod.arrays["atlas_display_cell_count"] == 1)
    assert np.all(_polygon_areas(lod.arrays) > 0.0)
    offsets = lod.arrays["atlas_display_sparse_cell_offsets"]
    membership = lod.arrays["atlas_display_sparse_cell_indices"]
    sources = lod.arrays["atlas_display_source_triangle"]
    sparse_source = {
        int(cell): int(source)
        for cell, source in zip(canonical["atlas_sparse_cell"], canonical["atlas_source_triangle"], strict=True)
    }
    for polygon, (start, stop) in enumerate(zip(offsets[:-1], offsets[1:], strict=True)):
        assert {sparse_source[int(cell)] for cell in membership[start:stop]} == {int(sources[polygon])}


def test_canonical_cell_cover_is_disjoint_and_has_equal_area() -> None:
    selected = {0: [(0, 0), (0, 1), (1, 0)], 1: [(0, 0), (1, 1)]}
    canonical, support_vertices, support_faces = _canonical(selected=selected)
    lod = build_atlas_display_lod(canonical, support_vertices, support_faces, resolution=4)
    raw_triangles = canonical["atlas_vertices"][canonical["atlas_faces"]]
    raw_area = (
        0.5
        * np.linalg.norm(
            np.cross(raw_triangles[:, 1] - raw_triangles[:, 0], raw_triangles[:, 2] - raw_triangles[:, 0]), axis=1
        ).sum()
    )

    membership = lod.arrays["atlas_display_sparse_cell_indices"]
    assert len(membership) == len(np.unique(membership)) == len(np.unique(canonical["atlas_sparse_cell"]))
    assert _polygon_areas(lod.arrays).sum() == pytest.approx(raw_area, rel=3e-6)


def test_exporter_appends_hashed_display_arrays_without_changing_canonical_payload(tmp_path, monkeypatch) -> None:
    canonical, support_vertices, support_faces = _canonical(resolution=2, selected={0: [(0, 0), (0, 1), (1, 0)]})
    for name in DISPLAY_LOD_KEY_FIELDS[2:]:
        canonical.pop(name)
    raw_faces = len(canonical["atlas_faces"])
    canonical.update(
        {
            "atlas_confidence": np.ones(raw_faces, dtype=np.float32),
            "atlas_camera_count": np.ones(raw_faces, dtype=np.uint16),
            "atlas_observation_count": np.ones(raw_faces, dtype=np.uint32),
            "atlas_entity_probabilities": np.tile([0.0, 1.0], (raw_faces, 1)).astype(np.float32),
            "atlas_material_probabilities": np.tile([0.0, 0.0, 1.0], (raw_faces, 1)).astype(np.float32),
        }
    )
    canonical_before = {name: value.copy() for name, value in canonical.items()}
    artifact = tmp_path / "atlas.npz"
    artifact.write_bytes(b"atlas")
    artifact.with_suffix(".json").write_text('{"admission": {}}')
    digest = exporter.sha256_file(artifact)
    atlas = types.SimpleNamespace(
        source_mask=np.full(3, 3, dtype=np.uint8),
        prior_weight=np.ones(3, dtype=np.float32),
        concept_weight=np.ones(3, dtype=np.float32),
        atlas_resolution=2,
        observed_triangle_count=1,
        cell_count=3,
        station_ids=("camera",),
        mesh_sha256="b" * 64,
        content_digest=lambda: "c" * 64,
    )
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0, 1] = probability[0, 0, 1, 1] = probability[0, 1, 0, 1] = 1.0
    supported = probability.sum(axis=-1) > 0.0
    binding = types.SimpleNamespace(
        face_to_atlas_row=np.asarray([0, -1]),
        supported=supported,
        nonblocking=np.zeros_like(supported),
        material_probability=probability,
        material_names=("unknown", "brick"),
        provenance={},
    )
    material = types.SimpleNamespace(atlas_material=binding, face_class=np.asarray([1, 1]))
    data = types.SimpleNamespace(manifest={"mesh_sha256": "b" * 64, "semantic_binding": {"atlas_npz_sha256": digest}})
    geometry = types.SimpleNamespace(vertices=support_vertices, faces=support_faces)
    run = types.SimpleNamespace(atlas_npz=str(artifact))
    monkeypatch.setattr(exporter, "load_surface_atlas", lambda *_args, **_kwargs: atlas)
    monkeypatch.setattr(
        exporter, "to_surface_mesh", lambda *_args, **_kwargs: types.SimpleNamespace(as_arrays=lambda: canonical)
    )
    monkeypatch.setattr(
        exporter,
        "artifact_admission_gate",
        lambda *_args, **_kwargs: types.SimpleNamespace(as_dict=lambda: {"version": 1}),
    )
    payload: dict[str, np.ndarray] = {}
    manifest: dict[str, object] = {"class_names": ["ground", "wall"]}

    exporter.attach_production_surface_atlas(payload, manifest, data, run, material, geometry)

    for name, expected in canonical_before.items():
        np.testing.assert_array_equal(payload[name], expected)
    lod = manifest["surface_atlas"]["display_lod"]
    assert lod["display_only"] is True
    assert lod["canonical_triangle_face_count"] == raw_faces
    assert lod["canonical_sparse_cell_count"] == 3
    assert lod["display_polygon_count"] == 1
    assert lod["merged_parent_triangle_count"] == 1
    assert len(lod["membership_sha256"]) == 64
    assert set(lod["payload_arrays"]) == {name for name in payload if name.startswith("atlas_display_")}


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_blender_uses_polygon_lod_for_categories_and_raw_mesh_for_continuous_audit(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "atlas-lod.json"
    script = tmp_path / "atlas_lod_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys
            import bpy
            import numpy as np
            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender import scene

            scene.reset_scene()
            payload = {{
                "atlas_vertices": np.array([[0,0,0], [1,0,0], [1,1,0], [0,1,0]], dtype=float),
                "atlas_faces": np.array([[0,1,2], [0,2,3]]),
                "atlas_entity": np.array([1, 1]), "atlas_material": np.array([1, 1]),
                "atlas_confidence": np.array([0.4, 0.9]),
                "atlas_camera_count": np.array([1, 3]), "atlas_observation_count": np.array([2, 8]),
                "atlas_entity_probabilities": np.array([[0.1,0.9], [0.2,0.8]]),
                "atlas_material_probabilities": np.array([[0.1,0.9], [0.3,0.7]]),
                "atlas_transport_state": np.array([0,0]), "atlas_transport_material": np.array([1,1]),
                "atlas_transport_probabilities": np.array([[0.1,0.9], [0.3,0.7]]),
                "atlas_geometric_fallback_class": np.array([1,1]), "atlas_source_mask": np.array([3,3]),
                "atlas_vistas_prior_weight": np.array([1.0,2.0]), "atlas_sam3_concept_weight": np.array([3.0,4.0]),
                "atlas_display_vertices": np.array([[0,0,0], [1,0,0], [1,1,0], [0,1,0]], dtype=float),
                "atlas_display_polygon_offsets": np.array([0,4]), "atlas_display_polygon_indices": np.array([0,1,2,3]),
                "atlas_display_source_triangle": np.array([7]),
                "atlas_display_entity": np.array([1]), "atlas_display_material": np.array([1]),
                "atlas_display_transport_state": np.array([0]), "atlas_display_transport_material": np.array([1]),
                "atlas_display_geometric_fallback_class": np.array([1]), "atlas_display_source_mask": np.array([3]),
                "atlas_display_cell_count": np.array([2]),
            }}
            manifest = {{
                "class_names": ["ground", "wall"],
                "surface_atlas": {{
                    "vocabularies": {{"entity": ["unknown", "building"], "material": ["unknown", "brick"]}},
                    "transport_audit": {{"material_names": ["unknown", "brick"]}},
                }},
            }}
            groups = {{key: scene.collection(key) for key in (
                "transport_state", "transport_material", "transport_fallback", "source_contribution",
                "vistas_contribution", "sam3_contribution", "entity_semantics", "atlas_confidence",
                "atlas_camera_count", "atlas_observation_count",
            )}}
            result = scene.build_fused_semantic_surface(
                payload, manifest, scene.collection("fused_semantics"), audit_collections=groups
            )
            hero = bpy.data.objects["all_camera_fused_surface_atlas"]
            raw = bpy.data.objects["all_camera_fused_surface_atlas_raw"]
            categorical = bpy.data.objects["atlas_final_transport_state"]
            continuous = bpy.data.objects["all_camera_atlas_confidence"]
            output = {{
                "result": result,
                "hero_polygons": len(hero.data.polygons), "hero_loop_total": hero.data.polygons[0].loop_total,
                "raw_polygons": len(raw.data.polygons), "raw_hidden": [raw.hide_viewport, raw.hide_render],
                "categorical_shared": categorical.data == hero.data,
                "continuous_shared": continuous.data == raw.data,
                "continuous_visible": [continuous.hide_viewport, continuous.hide_render],
                "raw_has_confidence": "confidence" in raw.data.attributes,
                "hero_has_confidence": "confidence" in hero.data.attributes,
            }}
            pathlib.Path({str(report)!r}).write_text(json.dumps(output))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert report.is_file(), result.stdout[-3000:] + result.stderr[-3000:]
    measured = json.loads(report.read_text())
    assert measured["result"] == {"status": "built", "faces": 1}
    assert measured["hero_polygons"] == 1
    assert measured["hero_loop_total"] == 4
    assert measured["raw_polygons"] == 2
    assert measured["raw_hidden"] == [True, True]
    assert measured["categorical_shared"]
    assert measured["continuous_shared"]
    assert measured["continuous_visible"] == [False, False]
    assert measured["raw_has_confidence"]
    assert not measured["hero_has_confidence"]

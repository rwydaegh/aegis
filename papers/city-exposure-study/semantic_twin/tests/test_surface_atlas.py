from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import replace

import numpy as np
import pytest

import build_surface_atlas
from semantic_twin.materials.atlas import (
    FALLBACK_UNOBSERVED,
    SOURCE_VISTAS_PRIOR,
    JointSemanticMaterialAtlas,
)
from semantic_twin.vision.surface_atlas import (
    CameraSurfaceObservations,
    _texel_indices,
    fuse_surface_observations,
    load_surface_atlas,
    save_surface_atlas,
    to_surface_mesh,
)

MESH_SHA = "a" * 64
ENTITY_NAMES = ("Building", "Road", "Curb", "Person")
MATERIAL_NAMES = ("unknown", "brick", "glass", "asphalt_concrete", "human_tissue")
CONCEPT_NAMES = ("unlabelled", "glass window")
PRIOR = np.array(
    (
        (0.0, 0.6, 0.4, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 0.0, 1.0),
    ),
    dtype=np.float32,
)
CONCEPT = np.array(((1.0, 0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0, 0.0)), dtype=np.float32)


def observation(
    camera_id: str,
    barycentric: np.ndarray,
    *,
    entity: int = 0,
    source: int = 0,
    confidence: float = 1.0,
) -> CameraSurfaceObservations:
    count = len(barycentric)
    concept = np.full(count, source, dtype=np.int16)
    if source:
        material = np.full(count, 2, dtype=np.int16)
        mass = np.ones(count)
        material_confidence = np.full(count, confidence)
    else:
        material = np.full(count, PRIOR[entity].argmax(), dtype=np.int16)
        mass = np.full(count, PRIOR[entity].max())
        material_confidence = np.zeros(count)
    return CameraSurfaceObservations(
        camera_id=camera_id,
        triangle_id=np.zeros(count, dtype=np.int32),
        barycentric=np.asarray(barycentric, dtype=np.float32),
        entity=np.full(count, entity, dtype=np.int16),
        entity_confidence=np.full(count, confidence, dtype=np.float32),
        rf_material=material,
        material_prior_mass=mass,
        material_concept=concept,
        material_confidence=material_confidence,
        material_source=np.full(count, source, dtype=np.uint8),
    )


def fuse(*cameras: CameraSurfaceObservations, resolution: int = 3) -> JointSemanticMaterialAtlas:
    return fuse_surface_observations(
        cameras,
        triangle_count=2,
        atlas_resolution=resolution,
        entity_names=ENTITY_NAMES,
        material_names=MATERIAL_NAMES,
        concept_names=CONCEPT_NAMES,
        material_prior=PRIOR,
        concept_material=CONCEPT,
        mesh_sha256=MESH_SHA,
    )


def test_full_material_distributions_survive_instead_of_quicklook_winners() -> None:
    atlas = fuse(observation("view", np.array(((1.0, 0.0, 0.0),))))

    posterior = atlas.material_probability[0, 0, 0]
    np.testing.assert_allclose(posterior, PRIOR[0])
    assert atlas.material_label[0] == MATERIAL_NAMES.index("brick")
    assert posterior[MATERIAL_NAMES.index("glass")] == pytest.approx(0.4)


def test_each_camera_gets_one_texel_vote_regardless_of_pixel_count() -> None:
    repeated = np.repeat(np.array(((1.0, 0.0, 0.0),)), 40, axis=0)
    atlas = fuse(
        observation("close", repeated),
        observation("far", np.array(((1.0, 0.0, 0.0),)), source=1),
    )

    posterior = atlas.material_probability[0, 0, 0]
    assert posterior[MATERIAL_NAMES.index("brick")] == pytest.approx(0.3)
    assert posterior[MATERIAL_NAMES.index("glass")] == pytest.approx(0.7)
    assert atlas.camera_count[0] == 2
    assert atlas.observation_count[0] == 41
    assert atlas.prior_weight[0] == pytest.approx(1.0)
    assert atlas.concept_weight[0] == pytest.approx(1.0)


def test_zero_support_cells_and_direct_face_join_are_explicit() -> None:
    atlas = fuse(observation("view", np.array(((1.0, 0.0, 0.0),))))

    np.testing.assert_array_equal(atlas.face_to_atlas_row, np.array((0, -1)))
    assert atlas.material_support.shape == (1, 3, 3)
    assert atlas.material_support[0, 0, 0] > 0.0
    assert atlas.material_support[0, 1, 0] == 0.0
    assert np.all(atlas.material_probability[0, 1, 0] == 0.0)
    assert atlas.fallback_state_dense[0, 1, 0] == FALLBACK_UNOBSERVED


def test_host_gate_keeps_embedded_ground_cells_and_rejects_people() -> None:
    curb = fuse(observation("curb", np.array(((1.0, 0.0, 0.0),)), entity=2))
    posterior, supported = curb.host_compatible_material_probability(np.array((0, 1)))
    assert supported[0, 0, 0]
    assert posterior[0, 0, 0, MATERIAL_NAMES.index("asphalt_concrete")] == pytest.approx(1.0)

    person = fuse(observation("person", np.array(((1.0, 0.0, 0.0),)), entity=3))
    posterior, supported = person.host_compatible_material_probability(np.array((1, 1)))
    assert not supported.any()
    assert np.all(posterior == 0.0)


def test_one_large_triangle_emits_distinct_brick_and_glass_regions() -> None:
    atlas = fuse(
        observation("brick", np.array(((2 / 3, 1 / 6, 1 / 6),))),
        observation("glass", np.array(((1 / 6, 2 / 3, 1 / 6),)), source=1),
    )
    vertices = np.array(((0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (0.0, 3.0, 0.0), (9.0, 0.0, 0.0)))
    faces = np.array(((0, 1, 2), (1, 3, 2)))

    audit = to_surface_mesh(atlas, vertices, faces)
    host_posterior, host_supported = atlas.host_compatible_material_probability(np.array((1, 1)))

    assert set(audit.atlas_material) == {MATERIAL_NAMES.index("brick"), MATERIAL_NAMES.index("glass")}
    assert host_supported.sum() == 2
    assert set(host_posterior[host_supported].argmax(axis=1)) == {
        MATERIAL_NAMES.index("brick"),
        MATERIAL_NAMES.index("glass"),
    }
    assert np.all(audit.atlas_source_triangle == 0)
    assert audit.atlas_entity_probabilities.shape[0] == len(audit.atlas_faces)
    assert audit.atlas_material_probabilities.shape[0] == len(audit.atlas_faces)
    assert set(audit.as_arrays()) >= {"atlas_vertices", "atlas_faces", "atlas_entity", "atlas_material"}


def test_r8_audit_tessellation_emits_every_sparse_cell_with_exact_provenance() -> None:
    resolution = 8
    divisions = resolution - 1
    row_column = [(row, column) for row in range(resolution) for column in range(resolution - row)]
    barycentric = np.asarray(
        [(1.0 - (row + column) / divisions, column / divisions, row / divisions) for row, column in row_column]
    )
    atlas = fuse(observation("all-r8-cells", barycentric), resolution=resolution)
    vertices = np.array(((0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (0.0, 3.0, 0.0), (9.0, 0.0, 0.0)))
    faces = np.array(((0, 1, 2), (1, 3, 2)))

    audit = to_surface_mesh(atlas, vertices, faces)
    face_vertices = audit.atlas_vertices[audit.atlas_faces]
    centroids = face_vertices.mean(axis=1)
    centroid_barycentric = np.column_stack(
        (1.0 - centroids[:, 0] / 3.0 - centroids[:, 1] / 3.0, centroids[:, 0] / 3.0, centroids[:, 1] / 3.0)
    )
    selected_row, selected_column = _texel_indices(centroid_barycentric, resolution)
    area = 0.5 * np.linalg.norm(
        np.cross(face_vertices[:, 1] - face_vertices[:, 0], face_vertices[:, 2] - face_vertices[:, 0]),
        axis=1,
    )

    np.testing.assert_array_equal(np.unique(audit.atlas_sparse_cell), np.arange(atlas.cell_count))
    np.testing.assert_array_equal(selected_row, audit.atlas_texel_row)
    np.testing.assert_array_equal(selected_column, audit.atlas_texel_column)
    np.testing.assert_allclose(area.sum(), 4.5, rtol=1e-6)
    assert np.all(area > 0.0)
    emitted = set(zip(audit.atlas_texel_row.tolist(), audit.atlas_texel_column.tolist(), strict=True))
    assert emitted == set(row_column)
    assert {(row, column) for row, column in emitted if row + column == divisions} == {
        (row, divisions - row) for row in range(resolution)
    }


def test_zero_confidence_concept_observation_is_skipped_cleanly() -> None:
    zero_concept = observation("zero-concept", np.array(((1.0, 0.0, 0.0),)), source=1)
    zero_concept = replace(zero_concept, material_confidence=np.zeros(1, dtype=np.float32))
    live_prior = observation("live-prior", np.array(((0.0, 1.0, 0.0),)))

    atlas = fuse(zero_concept, live_prior)

    assert atlas.cell_count == 1
    assert (int(atlas.texel_row[0]), int(atlas.texel_column[0])) == (0, 2)
    assert atlas.observation_count.tolist() == [1]
    assert atlas.camera_count.tolist() == [1]
    assert atlas.source_mask.tolist() == [SOURCE_VISTAS_PRIOR]

    empty = fuse(zero_concept)
    assert empty.cell_count == 0
    assert empty.observed_triangle_count == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("entity_index", -1, "entity posterior index"),
        ("entity_index", len(ENTITY_NAMES), "entity posterior index"),
        ("joint_entity", -1, "joint posterior index"),
        ("joint_entity", len(ENTITY_NAMES), "joint posterior index"),
        ("joint_material", -1, "joint posterior index"),
        ("joint_material", len(MATERIAL_NAMES), "joint posterior index"),
        ("entity_label", -1, "entity_label"),
        ("entity_label", len(ENTITY_NAMES), "entity_label"),
        ("material_label", -1, "material_label"),
        ("material_label", len(MATERIAL_NAMES), "material_label"),
    ),
)
def test_atlas_rejects_negative_and_out_of_range_vocabulary_indices(
    field: str,
    value: int,
    message: str,
) -> None:
    atlas = fuse(observation("view", np.array(((1.0, 0.0, 0.0),))))
    corrupted = np.asarray(getattr(atlas, field), dtype=np.int64).copy()
    corrupted[0] = value

    with pytest.raises(ValueError, match=message):
        replace(atlas, **{field: corrupted})


def test_atlas_rejects_square_grid_cell_outside_canonical_triangle() -> None:
    atlas = fuse(observation("view", np.array(((1.0, 0.0, 0.0),))))

    with pytest.raises(ValueError, match="canonical triangle"):
        replace(
            atlas,
            texel_row=np.asarray([2], dtype=np.int64),
            texel_column=np.asarray([2], dtype=np.int64),
        )


def test_sparse_artifact_round_trips_with_manifest_and_mesh_gate(tmp_path: pathlib.Path) -> None:
    atlas = fuse(observation("view", np.array(((1.0, 0.0, 0.0),))))
    path = tmp_path / "atlas.npz"
    save_surface_atlas(
        atlas,
        path,
        metadata={
            "vocabularies": {"material_concept": list(CONCEPT_NAMES)},
            "cameras": [{"camera_id": "view"}],
        },
    )

    loaded = load_surface_atlas(path, expected_mesh_sha256=MESH_SHA)

    assert loaded.content_digest() == atlas.content_digest()
    np.testing.assert_allclose(loaded.material_probability, atlas.material_probability)
    with pytest.raises(ValueError, match="different support mesh"):
        load_surface_atlas(path, expected_mesh_sha256="b" * 64)


def test_cli_contract_exposes_every_numerical_build_choice() -> None:
    args = build_surface_atlas.arguments(["--site", "korenmarkt"])

    assert vars(args) == {
        "site": "korenmarkt",
        "crop_m": 250,
        "grid_height": 1536,
        "block_rows": 128,
        "atlas_resolution": 8,
        "max_residual_deg": 4.0,
        "max_sky_conflict": 0.5,
        "min_conflict_range_m": 2.0,
        "concepts": pathlib.Path("config/semantic_concepts.json").resolve(),
        "out": build_surface_atlas.DEFAULT_OUT,
        "semantics_dirname": "semantics",
    }


def test_atlas_catalogue_record_carries_canonical_review_identity() -> None:
    catalogue = build_surface_atlas.paths.config_dir() / "semantic_concepts.json"

    record = build_surface_atlas._concept_catalogue_record(catalogue)
    build_surface_atlas._validate_catalogue_identity(
        {"concept_vocabulary": {"catalogue_semantic_sha256": record["catalogue_semantic_sha256"]}},
        selected=record,
        camera_id="camera-a",
    )

    assert record["path"] == str(catalogue)
    assert record["sha256"] == hashlib.sha256(catalogue.read_bytes()).hexdigest()
    assert record["matches_reviewed_production_catalogue"] is True
    assert record["catalogue_semantic_sha256"] == record["required_production_catalogue_semantic_sha256"]


def test_atlas_refuses_matching_labels_and_count_from_another_catalogue() -> None:
    catalogue = build_surface_atlas.paths.config_dir() / "semantic_concepts.json"
    selected = build_surface_atlas._concept_catalogue_record(catalogue)
    concepts = build_surface_atlas.ConceptCatalog.load(catalogue)
    metadata = {
        "concept_id2label": {str(index): label for index, label in concepts.id2label().items()},
        "concept_vocabulary": {
            "id_count": len(concepts.id2label()),
            "prompt_count": len(concepts.concepts),
            "catalogue_semantic_sha256": "f" * 64,
        },
    }

    with pytest.raises(ValueError, match="produced with semantic concept catalogue"):
        build_surface_atlas._validate_catalogue_identity(
            metadata,
            selected=selected,
            camera_id="camera-b",
        )


def test_versioned_semantic_evidence_is_selected_without_a_symlink(tmp_path: pathlib.Path) -> None:
    capture = tmp_path / "camera"
    legacy = capture / "semantics"
    versioned = capture / "semantics_sam3_3c879f3_61id"
    legacy.mkdir(parents=True)
    versioned.mkdir()
    (legacy / "semantics.json").write_text('{"version": "old"}', encoding="utf-8")
    (versioned / "semantics.json").write_text('{"version": "pinned"}', encoding="utf-8")

    selected = build_surface_atlas._semantics_directory(capture, "semantics_sam3_3c879f3_61id")

    assert selected == versioned
    assert json.loads((selected / "semantics.json").read_text(encoding="utf-8")) == {"version": "pinned"}
    assert not selected.is_symlink()
    with pytest.raises(ValueError, match="relative path"):
        build_surface_atlas._semantics_directory(capture, "../elsewhere")


def test_camera_provenance_hashes_every_present_input_and_names_models(tmp_path: pathlib.Path) -> None:
    pose = tmp_path / "pose.json"
    semantics = tmp_path / "semantics.npz"
    metadata_path = tmp_path / "semantics.json"
    panorama = tmp_path / "panorama.png"
    pose.write_text('{"heading_deg": 90}\n', encoding="utf-8")
    np.savez_compressed(
        semantics,
        entity=np.zeros((2, 4), dtype=np.uint8),
        vegetation_form=np.ones((2, 4), dtype=np.uint8),
        vegetation_subtype=np.ones((2, 4), dtype=np.uint8),
        vegetation_confidence=np.ones((2, 4), dtype=np.float32),
    )
    metadata = {
        "backend": "hybrid",
        "model": "facebook/mask2former-mapillary-vistas",
        "checkpoint": "entity-revision",
        "concept_backend": {"model": "facebook/sam3", "threshold": 0.35},
        "concept_cache_key": "concept-cache",
        "vegetation_backend": "vegetation-classifier",
        "vegetation_model": "vegetation-model",
        "vegetation_checkpoint": "vegetation-revision",
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    panorama.write_bytes(b"lossless panorama fixture")

    provenance = build_surface_atlas._camera_provenance(
        pose_path=pose,
        semantics_path=semantics,
        metadata_path=metadata_path,
        panorama_path=panorama,
        metadata=metadata,
    )

    for name, path in {
        "pose_json": pose,
        "semantic_npz": semantics,
        "semantic_json": metadata_path,
        "panorama": panorama,
    }.items():
        assert provenance["input_files"][name] == {
            "present": True,
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    assert provenance["semantic_product"] == {
        "backend": "hybrid",
        "entity_model": {
            "model": "facebook/mask2former-mapillary-vistas",
            "checkpoint": "entity-revision",
        },
        "concept_model": {
            "model": "facebook/sam3",
            "threshold": 0.35,
            "immutable_revision": {
                "status": "unresolved",
                "kind": None,
                "value": None,
                "source_field": None,
                "reported_mutable_or_unverifiable_values": [],
                "note": (
                    "The semantic artifact does not record an immutable SAM3 weight digest or commit. "
                    "The model name and cache key identify settings, not exact weights."
                ),
            },
        },
        "concept_cache_key": "concept-cache",
        "vegetation": {
            "status": "present",
            "rasters": {
                "vegetation_form": True,
                "vegetation_subtype": True,
                "vegetation_confidence": True,
            },
            "missing_rasters": [],
            "backend": "vegetation-classifier",
            "model": "vegetation-model",
            "checkpoint": "vegetation-revision",
            "note": "Vegetation form, subtype, and confidence rasters are present.",
        },
    }


def test_camera_provenance_records_an_immutable_sam3_commit_when_present(tmp_path: pathlib.Path) -> None:
    pose = tmp_path / "pose.json"
    semantics = tmp_path / "semantics.npz"
    metadata_path = tmp_path / "semantics.json"
    pose.write_text("{}\n", encoding="utf-8")
    np.savez_compressed(semantics, entity=np.zeros((1, 1), dtype=np.uint8))
    metadata_path.write_text("{}\n", encoding="utf-8")
    revision = "1234567890abcdef1234567890abcdef12345678"
    metadata = {
        "concept_backend": {
            "model": "facebook/sam3",
            "revision": revision,
        }
    }

    provenance = build_surface_atlas._camera_provenance(
        pose_path=pose,
        semantics_path=semantics,
        metadata_path=metadata_path,
        panorama_path=None,
        metadata=metadata,
    )

    assert provenance["semantic_product"]["concept_model"]["immutable_revision"] == {
        "status": "resolved",
        "kind": "git_commit",
        "value": revision,
        "source_field": "concept_backend.revision",
    }


def test_camera_provenance_does_not_call_a_mutable_sam3_tag_immutable(tmp_path: pathlib.Path) -> None:
    pose = tmp_path / "pose.json"
    semantics = tmp_path / "semantics.npz"
    metadata_path = tmp_path / "semantics.json"
    pose.write_text("{}\n", encoding="utf-8")
    np.savez_compressed(semantics, entity=np.zeros((1, 1), dtype=np.uint8))
    metadata_path.write_text("{}\n", encoding="utf-8")
    metadata = {"concept_backend": {"model": "facebook/sam3", "revision": "main"}}

    provenance = build_surface_atlas._camera_provenance(
        pose_path=pose,
        semantics_path=semantics,
        metadata_path=metadata_path,
        panorama_path=None,
        metadata=metadata,
    )

    revision = provenance["semantic_product"]["concept_model"]["immutable_revision"]
    assert revision["status"] == "unresolved"
    assert revision["value"] is None
    assert revision["reported_mutable_or_unverifiable_values"] == [
        {"field": "concept_backend.revision", "value": "main"}
    ]


def test_absent_vegetation_evidence_and_panorama_are_explicit(tmp_path: pathlib.Path) -> None:
    pose = tmp_path / "pose.json"
    semantics = tmp_path / "semantics.npz"
    metadata_path = tmp_path / "semantics.json"
    pose.write_text("{}\n", encoding="utf-8")
    np.savez_compressed(semantics, entity=np.zeros((2, 4), dtype=np.uint8))
    metadata_path.write_text("{}\n", encoding="utf-8")

    provenance = build_surface_atlas._camera_provenance(
        pose_path=pose,
        semantics_path=semantics,
        metadata_path=metadata_path,
        panorama_path=None,
        metadata={},
    )
    vegetation = provenance["semantic_product"]["vegetation"]
    summary = build_surface_atlas._vegetation_evidence_summary([{"semantic_product": {"vegetation": vegetation}}])

    assert provenance["input_files"]["panorama"] == {
        "present": False,
        "path": None,
        "sha256": None,
    }
    assert vegetation["status"] == "absent"
    assert vegetation["missing_rasters"] == list(build_surface_atlas.VEGETATION_RASTERS)
    assert "not classifications" in vegetation["note"]
    assert summary == {
        "status": "absent",
        "camera_count": 1,
        "complete_camera_count": 0,
        "partial_camera_count": 0,
        "absent_camera_count": 1,
        "note": (
            "Only explicit vegetation form, subtype, and confidence rasters count as vegetation classification "
            "evidence. Catalogue labels alone do not."
        ),
    }

from __future__ import annotations

import dataclasses
import pathlib

import numpy as np
import pytest

from semantic_twin.materials import VegetationBinding, bind_walk_vegetation
from semantic_twin.scene.site_semantics import _load_site_semantic_rasters, _site_vegetation_arrays
from semantic_twin.vision.layers import layer_rules, view_layers
from semantic_twin.vision.panorama import vegetation_from_concepts
from semantic_twin.vision.prompted import MODEL, cache_key
from semantic_twin.vision.vocabulary import ConceptCatalog
from semantic_twin.vision.walk_evidence import _walk_vegetation_arrays

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "config" / "semantic_concepts.json"
EXPECTED_PROMPTS = (
    "brick facade",
    "painted brick wall",
    "ashlar stone facade",
    "rubble stone masonry wall",
    "plaster facade",
    "exposed concrete wall",
    "marble cladding",
    "ceramic tile facade",
    "glass curtain wall",
    "glass window",
    "shop window",
    "metal cladding panel",
    "corrugated metal sheet",
    "metal roller shutter",
    "timber cladding",
    "half-timbered facade",
    "plywood hoarding",
    "oriented strand board panel",
    "open archway",
    "roof tile",
    "slate roof",
    "metal roof",
    "glass roof",
    "solar panel",
    "scaffolding",
    "asphalt road",
    "cobblestone paving",
    "brick paving",
    "paving slab",
    "gravel",
    "grass lawn",
    "bare soil",
    "painted road marking",
    "tram rail",
    "water",
    "foliage",
    "shrub foliage",
    "tree canopy",
    "forest canopy",
    "wooden door",
    "metal door",
    "concrete surface",
    "metal surface",
    "wooden surface",
    "tree trunk",
    "bollard",
    "outdoor table",
    "outdoor chair",
    "parasol",
    "awning",
    "planter",
    "flower pot",
    "parking meter",
    "statue",
    "kiosk",
    "temporary barrier",
    "handrail",
    "railing",
    "drainpipe",
    "overhead cable",
)


def _catalog() -> ConceptCatalog:
    return ConceptCatalog.load(CATALOG)


def test_the_vegetation_binding_is_part_of_the_public_materials_api() -> None:
    assert VegetationBinding.__module__ == "semantic_twin.materials.evidence"
    assert bind_walk_vegetation.__module__ == "semantic_twin.materials.evidence"


def test_vegetation_prompt_order_and_cache_identity_are_pinned() -> None:
    catalog = _catalog()

    assert catalog.prompts == EXPECTED_PROMPTS
    assert cache_key(model=MODEL, resolution=1008, threshold=0.35, view_size=1536, catalog=catalog) == (
        "f9db3e260983ebc9"
    )


def test_grass_and_woody_foliage_survive_the_independent_panorama_layer() -> None:
    catalog = _catalog()
    concept_ids = catalog.concept_ids()
    masks = np.asarray([[[True, False, False]], [[False, True, False]]])
    layers = view_layers(
        masks,
        np.asarray(["grass lawn", "foliage"]),
        np.asarray(["surface", "surface"]),
        np.asarray([0.8, 0.9], dtype=np.float32),
        concept_ids,
        layer_rules(catalog),
    )

    concept, confidence = layers["vegetation"]
    form, subtype, resolved_confidence = vegetation_from_concepts(concept, confidence, catalog)

    assert [catalog.vegetation_forms[index] for index in form[0]] == [
        "ground_vegetation",
        "woody_canopy",
        "unresolved",
    ]
    assert [catalog.vegetation_subtypes[index] for index in subtype[0]] == [
        "grass",
        "unresolved",
        "unresolved",
    ]
    assert resolved_confidence[0, 2] == 0.0


def test_grass_shrub_tree_and_forest_keep_distinct_subtypes() -> None:
    catalog = _catalog()
    prompts = np.asarray(["grass lawn", "shrub foliage", "tree canopy", "forest canopy"])
    masks = np.eye(4, dtype=bool)[:, None, :]
    layers = view_layers(
        masks,
        prompts,
        np.asarray(["surface"] * 4),
        np.asarray([0.9] * 4, dtype=np.float32),
        catalog.concept_ids(),
        layer_rules(catalog),
    )

    concept, confidence = layers["vegetation"]
    form, subtype, _resolved_confidence = vegetation_from_concepts(concept, confidence, catalog)

    assert [catalog.vegetation_forms[index] for index in form[0]] == [
        "ground_vegetation",
        "woody_canopy",
        "woody_canopy",
        "woody_canopy",
    ]
    assert [catalog.vegetation_subtypes[index] for index in subtype[0]] == [
        "grass",
        "shrub",
        "tree",
        "forest",
    ]


def test_dense_only_vegetation_stays_unresolved() -> None:
    catalog = _catalog()
    form, subtype, confidence = vegetation_from_concepts(
        np.zeros((2, 3), dtype=np.uint16),
        np.ones((2, 3), dtype=np.float16),
        catalog,
    )

    assert not form.any()
    assert not subtype.any()
    assert not confidence.any()


def test_tree_trunk_stays_wood_and_never_routes_to_canopy() -> None:
    catalog = _catalog()
    trunk = catalog.by_prompt["tree trunk"]
    form_table, subtype_table = catalog.vegetation_tables()
    trunk_id = catalog.concept_ids()[trunk.prompt]

    assert max(trunk.material, key=trunk.material.get) == "wood"
    assert form_table[trunk_id] == 0
    assert subtype_table[trunk_id] == 0
    vegetation_rule = {rule.name: rule for rule in layer_rules(catalog)}["vegetation"]
    assert trunk.prompt not in vegetation_rule.labels


def test_foliage_never_routes_to_the_wood_interface() -> None:
    catalog = _catalog()
    for prompt in ("foliage", "shrub foliage", "tree canopy", "forest canopy"):
        concept = catalog.by_prompt[prompt]
        assert "wood" not in concept.material
        assert max(concept.material, key=concept.material.get) == "vegetation_effective"
    vistas = catalog.bridges["mask2former_mapillary_vistas"]
    assert "wood" not in vistas.material_prior["Vegetation"]


@pytest.mark.parametrize("subtype", ["shrub", "tree", "forest"])
def test_the_catalog_can_carry_diagnostic_woody_subtypes(subtype: str) -> None:
    catalog = _catalog()
    foliage = catalog.by_prompt["foliage"]
    custom = dataclasses.replace(foliage, vegetation_subtype=subtype)
    concepts = [custom if concept.prompt == foliage.prompt else concept for concept in catalog.concepts]
    loaded = ConceptCatalog(
        catalog.taxonomy,
        concepts,
        material_grounding=catalog.material_grounding,
        bridges=catalog.bridges,
        grounding_note=catalog.grounding_note,
    )
    form_table, subtype_table = loaded.vegetation_tables()
    foliage_id = loaded.concept_ids()["foliage"]

    assert loaded.vegetation_forms[form_table[foliage_id]] == "woody_canopy"
    assert loaded.vegetation_subtypes[subtype_table[foliage_id]] == subtype


def _write_walk(path: pathlib.Path, order: list[int]) -> None:
    image_ids = np.asarray(["cam_b", "cam_a"])[order]
    form = np.asarray([[1, 2, 0], [2, 2, 0]], dtype=np.uint8)[order]
    subtype = np.asarray([[1, 3, 0], [4, 2, 0]], dtype=np.uint8)[order]
    rays = np.asarray([[8, 3, 0], [2, 7, 0]], dtype=np.int32)[order]
    np.savez(
        path,
        image_ids=image_ids,
        modal_vegetation_form=form,
        modal_vegetation_subtype=subtype,
        vegetation_rays=rays,
        vegetation_form_names=np.asarray(["unresolved", "ground_vegetation", "woody_canopy"]),
        vegetation_subtype_names=np.asarray(["unresolved", "grass", "shrub", "tree", "forest"]),
    )


def test_walk_fusion_keeps_grass_and_woody_canopy_and_is_order_invariant(tmp_path) -> None:
    first = tmp_path / "first.npz"
    reversed_rows = tmp_path / "reversed.npz"
    _write_walk(first, [0, 1])
    _write_walk(reversed_rows, [1, 0])
    areas = np.asarray([1.0, 2.0, 3.0])

    a = bind_walk_vegetation(areas, walk_npz=first)
    b = bind_walk_vegetation(areas, walk_npz=reversed_rows)

    assert [a.form_names[index] for index in a.face_form] == [
        "ground_vegetation",
        "woody_canopy",
        "unresolved",
    ]
    assert a.subtype_names[a.face_subtype[0]] == "grass"
    assert np.array_equal(a.face_form, b.face_form)
    assert np.array_equal(a.face_subtype, b.face_subtype)
    assert np.array_equal(a.face_weight, b.face_weight)
    assert a.covered_fraction_by_area == pytest.approx(3.0 / 6.0)


def test_an_old_walk_file_loads_as_exactly_unresolved(tmp_path) -> None:
    old = tmp_path / "legacy_walk.npz"
    np.savez(
        old,
        modal_class=np.asarray([[1, 2, 3]], dtype=np.int16),
        clean_rays=np.asarray([[9, 8, 7]], dtype=np.int32),
    )

    binding = bind_walk_vegetation(np.asarray([1.0, 2.0, 3.0]), walk_npz=old)

    assert not binding.resolved.any()
    assert not binding.face_weight.any()
    assert binding.covered_fraction_by_face == 0.0
    assert binding.covered_fraction_by_area == 0.0
    assert binding.provenance["dense_vegetation"] == "unresolved"


def test_a_partly_written_vegetation_schema_is_refused(tmp_path) -> None:
    partial = tmp_path / "partial.npz"
    np.savez(
        partial,
        modal_vegetation_form=np.asarray([[1, 0]], dtype=np.uint8),
        vegetation_rays=np.asarray([[4, 0]], dtype=np.int32),
    )

    with pytest.raises(ValueError, match="schema is incomplete.*modal_vegetation_subtype"):
        bind_walk_vegetation(np.ones(2), walk_npz=partial)


@pytest.mark.parametrize("image_ids", [np.asarray(["one"]), np.asarray(["one", "two", "three"])])
def test_walk_vegetation_requires_one_image_id_per_station(tmp_path, image_ids: np.ndarray) -> None:
    path = tmp_path / f"ids_{len(image_ids)}.npz"
    np.savez(
        path,
        image_ids=image_ids,
        modal_vegetation_form=np.asarray([[1, 0], [2, 0]], dtype=np.uint8),
        modal_vegetation_subtype=np.asarray([[1, 0], [3, 0]], dtype=np.uint8),
        vegetation_rays=np.asarray([[4, 0], [5, 0]], dtype=np.int32),
    )

    with pytest.raises(ValueError, match=f"2 station rows but {len(image_ids)} image_ids"):
        bind_walk_vegetation(np.ones(2), walk_npz=path)


def _station_vegetation(form: list[int], subtype: list[int], rays: list[int]) -> dict[str, np.ndarray]:
    form_array = np.asarray(form, dtype=np.uint8)
    subtype_array = np.asarray(subtype, dtype=np.uint8)
    rays_array = np.asarray(rays, dtype=np.int32)
    form_counts = np.zeros((len(form), 3), dtype=np.int32)
    subtype_counts = np.zeros((len(form), 5), dtype=np.int32)
    face = np.arange(len(form))
    np.add.at(form_counts, (face[form_array > 0], form_array[form_array > 0]), rays_array[form_array > 0])
    np.add.at(
        subtype_counts,
        (face[subtype_array > 0], subtype_array[subtype_array > 0]),
        rays_array[subtype_array > 0],
    )
    return {
        "modal_vegetation_form": form_array,
        "modal_vegetation_subtype": subtype_array,
        "vegetation_rays": rays_array,
        "vegetation_form_counts": form_counts,
        "vegetation_subtype_counts": subtype_counts,
    }


def test_walk_writer_emits_the_complete_vegetation_schema() -> None:
    results = [
        _station_vegetation([1, 0], [1, 0], [4, 0]),
        _station_vegetation([2, 0], [3, 0], [5, 0]),
    ]
    arrays, report = _walk_vegetation_arrays(
        results,
        ["unresolved", "ground_vegetation", "woody_canopy"],
        ["unresolved", "grass", "shrub", "tree", "forest"],
    )

    assert set(arrays) == {
        "modal_vegetation_form",
        "modal_vegetation_subtype",
        "vegetation_rays",
        "vegetation_form_counts",
        "vegetation_subtype_counts",
        "vegetation_form_names",
        "vegetation_subtype_names",
    }
    assert report is not None
    assert report["faces_with_resolved_form"] == 1


def test_walk_writer_refuses_a_mixed_old_and_new_station_set() -> None:
    arrays, report = _walk_vegetation_arrays(
        [_station_vegetation([1], [1], [4]), {"modal_class": np.asarray([7])}],
        ["unresolved", "ground_vegetation", "woody_canopy"],
        ["unresolved", "grass", "shrub", "tree", "forest"],
    )

    assert arrays == {}
    assert report == {"status": "mixed semantic files, refusing a vegetation axis only some stations carry"}


def test_site_writer_emits_the_companion_axis_and_refuses_mixed_files() -> None:
    names = ["unresolved", "ground_vegetation", "woody_canopy"]
    subtypes = ["unresolved", "grass", "shrub", "tree", "forest"]
    new = _station_vegetation([1, 2], [1, 3], [4, 5])

    arrays, report = _site_vegetation_arrays([new], names, subtypes)
    assert set(arrays) == {
        "modal_vegetation_form",
        "modal_vegetation_subtype",
        "vegetation_rays",
        "vegetation_form_names",
        "vegetation_subtype_names",
    }
    assert report == {
        "form_vocabulary": names,
        "diagnostic_subtype_vocabulary": subtypes,
        "dense_vegetation": "unresolved and contributes no form vote",
    }

    arrays, report = _site_vegetation_arrays([new, {"modal_class": np.asarray([7, 7])}], names, subtypes)
    assert arrays == {}
    assert report == {"status": "mixed semantic files, refusing a vegetation axis only some stations carry"}


def test_site_loader_preserves_a_fully_legacy_artifact_pair(tmp_path) -> None:
    path = tmp_path / "legacy.npz"
    entity = np.arange(8, dtype=np.uint8).reshape(2, 4)
    np.savez(path, entity=entity)

    labels, form, subtype = _load_site_semantic_rasters(path, 2, 4, 0, 0, "legacy_station")

    np.testing.assert_array_equal(labels, entity)
    assert form is None
    assert subtype is None


def test_site_loader_refuses_new_metadata_paired_with_an_old_npz(tmp_path) -> None:
    path = tmp_path / "old_arrays.npz"
    np.savez(path, entity=np.zeros((2, 4), dtype=np.uint8))

    with pytest.raises(ValueError, match="metadata declares vegetation but its NPZ does not contain the arrays"):
        _load_site_semantic_rasters(path, 2, 4, 3, 5, "mixed_station")


def test_site_loader_refuses_new_npz_arrays_paired_with_legacy_metadata(tmp_path) -> None:
    path = tmp_path / "new_arrays.npz"
    shape = (2, 4)
    np.savez(
        path,
        entity=np.zeros(shape, dtype=np.uint8),
        vegetation_form=np.ones(shape, dtype=np.uint8),
        vegetation_subtype=np.ones(shape, dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="metadata does not declare vegetation but its NPZ contains the arrays"):
        _load_site_semantic_rasters(path, 2, 4, 0, 0, "mixed_station")


def test_site_loader_refuses_a_partial_npz_axis(tmp_path) -> None:
    path = tmp_path / "partial_arrays.npz"
    shape = (2, 4)
    np.savez(
        path,
        entity=np.zeros(shape, dtype=np.uint8),
        vegetation_form=np.ones(shape, dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="NPZ carries only half of the vegetation axis"):
        _load_site_semantic_rasters(path, 2, 4, 3, 5, "partial_station")


def test_site_loader_accepts_a_complete_matching_vegetation_pair(tmp_path) -> None:
    path = tmp_path / "complete.npz"
    entity = np.arange(8, dtype=np.uint8).reshape(2, 4)
    form = np.asarray([[1, 1, 0, 2], [0, 2, 2, 0]], dtype=np.uint8)
    subtype = np.asarray([[1, 1, 0, 3], [0, 4, 3, 0]], dtype=np.uint8)
    np.savez(path, entity=entity, vegetation_form=form, vegetation_subtype=subtype)

    labels, loaded_form, loaded_subtype = _load_site_semantic_rasters(path, 2, 4, 3, 5, "new_station")

    np.testing.assert_array_equal(labels, entity)
    np.testing.assert_array_equal(loaded_form, form)
    np.testing.assert_array_equal(loaded_subtype, subtype)

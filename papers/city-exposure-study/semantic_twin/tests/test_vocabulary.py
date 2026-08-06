from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest
from PIL import Image

from semantic_twin.vision.vocabulary import ConceptCatalog, gate_prompts
from semantic_twin.vision.layers import layer_rules, render_layer_diagnostics, view_layers

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "config" / "semantic_concepts.json"
BRIDGE = "mask2former_mapillary_vistas"


def catalog() -> ConceptCatalog:
    return ConceptCatalog.load(CATALOG)


def test_catalog_is_valid_and_multiaxial() -> None:
    concept = catalog().by_prompt["glass window"]
    assert concept.kind == "surface"
    assert np.isclose(catalog().categorical_probability(concept, "entities").sum(), 1.0)
    assert np.isclose(catalog().categorical_probability(concept, "materials").sum(), 1.0)
    attributes = catalog().attribute_probability(concept)
    assert attributes[catalog().taxonomy["attributes"].index("transparent")] > 0.9
    assert attributes[catalog().taxonomy["attributes"].index("reflective")] > 0.8


def test_every_material_label_declares_where_its_dielectric_model_comes_from() -> None:
    loaded = catalog()
    assert set(loaded.material_grounding) == set(loaded.taxonomy["materials"])
    for binding in loaded.material_grounding.values():
        if binding.bound_to_itu_p2040:
            assert binding.library == "itu_p2040_4"
        else:
            assert binding.note or binding.status == "no_model"


def test_the_itu_audit_names_the_rows_no_prompt_can_reach() -> None:
    rows = [record["name"] for record in json.loads((ROOT / "config" / "itu_p2040_4.json").read_text())["materials"]]
    coverage = catalog().library_coverage(rows)

    assert set(coverage.reachable) | set(coverage.unreachable) == set(rows)
    assert len(coverage.reachable) >= 11
    # Every row that stays out of reach is an interior floor or ceiling finish.
    # Street-level imagery of an outdoor square cannot see any of them, and that
    # is a property of the library rather than a defect in the prompt set.
    assert set(coverage.unreachable) == {"ceiling_board", "floorboard", "vinyl_tile", "carpet_tile"}
    # Materials a prompt can name that no P.2040 row covers must stay visible.
    assert "ceramic" in coverage.unbound_materials
    assert "vegetation_effective" in coverage.unbound_materials


def test_facade_materials_are_separable_and_carry_their_ambiguity() -> None:
    loaded = catalog()
    facades = [
        concept for concept in loaded.concepts if concept.entity.get("facade", 0.0) > 0.0 and concept.kind == "surface"
    ]
    dominant = {max(concept.material, key=concept.material.get) for concept in facades}
    assert {"brick", "marble", "concrete", "glass", "metal", "wood", "plasterboard"} <= dominant

    curtain_wall = loaded.by_prompt["glass curtain wall"]
    # A metallised coating is invisible in a street photograph and dominates the
    # RF response, so it has to be a prior on an attribute, never a detection.
    assert curtain_wall.attributes["metallised"] > 0.5
    assert "coating" in curtain_wall.caveat

    # Ashlar and rubble stone share a dielectric prior and split on roughness.
    ashlar, rubble = loaded.by_prompt["ashlar stone facade"], loaded.by_prompt["rubble stone masonry wall"]
    assert max(ashlar.material, key=ashlar.material.get) == max(rubble.material, key=rubble.material.get)
    assert rubble.attributes["rough"] > 0.9 > ashlar.attributes["rough"]


def test_the_gate_skips_facade_prompts_on_a_view_with_no_building() -> None:
    loaded = catalog()
    bridge = loaded.bridges[BRIDGE]

    sky_only = gate_prompts(loaded, bridge, frozenset({"Sky"}), view="zenith")
    street = gate_prompts(loaded, bridge, frozenset({"Building", "Sky", "Pedestrian Area"}), view="h+00_000")

    assert "brick facade" not in sky_only.prompts
    assert "brick facade" in street.prompts
    assert "cobblestone paving" in street.prompts
    assert "cobblestone paving" not in sky_only.prompts
    # Entity-free material fallbacks are never gated away.
    for fallback in ("metal surface", "wooden surface", "concrete surface"):
        assert fallback in sky_only.prompts
        assert fallback in sky_only.ungated
    assert len(sky_only.prompts) < len(street.prompts) < len(loaded.concepts) + 1
    assert set(sky_only.prompts) | set(sky_only.skipped) == set(loaded.prompts)


@pytest.mark.local_data
def test_the_bridge_names_exactly_the_classes_the_checkpoint_emits() -> None:
    # Pinned from a real run's manifest. A typo in a Vistas class name silently
    # collapses that class's prior onto unknown and makes every concept routed
    # through it inadmissible, with nothing raising anywhere.
    emitted = set(
        json.loads((ROOT / "data/panoramas/korenmarkt/semantics/semantics.json").read_text())[
            "entity_id2label"
        ].values()
    )
    bridge = catalog().bridges[BRIDGE]

    assert set(bridge.material_prior) == emitted
    routed = {label for labels in bridge.entity_support.values() for label in labels}
    assert routed <= emitted


def test_a_trace_of_metal_in_a_prior_is_not_permission_to_claim_metal() -> None:
    bridge = catalog().bridges[BRIDGE]
    compatible = bridge.material_compatible("metal")

    # Building carries 0.03 metal for the occasional clad frontage. Reading that
    # as admissibility let a vague metal prompt overwrite a facade prior with
    # 0.96 metal, which at 28 GHz is the most consequential error available.
    assert bridge.material_prior["Building"]["metal"] > 0.0
    assert "Building" not in compatible
    assert {"Pole", "Bike Rack", "Fire Hydrant", "Guard Rail"} <= compatible


def test_the_bridge_binds_every_dense_class_to_a_material_spread() -> None:
    bridge = catalog().bridges[BRIDGE]
    building = bridge.material_prior["Building"]

    assert np.isclose(sum(building.values()), 1.0)
    # One Vistas class covers five wall materials, so its prior must stay flat.
    # If any single material dominated it, the concept backend would have
    # nothing left to sharpen.
    assert max(building.values()) < 0.4
    assert {"brick", "plasterboard", "concrete", "marble", "glass"} <= set(building)
    assert bridge.material_prior["Sky"] == {"air": 1.0}


def test_a_material_only_prompt_loses_to_a_prompt_that_names_an_entity() -> None:
    loaded = catalog()
    bonus = {rule.name: rule.priority_bonus for rule in layer_rules(loaded)}["material"]

    # The vague fallbacks are the weakest evidence in the catalogue and must
    # rank below anything that commits to an entity.
    assert bonus["metal surface"] < 0.0
    assert bonus["cobblestone paving"] > bonus["metal surface"]
    assert bonus["glass window"] > bonus["brick facade"] >= bonus["metal surface"]


def test_a_demoted_prompt_can_still_claim_a_pixel_nothing_else_wants() -> None:
    loaded = catalog()
    concept_ids = {"unlabelled": 0}
    concept_ids.update({concept.prompt: index + 1 for index, concept in enumerate(loaded.concepts)})
    masks = np.asarray([[[True, True]], [[True, False]]])

    layers = view_layers(
        masks,
        np.asarray(["metal surface", "cobblestone paving"]),
        np.asarray(["surface", "surface"]),
        np.asarray([0.40, 0.40], dtype=np.float32),
        concept_ids,
        layer_rules(loaded),
    )

    # Left pixel: the entity-bearing concept wins despite an equal raw score.
    # Right pixel: only the demoted concept covers it, and a negative priority
    # must not stop it claiming an otherwise empty pixel.
    assert layers["material"][0].tolist() == [[concept_ids["cobblestone paving"], concept_ids["metal surface"]]]


def test_layered_fusion_keeps_detail_and_clutter_out_of_the_support_winner() -> None:
    loaded = catalog()
    concept_ids = {"unlabelled": 0}
    concept_ids.update({concept.prompt: index + 1 for index, concept in enumerate(loaded.concepts)})
    masks = np.asarray(
        [
            [[True, False]],  # broad static support
            [[True, False]],  # detail overlay on the same pixel
            [[False, True]],  # dynamic clutter on a second pixel
        ]
    )
    layers = view_layers(
        masks,
        np.asarray(["brick facade", "glass window", "temporary barrier"]),
        np.asarray(["surface", "surface", "object"]),
        np.asarray([0.95, 0.40, 0.80], dtype=np.float32),
        concept_ids,
        layer_rules(loaded),
    )

    assert layers["support"][0].tolist() == [[concept_ids["brick facade"], 0]]
    assert layers["material"][0].tolist() == [[concept_ids["glass window"], 0]]
    assert layers["clutter"][0].tolist() == [[0, concept_ids["temporary barrier"]]]
    assert layers["dynamic_clutter"][0].tolist() == [[0, concept_ids["temporary barrier"]]]


def test_view_layers_rejects_a_prediction_from_another_catalogue() -> None:
    loaded = catalog()
    concept_ids = {"unlabelled": 0, "brick facade": 1}
    with pytest.raises(ValueError, match="missing from catalog"):
        view_layers(
            np.asarray([[[True]]]),
            np.asarray(["a concept that was retired"]),
            np.asarray(["surface"]),
            np.asarray([0.9], dtype=np.float32),
            concept_ids,
            layer_rules(loaded),
        )


def test_layered_diagnostic_writes_separate_alpha_and_overlay_files(tmp_path: pathlib.Path) -> None:
    labels = {0: "unlabelled", 1: "brick facade", 2: "glass window", 3: "temporary barrier"}
    zero = np.zeros((2, 4), dtype=np.float16)
    layers = {
        "support": (np.asarray([[1, 1, 0, 0], [1, 1, 0, 0]], dtype=np.uint16), zero),
        "material": (np.asarray([[2, 0, 0, 0], [0, 0, 0, 0]], dtype=np.uint16), zero),
        "clutter": (np.asarray([[0, 0, 3, 0], [0, 0, 0, 0]], dtype=np.uint16), zero),
        "dynamic_clutter": (np.asarray([[0, 0, 3, 0], [0, 0, 0, 0]], dtype=np.uint16), zero),
    }
    source = tmp_path / "source.jpg"
    Image.new("RGB", (4, 2), (10, 20, 30)).save(source)

    render_layer_diagnostics(layers, labels, tmp_path, source)

    assert (tmp_path / "panorama_support.png").exists()
    assert (tmp_path / "panorama_material.png.rgba.png").exists()
    assert (tmp_path / "panorama_dynamic_clutter.png").exists()
    assert (tmp_path / "panorama_layered_overlay.png").exists()

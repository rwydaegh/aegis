from __future__ import annotations

import pathlib

import numpy as np
from PIL import Image

from semantic_twin.concepts import ConceptCatalog
from semantic_twin.fuse_concepts import layer_rules, render_layer_diagnostics, view_layers

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_catalog_is_valid_and_multiaxial() -> None:
    catalog = ConceptCatalog.load(ROOT / "config" / "semantic_concepts.json")
    concept = catalog.by_prompt["glass window"]
    assert concept.kind == "surface"
    assert np.isclose(catalog.categorical_probability(concept, "entities").sum(), 1.0)
    assert np.isclose(catalog.categorical_probability(concept, "materials").sum(), 1.0)
    attributes = catalog.attribute_probability(concept)
    assert attributes[catalog.taxonomy["attributes"].index("transparent")] > 0.9
    assert attributes[catalog.taxonomy["attributes"].index("reflective")] > 0.8


def test_layered_fusion_keeps_window_and_person_out_of_facade_winner() -> None:
    catalog = ConceptCatalog.load(ROOT / "config" / "semantic_concepts.json")
    concept_ids = {"unlabelled": 0}
    concept_ids.update({concept.prompt: index + 1 for index, concept in enumerate(catalog.concepts)})
    masks = np.asarray(
        [
            [[True, False]],  # broad static support
            [[True, False]],  # detail overlay on the same pixel
            [[False, True]],  # dynamic clutter on a second pixel
        ]
    )
    layers = view_layers(
        masks,
        np.asarray(["brick facade", "glass window", "person"]),
        np.asarray(["surface", "surface", "object"]),
        np.asarray([0.95, 0.40, 0.80], dtype=np.float32),
        concept_ids,
        layer_rules(catalog),
    )

    assert layers["support"][0].tolist() == [[concept_ids["brick facade"], 0]]
    assert layers["material"][0].tolist() == [[concept_ids["glass window"], 0]]
    assert layers["clutter"][0].tolist() == [[0, concept_ids["person"]]]
    assert layers["dynamic_clutter"][0].tolist() == [[0, concept_ids["person"]]]


def test_layered_diagnostic_writes_separate_alpha_and_overlay_files(tmp_path: pathlib.Path) -> None:
    labels = {0: "unlabelled", 1: "brick facade", 2: "glass window", 3: "person"}
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

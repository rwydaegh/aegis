from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from semantic_twin.viz.blender.panorama_panels import (
    PRIMARY_PANEL_KEYS,
    PUBLICATION_PANEL_KEYS,
    audit_panel_specs,
    compose_aligned_comparison,
    compose_vertical_curtain,
    panel_availability,
    pipeline_layer_specs,
    pipeline_panel_specs,
    primary_panel_specs,
    publication_panel_specs,
    records_from_paths,
    render_sam3_concept_panel,
    render_sam3_raw_instance_panel,
    write_composition_manifest,
)


def _panel_images(tmp_path: Path, keys: tuple[str, ...]) -> dict[str, Path]:
    paths = {}
    for index, key in enumerate(keys):
        path = tmp_path / f"{key}.png"
        Image.new("RGB", (40, 20), (index * 25, 30, 80)).save(path)
        paths[key] = path
    return paths


def test_primary_panels_keep_the_causal_atlas_channels_separate() -> None:
    specs = primary_panel_specs()
    assert tuple(spec.key for spec in specs) == PRIMARY_PANEL_KEYS
    assert specs[2].channel == "entity_posterior_winner"
    assert specs[2].collection_key == "entity_semantics"
    assert specs[2].show_collections == ("entity_semantics",)
    assert "not per-pixel segmentation" in specs[2].role
    assert "posterior argmax" in specs[3].role
    assert "full posterior" in specs[3].role
    audit = {spec.key: spec for spec in audit_panel_specs()}
    assert "confidence" not in audit["vistas_weight"].title.lower()
    assert audit["confidence"].channel == "confidence"
    assert audit["confidence"].collection_key == "atlas_confidence"
    assert audit["confidence"].show_collections == ("atlas_confidence",)
    assert audit["camera_count"].collection_key == "atlas_camera_count"
    assert audit["camera_count"].show_collections == ("atlas_camera_count",)
    assert audit["observation_count"].collection_key == "atlas_observation_count"
    assert audit["observation_count"].show_collections == ("atlas_observation_count",)
    assert audit["legacy_refusal_depth_status"].required is False


def test_missing_fused_hybrid_is_unavailable_and_not_a_vistas_substitute() -> None:
    records = panel_availability(channels=("vistas_prior_weight",))
    fused = next(record for record in records if record.spec.key == "fused_entity")
    vistas = next(record for record in records if record.spec.key == "vistas_weight")
    assert fused.status == "unavailable"
    assert "Vistas-only" in (fused.reason or "")
    assert vistas.status == "available"


def test_composers_record_slices_dimensions_and_hashes(tmp_path: Path) -> None:
    paths = _panel_images(tmp_path, PRIMARY_PANEL_KEYS)
    metadata = {
        "capture": "capture-a",
        "registration_residual_deg": 0.75,
        "image_sha256": "1" * 64,
        "atlas_sha256": "2" * 64,
        "blend_sha256": "3" * 64,
    }
    curtain = compose_vertical_curtain(paths, tmp_path / "curtain.png", specs=primary_panel_specs(), metadata=metadata)
    assert curtain.dimensions == (40, 20)
    assert curtain.layout == "vertical_curtain_2_to_1"
    assert len(curtain.panels) == 5
    assert curtain.panels[-1].slice_bounds == (32, 0, 40, 20)
    assert curtain.output_sha256 == hashlib.sha256(curtain.output_path.read_bytes()).hexdigest()
    manifest_path = write_composition_manifest(curtain, tmp_path / "curtain.json")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["capture"] == "capture-a"
    assert manifest["panels"][0]["channel"] == "photo"
    assert manifest["panels"][0]["dimensions"] == [8, 20]
    assert manifest["panels"][-1]["slice_bounds"] == [32, 0, 40, 20]
    assert manifest["output_sha256"] == curtain.output_sha256

    comparison = compose_aligned_comparison(
        paths,
        tmp_path / "comparison.png",
        specs=primary_panel_specs(),
        metadata=metadata,
    )
    assert comparison.dimensions == (40, 100)
    assert comparison.panels[1].slice_bounds == (0, 20, 40, 40)
    assert comparison.panels[1].dimensions == (40, 20)


def test_records_reject_mismatched_registered_dimensions(tmp_path: Path) -> None:
    paths = _panel_images(tmp_path, PRIMARY_PANEL_KEYS)
    Image.new("RGB", (41, 20)).save(paths["final_transport"])
    try:
        records_from_paths(paths, specs=primary_panel_specs(), dimensions=(40, 20))
    except ValueError as error:
        assert "synchronized dimensions" in str(error)
    else:
        raise AssertionError("a panel with a different projection size must be rejected")


def test_composers_reject_mismatched_registered_dimensions(tmp_path: Path) -> None:
    paths = _panel_images(tmp_path, PRIMARY_PANEL_KEYS)
    Image.new("RGB", (41, 20)).save(paths["final_transport"])
    for compose, name in (
        (compose_vertical_curtain, "curtain.png"),
        (compose_aligned_comparison, "comparison.png"),
    ):
        try:
            compose(paths, tmp_path / name, specs=primary_panel_specs())
        except ValueError as error:
            assert "synchronized registered dimensions" in str(error)
        else:
            raise AssertionError("a composer must reject differently sized registered panels")


def test_pipeline_spec_order_has_primary_then_audit() -> None:
    specs = pipeline_panel_specs()
    assert tuple(spec.key for spec in specs[:5]) == PRIMARY_PANEL_KEYS
    assert tuple(spec.key for spec in specs[5:]) == tuple(spec.key for spec in audit_panel_specs())


def test_pipeline_layers_do_not_depth_fight_the_coplanar_support_holdout() -> None:
    layers = dict(pipeline_layer_specs())
    assert layers["Registered photograph"] == ("twin",)
    assert layers["Full traced support"] == ("twin", "outer_support", "support_extent")
    assert layers["Fused entity semantics (all-camera projection-aligned fusion)"] == ("entity_semantics",)
    assert all(
        "twin" not in shown
        for title, shown in layers.items()
        if title not in {"Registered photograph", "Full traced support"}
    )


def test_publication_panels_put_image_space_sam3_before_surface_fusion() -> None:
    specs = publication_panel_specs()
    assert tuple(spec.key for spec in specs) == PUBLICATION_PANEL_KEYS
    assert "spherical reprojection" in specs[1].role
    assert "raw overlapping instance masks" in specs[1].role


def test_render_sam3_concept_panel_uses_pinned_image_space_evidence(tmp_path: Path) -> None:
    panorama = tmp_path / "panorama.png"
    Image.new("RGB", (4, 2), (100, 100, 100)).save(panorama)
    semantics = tmp_path / "panorama_semantics.npz"
    np.savez_compressed(semantics, support_concept=np.array([[0, 1, 1, 0], [2, 2, 0, 0]]))
    metadata = tmp_path / "semantics.json"
    metadata.write_text(
        json.dumps(
            {
                "concept_backend": {"model": "facebook/sam3", "revision": "pinned"},
                "concept_id2label": {"0": "unlabelled", "1": "stone", "2": "glass"},
            }
        )
    )

    record = render_sam3_concept_panel(panorama, semantics, metadata, tmp_path / "sam3.png", opacity=1.0)

    assert record.status == "available"
    assert record.dimensions == (4, 2)
    rendered = np.asarray(Image.open(record.path))
    assert tuple(rendered[0, 0]) == (100, 100, 100)
    assert tuple(rendered[0, 1]) != (100, 100, 100)
    provenance = json.loads((tmp_path / "sam3.provenance.json").read_text())
    assert provenance["concept_backend"]["revision"] == "pinned"
    assert provenance["labelled_fraction"] == 0.5


def test_render_sam3_raw_instance_panel_preserves_all_overlaps(tmp_path: Path) -> None:
    view = tmp_path / "view.png"
    Image.new("RGB", (2, 2), (100, 100, 100)).save(view)
    masks = np.array(
        [
            [[True, True], [False, False]],
            [[False, True], [False, True]],
        ]
    )
    packed = np.packbits(masks.reshape(2, -1), axis=1)
    cache = tmp_path / "concepts.npz"
    np.savez_compressed(
        cache,
        packed_masks=packed,
        mask_shape=np.array([2, 2]),
        scores=np.array([0.4, 0.9]),
        labels=np.array(["stone", "glass"]),
        kinds=np.array(["surface", "surface"]),
        cache_key=np.array("cache-a"),
    )

    output = render_sam3_raw_instance_panel(view, cache, tmp_path / "raw.png", opacity=0.5)

    assert Image.open(output).size == (2, 2)
    provenance = json.loads((tmp_path / "raw.provenance.json").read_text())
    assert provenance["instance_count"] == 2
    assert provenance["labels"] == ["stone", "glass"]

from __future__ import annotations

import pathlib

import numpy as np
import pytest
from PIL import Image

from semantic_twin.pano_geometry import (
    PerspectiveView,
    extract_perspective,
    inference_views,
    perspective_directions,
    view_pixel_coordinates,
)
from semantic_twin.vision.vocabulary import ConceptCatalog
from semantic_twin.vision.dense import (
    BRIDGE,
    DEFAULT_INFERENCE_SIZE,
    MODEL,
    PRODUCTION_REVISION,
    Mask2FormerBackend,
    dense_cache_settings,
    resolve_mask2former_snapshot,
    reusable_dense_cache,
)
from semantic_twin.vision.fuse import fuse_layers, fuse_predictions
from semantic_twin.vision.material import concept_support_table, resolve_material, vistas_material_prior
from semantic_twin.vision.panorama import predict_views
from semantic_twin.vision.views import DEFAULT_VIEW_SIZE, perspective_crop, present_classes

ROOT = pathlib.Path(__file__).resolve().parent.parent


def snapshot_path(root: pathlib.Path, revision: str) -> pathlib.Path:
    path = root / "models--facebook--mask2former" / "snapshots" / revision
    path.mkdir(parents=True)
    return path


def test_production_dense_snapshot_is_exactly_pinned_and_recorded(tmp_path) -> None:
    calls: list[tuple[str, str | None]] = []
    path = snapshot_path(tmp_path, PRODUCTION_REVISION)

    def download(*, repo_id: str, revision: str | None) -> str:
        calls.append((repo_id, revision))
        return str(path)

    resolved, identity = resolve_mask2former_snapshot(
        MODEL,
        PRODUCTION_REVISION,
        production=True,
        downloader=download,
    )

    assert resolved == path
    assert calls == [(MODEL, PRODUCTION_REVISION)]
    assert identity == {
        "status": "resolved",
        "repository": MODEL,
        "requested_revision": PRODUCTION_REVISION,
        "resolved_revision": PRODUCTION_REVISION,
        "request_is_immutable": True,
        "matches_reviewed_production_snapshot": True,
        "production_mode": True,
        "required_production_revision": PRODUCTION_REVISION,
        "note": "The requested revision was immutable and the returned snapshot matched it.",
    }


@pytest.mark.parametrize("revision", [None, "main", "4772b6b", "1" * 40])
def test_production_dense_snapshot_refuses_any_other_revision(revision: str | None) -> None:
    with pytest.raises(ValueError, match="production dense inference requires --dense-revision"):
        resolve_mask2former_snapshot(MODEL, revision, production=True)


def test_production_dense_snapshot_refuses_another_repository() -> None:
    with pytest.raises(ValueError, match="production dense inference requires model"):
        resolve_mask2former_snapshot("someone/another-model", PRODUCTION_REVISION, production=True)


def test_development_dense_snapshot_resolves_a_mutable_reference_honestly(tmp_path) -> None:
    path = snapshot_path(tmp_path, PRODUCTION_REVISION)
    resolved, identity = resolve_mask2former_snapshot(
        MODEL,
        "main",
        production=False,
        downloader=lambda **unused: str(path),
    )

    assert resolved == path
    assert identity["requested_revision"] == "main"
    assert identity["resolved_revision"] == PRODUCTION_REVISION
    assert identity["request_is_immutable"] is False
    assert identity["matches_reviewed_production_snapshot"] is True
    assert identity["production_mode"] is False
    assert "mutable" in identity["note"]


def test_dense_snapshot_rejects_a_hub_response_from_the_wrong_commit(tmp_path) -> None:
    requested = "1" * 40
    wrong = snapshot_path(tmp_path, "2" * 40)
    with pytest.raises(RuntimeError, match="returned a different Mask2Former snapshot"):
        resolve_mask2former_snapshot(
            MODEL,
            requested,
            production=False,
            downloader=lambda **unused: str(wrong),
        )


def test_dense_backend_loads_processor_and_weights_from_one_local_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import huggingface_hub
    import transformers

    path = snapshot_path(tmp_path, PRODUCTION_REVISION)
    calls: list[tuple[str, str, dict[str, object]]] = []

    class Processor:
        size = {"height": 384, "width": 384}

    class Model:
        config = type("Config", (), {"id2label": {0: "Sky"}})()

        def to(self, device: str):
            calls.append(("device", device, {}))
            return self

        def eval(self) -> None:
            calls.append(("eval", "", {}))

    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda **unused: str(path))
    monkeypatch.setattr(
        transformers.AutoImageProcessor,
        "from_pretrained",
        classmethod(lambda cls, source, **options: (calls.append(("processor", source, options)), Processor())[1]),
    )
    monkeypatch.setattr(
        transformers.Mask2FormerForUniversalSegmentation,
        "from_pretrained",
        classmethod(lambda cls, source, **options: (calls.append(("model", source, options)), Model())[1]),
    )

    backend = Mask2FormerBackend(
        MODEL,
        "cpu",
        revision=PRODUCTION_REVISION,
        production=True,
    )

    assert ("processor", str(path), {"local_files_only": True}) in calls
    assert (
        "model",
        str(path),
        {"use_safetensors": True, "local_files_only": True},
    ) in calls
    assert backend.checkpoint_digest == PRODUCTION_REVISION
    assert backend.revision_identity["production_mode"] is True


def panorama_image(width: int = 256, height: int = 128) -> Image.Image:
    rng = np.random.default_rng(7)
    return Image.fromarray(rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8), "RGB")


def reference_fuse(
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    """The straightforward every-view-over-every-pixel fusion, as a reference."""
    labels_out = np.zeros((height, width), dtype=np.uint16)
    confidence_out = np.zeros((height, width), dtype=np.float16)
    best = np.full((height, width), -np.inf, dtype=np.float32)
    yaw = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    pitch = (0.5 - (np.arange(height) + 0.5) / height) * np.pi
    yy, pp = np.meshgrid(yaw, pitch)
    cp = np.cos(pp)
    directions = np.stack([np.sin(yy) * cp, np.cos(yy) * cp, np.sin(pp)], axis=2)
    for view, labels, confidence in predictions:
        px, py, valid = view_pixel_coordinates(directions, view, labels.shape[1], labels.shape[0])
        sampled_conf = np.zeros_like(best)
        sampled_labels = np.zeros_like(labels_out)
        sampled_conf[valid] = confidence[py[valid], px[valid]].astype(np.float32)
        sampled_labels[valid] = labels[py[valid], px[valid]]
        centre = perspective_directions(view, 1, 1)[0, 0]
        score = sampled_conf * np.clip(directions @ centre, 0.0, 1.0) ** 4
        take = valid & (score > best)
        best[take] = score[take]
        labels_out[take] = sampled_labels[take]
        confidence_out[take] = sampled_conf[take].astype(np.float16)
    return labels_out, confidence_out


def synthetic_predictions(view_size: int = 48) -> list[tuple[PerspectiveView, np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(11)
    predictions = []
    for index, view in enumerate(inference_views()):
        labels = rng.integers(0, 60, size=(view_size, view_size)).astype(np.uint16)
        confidence = (0.2 + 0.8 * rng.random((view_size, view_size))).astype(np.float16)
        confidence[0, 0] = np.float16(1.0 - index * 0.01)
        predictions.append((view, labels, confidence))
    return predictions


def test_perspective_crop_matches_the_panorama_geometry_helper() -> None:
    panorama = panorama_image()
    array = np.asarray(panorama.convert("RGB"))
    view = PerspectiveView("h+00_045", 45.0, 0.0, 90.0)

    hoisted = perspective_crop(array, view, width=64, height=64)
    reference = extract_perspective(panorama, view, width=64, height=64)

    np.testing.assert_array_equal(np.asarray(hoisted), np.asarray(reference))
    with pytest.raises(ValueError, match="decoded"):
        perspective_crop(array[:, :, 0], view, width=8, height=8)


def test_the_panorama_is_decoded_once_for_every_inference_view(tmp_path) -> None:
    class CountingPanorama:
        def __init__(self, image: Image.Image) -> None:
            self.image = image
            self.conversions = 0

        def convert(self, mode: str) -> Image.Image:
            self.conversions += 1
            return self.image.convert(mode)

    class ConstantBackend:
        def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
            return (
                np.zeros(image.size[::-1], dtype=np.uint16),
                np.full(image.size[::-1], 0.5, dtype=np.float16),
            )

    panorama = CountingPanorama(panorama_image())

    predictions, manifest, concepts = predict_views(panorama, ConstantBackend(), tmp_path, view_size=32)

    assert len(predictions) == len(inference_views()) == len(manifest)
    assert panorama.conversions == 1
    assert concepts == {}


class CountingBackend:
    """A dense backend that records how many crops it was actually asked about."""

    model_name = "a-test-checkpoint"
    checkpoint_digest = "cafef00d"
    inference_size = 64
    id2label = {0: "Sky"}

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        self.calls += 1
        return (
            np.zeros(image.size[::-1], dtype=np.uint16),
            np.full(image.size[::-1], 0.5, dtype=np.float16),
        )


def test_dense_views_cached_under_other_settings_are_recomputed(tmp_path) -> None:
    panorama = panorama_image()
    views = len(inference_views())
    backend = CountingBackend()

    predict_views(panorama, backend, tmp_path, view_size=32)
    assert backend.calls == views
    assert reusable_dense_cache(tmp_path, dense_cache_settings(backend, 32))

    # Same settings: the cache is trusted and nothing is segmented again.
    predict_views(panorama, backend, tmp_path, view_size=32)
    assert backend.calls == views

    # A different crop size is a different cache, and so is a different
    # checkpoint or inference resolution. Reusing 384-resolution labels under a
    # 1536 run is the failure this guards against.
    assert not reusable_dense_cache(tmp_path, dense_cache_settings(backend, 48))
    predict_views(panorama, backend, tmp_path, view_size=48)
    assert backend.calls == 2 * views

    backend.inference_size = 128
    assert not reusable_dense_cache(tmp_path, dense_cache_settings(backend, 48))
    backend.inference_size = 64
    backend.model_name = "another-checkpoint"
    assert not reusable_dense_cache(tmp_path, dense_cache_settings(backend, 48))


def test_the_cache_is_keyed_on_the_checkpoint_and_the_source_panorama(tmp_path) -> None:
    backend = CountingBackend()
    views = tmp_path / "views"
    views.mkdir()
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    panorama_image().save(first)
    panorama_image(width=252).save(second)

    predict_views(panorama_image(), backend, views, view_size=32, panorama_path=first)
    assert reusable_dense_cache(views, dense_cache_settings(backend, 32, first))

    # A different capture of the same site writes into the same directory.
    assert not reusable_dense_cache(views, dense_cache_settings(backend, 32, second))
    # A model name does not pin a checkpoint, because a name can be re-uploaded.
    backend.checkpoint_digest = "a different revision"
    assert not reusable_dense_cache(views, dense_cache_settings(backend, 32, first))


def test_an_unstamped_view_directory_is_never_reused(tmp_path) -> None:
    backend = CountingBackend()
    predict_views(panorama_image(), backend, tmp_path, view_size=32)
    (tmp_path / "cache_settings.json").unlink()

    assert not reusable_dense_cache(tmp_path, dense_cache_settings(backend, 32))
    predict_views(panorama_image(), backend, tmp_path, view_size=32)
    assert backend.calls == 2 * len(inference_views())


def test_footprint_culling_reproduces_the_unculled_fusion_exactly() -> None:
    predictions = synthetic_predictions()

    labels, confidence = fuse_predictions(predictions, width=192, height=96, row_chunk=17)
    expected_labels, expected_confidence = reference_fuse(predictions, width=192, height=96)

    np.testing.assert_array_equal(labels, expected_labels)
    np.testing.assert_array_equal(confidence, expected_confidence)


def test_footprint_culling_survives_an_odd_output_size_and_a_single_row_chunk() -> None:
    predictions = synthetic_predictions(view_size=32)

    labels, confidence = fuse_predictions(predictions, width=101, height=50, row_chunk=1)
    expected_labels, expected_confidence = reference_fuse(predictions, width=101, height=50)

    np.testing.assert_array_equal(labels, expected_labels)
    np.testing.assert_array_equal(confidence, expected_confidence)


def test_the_inference_resolution_is_an_explicit_default_not_the_checkpoint_384() -> None:
    assert DEFAULT_INFERENCE_SIZE == 1536
    assert DEFAULT_VIEW_SIZE == DEFAULT_INFERENCE_SIZE


def test_sparse_layer_fusion_never_lets_an_empty_view_claim_a_pixel() -> None:
    views = inference_views()[:2]
    labelled = (views[0], np.ones((8, 8), dtype=np.uint16), np.full((8, 8), 0.2, dtype=np.float16))
    empty = (views[1], np.zeros((8, 8), dtype=np.uint16), np.full((8, 8), 0.9, dtype=np.float16))

    dense, _ = fuse_predictions([labelled, empty], width=64, height=32)
    sparse, _ = fuse_predictions([labelled, empty], width=64, height=32, require_nonzero=True)

    # The dense partition lets class zero win on confidence. The sparse layer
    # treats zero as "nothing detected here", so it can only lose.
    assert np.count_nonzero(dense == 1) < np.count_nonzero(sparse == 1)
    assert set(np.unique(sparse).tolist()) <= {0, 1}
    assert np.all(sparse[dense == 1] == 1)


def test_fusing_layers_together_matches_fusing_them_one_at_a_time() -> None:
    rng = np.random.default_rng(3)
    views = inference_views()[:6]
    layers = {
        name: [
            (
                rng.integers(0, 5, size=(24, 24)).astype(np.uint16),
                rng.random((24, 24)).astype(np.float16),
            )
            for _ in views
        ]
        for name in ("support", "material", "clutter")
    }

    together = fuse_layers(views, layers, width=96, height=48, row_chunk=13, require_nonzero=True)

    for name, per_view in layers.items():
        alone = fuse_predictions(
            [(view, labels, confidence) for view, (labels, confidence) in zip(views, per_view, strict=True)],
            width=96,
            height=48,
            row_chunk=13,
            require_nonzero=True,
        )
        np.testing.assert_array_equal(together[name][0], alone[0])
        np.testing.assert_array_equal(together[name][1], alone[1])


def test_fuse_layers_rejects_a_layer_that_is_missing_a_view() -> None:
    views = inference_views()[:3]
    raster = (np.zeros((8, 8), dtype=np.uint16), np.zeros((8, 8), dtype=np.float16))
    with pytest.raises(ValueError, match="one raster pair per view"):
        fuse_layers(views, {"support": [raster, raster]}, width=32, height=16)


def test_present_classes_ignores_a_handful_of_stray_pixels() -> None:
    labels = np.zeros((64, 64), dtype=np.uint16)
    labels[:32] = 17
    labels[60, :3] = 27
    id2label = {0: "Bird", 17: "Building", 27: "Sky"}

    assert present_classes(labels, id2label, minimum_pixels=256) == frozenset({"Bird", "Building"})
    assert "Sky" in present_classes(labels, id2label, minimum_pixels=2)


def _bridge_tables(id2label: dict[int, str]):
    catalog = ConceptCatalog.load(ROOT / "config" / "semantic_concepts.json")
    bridge = catalog.bridges[BRIDGE]
    return (
        catalog,
        vistas_material_prior(id2label, catalog, bridge),
        concept_support_table(id2label, catalog, bridge),
    )


def test_a_facade_concept_cannot_repaint_the_person_standing_in_front_of_it() -> None:
    id2label = {0: "Building", 1: "Person"}
    catalog, prior, support = _bridge_tables(id2label)
    materials = catalog.taxonomy["materials"]
    brick = catalog.prompts.index("brick facade") + 1

    entity = np.asarray([[0, 1]], dtype=np.uint16)
    concept = np.asarray([[brick, brick]], dtype=np.uint16)
    resolved = resolve_material(
        entity,
        concept,
        np.full(concept.shape, 0.8, dtype=np.float16),
        prior_table=prior,
        concept_material=catalog.material_matrix(),
        support_table=support,
    )

    assert materials[int(resolved.material[0, 0])] == "brick"
    assert resolved.source[0, 0] == 1
    # The concept is not admissible over Person, so the dense prior stands and
    # the pixel keeps human tissue instead of becoming a brick scatterer.
    assert materials[int(resolved.material[0, 1])] == "human_tissue"
    assert resolved.source[0, 1] == 0
    assert resolved.concept[0, 1] == 0


def test_the_material_axis_stays_dense_where_no_concept_fired() -> None:
    id2label = {0: "Building", 1: "Road", 2: "Sky"}
    catalog, prior, support = _bridge_tables(id2label)
    materials = catalog.taxonomy["materials"]

    entity = np.asarray([[0, 1, 2]], dtype=np.uint16)
    concept = np.zeros((1, 3), dtype=np.uint16)
    resolved = resolve_material(
        entity,
        concept,
        np.full(concept.shape, 0.8, dtype=np.float16),
        prior_table=prior,
        concept_material=catalog.material_matrix(),
        support_table=support,
    )

    assert np.all(resolved.source == 0)
    assert materials[int(resolved.material[0, 1])] == "asphalt_concrete"
    assert materials[int(resolved.material[0, 2])] == "air"
    # Building is deliberately unresolved: its winning prior mass is small, so
    # the pixel reads as uncertain rather than confidently brick.
    assert resolved.prior_mass[0, 0] < 0.4
    assert resolved.prior_mass[0, 1] > resolved.prior_mass[0, 0]


def test_a_material_only_concept_is_admissible_only_where_the_prior_allows_it() -> None:
    id2label = {0: "Pole", 1: "Pedestrian Area", 2: "Sky"}
    catalog, prior, support = _bridge_tables(id2label)
    materials = catalog.taxonomy["materials"]
    metal = catalog.prompts.index("metal surface") + 1

    # Pole carries metal mass, a cobbled square and the sky do not.
    assert support[metal].tolist() == [True, False, False]
    entity = np.asarray([[0, 1, 2]], dtype=np.uint16)
    concept = np.full((1, 3), metal, dtype=np.uint16)
    resolved = resolve_material(
        entity,
        concept,
        np.full(concept.shape, 0.8, dtype=np.float16),
        prior_table=prior,
        concept_material=catalog.material_matrix(),
        support_table=support,
    )

    assert resolved.source.tolist() == [[1, 0, 0]]
    assert materials[int(resolved.material[0, 0])] == "metal"
    # The concept sharpens the pole from a 0.8 prior to its own 0.96.
    assert resolved.prior_mass[0, 0] > 0.9
    assert materials[int(resolved.material[0, 1])] == "marble"
    assert materials[int(resolved.material[0, 2])] == "air"


def test_a_rejected_concept_leaves_no_confidence_behind() -> None:
    id2label = {0: "Building", 1: "Person"}
    catalog, prior, support = _bridge_tables(id2label)
    brick = catalog.prompts.index("brick facade") + 1

    resolved = resolve_material(
        np.asarray([[0, 1]], dtype=np.uint16),
        np.asarray([[brick, brick]], dtype=np.uint16),
        np.asarray([[0.9, 0.9]], dtype=np.float16),
        prior_table=prior,
        concept_material=catalog.material_matrix(),
        support_table=support,
    )

    # A confidence surviving next to a zeroed concept would advertise a
    # detection that is not in the output.
    assert resolved.detection_confidence.tolist() == [[np.float16(0.9), 0.0]]
    assert np.all((resolved.concept > 0) == (resolved.detection_confidence > 0))


def test_prior_mass_is_the_catalogue_share_and_not_the_detection_score() -> None:
    id2label = {0: "Pole"}
    catalog, prior, support = _bridge_tables(id2label)
    metal = catalog.prompts.index("metal surface") + 1

    resolved = resolve_material(
        np.zeros((1, 1), dtype=np.uint16),
        np.full((1, 1), metal, dtype=np.uint16),
        np.full((1, 1), 0.36, dtype=np.float16),
        prior_table=prior,
        concept_material=catalog.material_matrix(),
        support_table=support,
    )

    # A detection barely over threshold still exports the concept's own prior
    # mass, so the two must never be read as one number.
    assert float(resolved.prior_mass[0, 0]) > 0.9
    assert float(resolved.detection_confidence[0, 0]) < 0.4


def test_resolve_material_rejects_mismatched_rasters() -> None:
    id2label = {0: "Building"}
    catalog, prior, support = _bridge_tables(id2label)
    with pytest.raises(ValueError, match="same shape"):
        resolve_material(
            np.zeros((1, 2), dtype=np.uint16),
            np.zeros((1, 3), dtype=np.uint16),
            np.zeros((1, 3), dtype=np.float16),
            prior_table=prior,
            concept_material=catalog.material_matrix(),
            support_table=support,
        )

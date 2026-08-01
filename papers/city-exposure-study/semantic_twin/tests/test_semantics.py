from __future__ import annotations

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
from semantic_twin.semantics import (
    DEFAULT_INFERENCE_SIZE,
    DEFAULT_VIEW_SIZE,
    fuse_predictions,
    perspective_crop,
    predict_views,
)


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

    predictions, manifest = predict_views(panorama, ConstantBackend(), tmp_path, view_size=32)

    assert len(predictions) == len(inference_views()) == len(manifest)
    assert panorama.conversions == 1


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

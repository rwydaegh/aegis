from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.concepts import ConceptCatalog
from semantic_twin.sam3_concepts import (
    MODEL,
    ConceptPrediction,
    cache_key,
    load_prediction,
    save_prediction,
    select_instances,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "config" / "semantic_concepts.json"


def settings(catalog: ConceptCatalog, **overrides) -> dict:
    base = {"model": MODEL, "resolution": 1008, "threshold": 0.35, "view_size": 1536, "catalog": catalog}
    return {**base, **overrides}


def prediction(height: int = 4, width: int = 6) -> ConceptPrediction:
    masks = np.zeros((2, height, width), dtype=bool)
    masks[0, :2] = True
    masks[1, 2:, 3:] = True
    return ConceptPrediction(
        masks=masks,
        labels=np.asarray(["brick facade", "glass window"]),
        kinds=np.asarray(["surface", "surface"]),
        scores=np.asarray([0.9, 0.6], dtype=np.float32),
        height=height,
        width=width,
        asked_prompts=("brick facade", "glass window"),
    )


def test_a_cached_view_round_trips_bit_identically(tmp_path: pathlib.Path) -> None:
    catalog = ConceptCatalog.load(CATALOG)
    key = cache_key(**settings(catalog))
    path = tmp_path / "h+00_000.npz"
    original = prediction()

    save_prediction(path, original, key=key)
    restored = load_prediction(path, key=key)

    assert restored is not None
    np.testing.assert_array_equal(restored.masks, original.masks)
    np.testing.assert_array_equal(restored.labels, original.labels)
    np.testing.assert_array_equal(restored.scores, original.scores)
    assert restored.asked_prompts == original.asked_prompts


def test_a_cached_view_is_refused_under_different_inference_settings(tmp_path: pathlib.Path) -> None:
    catalog = ConceptCatalog.load(CATALOG)
    path = tmp_path / "h+00_000.npz"
    save_prediction(path, prediction(), key=cache_key(**settings(catalog)))

    for change in (
        {"model": "facebook/sam3-something-else"},
        {"resolution": 1260},
        {"threshold": 0.4},
        {"view_size": 1024},
    ):
        assert load_prediction(path, key=cache_key(**settings(catalog, **change))) is None
    assert load_prediction(path, key=cache_key(**settings(catalog))) is not None


def test_an_empty_view_round_trips_without_a_mask_array(tmp_path: pathlib.Path) -> None:
    catalog = ConceptCatalog.load(CATALOG)
    key = cache_key(**settings(catalog))
    path = tmp_path / "zenith.npz"
    empty = ConceptPrediction(
        masks=np.zeros((0, 8, 8), dtype=bool),
        labels=np.asarray([], dtype=str),
        kinds=np.asarray([], dtype=str),
        scores=np.asarray([], dtype=np.float32),
        height=8,
        width=8,
    )

    save_prediction(path, empty, key=key)
    restored = load_prediction(path, key=key)

    assert restored is not None
    assert restored.masks.shape == (0, 8, 8)
    assert len(restored.labels) == 0


def test_a_missing_or_unkeyed_file_is_a_cache_miss_not_an_error(tmp_path: pathlib.Path) -> None:
    catalog = ConceptCatalog.load(CATALOG)
    key = cache_key(**settings(catalog))
    assert load_prediction(tmp_path / "absent.npz", key=key) is None

    legacy = tmp_path / "legacy.npz"
    np.savez_compressed(
        legacy,
        packed_masks=np.zeros((0, 0), dtype=np.uint8),
        mask_shape=np.asarray([4, 4]),
        scores=np.asarray([], dtype=np.float32),
        labels=np.asarray([], dtype=str),
        kinds=np.asarray([], dtype=str),
    )
    assert load_prediction(legacy, key=key) is None


def test_masks_stay_attached_to_the_prompt_that_produced_them() -> None:
    prompts = ("brick facade", "glass window", "person")
    kinds = {"brick facade": "surface", "glass window": "surface", "person": "object"}
    # Two queries fire on the first prompt, none on the second, one on the third.
    probability = np.asarray(
        [
            [0.90, 0.10, 0.70],
            [0.20, 0.05, 0.30],
            [0.05, 0.60, 0.10],
        ],
        dtype=np.float32,
    )

    keep, labels, kinds_out, scores = select_instances(probability, prompts, kinds, threshold=0.35)

    assert keep.sum() == 3
    # Row-major order over (prompt, query), which is the order the mask tensor
    # comes back in. Any other order silently mislabels every surface.
    assert labels == ["brick facade", "brick facade", "person"]
    assert kinds_out == ["surface", "surface", "object"]
    assert scores == pytest.approx([0.90, 0.70, 0.60])
    # Selecting the mask tensor with the same boolean has to give the same order.
    masks = np.arange(9).reshape(3, 3)
    assert masks[keep].tolist() == [0, 2, 7]


def test_select_instances_rejects_a_result_that_does_not_match_the_prompts() -> None:
    with pytest.raises(ValueError, match="prompt rows"):
        select_instances(np.zeros((2, 4), dtype=np.float32), ("a", "b", "c"), {}, threshold=0.5)
    with pytest.raises(ValueError, match="prompt, query"):
        select_instances(np.zeros(4, dtype=np.float32), ("a",), {}, threshold=0.5)


def test_the_cache_key_ignores_priors_the_model_never_sees(tmp_path: pathlib.Path) -> None:
    catalog = ConceptCatalog.load(CATALOG)
    document = json.loads(CATALOG.read_text())
    for record in document["concepts"]:
        if record["prompt"] == "brick facade":
            record["material"] = {"brick": 0.5, "concrete": 0.5}
            record["attributes"] = {"rough": 0.1}
    retuned = tmp_path / "retuned.json"
    retuned.write_text(json.dumps(document))

    # Priors are read fresh at fusion time and never reach SAM 3, so retuning
    # one must not throw away a city of segmentation.
    assert cache_key(**settings(catalog)) == cache_key(**settings(ConceptCatalog.load(retuned)))

    document["concepts"].append(
        {"prompt": "a brand new prompt", "kind": "surface", "entity": {"unknown": 1.0}, "material": {"unknown": 1.0}}
    )
    added = tmp_path / "added.json"
    added.write_text(json.dumps(document))
    assert cache_key(**settings(catalog)) != cache_key(**settings(ConceptCatalog.load(added)))

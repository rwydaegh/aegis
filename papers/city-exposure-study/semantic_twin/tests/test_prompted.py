from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.vision.vocabulary import ConceptCatalog
from semantic_twin.vision.prompted import (
    MODEL,
    PRODUCTION_CATALOGUE_SEMANTIC_SHA256,
    PRODUCTION_REPOSITORY_COMMIT,
    PRODUCTION_REVISION,
    ConceptPrediction,
    Sam3ConceptBackend,
    cache_key,
    load_prediction,
    resolve_sam3_snapshot,
    save_prediction,
    select_instances,
    semantic_catalogue_identity,
    verify_sam3_repository,
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


def test_reviewed_semantic_catalogue_is_accepted_for_production() -> None:
    identity = semantic_catalogue_identity(CATALOG, production=True)

    assert identity["catalogue_semantic_sha256"] == PRODUCTION_CATALOGUE_SEMANTIC_SHA256
    assert identity["matches_reviewed_production_catalogue"] is True
    assert identity["production_mode"] is True


def test_production_catalogue_identity_ignores_json_formatting(tmp_path: pathlib.Path) -> None:
    document = json.loads(CATALOG.read_text())
    reordered = dict(reversed(tuple(document.items())))
    reformatted = tmp_path / "semantic_concepts.json"
    reformatted.write_text(json.dumps(reordered, indent=4))

    identity = semantic_catalogue_identity(reformatted, production=True)

    assert identity["catalogue_semantic_sha256"] == PRODUCTION_CATALOGUE_SEMANTIC_SHA256
    assert identity["catalogue_sha256"] != semantic_catalogue_identity(CATALOG, production=True)["catalogue_sha256"]


@pytest.mark.parametrize("change", ["prompt", "mapping"])
def test_production_refuses_a_different_catalogue_with_the_same_id_count(
    tmp_path: pathlib.Path,
    change: str,
) -> None:
    document = json.loads(CATALOG.read_text())
    if change == "prompt":
        document["concepts"][0]["prompt"] = "review bypass with the same count"
    else:
        document["backend_bridge"]["mask2former_mapillary_vistas"]["entity_support"]["facade"] = ["Sky"]
    changed = tmp_path / "semantic_concepts.json"
    changed.write_text(json.dumps(document))

    assert len(ConceptCatalog.load(changed).id2label()) == 61
    with pytest.raises(ValueError, match="reviewed semantic catalogue"):
        semantic_catalogue_identity(changed, production=True)


def test_development_records_an_unreviewed_catalogue_without_refusing_it(tmp_path: pathlib.Path) -> None:
    document = json.loads(CATALOG.read_text())
    document["concepts"][0]["prompt"] = "development-only label"
    changed = tmp_path / "semantic_concepts.json"
    changed.write_text(json.dumps(document))

    identity = semantic_catalogue_identity(changed, production=False)

    assert identity["matches_reviewed_production_catalogue"] is False
    assert identity["production_mode"] is False


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
        {"model_revision": "1" * 40},
    ):
        assert load_prediction(path, key=cache_key(**settings(catalog, **change))) is None
    assert load_prediction(path, key=cache_key(**settings(catalog))) is not None


def test_an_immutable_hugging_face_revision_is_used_verified_and_recorded(tmp_path: pathlib.Path) -> None:
    revision = PRODUCTION_REVISION
    snapshot = tmp_path / "models--facebook--sam3" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    (snapshot / "sam3.pt").write_bytes(b"pinned checkpoint")
    (snapshot / "config.json").write_bytes(b'{"model": "sam3"}')
    calls: list[tuple[str, str, str]] = []

    def download(*, repo_id: str, filename: str, revision: str) -> str:
        calls.append((repo_id, filename, revision))
        return str(snapshot / filename)

    checkpoint, identity = resolve_sam3_snapshot(revision, production=True, downloader=download)

    assert checkpoint == snapshot / "sam3.pt"
    assert calls == [
        ("facebook/sam3", "sam3.pt", revision),
        ("facebook/sam3", "config.json", revision),
    ]
    assert identity["status"] == "resolved"
    assert identity["resolved_revision"] == revision
    assert identity["checkpoint_sha256"] == "2ea54754bc597a399df6c75aa6e1b19e495627ccfac66a711afad4e381a08e0f"
    assert identity["matches_reviewed_production_snapshot"] is True
    assert identity["required_production_revision"] == PRODUCTION_REVISION
    assert identity["production_mode"] is True


@pytest.mark.parametrize("revision", [None, "main", "v1", "3c879f3"])
def test_production_refuses_a_missing_or_mutable_sam_revision(revision: str | None) -> None:
    with pytest.raises(ValueError, match="40-character Hub commit"):
        resolve_sam3_snapshot(revision, production=True)


def test_production_refuses_another_immutable_sam_revision() -> None:
    with pytest.raises(ValueError, match="reviewed 40-character Hub commit"):
        resolve_sam3_snapshot("1" * 40, production=True)


def test_development_accepts_another_immutable_sam_revision(tmp_path: pathlib.Path) -> None:
    revision = "1" * 40
    snapshot = tmp_path / "models--facebook--sam3" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    (snapshot / "sam3.pt").write_bytes(b"development checkpoint")
    (snapshot / "config.json").write_bytes(b"{}")

    checkpoint, identity = resolve_sam3_snapshot(
        revision,
        production=False,
        downloader=lambda **call: str(snapshot / call["filename"]),
    )

    assert checkpoint == snapshot / "sam3.pt"
    assert identity["resolved_revision"] == revision
    assert identity["matches_reviewed_production_snapshot"] is False
    assert identity["required_production_revision"] == PRODUCTION_REVISION
    assert identity["production_mode"] is False


def test_development_keeps_mutable_sam_identity_explicitly_unresolved() -> None:
    checkpoint, identity = resolve_sam3_snapshot("main", production=False)

    assert checkpoint is None
    assert identity == {
        "status": "unresolved",
        "repository": "facebook/sam3",
        "requested_revision": "main",
        "resolved_revision": None,
        "checkpoint_filename": "sam3.pt",
        "checkpoint_sha256": None,
        "matches_reviewed_production_snapshot": False,
        "required_production_revision": PRODUCTION_REVISION,
        "production_mode": False,
        "note": "No immutable 40-character Hugging Face commit was supplied.",
    }


def test_sam_repository_commit_is_verified_for_production() -> None:
    commit = PRODUCTION_REPOSITORY_COMMIT

    assert verify_sam3_repository(commit, commit, production=True) == {
        "status": "resolved",
        "expected_commit": commit,
        "resolved_commit": commit,
        "matches_reviewed_production_source": True,
        "required_production_commit": PRODUCTION_REPOSITORY_COMMIT,
        "production_mode": True,
    }
    with pytest.raises(RuntimeError, match="installed source at reviewed commit"):
        verify_sam3_repository(commit, "1" * 40, production=True)
    with pytest.raises(ValueError, match="sam-repository-commit"):
        verify_sam3_repository(None, commit, production=True)


def test_production_refuses_another_matching_immutable_sam_source_pair() -> None:
    other = "1" * 40

    with pytest.raises(ValueError, match="reviewed source commit"):
        verify_sam3_repository(other, other, production=True)


def test_development_accepts_another_matching_immutable_sam_source_pair() -> None:
    other = "1" * 40

    identity = verify_sam3_repository(other, other, production=False)

    assert identity == {
        "status": "resolved",
        "expected_commit": other,
        "resolved_commit": other,
        "matches_reviewed_production_source": False,
        "required_production_commit": PRODUCTION_REPOSITORY_COMMIT,
        "production_mode": False,
    }


def test_backend_manifest_carries_weight_and_source_commits_into_semantics_json() -> None:
    weight_commit = PRODUCTION_REVISION
    source_commit = PRODUCTION_REPOSITORY_COMMIT
    backend = object.__new__(Sam3ConceptBackend)
    backend.snapshot = {
        "status": "resolved",
        "resolved_revision": weight_commit,
        "checkpoint_sha256": "a" * 64,
    }
    backend.repository = {
        "status": "resolved",
        "expected_commit": source_commit,
        "resolved_commit": source_commit,
    }
    backend.resolution = 1008
    backend.processor_default_resolution = 1008
    backend.threshold = 0.35
    backend.prompt_batch = 32

    manifest = backend.manifest()

    assert manifest["revision"] == weight_commit
    assert manifest["checkpoint_sha256"] == "a" * 64
    assert manifest["repository_commit"] == source_commit
    assert manifest["huggingface_snapshot"] is backend.snapshot
    assert manifest["sam3_repository"] is backend.repository


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

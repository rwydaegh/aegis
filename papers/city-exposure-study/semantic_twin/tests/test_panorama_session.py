from __future__ import annotations

import dataclasses
import json
import pathlib

import numpy as np
import pytest
from PIL import Image

from semantic_twin.vision import panorama as panorama_module
from semantic_twin.vision.panorama import PanoramaModelSession, PanoramaRunConfig
from semantic_twin.vision.prompted import ConceptPrediction

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FakeDenseBackend:
    constructions = 0

    def __init__(
        self,
        model_name: str,
        device: str,
        *,
        inference_size: int,
        revision: str | None,
        production: bool,
    ) -> None:
        type(self).constructions += 1
        self.model_name = model_name
        self.device = "cuda" if device == "auto" else device
        self.inference_size = inference_size
        self.processor_saved_size = {"height": 384, "width": 384}
        self.checkpoint_digest = revision or "fake-dense"
        self.revision_identity = {"resolved_revision": revision or "fake-dense"}
        self.id2label = {0: "Building"}

    def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        shape = image.size[::-1]
        return np.zeros(shape, dtype=np.uint16), np.full(shape, 0.75, dtype=np.float16)


class FakeConceptBackend:
    constructions = 0

    def __init__(self, catalog, **settings) -> None:
        type(self).constructions += 1
        self.catalog = catalog
        self.settings = settings

    def predict(self, image: Image.Image, prompts: tuple[str, ...]) -> ConceptPrediction:
        width, height = image.size
        return ConceptPrediction(
            masks=np.empty((0, height, width), dtype=bool),
            labels=np.asarray([], dtype=str),
            kinds=np.asarray([], dtype=str),
            scores=np.asarray([], dtype=np.float32),
            height=height,
            width=width,
            asked_prompts=prompts,
        )

    def manifest(self) -> dict[str, object]:
        return {"model": "fake-sam3", **self.settings}


def _config(tmp_path: pathlib.Path, name: str, *, concepts: pathlib.Path | None = None) -> PanoramaRunConfig:
    source = tmp_path / f"{name}.png"
    Image.new("RGB", (64, 32), (90, 120, 150)).save(source)
    return PanoramaRunConfig(
        panorama=source,
        out=tmp_path / name,
        model="fake-dense",
        device="cuda",
        backend="hybrid",
        concepts=concepts or ROOT / "config" / "semantic_concepts.json",
        view_size=16,
        inference_size=32,
        concept_resolution=24,
        concept_threshold=0.35,
        prompt_batch=7,
        gate_min_pixels=1,
        output_width=32,
        force=False,
        dense_revision="dense-revision",
        sam_revision="sam-revision",
        sam_repository_commit="source-revision",
        production=False,
    )


@pytest.fixture
def fake_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeDenseBackend.constructions = 0
    FakeConceptBackend.constructions = 0
    monkeypatch.setattr(panorama_module, "Mask2FormerBackend", FakeDenseBackend)
    monkeypatch.setattr("semantic_twin.vision.prompted.Sam3ConceptBackend", FakeConceptBackend)


def _arrays(path: pathlib.Path) -> dict[str, np.ndarray]:
    with np.load(path / "panorama_semantics.npz", allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def test_session_constructs_each_model_once_and_matches_independent_runs(tmp_path, fake_backends) -> None:
    independent_a = _config(tmp_path, "independent_a")
    independent_b = _config(tmp_path, "independent_b")
    shared_a = _config(tmp_path, "shared_a")
    shared_b = _config(tmp_path, "shared_b")

    panorama_module.run(independent_a)
    panorama_module.run(independent_b)
    assert (FakeDenseBackend.constructions, FakeConceptBackend.constructions) == (2, 2)

    session = PanoramaModelSession(shared_a)
    assert session.concept_backend.settings["device"] == "cuda"
    panorama_module.run(shared_a, session=session)
    panorama_module.run(shared_b, session=session)
    assert (FakeDenseBackend.constructions, FakeConceptBackend.constructions) == (3, 3)

    for expected, actual in ((independent_a.out, shared_a.out), (independent_b.out, shared_b.out)):
        expected_arrays = _arrays(expected)
        actual_arrays = _arrays(actual)
        assert expected_arrays.keys() == actual_arrays.keys()
        for name in expected_arrays:
            np.testing.assert_array_equal(actual_arrays[name], expected_arrays[name])


def test_session_refuses_numerical_or_catalogue_content_drift(tmp_path, fake_backends) -> None:
    concepts = tmp_path / "concepts.json"
    concepts.write_text((ROOT / "config" / "semantic_concepts.json").read_text())
    config = _config(tmp_path, "first", concepts=concepts)
    session = PanoramaModelSession(config)

    with pytest.raises(ValueError, match="concept_threshold"):
        session.validate(dataclasses.replace(config, concept_threshold=0.36))

    document = json.loads(concepts.read_text())
    concepts.write_text(json.dumps(document, indent=4))
    with pytest.raises(ValueError, match="catalogue_sha256"):
        session.validate(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("backend", "dense"),
        ("model", "other-dense"),
        ("device", "auto"),
        ("dense_revision", "other-dense-revision"),
        ("sam_revision", "other-sam-revision"),
        ("sam_repository_commit", "other-source-revision"),
        ("view_size", 18),
        ("inference_size", 34),
        ("concept_resolution", 26),
        ("concept_threshold", 0.36),
        ("prompt_batch", 8),
        ("gate_min_pixels", 2),
        ("output_width", 34),
        ("production", True),
    ],
)
def test_session_refuses_every_model_identity_field(tmp_path, fake_backends, field, value) -> None:
    config = _config(tmp_path, "identity")
    session = PanoramaModelSession(config)

    with pytest.raises(ValueError, match=field):
        session.validate(dataclasses.replace(config, **{field: value}))

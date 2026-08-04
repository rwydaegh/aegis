from __future__ import annotations

import pathlib

import numpy as np
import pytest

from semantic_twin.vision import evidence as evidence_module
from semantic_twin.vision.evidence import (
    EvidenceAccumulator,
    ObservationQuality,
    SoftAssociation,
    categorical_information,
)


def quality(count: int) -> ObservationQuality:
    ones = np.ones(count)
    return ObservationQuality(ones, ones, ones, ones, ones, ones)


def test_uniform_classification_carries_no_directional_information() -> None:
    assert categorical_information(np.array([[0.5, 0.5]]))[0] == 0.0
    assert categorical_information(np.array([[1.0, 0.0]]))[0] > 0.99


def test_soft_association_distributes_evidence_between_surfaces() -> None:
    evidence = EvidenceAccumulator(2, ["wall", "road"], ["brick", "asphalt"], ["reflective"])
    evidence.update(
        SoftAssociation(np.array([[0, 1]]), np.array([[0.75, 0.25]])),
        quality(1),
        np.array([[1.0, 0.0]]),
        np.array([[1.0, 0.0]]),
        np.array([[0.8]]),
    )
    wall_probability = evidence.entity_posterior()[:, 0]
    assert wall_probability[0] > wall_probability[1] > 0.5
    assert evidence.support_weight[0] == 0.75
    assert evidence.support_weight[1] == 0.25


def test_attributes_are_independent_multilabel_posteriors() -> None:
    evidence = EvidenceAccumulator(1, ["fixture"], ["metal"], ["thin", "reflective", "movable"])
    evidence.update(
        SoftAssociation(np.array([[0]]), np.array([[1.0]])),
        quality(1),
        np.array([[1.0]]),
        np.array([[1.0]]),
        np.array([[0.95, 0.9, 0.05]]),
    )
    posterior = evidence.attribute_posterior()[0]
    assert posterior[0] > 0.5
    assert posterior[1] > 0.5
    assert posterior[2] < 0.5


def test_evidence_round_trip(tmp_path) -> None:
    evidence = EvidenceAccumulator(3, ["a", "b"], ["x", "y"], ["thin"])
    path = tmp_path / "evidence.npz"
    evidence.save(path)
    restored = EvidenceAccumulator.load(path)
    np.testing.assert_array_equal(restored.entity_alpha, evidence.entity_alpha)
    assert restored.attribute_labels == ["thin"]


def _corrupted_checkpoint(tmp_path, **overrides) -> pathlib.Path:
    evidence = EvidenceAccumulator(3, ["a", "b"], ["x", "y"], ["thin"])
    path = tmp_path / "evidence.npz"
    evidence.save(path)
    with np.load(path, allow_pickle=False) as document:
        arrays = {name: document[name] for name in document.files}
    arrays.update(overrides)
    np.savez_compressed(path, **arrays)
    return path


def test_evidence_load_rejects_arrays_that_disagree_with_the_label_lists(tmp_path) -> None:
    path = _corrupted_checkpoint(tmp_path, entity_alpha=np.zeros((3, 5), dtype=np.float32))
    with pytest.raises(ValueError, match="entity_alpha must have shape"):
        EvidenceAccumulator.load(path)

    path = _corrupted_checkpoint(tmp_path, support_weight=np.zeros(3, dtype=np.float64))
    with pytest.raises(ValueError, match="support_weight must have shape"):
        EvidenceAccumulator.load(path)

    path = _corrupted_checkpoint(tmp_path, material_alpha=np.full((3, 2), np.nan, dtype=np.float32))
    with pytest.raises(ValueError, match="finite non-negative"):
        EvidenceAccumulator.load(path)


def _reference_update(evidence: EvidenceAccumulator, association, observation_quality, entity, material, attributes):
    """Straightforward per observation accumulation, in double precision."""
    probability = association.probabilities / association.probabilities.sum(axis=1, keepdims=True)
    base = np.prod(
        np.stack(
            [
                observation_quality.registration,
                observation_quality.geometry,
                observation_quality.resolution,
                observation_quality.incidence,
                observation_quality.visibility,
                observation_quality.independence,
            ]
        ),
        axis=0,
    )
    entity_weight = base * categorical_information(entity)
    material_weight = base * categorical_information(material)
    attribute_weight = base[:, None] * np.abs(2.0 * attributes - 1.0)
    totals = {
        "entity_alpha": np.array(evidence.entity_alpha, dtype=np.float64),
        "material_alpha": np.array(evidence.material_alpha, dtype=np.float64),
        "attribute_alpha": np.array(evidence.attribute_alpha, dtype=np.float64),
        "attribute_beta": np.array(evidence.attribute_beta, dtype=np.float64),
        "support_weight": np.array(evidence.support_weight, dtype=np.float64),
    }
    counts = np.array(evidence.observation_count, dtype=np.int64)
    for row in range(len(entity)):
        for candidate in range(association.surface_indices.shape[1]):
            surface = int(association.surface_indices[row, candidate])
            share = probability[row, candidate]
            totals["entity_alpha"][surface] += entity[row] * entity_weight[row] * share
            totals["material_alpha"][surface] += material[row] * material_weight[row] * share
            totals["attribute_alpha"][surface] += attribute_weight[row] * attributes[row] * share
            totals["attribute_beta"][surface] += attribute_weight[row] * (1.0 - attributes[row]) * share
            totals["support_weight"][surface] += base[row] * share
            counts[surface] += share > 0.0
    return totals, counts


def test_update_matches_a_direct_per_observation_accumulation() -> None:
    rng = np.random.default_rng(19)
    surfaces, rows, candidates, entities, materials, attributes = 40, 250, 3, 7, 4, 3
    association = SoftAssociation(
        rng.integers(0, surfaces, (rows, candidates)),
        rng.random((rows, candidates)),
    )
    observation_quality = ObservationQuality(*[rng.random(rows) for _ in range(6)])
    entity = rng.random((rows, entities))
    entity /= entity.sum(axis=1, keepdims=True)
    material = rng.random((rows, materials))
    material /= material.sum(axis=1, keepdims=True)
    attribute = rng.random((rows, attributes))

    evidence = EvidenceAccumulator(
        surfaces,
        [f"e{index}" for index in range(entities)],
        [f"m{index}" for index in range(materials)],
        [f"a{index}" for index in range(attributes)],
    )
    expected, counts = _reference_update(evidence, association, observation_quality, entity, material, attribute)
    evidence.update(association, observation_quality, entity, material, attribute)

    for name, reference in expected.items():
        actual = getattr(evidence, name)
        assert actual.dtype == np.float32
        np.testing.assert_allclose(actual, reference, rtol=1e-5, atol=1e-6)
    np.testing.assert_array_equal(evidence.observation_count, counts.astype(np.uint32))


def test_zero_probability_candidates_are_dropped_without_changing_the_posterior() -> None:
    rng = np.random.default_rng(23)
    rows = 64
    entity = rng.random((rows, 3))
    entity /= entity.sum(axis=1, keepdims=True)
    material = rng.random((rows, 2))
    material /= material.sum(axis=1, keepdims=True)
    attribute = rng.random((rows, 2))
    probabilities = rng.random((rows, 2))
    probabilities[:, 1] = 0.0

    dense = EvidenceAccumulator(9, ["a", "b", "c"], ["x", "y"], ["p", "q"])
    sparse_only = EvidenceAccumulator(9, ["a", "b", "c"], ["x", "y"], ["p", "q"])
    indices = rng.integers(0, 9, (rows, 2))
    dense.update(SoftAssociation(indices, probabilities), quality(rows), entity, material, attribute)
    sparse_only.update(
        SoftAssociation(indices[:, :1], probabilities[:, :1]),
        quality(rows),
        entity,
        material,
        attribute,
    )

    np.testing.assert_array_equal(dense.entity_alpha, sparse_only.entity_alpha)
    np.testing.assert_array_equal(dense.observation_count, sparse_only.observation_count)


def test_two_candidates_naming_one_surface_are_counted_twice() -> None:
    evidence = EvidenceAccumulator(2, ["a"], ["x"], ["p"])
    evidence.update(
        SoftAssociation(np.array([[1, 1]]), np.array([[0.5, 0.5]])),
        quality(1),
        np.array([[1.0]]),
        np.array([[1.0]]),
        np.array([[1.0]]),
    )
    assert evidence.observation_count.tolist() == [0, 2]
    assert evidence.support_weight[1] == pytest.approx(1.0)


def test_row_blocked_scatter_matches_the_single_threaded_result_bit_for_bit(monkeypatch) -> None:
    rng = np.random.default_rng(29)
    surfaces, rows, candidates = 300, 4000, 3
    association = SoftAssociation(
        rng.integers(0, surfaces, (rows, candidates)),
        rng.random((rows, candidates)),
    )
    observation_quality = ObservationQuality(*[rng.random(rows) for _ in range(6)])
    entity = rng.random((rows, 6))
    entity /= entity.sum(axis=1, keepdims=True)
    material = rng.random((rows, 3))
    material /= material.sum(axis=1, keepdims=True)
    attribute = rng.random((rows, 2))
    labels = (["e0", "e1", "e2", "e3", "e4", "e5"], ["m0", "m1", "m2"], ["a0", "a1"])

    results = []
    for parallel_entries in (10**12, 1):
        monkeypatch.setattr(evidence_module, "_SCATTER_PARALLEL_ENTRIES", parallel_entries)
        monkeypatch.setattr(evidence_module, "_SCATTER_WORKERS", 1 if parallel_entries > 1 else 4)
        accumulator = EvidenceAccumulator(surfaces, *labels)
        accumulator.update(association, observation_quality, entity, material, attribute)
        results.append(accumulator)

    serial, threaded = results
    for name in ("entity_alpha", "material_alpha", "attribute_alpha", "attribute_beta", "support_weight"):
        np.testing.assert_array_equal(getattr(serial, name), getattr(threaded, name))

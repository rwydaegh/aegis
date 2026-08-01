from __future__ import annotations

import numpy as np

from semantic_twin.evidence import EvidenceAccumulator, ObservationQuality, SoftAssociation, categorical_information


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

from __future__ import annotations

import numpy as np

from compare_mesh_depth import DECISIONS, classify, fit_log_scale


def test_depth_conflict_labels_closer_ml_surface_as_front_blocker() -> None:
    mesh = np.full((20, 20), 20.0, dtype=np.float32)
    ml = np.full((20, 20), 5.0, dtype=np.float32)
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.05, dtype=np.float32)
    decision, _ = classify(mesh, ml, error, labels, scale=1.0)
    assert np.all(decision == DECISIONS["front_blocker"])


def test_scale_fit_recovers_known_metric_factor() -> None:
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.1, dtype=np.float32)
    assert fit_log_scale(np.full((20, 20), 12.0), np.full((20, 20), 3.0), error, labels) == 4.0


def test_second_opinion_inflates_uncertainty_instead_of_creating_false_blocker() -> None:
    mesh = np.full((20, 20), 20.0, dtype=np.float32)
    ml = np.full((20, 20), 5.0, dtype=np.float32)
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.05, dtype=np.float32)
    decision, _ = classify(
        mesh, ml, error, labels, scale=1.0, second_opinion_range=np.full((20, 20), 1000.0), second_opinion_scale=1.0
    )
    assert np.all(decision != DECISIONS["front_blocker"])

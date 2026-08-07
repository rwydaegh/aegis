from __future__ import annotations

import numpy as np
import pytest

from render_fishnet_projection import projection_metrics


def test_projection_metrics_separates_overlap_and_spill() -> None:
    reference = np.array([[True, True, False], [False, True, False]])
    projected = np.array([[True, False, True], [False, True, False]])

    metrics = projection_metrics(reference, projected)

    assert metrics["true_positive_pixels"] == 2
    assert metrics["false_positive_pixels"] == 1
    assert metrics["false_negative_pixels"] == 1
    assert metrics["iou"] == pytest.approx(0.5)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)


def test_projection_metrics_rejects_different_shapes() -> None:
    with pytest.raises(ValueError, match="equal shapes"):
        projection_metrics(np.zeros((2, 2)), np.zeros((3, 2)))

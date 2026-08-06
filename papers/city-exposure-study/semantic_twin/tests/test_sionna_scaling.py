"""Metrics and argument checks for the Sionna scaling study."""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.cli.sionna_scaling import _positive_counts, sample_metrics
from semantic_twin.transport.sionna_forward import TransferSamples


def test_positive_counts_parses_a_unique_sweep() -> None:
    assert _positive_counts("3, 9,27") == (3, 9, 27)


@pytest.mark.parametrize("value", ["", "0,3", "3,3", "-1"])
def test_positive_counts_rejects_invalid_sweeps(value: str) -> None:
    with pytest.raises(Exception):
        _positive_counts(value)


def test_sample_metrics_drops_the_first_timing_but_keeps_all_seed_values() -> None:
    samples = TransferSamples(
        direct=np.ones((3, 2)),
        total=np.array([[1.1, 1.2], [1.2, 1.3], [1.3, 1.4]]),
        seconds=np.array([9.0, 2.0, 4.0]),
    )

    metrics = sample_metrics(samples)

    assert metrics["seconds_mean"] == pytest.approx(5.0)
    assert metrics["seconds_warmed_mean"] == pytest.approx(3.0)
    assert len(metrics["surplus_db_mean"]) == 2
    assert metrics["median_single_seed_sd_db"] > 0.0

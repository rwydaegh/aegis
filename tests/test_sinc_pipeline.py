"""Tests for S_inc computation pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def simple_body():
    vertices = np.array(
        [
            [[0, 0, 0], [0.02, 0, 0], [0.01, 0.02, 0]],
            [[0.02, 0, 0], [0.04, 0, 0], [0.03, 0.02, 0]],
        ],
        dtype=float,
    )
    normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=float)
    centroids = vertices.mean(axis=1)
    areas = np.array([0.0002, 0.0002])
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="test")


@pytest.fixture
def downward_paths():
    return PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([10.0]),
    )


def test_sinc_populated(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert result.sinc is not None
    assert result.sinc.shape == (2,)


def test_sinc_larger_than_sab(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert np.all(result.sinc >= result.sab)


def test_sinc_equals_sab_div_t0_normal_incidence(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial", fresnel=True)
    T0 = SKIN_28GHZ.T0
    np.testing.assert_allclose(result.sinc, result.sab / T0, rtol=0.01)


def test_freq_hz_on_result(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert result.freq_hz == 28e9


def test_freq_hz_override(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial", freq_hz=60e9)
    assert result.freq_hz == 60e9


def test_sab_averaged_always_present(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert result.sab_averaged is not None


def test_sinc_averaged_present(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert result.sinc_averaged is not None


def test_1cm2_none_below_30ghz(simple_body, downward_paths):
    engine = DosimetryEngine(SKIN_28GHZ)
    result = engine.compute(simple_body, downward_paths, mode="spatial")
    assert result.sab_1cm2_averaged is None

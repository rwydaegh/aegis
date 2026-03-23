"""Tests for the skin model resolver."""

import pytest

from aegis.tissue.dielectric import TissueModel


@pytest.mark.slow
def test_itis_returns_tissue_model():
    from aegis.viewer.compute import resolve_skin_model

    tm = resolve_skin_model("itis", 28e9)
    assert isinstance(tm, TissueModel)
    assert tm.freq_hz == 28e9
    assert 10 < tm.eps_r < 25
    assert 15 < tm.sigma < 35


@pytest.mark.slow
def test_christ2021_is_scaled_itis():
    from aegis.viewer.compute import resolve_skin_model

    itis = resolve_skin_model("itis", 28e9)
    christ = resolve_skin_model("christ2021", 28e9)
    assert abs(christ.eps_r - itis.eps_r * 1.2) < 0.01
    assert abs(christ.sigma - itis.sigma * 1.2) < 0.01


def test_christ2025_returns_tissue_model():
    from aegis.viewer.compute import resolve_skin_model

    tm = resolve_skin_model("christ2025", 28e9)
    assert isinstance(tm, TissueModel)
    assert tm.freq_hz == 28e9
    assert 5 < tm.eps_r < 50


def test_nict_returns_tissue_model():
    from aegis.viewer.compute import resolve_skin_model

    tm = resolve_skin_model("nict", 28e9)
    assert isinstance(tm, TissueModel)
    assert tm.freq_hz == 28e9
    assert tm.eps_r > 0
    assert tm.sigma > 0


def test_nict_clamps_outside_range():
    """NICT data runs ~1 MHz to ~100 GHz. Below/above should clamp."""
    from aegis.viewer.compute import resolve_skin_model

    low = resolve_skin_model("nict", 100e3)
    high = resolve_skin_model("nict", 200e9)
    assert low.eps_r > 0
    assert high.eps_r > 0


def test_unknown_model_raises():
    from aegis.viewer.compute import resolve_skin_model

    with pytest.raises(ValueError, match="Unknown skin model"):
        resolve_skin_model("nonexistent", 28e9)


@pytest.mark.slow
def test_frequency_variation():
    """Different frequencies should give different properties."""
    from aegis.viewer.compute import resolve_skin_model

    t1 = resolve_skin_model("itis", 1e9)
    t2 = resolve_skin_model("itis", 60e9)
    assert t1.eps_r != t2.eps_r
    assert t1.sigma != t2.sigma


def test_skin_models_list():
    from aegis.viewer.compute import SKIN_MODELS

    assert len(SKIN_MODELS) == 4
    ids = [m["id"] for m in SKIN_MODELS]
    assert "itis" in ids
    assert "christ2021" in ids
    assert "christ2025" in ids
    assert "nict" in ids
    for m in SKIN_MODELS:
        assert "id" in m
        assert "label" in m

"""Caching contract for the parametric-body viewer path.

These run without smplx/torch (the model load is mocked) so the cache behaviour
is exercised in every environment, including the slim CI job. The viewer re-poses
the body twice per Exposure Lab compute (once for the visible mesh on
/api/parametric-body, once for dose on /api/lab/compute); without caching a pure
source/physics slider edit paid two full SMPL-X forward passes plus two model
loads on every tick. See aegis.geometry.parametric.generate_posed.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.geometry import parametric
from aegis.geometry.mesh import BodyMesh


@pytest.fixture(autouse=True)
def _clear_caches():
    # These tests monkeypatch the loader and seed the module-global caches; clear
    # them before and after so a fake model can never leak into another test
    # (the lru_cache and posed cache outlive a single test, see #pollution).
    parametric._load_cached.cache_clear()
    parametric._POSED_CACHE.clear()
    yield
    parametric._load_cached.cache_clear()
    parametric._POSED_CACHE.clear()


class _FakePB:
    def __init__(self, counter):
        self._counter = counter

    def generate(self, betas, pose=None, name="x"):
        self._counter["gen"] += 1
        return BodyMesh.sphere(radius=0.2, n_subdivisions=1)


def test_generate_posed_caches_identical_inputs(monkeypatch):
    counter = {"gen": 0}
    monkeypatch.setattr(parametric.ParametricBody, "load", staticmethod(lambda *a, **k: _FakePB(counter)))
    parametric._POSED_CACHE.clear()

    betas = np.zeros(10)
    pose = np.zeros(66)
    parametric.generate_posed("smplx", "neutral", betas, pose=pose)
    parametric.generate_posed("smplx", "neutral", betas, pose=pose.copy())  # same bytes -> hit
    assert counter["gen"] == 1, "identical inputs must hit the cache, not re-pose"

    pose2 = pose.copy()
    pose2[3] = 0.5
    parametric.generate_posed("smplx", "neutral", betas, pose=pose2)
    assert counter["gen"] == 2, "a changed pose must re-pose"


def test_generate_posed_distinguishes_gender_and_betas(monkeypatch):
    counter = {"gen": 0}
    monkeypatch.setattr(parametric.ParametricBody, "load", staticmethod(lambda *a, **k: _FakePB(counter)))
    parametric._POSED_CACHE.clear()

    pose = np.zeros(66)
    parametric.generate_posed("smplx", "neutral", np.zeros(10), pose=pose)
    parametric.generate_posed("smplx", "male", np.zeros(10), pose=pose)  # gender differs
    parametric.generate_posed("smplx", "neutral", np.ones(10), pose=pose)  # betas differ
    assert counter["gen"] == 3


def test_posed_cache_is_bounded(monkeypatch):
    counter = {"gen": 0}
    monkeypatch.setattr(parametric.ParametricBody, "load", staticmethod(lambda *a, **k: _FakePB(counter)))
    parametric._POSED_CACHE.clear()
    for i in range(parametric._POSED_CACHE_MAX + 5):
        parametric.generate_posed("smplx", "neutral", np.zeros(10), pose=np.full(66, float(i)))
    assert len(parametric._POSED_CACHE) == parametric._POSED_CACHE_MAX


def test_load_is_cached(monkeypatch):
    """ParametricBody.load must construct the model once per (type, gender)."""
    counter = {"load": 0}

    def fake_smplx(gender, model_path):
        counter["load"] += 1
        return object()

    monkeypatch.setattr(parametric, "_load_smplx", fake_smplx)
    parametric._load_cached.cache_clear()

    parametric.ParametricBody.load("smplx", "neutral")
    parametric.ParametricBody.load("smplx", "neutral")
    assert counter["load"] == 1, "same gender must reuse the constructed model"
    parametric.ParametricBody.load("smplx", "male")
    assert counter["load"] == 2, "a different gender constructs its own model"

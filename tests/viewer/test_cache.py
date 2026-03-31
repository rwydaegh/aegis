"""Tests for the environment disk cache."""

import pytest

from aegis.viewer.cache import EnvironmentCache


@pytest.fixture
def cache(tmp_path):
    return EnvironmentCache(cache_dir=str(tmp_path))


def test_miss_returns_none(cache):
    assert cache.get("osm", 51.0, 3.7, 200, {}) is None


def test_put_then_get(cache):
    data = {"buildings": [{"id": 1}]}
    meta = {"count": 1}
    cache.put("osm", 51.0, 3.7, 200, {}, data, meta)
    result = cache.get("osm", 51.0, 3.7, 200, {})
    assert result is not None
    assert result["data"] == data
    assert result["meta"] == meta


def test_different_options_different_keys(cache):
    data_a = {"buildings": [{"id": 1}]}
    data_b = {"buildings": [{"id": 2}]}
    opts_a = {"detail": True}
    opts_b = {"detail": False}
    cache.put("osm", 51.0, 3.7, 200, opts_a, data_a, {})
    cache.put("osm", 51.0, 3.7, 200, opts_b, data_b, {})
    assert cache.get("osm", 51.0, 3.7, 200, opts_a)["data"] == data_a
    assert cache.get("osm", 51.0, 3.7, 200, opts_b)["data"] == data_b


def test_nearby_coords_same_key(cache):
    """Coordinates within 0.0001 degrees (~10m) should hit the same cache entry."""
    data = {"buildings": []}
    cache.put("osm", 51.04471, 3.72681, 200, {}, data, {})
    result = cache.get("osm", 51.04479, 3.72689, 200, {})
    assert result is not None


def test_clear(cache):
    cache.put("osm", 51.0, 3.7, 200, {}, {"b": []}, {})
    assert cache.get("osm", 51.0, 3.7, 200, {}) is not None
    cache.clear()
    assert cache.get("osm", 51.0, 3.7, 200, {}) is None


def test_cache_dir_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_CACHE_DIR", str(tmp_path / "custom"))
    c = EnvironmentCache()
    c.put("osm", 51.0, 3.7, 200, {}, {"test": True}, {})
    assert (tmp_path / "custom" / "environments").is_dir()

"""Tests for the environment disk cache."""

import pytest

from aegis.viewer.cache import EnvironmentCache


@pytest.fixture
def cache(tmp_path):
    return EnvironmentCache(cache_dir=str(tmp_path))


def _binary_paths(cache, source, lat, lon, radius, options):
    key = cache._key(source, lat, lon, radius, options)
    return cache._dir / f"{key}.bin", cache._dir / f"{key}.meta.json"


def _json_path(cache, source, lat, lon, radius, options):
    return cache._dir / f"{cache._key(source, lat, lon, radius, options)}.json"


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


def test_put_then_get_binary(cache):
    blob = b"\x00\x01\x02hello"
    meta = {"n_triangles": 3}
    cache.put_binary("osm", 51.0, 3.7, 200, {}, blob, meta)
    result = cache.get_binary("osm", 51.0, 3.7, 200, {})
    assert result is not None
    assert result == (blob, meta)


def test_get_returns_none_on_corrupt_json(cache):
    """Truncated JSON file must surface as a cache miss, not a 500."""
    cache.put("osm", 51.0, 3.7, 200, {}, {"data": []}, {"count": 0})
    path = _json_path(cache, "osm", 51.0, 3.7, 200, {})
    assert path.exists()
    path.write_text('{"data": ')  # truncated
    assert cache.get("osm", 51.0, 3.7, 200, {}) is None
    # Corrupt entry should be removed so the next refresh starts clean
    assert not path.exists()


def test_get_binary_returns_none_on_corrupt_meta(cache):
    """Corrupt meta sidecar must surface as a cache miss, not a 500."""
    cache.put_binary("osm", 51.0, 3.7, 200, {}, b"abc", {"x": 1})
    bin_path, meta_path = _binary_paths(cache, "osm", 51.0, 3.7, 200, {})
    assert bin_path.exists()
    assert meta_path.exists()
    meta_path.write_text("{not json")
    assert cache.get_binary("osm", 51.0, 3.7, 200, {}) is None
    # Both files cleaned up so next request refreshes
    assert not bin_path.exists()
    assert not meta_path.exists()


def test_get_binary_returns_none_when_meta_missing(cache):
    """Bin file with no meta (interrupted write before atomic rename) -> miss."""
    cache.put_binary("osm", 51.0, 3.7, 200, {}, b"abc", {"x": 1})
    bin_path, meta_path = _binary_paths(cache, "osm", 51.0, 3.7, 200, {})
    meta_path.unlink()
    assert cache.get_binary("osm", 51.0, 3.7, 200, {}) is None


def test_put_binary_is_atomic(cache, monkeypatch):
    """If write_text on meta fails after bin succeeds, both files are cleaned."""
    cache.put_binary("osm", 51.0, 3.7, 200, {}, b"abc", {"x": 1})
    bin_path, meta_path = _binary_paths(cache, "osm", 51.0, 3.7, 200, {})
    assert bin_path.exists()
    assert meta_path.exists()

    # Force the second atomic write to fail
    original = EnvironmentCache._atomic_write_text

    def _fail_text(path, data):  # pragma: no cover - tested via monkeypatch
        if path.suffix == ".json":
            raise OSError("disk full simulation")
        return original(path, data)

    monkeypatch.setattr(EnvironmentCache, "_atomic_write_text", staticmethod(_fail_text))
    cache.put_binary("osm", 52.0, 4.7, 300, {}, b"xyz", {"y": 2})
    bin_path2, meta_path2 = _binary_paths(cache, "osm", 52.0, 4.7, 300, {})
    # No partial entry left behind
    assert not bin_path2.exists()
    assert not meta_path2.exists()

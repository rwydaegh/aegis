import json

import numpy as np

from aegis.study import mobility
from aegis.study.mobility import decode_polyline, route_walk, sample_population_xy


def test_decode_polyline_known_value():
    # Google's documented example
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(pts) == 3
    np.testing.assert_allclose(pts[0], [38.5, -120.2], atol=1e-4)
    np.testing.assert_allclose(pts[-1], [43.252, -126.453], atol=1e-4)


def test_population_sampling_prefers_dense_cells():
    # 2x2 density raster, all mass in the lower-right cell
    density = np.array([[0.0, 0.0], [0.0, 100.0]])
    rng = np.random.default_rng(0)
    lats, lons = sample_population_xy(density, bounds=(50.0, 51.0, 3.0, 4.0), n=500, rng=rng)
    # the hot cell is the lower-right -> high lon, low lat
    assert np.mean(lons) > 3.5
    assert np.mean(lats) < 50.5


def test_route_walk_uses_cache_and_fake_call(tmp_path, monkeypatch):
    encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    calls = []

    def fake_call(orig, dest, api_key):
        calls.append((orig, dest))
        return {"routes": [{"polyline": {"encodedPolyline": encoded}}]}

    monkeypatch.setattr(mobility, "_call_routes", fake_call)

    orig, dest = (38.5, -120.2), (43.252, -126.453)
    route1 = route_walk(orig, dest, cache_dir=tmp_path, api_key="fake")
    assert len(route1) == 3
    assert len(calls) == 1

    # second call hits the cache, no new network call
    route2 = route_walk(orig, dest, cache_dir=tmp_path, api_key="fake")
    assert route2 == route1
    assert len(calls) == 1

    cached = list(tmp_path.glob("route_*.json"))
    assert len(cached) == 1
    assert len(json.loads(cached[0].read_text())) == 3


def test_route_walk_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_DIRECTIONS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="API key"):
        route_walk((0.0, 0.0), (1.0, 1.0), cache_dir=tmp_path)

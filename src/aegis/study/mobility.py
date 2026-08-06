"""Pedestrian mobility: GHSL population sampling and Google Routes routing.

Origins and destinations are sampled weighted by GHSL population density, routed
with the Google Routes API (computeRoutes) in WALK mode, and decoded to lat/lon
polylines. The legacy Directions API this module used before is no longer
enabled on new Google projects and returns REQUEST_DENIED. Routing is billed
per call, so results are cached on disk keyed by rounded endpoints. The HTTP
call is isolated behind ``_call_routes`` so tests inject a fake.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_API_KEY_ENV = "GOOGLE_DIRECTIONS_API_KEY"
_API_KEY_ENV_FALLBACK = "GOOGLE_API_KEY"


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline to a list of (lat, lon) pairs."""
    coords: list[tuple[float, float]] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        for is_lon in (False, True):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += delta
            else:
                lat += delta
        coords.append((lat * 1e-5, lon * 1e-5))
    return coords


def sample_population_xy(density, bounds, n, rng):
    """Sample n (lat, lon) points weighted by a population density raster.

    Row 0 of ``density`` is the northern (high-latitude) edge, matching the
    standard raster orientation. ``bounds`` is (lat_min, lat_max, lon_min, lon_max).
    """
    density = np.asarray(density, dtype=float)
    lat_min, lat_max, lon_min, lon_max = bounds
    h, w = density.shape
    weights = density.ravel()
    total = weights.sum()
    if total <= 0:
        raise ValueError("density has no positive mass")
    probs = weights / total
    flat_idx = rng.choice(weights.size, size=n, p=probs)
    rows, cols = np.divmod(flat_idx, w)
    # jitter uniformly within each cell
    jr = rng.uniform(0.0, 1.0, size=n)
    jc = rng.uniform(0.0, 1.0, size=n)
    lats = lat_max - (rows + jr) / h * (lat_max - lat_min)
    lons = lon_min + (cols + jc) / w * (lon_max - lon_min)
    return lats, lons


def _cache_key(orig, dest) -> str:
    raw = f"{round(orig[0], 5)},{round(orig[1], 5)}->{round(dest[0], 5)},{round(dest[1], 5)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _call_routes(orig, dest, api_key):  # pragma: no cover - network
    import requests

    body = {
        "origin": {"location": {"latLng": {"latitude": orig[0], "longitude": orig[1]}}},
        "destination": {"location": {"latLng": {"latitude": dest[0], "longitude": dest[1]}}},
        "travelMode": "WALK",
        "polylineQuality": "HIGH_QUALITY",
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
    }
    resp = requests.post(_ROUTES_URL, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def route_walk(orig, dest, cache_dir, api_key=None):
    """Return a decoded (lat, lon) walking route, cached on disk.

    Reads the API key from GOOGLE_DIRECTIONS_API_KEY, then GOOGLE_API_KEY, if
    not given. Raises if no key is available rather than falling back to a
    straight line, which would silently degrade the routing realism.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"route_{_cache_key(orig, dest)}.json"
    if cache_file.exists():
        return [tuple(p) for p in json.loads(cache_file.read_text())]

    key = api_key or os.environ.get(_API_KEY_ENV) or os.environ.get(_API_KEY_ENV_FALLBACK)
    if not key:
        raise RuntimeError(
            f"No Google Routes API key. Set {_API_KEY_ENV} or pass api_key. "
            "Refusing to fall back to straight-line routing."
        )

    payload = _call_routes(orig, dest, key)
    routes = payload.get("routes", [])
    if not routes:
        raise RuntimeError(f"Routes API returned no route: {payload.get('error') or payload}")
    encoded = routes[0]["polyline"]["encodedPolyline"]
    coords = decode_polyline(encoded)
    cache_file.write_text(json.dumps(coords))
    return coords


def load_ghsl_density(path, bounds):  # pragma: no cover - heavy external file
    """Load a GHSL population GeoTIFF and clip to (lat_min, lat_max, lon_min, lon_max).

    Lazy-imports rasterio so the rest of the module works without it.
    """
    try:
        import rasterio
        from rasterio.warp import transform_bounds
        from rasterio.windows import from_bounds
    except ImportError as exc:
        raise ImportError("load_ghsl_density needs rasterio (pip install rasterio) to read the GHSL GeoTIFF.") from exc

    lat_min, lat_max, lon_min, lon_max = bounds
    with rasterio.open(path) as src:
        left, bottom, right, top = transform_bounds("EPSG:4326", src.crs, lon_min, lat_min, lon_max, lat_max)
        window = from_bounds(left, bottom, right, top, transform=src.transform)
        data = src.read(1, window=window)
    return np.asarray(data, dtype=float), bounds

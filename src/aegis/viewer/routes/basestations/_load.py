"""POST /api/basestations/load handler."""

from __future__ import annotations

import logging
import os
import threading

import numpy as np
from flask import jsonify, request

from aegis.viewer.server import scoped_cache_set

from ._data import (
    _cache_origin,
    _list_available_regions,
    load_basestations_for_region,
)
from ._fidelity import _bs_summary
from ._geocode import (
    COUNTRY_TO_REGION,
    _resolve_belgian_region,
    geocode_location,
    reverse_geocode_country,
)

logger = logging.getLogger(__name__)


def _geocode_if_needed(params: dict) -> tuple[dict, tuple | None]:
    """Populate params[lat]/params[lon] by geocoding; return (address, error_response).

    When only a location string is given we forward-geocode. When only lat/lon
    are given and no country, we reverse-geocode for the country code.
    """
    address: dict = {}
    location_str = params.get("location")
    if location_str and not params.get("bbox") and "lat" not in params:
        try:
            lat, lon, address = geocode_location(location_str)
        except ValueError as e:
            return address, (jsonify({"error": str(e)}), 400)
        except Exception as e:
            logger.exception("Geocoding failed for %r", location_str)
            return address, (jsonify({"error": f"Geocoding failed: {e}"}), 502)
        params["lat"] = lat
        params["lon"] = lon
        return address, None

    if "lat" in params and "lon" in params and not params.get("country"):
        try:
            lat = float(params["lat"])
            lon = float(params["lon"])
        except (TypeError, ValueError):
            return address, (jsonify({"error": "lat/lon must be numbers"}), 400)
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return address, (
                jsonify({"error": "lat must be in [-90,90] and lon in [-180,180]"}),
                400,
            )
        try:
            address = reverse_geocode_country(lat, lon)
        except Exception as e:
            logger.warning("Reverse geocoding failed for (%s, %s): %s", lat, lon, e)
            return address, (
                jsonify(
                    {
                        "error": (
                            f"Could not determine country for coordinates ({lat}, {lon}). "
                            "Provide an explicit 'country' parameter."
                        )
                    }
                ),
                502,
            )
    return address, None


def _build_bbox(params: dict):
    """Build [lon_min, lon_max, lat_min, lat_max] from explicit bbox or lat+radius."""
    bbox = params.get("bbox")
    if bbox is not None or "lat" not in params or "lon" not in params:
        return bbox, None

    lat = float(params["lat"])
    lon = float(params["lon"])
    radius_m = float(params.get("radius_m", 500))
    if radius_m <= 0 or radius_m > 50_000:
        return None, (jsonify({"error": "radius_m must be between 0 and 50000"}), 400)
    dlat = radius_m / 111_320.0
    cos_lat = np.cos(np.radians(lat))
    if cos_lat < 1e-3:
        return None, (jsonify({"error": "lat too close to poles for bbox computation"}), 400)
    dlon = radius_m / (111_320.0 * cos_lat)
    return [lon - dlon, lon + dlon, lat - dlat, lat + dlat], None


def _resolve_country_and_region(params: dict, address: dict, cache: dict, cache_lock):
    """Return ``(country, region, early_response)`` — early_response set for unknown country."""
    country = params.get("country") or address.get("country", "Belgium")
    region = params.get("region")

    country_code = address.get("country_code", "").lower()
    if country_code in COUNTRY_TO_REGION:
        country = country_code

    if region is None and country.strip().lower() == "belgium":
        if "lat" in params and "lon" in params:
            region = _resolve_belgian_region(address, float(params["lat"]), float(params["lon"]))
            logger.info("Resolved Belgian region: %s", region)
        else:
            region = "brussels"
    elif region is None:
        region = COUNTRY_TO_REGION.get(country.strip().lower())
        if region is None:
            with cache_lock:
                scoped_cache_set(cache, "basestations", [])
            return country, None, jsonify({"count": 0, "basestations": []})
    return country, region, None


def _handle_basestations_load(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/load."""
    params = request.get_json(silent=True) or {}

    address, err = _geocode_if_needed(params)
    if err is not None:
        return err

    bbox, err = _build_bbox(params)
    if err is not None:
        return err

    country, region, early = _resolve_country_and_region(params, address, cache, cache_lock)
    if early is not None:
        return early

    data_dir = os.environ.get("AEGIS_DATA_DIR", "data")
    try:
        basestations = load_basestations_for_region(data_dir, region, country, bbox, params)
    except ImportError:
        available = _list_available_regions(data_dir)
        hint = f"Available regions: {', '.join(sorted(available))}" if available else "No base station data files found"
        return jsonify({"error": f"No base station data for region '{region}'. {hint}"}), 400
    except Exception as exc:
        logger.exception("Failed to load basestations")
        return jsonify({"error": f"Loading failed: {exc}"}), 500

    with cache_lock:
        scoped_cache_set(cache, "basestations", basestations)
        _cache_origin(cache, bbox, params, basestations)

    return jsonify(
        {
            "count": len(basestations),
            "basestations": [_bs_summary(bs) for bs in basestations],
        }
    )

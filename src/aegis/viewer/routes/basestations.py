"""Base station routes: load, list, and compute dosimetry from cell towers."""

from __future__ import annotations

import logging
import os
import re
import threading

import numpy as np
from flask import Flask, Response, jsonify, request

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"


def _list_available_regions(data_dir: str) -> list[str]:
    """Return region names that have Parquet or CSV data files."""
    regions: set[str] = set()
    # Check merged Parquet files
    merged_dir = os.path.join(data_dir, "basestations", "merged")
    if os.path.isdir(merged_dir):
        for f in os.listdir(merged_dir):
            if f.endswith(".parquet"):
                regions.add(f[:-8])  # strip .parquet
    # Check CSV files (backwards compat)
    bs_dir = os.path.join(data_dir, "basestations")
    if os.path.isdir(bs_dir):
        for f in os.listdir(bs_dir):
            if f.endswith(".csv"):
                regions.add(f[:-4])
    return sorted(regions)


_ISO3166_TO_REGION = {
    "BE-VLG": "flanders",
    "BE-BRU": "brussels",
    "BE-WAL": "wallonia",
}


def geocode_location(location: str) -> tuple[float, float, dict]:
    """Geocode a location string to (latitude, longitude, address_details).

    Tries parsing as "lat, lon" first (returns empty address dict),
    falls back to geopy Nominatim with address details.
    Raises ValueError on failure.
    """
    match = re.match(
        r"^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$",
        location,
    )
    if match:
        return float(match.group(1)), float(match.group(2)), {}

    from geopy.exc import GeopyError
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="aegis-viewer", timeout=10)
    try:
        result = geolocator.geocode(location, addressdetails=True)
    except GeopyError as e:
        raise ValueError(f"Geocoding service unavailable: {e}") from e

    if result is None:
        raise ValueError(f"Could not geocode location: {location!r}")
    address = result.raw.get("address", {})
    return result.latitude, result.longitude, address


def _resolve_belgian_region(address: dict, lat: float, lon: float) -> str:
    """Determine the Belgian region from Nominatim address or coordinates.

    Uses ISO 3166-2 level 4 code from Nominatim (authoritative), with a
    coordinate-based fallback for raw lat/lon input without address data.
    """
    iso_code = address.get("ISO3166-2-lvl4", "")
    region = _ISO3166_TO_REGION.get(iso_code)
    if region:
        return region

    # Fallback: coordinate heuristic for raw lat/lon input
    if 50.79 <= lat <= 50.92 and 4.24 <= lon <= 4.49:
        return "brussels"
    if lat >= 50.75:
        return "flanders"
    return "wallonia"


def _handle_basestations_load(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/load."""
    from aegis.basestation.adapter import load_basestations_from_csv

    params = request.get_json(silent=True) or {}

    address = {}
    location_str = params.get("location")
    if location_str and not params.get("bbox") and "lat" not in params:
        try:
            lat, lon, address = geocode_location(location_str)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Geocoding failed for %r", location_str)
            return jsonify({"error": f"Geocoding failed: {e}"}), 502
        params["lat"] = lat
        params["lon"] = lon

    # Build bbox from lat/lon/radius or use explicit bbox
    bbox = params.get("bbox")
    if bbox is None and "lat" in params and "lon" in params:
        lat = float(params["lat"])
        lon = float(params["lon"])
        radius_m = float(params.get("radius_m", 500))
        if radius_m <= 0 or radius_m > 50_000:
            return jsonify({"error": "radius_m must be between 0 and 50000"}), 400
        dlat = radius_m / 111_320.0
        cos_lat = np.cos(np.radians(lat))
        if cos_lat < 1e-3:
            return jsonify({"error": "lat too close to poles for bbox computation"}), 400
        dlon = radius_m / (111_320.0 * cos_lat)
        bbox = [lon - dlon, lon + dlon, lat - dlat, lat + dlat]

    # Resolve country from geocoded address if not explicitly provided
    country = params.get("country")
    if country is None:
        country = address.get("country", "Belgium")
    region = params.get("region")

    # Map country name or code to region name for Parquet lookup
    _COUNTRY_TO_REGION: dict[str, str] = {
        "netherlands": "netherlands",
        "nederland": "netherlands",
        "nl": "netherlands",
        "germany": "germany",
        "deutschland": "germany",
        "de": "germany",
        "austria": "austria",
        "österreich": "austria",
        "at": "austria",
        "australia": "australia",
        "au": "australia",
        "france": "france",
        "fr": "france",
        "denmark": "denmark",
        "danmark": "denmark",
        "dk": "denmark",
    }
    # Also resolve from country_code if available
    country_code = address.get("country_code", "").lower()
    if country_code in _COUNTRY_TO_REGION:
        country = country_code

    if region is None and country.strip().lower() == "belgium":
        if "lat" in params and "lon" in params:
            region = _resolve_belgian_region(address, float(params["lat"]), float(params["lon"]))
            logger.info("Resolved Belgian region: %s", region)
        else:
            region = "brussels"
    elif region is None:
        region = _COUNTRY_TO_REGION.get(country.strip().lower(), "")

    # Try merged Parquet first (fast, with provenance), then CSV, then API
    data_dir = os.environ.get("AEGIS_DATA_DIR", "data")
    parquet_path = None
    parquet_name = f"{region}.parquet" if region else "brussels.parquet"
    for candidate in [
        os.path.join(data_dir, "basestations", "merged", parquet_name),
    ]:
        if os.path.exists(candidate):
            parquet_path = candidate
            break

    csv_path = None
    csv_name = f"{region}.csv" if region else "brussels.csv"
    for candidate in [
        os.path.join(data_dir, "basestations", csv_name),
        f"data/basestations/{csv_name}",
    ]:
        if os.path.exists(candidate):
            csv_path = candidate
            break

    try:
        if parquet_path:
            from aegis.basestation.adapter import load_basestations_from_parquet

            basestations = load_basestations_from_parquet(
                parquet_path,
                bbox=bbox,
                operator=params.get("operator"),
                technology=params.get("technology"),
                frequency_band=params.get("frequency_band"),
            )
        elif csv_path:
            basestations = load_basestations_from_csv(
                csv_path,
                bbox=bbox,
                operator=params.get("operator"),
                technology=params.get("technology"),
            )
        else:
            from aegis.basestation.adapter import load_basestations

            basestations = load_basestations(
                country=country,
                region=region,
                bbox=bbox,
                operator=params.get("operator"),
                technology=params.get("technology"),
                max_workers=int(params.get("max_workers", 4)),
            )
    except ImportError:
        available = _list_available_regions(data_dir)
        hint = f"Available regions: {', '.join(sorted(available))}" if available else "No base station data files found"
        return jsonify({"error": f"No base station data for region '{region}'. {hint}"}), 400
    except Exception as exc:
        logger.exception("Failed to load basestations")
        return jsonify({"error": f"Loading failed: {exc}"}), 500

    # Store in cache
    with cache_lock:
        cache["basestations"] = basestations
        if bbox and len(bbox) == 4:
            cache["basestations_origin"] = (
                (bbox[2] + bbox[3]) / 2,
                (bbox[0] + bbox[1]) / 2,
            )
        elif "lat" in params and "lon" in params:
            cache["basestations_origin"] = (
                float(params["lat"]),
                float(params["lon"]),
            )

    return jsonify(
        {
            "count": len(basestations),
            "basestations": [_bs_summary(bs) for bs in basestations],
        }
    )


def _handle_basestations_compute(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/compute."""
    from aegis.basestation.adapter import paths_from_basestations
    from aegis.basestation.classify import classify_basestation
    from aegis.basestation.power import ExposureMode
    from aegis.engine import DosimetryEngine
    from aegis.viewer.compute import _transform_body_for_viewer, resolve_skin_model
    from aegis.viewer.routes.compute import (
        _build_binary_response,
        _build_stats_response,
        _inject_curvature_H,
        _json_dumps_safe,
        _parse_rotation_y,
        _parse_vec3,
    )

    with cache_lock:
        basestations = cache.get("basestations", [])
        origin = cache.get("basestations_origin")
        body = cache.get("body")

    if not basestations:
        return jsonify({"error": "No base stations loaded"}), 400
    if body is None:
        return jsonify({"error": "No body mesh loaded"}), 400
    if origin is None:
        return jsonify({"error": "No scene origin set"}), 400

    params = request.get_json(silent=True) or {}

    # Filter by indices
    indices = params.get("indices")
    selected = basestations
    if indices is not None:
        if not isinstance(indices, list):
            return jsonify({"error": "'indices' must be a list of integers"}), 400
        try:
            indices = [int(i) for i in indices]
        except (TypeError, ValueError):
            return jsonify({"error": "'indices' must contain only integers"}), 400
        selected = [basestations[i] for i in indices if 0 <= i < len(basestations)]
    if not selected:
        return jsonify({"error": "No base stations selected"}), 400

    # Body offset and rotation
    body_offset, err = _parse_vec3(params, "body_offset", [0, 0, 0])
    if err:
        return err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err

    # Transform body by offset + rotation (same as /api/dosimetry)
    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = np.mean(transformed_body.centroids, axis=0)

    # Exposure mode
    exposure_mode_str = params.get("exposure_mode", "theoretical")
    try:
        exposure_mode = ExposureMode(exposure_mode_str)
    except ValueError:
        return jsonify({"error": f"Invalid exposure_mode: {exposure_mode_str!r}"}), 400

    # Build per-station ExposureConfig from classification
    exposure_configs = []
    for bs in selected:
        cls = classify_basestation(
            gain_dbi=bs.gain_dbi,
            technology=bs.technology,
            freq_mhz=bs.freq_mhz,
            h_bw=bs.horizontal_beamwidth_deg or 0,
            v_bw=bs.vertical_beamwidth_deg or 0,
        )
        exposure_configs.append(cls["exposure_config"])

    # Compute paths
    try:
        max_distance_m = float(params.get("max_distance_m", 2000))
    except (TypeError, ValueError):
        return jsonify({"error": "max_distance_m must be a number"}), 400
    if max_distance_m <= 0:
        return jsonify({"error": "max_distance_m must be positive"}), 400
    paths = paths_from_basestations(
        selected,
        body_center,
        origin,
        max_distance_m=max_distance_m,
        exposure_mode=exposure_mode,
        exposure_configs=exposure_configs,
    )

    if paths.n_paths == 0 or paths.total_power <= 0:
        # Return zero result
        n_tri = body.n_triangles
        sab_bytes = np.zeros(n_tri, dtype=np.float32).tobytes()
        stats = {
            "p_abs": 0,
            "p_abs_mw": 0,
            "peak_sab": 0,
            "n_illuminated": 0,
            "n_triangles": n_tri,
            "n_basestations": len(selected),
            "n_paths": 0,
            "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
            "peaks": {"sab": 0.0},
        }
        resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    # EIRP-weighted average frequency for tissue model
    freq_hz = params.get("freq_hz")
    if freq_hz is None:
        total_eirp_w = sum(10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected)
        if total_eirp_w > 0:
            freq_hz = sum(bs.freq_hz * 10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected) / total_eirp_w
        else:
            freq_hz = 3.5e9
    freq_hz = float(freq_hz)

    skin_model = params.get("skin_model", "itis")
    tissue = resolve_skin_model(skin_model, freq_hz)

    # Dosimetry engine
    engine = DosimetryEngine(tissue)
    mode = params.get("mode", "spatial")
    engine_kw = {"mode": mode, "spatial_averaging": True}
    engine_kw = _inject_curvature_H(engine_kw, transformed_body)

    result = engine.compute(transformed_body, paths, **engine_kw)

    # Build response using existing format
    quantities = params.get("quantities", ["sab", "sab_4cm2"])
    buf, arrays_meta = _build_binary_response(result, quantities)

    level, mode_str, corrections = None, mode, []
    stats = _build_stats_response(
        result,
        transformed_body,
        tissue,
        level,
        mode=mode_str,
        corrections=corrections,
        extra={
            "n_basestations": len(selected),
            "n_paths": paths.n_paths,
            "freq_hz": freq_hz,
            "total_power_w_m2": float(paths.total_power),
            "arrays": arrays_meta,
        },
    )

    resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def _handle_basestations_compute_mimo(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/compute_mimo."""
    from aegis.basestation.classify import classify_antenna, infer_element_grid
    from aegis.basestation.coords import wgs84_to_enu
    from aegis.constants import C_0
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.compute import compute_mimo_scene_with_bodies
    from aegis.mimo.scene import MIMOScene
    from aegis.mimo.user import UserConfig, UserState
    from aegis.viewer.routes.compute import _json_dumps_safe, _parse_rotation_y, _parse_vec3

    params = request.get_json(silent=True) or {}

    # Validate index
    with cache_lock:
        basestations = cache.get("basestations", [])
        origin = cache.get("basestations_origin")
        body = cache.get("body")
        bodies_cache = cache.get("bodies", {})

    index = params.get("index")
    if index is None:
        return jsonify({"error": "Missing 'index' in request"}), 400
    try:
        index = int(index)
    except (TypeError, ValueError):
        return jsonify({"error": "'index' must be an integer"}), 400
    if index < 0 or index >= len(basestations):
        return jsonify({"error": f"Index {index} out of range [0, {len(basestations)})"}), 400

    bs = basestations[index]

    # Classify and validate mMIMO
    archetype = classify_antenna(
        gain_dbi=bs.gain_dbi,
        technology=bs.technology,
        freq_mhz=bs.freq_mhz,
        h_bw=bs.horizontal_beamwidth_deg or 0,
        v_bw=bs.vertical_beamwidth_deg or 0,
    )
    if archetype != "mmimo":
        return jsonify({"error": f"Base station {index} is classified as '{archetype}', not 'mmimo'"}), 400

    if body is None:
        return jsonify({"error": "No body mesh loaded"}), 404
    if origin is None:
        return jsonify({"error": "No scene origin set"}), 400

    # Parse body transform
    body_offset, err = _parse_vec3(params, "body_offset", [0, 0, 0])
    if err:
        return err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err

    try:
        level = int(params.get("level", 7))
    except (TypeError, ValueError):
        return jsonify({"error": "level must be an integer"}), 400
    if level not in (7, 8):
        return jsonify({"error": "level must be 7 or 8 for MIMO"}), 400
    precoder_type = str(params.get("precoder_type", "mrt"))

    # Infer element grid
    n_h, n_v = infer_element_grid(archetype, bs.gain_dbi)

    # Compute antenna position in ENU
    lat0, lon0 = origin
    ant_pos = wgs84_to_enu(bs.latitude, bs.longitude, 0.0, lat0, lon0)
    ant_pos[2] = bs.height_m

    # Compute broadside direction from azimuth and tilt in ENU
    az_rad = np.deg2rad(bs.azimuth_deg)
    tilt_rad = np.deg2rad(bs.total_tilt_deg)
    broadside = np.array(
        [
            np.sin(az_rad) * np.cos(tilt_rad),
            np.cos(az_rad) * np.cos(tilt_rad),
            -np.sin(tilt_rad),
        ],
        dtype=np.float64,
    )

    # Half-wavelength spacing
    freq_hz = bs.freq_hz
    wavelength = C_0 / freq_hz
    spacing = wavelength / 2.0

    # Build AntennaArray
    try:
        array = AntennaArray.upa(
            n_h=n_h,
            n_v=n_v,
            d_h=spacing,
            d_v=spacing,
            center=ant_pos,
            broadside=broadside,
            element_pattern="patch",
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Failed to build antenna array: {exc}"}), 400

    # Total power from EIRP (convert dBm to watts)
    total_power = 10 ** ((bs.eirp_dbm - 30) / 10)

    # Find phantom name from cache
    phantom_name = cache.get("default_body", "thelonious")
    if phantom_name not in bodies_cache:
        # Try any available phantom
        if bodies_cache:
            phantom_name = next(iter(bodies_cache))
        else:
            return jsonify({"error": "No phantom loaded"}), 404

    # Create user at body_offset with device near the body
    default_offset = cache.get("body_device_offsets", {}).get(phantom_name, [0.0, 0.30, 1.4])
    device_offset = np.array(default_offset, dtype=np.float64)
    # Rotate device offset by body orientation (Z-axis rotation)
    cos_o, sin_o = np.cos(body_rotation_y), np.sin(body_rotation_y)
    rotated_offset = np.array(
        [
            cos_o * device_offset[0] - sin_o * device_offset[1],
            sin_o * device_offset[0] + cos_o * device_offset[1],
            device_offset[2],
        ]
    )
    user_cfg = UserConfig(
        user_id="bs_mimo_user",
        phantom_name=phantom_name,
        position=body_offset,
        device_position=body_offset + rotated_offset,
        device_orientation=np.array([0.0, 0.0, 1.0]),
        orientation=float(body_rotation_y),
    )
    user = UserState(config=user_cfg)

    scene = MIMOScene(
        array=array,
        users=[user],
        freq_hz=freq_hz,
        total_power=total_power,
    )

    # Resolve body meshes
    bodies = {name: entry["body"] for name, entry in bodies_cache.items()}

    try:
        summary = compute_mimo_scene_with_bodies(
            scene,
            bodies,
            level=level,
            precoder_type=precoder_type,
        )
    except Exception as exc:
        logger.exception("mMIMO compute failed for base station %d", index)
        return jsonify({"error": f"MIMO compute failed: {exc}"}), 500

    # Build binary response from user result
    sab_data = user._sab_raw
    if sab_data is None:
        n_tri = body.n_triangles
        sab_bytes = np.zeros(n_tri, dtype=np.float32).tobytes()
        peak_sab = 0.0
        p_abs = 0.0
    else:
        sab_f32 = sab_data.astype(np.float32)
        sab_bytes = sab_f32.tobytes()
        peak_sab = float(np.max(sab_f32))
        p_abs = float(user.result.p_abs) if user.result else 0.0

    n_tri = len(sab_data) if sab_data is not None else body.n_triangles
    stats = {
        "p_abs": p_abs,
        "p_abs_mw": p_abs * 1e3,
        "peak_sab": peak_sab,
        "n_triangles": n_tri,
        "n_elements": array.n_elements,
        "n_h": n_h,
        "n_v": n_v,
        "archetype": archetype,
        "freq_hz": freq_hz,
        "level": level,
        "precoder_type": precoder_type,
        "total_power_w": total_power,
        "base_station_index": index,
        "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
        "peaks": {"sab": peak_sab},
        "timings": summary.get("timings", {}),
    }

    resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register base station API routes."""

    @app.route("/api/basestations/load", methods=["POST"])
    def api_basestations_load():
        """Load base stations from basestationLib for a given area."""
        return _handle_basestations_load(cache, cache_lock)

    @app.route("/api/basestations/list")
    def api_basestations_list():
        """List currently loaded base stations."""
        with cache_lock:
            basestations = cache.get("basestations", [])

        return jsonify(
            {
                "count": len(basestations),
                "basestations": [_bs_summary(bs) for bs in basestations],
            }
        )

    @app.route("/api/basestations/compute", methods=["POST"])
    def api_basestations_compute():
        """Compute dosimetry from loaded base stations."""
        return _handle_basestations_compute(cache, cache_lock)

    @app.route("/api/basestations/compute_mimo", methods=["POST"])
    def api_basestations_compute_mimo():
        """Compute coherent MIMO dosimetry for an mMIMO base station."""
        return _handle_basestations_compute_mimo(cache, cache_lock)


def _bs_summary(bs) -> dict:
    """Serialize a BaseStation to a JSON-safe dict with classification."""
    from aegis.basestation.classify import classify_basestation
    from aegis.basestation.provenance import aggregate_confidence

    classification = classify_basestation(
        gain_dbi=bs.gain_dbi,
        technology=bs.technology,
        freq_mhz=bs.freq_mhz,
        h_bw=bs.horizontal_beamwidth_deg or 0,
        v_bw=bs.vertical_beamwidth_deg or 0,
    )
    # Serialize ExposureConfig fields (dataclass, not JSON-serializable)
    exp = classification.pop("exposure_config")
    classification["duplex_mode"] = exp.duplex_mode
    classification["tdd_dl_ratio"] = exp.tdd_dl_ratio
    classification["power_reduction_factor"] = exp.power_reduction_factor
    classification["traffic_load_factor"] = exp.traffic_load_factor
    # Remove beam_config (not JSON-serializable as-is)
    classification.pop("beam_config", None)

    prov_dict = bs.provenance_dict
    return {
        "site_code": bs.site_code,
        "antenna_label": bs.antenna_label,
        "operator": bs.operator,
        "technology": bs.technology,
        "latitude": bs.latitude,
        "longitude": bs.longitude,
        "height_m": bs.height_m,
        "eirp_dbm": bs.eirp_dbm,
        "gain_dbi": bs.gain_dbi,
        "freq_mhz": bs.freq_mhz,
        "azimuth_deg": bs.azimuth_deg,
        "total_tilt_deg": bs.total_tilt_deg,
        "has_pattern": bs.pattern is not None,
        "horizontal_beamwidth_deg": bs.horizontal_beamwidth_deg,
        "vertical_beamwidth_deg": bs.vertical_beamwidth_deg,
        "frequency_band": bs.frequency_band,
        "pattern_source": bs.pattern_source,
        "confidence": aggregate_confidence(bs.provenance),
        "provenance": {k: {"origin": v.origin, "confidence": v.confidence} for k, v in prov_dict.items()},
        **classification,
    }

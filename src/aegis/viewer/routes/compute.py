"""Compute routes: dosimetry, ray tracing, voxel RT."""

from __future__ import annotations

import json
import logging

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.compliance import ExposureScenario, evaluate_compliance
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.viewer.compute import _load_phantom_masses

logger = logging.getLogger(__name__)

# String constants (avoid duplicate literals)
_OCTET_STREAM = "application/octet-stream"
_ERR_NO_BODY = "No body mesh loaded"
_ERR_NO_DIFFERT = "DiffeRT not installed"
_ERR_VEC3_LEN = "must be a 3-element array [x, y, z]"
_ERR_VEC3_TYPE = "must be a 3-element numeric array"
_ERR_INVALID_JSON = "Invalid or missing JSON body"
_ERR_ROTATION_TYPE = "body_rotation_y must be a number"


def _inject_curvature_H(engine_kw: dict, body) -> dict:
    """Add curvature_H to engine kwargs if curvature or diffraction is requested."""
    if engine_kw.get("curvature") or engine_kw.get("diffraction"):
        from aegis.viewer.compute import _compute_face_curvature

        engine_kw["curvature_H"] = _compute_face_curvature(body)
    return engine_kw


def _parse_vec3(params: dict, key: str, default: list | None = None):
    """Parse a 3-element numeric array from request params.

    Returns (np.ndarray, None) on success or (None, error_response) on failure.
    """
    default = default or [0, 0, 0]
    try:
        raw = list(params.get(key, default))
        if len(raw) != 3:
            return None, (jsonify({"error": f"{key} {_ERR_VEC3_LEN}"}), 400)
        return np.array([float(v) for v in raw], dtype=np.float64), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{key} {_ERR_VEC3_TYPE}"}), 400)


def _parse_rotation_y(params: dict):
    """Parse body_rotation_y from request params.

    Returns (float, None) on success or (None, error_response) on failure.
    """
    try:
        return float(params.get("body_rotation_y", 0.0)), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": _ERR_ROTATION_TYPE}), 400)


def _parse_freq_and_tissue(params: dict, default_freq: float = DEFAULT_FREQ_HZ):
    """Parse freq_hz and resolve tissue model from request params.

    Returns (tissue, freq_hz, None) on success or (None, None, error_response) on failure.
    """
    from aegis.viewer.compute import resolve_skin_model

    try:
        freq_hz = float(params.get("freq_hz", default_freq))
    except (TypeError, ValueError):
        return None, None, (jsonify({"error": "freq_hz must be a number"}), 400)
    if freq_hz <= 0:
        return None, None, (jsonify({"error": "freq_hz must be positive"}), 400)

    skin_model_name = params.get("skin_model", "itis")
    try:
        tissue = resolve_skin_model(skin_model_name, freq_hz)
    except ValueError as exc:
        return None, None, (jsonify({"error": str(exc)}), 400)

    return tissue, freq_hz, None


def _parse_quantities_and_scenario(params: dict):
    """Parse display quantities and exposure scenario from request params.

    Returns (quantities, scenario, None) on success or (None, None, error_response) on failure.
    """
    quantities = params.get("quantities", ["sab", "sab_4cm2"])
    scenario_str = params.get("exposure_scenario", "general_public")
    try:
        scenario = ExposureScenario(scenario_str)
    except ValueError:
        return None, None, (jsonify({"error": f"Invalid exposure_scenario: {scenario_str}"}), 400)
    return quantities, scenario, None


def _run_dosimetry(tissue, body, paths, engine_kw):
    """Instantiate engine, inject curvature, run compute, return result."""
    from aegis.engine import DosimetryEngine

    engine = DosimetryEngine(tissue)
    _inject_curvature_H(engine_kw, body)
    body_mass = _load_phantom_masses().get(body.name) if body.name else None
    return engine.compute(body, paths, body_mass=body_mass, **engine_kw)


def _make_rt_response(result, body, tissue, engine_kw, quantities, scenario, extra, timing_pairs):
    """Build binary Response with X-Stats header for RT route handlers.

    timing_pairs is a list of (key, value) timing entries to inject.
    """
    buf, arrays_meta = _build_binary_response(result, quantities)
    level_val, mode_val, corr_val = _stats_label(engine_kw)
    stats = _build_stats_response(
        result,
        body,
        tissue,
        level_val,
        mode=mode_val,
        corrections=corr_val,
        extra=extra,
        scenario=scenario,
    )
    timings = stats.get("timings", {})
    for key, val in timing_pairs:
        timings[key] = val
    stats["timings"] = timings
    stats["arrays"] = arrays_meta
    resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = json.dumps(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp, stats


def _parse_mode_or_level(params: dict, default_level: int = 2) -> dict:
    """Extract mode+corrections or level from request params.

    Returns a dict with either {'level': int} or {'mode': str, ...corrections}.
    """
    mode = params.get("mode")
    if mode is not None:
        out: dict = {"mode": mode}
        if mode == "spatial":
            out["fresnel"] = bool(params.get("fresnel", True))
            out["polarisation"] = bool(params.get("polarisation", False))
            out["curvature"] = bool(params.get("curvature", False))
            out["diffraction"] = bool(params.get("diffraction", False))
        return out
    level = params.get("level", default_level)
    return {"level": int(level)}


def _stats_label(engine_kwargs: dict) -> tuple:
    """Return (level_int, mode_str, corrections_list) for stats response."""
    if "mode" in engine_kwargs:
        mode = engine_kwargs["mode"]
        corrections = [k for k in ("fresnel", "polarisation", "curvature", "diffraction") if engine_kwargs.get(k)]
        return (None, mode, corrections)
    return (engine_kwargs.get("level", 2), None, [])


def _build_binary_response(result, quantities):
    """Assemble multi-array binary buffer from a DosimetryResult.

    Returns (buf, arrays_meta) where arrays_meta is a list of
    {"key": str, "offset": int, "length": int} dicts describing each array
    in the buffer.
    """
    buf = bytearray()
    arrays_meta = []

    # sab is always included
    sab_arr = result.sab.astype(np.float32)
    sab_bytes = sab_arr.tobytes()
    arrays_meta.append({"key": "sab", "offset": 0, "length": sab_arr.shape[0]})
    buf.extend(sab_bytes)

    quantity_map = {
        "sab_4cm2": lambda: result.sab_averaged,
        "sab_1cm2": lambda: result.sab_1cm2_averaged,
        "sinc_local": lambda: result.sinc,
        "sinc_averaged": lambda: result.sinc_averaged,
    }

    for key in quantities:
        if key == "sab":
            continue  # already included
        getter = quantity_map.get(key)
        if getter is None:
            continue
        arr = getter()
        if arr is None:
            continue
        arr_f32 = arr.astype(np.float32)
        arr_bytes = arr_f32.tobytes()
        arrays_meta.append({"key": key, "offset": len(buf), "length": arr_f32.shape[0]})
        buf.extend(arr_bytes)

    return buf, arrays_meta


def _build_stats_response(result, body, tissue, level, extra=None, mode=None, corrections=None, scenario=None):
    """Build the X-Stats JSON dict from a DosimetryResult."""
    freq_hz = result.freq_hz or tissue.freq_hz
    scenario = scenario or ExposureScenario.GENERAL_PUBLIC

    # Precompute per-quantity peaks (each np.max called once)
    peak_sab_averaged = float(np.max(result.sab_averaged)) if result.sab_averaged is not None else None
    peak_sab_1cm2 = float(np.max(result.sab_1cm2_averaged)) if result.sab_1cm2_averaged is not None else None
    peak_sinc_local = float(np.max(result.sinc)) if result.sinc is not None else None
    peak_sinc_averaged = float(np.max(result.sinc_averaged)) if result.sinc_averaged is not None else None

    # S_inc whole-body average
    sinc_wb = None
    if result.sinc is not None:
        sinc_wb = float(np.sum(result.sinc * body.areas) / np.sum(body.areas))

    try:
        compliance = evaluate_compliance(
            scenario=scenario,
            freq_hz=freq_hz,
            sab_4cm2=peak_sab_averaged,
            sinc_local=peak_sinc_averaged,
            sinc_whole_body=sinc_wb,
            sar_wb=result.sar_wb,
            sab_1cm2=peak_sab_1cm2,
        )
    except ValueError:
        # Frequency outside ICNIRP 2020 range (>6 GHz to 300 GHz)
        compliance = None

    stats = {
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "peak_sab_averaged": peak_sab_averaged,
        "compliance": {
            "overall_pass": compliance.overall_pass,
            "margin_db": compliance.margin_db if compliance.margin_db != float("inf") else None,
            "scenario": scenario.value,
            "freq_hz": freq_hz,
            "checks": [
                {
                    "label": c.label,
                    "value": round(c.value, 4),
                    "limit": round(c.limit, 4),
                    "unit": c.unit,
                    "pass": c.compliant,
                    "ratio": round(c.ratio, 4),
                }
                for c in compliance.all_checks
            ],
        }
        if compliance is not None
        else None,
        "compliant": compliance.overall_pass if compliance is not None else None,
        "warning": "Frequency outside ICNIRP 2020 range (>6 GHz to 300 GHz); compliance not evaluated."
        if compliance is None
        else None,
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level if level is not None else 0,
        "T0": float(tissue.T0),
        "tissue_eps_r": tissue.eps_r,
        "tissue_sigma": tissue.sigma,
    }

    # Per-quantity peak values (reuse precomputed values)
    peaks = {"sab": float(result.peak_sab)}
    if peak_sab_averaged is not None:
        peaks["sab_4cm2"] = peak_sab_averaged
    if peak_sab_1cm2 is not None:
        peaks["sab_1cm2"] = peak_sab_1cm2
    if peak_sinc_local is not None:
        peaks["sinc_local"] = peak_sinc_local
    if peak_sinc_averaged is not None:
        peaks["sinc_averaged"] = peak_sinc_averaged
    stats["peaks"] = peaks

    if mode is not None:
        stats["mode"] = mode
    if corrections:
        stats["corrections"] = corrections
    if extra:
        stats.update(extra)
    return stats


def _zero_paths_response(body, tissue, level, extra=None):
    """Build stats dict when zero paths are found."""
    n_tri = body.n_triangles
    stats = {
        "p_abs": 0,
        "p_abs_mw": 0,
        "peak_sab": 0,
        "compliant": True,
        "n_illuminated": 0,
        "n_triangles": n_tri,
        "level": level,
        "S_inc": 0,
        "distance_m": 0,
        "T0": tissue.T0,
        "n_rt_paths": 0,
        "path_viz": [],
        "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
        "peaks": {"sab": 0.0},
    }
    if extra:
        stats.update(extra)
    sab_bytes = np.zeros(body.n_triangles, dtype=np.float32).tobytes()
    resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = json.dumps(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach compute routes to *app*."""

    def _parse_rt_config(params: dict) -> dict:
        """Extract rt_config from request params, with backward-compatible fallbacks."""
        rt = params.get("rt_config", {})
        if not isinstance(rt, dict):
            rt = {}
        return {
            "max_depth": rt.get("max_depth", params.get("max_order", 3)),
            "method": rt.get("method", "exhaustive"),
            "rays_per_source": rt.get("rays_per_source", 1_000_000),
            "max_paths_per_source": rt.get("max_paths_per_source", 1_000_000),
            "chunk_size": rt.get("chunk_size"),
            "los": rt.get("los", True),
            "specular_reflection": rt.get("specular_reflection", True),
            "diffuse_reflection": rt.get("diffuse_reflection", False),
            "refraction": rt.get("refraction", True),
            "diffraction": rt.get("diffraction", False),
            "edge_diffraction": rt.get("edge_diffraction", False),
            "diffraction_lit_region": rt.get("diffraction_lit_region", True),
            "reflection_loss_per_order": rt.get(
                "reflection_loss_per_order",
                cache["config"]["raytracer"]["reflection_loss_per_order"],
            ),
            "synthetic_array": rt.get("synthetic_array", True),
            "seed": rt.get("seed", 42),
        }

    @app.route("/api/compute", methods=["POST"])
    def api_compute():
        """Compute dosimetry for given antenna position."""
        from aegis.viewer.compute import compute_dosimetry

        params = request.get_json(silent=True)
        if params is None:
            if request.data:
                return jsonify({"error": "Invalid JSON body"}), 400
            params = {}
        elif not isinstance(params, dict):
            return jsonify({"error": "JSON body must be an object"}), 400

        body_name = params.get("body_name", cache.get("default_body"))
        with cache_lock:
            entry = cache.get("bodies", {}).get(body_name)
            cfg = cache["config"]
        if entry is None:
            return jsonify({"error": f"Body '{body_name}' not found"}), 404
        body = entry["body"]

        dcfg = cfg["dosimetry"]
        pwr_cfg = dcfg["power_input"]
        allowed_n_paths = {int(opt["value"]) for opt in dcfg["path_options"]}

        # Accept mode + correction flags (new API) or level (legacy)
        mode = params.get("mode")
        if mode is not None:
            if mode not in ("bound", "aggregate", "spatial"):
                return jsonify({"error": "mode must be one of: bound, aggregate, spatial"}), 400
            if mode == "spatial":
                corrections = {
                    "fresnel": bool(params.get("fresnel", True)),
                    "polarisation": bool(params.get("polarisation", False)),
                    "curvature": bool(params.get("curvature", False)),
                    "diffraction": bool(params.get("diffraction", False)),
                }
            else:
                corrections = None
            level = None
        else:
            try:
                level = int(params.get("level", dcfg["default_level"]))
            except (TypeError, ValueError):
                return jsonify({"error": "level must be an integer"}), 400
            if level not in range(0, 9):
                return jsonify({"error": "level must be between 0 and 8"}), 400
            mode = None
            corrections = None

        try:
            power_dbm = float(params.get("power_dbm", dcfg["default_power_dbm"]))
        except (TypeError, ValueError):
            return jsonify({"error": "power_dbm must be a number"}), 400
        if not (pwr_cfg["min"] <= power_dbm <= pwr_cfg["max"]):
            return jsonify({"error": f"power_dbm must be between {pwr_cfg['min']} and {pwr_cfg['max']} dBm"}), 400

        try:
            n_paths = int(params.get("n_paths", dcfg["default_n_paths"]))
        except (TypeError, ValueError):
            return jsonify({"error": "n_paths must be an integer"}), 400
        if n_paths not in allowed_n_paths:
            return jsonify({"error": f"n_paths must be one of {sorted(allowed_n_paths)}"}), 400

        # Stochastic channel params (optional, overrides n_paths when present)
        stochastic = None
        if params.get("stochastic"):
            stoch_cfg = cfg["dosimetry"].get("stochastic", {})
            try:
                stochastic = {
                    "preset": params.get("stochastic_preset", stoch_cfg.get("default_preset", "3GPP_38.901_UMi_LOS")),
                    "seed": int(params.get("stochastic_seed", stoch_cfg.get("default_seed", 42))),
                    "overrides": params.get("stochastic_overrides", {}),
                    "freq_ghz": float(params.get("freq_hz", DEFAULT_FREQ_HZ)) / 1e9,
                }
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid stochastic parameters (seed must be integer)"}), 400

        tissue, _, err = _parse_freq_and_tissue(params)
        if err:
            return err

        antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
        if err:
            return err
        body_offset, err = _parse_vec3(params, "body_offset")
        if err:
            return err
        body_rotation_y, err = _parse_rotation_y(params)
        if err:
            return err
        quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
        if err:
            return err

        import time as _time

        t_route = _time.perf_counter()

        try:
            result, res_body, res_tissue, res_level, res_mode, res_corr, extra = compute_dosimetry(
                body,
                antenna_pos=antenna_pos,
                body_offset=body_offset,
                body_rotation_y=body_rotation_y,
                level=level,
                mode=mode,
                corrections=corrections,
                tissue=tissue,
                power_dbm=power_dbm,
                n_paths=n_paths,
                config=cfg,
                stochastic=stochastic,
            )
        except Exception as exc:
            logger.exception("compute_dosimetry failed")
            return jsonify({"error": str(exc)}), 500

        t_compute = _time.perf_counter()

        try:
            # Build multi-array binary response and stats header
            buf, arrays_meta = _build_binary_response(result, quantities)
            stats = _build_stats_response(
                result,
                res_body,
                res_tissue,
                res_level,
                mode=res_mode,
                corrections=res_corr,
                extra=extra,
                scenario=exposure_scenario,
            )
        except Exception as exc:
            logger.exception("response build failed")
            return jsonify({"error": str(exc)}), 500

        t_stats = _time.perf_counter()

        # Store compliance result for /api/compliance/summary export
        app.config["_last_compliance_result"] = stats.get("compliance")

        # Inject route-level timings
        timings = extra.get("timings", {})
        timings["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
        timings["route_total_ms"] = (t_stats - t_route) * 1e3
        stats["timings"] = timings
        stats["arrays"] = arrays_meta

        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/scenes")
    def api_scenes():
        """List available Sionna XML scenes for DiffeRT ray tracing."""
        try:
            from aegis.viewer.raytracer import list_available_scenes

            return jsonify(list_available_scenes())
        except ImportError:
            return jsonify({"error": _ERR_NO_DIFFERT}), 501

    @app.route("/api/scene/load", methods=["POST"])
    def api_scene_load():
        """Load a Sionna scene and return its geometry for Three.js."""
        try:
            from aegis.viewer.raytracer import load_scene, scene_geometry_to_binary
        except ImportError:
            return jsonify({"error": _ERR_NO_DIFFERT}), 501

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        scene_path = params.get("path")
        if not scene_path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        try:
            scene_data = load_scene(scene_path)
            data, meta = scene_geometry_to_binary(scene_data)
            resp = Response(data, mimetype=_OCTET_STREAM)
            resp.headers["X-Meta"] = json.dumps(meta)
            resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
            return resp
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/voxels/hull-mesh", methods=["GET"])
    def api_voxels_hull_mesh():
        """Exterior voxel hull as triangle soup (same geometry as voxel DiffeRT)."""
        try:
            from aegis.viewer.raytracer import get_or_build_voxel_scene, scene_geometry_to_binary
        except ImportError:
            return jsonify({"error": _ERR_NO_DIFFERT}), 501

        with cache_lock:
            voxel_positions = cache.get("voxel_positions")
            voxel_sizes = cache.get("voxel_sizes")
            voxel_materials = cache.get("voxel_materials")
            cfg = cache.get("config", {})
        if voxel_positions is None or len(voxel_positions) == 0:
            return jsonify({"error": "No voxel data"}), 400

        from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

        z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
        ext_mask = extract_exterior(grid_coords)
        ext_grid = grid_coords[ext_mask]
        ext_pos = z_up_pos[ext_mask]

        ext_materials = None
        if voxel_materials is not None:
            ext_materials = [voxel_materials[i] for i in np.nonzero(ext_mask)[0]]
        material_colors = cfg.get("voxels", {}).get("material_colors")

        try:
            scene = get_or_build_voxel_scene(
                ext_pos,
                ext_grid,
                voxel_size=vs,
                materials=ext_materials,
                material_colors=material_colors,
            )
            mesh = scene.mesh
            vertices = np.array(mesh.vertices)
            triangles = np.array(mesh.triangles)
            mnames = list(mesh.material_names) if mesh.material_names else []
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        scene_data = {
            "vertices": vertices,
            "triangles": triangles,
            "face_colors": np.array(mesh.face_colors),
            "n_vertices": int(len(vertices)),
            "n_triangles": int(len(triangles)),
            "material_names": mnames,
        }
        data, meta = scene_geometry_to_binary(scene_data)
        resp = Response(data, mimetype=_OCTET_STREAM)
        resp.headers["X-Meta"] = json.dumps(meta)
        resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
        return resp

    @app.route("/api/compute/rt", methods=["POST"])
    def api_compute_rt():
        """Compute dosimetry using DiffeRT ray-traced paths."""
        try:
            from aegis.viewer.raytracer import compute_paths_differt
        except ImportError:
            return jsonify({"error": _ERR_NO_DIFFERT}), 501

        from aegis.viewer.compute import _transform_body_for_viewer

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": _ERR_INVALID_JSON}), 400

        body_name = params.get("body_name", cache.get("default_body"))
        with cache_lock:
            entry = cache.get("bodies", {}).get(body_name)
        if entry is None:
            return jsonify({"error": f"Body '{body_name}' not found"}), 404
        body = entry["body"]

        antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
        if err:
            return err

        scene_path = params.get("scene_path")
        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", DEFAULT_POWER_DBM)
        rt_cfg_parsed = _parse_rt_config(params)

        body_offset, err = _parse_vec3(params, "body_offset")
        if err:
            return err
        body_rotation_y, err = _parse_rotation_y(params)
        if err:
            return err
        tissue, _, err = _parse_freq_and_tissue(params)
        if err:
            return err
        quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
        if err:
            return err

        # RT receiver: use configured default center (z=1m) shifted by body offset
        # (body centroid mean is ~z=-0.38, below floors of most Sionna scenes)
        default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
        body_center = default_bc + body_offset

        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

        import time as _time

        t_route = _time.perf_counter()

        # Try Modal GPU first, fall back to local CPU (only if Modal is not configured)
        from aegis.viewer.modal_proxy import gpu_status as _gpu_status

        _was_cold = not _gpu_status().get("warm", False)
        gpu_backend = None
        modal_result = None
        modal_error = None
        try:
            from pathlib import Path as _Path

            from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled
            from aegis.viewer.modal_proxy import trace_differt as _modal_trace_differt

            scene_dir = _Path(scene_path).parent
            scene_xml = _Path(scene_path).read_text()
            # Bundle mesh files so Modal has them
            scene_files = {}
            for f in scene_dir.rglob("*"):
                if f.is_file() and f.name != _Path(scene_path).name:
                    scene_files[str(f.relative_to(scene_dir))] = f.read_bytes()
            modal_result = _modal_trace_differt(
                scene_xml=scene_xml,
                scene_files=scene_files,
                tx_pos=antenna_pos.tolist(),
                rx_pos=body_center.tolist(),
                max_order=rt_cfg_parsed["max_depth"],
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=rt_cfg_parsed["reflection_loss_per_order"],
                method=rt_cfg_parsed["method"],
                num_rays=rt_cfg_parsed["rays_per_source"],
                chunk_size=rt_cfg_parsed["chunk_size"],
            )
            if modal_result is None and _modal_enabled():
                modal_error = "Modal DiffeRT returned no result"
        except Exception as e:
            logger.error("Modal DiffeRT proxy attempt failed: %s", e, exc_info=True)
            from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled

            if _modal_enabled():
                modal_error = str(e)

        if modal_result is not None:
            from aegis.paths import PropagationPaths

            paths = PropagationPaths.from_dict(modal_result["paths"])
            path_viz = modal_result["path_viz"]
            gpu_backend = modal_result.get("gpu_backend")
            rt_ms = modal_result.get("timings", {}).get("trace_ms")
        elif modal_error:
            # Modal is configured but failed - don't fall back to local CPU (OOM risk)
            return jsonify({"error": f"DiffeRT on Modal failed: {modal_error}"}), 503
        else:
            # No Modal configured - use local CPU (dev mode)
            try:
                paths, path_viz = compute_paths_differt(
                    scene_path,
                    tx_pos=antenna_pos,
                    rx_pos=body_center,
                    max_order=rt_cfg_parsed["max_depth"],
                    freq_hz=tissue.freq_hz,
                    tx_power_dbm=power_dbm,
                    reflection_loss_per_order=rt_cfg_parsed["reflection_loss_per_order"],
                    method=rt_cfg_parsed["method"],
                    num_rays=rt_cfg_parsed["rays_per_source"],
                    chunk_size=rt_cfg_parsed["chunk_size"],
                )
            except Exception as e:
                return jsonify({"error": f"Ray tracing failed: {e}"}), 500
            rt_ms = None

        t_rt = _time.perf_counter()

        level_val, _, _ = _stats_label(engine_kw)
        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level_val or 0)

        result = _run_dosimetry(tissue, transformed_body, paths, engine_kw)
        t_compute = _time.perf_counter()

        dist = float(np.linalg.norm(antenna_pos - body_center))
        extra = {
            "S_inc": float(np.sum(paths.power)),
            "distance_m": dist,
            "n_rt_paths": paths.n_paths,
            "path_viz": path_viz,
            "cold_start": _was_cold,
        }

        if gpu_backend is not None:
            extra["gpu_backend"] = gpu_backend

        t_stats = _time.perf_counter()
        timing_pairs = [
            ("rt_ms", rt_ms if rt_ms is not None else (t_rt - t_route) * 1e3),
            ("kernel_ms", (t_compute - t_rt) * 1e3),
            ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
            ("route_total_ms", (t_stats - t_route) * 1e3),
        ]
        resp, stats = _make_rt_response(
            result,
            body,
            tissue,
            engine_kw,
            quantities,
            exposure_scenario,
            extra,
            timing_pairs,
        )
        app.config["_last_compliance_result"] = stats.get("compliance")
        return resp

    @app.route("/api/compute/sionna-rt", methods=["POST"])
    def api_compute_sionna_rt():
        """Compute dosimetry using Sionna RT ray-traced paths (via Modal GPU)."""
        from aegis.viewer.compute import _transform_body_for_viewer

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": _ERR_INVALID_JSON}), 400

        body_name = params.get("body_name", cache.get("default_body"))
        with cache_lock:
            entry = cache.get("bodies", {}).get(body_name)
        if entry is None:
            return jsonify({"error": f"Body '{body_name}' not found"}), 404
        body = entry["body"]

        antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
        if err:
            return err

        scene_path = params.get("scene_path")
        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", DEFAULT_POWER_DBM)
        rt_cfg_parsed = _parse_rt_config(params)

        body_offset, err = _parse_vec3(params, "body_offset")
        if err:
            return err
        body_rotation_y, err = _parse_rotation_y(params)
        if err:
            return err
        tissue, _, err = _parse_freq_and_tissue(params)
        if err:
            return err
        quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
        if err:
            return err

        # RT receiver: use configured default center (z=1m) shifted by body offset
        default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
        body_center = default_bc + body_offset

        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

        import time as _time

        t_route = _time.perf_counter()

        # Call Modal GPU for Sionna RT (no local CPU fallback)
        from aegis.viewer.modal_proxy import gpu_status as _gpu_status

        _was_cold = not _gpu_status().get("warm", False)

        # Extract scene name from path: .../simple_reflector/simple_reflector.xml -> simple_reflector
        from pathlib import Path as _Path

        from aegis.viewer.modal_proxy import trace_sionna_bundled as _modal_trace_sionna

        scene_name = _Path(scene_path).parent.name
        rt_config_dict = {
            "los": rt_cfg_parsed["los"],
            "specular_reflection": rt_cfg_parsed["specular_reflection"],
            "diffuse_reflection": rt_cfg_parsed["diffuse_reflection"],
            "refraction": rt_cfg_parsed["refraction"],
            "diffraction": rt_cfg_parsed["diffraction"],
            "edge_diffraction": rt_cfg_parsed["edge_diffraction"],
            "diffraction_lit_region": rt_cfg_parsed["diffraction_lit_region"],
            "samples_per_src": rt_cfg_parsed["rays_per_source"],
            "max_num_paths_per_src": rt_cfg_parsed["max_paths_per_source"],
            "synthetic_array": rt_cfg_parsed["synthetic_array"],
            "seed": rt_cfg_parsed["seed"],
        }

        modal_result = _modal_trace_sionna(
            scene_name=scene_name,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_bounces=rt_cfg_parsed["max_depth"],
            freq_hz=tissue.freq_hz,
            tx_power_dbm=power_dbm,
            rt_config=rt_config_dict,
        )

        if modal_result is None:
            return jsonify({"error": "Sionna RT requires GPU. Modal unavailable."}), 503

        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_dict(modal_result["paths"])
        path_viz = modal_result["path_viz"]
        gpu_backend = modal_result.get("gpu_backend")
        rt_ms = modal_result.get("timings", {}).get("trace_ms")

        t_rt = _time.perf_counter()

        level_val, _, _ = _stats_label(engine_kw)
        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level_val or 0)

        result = _run_dosimetry(tissue, transformed_body, paths, engine_kw)
        t_compute = _time.perf_counter()

        dist = float(np.linalg.norm(antenna_pos - body_center))
        extra = {
            "S_inc": float(np.sum(paths.power)),
            "distance_m": dist,
            "n_rt_paths": paths.n_paths,
            "path_viz": path_viz,
            "backend": "sionna",
            "cold_start": _was_cold,
        }

        if gpu_backend is not None:
            extra["gpu_backend"] = gpu_backend

        t_stats = _time.perf_counter()
        timing_pairs = [
            ("rt_ms", rt_ms if rt_ms is not None else (t_rt - t_route) * 1e3),
            ("kernel_ms", (t_compute - t_rt) * 1e3),
            ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
            ("route_total_ms", (t_stats - t_route) * 1e3),
        ]
        resp, stats = _make_rt_response(
            result,
            body,
            tissue,
            engine_kw,
            quantities,
            exposure_scenario,
            extra,
            timing_pairs,
        )
        app.config["_last_compliance_result"] = stats.get("compliance")
        return resp

    @app.route("/api/compute/voxel-rt", methods=["POST"])
    def api_compute_voxel_rt():
        """Compute dosimetry using Sionna RT on the voxel environment geometry (via Modal GPU)."""
        from aegis.viewer.compute import _transform_body_for_viewer

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": _ERR_INVALID_JSON}), 400

        body_name = params.get("body_name", cache.get("default_body"))
        with cache_lock:
            entry = cache.get("bodies", {}).get(body_name)
            voxel_positions = cache.get("voxel_positions")
            voxel_sizes = cache.get("voxel_sizes")
            voxel_materials = cache.get("voxel_materials")
            cfg = cache["config"]
        if entry is None:
            return jsonify({"error": f"Body '{body_name}' not found"}), 404
        body = entry["body"]

        if voxel_positions is None or len(voxel_positions) == 0:
            return jsonify({"error": "No voxel data available"}), 400

        antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
        if err:
            return err
        body_offset, err = _parse_vec3(params, "body_offset")
        if err:
            return err
        body_rotation_y, err = _parse_rotation_y(params)
        if err:
            return err

        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", DEFAULT_POWER_DBM)
        rt_cfg_parsed = _parse_rt_config(params)
        max_order = rt_cfg_parsed["max_depth"]

        quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
        if err:
            return err
        tissue, _, err = _parse_freq_and_tissue(params)
        if err:
            return err

        # Transform body consistently (vertices, centroids, normals all rotated + offset)
        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
        body_center = transformed_body.centroids.mean(axis=0)

        import time as _time

        t_route = _time.perf_counter()

        # Prepare voxel mesh data for Modal
        max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]
        try:
            from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

            z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
            ext_mask = extract_exterior(grid_coords)
            ext_pos = z_up_pos[ext_mask]

            # Each exterior voxel face is 2 triangles, up to 6 faces per voxel
            est_triangles = len(ext_pos) * 12
            if est_triangles > max_rt_triangles and max_order > 0:
                return jsonify(
                    {
                        "error": f"Scene too large for reflections ({est_triangles:,} triangles, "
                        f"limit {max_rt_triangles:,}). Use LOS only (order 0) or reduce scene size."
                    }
                ), 400

            ext_materials = None
            if voxel_materials is not None:
                ext_materials = [voxel_materials[i] for i in np.nonzero(ext_mask)[0]]
        except Exception as e:
            return jsonify({"error": f"Voxel mesh build failed: {e}"}), 500

        # Call Modal GPU for Sionna RT on voxel geometry
        import hashlib

        from aegis.viewer.modal_proxy import gpu_status as _gpu_status
        from aegis.viewer.modal_proxy import trace_sionna_voxel as _modal_trace_voxel

        _was_cold = not _gpu_status().get("warm", False)

        voxel_hash = hashlib.md5(np.asarray(voxel_positions).tobytes()).hexdigest()[:12]
        scene_key = f"voxel_{voxel_hash}"

        scene_data = {
            "vertices": ext_pos.tolist(),
            "triangles": [],  # triangulation handled on Modal side
            "materials": ext_materials or [],
        }

        rt_config_dict = {
            "los": rt_cfg_parsed["los"],
            "specular_reflection": rt_cfg_parsed["specular_reflection"],
            "diffuse_reflection": rt_cfg_parsed["diffuse_reflection"],
            "refraction": rt_cfg_parsed["refraction"],
            "diffraction": rt_cfg_parsed["diffraction"],
            "edge_diffraction": rt_cfg_parsed["edge_diffraction"],
            "diffraction_lit_region": rt_cfg_parsed["diffraction_lit_region"],
            "samples_per_src": rt_cfg_parsed["rays_per_source"],
            "max_num_paths_per_src": rt_cfg_parsed["max_paths_per_source"],
            "synthetic_array": rt_cfg_parsed["synthetic_array"],
            "seed": rt_cfg_parsed["seed"],
        }

        modal_result = _modal_trace_voxel(
            scene_key=scene_key,
            scene_data=scene_data,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_bounces=max_order,
            freq_hz=tissue.freq_hz,
            tx_power_dbm=power_dbm,
            rt_config=rt_config_dict,
        )

        if modal_result is None:
            return jsonify({"error": "GPU unavailable for voxel ray tracing"}), 503

        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_dict(modal_result["paths"])
        path_viz = modal_result["path_viz"]
        gpu_backend = modal_result.get("gpu_backend")
        rt_ms = modal_result.get("timings", {}).get("trace_ms")

        t_rt = _time.perf_counter()

        level_val, _, _ = _stats_label(engine_kw)
        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level_val or 0)

        result = _run_dosimetry(tissue, transformed_body, paths, engine_kw)
        t_compute = _time.perf_counter()

        dist = float(np.linalg.norm(antenna_pos - body_center))
        extra = {
            "S_inc": float(np.sum(paths.power)),
            "distance_m": dist,
            "n_rt_paths": paths.n_paths,
            "path_viz": path_viz,
        }

        extra["backend"] = "sionna-voxel"
        extra["cold_start"] = _was_cold
        if gpu_backend is not None:
            extra["gpu_backend"] = gpu_backend

        t_stats = _time.perf_counter()
        timing_pairs = [
            ("rt_ms", rt_ms if rt_ms is not None else (t_rt - t_route) * 1e3),
            ("kernel_ms", (t_compute - t_rt) * 1e3),
            ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
            ("route_total_ms", (t_stats - t_route) * 1e3),
        ]
        resp, stats = _make_rt_response(
            result,
            body,
            tissue,
            engine_kw,
            quantities,
            exposure_scenario,
            extra,
            timing_pairs,
        )
        app.config["_last_compliance_result"] = stats.get("compliance")
        return resp

    @app.route("/api/compliance/report", methods=["GET"])
    def compliance_report():
        """Compliance data is returned inline in X-Stats from compute endpoints.

        This endpoint is deprecated. Clients should read compliance from the
        X-Stats header of /api/compute responses.
        """
        return jsonify({"error": "Compliance data is available in X-Stats from /api/compute"}), 410

    @app.route("/api/channel-presets", methods=["GET"])
    def channel_presets():
        """List available 3GPP stochastic channel presets."""
        from pathlib import Path

        from aegis.channel import list_presets, load_preset

        with cache_lock:
            cfg = cache["config"]
        stoch_cfg = cfg["dosimetry"].get("stochastic", {})
        preset_dir = Path(stoch_cfg.get("preset_dir", "data/channel_presets"))
        if not preset_dir.is_absolute():
            preset_dir = Path(__file__).resolve().parents[4] / preset_dir
        featured = stoch_cfg.get("featured_presets", [])
        all_names = list_presets(preset_dir)
        presets = []
        for name in all_names:
            try:
                p = load_preset(name, preset_dir)
                presets.append(
                    {
                        "name": name,
                        "featured": name in featured,
                        "params": p["params"],
                    }
                )
            except Exception:
                continue
        return jsonify(presets)

    @app.route("/api/gpu/status")
    def api_gpu_status():
        """Return GPU container warmth status."""
        from aegis.viewer.modal_proxy import gpu_status

        return jsonify(gpu_status())

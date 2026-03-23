"""Compute routes: dosimetry, ray tracing, voxel RT."""

from __future__ import annotations

import json
import logging

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.compliance import ExposureScenario, evaluate_compliance
from aegis.viewer.compute import PHANTOM_MASS_KG

logger = logging.getLogger(__name__)

# String constants (avoid duplicate literals)
_OCTET_STREAM = "application/octet-stream"
_ERR_NO_BODY = "No body mesh loaded"
_ERR_NO_DIFFERT = "DiffeRT not installed"


def _inject_curvature_H(engine_kw: dict, body) -> dict:
    """Add curvature_H to engine kwargs if curvature or diffraction is requested."""
    if engine_kw.get("curvature") or engine_kw.get("diffraction"):
        from aegis.viewer.compute import _compute_face_curvature

        engine_kw["curvature_H"] = _compute_face_curvature(body)
    return engine_kw


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
    from flask import current_app

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

    compliance = evaluate_compliance(
        scenario=scenario,
        freq_hz=freq_hz,
        sab_4cm2=peak_sab_averaged if peak_sab_averaged is not None else float(result.peak_sab),
        sinc_local=peak_sinc_averaged,
        sinc_whole_body=sinc_wb,
        sar_wb=result.sar_wb,
        sab_1cm2=peak_sab_1cm2,
    )

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
        },
        "compliant": compliance.overall_pass,
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level if level is not None else 0,
        "T0": float(tissue.T0),
        "tissue_eps_r": tissue.eps_r,
        "tissue_sigma": tissue.sigma,
    }

    # Store compliance result for the /api/compliance/report endpoint.
    # NOTE: global app state, single-session assumption. Concurrent users
    # may read each other's compliance results.
    current_app.config["_last_compliance_result"] = stats["compliance"]

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

    @app.route("/api/compute", methods=["POST"])
    def api_compute():
        """Compute dosimetry for given antenna position."""
        from aegis.viewer.compute import compute_dosimetry, resolve_skin_model

        with cache_lock:
            body = cache.get("body")
            cfg = cache["config"]
        if body is None:
            return jsonify({"error": _ERR_NO_BODY}), 400

        params = request.get_json(silent=True)
        if params is None:
            if request.data:
                return jsonify({"error": "Invalid JSON body"}), 400
            params = {}
        elif not isinstance(params, dict):
            return jsonify({"error": "JSON body must be an object"}), 400

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
            stochastic = {
                "preset": params.get("stochastic_preset", stoch_cfg.get("default_preset", "3GPP_38.901_UMi_LOS")),
                "seed": int(params.get("stochastic_seed", stoch_cfg.get("default_seed", 42))),
                "overrides": params.get("stochastic_overrides", {}),
                "freq_ghz": float(params.get("freq_hz", 28e9)) / 1e9,
            }

        freq_hz = float(params.get("freq_hz", 28e9))
        skin_model_name = params.get("skin_model", "itis")
        try:
            tissue = resolve_skin_model(skin_model_name, freq_hz)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        antenna_pos = params.get("antenna_pos", [5, 0, 1])
        body_offset = params.get("body_offset", [0, 0, 0])
        body_rotation_y = params.get("body_rotation_y", 0.0)

        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        exposure_scenario_str = params.get("exposure_scenario", "general_public")
        try:
            exposure_scenario = ExposureScenario(exposure_scenario_str)
        except ValueError:
            return jsonify({"error": f"Invalid exposure_scenario: {exposure_scenario_str}"}), 400

        import time as _time

        t_route = _time.perf_counter()

        try:
            result, res_body, res_tissue, res_level, res_mode, res_corr, extra = compute_dosimetry(
                body,
                antenna_pos=np.array(antenna_pos),
                body_offset=np.array(body_offset),
                body_rotation_y=float(body_rotation_y),
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
            ext_materials = [voxel_materials[i] for i in np.where(ext_mask)[0]]
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

        body = cache.get("body")
        if body is None:
            return jsonify({"error": _ERR_NO_BODY}), 400

        from aegis.viewer.compute import _transform_body_for_viewer, resolve_skin_model

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        scene_path = params.get("scene_path")
        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", 60.0)
        max_order = params.get("max_order", 1)
        body_offset = np.array(params.get("body_offset", [0, 0, 0]))
        body_rotation_y = float(params.get("body_rotation_y", 0.0))

        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        exposure_scenario_str = params.get("exposure_scenario", "general_public")
        try:
            exposure_scenario = ExposureScenario(exposure_scenario_str)
        except ValueError:
            return jsonify({"error": f"Invalid exposure_scenario: {exposure_scenario_str}"}), 400

        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        freq_hz = float(params.get("freq_hz", 28e9))
        skin_model_name = params.get("skin_model", "itis")
        try:
            tissue = resolve_skin_model(skin_model_name, freq_hz)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        # RT receiver: use configured default center (z=1m) shifted by body offset
        # (body centroid mean is ~z=-0.38, below floors of most Sionna scenes)
        default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
        body_center = default_bc + body_offset

        # Transform body mesh for dosimetry engine
        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

        import time as _time

        t_route = _time.perf_counter()

        # Run DiffeRT
        try:
            rt_cfg = cache["config"]["raytracer"]
            paths, path_viz = compute_paths_differt(
                scene_path,
                tx_pos=antenna_pos,
                rx_pos=body_center,
                max_order=max_order,
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=rt_cfg["reflection_loss_per_order"],
            )
        except Exception as e:
            return jsonify({"error": f"Ray tracing failed: {e}"}), 500

        t_rt = _time.perf_counter()

        level_val, mode_val, corr_val = _stats_label(engine_kw)
        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level_val or 0)

        # Run dosimetry engine on the transformed body
        from aegis.engine import DosimetryEngine

        engine = DosimetryEngine(tissue)
        _inject_curvature_H(engine_kw, transformed_body)
        body_mass = PHANTOM_MASS_KG.get(body.name) if body.name else None
        result = engine.compute(transformed_body, paths, body_mass=body_mass, **engine_kw)

        t_compute = _time.perf_counter()

        buf, arrays_meta = _build_binary_response(result, quantities)
        dist = float(np.linalg.norm(antenna_pos - body_center))
        total_power = float(np.sum(paths.power))

        stats = _build_stats_response(
            result,
            body,
            tissue,
            level_val,
            mode=mode_val,
            corrections=corr_val,
            extra={
                "S_inc": total_power,
                "distance_m": dist,
                "n_rt_paths": paths.n_paths,
                "path_viz": path_viz,
            },
            scenario=exposure_scenario,
        )

        t_stats = _time.perf_counter()

        timings = stats.get("timings", {})
        timings["rt_ms"] = (t_rt - t_route) * 1e3
        timings["kernel_ms"] = (t_compute - t_rt) * 1e3
        timings["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
        timings["route_total_ms"] = (t_stats - t_route) * 1e3
        stats["timings"] = timings
        stats["arrays"] = arrays_meta

        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/compute/sionna-rt", methods=["POST"])
    def api_compute_sionna_rt():
        """Compute dosimetry using Sionna RT ray-traced paths."""
        try:
            from aegis.integration.sionna import paths_from_sionna_scene
        except ImportError:
            return jsonify({"error": "Sionna RT not installed. Install with: pip install aegis[sionna]"}), 501

        body = cache.get("body")
        if body is None:
            return jsonify({"error": _ERR_NO_BODY}), 400

        from aegis.viewer.compute import _transform_body_for_viewer, resolve_skin_model

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        scene_path = params.get("scene_path")
        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", 60.0)
        max_bounces = params.get("max_order", 5)
        body_offset = np.array(params.get("body_offset", [0, 0, 0]))
        body_rotation_y = float(params.get("body_rotation_y", 0.0))

        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        exposure_scenario_str = params.get("exposure_scenario", "general_public")
        try:
            exposure_scenario = ExposureScenario(exposure_scenario_str)
        except ValueError:
            return jsonify({"error": f"Invalid exposure_scenario: {exposure_scenario_str}"}), 400

        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        freq_hz = float(params.get("freq_hz", 28e9))
        skin_model_name = params.get("skin_model", "itis")
        try:
            tissue = resolve_skin_model(skin_model_name, freq_hz)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        # RT receiver: use configured default center (z=1m) shifted by body offset
        default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
        body_center = default_bc + body_offset

        # Transform body mesh for dosimetry engine
        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

        import time as _time

        t_route = _time.perf_counter()

        try:
            import sionna.rt

            scene = sionna.rt.load_scene(scene_path)
            paths, path_viz = paths_from_sionna_scene(
                scene,
                tx_positions=antenna_pos[np.newaxis, :] if antenna_pos.ndim == 1 else antenna_pos,
                rx_position=body_center,
                freq_hz=tissue.freq_hz,
                max_bounces=max_bounces,
                tx_power_dbm=power_dbm,
                return_viz=True,
            )
        except ImportError:
            return jsonify({"error": "Sionna RT not installed"}), 501
        except Exception as e:
            return jsonify({"error": f"Sionna ray tracing failed: {e}"}), 500

        t_rt = _time.perf_counter()

        level_val, mode_val, corr_val = _stats_label(engine_kw)
        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level_val or 0)

        from aegis.engine import DosimetryEngine

        engine = DosimetryEngine(tissue)
        _inject_curvature_H(engine_kw, transformed_body)
        body_mass = PHANTOM_MASS_KG.get(body.name) if body.name else None
        result = engine.compute(transformed_body, paths, body_mass=body_mass, **engine_kw)

        t_compute = _time.perf_counter()

        buf, arrays_meta = _build_binary_response(result, quantities)
        dist = float(np.linalg.norm(antenna_pos - body_center))
        total_power = float(np.sum(paths.power))

        stats = _build_stats_response(
            result,
            body,
            tissue,
            level_val,
            mode=mode_val,
            corrections=corr_val,
            extra={
                "S_inc": total_power,
                "distance_m": dist,
                "n_rt_paths": paths.n_paths,
                "path_viz": path_viz,
                "backend": "sionna",
            },
            scenario=exposure_scenario,
        )

        t_stats = _time.perf_counter()

        timings = stats.get("timings", {})
        timings["rt_ms"] = (t_rt - t_route) * 1e3
        timings["kernel_ms"] = (t_compute - t_rt) * 1e3
        timings["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
        timings["route_total_ms"] = (t_stats - t_route) * 1e3
        stats["timings"] = timings
        stats["arrays"] = arrays_meta

        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/compute/voxel-rt", methods=["POST"])
    def api_compute_voxel_rt():
        """Compute dosimetry using DiffeRT on the voxel environment geometry."""
        try:
            from aegis.viewer.raytracer import get_or_build_voxel_scene
        except ImportError:
            return jsonify({"error": _ERR_NO_DIFFERT}), 501

        from aegis.viewer.compute import _transform_body_for_viewer, resolve_skin_model

        with cache_lock:
            body = cache.get("body")
            voxel_positions = cache.get("voxel_positions")
            voxel_sizes = cache.get("voxel_sizes")
            voxel_materials = cache.get("voxel_materials")
            cfg = cache["config"]
        if body is None:
            return jsonify({"error": _ERR_NO_BODY}), 400

        if voxel_positions is None or len(voxel_positions) == 0:
            return jsonify({"error": "No voxel data available"}), 400

        params = request.get_json(silent=True)
        if not isinstance(params, dict):
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        body_offset = np.array(params.get("body_offset", [0, 0, 0]), dtype=np.float64)
        body_rotation_y = float(params.get("body_rotation_y", 0.0))
        engine_kw = _parse_mode_or_level(params)
        power_dbm = params.get("power_dbm", 60.0)
        max_order = params.get("max_order", 0)

        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        exposure_scenario_str = params.get("exposure_scenario", "general_public")
        try:
            exposure_scenario = ExposureScenario(exposure_scenario_str)
        except ValueError:
            return jsonify({"error": f"Invalid exposure_scenario: {exposure_scenario_str}"}), 400

        freq_hz = float(params.get("freq_hz", 28e9))
        skin_model_name = params.get("skin_model", "itis")
        try:
            tissue = resolve_skin_model(skin_model_name, freq_hz)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        # Transform body consistently (vertices, centroids, normals all rotated + offset)
        transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
        body_center = transformed_body.centroids.mean(axis=0)

        import time as _time

        t_route = _time.perf_counter()

        # Build or get cached voxel DiffeRT scene
        max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]
        try:
            from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

            z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
            ext_mask = extract_exterior(grid_coords)
            ext_grid = grid_coords[ext_mask]
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
                ext_materials = [voxel_materials[i] for i in np.where(ext_mask)[0]]
            material_colors = cfg.get("voxels", {}).get("material_colors")

            scene = get_or_build_voxel_scene(
                ext_pos,
                ext_grid,
                voxel_size=vs,
                materials=ext_materials,
                material_colors=material_colors,
            )
        except Exception as e:
            return jsonify({"error": f"Voxel mesh build failed: {e}"}), 500

        # Run DiffeRT on the voxel scene
        try:
            import equinox as eqx
            import jax.numpy as jnp

            from aegis.viewer.raytracer import isotropic_incident_power_density

            scene_with_tx_rx = eqx.tree_at(lambda s: s.transmitters, scene, jnp.array([antenna_pos.tolist()]))
            scene_with_tx_rx = eqx.tree_at(lambda s: s.receivers, scene_with_tx_rx, jnp.array([body_center.tolist()]))

            all_k_hat = []
            all_power = []
            path_viz = []

            rt_cfg = cfg["raytracer"]
            tx_power_w = 10 ** ((power_dbm - 30) / 10)
            d_clamp = float(rt_cfg["fspl_distance_clamp"])

            for order in range(max_order + 1):
                try:
                    paths_result = scene_with_tx_rx.compute_paths(order=order)
                except Exception as e:
                    logger.warning("Bounce order %d failed, skipping: %s", order, e)
                    continue

                verts = np.array(paths_result.vertices)
                mask = np.array(paths_result.mask)
                flat_v = verts.reshape(-1, verts.shape[-2], verts.shape[-1])
                flat_m = mask.flatten()

                for i in range(len(flat_v)):
                    if i >= len(flat_m) or not flat_m[i]:
                        continue
                    pv = flat_v[i]
                    segments = np.diff(pv, axis=0)
                    seg_lens = np.linalg.norm(segments, axis=1)
                    total_len = float(np.sum(seg_lens))
                    if total_len < 1e-6:
                        continue

                    k_hat = segments[-1] / np.linalg.norm(segments[-1])
                    all_k_hat.append(k_hat)

                    S_inc = isotropic_incident_power_density(tx_power_w, total_len, min_distance_m=d_clamp) * (
                        rt_cfg["reflection_loss_per_order"] ** order
                    )
                    all_power.append(S_inc)

                    path_viz.append(
                        {
                            "vertices": pv.tolist(),
                            "order": order,
                            "length": total_len,
                        }
                    )

        except Exception as e:
            return jsonify({"error": f"Voxel RT failed: {e}"}), 500

        t_rt = _time.perf_counter()

        level_val, mode_val, corr_val = _stats_label(engine_kw)
        if not all_k_hat:
            return _zero_paths_response(body, tissue, level_val or 0)

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_powers(k_hat=np.array(all_k_hat), power=np.array(all_power))
        engine = DosimetryEngine(tissue)
        _inject_curvature_H(engine_kw, transformed_body)
        body_mass = PHANTOM_MASS_KG.get(body.name) if body.name else None

        result = engine.compute(transformed_body, paths, body_mass=body_mass, **engine_kw)

        t_compute = _time.perf_counter()

        buf, arrays_meta = _build_binary_response(result, quantities)
        dist = float(np.linalg.norm(antenna_pos - body_center))

        stats = _build_stats_response(
            result,
            body,
            tissue,
            level_val,
            mode=mode_val,
            corrections=corr_val,
            extra={
                "S_inc": float(np.sum(all_power)),
                "distance_m": dist,
                "n_rt_paths": len(all_k_hat),
                "path_viz": path_viz,
            },
            scenario=exposure_scenario,
        )

        t_stats = _time.perf_counter()

        timings = stats.get("timings", {})
        timings["rt_ms"] = (t_rt - t_route) * 1e3
        timings["kernel_ms"] = (t_compute - t_rt) * 1e3
        timings["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
        timings["route_total_ms"] = (t_stats - t_route) * 1e3
        stats["timings"] = timings
        stats["arrays"] = arrays_meta

        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/compliance/report", methods=["GET"])
    def compliance_report():
        """Return the last compliance result as JSON."""
        # NOTE: reads global app state (single-session assumption).
        # Concurrent users may read another session's compliance result.
        last = app.config.get("_last_compliance_result")
        if last is None:
            return jsonify({"error": "No computation result available"}), 404
        return jsonify(last)

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

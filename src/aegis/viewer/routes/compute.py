"""Compute routes: dosimetry, ray tracing, voxel RT."""

from __future__ import annotations

import json

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.compliance import ICNIRP_2020


def _build_stats_response(result, body, tissue, level, extra=None):
    """Build the X-Stats JSON dict from a DosimetryResult."""
    stats = {
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "compliant": bool(result.peak_sab < ICNIRP_2020.sab_peak),
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level,
        "T0": float(tissue.T0),
    }
    if extra:
        stats.update(extra)
    return stats


def _zero_paths_response(body, tissue, level, extra=None):
    """Build stats dict when zero paths are found."""
    stats = {
        "p_abs": 0,
        "p_abs_mw": 0,
        "peak_sab": 0,
        "compliant": True,
        "n_illuminated": 0,
        "n_triangles": body.n_triangles,
        "level": level,
        "S_inc": 0,
        "distance_m": 0,
        "T0": tissue.T0,
        "n_rt_paths": 0,
        "path_viz": [],
    }
    if extra:
        stats.update(extra)
    sab_bytes = np.zeros(body.n_triangles, dtype=np.float32).tobytes()
    resp = Response(sab_bytes, mimetype="application/octet-stream")
    resp.headers["X-Stats"] = json.dumps(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach compute routes to *app*."""

    @app.route("/api/compute", methods=["POST"])
    def api_compute():
        """Compute dosimetry for given antenna position."""
        from aegis.viewer.compute import TISSUE_PRESETS, compute_dosimetry

        with cache_lock:
            body = cache.get("body")
            cfg = cache["config"]
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

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

        try:
            level = int(params.get("level", dcfg["default_level"]))
        except (TypeError, ValueError):
            return jsonify({"error": "level must be an integer"}), 400
        if level not in range(0, 9):
            return jsonify({"error": "level must be between 0 and 8"}), 400

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

        tissue_name = params.get("tissue", "skin_28ghz")
        if tissue_name not in TISSUE_PRESETS:
            return jsonify({"error": f"Unknown tissue preset: {tissue_name!r}"}), 400

        antenna_pos = params.get("antenna_pos", [5, 0, 1])
        body_offset = params.get("body_offset", [0, 0, 0])
        body_rotation_y = params.get("body_rotation_y", 0.0)

        tissue = TISSUE_PRESETS[tissue_name]

        result = compute_dosimetry(
            body,
            antenna_pos=np.array(antenna_pos),
            body_offset=np.array(body_offset),
            body_rotation_y=float(body_rotation_y),
            level=level,
            tissue=tissue,
            power_dbm=power_dbm,
            n_paths=n_paths,
            config=cfg,
        )

        # Return binary S_ab with JSON stats in header
        sab_bytes = result.pop("sab_bytes")
        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(result)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/scenes")
    def api_scenes():
        """List available Sionna XML scenes for DiffeRT ray tracing."""
        try:
            from aegis.viewer.raytracer import list_available_scenes

            return jsonify(list_available_scenes())
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

    @app.route("/api/scene/load", methods=["POST"])
    def api_scene_load():
        """Load a Sionna scene and return its geometry for Three.js."""
        try:
            from aegis.viewer.raytracer import load_scene, scene_geometry_to_binary
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        params = request.get_json()
        scene_path = params.get("path")
        if not scene_path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        try:
            scene_data = load_scene(scene_path)
            data, meta = scene_geometry_to_binary(scene_data)
            resp = Response(data, mimetype="application/octet-stream")
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
            return jsonify({"error": "DiffeRT not installed"}), 501

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
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
        return resp

    @app.route("/api/compute/rt", methods=["POST"])
    def api_compute_rt():
        """Compute dosimetry using DiffeRT ray-traced paths."""
        try:
            from aegis.viewer.raytracer import compute_paths_differt
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        from aegis.viewer.compute import TISSUE_PRESETS

        body = cache.get("body")
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

        params = request.get_json()
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        scene_path = params.get("scene_path")
        level = params.get("level", 2)
        tissue_name = params.get("tissue", "skin_28ghz")
        power_dbm = params.get("power_dbm", 30.0)
        max_order = params.get("max_order", 1)
        body_pos = params.get("body_pos")

        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        tissue = TISSUE_PRESETS.get(tissue_name)
        if tissue is None:
            from aegis.tissue.dielectric import SKIN_28GHZ

            tissue = SKIN_28GHZ

        # Body position in scene coordinates (defaults to origin at height 1.0)
        default_bc = cache["config"]["raytracer"]["default_body_center"]
        body_center = np.array(body_pos) if body_pos is not None else np.array(default_bc)

        # Run DiffeRT
        try:
            paths, path_viz = compute_paths_differt(
                scene_path,
                tx_pos=antenna_pos,
                rx_pos=body_center,
                max_order=max_order,
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
            )
        except Exception as e:
            return jsonify({"error": f"Ray tracing failed: {e}"}), 500

        if paths.n_paths == 0:
            return _zero_paths_response(body, tissue, level)

        # Run dosimetry engine
        from aegis.engine import DosimetryEngine

        engine = DosimetryEngine(tissue)
        result = engine.compute(body, paths, level=level)

        sab_bytes = result.sab.astype(np.float32).tobytes()
        dist = float(np.linalg.norm(antenna_pos - body_center))
        total_power = float(np.sum(paths.power))

        stats = _build_stats_response(
            result,
            body,
            tissue,
            level,
            extra={
                "S_inc": total_power,
                "distance_m": dist,
                "n_rt_paths": paths.n_paths,
                "path_viz": path_viz,
            },
        )

        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/compute/voxel-rt", methods=["POST"])
    def api_compute_voxel_rt():
        """Compute dosimetry using DiffeRT on the voxel environment geometry."""
        try:
            from aegis.viewer.raytracer import get_or_build_voxel_scene
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        from aegis.viewer.compute import TISSUE_PRESETS

        with cache_lock:
            body = cache.get("body")
            voxel_positions = cache.get("voxel_positions")
            voxel_sizes = cache.get("voxel_sizes")
            voxel_materials = cache.get("voxel_materials")
            cfg = cache["config"]
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

        if voxel_positions is None or len(voxel_positions) == 0:
            return jsonify({"error": "No voxel data available"}), 400

        params = request.get_json()
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        body_offset = np.array(params.get("body_offset", [0, 0, 0]), dtype=np.float64)
        body_rotation_y = float(params.get("body_rotation_y", 0.0))
        level = params.get("level", 2)
        tissue_name = params.get("tissue", "skin_28ghz")
        power_dbm = params.get("power_dbm", 30.0)
        max_order = params.get("max_order", 0)

        tissue = TISSUE_PRESETS.get(tissue_name)
        if tissue is None:
            from aegis.tissue.dielectric import SKIN_28GHZ

            tissue = SKIN_28GHZ

        # Apply yaw rotation to body centroids and normals only (not vertices)
        from aegis.viewer.compute import _rotation_matrix_z

        if abs(body_rotation_y) > 1e-9:
            R = _rotation_matrix_z(body_rotation_y)
            rotated_centroids = body.centroids @ R.T
            rotated_normals = body.normals @ R.T
        else:
            rotated_centroids = body.centroids
            rotated_normals = body.normals

        body_center = rotated_centroids.mean(axis=0) + body_offset

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
                except Exception:
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

        if not all_k_hat:
            return _zero_paths_response(body, tissue, level)

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_powers(k_hat=np.array(all_k_hat), power=np.array(all_power))
        engine = DosimetryEngine(tissue)

        # Use rotated body for correct normal-incidence geometry
        if abs(body_rotation_y) > 1e-9:
            from aegis.geometry.mesh import BodyMesh as _BM

            rt_body = _BM(
                vertices=body.vertices,
                normals=rotated_normals,
                centroids=rotated_centroids,
                areas=body.areas,
                name=body.name,
            )
        else:
            rt_body = body

        result = engine.compute(rt_body, paths, level=level)

        sab_bytes = result.sab.astype(np.float32).tobytes()
        dist = float(np.linalg.norm(antenna_pos - body_center))

        stats = _build_stats_response(
            result,
            body,
            tissue,
            level,
            extra={
                "S_inc": float(np.sum(all_power)),
                "distance_m": dist,
                "n_rt_paths": len(all_k_hat),
                "path_viz": path_viz,
            },
        )

        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

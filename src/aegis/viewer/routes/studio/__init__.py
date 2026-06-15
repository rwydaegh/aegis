"""Coherent Exposure Studio API routes (runtime backend).

Phase 1b serves the precomputed packs resolved by :mod:`._config` and
reconstructs coherent field slices on demand. The runtime studio is
fork-free: it imports only ``aegis.*`` (notably ``aegis.hotspot`` and
``aegis.coherent``) plus stdlib/numpy, and never touches the paper fork or the
ray tracer. Packs are produced offline by ``scripts/studio_precompute.py``.
"""

from __future__ import annotations

import threading

import numpy as np
from flask import Flask, jsonify

from ._config import available_packs, paper_fork_paths_dir, studio_data_dir

__all__ = [
    "available_packs",
    "paper_fork_paths_dir",
    "register",
    "studio_data_dir",
]


class _QPackMissing(Exception):
    """ECBF was requested but its exposure-operator (Q) pack is absent.

    Carries the pack stem so the route can emit the not-precomputed 409 sentinel.
    """

    def __init__(self, stem: str) -> None:
        self.stem = stem
        super().__init__(stem)


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register the Coherent Exposure Studio API routes."""
    from aegis.viewer.routes._helpers import get_json_dict
    from aegis.viewer.routes.compute._responses import _json_dumps_safe

    from . import _bodymap, _channel, _paths, _phantom, _precoders, _presets, _slice, _volume

    def _beam_field(beam, paths, focus_xyz, freq_hz, condition, array_n, freq_ghz, ecbf_budget_frac):
        """Resolve a beam to ``(x, field_source)`` for the field reconstructors.

        Most beams collapse a per-element precoder ``x`` (field_source None); the
        decohered baseline is a precomputed weight source instead (x None). ECBF
        loads its precomputed Q and raises :class:`_QPackMissing` when absent.
        """
        if beam == "decohered":
            # Canonical decohered baseline: scramble inter-direction phase after
            # collapse (not expressible as a per-element precoder).
            x_base = _precoders.build_precoder("mrt", paths, focus_xyz, freq_hz, power=1.0)
            return None, _slice.decohered_field_source(paths, x_base)
        if beam == "ecbf":
            q = _paths.load_q(condition, array_n, freq_ghz, cache, cache_lock)
            if q is None:
                raise _QPackMissing(f"{condition}_bs{int(array_n)}_{freq_ghz:g}")
            x = _precoders.build_ecbf_from_q(paths, focus_xyz, freq_hz, q, power=1.0, budget_frac=ecbf_budget_frac)
            return x, None
        return _precoders.build_precoder(beam, paths, focus_xyz, freq_hz, power=1.0), None

    @app.route("/api/studio/manifest")
    def api_studio_manifest():
        return jsonify(_presets.manifest())

    @app.route("/api/studio/rays")
    def api_studio_rays():
        from flask import request

        condition = request.args.get("condition", "los")
        array_n = request.args.get("array_n", default=16, type=int)
        seed = request.args.get("seed", default=0, type=int)
        top_k = request.args.get("top_k", default=200, type=int)
        # Bound allocation against a huge top_k and keep a negative value from
        # silently slicing entries off the end via the [::-1][:top_k] path.
        top_k = min(max(int(top_k), 1), 2000)
        try:
            k_hat, psi, element_index, _n = _paths.load_paths(condition, array_n, seed, cache, cache_lock)
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        return jsonify(_paths.unique_directions(k_hat, psi, element_index, top_k))

    @app.route("/api/studio/slice", methods=["POST"])
    def api_studio_slice():
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        beam = params.get("beam", "mrt")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")
        quantity = params.get("quantity", "S")

        try:
            # Coerce client-supplied fields inside the try so a malformed body
            # (e.g. {"array_n": "abc"} or {"plane": 5}) returns 400, not 500.
            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            # "at-skin" snaps the steering focus onto the nearest body surface so
            # the beam targets the skin where absorbed power matters; "free-space"
            # leaves the focus wherever the sliders placed it.
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(focus_xyz, cache=cache, cache_lock=cache_lock)
            plane = dict(params.get("plane", {}))
            plane["center"] = focus_xyz

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock)
            x, field_source = _beam_field(
                beam, paths, focus_xyz, freq_hz, condition, array_n, freq_ghz, ecbf_budget_frac
            )
            out = _slice.compute_slice(paths, x, plane, freq_hz, quantity, field_source=field_source)
        except _QPackMissing as e:
            return jsonify(
                {"error": f"exposure-operator (Q) pack not precomputed: {e.stem}", "not_precomputed": True}
            ), 409
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        scalar = out["scalar"]
        stats = {
            "shape": list(scalar.shape),
            "world": out["world"],
            "vmin": out["vmin"],
            "vmax": out["vmax"],
            "units": out["units"],
            "peak_xyz": out["peak_xyz"],
            "peak_value": out["peak_value"],
            "quantity": out["quantity"],
            "provenance": f"studio runtime | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz",
        }
        buf = np.ascontiguousarray(scalar, dtype=np.float32).tobytes()
        resp = app.make_response(buf)
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/studio/volume", methods=["POST"])
    def api_studio_volume():
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        beam = params.get("beam", "mrt")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            extent_m = float(params.get("extent_m", 0.16))
            res = int(params.get("res", 32))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(focus_xyz, cache=cache, cache_lock=cache_lock)

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock)
            x, field_source = _beam_field(
                beam, paths, focus_xyz, freq_hz, condition, array_n, freq_ghz, ecbf_budget_frac
            )
            out = _volume.compute_volume(paths, x, focus_xyz, freq_hz, extent_m, res, field_source=field_source)
        except _QPackMissing as e:
            return jsonify(
                {"error": f"exposure-operator (Q) pack not precomputed: {e.stem}", "not_precomputed": True}
            ), 409
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        scalar = out["scalar"]
        stats = {
            "shape": out["shape"],
            "origin": out["origin"],
            "spacing": out["spacing"],
            "vmin": out["vmin"],
            "vmax": out["vmax"],
            "units": out["units"],
            "peak_xyz": out["peak_xyz"],
            "peak_value": out["peak_value"],
            "quantity": out["quantity"],
            "provenance": f"studio runtime volume | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz",
        }
        buf = np.ascontiguousarray(scalar, dtype=np.float32).tobytes()
        resp = app.make_response(buf)
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/studio/phantom")
    def api_studio_phantom():
        from flask import request

        mesh = request.args.get("mesh", "thelonious")
        if not _phantom.is_known_mesh(mesh):
            return jsonify({"error": f"unknown mesh: {mesh}"}), 404
        try:
            buf, stats = _phantom.build_phantom_payload(mesh, cache, cache_lock)
        except FileNotFoundError:
            # Same not-precomputed sentinel the bodymap endpoint uses.
            return jsonify({"error": f"phantom pack not precomputed: {mesh}", "not_precomputed": True}), 409
        resp = app.make_response(buf)
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/studio/bodymap")
    def api_studio_bodymap():
        from flask import request

        condition = request.args.get("condition", "los")
        array_n = request.args.get("array_n", default=16, type=int)
        beam = request.args.get("beam", "mrt")
        quantity = request.args.get("quantity", "mrt")
        frequency_ghz = request.args.get("frequency_ghz", default=28.0, type=float)
        realisation = request.args.get("realisation", default=0, type=int)
        statistic = request.args.get("statistic", "single")
        out = _bodymap.get_bodymap(
            condition,
            array_n,
            beam,
            quantity,
            frequency_ghz,
            realisation,
            statistic=statistic,
            cache=cache,
            cache_lock=cache_lock,
        )
        if out.get("not_precomputed"):
            return jsonify({"error": out["error"], "not_precomputed": True}), 409
        return jsonify(out)

    @app.route("/api/studio/bodymap-live", methods=["POST"])
    def api_studio_bodymap_live():
        """Live per-triangle deposited S_ab for the current beam + focus.

        Unlike the precomputed (focus-frozen) body map, this applies the live
        precoder to the stored field channel, so the map tracks focus, beam, and
        ECBF budget. Mirrors the slice's parameter handling and the bodymap JSON
        payload, so the frontend reuses the same body-map render path.
        """
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        beam = params.get("beam", "mrt")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(focus_xyz, cache=cache, cache_lock=cache_lock)

            loaded = _channel.load_channel(condition, array_n, freq_ghz, seed, cache, cache_lock)
            if loaded is None:
                stem = f"{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}"
                return jsonify({"error": f"field-channel pack not precomputed: {stem}", "not_precomputed": True}), 409
            g_tilde, _areas = loaded

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock)
            x, _field_source = _beam_field(
                beam, paths, focus_xyz, freq_hz, condition, array_n, freq_ghz, ecbf_budget_frac
            )
            if x is None:
                # The decohered baseline is a field-domain weight source, not a
                # per-element precoder, so it does not compose with G_tilde.
                return jsonify({"error": f"live body map unsupported for beam '{beam}'", "not_precomputed": True}), 409
            out = _channel.compute_live_bodymap(g_tilde, x)
        except _QPackMissing as e:
            return jsonify(
                {"error": f"exposure-operator (Q) pack not precomputed: {e.stem}", "not_precomputed": True}
            ), 409
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        out["provenance"] = (
            f"studio runtime live body map | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz"
        )
        return jsonify(out)

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

    from . import (
        _array,
        _bodymap,
        _channel,
        _compliance,
        _paths,
        _phantom,
        _precoders,
        _presets,
        _scene,
        _slice,
        _volume,
    )

    def _beam_field(
        beam,
        paths,
        focus_xyz,
        freq_hz,
        condition,
        array_n,
        freq_ghz,
        ecbf_budget_frac,
        mesh="thelonious",
        focus_mode="free-space",
        seed=0,
        ue_antenna="dipole",
        ue_idx=_channel.DEFAULT_UE_IDX,
    ):
        """Resolve a beam to ``(x, field_source)`` for the field reconstructors.

        Most beams collapse a per-element precoder ``x`` (field_source None); the
        decohered baseline is a precomputed weight source instead (x None). ECBF
        loads its precomputed Q (per-phantom) and raises :class:`_QPackMissing`
        when absent.

        ``ue_antenna`` selects the UE receive pattern that shapes the matched
        filter, so MRT / decoy / decohered / ECBF respond to it; the worst-case
        beam maximises absorption directly and is antenna-independent.
        """
        if beam == "decohered":
            # Canonical decohered baseline: scramble inter-direction phase after
            # collapse (not expressible as a per-element precoder).
            x_base = _precoders.build_precoder("mrt", paths, focus_xyz, freq_hz, power=1.0, ue_antenna=ue_antenna)
            return None, _slice.decohered_field_source(paths, x_base)
        if beam == "ecbf":
            # Q must match the seed of the channel/UE the map is shown at, so the
            # exposure budget and the displayed S_ab refer to the same realisation.
            q = _paths.load_q(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock)
            if q is None:
                raise _QPackMissing(f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}")
            x = _precoders.build_ecbf_from_q(
                paths, focus_xyz, freq_hz, q, power=1.0, budget_frac=ecbf_budget_frac, ue_antenna=ue_antenna
            )
            return x, None
        if beam == "gep":
            # GEP is the unconstrained dual to ECBF (x propto Q^{-1} conj(h)), so
            # it reads the same per-realisation Q pack and reports the same
            # not-precomputed sentinel when absent.
            q = _paths.load_q(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock)
            if q is None:
                raise _QPackMissing(f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}")
            x = _precoders.build_gep_from_q(paths, focus_xyz, freq_hz, q, power=1.0, ue_antenna=ue_antenna)
            return x, None
        if beam == "worstcase" and focus_mode == "at-skin":
            # On the body: build the worst-case ABSORPTION beam from the tissue
            # channel at the snapped focus, so the deposited map there reaches the
            # worst-case body-map envelope. In free-space mode there is no surface,
            # so build_precoder falls back to the free-space field worst case.
            from aegis.tissue.dielectric import skin_props

            normal = _phantom.focus_surface_normal(focus_xyz, mesh, cache, cache_lock, ue_idx)
            n_tilde, sigma = skin_props(freq_ghz)
            x = _precoders.build_precoder(
                "worstcase",
                paths,
                focus_xyz,
                freq_hz,
                power=1.0,
                body_normal=normal,
                n_tilde=n_tilde,
                sigma=sigma,
            )
            return x, None
        return _precoders.build_precoder(beam, paths, focus_xyz, freq_hz, power=1.0, ue_antenna=ue_antenna), None

    def _parse_ue_antenna(params):
        """Validated UE receive-antenna kind from a request body (default dipole)."""
        ue_antenna = params.get("ue_antenna", "dipole")
        if ue_antenna not in _presets._UE_ANTENNAS:
            raise ValueError(f"unknown ue_antenna {ue_antenna!r}; expected one of {_presets._UE_ANTENNAS}")
        return ue_antenna

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
        # Corridor UE the body stands at: the BS->UE multipath geometry changes
        # with the standing position, so the drawn arrival rays follow the slider.
        ue_idx = request.args.get("ue_idx", default=_channel.DEFAULT_UE_IDX, type=int)
        # Bound allocation against a huge top_k and keep a negative value from
        # silently slicing entries off the end via the [::-1][:top_k] path.
        top_k = min(max(int(top_k), 1), 2000)
        try:
            k_hat, psi, element_index, _n = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
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
        mesh = params.get("mesh", "thelonious")
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
            # Corridor UE the body stands at: selects the per-UE ray pack so the
            # field cut reflects the beam steered to this standing position.
            ue_idx = int(params.get("ue_idx", _channel.DEFAULT_UE_IDX))
            # "at-skin" snaps the steering focus onto the nearest body surface so
            # the beam targets the skin where absorbed power matters; "free-space"
            # leaves the focus wherever the sliders placed it.
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(
                    focus_xyz, mesh, cache=cache, cache_lock=cache_lock, ue_idx=ue_idx
                )
            ue_antenna = _parse_ue_antenna(params)
            plane = dict(params.get("plane", {}))
            plane["center"] = focus_xyz

            # The field cut is body-independent, but the BS->UE paths it is built
            # from are per-UE, so the cut follows the body down the corridor.
            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            x, field_source = _beam_field(
                beam,
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                ecbf_budget_frac,
                mesh,
                focus_mode,
                seed,
                ue_antenna=ue_antenna,
                ue_idx=ue_idx,
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
            "provenance": (
                f"studio runtime | {mesh} | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz"
            ),
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
        mesh = params.get("mesh", "thelonious")
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
            ue_antenna = _parse_ue_antenna(params)
            # Corridor UE the body stands at: selects the per-UE ray pack so the
            # field box reflects the beam steered to this standing position.
            ue_idx = int(params.get("ue_idx", _channel.DEFAULT_UE_IDX))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(
                    focus_xyz, mesh, cache=cache, cache_lock=cache_lock, ue_idx=ue_idx
                )

            # The field box is body-independent, but the BS->UE paths it is built
            # from are per-UE, so the box follows the body down the corridor.
            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            x, field_source = _beam_field(
                beam,
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                ecbf_budget_frac,
                mesh,
                focus_mode,
                seed,
                ue_antenna=ue_antenna,
                ue_idx=ue_idx,
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
            "provenance": (
                f"studio runtime volume | {mesh} | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz"
            ),
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
        # The body stands at a corridor UE position; non-default positions carry
        # a _ue{idx} suffix on the phantom pack. Accept it from the query string
        # (GET) or, defensively, a JSON body so the client can pick either form.
        ue_idx = request.args.get("ue_idx", default=None, type=int)
        if ue_idx is None:
            body = request.get_json(silent=True) or {}
            ue_idx = int(body.get("ue_idx", _channel.DEFAULT_UE_IDX))
        if not _phantom.is_known_mesh(mesh):
            return jsonify({"error": f"unknown mesh: {mesh}"}), 404
        try:
            buf, stats = _phantom.build_phantom_payload(mesh, cache, cache_lock, ue_idx)
        except FileNotFoundError:
            # Same not-precomputed sentinel the bodymap endpoint uses.
            return jsonify({"error": f"phantom pack not precomputed: {mesh}", "not_precomputed": True}), 409
        resp = app.make_response(buf)
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/studio/scene")
    def api_studio_scene():
        from flask import request

        condition = request.args.get("condition", "los")
        seed = request.args.get("seed", default=0, type=int)
        out = _scene.get_scene(condition, seed, cache, cache_lock)
        if out.get("not_precomputed"):
            return jsonify(out), 409
        return jsonify(out)

    @app.route("/api/studio/bodymap")
    def api_studio_bodymap():
        from flask import request

        condition = request.args.get("condition", "los")
        array_n = request.args.get("array_n", default=16, type=int)
        beam = request.args.get("beam", "mrt")
        quantity = request.args.get("quantity", "mrt")
        frequency_ghz = request.args.get("frequency_ghz", default=10.0, type=float)
        realisation = request.args.get("realisation", default=0, type=int)
        statistic = request.args.get("statistic", "single")
        mesh = request.args.get("mesh", "thelonious")
        out = _bodymap.get_bodymap(
            condition,
            array_n,
            beam,
            quantity,
            frequency_ghz,
            realisation,
            statistic=statistic,
            mesh=mesh,
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
        mesh = params.get("mesh", "thelonious")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            ue_antenna = _parse_ue_antenna(params)
            # Corridor UE the body stands at; selects the per-UE ray / channel /
            # phantom packs so the live deposited map follows the body down the
            # corridor. Defaults to the mid-corridor UE (empty suffix).
            ue_idx = int(params.get("ue_idx", _channel.DEFAULT_UE_IDX))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(
                    focus_xyz, mesh, cache=cache, cache_lock=cache_lock, ue_idx=ue_idx
                )

            loaded = _channel.load_channel(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock, ue_idx)
            if loaded is None:
                stem = f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}{_channel.ue_suffix(ue_idx)}"
                return jsonify({"error": f"field-channel pack not precomputed: {stem}", "not_precomputed": True}), 409
            g_tilde, _areas = loaded

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            x, _field_source = _beam_field(
                beam,
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                ecbf_budget_frac,
                mesh,
                focus_mode,
                seed,
                ue_antenna=ue_antenna,
                ue_idx=ue_idx,
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
            f"studio runtime live body map | {mesh} | {condition} bs{array_n} seed{seed} "
            f"| beam={beam} | {freq_ghz:g}GHz"
        )
        return jsonify(out)

    @app.route("/api/studio/compliance", methods=["POST"])
    def api_studio_compliance():
        """ICNIRP compliance scalars for the current beam + focus.

        Returns the absorbed power, whole-body SAR, the 4 cm^2 spatially-averaged
        peak absorbed power density (psSAR proxy), the peak / mean ratio, and the
        served signal relative to MRT. Mirrors bodymap-live's parameter handling
        (it applies the same live precoder to the same field channel). The 4 cm^2
        averaging matrix is cached per phantom, so the first request for a mesh
        pays the build cost and the rest are cheap; the frontend gates this behind
        an opt-in toggle for that reason.
        """
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        beam = params.get("beam", "mrt")
        mesh = params.get("mesh", "thelonious")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            from aegis.hotspot import channel_at, make_rx_response

            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            ue_antenna = _parse_ue_antenna(params)
            ue_idx = int(params.get("ue_idx", _channel.DEFAULT_UE_IDX))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(
                    focus_xyz, mesh, cache=cache, cache_lock=cache_lock, ue_idx=ue_idx
                )

            loaded = _channel.load_channel(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock, ue_idx)
            if loaded is None:
                stem = f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}{_channel.ue_suffix(ue_idx)}"
                return jsonify({"error": f"field-channel pack not precomputed: {stem}", "not_precomputed": True}), 409
            g_tilde, areas = loaded

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            x, _field_source = _beam_field(
                beam,
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                ecbf_budget_frac,
                mesh,
                focus_mode,
                seed,
                ue_antenna=ue_antenna,
                ue_idx=ue_idx,
            )
            if x is None:
                # The decohered baseline is a field-domain weight source, not a
                # per-element precoder, so it has no x to score.
                return jsonify({"error": f"compliance unsupported for beam '{beam}'", "not_precomputed": True}), 409

            # Signal channel + MRT reference at the (possibly snapped) focus, so
            # signal_rel measures this beam against the matched filter it competes
            # with at the same operating point.
            k_hat, psi, element_index, n_elements = paths
            ue_rx = make_rx_response(ue_antenna, freq_hz)
            h = channel_at(focus_xyz, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
            x_mrt = _precoders.build_precoder("mrt", paths, focus_xyz, freq_hz, power=1.0, ue_antenna=ue_antenna)

            g_avg = _compliance.averaging_matrix(mesh, ue_idx, cache, cache_lock)
            out = _compliance.compute_scalars(g_tilde, areas, x, h, x_mrt, g_avg, _compliance.body_mass_kg(mesh))
        except _QPackMissing as e:
            return jsonify(
                {"error": f"exposure-operator (Q) pack not precomputed: {e.stem}", "not_precomputed": True}
            ), 409
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        out["provenance"] = (
            f"studio compliance | {mesh} | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz"
        )
        return jsonify(out)

    @app.route("/api/studio/precoder", methods=["POST"])
    def api_studio_precoder():
        """Per-element precoder ``x`` + array geometry for the live Tx lobe.

        Returns the synthesised precoder weights and the physical element layout
        they index against, so the frontend can draw the realised transmit
        radiation pattern ``|sum_j x_j exp(+i k0 r_j . d)|^2`` rather than a
        uniform-excitation stand-in. Mirrors bodymap-live's parameter handling.
        The decohered baseline scrambles inter-direction phase after collapse and
        is not a per-element precoder, so it reports ``available: false``.
        """
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        beam = params.get("beam", "mrt")
        mesh = params.get("mesh", "thelonious")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            ecbf_budget_frac = float(params.get("ecbf_budget_frac", 0.5))
            ue_antenna = _parse_ue_antenna(params)
            ue_idx = int(params.get("ue_idx", _channel.DEFAULT_UE_IDX))
            if focus_mode == "at-skin":
                focus_xyz = _phantom.snap_focus_to_skin(
                    focus_xyz, mesh, cache=cache, cache_lock=cache_lock, ue_idx=ue_idx
                )

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            x, _field_source = _beam_field(
                beam,
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                ecbf_budget_frac,
                mesh,
                focus_mode,
                seed,
                ue_antenna=ue_antenna,
                ue_idx=ue_idx,
            )
        except _QPackMissing as e:
            return jsonify(
                {"error": f"exposure-operator (Q) pack not precomputed: {e.stem}", "not_precomputed": True}
            ), 409
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        if x is None:
            return jsonify({"available": False, "reason": f"beam '{beam}' has no per-element precoder"})

        x = np.asarray(x).reshape(-1)
        e_y, e_zp = _array.array_axes()
        return jsonify(
            {
                "available": True,
                "beam": beam,
                "n_h": int(array_n),
                "n_v": int(array_n),
                "axis_h": e_y.tolist(),
                "axis_v": e_zp.tolist(),
                "spacing_m": _array.element_spacing_m(),
                # k0 for the array factor must match the frequency x was designed
                # at (channel_at uses the dosimetry freq), so the MRT lobe points
                # at the focus. The element spacing stays physical (28 GHz panel).
                "freq_hz": freq_hz,
                "real": np.real(x).astype(float).tolist(),
                "imag": np.imag(x).astype(float).tolist(),
                "provenance": (
                    f"studio precoder | {mesh} | {condition} bs{array_n} seed{seed} | beam={beam} | {freq_ghz:g}GHz"
                ),
            }
        )

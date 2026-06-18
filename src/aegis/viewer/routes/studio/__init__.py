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
        _absolute_ecbf,
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

    def _absolute_ecbf_beam(
        paths,
        focus_xyz,
        freq_hz,
        condition,
        array_n,
        freq_ghz,
        seed,
        mesh,
        ue_idx,
        ue_antenna,
        sar_wb_on,
        peak_sab_on,
        tx_power_w,
        scenario="general_public",
    ):
        """Absolute-limit ECBF result dict (loads channel + averaging matrix + h).

        Single source of truth for the absolute ECBF beam: it loads the field
        channel (per-phantom), the cached 4 cm^2 averaging matrix, and the signal
        channel h at the focus, then solves the two-restriction QCQP at the
        absolute transmit power. Raises :class:`_QPackMissing` (the channel stem)
        when the field-channel pack is absent, so the same not-precomputed 409 the
        relative path uses is returned. Both ``_beam_field`` (for the rendered
        beam) and the compliance route (for the regime readout) call this.
        """
        from aegis.hotspot import channel_at, make_rx_response

        loaded = _channel.load_channel(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock, ue_idx)
        if loaded is None:
            stem = f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}{_channel.ue_suffix(ue_idx)}"
            raise _QPackMissing(stem)
        g_tilde, areas = loaded
        k_hat, psi, element_index, n_elements = paths
        ue_rx = make_rx_response(ue_antenna, freq_hz)
        h = channel_at(focus_xyz, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
        g_avg = _compliance.averaging_matrix(mesh, ue_idx, cache, cache_lock)
        return _absolute_ecbf.build_ecbf_absolute(
            g_tilde,
            areas,
            g_avg,
            h,
            freq_hz,
            _compliance.body_mass_kg(mesh),
            tx_power_w,
            sar_wb_on=sar_wb_on,
            peak_on=peak_sab_on,
            scenario=scenario,
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
        constraint_mode="relative",
        sar_wb_on=True,
        peak_sab_on=True,
        tx_power_w=1.0,
    ):
        """Resolve a beam to ``(x, field_source)`` for the field reconstructors.

        Most beams collapse a per-element precoder ``x`` (field_source None); the
        decohered baseline is a precomputed weight source instead (x None). ECBF
        loads its precomputed Q (per-phantom) and raises :class:`_QPackMissing`
        when absent.

        ``constraint_mode`` switches ECBF between the relative budget (default,
        a fraction of the MRT absorption, render-only) and the absolute ICNIRP
        restrictions solved at ``tx_power_w`` watts (``sar_wb_on`` / ``peak_sab_on``
        toggle which basic restriction binds).

        ``ue_antenna`` selects the UE receive pattern that shapes the matched
        filter, so MRT / decoy / decohered / ECBF respond to it; the worst-case
        beam maximises absorption directly and is antenna-independent.
        """
        if beam == "ecbf" and constraint_mode == "absolute":
            res = _absolute_ecbf_beam(
                paths,
                focus_xyz,
                freq_hz,
                condition,
                array_n,
                freq_ghz,
                seed,
                mesh,
                ue_idx,
                ue_antenna,
                sar_wb_on,
                peak_sab_on,
                tx_power_w,
            )
            return res["x"], None
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

    def _parse_constraint_args(params):
        """ECBF constraint-mode kwargs for ``_beam_field`` from a request body.

        ``relative`` (default) keeps the render-only budget ECBF; ``absolute``
        switches to the two-restriction ICNIRP solve at ``tx_power_w`` watts. The
        SAR_wb / peak toggles default on so absolute mode enforces both unless the
        client opts out.
        """
        constraint_mode = params.get("constraint_mode", "relative")
        if constraint_mode not in ("relative", "absolute"):
            raise ValueError(f"unknown constraint_mode {constraint_mode!r}; expected 'relative' or 'absolute'")
        return {
            "constraint_mode": constraint_mode,
            "sar_wb_on": bool(params.get("sar_wb_on", True)),
            "peak_sab_on": bool(params.get("peak_sab_on", True)),
            "tx_power_w": float(params.get("tx_power_w", 1.0)),
        }

    def _compliance_limits(freq_hz):
        """ICNIRP limit values for the current frequency, for the absolute readout.

        ``sab_4cm2`` is ``None`` at or below 6 GHz (the peak restriction does not
        apply there); the frontend hides the peak toggle in that case.
        """
        from aegis.compliance import ExposureScenario, icnirp_limits

        limits = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, freq_hz=float(freq_hz))
        return {
            "sar_wb": float(limits.sar_wb),
            "sab_4cm2": (float(limits.sab_4cm2) if limits.sab_4cm2 is not None else None),
            "scenario": "general_public",
        }

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
            constraint_args = _parse_constraint_args(params)
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
                **constraint_args,
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
            constraint_args = _parse_constraint_args(params)
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
                **constraint_args,
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

            constraint_args = _parse_constraint_args(params)
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
                **constraint_args,
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

            constraint_args = _parse_constraint_args(params)
            absolute = beam == "ecbf" and constraint_args["constraint_mode"] == "absolute"

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)

            # Signal channel + MRT reference at the (possibly snapped) focus, so
            # signal_rel measures this beam against the matched filter it competes
            # with at the same operating point. In absolute mode both the beam and
            # the MRT reference run at tx_power_w watts, so the readout densities
            # are absolute (W, W/kg, W/m^2) and comparable to the ICNIRP limits.
            k_hat, psi, element_index, n_elements = paths
            ue_rx = make_rx_response(ue_antenna, freq_hz)
            h = channel_at(focus_xyz, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
            snr_mrt_db = float(params.get("snr_mrt_db", 20.0))
            g_avg = _compliance.averaging_matrix(mesh, ue_idx, cache, cache_lock)

            abs_res = None
            if absolute:
                abs_res = _absolute_ecbf_beam(
                    paths,
                    focus_xyz,
                    freq_hz,
                    condition,
                    array_n,
                    freq_ghz,
                    seed,
                    mesh,
                    ue_idx,
                    ue_antenna,
                    constraint_args["sar_wb_on"],
                    constraint_args["peak_sab_on"],
                    constraint_args["tx_power_w"],
                )
                x = abs_res["x"]
                p_tx = float(constraint_args["tx_power_w"])
                x_mrt = np.sqrt(p_tx) * np.conj(h) / np.linalg.norm(h)
            else:
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
                    **constraint_args,
                )
                if x is None:
                    # The decohered baseline is a field-domain weight source, not a
                    # per-element precoder, so it has no x to score.
                    return jsonify({"error": f"compliance unsupported for beam '{beam}'", "not_precomputed": True}), 409
                x_mrt = _precoders.build_precoder("mrt", paths, focus_xyz, freq_hz, power=1.0, ue_antenna=ue_antenna)

            out = _compliance.compute_scalars(
                g_tilde, areas, x, h, x_mrt, g_avg, _compliance.body_mass_kg(mesh), snr_mrt_db=snr_mrt_db
            )
            if abs_res is not None:
                # Absolute mode: surface the binding restriction and the per-limit
                # utilisation so the HUD can show the regime and margin bars.
                limits = _compliance_limits(freq_hz)
                out["constraint_mode"] = "absolute"
                out["tx_power_w"] = float(constraint_args["tx_power_w"])
                out["regime"] = abs_res["regime"]
                out["per_constraint"] = abs_res["per_constraint"]
                out["n_regions_active"] = abs_res["n_regions_active"]
                out["ecbf_converged"] = abs_res["converged"]
                out["icnirp_limits"] = limits
            else:
                out["constraint_mode"] = "relative"
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

    @app.route("/api/studio/compliance-sweep", methods=["POST"])
    def api_studio_compliance_sweep():
        """ECBF compliance scalars swept across the absorbed-power budget.

        The budget slider only steers ECBF, so this traces the ECBF
        exposure/signal Pareto front: for each ``budget_frac`` it re-solves the
        QCQP against the same precomputed Q and scores the resulting beam. Every
        input except the precoder is fixed across the sweep (channel, Q, averaging
        matrix, MRT reference), so all of them are loaded once and only
        ``solve_ecbf`` runs per point. The 409 sentinels match the compliance
        route (no field-channel / Q pack). Used by the budget-sweep chart, which
        marks the live budget on these curves.
        """
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        mesh = params.get("mesh", "thelonious")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            import numpy as np

            from aegis.hotspot import channel_at, make_rx_response

            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            snr_mrt_db = float(params.get("snr_mrt_db", 20.0))
            n_points = int(np.clip(int(params.get("n_points", 20)), 4, 64))
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

            q = _paths.load_q(condition, array_n, freq_ghz, seed, mesh, cache, cache_lock)
            if q is None:
                stem = f"{mesh}_{condition}_bs{int(array_n)}_{freq_ghz:g}_seed{int(seed)}"
                return jsonify(
                    {"error": f"exposure-operator (Q) pack not precomputed: {stem}", "not_precomputed": True}
                ), 409

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            k_hat, psi, element_index, n_elements = paths
            ue_rx = make_rx_response(ue_antenna, freq_hz)
            h = channel_at(focus_xyz, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
            x_mrt = _precoders.build_precoder("mrt", paths, focus_xyz, freq_hz, power=1.0, ue_antenna=ue_antenna)
            g_avg = _compliance.averaging_matrix(mesh, ue_idx, cache, cache_lock)
            body_mass = _compliance.body_mass_kg(mesh)

            fracs = np.linspace(0.05, 1.0, n_points)
            keys = (
                "p_abs_w",
                "sar_wb",
                "pssar_4cm2",
                "peak_sab",
                "eta_4cm2",
                "signal_rel",
                "spectral_efficiency_bps_hz",
            )
            series: dict[str, list] = {k: [] for k in keys}
            for frac in fracs:
                x = _precoders.build_ecbf_from_q(
                    paths, focus_xyz, freq_hz, q, power=1.0, budget_frac=float(frac), ue_antenna=ue_antenna
                )
                row = _compliance.compute_scalars(g_tilde, areas, x, h, x_mrt, g_avg, body_mass, snr_mrt_db=snr_mrt_db)
                for k in keys:
                    series[k].append(row[k])
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        return jsonify(
            {
                "budget_frac": [float(f) for f in fracs],
                "series": series,
                "snr_mrt_db": snr_mrt_db,
                "units": {
                    "p_abs_w": "W per W tx",
                    "sar_wb": "W/kg per W tx",
                    "pssar_4cm2": "W/m^2 per W tx",
                    "peak_sab": "W/m^2 per W tx",
                    "eta_4cm2": "-",
                    "signal_rel": "-",
                    "spectral_efficiency_bps_hz": "bit/s/Hz",
                },
                "provenance": (
                    f"studio compliance sweep | {mesh} | {condition} bs{array_n} seed{seed} | "
                    f"ecbf | {freq_ghz:g}GHz | {n_points} pts"
                ),
            }
        )

    @app.route("/api/studio/power-sweep", methods=["POST"])
    def api_studio_power_sweep():
        """Absolute-ICNIRP ECBF vs MRT absorbed power swept across transmit power.

        The headline of absolute mode. As the total transmit power rises, the
        matched filter (MRT) absorbed power climbs without bound (it "diverges"
        straight through the ICNIRP basic restriction), while the absolute-limit
        ECBF beam tracks it until a restriction binds and then flattens against the
        fixed limit. For each transmit power it re-solves the two-restriction QCQP
        and also scores the MRT reference at the same power, so the chart can draw
        both curves and the horizontal ICNIRP limit they are measured against. MRT
        is exactly linear in power (the matched filter is fixed), so it is scored
        once at unit power and scaled. Only the field-channel pack is required (the
        absolute solver uses the channel + 4 cm^2 averaging matrix directly, no Q
        pack), so the 409 sentinel matches the channel-load path of the other
        routes. Independent of the live transmit power: the dBm slider only marks a
        cursor on these curves, so it is not in the fetch key.
        """
        params, err = get_json_dict()
        if err is not None:
            return err
        condition = params.get("condition", "los")
        mesh = params.get("mesh", "thelonious")
        focus_xyz = params.get("focus_xyz", [0.923, -0.005, 0.734])
        focus_mode = params.get("focus_mode", "free-space")

        try:
            from aegis.hotspot import channel_at, make_rx_response

            from ._channel import deposited_sab

            array_n = int(params.get("array_n", 16))
            seed = int(params.get("seed", 0))
            freq_ghz = float(params.get("frequency_ghz", 10))
            freq_hz = freq_ghz * 1e9
            n_points = int(np.clip(int(params.get("n_points", 24)), 4, 48))
            sar_wb_on = bool(params.get("sar_wb_on", True))
            peak_sab_on = bool(params.get("peak_sab_on", True))
            power_min_dbm = float(params.get("power_min_dbm", 0.0))
            power_max_dbm = float(params.get("power_max_dbm", 100.0))
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
            areas = np.asarray(areas, dtype=float).ravel()

            paths = _paths.load_paths(condition, array_n, seed, cache, cache_lock, ue_idx)
            k_hat, psi, element_index, n_elements = paths
            ue_rx = make_rx_response(ue_antenna, freq_hz)
            h = channel_at(focus_xyz, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
            g_avg = _compliance.averaging_matrix(mesh, ue_idx, cache, cache_lock)
            mass = _compliance.body_mass_kg(mesh)
            limits = _compliance_limits(freq_hz)

            # MRT is the matched filter; its absorbed densities are exactly linear
            # in transmit power, so score it once at unit power and scale per point.
            x_mrt_unit = np.conj(h) / max(float(np.linalg.norm(h)), 1e-30)
            sab_mrt_unit = deposited_sab(g_tilde, x_mrt_unit)
            p_abs_mrt_unit = float(np.sum(sab_mrt_unit * areas))
            avg_mrt_unit = np.asarray(g_avg @ sab_mrt_unit).ravel()
            peak_mrt_unit = float(avg_mrt_unit.max()) if avg_mrt_unit.size else 0.0

            powers_dbm = np.linspace(power_min_dbm, power_max_dbm, n_points)
            powers_w = 10.0 ** ((powers_dbm - 30.0) / 10.0)

            ecbf: dict[str, list] = {"p_abs_w": [], "sar_wb": [], "peak_sab": [], "regime": []}
            mrt: dict[str, list] = {"p_abs_w": [], "sar_wb": [], "peak_sab": []}
            for p_w in powers_w:
                res = _absolute_ecbf.build_ecbf_absolute(
                    g_tilde,
                    areas,
                    g_avg,
                    h,
                    freq_hz,
                    mass,
                    float(p_w),
                    sar_wb_on=sar_wb_on,
                    peak_on=peak_sab_on,
                )
                per = {c["name"]: c for c in res["per_constraint"]}
                ecbf["p_abs_w"].append(res["p_abs_w"])
                ecbf["sar_wb"].append(per["sar_wb"]["value"] if "sar_wb" in per else None)
                ecbf["peak_sab"].append(per["peak_sab"]["value"] if "peak_sab" in per else None)
                ecbf["regime"].append(res["regime"])
                p_abs_mrt = p_abs_mrt_unit * float(p_w)
                mrt["p_abs_w"].append(p_abs_mrt)
                mrt["sar_wb"].append((p_abs_mrt / float(mass)) if (mass and float(mass) > 0) else None)
                mrt["peak_sab"].append(peak_mrt_unit * float(p_w))
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except (KeyError, ValueError, TypeError, NotImplementedError) as e:
            return jsonify({"error": str(e)}), 400

        # The absolute whole-body limit on total absorbed power is L_wb * mass [W],
        # so the P_abs curve can be drawn against a single horizontal reference.
        p_abs_wb_w = (limits["sar_wb"] * float(mass)) if (mass and float(mass) > 0) else None
        return jsonify(
            {
                "power_dbm": [float(d) for d in powers_dbm],
                "power_w": [float(w) for w in powers_w],
                "ecbf": ecbf,
                "mrt": mrt,
                "limits": {**limits, "p_abs_wb_w": p_abs_wb_w},
                "mass_kg": (float(mass) if (mass and float(mass) > 0) else None),
                "sar_wb_on": sar_wb_on,
                "peak_sab_on": peak_sab_on and limits["sab_4cm2"] is not None,
                "provenance": (
                    f"studio power sweep | {mesh} | {condition} bs{array_n} seed{seed} | "
                    f"ecbf vs mrt | {freq_ghz:g}GHz | {n_points} pts"
                ),
            }
        )

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
            constraint_args = _parse_constraint_args(params)
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
                **constraint_args,
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

"""Tests for compute route parsing helpers and stats builder.

Covers: _parse_vec3, _parse_rotation_y, _parse_freq_and_tissue,
_parse_quantities_and_scenario, _parse_mode_or_level, _build_binary_response.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("flask")

from flask import Flask  # noqa: E402

from aegis.viewer.routes.compute import (  # noqa: E402
    _build_binary_response,
    _parse_bool,
    _parse_mode_or_level,
    _parse_quantities_and_scenario,
    _parse_rotation_y,
    _parse_vec3,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


# ---------------------------------------------------------------------------
# _parse_vec3
# ---------------------------------------------------------------------------


class TestParseVec3:
    def test_valid_defaults(self) -> None:
        val, err = _parse_vec3({}, "pos")
        assert err is None
        np.testing.assert_array_equal(val, [0, 0, 0])

    def test_valid_floats(self) -> None:
        val, err = _parse_vec3({"pos": [1.5, -2.0, 3.0]}, "pos")
        assert err is None
        np.testing.assert_allclose(val, [1.5, -2.0, 3.0])

    def test_valid_ints(self) -> None:
        val, err = _parse_vec3({"pos": [1, 2, 3]}, "pos")
        assert err is None
        np.testing.assert_array_equal(val, [1, 2, 3])

    def test_wrong_length_2(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": [1, 2]}, "pos")
            assert val is None
            assert err is not None
            resp, status = err
            assert status == 400

    def test_wrong_length_4(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": [1, 2, 3, 4]}, "pos")
            assert val is None
            assert err[1] == 400

    def test_non_numeric(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": ["a", "b", "c"]}, "pos")
            assert val is None
            assert err[1] == 400

    def test_none_value(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": None}, "pos")
            assert val is None
            assert err[1] == 400

    def test_custom_default(self) -> None:
        val, err = _parse_vec3({}, "pos", default=[5, 6, 7])
        assert err is None
        np.testing.assert_array_equal(val, [5, 6, 7])

    def test_empty_list(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": []}, "pos")
            assert val is None
            assert err[1] == 400

    def test_zeros(self) -> None:
        val, err = _parse_vec3({"pos": [0, 0, 0]}, "pos")
        assert err is None
        np.testing.assert_array_equal(val, [0, 0, 0])

    def test_large_values(self) -> None:
        val, err = _parse_vec3({"pos": [1e10, -1e10, 1e-10]}, "pos")
        assert err is None
        np.testing.assert_allclose(val, [1e10, -1e10, 1e-10])

    def test_rejects_nan(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": [float("nan"), 0, 0]}, "pos")
            assert val is None
            assert err[1] == 400
            assert "finite" in err[0].get_json()["error"].lower()

    def test_rejects_inf(self, app) -> None:
        with app.app_context():
            val, err = _parse_vec3({"pos": [float("inf"), 0, 0]}, "pos")
            assert val is None
            assert err[1] == 400
            assert "finite" in err[0].get_json()["error"].lower()


# ---------------------------------------------------------------------------
# _parse_rotation_y
# ---------------------------------------------------------------------------


class TestParseRotationY:
    def test_default(self) -> None:
        val, err = _parse_rotation_y({})
        assert err is None
        assert val == 0.0

    def test_valid_float(self) -> None:
        val, err = _parse_rotation_y({"body_rotation_y": 1.57})
        assert err is None
        assert val == pytest.approx(1.57)

    def test_valid_negative(self) -> None:
        val, err = _parse_rotation_y({"body_rotation_y": -3.14})
        assert err is None
        assert val == pytest.approx(-3.14)

    def test_valid_zero(self) -> None:
        val, err = _parse_rotation_y({"body_rotation_y": 0})
        assert err is None
        assert val == 0.0

    def test_string_raises(self, app) -> None:
        with app.app_context():
            val, err = _parse_rotation_y({"body_rotation_y": "abc"})
            assert val is None
            assert err[1] == 400

    def test_none_raises(self, app) -> None:
        with app.app_context():
            val, err = _parse_rotation_y({"body_rotation_y": None})
            assert val is None
            assert err[1] == 400

    def test_int_coerced(self) -> None:
        val, err = _parse_rotation_y({"body_rotation_y": 2})
        assert err is None
        assert val == 2.0

    def test_rejects_nan(self, app) -> None:
        with app.app_context():
            val, err = _parse_rotation_y({"body_rotation_y": float("nan")})
            assert val is None
            assert err[1] == 400

    def test_rejects_inf(self, app) -> None:
        with app.app_context():
            val, err = _parse_rotation_y({"body_rotation_y": float("inf")})
            assert val is None
            assert err[1] == 400


# ---------------------------------------------------------------------------
# _parse_quantities_and_scenario
# ---------------------------------------------------------------------------


class TestParseQuantitiesAndScenario:
    def test_defaults(self) -> None:
        q, s, err = _parse_quantities_and_scenario({})
        assert err is None
        assert q == ["sab", "sab_4cm2"]
        assert s.value == "general_public"

    def test_custom_quantities(self) -> None:
        q, s, err = _parse_quantities_and_scenario({"quantities": ["sab", "sinc_local"]})
        assert err is None
        assert "sinc_local" in q

    def test_occupational_scenario(self) -> None:
        q, s, err = _parse_quantities_and_scenario({"exposure_scenario": "occupational"})
        assert err is None
        assert s.value == "occupational"

    def test_invalid_scenario(self, app) -> None:
        with app.app_context():
            q, s, err = _parse_quantities_and_scenario({"exposure_scenario": "nonexistent"})
            assert q is None
            assert err[1] == 400


# ---------------------------------------------------------------------------
# _parse_mode_or_level
# ---------------------------------------------------------------------------


class TestParseModeOrLevel:
    def test_default_level(self) -> None:
        kw, err = _parse_mode_or_level({})
        assert err is None
        assert kw == {"level": 2}

    def test_explicit_level(self) -> None:
        kw, err = _parse_mode_or_level({"level": 4})
        assert err is None
        assert kw == {"level": 4}

    def test_level_0(self) -> None:
        kw, err = _parse_mode_or_level({"level": 0})
        assert err is None
        assert kw == {"level": 0}

    def test_level_6(self) -> None:
        kw, err = _parse_mode_or_level({"level": 6})
        assert err is None
        assert kw == {"level": 6}

    def test_level_7_valid(self) -> None:
        kw, err = _parse_mode_or_level({"level": 7})
        assert err is None
        assert kw == {"level": 7}

    def test_level_8_valid(self) -> None:
        kw, err = _parse_mode_or_level({"level": 8})
        assert err is None
        assert kw == {"level": 8}

    def test_level_9_rejected(self, app) -> None:
        with app.app_context():
            kw, err = _parse_mode_or_level({"level": 9})
            assert kw is None
            assert err[1] == 400

    def test_negative_level_rejected(self, app) -> None:
        with app.app_context():
            kw, err = _parse_mode_or_level({"level": -1})
            assert kw is None
            assert err[1] == 400

    def test_non_integer_level(self, app) -> None:
        with app.app_context():
            kw, err = _parse_mode_or_level({"level": "abc"})
            assert kw is None
            assert err[1] == 400

    def test_mode_bound(self) -> None:
        kw, err = _parse_mode_or_level({"mode": "bound"})
        assert err is None
        assert kw == {"mode": "bound"}

    def test_mode_aggregate(self) -> None:
        kw, err = _parse_mode_or_level({"mode": "aggregate"})
        assert err is None
        assert kw == {"mode": "aggregate"}

    def test_mode_spatial(self) -> None:
        kw, err = _parse_mode_or_level({"mode": "spatial"})
        assert err is None
        assert "mode" in kw
        assert kw["mode"] == "spatial"
        assert "fresnel" in kw

    def test_mode_spatial_corrections(self) -> None:
        kw, err = _parse_mode_or_level({"mode": "spatial", "fresnel": True, "curvature": True})
        assert err is None
        assert kw["fresnel"] is True
        assert kw["curvature"] is True

    def test_invalid_mode(self, app) -> None:
        with app.app_context():
            kw, err = _parse_mode_or_level({"mode": "coherent"})
            assert kw is None
            assert err[1] == 400

    def test_mode_takes_precedence_over_level(self) -> None:
        kw, err = _parse_mode_or_level({"mode": "bound", "level": 4})
        assert err is None
        assert kw == {"mode": "bound"}

    def test_custom_default_level(self) -> None:
        kw, err = _parse_mode_or_level({}, default_level=5)
        assert err is None
        assert kw == {"level": 5}


# ---------------------------------------------------------------------------
# _parse_bool
# ---------------------------------------------------------------------------


class TestParseBool:
    def test_none_returns_default_true(self) -> None:
        assert _parse_bool(None, True) is True

    def test_none_returns_default_false(self) -> None:
        assert _parse_bool(None, False) is False

    def test_bool_true(self) -> None:
        assert _parse_bool(True, False) is True

    def test_bool_false(self) -> None:
        assert _parse_bool(False, True) is False

    def test_string_false(self) -> None:
        assert _parse_bool("false", True) is False

    def test_string_true(self) -> None:
        assert _parse_bool("true", False) is True

    def test_string_zero(self) -> None:
        assert _parse_bool("0", True) is False

    def test_empty_string(self) -> None:
        assert _parse_bool("", True) is False

    def test_int_zero(self) -> None:
        assert _parse_bool(0, True) is False

    def test_int_one(self) -> None:
        assert _parse_bool(1, False) is True


# ---------------------------------------------------------------------------
# _build_binary_response
# ---------------------------------------------------------------------------


class TestBuildBinaryResponse:
    def _mock_result(self):
        from unittest.mock import MagicMock

        r = MagicMock()
        r.sab = np.array([1.0, 2.0, 3.0])
        r.sab_averaged = np.array([0.5, 1.0, 1.5])
        r.sab_1cm2_averaged = None
        r.sinc = np.array([10.0, 20.0, 30.0])
        r.sinc_averaged = np.array([8.0, 16.0, 24.0])
        return r

    def test_sab_always_included(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, [])
        assert len(meta) == 1
        assert meta[0]["key"] == "sab"
        assert meta[0]["length"] == 3

    def test_multiple_quantities(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["sab", "sab_4cm2", "sinc_local"])
        keys = [m["key"] for m in meta]
        assert "sab" in keys
        assert "sab_4cm2" in keys
        assert "sinc_local" in keys
        assert len(meta) == 3

    def test_none_quantity_skipped(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["sab_1cm2"])
        # sab_1cm2 is None, so only sab is included
        keys = [m["key"] for m in meta]
        assert "sab_1cm2" not in keys

    def test_unknown_quantity_skipped(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["nonexistent_key"])
        assert len(meta) == 1  # only sab

    def test_binary_roundtrip(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["sab"])
        arr = np.frombuffer(bytes(buf), dtype=np.float32)
        np.testing.assert_allclose(arr, r.sab, rtol=1e-6)

    def test_offsets_are_correct(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["sab", "sab_4cm2", "sinc_local"])
        for m in meta:
            offset = m["offset"]
            length = m["length"]
            arr = np.frombuffer(bytes(buf)[offset : offset + length * 4], dtype=np.float32)
            assert len(arr) == length

    def test_sab_duplicate_not_repeated(self) -> None:
        r = self._mock_result()
        buf, meta = _build_binary_response(r, ["sab", "sab"])
        keys = [m["key"] for m in meta]
        assert keys.count("sab") == 1


# ---------------------------------------------------------------------------
# _build_stats_response
# ---------------------------------------------------------------------------


class TestBuildStatsResponse:
    """Tests for _build_stats_response compliance fallback paths."""

    def test_sab_averaged_none_falls_back_to_raw_peak(self):
        """When sab_averaged is None, compliance should use raw sab peak."""
        from types import SimpleNamespace

        from aegis.result import DosimetryResult
        from aegis.viewer.routes.compute import _build_stats_response

        sab = np.array([5.0, 10.0, 15.0])
        result = DosimetryResult(
            freq_hz=28e9,
            sab=sab,
            sab_averaged=None,
            sab_1cm2_averaged=None,
            sinc=None,
            sinc_averaged=None,
            sar_wb=None,
            p_abs=0.01,
            fidelity_level=2,
        )
        body = SimpleNamespace(areas=np.array([1e-4, 1e-4, 1e-4]), n_triangles=3)
        tissue = SimpleNamespace(freq_hz=28e9, T0=0.4, eps_r=10.0, sigma=20.0)

        stats = _build_stats_response(result, body, tissue, level=2)

        # Compliance must be evaluated (not None) even though sab_averaged is None
        assert stats["compliance"] is not None
        checks = stats["compliance"]["checks"]
        sab_check = [c for c in checks if "4 cm" in c["label"]]
        assert len(sab_check) == 1
        # The fallback value should be the raw sab peak (15.0)
        assert sab_check[0]["value"] == round(15.0, 4)

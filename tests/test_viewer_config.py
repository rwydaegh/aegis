"""Viewer config helpers (scenarios, merge)."""

from __future__ import annotations

from aegis.viewer.config import apply_scenario_to_config, scenario_launch


def test_scenario_launch_open_ground_in_defaults():
    from aegis.viewer.config import DEFAULTS

    launch = scenario_launch(DEFAULTS, "open_ground")
    assert "voxel_dir" in launch
    assert launch["voxel_dir"] is None
    assert launch.get("voxel_json") is None


def test_scenario_launch_unknown_is_empty():
    assert scenario_launch({}, "missing") == {}
    assert scenario_launch({"scenarios": {}}, "open_ground") == {}


def test_apply_scenario_to_config_sets_active_fields():
    cfg = {
        "scenarios": {
            "demo": {
                "description": "Test scenario",
                "launch": {"bbox": 25.0},
            },
        },
        "other": 1,
    }
    out = apply_scenario_to_config(cfg, "demo")
    assert out["active_scenario"] == "demo"
    assert out["active_scenario_description"] == "Test scenario"
    assert out["other"] == 1
    assert out["scenarios"]["demo"]["launch"]["bbox"] == 25.0

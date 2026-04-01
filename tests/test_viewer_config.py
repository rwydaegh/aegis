"""Viewer config helpers (scenarios, merge)."""

from __future__ import annotations

from pathlib import Path

from aegis.viewer.config import (
    _deep_merge,
    apply_scenario_to_config,
    load_config,
    scenario_launch,
)


def test_scenario_launch_open_ground_in_defaults():
    from aegis.viewer.config import DEFAULTS

    launch = scenario_launch(DEFAULTS, "open_ground")
    assert "voxel_dir" in launch
    assert launch["voxel_dir"] is None
    assert launch.get("voxel_json") is None


def test_scenario_launch_unknown_is_empty():
    assert scenario_launch({}, "missing") == {}
    assert scenario_launch({"scenarios": {}}, "open_ground") == {}


def test_e2e_lab_config_loads():
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "e2e_lab.json")
    launch = scenario_launch(cfg, "e2e_lab")
    assert launch.get("body") == "e2e_icosahedron"
    assert launch.get("voxel_dir") is None
    assert "data_dir" in launch
    out = apply_scenario_to_config(cfg, "e2e_lab")
    assert out["active_scenario"] == "e2e_lab"


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


def test_deep_merge_nested_preserves_sibling_keys():
    base = {"scene": {"grid": {"enabled": False, "size": 200}, "background_color": "#111"}}
    override = {"scene": {"grid": {"enabled": True}}}
    out = _deep_merge(base, override)
    assert out["scene"]["grid"]["enabled"] is True
    assert out["scene"]["grid"]["size"] == 200
    assert out["scene"]["background_color"] == "#111"


def test_deep_merge_replaces_lists():
    base = {"dosimetry": {"fidelity_levels": [{"value": 0, "label": "A"}]}}
    override = {"dosimetry": {"fidelity_levels": [{"value": 2, "label": "B"}]}}
    out = _deep_merge(base, override)
    assert out["dosimetry"]["fidelity_levels"] == [{"value": 2, "label": "B"}]


def test_deep_merge_empty_override_is_noop():
    from copy import deepcopy

    from aegis.viewer.config import DEFAULTS

    base = deepcopy(DEFAULTS)
    out = _deep_merge(base, {})
    assert out == base

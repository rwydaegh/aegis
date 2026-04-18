"""Viewer configuration with deep-merge over defaults.

The canonical source is ``src/aegis/viewer/default_config.json``, loaded once
at module import. Public ``DEFAULTS`` is re-exported for backwards compatibility
with existing callers (scene_data, compute, tests).
"""

from __future__ import annotations

import copy
import json
from importlib.resources import files
from pathlib import Path


def _load_defaults() -> dict:
    """Load the canonical default config from the packaged JSON resource."""
    with files("aegis.viewer").joinpath("default_config.json").open("r") as f:
        return json.load(f)


DEFAULTS: dict = _load_defaults()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(config_path: str | Path | None = None) -> dict:
    """Load viewer config, merging user overrides on top of defaults.

    If config_path is None, returns the defaults unchanged.
    """
    if config_path is None:
        return copy.deepcopy(DEFAULTS)

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        user_config = json.load(f)

    return _deep_merge(DEFAULTS, user_config)


def scenario_launch(cfg: dict, scenario_name: str | None) -> dict:
    """Return the `launch` block for a named scenario, or {} if missing.

    Launch keys are optional: voxel_dir, voxel_json, body, bbox (scene radius
    in meters, same Semantics as ``--bbox``), data_dir.
    """
    if not scenario_name:
        return {}
    scenarios = cfg.get("scenarios") or {}
    entry = scenarios.get(scenario_name)
    if not entry:
        return {}
    return copy.deepcopy(entry.get("launch") or {})


def apply_scenario_to_config(cfg: dict, scenario_name: str | None) -> dict:
    """Copy cfg and set ``active_scenario`` / ``active_scenario_description`` for the client."""
    out = copy.deepcopy(cfg)
    if not scenario_name:
        return out
    out["active_scenario"] = scenario_name
    entry = (out.get("scenarios") or {}).get(scenario_name) or {}
    desc = entry.get("description")
    if desc:
        out["active_scenario_description"] = desc
    return out


def save_default_config(path: str | Path) -> None:
    """Write the full default config to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(DEFAULTS, f, indent=2)
    print(f"Default config written to {path}")

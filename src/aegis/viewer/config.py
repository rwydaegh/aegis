"""Viewer configuration with deep-merge over defaults."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from aegis.defaults import DEFAULT_FIDELITY_LEVEL, DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM

DEFAULTS: dict = {
    "server": {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": False,
        "open_browser": True,
    },
    "scene": {
        "background_color": "#111115",
        "grid": {
            "enabled": False,
            "size": 200,
            "divisions": 100,
            "color": "#666666",
            "line_color": "#444444",
            "y_offset": -0.01,
        },
        "ground_plane": {
            "enabled": False,
            "size": 500,
            "color": "#1a1a20",
            "opacity": 0.5,
            "roughness": 1.0,
            "metalness": 0.0,
        },
    },
    "camera": {
        "fov": 55,
        "near": 0.01,
        "far": 5000,
        "initial_position": [2, 1.5, 2],
        "controls": {
            "enable_damping": True,
            "damping_factor": 0.05,
            "min_distance": 0.1,
            "max_distance": 2000,
        },
    },
    "renderer": {
        "max_pixel_ratio": 2,
        "tone_mapping": "ACESFilmic",
        "tone_mapping_exposure": 1.2,
        "shadow_map_type": "PCFSoft",
        "shadows_enabled": True,
        "antialias": True,
    },
    "lighting": {
        "ambient": {
            "color": "#404050",
            "intensity": 0.6,
        },
        "sun": {
            "color": "#fff5e6",
            "intensity": 1.2,
            "position": [100, 200, 80],
            "cast_shadow": True,
        },
        "fill": {
            "color": "#6688cc",
            "intensity": 0.4,
            "position": [-30, 20, 0],
        },
        "hemisphere": {
            "sky_color": "#8899bb",
            "ground_color": "#444422",
            "intensity": 0.3,
        },
    },
    "body": {
        "default_name": "thelonious",
        "default_color": 0.5,
        "default_offset": [0, 0, 0],
        "default_rotation_y": 0,
        "wireframe": False,
        "material": {
            "roughness": 0.6,
            "metalness": 0.1,
            "double_sided": True,
        },
        "layer_button_color": [255, 140, 0],
        "smartphone": {
            "forward_distance": 0.30,
        },
        "phantom_type": "stl",
        "phantom_dir": "data/phantoms",
        "default_phantom": "adult_male",
        "default_pose": "idle",
        "animation_speed": 1.0,
    },
    "voxels": {
        "size_scale": 0.95,
        "default_size_fallback": 0.244,
        "material": {
            "roughness": 0.85,
            "metalness": 0.05,
            "flat_shading": True,
        },
        "material_colors": {
            "concrete": [180, 180, 180],
            "asphalt": [80, 80, 80],
            "vegetation": [40, 160, 40],
            "water": [30, 100, 220],
            "brick": [200, 80, 50],
            "glass": [150, 210, 240],
        },
        "heightmap_resolution_factor": 1,
    },
    "antenna": {
        "default_position": None,
        "sphere_radius": 0.08,
        "sphere_segments": 16,
        "color": "#ff3333",
        "emissive_color": "#881111",
        "cone_radius": 0.05,
        "cone_height": 0.15,
        "cone_segments": 8,
        "cone_y_offset": -0.12,
        "pole_radius": 0.015,
        "pole_height": 2,
        "pole_segments": 8,
        "pole_color": "#888888",
        "placement_height_offset": 2.0,
        "nudge_step": 1.0,
        "nudge_step_shift": 3.0,
        "radiation_pattern": {
            "enabled": True,
            "match_physics": False,
            "type": "short_dipole",
            "ico_detail": 6,
            "radius": 0.9,
            "lobe_gamma": 0.42,
            "dynamic_range_db": 36.0,
            "opacity": 0.94,
            "metalness": 0.12,
            "roughness": 0.5,
            "wireframe": False,
            "edge_lines": True,
            "edge_color": "#222233",
            "hub_radius": 0.055,
            "hub_color": "#aa2222",
            "hub_emissive": "#441010",
            "show_legacy_cone": False,
            "elements": [
                {
                    "offset": [0.0, 0.0, 0.0],
                    "weight": [1.0, 0.0],
                    "axis": [0.0, 1.0, 0.0],
                }
            ],
        },
    },
    "physics": {
        "gravity": 9.81,
        "walk_accel": 25.0,
        "ground_friction": 12.0,
        "air_friction": 0.5,
        "max_walk_speed": 3.0,
        "sprint_multiplier": 2.5,
        "jump_impulse": 5.0,
        "rotation_accel": 15.0,
        "rotation_friction": 8.0,
        "max_rotation_speed": 3.0,
        "facing_smooth": 8.0,
        "ground_snap": 0.05,
        "dt_clamp": 0.1,
        "max_step_height": 0.5,
    },
    "interaction": {
        "click_max_drag_px": 5,
        "click_max_hold_ms": 300,
        "debounce_ms": 200,
        "focus_hint_timeout_ms": 3000,
        "recompute_interval_ms": 500,
        "compute_timeout_ms": 60000,
    },
    "dosimetry": {
        "default_level": DEFAULT_FIDELITY_LEVEL,
        "default_power_dbm": DEFAULT_POWER_DBM,
        "default_max_order": 0,
        "freq_hz": DEFAULT_FREQ_HZ,
        "exposure_scenario": "general_public",
        "display_mode": "raw_sab",
        "fidelity_levels": [
            {"value": 0, "label": "Level 0 - Bound"},
            {"value": 1, "label": "Level 1 - Aggregate"},
            {"value": 2, "label": "Level 2 - Geometric ReLU"},
            {"value": 3, "label": "Level 3 - Fresnel"},
            {"value": 4, "label": "Level 4 - Polarisation"},
            {"value": 5, "label": "Level 5 - Curvature"},
            {"value": 6, "label": "Level 6 - Diffraction"},
        ],
        "power_input": {
            "min": 0,
            "max": 100,
            "step": 1,
        },
        "stochastic": {
            "preset_dir": "channel_presets",
            "default_preset": "3GPP_38.901_UMi_LOS",
            "default_seed": 42,
        },
        "level0_D_max": 4.0,
        "compliance_threshold": 10.0,
        "max_order_options": [
            {"value": 0, "label": "0 (LOS only)"},
            {"value": 1, "label": "1 (+ single reflection)"},
            {"value": 2, "label": "2 (+ double reflection)"},
        ],
        "convex_body_area_factor": 0.25,
        "skin_model": "itis",
        "dynamic_range_db": 30,
    },
    "mimo": {
        "enabled": False,
        "array": {
            "type": "upa",
            "n_h": 4,
            "n_v": 4,
            "d_h_wavelengths": 0.5,
            "d_v_wavelengths": 0.5,
            "position": [5.0, 0.0, 3.0],
            "broadside": [-1.0, 0.0, 0.0],
        },
        "users": [
            {
                "id": "user_0",
                "phantom": "thelonious",
                "position": [0.0, 0.0, 0.0],
                "orientation": 0.0,
                "device_offset": [0.25, 0.0, 1.4],
            },
        ],
        "precoder": "mrt",
        "exposure_budget_mw": 100,
        "max_users": 8,
    },
    "colormap": {
        "name": "inferno",
        "stops": [
            [0.0, 0.001, 0.014, 0.071],
            [0.25, 0.341, 0.063, 0.431],
            [0.5, 0.737, 0.216, 0.329],
            [0.75, 0.976, 0.557, 0.035],
            [1.0, 0.988, 1.0, 0.644],
        ],
        "legend": {
            "bar_width": 18,
            "bar_height": 200,
            "gradient_css": (
                "linear-gradient(to bottom, rgb(252,255,164), rgb(249,142,9),"
                " rgb(188,55,84), rgb(87,16,110), rgb(0,4,18))"
            ),
        },
    },
    "distance_viz": {
        "line_color": "#ffffff",
        "dash_size": 0.15,
        "gap_size": 0.08,
        "line_opacity": 0.5,
        "label_canvas_width": 128,
        "label_canvas_height": 32,
        "label_bg_color": "rgba(0,0,0,0.6)",
        "label_text_color": "#ffffff",
        "label_font": "bold 18px sans-serif",
        "label_y_offset": 0.2,
        "label_scale": [1.0, 0.25, 1],
        "path_line_color": "#ff6600",
        "path_line_opacity": 0.6,
    },
    "rt_paths": {
        "los_color": "#00ff44",
        "single_reflection_color": "#ff8800",
        "multi_reflection_color": "#ff0088",
        "opacity": 0.8,
        "line_width": 2,
    },
    "sionna_scene": {
        "color": "#8899aa",
        "roughness": 0.8,
        "metalness": 0.1,
        "opacity": 0.7,
        "double_sided": True,
        "ground_ray_height": 2000.0,
        "ground_sample_step_m": 0.35,
        "feet_clearance_m": 0.05,
    },
    "environment": {
        "source": "none",
        "location": None,
        "radius": 200,
        "osm": {
            "default_building_height": 10,
            "level_height": 3.0,
            "buildings": True,
            "roads": True,
            "water": True,
        },
        "tiles": {
            "geometric_error": 30.0,
        },
    },
    "location": {
        "default_radius": 30,
        "radius_min": 10,
        "radius_max": 500,
        "radius_step": 10,
        "default_resolution": 200,
    },
    "raytracer": {
        "max_rt_triangles": 50000,
        "reflection_loss_per_order": 0.5,
        "fspl_distance_clamp": 0.01,
        "default_body_center": [0.0, 0.0, 1.0],
        "default_source": "differt",
    },
    "material_classification": {
        "saturation_gray_threshold": 0.08,
        "value_dark_threshold": 0.15,
        "value_asphalt_threshold": 0.35,
        "vegetation_hue_range_1": [60, 150],
        "vegetation_sat_min_1": 0.15,
        "vegetation_val_min_1": 0.2,
        "vegetation_hue_range_2": [40, 60],
        "vegetation_sat_min_2": 0.25,
        "vegetation_val_min_2": 0.25,
        "brick_hue_low": 40,
        "brick_hue_high": 330,
        "brick_sat_min": 0.15,
        "water_sat_min": 0.6,
        "water_val_min": 0.4,
        "glass_sat_min": 0.45,
        "glass_val_min": 0.55,
        "blue_hue_range": [160, 280],
        "brick_secondary_hue_range": [20, 50],
        "brick_secondary_sat_max": 0.4,
        "min_voxels_for_material": 5,
        "ground_height_percentile": 10,
        "ground_height_margin": 2.0,
        "ground_center_vertical_offset": 1.0,
    },
    "ui": {
        "title": "AEGIS Viewer",
        "panel": {
            "position_top": 12,
            "position_left": 12,
            "max_width": 300,
            "padding": 16,
            "border_radius": 8,
            "backdrop_blur": 8,
            "background": "rgba(0,0,0,0.88)",
        },
        "colors": {
            "heading": "#7eb4ff",
            "body_background": "#111",
            "section_title": "#aaa",
            "stat_label": "#888",
            "stat_value": "#fff",
            "pass": "#2ecc71",
            "fail": "#e74c3c",
            "input_background": "#222",
            "input_border": "#444",
            "input_text": "#ccc",
            "hint_text": "#666",
            "button_gradient_start": "#667eea",
            "button_gradient_end": "#764ba2",
            "cancel_gradient_start": "#e74c3c",
            "cancel_gradient_end": "#c0392b",
            "layer_btn_bg": "#222",
            "layer_btn_hover_bg": "#333",
            "layer_btn_active_bg": "#2a2a3a",
            "layer_btn_active_border": "#667eea",
            "log_background": "#1a1a1a",
        },
        "fonts": {
            "family": "'Segoe UI', sans-serif",
            "section_title_size": 12,
            "heading_size": 15,
            "button_size": 12,
            "layer_button_size": 11,
            "hint_size": 10,
            "dashboard_size": 12,
            "dashboard_line_height": 1.8,
        },
        "loading": {
            "spinner_size": 40,
            "spinner_border": 3,
            "spinner_speed_s": 1,
            "font_size": 18,
            "color": "#7eb4ff",
        },
        "computing": {
            "spinner_size": 24,
            "spinner_border": 2,
            "spinner_speed_s": 0.8,
            "font_size": 14,
            "background": "rgba(0,0,0,0.6)",
        },
        "legend": {
            "label_font_size": 10,
            "label_color": "#ccc",
            "title_font_size": 10,
            "title_color": "#888",
        },
    },
    "three_js": {
        "version": "0.160.0",
        "cdn": "https://unpkg.com/three@0.160.0",
    },
    "basestations": {
        "classification": {
            "element_gain_dbi": 5.0,
            "mmimo_gain_threshold": 20.0,
            "small_cell_gain_threshold": 10.0,
            "default_freq_mhz": 2100,
            "standard_grids": {
                "mmimo": [[4, 4], [4, 8], [8, 8], [8, 16]],
                "sector": [[1, 2], [1, 4], [2, 4], [2, 8]],
                "small_cell": [[1, 1], [2, 2]],
            },
        },
        "panel": {
            "depth": 0.05,
            "pole_radius": 0.04,
            "element_dot_radius": 0.008,
            "show_elements": True,
            "margin": 0.02,
        },
        "mmimo": {
            "default_panel_width": 0.7,
            "default_panel_height": 0.4,
            "show_pattern": True,
            "ico_detail": 6,
            "pattern_opacity": 0.85,
            "dynamic_range_db": 36,
        },
        "sector": {
            "default_panel_width": 0.3,
            "default_panel_height": 1.0,
            "show_pattern": False,
        },
        "small_cell": {
            "default_panel_width": 0.15,
            "default_panel_height": 0.15,
            "show_pattern": False,
        },
        "pattern_library": {
            "cloudrf_api_key_env": "CLOUDRF_API_KEY",
            "auto_build_index": True,
        },
        "auto_load_with_scene": False,
        "default_radius_m": 500,
        "max_distance_m": 2000,
        "site_vertical_gap": 0.1,
        "exposure": {
            "default_mode": "theoretical",
            "defaults_by_archetype": {
                "sector": {
                    "duplex_mode": "fdd",
                    "tdd_dl_ratio": 1.0,
                    "power_reduction_factor": 1.0,
                    "traffic_load_factor": 0.5,
                },
                "mmimo": {
                    "duplex_mode": "tdd",
                    "tdd_dl_ratio": 0.75,
                    "power_reduction_factor": 0.32,
                    "traffic_load_factor": 0.5,
                },
                "small_cell": {
                    "duplex_mode": "fdd",
                    "tdd_dl_ratio": 1.0,
                    "power_reduction_factor": 1.0,
                    "traffic_load_factor": 0.3,
                },
            },
            "sidelobe_suppression_db": 15.0,
            "beam_config": {
                "broadcast_gain_dbi": 18.0,
                "broadcast_hbw_deg": 65.0,
                "broadcast_vbw_deg": 10.0,
                "traffic_gain_dbi": 25.0,
                "traffic_hbw_deg": 12.0,
                "traffic_vbw_deg": 8.0,
                "sweep_h_range_deg": 60.0,
                "sweep_v_range_deg": 15.0,
            },
        },
    },
    "default_scenario": "open_ground",
    "scenarios": {
        "open_ground": {
            "description": "Body in free space, single antenna at 28 GHz",
            "launch": {"voxel_dir": None, "voxel_json": None},
            "label": "Open ground",
            "icon": "radio",
            "instant": True,
            "autoCompute": True,
            "webState": {
                "freqGhz": 28,
                "powerDbm": 60,
                "mode": "spatial",
                "antennaPos": [0, 1.5, -0.8],
                "environment": {"source": "none"},
            },
        },
        "mmwave_close": {
            "description": "60 GHz antenna 10 cm from skin surface",
            "launch": {"voxel_dir": None},
            "label": "Close-range mmWave",
            "icon": "zap",
            "instant": True,
            "autoCompute": True,
            "webState": {
                "freqGhz": 60,
                "powerDbm": 40,
                "mode": "spatial",
                "antennaPos": [0, 0.15, -0.5],
                "environment": {"source": "none"},
            },
        },
        "urban_ghent": {
            "description": "28 GHz outdoor with OpenStreetMap buildings",
            "launch": {},
            "label": "Urban Ghent",
            "icon": "building",
            "instant": False,
            "autoCompute": True,
            "webState": {
                "freqGhz": 28,
                "powerDbm": 60,
                "mode": "spatial",
                "antennaPos": [0, 10.0, -3.0],
                "environment": {
                    "source": "osm",
                    "lat": 51.0447,
                    "lon": 3.7268,
                    "locationQuery": "Ghent, Belgium",
                },
            },
        },
        "coverage_globe": {
            "description": "Browse base station coverage worldwide",
            "launch": {},
            "label": "Coverage globe",
            "icon": "globe",
            "instant": True,
            "autoCompute": False,
            "webState": {
                "antennaPos": None,
                "environment": {
                    "source": "coverage",
                    "lat": 0,
                    "lon": 0,
                },
            },
        },
        "empty": {
            "description": "Clear everything and start fresh",
            "launch": {},
            "label": "Empty scene",
            "icon": "refresh-cw",
            "instant": True,
            "autoCompute": False,
            "hidden": True,
            "webState": {
                "antennaPos": None,
                "environment": {"source": "none"},
                "clearResults": True,
                "clearScene": True,
            },
        },
    },
}


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

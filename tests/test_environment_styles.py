"""Tests for the building style system (styles.py)."""

from __future__ import annotations

from aegis.environment.styles import (
    BuildingStyle,
    StyleLibrary,
    WindowParams,
    resolve_style,
)


def test_default_style_exists():
    lib = StyleLibrary()
    style = lib.get("default")
    assert isinstance(style, BuildingStyle)


def test_window_params_total_width():
    wp = WindowParams(width=1.2, height=1.8, margin_left=1.0, margin_right=1.0, sill_height=0.9)
    assert abs(wp.total_width - 3.2) < 1e-9


def test_windows_per_facade():
    wp = WindowParams(width=1.2, height=1.8, margin_left=1.0, margin_right=1.0, sill_height=0.9)
    # 12.0 / 3.2 = 3.75 -> floor to 3
    assert wp.count_for_width(12.0) == 3


def test_resolve_style_from_tags():
    tags = {"building": "apartments", "building:levels": "6"}
    style = resolve_style(tags)
    assert isinstance(style, BuildingStyle)
    assert style.num_levels == 6


def test_facade_color_deterministic():
    lib = StyleLibrary()
    style = lib.get("default")
    color1 = style.facade_color(seed=42)
    color2 = style.facade_color(seed=42)
    assert color1 == color2


def test_style_library_building_types():
    building_types = [
        "default",
        "house",
        "detached",
        "apartments",
        "office",
        "commercial",
        "industrial",
        "retail",
        "garage",
    ]
    lib = StyleLibrary()
    for bt in building_types:
        style = lib.get(bt)
        assert isinstance(style, BuildingStyle), f"Expected BuildingStyle for '{bt}'"

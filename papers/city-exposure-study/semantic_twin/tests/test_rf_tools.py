"""Numerical tests for the exploratory RF tools offered to Gemini."""

from __future__ import annotations

import pytest

from semantic_twin.vision.rf_tools import (
    compare_surface_hypotheses,
    itu_material_state,
    rough_surface_response,
    roughness_priors,
)


def test_itu_tool_reads_the_existing_material_law() -> None:
    brick = itu_material_state("brick", 15.0)
    assert brick["relative_permittivity_real"] == pytest.approx(3.91)
    assert brick["conductivity_s_per_m"] > 0.0
    assert brick["applicability"] == "within_recommendation_range"


def test_roughness_search_finds_brick_wall_context() -> None:
    matches = roughness_priors(itu_material="brick", query="weathered brick masonry wall")
    names = {entry["name"] for entry in matches}
    assert "brick_wall_with_mortar_joints" in names


def test_rough_surface_tool_preserves_more_specular_power_at_grazing_incidence() -> None:
    normal = rough_surface_response(2.0, 15.0, 0.0)
    grazing = rough_surface_response(2.0, 15.0, 75.0)
    assert normal["coherent_specular_power_fraction"] < grazing["coherent_specular_power_fraction"]
    assert normal["noncoherent_power_fraction"] > grazing["noncoherent_power_fraction"]


def test_hypothesis_tool_keeps_material_and_roughness_effects_separate() -> None:
    rows = compare_surface_hypotheses(
        [
            {"label": "smooth render", "itu_material": "plasterboard", "rms_height_mm": 0.2},
            {"label": "brick joints", "itu_material": "brick", "rms_height_mm": 2.6},
        ],
        frequency_ghz=15.0,
        incidence_deg=30.0,
    )
    assert [row["label"] for row in rows] == ["smooth render", "brick joints"]
    assert rows[0]["coherent_specular_power_fraction"] > rows[1]["coherent_specular_power_fraction"]
    for row in rows:
        total = row["coherent_reflected_power"] + row["noncoherent_reflected_power"]
        assert total == pytest.approx(row["smooth_interface_power_reflectance"])

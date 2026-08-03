"""Tests for the vision model material backend.

The physics assertions are the ones that matter. A layered stack has to reduce
to a half space when the coating goes away and to its outer material when the
coating gets thick, a posterior mean has to lie between the extremes it mixes,
and a draw has to reproduce the posterior it was drawn from. Those are the
properties the report's numbers rest on.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from semantic_twin.facade_vlm import (
    MATERIAL_VOCABULARY,
    Layer,
    VlmResponse,
    agreement,
    argmax_power_reflectance,
    build_prompt,
    expected_calibration_gap,
    half_space_power_reflectance,
    layered_power_reflectance,
    material_power_reflectance,
    parse_response,
    pooled_posterior,
    posterior_power_reflectance,
    reliability,
    sample_face_materials,
    stack_power_reflectance,
    total_variation,
)
from semantic_twin.materials import MaterialLibrary
from semantic_twin.propagation.material_posterior import bind_posterior

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config"


@pytest.fixture(scope="module")
def library() -> MaterialLibrary:
    return MaterialLibrary.load(CONFIG / "itu_p2040_4.json")


def payload(**overrides: object) -> dict:
    base = {
        "stack": [
            {"material": "painted_render", "thickness_mm": 15},
            {"material": "fired_clay_brick", "thickness_mm": None},
        ],
        "relief": {"pattern": "coursed_masonry", "pitch_mm": 65, "depth_mm": 8},
        "rms_height_mm": 0.1,
        "material_posterior": {"brick": 0.5, "plasterboard": 0.3, "glass": 0.2},
        "confidence": 0.6,
        "legible": True,
        "note": "render over brick",
    }
    base.update(overrides)
    return base


def test_parse_normalises_the_posterior_and_translates_finishes() -> None:
    response = parse_response(payload(), crop_id="c0", source="panorama")
    assert pytest.approx(sum(response.posterior.values())) == 1.0
    assert set(response.posterior) == set(MATERIAL_VOCABULARY)
    assert [layer.material for layer in response.stack] == ["plasterboard", "brick"]
    assert response.stack[-1].thickness_mm is None


def test_parse_refuses_a_material_outside_the_vocabulary() -> None:
    with pytest.raises(ValueError, match="outside the vocabulary"):
        parse_response(payload(material_posterior={"granite": 1.0}), crop_id="c0", source="panorama")


def test_parse_refuses_an_interior_layer_with_no_thickness() -> None:
    stack = [
        {"material": "painted_render", "thickness_mm": None},
        {"material": "fired_clay_brick", "thickness_mm": None},
    ]
    with pytest.raises(ValueError, match="no transfer matrix"):
        parse_response(payload(stack=stack), crop_id="c0", source="panorama")


def test_parse_refuses_an_unknown_relief_pattern() -> None:
    with pytest.raises(ValueError, match="relief pattern"):
        parse_response(
            payload(relief={"pattern": "corrugated", "pitch_mm": None, "depth_mm": None}),
            crop_id="c0",
            source="panorama",
        )


def test_prompt_carries_every_vocabulary_name() -> None:
    prompt = build_prompt()
    for name in MATERIAL_VOCABULARY:
        assert name in prompt


def test_zero_thickness_stack_is_the_half_space() -> None:
    permittivity = np.array([complex(5.24, -0.05)])
    for angle in (0.0, 45.0, 80.0):
        cosine = float(np.cos(np.radians(angle)))
        assert layered_power_reflectance(permittivity, np.zeros(0), cosine, 15.0e9) == pytest.approx(
            half_space_power_reflectance(permittivity[0], cosine)
        )


def test_a_vanishing_coating_reduces_to_its_substrate() -> None:
    stack = np.array([complex(2.73, -0.01), complex(3.91, -0.04)])
    thin = layered_power_reflectance(stack, np.array([1.0e-9]), 1.0, 15.0e9)
    assert thin == pytest.approx(half_space_power_reflectance(stack[1], 1.0), rel=1e-4)


def test_a_lossless_stack_never_reflects_more_than_unity() -> None:
    stack = np.array([complex(2.73, 0.0), complex(6.31, 0.0), complex(3.91, 0.0)])
    for thickness in (0.002, 0.01, 0.05):
        value = layered_power_reflectance(stack, np.full(2, thickness), 0.5, 15.0e9)
        assert 0.0 <= value <= 1.0


def test_thickness_averaged_render_over_brick_lands_on_pure_render(library: MaterialLibrary) -> None:
    """The interference washes out, so the stack is its outer layer.

    This is the quantitative reason the layered branch of the model does not earn
    its own field: once the coat thickness is uncertain by more than the half
    wave period in the coating, which is 6 mm at 15 GHz, the stack cannot be
    distinguished from a render half space.
    """
    thicknesses = np.linspace(8.0, 25.0, 200)
    mean = float(
        np.mean(
            [
                stack_power_reflectance((Layer("plasterboard", t), Layer("brick", None)), 15.0e9, 1.0, library)
                for t in thicknesses
            ]
        )
    )
    pure_render = material_power_reflectance(15.0e9, 1.0, library)["plasterboard"]
    assert 10 * abs(np.log10(mean / pure_render)) < 0.3


def test_posterior_mean_sits_between_the_materials_it_mixes(library: MaterialLibrary) -> None:
    reflectance = material_power_reflectance(15.0e9, 1.0, library)
    posterior = {"brick": 0.5, "metal": 0.5}
    mean = posterior_power_reflectance(posterior, reflectance)
    assert reflectance["brick"] < mean < reflectance["metal"]


def test_posterior_mean_exceeds_the_argmax_when_the_tail_reflects_harder(library: MaterialLibrary) -> None:
    reflectance = material_power_reflectance(15.0e9, 1.0, library)
    posterior = {"brick": 0.6, "metal": 0.4}
    assert posterior_power_reflectance(posterior, reflectance) > argmax_power_reflectance(posterior, reflectance)


def test_posterior_with_all_mass_on_unknown_is_refused(library: MaterialLibrary) -> None:
    reflectance = material_power_reflectance(15.0e9, 1.0, library)
    with pytest.raises(ValueError, match="unknown"):
        posterior_power_reflectance({"unknown": 1.0}, reflectance)


def test_sampling_reproduces_the_posterior_it_was_drawn_from() -> None:
    rng = np.random.default_rng(0)
    posterior = np.tile(np.array([0.5, 0.3, 0.2]), (200_000, 1))
    draws = sample_face_materials(posterior, rng)
    counts = np.bincount(draws, minlength=3) / draws.size
    assert counts == pytest.approx(np.array([0.5, 0.3, 0.2]), abs=0.005)


def test_total_variation_is_zero_on_itself_and_one_on_disjoint_support() -> None:
    first = {name: 0.0 for name in MATERIAL_VOCABULARY} | {"brick": 1.0}
    second = {name: 0.0 for name in MATERIAL_VOCABULARY} | {"glass": 1.0}
    assert total_variation(first, first) == pytest.approx(0.0)
    assert total_variation(first, second) == pytest.approx(1.0)


def _response(crop_id: str, top: str, confidence: float, draw: int = 0) -> VlmResponse:
    return parse_response(
        payload(material_posterior={top: 0.8, "glass": 0.2}, confidence=confidence),
        crop_id=crop_id,
        source="panorama",
        draw=draw,
    )


def test_agreement_scores_only_within_group_pairs() -> None:
    responses = [
        _response("a", "brick", 0.7, 0),
        _response("a", "brick", 0.7, 1),
        _response("b", "concrete", 0.7, 0),
    ]
    report = agreement(responses, {"a": "wall", "b": "other"})
    assert report.pairs == 1
    assert report.top1_agreement == pytest.approx(1.0)


def test_reliability_detects_overconfidence() -> None:
    responses = [
        _response("a", "brick", 0.95, 0),
        _response("a", "concrete", 0.95, 1),
    ]
    curve = reliability(responses, {"a": "wall"}, bins=4)
    assert curve[-1]["gap"] == pytest.approx(0.95)
    assert expected_calibration_gap(curve) == pytest.approx(0.95)


def test_pooled_posterior_respects_its_weights() -> None:
    responses = [_response("a", "brick", 0.5), _response("b", "concrete", 0.5)]
    heavy = pooled_posterior(responses, np.array([9.0, 1.0]))
    assert heavy["brick"] > heavy["concrete"]


def test_bind_posterior_only_touches_the_named_class() -> None:
    geometric = np.array([0, 1, 1, 2, 3], dtype=np.int64)
    areas = np.ones(5)
    binding = bind_posterior(areas, geometric, {"facade": {"glass": 1.0}}, seed=0)
    assert binding.face_class[0] == 0
    assert binding.face_class[3] == 2
    assert binding.class_names[binding.face_class[1]] == "posterior_glass"
    assert binding.drawn_area_fraction == pytest.approx(0.4)


def test_bind_posterior_folds_substituted_materials_onto_their_row() -> None:
    geometric = np.ones(64, dtype=np.int64)
    binding = bind_posterior(np.ones(64), geometric, {"facade": {"ceramic": 1.0}}, seed=1)
    assert set(binding.realised_composition) == {"marble"}


def test_bind_posterior_refuses_a_posterior_with_no_traceable_mass() -> None:
    with pytest.raises(ValueError, match="no traceable mass"):
        bind_posterior(np.ones(4), np.ones(4, dtype=np.int64), {"facade": {"unknown": 1.0}})


def test_bind_posterior_refuses_a_class_that_is_not_geometric() -> None:
    with pytest.raises(ValueError, match="not a geometric class"):
        bind_posterior(np.ones(4), np.ones(4, dtype=np.int64), {"gargoyle": {"brick": 1.0}})

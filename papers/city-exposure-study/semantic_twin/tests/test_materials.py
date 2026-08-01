from __future__ import annotations

import pathlib

import numpy as np

from semantic_twin.materials import MaterialLibrary, radio_material_from_roughness

ROOT = pathlib.Path(__file__).resolve().parent.parent


def library() -> MaterialLibrary:
    return MaterialLibrary.load(ROOT / "config" / "itu_p2040_4.json")


def test_itu_concrete_at_28_ghz_matches_reference_curve() -> None:
    concrete = library()["concrete"].evaluate(28e9)
    assert concrete.relative_permittivity_real == 5.24
    assert np.isclose(concrete.conductivity_s_per_m, 0.6257, rtol=0.01)
    assert concrete.applicability == "within_recommendation_range"


def test_out_of_range_evaluation_is_explicit_and_more_uncertain() -> None:
    brick = library()["brick"].evaluate(60e9)
    assert brick.applicability == "indicative_extrapolation"
    assert brick.uncertainty_multiplier > 1.0


def test_complex_permittivity_uses_lossy_sign_convention() -> None:
    glass = library()["glass"].evaluate(39e9)
    assert glass.complex_relative_permittivity.real > 1.0
    assert glass.complex_relative_permittivity.imag < 0.0


def test_complete_radio_material_retains_non_itu_provenance() -> None:
    evaluation = library()["brick"].evaluate(28e9)
    material = radio_material_from_roughness(
        evaluation,
        name="brick-facade",
        thickness_m=0.2,
        rms_height_m=0.001,
        reference_incidence_deg=45.0,
        xpd_coefficient=0.1,
    )
    assert material.relative_permittivity == evaluation.relative_permittivity_real
    assert material.scattering_coefficient > 0.0
    assert material.provenance["roughness_closure"]["status"].startswith("engineering")

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.materials import SurfaceRoughnessLibrary
from semantic_twin.mmwave import rayleigh_smooth_threshold_m, specular_power_fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "surface_roughness.json"


@pytest.fixture(scope="module")
def library() -> SurfaceRoughnessLibrary:
    return SurfaceRoughnessLibrary.load(CONFIG)


@pytest.fixture(scope="module")
def document() -> dict:
    return json.loads(CONFIG.read_text())


def test_specular_fraction_matches_published_sensitivity_numbers() -> None:
    # ROUGHNESS.md quotes these, so a change to the closure has to break a test.
    expected = {0.0002: 0.946, 0.0005: 0.709, 0.001: 0.252, 0.002: 0.004}
    for rms, value in expected.items():
        assert specular_power_fraction(rms, 1.0, 28e9) == pytest.approx(value, abs=5e-4)


def test_grazing_incidence_restores_a_rough_wall_to_near_specular() -> None:
    normal = specular_power_fraction(0.002, 1.0, 28e9)
    grazing = specular_power_fraction(0.002, np.cos(np.radians(75.0)), 28e9)
    assert normal < 0.01
    assert grazing == pytest.approx(0.691, abs=5e-3)


def test_rayleigh_threshold_is_lambda_over_eight_cosine() -> None:
    assert rayleigh_smooth_threshold_m(28e9, 1.0) == pytest.approx(0.010707 / 8.0, rel=1e-3)
    assert rayleigh_smooth_threshold_m(28e9, np.cos(np.radians(60.0))) == pytest.approx(2.0 * 0.010707 / 8.0, rel=1e-3)


def test_every_class_declares_a_known_grade_and_structure(library, document) -> None:
    grades = set(document["evidence_grades"])
    structures = set(document["structures"])
    assert library.classes
    for entry in library.classes.values():
        assert entry.evidence_grade in grades
        assert entry.structure in structures


def test_every_concept_reference_exists_in_the_concept_catalogue(library) -> None:
    catalogue = json.loads((ROOT / "config" / "semantic_concepts.json").read_text())
    prompts = {record["prompt"] for record in catalogue["concepts"]}
    for entry in library.classes.values():
        assert set(entry.concepts) <= prompts, entry.name


def test_every_itu_row_reference_exists_in_the_material_library(library) -> None:
    rows = {record["name"] for record in json.loads((ROOT / "config" / "itu_p2040_4.json").read_text())["materials"]}
    for entry in library.classes.values():
        assert set(entry.itu_rows) <= rows, entry.name


def test_periodic_classes_refuse_the_gaussian_closure(library) -> None:
    periodic = [e for e in library.classes.values() if not e.gaussian_model_applies]
    assert periodic, "the table should carry at least one periodic class"
    for entry in periodic:
        with pytest.raises(ValueError, match="Gaussian"):
            entry.specular_power_fraction(28e9, 0.0)
        assert entry.specular_power_fraction(28e9, 0.0, allow_periodic=True) >= 0.0
        assert entry.periodic_component is not None


def test_samples_stay_inside_the_declared_range(library) -> None:
    rng = np.random.default_rng(0)
    for entry in library.classes.values():
        draws = entry.sample(512, rng)
        lower, upper = entry.plausible_range_m
        assert draws.min() >= lower
        assert draws.max() <= upper


def test_central_value_refuses_to_sit_outside_its_own_range() -> None:
    from semantic_twin.materials import SurfaceRoughnessPrior

    with pytest.raises(ValueError, match="plausible range"):
        SurfaceRoughnessPrior(
            name="broken",
            rms_height_m=0.01,
            log_standard_deviation=0.5,
            plausible_range_m=(0.001, 0.002),
            correlation_length_m=None,
            correlation_length_status="not_reported",
            evidence_grade="extrapolated",
            radio_fitted=False,
            structure="gaussian_random",
            gaussian_closure_reliable=True,
            mean_texture_depth_m=None,
            periodic_component=None,
            concepts=(),
            itu_rows=(),
            provenance={},
        )


def test_extrapolated_entries_carry_a_wider_prior_than_measured_ones(library) -> None:
    measured = [e.log_standard_deviation for e in library.classes.values() if e.evidence_grade.startswith("measured")]
    extrapolated = [e.log_standard_deviation for e in library.classes.values() if e.evidence_grade == "extrapolated"]
    if measured and extrapolated:
        assert min(extrapolated) >= min(measured)


def test_lookup_by_concept_prompt_finds_a_class(library) -> None:
    assert library.for_concept("asphalt road")
    assert library.for_concept("not a prompt in the catalogue") == []


def test_radio_fitted_values_cannot_enter_the_library() -> None:
    from semantic_twin.materials import SurfaceRoughnessPrior

    with pytest.raises(ValueError, match="double counts"):
        SurfaceRoughnessPrior(
            name="fitted",
            rms_height_m=0.0065,
            log_standard_deviation=0.5,
            plausible_range_m=(0.001, 0.01),
            correlation_length_m=0.0021,
            correlation_length_status="not_reported",
            evidence_grade="inferred_radio",
            radio_fitted=True,
            structure="gaussian_random",
            gaussian_closure_reliable=False,
            mean_texture_depth_m=None,
            periodic_component=None,
            concepts=(),
            itu_rows=(),
            provenance={},
        )


def test_mean_texture_depth_is_carried_separately_from_rms_height(library) -> None:
    with_texture = [e for e in library.classes.values() if e.mean_texture_depth_m is not None]
    assert with_texture, "the paving classes should carry a mean texture depth"
    for entry in with_texture:
        assert entry.mean_texture_depth_m != entry.rms_height_m
        assert entry.provenance["mean_texture_depth_status"]


def test_closure_reliability_flag_agrees_with_the_g_squared_threshold(library) -> None:
    for entry in library.classes.values():
        g = 4.0 * np.pi * entry.rms_height_m / (299792458.0 / 28e9)
        expected = bool(g**2 < 3.0 and entry.gaussian_model_applies)
        assert entry.gaussian_closure_reliable is expected, entry.name

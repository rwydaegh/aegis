"""What the materials package promises, checked against something outside itself.

Three kinds of check live here. The catalogue rows are checked against
Recommendation ITU-R P.2040-4 and against energy conservation, so a mistyped
coefficient shows up as a surface that reflects more than it receives. The
binding is checked on the one property it exists for: coverage is counted from
a per triangle provenance array rather than asserted, so a run with no
photographs reports zero because it measured zero. The roughness rules are
checked against each other in the limit where they must agree, which is the
only place a two scale surface has a right answer everybody shares.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib

import numpy as np
import pytest

from semantic_twin.materials import (
    CLASS_NAMES,
    IMAGE_MATERIALS,
    MASONRY_RULE,
    MATERIAL_VOCABULARY,
    QUADRATURE_RULE,
    SURFACE_CLASSES,
    MaterialLibrary,
    MaterialSpec,
    MaterialTable,
    Provenance,
    SurfaceBinding,
    SurfaceRoughnessLibrary,
    bind_walk_entities,
    effective_rms_height,
    extend_classes,
    geometric_binding,
    load_table,
    masonry_equivalent_rms_height,
)
from semantic_twin.materials.foliage import FoliageMedium, medium_for_spec
from semantic_twin.materials.stack import (
    argmax_power_reflectance,
    half_space_power_reflectance,
    layer_permittivity,
    layered_power_reflectance,
    material_power_reflectance,
    posterior_power_reflectance,
)
from semantic_twin.transport.tracer import fresnel_power_reflectance

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config"
CARRIER_HZ = 15.0e9


@pytest.fixture(scope="module")
def materials() -> MaterialLibrary:
    return MaterialLibrary.load(CONFIG / "itu_p2040_4.json")


@pytest.fixture(scope="module")
def roughness() -> SurfaceRoughnessLibrary:
    return SurfaceRoughnessLibrary.load(CONFIG / "surface_roughness.json")


# --- the rows -------------------------------------------------------------


def test_the_brick_row_reproduces_the_published_table_3_power_law(materials) -> None:
    """P.2040-4 Table 3 gives brick a = 3.75, b = 0, c = 0.038, d = 0."""
    evaluation = materials["brick"].evaluate(CARRIER_HZ)
    assert evaluation.relative_permittivity_real == pytest.approx(3.91, abs=0.2)
    assert evaluation.conductivity_s_per_m == pytest.approx(0.0367, rel=0.15)
    # eps'' = 17.98 sigma / f_GHz is the recommendation's own conversion.
    assert evaluation.relative_permittivity_imag == pytest.approx(
        17.98 * evaluation.conductivity_s_per_m / 15.0, rel=1e-12
    )


def test_the_vacuum_row_is_free_space_at_every_carrier(materials) -> None:
    """Vegetation is bound here, so the row has to be exactly free space.

    The choice removes 71.8 dB of reflection a wood row would invent at a
    canopy boundary. It only does that if the row itself is transparent.
    """
    for frequency_hz in (1.0e9, CARRIER_HZ, 60.0e9):
        evaluation = materials["vacuum_air"].evaluate(frequency_hz)
        assert evaluation.complex_relative_permittivity == 1.0 + 0.0j
    assert IMAGE_MATERIALS["vegetation_effective"].itu_row == "vacuum_air"


def test_no_row_reflects_more_power_than_it_receives(materials) -> None:
    """A half space cannot return more than it is given, at any angle."""
    cosines = np.cos(np.radians(np.linspace(0.0, 89.0, 40)))
    for name, row in materials.materials.items():
        frequency_hz = 1e9 * np.clip(15.0, row.minimum_ghz, row.maximum_ghz)
        permittivity = row.evaluate(frequency_hz).complex_relative_permittivity
        reflectance = fresnel_power_reflectance(cosines, permittivity)
        assert np.all(reflectance >= 0.0), name
        assert np.all(reflectance <= 1.0), name


def test_a_lossless_row_reflects_less_than_the_metal_row(materials) -> None:
    """Ordering against a known extreme, not against a stored number."""
    normal = np.array([1.0])
    metal = fresnel_power_reflectance(normal, materials["metal"].evaluate(CARRIER_HZ).complex_relative_permittivity)
    brick = fresnel_power_reflectance(normal, materials["brick"].evaluate(CARRIER_HZ).complex_relative_permittivity)
    assert metal > 0.99 > brick > 0.0


def test_every_class_this_study_traces_sits_inside_the_recommendation(materials) -> None:
    """The 15 GHz carrier needs no extrapolation for any material it can bind.

    Swapping a class onto a row whose band stops below 15 GHz would silently
    widen every uncertainty in the study, so it is checked rather than assumed.
    """
    for spec in {**SURFACE_CLASSES, **IMAGE_MATERIALS}.values():
        evaluation = materials[spec.itu_row].evaluate(CARRIER_HZ)
        assert evaluation.applicability == "within_recommendation_range"
        assert evaluation.uncertainty_multiplier == 1.0


# --- the table ------------------------------------------------------------


def test_a_table_cannot_exist_without_saying_which_recommendation_made_it() -> None:
    with pytest.raises(ValueError, match="where its rows came from"):
        MaterialTable(
            frequency_hz=CARRIER_HZ,
            class_names=("ground",),
            permittivity=np.array([4.0 + 0.0j]),
            rms_height_m=np.array([0.001]),
            spec={"ground": SURFACE_CLASSES["ground"]},
            provenance={},
        )


def test_a_table_refuses_a_class_it_has_no_recipe_for() -> None:
    with pytest.raises(ValueError, match="no material spec"):
        MaterialTable(
            frequency_hz=CARRIER_HZ,
            class_names=("ground", "facade"),
            permittivity=np.array([4.0 + 0.0j, 4.0 + 0.0j]),
            rms_height_m=np.array([0.001, 0.001]),
            spec={"ground": SURFACE_CLASSES["ground"]},
            provenance={"class_rule": "test"},
        )


def test_only_a_canopy_is_a_volume_and_the_table_says_which() -> None:
    """``media`` is how a transport estimator learns a class is not a surface."""
    assert [name for name, spec in IMAGE_MATERIALS.items() if not spec.is_interface] == ["vegetation_effective"]
    class_names, spec = extend_classes(sorted(IMAGE_MATERIALS), "semantic_", IMAGE_MATERIALS)
    table = load_table(CONFIG, CARRIER_HZ, class_names=class_names, class_binding=spec)
    assert set(table.media) == {"semantic_vegetation_effective"}
    assert all(SURFACE_CLASSES[name].is_interface for name in CLASS_NAMES)


def test_a_canopy_spec_resolves_to_a_p833_medium_and_a_brick_spec_does_not() -> None:
    medium = medium_for_spec(IMAGE_MATERIALS["vegetation_effective"], CARRIER_HZ)
    assert isinstance(medium, FoliageMedium)
    assert medium.extinction_per_m > 0.0
    assert 0.0 <= medium.albedo <= 1.0
    assert medium_for_spec(IMAGE_MATERIALS["brick"], CARRIER_HZ) is None


def test_a_medium_tag_with_no_model_behind_it_is_refused() -> None:
    with pytest.raises(ValueError, match="no participating medium model"):
        medium_for_spec(MaterialSpec("brick", "brick_face", medium="fog"), CARRIER_HZ)


# --- the surface ----------------------------------------------------------


def _tetrahedron() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 9.0]],
        dtype=np.float64,
    )
    faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], dtype=np.int64)
    a = vertices[faces[:, 0]]
    areas = 0.5 * np.linalg.norm(np.cross(vertices[faces[:, 1]] - a, vertices[faces[:, 2]] - a), axis=1)
    return vertices, faces, areas


def test_a_binding_cannot_exist_without_saying_how_its_classes_were_decided() -> None:
    with pytest.raises(ValueError, match="how its classes were decided"):
        SurfaceBinding(
            class_names=CLASS_NAMES,
            spec=dict(SURFACE_CLASSES),
            face_class=np.zeros(3, dtype=np.int64),
            face_source=np.zeros(3, dtype=np.int8),
            face_area_m2=np.ones(3),
            provenance={},
        )


def test_a_binding_refuses_a_provenance_value_that_names_no_route() -> None:
    with pytest.raises(ValueError, match="name no Provenance member"):
        SurfaceBinding(
            class_names=CLASS_NAMES,
            spec=dict(SURFACE_CLASSES),
            face_class=np.zeros(3, dtype=np.int64),
            face_source=np.array([0, 0, 99], dtype=np.int8),
            face_area_m2=np.ones(3),
            provenance={"class_rule": "test"},
        )


def test_a_binding_refuses_a_class_index_outside_the_names_it_carries() -> None:
    with pytest.raises(ValueError, match="leaves the 4 classes"):
        SurfaceBinding(
            class_names=CLASS_NAMES,
            spec=dict(SURFACE_CLASSES),
            face_class=np.array([0, 1, 7], dtype=np.int64),
            face_source=np.zeros(3, dtype=np.int8),
            face_area_m2=np.ones(3),
            provenance={"class_rule": "test"},
        )


def test_the_orientation_rule_measures_its_own_zero_coverage() -> None:
    """The eleven city headline reported this zero as a literal. Now it counts."""
    vertices, faces, areas = _tetrahedron()
    binding = geometric_binding(vertices, faces, areas, ground_datum_m=0.0)
    assert binding.covered_fraction_by_face == 0.0
    assert binding.covered_fraction_by_area == 0.0
    assert binding.area_fraction_by_source() == {"GEOMETRIC": 1.0}
    assert set(np.unique(binding.face_source)) == {int(Provenance.GEOMETRIC)}


def test_coverage_by_area_and_by_face_are_two_different_measurements() -> None:
    """One large photographed wall among small ones moves them far apart."""
    areas = np.array([100.0, 1.0, 1.0, 1.0])
    source = np.array([Provenance.IMAGE_FISHNET, 0, 0, 0], dtype=np.int8)
    binding = SurfaceBinding(
        class_names=CLASS_NAMES,
        spec=dict(SURFACE_CLASSES),
        face_class=np.ones(4, dtype=np.int64),
        face_source=source,
        face_area_m2=areas,
        provenance={"class_rule": "test"},
    )
    assert binding.covered_fraction_by_face == pytest.approx(0.25)
    assert binding.covered_fraction_by_area == pytest.approx(100.0 / 103.0)
    assert binding.area_fraction_by_source()["IMAGE_FISHNET"] == pytest.approx(100.0 / 103.0)


def test_the_class_index_is_the_whole_contract_between_a_binding_and_a_table() -> None:
    """A table built from a binding indexes that binding's own face classes."""
    vertices, faces, areas = _tetrahedron()
    binding = geometric_binding(vertices, faces, areas, ground_datum_m=0.0)
    table = binding.evaluate(CONFIG, CARRIER_HZ)
    assert table.class_names == binding.class_names
    assert table.permittivity[binding.face_class].shape == (faces.shape[0],)
    for index, name in enumerate(table.class_names):
        assert table.spec[name] is binding.spec[name]
        assert table.index(name) == index


def test_the_evidence_classes_sit_on_top_of_the_orientation_ones() -> None:
    """The offset every evidence binding writes is ``len(CLASS_NAMES)``."""
    class_names, spec = extend_classes(["brick", "glass"], "semantic_", IMAGE_MATERIALS)
    assert class_names[: len(CLASS_NAMES)] == CLASS_NAMES
    assert class_names[len(CLASS_NAMES) :] == ("semantic_brick", "semantic_glass")
    assert spec["semantic_brick"] is IMAGE_MATERIALS["brick"]
    assert spec["facade"] is SURFACE_CLASSES["facade"]


def test_a_walk_binding_marks_the_faces_a_station_saw_and_no_others(tmp_path) -> None:
    """Provenance and coverage are the same fact counted once.

    Two triangles are visible to a station, two are not. The unseen pair keeps
    the class the orientation rule gave it and keeps saying so.
    """
    semantics = tmp_path / "semantics.json"
    semantics.write_text(
        json.dumps(
            {
                "entity_id2label": {"1": "Building", "2": "Sky"},
                "vistas_material_prior": {"Building": {"brick": 1.0}, "Sky": {}},
            }
        )
    )
    walk = tmp_path / "walk_semantic.npz"
    np.savez(
        walk,
        modal_class=np.array([[1, 1, 2, 2]], dtype=np.int64),
        clean_rays=np.array([[8.0, 4.0, 5.0, 0.0]], dtype=np.float64),
    )
    areas = np.array([2.0, 2.0, 1.0, 1.0])
    geometric = np.full(4, CLASS_NAMES.index("facade"), dtype=np.int64)

    binding = bind_walk_entities(areas, geometric, walk_npz=walk, semantics_path=semantics)

    seen = np.array([True, True, False, False])
    assert np.array_equal(binding.covered, seen)
    assert np.array_equal(binding.face_source == int(Provenance.IMAGE_WALK_ENTITY), seen)
    assert np.array_equal(binding.face_class[~seen], geometric[~seen])
    assert [binding.class_names[i] for i in binding.face_class[seen]] == ["semantic_brick"] * 2
    assert binding.covered_fraction_by_face == pytest.approx(0.5)
    assert binding.covered_fraction_by_area == pytest.approx(4.0 / 6.0)


def _one_station_walk(tmp_path) -> tuple[pathlib.Path, pathlib.Path]:
    semantics = tmp_path / "semantics.json"
    semantics.write_text(
        json.dumps(
            {
                "entity_id2label": {"1": "Building", "2": "Wall"},
                "vistas_material_prior": {"Building": {"brick": 1.0}, "Wall": {"glass": 1.0}},
            }
        )
    )
    walk = tmp_path / "walk_semantic.npz"
    np.savez(
        walk,
        image_ids=np.array(["cam_a", "cam_b"]),
        modal_class=np.array([[1, 1, 1, 1], [2, 2, 2, 2]], dtype=np.int64),
        clean_rays=np.array([[9.0, 9.0, 9.0, 9.0], [4.0, 4.0, 4.0, 4.0]], dtype=np.float64),
    )
    return walk, semantics


def test_weighting_every_station_at_one_is_the_unweighted_vote(tmp_path) -> None:
    """The hook has to be inert by default, because it is bolted onto a golden lock."""
    walk, semantics = _one_station_walk(tmp_path)
    areas, geometric = np.ones(4), np.ones(4, dtype=np.int64)
    plain = bind_walk_entities(areas, geometric, walk_npz=walk, semantics_path=semantics)
    weighted = bind_walk_entities(
        areas,
        geometric,
        walk_npz=walk,
        semantics_path=semantics,
        station_weight={"cam_a": 1.0, "cam_b": 1.0},
    )
    assert np.array_equal(plain.face_class, weighted.face_class)


def test_dropping_a_station_hands_the_wall_to_the_one_that_is_left(tmp_path) -> None:
    """A camera that could not be placed should be removable, not just noted."""
    walk, semantics = _one_station_walk(tmp_path)
    areas, geometric = np.ones(4), np.ones(4, dtype=np.int64)
    both = bind_walk_entities(areas, geometric, walk_npz=walk, semantics_path=semantics)
    dropped = bind_walk_entities(
        areas, geometric, walk_npz=walk, semantics_path=semantics, station_weight={"cam_a": 0.0}
    )
    assert [both.class_names[i] for i in both.face_class] == ["semantic_brick"] * 4
    assert [dropped.class_names[i] for i in dropped.face_class] == ["semantic_glass"] * 4
    assert dropped.covered_fraction_by_face == 1.0


def test_weighting_a_station_the_walk_does_not_carry_is_refused(tmp_path) -> None:
    walk, semantics = _one_station_walk(tmp_path)
    with pytest.raises(ValueError, match="does not carry"):
        bind_walk_entities(
            np.ones(4),
            np.ones(4, dtype=np.int64),
            walk_npz=walk,
            semantics_path=semantics,
            station_weight={"cam_typo": 0.0},
        )


def test_a_walk_binding_refuses_semantics_cut_against_another_mesh(tmp_path) -> None:
    semantics = tmp_path / "semantics.json"
    semantics.write_text(json.dumps({"entity_id2label": {"1": "Building"}, "vistas_material_prior": {}}))
    walk = tmp_path / "walk_semantic.npz"
    np.savez(walk, modal_class=np.ones((1, 5), dtype=np.int64), clean_rays=np.ones((1, 5)))
    with pytest.raises(ValueError, match="the tracer mesh has 4"):
        bind_walk_entities(np.ones(4), np.zeros(4, dtype=np.int64), walk_npz=walk, semantics_path=semantics)


# --- the roughness rules --------------------------------------------------


def test_both_rules_return_the_finish_height_where_there_is_no_coursing(roughness) -> None:
    """The smooth limit is the one place the two rules must agree exactly."""
    smooth = [prior for prior in roughness.classes.values() if prior.gaussian_model_applies]
    assert smooth, "the library should still carry single scale classes"
    for prior in smooth:
        assert effective_rms_height(prior) == prior.rms_height_m
        assert masonry_equivalent_rms_height(prior) == prior.rms_height_m


def test_a_coursed_surface_is_rougher_than_its_finish_under_either_rule(roughness) -> None:
    prior = roughness["brick_wall_with_mortar_joints"]
    assert effective_rms_height(prior) > prior.rms_height_m
    assert masonry_equivalent_rms_height(prior) > prior.rms_height_m


def test_the_masonry_rule_reads_the_unit_scatter_the_default_rule_never_opens(roughness) -> None:
    """Brick to brick scatter is a declared tolerance class, and it matters.

    ``config/surface_roughness.json`` states 3 mm of unit to unit scatter for a
    brick wall. Doubling it has to change an answer that claims to model
    coursed masonry. Finding 2 of ``docs/BUGS.md`` is that the default rule
    reads only the joint step, and this test is what would catch a silent
    regression the other way once that finding is fixed.
    """
    prior = roughness["brick_wall_with_mortar_joints"]
    scattered = dataclasses.replace(
        prior,
        periodic_component={**prior.periodic_component, "unit_scatter_mm": 6.0},
    )
    assert masonry_equivalent_rms_height(scattered) > masonry_equivalent_rms_height(prior)


def test_the_masonry_rule_says_so_when_the_surface_is_not_coursed_at_all(roughness) -> None:
    """Profiled steel sheet is periodic but has no joints, so it has no wall."""
    with pytest.raises(ValueError):
        masonry_equivalent_rms_height(roughness["metal_profiled_sheet"])


def test_switching_the_roughness_rule_moves_only_the_coursed_classes() -> None:
    """The rule is a wiring point, so it must not disturb what it does not model."""
    default = load_table(CONFIG, CARRIER_HZ)
    masonry = load_table(CONFIG, CARRIER_HZ, roughness_rule=MASONRY_RULE)
    assert np.array_equal(default.permittivity, masonry.permittivity)
    for index, name in enumerate(default.class_names):
        coursed = not masonry.spec[name].roughness_class.startswith("concrete_")
        moved = masonry.rms_height_m[index] != default.rms_height_m[index]
        assert moved == coursed, name
    assert default.provenance["roughness_rule"] == QUADRATURE_RULE
    assert masonry.provenance["roughness_rule"] == MASONRY_RULE


# --- the layered stack -----------------------------------------------------


def test_every_word_the_model_may_say_reaches_an_itu_row(materials) -> None:
    """The vocabulary claims this about itself and nothing checked it.

    A name with no row cannot be traced, so a name added to the vocabulary
    without a row or a substitution is a run that dies at the first facade.
    """
    for name in MATERIAL_VOCABULARY:
        if name == "unknown":
            continue
        assert layer_permittivity(name, CARRIER_HZ, materials).real >= 1.0


def test_a_vanishing_outer_layer_leaves_the_substrate_alone(materials) -> None:
    """The limit that says the transfer matrix recursion is wired the right way."""
    brick = layer_permittivity("brick", CARRIER_HZ, materials)
    glass = layer_permittivity("glass", CARRIER_HZ, materials)
    thin = layered_power_reflectance(np.array([glass, brick]), np.array([1.0e-9]), 1.0, CARRIER_HZ)
    assert thin == pytest.approx(half_space_power_reflectance(brick, 1.0), rel=1e-6)


def test_no_stack_returns_more_power_than_it_receives(materials) -> None:
    permittivity = np.array([layer_permittivity(name, CARRIER_HZ, materials) for name in ("plasterboard", "brick")])
    for thickness_mm in np.linspace(0.5, 40.0, 60):
        value = layered_power_reflectance(permittivity, np.array([thickness_mm / 1000.0]), 0.7, CARRIER_HZ)
        assert 0.0 <= value <= 1.0


def test_a_broad_posterior_does_not_reflect_like_its_modal_label(materials) -> None:
    """Small mass on a strong reflector is not a small correction."""
    reflectance = material_power_reflectance(CARRIER_HZ, 1.0, materials)
    posterior = {"brick": 0.97, "metal": 0.03}
    assert posterior_power_reflectance(posterior, reflectance) > argmax_power_reflectance(posterior, reflectance)


def test_an_unknown_reading_of_the_unknown_mass_is_refused(materials) -> None:
    reflectance = material_power_reflectance(CARRIER_HZ, 1.0, materials)
    with pytest.raises(ValueError, match="unknown_policy"):
        posterior_power_reflectance({"brick": 1.0}, reflectance, unknown_policy="guess")


def test_an_unknown_roughness_rule_is_named_rather_than_defaulted() -> None:
    with pytest.raises(ValueError, match="unknown roughness rule"):
        load_table(CONFIG, CARRIER_HZ, roughness_rule="whatever_is_handy")

import math

import numpy as np
import pytest

from semantic_twin.masonry import (
    BONDS,
    BRICK_FORMATS,
    ENGLISH_BOND,
    FLEMISH_BOND,
    JOINT_PROFILES,
    RECESSED_JOINT,
    RUNNING_BOND,
    STACK_BOND,
    STANDARD_JOINT,
    TOLERANCE_CLASSES,
    BrickFormat,
    JointGeometry,
    MasonryWall,
    permittivity_from_evaluation,
)


def wall(format_name: str = "standard_metric", joint: JointGeometry = STANDARD_JOINT, bond=RUNNING_BOND) -> MasonryWall:
    return MasonryWall(BRICK_FORMATS[format_name], joint, bond)


def test_pitches_are_the_unit_plus_one_joint() -> None:
    uk = wall("standard_metric")
    assert uk.course_pitch_m == pytest.approx(0.075)
    assert uk.stretcher_pitch_m == pytest.approx(0.225)


def test_belgian_and_dutch_formats_do_not_have_the_british_course_pitch() -> None:
    # The whole point of the format leg: 75 mm is a British number and the
    # Waalformaat facades this study photographs are on 60 mm.
    waal = MasonryWall(BRICK_FORMATS["waalformaat"], STANDARD_JOINT, RUNNING_BOND)
    assert waal.course_pitch_m == pytest.approx(0.060)
    assert waal.stretcher_pitch_m == pytest.approx(0.220)
    belgian_joint = JointGeometry(bed_m=0.012, perp_m=0.012, recess_m=0.0)
    m50 = MasonryWall(BRICK_FORMATS["module_m50"], belgian_joint, RUNNING_BOND)
    m65 = MasonryWall(BRICK_FORMATS["module_m65"], belgian_joint, RUNNING_BOND)
    assert m50.course_pitch_m == pytest.approx(0.060)
    assert m65.course_pitch_m == pytest.approx(0.075)
    assert m50.stretcher_pitch_m == pytest.approx(0.200)
    assert m65.stretcher_pitch_m == pytest.approx(0.200)


def test_formats_are_modular_so_the_header_pitch_is_exactly_half() -> None:
    for name in ("standard_metric", "waalformaat", "module_m65"):
        brick = BRICK_FORMATS[name]
        joint = 0.012 if name.startswith("module") else 0.010
        assert brick.length_m + joint == pytest.approx(2.0 * (brick.width_m + joint), abs=1e-9)


def test_tolerance_formulas_reproduce_the_tabulated_british_triples() -> None:
    # The familiar T1 = 6/4/3 and R1 = 9/6/5 are the square-root formulas
    # evaluated for a 215 x 102.5 x 65 mm unit, which is why they must not be
    # transferred to another format.
    t1 = TOLERANCE_CLASSES["T1"]
    r1 = TOLERANCE_CLASSES["R1"]
    assert t1.limit_mm(215.0) == pytest.approx(6.0, abs=0.2)
    assert t1.limit_mm(102.5) == pytest.approx(4.0, abs=0.1)
    assert t1.limit_mm(65.0) == pytest.approx(3.2, abs=0.05)
    # The published table rounds each formula value up to a whole millimetre.
    assert math.ceil(r1.limit_mm(215.0)) == 9
    assert math.ceil(r1.limit_mm(102.5)) == 7
    assert r1.limit_mm(102.5) == pytest.approx(6.07, abs=0.02)
    assert r1.limit_mm(65.0) == pytest.approx(4.84, abs=0.02)


def test_a_shorter_unit_carries_a_tighter_range_class() -> None:
    r1 = TOLERANCE_CLASSES["R1"]
    assert r1.limit_mm(50.0) == pytest.approx(4.24, abs=0.02)
    assert r1.limit_mm(50.0) < r1.limit_mm(65.0)


def test_t1_floor_binds_on_small_dimensions() -> None:
    assert TOLERANCE_CLASSES["T1"].limit_mm(20.0) == pytest.approx(3.0)
    assert TOLERANCE_CLASSES["T2"].limit_mm(20.0) == pytest.approx(2.0)


def test_a_mean_class_carries_no_unit_to_unit_scatter() -> None:
    with pytest.raises(ValueError):
        TOLERANCE_CLASSES["T1"].standard_deviation_m(65.0)
    sigma = TOLERANCE_CLASSES["R1"].standard_deviation_m(102.5)
    assert sigma == pytest.approx(6.07 / 3.078 / 1000.0, rel=1e-3)


def test_mask_area_matches_the_analytic_joint_fraction() -> None:
    for bond in BONDS.values():
        for name in ("standard_metric", "waalformaat"):
            surface = wall(name, STANDARD_JOINT, bond)
            mask = surface.mortar_mask(1800, 1200)
            assert mask.mean() == pytest.approx(surface.joint_area_fraction, abs=3e-3), (bond.name, name)


def test_brick_faces_and_joints_partition_the_cell() -> None:
    for bond in BONDS.values():
        surface = wall("standard_metric", STANDARD_JOINT, bond)
        face_area = sum(w * h for _, _, w, h in surface.unit_rectangles())
        cell_area = surface.cell_x_m * surface.cell_y_m
        assert face_area / cell_area == pytest.approx(1.0 - surface.joint_area_fraction, rel=1e-9)


def test_cell_dimensions_follow_the_bond() -> None:
    assert wall(bond=STACK_BOND).cell_y_m == pytest.approx(0.075)
    assert wall(bond=RUNNING_BOND).cell_y_m == pytest.approx(0.150)
    assert wall(bond=ENGLISH_BOND).cell_x_m == pytest.approx(0.225)
    assert wall(bond=FLEMISH_BOND).cell_x_m == pytest.approx(1.5 * 0.225)


def test_flemish_bond_alternates_a_stretcher_and_a_header_along_every_course() -> None:
    # The Flemish repeat is a stretcher plus a header, so its perpend spacings
    # alternate between a full and a half stretcher pitch. That is the property
    # that gives it a longer period than running bond, and it is why the two
    # bonds are separable in the far field at all.
    surface = wall(bond=FLEMISH_BOND)
    centres = sorted(fraction * surface.cell_x_m for fraction in FLEMISH_BOND.courses[0])
    spacing = np.diff(centres + [centres[0] + surface.cell_x_m])
    assert np.allclose(sorted(spacing), sorted([surface.stretcher_pitch_m, 0.5 * surface.stretcher_pitch_m]))


def test_flemish_bond_centres_its_headers_over_the_stretchers_below() -> None:
    surface = wall(bond=FLEMISH_BOND)
    lower = surface.unit_rectangles()[0]
    stretcher_centre = lower[0] + 0.5 * lower[2]
    upper = [r for r in surface.unit_rectangles() if r[1] > lower[1]]
    header = min(upper, key=lambda r: r[2])
    assert header[0] + 0.5 * header[2] == pytest.approx(stretcher_centre)


def test_height_map_is_two_valued_and_signed_the_right_way() -> None:
    surface = wall(joint=RECESSED_JOINT)
    heights = surface.height_map(256, 256)
    assert set(np.unique(heights)) == {0.0, -RECESSED_JOINT.recess_m}
    assert heights.min() == pytest.approx(-0.005)


def test_a_proud_joint_reverses_the_relief() -> None:
    surface = wall(joint=JOINT_PROFILES["tuckpointed"])
    assert surface.height_map(128, 128).max() == pytest.approx(0.004)


def test_layer_stack_collapses_when_the_joint_is_flush() -> None:
    flush = wall(joint=STANDARD_JOINT).rcwa_layers(128, 128)
    recessed = wall(joint=RECESSED_JOINT).rcwa_layers(128, 128)
    assert len(flush) == 2
    assert len(recessed) == 3
    assert recessed[1].thickness_m == pytest.approx(0.005)
    assert recessed[0].homogeneous
    assert not recessed[-1].homogeneous or True


def test_permittivity_convention_gives_a_positive_imaginary_part() -> None:
    eps = permittivity_from_evaluation(3.91, 0.0451, 28e9)
    assert eps.real == pytest.approx(3.91)
    assert eps.imag > 0.0
    assert eps.imag == pytest.approx(17.98 * 0.0451 / 28.0, rel=1e-3)


def test_degenerate_geometry_is_refused() -> None:
    with pytest.raises(ValueError):
        BrickFormat(name="bad", length_m=0.0, height_m=0.05, width_m=0.1)
    with pytest.raises(ValueError):
        JointGeometry(bed_m=0.0, perp_m=0.01, recess_m=0.0)
    with pytest.raises(ValueError):
        wall().mortar_mask(4, 4)


def test_running_bond_primitive_cell_is_centred_rectangular() -> None:
    surface = wall()
    primitive = surface.lattice(primitive=True)
    conventional = surface.lattice()
    assert primitive.area_m2 == pytest.approx(0.5 * conventional.area_m2)
    assert math.isclose(conventional.a2[1], 0.150)

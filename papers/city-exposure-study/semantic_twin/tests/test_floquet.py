import math

import numpy as np
import pytest

from semantic_twin.materials.masonry import (
    Lattice,
    centred_rectangular_lattice,
    diffraction_orders,
    grating_order_angles_deg,
    incident_wavevector,
    rectangular_lattice,
)
from semantic_twin.materials.roughness import wavelength_m


def test_reciprocal_vectors_satisfy_their_defining_relation() -> None:
    lattice = Lattice((0.225, 0.0), (0.1125, 0.075))
    b1, b2 = lattice.reciprocal()
    assert np.dot(b1, lattice.a1) == pytest.approx(2.0 * math.pi)
    assert np.dot(b2, lattice.a2) == pytest.approx(2.0 * math.pi)
    assert np.dot(b1, lattice.a2) == pytest.approx(0.0, abs=1e-12)
    assert np.dot(b2, lattice.a1) == pytest.approx(0.0, abs=1e-12)


def test_degenerate_lattice_is_refused() -> None:
    with pytest.raises(ValueError):
        Lattice((0.1, 0.0), (0.2, 0.0))


def test_centred_rectangular_cell_is_half_the_rectangular_one() -> None:
    rectangular = rectangular_lattice(0.225, 0.075)
    centred = centred_rectangular_lattice(0.225, 0.075)
    assert centred.area_m2 == pytest.approx(rectangular.area_m2)
    # The running bond primitive cell holds one brick where the conventional
    # rectangular cell of two courses holds two, so the conventional cell is
    # twice the primitive area.
    conventional = rectangular_lattice(0.225, 0.150)
    assert conventional.area_m2 == pytest.approx(2.0 * centred.area_m2)


def test_grating_equation_reproduces_textbook_order_angles() -> None:
    # 75 mm pitch at 28 GHz is 7.0 wavelengths, so order m leaves at
    # arcsin(m / 7.0) under normal incidence.
    lam = float(wavelength_m(28e9))
    pitch = 0.075
    angles = grating_order_angles_deg(pitch, 28e9, 0.0)
    expected = [math.degrees(math.asin(m * lam / pitch)) for m in range(-7, 8) if abs(m * lam / pitch) <= 1.0]
    assert np.allclose(np.sort(angles), np.sort(expected))


def test_order_count_at_28_ghz_matches_the_roughness_note() -> None:
    # ROUGHNESS.md quotes 15 orders for a 75 mm course pitch and 43 for a
    # 225 mm stretcher pitch at 28 GHz under normal incidence.
    assert grating_order_angles_deg(0.075, 28e9, 0.0).size == 15
    assert grating_order_angles_deg(0.225, 28e9, 0.0).size == 43


def test_two_dimensional_orders_agree_with_the_one_dimensional_closed_form() -> None:
    lattice = rectangular_lattice(0.225, 0.075)
    orders = diffraction_orders(lattice, 28e9, 35.0, 0.0)
    in_plane = orders.propagating & (orders.n == 0)
    computed = np.sort(orders.theta_deg[in_plane] * np.sign(orders.kx[in_plane]))
    closed_form = np.sort(grating_order_angles_deg(0.225, 28e9, 35.0))
    assert np.allclose(computed, closed_form, atol=1e-9)


def test_incident_wavevector_has_the_right_length_and_points_at_the_wall() -> None:
    k = incident_wavevector(28e9, 62.0, 17.0)
    k0 = 2.0 * math.pi / float(wavelength_m(28e9))
    assert np.linalg.norm(k) == pytest.approx(k0)
    assert k[2] < 0.0


def test_order_count_falls_as_the_wavelength_grows() -> None:
    lattice = rectangular_lattice(0.220, 0.060)
    counts = [diffraction_orders(lattice, f, 0.0, 0.0).count for f in (7e9, 15e9, 28e9, 40e9)]
    assert counts == sorted(counts)
    assert counts[0] < counts[-1] / 4


def test_evanescent_orders_are_retained_but_not_counted() -> None:
    orders = diffraction_orders(rectangular_lattice(0.225, 0.075), 28e9, 0.0, 0.0)
    assert orders.count < orders.m.size
    assert np.all(np.real(orders.kz[~orders.propagating]) < 1e-6)


def test_selecting_an_absent_order_raises() -> None:
    orders = diffraction_orders(rectangular_lattice(0.225, 0.075), 28e9, 0.0, 0.0, order_limit=2)
    assert orders.select(0, 0) >= 0
    with pytest.raises(KeyError):
        orders.select(99, 99)


def test_angular_separation_is_the_nearest_neighbour_spacing() -> None:
    orders = diffraction_orders(rectangular_lattice(0.075, 0.075), 28e9, 0.0, 0.0)
    separations = orders.angular_separations_deg()
    assert separations.size == orders.count
    assert np.all(separations > 0.0)
    assert np.median(separations) < 30.0

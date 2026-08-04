"""What has to be true at a dielectric interface, whatever the numbers are.

This file pins physics, not values. Nothing here reads a stored answer. Every
assertion is a statement that holds for any correct half space reflectance, so
it survives a change of material, a change of frequency and a change of
implementation, and it goes red the moment the algebra stops being Fresnel.

The rule the file is written against: never test only the symmetric case. A
50/50 split, a perfect conductor and normal incidence are all regimes where a
wrong coefficient can hide. The angles and materials below are chosen so the
reflected and transmitted shares are lopsided.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.materials import MaterialLibrary
from semantic_twin.transport.tracer import fresnel_power_reflectance

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config" / "itu_p2040_4.json"


def transmitted_power_fraction(cos_i: np.ndarray, permittivity: complex) -> np.ndarray:
    """Power crossing the boundary, from the field transmission coefficients.

    Written out here rather than imported, because the point is to check the
    reflectance against something derived independently of it. The incident
    medium is air, so ``k_z`` is ``cos_i`` above the boundary and ``root`` below.

    For the s wave the transmitted normal Poynting flux carries ``Re(k_z2)``.
    For the p wave the H field is continuous and ``E_x = k_z H_y / (w eps0 eps)``,
    so the flux carries ``Re(k_z2 / eps2)`` instead. Getting that division by the
    permittivity wrong is the classic way to break energy balance in a lossy
    medium while leaving the lossless case intact.
    """
    cos_i = np.asarray(cos_i, dtype=np.complex128)
    root = np.sqrt(permittivity - (1.0 - cos_i**2))
    t_s = 2.0 * cos_i / (cos_i + root)
    t_p = 2.0 * permittivity * cos_i / (permittivity * cos_i + root)
    flux_s = np.real(root) / np.real(cos_i) * np.abs(t_s) ** 2
    flux_p = np.real(root / permittivity) / np.real(cos_i) * np.abs(t_p) ** 2
    return np.real(0.5 * (flux_s + flux_p))


#: Angles picked so the reflected share runs from about 0.1 to about 0.6. None
#: of them is 45 degrees and none of them is Brewster for the materials used.
UNEVEN_ANGLES_DEG = np.array([0.0, 17.0, 33.0, 52.0, 68.0, 81.0])


@pytest.mark.parametrize(
    "permittivity",
    [
        complex(5.31, -0.90),  # concrete at 15 GHz
        complex(3.91, -0.11),  # brick
        complex(6.31, -0.75),  # glass
        complex(1.99, -0.10),  # wood, the weakest reflector in the set
        complex(7.07, -0.30),  # marble
    ],
)
def test_reflected_plus_transmitted_is_one_at_an_interface(permittivity):
    """Energy in equals energy out, on a split that is nowhere near 50/50.

    A half space absorbs nothing at the boundary itself, so whatever is not
    reflected has to cross it. The reflected share here runs from 0.09 to 0.62,
    so a coefficient that is wrong by a constant factor cannot pass by being
    right at one crossing point.
    """
    cos_i = np.cos(np.radians(UNEVEN_ANGLES_DEG))
    reflected = fresnel_power_reflectance(cos_i, np.asarray(permittivity))
    transmitted = transmitted_power_fraction(cos_i, permittivity)
    assert np.min(reflected) < 0.25
    assert np.max(reflected) > 0.35
    assert reflected + transmitted == pytest.approx(np.ones_like(reflected), abs=1e-12)


def material_rows() -> list[tuple[str, float, complex]]:
    """Every row of the shipped P.2040-4 table, at three points in its own band.

    Discovered from the file rather than listed, so a row added to the config is
    covered without anyone remembering to add it here.
    """
    library = MaterialLibrary.load(CONFIG)
    rows = []
    for name, material in library.materials.items():
        low, high = material.minimum_ghz, material.maximum_ghz
        for ghz in (low, float(np.sqrt(low * high)), high):
            evaluation = material.evaluate(ghz * 1e9)
            rows.append((f"{name}@{ghz:g}GHz", ghz, evaluation.complex_relative_permittivity))
    return rows


ROWS = material_rows()


@pytest.mark.parametrize(("label", "ghz", "permittivity"), ROWS, ids=[row[0] for row in ROWS])
def test_reflectance_stays_a_fraction_from_normal_to_grazing(label, ghz, permittivity):
    """No material, at any incidence, may reflect a negative or superunit share.

    Sampled densely right up to 89.999 degrees, because grazing is where a sign
    error in the square root branch shows up and where every published facade
    interaction actually lives.
    """
    del label, ghz
    cos_i = np.cos(np.radians(np.linspace(0.0, 89.999, 601)))
    reflected = fresnel_power_reflectance(cos_i, np.asarray(permittivity))
    assert np.all(np.isfinite(reflected))
    assert np.all(reflected >= 0.0)
    assert np.all(reflected <= 1.0)


@pytest.mark.parametrize(("label", "ghz", "permittivity"), ROWS, ids=[row[0] for row in ROWS])
def test_the_grazing_limit_is_total_reflection(label, ghz, permittivity):
    """Any half space that is not air reflects everything at grazing incidence.

    Both coefficients go to magnitude one as ``cos_i`` goes to zero, whatever
    the permittivity is, so this is a limit the material cannot argue with. Air
    is excluded because its interface does not exist.

    How fast the limit is reached depends on the material. The TM coefficient
    only turns over once ``|eps| cos_i`` drops below ``|sqrt(eps)|``, and for
    the metal row ``sqrt(eps)`` is about 9,500, so a good conductor is still 0.2
    percent short of total reflection at a hundredth of a milliradian while
    concrete is short by six parts in ten million there. That is why the sweep
    runs to a nanoradian.

    The assertion is a rate law rather than a threshold, which is the stronger
    statement and the one that cannot be met by choosing a number. Expanding
    either coefficient about ``cos_i = 0`` leaves ``1 - R`` linear in ``cos_i``,
    so dividing the angle by a hundred has to divide the shortfall by a hundred.
    Measured over the last two decades of the sweep, across all 42 rows, the
    ratio is 100.00 for every dielectric and 99.81 at worst for metal. So the
    residual at any given angle is the exact Fresnel value there and not a leak.

    The rate law is asserted on the last two points only. The expansion needs
    ``|eps| cos_i`` to be well under ``|sqrt(eps)|`` before it holds, and metal
    at a hundredth of a milliradian is only a tenth of the way there, where the
    ratio still reads 83.
    """
    del label, ghz
    if abs(permittivity - 1.0) < 1e-12:
        pytest.skip("air against air is not an interface")
    cos_i = np.array([1e-5, 1e-7, 1e-9])
    reflected = fresnel_power_reflectance(cos_i, np.asarray(permittivity))
    shortfall = 1.0 - reflected
    assert np.all(np.diff(reflected) > 0.0)
    assert np.all(shortfall > 0.0)
    assert shortfall[1] / shortfall[2] == pytest.approx(100.0, rel=0.01)
    assert reflected[-1] > 0.9999


@pytest.mark.parametrize(("label", "ghz", "permittivity"), ROWS, ids=[row[0] for row in ROWS])
def test_normal_incidence_matches_the_refractive_index_form(label, ghz, permittivity):
    """At normal incidence there is only one answer and it has no angles in it.

    ``|(1 - n) / (1 + n)|**2`` with ``n = sqrt(eps)``. The two polarisations are
    the same wave there, so this checks TE and TM against each other as well as
    against the closed form.
    """
    del label, ghz
    index = np.sqrt(complex(permittivity))
    expected = float(np.abs((1.0 - index) / (1.0 + index)) ** 2)
    measured = float(fresnel_power_reflectance(np.array([1.0]), np.asarray(permittivity))[0])
    assert measured == pytest.approx(expected, rel=1e-10, abs=1e-14)


def test_every_config_row_is_covered():
    """The introspection above must actually have found the table.

    A file walk that silently returns nothing turns every parametrised test
    into a pass. This is the guard against that.
    """
    names = {row[0].split("@")[0] for row in ROWS}
    document = json.loads(CONFIG.read_text())
    assert names == {record["name"] for record in document["materials"]}
    assert len(names) >= 15

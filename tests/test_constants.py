"""Tests for physical constants in aegis.constants."""

import math

from aegis.constants import C_0, EPS_0, MU_0, Z_0


def test_c0_from_mu0_eps0():
    """Tabulated MU_0 and EPS_0 are rounded; C_0 is exact, so match is ~2e-10 relative."""
    expected = 1.0 / math.sqrt(MU_0 * EPS_0)
    assert math.isclose(C_0, expected, rel_tol=1e-9, abs_tol=0.0)


def test_z0_from_mu0_eps0():
    expected = math.sqrt(MU_0 / EPS_0)
    assert math.isclose(Z_0, expected, rel_tol=1e-9, abs_tol=0.0)

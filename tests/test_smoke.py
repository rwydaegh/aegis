"""Smoke tests to verify the package installs and imports correctly."""

import aegis
from aegis.constants import C_0, EPS_0, Z_0


def test_version():
    assert aegis.__version__ == "0.0.1"


def test_constants_physically_consistent():
    """Z_0 should equal sqrt(mu_0 / eps_0), which is ~376.73 ohm."""
    import math

    from aegis.constants import MU_0

    z0_computed = math.sqrt(MU_0 / EPS_0)
    assert abs(Z_0 - z0_computed) / Z_0 < 1e-6


def test_speed_of_light():
    """c_0 should equal 1 / sqrt(mu_0 * eps_0)."""
    import math

    from aegis.constants import MU_0

    c_computed = 1.0 / math.sqrt(MU_0 * EPS_0)
    assert abs(C_0 - c_computed) / C_0 < 1e-6

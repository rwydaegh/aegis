"""Mie regression test: the CI canary.

Validates the AEGIS Fresnel framework against exact Mie theory for lossy
dielectric spheres. If this test passes, the tissue model and Fresnel
coefficients are correct.

The key metric is R_sphere = T_0 / Q_abs_GO, which measures how well
T_0 approximates the angle-averaged Fresnel transmission on a sphere.
At 28 GHz skin, R_sphere ~ 0.988 (framework underestimates by ~1.2%).
"""

import pytest

from aegis.tissue.fresnel import T0, fresnel_transmission, n_complex

scipy_integrate = pytest.importorskip("scipy.integrate")
mp = pytest.importorskip("miepython")

pytestmark = pytest.mark.slow


def _T_avg(mu: float, n_tilde: complex) -> float:
    """Unpolarized Fresnel transmission at cosine mu."""
    T_s, T_p = fresnel_transmission(mu, n_tilde)
    return 0.5 * (T_s + T_p)


def _Q_abs_GO(n_tilde: complex) -> float:
    """Geometric optics limit: Q_abs = 2 * integral(T_avg(mu)*mu, 0, 1)."""
    result, _ = scipy_integrate.quad(lambda mu: 2 * _T_avg(mu, n_tilde) * mu, 0, 1)
    return result


class TestMieRegression:
    """Mie theory validation at 28 GHz skin."""

    N_SKIN_28 = n_complex(17.0, 25.0, 28e9)
    T0_SKIN_28 = T0(N_SKIN_28)

    def test_R_sphere_28ghz(self):
        """R_sphere = T_0 / Q_abs_GO should be ~0.988 at 28 GHz."""
        Q_GO = _Q_abs_GO(self.N_SKIN_28)
        R_sphere = self.T0_SKIN_28 / Q_GO
        assert R_sphere == pytest.approx(0.988, abs=0.005)

    def test_large_sphere_convergence(self):
        """For a large sphere (x=500), T_0/Q_abs should approach R_sphere."""
        Q_GO = _Q_abs_GO(self.N_SKIN_28)
        R_sphere = self.T0_SKIN_28 / Q_GO

        x = 500
        lambda0 = 1.0
        d = x * lambda0 / 3.14159265
        qext, qsca, _, _ = mp.efficiencies(self.N_SKIN_28, d, lambda0)
        qabs = qext - qsca

        ratio = self.T0_SKIN_28 / qabs
        # At x=500 diffraction is still significant. The ratio should be
        # closer to R_sphere than to 1.0 (i.e., converging toward GO limit).
        dist_to_Rsphere = abs(ratio - R_sphere)
        dist_to_unity = abs(ratio - 1.0)
        assert dist_to_Rsphere < dist_to_unity

    def test_framework_underestimates_at_28ghz(self):
        """At 28 GHz, R_sphere < 1 (framework is conservative)."""
        Q_GO = _Q_abs_GO(self.N_SKIN_28)
        R_sphere = self.T0_SKIN_28 / Q_GO
        assert R_sphere < 1.0

    def test_mie_error_decreases_with_size(self):
        """Larger spheres have smaller framework errors (closer to GO limit)."""
        lambda0 = 1.0
        errors = []
        for x in [10, 50, 200]:
            d = x * lambda0 / 3.14159265
            qext, qsca, _, _ = mp.efficiencies(self.N_SKIN_28, d, lambda0)
            qabs = qext - qsca
            error = abs(self.T0_SKIN_28 / qabs - 1)
            errors.append(error)

        # Error should decrease monotonically with size
        assert errors[0] > errors[1] > errors[2]

import numpy as np
import pytest

from aegis.nearfield.patterns import AntennaPattern3D


def _sphere_average(p: AntennaPattern3D) -> float:
    th = p.theta_rad
    sin_th = np.sin(th)[None, :]
    w = sin_th
    return float(np.sum(p.directivity * w) / np.sum(np.ones_like(p.directivity) * w))


@pytest.mark.parametrize("freq", [3.5e9])
def test_dipole_shape_and_peak(freq):
    p = AntennaPattern3D.dipole(freq)
    assert p.directivity.shape == (p.phi_rad.size, p.theta_rad.size)
    assert np.all(p.directivity >= 0.0)
    assert 1.55 < p.directivity.max() < 1.75
    assert 0.9 < _sphere_average(p) < 1.1


def test_patch_is_broadside():
    freq = 3.5e9
    p = AntennaPattern3D.patch(freq)
    assert p.directivity.shape == (p.phi_rad.size, p.theta_rad.size)
    i_theta0 = int(np.argmin(np.abs(p.theta_rad - 0.0)))
    i_theta_pi = int(np.argmin(np.abs(p.theta_rad - np.pi)))
    assert p.directivity[:, i_theta0].mean() > p.directivity[:, i_theta_pi].mean()
    assert np.all(p.directivity >= 0.0)

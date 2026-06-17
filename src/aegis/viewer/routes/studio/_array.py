"""Base-station array geometry for the studio Tx radiation pattern.

Fork-free reconstruction of ``e8_rt_runner.bs_element_positions`` (the panel the
studio ray packs were traced against). The runtime studio never imports the
paper fork, but the precoder ``x`` it synthesises is indexed against this exact
element layout, so the Tx radiation pattern needs the same geometry to evaluate
``AF(d) = sum_j x_j exp(+i k0 r_j . d)``.

The reconstruction is byte-for-byte identical to the fork (verified against
``bs_element_positions`` for N = 8 and N = 16): element ``k = a*N + b`` sits at
``centre + (b - mid) d e_y + (a - mid) d e_zp`` where ``a`` is the panel-up row
(axis ``e_zp``) and ``b`` the column (axis ``e_y``).
"""

from __future__ import annotations

import numpy as np

# Fixed panel from e8_scene_setup (the studio scene the packs were traced in):
# centre at x = -13 m, suspended at z = 3 m, 10 deg downtilt, 28 GHz, single-pol
# half-wavelength URA facing +x.
_BS_CENTER = (-13.0, 0.0, 3.0)
_BS_TILT_DEG = 10.0
_BS_FREQ_HZ = 28e9
_SPACING_LAMBDA = 0.5
_C0 = 299792458.0


def array_axes() -> tuple[np.ndarray, np.ndarray]:
    """Panel horizontal (``e_y``) and panel-up (``e_zp``) world-frame unit axes."""
    theta = np.deg2rad(_BS_TILT_DEG)
    e_y = np.array([0.0, 1.0, 0.0])
    e_zp = np.array([np.sin(theta), 0.0, np.cos(theta)])
    return e_y, e_zp


def element_spacing_m() -> float:
    """Inter-element spacing [m] (half a wavelength at the panel frequency)."""
    return _SPACING_LAMBDA * _C0 / _BS_FREQ_HZ


def array_freq_hz() -> float:
    """Physical panel carrier [Hz], fixed regardless of the dosimetry frequency."""
    return _BS_FREQ_HZ


def bs_element_positions(array_n: int) -> np.ndarray:
    """``(array_n**2, 3)`` world-frame element positions, order ``k = a*N + b``."""
    n = int(array_n)
    e_y, e_zp = array_axes()
    d = element_spacing_m()
    centre = np.array(_BS_CENTER)
    mid = (n - 1) / 2
    a, b = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")  # a row, b col
    pos = (
        centre[None, None, :]
        + (b - mid)[..., None] * d * e_y[None, None, :]
        + (a - mid)[..., None] * d * e_zp[None, None, :]
    )
    return pos.reshape(-1, 3)

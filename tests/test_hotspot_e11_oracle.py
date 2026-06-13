"""Ground-truth oracle for the hotspot field reconstruction (e11).

Replays a real ray-traced LOS path pack from the coherent-exposure-operator
study, builds a maximum-ratio-transmission (MRT) precoder, reconstructs the
free-space focal spot and an apples-to-apples unfocused (random-phase,
matched-power) baseline, and checks the focused/unfocused peak ratio against
the documented range. The study reports a LOS free-space focusing peak ratio
of about 52x (results/e11_hotspot_report.md, sec. 2). This test uses a broad
[20, 200] band so it stays robust to slice orientation and resolution while
still catching a gross regression in the synthesis or MRT path.

Marked slow: it loads a multi-megabyte path pack and reconstructs dense
slices. Skipped if the data pack is absent.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aegis.hotspot import (
    SlicePlane,
    channel_at,
    field_on,
    power_density,
)

FREQ = 28e9

_PACK = (
    Path(__file__).resolve().parents[1]
    / "papers"
    / "coherent-exposure-operator"
    / "data"
    / "e11_paths"
    / "bs16_los_seed0.npz"
)

# Focus targets from the e11 study geometry.
CHEST_FOCUS = np.array([0.923, -0.005, 0.734])
AIR_FOCUS = np.array([0.502, 0.0, 1.794])


def _load_pack():
    d = np.load(_PACK)
    k = np.asarray(d["k_hat"], dtype=np.float64)
    psi = np.asarray(d["psi"], dtype=np.complex128)
    elem = np.asarray(d["element_index"], dtype=int)
    n_elements = int(d["n_elements"])
    return k, psi, elem, n_elements


def _mrt(target, k, psi, elem, n_elements, power=1.0):
    """Matched-ratio-transmission precoder: x = sqrt(P) conj(h)/||h||."""
    h = channel_at(target, k, psi, elem, FREQ, n_elements)
    return np.sqrt(power) * np.conj(h) / np.linalg.norm(h)


def _unfocused(n_elements, power=1.0, seed=0):
    """Equal-power-per-element random-phase beam, same ||x||^2 = P."""
    rng = np.random.default_rng(seed)
    return np.sqrt(power / n_elements) * np.exp(1j * rng.uniform(0, 2 * np.pi, n_elements))


@pytest.mark.slow
def test_e11_los_free_space_focusing_ratio():
    if not _PACK.exists():
        pytest.skip(f"e11 path pack not found at {_PACK}")

    k, psi, elem, n_elements = _load_pack()

    # MRT to the chest focus, matched transmit power ||x||^2 = 1.
    x_foc = _mrt(CHEST_FOCUS, k, psi, elem, n_elements, power=1.0)
    assert abs(np.vdot(x_foc, x_foc) - 1.0) < 1e-9

    x_unf = _unfocused(n_elements, power=1.0, seed=0)
    assert abs(np.vdot(x_unf, x_unf) - 1.0) < 1e-9  # matched power

    # Transverse free-space slice at the air focus, plane normal along the
    # mean propagation direction so the focal spot lies in the plane.
    axis = k.mean(axis=0)
    axis /= np.linalg.norm(axis)
    plane = SlicePlane.oriented(AIR_FOCUS, axis, 0.04, 200)

    s_foc = power_density(field_on(plane, k, psi, elem, x_foc, FREQ))
    s_unf = power_density(field_on(plane, k, psi, elem, x_unf, FREQ))

    ratio = float(s_foc.max() / s_unf.max())
    assert 20.0 < ratio < 200.0, f"focused/unfocused peak ratio {ratio:.1f} outside documented band"

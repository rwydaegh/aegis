"""Tests for the distal (self-shadowing) Fock gate in aegis.kernels.fock.

The distal gate encodes the corrected C-metric math (DECISIONS L13 /
theory/unified/sec_08_distal_cmetric.tex): clearance c > 0 maps to the lit
branch (no minus sign), the near-field factor w_nf divides the detour
(narrows the penumbra), and the gate carries BOTH the Fock curvature width
sigma_F ~ (k R_occ)^{-1/3} and the knife-edge Fresnel width sigma_ke ~
(k L)^{-1/2}, the broader mechanism winning.
"""

from __future__ import annotations

import numpy as np

from aegis.kernels.fock import distal_gate, fock_xi_distal


def test_xi_distal_sign_clear_is_lit():
    # c > 0 (clear) must map to xi_d > 0 (lit branch), NO minus sign.
    xi = fock_xi_distal(clearance=0.2, R_occ=0.02, freq_hz=28e9, w_nf=1.0)
    assert xi > 0
    xi_sh = fock_xi_distal(clearance=-0.2, R_occ=0.02, freq_hz=28e9, w_nf=1.0)
    assert xi_sh < 0


def test_xi_distal_wnf_divides_narrows_penumbra():
    # near-field w_nf < 1 RAISES |xi| (sharper penumbra) vs far field.
    far = fock_xi_distal(0.1, 0.02, 28e9, w_nf=1.0)
    near = fock_xi_distal(0.1, 0.02, 28e9, w_nf=0.5)
    assert near > far


def test_distal_gate_clear_is_unity():
    # Deep clear (clearance well beyond the Fock penumbra sigma_F ~ (kR)^{-1/3})
    # saturates the gate to 1. At 28 GHz a 0.1 m occluder has m_occ ~ 3, so a
    # 1 rad clearance is > 3 sigma into the lit region.
    g = distal_gate(
        np.array([1.0]), np.array([0.1]), 28e9, 0.5, 0.5,
        d1=np.array([np.inf]), d2=np.array([0.05]), diffraction_model="fock",
    )
    assert np.all(g > 0.99)


def test_distal_gate_higher_freq_sharpens():
    # The lambda -> 0 binary limit is approached as frequency rises: the Fock
    # penumbra width sigma_F ~ (kR)^{-1/3} shrinks, so at a fixed clearance the
    # lit side rises toward 1 and the shadow side falls toward 0. (Full binary
    # collapse at mmWave needs a large occluder; the trend is the testable claim.)
    c = np.array([0.15, -0.15])
    R_occ = np.array([0.1, 0.1])
    d2 = np.array([0.05, 0.05])
    d1 = np.array([np.inf, np.inf])
    lo = distal_gate(c, R_occ, 28e9, 0.5, 0.5, d1=d1, d2=d2, diffraction_model="fock")
    hi = distal_gate(c, R_occ, 300e9, 0.5, 0.5, d1=d1, d2=d2, diffraction_model="fock")
    assert hi[0] > lo[0]  # lit side sharper toward 1
    assert hi[1] < lo[1]  # shadow side sharper toward 0


def test_distal_gate_knife_limit_recovers_erf():
    # R_occ -> inf (flat edge): gate == 0.5(1+erf(c/sigma_ke)), no creeping tail.
    c = np.array([0.0])
    R_occ = np.array([1e6])
    d2 = np.array([0.05])
    d1 = np.array([np.inf])
    g = distal_gate(c, R_occ, 28e9, 0.5, 0.5, d1=d1, d2=d2, diffraction_model="fock")
    assert np.allclose(g, 0.5, atol=0.05)  # erf at c=0 is the half value


def test_distal_gate_non_fock_is_pure_knife():
    c = np.array([0.0])
    g = distal_gate(
        c, np.array([0.02]), 28e9, 0.5, 0.5,
        d1=np.array([np.inf]), d2=np.array([0.05]), diffraction_model="none",
    )
    assert np.allclose(g, 0.5, atol=1e-6)  # exactly the erf half value


def test_distal_gate_monotonic_in_clearance():
    # The gate rises monotonically from shadow (~0) to lit (~1) with clearance,
    # over a range that spans the Fock penumbra (R_occ = 0.05 -> sigma_F ~ 0.5 rad).
    c = np.linspace(-1.0, 1.0, 25)
    R_occ = np.full_like(c, 0.05)
    d2 = np.full_like(c, 0.05)
    d1 = np.full_like(c, np.inf)
    g = distal_gate(c, R_occ, 28e9, 0.5, 0.5, d1=d1, d2=d2, diffraction_model="fock")
    assert g[0] < 0.15
    assert g[-1] > 0.85
    # non-decreasing up to small creeping-tail ripple
    assert np.all(np.diff(g) > -1e-3)

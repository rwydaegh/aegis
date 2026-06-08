"""Tests for the Fock diffraction transition gate (kernels/fock.py).

The oracles are the truth: when the gate disagrees with the exact cylinder
surface field, the gate is wrong. The PEC cylinder oracle
(studies/diffraction/cylinder_oracle.py) is validated (Fock shadow decay,
soft/hard ratio 2.295). These tests pin the gate to it.

Physics targets (see studies/diffraction/{DECISIONS,FINDINGS}.md):
- penumbra width scales (kR)^{-1/3}, carried by xi = m*theta, m = (kR/2)^{1/3}
- shadow creeping decay |psi|^2 ~ exp(-sqrt3 q1 |xi|), q1 = |first Airy(') zero|
- PEC soft/hard decay-slope ratio q1_soft/q1_hard = 2.338/1.019 = 2.295
- GO recovery deep lit, ReLU recovery as kR -> inf
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from aegis.kernels import fock

# The committed oracle lives under studies/; pytest pythonpath includes the
# repo root, so studies is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studies" / "diffraction"))
from cylinder_oracle import pec_cylinder_surface_field  # noqa: E402

SQRT3 = np.sqrt(3.0)
Q1_SOFT = 2.338107410459767  # |first zero of Ai|
Q1_HARD = 1.018792971647471  # |first zero of Ai'|


def _oracle_hard_field_gate(kR: float):
    """PEC TE (hard) dimensionless field gate g^2(theta), GO-anchored.

    The hard observable is the surface field |H_z|^2, whose lit GO is angle
    independent (|2 H_inc|^2), so the field gate is P / median(P_lit): it -> 1
    deep lit and -> the universal Fock terminator value at theta = 0.
    """
    theta = np.deg2rad(np.linspace(-30.0, 50.0, 8001))
    P = pec_cylinder_surface_field(kR, np.pi / 2 + theta, "TE")
    lit = (theta > np.deg2rad(25.0)) & (theta < np.deg2rad(40.0))
    return theta, P / np.median(P[lit])


def _oracle_soft_current_gate(kR: float):
    """PEC TM (soft) dimensionless current gate g^2(theta), GO-anchored.

    The soft observable is the surface current |dE_z/dn|^2, whose lit GO scales
    as sin^2(theta) (the cos^2 of the local incidence). Dividing by sin^2 gives
    a gate -> 1 deep lit; it diverges at the terminator (1/sin^2), so the soft
    comparison is made in the shadow where the current gate is well posed.
    """
    theta = np.deg2rad(np.linspace(-30.0, 50.0, 8001))
    P = pec_cylinder_surface_field(kR, np.pi / 2 + theta, "TM")
    s = np.sin(np.maximum(theta, 1e-9))
    lit = (theta > np.deg2rad(25.0)) & (theta < np.deg2rad(40.0))
    C = np.median(P[lit] / s[lit] ** 2)
    return theta, P / (C * s**2)


def test_pec_eigenvalues_match_airy_zeros():
    soft = fock.fock_eigenvalues("soft", n_terms=3)
    hard = fock.fock_eigenvalues("hard", n_terms=3)
    np.testing.assert_allclose(np.real(soft), [2.338, 4.088, 5.521], atol=2e-3)
    np.testing.assert_allclose(np.real(hard), [1.019, 3.248, 4.820], atol=2e-3)


def test_theta_from_mu_signed():
    assert fock.theta_from_mu(0.0) == pytest.approx(0.0)
    assert fock.theta_from_mu(1.0) == pytest.approx(np.pi / 2)
    assert fock.theta_from_mu(-0.5) == pytest.approx(-np.pi / 6)


def test_phi_lit_limits():
    assert fock.phi_lit(8.0) == pytest.approx(1.0, abs=1e-6)
    assert fock.phi_lit(-8.0) == pytest.approx(0.0, abs=1e-6)
    assert abs(fock.phi_lit(0.0)) == pytest.approx(0.5, abs=1e-9)


def test_shadow_series_decays_with_validated_slope():
    xi = np.linspace(-6.0, -2.0, 40)
    for pol, q1 in (("soft", Q1_SOFT), ("hard", Q1_HARD)):
        psi = fock.psi_shadow(xi, pol)
        slope = np.polyfit(xi, np.log(np.abs(psi) ** 2), 1)[0]
        assert slope == pytest.approx(SQRT3 * q1, rel=0.05)


def test_soft_hard_pec_ratio_2295():
    xi = np.linspace(-6.0, -2.0, 40)
    s_soft = np.polyfit(xi, np.log(np.abs(fock.psi_shadow(xi, "soft")) ** 2), 1)[0]
    s_hard = np.polyfit(xi, np.log(np.abs(fock.psi_shadow(xi, "hard")) ** 2), 1)[0]
    assert s_soft / s_hard == pytest.approx(2.295, rel=0.03)


def test_fock_local_recovers_relu_asymptotically():
    mu = np.linspace(-0.3, 0.8, 200)
    relu = np.maximum(mu, 0.0)
    errs = []
    for R in (0.05, 0.5, 5.0):
        g = fock.fock_local(mu, R, 28e9, 0.5, 0.5)
        errs.append(float(np.max(np.abs(g - relu))))
    # penumbra width ~ (kR)^{-1/3} shrinks with R: error is monotone decreasing
    assert errs[0] > errs[1] > errs[2]
    assert errs[-1] < 0.05


def test_fock_local_nonnegative_and_shadow_leakage():
    mu = np.linspace(-0.3, 0.8, 200)
    # large kR (R = 5 m at 28 GHz, kR ~ 2900): deep-shadow leakage is negligible
    g = fock.fock_local(mu, 5.0, 28e9, 0.5, 0.5)
    assert np.all(g >= 0.0)
    assert np.max(g[mu < -0.2]) < 1e-3
    # the creeping wave leaks past the terminator: nonzero at the grazing point
    assert g[np.argmin(np.abs(mu))] > 0.0


def _hard_slope(eta, kR):
    """Shadow power-decay slope 2 Im(nu) for the impedance hard pole."""
    m = (kR / 2.0) ** (1.0 / 3.0)
    q_F = fock.fock_impedance_param(eta, kR, "hard")
    q_p = fock.fock_eigenvalues("hard", q_F)[0]
    nu = kR + m * np.exp(1j * np.pi / 3.0) * q_p
    return 2.0 * nu.imag


def test_impedance_hard_pole_matches_exact_dielectric():
    """The impedance (Leontovich) hard pole reproduces the exact dielectric
    p-pol shadow decay (HARD_POL_RESOLUTION.md table a) to within 5%."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    eta = 1.0 / SKIN_28GHZ.n_complex
    assert eta.imag > 0  # physical inductive skin (AEGIS stores n - ik)
    targets = {40.0: 5.654, 80.0: 7.503, 160.0: 10.099}
    for kR, tgt in targets.items():
        assert _hard_slope(eta, kR) == pytest.approx(tgt, rel=0.05)


def test_q_hard_table_drifts_upward():
    """q_eff(hard) drifts upward with kR (1.0 -> 2.4), the lossy-skin signature."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    table = fock.fock_q_hard_table(SKIN_28GHZ)
    q40 = float(table(40.0))
    q320 = float(table(320.0))
    assert 1.0 < q40 < 2.4
    assert 1.0 < q320 < 2.4
    assert q40 < q320


def test_q_F_sign_guard():
    """A gain medium (Im(eta) < 0) is rejected; the physical branch decays."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    eta = 1.0 / SKIN_28GHZ.n_complex
    # Feeding the conjugate (Im(eta) < 0) models gain and must not silently
    # produce an anti-physical (growing) pole.
    with pytest.raises(ValueError, match="gain medium"):
        fock.fock_impedance_param(np.conj(eta), 80.0, "hard")
    # The physical branch (Im(eta) > 0) gives a decaying pole, Im(nu) > 0.
    assert _hard_slope(eta, 80.0) > 0.0


def test_soft_hard_impedance_ratio_skin():
    """Skin soft/hard decay-slope ratio is in (1.5, 2.0) and decreases with kR
    (HARD_POL_RESOLUTION.md table c: ~1.95 -> ~1.59), below the PEC 2.295."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    eta = 1.0 / SKIN_28GHZ.n_complex

    def slope(kR, pol):
        m = (kR / 2.0) ** (1.0 / 3.0)
        q_F = fock.fock_impedance_param(eta, kR, pol)
        q_p = fock.fock_eigenvalues(pol, q_F)[0]
        return 2.0 * (kR + m * np.exp(1j * np.pi / 3.0) * q_p).imag

    ratios = [slope(kR, "soft") / slope(kR, "hard") for kR in (20.0, 40.0, 80.0, 160.0, 320.0)]
    for r in ratios:
        assert 1.5 < r < 2.0
    assert ratios[0] > ratios[-1]  # decreasing with kR
    assert ratios[0] == pytest.approx(1.95, abs=0.1)
    assert ratios[-1] == pytest.approx(1.59, abs=0.1)


def test_impedance_reduces_to_pec_as_n_large():
    """As |n| -> inf (eta -> 0) the hard eigenvalue -> the PEC hard value 1.019
    (the Leontovich -> PEC limit)."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    eta = (1.0 / SKIN_28GHZ.n_complex) * 1e-3  # shrink the skin impedance
    kR = 160.0
    q_F = fock.fock_impedance_param(eta, kR, "hard")
    q_p = fock.fock_eigenvalues("hard", q_F)[0]
    q_eff = q_p.real + q_p.imag / SQRT3
    assert q_eff == pytest.approx(1.019, abs=0.03)


def test_impedance_psi_shadow_finite_and_decays():
    """End-to-end: the impedance path gives finite, shadow-decaying gates."""
    from aegis.tissue.dielectric import SKIN_28GHZ

    eta = 1.0 / SKIN_28GHZ.n_complex
    q_F_h = fock.fock_impedance_param(eta, 80.0, "hard")
    q_F_s = fock.fock_impedance_param(eta, 80.0, "soft")
    xi = np.linspace(-6.0, -2.0, 40)
    psi = fock.psi_shadow(xi, "hard", q_F_h)
    assert np.all(np.isfinite(psi))
    slope = np.polyfit(xi, np.log(np.abs(psi) ** 2), 1)[0]
    assert slope > 0  # decays into the shadow (xi < 0)
    mu = np.linspace(-0.3, 0.8, 200)
    g = fock.fock_local(mu, 0.05, 28e9, 0.5, 0.5, q_F_s=q_F_s, q_F_h=q_F_h)
    assert np.all(np.isfinite(g))
    assert np.all(g >= 0.0)


def test_gate_matches_pec_cylinder_oracle():
    """Pin the residue-amplitude scale to the exact PEC cylinder oracle.

    HARD (TE): the surface-field gate has a clean, kR-independent terminator
    value (~0.488). We assert the module reproduces it and tracks the oracle
    across the penumbra. Tolerance: absolute 0.12 on the GO-anchored |g|^2 over
    [-6 deg, +12 deg]. The closed-form composite matches the lit penumbra and
    terminator to within ~6%; it under-predicts the dose-negligible deep shadow
    (~1e-6 of lit per FINDINGS F5), which is the documented limitation of a
    3-pole additive composite.

    SOFT (TM): the PEC observable is the surface current (lit GO ~ sin^2), so it
    cannot anchor a field-gate terminator (1/sin^2 divergence). Soft shares the
    Fock normalization prefactor with hard; it is validated here by its shadow
    decay matching the oracle current gate.
    """
    kR_list = (40.0, 80.0, 160.0)

    # --- HARD terminator pin: module reproduces the oracle terminator value ---
    term_oracle = []
    for kR in (160.0, 320.0, 640.0):
        theta, g2 = _oracle_hard_field_gate(kR)
        term_oracle.append(g2[np.argmin(np.abs(theta))])
    term_oracle = float(np.mean(term_oracle))
    term_model = float(np.abs(fock.fock_g(0.0, "hard")) ** 2)
    assert term_model == pytest.approx(term_oracle, abs=0.03)

    # --- HARD penumbra shape vs oracle, GO-anchored, across kR ---
    for kR in kR_list:
        theta, g2 = _oracle_hard_field_gate(kR)
        m = (kR / 2.0) ** (1.0 / 3.0)
        win = (theta > np.deg2rad(-6.0)) & (theta < np.deg2rad(12.0))
        model = np.abs(fock.fock_g(m * theta[win], "hard")) ** 2
        assert np.max(np.abs(model - g2[win])) < 0.12

    # --- SOFT shadow decay vs oracle current gate (both -> sqrt3 q1_soft) ---
    for kR in kR_list:
        theta, g2 = _oracle_soft_current_gate(kR)
        m = (kR / 2.0) ** (1.0 / 3.0)
        win = (theta > np.deg2rad(-18.0)) & (theta < np.deg2rad(-6.0))
        th_sh = theta[win]
        slope_oracle = np.polyfit(th_sh, np.log(g2[win]), 1)[0]
        model = np.abs(fock.fock_g(m * th_sh, "soft")) ** 2
        slope_model = np.polyfit(th_sh, np.log(model), 1)[0]
        assert slope_model == pytest.approx(slope_oracle, rel=0.15)

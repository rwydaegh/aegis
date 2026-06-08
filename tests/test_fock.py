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

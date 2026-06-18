"""Absolute-limit two-restriction ECBF for the Coherent Exposure Studio.

Covers the solver core in
``aegis.viewer.routes.studio._absolute_ecbf.build_ecbf_absolute``:

- generalisation: the multibody solver with one global operator and K=1 matches
  the single-body ``solve_ecbf`` to machine precision;
- enforcement: the SAR_wb and peak 4 cm^2 restrictions are respected;
- regime classification (free / sar_wb / peak_sab) on constructed geometry;
- flattening above the knee (the absolute solve is not power-homogeneous);
- constraint generation converges within ``max_gen`` or logs the cap.

The scenes are synthetic (no precomputed packs), so these run in CI.
"""

from __future__ import annotations

import logging

import numpy as np
import pytest
import scipy.sparse as sp

from aegis.coherent import solve_ecbf, solve_multibody_ecbf
from aegis.viewer.routes.studio._absolute_ecbf import build_ecbf_absolute, global_operator

FREQ_HZ = 10.0e9  # > 6 GHz so the 4 cm^2 S_ab limit applies (general public: 20 W/m^2)
L_WB = 0.08  # general-public whole-body SAR limit [W/kg]
L_LOC = 20.0  # general-public 4 cm^2 S_ab limit [W/m^2]


def _identity_avg(t: int):
    """Identity averaging matrix: each triangle is its own 4 cm^2 'region'."""
    return sp.csr_array(sp.eye(t, format="csr"))


def _rank1_scene(m=8, t=10, hot_gain=1.0, seed=0):
    """Aligned rank-1 scene: every triangle couples through one steering vector.

    All per-triangle channels point along a single unit vector ``a0`` and the
    matched filter targets it, so signal and every exposure share one scalar
    ``|a0^H x|^2``. That makes the regime analytic: ECBF just scales the MRT beam
    until the tighter restriction sits on its limit. Triangle 0 carries ``hot_gain``
    so the local peak can be made to bind before whole-body SAR.
    """
    rng = np.random.default_rng(seed)
    a0 = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    a0 = a0 / np.linalg.norm(a0)
    gains = np.ones(t)
    gains[0] = hot_gain
    g = np.zeros((t, 3, m), dtype=np.complex64)
    g[:, 0, :] = gains[:, None] * a0[None, :]
    areas = np.full(t, 0.01)  # 1 cm^2 per triangle
    h = np.conj(a0)  # MRT points at a0
    return g, areas, _identity_avg(t), h, gains


def _random_scene(m=8, t=16, seed=1):
    """Full-rank scene: distinct per-triangle steering vectors.

    Enforcing one local operator reshapes x and can raise exposure at triangles
    outside that window, so the local peak genuinely needs constraint generation.
    """
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((t, m)) + 1j * rng.standard_normal((t, m))
    g = np.zeros((t, 3, m), dtype=np.complex64)
    g[:, 0, :] = a
    areas = np.full(t, 0.01)
    h = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    return g, areas, _identity_avg(t), h


def test_multibody_single_global_matches_solve_ecbf():
    """K=1, one global operator, noise_power=None collapses to single-body ECBF."""
    rng = np.random.default_rng(7)
    m = 6
    h = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    b = rng.standard_normal((m, m)) + 1j * rng.standard_normal((m, m))
    q = b.conj().T @ b  # Hermitian PSD
    power = 2.0
    # Budget below the MRT absorption so the exposure constraint actually binds.
    x_mrt = np.sqrt(power) * np.conj(h) / np.linalg.norm(h)
    p_abs_mrt = float(np.real(x_mrt.conj() @ q @ x_mrt))
    budget = 0.4 * p_abs_mrt

    x_single = np.asarray(solve_ecbf(h, q, budget, power))
    w_multi = np.asarray(solve_multibody_ecbf(h[None, :], [q], [budget], power, noise_power=None))
    x_multi = w_multi.reshape(m, -1)[:, 0]

    # Compare phase-invariant quantities: served signal and absorbed power.
    s_single = abs(h @ x_single) ** 2
    s_multi = abs(h @ x_multi) ** 2
    a_single = float(np.real(x_single.conj() @ q @ x_single))
    a_multi = float(np.real(x_multi.conj() @ q @ x_multi))
    assert s_multi == pytest.approx(s_single, rel=1e-6, abs=1e-9)
    assert a_multi == pytest.approx(a_single, rel=1e-6, abs=1e-9)
    assert a_multi <= budget * (1 + 1e-6)


def test_sar_wb_restriction_enforced():
    """SAR on, peak off, high power: total absorbed power respects L_wb * mass."""
    g, areas, g_avg, h, _ = _rank1_scene(hot_gain=1.0)
    mass = 10.0
    res = build_ecbf_absolute(g, areas, g_avg, h, FREQ_HZ, mass, power_w=50.0, sar_wb_on=True, peak_on=False)
    budget_w = L_WB * mass
    assert res["p_abs_w"] <= budget_w * (1 + 1e-3)
    # Well above the knee the whole-body restriction binds.
    assert res["regime"] == "sar_wb"


def test_peak_sab_restriction_enforced():
    """Peak on, sar off: the worst 4 cm^2 average respects L_loc."""
    g, areas, g_avg, h = _random_scene(t=6, seed=2)
    res = build_ecbf_absolute(
        g,
        areas,
        g_avg,
        h,
        FREQ_HZ,
        mass=None,
        power_w=15.0,
        sar_wb_on=False,
        peak_on=True,
        max_gen=12,
        max_regions=12,
    )
    x = res["x"]
    sab = (np.abs(np.einsum("tim,m->ti", g.astype(complex), x)) ** 2).sum(axis=1)
    peak = float(np.asarray(g_avg @ sab).ravel().max())
    assert peak <= L_LOC * (1 + 1e-2)
    assert res["converged"]


def test_regime_free_at_low_power():
    """Tiny power: neither restriction binds, the matched filter is feasible."""
    g, areas, g_avg, h, _ = _rank1_scene(hot_gain=1.0)
    res = build_ecbf_absolute(g, areas, g_avg, h, FREQ_HZ, mass=10.0, power_w=0.05, sar_wb_on=True, peak_on=True)
    assert res["regime"] == "free"
    assert res["n_regions_active"] == 0


def test_regime_peak_binds_when_local_is_hot():
    """A hot triangle drives the local peak to its limit before whole-body SAR.

    In the aligned scene every exposure tracks the single scalar ``|a0^H x|^2``, so
    capping the hot triangle's 4 cm^2 average at ``L_loc`` also caps the total
    absorbed power well below ``L_wb * mass``: the local peak binds, SAR stays
    slack, for any power past the peak knee.
    """
    g, areas, g_avg, h, gains = _rank1_scene(hot_gain=3.0)
    mass = 10.0
    power = 10.0
    assert power > L_LOC / gains.max() ** 2  # past the local-peak knee
    res = build_ecbf_absolute(g, areas, g_avg, h, FREQ_HZ, mass, power_w=power, sar_wb_on=True, peak_on=True)
    assert res["regime"] == "peak_sab"
    # The whole-body restriction is not binding at this operating point.
    assert res["p_abs_w"] < L_WB * mass


def test_flattening_above_the_knee():
    """Past the binding knee, doubling transmit power leaves the bound dose flat."""
    g, areas, g_avg, h, _ = _rank1_scene(hot_gain=1.0)
    mass = 10.0
    kw = dict(sar_wb_on=True, peak_on=True)
    lo = build_ecbf_absolute(g, areas, g_avg, h, FREQ_HZ, mass, power_w=40.0, **kw)
    hi = build_ecbf_absolute(g, areas, g_avg, h, FREQ_HZ, mass, power_w=80.0, **kw)
    # Both are SAR-bound, and the binding absorbed power is flat (not homogeneous
    # in P): doubling power does not double the absorbed power.
    assert lo["regime"] == "sar_wb"
    assert hi["regime"] == "sar_wb"
    assert hi["p_abs_w"] == pytest.approx(lo["p_abs_w"], rel=2e-3)
    # Contrast: the unconstrained MRT absorption would have doubled.
    q_glob = global_operator(g, areas)
    x_mrt_lo = np.sqrt(40.0) * np.conj(h) / np.linalg.norm(h)
    x_mrt_hi = np.sqrt(80.0) * np.conj(h) / np.linalg.norm(h)
    p_mrt_lo = float(np.real(x_mrt_lo.conj() @ q_glob @ x_mrt_lo))
    p_mrt_hi = float(np.real(x_mrt_hi.conj() @ q_glob @ x_mrt_hi))
    assert p_mrt_hi == pytest.approx(2 * p_mrt_lo, rel=1e-6)


def test_constraint_generation_converges():
    """Full-rank scene: generation reaches a feasible peak within the caps.

    Each added local operator can raise exposure at triangles outside its window,
    so the worst row migrates and generation needs several rounds. With the caps
    above the triangle count it converges to a feasible peak (every 4 cm^2 average
    at or below the limit).
    """
    g, areas, g_avg, h = _random_scene(t=8, seed=3)
    res = build_ecbf_absolute(
        g,
        areas,
        g_avg,
        h,
        FREQ_HZ,
        mass=None,
        power_w=20.0,
        sar_wb_on=False,
        peak_on=True,
        max_gen=12,
        max_regions=12,
    )
    assert res["converged"]
    assert not res["cap_hit"]
    assert res["n_gen_iters"] >= 1
    x = res["x"]
    sab = (np.abs(np.einsum("tim,m->ti", g.astype(complex), x)) ** 2).sum(axis=1)
    assert float(np.asarray(g_avg @ sab).ravel().max()) <= L_LOC * (1 + 1e-2)


def test_constraint_generation_cap_is_logged(caplog):
    """Hitting the region cap logs a warning instead of silently truncating."""
    g, areas, g_avg, h = _random_scene(seed=5)
    with caplog.at_level(logging.WARNING):
        res = build_ecbf_absolute(
            g,
            areas,
            g_avg,
            h,
            FREQ_HZ,
            mass=None,
            power_w=60.0,
            sar_wb_on=False,
            peak_on=True,
            max_gen=1,
            max_regions=1,
        )
    assert res["cap_hit"]
    assert not res["converged"]
    assert any("constraint generation hit the cap" in r.message for r in caplog.records)


def test_peak_toggle_ignored_below_6ghz():
    """At/below 6 GHz the 4 cm^2 limit does not exist; fall back to SAR_wb-only."""
    g, areas, g_avg, h, _ = _rank1_scene(hot_gain=3.0)
    res = build_ecbf_absolute(
        g,
        areas,
        g_avg,
        h,
        freq_hz=3.5e9,
        mass=10.0,
        power_w=50.0,
        sar_wb_on=True,
        peak_on=True,
    )
    names = [c["name"] for c in res["per_constraint"]]
    assert "peak_sab" not in names
    assert "sar_wb" in names
    assert res["regime"] in ("sar_wb", "free")


def test_per_constraint_readout_shape():
    """per_constraint carries name/value/limit/utilisation/active for each toggle."""
    g, areas, g_avg, h, _ = _rank1_scene(hot_gain=2.0)
    res = build_ecbf_absolute(
        g,
        areas,
        g_avg,
        h,
        FREQ_HZ,
        mass=10.0,
        power_w=15.0,
        sar_wb_on=True,
        peak_on=True,
    )
    by_name = {c["name"]: c for c in res["per_constraint"]}
    assert set(by_name) == {"sar_wb", "peak_sab"}
    for c in res["per_constraint"]:
        assert c["limit"] > 0
        assert c["utilisation"] == pytest.approx(c["value"] / c["limit"], rel=1e-9)
        assert isinstance(c["active"], bool)

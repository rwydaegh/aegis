"""Polarisation is carried from psi into incoherent dosimetry.

These tests pin the requirement that the level-4 / spatial polarisation
correction reflects the *actual* incident polarisation state, not a free
scalar knob. The historical defect: ray tracers fill ``psi`` with the true
polarisation, but the incoherent kernels read ``paths.power`` (a scalar) and
``q`` defaulted to a constant, so TE and TM incidence produced identical
absorbed power. See studies/self_shadowing/report/exactness_polarization.

The oracle is the Fresnel power transmission: at oblique incidence a wave
polarised along the local TE direction must absorb ``T_s``; a wave polarised
along the local TM direction must absorb ``T_p``; and ``T_p != T_s`` away from
normal incidence.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from conftest import make_single_triangle

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"


def _fresnel_TsTp(mu: float, n_tilde: complex) -> tuple[float, float]:
    """Analytic Fresnel power transmission, independent of AEGIS internals."""
    n2 = n_tilde**2
    xi = np.sqrt(n2 - (1.0 - mu**2))
    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)
    return float(1 - abs(r_s) ** 2), float(1 - abs(r_p) ** 2)


def _oblique_setup(theta_deg: float):
    """Single +z triangle, plane wave at theta in the x-z incidence plane.

    Returns (mesh, k_hat, mu, e_s_dir, e_p_dir).
    """
    mesh = make_single_triangle()  # normal = +z
    th = np.deg2rad(theta_deg)
    k_hat = np.array([np.sin(th), 0.0, -np.cos(th)])  # travels down-and-forward
    mu = np.cos(th)
    n = np.array([0.0, 0.0, 1.0])
    e_s = np.cross(k_hat, n)
    e_s = e_s / np.linalg.norm(e_s)  # local TE direction (= +/- y)
    e_p = np.cross(e_s, k_hat)
    e_p = e_p / np.linalg.norm(e_p)  # local TM direction (in x-z plane)
    return mesh, k_hat, mu, e_s, e_p


def _teff(engine, mesh, paths, mu):
    res = engine.compute(mesh, paths, mode="spatial", fresnel=True, polarisation=True)
    sab = np.asarray(res.sab)
    power = float(paths.power[0])
    return float(sab[0] / (power * mu))


@pytest.mark.parametrize("theta_deg", [30.0, 45.0, 60.0, 75.0])
def test_te_and_tm_match_fresnel(theta_deg: float) -> None:
    """TE-polarised wave absorbs T_s, TM-polarised absorbs T_p, and they differ."""
    mesh, k_hat, mu, e_s, e_p = _oblique_setup(theta_deg)
    engine = DosimetryEngine(SKIN_28GHZ)
    T_s, T_p = _fresnel_TsTp(mu, engine.n_tilde)

    paths_te = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=e_s)
    paths_tm = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=e_p)

    teff_te = _teff(engine, mesh, paths_te, mu)
    teff_tm = _teff(engine, mesh, paths_tm, mu)

    assert teff_te == pytest.approx(T_s, rel=1e-6)
    assert teff_tm == pytest.approx(T_p, rel=1e-6)
    # the whole point: polarisation actually changes the answer
    assert abs(teff_tm - teff_te) > 0.05


def test_polarisation_state_actually_flows() -> None:
    """Regression for the wiring bug: TE vs TM must NOT be identical."""
    mesh, k_hat, mu, e_s, e_p = _oblique_setup(70.0)
    engine = DosimetryEngine(SKIN_28GHZ)
    paths_te = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=e_s)
    paths_tm = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=e_p)
    assert _teff(engine, mesh, paths_te, mu) != pytest.approx(_teff(engine, mesh, paths_tm, mu), rel=1e-3)


def test_unpolarised_average_recovers_Tavg() -> None:
    """Averaging absorbed power over the polarisation angle gives T_avg (level 3)."""
    mesh, k_hat, mu, e_s, e_p = _oblique_setup(60.0)
    engine = DosimetryEngine(SKIN_28GHZ)
    T_s, T_p = _fresnel_TsTp(mu, engine.n_tilde)
    T_avg = 0.5 * (T_s + T_p)
    teffs = []
    for alpha in np.linspace(0, np.pi, 18, endpoint=False):
        pol = np.cos(alpha) * e_s + np.sin(alpha) * e_p
        paths = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=pol)
        teffs.append(_teff(engine, mesh, paths, mu))
    assert np.mean(teffs) == pytest.approx(T_avg, rel=1e-3)


def test_teff_bounded_by_Ts_Tp() -> None:
    """For any polarisation, T_eff lies between T_s and T_p."""
    mesh, k_hat, mu, e_s, e_p = _oblique_setup(65.0)
    engine = DosimetryEngine(SKIN_28GHZ)
    T_s, T_p = _fresnel_TsTp(mu, engine.n_tilde)
    lo, hi = min(T_s, T_p), max(T_s, T_p)
    rng = np.random.default_rng(0)
    for _ in range(20):
        alpha = rng.uniform(0, 2 * np.pi)
        chi = rng.uniform(-np.pi / 4, np.pi / 4)  # ellipticity
        pol = np.cos(chi) * (np.cos(alpha) * e_s + np.sin(alpha) * e_p) + 1j * np.sin(chi) * (
            -np.sin(alpha) * e_s + np.cos(alpha) * e_p
        )
        paths = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]), polarisation=pol)
        t = _teff(engine, mesh, paths, mu)
        assert lo - 1e-9 <= t <= hi + 1e-9


def test_normal_incidence_polarisation_universal() -> None:
    """At normal incidence T_eff = T0 for every polarisation (preserved)."""
    mesh = make_single_triangle()
    engine = DosimetryEngine(SKIN_28GHZ)
    k_hat = np.array([[0.0, 0.0, -1.0]])
    for pol in (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([1.0, 1.0, 0.0])):
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0]), polarisation=pol)
        res = engine.compute(mesh, paths, mode="spatial", fresnel=True, polarisation=True)
        assert float(np.asarray(res.sab)[0]) == pytest.approx(engine.T0, rel=1e-9)


def test_fabricated_polarisation_does_not_leak() -> None:
    """from_powers without an explicit polarisation is marked unpolarised, so the
    correction falls back to T_avg rather than using the invented psi direction."""
    mesh, k_hat, mu, e_s, e_p = _oblique_setup(60.0)
    engine = DosimetryEngine(SKIN_28GHZ)
    T_s, T_p = _fresnel_TsTp(mu, engine.n_tilde)
    T_avg = 0.5 * (T_s + T_p)
    paths = PropagationPaths.from_powers(k_hat=k_hat[None, :], power=np.array([1.0]))
    assert paths.polarised is False
    assert _teff(engine, mesh, paths, mu) == pytest.approx(T_avg, rel=1e-6)


def test_scalar_q_backward_compatible() -> None:
    """The legacy scalar-q path still works when no real polarisation is present."""
    from aegis.kernels.spatial import spatial_kernel

    mesh, k_hat, mu, e_s, e_p = _oblique_setup(60.0)
    engine = DosimetryEngine(SKIN_28GHZ)
    T_s, T_p = _fresnel_TsTp(mu, engine.n_tilde)
    sab = spatial_kernel(
        mesh.normals,
        k_hat[None, :],
        np.array([1.0]),
        engine.n_tilde,
        engine.T0,
        engine.freq_hz,
        fresnel=True,
        polarisation=True,
        q=1.0,
    )
    teff = float(np.asarray(sab)[0] / mu)
    assert teff == pytest.approx(T_p, rel=1e-6)  # q=+1 -> pure TM


# --------------------------------------------------------------------------
# Stochastic channels feed the same polarisation path (optionally)
# --------------------------------------------------------------------------
def test_stochastic_channel_polarisation_flag() -> None:
    """generate_channel marks paths polarised only when xpr_db is given."""
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", _DATA_DIR)
    kw = dict(
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    plain = generate_channel(preset["params"], **kw)
    polarised = generate_channel(preset["params"], xpr_db=8.0, **kw)
    assert plain.polarised is False
    assert polarised.polarised is True
    # same geometry and total power, different (real) polarisation content
    assert polarised.n_paths == plain.n_paths
    assert polarised.total_power == pytest.approx(plain.total_power, rel=1e-9)


def test_stochastic_polarisation_changes_dosimetry() -> None:
    """A polarised stochastic channel yields a different map than the unpolarised one."""
    from conftest import make_icosahedron

    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", _DATA_DIR)
    kw = dict(
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=7,
    )
    mesh = make_icosahedron()
    engine = DosimetryEngine(SKIN_28GHZ)
    pol = generate_channel(preset["params"], xpr_db=8.0, **kw)
    unpol = generate_channel(preset["params"], **kw)  # polarised=False -> T_avg fallback
    sab_pol = np.asarray(engine.compute(mesh, pol, mode="spatial", fresnel=True, polarisation=True).sab)
    sab_unpol = np.asarray(engine.compute(mesh, unpol, mode="spatial", fresnel=True, polarisation=True).sab)
    assert not np.allclose(sab_pol, sab_unpol, rtol=1e-3)


# --------------------------------------------------------------------------
# The polarised flag propagates through the path algebra
# --------------------------------------------------------------------------
def test_polarised_flag_propagation() -> None:
    k = np.array([[0.0, 0.0, -1.0]])
    real = PropagationPaths.from_powers(k_hat=k, power=np.array([1.0]), polarisation=np.array([1.0, 0.0, 0.0]))
    fake = PropagationPaths.from_powers(k_hat=k, power=np.array([1.0]))
    assert real.polarised is True
    assert fake.polarised is False
    # subset preserves
    assert real.subset([0]).polarised is True
    # concatenate: all-real stays real, any-fake collapses to unpolarised
    assert PropagationPaths.concatenate([real, real]).polarised is True
    assert PropagationPaths.concatenate([real, fake]).polarised is False
    # dict round-trip preserves the flag
    assert PropagationPaths.from_dict(real.to_dict()).polarised is True
    assert PropagationPaths.from_dict(fake.to_dict()).polarised is False

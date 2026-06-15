"""Invariants for the hotspot field-reconstruction module.

Run: python -m pytest tests/test_hotspot.py -q
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.constants import C_0
from aegis.hotspot import (
    FieldVolume,
    SlicePlane,
    channel_at,
    collapse_paths,
    default_stack,
    field_channel_at,
    field_on,
    local_max_intensity,
    power_density,
    single_layer_reference,
    solve_layered,
    synthesize_field,
    transmitted_field,
)
from aegis.hotspot.averaging import (
    decohere_weights,
    exposure_average,
    incoherent_power,
    participation_ratio,
    patch_sweep,
    propagation_average,
)
from aegis.hotspot.metrics import fwhm_1d
from aegis.hotspot.worstcase import intensity_under, worst_case_map
from aegis.tissue.fresnel import (
    fresnel_transmission,
    n_complex,
)

FREQ = 28e9
K0 = 2 * np.pi * FREQ / C_0
LAM = C_0 / FREQ


def _synthetic_array(n_unique=40, n_elem=16, seed=0, cone_deg=18.0):
    """Synthetic-array paths arriving within a forward cone about -z.

    A bounded angular spread emulates a real aperture, so MRT phase
    conjugation produces a well-posed (sharp, unambiguous) focus.
    """
    rng = np.random.default_rng(seed)
    half = np.deg2rad(cone_deg)
    cos_min = np.cos(half)
    cosz = rng.uniform(cos_min, 1.0, size=n_unique)
    phi = rng.uniform(0, 2 * np.pi, size=n_unique)
    sinz = np.sqrt(1 - cosz**2)
    # directions clustered about +z, then flip to travel toward -z (downward)
    dirs = np.column_stack([sinz * np.cos(phi), sinz * np.sin(phi), -cosz])
    k_all = np.tile(dirs, (n_elem, 1))
    psi = rng.normal(size=(n_unique * n_elem, 3)) + 1j * rng.normal(size=(n_unique * n_elem, 3))
    elem = np.repeat(np.arange(n_elem), n_unique)
    return k_all, psi, elem, n_elem


# --- synthesis ---------------------------------------------------------------
def test_single_plane_wave_exact():
    k = np.array([[0.0, 0.0, 1.0]])
    psi = np.array([[1.0 + 0j, 0, 0]])
    ku, w = collapse_paths(k, psi, np.array([0]), np.array([1.0 + 0j]))
    pts = np.array([[0, 0, 0.0], [0, 0, LAM / 2], [0, 0, LAM]])
    E = synthesize_field(pts, ku, w, FREQ, dtype=np.complex128)
    expected = np.exp(-1j * K0 * pts[:, 2])
    assert np.max(np.abs(E[:, 0] - expected)) < 1e-9


def test_collapse_matches_bruteforce():
    k, psi, elem, M = _synthetic_array()
    rng = np.random.default_rng(1)
    x = rng.normal(size=M) + 1j * rng.normal(size=M)
    pts = rng.normal(size=(200, 3)) * 0.05
    ku, w = collapse_paths(k, psi, elem, x)
    assert ku.shape[0] == 40
    E_collapsed = synthesize_field(pts, ku, w, FREQ, dtype=np.complex128)
    phase = np.exp(-1j * K0 * (pts @ k.T))
    E_brute = (phase * x[elem][None, :]) @ psi
    assert np.max(np.abs(E_collapsed - E_brute)) < 1e-9


def test_mrt_focuses_at_target():
    # MRT phase-conjugates the co-polarised scalar channel, so the co-pol
    # channel response |h(r)^H x|^2 is maximised exactly at the target
    # (matched-filter property), and the focus stands above the background.
    k, psi, elem, M = _synthetic_array(seed=2)
    target = np.array([0.3, -0.2, 1.1])
    h = channel_at(target, k, psi, elem, FREQ, M)
    x = np.conj(h) / np.linalg.norm(h)  # ||x|| = 1
    assert abs(np.vdot(x, x) - 1.0) < 1e-12

    # The co-pol response at the target equals the matched-filter value
    # ||h||^2, and the target is a local maximum in the transverse plane
    # (the aperture focuses tightly across the beam; the longitudinal focus
    # is intentionally elongated for a narrow aperture, so test transverse).
    step = 0.5 * LAM
    nbrs = target + step * np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0.0]])
    pts = np.vstack([target[None, :], nbrs])
    copol = np.abs(channel_at(pts, k, psi, elem, FREQ, M) @ x) ** 2
    assert copol[0] == copol.max()  # transverse local maximum
    assert abs(copol[0] - np.linalg.norm(h) ** 2) < 1e-6  # matched-filter value

    vol = FieldVolume.centered(target, 0.06, 41)
    cp = np.abs(channel_at(vol.points, k, psi, elem, FREQ, M) @ x) ** 2
    assert cp.max() / cp.mean() > 3.0  # focus stands above the background


def test_power_scales_quadratically():
    k, psi, elem, M = _synthetic_array(seed=3)
    x = np.ones(M) / np.sqrt(M)
    plane = SlicePlane.oriented([0, 0, 1], [0, 0, 1], 0.05, 32)
    S1 = power_density(field_on(plane, k, psi, elem, x, FREQ, dtype=np.complex128))
    S2 = power_density(field_on(plane, k, psi, elem, 2 * x, FREQ, dtype=np.complex128))
    assert np.allclose(S2, 4 * S1, rtol=1e-5)


def test_fwhm_recovers_gaussian():
    x = np.linspace(-1, 1, 4001)
    sigma = 0.1
    y = np.exp(-(x**2) / (2 * sigma**2))
    fwhm, left, right = fwhm_1d(x, y)
    assert abs(fwhm - 2.3548 * sigma) < 1e-3


# --- averaging ---------------------------------------------------------------
def test_exposure_dominates_propagation():
    # <|E|^2> >= |<E>|^2 pointwise (Cauchy-Schwarz) on any patch.
    k, psi, elem, M = _synthetic_array(seed=7)
    x = np.conj(channel_at(np.array([0.1, 0.0, 1.0]), k, psi, elem, FREQ, M))
    plane = SlicePlane.oriented([0, 0, 1], [0, 0, 1], 0.08, 64)
    E = field_on(plane, k, psi, elem, x, FREQ, dtype=np.complex128)
    pix = float(plane.u[1] - plane.u[0])
    Se = exposure_average(E, pix, 0.02)
    Sp = propagation_average(E, pix, 0.02)
    assert np.all(Se >= Sp - 1e-9)


def test_single_plane_wave_no_cancellation():
    # |E| is spatially uniform, so the two averages coincide.
    k = np.array([[0.0, 0.0, 1.0]])
    psi = np.array([[1.0 + 0j, 0, 0]])
    ku, w = collapse_paths(k, psi, np.array([0]), np.array([1.0 + 0j]))
    plane = SlicePlane.oriented([0, 0, 1], [0, 0, 1], 0.05, 32)
    E = synthesize_field(plane.points, ku, w, FREQ, dtype=np.complex128).reshape(32, 32, 3)
    pix = float(plane.u[1] - plane.u[0])
    Se = exposure_average(E, pix, 0.02)
    Sp = propagation_average(E, pix, 0.02)
    assert np.max(np.abs(Se - Sp)) < 1e-9


def test_patch_average_dilutes_peak():
    # The exposure-wise peak cannot grow as the averaging patch grows.
    k, psi, elem, M = _synthetic_array(seed=8)
    x = np.conj(channel_at(np.array([0.0, 0.0, 1.0]), k, psi, elem, FREQ, M))
    plane = SlicePlane.oriented([0, 0, 1], [0, 0, 1], 0.06, 96)
    E = field_on(plane, k, psi, elem, x, FREQ, dtype=np.complex128)
    sweep = patch_sweep(plane, E, [0.001, 0.005, 0.01, 0.02])
    peaks = [s.peak_exposure for s in sweep]
    assert all(peaks[i] >= peaks[i + 1] - 1e-9 for i in range(len(peaks) - 1))


def test_spatial_mean_converges_to_incoherent_floor():
    # Over a window many wavelengths wide the cross terms wash out, so the
    # mean of |E|^2 approaches sum_u |w_u|^2 / 2Z0.
    k, psi, elem, M = _synthetic_array(n_unique=60, seed=9)
    x = np.exp(1j * np.linspace(0, 7, M)) / np.sqrt(M)
    ku, w = collapse_paths(k, psi, elem, x)
    plane = SlicePlane.oriented([0, 0, 1], [0, 0, 1], 1.0, 220)
    E = field_on(plane, k, psi, elem, x, FREQ, dtype=np.complex128)
    S_mean = power_density(E).mean()
    floor = incoherent_power(w)
    assert abs(S_mean - floor) / floor < 0.2


# --- matched illumination / worst case ---------------------------------------
def test_participation_ratio_bounds():
    # equal-power directions -> U; one dominant direction -> ~1.
    w_eq = np.ones((10, 3)) / np.sqrt(3)
    assert abs(participation_ratio(w_eq) - 10) < 1e-9
    w_dom = np.ones((10, 3)) * 1e-3
    w_dom[0] = [1.0, 0, 0]
    assert participation_ratio(w_dom) < 1.2


def test_decohere_preserves_illumination():
    # scrambling inter-direction phase leaves the angular power spectrum and
    # hence the incoherent floor exactly unchanged.
    k, psi, elem, M = _synthetic_array(seed=11)
    x = np.conj(channel_at(np.array([0.1, 0.0, 1.0]), k, psi, elem, FREQ, M))
    _, w = collapse_paths(k, psi, elem, x)
    rng = np.random.default_rng(3)
    wd = decohere_weights(w, rng)
    assert abs(incoherent_power(wd) - incoherent_power(w)) < 1e-12
    assert np.allclose(np.linalg.norm(wd, axis=1), np.linalg.norm(w, axis=1))


def test_worst_case_dominates_any_precoder():
    # lambda_max(G^H G) >= ||G x||^2 for every unit-power precoder, and the
    # returned x_opt achieves it.
    k, psi, elem, M = _synthetic_array(seed=12)
    G = field_channel_at(np.array([0.2, -0.1, 1.0]), k, psi, elem, FREQ, M)
    lam, x_opt = local_max_intensity(G, power=1.0)
    assert abs(np.vdot(x_opt, x_opt) - 1.0) < 1e-9
    assert abs(intensity_under(G, x_opt) - lam) < 1e-6
    rng = np.random.default_rng(4)
    for _ in range(20):
        xr = rng.normal(size=M) + 1j * rng.normal(size=M)
        xr /= np.linalg.norm(xr)
        assert intensity_under(G, xr) <= lam + 1e-9


def test_worst_case_map_matches_loop():
    k, psi, elem, M = _synthetic_array(seed=13)
    G_stack = np.stack(
        [field_channel_at(p, k, psi, elem, FREQ, M) for p in np.random.default_rng(5).normal(size=(8, 3)) * 0.05]
    )
    wc = worst_case_map(G_stack)
    ref = np.array([local_max_intensity(G)[0] for G in G_stack])
    assert np.allclose(wc, ref, rtol=1e-9)


def test_transmitted_field_decays_with_depth():
    # the internal field attenuates into tissue (the skin-depth decay).
    k, psi, elem, M = _synthetic_array(seed=14)
    x = np.conj(channel_at(np.array([0.0, 0.0, 1.0]), k, psi, elem, FREQ, M))
    ku, w = collapse_paths(k, psi, elem, x)
    n_tilde = n_complex(17.0, 25.0, FREQ)
    normal = np.tile([0.0, 0.0, 1.0], (40, 1))  # surface facing +z toward the array
    r_s = np.zeros((40, 3))
    z = np.linspace(0, 3e-3, 40)
    E = transmitted_field(r_s, normal, z, ku, w, FREQ, n_tilde)
    S = np.sum(np.abs(E) ** 2, axis=1)
    assert S[0] > S[-1]  # decays into the body
    assert S[-1] < 0.2 * S[0]  # several skin depths gone by 3 mm


# --- layered skin ------------------------------------------------------------
@pytest.mark.parametrize("theta", [0.0, 0.3, 0.6, 1.0])
@pytest.mark.parametrize("pol", ["TE", "TM"])
def test_tmm_transmission_matches_fresnel(theta, pol):
    n = n_complex(17.0, 25.0, FREQ)
    prof = single_layer_reference(17.0, 25.0, FREQ, theta, pol)
    mu = np.cos(theta)
    Ts, Tp = fresnel_transmission(mu, n)
    ref = Ts if pol == "TE" else Tp
    assert abs(prof.power_transmission - ref) < 1e-9


def test_tmm_normal_incidence_te_equals_tm():
    pte = solve_layered(default_stack(FREQ), FREQ, 0.0, "TE", n_z=3000)
    ptm = solve_layered(default_stack(FREQ), FREQ, 0.0, "TM", n_z=3000)
    assert np.max(np.abs(pte.E_abs - ptm.E_abs)) < 1e-9


def test_tmm_te_field_continuous():
    # TE has no normal E; |E| must be continuous across every interface.
    prof = solve_layered(default_stack(FREQ), FREQ, 0.7, "TE", n_z=12000)
    for zb in prof.boundaries[1:]:
        i = np.searchsorted(prof.z, zb)
        rel = abs(prof.E_abs[i] - prof.E_abs[i - 1]) / max(prof.E_abs[i - 1], 1e-9)
        assert rel < 5e-3


def test_tmm_sar_peaks_at_surface():
    prof = single_layer_reference(17.0, 25.0, FREQ, 0.0, "TE", n_z=4000)
    assert np.argmax(prof.sar) < 5  # within the first few samples of the surface
    assert prof.sar[0] > prof.sar[-1]


# --------------------------------------------------------------------------
# UE antenna in the end-to-end channel (monograph eq. h-def)
# --------------------------------------------------------------------------
def test_rx_response_perpendicular_to_k():
    # C_R(k) is a transverse field, so it must be perpendicular to every k.
    from aegis.hotspot.antenna import make_rx_response

    rng = np.random.default_rng(3)
    k = rng.normal(size=(50, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    for kind in ("vertical", "dipole", "patch", "isotropic"):
        C = make_rx_response(kind, FREQ)(k)
        assert np.max(np.abs(np.einsum("nj,nj->n", C, k))) < 1e-9


def test_dipole_null_along_axis_max_broadside():
    # Half-wave dipole along z: null at the poles, peak at broadside.
    from aegis.hotspot.antenna import dipole_response

    axis = np.array([0.0, 0.0, 1.0])
    k = np.array([[0, 0, 1.0], [0, 0, -1.0], [1, 0, 0.0], [0, 1, 0.0]])
    g = np.sum(np.abs(dipole_response(k, axis, FREQ)) ** 2, axis=1)
    assert g[0] < 1e-12  # endfire null (+z)
    assert g[1] < 1e-12  # endfire null (-z)
    assert g[2] > 10 * g[0] + 1e-30  # broadside peak
    assert np.isclose(g[2], g[3])  # azimuth-symmetric


def test_isotropic_matches_legacy_vertical_direction():
    # Isotropic (unit directivity, vertical pol) must give the same channel
    # *direction* as the legacy vertical reference, so MRT is unchanged.
    from aegis.hotspot.antenna import make_rx_response

    k, psi, elem, M = _synthetic_array()
    target = np.array([0.05, -0.02, 1.0])
    h_legacy = channel_at(target, k, psi, elem, FREQ, M)
    h_iso = channel_at(target, k, psi, elem, FREQ, M, rx_response=make_rx_response("isotropic", FREQ))
    # same beam direction up to a global scale/phase
    ov = np.abs(np.vdot(h_legacy, h_iso)) / (np.linalg.norm(h_legacy) * np.linalg.norm(h_iso))
    assert ov > 0.999


def test_antenna_changes_precoder_but_not_worstcase():
    # A directional UE antenna moves the MRT beam (overlap < 1), yet the
    # exposure eigenvalue lambda_max is precoder-independent. The arrivals
    # travel toward -z, so the dipole is laid broadside (axis +x) to see them.
    from aegis.hotspot.antenna import make_rx_response

    k, psi, elem, M = _synthetic_array()
    target = np.array([0.05, -0.02, 1.0])
    h_v = channel_at(target, k, psi, elem, FREQ, M, rx_response=make_rx_response("vertical", FREQ))
    h_d = channel_at(target, k, psi, elem, FREQ, M, rx_response=make_rx_response("dipole", FREQ, axis=(1.0, 0.0, 0.0)))
    assert np.linalg.norm(h_d) > 0
    xv = np.conj(h_v) / np.linalg.norm(h_v)
    xd = np.conj(h_d) / np.linalg.norm(h_d)
    overlap = np.abs(np.vdot(xv, xd))
    assert overlap < 0.999  # the antenna actually changed the beam
    G = field_channel_at(target, k, psi, elem, FREQ, M)
    lam = np.linalg.svd(G, compute_uv=False)[0] ** 2
    # both precoders are bounded by the same eigenvalue
    assert np.sum(np.abs(G @ xv) ** 2) <= lam + 1e-9
    assert np.sum(np.abs(G @ xd) ** 2) <= lam + 1e-9


def test_worstcase_beam_at_skin_reaches_absorption_envelope():
    # The studio's at-skin worstcase beam is built from the tissue channel
    # G_tilde at the focus, so it must deposit exactly the worst-case absorption
    # eigenvalue lambda_max(G_tilde^H G_tilde) there. The free-space field-optimal
    # beam (the only option for an in-air focus) is a different precoder that
    # underachieves that envelope once the Fresnel filter is applied.
    from aegis.coherent.body_channel import compute_body_channel
    from aegis.tissue.dielectric import skin_props
    from aegis.viewer.routes.studio._precoders import build_precoder

    k, psi, elem, M = _synthetic_array()
    paths = (k, psi, elem, M)
    focus = np.array([0.05, -0.02, 1.0])
    normal = np.array([0.0, 0.0, 1.0])  # faces the -z arrivals (mu = n.(-k) > 0)
    n_tilde, sigma = skin_props(28.0)

    g_tilde = compute_body_channel(
        normal.reshape(1, 3), focus.reshape(1, 3), k, psi, elem, n_tilde, sigma, FREQ, M
    )
    lam = float(np.linalg.svd(g_tilde[0], compute_uv=False)[0] ** 2)

    x_abs = build_precoder(
        "worstcase", paths, focus, FREQ, power=1.0, body_normal=normal, n_tilde=n_tilde, sigma=sigma
    )
    x_field = build_precoder("worstcase", paths, focus, FREQ, power=1.0)

    dep_abs = float(np.sum(np.abs(g_tilde[0] @ x_abs) ** 2))
    dep_field = float(np.sum(np.abs(g_tilde[0] @ x_field) ** 2))

    # Both are matched-power precoders.
    assert np.isclose(np.vdot(x_abs, x_abs).real, 1.0)
    assert np.isclose(np.vdot(x_field, x_field).real, 1.0)
    # The absorption beam reaches the worst-case envelope; the field beam cannot exceed it.
    assert np.isclose(dep_abs, lam, rtol=1e-6)
    assert dep_field <= lam + 1e-9
    # The two are genuinely different beams (the bug was using the field one on the body).
    assert np.abs(np.vdot(x_abs, x_field)) < 0.999
    assert dep_field < lam  # field-optimal strictly underachieves absorption worst case

"""Shipboard X-band exposure-envelope sweep: AEGIS envelope vs industry zone.

Reproduces every number in 02_envelope_numbers.md. Run:
    .venv/bin/python spinoff/military_angle/agent_reports/envelope_calc/run_envelope.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from envelope_lib import (  # noqa: E402
    build_G_tilde, planar_array, skin_at, exposure_operator,
    sab_of_beam, worst_case_local_apd,
)
from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.constants import Z_0  # noqa: E402

REPO = HERE.parents[3]
C = 2.99792458e8

# ---------------------------------------------------------------------------
# Scenario parameters (justified in the report from public naval X-band data)
# ---------------------------------------------------------------------------
FREQ = 9.4e9                      # X-band shipboard fire-control / nav band
LAM = C / FREQ                    # 0.0319 m
G_ELEM = np.pi                    # filled lambda/2 aperture element directivity (4.97 dBi)
SCEN = "occupational"            # military-controlled == ICNIRP occupational
# ICNIRP 2020 occupational limits at 9.4 GHz
SAB_4CM2_LIM = 100.0             # W/m^2 (basic restriction, absorbed, 4 cm^2)
SAR_WB_LIM = 0.4                 # W/kg
SINC_LOCAL_LIM = 275.0 / (FREQ / 1e9) ** 0.177   # W/m^2 (reference level, local)
DUKE_MASS = 72.0                 # kg

RADIUS_4CM2 = np.sqrt(4e-4 / np.pi)   # 0.01128 m disk of 4 cm^2


def load_body(subsample=None, seed=0):
    b = BodyMesh.load(str(REPO / "data/duke.stl"))
    cen, nrm, ar = b.centroids.copy(), b.normals.copy(), b.areas.copy()
    # center feet at z origin already (~-0.9..0.9); shift so feet at z=0 (deck)
    cen[:, 2] -= cen[:, 2].min()
    if subsample and subsample < len(ar):
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(ar), subsample, replace=False)
        # scale areas so total area is preserved (unbiased Q estimate)
        scale = ar.sum() / ar[idx].sum()
        return cen[idx], nrm[idx], ar[idx] * scale, (cen, nrm, ar)
    return cen, nrm, ar, (cen, nrm, ar)


def yaw_body(cen, nrm, deg):
    t = np.deg2rad(deg)
    Rz = np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
    return cen @ Rz.T, nrm @ Rz.T


def place(cen, nrm, r):
    """Body centered at (r,0, z). Array sits at x=0. Body center height ~ mid."""
    c = cen.copy()
    c[:, 0] += r
    return c, nrm


def coord_ascent_unimodular(Q, iters=60, restarts=4, seed=0):
    """Max x^H Q x s.t. |x_i|=1/sqrt(M) (phase-only). Coordinate ascent.

    Returns best achievable value (lower bound on the phase-only supremum)."""
    M = Q.shape[0]
    rng = np.random.default_rng(seed)
    best = 0.0
    for _ in range(restarts):
        x = np.exp(1j * rng.uniform(0, 2 * np.pi, M)) / np.sqrt(M)
        for _ in range(iters):
            Qx = Q @ x
            for i in range(M):
                # optimal phase for element i given the rest: align x_i with (Qx - Q_ii x_i)
                gi = Qx[i] - Q[i, i] * x[i]
                if abs(gi) > 0:
                    new = (gi.conj() / abs(gi)) / np.sqrt(M)
                    Qx += Q[:, i] * (new - x[i])
                    x[i] = new
        val = float(np.real(x.conj() @ Q @ x))
        best = max(best, val)
    return best


def worst_case_4cm2(G, cen, areas, hotspot_tris, tree):
    """Worst-case-over-all-beams 4 cm^2-averaged APD.

    For each candidate window (disk of 4 cm^2 around a hot triangle) the worst
    4 cm^2 APD over all unit-norm beams is lambda_max of the windowed operator
    Q_w = (1/A_w) sum_{t in w} area_t G_t^H G_t. Max over windows.
    """
    best = 0.0
    best_frac_peak = 1.0
    for t0 in hotspot_tris:
        idx = tree.query_ball_point(cen[t0], RADIUS_4CM2)
        if len(idx) < 2:
            continue
        idx = np.asarray(idx)
        Aw = areas[idx].sum()
        Gw = G[idx]                              # (nw,3,M)
        w = np.sqrt(areas[idx] / Aw)[:, None, None]
        Gh = (w * Gw).reshape(-1, G.shape[2])
        Qw = Gh.conj().T @ Gh
        lam = float(np.linalg.eigvalsh((Qw + Qw.conj().T) / 2)[-1])
        if lam > best:
            best = lam
    return best


def steer_far(pel, u):
    """Unit-norm precoder steering the main beam toward far-field direction u."""
    x = np.exp(1j * (2 * np.pi * FREQ / C) * (pel @ np.asarray(u, float)))
    return x / np.linalg.norm(x)


def run():
    out = {"params": {
        "freq_hz": FREQ, "lambda_m": LAM, "g_elem": G_ELEM,
        "sab_4cm2_lim_Wm2": SAB_4CM2_LIM, "sar_wb_lim_Wkg": SAR_WB_LIM,
        "sinc_local_lim_Wm2": SINC_LOCAL_LIM, "duke_mass_kg": DUKE_MASS,
        "skin_ref": None,
    }, "arrays": {}}

    n_t, sig, fk = skin_at(FREQ / 1e9)
    out["params"]["skin_ref"] = {"key_ghz": fk, "n_tilde": [n_t.real, n_t.imag], "sigma": sig}

    arrays = {
        "tracker_256": dict(n_side=16, subsample=None),
        "illuminator_1600": dict(n_side=40, subsample=9000),
    }

    for aname, acfg in arrays.items():
        nside = acfg["n_side"]; M = nside ** 2
        D = nside * LAM / 2
        r_ff = 2 * D ** 2 / LAM
        G_arr_dbi = 10 * np.log10(M * G_ELEM)
        cen0, nrm0, ar0, full = load_body(subsample=acfg["subsample"])
        rec = {"M": M, "aperture_m": D, "far_field_m": r_ff,
               "gain_dBi": G_arr_dbi, "n_tri": len(ar0), "ranges": {}}

        for r in [5.0, 10.0, 20.0, 50.0, 100.0]:
            rr = {}
            for yaw in [0.0, 90.0, 180.0]:
                cy, ny = yaw_body(cen0, nrm0, yaw)
                cp, npn = place(cy, ny, r)
                # array centered at x=0, at body mid-height
                zc = cp[:, 2].mean()
                pel = planar_array(nside, LAM / 2, center=(0.0, 0.0, zc))
                G = build_G_tilde(cp, npn, pel, n_t, sig, FREQ, g_elem=G_ELEM)

                Q = exposure_operator(G, ar0)
                ev = np.linalg.eigvalsh(Q)
                lam_max = float(ev[-1]); trace = float(ev.sum())

                wc_local = worst_case_local_apd(G)   # (T,) per W, single-tri
                peak_tri = float(wc_local.max())
                topk = np.argsort(wc_local)[-8:]
                tree = cKDTree(cp)
                wc4 = worst_case_4cm2(G, cp, ar0, topk, tree)

                # (C) realistic beam: steer main beam at body center (worst realistic)
                bc = cp.mean(axis=0)
                u_body = bc / np.linalg.norm(bc)
                x_steer = steer_far(pel, u_body)
                sab_steer = sab_of_beam(G, x_steer)
                p_abs_steer = float(np.real(x_steer.conj() @ Q @ x_steer))
                peak_steer = float(sab_steer.max())
                # off-beam: target 10 deg above body in elevation
                u_off = np.array([np.cos(np.deg2rad(10)), 0, np.sin(np.deg2rad(10))])
                x_off = steer_far(pel, u_off)
                p_abs_off = float(np.real(x_off.conj() @ Q @ x_off))
                peak_off = float(sab_of_beam(G, x_off).max())

                # (A) industry unperturbed far-field zone (per W)
                sinc_ff = M * G_ELEM / (4 * np.pi * r ** 2)
                # near-field aperture plateau 4P/A (per W), A = physical aperture
                A_ap = D ** 2
                sinc_nf = 4.0 / A_ap

                entry = dict(
                    lam_max=lam_max, trace=trace, top_frac=lam_max / trace,
                    wc_local_peak=peak_tri, wc_local_4cm2=wc4,
                    p_abs_steer=p_abs_steer, peak_steer=peak_steer,
                    rho=p_abs_steer / lam_max if lam_max > 0 else 0.0,
                    p_abs_off=p_abs_off, peak_off=peak_off,
                    sinc_ff=sinc_ff, sinc_nf=sinc_nf,
                )
                # per-element-modulus (phase-only) constrained whole-body max, near-field only
                if yaw == 0.0 and r <= r_ff * 1.5:
                    ph = coord_ascent_unimodular(Q, iters=40, restarts=3)
                    entry["phaseonly_max"] = ph
                    entry["phaseonly_over_lammax"] = ph / lam_max if lam_max > 0 else 0.0
                rr[f"yaw{int(yaw)}"] = entry
            rec["ranges"][f"r{int(r)}"] = rr
        out["arrays"][aname] = rec
        print(f"done {aname}")

    (HERE / "results.json").write_text(json.dumps(out, indent=2))
    print("wrote results.json")
    return out


if __name__ == "__main__":
    run()

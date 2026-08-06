"""Derived numbers for the envelope report: zone comparison, looseness of
lambda_max, scan-sector envelope, three blindnesses, breach power."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from envelope_lib import (build_G_tilde, planar_array, skin_at, exposure_operator,  # noqa: E402
                          sab_of_beam, worst_case_local_apd)
from aegis.geometry.mesh import BodyMesh  # noqa: E402
REPO = HERE.parents[3]
C = 2.99792458e8
d = json.load(open(HERE / "results.json"))
P = d["params"]
SINC_LIM = P["sinc_local_lim_Wm2"]; SAB_LIM = P["sab_4cm2_lim_Wm2"]
SAR_LIM = P["sar_wb_lim_Wkg"]; MASS = P["duke_mass_kg"]; FREQ = P["freq_hz"]; LAM = C / FREQ
n_t, sig, fk = skin_at(FREQ / 1e9)
T0n = 1 - abs((1 - n_t) / (1 + n_t)) ** 2

print("=" * 70)
print("A vs B ZONE COMPARISON (compliance ratio per unit radiated power)")
print("C_A = sinc_ff/SINC_lim ; C_B = wc_local_4cm2/SAB_lim ; ratio C_B/C_A")
print("A zone boundary is at larger range when C_A>C_B (ratio<1).")
print("=" * 70)
for aname, a in d["arrays"].items():
    print(f"\n{aname} (gain {a['gain_dBi']:.1f} dBi, far-field {a['far_field_m']:.0f} m):")
    print("  r(m)  yaw0: C_B/C_A   wc4/sinc   [B zone / A zone radius]")
    for rk, rr in a["ranges"].items():
        e = rr["yaw0"]
        ratio = (e["wc_local_4cm2"] / SAB_LIM) / (e["sinc_ff"] / SINC_LIM)
        wcs = e["wc_local_4cm2"] / e["sinc_ff"]
        # zone radius ratio: both ~1/r^2, so r_B/r_A = sqrt(C_B/C_A) at fixed r
        zr = np.sqrt(ratio)
        print(f"  {rk[1:]:>4}          {ratio:6.3f}     {wcs:6.3f}        {zr:6.3f}")

print("\n" + "=" * 70)
print("THREE BLINDNESSES at 9.4 GHz (illuminator, yaw0)")
print("=" * 70)
for aname, a in d["arrays"].items():
    for rk in ["r10", "r20"]:
        e = a["ranges"][rk]["yaw0"]
        b_i = e["wc_local_peak"] / e["wc_local_4cm2"]           # spatial 4cm2 dilution
        b_iii = e["wc_local_peak"] / (T0n * e["sinc_ff"])       # near-field focal enhancement
        print(f"{aname} {rk}: (i)spatial={b_i:.2f}  (iii)nf-focus={b_iii:.2f}  T0={T0n:.3f}")

# focal spot size: from a beam steered to body centre, illuminator r10
print("\n" + "=" * 70)
print("FOCAL SPOT SIZE at 9.4 GHz (recompute illuminator r=10 m, steer to torso)")
print("=" * 70)
b = BodyMesh.load(str(REPO / "data/duke.stl"))
cen = b.centroids.copy(); cen[:, 2] -= cen[:, 2].min(); nrm = b.normals.copy()
rng = np.random.default_rng(0); idx = rng.choice(len(b.areas), 12000, replace=False)
cen, nrm, ar = cen[idx], nrm[idx], b.areas[idx] * (b.areas.sum() / b.areas[idx].sum())
r = 10.0
cp = cen.copy(); cp[:, 0] += r
nside = 40; pel = planar_array(nside, LAM / 2, center=(0, 0, cp[:, 2].mean()))
G = build_G_tilde(cp, nrm, pel, n_t, sig, FREQ, g_elem=np.pi)
Q = exposure_operator(G, ar)
ev, V = np.linalg.eigh(Q)
lam_max = float(ev[-1])
# worst-case beam = top eigenvector
x_wc = V[:, -1]
sab = sab_of_beam(G, x_wc)
tpk = int(np.argmax(sab)); pk = sab[tpk]
tree = cKDTree(cp)
# spot: area of triangles >= 50% of peak, contiguous-ish around hotspot
near = tree.query_ball_point(cp[tpk], 0.4)
near = np.array(near)
hot = near[sab[near] >= 0.5 * pk]
spot_area_cm2 = ar[hot].sum() * 1e4
# diameter estimate
diam = 2 * np.sqrt(spot_area_cm2 / np.pi)
print(f"worst-case beam peak S_ab per W = {pk:.3f} ; >=50%-peak footprint = {spot_area_cm2:.0f} cm^2 (~{diam:.1f} cm dia)")
print(f"4 cm^2 window diameter = {2*np.sqrt(4/np.pi):.2f} cm  ->  spot {'>>' if spot_area_cm2>8 else '~'} 4 cm^2  => spatial dilution ~1")

# LOOSENESS of lambda_max vs per-element modulus (phase-only, equal power) with good init
print("\n" + "=" * 70)
print("Q2: looseness of unconstrained lambda_max vs phase-only equal-power beam")
print("phase-only achievable >= best of {steer-to-body, top-eigvec phase} + coord ascent")
print("=" * 70)
def coord_ascent(Q, x0, iters=200):
    M = Q.shape[0]; x = x0.copy().astype(complex); x /= (np.abs(x) * np.sqrt(M))
    Qx = Q @ x
    for _ in range(iters):
        for i in range(M):
            gi = Qx[i] - Q[i, i] * x[i]
            if abs(gi) > 0:
                new = (gi.conj() / abs(gi)) / np.sqrt(M)
                Qx += Q[:, i] * (new - x[i]); x[i] = new
    return float(np.real(x.conj() @ Q @ x)), x
# inits
bc = cp.mean(0); u = bc / np.linalg.norm(bc)
x_steer = np.exp(1j * (2 * np.pi * FREQ / C) * (pel @ u))
v_ph = np.exp(1j * np.angle(V[:, -1]))
best = 0.0
for x0 in [x_steer, v_ph]:
    val, _ = coord_ascent(Q, x0)
    best = max(best, val)
p_steer = float(np.real((x_steer/np.linalg.norm(x_steer)).conj() @ Q @ (x_steer/np.linalg.norm(x_steer))))
print(f"illuminator r=10: lam_max={lam_max:.4f}")
print(f"  steer-to-body (in-phase, = industry full-gain beam): {p_steer:.4f}  ({p_steer/lam_max*100:.0f}% of lam_max)")
print(f"  best phase-only equal-power achievable:              {best:.4f}  ({best/lam_max*100:.0f}% of lam_max)")
print(f"  => lam_max is at most {lam_max/best:.2f}x above the realizable phase-only worst case")

# SCAN-SECTOR restricted worst case: array boresight at horizon (+x), person on deck below.
# Restrict beams to a scan cone about +x (main energy stays off the deck). Model: worst-case
# over beams that are steering vectors within the scan sector, evaluated on the body.
print("\n" + "=" * 70)
print("SCAN-SECTOR envelope: worst on-body deposit when main beam is confined to")
print("a scan cone that excludes the body direction (the real zone-shrink lever)")
print("=" * 70)
# body is at +x, elevation ~0 (torso at array height). Put array boresight at +x but
# person at 30 deg below boresight: shift array up so body dir is 30 deg down.
# simpler: compute max over far-field steering directions within +/-45 deg of +x in azimuth
# and >=+15 deg elevation (beam kept above deck) of the on-body absorbed peak.
def steer(u):
    x = np.exp(1j * (2 * np.pi * FREQ / C) * (pel @ u)); return x / np.linalg.norm(x)
best_in = 0.0; best_sky = 0.0
for az in np.deg2rad(np.linspace(-60, 60, 25)):
    for el in np.deg2rad(np.linspace(-40, 40, 25)):
        u = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        pk_body = float(sab_of_beam(G, steer(u)).max())
        best_in = max(best_in, pk_body)               # beam free to point anywhere (incl at body)
        if el >= np.deg2rad(15):                        # beam kept >=15 deg above horizon
            best_sky = max(best_sky, pk_body)
print(f"  worst on-body peak, beam free to point at person: {best_in:.3f} W/m2 per W")
print(f"  worst on-body peak, beam confined >=15 deg elevation (off deck): {best_sky:.3f}")
print(f"  scan-sector suppression = {best_in/max(best_sky,1e-9):.1f}x = {10*np.log10(best_in/max(best_sky,1e-9)):.0f} dB")

# Q4 breach power at 20 m, scaled to real emitter gains
print("\n" + "=" * 70)
print("Q4: total radiated power to breach occupational APD (100 W/m2) at 20 m")
print("=" * 70)
for aname, a in d["arrays"].items():
    e = a["ranges"]["r20"]["yaw0"]
    wc = e["wc_local_4cm2"]
    Pbreach = SAB_LIM / wc
    print(f"  {aname} ({a['gain_dBi']:.0f} dBi): worst-case beam breaches at {Pbreach:.0f} W radiated")
# scale to AN/SPG-62: 45 dBi, gain ratio vs illuminator(37 dBi)
g_ratio = 10 ** ((45 - 37) / 10)
wc_spg = d["arrays"]["illuminator_1600"]["ranges"]["r20"]["yaw0"]["wc_local_4cm2"] * g_ratio
Pbreach_spg = SAB_LIM / wc_spg
print(f"  AN/SPG-62-scaled (45 dBi): breaches at {Pbreach_spg:.1f} W radiated at 20 m")
print(f"  AN/SPG-62 actually radiates 10 kW (CW)  -> breach factor {1e4/Pbreach_spg:.0f}x over the limit")
# zone radius for AN/SPG-62 at 10 kW: wc ~ 1/r^2, so r_zone = 20 * sqrt(P*wc20 / 100)
r_zone_spg = 20 * np.sqrt(1e4 * wc_spg / SAB_LIM)
# industry far-field zone: sinc_ff(20)*g_ratio vs SINC_lim
sinc20 = d["arrays"]["illuminator_1600"]["ranges"]["r20"]["yaw0"]["sinc_ff"] * g_ratio
r_zone_ind = 20 * np.sqrt(1e4 * sinc20 / SINC_LIM)
print(f"  AEGIS envelope zone radius (10 kW): {r_zone_spg:.0f} m ; industry incident zone: {r_zone_ind:.0f} m")
print(f"  => AEGIS zone / industry zone = {r_zone_spg/r_zone_ind:.3f}")
np.save(HERE / "spot_sab.npy", np.column_stack([cp, sab]))

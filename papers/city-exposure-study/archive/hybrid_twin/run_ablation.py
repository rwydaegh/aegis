"""Three-way scene ablation: intelligent hybrid vs naive OSM vs naive photogrammetry.

Traces every base-station sector to a decimated version of the pedestrian walk in
each of the three Mitsuba scenes written by `export_scenes.py` and records the
exposure-relevant quantities per walk sample: total path gain, LOS flag, path
count. The three scenes share one ENU frame, so the walk xy is identical in all
three; only the z differs, because each scene has its own idea of where the
ground is (that disagreement is part of what is being measured).

    python run_ablation.py --every 10                                    # smoke
    python run_ablation.py --every 2 --samples 4000000 \
        --out data/ablation_full.json --figure figures/ablation_full.png # full
    python run_ablation.py --scenes osm --verify-sectors                 # sanity
    python run_ablation.py --plot-only                                   # redraw

Runs on the venv python, not Blender. The ENU frame and the terrain lookup follow
`export_scenes.py`; the ground probe does not, see `probe_street`. Findings and
the choices behind the defaults are in ABLATION_NOTES.md.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time
import xml.etree.ElementTree as ET

import numpy as np

C0 = 299792458.0
EPS0 = 8.8541878128e-12
WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3
WALK_STEP = 1.0          # m, same resampling as poc_relevance.py
RX_AGL = 1.5             # m above the local scene surface
SCENES = ("hybrid", "osm", "photo")
VEG_MATERIAL_NAME = "itu_wood"   # the placeholder the exporter put on the canopies


# ------------------------------------------------------------------ geodesy
def llh_to_ecef(lat_deg, lon_deg, h=0.0):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array([
        (n + h) * math.cos(lat) * math.cos(lon),
        (n + h) * math.cos(lat) * math.sin(lon),
        (n * (1 - WGS84_E2) + h) * math.sin(lat)])


def enu_rotation(lat_deg, lon_deg):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon),
                      math.cos(lat)])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon),
                   math.sin(lat)])
    return np.vstack([east, north, up])


def terrain_z(terrain, x, y):
    """Bilinear lookup on the exporter's terrain grid, clamped at the border."""
    z = np.asarray(terrain["z"])
    n, x0, st = terrain["n"], terrain["x0"], terrain["step"]
    fx = min(max((x - x0) / st, 0.0), n - 1.001)
    fy = min(max((y - x0) / st, 0.0), n - 1.001)
    ix, iy = int(fx), int(fy)
    tx, ty = fx - ix, fy - iy
    return float((1 - ty) * ((1 - tx) * z[iy, ix] + tx * z[iy, ix + 1])
                 + ty * ((1 - tx) * z[iy + 1, ix] + tx * z[iy + 1, ix + 1]))


def probe_surface(scene, x, y, z_from=400.0):
    """Height of the topmost surface of a loaded Mitsuba scene at (x, y)."""
    import mitsuba as mi

    r = mi.Ray3f(o=mi.Point3f(x, y, z_from), d=mi.Vector3f(0.0, 0.0, -1.0))
    si = scene.mi_scene.ray_intersect(r)
    if not bool(np.asarray(si.is_valid())[0]):
        return None
    return float(np.asarray(si.p).ravel()[2])


def probe_street(scene, xy, radius=2.5, z_from=400.0):
    """Street level under each walk sample: lowest of five probes on a small disk.

    A single vertical ray is wrong here. The walk hugs facades, so the ray clips
    a roof edge or an overhang and the receiver ends up on a roof: six of the 49
    smoke samples came out 14-21 m above the terrain that way, over a 50 m
    stretch where the route runs along a building edge. `poc_relevance.py` uses
    the same min-over-disk projection for the same reason. A receiver genuinely
    on a roof still reads as a roof, since all five probes land on it.

    Takes and returns arrays: one batched Mitsuba call for the whole walk, since
    ray by ray the drjit dispatch overhead dominates (26 s for 123 samples).
    Samples where no probe hits anything come back as NaN.
    """
    import mitsuba as mi

    xy = np.atleast_2d(np.asarray(xy, dtype=float))
    off = np.array([(0.0, 0.0), (radius, 0.0), (-radius, 0.0),
                    (0.0, radius), (0.0, -radius)])
    p = (xy[:, None, :] + off[None, :, :]).reshape(-1, 2)
    r = mi.Ray3f(o=mi.Point3f(p[:, 0], p[:, 1], np.full(len(p), z_from)),
                 d=mi.Vector3f(0.0, 0.0, -1.0))
    si = scene.mi_scene.ray_intersect(r)
    z = np.asarray(si.p.z, dtype=float).reshape(len(xy), len(off))
    ok = np.asarray(si.is_valid()).reshape(len(xy), len(off))
    z = np.where(ok, z, np.inf)
    out = z.min(axis=1)
    return np.where(np.isfinite(out), out, np.nan)


# --------------------------------------------------------------------- walk
def load_walk_xy(gpx_path, rot, p0, step=WALK_STEP):
    """GPX track -> ENU xy resampled at `step`, plus cumulative arc length."""
    pts = []
    for tp in ET.parse(gpx_path).getroot().iter(
            "{http://www.topografix.com/GPX/1/1}trkpt"):
        e = rot @ (llh_to_ecef(float(tp.get("lat")), float(tp.get("lon"))) - p0)
        pts.append(e[:2])
    pts = np.asarray(pts)
    out = []
    for a, b in zip(pts[:-1], pts[1:], strict=True):
        seg = b - a
        n = max(int(np.linalg.norm(seg) / step), 1)
        for i in range(n):
            out.append(a + seg * (i / n))
    out.append(pts[-1])
    out = np.asarray(out)
    d = np.linalg.norm(np.diff(out, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    return out, s


# -------------------------------------------------------------------- sites
def cluster_sites(sites, rot, p0, xy_tol=15.0, z_tol=3.0, merge_deg=15.0):
    """Collapse the operator records of `sites.json` into physical masts.

    `data/sites.json` holds one record per operator/technology registration, so
    the same mast appears several times (10 records, 6 masts here). Records
    within `xy_tol` horizontally and `z_tol` in antenna height are one mast; its
    sector set is the union of the member azimuths deduplicated at `merge_deg`,
    because two registrations of the same physical panel differ by a few degrees.
    """
    recs = []
    for s in sites:
        e = rot @ (llh_to_ecef(s["lat"], s["lon"]) - p0)
        recs.append(dict(s, x=float(e[0]), y=float(e[1])))
    recs.sort(key=lambda r: -r["power_dbm_max"])

    masts = []
    for r in recs:
        for m in masts:
            if (math.hypot(r["x"] - m["x"], r["y"] - m["y"]) < xy_tol
                    and abs(r["height"] - m["height"]) < z_tol):
                m["members"].append(r["site"])
                m["azimuths"] += list(r["azimuths"])
                m["n_antennas"] += r["n_antennas"]
                m["height"] = max(m["height"], r["height"])
                break
        else:
            masts.append({"site": r["site"], "members": [r["site"]],
                          "x": r["x"], "y": r["y"], "height": r["height"],
                          "power_dbm_max": r["power_dbm_max"],
                          "n_antennas": r["n_antennas"],
                          "azimuths": list(r["azimuths"])})

    for m in masts:
        kept = []
        for a in sorted(set(float(a) % 360.0 for a in m["azimuths"])):
            if not kept or min(abs(a - k) for k in kept) >= merge_deg:
                kept.append(a)
        # wrap-around: 355 and 5 are the same panel
        if len(kept) > 1 and (kept[0] + 360.0 - kept[-1]) < merge_deg:
            kept.pop()
        m["azimuths"] = kept
    return masts


def sector_orientation(azimuth_deg, downtilt_deg):
    """Sionna (yaw, pitch, roll) for a compass azimuth and a mechanical downtilt.

    Sionna's element boresight is +x with zero orientation, and this frame's +x
    is East, so a compass azimuth A (from North, clockwise) is a yaw of 90 - A.
    Positive pitch rotates the boresight about +y, i.e. downwards.
    """
    return [math.radians(90.0 - azimuth_deg), math.radians(downtilt_deg), 0.0]


def tr38901_gain_db(theta, phi):
    """Power gain [dBi] of the 3GPP TR 38.901 Table 7.3-1 element, numpy port.

    Same expression as `sionna.rt.antenna_pattern.v_tr38901_pattern`, which
    returns the field amplitude sqrt(10**(a_db/10)); this returns a_db.
    """
    phi = (phi + math.pi) % (2.0 * math.pi) - math.pi
    theta_3db = phi_3db = math.radians(65.0)
    a_v = -np.minimum(12.0 * ((theta - math.pi / 2.0) / theta_3db) ** 2, 30.0)
    a_h = -np.minimum(12.0 * (phi / phi_3db) ** 2, 30.0)
    return -np.minimum(-(a_v + a_h), 30.0) + 8.0


def sector_gains(theta_t, phi_t, azimuths, pattern):
    """Per-sector power gain for every departure direction, sectors last.

    All sectors of a mast sit at the same point, so their ray geometry is
    identical and one isotropic trace serves all of them: the element pattern is
    a per-path scalar applied afterwards. This is exact for a yaw-only rotation,
    because a rotation about z leaves the spherical polarization basis at a given
    world direction unchanged, so only the pattern arguments move. It is not
    exact once a downtilt is added, which is why `--downtilt` forces the traced
    mode. `theta_t`/`phi_t` are world-frame angles of departure.
    """
    if pattern == "iso":
        return np.ones(theta_t.shape + (len(azimuths),))
    if pattern != "tr38901":
        raise ValueError(f"no analytic sector model for pattern {pattern!r}; "
                         "use --sector-mode traced")
    out = np.empty(theta_t.shape + (len(azimuths),))
    for k, az in enumerate(azimuths):
        yaw = math.radians(90.0 - az)
        out[..., k] = 10.0 ** (tr38901_gain_db(theta_t, phi_t - yaw) / 10.0)
    return out


# --------------------------------------------------------------- vegetation
def derive_vegetation(freq_hz, blobs, eps_r=1.2, species="Plane tree, american"):
    """Effective homogeneous lossy medium for the canopy proxies, from ITU-R P.833.

    Source number: Recommendation ITU-R P.833-10 (09/2021), Table 8, "Fitted
    values of sigma with frequency/species", 3.5 GHz row, in leaf. sigma is the
    RET combined absorption and scatter coefficient; the RET reduced intensity
    goes as exp(-tau) with tau = sigma * z and intensity is power, so the
    specific attenuation is 10*log10(e)*sigma = 4.343*sigma dB/m (not 8.686,
    which applies to a field propagation constant such as the K_c'' of Step 9).
    """
    sigma_ret = {              # ITU-R P.833-10 Table 8, 3.5 GHz, in leaf [Np/m]
        "Ginkgo": 0.30,
        "Cherry, Japanese": 0.21,
        "Trident maple": 0.73,
        "Korean pine": 0.334,
        "Himalayan cedar": 0.603,
        "Plane tree, american": 0.513,
        "Dawn redwood": 0.370,
    }
    sig = sigma_ret[species]
    gamma_db_m = 10.0 * math.log10(math.e) * sig          # 4.343 * sigma
    alpha = 0.11513 * gamma_db_m                          # Np/m, field
    # low-loss slab: alpha = (pi f / c) * eps'' / sqrt(eps')
    eps_pp = alpha * math.sqrt(eps_r) * C0 / (math.pi * freq_hz)
    conductivity = 2.0 * math.pi * freq_hz * EPS0 * eps_pp
    tan_d = eps_pp / eps_r
    # exact Debye attenuation constant, to show the low-loss step is harmless
    alpha_exact = (2 * math.pi * freq_hz / C0) * math.sqrt(
        0.5 * eps_r * (math.sqrt(1 + tan_d ** 2) - 1))

    # Sionna models every intersected face as a slab of `thickness`, so a closed
    # canopy proxy is crossed twice. Size the slab at half the mean chord of the
    # proxies so that entry + exit reproduces one mean traversal.
    chords = []
    for b in blobs:
        r = max(math.sqrt(b["area_m2"] / math.pi), 2.0)
        h = max(b["h_mean"], 3.0)
        rz = 0.5 * (h - 0.35 * h)                          # CANOPY_BASE_FRAC=0.35
        vol = 4.0 / 3.0 * math.pi * r * r * rz
        if rz < r:                                         # oblate
            e = math.sqrt(1.0 - (rz / r) ** 2)
            surf = 2 * math.pi * r * r * (1 + (1 - e * e) / e * math.atanh(e))
        else:                                              # prolate
            e = math.sqrt(1.0 - (r / rz) ** 2)
            surf = 2 * math.pi * r * r * (1 + rz / (r * e) * math.asin(e))
        chords.append(4.0 * vol / surf)                    # Cauchy mean chord
    mean_chord = float(np.median(chords))
    thickness = 0.5 * mean_chord

    return {
        "name": "canopy_p833",
        "source": {
            "recommendation": "ITU-R P.833-10 (09/2021), Attenuation in vegetation",
            "url": "https://www.itu.int/dms_pubrec/itu-r/rec/p/"
                   "R-REC-P.833-10-202109-I!!PDF-E.pdf",
            "table": "Table 8, fitted values of sigma with frequency/species",
            "row": "3.5 GHz, in leaf",
            "species": species,
            "species_note": "Platanus is the dominant street tree around the "
                            "Korenmarkt; Table 8 has no European species at "
                            "3.5 GHz, so the American plane column is used.",
            "sigma_ret_np_per_m": sig,
            "all_in_leaf_3p5ghz_np_per_m": sigma_ret,
        },
        "derivation": [
            "gamma = 10*log10(e) * sigma_RET  [dB/m]. sigma_RET is a power "
            "extinction coefficient (P.833 uses exp(-tau) inside a -10*log10), "
            "so the conversion factor is 4.343, not 8.686.",
            "alpha = 0.11513 * gamma  [Np/m, field amplitude].",
            "Low-loss slab: alpha ~ (pi f / c) * eps'' / sqrt(eps'), so "
            "eps'' = alpha * sqrt(eps') * c / (pi f).",
            "sigma_cond = 2 pi f eps0 eps''.",
            "eps' is not measured here; 1.2 is taken as a sparse canopy, which "
            "keeps the front-face Fresnel reflection near -27 dB so the proxy "
            "attenuates rather than mirrors.",
            "Sionna treats every intersected face as a slab of `thickness`, so "
            "a closed proxy is crossed twice; thickness is half the median "
            "Cauchy mean chord (4V/S) of the 15 proxies.",
        ],
        "frequency_hz": freq_hz,
        "gamma_db_per_m": gamma_db_m,
        "alpha_np_per_m": alpha,
        "relative_permittivity": eps_r,
        "loss_tangent": tan_d,
        "imag_permittivity": eps_pp,
        "conductivity_s_per_m": conductivity,
        "alpha_exact_np_per_m": alpha_exact,
        "low_loss_error_pct": 100.0 * (alpha_exact - alpha) / alpha,
        "thickness_m": thickness,
        "mean_chord_m": mean_chord,
        "one_way_slab_loss_db": gamma_db_m * thickness,
        "proxy_traversal_loss_db": gamma_db_m * mean_chord,
        "sensitivity_db_per_m": {
            k: 10.0 * math.log10(math.e) * v for k, v in sigma_ret.items()},
        "caveats": [
            "The proxies are fused blobs from the upstream clustering, so a "
            "tree row is one ellipsoid; a per-metre canopy density applied to "
            "a row-sized volume overstates the loss for the widest proxy "
            "(17.5 m radius). The half-mean-chord thickness bounds this: the "
            "loss is the same for every proxy regardless of its size.",
            "P.833 Table 8 is a single-tree canopy, denser than the woodland "
            "average of Fig. 2 (~0.3 dB/m at 2 GHz). That is the right regime "
            "for a canopy proxy and the wrong one for a forest.",
        ],
    }


def apply_vegetation(scene, veg):
    """Swap the placeholder itu_wood BSDF on the canopy proxies for the P.833 medium."""
    from sionna.rt import RadioMaterial

    mat = RadioMaterial(veg["name"],
                        relative_permittivity=veg["relative_permittivity"],
                        conductivity=veg["conductivity_s_per_m"],
                        thickness=veg["thickness_m"])
    n = 0
    for obj in scene.objects.values():
        if obj.radio_material.name == VEG_MATERIAL_NAME:
            obj.radio_material = mat
            n += 1
    return n


# ---------------------------------------------------------------------- run
def solve_site(scene, mast, rx_xyz, args):
    """Trace one mast to every walk sample and reduce to per-sample scalars.

    In `analytic` sector mode one isotropic source is traced and the sector
    patterns are applied per path afterwards; in `traced` mode one transmitter
    per sector is placed and Sionna applies them.
    """
    from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter

    analytic = args.sector_mode == "analytic"
    scene.tx_array = PlanarArray(num_rows=1, num_cols=1, polarization="V",
                                 pattern="iso" if analytic else args.tx_pattern)
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                 polarization="V")
    for name in list(scene.transmitters):
        scene.remove(name)
    for name in list(scene.receivers):
        scene.remove(name)
    if analytic:
        scene.add(Transmitter("s0", position=mast["pos"]))
    else:
        for k, az in enumerate(mast["azimuths"]):
            scene.add(Transmitter(f"s{k}", position=mast["pos"],
                                  orientation=sector_orientation(az, args.downtilt)))
    for i, p in enumerate(rx_xyz):
        scene.add(Receiver(f"r{i}", position=[float(v) for v in p]))

    t0 = time.time()
    paths = PathSolver()(scene, max_depth=args.max_depth,
                         samples_per_src=args.samples, los=True,
                         specular_reflection=True, refraction=True,
                         diffraction=args.diffraction,
                         edge_diffraction=args.edge_diffraction, seed=args.seed)
    dt = time.time() - t0

    a_r, a_i = paths.a
    a = np.asarray(a_r) ** 2 + np.asarray(a_i) ** 2      # [rx, 1, tx, 1, path]
    a = a[:, 0, :, 0, :]                                 # [rx, tx, path]
    valid = np.asarray(paths.valid)                      # [rx, tx, path]
    inter = np.asarray(paths.interactions)               # [depth, rx, tx, path]
    a = np.where(valid, a, 0.0)

    if analytic:
        g = sector_gains(np.asarray(paths.theta_t), np.asarray(paths.phi_t),
                         mast["azimuths"], args.tx_pattern)   # [rx, 1, path, sec]
        gain_sector = np.einsum("rtp,rtps->rs", a, g)         # [rx, sector]
    else:
        gain_sector = a.sum(axis=2)                           # [rx, sector]
    gain_total = gain_sector.sum(axis=1)
    n_paths = valid.any(axis=1).sum(axis=1)              # union over sources
    los = (valid & (inter == 0).all(axis=0)).any(axis=(1, 2))
    return {
        "gain_db": to_db(gain_total),
        "gain_db_per_sector": [to_db(gain_sector[:, k])
                               for k in range(gain_sector.shape[1])],
        "gain_db_best_sector": to_db(gain_sector.max(axis=1)),
        "los": [bool(v) for v in los],
        "n_paths": [int(v) for v in n_paths],
        "solve_s": dt,
    }


def to_db(x):
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, None, dtype=object)
    m = x > 0
    out[m] = np.round(10.0 * np.log10(x[m]), 3)
    return [None if v is None else float(v) for v in out]


# --------------------------------------------------------------------- plot
def plot(result, png):
    """Path gain along the walk, one panel per mast, three scene variants."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = np.asarray(result["walk"]["s"])
    sites = result["sites"]
    scenes = result["scenes"]
    colors = {"hybrid": "#1b6ca8", "osm": "#e07b39", "photo": "#3aa76d"}
    n = len(sites)
    fig, axes = plt.subplots(n, 1, figsize=(9, 2.3 * n + 0.8), sharex=True,
                             sharey=True)
    axes = np.atleast_1d(axes)
    # common y range so panels are comparable; a handful of near-zero-gain
    # samples fall off the bottom rather than flattening every other curve
    allg = [v for e in scenes.values() for r in e["sites"].values()
            for v in r["gain_db"] if v is not None]
    lo, hi = -160.0, float(np.ceil(max(allg))) + 3.0
    for ax, site in zip(axes, sites, strict=True):
        for name, entry in scenes.items():
            r = entry["sites"].get(site["site"])
            if r is None:
                continue
            g = np.array([np.nan if v is None else v for v in r["gain_db"]])
            ax.plot(s, g, lw=1.2, color=colors.get(name), label=name)
            los = np.array(r["los"])
            ax.plot(s[los], g[los], ".", ms=3.0, color=colors.get(name))
        d = np.hypot(np.asarray(result["walk"]["x"]) - site["pos"][0],
                     np.asarray(result["walk"]["y"]) - site["pos"][1])
        ax.set_title(f"{site['site'][:46]}  h={site['height']:.1f} m, "
                     f"{len(site['azimuths'])} sectors, "
                     f"walk range {d.min():.0f}-{d.max():.0f} m",
                     fontsize=9, loc="left")
        ax.set_ylabel("path gain [dB]")
        ax.set_ylim(lo, hi)
        ax.grid(alpha=0.25, lw=0.5)
    axes[0].legend(fontsize=8, ncol=3, loc="upper right")
    axes[-1].set_xlabel("walk arc length [m]   dots = LOS, gaps = no path found, "
                        f"curves clipped at {lo:.0f} dB")
    m = result["meta"]
    fig.suptitle(f"Scene ablation, {m['frequency_hz'] / 1e9:.1f} GHz, "
                 f"max_depth={m['max_depth']}, "
                 f"diffraction={m['diffraction']}, every {m['every']} m",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=150)
    print(f"[plot] -> {png}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    root = pathlib.Path(__file__).resolve().parent
    ap.add_argument("--root", default=str(root))
    ap.add_argument("--every", type=int, default=10,
                    help="keep every Nth 1 m walk sample (10 = smoke, 1 = full)")
    ap.add_argument("--n-sites", type=int, default=4,
                    help="how many masts to trace, strongest power_dbm_max first")
    ap.add_argument("--scenes", default=",".join(SCENES))
    ap.add_argument("--frequency", type=float, default=3.5e9)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--samples", type=int, default=1000000)
    ap.add_argument("--no-diffraction", dest="diffraction", action="store_false")
    ap.add_argument("--edge-diffraction", action="store_true")
    ap.add_argument("--tx-pattern", default="tr38901")
    ap.add_argument("--sector-mode", choices=("analytic", "traced"),
                    default="analytic",
                    help="analytic: one iso trace per mast, sector patterns applied "
                         "per path afterwards (exact for yaw-only, ~N_sector times "
                         "cheaper); traced: one transmitter per sector")
    ap.add_argument("--verify-sectors", action="store_true",
                    help="trace one mast both ways on a few samples and report the "
                         "worst per-sector disagreement, then exit")
    ap.add_argument("--downtilt", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--probe-radius", type=float, default=2.5,
                    help="disk radius for the min-over-disk street probe [m]")
    ap.add_argument("--eps-canopy", type=float, default=1.2)
    ap.add_argument("--no-vegetation-override", action="store_true")
    ap.add_argument("--out", default="data/ablation_smoke.json")
    ap.add_argument("--figure", default="figures/ablation_smoke.png")
    ap.add_argument("--plot-only", action="store_true",
                    help="redraw the figure from an existing --out json and exit")
    args = ap.parse_args()
    if args.plot_only:
        plot(json.loads((pathlib.Path(args.root) / args.out).read_text()),
             pathlib.Path(args.root) / args.figure)
        return
    if args.sector_mode == "analytic" and args.downtilt != 0.0:
        ap.error("a downtilt rotates the polarization basis, so the analytic "
                 "sector model no longer holds: use --sector-mode traced")

    from sionna.rt import load_scene

    root = pathlib.Path(args.root).resolve()
    data = root / "data"
    osm = json.loads((data / "osm_buildings.json").read_text())
    p0 = llh_to_ecef(osm["lat"], osm["lon"], 0.0)
    rot = enu_rotation(osm["lat"], osm["lon"])
    terrain = json.loads((data / "terrain_grid.json").read_text())["terrain"]
    decisions = json.loads((data / "decisions.json").read_text())
    blobs = [b for b in decisions["unmapped_blobs"] if b["guess"] == "vegetation"]

    veg = derive_vegetation(args.frequency, blobs, eps_r=args.eps_canopy)
    (data / "vegetation_material.json").write_text(json.dumps(veg, indent=1))
    print(f"[veg] gamma={veg['gamma_db_per_m']:.3f} dB/m  "
          f"eps'={veg['relative_permittivity']}  "
          f"sigma={veg['conductivity_s_per_m']:.4e} S/m  "
          f"thickness={veg['thickness_m']:.2f} m  "
          f"({veg['proxy_traversal_loss_db']:.1f} dB per traversal)", flush=True)

    walk_xy, walk_s = load_walk_xy(data / "walk.gpx", rot, p0)
    idx = np.arange(0, len(walk_xy), args.every)
    walk_xy, walk_s = walk_xy[idx], walk_s[idx]
    print(f"[walk] {len(idx)} samples over {walk_s[-1]:.0f} m "
          f"(every {args.every} m)", flush=True)

    masts = cluster_sites(json.loads((data / "sites.json").read_text()), rot, p0)
    print(f"[sites] {len(masts)} physical masts from "
          f"{len(json.loads((data / 'sites.json').read_text()))} records", flush=True)
    masts = masts[:args.n_sites]

    names = [n for n in args.scenes.split(",") if n]
    scenes = {}
    for n in names:
        sc = load_scene(str(root / "scenes" / n / "scene.xml"), merge_shapes=True)
        sc.frequency = args.frequency
        if not args.no_vegetation_override:
            k = apply_vegetation(sc, veg)
            if k:
                print(f"[{n}] canopy material overridden on {k} object(s)", flush=True)
        scenes[n] = sc

    # The mast is a real object at a real height, so its position is identical in
    # all three scenes: terrain plus the registered antenna height, raised if
    # needed to clear the photogrammetry roof it stands on. The OSM scene then
    # shows the mast floating over its own too-short roof, which is the naive
    # error being modelled, not a placement inconsistency.
    truth = scenes.get("photo") or scenes[names[0]]
    for m in masts:
        gz = terrain_z(terrain, m["x"], m["y"])
        surf = [probe_surface(sc, m["x"], m["y"]) for sc in
                (truth, scenes.get("hybrid")) if sc is not None]
        z = max([gz + m["height"]] + [s + 2.0 for s in surf if s is not None])
        m["pos"] = [m["x"], m["y"], z]
        m["ground_z"] = gz
        print(f"[site] {m['site'][:34]:34s} pos={[round(v, 1) for v in m['pos']]} "
              f"h={m['height']:.1f} sectors={len(m['azimuths'])} "
              f"az={[round(a) for a in m['azimuths']]}", flush=True)

    if args.verify_sectors:
        sc = scenes[names[0]]
        m = masts[0]
        n = min(12, len(walk_xy))
        z = probe_street(sc, walk_xy[:n], args.probe_radius)
        z = np.where(np.isnan(z), [terrain_z(terrain, float(x), float(y))
                                   for x, y in walk_xy[:n]], z)
        rx = np.column_stack([walk_xy[:n], z + RX_AGL])
        want = args.diffraction
        for diff in (False, want) if want else (False,):
            args.diffraction = diff
            got = {}
            for mode in ("analytic", "traced"):
                args.sector_mode = mode
                got[mode] = solve_site(sc, m, rx, args)
            worst, tot = 0.0, 0.0
            for k in range(len(m["azimuths"])):
                for a, b in zip(got["analytic"]["gain_db_per_sector"][k],
                                got["traced"]["gain_db_per_sector"][k], strict=True):
                    if a is None and b is None:
                        continue
                    worst = max(worst, 999.0 if (a is None or b is None)
                                else abs(a - b))
            for a, b in zip(got["analytic"]["gain_db"], got["traced"]["gain_db"],
                            strict=True):
                if a is not None and b is not None:
                    tot = max(tot, abs(a - b))
            print(f"[verify] diffraction={diff}  worst per-sector delta="
                  f"{worst:.4f} dB (999 = one mode found no path)  "
                  f"worst site-total delta={tot:.4f} dB  "
                  f"t_analytic={got['analytic']['solve_s']:.1f} s  "
                  f"t_traced={got['traced']['solve_s']:.1f} s")
        return

    result = {
        "meta": {
            "frequency_hz": args.frequency, "max_depth": args.max_depth,
            "samples_per_src": args.samples, "diffraction": args.diffraction,
            "edge_diffraction": args.edge_diffraction,
            "sector_mode": args.sector_mode,
            "every": args.every, "walk_step_m": WALK_STEP, "rx_agl_m": RX_AGL,
            "tx_pattern": args.tx_pattern, "rx_pattern": "iso",
            "polarization": "V", "downtilt_deg": args.downtilt, "seed": args.seed,
            "vegetation_override": not args.no_vegetation_override,
            "sector_power": "equal per sector, gains are per-sector channel gains "
                            "summed incoherently over sectors",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "vegetation": veg,
        "walk": {"x": [round(float(v), 3) for v in walk_xy[:, 0]],
                 "y": [round(float(v), 3) for v in walk_xy[:, 1]],
                 "s": [round(float(v), 3) for v in walk_s]},
        "sites": [{k: m[k] for k in
                   ("site", "members", "pos", "height", "ground_z", "azimuths",
                    "power_dbm_max", "n_antennas")} for m in masts],
        "scenes": {},
    }

    out = root / args.out
    for n in names:
        sc = scenes[n]
        surf = probe_street(sc, walk_xy, args.probe_radius)
        missed = int(np.isnan(surf).sum())
        surf = np.where(np.isnan(surf), [terrain_z(terrain, float(x), float(y))
                                         for x, y in walk_xy], surf)
        rx_z = surf + RX_AGL
        rx_xyz = np.column_stack([walk_xy, rx_z])
        print(f"[{n}] rx surface median={np.median(surf):.2f} m"
              + (f" ({missed} probes missed, fell back to terrain)" if missed else ""),
              flush=True)
        entry = {"rx_z": [round(float(v), 3) for v in rx_z], "sites": {}}
        for m in masts:
            r = solve_site(sc, m, rx_xyz, args)
            entry["sites"][m["site"]] = r
            g = np.array([v for v in r["gain_db"] if v is not None])
            print(f"[{n}] {m['site'][:28]:28s} {r['solve_s']:7.1f} s  "
                  f"median={np.median(g):7.1f} dB  los={sum(r['los'])}/"
                  f"{len(r['los'])}  covered={len(g)}/{len(r['gain_db'])}",
                  flush=True)
            result["scenes"][n] = entry
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=1))
        del scenes[n]
    print(f"[done] -> {out}")
    plot(result, root / args.figure)


if __name__ == "__main__":
    main()

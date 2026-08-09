"""Exactness study: inter-body reflection and polarization, tested on Thelonious.

Two questions, both run on the real phantom mesh (data/thelonious.stl):

1. Inter-body reflection. The monograph (sec:inter-body) bounds the recapture
   enhancement C(f) = 1/(1 - Rbar f) and argues it is negligible (<2% body
   averaged) via a self-compensation mechanism. We test that claim directly:
   compute the diffuse recapture fraction f = 1 - eta per triangle, the
   enhancement map C, the self-compensation eta*C vs eta, and a forward
   specular-bounce recapture sweep to look for local hotspots the body
   average hides.

2. Polarization. The exact law is Teff = Tavg + (q/2) DeltaT. Incoherent
   levels 0-6 use only Tavg (level 3) or a scalar q knob (level 4); the
   diffraction gate is polarization-blind in theory and code. We quantify
   how much the per-triangle TE/TM splitting DeltaT matters on the real body
   (it peaks at grazing, exactly where the shadow gate lives), and we develop
   the soft/hard creeping-wave split for a smooth convex body (Fock theory),
   the polarization signature the gate currently ignores.

Outputs results to results_exactness.json and figures to report/figures/.
Run with the project venv: .venv/bin/python studies/self_shadowing/exactness_study.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# scienceplots style from the theory scripts
_THEORY = Path(__file__).resolve().parents[2] / "theory" / "scripts"
sys.path.insert(0, str(_THEORY))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    import _plot_style

    _plot_style.apply_monograph_style()
    _HAVE_STYLE = True
except Exception:  # pragma: no cover
    _HAVE_STYLE = False

from aegis.geometry import occlusion as occ  # noqa: E402
from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.tissue import fresnel, n_complex  # noqa: E402

HERE = Path(__file__).resolve().parent
FIGDIR = HERE / "report" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)
STL = Path(__file__).resolve().parents[2] / "data" / "thelonious.stl"

RBAR = 0.46  # flux-weighted reflectance, monograph sec:inter-body

# Skin dielectric (eps_r, sigma) at three bands; n_complex from Cole-Cole-ish.
SKIN = {
    "3.5 GHz": (37.95, 1.49, 3.5e9),
    "28 GHz": (17.0, 25.0, 28e9),
    "60 GHz": (7.98, 36.4, 60e9),
}


def savefig(fig, name: str) -> None:
    fig.savefig(FIGDIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------
# Ray-casting helpers built on the production occlusion BVH
# --------------------------------------------------------------------------
def build_caster(mesh: BodyMesh):
    tri = occ._precompute_triangle_data(mesh.vertices)
    bvh, tri_order = occ.build_bvh(tri["tri_bmin"], tri["tri_bmax"], mesh.centroids, max_leaf=8)
    return tri, bvh, tri_order


def any_hit(origin, direction, tri, bvh, tri_order, ignore, t_min):
    return occ.ray_mesh_any_hit(
        float(origin[0]), float(origin[1]), float(origin[2]),
        float(direction[0]), float(direction[1]), float(direction[2]),
        bvh, tri_order,
        tri["tri_v0x"], tri["tri_v0y"], tri["tri_v0z"],
        tri["tri_e1x"], tri["tri_e1y"], tri["tri_e1z"],
        tri["tri_e2x"], tri["tri_e2y"], tri["tri_e2z"],
        ignore, t_min,
    )


# --------------------------------------------------------------------------
# Part 1: inter-body reflection
# --------------------------------------------------------------------------
def study_inter_body(mesh: BodyMesh, results: dict) -> None:
    print("[1] inter-body reflection ...")
    area = mesh.areas
    Atot = area.sum()

    # Diffuse recapture bound f = 1 - eta (cosine-weighted hemisphere blocked).
    eta = occ.compute_ambient_occlusion(mesh, n_rays=128, seed=0)
    f_diff = 1.0 - eta
    f_global = float((f_diff * area).sum() / Atot)
    C = 1.0 / (1.0 - RBAR * f_diff)
    C_global = float((C * area).sum() / Atot)
    # body-averaged absorbed-power enhancement weighted by direct exposure eta
    enh_global = float(((eta * C) * area).sum() / (eta * area).sum())

    print(f"    f_global (diffuse) = {f_global:.4f}  (monograph ~0.09)")
    print(f"    C_global (diffuse) = {C_global:.4f}  (monograph ~1.04)")
    print(f"    eta-weighted enhancement = {enh_global:.4f}")

    # Worst local concavity (diffuse bound).
    iw = int(np.argmax(f_diff))
    Cmax_diff = float(C[iw])
    print(f"    worst diffuse: f={f_diff[iw]:.3f}  C={Cmax_diff:.3f}")

    # Specular recapture: sweep incident directions, for each lit triangle cast
    # the mirror-reflected ray and test if it strikes the body. f_spec is the
    # lit-area-weighted recapture fraction; we keep the max over directions and
    # the worst per-triangle local enhancement using grazing reflectance.
    tri, bvh, tri_order = build_caster(mesh)
    n = mesh.normals
    c = mesh.centroids
    eps_o = 1e-6 * mesh.scale
    t_min = 10.0 * eps_o

    # azimuth sweep at horizontal incidence + a couple of elevations
    dirs = []
    for el in (0.0, np.deg2rad(20.0)):
        for az in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            dirs.append(np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)]))
    f_spec_list = []
    spec_hit_any = np.zeros(mesh.n_triangles, dtype=bool)
    for k in dirs:
        mu = -(n @ k)  # front-facing where mu>0
        lit = np.where(mu > 1e-3)[0]
        hit_area = 0.0
        lit_area = 0.0
        for i in lit:
            ni = n[i]
            r = k - 2.0 * (k @ ni) * ni  # specular reflection of incident ray
            origin = c[i] + eps_o * ni
            h = any_hit(origin, r, tri, bvh, tri_order, int(i), t_min)
            lit_area += area[i]
            if h:
                hit_area += area[i]
                spec_hit_any[i] = True
        f_spec_list.append(hit_area / max(lit_area, 1e-12))
    f_spec_max = float(np.max(f_spec_list))
    f_spec_mean = float(np.mean(f_spec_list))
    print(f"    f_spec mean={f_spec_mean:.4f} max={f_spec_max:.4f}  (monograph ~0.3*f_diff)")

    # Self-compensation figure: eta*C vs eta should track eta closely.
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 3.0))
    order = np.argsort(eta)
    ax[0].hist(f_diff, bins=60, weights=area, color="C0", alpha=0.85)
    ax[0].axvline(f_global, color="k", ls="--", lw=1, label=f"$f_{{global}}={f_global:.3f}$")
    ax[0].set_xlabel(r"diffuse recapture fraction $f=1-\eta$")
    ax[0].set_ylabel("body area (arb.)")
    ax[0].legend()
    ax[1].plot([0, 1], [0, 1], "k:", lw=1, label="no reflection")
    ax[1].scatter(eta[order][::20], (eta * C)[order][::20], s=2, alpha=0.3, color="C3")
    # specular-corrected curve (f_spec ~ 0.3 f_diff)
    C_spec = 1.0 / (1.0 - RBAR * 0.3 * f_diff)
    ax[1].scatter(eta[order][::20], (eta * C_spec)[order][::20], s=2, alpha=0.3, color="C0",
                  label="specular")
    ax[1].scatter([], [], s=8, color="C3", label="diffuse bound")
    ax[1].set_xlabel(r"direct exposure $\eta$")
    ax[1].set_ylabel(r"effective exposure $\eta\,C$")
    ax[1].legend(loc="upper left")
    fig.tight_layout()
    savefig(fig, "inter_body")

    results["inter_body"] = {
        "n_triangles": mesh.n_triangles,
        "total_area_m2": float(Atot),
        "f_global_diffuse": f_global,
        "C_global_diffuse": C_global,
        "eta_weighted_enhancement": enh_global,
        "worst_diffuse_f": float(f_diff[iw]),
        "worst_diffuse_C": Cmax_diff,
        "f_spec_mean": f_spec_mean,
        "f_spec_max": f_spec_max,
        "f_spec_over_f_diff": f_spec_mean / max(f_global, 1e-9),
        "Rbar": RBAR,
    }


# --------------------------------------------------------------------------
# Part 2: polarization at the absorbing surface
# --------------------------------------------------------------------------
def fresnel_TsTp(mu, n_tilde):
    """Power transmission T_s, T_p for incidence cosine mu and index n_tilde."""
    mu = np.asarray(mu, dtype=float)
    n2 = n_tilde**2
    xi = np.sqrt(n2 - (1.0 - mu**2))  # cos of refracted angle * n_tilde
    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)
    T_s = 1.0 - np.abs(r_s) ** 2
    T_p = 1.0 - np.abs(r_p) ** 2
    return T_s, T_p


def study_polarization(mesh: BodyMesh, results: dict) -> None:
    print("[2] polarization at the surface ...")
    n = mesh.normals
    area = mesh.areas

    # DeltaT(theta) curves for the three bands
    theta = np.linspace(0, np.deg2rad(89.5), 400)
    mu = np.cos(theta)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    band_dt75 = {}
    for band, (eps_r, sigma, f) in SKIN.items():
        nt = n_complex(eps_r, sigma, f)
        T_s, T_p = fresnel_TsTp(mu, nt)
        dT = T_p - T_s
        ax.plot(np.rad2deg(theta), dT, label=band)
        band_dt75[band] = float(np.interp(75.0, np.rad2deg(theta), dT))
    ax.set_xlabel(r"incidence angle $\theta$ (deg)")
    ax.set_ylabel(r"$\Delta T = T_p - T_s$")
    ax.legend()
    fig.tight_layout()
    savefig(fig, "deltaT_angle")
    print(f"    DeltaT at 75deg: {band_dt75}")

    # Integrated body absorption for a real fully-polarized plane wave.
    # Incident from +x (horizontal). Compare vertical vs horizontal polarization
    # vs the unpolarized (Tavg) assumption that levels 0-6 make.
    k = np.array([1.0, 0.0, 0.0])
    mu_r = -(n @ k)  # = cos of incidence angle, lit where >0
    lit = mu_r > 1e-4
    nt = n_complex(*SKIN["28 GHz"])
    T_s, T_p = fresnel_TsTp(np.clip(mu_r, 1e-4, 1.0), nt)
    T_avg = 0.5 * (T_s + T_p)

    # local TE/TM basis
    kxn = np.cross(np.broadcast_to(k, n.shape), n)
    e_s = kxn / np.clip(np.linalg.norm(kxn, axis=1, keepdims=True), 1e-12, None)
    e_p = np.cross(e_s, np.broadcast_to(k, n.shape))

    def integ(pol_hat):
        es2 = (e_s @ pol_hat) ** 2
        ep2 = (e_p @ pol_hat) ** 2
        T_eff = es2 * T_s + ep2 * T_p
        w = T_eff * mu_r * area
        return float(w[lit].sum())

    P_vert = integ(np.array([0.0, 0.0, 1.0]))
    P_horiz = integ(np.array([0.0, 1.0, 0.0]))
    P_unpol = float((T_avg * mu_r * area)[lit].sum())
    print(f"    integrated absorbed (arb): vert={P_vert:.4f} horiz={P_horiz:.4f} unpol={P_unpol:.4f}")
    print(f"    vert/unpol={P_vert / P_unpol:.4f}  horiz/unpol={P_horiz / P_unpol:.4f}")

    # per-triangle max deviation of T_eff from T_avg (vertical pol)
    es2 = (e_s @ np.array([0.0, 0.0, 1.0])) ** 2
    ep2 = (e_p @ np.array([0.0, 0.0, 1.0])) ** 2
    T_eff_v = es2 * T_s + ep2 * T_p
    dev = (T_eff_v - T_avg)[lit]
    grazing_area_frac = float(area[lit][mu_r[lit] < np.cos(np.deg2rad(60))].sum() / area[lit].sum())

    fig, ax = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax[0].hist(np.rad2deg(np.arccos(np.clip(mu_r[lit], 0, 1))), bins=50, weights=area[lit],
               color="C0", alpha=0.85)
    ax[0].axvline(60, color="k", ls="--", lw=1, label=r"$60^\circ$")
    ax[0].set_xlabel(r"incidence angle $\theta$ (deg)")
    ax[0].set_ylabel("lit area (arb.)")
    ax[0].legend()
    ax[1].hist(dev / T_avg[lit], bins=60, weights=area[lit], color="C3", alpha=0.85)
    ax[1].set_xlabel(r"$(T_{\rm eff}-T_{\rm avg})/T_{\rm avg}$, vertical pol")
    ax[1].set_ylabel("lit area (arb.)")
    fig.tight_layout()
    savefig(fig, "polarization_body")

    # Coronal-plane silhouette map: where on the body does polarization matter?
    # Wave from +x; project lit triangles onto (y, z) and colour by relative
    # T_eff deviation (vertical pol) and by incidence angle.
    cen = mesh.centroids[lit]
    rel = (dev / T_avg[lit])
    fig, ax = plt.subplots(1, 2, figsize=(5.6, 4.2))
    sc0 = ax[0].scatter(cen[:, 1], cen[:, 2], c=rel, s=2, cmap="RdBu_r",
                        vmin=-0.6, vmax=0.6)
    ax[0].set_title(r"$(T_{\rm eff}-T_{\rm avg})/T_{\rm avg}$")
    th = np.rad2deg(np.arccos(np.clip(mu_r[lit], 0, 1)))
    sc1 = ax[1].scatter(cen[:, 1], cen[:, 2], c=th, s=2, cmap="viridis", vmin=0, vmax=90)
    ax[1].set_title(r"incidence $\theta$ (deg)")
    for a in ax:
        a.set_aspect("equal")
        a.set_xlabel("y (m)")
        a.set_xticks([])
        a.set_yticks([])
    ax[0].set_ylabel("z (m)")
    fig.colorbar(sc0, ax=ax[0], fraction=0.046, pad=0.04)
    fig.colorbar(sc1, ax=ax[1], fraction=0.046, pad=0.04)
    fig.suptitle("Thelonious, vertical polarization, wave from $+x$, 28 GHz", fontsize=8)
    fig.tight_layout()
    savefig(fig, "polarization_bodymap")

    results["polarization"] = {
        "deltaT_at_75deg": band_dt75,
        "P_vert_over_unpol": P_vert / P_unpol,
        "P_horiz_over_unpol": P_horiz / P_unpol,
        "vert_minus_horiz_rel": (P_vert - P_horiz) / P_unpol,
        "max_local_Teff_dev_rel": float(np.max(np.abs(dev / T_avg[lit]))),
        "grazing_area_frac_gt60deg": grazing_area_frac,
    }


# --------------------------------------------------------------------------
# Part 3: soft/hard diffraction split for a smooth convex body (Fock)
# --------------------------------------------------------------------------
def study_soft_hard(results: dict) -> None:
    print("[3] soft/hard creeping-wave split (Fock) ...")
    # For a smooth convex perfect conductor, the deep-shadow surface field
    # decays as a sum of creeping-wave modes exp(-alpha_m * xi), where the
    # attenuation exponents are set by the zeros of the Airy function:
    #   soft (Dirichlet, E-pol):  q_m  = -zeros of Ai
    #   hard (Neumann,   H-pol):  q'_m = -zeros of Ai'
    # The leading attenuation per unit Fock arc length xi is
    #   alpha = (sqrt(3)/2) q_1   with q_1(soft)=2.3381, q_1(hard)=1.0188.
    # Hard creeping waves decay ~2.3x slower -> more leakage into shadow for
    # H-polarization. This is the polarization signature the scalar gate omits.
    from scipy.special import ai_zeros

    a_zeros, ap_zeros, _, _ = ai_zeros(3)
    q_soft = -a_zeros  # 2.3381, 4.0879, 5.5206
    q_hard = -ap_zeros  # 1.0188, 3.2482, 4.8201
    alpha_soft = (np.sqrt(3) / 2) * q_soft[0]
    alpha_hard = (np.sqrt(3) / 2) * q_hard[0]
    ratio = alpha_soft / alpha_hard
    print(f"    q1 soft={q_soft[0]:.4f} hard={q_hard[0]:.4f}  alpha ratio soft/hard={ratio:.3f}")

    # Fock arc-length parameter xi for a smooth body, with the geodesic shadow
    # depth s (m) past the terminator on a cylinder of radius R:
    #   xi = (k R / 2)^(1/3) * (s / R) = m(R) * (s/R),  m = (kR/2)^(1/3)
    # Show the soft vs hard surface-field magnitude vs shadow depth at 28 GHz
    # on a R=5cm limb.
    lam = 3e8 / 28e9
    kk = 2 * np.pi / lam
    R = 0.05
    m_fac = (kk * R / 2.0) ** (1.0 / 3.0)
    s = np.linspace(0, 0.04, 300)  # 0..4 cm into shadow
    xi = m_fac * (s / R)
    # leading-mode magnitude (normalized to 1 at terminator)
    U_soft = np.exp(-alpha_soft * xi)
    U_hard = np.exp(-alpha_hard * xi)

    fig, ax = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax[0].plot(np.rad2deg(s / R), 20 * np.log10(U_soft), label="soft (TE / E-pol)")
    ax[0].plot(np.rad2deg(s / R), 20 * np.log10(U_hard), label="hard (TM / H-pol)")
    ax[0].set_xlabel(r"geodesic depth into shadow (deg of arc)")
    ax[0].set_ylabel("surface field (dB)")
    ax[0].set_title(f"R={R*100:.0f} cm limb, 28 GHz")
    ax[0].legend()
    # polarization split (hard - soft) in dB grows with depth
    split = 20 * np.log10(U_hard) - 20 * np.log10(U_soft)
    ax[1].plot(np.rad2deg(s / R), split, color="C2")
    ax[1].set_xlabel(r"geodesic depth into shadow (deg of arc)")
    ax[1].set_ylabel("H$-$E polarization split (dB)")
    fig.tight_layout()
    savefig(fig, "soft_hard")

    # split at a representative 15 deg of shadow arc
    idx = int(np.argmin(np.abs(np.rad2deg(s / R) - 15.0)))
    results["soft_hard"] = {
        "q1_soft": float(q_soft[0]),
        "q1_hard": float(q_hard[0]),
        "alpha_soft": float(alpha_soft),
        "alpha_hard": float(alpha_hard),
        "alpha_ratio_soft_hard": float(ratio),
        "fock_m_factor_R5cm_28GHz": float(m_fac),
        "pol_split_dB_at_15deg_arc": float(split[idx]),
    }


def main() -> None:
    if not STL.exists():
        raise SystemExit(f"missing {STL}")
    mesh = BodyMesh.load(STL)
    print(f"loaded {mesh.name}: {mesh.n_triangles} triangles, area {mesh.total_area:.3f} m^2, "
          f"height {mesh.height:.2f} m")
    results: dict = {"phantom": mesh.name, "n_triangles": mesh.n_triangles}
    study_inter_body(mesh, results)
    study_polarization(mesh, results)
    study_soft_hard(results)
    out = HERE / "results_exactness.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

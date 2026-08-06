"""Controlled rank(Q) physics with the REAL AEGIS body channel.

Uses aegis.coherent.body_channel.compute_body_channel (real Fresnel t_s/t_p +
tissue depth coupling) and compute_exposure_operator, fed by the paper's own
far-field cluster path model (synthetic_paths_for_target + expand_paths_to_array):
each cluster is a plane wave shared across elements, with per-element phase
steering exp(+i k0 k_hat . offset_j).

Tests the orchestrator's DoF hypotheses on the REAL operator:
  E1  far-field rank structure vs n_clusters      (algebraic rank <= n_clusters?)
  E2  frequency invariance, lambda/2-SCALED array  (aperture ~ lambda)
  E3  frequency, FIXED physical aperture           (counterfactual)
  E4  distance sweep
  E5  aperture growth (lambda/2) vs oversampling (fixed aperture)
"""
import numpy as np
from aegis.geometry.mesh import load_stl_binary, triangle_areas
from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.tissue import dielectric

C_0 = 299792458.0
F_REF = 28e9  # reference for lambda/2 spacing


def metrics(Q):
    Q = 0.5 * (Q + Q.conj().T)
    lam = np.linalg.eigvalsh(Q).real[::-1]
    lam = np.maximum(lam, 0.0)
    tot = lam.sum()
    lmax = lam[0]
    cum = np.cumsum(lam) / max(tot, 1e-300)
    return dict(
        r90=int(np.searchsorted(cum, 0.90) + 1),
        r99=int(np.searchsorted(cum, 0.99) + 1),
        nr6=int((lam > 1e-6 * lmax).sum()),
        nr10=int((lam > 1e-10 * lmax).sum()),
        PR=float(tot**2 / (lam**2).sum()),
        stable=float(tot / lmax),
        top1=float(lmax / tot),
    )


def ura(M_side, spacing, center):
    """URA in the x = const plane (facing -x toward the body along +x)."""
    g = (np.arange(M_side) - (M_side - 1) / 2) * spacing
    yy, zz = np.meshgrid(g, g, indexing="ij")
    M = M_side * M_side
    return np.stack([np.full(M, center[0]), yy.ravel() + center[1], zz.ravel() + center[2]], axis=1)


def _basis(k):
    ref = np.array([0.0, 0.0, 1.0]) if abs(k[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(k, ref); e1 /= np.linalg.norm(e1)
    e2 = np.cross(k, e1); e2 /= np.linalg.norm(e2)
    return e1, e2


def far_field_paths(elem_pos, target, n_clusters, cone_deg, freq_hz, rng):
    """Paper's far-field cluster model. Returns k_hat (N,3), psi (N,3), elem (N,)."""
    M = len(elem_pos)
    ctr = elem_pos.mean(0)
    off = elem_pos - ctr
    k0 = 2 * np.pi * freq_hz / C_0
    los = target - ctr
    k_los = los / np.linalg.norm(los)
    e1, e2 = _basis(k_los)
    cone = np.deg2rad(cone_deg)
    K, PSI, EL = [], [], []
    for c in range(n_clusters):
        if c == 0:
            k = k_los.copy(); amp = 1.0
        else:
            ct = 1.0 - rng.uniform() * (1.0 - np.cos(cone))
            st = np.sqrt(max(0.0, 1 - ct * ct)); phi = rng.uniform(0, 2 * np.pi)
            k = ct * k_los + st * (np.cos(phi) * e1 + np.sin(phi) * e2)
            k /= np.linalg.norm(k); amp = rng.uniform(0.2, 0.6)
        ea, eb = _basis(k)
        th = rng.uniform(0, 2 * np.pi); ph = rng.uniform(0, 2 * np.pi); el = rng.uniform(0.7, 1.0)
        rp = np.cos(th) * ea + el * np.sin(th) * eb
        ip = -el * np.sin(th) * ea + np.cos(th) * eb
        pol = np.cos(ph) * rp + 1j * np.sin(ph) * ip
        pol /= np.linalg.norm(pol)
        phase = np.exp(1j * k0 * (off @ k))  # (M,) per-element steering
        for j in range(M):
            K.append(k); PSI.append(amp * pol * phase[j]); EL.append(j)
    return np.array(K), np.array(PSI, complex), np.array(EL, np.intp)


def build_Q(elem_pos, target, nrm, cen, areas, n_clusters, cone_deg, freq_hz, rng, tissue_freq_ghz=None):
    k_hat, psi, elem = far_field_paths(elem_pos, target, n_clusters, cone_deg, freq_hz, rng)
    fg = tissue_freq_ghz if tissue_freq_ghz is not None else freq_hz / 1e9
    nt, sigma = dielectric.skin_props(fg)
    G = compute_body_channel(nrm, cen, k_hat, psi, elem, nt, sigma, freq_hz, len(elem_pos))
    return compute_exposure_operator(np.asarray(G), areas), k_hat


def load_body(n_tri=2000):
    v, nrm, cen = load_stl_binary("data/duke.stl")
    areas = triangle_areas(v)
    idx = np.linspace(0, len(cen) - 1, n_tri, dtype=int)
    return nrm[idx], cen[idx], areas[idx]


def main():
    nrm, cen, areas = load_body(2000)
    bc = cen.mean(0)
    # array 5 m in front along +x; body faces +x or -x. Pick axis with most lit.
    target = np.array([bc[0], bc[1], bc[2] + 0.1])
    print(f"body: {len(cen)} tri, centroid={bc.round(2)}, extent={(cen.max(0)-cen.min(0)).round(2)}")

    # pick illumination axis by lit fraction at 28 GHz single LOS
    best = None
    for axis, sgn, name in [(0,-1,'-x'),(0,1,'+x'),(1,-1,'-y'),(1,1,'+y')]:
        cpos = bc.copy(); cpos[axis] += sgn * 5.0
        k = (target - cpos); k /= np.linalg.norm(k)
        mu = nrm @ (-k)
        lit = (mu > 0).mean()
        if best is None or lit > best[0]:
            best = (lit, axis, sgn, name, cpos.copy())
    lit, axis, sgn, name, _ = best
    print(f"illumination axis {name}: lit fraction {lit:.2f}")

    def array_center(D):
        c = bc.copy(); c[axis] += sgn * D; return c

    lam28 = C_0 / F_REF
    rng0 = lambda: np.random.default_rng(0)

    # ---- E1: far-field rank structure vs n_clusters (fixed array, 28 GHz, D=5m) ----
    print("\n=== E1: rank(Q) vs n_clusters  (16x16 array, lambda/2@28, D=5m, 28 GHz, cone=20deg) ===")
    print(f"    {'n_clus':>6} {'nr6':>5} {'nr10':>5} {'r90':>4} {'r99':>4} {'PR':>6} {'top1':>6}")
    M_side = 16
    ep = ura(M_side, lam28/2, array_center(5.0))
    tgt = target
    for nc in [1, 2, 4, 8, 16]:
        Q, _ = build_Q(ep, tgt, nrm, cen, areas, nc, 20.0, F_REF, np.random.default_rng(0))
        m = metrics(Q)
        print(f"    {nc:6d} {m['nr6']:5d} {m['nr10']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f} {m['top1']:6.3f}")

    # ---- E2: frequency invariance, lambda/2-SCALED array (aperture ~ lambda) ----
    print("\n=== E2: FREQ INVARIANCE, lambda/2-scaled array (aperture shrinks with lambda), 8 clusters, D=5m ===")
    print("    [tissue fixed at 28GHz to isolate geometry; array=16x16 lambda/2 at each freq]")
    print(f"    {'f_GHz':>6} {'aper_cm':>8} {'nr6':>5} {'r90':>4} {'r99':>4} {'PR':>6} {'top1':>6}")
    for fg in [8, 15, 28]:
        f = fg * 1e9; lam = C_0 / f
        ep = ura(16, lam/2, array_center(5.0))
        aper = 15 * lam/2 * 100
        Q, _ = build_Q(ep, tgt, nrm, cen, areas, 8, 20.0, f, np.random.default_rng(0), tissue_freq_ghz=28)
        m = metrics(Q)
        print(f"    {fg:6d} {aper:8.2f} {m['nr6']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f} {m['top1']:6.3f}")

    # ---- E3: frequency, FIXED physical aperture (counterfactual; matches studio) ----
    print("\n=== E3: FIXED physical aperture (lambda/2@28 held fixed), tissue fixed, 8 clusters, D=5m ===")
    print(f"    {'f_GHz':>6} {'aper_cm':>8} {'nr6':>5} {'r90':>4} {'r99':>4} {'PR':>6} {'top1':>6}")
    ep_fixed = ura(16, lam28/2, array_center(5.0))
    aper_fixed = 15 * lam28/2 * 100
    for fg in [8, 15, 28]:
        f = fg * 1e9
        Q, _ = build_Q(ep_fixed, tgt, nrm, cen, areas, 8, 20.0, f, np.random.default_rng(0), tissue_freq_ghz=28)
        m = metrics(Q)
        print(f"    {fg:6d} {aper_fixed:8.2f} {m['nr6']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f} {m['top1']:6.3f}")

    # ---- E4: distance sweep (fixed array lambda/2@28, 28 GHz, 8 clusters) ----
    print("\n=== E4: DISTANCE sweep (16x16 lambda/2@28, 28 GHz, 8 clusters, cone=20) ===")
    print(f"    {'D_m':>5} {'nr6':>5} {'r90':>4} {'r99':>4} {'PR':>6} {'top1':>6}")
    for D in [2.0, 5.0, 10.0, 20.0]:
        ep = ura(16, lam28/2, array_center(D))
        Q, _ = build_Q(ep, tgt, nrm, cen, areas, 8, 20.0, F_REF, np.random.default_rng(0))
        m = metrics(Q)
        print(f"    {D:5.1f} {m['nr6']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f} {m['top1']:6.3f}")

    # ---- E5a: aperture growth at lambda/2 (M grows, aperture grows) ----
    print("\n=== E5a: aperture growth, lambda/2@28 (M grows AND aperture grows), 28 GHz, 8 clusters ===")
    print(f"    {'M_side':>6} {'M':>5} {'aper_cm':>8} {'nr6':>5} {'r90':>4} {'r99':>4} {'PR':>6}")
    for Ms in [4, 8, 16, 24]:
        ep = ura(Ms, lam28/2, array_center(5.0))
        aper = (Ms-1) * lam28/2 * 100
        Q, _ = build_Q(ep, tgt, nrm, cen, areas, 8, 20.0, F_REF, np.random.default_rng(0))
        m = metrics(Q)
        print(f"    {Ms:6d} {Ms*Ms:5d} {aper:8.2f} {m['nr6']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f}")

    # ---- E5b: oversampling a FIXED aperture (M grows, aperture fixed) ----
    print("\n=== E5b: OVERSAMPLE fixed aperture (aperture=16*lambda/2@28 fixed, M grows), 28 GHz, 8 clusters ===")
    print(f"    {'M_side':>6} {'M':>5} {'spac/lam':>9} {'nr6':>5} {'r90':>4} {'r99':>4} {'PR':>6}")
    aper_m = 16 * lam28/2  # fixed physical aperture
    for Ms in [8, 16, 24, 32]:
        spac = aper_m / (Ms - 1)
        ep = ura(Ms, spac, array_center(5.0))
        Q, _ = build_Q(ep, tgt, nrm, cen, areas, 8, 20.0, F_REF, np.random.default_rng(0))
        m = metrics(Q)
        print(f"    {Ms:6d} {Ms*Ms:5d} {spac/lam28:9.3f} {m['nr6']:5d} {m['r90']:4d} {m['r99']:4d} {m['PR']:6.2f}")


if __name__ == "__main__":
    main()

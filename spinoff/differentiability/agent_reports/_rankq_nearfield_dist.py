"""Distance dependence of eff-rank in the NEAR-FIELD / geometric-illumination
regime (each element sees the body at its own angle; body-subtended angle
shrinks as 1/distance). This is the regime where the Bucci DoF ~ 1/d^2 lives.

NOTE: this is a toy near-field spherical-wave channel (fixed z-dipole, no
Fresnel), NOT AEGIS's far-field cluster model. It isolates the geometric
body-subtended-angle effect that the far-field model (which fixes the cluster
cone) cannot show. Units are CORRECT (mesh is already in meters; NO /1000).
"""
import numpy as np
from aegis.geometry.mesh import load_stl_binary, triangle_areas
C_0 = 299792458.0


def metrics(Q):
    lam = np.maximum(np.linalg.eigvalsh(Q).real[::-1], 0.0)
    tot = lam.sum(); cum = np.cumsum(lam) / tot
    return (int(np.searchsorted(cum, 0.90) + 1), int(np.searchsorted(cum, 0.99) + 1),
            float(tot**2 / (lam**2).sum()), float(lam[0] / tot))


def build_Q_nf(centroids, normals, areas, elem_pos, freq_hz):
    k0 = 2 * np.pi * freq_hz / C_0
    dvec = centroids[:, None, :] - elem_pos[None, :, :]
    d = np.linalg.norm(dvec, axis=-1)
    khat = dvec / d[..., None]
    amp = np.exp(-1j * k0 * d) / d
    mu = -np.einsum("tj,tmj->tm", normals, khat)
    lit = np.maximum(mu, 0.0)
    e = np.array([0.0, 0.0, 1.0])
    et = e[None, None, :] - khat * np.einsum("j,tmj->tm", e, khat)[..., None]
    et /= np.maximum(np.linalg.norm(et, axis=-1, keepdims=True), 1e-12)
    G = np.transpose((amp * lit)[..., None] * et, (0, 2, 1))  # (T,3,M)
    Q = np.einsum("t,tia,tib->ab", areas, G.conj(), G)
    return 0.5 * (Q + Q.conj().T)


def main():
    v, n, c = load_stl_binary("data/duke.stl")   # ALREADY METERS
    a = triangle_areas(v)
    idx = np.linspace(0, len(c) - 1, 4000, dtype=int)
    c, n, a = c[idx], n[idx], a[idx]
    bc = c.mean(0)
    f = 28e9; lam = C_0 / f
    print("duke meters, extent", (c.max(0) - c.min(0)).round(2), " (NO spurious /1000)")
    print("\n=== NEAR-FIELD distance sweep, 16x16 array lambda/2@28, single spherical wave/elem ===")
    print(f"    {'D_m':>5} {'body_subtend_deg':>16} {'r90':>4} {'r99':>4} {'PR':>6} {'top1':>6}")
    Ms = 16
    g = (np.arange(Ms) - (Ms - 1) / 2) * lam / 2
    yy, zz = np.meshgrid(g, g, indexing="ij")
    body_h = (c[:, 2].max() - c[:, 2].min())
    for D in [1.5, 3.0, 6.0, 12.0, 24.0]:
        ep = np.stack([np.full(Ms * Ms, bc[0] - D), yy.ravel() + bc[1], zz.ravel() + bc[2]], axis=1)
        Q = build_Q_nf(c, n, a, ep, f)
        r90, r99, pr, top1 = metrics(Q)
        subtend = np.rad2deg(2 * np.arctan(body_h / 2 / D))
        print(f"    {D:5.1f} {subtend:16.1f} {r90:4d} {r99:4d} {pr:6.2f} {top1:6.3f}")


if __name__ == "__main__":
    main()

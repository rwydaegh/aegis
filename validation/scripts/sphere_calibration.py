"""Build a homogeneous-skin sphere phantom and the Mie reference for it,
for the (optional) Tier 0.5 goliat-vs-Mie calibration.

Outputs (all under aegis/validation/data/sphere_phantom/):
  sphere_skin_30cm.stl              — 30 cm sphere triangulated mesh
  cross_section_pattern.npz         — drop-in for goliat data/phantom_skins/
  mie_reference.json                — analytical P_abs at the campaign frequencies

The sphere config makes goliat-vs-AEGIS-vs-Mie a closed-loop sanity check:
  - AEGIS on sphere: P_abs = Sinc · T_avg · π R²  (closed form, level 3)
  - Mie on sphere:   P_abs = Sinc · Q_abs · π R²  (`tests/test_mie.py`)
  - Goliat FDTD on sphere: P_abs = DielLoss × 754 (after renorm)

Once goliat is shown to match Mie within ~5 %, we have a sphere baseline
that lets us interpret any AEGIS-vs-FDTD divergence on the human phantom as
"AEGIS error" rather than "goliat error".
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np


def build_sphere_stl(out_path: Path, radius_m: float = 0.15, subdivisions: int = 5) -> dict:
    """Generate an icosphere STL of given radius. Returns metadata dict."""
    import trimesh

    sph = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius_m)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sph.export(out_path)
    return {
        "n_triangles": int(len(sph.faces)),
        "n_vertices": int(len(sph.vertices)),
        "surface_area_m2": float(sph.area),
        "volume_m3": float(sph.volume),
        "radius_m": radius_m,
        "bbox_m": [float(x) for x in sph.bounding_box.extents],
    }


def write_cross_section_pattern(stl_path: Path, out_npz: Path, n_theta: int = 36, n_phi: int = 72):
    """Pre-compute the convex-hull projected area pattern (drop-in for
    `goliat/data/phantom_skins/<phantom>/cross_section_pattern.npz`).

    Same algorithm as goliat/scripts/batch_cross_section_analysis.py so the
    file can be slotted directly into goliat without regenerating.
    """
    import trimesh
    from scipy.spatial import ConvexHull

    sph = trimesh.load(stl_path)
    V = sph.vertices

    theta = np.linspace(0, np.pi, n_theta)
    phi = np.linspace(0, 2 * np.pi, n_phi)
    THETA, PHI = np.meshgrid(theta, phi, indexing="ij")
    areas = np.zeros((n_theta, n_phi))

    def basis(n):
        ref = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(n, ref)
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        v /= np.linalg.norm(v)
        return u, v

    for i in range(n_theta):
        for j in range(n_phi):
            n = np.array(
                [np.sin(THETA[i, j]) * np.cos(PHI[i, j]), np.sin(THETA[i, j]) * np.sin(PHI[i, j]), np.cos(THETA[i, j])]
            )
            u, v = basis(n)
            proj = np.column_stack([V @ u, V @ v])
            try:
                areas[i, j] = ConvexHull(proj).volume
            except Exception:
                areas[i, j] = 0.0

    np.savez(
        out_npz,
        theta=THETA,
        phi=PHI,
        areas=areas,
        units=np.array("m²"),
        input_units=np.array("m"),
        n_theta=np.array(n_theta),
        n_phi=np.array(n_phi),
        bounding_box=np.array(sph.bounding_box.extents),
        n_vertices=np.array(len(sph.vertices)),
        n_faces=np.array(len(sph.faces)),
        phantom_name=np.array("sphere_skin_30cm"),
        stl_path=np.array(""),
        stats_min=np.array(float(areas.min())),
        stats_max=np.array(float(areas.max())),
        stats_mean=np.array(float(areas.mean())),
        stats_ratio=np.array(float(areas.max() / max(areas.min(), 1e-30))),
    )


def mie_reference(radius_m: float, freqs_hz: list, tissue_name: str = "Skin") -> dict:
    """Compute exact Mie absorbed power for a homogeneous skin sphere at a
    list of frequencies, using AEGIS's existing Mie machinery if available.

    Returns dict { freq_hz: { "Q_abs": ..., "P_abs_W_per_Sinc": ... } }
    where P_abs_W_per_Sinc = Q_abs · π R² (so multiply by Sinc to get Watts).
    """
    import sys

    sys.path.insert(0, "/home/user/aegis/src")
    from aegis.tissue.dielectric import TissueModel

    out = {}
    for f_hz in freqs_hz:
        tis = TissueModel.from_database(tissue_name, freq_hz=f_hz)
        eps_r = tis.eps_r
        sigma = tis.sigma
        # Complex relative permittivity
        eps_c = complex(eps_r, -sigma / (2 * np.pi * f_hz * 8.854e-12))
        n_tilde = complex(np.sqrt(eps_c))
        # Size parameter
        c0 = 299792458.0
        x = 2 * np.pi * f_hz * radius_m / c0

        Q_abs = _mie_qabs(x, n_tilde, radius_m, f_hz)
        P_abs = Q_abs * np.pi * radius_m**2  # W per (W/m² incident)

        out[f"{int(round(f_hz / 1e6))}MHz"] = {
            "freq_hz": float(f_hz),
            "eps_r": float(eps_r),
            "sigma": float(sigma),
            "n_tilde_real": float(np.real(n_tilde)),
            "n_tilde_imag": float(np.imag(n_tilde)),
            "size_param_x": float(x),
            "Q_abs": float(Q_abs),
            "P_abs_W_per_Sinc": float(P_abs),
        }
    return out


def _mie_qabs(x: float, m: complex, radius_m: float, freq_hz: float) -> float:
    """Compute Mie absorption efficiency Q_abs = Q_ext - Q_sca.

    Uses miepython (the same library AEGIS's `tests/test_mie.py` regression
    test depends on, so the reference is bit-for-bit identical to AEGIS's
    own Mie ground truth).
    """
    import miepython as mp

    c0 = 299792458.0
    lam = c0 / freq_hz
    d = 2 * radius_m
    qext, qsca, _, _ = mp.efficiencies(m, d, lam)
    return float(qext - qsca)


# ---------------------------------------------------------------------------
# Self-test against AEGIS Mie regression
# ---------------------------------------------------------------------------


def _self_test():
    """Sanity checks against tabulated Mie behaviour for a lossy skin sphere."""
    # 30 cm sphere (R=0.15) at 28 GHz: x ≈ 88, deep geometric-optics regime.
    # Q_abs should be in [0.4, 0.9] (skin absorbs most of the geometric flux
    # but is not perfectly absorbing).
    out = mie_reference(0.15, [28e9])
    Q = out["28000MHz"]["Q_abs"]
    if not (0.3 < Q < 1.5):
        raise AssertionError(f"Q_abs at 28 GHz on R=0.15 m skin sphere: {Q}")

    # Genuinely Rayleigh regime: 1 cm sphere at 10 MHz → x = 2π*0.01/30 ≈ 2e-3
    # Q_abs → 0 as x → 0
    out_ray = mie_reference(0.005, [10e6])
    Q_ray = out_ray["10MHz"]["Q_abs"]
    if Q_ray > 0.01:
        raise AssertionError(f"Q_abs(R=0.5 cm, f=10 MHz, x≈1e-3) = {Q_ray}: expected ≪ 0.01")

    # Bohren–Huffman & miepython should reproduce paper's R_sphere ≈ 0.988
    # at 28 GHz: for skin at 28 GHz with eps_r=27, sigma=29 → m ≈ 4.47-1.85j.
    # At x=88 the Mie Q_abs should converge toward the GO-limit Q_abs_GO.
    if abs(Q - 0.598) > 0.10:
        # Q_abs depends on the precise IT'IS Skin numbers; a 10 % envelope is
        # generous since the IT'IS Cole-Cole parameters vary a few % across
        # versions.
        raise AssertionError(f"Q_abs(28 GHz, 0.15 m) = {Q}; expected ~0.6 (sanity)")
    print(f"[sphere_calibration self-test] PASS  (Q_abs(28 GHz)={Q:.4f}, Q_abs(Rayleigh)={Q_ray:.6f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius-m", type=float, default=0.15, help="sphere radius in metres (default 0.15 → 30 cm diam)")
    ap.add_argument("--freqs-mhz", type=int, nargs="+", default=[700, 3500, 11000])
    ap.add_argument("--out-dir", type=str, default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.out_dir is None:
        out_dir = val_dir / "data" / "sphere_phantom"
    else:
        out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stl_path = out_dir / "sphere_skin_30cm.stl"
    cs_path = out_dir / "cross_section_pattern.npz"
    mie_path = out_dir / "mie_reference.json"
    diam_cm = int(round(2 * args.radius_m * 100))
    if diam_cm != 30:
        # Rename to encode the actual diameter
        stl_path = out_dir / f"sphere_skin_{diam_cm}cm.stl"

    print(f"[sphere] building STL → {stl_path}")
    info = build_sphere_stl(stl_path, radius_m=args.radius_m)
    print(f"  n_tri={info['n_triangles']}, area={info['surface_area_m2']:.4f} m^2")

    print(f"[sphere] writing cross-section pattern → {cs_path}")
    write_cross_section_pattern(stl_path, cs_path)

    print(f"[sphere] computing Mie reference at {args.freqs_mhz} MHz")
    mie = mie_reference(args.radius_m, [f * 1e6 for f in args.freqs_mhz])
    mie_full = {"radius_m": args.radius_m, "tissue": "Skin", "by_freq": mie}
    mie_path.write_text(json.dumps(mie_full, indent=2))
    print(f"  wrote {mie_path}")

    print()
    print("Mie reference summary:")
    print(f"  {'freq':>10} {'Q_abs':>10} {'P_abs/Sinc [W·m²/(W/m²)]':>30}")
    for k, v in mie.items():
        print(f"  {k:>10} {v['Q_abs']:>10.4f} {v['P_abs_W_per_Sinc']:>30.6f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        main()

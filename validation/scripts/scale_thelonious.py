"""Scale the thelonious phantom STL by a uniform factor for the
scaled-thelonious sanity-check campaign (Phase 1 of the validation plan).

The output is a triangulated skin mesh ready to drop into
`aegis/validation/data/scaled_phantoms/`.  Goliat then builds a fresh
voxel grid from the scaled mesh; on the AEGIS side the same STL is
loaded and analysed in the same way as the full-size phantom.

A `cross_section_pattern.npz` matching goliat's existing format is also
produced so the file can be slotted directly into
`goliat/data/phantom_skins/<phantom_name>/` without regenerating.

Usage:
    python scale_thelonious.py                    # 1/3 scale (default)
    python scale_thelonious.py --factor 0.5       # 1/2 scale
    python scale_thelonious.py --factor 0.25      # 1/4 scale

See `scaled_thelonious_proposal.md` for the framing — this is a
sanity check on Maxwell scale invariance for the AEGIS/FDTD chain,
not a high-frequency validation.
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np


def fraction_label(factor: float) -> str:
    """Convert a scale factor into a human-readable suffix.

    1/3 → 'one_third', 1/2 → 'one_half', 1/4 → 'one_quarter',
    otherwise '0p333' style fallback.
    """
    known = {
        1.0 / 3.0: "one_third",
        0.5: "one_half",
        0.25: "one_quarter",
        2.0 / 3.0: "two_thirds",
    }
    for f, label in known.items():
        if abs(factor - f) < 1e-6:
            return label
    return f"{factor:.4f}".replace(".", "p")


def scale_mesh(in_stl: Path, factor: float, recenter: bool) -> tuple:
    """Load `in_stl`, apply uniform scale `factor`, optionally translate
    so the bbox z range starts at the same minimum z as the input
    (keeps the feet on the same "floor" — useful when goliat builds
    its sim bbox below the body).

    Returns the scaled trimesh.
    """
    import trimesh

    m = trimesh.load(in_stl, force="mesh")
    orig_bounds = m.bounds.copy()
    orig_area = float(m.area)
    orig_volume = float(m.volume)

    # Uniform scale around the world origin first.
    m.apply_scale(factor)

    if recenter:
        # Keep the floor at the same z as the original (z_min unchanged).
        # Anchor the scaled body at the same x=0, y=0 column as the
        # original by translating x,y to the original mid-bbox.
        new_bounds = m.bounds
        dx = (orig_bounds[0, 0] + orig_bounds[1, 0]) * 0.5 - (new_bounds[0, 0] + new_bounds[1, 0]) * 0.5
        dy = (orig_bounds[0, 1] + orig_bounds[1, 1]) * 0.5 - (new_bounds[0, 1] + new_bounds[1, 1]) * 0.5
        dz = orig_bounds[0, 2] - new_bounds[0, 2]
        m.apply_translation([dx, dy, dz])

    new_bounds = m.bounds
    info = {
        "factor": factor,
        "orig_bounds": orig_bounds.tolist(),
        "orig_area_m2": orig_area,
        "orig_volume_m3": orig_volume,
        "new_bounds": new_bounds.tolist(),
        "new_area_m2": float(m.area),
        "new_volume_m3": float(m.volume),
        "new_extents_m": m.extents.tolist(),
        "n_triangles": int(len(m.faces)),
        "n_vertices": int(len(m.vertices)),
    }
    return m, info


def write_cross_section_pattern(
    mesh,
    out_npz: Path,
    phantom_name: str,
    n_theta: int = 36,
    n_phi: int = 72,
):
    """Pre-compute the convex-hull projected area pattern.  Same algorithm
    as `goliat/scripts/batch_cross_section_analysis.py` and
    `aegis/validation/scripts/sphere_calibration.py:write_cross_section_pattern`.
    """
    from scipy.spatial import ConvexHull

    V = mesh.vertices
    theta = np.linspace(0.0, np.pi, n_theta)
    phi = np.linspace(0.0, 2.0 * np.pi, n_phi)
    THETA, PHI = np.meshgrid(theta, phi, indexing="ij")
    areas = np.zeros((n_theta, n_phi))

    def basis(n):
        ref = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = np.cross(n, ref)
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        v /= np.linalg.norm(v)
        return u, v

    for i in range(n_theta):
        for j in range(n_phi):
            n = np.array(
                [
                    np.sin(THETA[i, j]) * np.cos(PHI[i, j]),
                    np.sin(THETA[i, j]) * np.sin(PHI[i, j]),
                    np.cos(THETA[i, j]),
                ]
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
        bounding_box=np.array(mesh.bounding_box.extents),
        n_vertices=np.array(len(mesh.vertices)),
        n_faces=np.array(len(mesh.faces)),
        phantom_name=np.array(phantom_name),
        stl_path=np.array(""),
        stats_min=np.array(float(areas.min())),
        stats_max=np.array(float(areas.max())),
        stats_mean=np.array(float(areas.mean())),
        stats_ratio=np.array(float(areas.max() / max(areas.min(), 1e-30))),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--factor", type=float, default=1.0 / 3.0, help="Uniform scale factor (default 1/3)")
    ap.add_argument(
        "--in-stl",
        type=str,
        default=None,
        help="Source STL (default: <repo>/data/thelonious.stl)",
    )
    ap.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Output directory (default: <repo>/validation/data/scaled_phantoms)",
    )
    ap.add_argument(
        "--no-recenter",
        action="store_true",
        help="Skip the recenter step (default scales then anchors floor to original z_min)",
    )
    ap.add_argument(
        "--no-cross-section",
        action="store_true",
        help="Skip cross_section_pattern.npz generation (slow on dense meshes)",
    )
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo = here.parent.parent
    if args.in_stl is None:
        in_stl = repo / "data" / "thelonious.stl"
    else:
        in_stl = Path(args.in_stl)
    if not in_stl.exists():
        raise FileNotFoundError(f"Input STL not found: {in_stl}")

    label = fraction_label(args.factor)
    phantom_name = f"thelonious_{label}"

    if args.out_dir is None:
        out_dir = repo / "validation" / "data" / "scaled_phantoms"
    else:
        out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_stl = out_dir / f"{phantom_name}.stl"
    out_npz = out_dir / f"{phantom_name}_cross_section_pattern.npz"

    print(f"[scale_thelonious] factor = {args.factor}  (label='{label}')")
    print(f"[scale_thelonious] reading {in_stl}")
    mesh, info = scale_mesh(in_stl, args.factor, recenter=not args.no_recenter)

    print(f"[scale_thelonious] writing scaled STL → {out_stl}")
    mesh.export(out_stl)

    if not args.no_cross_section:
        print(f"[scale_thelonious] writing cross-section pattern → {out_npz}")
        write_cross_section_pattern(mesh, out_npz, phantom_name=phantom_name)

    # Compact summary
    bb_extent = info["new_extents_m"]
    print()
    print("Scaled phantom summary")
    print(f"  name              : {phantom_name}")
    print(f"  factor            : {info['factor']:.6f}")
    print(f"  triangles         : {info['n_triangles']}")
    print(f"  surface area (m²) : {info['orig_area_m2']:.4f} → {info['new_area_m2']:.4f} ({info['new_area_m2']/info['orig_area_m2']:.4f}×)")
    print(f"  volume (m³)       : {info['orig_volume_m3']:.6f} → {info['new_volume_m3']:.6f} ({info['new_volume_m3']/info['orig_volume_m3']:.4f}×)")
    print(f"  bbox extent (m)   : {bb_extent[0]:.4f} × {bb_extent[1]:.4f} × {bb_extent[2]:.4f}")
    diam_cm = np.sqrt(bb_extent[0] ** 2 + bb_extent[1] ** 2) * 100.0
    print(f"  diag (x,y) (cm)   : {diam_cm:.2f}  (≈ characteristic d for x = πd/λ)")

    # Quick x = πd/λ map
    print()
    print("Estimated x = π d / λ at canonical proposal frequencies (d = diag x,y):")
    for f_mhz in (700, 2400, 5200, 10000, 28000):
        lam = 299.792458 / f_mhz  # metres per MHz
        x_param = np.pi * (diam_cm / 100.0) / lam
        print(f"  {f_mhz:>6} MHz : λ = {lam*100:6.2f} cm,  x = {x_param:6.2f}")


if __name__ == "__main__":
    main()

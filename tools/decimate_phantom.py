"""Curvature-adaptive decimation for AEGIS phantom STL meshes.

The eartha phantom ships at ~164k triangles, roughly 2.7x denser per unit
surface area than the other phantoms (duke/ella/thelonious cluster tightly at
~30k tris/m2). The over-tessellation is not uniform: large flat patches (torso,
thighs, back) carry far more triangles than they need, while small high-detail
features (ears, fingertips, nose) are where the budget should go.

This script runs a quality-weighted quadric edge-collapse decimation. The
per-vertex absolute curvature is written into the mesh quality channel and used
as a collapse weight, so the solver spends triangles where curvature is high and
flattens the broad low-curvature patches aggressively. The result keeps fine
features while bringing the global triangle budget in line with the other
phantoms.

Usage:
    python tools/decimate_phantom.py data/eartha.stl --target 60000 \
        --out data/eartha_decimated.stl
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pymeshlab as ml


def _topo(ms: ml.MeshSet) -> dict:
    g = ms.get_topological_measures()
    m = ms.current_mesh()
    return {
        "faces": m.face_number(),
        "verts": m.vertex_number(),
        "boundary_edges": g.get("boundary_edges"),
        "nm_edges": g.get("non_two_manifold_edges"),
        "nm_verts": g.get("non_two_manifold_vertices"),
        "components": g.get("connected_components_number"),
        "genus": g.get("genus"),
    }


def decimate(
    src: Path,
    out: Path,
    target_faces: int,
    quality_thr: float = 0.5,
    curvature: str = "abs",
    curv_power: float = 1.0,
) -> None:
    ms = ml.MeshSet()
    ms.load_new_mesh(str(src))

    # STL is a face soup: weld coincident vertices into a real manifold first,
    # otherwise edge collapses cannot cross triangle seams.
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_unreferenced_vertices()

    before = _topo(ms)
    print(f"loaded {src.name}: {before['faces']} faces, {before['verts']} verts")
    print(
        f"  watertight={before['boundary_edges'] == 0} "
        f"manifold={before['nm_edges'] == 0 and before['nm_verts'] == 0} "
        f"genus={before['genus']} components={before['components']}"
    )

    # Write absolute mean curvature into the per-vertex quality channel. ABS so
    # both convex tips (nose, fingers, ears) and any saddle/concave creases are
    # treated as high-detail and protected from collapse.
    curv_map = {
        "mean": "Mean Curvature",
        "gauss": "Gaussian Curvature",
        "rms": "RMS Curvature",
        "abs": "ABS Curvature",
    }
    ms.compute_scalar_by_discrete_curvature_per_vertex(curvaturetype=curv_map[curvature])

    # Clamp to the 1..99 percentile (a few sharp spikes should not dominate),
    # normalise to [0, 1] and raise to curv_power. The normalised weight feeds
    # qualityweight below: higher weight = more protected = finer triangles. With
    # weights in [0, 1], power 1 protects everything above the flats (widest
    # adaptive band, best flat/sharp contrast here); power > 1 crushes mid
    # curvature toward 0 so only razor edges survive (narrower, less contrast).
    m = ms.current_mesh()
    q = np.asarray(m.vertex_scalar_array())
    lo, hi = np.percentile(q, [1.0, 99.0])
    qn = np.clip((q - lo) / (hi - lo + 1e-9), 0.0, 1.0)
    weight = qn**curv_power * 1000.0 + 1.0

    # Rebuild the mesh carrying the emphasised weight in the quality channel
    # (the Mesh scalar array is read-only in place, so reconstruct it).
    ms.add_mesh(
        ml.Mesh(
            vertex_matrix=np.asarray(m.vertex_matrix()),
            face_matrix=np.asarray(m.face_matrix()),
            v_scalar_array=weight,
        )
    )

    print(f"  curvature ({curvature}) clamped [{lo:.2f}, {hi:.2f}], emphasis power {curv_power}")

    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=target_faces,
        qualitythr=quality_thr,  # 0..1, higher keeps better-shaped triangles
        preserveboundary=True,
        preservenormal=True,  # do not flip the surface
        preservetopology=True,  # keep genus/handles, no holes punched
        optimalplacement=True,  # place collapsed vertex at error-minimum
        planarquadric=False,  # let flat patches coarsen into big triangles
        qualityweight=True,  # weight error by curvature quality
        autoclean=True,
    )

    after = _topo(ms)
    print(f"decimated -> {after['faces']} faces, {after['verts']} verts")
    print(
        f"  watertight={after['boundary_edges'] == 0} "
        f"manifold={after['nm_edges'] == 0 and after['nm_verts'] == 0} "
        f"genus={after['genus']} components={after['components']}"
    )

    ms.save_current_mesh(str(out), binary=True)
    print(f"saved {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target", type=int, default=60000, help="target face count")
    ap.add_argument("--quality-thr", type=float, default=0.5)
    ap.add_argument("--curvature", choices=["mean", "gauss", "rms", "abs"], default="abs")
    ap.add_argument("--curv-power", type=float, default=1.0, help="curvature emphasis exponent")
    args = ap.parse_args()
    decimate(args.src, args.out, args.target, args.quality_thr, args.curvature, args.curv_power)


if __name__ == "__main__":
    main()

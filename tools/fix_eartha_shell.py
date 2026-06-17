"""Repair the eartha phantom: collapse its double-walled hollow shell into a
solid single-skin body, preserving the original outer-skin detail.

Diagnosis:
  - duke / ella / thelonious are solid single-skin bodies (one surface, outward
    normals, filled interior: an inward ray crosses the whole body, ~30-70 L).
  - eartha alone is a ~4 mm-thick hollow shell. Every cross-section is two
    concentric loops (outer skin + inner wall). Enclosed volume is only 4.2 L and
    its 2.03 m2 "area" is actually both walls. That doubles the triangle count
    and gives half the faces inward-pointing normals, which corrupts the Sab
    surface model and any self-shadow / occlusion pass.

Fix (detail-preserving): voxel-fill the shell into a solid and use that solid
ONLY as an inside/outside oracle. The inner wall is buried ~4 mm inside the
filled solid, the outer skin sits on its surface, so a face is "outer" iff its
centroid pushed a few mm along its normal lands outside the solid. Keeping those
ORIGINAL faces preserves the full ear / fingertip detail (a voxel remesh would
quantise it away). The fold seams left where the two walls meet are then closed
into a watertight body.

A separate curvature-adaptive decimation pass (tools/decimate_phantom.py) then
matches the phantom density and triangle-size distribution.

Usage:
    python tools/fix_eartha_shell.py data/eartha.stl --out data/eartha_solid.stl
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import numpy as np
import pymeshlab as ml
import trimesh
from scipy import ndimage


def _oracle(m: trimesh.Trimesh, pitch: float):
    """Filled-solid occupancy oracle. Returns inside(points) -> bool array."""
    vg = m.voxelized(pitch=pitch)
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(vg.matrix, iterations=1))
    inv = np.linalg.inv(vg.transform)
    shape = filled.shape

    def inside(pts: np.ndarray) -> np.ndarray:
        idx = np.round((np.c_[pts, np.ones(len(pts))] @ inv.T)[:, :3]).astype(int)
        ok = (idx >= 0).all(1) & (idx[:, 0] < shape[0]) & (idx[:, 1] < shape[1]) & (idx[:, 2] < shape[2])
        res = np.zeros(len(pts), bool)
        ii = idx[ok]
        res[ok] = filled[ii[:, 0], ii[:, 1], ii[:, 2]]
        return res

    return inside, filled.sum() * pitch**3


def fix_shell(src: Path, out: Path, pitch: float = 0.0015, push: float = 0.003) -> trimesh.Trimesh:
    m = trimesh.load(str(src))
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    print(f"input: {len(m.faces)} faces, area {m.area:.3f} m2, volume {m.volume * 1000:.1f} L")

    inside, vol = _oracle(m, pitch)
    print(f"oracle: filled solid {vol * 1000:.1f} L at {pitch * 1000:.1f} mm voxels")

    # A face is outer skin iff pushing its centroid outward leaves the solid.
    outer = ~inside(m.triangles_center + push * m.face_normals)
    print(f"classified {outer.sum()} outer / {(~outer).sum()} inner faces")
    skin = m.submesh([outer], append=True)

    # Close the fold seams (small holes where the two walls met) into a watertight
    # body. pymeshlab handles the bulk; trimesh mops up any final triangle hole.
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf:
        skin.export(tf.name)
        ms = ml.MeshSet()
        ms.load_new_mesh(tf.name)
        ms.meshing_remove_duplicate_vertices()
        ms.meshing_remove_unreferenced_vertices()
        ms.meshing_remove_connected_component_by_face_number(mincomponentsize=200)
        ms.meshing_repair_non_manifold_edges()
        ms.meshing_close_holes(maxholesize=300)
        ms.meshing_repair_non_manifold_edges()
        ms.save_current_mesh(tf.name, binary=True)
        skin = trimesh.load(tf.name)

    skin.merge_vertices()
    trimesh.repair.fill_holes(skin)
    trimesh.repair.fix_normals(skin)
    skin.export(str(out))
    genus = (2 - skin.euler_number) / 2
    print(
        f"output: {len(skin.faces)} faces, area {skin.area:.3f} m2, "
        f"volume {skin.volume * 1000:.1f} L, watertight {skin.is_watertight}, genus {genus:.0f}"
    )
    return skin


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pitch", type=float, default=0.0015, help="oracle voxel pitch (m)")
    ap.add_argument("--push", type=float, default=0.003, help="outward test distance (m)")
    args = ap.parse_args()
    fix_shell(args.src, args.out, args.pitch, args.push)


if __name__ == "__main__":
    main()

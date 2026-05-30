"""Export the Sionna Munich scene as a single small GLB for the
HTML RX picker. We crop to a bounding box around the BS so the
GLB stays under a few hundred KB and loads instantly in three.js.
"""
from __future__ import annotations
import glob, os
from pathlib import Path

import trimesh
import numpy as np

MESH_DIR = Path("/home/user/aegis/.venv/lib/python3.12/site-packages/"
                "sionna/rt/scenes/munich/meshes")
OUT = Path("/home/user/aegis/JSAC2/code/outputs/munich/munich_scene.glb")

# Crop box (world coords). BS at (8.5, 21.7, 35).
X_MIN, X_MAX = -120.0, 120.0
Y_MIN, Y_MAX = -100.0, 150.0


def main():
    files = sorted(glob.glob(str(MESH_DIR / "*.ply")))
    print(f"{len(files)} PLY files in scene")

    scene = trimesh.Scene()
    n_kept = 0
    n_v = 0
    for f in files:
        try:
            m = trimesh.load(f)
            if not isinstance(m, trimesh.Trimesh): continue
            b = m.bounds
            if b[1, 0] < X_MIN or b[0, 0] > X_MAX: continue
            if b[1, 1] < Y_MIN or b[0, 1] > Y_MAX: continue
            # Color by material guessed from file name
            name = Path(f).stem
            if "metal" in name.lower():
                color = [180, 180, 200, 255]
            elif "marble" in name.lower():
                color = [220, 215, 200, 255]
            elif "ground" in name.lower():
                color = [180, 175, 170, 255]
            else:
                color = [200, 195, 185, 255]
            m.visual.face_colors = color
            scene.add_geometry(m, node_name=name[:30])
            n_kept += 1
            n_v += m.vertices.shape[0]
        except Exception:
            continue

    print(f"  kept {n_kept} meshes, {n_v} verts total")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    glb = scene.export(file_type="glb")
    with open(OUT, "wb") as fh:
        fh.write(glb)
    print(f"  wrote {OUT}  ({len(glb)/1024:.1f} KB)")


if __name__ == "__main__":
    main()

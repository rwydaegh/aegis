"""Unified phantom processing: clean, repair, and density-normalise an STL.

Applies the same treatment to every phantom, doing only what each one needs:

  1. Weld the STL face soup, drop duplicate faces and tiny stray components,
     make normals outward-consistent.
  2. If the mesh is a double-walled shell (eartha), extract the outer skin and
     close it into a solid single-skin body (see tools/fix_eartha_shell.py).
  3. If it is over-dense relative to the house standard (~30k triangles/m2),
     run the curvature-adaptive decimation (see tools/decimate_phantom.py) to
     bring it in line while keeping ear / fingertip detail.

Healthy phantoms (duke, ella, thelonious) are already solid and at the house
density, so for them this is just the clean-up in step 1.

Usage:
    python tools/process_phantom.py data/eartha.stl --out data/eartha_processed.stl
    python tools/process_phantom.py --all          # process every data/*.stl phantom
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decimate_phantom import decimate  # noqa: E402
from fix_eartha_shell import fix_shell  # noqa: E402

HOUSE_DENSITY = 30000.0  # triangles per m2, the duke / ella / thelonious standard
PHANTOMS = ["thelonious", "duke", "ella", "eartha"]


def _is_double_walled(m: trimesh.Trimesh, n: int = 3000) -> bool:
    """True if most inward rays hit another wall within 8 mm (a thin shell)."""
    fi = np.random.default_rng(0).choice(len(m.faces), min(n, len(m.faces)), replace=False)
    o, nrm = m.triangles_center[fi], m.face_normals[fi]
    loc, ri, _ = m.ray.intersects_location(o - nrm * 1e-4, -nrm, multiple_hits=False)
    d = np.linalg.norm(loc - (o - nrm * 1e-4)[ri], axis=1)
    return float(np.mean(d < 0.008)) > 0.4


def _clean(m: trimesh.Trimesh) -> trimesh.Trimesh:
    """Weld, drop tiny stray components and degenerate faces, fix normals."""
    m.merge_vertices()
    m.update_faces(m.unique_faces() & m.nondegenerate_faces())
    comps = m.split(only_watertight=False)
    if len(comps) > 1:
        keep = max(len(c.faces) for c in comps)
        comps = [c for c in comps if len(c.faces) >= max(50, keep * 0.01)]
        m = trimesh.util.concatenate(comps) if len(comps) > 1 else comps[0]
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    return m


def process(src: Path, out: Path) -> None:
    print(f"\n=== {src.name} ===")
    m = _clean(trimesh.load(str(src)))
    print(f"cleaned: {len(m.faces)} faces, area {m.area:.3f} m2, watertight {m.is_watertight}")

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "stage.stl"

        if _is_double_walled(m):
            print("detected double-walled shell -> extracting solid outer skin")
            m.export(stage)
            m = fix_shell(stage, stage)  # writes and returns the solid skin
        else:
            m.export(stage)

        target = round(HOUSE_DENSITY * m.area)
        if len(m.faces) > 1.3 * target:
            print(f"over-dense ({len(m.faces) / m.area:.0f}/m2) -> decimating to {target} faces")
            decimate(stage, out, target_faces=target)
        else:
            print(f"already at house density ({len(m.faces) / m.area:.0f}/m2) -> cleaned only")
            m.export(out)

    final = trimesh.load(str(out))
    final.merge_vertices()
    print(
        f"-> {out.name}: {len(final.faces)} faces, {len(final.faces) / final.area:.0f}/m2, "
        f"watertight {final.is_watertight}, genus {(2 - final.euler_number) / 2:.0f}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path, nargs="?")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--all", action="store_true", help="process every phantom in data/")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    args = ap.parse_args()

    if args.all:
        for name in PHANTOMS:
            process(args.data_dir / f"{name}.stl", args.data_dir / f"{name}_processed.stl")
    else:
        if not args.src or not args.out:
            ap.error("provide SRC and --out, or use --all")
        process(args.src, args.out)


if __name__ == "__main__":
    main()

"""Bootstrap the SMPL-X model files from a license-gated zip download.

The SMPL-X parametric body model is hosted at https://smpl-x.is.tue.mpg.de/ and
distributed under a research license that requires registration. We cannot
ship the model files in this repository or fetch them anonymously from CI.

Workflow:

1.  Register at https://smpl-x.is.tue.mpg.de/, accept the EULA, download
    ``models_smplx_v1_1.zip`` (~200 MB, contains NEUTRAL/MALE/FEMALE in npz + pkl).
2.  Run ``python scripts/fetch_smplx.py /path/to/models_smplx_v1_1.zip``.
    The three NPZ files end up in ``~/.aegis/models/smplx/`` (or
    ``$AEGIS_MODELS_DIR/smplx/`` if set), which is where ``ParametricBody.load("smplx")``
    looks for them.

The script accepts either a zip archive or an already-extracted directory. It is
idempotent: re-running with the same source just overwrites the existing files.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

REQUIRED = ("SMPLX_NEUTRAL.npz", "SMPLX_FEMALE.npz", "SMPLX_MALE.npz")


def _default_dest() -> Path:
    root = os.environ.get("AEGIS_MODELS_DIR")
    if root:
        return Path(root).expanduser() / "smplx"
    return Path.home() / ".aegis" / "models" / "smplx"


def _extract_from_zip(zip_path: Path, dest: Path) -> list[str]:
    placed: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for fname in REQUIRED:
            match = next((n for n in names if Path(n).name == fname), None)
            if match is None:
                raise FileNotFoundError(f"{fname} not in {zip_path}; got {names[:5]}...")
            with zf.open(match) as src, (dest / fname).open("wb") as dst:
                shutil.copyfileobj(src, dst)
            placed.append(fname)
    return placed


def _copy_from_dir(src_dir: Path, dest: Path) -> list[str]:
    placed: list[str] = []
    for fname in REQUIRED:
        candidates = list(src_dir.rglob(fname))
        if not candidates:
            raise FileNotFoundError(f"{fname} not under {src_dir}")
        shutil.copy2(candidates[0], dest / fname)
        placed.append(fname)
    return placed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("source", type=Path, help="Path to models_smplx_v1_1.zip or extracted dir")
    p.add_argument("--dest", type=Path, default=None, help="Override destination dir (default: ~/.aegis/models/smplx)")
    args = p.parse_args(argv)

    dest = args.dest if args.dest else _default_dest()
    dest.mkdir(parents=True, exist_ok=True)

    src = args.source.expanduser().resolve()
    if not src.exists():
        print(f"error: {src} does not exist", file=sys.stderr)
        return 2

    if src.is_dir():
        placed = _copy_from_dir(src, dest)
    elif zipfile.is_zipfile(src):
        placed = _extract_from_zip(src, dest)
    else:
        print(f"error: {src} is neither a zip archive nor a directory", file=sys.stderr)
        return 2

    print(f"Installed {len(placed)} SMPL-X model files into {dest}:")
    for name in placed:
        size = (dest / name).stat().st_size / 1e6
        print(f"  {name}  ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

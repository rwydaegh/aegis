#!/usr/bin/env python3
"""Sync markdown tutorials to numbered Jupyter notebooks.

The markdown files in docs/tutorials/ are the source of truth.
This script converts them to .ipynb files in notebooks/ using Jupytext.

Usage:
    python tools/sync_notebooks.py          # regenerate all notebooks
    python tools/sync_notebooks.py --check  # verify notebooks are up to date
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TUTORIALS = [
    ("quickstart.md", "01_quickstart.ipynb"),
    ("fidelity_levels.md", "02_fidelity_levels.ipynb"),
    ("tissue_and_fresnel.md", "03_tissue_and_fresnel.ipynb"),
    ("compliance.md", "04_compliance.ipynb"),
    ("coherent_mimo.md", "05_coherent_mimo.ipynb"),
]

SRC_DIR = REPO / "docs" / "tutorials"
DST_DIR = REPO / "notebooks"


def sync():
    DST_DIR.mkdir(exist_ok=True)
    for md_name, nb_name in TUTORIALS:
        src = SRC_DIR / md_name
        dst = DST_DIR / nb_name
        if not src.exists():
            print(f"  SKIP {md_name} (not found)")
            continue
        subprocess.run(
            [sys.executable, "-m", "jupytext", "--to", "notebook", "-o", str(dst), str(src)],
            check=True,
        )
        print(f"  {md_name} -> {nb_name}")


def check():
    """Verify notebooks match their source markdown."""
    import tempfile

    ok = True
    for md_name, nb_name in TUTORIALS:
        src = SRC_DIR / md_name
        dst = DST_DIR / nb_name
        if not src.exists():
            continue
        if not dst.exists():
            print(f"  MISSING {nb_name}")
            ok = False
            continue
        with tempfile.NamedTemporaryFile(suffix=".ipynb") as tmp:
            subprocess.run(
                ["jupytext", "--to", "notebook", "-o", tmp.name, str(src)],
                check=True,
                capture_output=True,
            )
            expected = Path(tmp.name).read_text()
            actual = dst.read_text()
            if expected != actual:
                print(f"  STALE {nb_name}")
                ok = False
            else:
                print(f"  OK    {nb_name}")
    return ok


if __name__ == "__main__":
    if "--check" in sys.argv:
        print("Checking notebooks are up to date...")
        if not check():
            print("\nSome notebooks are stale. Run: python tools/sync_notebooks.py")
            sys.exit(1)
        print("\nAll notebooks up to date.")
    else:
        print("Syncing tutorials -> notebooks...")
        sync()
        print("\nDone.")

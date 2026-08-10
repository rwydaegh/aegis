"""Export the coauthor-facing v4 snapshot from the canonical sources."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def export_v4(
    main_root: Path,
    si_source: Path,
    output_dir: Path,
    papermaker_project: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(papermaker_project),
            "papermaker",
            "assemble",
            str(main_root),
            "--out",
            str(output_dir / "paper.tex"),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    shutil.copy2(si_source, output_dir / "paper_SI.tex")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, default=REPO_ROOT / "main")
    parser.add_argument("--si-source", type=Path, default=REPO_ROOT / "paper_SI.tex")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "v4_to_coauthors",
    )
    parser.add_argument(
        "--papermaker-project",
        type=Path,
        default=Path("/home/user/PaperMaker9000"),
    )
    args = parser.parse_args()
    export_v4(
        args.main_root.resolve(),
        args.si_source.resolve(),
        args.output_dir.resolve(),
        args.papermaker_project.resolve(),
    )


if __name__ == "__main__":
    main()

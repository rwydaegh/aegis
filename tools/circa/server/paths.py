"""All path constants for circa, derived from a paper directory."""

from pathlib import Path


def workdir(paper_dir: Path) -> Path:
    return paper_dir / ".circa"


def pidfile(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "pidfile"


def style_md(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "style.md"


def snapshots_dir(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "snapshots"


def snapshots_ledger(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "snapshots.jsonl"


def hunks_dir(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "hunks"


def annotations_log(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "annotations.jsonl"


def parser_errors_log(paper_dir: Path) -> Path:
    return workdir(paper_dir) / "parser_errors.log"


def ensure_workdir(paper_dir: Path) -> None:
    workdir(paper_dir).mkdir(exist_ok=True)
    snapshots_dir(paper_dir).mkdir(exist_ok=True)
    hunks_dir(paper_dir).mkdir(exist_ok=True)

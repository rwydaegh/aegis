"""Report the independent public and private repository states."""

import subprocess
from pathlib import Path


def show(name: str, path: Path) -> None:
    print(f"{name}: {path}", flush=True)
    if not (path / ".git").exists():
        print("  Not checked out here")
        return
    result = subprocess.run(["git", "status", "--short", "--branch"], cwd=path, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{upstream}"], cwd=path, capture_output=True, text=True
    )
    if upstream.returncode:
        print("  No upstream configured", flush=True)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    show("Public", root)
    show("Private", root / "private")
    papers = root / "private" / "papers"
    if papers.is_dir():
        for project in sorted(papers.iterdir()):
            if (project / ".git").exists():
                show(project.name, project)

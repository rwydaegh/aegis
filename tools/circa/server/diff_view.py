from pathlib import Path


def current_diff(paper_dir: Path, batch_id: str) -> str:
    """Return unified diff of current paper.tex vs the snapshot for batch_id. Stubbed in Task 12; expanded in Task 13."""
    import difflib
    from . import paths

    snap = paths.snapshots_dir(paper_dir) / f"{batch_id}.tex"
    if not snap.exists():
        return ""
    pre = snap.read_text().splitlines(keepends=True)
    post = (paper_dir / "paper.tex").read_text().splitlines(keepends=True)
    return "".join(difflib.unified_diff(pre, post, fromfile="a/paper.tex", tofile="b/paper.tex", n=3))

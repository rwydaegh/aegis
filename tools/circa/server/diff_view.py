import difflib
from typing import Optional


def current_diff(paper_dir, batch_id: Optional[str] = None, last_built_tex: Optional[str] = None) -> str:
    """Diff current paper.tex against last_built_tex (preferred) or the batch snapshot."""
    if last_built_tex is not None:
        post = (paper_dir / "paper.tex").read_text().splitlines(keepends=True)
        pre = last_built_tex.splitlines(keepends=True)
    else:
        from . import paths

        snap = paths.snapshots_dir(paper_dir) / f"{batch_id}.tex"
        if not snap.exists():
            return ""
        pre = snap.read_text().splitlines(keepends=True)
        post = (paper_dir / "paper.tex").read_text().splitlines(keepends=True)
    return "".join(difflib.unified_diff(pre, post, fromfile="a/paper.tex", tofile="b/paper.tex", n=3))

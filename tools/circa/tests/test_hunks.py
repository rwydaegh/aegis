from pathlib import Path

import pytest

from server import paths
from server.hunks import HunkManager


PRE = """\\documentclass{article}
\\begin{document}
Paragraph one is here.
Filler one.
Filler two.
Filler three.
Filler four.
Filler five.
Filler six.
Filler seven.
Filler eight.
Filler nine.
Paragraph eleven is here.
End of doc.
\\end{document}
"""

POST_ABC_ONLY = """\\documentclass{article}
\\begin{document}
% [circa:abc:begin]
Paragraph ONE is rephrased.
% [circa:abc:end]
Filler one.
Filler two.
Filler three.
Filler four.
Filler five.
Filler six.
Filler seven.
Filler eight.
Filler nine.
Paragraph eleven is here.
End of doc.
\\end{document}
"""

POST_ABC_AND_DEF = """\\documentclass{article}
\\begin{document}
% [circa:abc:begin]
Paragraph ONE is rephrased.
% [circa:abc:end]
Filler one.
Filler two.
Filler three.
Filler four.
Filler five.
Filler six.
Filler seven.
Filler eight.
Filler nine.
% [circa:def:begin]
Paragraph ELEVEN is rephrased.
% [circa:def:end]
End of doc.
\\end{document}
"""

POST_MERGED = """\\documentclass{article}
\\begin{document}
% [circa:abc+def:begin]
Paragraphs one and eleven merged into one block.
% [circa:abc+def:end]
Filler two.
Filler three.
Filler four.
Filler five.
Filler six.
Filler seven.
Filler eight.
Filler nine.
End of doc.
\\end{document}
"""


def test_extract_one_hunk(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_ONLY)
    h = HunkManager(paper_dir).extract_for_batch("b1", ["abc"])
    assert "abc" in h
    assert "% [circa:abc:begin]" in h["abc"]


def test_extract_two_independent_hunks(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_AND_DEF)
    h = HunkManager(paper_dir).extract_for_batch("b1", ["abc", "def"])
    assert "abc" in h and "def" in h
    assert h["abc"] != h["def"]


def test_merged_fence_assigns_same_hunk_to_both(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_MERGED)
    h = HunkManager(paper_dir).extract_for_batch("b1", ["abc", "def"])
    assert h["abc"] == h["def"]


def test_persist_and_load(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_ONLY)
    mgr = HunkManager(paper_dir)
    mgr.persist_for_batch("b1", ["abc"])
    assert mgr.load_hunk("abc") is not None


def test_apply_reverse_restores_pre(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_ONLY)
    mgr = HunkManager(paper_dir)
    mgr.persist_for_batch("b1", ["abc"])
    mgr.apply_reverse("abc")
    assert (paper_dir / "paper.tex").read_text() == PRE


def test_reject_succeeds_after_unrelated_subsequent_batch(paper_dir: Path):
    """The spec's central safety case: batch1 edits paragraph 1, batch2 edits paragraph 11 (non-overlapping).
    Rejecting batch1's annotation should still succeed because context lines around batch1's hunk are intact.
    With n=3 context and 9 unchanged filler lines between the edits, the abc hunk's trailing context
    (Filler one/two/three) does NOT overlap with the def hunk's region. This is the reason we DON'T pass
    --unidiff-zero."""
    paths.ensure_workdir(paper_dir)
    # Batch 1: snapshot PRE, paper -> POST_ABC_ONLY, persist abc.
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_ONLY)
    mgr = HunkManager(paper_dir)
    mgr.persist_for_batch("b1", ["abc"])
    # Batch 2 lands afterwards: paper now has both fences (POST_ABC_AND_DEF).
    (paper_dir / "paper.tex").write_text(POST_ABC_AND_DEF)
    # Reject abc: should remove only abc's edit, leaving def's intact.
    mgr.apply_reverse("abc")
    text = (paper_dir / "paper.tex").read_text()
    assert "% [circa:abc:begin]" not in text
    assert "Paragraph one is here." in text  # restored
    assert "% [circa:def:begin]" in text  # untouched
    assert "Paragraph ELEVEN is rephrased." in text


def test_reject_refuses_when_context_destroyed(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    (paths.snapshots_dir(paper_dir) / "b1.tex").write_text(PRE)
    (paper_dir / "paper.tex").write_text(POST_ABC_ONLY)
    mgr = HunkManager(paper_dir)
    mgr.persist_for_batch("b1", ["abc"])
    (paper_dir / "paper.tex").write_text("totally different content")
    with pytest.raises(RuntimeError, match="conflict"):
        mgr.apply_reverse("abc")

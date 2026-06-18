"""Circa honours a non-default tex filename (e.g. main_circa.tex) end to end.

The server hardcoded `paper.tex` historically; for PaperMaker papers the working
copy is assembled under a different name and ported back to the leaves later.
These tests pin the filename threading through the snapshot, hunk, diff, build,
and prompt layers so a renamed working copy stays self-consistent.
"""

import shutil
from pathlib import Path

from server import paths
from server.claude_session import _build_system_prompt
from server.diff_view import current_diff
from server.hunks import HunkManager
from server.pdf_builder import PdfBuilder
from server.snapshots import SnapshotManager

TEX = "main_circa.tex"


def _renamed_paper_dir(paper_dir: Path) -> Path:
    shutil.move(str(paper_dir / "paper.tex"), str(paper_dir / TEX))
    return paper_dir


def test_snapshot_targets_named_tex(paper_dir: Path):
    _renamed_paper_dir(paper_dir)
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir, tex_name=TEX)
    mgr.take_snapshot("b1")
    snap = paths.snapshots_dir(paper_dir) / "b1.tex"
    assert snap.read_text() == (paper_dir / TEX).read_text()


def test_revert_restores_named_tex(paper_dir: Path):
    _renamed_paper_dir(paper_dir)
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir, tex_name=TEX)
    original = (paper_dir / TEX).read_text()
    mgr.take_snapshot("b1")
    (paper_dir / TEX).write_text("clobbered")
    mgr.record_post_sha("b1")
    mgr.revert("b1", force=True)
    assert (paper_dir / TEX).read_text() == original


def test_hunk_diff_headers_use_named_tex(paper_dir: Path):
    _renamed_paper_dir(paper_dir)
    paths.ensure_workdir(paper_dir)
    snap_mgr = SnapshotManager(paper_dir, tex_name=TEX)
    snap_mgr.take_snapshot("b1")
    tex = paper_dir / TEX
    tex.write_text(tex.read_text() + "\n% [circa:a1:begin]\nnew line\n% [circa:a1:end]\n")
    hunks = HunkManager(paper_dir, tex_name=TEX).extract_for_batch("b1", ["a1"])
    assert "a1" in hunks
    # git apply -R needs the real filename in the diff headers to locate the file.
    assert f"a/{TEX}" in hunks["a1"]
    assert f"b/{TEX}" in hunks["a1"]


def test_current_diff_reads_named_tex(paper_dir: Path):
    _renamed_paper_dir(paper_dir)
    (paper_dir / TEX).write_text("after\n")
    diff = current_diff(paper_dir, last_built_tex="before\n", tex_name=TEX)
    assert f"a/{TEX}" in diff
    assert "-before" in diff and "+after" in diff


def test_pdf_builder_uses_named_tex():
    builder = PdfBuilder(Path("/tmp"), tex_name=TEX)
    assert builder.tex_name == TEX
    assert builder.stem == "main_circa"


def test_system_prompt_names_the_tex_file(paper_dir: Path):
    prompt = _build_system_prompt(
        paper_dir, "outline", pdfcomment_enabled=False, tells_path=None, tex_name=TEX
    )
    assert TEX in prompt
    assert "editor for main_circa.tex" in prompt


def test_default_tex_name_is_paper_tex(paper_dir: Path):
    # Backward compatibility: omitting tex_name keeps the historical paper.tex.
    assert SnapshotManager(paper_dir).paper_tex.name == "paper.tex"
    assert PdfBuilder(paper_dir).tex_name == "paper.tex"

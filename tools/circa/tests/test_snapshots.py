import json
from pathlib import Path

import pytest

from server import paths
from server.snapshots import SnapshotManager


def test_take_snapshot_copies_paper_tex(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir)
    mgr.take_snapshot("b1")
    snap = paths.snapshots_dir(paper_dir) / "b1.tex"
    assert snap.read_text() == (paper_dir / "paper.tex").read_text()


def test_record_post_sha(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir)
    mgr.take_snapshot("b1")
    (paper_dir / "paper.tex").write_text("modified")
    mgr.record_post_sha("b1")
    entries = [json.loads(l) for l in paths.snapshots_ledger(paper_dir).read_text().splitlines() if l]  # noqa: E741
    assert entries[-1]["sha256_post"] is not None
    assert entries[-1]["sha256_post"] != entries[-1]["sha256_pre"]


def test_revert_restores_when_sha_matches(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir)
    original = (paper_dir / "paper.tex").read_text()
    mgr.take_snapshot("b1")
    (paper_dir / "paper.tex").write_text("CLAUDE EDIT")
    mgr.record_post_sha("b1")
    mgr.revert("b1", force=False)
    assert (paper_dir / "paper.tex").read_text() == original


def test_revert_refuses_when_user_modified(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir)
    mgr.take_snapshot("b1")
    (paper_dir / "paper.tex").write_text("CLAUDE EDIT")
    mgr.record_post_sha("b1")
    (paper_dir / "paper.tex").write_text("USER HAND EDIT")
    with pytest.raises(RuntimeError, match="differs"):
        mgr.revert("b1", force=False)


def test_revert_force(paper_dir: Path):
    paths.ensure_workdir(paper_dir)
    mgr = SnapshotManager(paper_dir)
    original = (paper_dir / "paper.tex").read_text()
    mgr.take_snapshot("b1")
    (paper_dir / "paper.tex").write_text("USER HAND EDIT")
    mgr.revert("b1", force=True)
    assert (paper_dir / "paper.tex").read_text() == original

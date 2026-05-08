import os
from pathlib import Path

import pytest

from server import paths
from circa_cli import (
    bootstrap_workdir,
    insert_pdfcomment_package,
    write_pidfile,
    PidfileBusy,
)


def test_bootstrap_creates_workdir_subdirs(paper_dir: Path):
    bootstrap_workdir(paper_dir)
    assert paths.snapshots_dir(paper_dir).exists()
    assert paths.hunks_dir(paper_dir).exists()


def test_style_md_template_copied_first_run(paper_dir: Path):
    bootstrap_workdir(paper_dir)
    assert paths.style_md(paper_dir).exists()


def test_style_md_not_overwritten(paper_dir: Path):
    bootstrap_workdir(paper_dir)
    paths.style_md(paper_dir).write_text("custom")
    bootstrap_workdir(paper_dir)
    assert paths.style_md(paper_dir).read_text() == "custom"


def test_pdfcomment_inserted_after_hyperref(paper_dir: Path):
    inserted = insert_pdfcomment_package(paper_dir / "paper.tex")
    assert inserted is True
    text = (paper_dir / "paper.tex").read_text()
    assert "\\usepackage[author={circa}]{pdfcomment}" in text
    assert text.find("\\usepackage[author={circa}]{pdfcomment}") > text.find("\\usepackage{hyperref}")


def test_pdfcomment_idempotent(paper_dir: Path):
    insert_pdfcomment_package(paper_dir / "paper.tex")
    again = insert_pdfcomment_package(paper_dir / "paper.tex")
    assert again is False
    assert (paper_dir / "paper.tex").read_text().count("\\usepackage[author={circa}]{pdfcomment}") == 1


def test_pdfcomment_raises_if_no_hyperref(tmp_path: Path):
    p = tmp_path / "no_hyperref.tex"
    p.write_text("\\documentclass{article}\\begin{document}\\end{document}")
    with pytest.raises(RuntimeError, match="hyperref"):
        insert_pdfcomment_package(p)


def test_pidfile_refuses_when_live_pid(paper_dir: Path):
    bootstrap_workdir(paper_dir)
    write_pidfile(paper_dir, os.getpid())
    with pytest.raises(PidfileBusy):
        write_pidfile(paper_dir, os.getpid() + 100000)


def test_pidfile_overrides_dead_pid(paper_dir: Path):
    bootstrap_workdir(paper_dir)
    paths.pidfile(paper_dir).write_text("99999999")
    write_pidfile(paper_dir, os.getpid())
    assert int(paths.pidfile(paper_dir).read_text()) == os.getpid()

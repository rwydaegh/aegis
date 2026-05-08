import asyncio
import pytest

from server.pdf_builder import PdfBuilder, BuildResult  # noqa: F401


@pytest.mark.asyncio
async def test_build_succeeds(paper_dir):
    result = await PdfBuilder(paper_dir, build_timeout_s=60).build()
    assert result.ok
    assert (paper_dir / "paper.pdf").exists()


@pytest.mark.asyncio
async def test_build_fails_on_broken_tex(paper_dir):
    (paper_dir / "paper.tex").write_text(
        "\\documentclass{article}\\begin{document}\\bogusmacro\\end{document}"
    )
    result = await PdfBuilder(paper_dir, build_timeout_s=60).build()
    assert not result.ok
    assert result.error_tail


@pytest.mark.asyncio
async def test_concurrent_builds_serialize(paper_dir):
    builder = PdfBuilder(paper_dir, build_timeout_s=60)
    r1, r2 = await asyncio.gather(builder.build(), builder.build())
    assert r1.ok and r2.ok

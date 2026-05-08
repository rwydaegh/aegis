from pathlib import Path

from server.cleanup import clean_comments


SAMPLE = """\\documentclass{article}
\\begin{document}
% [circa:abc:begin]
Hello world.
% [circa:abc:end]
\\pdfcomment[author={circa}]{rephrased} % [circa:abc]
% [circa:abc] inline note follows
\\pdfcomment[author={someone-else}]{do not strip me}
\\end{document}
"""


def test_strip_pdfcomment_lines_only(tmp_path: Path):
    p = tmp_path / "p.tex"
    p.write_text(SAMPLE)
    n = clean_comments(p, strip_fences=False)
    out = p.read_text()
    assert "\\pdfcomment[author={circa}]" not in out
    assert "\\pdfcomment[author={someone-else}]" in out
    assert "% [circa:abc:begin]" in out
    assert "% [circa:abc] inline note" not in out
    assert n >= 2


def test_strip_fences_too(tmp_path: Path):
    p = tmp_path / "p.tex"
    p.write_text(SAMPLE)
    clean_comments(p, strip_fences=True)
    out = p.read_text()
    assert "% [circa:abc:begin]" not in out
    assert "% [circa:abc:end]" not in out

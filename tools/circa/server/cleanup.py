import re
from pathlib import Path

_PDFCOMMENT = re.compile(r"^\\pdfcomment\[.*?\]\{.*?\}\s*%\s*\[circa:[^\]]+\]\s*$", re.MULTILINE)
# Inline note line that isn't a fence (no :begin/:end and no '+' merge marker handled via the negation):
_INLINE_NOTE = re.compile(r"^%\s*\[circa:[^\]:+]+\][^\n]*$", re.MULTILINE)
_FENCE = re.compile(r"^%\s*\[circa:[^\]]+:(?:begin|end)\]\s*$", re.MULTILINE)


def clean_comments(paper_tex: Path, strip_fences: bool) -> int:
    text = paper_tex.read_text()
    n = 0
    text, k = _PDFCOMMENT.subn("", text)
    n += k
    text, k = _INLINE_NOTE.subn("", text)
    n += k
    if strip_fences:
        text, k = _FENCE.subn("", text)
        n += k
    text = re.sub(r"\n{3,}", "\n\n", text)
    paper_tex.write_text(text)
    return n

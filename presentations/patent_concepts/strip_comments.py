"""Strip LaTeX comments from .tex files.

Removes full-line comments and inline `% explanatory text`, but preserves:
  - escaped percent signs (\\%), which are literal characters in the output
  - bare trailing `%` with nothing after it (space-suppression in macro/template
    definitions; removing these would inject spurious spaces)
"""
import sys
from pathlib import Path


def first_unescaped_percent(line: str) -> int:
    i = 0
    while i < len(line):
        if line[i] == "%":
            bs = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                return i
        i += 1
    return -1


def strip(text: str) -> str:
    out = []
    for line in text.split("\n"):
        p = first_unescaped_percent(line)
        if p == -1:
            out.append(line)
            continue
        before, after = line[:p], line[p + 1:]
        if after.strip() == "":
            # nothing after %: bare functional % (keep) unless the whole line is a comment
            if before.strip() == "":
                continue  # blank/empty comment line -> drop
            out.append(line)  # functional trailing % -> keep verbatim
        else:
            if before.strip() == "":
                continue  # full-line comment -> drop the line
            out.append(before.rstrip())  # inline comment -> keep code only
    return "\n".join(out)


for f in sys.argv[1:]:
    path = Path(f)
    original = path.read_text()
    path.write_text(strip(original))
    print(f"{f}: {len(original.splitlines())} -> {len(path.read_text().splitlines())} lines")

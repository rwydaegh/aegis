# TAP paper v4 coauthor package

This directory contains the clean fourth-version snapshot prepared after
Emmeric Tanghe's comments on v3.

The PaperMaker tree in `../main/` is the source of truth. Run
`uv run python scripts/export_v4.py` from the project root to regenerate the
manuscript snapshots in this directory. The exporter assembles `paper.tex`
from `main/` and copies the unchanged SI from the project-level
`paper_SI.tex`.

## Manuscript

- `paper.tex`: v4 manuscript source.
- `tap_paper_v4.pdf`: compiled v4 manuscript.
- `paper_SI.tex`: unchanged SI source carried forward from v3.
- `tap_paper_v4_SI.pdf`: unchanged compiled SI carried forward from v3.

## Emmeric follow-up

The `emmeric/` directory contains the short follow-up email, the feedback note
in Markdown and Word formats, and the compiled v3-to-v4 latexdiff. No SI
latexdiff is included because the SI did not change in this feedback round.

The untouched latexdiff comparison source remains at
`../v3_to_coauthors/paper.tex`.

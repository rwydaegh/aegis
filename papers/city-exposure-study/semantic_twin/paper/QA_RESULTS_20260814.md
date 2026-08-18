# Paper QA on 2026-08-14

The canonical IEEE Access manuscript builds to eight pages, and the standalone
supplement builds to six pages. Both PDFs have embedded fonts, no undefined
references, and no undefined citations.

PaperMaker checks pass:

- main and supplement lint: zero flags
- main style scan: zero hits
- supplement style scan: four tier-D uses of the domain term `pose`, with no
  tier-A or tier-B hits
- paragraph-lens coverage: 166 of 166 rules
- executable claims: 13 of 13 pass
- claim links: no orphan or dangling claim identifiers across the main paper
  and supplement

The required `papermaker render` command reached a PaperMaker decoding bug when
the existing bibliography produced a non-UTF-8 byte in the captured `pdflatex`
output. The repository and PaperMaker sources were not changed to hide this
tooling defect. The already successful PDF builds were rendered with the exact
Poppler conversion used for visual review:

```bash
pdftoppm -png -r 300 build/main.pdf build/main_pages_qa_20260814_v2/page
pdftoppm -png -r 300 build/supplement_wrapper.pdf \
  build/si_pages_qa_20260814_v3/page
```

The commands produced eight main-paper PNGs and six supplement PNGs. Every page
was inspected. The first supplement iteration exposed a table crossing the
column boundary. The source table was resized to the column width, the complete
supplement was rebuilt, and all six pages were inspected again. The final page
set has no overlap, clipping, unreadable figure, or undefined cross-reference.
The final convergence wording was also qualified after the independent audit
identified rare-event first-diffuse behavior in Mexico City. Both PDFs were
rebuilt and all 14 pages were inspected once more after that correction.

The Access class still reports its inherited output-routine box warnings in the
main build. One text line is 2.57 pt overfull. The rendered page review shows no
visible clipping. The final supplement has no overfull-box warning.

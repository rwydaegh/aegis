# Canonical IEEE Access paper

Start with [READ_THIS_FIRST.md](READ_THIS_FIRST.md). The sole canonical
manuscript is the PaperMaker9000 paragraph tree in `main/`. Its compiled IEEE
Access source and PDF are `build/main.tex` and `build/main.pdf`. The argument is
in [spine.md](spine.md), and author decisions are collected in
[QUESTIONS_BANK.md](QUESTIONS_BANK.md).

The manuscript is a regular IEEE Access Research Article. Its main result is the
authenticated five-site, 73-standpoint calculation under the declared
first-material-interaction model. The supplement includes a ten-route extension
under the same production contract and a separate geometric fixed-grid diagnostic.
The current publication figures are indexed in [figures/README.md](figures/README.md).
The supplementary paragraph tree is in `si_new/`.

The existing `paper.tex`, `body.tex`, `methods.tex`, `si.tex`, and their PDFs
belong to the superseded eleven-city source-law manuscript. They remain only for
provenance. `ROOFLINE_METHODS_RESULTS_DRAFT.tex` is also a noncanonical prose
scaffold.

## Build and check

Run from this directory:

```bash
uv run --project /home/user/PaperMaker9000 papermaker assemble main --out build/main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build build/main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build build/main.tex
uv run --project /home/user/PaperMaker9000 papermaker lint main
uv run --project /home/user/PaperMaker9000 papermaker style-scan main
uv run --project /home/user/PaperMaker9000 papermaker lenses --type paragraph --coverage
uv run --project /home/user/PaperMaker9000 papermaker claims run --code-root code
```

The Access class, font files, and logos are the official May 13, 2026 template
assets. Do not replace them with an older class.

Build the separate supplement from this directory with:

```bash
uv run --project /home/user/PaperMaker9000 papermaker assemble si_new \
  --out build/supplement_body.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -output-directory=build si_new/supplement_wrapper.tex
```

## Current authority order

1. The authenticated five-city JSON and artifact manifest
2. `docs/CURRENT_PRODUCTION_CONTRACT.md`
3. `docs/RESULTS_INVENTORY.md`
4. `paper/spine.md`
5. Historical manuscript files, only when they do not conflict with the sources
   above

Do not copy numbers from the old compiled PDFs into the new manuscript.

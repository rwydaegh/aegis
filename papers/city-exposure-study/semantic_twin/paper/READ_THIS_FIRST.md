# Read this first

This directory now has one canonical manuscript: the paragraph tree in
`main/`. PaperMaker9000 assembles it into `build/main.tex` and compiles
`build/main.pdf`. The older `paper.tex`, `body.tex`, `methods.tex`, and `si.tex`
describe a superseded eleven-site study and are not scientific sources for the
new manuscript.

The manuscript targets a regular IEEE Access Research Article. Its result is the
verified five-site, 73-standpoint, first-material calculation. All absolute
values are normalized per unit areal source density and EIRP. The study is a
fixed-route comparison. It is not a population study, a city ranking, a
deployed-network estimate, a compliance assessment, or a complete multipath
solution.

The main manuscript is eight pages in the current Access build. The separate
supplement is six pages. The graphical abstract meets the 660 by 295 pixel,
300 dpi, and file-size requirements. The scientific plots are generated from
the sealed current result package. No fake or placeholder result data are used.

Read `QUESTIONS_BANK.md` for author decisions that do not block scientific or
technical completion. Read `spine.md` for the argument. Read
`../docs/RESULTS_INVENTORY.md` and `../docs/CURRENT_PRODUCTION_CONTRACT.md` for
the numerical and method authorities.

The post-draft review and applied fixes are summarized in `LENS_REVIEW.md`.
The required final checks are PaperMaker lint and lens coverage, a clean Access
template build, page-by-page PNG inspection, figure-source checks, citation
checks, claim checks, and a fresh Git diff review.

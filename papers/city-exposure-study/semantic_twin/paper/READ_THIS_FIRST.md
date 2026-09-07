# Read this first

This directory now has one canonical manuscript: the paragraph tree in
`main/`. PaperMaker9000 assembles it into `build/main.tex` and compiles
`build/main.pdf`. The older `paper.tex`, `body.tex`, `methods.tex`, and `si.tex`
describe a superseded eleven-site study and are not scientific sources for the
new manuscript.

The manuscript targets the IEEE Open Journal of the Communications Society
(OJ-COMS) special issue on human-centric wireless systems. Its main result is
the authenticated ten-route calculation: 163 observation points, 64 independent
runs per point, and a declared single-reflection model. All values are
normalized per unit areal source density and EIRP. The study scope is the ten
selected routes under the declared roofline source and single-reflection models.

The main manuscript is eight pages in the current OJ-COMS build. The separate
supplement is built independently. The graphical abstract meets the 660 by 295 pixel,
300 dpi, and file-size requirements. The scientific plots are generated from
the sealed current result package. No fake or placeholder result data are used.

Read `QUESTIONS_BANK.md` for author decisions that do not block scientific or
technical completion. Read `spine.md` for the argument. Read
`../docs/RESULTS_INVENTORY.md` and `../docs/CURRENT_PRODUCTION_CONTRACT.md` for
the numerical and method authorities.

The post-draft review and applied fixes are summarized in `LENS_REVIEW.md`.
The required final checks are PaperMaker lint and lens coverage, a clean OJ-COMS
template build, page-by-page PNG inspection, figure-source checks, citation
checks, claim checks, and a fresh Git diff review.

# Draft notes

## What this draft contains

- A complete IEEEtran journal draft with a title, a 244-word abstract, six index terms, and the requested single-author affiliation.
- An introduction that motivates the exposure ratio and makes the co-located photograph argument explicit.
- A related-work section that treats per-pair ray tracing as a careful solution to a different problem. It also concedes prior work on stochastic deployment integration, image-derived materials, multi-city exposure, and adjoint transport.
- The complete body of `methods.tex`, copied without editing its prose, equations, labels, symbol table, algorithms, or macros. Its manual bibliography entries retain their keys and text, and the combined bibliography adds the references used by the new sections.
- Results in the R1 to R6 order from `SPINE.md`. The draft includes the eleven-square overview, the final eleven-square exposure distributions, the result summary table, the crop-convergence plot, and the honesty-ledger table.
- A discussion that interprets the ratio, the local reach of image evidence, the failed monostatic proxy, the masonry-only material bound, the Monte Carlo errors, and every bias in the honesty ledger.
- A short conclusion with future work tied to the missing beam sweep, diffuse scattering, and the one-square bystander scope.

## Remaining todo

The draft contains one `\todo{}`. No geometric-steering or codebook-beam sweep has been run. The sources support exact cancellation for full digital maximum ratio transmission and a one-sided upper bound for geometric steering. They do not contain the numerical gap below that bound. The draft marks the missing sweep instead of inventing it.

## Source disagreements

- `methods.tex` reports the geometric visibility experiment on twelve standpoints as 1.000000, 0.999991, and 0.984 for closed loops, and 0.999, 0.916, and 0.736 for outward paths. `SPINE.md` reports the later 42-standpoint, four-city run as 1.000000, 0.999972, and 0.980 for closed loops, and 0.999103, 0.912004, and 0.714182 for outward paths. These appear to be different sample sets rather than a contradiction. The paper retains the numbers owned by `methods.tex` and does not add the newer set a second time.
- `PRIOR_ART.md` calls the Wiame paper a 2023 paper. Crossref assigns it to volume 73, issue 1, in 2024. The bibliography uses the issue year, 2024.
- `SPINE.md` says the published street-cell evidence-ladder shift of 0.079 dB is 2.3 standard errors. `CODE_AUDIT.md` reports 2.7 standard errors for one run and gives an eight-run mean of 0.167 plus or minus 0.022 dB. Since `SPINE.md` is the required numerical authority and explicitly says the 0.079 dB value is unresolved, the paper repeats only that unresolved status. The discrepancy should be reconciled before submission.
- `methods.tex` was edited concurrently during drafting. Its line count increased from 940 to 1015 while sources were being read. The final copied method body matches the current file apart from one trailing blank line. No changes were made to `methods.tex`.

## Holes in the spine

- R2 says the corrected illumination law reorders the cities, but `SPINE.md` gives no old-versus-corrected ranking, rank changes, or paired shifts. It gives only correlations between the three corrected illumination models. The draft can show that illumination changes the ordering, but it cannot quantify which squares the correction itself reordered. A final R2 table or sentence needs a measured pre-correction comparison if that distinction is meant to carry the section.
- R4 is partly an analytic result and partly an unrun experiment. Exact cancellation for full digital maximum ratio transmission is proved. The claim about geometric steering and codebook selection is a one-sided bound. The numerical result advertised by the R4 heading has not been measured, so the draft leaves a todo.
- R6 states that the converged radius is a property of each illumination model, but `SPINE.md` gives only the common 250 m operating point. The figure supports the choice visually. Per-model convergence radii or a stated common stopping rule would make this result reproducible from the prose alone.
- The eleven-square overview figure labels its visual mesh crops as 130 m for most sites, whereas the final exposure run uses 250 m. The caption now states that difference. A regenerated overview at the final crop would remove the possible confusion.
- The methods body already contains measured bystander, bounce-budget, and diffraction results. R5 and parts of the discussion necessarily repeat some of them because the request requires six result beats while also requiring the methods text to remain intact. The clean structural fix belongs in `methods.tex` and was not attempted here.

## Build and layout

- The inherited illumination-model table produces the same 5.33 pt overfull box noted for `methods.tex`. It was not changed because another author owns that file and the copied method content had to stay intact.
- The required two-pass `pdflatex` build completes successfully. The final PDF has 15 pages, zero undefined references, and zero undefined citations.
- A page-by-page image review found and removed an empty float page by setting the honesty ledger as a compact single-column table. The conclusion now remains contiguous on the final page.

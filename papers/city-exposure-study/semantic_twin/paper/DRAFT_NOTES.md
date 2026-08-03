# Draft notes

## Changes in this revision

- Re-read `paper.tex`, the previous notes, the complete house rule list,
  `SPINE.md`, the current `methods.tex`, `BEAMFORMING.md`, and
  `FIGURES/README.md` before editing.
- Rewrote the abstract at the measured strength. It now gives the median
  within-square spreads beside the between-square spreads, names the street-cell
  counter case, reports the nonuniform illumination-law correction, and includes
  standpoint-sampling uncertainty.
- Replaced R2 with the paired eleven-city law comparison. The paper now reports
  the shift ranges, residual rms values, old-versus-corrected rank correlations,
  and the two sites that account for almost all reordering: New York rooftop and
  Tokyo street.
- Expanded R1 to give the full within-versus-between comparison. The comparison
  goes the paper's way for isotropic and rooftop illumination and not for street
  cells. Per-city claims are qualified by standpoint sampling.
- Added standpoint sampling to the discussion and honesty table. The per-city
  median changes are 0.128, 0.061, and 0.188 dB rms, with worst changes of
  0.242, 0.116, and 0.326 dB under isotropic, rooftop, and street illumination.
- Updated the material result with the whole-field ground comparison and the
  measured facade bracket. The ground-inclusive result is larger and has the
  opposite sign. The dielectric bracket spans 0.34 dB isotropic and 0.58 dB
  rooftop, while metal changes the medians by 2.502 and 4.374 dB.
- Replaced the geometric-steering placeholder with the measured aperture sweep
  from `BEAMFORMING.md`. An 8 by 8 panel changes the Korenmarkt rooftop and
  street ratios by -0.38 and -1.64 dB. No codebook value was invented.
- Updated the bystander result to 2.15 people per square metre, added its paired
  noise floors and absorber control, and stated that it used the superseded
  six-interaction configuration.
- Added the per-model crop convergence radii and the separate nonconvergent
  deployment-cap result.
- Synchronized the current 42-standpoint, four-city visibility experiment from
  `methods.tex`, including the outward-path fractions. A later concurrent change
  to `methods.tex` added an independent reflected-term check, which is also
  included. Its bibliography entries remain present in the combined bibliography.
- Corrected the street diffraction median from 0.44 to 0.42 dB, its 2 GHz value
  from 1.82 to 1.78 dB, and the largest defined bound to 12.64 dB. The paper also
  reports the 1.26 dB street 90th percentile over the 56 defined standpoints.
- Resolved the old 0.079 dB evidence-ladder discrepancy. It was the lowest of
  eight draws. The seed-averaged value is 0.167 plus or minus 0.022 dB.
- Added Figures 22, 24, and 25. They show the evidence radius, the diffraction
  bound, and the measured bounce budget. All three carry claims that were
  previously left in prose.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** Several bullets here are rooftop
> and street results: the eleven-city law comparison, the standpoint sampling triples, the
> rooftop half of the material bracket, the aperture sweep, the crowd result and the
> deployment-cap result. Those are stale, while the isotropic entries, the bounce budget,
> the four-city visibility experiment and the abstract's structure survive.

## Still open

- The nearest-grid codebook table in `BEAMFORMING.md` still contains
  placeholders. Best-beam selection needs a finite-site experiment because the
  stored estimator does not retain the paths belonging to one site.
- Diffuse-scattering strength remains modeled rather than fitted and is the
  largest unresolved physical uncertainty.
- The bystander result covers one square and has not been rerun at the current
  three-interaction operating point.
- Standpoint selection needs a stable spatial sampling rule or a resampling
  error estimate built into each city result. More rays do not reduce this term.
- The eleven-square overview still uses smaller visual crops in some panels than
  the 250 m exposure run. Its caption states the distinction.

## Remaining source problems

- `SPINE.md` says 10.7% of launched power escapes untouched. The shipped
  bounce-evidence data and Figure 25 show 21.0%. The 10.7% value subtracts
  per-depth incident shares that are not a partition because a ray reaching a
  later depth was counted at earlier depths. The paper uses 21.0%.
- `SPINE.md` says the three-interaction budget moves no standpoint by more than
  0.12 dB. That value belongs to the roulette-on row. The current roulette-off
  default has worst changes of 0.005, 0.016, and 0.063 dB. The paper uses
  0.063 dB. The corresponding truncated shares are 0.0037 median and 0.0201
  worst, rather than the rounded 0.0038 and 0.021.
- The spine's shorthand of 0.24 dB worst standpoint-sampling error is the
  isotropic value. The street-cell worst is 0.326 dB. The paper gives all three
  models rather than generalizing the isotropic number.
- The spine and the older part of `methods.tex` still carry the pre-figure
  street diffraction and bounce values listed above. `methods.tex` was not
  modified. The paper copy uses the shipped JSON and the newer figure audit.
- The spine says only the direct term has an independent implementation check.
  The current `methods.tex` now contains a second-tracer check of the reflected
  term. It resolves no disagreement against its 0.24 to 0.46 dB Monte Carlo
  floor. The paper includes this new check and its limits.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** The street diffraction values, the
> per-model worst sampling errors and the second-tracer floor are quoted one number per
> illumination model, so their rooftop and street entries are stale. The power share, the
> interaction budget and the truncated share items in the same list are transport and
> survive.

## Build and layout

- The required two-pass `pdflatex` build completes successfully. The final PDF
  has 18 pages, zero undefined references, and zero undefined citations.
- All PDF fonts are embedded. A page-by-page PNG review found no clipped content,
  float-only page, or unreadable new figure.
- The inherited illumination-model table still produces its 5.33 pt overfull
  box. The source table belongs to `methods.tex` and was not changed.
- The source contains no em dashes and no prose semicolons. The only semicolons
  are the two `\;` mathematical spacing commands in the inherited equations.
- No `\todo{}` remains because the geometric-steering sweep is now measured.
  The unmeasured codebook case is stated as an open limit without a number.

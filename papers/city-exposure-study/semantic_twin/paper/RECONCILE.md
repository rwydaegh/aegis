# Reconciling paper.tex and methods.tex

Date 2026-08-03. Both files were owned for this pass. The duplicated methods body
now lives in one file, `paper/body.tex`, which both documents `\input`.

## Lead: the number both files got wrong

**Under the isotropic model, chi does not equal the sky fraction.** Both files
stated this twice each, in Models used and again in Validation, and offered it as
an exact identity check passed by two independent code paths. It is false in the
paper's own shipped output. Recomputed over the 880 rows of `city250_L3`:

| quantity | median | worst |
|---|---|---|
| 10 log10(chi_iso / sky) | **+0.9874 dB** | **+2.9406 dB** |
| 10 log10(chi_iso_direct / sky) | +0.0004 dB | 0.0651 dB |

It cannot hold, because chi = chi_dir + chi_ref and the reflected term is
positive. What is true is the statement the Estimator subsection already made
correctly: the **direct** term equals the sky fraction, and it does so to four
ten-thousandths of a decibel. Scoped to the direct term the check is real and
rather good, so it was rescoped rather than deleted, in both places, and the
measured agreement is now quoted. This is the only defect where both files were
wrong and where the paper claimed a check its own output disproves.

## Every number that differed between the two files

Verified from `outputs/`, not from the markdown reports. Where a report and the
JSON disagreed, the JSON won.

| quantity | paper.tex | methods.tex | what the data says | wrong file |
|---|---|---|---|---|
| visible-direction cross check | median 0.19 / 1.14 / 3.70 %, worst 1.29 / 6.44 / 23.05 % | "to within" 0.34 / 1.73 / 7.3 % | pooled median and max over the 60 standpoints; 0.34 / 1.73 / 7.3 is the **Times Square column**, one site's medians | methods.tex |
| street diffraction uplift median | 0.42 dB | 0.44 dB | **0.4218 dB** over the 56 standpoints with a defined uplift | methods.tex |
| 2 GHz street median | 1.78 dB | 1.82 dB | **1.7788 dB** over the same 56 | methods.tex |
| worst standpoint uplift | 12.64 dB | 12.6 dB | **12.6397 dB**, Grand-Place | methods.tex (rounded) |
| crowd isotropic loss | 0.07 dB | 0.05 dB | 0.07001641, three-interaction retrace | methods.tex |
| crowd rooftop loss | 1.07 dB | 1.0 dB | 1.06896791 | methods.tex |
| absorber "from" triple | 0.07 / 1.07 / 1.40 | 0.05 / 1.04 / 1.39 | 0.070 / 1.069 / 1.396 | methods.tex |
| crowd density | 2.15 per m2 | "two people per square metre" | 2.152782, per **walkable** m2 | methods.tex |
| depth shares additive? | silent | "not parts of one whole" | correct, they are not | paper.tex |
| eighth station | excluded, no resolution | re-registration to 1.000 given | neither: the observation stands, the causal story does not, see below | both |
| S_inc definition | dropped | given | needed, S_inc is used in eq. (sab) | paper.tex |
| SAM 3 citation | collapsed to `\cite{sam}` | split, with a `\todo` | correct, `CITATIONS.md` forbids inventing a SAM 3 entry | paper.tex |

### The 0.44 versus 0.42 case is worth recording

`WHY_NOT.md` line 428, the stated source, supports methods.tex. It is not a
transcription slip. The two files used **different conventions for the four
standpoints whose street direct term is exactly zero**, where the uplift is
0/0 and undefined:

- rank those four at the top of the sample and take the median over all 60: **0.4350** and **1.8247**, which is WHY_NOT's 0.44 and 1.82;
- take the median over the 56 where the uplift is defined: **0.4218** and **1.7788**, which is paper.tex's 0.42 and 1.78.

The 56-standpoint convention was adopted, because it is what the shipped figure
plots, what `FIGURES/README.md` and `SPINE.md` document, and what the validation
percentages in the same paragraph already use. Mixing 3.70 % (56-based) with
0.44 dB (60-based) would have been incoherent. Both files now say which
population each median is over.

## Findings from the provenance audit that were applied

Beyond the drift above, these were fixed in the shared body or in `paper.tex`.

- **Finding 15, configuration drift.** A new table, "Trace configuration behind
  each result", gives crop, bounces, rays and standpoints per result block, and
  the Results preamble no longer asserts one configuration for all of them.
- **Finding 3.** The bounce-budget power shares are now labelled as a 130 m
  crop at eight stations, with the 250 m values beside them. The truncation
  bound now carries the published population: 0.0050 median and 0.0795 worst
  over 880 standpoints, against the 0.0037 / 0.0201 of the 40-standpoint walk.
  The 0.063 dB budget deviation is scoped to those 40 at a 130 m crop, with
  0.384 dB given as the bound that holds across the four squares measured at the
  published crop.
- **Finding 5.** The deployment cap swing is 100 to 400 m, not 50 to 500 m.
  Recomputed: 7.398 rooftop, 9.242 street, 0.5072 contrast, all on the
  100 to 400 m grid. Over 50 to 500 m the swing is about 10.8 dB.
- **Finding 9.** "Three continents" is two, and the four meshes are named. The
  0.941 to 0.999 coverage is a range over four **pooled per-square** values, not
  over 35 stations, which run 0.696 to 0.9998, and it is a different four
  squares from the visibility set. "Beyond 40 m every depth falls below 0.21" is
  false, the 40 to 80 m bin reaches 0.2113, so it now reads 0.22. The walk's
  90 m is a sampling radius, cameras span 56 m. "Two parts in a thousand" is
  four at the median and twenty two at the worst.
- **Finding 10.** "The three most enclosed squares" is wrong. By median sky
  fraction Korenmarkt ranks fourth, behind Times Square, Brussels and Tokyo. The
  set is the two most enclosed plus the reference square, and now says so.
- **Finding 7.** The crowd-retrace claim was true for two of three columns. The
  isotropic column moved 0.021 dB against a 0.009 dB floor. Stated per column.
- **Medians presented as bounds.** The dielectric bracket's 0.58 dB is a median
  span, worst standpoints +1.56 / +2.48 / -2.67 dB, now stated. The cross
  validation's 0.25 and 0.16 dB are the **worst of three** models, median across
  models 0.24 and 0.03, and the floor is 0.23 to 0.35 dB in the shipped
  configuration, not 0.24 to 0.46 which included a `specular` mode that was
  never used.
- **Naming the external check.** Sionna RT and the Grand-Place are now named at
  the point of use.
- **Monte Carlo error model.** 0.0042 / 0.0136 / 0.0343 dB are attributed to a
  measurement over eight disjoint seed streams, with the per-seed values stated
  as not retained. Not deleted and not softened.
- **Torn row files.** Two of eleven `city250_corrected` files are damaged: 78
  valid rows at Times Square, and Prague has 81 lines of which one is
  unparseable. The abstract's dominant-uncertainty triple rests on 878 of 880
  pre-change standpoints, and the disk recomputation, 0.125 / 0.066 / 0.181 dB,
  is now given beside the recorded 0.128 / 0.061 / 0.188. The published headline
  run parses clean at 880.
- **Smaller items.** Roulette agrees to two significant figures on two models
  and three on the third, not three on all. The A7 band is +/-5 degrees of
  23.6 degrees, which is what produces 7.8 and 0.4 %, not "a few degrees of 24".
  The 3.1 to 5.0 frequency factor is a linear-excess ratio and now says so. The
  arriving shares are 0.212 and 0.185, not 0.21 and 0.19. The absorber control
  ran 8 standpoints against the crowd arm's 12, sharing 2, and that is stated.
  "The three paragraphs after this list" was wrong, there are six.
  `ITU-R P.2040-4` is 2025 in both bibliographies.
- **Captions.** Figure 25's depth bars are stated as not additive. Figure 16's
  axis clip at the 1st and 99.5th percentiles is stated.

## Applied from the supplementary-information pass

- **The interaction-budget bound was understated six times over.** "No
  standpoint by more than 0.063 dB" is Korenmarkt at a 130 m crop. Across four
  squares at the published 250 m crop the worst is **0.384 dB** at the
  Grand-Place under the street model. Both are now given, with the second named
  as the one that holds everywhere it was measured. The budget argument still
  reads the same way, because what it rests on is that no standpoint of either
  set moves half a decibel, and that survives at 0.384 dB.
- **The 21.0 % untouched share is pooled over the eight camera positions.**
  Over the 40 walk standpoints it is 23.6 %, and over the 250 m crop 23.3 %. All
  three are now stated with their population.
- **The re-registration mechanism was dropped, the observation kept.** The pose
  file shows only one registration of that camera and the "before" position is
  byte-identical to the raw provider pose, so the 0.362 to 1.000 story cannot
  carry a causal claim. What survives is that a pose can clear the skyline
  residual and still fail on coverage. The text now says the displacement does
  not order coverage, since the standpoint displaced furthest scores 0.978.
- **Two cross-references** to Sections S1, S2 and S3 of the supplementary
  information were added.

## What was done about the duplication

`paper/body.tex` holds the shared methods body, sections "Exposure ratio"
through "Validation", 1022 lines. `paper.tex` and `methods.tex` each reduce to a
preamble, a title, their own front and back matter, and `\input{body}`. The two
bodies are now the same bytes by construction and cannot drift.

The spelling obstacle was resolved to **American** throughout, as the target is
an IEEE journal. `methods.tex` lost its British forms. The one remaining British
spelling is "millimetre" inside the `adhikari` bibliography entry, which is the
published title of that paper and should not be changed. `methods.tex` gained
`\todo` in `paper.tex`'s preamble so the SAM 3 marker renders in both.

Verification: both documents build twice with **zero undefined references and
zero undefined citations**, and no LaTeX warnings at all. `paper.pdf` is 20
pages, `methods.pdf` is 11 pages.

## Open, not applied

- **Finding 11, beamforming axes.** "Reversing pairs up to 1.53 dB rooftop and
  2.97 dB street on axes 5.6 and 9.8 dB wide" uses `antenna11_250m.json` at 32
  standpoints per site, while the headline spreads 4.93 and 9.58 dB are the
  80-standpoint figures. Two numbers about 200 lines apart are both called the
  eleven-square spread. The conclusion is unaffected and would be slightly
  stronger against the headline axis. Also unstated: 0.818 is the worst of three
  grid rotations, and "full digital maximum ratio transmission" maps to the
  `_element` columns, not `_matched`.
- **The "+50 dB" coarse beam grid.** The paper says such grids "were computed
  and excluded". `ARTEFACT_CODEBOOKS = (8, 16, 32)` in `antenna.py` are all at
  least as fine as the aperture, so they were excluded a priori, not computed.
  This is a claim about what was run and needs the author.
- **Other orphans** in the audit's finding 16 that have no artefact under
  `outputs/`: the one-run sd 0.0624 dB, the eight per-seed draws behind
  0.167 +/- 0.022 dB, the "at most 0.03 dB" retrace bound, and the "20 to 25 dB
  down" array figure from `BEAMFORMING.md`.
- **Element effect "1.07 dB at Madrid"** is aggregation-dependent and the paper
  does not say which reduction it used. Taking the dB ratio of per-city median
  chi instead gives Madrid 1.14 and makes Brussels the worst square.
- **`sensitivity.json` declares `published_run: city250_corrected`** while its
  own validation block matches `city250_L3`. A data-file label, not a paper
  claim, but it will confuse the next reader.
- **The SAM 3 reference is still a `\todo`.** `CITATIONS.md` is explicit that it
  must not be guessed at. It needs the real citation before submission.
- **The two torn `city250_corrected` files** should be re-run before submission.
  Not attempted here, per instruction.

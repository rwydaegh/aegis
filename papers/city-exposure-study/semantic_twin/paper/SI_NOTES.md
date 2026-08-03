# Supplementary information: what is in it, what is not, and what the body needs

`paper/si.tex` is a standalone IEEEtran document with its own bibliography. It
builds with two `pdflatex` passes, **11 pages**, zero undefined references and
zero undefined citations, zero overfull or underfull horizontal boxes. It uses
the same six macros and the same notation as the body, and renumbers sections,
tables and equations with an `S` prefix so a cross-document reference is never
ambiguous.

```
cd papers/city-exposure-study/semantic_twin/paper
pdflatex -interaction=nonstopmode si.tex && pdflatex -interaction=nonstopmode si.tex
```

## What went in

**S1 Panorama registration.** The skyline objective and how the observed and
modelled skylines are built, the six free parameters with their bounds, the
seventh bias parameter and why it is switched off, the differential evolution
settings, the vertex prune, the eight-seed study and what its covariance does and
does not mean, the admission gate with its three thresholds, the sky conflict
test, the crop diagnosis behind the poses that sat inside the geometry, the
Hachiko re-registration, the Times Square failure, the first-interaction coverage
test, and a per-square census of the whole corpus.

- Table S1: first-interaction coverage at the eight admitted Korenmarkt stations.
- Table S2: registration per square, 83 panoramas, 83 registered, 51 admitted,
  31 at the altitude bound, 14 inside the geometry.

**S2 Projection onto triangles.** Both routes. The station cast with its grid
height, its transient rejection and its ray-count-weighted vote. The cutter with
its near-plane and ownership guards, the four-step cut, the crop geometry, the
boundary tolerance sweep, the per-face record, the visible fraction and
confidence definitions, the occlusion budget, the round trip, and how much
triangle area the projection actually binds.

- Table S3: boundary simplification sweep.
- Table S4: per-view round trip.

**S3 Seeds and ray counts.** What a seed controls, the seed maps used by each
script, a per-result table of ray counts and interaction budgets, the three seed
studies that measure the Monte Carlo error, which comparisons are paired, and
the statement that standpoint sampling and not Monte Carlo is the dominant
uncertainty on a per-square number.

- Table S5: ray counts, 21 rows, one per result.
- Table S6: Monte Carlo standard deviation from eight seed streams.

**S4 The eleven squares, one by one.** The standpoint construction rule and the
per-square numbers behind the headline figure.

- Table S7: per square, triangles, ground datum, walk candidates, median $\chi$
  and 5th-to-95th spread under the three illumination models, median sky fraction.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** Table S7 reports median $\chi$ and
> a spread under each of the three models, so two of its three model blocks are built on
> the old height and range bands and are stale. Its triangle counts, ground datum, walk
> candidates, sky fraction and isotropic block survive, because they come from the
> geometry alone.

**S5 Material assignment.** The geometric class rule with its two thresholds,
the four-class table with ITU-R rows and RMS heights, an honest paragraph about
where the roughness numbers come from, and the per-square class area split.

- Table S8: the four-class assignment.
- Table S9: class area fractions per square.

**S6 Convergence sweeps.** Crop radius and interaction budget at more resolution
than the body has, plus the power-at-depth budget.

- Table S10: crop radius sweep, nine radii.
- Table S11: interaction budget at four squares.

## What was deliberately left out

- **Figures.** The SI is text and tables only. The candidate PNGs in `FIGURES/`
  are dark-themed showcase renders from an earlier pipeline phase and would not
  sit beside IEEE body figures. Nothing in the SI needs one.
- **The deployment range-cap sweep** (`outputs/sensitivity/`, 91 cap values, 11
  sites, the $\rho_+^{-1.2}$ scaling and the Spearman 0.81 reordering). It is a
  result, not an appendix to a method, and the body treats it as one. Putting it
  in the SI would move a result out of the paper.
- **The Istanbul rejection.** Interesting and well documented, but the criterion
  was a post-acquisition judgement with no coded threshold anywhere in the
  repository, and the site never entered the eleven.
- **The full ITU-R row table and the 16-class roughness library.** Only the four
  rows the runs actually use are given. The rest is a configuration file, not a
  result.
- **The Sionna cross-validation, the diffraction bound and the monostatic
  return.** They appear in Table S5 with their ray counts because that table
  promises completeness, and nowhere else. They are body material.
- **A ray-count convergence curve.** None exists at the corrected illumination
  law over more than one standpoint. See below.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** The second bullet keeps the
> deployment range-cap sweep out of the SI, and that sweep, its scaling exponent and its
> reordering exist only because the old law had a range band. The exclusion is stale in
> the sense that the result it defers to the body is going away, and the other exclusions
> stand as written.

## Numbers that could not be sourced, and are stated as not reported

Each of these is either absent from the SI or is carried with an explicit note
that it has no artefact behind it.

1. **The eight seed values behind the 120-standpoint noise study.** The study is
   real and its results are in Table S6, but the replica seeds were never written
   down and no replica file exists under `outputs/`. The SI says so under "How the error was measured" in S3.
2. **The grid height of `outputs/walk_korenmarkt/walk_semantic.npz`**, the
   binding every image-derived Korenmarkt number rests on. It records no grid
   height. That it was 1024 is established by a bit-for-bit rebuild, which the SI
   states under "The station cast" in S2.
3. **The Times Square full-circle yaw scan.** Prose only, no output file. The SI
   gives the numbers and says plainly that the scan can be repeated but not read
   off disk.
4. **Seed and location count in the crop convergence payload.** The file records
   neither. The seed of 11 in S3 comes from the script default and the observer
   count of 32 comes from the rows themselves.
5. **A glass bracket in the material ablation.** `run_material_ablation.py` plans
   `pure_glass` and `ablation.json` has no such variant. No glass number appears
   anywhere in the SI.
6. **Milan crop convergence.** Prose only, no JSON. Not in the SI, and the 250 m
   requirement is left as a one-site measurement.
7. **A fit statistic for the $\rho_+^{-1.2}$ deployment scaling.** No regression
   is performed anywhere. Not in the SI.
8. **Any per-standpoint error bar in any location file.** None exists. The SI says so.
9. **Any external ground-truth check on any pose.** None exists. S1 gives three
   internal tests and claims nothing beyond them.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** Item 7, the missing fit statistic
> for the deployment scaling, belongs to the old law's range band. It is stale, because
> the new law has no cap to fit, and the other eight items are registration, seed and
> image work that the change does not touch.

## Where the JSON and the prose disagree, and which the SI follows

The SI follows the JSON in every case below.

| # | Disagreement | What the SI does |
|---|---|---|
| 1 | `BOUNCE_BUDGET.md` assigns 0.998 first-interaction coverage to the 1.08 deg station and 0.978 to the 3.06 deg one. The shipped JSON has them the other way round. | Table S1 uses the JSON order. Verified independently from `walk_semantic.json → stations_used` and the station block of `korenmarkt_130m_bounce_evidence.json`. |
| 2 | `BOUNCE_BUDGET.md` says the 0.362 station was re-registered from one pose to another and that both poses passed the same gate at the same 3.67 deg residual. The pose file shows only one registration, and the "before" position is byte-identical to the raw provider pose in `walk_download.json`. | The SI subsection "First-interaction coverage is a sharper test than the residual" was rewritten. The probe standpoints at the 130 m binding are provider poses for all eight stations, the eight moved 3.91 to 5.50 m during registration, and the size of the move does not order the coverage. |
| 3 | The 0.362 to 1.000 change is presented as a controlled comparison. Three things differ between the two runs: probe standpoint, crop radius and station set. | The same subsection says so and credits none of the three. |
| 4 | `BOUNCE_BUDGET.md` says no standpoint out of 40 moves half a decibel at any budget. `brussels_grandplace_250m_bounce_evidence.json` reports two standpoints over 0.5 dB under street illumination with roulette on. | The SI subsection "Number of surface interactions" states both, and notes the claim holds at Korenmarkt where it was measured. |
| 5 | The paper quotes 0.063 dB as the worst interaction-budget change. That is Korenmarkt at 130 m. The worst across the four squares measured is 0.384 dB at Grand-Place. | Table S11 gives all five site-and-crop rows and the SI says which number the paper quotes. |
| 6 | `SPINE.md` gives the untouched share as 10.7 percent, computed as one minus the sum of the per-depth incident shares, which are not a partition. | The SI subsection "Where the power is" gives the first-depth complement and explains the error. |
| 7 | The paper's 79 / 8.85 / 1.19 / 0.23 percent power budget is pooled over the **eight camera positions**, not over the walk. At the walk the untouched share is 23.6 percent at 130 m and 22.6 percent at 250 m. | The same subsection gives both poolings and says which one the paper quotes. |
| 8 | `PAPER_METHODS.md` says the crop convergence file carries the superseded illumination law and that the corrected columns have no source. The file on disk is corrected-law. | The SI subsection "Crop radius" uses the file on disk. |
| 9 | `PAPER_METHODS.md` reports the crop sweep at 24 observers. The file has 32. | The same subsection says 32. |
| 10 | Roulette wall clock: the paper says 101 and 100 s, the 250 m JSON gives 101.92 and 106.35 s. | The SI gives 101.9 and 106.4 s and names the crop. |
| 11 | `MATERIAL_VLM.md` says a facade crop is "384 pixels across 22.5 degrees" and "26 mm per pixel at 20 m". Both follow from a linear-in-pixels approximation that is wrong for a 90 degree gnomonic view. The true angular width runs 18.4 to 28.1 degrees depending on where in the parent view the window sits. | Neither number appears in the SI. |
| 12 | `CROSS_VALIDATION.md` prints 6,550 paths per source where the JSON has 6542.9. | Neither appears in the SI. |
| 13 | `registration_sky_conflict.json` is a pre-re-registration snapshot and disagrees with the current pose files at Times Square and Hachiko. | Table S2 is recomputed from the pose files and reproduces `evidence_coverage.json`. |

One further item, recorded rather than resolved: the ITU-R P.2040-4 row in the
paper bibliography is dated 2023, while the manifest provenance names the 09/2025
edition. The SI bibliography follows the manifest and says 2025. If the body is
correct that the 2023 edition was used then the SI entry should change, not the
other way round.

## The exact edits the body needs

The two deferrals now live in `paper/body.tex`, not `paper/paper.tex`, after the
restructure that moved the methods into `body.tex`. Both are one-line changes and
neither has been applied here. Line numbers were 305 and 638 at the time of
writing and the file is being edited concurrently, so the surrounding sentence is
given as the anchor.

**Edit 1**, in the paragraph ending "What ran here is SAM 3, which takes the
material name itself as the prompt." Replace

```latex
described in the supplementary information.
```

with

```latex
described in Sections~S1 and~S2 of the supplementary information.
```

**Edit 2**, in the paragraph beginning "The estimator is stochastic, so every
reported value carries a Monte Carlo standard error". Replace

```latex
in the supplementary information.
```

with

```latex
in Section~S3 of the supplementary information.
```

If the body would rather point at the extra material as well, a third sentence
could be added anywhere convenient in the results:

```latex
Per-square numbers, the material assignment and the convergence sweeps are
given at greater length in Sections~S4 to~S6 of the supplementary information.
```

## Body claims the SI does not support at their current strength

These are flagged, not changed. They are all in `paper/body.tex`.

1. **The 0.362 station.** The body says the low coverage "is a registration
   failure rather than a coverage one" and that the station "stands eight meters
   from one scoring 0.999". The eight-metre spacing holds between registered
   poses and is 9.1 m between the probe standpoints the number was measured at.
   The "registration failure" reading is not supported: all eight probes are
   provider poses displaced 3.91 to 5.50 m from their registered camera, seven of
   them score 0.978 to 0.999, and the station that moved furthest is not the one
   that fails. The operational claim, that first-interaction coverage catches
   something the residual does not and costs one trace, survives intact. A
   minimal repair would be to drop "rather than a coverage one" and the causal
   sentence, keeping the observation and the exclusion.

2. **"never moves a standpoint by more than 0.063 dB".** True at Korenmarkt at
   130 m, which is where it was measured. Across the four squares that carry an
   interaction budget sweep the worst is 0.384 dB at Grand-Place, still well
   under half a decibel. Adding "at the reference square" would make the sentence
   exact.

3. **"Of all launched power, 21.0 percent never touches a surface".** This is
   pooled over the eight camera positions rather than over the walk the exposure
   numbers use. At the walk it is 23.6 percent. The three interaction shares
   beside it have the same provenance. Naming the pooling would settle it.

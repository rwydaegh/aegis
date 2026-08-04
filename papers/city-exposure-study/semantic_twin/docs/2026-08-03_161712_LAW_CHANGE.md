# The illumination law is being replaced

Read this before quoting any number labelled rooftop or street small cell.

Status on 2026-08-03: the replacement is **not finished** and none of its numbers
are final. Nothing in this repository has been recomputed under it. Every
document named below keeps its old numbers unedited, with a note saying which
law they came from.

## What the illumination law is

`Q_S(u)` is the angular density of incident power that the external base station
network puts on a standpoint, before the square is allowed to block or reflect
any of it. The exposure ratio is an integral of the traced transfer against
`Q_S`, so `Q_S` is a weight and nothing else. It never enters the ray trace. That
is why a single trace can be scored under several laws, and it is also why
changing the law changes every directional number without changing a single ray.

The isotropic model is `Q_S` constant. **The change of law does not touch it**,
so every isotropic number in the study stands as computed. It is a control
rather than a deployment, it has no sites in it, and open ground is still a
well defined reference for it. The one thing that does reach it is the reporting
change further down, which affects how the whole result is presented rather than
what the isotropic integral is worth.

## The old law

Two deployment classes, each described by four numbers.

| Class | Height above head | Horizontal range | Elevation support |
| --- | --- | --- | --- |
| Macro rooftop | 13.5 to 43.5 m | 25 to 250 m | 3.09 to 60.11 deg |
| Street small cell | 2.5 to 6.5 m | 10 to 150 m | 0.95 to 33.02 deg |

Sites are uniform in azimuth and uniform by area in range. The elevation support
is derived from the two bands. `MONOSTATIC_SBR.md` section 2.7 and 2.7.1 hold the
derivation, `DEPLOYMENT_GEOMETRY.md` argues the eight endpoint numbers, and
`semantic_twin/propagation/directions.py` implements it as `ROOFTOP` and
`STREET_SMALL_CELL`.

There were two versions of this law and **both are going**. The first placed
sites at a single fixed height and gave `1/sin^3(el)`. The second, from
2026-08-02, integrated an admissible height window at each elevation and gave a
truncated second moment times `1/sin^3(el)`. Many documents carry a correction
mark for that 2026-08-02 change. **That mark is not the current state.** Both
versions are height band and range band laws.

## The new law

Sites sit on facade tips. A facade tip is the top edge where a wall meets the
sky, which is the silhouette a pedestrian photographs. There is no mast.

The consequence is that each azimuth carries one source distance, read off the
skyline, rather than a distribution over one. So there is no range band to cap
and no height band to assume. The four numbers per class are gone, and with them
the two classes.

**The exact quantity is a line integral over the whole visible roofline.** A
first closed form, the mean over azimuth of `cos^2(alpha)/d`, has already turned
out to be an approximation rather than the law, because it assumes one visible
facade tip per azimuth and a roofline perpendicular to the line of sight, and
neither assumption holds. Any number computed from that closed form is
provisional and must not be propagated. The pilot output at
`outputs/skyline/pilot_250m.json` is a pilot and is labelled as one.

### Site density and transmit power never have to be stated

Antenna density per square kilometre is assumed the same in every city. That is
deliberate and it is not a weakness. The density and the transmit power enter as
one multiplier in front of every city's answer, so they cancel in any comparison
between cities. No number for either has to be quoted or defended, which is the
same reason the study reported a ratio in the first place.

### The line of sight term is normalised to one, and that is a reporting split

Setting the line of sight term to one is a **way of reporting the result in two
parts**. It is not a statement about how much power a source radiates.

The difference matters. Reading it as a definition of source power would mean
operators radiate harder where there is less sky, which nobody does, and it would
delete the shadowing result. The shadowing result is the most robust thing in the
study, because it needs no photographs and it holds at all eleven cities. So the
answer is reported as two factors: the line of sight term, and the multipath
surplus that sits on top of it.

### The old denominator does not survive

This is a separate change from the law itself and it is easy to miss.

`chi` was defined as the arriving power density over what **the same network
would deliver at the same point over open ground**. That definition needs the
network to still exist once the buildings are taken away. Under the new law the
sites live **on** the buildings, so removing the buildings removes the network
and the denominator is empty.

The replacement is to report the geometric quantity per unit site density and per
unit transmit power, with a second reference taken against the unoccluded
roofline. Anywhere a document defines `chi` against open ground, that definition
is superseded. The affected places are `paper/body.tex` section 1, `SPINE.md`
under "the quantity", and every restatement of the ratio that follows from them.

Note what this does **not** undo. The reason for reporting a ratio rather than an
absolute level stands, because the absolute level is still unknowable and a
common multiplier still cancels. What changes is which quantity sits underneath.

### Where the provisional closed form has already been written down

Concurrent work on the exporter and the walkthrough blends has documented the
closed form as if it were the law. `PAYLOAD.md`, under "where the sources are",
states the direct term as a mean over azimuth of `cos^2(alpha)/d` and quotes a
sky fraction pair at Korenmarkt. That is the approximation, not the law, for the
reason given above. The code and its note were left alone because they are
someone else's live work, but a reader should not take that section as the
definition.

### Still open

**Whether the source has zero thickness or occupies the top few metres of the
facade.** Not decided. A photogrammetric mesh is lumpy at the half metre scale,
so a zero thickness source may not be extractable from it reliably, and this may
have to change. Treat it as open, not as settled either way.

## Why the change

The strongest argument is arithmetic, not taste. In the path loss weighted branch
of the old law the range integrand is `dr` over `[r_lo, r_hi]`, which is
logarithmic in the outer cap. A logarithm has no plateau, so `d_max` did not
bound the answer, it set it. `DEPLOYMENT_GEOMETRY.md` section 7.5 measures the
headline movement across the defensible span of that cap as **7.8 dB**, against a
between city spread of 4.93 dB rooftop. The largest single lever in the study was
a number nobody could cite.

Two supporting reasons. Section 4.3 of `DEPLOYMENT_GEOMETRY.md` shows that across
3 863 228 European antennas the count above 6 GHz is zero, so no version of the
old law could ever be calibrated against a deployment. And `SENSITIVITY.md` shows
the cap dominating the height band by a wide margin, which says the model was
being steered by its least defensible parameter.

The facade tip law replaces an assumed outer edge with a physical one. Whether it
is the right physical one is a separate question and is still open.

## Which results survive and which need recomputing

The rule is one line. **A result that depends on the shape of `Q_S` needs
recomputing. A result that does not is fine.**

### Survives, no recomputation needed

| Result | Where | Why it survives |
| --- | --- | --- |
| Panorama coverage, registration counts, evidence reach | `COVERAGE.md`, `COVERAGE_LADDER.md`, `MATERIAL_REACH.md` | Geometry and image evidence. `Q_S` does not appear. |
| Closed loop guarantee, orders 1 to 3 | `MONOSTATIC.md`, `SPINE.md` evidence 1 | A statement about which surfaces a path touches. |
| Adjoint cost, 0.912 and 0.714 outward | `SPINE.md` evidence 2 | Same visibility measurement, read the other way. |
| Bounce budget, three interactions | `BOUNCE_BUDGET.md` | Truncation measured as a fraction of escaping power, before any weighting. |
| Sky fraction, 0.2271 at Korenmarkt | `MONOSTATIC_SBR.md` 2.7 | Pure geometry. |
| Mesh, fishnet, ground datum, walk | `FISHNET.md`, `GROUND_DATUM.md`, `WALK.md` | Scene construction. |
| Roughness, masonry, foliage | `ROUGHNESS.md`, `MASONRY.md`, `FOLIAGE.md` | Material and surface physics. |
| Transport check against Sionna RT | `CROSS_VALIDATION.md` | Tests the exit direction bins. The note already says it cannot test the illumination law, and that sentence is now the important one. |
| The material family conclusion | `SAM3_LADDER.md`, `MATERIAL_VLM.md` | Photographs establish a family, masonry against glass and metal, rather than tune a permittivity. The bracket is a material contrast and does not turn on the weight. |
| Every isotropic column, everywhere | throughout | The change does not touch the isotropic model. |
| Standpoint sampling as the dominant error term | `GROUND_DATUM.md`, `SPINE.md` ledger | A property of how many standpoints are drawn. |
| Zero deployed antennas above 6 GHz | `DEPLOYMENT_GEOMETRY.md` 4.3 | A count over a register. It applies to the new law too, which also cannot be calibrated. |
| Height flat against carrier frequency | `DEPLOYMENT_GEOMETRY.md` 4.4 | A measurement of what is deployed. |
| The argument for reporting a ratio at all | `SPINE.md`, `paper/body.tex` section 1 | Needs only that the absolute level is unknown and that a common multiplier cancels. **But the ratio's denominator is superseded, see below.** |

### Needs recomputing

| Result | Where | What has to be redone |
| --- | --- | --- |
| Between city spread, 4.93 dB rooftop and 9.58 dB street | `AGGREGATE_REBUILD.md`, `SPINE.md` R1, `paper/paper.tex` | Both directional numbers, and the counts 8 of 11 and 4 of 11 that go with them. |
| Within city spreads, rooftop and street columns | same | All of them. The isotropic column stands. |
| Rank correlations against isotropic, +0.936 and +0.345 | `SPINE.md` R1 | Both. |
| The whole law comparison, R2 | `SPINE.md` R2, `paper/paper.tex`, `outputs/law_comparison/` | It compares two laws that are now both superseded. The +5.67 and +3.98 dB shifts, the +1.05 to +6.33 dB range, the Spearman and Kendall figures, and the New York and Tokyo rank moves are all a comparison of old against older. |
| The below 5 degree measure share, and the Pearson -0.97 that explains the reordering | `SPINE.md` R2 | The mechanism is specific to a `1/sin^3` law with mass at its own support floor. The new law has no support floor of that kind. |
| Material shift decibels, rooftop and street columns | `SAM3_LADDER.md`, `MATERIAL_VLM.md`, `paper/paper.tex` | Both the shifts and the within square denominators they are quoted against, 8.4 dB rooftop and 16.7 dB street. |
| Every beamforming and antenna number | `BEAMFORMING.md`, `paper/paper.tex` | The aperture table, the direct path floor 0.6955 and 0.5054, the codebook column, the element pattern 0.256 and 10.225 dB, the 0.45 dB population average, the 0.62 and 1.07 dB effect, and the Kendall 0.818 and 0.709 ordering result. All are integrals against the old weights, and the population the element is averaged over is the old law's own measure. |
| Every bystander number outside the isotropic column | `BYSTANDERS.md`, `paper/paper.tex` | 1.40 dB street and 1.07 dB rooftop, the absorber control 1.069 to 1.332 and 1.396 to 1.607, the sent shares 88 % and 9 % below 5 degrees, and the arriving shares 0.212 and 0.185. The isotropic 0.070 and 0.708 dB pair stands. |
| Diffraction uplift, 0.15 dB rooftop and 0.42 dB street | `paper/body.tex`, `SPINE.md` ledger | Both. The 0.06 dB isotropic figure stands. |
| Crop convergence for the directional models, 100 m rooftop and 200 m street | `SPINE.md` R6, `paper/paper.tex` | Both radii, and therefore the argument that the published 250 m is set by the street model. The 60 m isotropic radius stands. |
| The range cap sweep, in full | `SENSITIVITY.md`, `SPINE.md` R6 | It sweeps a parameter the new law does not have. 7.40 and 9.24 dB, the `d^-1.2` fit, the 2.67 to 9.91 dB per site range, the support edge moving 7.7 to 1.9 degrees, the 0.51 dB contrast residual and the Spearman 0.81. Keep it as the diagnosis, do not carry it as a sensitivity band. |
| Height band edge elasticities, 0.3 to 1.9 dB | `SENSITIVITY.md`, `DEPLOYMENT_GEOMETRY.md` 7 | Same reason. There is no height band. |
| The crop against cap conflation, 0.5 to 7 % of rooftop from empty lines of sight and 20 % at New York | `SPINE.md` R6 | This is a statement about a cap reaching past the built extent. It has to be asked again as a different question, because the new law's source distance is read off geometry that is by construction inside the crop. |
| Monte Carlo floors, 0.0136 dB rooftop and 0.0343 dB street | `CODE_AUDIT.md`, `paper/si.tex` | Floors on old law integrals. The 0.0042 dB isotropic floor stands. |
| The seed replica result, 0.167 plus or minus 0.022 dB street | `CODE_AUDIT.md` 4.2, `SPINE.md` ledger | Street weighted. |
| The `S_0` brackets, 0.0075 to 3.0 and 0.010 to 4.1 W/m2 | `SPINE.md`, `paper/body.tex` | Quoted per deployment class, so both carry the old bands. The argument they support survives. |
| Unpolarised average, 7.8 % of rooftop measure and 0.4 % of street | `SPINE.md` ledger, `paper/body.tex` | Both shares are fractions of the old law's measure. |
| The illumination model table in the paper | `paper/body.tex`, table `tab:models` | It prints the eight endpoint numbers. It is a model definition and has to be rewritten rather than recomputed. |
| Figures 14, 15, 16, 17, 18, 19, 24 and 25 | `FIGURES/` | Regenerate. 18 and 19 are the hard cases, because they draw the height and range rectangles and the density those rectangles induce, so they do not survive as pictures at all. Figures 01 to 13 and 22 are geometry, materials or coverage and stand. `FIGURES/POLISH_NOTES.md` records per figure styling work on 15, 16, 18, 19, 24 and 25, which will have to be redone. |
| The definition of `chi` against open ground | `paper/body.tex` section 1, `SPINE.md` under "the quantity" | Superseded, not merely recomputed. Sites now sit on the buildings, so open ground has no network in it. See the denominator section above. |

### Open, and not yet a verdict

- **The converged crop radius.** The published 250 m came from the street model.
  Under the new law the source distance is read off the skyline rather than
  assumed, so the crop question changes shape and has to be asked again from
  scratch. Do not assume 250 m carries over and do not assume it shrinks.
- **The one dimensional elevation harvest.** Several sweeps are cheap because the
  old laws are uniform in azimuth, so one trace reduces to an elevation
  histogram and any band is a dot product. The facade tip law reads a skyline, so
  it is **not** azimuth uniform, and that reduction does not carry over unchanged.
  Anything built on it needs its machinery revisited, not just its numbers.
- **The headline claim that the square is close to the wrong unit.** A first
  measurement under the provisional closed form kept the claim standing, but that
  closed form is an approximation rather than the law, so the claim is currently
  unconfirmed and no number from that measurement may be used.

## What was archived

One file moved, and nothing was deleted.

`METHOD.tex` moved from `docs/` to `../archive/METHOD.tex`, with its built PDF
and its latexmk working files. It is an explanatory writeup of the old method,
and its worked example puts the source on a rooftop mast 80 m away, which is the
picture being dropped. `METHOD.md` replaces it. `../archive/README.md` records
what moved, why, and which parts of it were still good.

Nothing else was archived, and that is a judgement rather than an oversight. A
document that carries a measurement which is still true, or an argument that
survives, stays where it is with a marker on it. `DEPLOYMENT_GEOMETRY.md` is the
clearest case: it is wholly about the old law's eight numbers, and it stays,
because the finding that zero of 3.9 million European antennas sit above 6 GHz
matters more under the replacement than it did under the old law.
`SENSITIVITY.md` stays for the same kind of reason, since its cap sweep is the
measurement that condemned the cap.

## What was marked

Notes were added, and nothing else was rewritten or deleted. Every old number
stays where it was, because each is a correct record of a run that happened. The
notes say which law produced it and whether it still stands.

Documents carrying a header note, meaning the file as a whole predates the
change:

- `DEPLOYMENT_GEOMETRY.md`, which is wholly about the old law's eight numbers and
  is kept because section 4.3 is the evidence that the deployment being modelled
  does not exist, an argument that survives the change and matters more under it.
- `SENSITIVITY.md`, `PAPER_METHODS.md`, `REPORT.md`, `paper/PROVENANCE.md`,
  `paper/RECONCILE.md`.

Documents carrying section notes: `MONOSTATIC_SBR.md` 2.7 and 2.7.1, `SPINE.md`,
`AGGREGATE_REBUILD.md`, `../README.md`, `README.md`, `DECISIONS.md`,
`RERUNS.md`, `ROADMAP.md`, `CODE_AUDIT.md`, `CROSS_VALIDATION.md`,
`GROUND_DATUM.md`, `COVERAGE_LADDER.md`, `MATERIAL_VLM.md`, `SAM3_LADDER.md`,
`MATERIAL_REACH.md`, `BOUNCE_BUDGET.md`, `FOLIAGE.md`, `STATION_CALIBRATION.md`,
`CITIES.md`, `COVERAGE.md`, `PROPAGATION_BLENDS.md`, `WHY_NOT.md`,
`PROJECT_INTENT.md`, `MONOSTATIC.md`, `OVERNIGHT.md`, `FLOW_REVIEW.md`,
`PRIOR_ART.md`, `LIT_VERIFICATION.md`, `../FIGURES/README.md`,
`../outputs/exposure_korenmarkt/EXPOSURE_NOTES.md`, and `SI_NOTES.md`,
`DRAFT_NOTES.md`, `CITATIONS.md` and `STYLE_PASS.md` in `../paper/`.

Checked and found clean, needing no note: `DESIGN.md`, which never describes the
network at all, `PERFORMANCE.md`, `REMOTE_COMPUTE.md`, `WALK.md`, `FISHNET.md`,
`MASONRY.md`, `ROUGHNESS.md` and `../FIGURES/POLISH_NOTES.md`. That list is a
result too, and it is the shape of the change: the reconstruction half of the
study does not care what the illumination law is.

The LaTeX sources `paper/paper.tex`, `paper/body.tex` and `paper/si.tex` carry
their notes as comments, so the built PDF is unchanged. That is deliberate. The
paper still builds to 21 pages with no undefined references, and its numbers have
not been touched.

## What was not marked, and why

- **`semantic_twin/propagation/` and every other `.py` file.** The code is being
  changed separately. Nothing here edits it.
- **`BEAMFORMING.md` and `BYSTANDERS.md`.** Both were rewritten on 2026-08-03 by
  other work and were left alone to avoid a collision. Both are heavily affected,
  and their entries in the recompute table above stand whether or not the files
  themselves say so yet. **They still need marking.**

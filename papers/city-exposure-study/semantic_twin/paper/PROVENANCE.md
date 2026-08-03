# Provenance of every number in paper.tex and methods.tex

Audit date 2026-08-03. Read-only. Nothing in `paper.tex` or `methods.tex` was changed.

Every numeric claim in `paper/paper.tex` and `paper/methods.tex` was traced to a file
under `outputs/`, or recomputed from stored values, or marked as having no source.
Colleague reports in the top directory were used as leads only. Where a report and the
JSON disagree, the JSON wins and the disagreement is recorded as a finding.

The published cross city sweep is the `_L3` tag:
`outputs/exposure_korenmarkt/city250_L3_<site>_15ghz_locations.jsonl`, eleven sites,
80 standpoints each, 880 rows, no torn rows. Confirmed. Its manifest records
200000 rays, 512 launch cells, three interactions, roulette off, seed 7, 250 m crop,
3 m standpoint grid, 1 percent sky filter, 1.5 m head height. Every one of those
settings is stated correctly in the paper.

Ranking below is by how much a finding would change a reader's conclusion, not by how
many digits are wrong.

---

## Findings, ranked

### 1. The isotropic identity the paper offers as a validation check is false in the paper's own data

Both files state, in the Validation section, that "Under the isotropic model $\chi$ must
equal the sky fraction, because weighting all directions equally means the answer is the
open solid angle and nothing else, and the two are computed by different code paths."
The Models-used subsection repeats it: "under it $\chi$ is exactly the fraction of the
sphere that is open sky, which makes it a check on the estimator as well as a reference."

Recomputed over the 880 published standpoints of the `_L3` sweep:

| quantity | median | worst |
|---|---|---|
| $10\log_{10}(\chi_{\mathrm{iso}} / \mathrm{sky})$ | **+0.987 dB** | **+2.941 dB** |
| $10\log_{10}(\chi_{\mathrm{iso,dir}} / \mathrm{sky})$ | +0.0004 dB | 0.0651 dB |

Per site, median $\chi_{\mathrm{iso}}$ against median sky fraction: Korenmarkt
0.2916 against 0.2310, Brussels 0.2223 against 0.1702, New York 0.1694 against 0.1210.
The two are not equal and cannot be, because $\chi = \chi_{\mathrm{dir}} +
\chi_{\mathrm{ref}}$ and the reflected term is positive.

What is true is the statement the Estimator subsection already makes correctly: the
**direct** term equals the sky fraction, and it does so to 0.0004 dB. The Validation
subsection and the Models-used subsection generalise that to the whole ratio, which the
data contradicts by a decibel at the median. As written, a reader is told the estimator
passes an exact identity check that it fails by construction.

Ranked first because it is the only finding where the paper claims a check that its own
shipped output disproves, and because it appears in both files and twice in each.

### 2. methods.tex computes the direct share as one minus a sum of shares that are not a partition

`methods.tex` line 780: "Of all launched power, 10.7\% never touches a surface and
escapes straight to the sky ... A further 79\% interacts exactly once, 8.9\% twice,
1.2\% three times and 0.22\% ever again."

Source: `outputs/bounce_budget/korenmarkt_130m_bounce_evidence.json`,
`bounce_evidence.pooled_at_station_positions.share_of_launched_power_incident` =
`[0.789824, 0.088484, 0.011918, 0.001890, 0.000316, 0.000055, 0.000010, 0.000002]`.

That array is per-depth **arriving throughput**: the power still on the ray when it
reaches surface $k$, after $k-1$ reflection losses. It is neither cumulative nor
exclusive and its sum, 0.892499, means nothing. One minus that sum is 0.107501, which is
where 10.7 percent comes from. The forced arithmetic
$10.7 + 79 + 8.9 + 1.2 + 0.22 = 100.02$ is what makes it look like a partition.

The correct direct share is $1 - 0.789824 = 0.210176$, confirmed independently against
the tracer's own sky fraction: over the 40 walk standpoints, $1 -$ share[0] $= 0.236420$
and the mean sky fraction is 0.236420, identical to six decimals.

`paper.tex` has 21.0 percent and is right. It also uses the correct verb, "the shares
**reaching** the first, second, and third surfaces", where `methods.tex` says "interacts
**exactly** once / twice / three times", which the array is not. The true exclusive
ray-count partition, recoverable from the stored `hits` array, is 0.2102 never / 0.3090
once / 0.1529 twice / 0.0778 three times / 0.2501 four or more, which resembles neither
file.

`SPINE.md` line 168 already names this exact error and says it exists to prevent it.
`methods.tex` reintroduced it.

### 3. The bounce-budget power shares were measured at a 130 m crop and eight station positions, and the paper reports them as the setting of a 250 m study

`paper.tex` line 951 and the Discussion restatement at line 1490 give 21.0 percent
direct, 79 / 8.8 / 1.2 percent at the first three surfaces, 0.23 percent past the third,
truncated share 0.0037 median and 0.0201 worst, and "never moves a standpoint by more
than 0.063 dB". All of these come from
`outputs/bounce_budget/korenmarkt_130m_bounce_evidence.json`, whose `crop_radius_m` is
**130**, over the `pooled_at_station_positions` population of eight camera positions.

The Results preamble at line 1167 declares "a 250\,m crop, three surface interactions"
and "eleven squares ... 880 records".

The same quantities at the published 250 m crop
(`outputs/bounce_budget/korenmarkt_250m_bounce_evidence.json`):

| quantity | paper (130 m, stations) | 250 m, stations | 250 m, walk standpoints |
|---|---|---|---|
| direct share | **21.0%** | 23.3% | 22.6% |
| first surface | **79%** | 76.7% | 77.4% |
| second surface | **8.8%** | 8.68% | 8.42% |
| third surface | **1.2%** | 1.04% | 1.03% |
| past third | **0.23%** | 0.166% | 0.159% |
| truncated share, median / worst | **0.0037 / 0.0201** | 0.0044 / 0.0201 | |

`SPINE.md` line 205 warns about exactly this substitution for the coverage numbers
("Earlier notes quote the pair 10.5 % against 10.6 %, which is the Korenmarkt 130 m crop
and not the published 250 m one"). The warning was not carried to the power column.

The truncation bound is the more consequential half. `paper.tex` says "The share of
escaping power still in flight when the budget runs out is 0.0037 at the median
standpoint and 0.0201 at the worst, and every value reported here is a lower bound in
that sense." Recomputed over the 880 published standpoints from
`truncated_throughput_share` in the `_L3` location files: **median 0.005035, worst
0.079519** at Brussels. The worst published standpoint loses 8 percent of its escaping
power, not 2 percent.

Similarly "never moves a standpoint by more than 0.063\,dB" is the worst of the 40
Korenmarkt 130 m standpoints, roulette off. At the published 250 m crop, Brussels
`L3_roulette99` street reaches **0.384 dB** and Madrid 0.169 dB. The half-decibel claim
that follows it survives, but the 0.063 dB figure understates the published population by
a factor of six.

### 4. The whole material-discrimination subsection was run at a 130 m crop and six or twelve interactions, under a preamble that declares 250 m and three

All numbers in "Material discrimination bounds the claim" come from runs whose manifests
record a **130 m crop**:

| claim | source runs | crop | bounces | standpoints | rays |
|---|---|---|---|---|---|
| 0.024 / 0.029 / 0.022 dB, and spreads 3.9 / 8.4 / 16.7 dB | `sam3lad_walk_15ghz` vs `sam3lad_walk_facade_15ghz` | 130 m | 6 | 120 | 200k |
| $-0.218$ / $-0.156$ / $-0.024$ dB, 15 of 120, 2.020 dB | `sam3lad_walk_15ghz` vs `sam3lad_walk_sam3_15ghz` | 130 m | 6 | 120 | 200k |
| render / stone / metal bracket, 24 standpoints | `outputs/material_vlm/ablation.json` | 130 m | 12 | 24 | 60k |

Every value reproduces exactly from the JSON. The provenance defect is the label, not the
arithmetic. Three trace configurations sit inside one Results section whose preamble
names one of them, and the paper discloses only the standpoint counts, never the crop or
the bounce depth.

The sharpest consequence is that the paper now carries two different triples both called
the within-Korenmarkt spread:

- 3.9 / 8.4 / 16.7 dB, in the material subsection, from `sam3lad_walk_15ghz` at 130 m,
  6 bounces, 120 standpoints. Stored as `spread_db_p95_over_p05`, recomputed as
  3.8528 / 8.4288 / 16.7083.
- 2.85 / 6.39 / 8.43 dB, from the published `city250_L3_korenmarkt` run at 250 m,
  3 bounces, 80 standpoints, which is the Korenmarkt row of Table
  `tab:result-summary`.

Nothing in the text tells a reader they are different populations, and the street entry
differs by a factor of two.

The same substitution appears in the A6 paragraph: "Against a spread of 8.1\,dB within a
single square, 0.15\,dB changes nothing." The 8.1 dB is from `WHY_NOT.md` and is a walk
population figure; the published Korenmarkt rooftop within-square spread is 6.39 dB.

### 5. The deployment range cap swings are quoted over 50 to 500 m and were computed over 100 to 400 m

`paper.tex` line 1430: "Sweeping it from 50 to 500\,m changed the median absolute ratio
by 7.40\,dB rooftop and 9.24\,dB street. Between-city contrast changed by 0.51\,dB at the
median". The Validation section of both files repeats the pairing: "sweeping it from 50
to 500\,m never reaches a plateau ... worth 7.4\,dB at the median square for the rooftop
model ... the contrast between squares, which moves 0.51\,dB against that 7.4\,dB".

`outputs/sensitivity/sensitivity.json` stores the one-dimensional `d_max` axis over
**50 to 500 m** (91 points) but the `contrast` block over **100 to 400 m** (61 points).
Recomputing both quantities on both ranges from `one_dimensional.chi.d_max`:

| range | median absolute swing, rooftop | median absolute swing, street | median contrast swing, rooftop |
|---|---|---|---|
| 100 to 400 m | **7.398 dB** | **9.242 dB** | **0.507 dB** |
| 50 to 500 m | 10.601 dB | 15.485 dB | 0.741 dB |

So 7.40, 9.24 and 0.51 are all the 100 to 400 m numbers, correctly paired with each
other, and mislabelled with the wider range. The 14-times-steadier argument survives at
either range. The stated endpoints do not.

The contrast quantity itself is sound: `contrast_db` is each site's median $\chi$ in dB
relative to the cross-city mean, so it is genuinely a between-square quantity and not a
within-square spread. `spearman_endpoint_to_endpoint` = 0.8091 and `rank_changes` = 7
both trace exactly. Those two, unlike the swings, are computed on the 100 to 400 m grid
the paper does not name.

Note also that this whole sweep is harvested at 40 standpoints per site
(`locations_per_site` in `sensitivity.json`), not 80, and the file's `published_run`
field still says `city250_corrected`.

### 6. The bystander numbers in methods.tex are a whole generation behind, and two six-interaction leftovers survive in paper.tex

Everything in `outputs/bystander_study/` is the three-interaction retrace
(`max_bounces: 3`, `roulette_start: 4`, manifests written 2026-08-03T04:31 and 04:40).
The six-interaction generation survives only as a two-decimal stdout log,
`outputs/bystander_study_run.log`.

`methods.tex` quotes the superseded generation throughout:

| quantity | methods.tex | stored (3 interactions) |
|---|---|---|
| rooftop crowd loss | 1.0 dB | **1.06896791 dB** |
| isotropic crowd loss | 0.05 dB | **0.07001641 dB** |
| absorber "from" values | 0.05, 1.04, 1.39 | **0.070, 1.069, 1.396** |

Its absorber "to" values (0.71 / 1.33 / 1.61) are current, so the sentence splices two
budgets inside one comparison.

`paper.tex` is current in the Results subsection but carries two leftovers in the Body
coupling section: "cost a median 1.4\,dB under the street model and 1.0\,dB under the
rooftop model" (should be 1.07), and the arriving share "0.19" (stored value 0.18473,
which rounds to 0.18; 0.1850 was the six-interaction value).

### 7. A ratio in the Discussion is contradicted by a floor the same paper quotes

`paper.tex` line 1603: the crowd rerun found "every headline number moved by less than
the estimator's own noise floor for its column". The isotropic headline moved 0.070
against a six-interaction 0.049, a shift of **0.021 dB**, against the isotropic noise
floor of **0.009 dB** that the same paper quotes at line 1402. That is 2.3 times the
floor, not less than it. Rooftop (0.025 against 0.035) and street (0.005 against 0.112)
do satisfy the claim. The sentence is true for two of three columns and false for the
one the paper had already singled out as the interesting case.

### 8. The visible-direction cross check in methods.tex is the worst single site presented as a bound

`methods.tex` twice says the diffraction mask "reproduces the tracer's own direct term to
within 0.34\,\% for the isotropic model, 1.73\,\% for rooftop and 7.3\,\% for street".

Recomputed from `outputs/diffraction_bound/*_diffraction_bound.json` pooled over the 60
standpoints:

| model | pooled median | pooled worst | Times Square site median |
|---|---|---|---|
| isotropic | **0.189%** | **1.287%** | 0.336% |
| rooftop | **1.140%** | **6.443%** | 1.726% |
| street | **3.700%** | **23.045%** | 7.263% |

0.34 / 1.73 / 7.3 is the per-site median of the single worst site. It is neither a median
nor a bound, and the words "to within" make it a false bound: the actual worst
disagreements are 1.29, 6.44 and 23.05 percent. `paper.tex`'s "median disagreement ...
0.19\%, 1.14\%, and 3.70\%" and "worst ... 1.29\%, 6.44\%, and 23.05\%" are both exact.
This is the one check the paper offers as an independent code path, so overstating it is
material.

### 9. Two population statements in the evidence-reach paragraph are wrong

**"three continents".** The 42-standpoint closed-loop and outward-path medians
(1.000000 / 0.999972 / 0.980 and 0.999103 / 0.912004 / 0.714182) come from
`outputs/monostatic/monovis_{brussels_grandplace,korenmarkt,milan_duomo,tokyo_hachiko}_15ghz_visibility_locations.jsonl`.
Brussels, Ghent, Milan, Tokyo is **two** continents.

**"those four cities" is a different four.** The 0.941 to 0.999 coverage over 35 stations
comes from the four `*_250m_bounce_evidence.json` files, which are Brussels, Korenmarkt,
Madrid and Mexico City. The paragraph reads as if one four-city set carries both results.

**"0.941 to 0.999 ... across 35 stations" is a range over four pooled city values, not
over stations.** Stored `pooled_at_station_positions.walk.covered_fraction_by_power[0]`:
Brussels 0.997946, Korenmarkt 0.998948, Madrid 0.991904, Mexico 0.940949. The station
count 8+9+6+12 = 35 is right, but the per-station range over those 35 is **0.696 to
0.9998**. `BOUNCE_BUDGET.md` states both correctly; the paper compressed them.

**"beyond 40\,m every depth falls below 0.21" is false.** The 40 to 80 m bin of
`against_distance_from_nearest_station.walk` runs
`0.1056, 0.1895, 0.1986, 0.2113, 0.2069, 0.1994, 0.1849, 0.1481`. Bounce four is 0.2113.
On the `seen_by_the_ray_grid` layer four depths exceed 0.21, the largest being 0.2326.
The correct threshold is 0.22, or 0.24 on the grid layer.

**"the published walk, which spans 90\,m".** The panorama walk has a maximum pairwise
station separation of 56.0 m and a maximum radius from centre of 37.2 m
(`outputs/walk_korenmarkt/walk_selection.json`, `spread.baseline_m.max` and
`range_from_centre_m.max`). The 90 m is the standpoint sampling **radius**
(`walk.radius_m` in the run manifests). The 0.479 coverage figure is right; the span
attributed to it is not.

### 10. "the 3 most enclosed squares" is not what was run

The diffraction bound ran on Times Square, Grand-Place and Korenmarkt. Median sky
fraction over the eleven corrected 250 m runs ranks Korenmarkt **fourth**: New York
0.1138, Tokyo 0.1687, Brussels 0.1735, Korenmarkt 0.2310. Tokyo Hachiko is more enclosed
on median, on mean, and on the mean of its own 20 lowest standpoints, and it was not run.
The set is the two most enclosed plus the reference square. Both `paper.tex` and
`WHY_NOT.md` assert "the three most enclosed".

### 11. The beamforming ordering argument uses a wider axis than the paper's own headline

"reversing pairs up to 1.53\,dB apart rooftop and 2.97\,dB street on axes 5.6 and
9.8\,dB wide". All four numbers trace to `outputs/antenna/antenna11_250m.json`, which has
**32 standpoints per site**. The paper's headline between-square spreads, 4.93 and
9.58 dB, are the 80-standpoint `_L3` figures. The rooftop axes differ by 0.67 dB. A third
run, `eleven_city_law_ordering.json` at 40 standpoints, gives a third pair, 4.80 and
9.05 dB.

The qualitative conclusion is unaffected and would in fact be stronger against the
headline axis (1.53 / 4.93 = 31 percent rather than 27 percent), but two numbers ~200
lines apart are both described as the eleven-square spread and are not the same
measurement.

Related, and unstated: 0.818 is the worst of three grid rotations (0.818, 0.891, 0.927),
and "full digital maximum ratio transmission" maps to the `*_element` columns, not the
`*_matched` columns, which are exactly invariant. A reader who mapped it to `_matched`
would find the "two rooftop pairs" claim contradicted.

### 12. Orphans

Numbers with no artefact under `outputs/`.

| number | where it is used | only source |
|---|---|---|
| Monte Carlo standard errors 0.0042 / 0.0136 / 0.0343 dB | Discussion, and the "5.7 times" material claim, and the abstract's "roughly 25 times" | `CODE_AUDIT.md` section 4.1 |
| one-run sd 0.0624 dB, implied by "2.7 on one run" | Discussion | `CODE_AUDIT.md` section 4.2 |
| the eight per-seed draws behind $0.167 \pm 0.022$ dB | Discussion | `CODE_AUDIT.md` section 4.2 |
| "at most 0.03\,dB" retrace bound, and the six-interaction 0.049 / 1.044 / 1.391 it is computed from | Discussion, bystander scope paragraph | `BYSTANDERS.md` |
| 7.8\% of rooftop measure and 0.4\% of street, near $24^\circ$ | A7, and the honesty table | `WHY_NOT.md` line 825 |
| "+50\,dB" for a beam grid coarser than the aperture | Beamforming subsection | `BEAMFORMING.md` line 599 |
| "the array puts it 20 to 25\,dB down" | Beam pointing, both files | `BEAMFORMING.md` line 248 |

Two of these matter more than the rest.

The **entire Monte Carlo error model is unpersisted**. Four sentences and two
"N times the noise floor" claims rest on 0.0042 / 0.0136 / 0.0343 dB, on 0.0624, and on
eight per-seed medians that exist only in a markdown table. There is no seed-sweep JSON,
no per-seed medians, and no script under `semantic_twin/` that would reproduce them. The
numbers are internally consistent (mean of the eight draws is 0.16725, sample sd 0.0622
against the report's 0.0624, $0.0624/\sqrt{8} = 0.02206$, and $0.167/0.022 = 7.59$), but
none of it is reproducible from the repository.

The **7.8 / 0.4 percent polarization band** does reproduce as arithmetic, and I
recomputed it: integrating the counting law over $23.6 \pm 5^\circ$ gives 7.837 percent
of the rooftop measure and 0.403 percent of the street measure, matching `WHY_NOT.md` to
three digits. But the paper says "within a few degrees of $24^\circ$", and centring the
same $\pm 5^\circ$ window on $24^\circ$ gives 7.43 and 0.373 percent. The paper's stated
centre does not produce the paper's stated percentages, and $\pm 5^\circ$ is a
ten-degree-wide band rather than "a few degrees".

The "+50 dB" case is worse than an orphan. `ARTEFACT_CODEBOOKS = (8, 16, 32)` in
`antenna.py` line 1123 are all at least as fine as the aperture, so coarse grids were
never swept. The paper says they "were computed and excluded". They were excluded a
priori.

### 13. Smaller items, in descending order

**"a factor of 3.1 to 5.0" is a linear power ratio attached to decibel medians.** The
2 GHz medians 0.18 / 0.53 / 1.78 dB against the 15 GHz medians 0.06 / 0.15 / 0.42 dB give
3.09 / 3.44 / 4.22, that is 3.1 to 4.2. The "3.1 to 5.0" comes from the ratio of median
**linear** excess (3.137 / 3.594 / 4.963), which is what
`FIGURES/make_diffraction_bound_figure.py` prints. Correct, but a reader dividing the
numbers in the same sentence gets a different range.

**"88\% and 9\%, a ratio of nine".** Recomputed shares are 0.87858 and 0.09413, giving
9.334, so "a factor of nine" is right. The printed pair 88/9 gives 9.78, which rounds to
ten.

**"0.21 and 0.19, a ratio of 1.15"** in the Body coupling section of both files. The
stored arriving shares are 0.21164 and 0.18473, whose ratio is 1.1457. The rounded pair
in the text gives 1.105. Also 0.18473 rounds to 0.18, not 0.19; 0.19 is the
six-interaction value. The Results version of the same sentence, "0.212 and 0.185, a
ratio of 1.15", is correct.

**"same relative spread to three significant figures with roulette on and off".**
Stored: isotropic 6.955e-4 against 6.988e-4, rooftop 6.649e-3 against 6.684e-3, street
1.8626e-2 against 1.8634e-2. Two of three agree only to two significant figures.

**"2867 bodies"** is `bodies_median`, a median over 24 realisations spanning 759 to 4609
bodies, not a fixed count. The density 2.15 per square metre is per square metre of
**walkable** ground (median walkable fraction 0.4712, so about 1.01 per square metre of
disc). Neither file says walkable.

**The absorber contrast crosses standpoint sets.** The crowd arm ran 12 standpoints and
2 realisations; the absorber control ran **8 standpoints and 1 realisation**, with only 2
of 8 shared, a different walkable fraction (0.5292 against 0.4712), and a different crowd
(3220 bodies against 2867). Every "changed from X to Y" pair in that sentence compares
two different populations. `BYSTANDERS.md` flags this; neither `.tex` file does.

**Bibliography year.** Both files cite "Recommendation ITU-R P.2040-4, 2023". The run
manifests bind materials from "Recommendation ITU-R P.2040-4 (09/2025)". P.2040-3 is the
2023 revision. The revision number and the year do not belong to the same document.

**"10.2\,dB at the $60^\circ$ top of the band".** The band top in the paper's own Table
`tab:models` is $60.11^\circ$, where the taper is 10.264 dB. The 10.2 evaluates at a
round $60^\circ$.

**Element effect "1.07\,dB at Madrid" is aggregation-dependent.** It reproduces as a
median over 32 standpoints then a median over 11 squares. Taking the dB ratio of the
per-city median $\chi$ instead gives Madrid 1.14 and makes Brussels (1.22) the worst
square. The paper does not say which reduction it used.

**"confirms the geometric argument to about two parts in a thousand".** The worst of the
seven stations is 0.978159, which is 22 parts per thousand from 1, not 2. The median is
about 4 parts per thousand.

**The excluded station has no failure at the published crop.** The 0.362 first-interaction
coverage and the exclusion story are from `korenmarkt_130m_bounce_evidence.json`. The
250 m file has **nine** stations, none below 0.996503, built from a different evidence
file. `methods.tex` states this ("Re-registering the same camera for the wider binding
takes it to 1.000"); `paper.tex` drops the resolution and keeps only the exclusion.

---

## paper.tex against methods.tex

Every disagreement resolves in favour of `paper.tex`. `methods.tex` is consistently one
generation or one configuration behind.

| quantity | paper.tex | methods.tex | source value | verdict |
|---|---|---|---|---|
| direct share of launched power | 21.0% | 10.7% | 0.210176 | methods.tex wrong, and wrong by the non-partition mechanism |
| second-surface share | 8.8% | 8.9% | 0.088484 | paper.tex rounds correctly |
| share past third | 0.23% | 0.22% | 0.002273 | paper.tex rounds correctly |
| depth semantics | "shares reaching" | "interacts exactly $k$ times" | per-depth arriving throughput | methods.tex mislabels the quantity |
| worst L3 against L8 deviation | 0.063 dB | 0.12 dB | 0.062591 roulette off, 0.115642 roulette on | paper.tex matches the shipped config |
| truncated escaping share | 0.0037 / 0.0201 | 0.0038 / 0.021 | roulette off / roulette on rows | paper.tex matches the shipped config |
| roulette verdict | "changes neither variance nor work" | "a worse estimator at the same cost" | roulette-on spread is marginally **lower** on all three models | methods.tex contradicted by data |
| visible-direction check | median 0.19 / 1.14 / 3.70%, worst 1.29 / 6.44 / 23.05% | "to within" 0.34 / 1.73 / 7.3% | pooled median and worst | methods.tex quotes one site as a bound |
| street diffraction uplift median | 0.42 dB | 0.44 dB | 0.4218 over 56, 0.4350 over the mixed 60 | methods.tex stale, and inconsistent with its own next sentence |
| 2 GHz street median | 1.78 dB | 1.82 dB | 1.7788 over 56 | methods.tex stale |
| crowd rooftop loss | 1.07 dB (Results), 1.0 dB (Body coupling) | 1.0 dB | 1.06896791 | methods.tex stale, paper.tex stale in one place |
| crowd isotropic loss | 0.070 dB | 0.05 dB | 0.07001641 | methods.tex stale |
| absorber "from" values | 0.070 / 1.069 / 1.396 | 0.05 / 1.04 / 1.39 | current run | methods.tex stale |
| crowd density | 2.15 per m$^2$ | "two people per square metre" | 2.152782 | paper.tex precise |
| delay spread | "recorded per standpoint but is not analysed in this paper" | "Both are reported alongside $\chi$" | `mean_excess_delay_ns` is stored per standpoint | non-numeric contradiction |
| eighth station | excluded, no resolution given | excluded, re-registration to 1.000 given | 250 m run has no failing station | methods.tex more complete |

---

## Full provenance table

Verdicts: **T** traced, **D** derived and recomputed here, **S** stale, **O** orphan.
Arithmetic is shown for every D.

### Abstract and introduction

| claim | value | verdict | source |
|---|---|---|---|
| standpoints, squares | 880, eleven | T | `city250_L3_*_locations.jsonl`, 11 files x 80 rows |
| between-square spreads | 3.71 / 4.93 / 9.58 dB | D | recomputed 3.7064 / 4.9297 / 9.5804 from `_L3` medians, $10\log_{10}(\max/\min)$ |
| median within-square spreads | 3.92 / 5.46 / 8.43 dB | D | recomputed 3.9171 / 5.4628 / 8.4324, median of per-site $10\log_{10}(p_{95}/p_{05})$ |
| "fell 1.15 dB short for street cells" | 1.15 dB | D | $9.5804 - 8.4324 = 1.148$ |
| law residual rms | 1.39 / 0.98 dB | T | `law_comparison/eleven_city_law_ordering.json`, `residual_rms_db` 1.3925 / 0.9772 |
| standpoint resampling rms | 0.128 / 0.061 / 0.188 dB | see Discussion row | |
| "roughly 25 times the isotropic Monte Carlo error" | 25 | D, denominator O | $0.128 / 0.0051 = 25.1$, using the walk-median floor rescaled to 80 standpoints; 0.0051 exists only in `CODE_AUDIT.md` |
| material medians | 0.024 / 0.029 / 0.022 dB | D | recomputed from `sam3lad_walk` and `sam3lad_walk_facade` location files: $+0.024469$, $+0.029092$, $+0.022402$ |
| diffraction uplifts | 0.06 / 0.15 / 0.42 dB | D | pooled medians 0.0595 / 0.1543 / 0.4218 from the three `*_diffraction_bound.json` |
| open-ground level, rooftop | 0.0075 to 3.0 W/m$^2$ | D | $S_0 = P\nu/4\pi \oint(\rho_+-\rho_-)d\Omega$ with $\nu = $ areal density / 30 m, $\oint = 357.28$ m: 25/km$^2$ at 55 dBm gives 0.007492, 100/km$^2$ at 75 dBm gives 2.997 |
| open-ground level, street | 0.010 to 4.1 W/m$^2$ | D | same with $\oint = 65.663$ m, slab 4 m: 0.010327 to 4.131 |
| "nearly three orders of magnitude" | | D | $4.131/0.00749 = 551$, i.e. 2.74 decades |
| ICNIRP reference level | 10 W/m$^2$ | T | ICNIRP 2020, general public, 2 to 300 GHz |

### Assumptions

| claim | value | verdict | source |
|---|---|---|---|
| A1 far-field onset | $2D^2/\lambda = 9$ m | D | $2(0.3)^2/0.019986 = 9.006$ m |
| A1 closest source | 10 m | T | street band `range_band_m` lower edge |
| A2 phase turn | $3.1\times10^4$ rad | D | $k = 314.377$ rad/m, $\times 100$ m $= 3.1438\times10^4$ |
| A2 cells needed | $10^{10}$ against 512 | D | $4\pi(kR)^2 = 1.242\times10^{10}$; 512 is `local_cells` in the manifest |
| A4 street below $5^\circ$, counting | 88% | D | numerical integration of $Q \propto \rho_+^3-\rho_-^3$: **0.87858** |
| A4 street below $5^\circ$, spreading | 42% | D | same with $\rho_+-\rho_-$: **0.42182** |
| A6 diffracted amplitude | $1/56$, 35 dB | D | $ks = 314.377 \times 10 = 3143.8$, $\sqrt{} = 56.07$, $10\log_{10}(3143.8) = 34.97$ dB |
| A6 excess loss growth, corner | 3.0 to 3.5 dB/decade against 10 | T | `ericsson`, `mmmagic`, checked in `LIT_VERIFICATION.md` |
| A6 over-the-top beats scattering | 7 dB fit error | T | `adhikari` |
| A6 mask grid | 720 x 600 | T | `diffraction_bound/*.json`, `grid.azimuth` 720, `grid.elevation` 600 |
| A6 visible-direction check | 0.19 / 1.14 / 3.70%, worst 1.29 / 6.44 / 23.05% | D | pooled median and max over 60 (56 street) standpoints |
| A6 bound population | 20 standpoints, 3 squares, 60 total | T, label wrong | `bound_diffraction.py` selects the 20 lowest sky fraction per site; see finding 10 for "3 most enclosed" |
| A6 uplift medians | 0.06 / 0.15 / 0.42 dB | D | 0.0595 / 0.1543 / 0.4218 |
| A6 against 8.1 dB within a square | 8.1 dB | S-population | walk population figure from `WHY_NOT.md`; the published Korenmarkt rooftop spread is 6.39 dB |
| A6 2 GHz medians | 0.18 / 0.53 / 1.78 dB | D | 0.1840 / 0.5308 / 1.7788 |
| A6 factor | 3.1 to 5.0 | D, mislabelled | linear-excess ratios 3.137 / 3.594 / 4.963; the dB medians give 3.1 to 4.2 |
| A6 street measure below $5^\circ$ | 87.9% | D | 0.87858 |
| A6 worst street standpoint | 12.64 dB | T | Grand-Place index 232, uplift 12.6397 dB, $\chi_{\rm street} = 1.53\times10^{-4}$, 6th smallest of 878 |
| A6 fully occluded standpoints | 4 of 60 | T | Grand-Place indices 1062, 1049, 191, 204, all `street_small_cell_direct_traced = 0` |
| A6 counter-citation corner loss | about 2 dB against 40 dB | T | `duchizhik`; `SPINE.md` gives 2.2 dB and $-42$ dB |
| A7 XPR at zero excess loss | 28 dB, half a dB per dB | T | `karttunen`, pooled model; `LIT_VERIFICATION.md` section 2.2 |
| A7 even split needs | 56 dB | D | $28/0.5 = 56$ |
| A7 TE bound | 3.0 dB | T | `WHY_NOT.md` section 4.3 gives 3.01 dB |
| A7 pseudo-Brewster | $66^\circ$ incidence, tens of dB | T | 66.435$^\circ$ for concrete, TM minimum $-35.0$ dB |
| A7 band share | 7.8% rooftop, 0.4% street | D, O | $23.6\pm5^\circ$ gives 7.837% and 0.403%; the paper's stated $24^\circ$ centre gives 7.43% and 0.373%; no artefact under `outputs/` |

### Configuration and illumination model

| claim | value | verdict | source |
|---|---|---|---|
| crop radius | 250 m | T | every `_L3` manifest, `crop_radius_m` |
| standpoints per square | 80 | T | `locations_requested` and `locations_traced` |
| grid spacing | 3 m | T | `walk.spacing_m` |
| sky filter | 1% | T | `walk.min_sky_fraction` = 0.01 |
| candidates kept against traced | 801 against 80, Korenmarkt | T | `walk.candidates_after_clearance` |
| head height | 1.5 m | T | `walk.head_height_m` |
| rooftop band | 13.5 to 43.5 m, 25 to 250 m | T | manifest `illumination_models.rooftop` |
| street band | 2.5 to 6.5 m, 10 to 150 m | T | manifest `illumination_models.street_small_cell` |
| rooftop elevation support | 3.09 to 60.11 deg | D | $\arctan(13.5/250) = 3.0910$, $\arctan(43.5/25) = 60.1135$ |
| street elevation support | 0.95 to 33.02 deg | D | $\arctan(2.5/150) = 0.9548$, $\arctan(6.5/10) = 33.0239$ |
| element taper at median elevation | 0.26 dB at $9.5^\circ$ | D | 3GPP TR 38.901 Table 7.3-1, $12(9.5/65)^2 = 0.2563$; median of the rooftop measure on $d\Omega$ recomputed as $9.4969^\circ$ |
| element taper at band top | 10.2 dB at $60^\circ$ | D | $12(60/65)^2 = 10.2249$; at the true top $60.11^\circ$ it is 10.264 |
| off-axis suppression | 20 to 25 dB | O | `BEAMFORMING.md` only; the code's own 8x8 model gives $-17.1$ dB mean at $20^\circ$ |

### Estimator and bounce budget

| claim | value | verdict | source |
|---|---|---|---|
| launch cells $M$ | 512 | T | `trace_config.local_cells` |
| rays $N$ | 200000 | T | `trace_config.rays` |
| bounce budget $L$ | 3 | T | `trace_config.max_bounces` |
| closed-loop visibility | 1.000000 / 0.999972 / 0.980 | T | pooled medians over 42 records in the four `monovis_*_visibility_locations.jsonl`; order 3 is 0.979514 |
| spread across the four cities | "a few percent" | D | order 3 per city 0.9760 to 0.9842, spread 0.8 percentage points |
| "four meshes on three continents" | | S | the four are Brussels, Ghent, Milan, Tokyo, i.e. two continents |
| outward path visibility | 0.999103 / 0.912004 / 0.714182 | T | same files, `open_path_chain_observed` |
| "9%" and "29%" | | D | $1-0.912004 = 0.0880$, $1-0.714182 = 0.2858$ |
| seven of eight stations | 0.978 to 0.999 | T | `korenmarkt_130m_bounce_evidence.json`, station bounce-1 values 0.978159 to 0.999338 |
| eighth station | 0.362 | T | 0.361937 |
| eight metres apart | 8 m | D | ENU $(2.418,-0.884)$ against $(-3.522,-6.312)$, distance 8.05 m |
| second interaction within 20 m | 93 to 96% | T | distance bins 0-5, 5-10, 10-20: 0.9585, 0.9508, 0.9327 |
| third interaction within 20 m | about 89% | T | 0.8986, 0.8941, 0.8832 |
| beyond 40 m all depths | below 0.21 | S | bounce 4 is 0.2113 on the walk layer, up to 0.2326 on the grid layer |
| pooled first-interaction coverage | 0.479 | T | `pooled_walk_standpoints_only.walk.covered_fraction_by_power[0]` = 0.479251 |
| "walk spans 90 m" | 90 m | S | the panorama walk spans 56.0 m; 90 m is the standpoint radius |
| station coverage over 35 stations | 0.941 to 0.999 | S-label | that is the range of four **pooled** city values; the per-station range is 0.696 to 0.9998 |
| direct share of launched power | 21.0% | T at 130 m | $1 - 0.789824$; at the published 250 m crop it is 23.3% |
| first / second / third surface shares | 79 / 8.8 / 1.2% | T at 130 m | 0.789824 / 0.088484 / 0.011918; at 250 m 76.7 / 8.68 / 1.04 |
| past the third | 0.23% | D at 130 m | $\sum$ share[3:] $= 0.002273$; at 250 m 0.00166 |
| L3 against L8, median | 0.002 dB | T | model medians 0.0015 / 0.0023 / 0.0026 |
| L3 against L8, worst | 0.063 dB | T at 130 m | 0.062591 roulette off; at 250 m Brussels reaches 0.384 dB |
| none of 40 moves half a dB | 0 | T | `standpoints_over_0p5_db` = 0 in both L3 rows at Korenmarkt |
| truncated share | 0.0037 / 0.0201 | T at 130 m | 0.003686 / 0.020125; over the 880 published standpoints, 0.005035 / 0.079519 |
| roulette floor and inflation | 0.05, twentyfold | T | `tracer.py` line 286, `roulette_floor = 0.05`, $1/0.05 = 20$ |
| roulette wall times | 101 and 100 s | T | 100.894 and 100.450 s |
| roulette spread agreement | "three significant figures" | S | agrees to two on isotropic and rooftop |
| cost | $O(NL\log T)$, $T$ = 617091 | T | `mesh_triangles` |

### Results

| claim | value | verdict | source |
|---|---|---|---|
| Table `tab:result-summary`, all 12 cells | see abstract rows | D | recomputed exactly; isotropic 3.7064, 1.6994/3.9171/6.4568, 6 of 11; rooftop 4.9297, 2.5492/5.4628/12.8933, 8 of 11; street 9.5804, 4.8025/8.4324/19.0062, 4 of 11 |
| largest sampled median | Mexico Zocalo | T | top of both the isotropic and rooftop `_L3` orderings |
| Krakow datum correction | $-1.40$ iso, $-12.97$ street | D | `_corrected` against `_L3` medians: $-1.4021$, $-12.9724$ |
| Toulouse datum correction | $-1.29$, $-2.61$ | D | $-1.2943$, $-2.6078$ |
| every other square under 0.25 dB isotropic | | D | largest other is Brussels at $-0.2439$ |
| Spearman against isotropic | $+0.936$, $+0.345$ | D | recomputed 0.9364 and 0.3455 on the eleven `_L3` medians |
| Korenmarkt law shift at 250 m | 5.67 / 3.98 dB | T | `korenmarkt_law_comparison.json`, `rooftop_law_shift_db["250"]` = 5.6733, street 3.9810. At 130 m these are 2.54 and 0.84, so the paper quotes the right crop |
| rooftop shift range and mean | $+1.05$ to $+6.33$ about $+5.14$ | T | 1.0489, 6.3278, 5.1418 |
| street shift range and mean | $+1.45$ to $+4.41$ about $+3.43$ | T | 1.4540, 4.4060, 3.4342 |
| residual rms | 1.39 / 0.98 dB | T | 1.3925, 0.9772 |
| earlier against corrected Spearman | $+0.65$, $+0.88$ | T | 0.6455, 0.8818 |
| rank changes | 9 rooftop, 8 street | T | `rank_changes` |
| New York 1st to 9th, Tokyo 4th to 8th | | T | `rank_old`/`rank_new` and the stored orderings |
| drop-one Spearman | $+0.98$, no move over one place | D | recomputed 0.9758 both models, max rank move 1 |
| Pearson residual against low-elevation share | $-0.97$ | D | recomputed $-0.9745$ against the old-law share below $5^\circ$ |
| material shifts | 0.024 / 0.029 / 0.022 dB | D | see abstract row; **130 m crop, 6 bounces, 120 standpoints** |
| within-Korenmarkt spreads | 3.9 / 8.4 / 16.7 dB | D | 3.8528 / 8.4288 / 16.7083 on the baseline arm, same 120-standpoint 130 m population |
| 0.024 dB is 5.7 times 0.0042 dB | 5.7 | D, denominator O | $0.024/0.0042 = 5.714$; 0.0042 is in `CODE_AUDIT.md` only |
| whole-field change | $-0.218$, 15 of 120, 2.020 dB, $-0.156$, $-0.024$ | D | recomputed $-0.2179$, 15/120, $-2.0196$, $-0.1564$, $-0.0242$. The worst standpoint **decreased** by 2.020 dB; the sign is dropped |
| dielectric bracket | $-0.104$, $+0.239$, $-0.164$, $+0.414$ | T | `material_vlm/ablation.json`, `pure_plasterboard_m0` and `pure_marble_m0` paired medians, 24 standpoints |
| dielectric span | 0.34 / 0.58 dB | D | $0.239497-(-0.104090) = 0.343588$; $0.413837-(-0.163543) = 0.577380$ |
| metal | $+2.502$, $+4.374$, 24 of 24 | T | `pure_metal_m0` |
| steering table, 12 cells | | T | `antenna/paper_artefact_250m.json`, all twelve match to 3 decimals |
| retrace standpoints | 20 | T | `arguments.locations` |
| 8x8 percentiles | $-0.49$/$-0.25$, $-2.53$/$-1.09$ | T | reproduced exactly; percentiles taken on linear suppression, both inside the 20-point sample |
| direct fractions | 0.6955, 0.5054 | T | `summary.*.direct_measure`, median over the same 20 standpoints |
| floors | $-1.58$, $-2.96$ dB | D | $10\log_{10}(0.695538) = -1.5768$, $10\log_{10}(0.505450) = -2.9632$ |
| 32x32 reaches 96% of floor | 96% | D | $2.85224/2.96322 = 0.9626$ |
| codebook values | $-0.25$/$-1.54$, $-0.37$/$-1.61$, $-0.37$/$-1.66$ | T | all six stored |
| codebook granularity under 0.15 dB | | D | largest relevant gap is codebook8 against exact 8x8 rooftop, $0.375506-0.252703 = 0.1228$ |
| coarse grid returns $+50$ dB | | O | never swept; `ARTEFACT_CODEBOOKS = (8,16,32)` |
| element averaged over rooftop measure | 0.45 dB | D | measure-weighted mean gain 0.901278, i.e. 0.4514 dB down |
| element effect on the ratio | 0.62 median square, 1.07 Madrid | T, aggregation-dependent | nested median over 32 standpoints then 11 squares; the alternative reduction gives Madrid 1.14 and Brussels 1.22 |
| "two to four times" | | D | $0.6203/0.25633 = 2.42$, $1.0734/0.25633 = 4.19$ |
| Kendall under antenna policies | 0.818, 0.709 | D | recomputed $\tau_b$ over 55 pairs: 0.8182, 0.7091 |
| reversed pair gaps | 1.53, 2.97 dB | D | 1.5295 Madrid against Tokyo, 2.9675 Mexico against Tokyo |
| axis widths | 5.6, 9.8 dB | T, different population | 5.5941 and 9.7865 over **32** standpoints per site; the headline 4.93 / 9.58 are over 80 |
| MRT reversals | none street, two rooftop at 0.58 dB or less | D | `*_element` columns, $\tau = 1.000$ and 0.9273, gaps 0.5812 and 0.0150 |
| crowd density and bodies | 2.15 per m$^2$, 2867 | T, label loose | 2.152782, `bodies_median` over 24 realisations spanning 759 to 4609, per walkable m$^2$ |
| crowd losses | street 1.40, rooftop 1.07 dB | T | $-1.39606$, $-1.06897$ |
| ratio of losses | 1.3 | D | $1.39606/1.06897 = 1.3060$ |
| arriving shares | 0.212, 0.185, ratio 1.15 | D | 0.211643, 0.184726, ratio 1.1457 |
| isotropic crowd change | 0.070 dB | T | $-0.0700164$ |
| noise floors | 0.009 / 0.035 / 0.112 dB | T | `korenmarkt_15ghz_noise_floor.json`, `median_abs_db` 0.008654 / 0.035428 / 0.112325 |
| ratios to the floor | 8, 30, 12 | D | $0.070016/0.008654 = 8.09$; $1.068968/0.035428 = 30.17$; $1.396061/0.112325 = 12.43$ |
| isotropic 5th and 95th percentiles | $-0.59$, $+0.04$ | T | $-0.590707$, $+0.039015$, reproduced from the rows file; interpolated between adjacent sample members |
| absorber control | 0.708 / 1.332 / 1.607 dB | T | current absorber summary; but the run is 8 standpoints against the crowd arm's 12 |
| 0.3 per m$^2$ costs 0.5 and 0.3 dB | | T | $-0.495046$, $-0.331506$ |
| crowd geometry | 13 / 2.6 / 0.4 m | D | $0.23/\tan(1^\circ) = 13.18$, $/\tan(5^\circ) = 2.629$, $/\tan(30^\circ) = 0.398$; $1.73-1.50 = 0.23$ |
| crop convergence radii | 60 / 100 / 200 m | D | recomputed from `crop_convergence/korenmarkt_crop_convergence.json` at a 0.5 dB criterion: isotropic and sky at 60 m, **rooftop at 160 m**, street at 250 m. See the unsettled section |
| 130 to 250 m change | $-0.06$ / $-0.56$ / $-7.05$ dB | D, near | recomputed on the same file: $-0.031$ / $-0.653$ / $-7.404$ on medians. See the unsettled section |
| range cap absolute swing | 7.40 / 9.24 dB | D, range mislabelled | 7.398 / 9.242 over **100 to 400 m**; over 50 to 500 m they are 10.601 / 15.485 |
| between-city contrast swing | 0.51 dB | D, range mislabelled | 0.5072 over 100 to 400 m; 0.741 over 50 to 500 m |
| endpoint Spearman and rank changes | 0.81, 7 of 11 | T | `contrast.spearman_endpoint_to_endpoint` = 0.8091, `rank_changes` = 7 |
| $\rho_+^{-1.2}$ | $-1.2$ | D | median log-log slope $-1.181$ over 50 to 500 m, $-1.287$ over 100 to 400 m |

### Discussion

| claim | value | verdict | source |
|---|---|---|---|
| standpoints replaced | 56 to 76 of 80 at eight sites | D | complement of `SPINE.md`'s "4 to 24 survived"; eight is right because Korenmarkt keeps all 80 and Krakow and Toulouse are the two large movers |
| per-city median rms | 0.128 / 0.061 / 0.188 dB | D | over the eight small-mover sites, `_corrected` against the fixed-datum run |
| largest changes | 0.242 / 0.116 / 0.326 dB | D | same population |
| "7 to 47 times their Monte Carlo floors" | 7 to 47 | D, denominator O | against the rescaled floors 0.0051 / 0.0167 / 0.0420: largest changes give $0.116/0.0167 = 6.9$ and $0.242/0.0051 = 47.5$. The rms values against the same floors give 3.7 to 25.1, so "these values" must mean the largest changes only |
| monostatic first-order share | 98.6% | T | `monostatic/mono250_correlations.json` |
| two-way range | 4.05 m | T | same |
| return medians | $-70.81$ against $-70.99$ dB | T | same |
| pooled Spearman, partial, sky | $-0.526$, $-0.010$, $+0.961$ | T | same |
| second-order partial and share | $-0.345$, 0.37%, 24 dB below | T, D | $10\log_{10}(0.986/0.0037) = 24.3$ dB |
| cross-validation agreement | 0.25 / 0.16 dB against a 0.24 to 0.46 dB floor | T | `outputs/cross_validation/`; second square is Brussels Grand-Place |
| walk median standard errors | 0.0042 / 0.0136 / 0.0343 dB | O | `CODE_AUDIT.md` section 4.1 only |
| superseded street value | 0.079 dB | T | `coverage_ladder_conflict_gated_15ghz.json`, rung `clean_walk9`, `chi_street_small_cell.distribution_median_shift_db` = 0.07854. The "lowest of eight seed draws" qualifier is `CODE_AUDIT.md` only |
| seed-averaged shift | $0.167 \pm 0.022$ dB | O | `CODE_AUDIT.md` section 4.2; internally consistent, mean 0.16725, sd 0.0622, $0.0624/\sqrt8 = 0.02206$ |
| 7.6 and 2.7 standard errors | | D | $0.167/0.022 = 7.59$; $0.167/0.0624 = 2.68$. The 0.0624 appears nowhere in the paper |
| earlier headline | 0.298 dB | T | same file, `chi_rooftop_fixed_height.distribution_median_shift_db` = 0.29798, and the file's own `law_note` confirms it is the superseded law |
| crowd retrace bound | at most 0.03 dB | O | the six-interaction run was overwritten; only a 2 dp stdout log survives |
| honesty table, all rows | | T | each row traces to the corresponding result above |

---

## What could not be settled

**The crop-convergence radii do not reproduce cleanly.** The paper says isotropic and
sky fraction converged at 60 m, rooftop at 100 m and street at 200 m under a criterion of
"the smallest radius from which every later step stayed below 0.5\,dB". Applying that
criterion literally to `outputs/crop_convergence/korenmarkt_crop_convergence.json`, on
medians, I get isotropic and sky at 60 m (agreeing), **rooftop at 160 m** and **street at
250 m**, because the 130 to 160 m rooftop step is $-0.538$ dB and the 200 to 250 m street
step is $-0.858$ dB. On means the answer moves again. The paper's "street illumination at
200\,m" and the sentence that follows it, "the common 250\,m operating point was
therefore set by the street model alone and lay one crop step past the criterion", would
become "set by the street model at the criterion" under my reading. Settling this needs
the reduction the figure script actually uses: whether the step is scored on the mean or
the median, whether it is signed or absolute, and whether the criterion is applied to the
step or to the offset from the widest crop.

**The 130 to 250 m crop deltas differ from my recomputation.** The paper gives $-0.06$,
$-0.56$, $-7.05$ dB. On the same file, on medians, I get $-0.031$, $-0.653$, $-7.404$;
`run_law_comparison.py` on a different 40-standpoint observer set gives $-0.513$ rooftop
and $-6.941$ street. Three near-but-not-equal triples exist and the paper does not say
which observer set or which statistic it took. The conclusion is unaffected. The
provenance is not clean.

**The Monte Carlo error model cannot be reproduced at all.** 0.0042 / 0.0136 / 0.0343 dB,
the rescaled 0.0051 / 0.0167 / 0.0420, 0.0624, and the eight per-seed medians exist only
in `CODE_AUDIT.md`. Two "N times the noise floor" claims, the abstract's "roughly 25
times", the material result's "5.7 times" and the Discussion's "7 to 47 times" all rest
on them. Settling this needs the eight-seed retrace rerun with its per-seed medians
written to `outputs/`. `CODE_AUDIT.md` records that the original run cost about two hours
and its raw output was discarded, and no script under `semantic_twin/` reproduces it.

**The six-interaction bystander run is gone.** "these paired shifts moved by at most
0.03\,dB from the earlier six-interaction run" cannot be checked, because the retrace
overwrote the summary and rows. Reconstructing the comparison from the surviving
two-decimal stdout log puts the rooftop move at 0.031 dB, right on the bound, so the
claim has no margin. Settling this needs the six-interaction arm re-run under a
distinct tag.

**"Best-beam selection" and the coarse-grid $+50$ dB are both unmeasured.** The paper is
explicit that best-beam needs a finite-site trace it has not run, which is honest. It is
less explicit that coarse grids "were computed and excluded" when the artefact generator
never swept them. Settling the second needs either a sweep or a rewording.

**The absorber control's standpoint set.** Whether the 0.708 against 0.070 contrast
survives on a matched set is untested: the two arms share only 2 of 8 standpoints and
carry different crowds. Settling this needs the absorber arm re-run on the crowd arm's
12 standpoints.

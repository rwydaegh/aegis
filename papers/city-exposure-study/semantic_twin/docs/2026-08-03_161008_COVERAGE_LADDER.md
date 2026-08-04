# Does the one square material result travel? Yes, to all seven

The eleven square headline table was run with `--materials geometric` everywhere, so no number in it
depends on a photograph. Until now the only answer to "does that matter" came from one square. It now
comes from seven at the published 250 m crop and six at 130 m, and the answer is the same at every
one of them.

**Replacing the orientation rule with image evidence raises the rooftop exposure median at all seven
squares. The shift runs from +0.17 to +0.50 dB at 250 m and every square is resolved, the least
resolved sitting five standard errors from zero and the best resolved fifty one.** There is no square
where the effect vanishes and no square where it reverses.

The second finding is the one that could not have come from a single square, and it is a null.
**Tripling the bound area does not increase the shift.** Running the same six squares at the 130 m
crop, where two to four times as much of the scene carries evidence, moves the typical standpoint's
shift by between -0.04 and +0.05 dB. Whatever the image evidence is worth, it is not worth more when
more of the square has it.

> **Old illumination law, see `LAW_CHANGE.md`.** Both headline findings are stated on
> the rooftop model, whose sources sit in a height band and a range band above the
> head. The sign of the effect and the null on bound area survive, because both sides
> of every comparison carry the same weights, and every decibel quoted is an old law
> number.

## The seven squares, at 250 m

Every run is 80 standpoints at 200,000 rays on the 250 m mesh the headline table uses, repeated over
four disjoint seed streams, 320 standpoints per row. The shift is the ratio of the two distribution
medians in dB, the image bound rung against the geometric rung on the same standpoints. The
uncertainty is the standard error over the four seeds.

Fused stations, the `walk` rung.

| Square | Bound area | Seen area | Stations | Rooftop shift | Isotropic shift | Street shift |
| --- | --- | --- | --- | --- | --- | --- |
| Korenmarkt | 3.2 % | 3.3 % | 9 | **+0.501 +/- 0.035** | +0.320 +/- 0.044 | +0.580 +/- 0.065 |
| Mexico Zocalo | 6.6 % | 7.0 % | 12 | **+0.354 +/- 0.058** | +0.167 +/- 0.043 | +0.162 +/- 0.044 |
| Brussels Grand-Place | 4.5 % | 4.6 % | 8 | **+0.347 +/- 0.035** | +0.092 +/- 0.039 | +0.462 +/- 0.051 |
| Madrid Plaza Mayor | 5.1 % | 5.1 % | 6 | **+0.302 +/- 0.006** | +0.346 +/- 0.028 | +0.446 +/- 0.032 |
| Milan Duomo | 4.0 % | 4.0 % | 1 | **+0.221 +/- 0.017** | +0.125 +/- 0.021 | +0.156 +/- 0.036 |
| Prague Old Town Square | 9.9 % | 9.9 % | 12 | **+0.190 +/- 0.019** | +0.126 +/- 0.009 | +0.122 +/- 0.015 |
| Tokyo Hachiko | 7.9 % | 8.1 % | 3 | **+0.168 +/- 0.034** | -0.013 +/- 0.023 | -0.203 +/- 0.068 |

Per view fishnet surfaces, the `semantic` rung, which is a second and independent route through the
same photographs. Tokyo has no fishnet, so six squares rather than seven.

| Square | Bound area | Views | Rooftop shift | Isotropic shift | Street shift |
| --- | --- | --- | --- | --- | --- |
| Prague Old Town Square | 8.3 % | 52 | +0.147 +/- 0.010 | +0.111 +/- 0.014 | +0.196 +/- 0.017 |
| Mexico Zocalo | 5.2 % | 56 | +0.271 +/- 0.035 | +0.117 +/- 0.017 | +0.080 +/- 0.039 |
| Madrid Plaza Mayor | 4.7 % | 24 | +0.302 +/- 0.012 | +0.411 +/- 0.036 | +0.403 +/- 0.027 |
| Brussels Grand-Place | 3.7 % | 32 | +0.267 +/- 0.055 | +0.411 +/- 0.040 | +0.652 +/- 0.040 |
| Milan Duomo | 3.3 % | 4 | +0.078 +/- 0.026 | +0.080 +/- 0.023 | +0.066 +/- 0.040 |
| Korenmarkt | 0.7 % | 4 | +0.100 +/- 0.050 | +0.031 +/- 0.013 | +0.129 +/- 0.027 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street columns of
> both tables are shifts of old law integrals, and both tables are ordered by the
> rooftop one. The bound and seen areas, the station and view counts and the
> isotropic column survive, and the two directional columns need recomputing.

## The six squares that also run at 130 m

Same standpoint count, ray count and seeds, on the 130 m mesh. Milan has no 130 m build so it drops
out. Korenmarkt's walk rung here is the published eight station binding, `walk_semantic.npz`, rather
than the nine station one `build_site_semantics.py` writes at 250 m, which is why its station count
differs from its 250 m row.

| Square | Bound area | Rooftop shift | Isotropic shift | Street shift |
| --- | --- | --- | --- | --- |
| Korenmarkt, 8 stations | 10.6 % | **+0.592 +/- 0.070** | +0.337 +/- 0.042 | +0.153 +/- 0.047 |
| Brussels Grand-Place, 8 | 13.0 % | **+0.398 +/- 0.036** | +0.104 +/- 0.041 | +0.356 +/- 0.073 |
| Madrid Plaza Mayor, 6 | 20.1 % | **+0.286 +/- 0.005** | +0.354 +/- 0.030 | +0.460 +/- 0.054 |
| Prague Old Town Square, 12 | 30.9 % | **+0.200 +/- 0.017** | +0.136 +/- 0.004 | +0.102 +/- 0.025 |
| Tokyo Hachiko, 3 | 15.5 % | **+0.188 +/- 0.075** | +0.022 +/- 0.026 | -0.051 +/- 0.023 |
| Mexico Zocalo, 12 | 25.3 % | **+0.174 +/- 0.040** | +0.179 +/- 0.024 | +0.023 +/- 0.024 |

The fishnet rung at 130 m gives +0.412 +/- 0.039 at Brussels on 11.2 percent, +0.297 +/- 0.010 at
Madrid on 18.7, +0.202 +/- 0.015 at Prague on 33.0, +0.177 +/- 0.070 at Korenmarkt on 3.1 and
+0.101 +/- 0.019 at Mexico Zocalo on 23.4.

`outputs/exposure_korenmarkt/coverage_ladder_cross_site_250m_15ghz.json` and
`coverage_ladder_cross_site_130m_c130_15ghz.json` hold every per seed value behind these means, with a
figure beside each plotting the shift against the bound area.

> **Old illumination law, see `LAW_CHANGE.md`.** The 130 m rooftop and street shifts,
> and the fishnet figures in the paragraph above them, carry the old weights. The
> crop pair itself and the bound areas survive, because they are properties of the
> mesh and of where a camera could stand.

## Read the bound fraction before you read the shift

**Bound area is the fraction of the crop's triangle area whose material came from an image. The rest
of the square, 90 to 97 percent of it at 250 m, still came from the orientation rule.** A row reading
4.5 percent is not a run with materials. It is a run in which one twentieth of the area has evidence
and nineteen twentieths do not, and the shift in that row is what that one twentieth was worth.
Quoting the shift without the fraction invites the reader to take it for the effect of knowing the
materials of a square, which is a number this study has never measured anywhere.

The seen column is the area at least one admitted station saw. Bound is the subset of that whose
observed class carries prior mass over the RF material vocabulary, so a triangle seen only as sky
falls out between the two. The gap runs from 0.03 points at Korenmarkt and Madrid to 0.36 at Mexico
Zocalo, and it is reported because the two are different quantities.

**The bound fraction is set by where a camera could stand, not by how good the segmentation is.**
Admitted cameras sit within 29 to 62 m of their own centroid against a crop reaching 250 m, so most of
a 250 m crop is roofs and rear elevations that no photograph in this study has ever seen. Milan
reaches 4.0 percent from a single camera because the facade it faces is enormous and close, and Tokyo
reaches 7.9 from three because the crossing is small and tightly enclosed. Prague leads the column on
twelve admitted stations in a tight square. Ordering the table by bound fraction would be ordering it
by urban form and camera access, so the tables above are ordered by shift and the column is never
quoted on its own.

## The shift does not grow with the evidence

The strongest form of this is a within square test, so no difference in urban form can produce it.
Every square is measured twice, once at 250 m and once at 130 m, on the same standpoints per seed and
the same stations. The 130 m crop binds two to four times as much of the scene. If the shift were a
function of how much of the square carries evidence, it would grow.

| Square | Bound area, 250 m to 130 m | Shift per standpoint, 250 m to 130 m | Change |
| --- | --- | --- | --- |
| Madrid Plaza Mayor | 5.1 % to 20.1 %, x3.9 | +0.284 to +0.281 | **-0.002 dB** |
| Mexico Zocalo | 6.6 % to 25.3 %, x3.8 | +0.096 to +0.099 | **+0.003 dB** |
| Brussels Grand-Place | 4.5 % to 13.0 %, x2.9 | +0.107 to +0.103 | **-0.004 dB** |
| Prague Old Town Square | 9.9 % to 30.9 %, x3.1 | +0.162 to +0.152 | **-0.010 dB** |
| Korenmarkt | 3.2 % to 10.6 %, x3.3 | +0.115 to +0.075 | **-0.041 dB** |
| Tokyo Hachiko | 7.9 % to 15.5 %, x2.0 | -0.056 to -0.009 | **+0.046 dB** |

> **Old illumination law, see `LAW_CHANGE.md`.** The paired per standpoint shifts in
> this table are rooftop numbers. The null they carry survives, because it is a
> difference of two differences taken under the same weights inside each crop, and
> the values themselves move.

The statistic here is the median of the paired per standpoint ratios, how far a typical standpoint
moves, which for reasons given below is far the more stable of the two the ladder reports. **Four of
the six change by a hundredth of a decibel or less while their bound area roughly quadruples.** The
two that move at all move by four hundredths, in opposite directions, which is the size of the seed to
seed spread rather than a trend.

One caveat on the comparison and it does not rescue the growth hypothesis. Changing the crop changes
the scene as well as the bound fraction, and a 130 m crop is not converged for the rooftop or street
models, so the two absolute levels are not interchangeable. What is compared here is two paired
differences, each measured inside its own crop, and the annulus between 130 and 250 m is unbound in
both rungs of the 250 m pair, so it enters both sides. The comparison is therefore of what the
evidence was worth, not of what the exposure was.

Between squares the picture is much weaker and should not be dressed up. At 250 m the bound fraction
and the rooftop distribution median shift give a Pearson r of -0.67 at p = 0.10, at 130 m -0.74 at
p = 0.10, and on the per standpoint statistic -0.26 and +0.37 respectively, neither near significance.
The fishnet rung, an independent route over almost the same squares, gives +0.27 at 250 m and -0.28 at
130 m. So one route leans negative on one statistic and the others lean whichever way, none reaches
significance, and six or seven squares cannot resolve a slope. What they can rule out is a strong
positive one: a relationship in which doubling the bound area doubled the shift would not produce this
scatter, and the within square table above rules it out directly.

The reading that fits, offered as a reading and not a result, is that the first few percent of area
carries the whole effect. Those are the near frontages a street level camera sees first, and the
rooftop model's sources sit near the horizon with its multipath dominated by the facades immediately
around the standpoint. Adding rear elevations and further frontages adds bound area without adding the
surfaces that matter. Six squares that cannot resolve a slope cannot confirm a mechanism either.

> **Old illumination law, see `LAW_CHANGE.md`.** The correlations two paragraphs up
> are run on rooftop shifts, and the reading just above rests on the rooftop model's
> sources sitting near the horizon, which is the old law's elevation support. The
> refusal to claim a slope survives, and the reading is stale as written, because the
> facade tip law puts the sources on the roofline of the square itself.

## The two routes agree, except where their coverage differs

At the five squares that can answer both ways, the fishnet route and the fused station route are built
from the same photographs by different machinery. One cuts a surface per view and joins it back
through `face_source_triangle`, the other casts an equirectangular ray grid per station and tallies a
class per tracer triangle. They can disagree, which is why both are carried.

| Square | Walk shift | Fishnet shift | Difference | Bound area, walk against fishnet |
| --- | --- | --- | --- | --- |
| Madrid Plaza Mayor | +0.302 | +0.302 | +0.001 dB | 5.1 % against 4.7 % |
| Prague Old Town Square | +0.190 | +0.147 | +0.043 dB | 9.9 % against 8.3 % |
| Brussels Grand-Place | +0.347 | +0.267 | +0.081 dB | 4.5 % against 3.7 % |
| Mexico Zocalo | +0.354 | +0.271 | +0.084 dB | 6.6 % against 5.2 % |
| Milan Duomo | +0.221 | +0.078 | +0.142 dB | 4.0 % against 3.3 % |
| Korenmarkt | +0.501 | +0.100 | +0.401 dB | 3.2 % against 0.7 % |

> **Old illumination law, see `LAW_CHANGE.md`.** Both shift columns and the
> difference between them are rooftop numbers under the old weights. That two
> independently built bindings agree at four of the six squares is a statement about
> the bindings and survives, and the size of each agreement moves.

Four of the six agree to within a tenth of a decibel, which for two independently built bindings is a
real cross check and one the study previously had at no square. The two that do not are the two whose
fishnets were cut from a single panorama into four views. Korenmarkt's fishnet rung is a 0.7 percent
bound run, a fifth of the coverage of its walk rung, and it moves +0.100 dB, which sits on the same
curve as everything else rather than contradicting it.

Korenmarkt and Milan carry one further caveat the other four do not. Their fishnets were cut against
the single precision 130 m and 170 m exports, whose tile placement is seamed by up to a metre, while
the run uses the double precision 250 m build. The centroid and normal join therefore keeps 86.7
percent of Korenmarkt's source triangles and 87.7 percent of Milan's, all of the loss being normal
disagreement rather than distance. At Madrid, Mexico, Prague and Brussels the join is exact, matching
1.000 of source triangles at a median distance of 0.000 m, because their 130 m and 250 m builds come
from the same generation. This is recorded per run in the manifest and is now carried into the ladder
report rather than left inside it.

## Which Korenmarkt number this generalises, and which it does not

The study holds two different single square material results and they are easy to confuse, so this
report says plainly which one it extends.

**The evidence ladder is a positive result and it is the one that travels.** At Korenmarkt over the
130 m crop the paper reports the walk rung against the geometric rung at +0.347 +/- 0.001 dB
isotropic, +0.383 +/- 0.006 rooftop and +0.167 +/- 0.022 street, averaged over eight ray seed streams
on the conflict gated nine station set at 11.0 percent bound area. This report measures the same
comparison at seven squares and gets +0.17 to +0.50 dB rooftop at 250 m and +0.17 to +0.59 at 130 m,
everywhere. The single square number is now one of seven and it is the largest of the seven rather
than an outlier in kind.

**The material axis negative is a different comparison and it does not travel, because it cannot.**
The 0.024 dB isotropic and 0.029 dB rooftop shift, with 0.023 and 0.024 dB on the nine station set, is
the SAM 3 material posterior scored against the Vistas entity prior. Both sides of that comparison are
image derived, and it asks a narrower question: given that a photograph saw the facade, does reading a
material off it rather than an entity class change the answer. It reassigns 28.5 percent of the facade
area and moves the distribution by a fortieth of a decibel, which is resolved and negligible. Nothing
here weakens it and nothing here extends it. SAM 3 has run on twelve panoramas in this study and
eleven of them are Korenmarkt, so no other square can score the material axis at all, and the bindings
`build_site_semantics.py` writes carry the entity axis only. Reading this report's +0.17 to +0.50 dB
as a contradiction of that 0.024 dB would be comparing the value of having a photograph against the
value of segmenting it more finely.

> **Old illumination law, see `LAW_CHANGE.md`.** The +0.383 rooftop and +0.167 street
> figures quoted for Korenmarkt, the +0.17 to +0.50 dB range set beside them and the
> 0.029 dB rooftop material axis shift are all old law weighted. Which of the two
> single square results travels and which stays at one square is a property of the
> evidence and survives.

## The error budget, and a warning about the headline statistic

The two rungs of a comparison trace the same walk on the same per standpoint seeds, so the ray streams
are shared and the difference carries no independent Monte Carlo noise from them. That is why a shift
of two tenths of a decibel is measurable at all when a per square median carries about 0.13 dB rms of
standpoint sampling uncertainty in absolute terms.

What the difference does carry is the standpoint draw, because the shift is not the same at every
standpoint and a different 80 standpoints weight the moved ones differently. Each seed here redraws
the walk and the ray streams together, so the four seeds are disjoint replicates of the whole
measurement and their spread is the honest error bar. The standard deviation of a single run's rooftop
distribution median shift ranges from 0.012 dB at Madrid to 0.117 dB at Mexico Zocalo, and the
standard error on the four seed mean from 0.006 to 0.058 dB. The weakest walk row, Tokyo, is 4.9
standard errors from zero and the strongest, Madrid, is 51.

This error bar is deliberately larger than the one the paper's supplementary information quotes for
the same quantity. That one holds the standpoints fixed and varies only the ray seed over eight
streams, giving 0.001 to 0.022 dB, and it answers "would more rays change this". The four seed figure
answers "would a different walk change this", which is what a cross square comparison has to survive.
The pure ray noise floor at 80 standpoints is 0.0051 dB isotropic, 0.0167 rooftop and 0.0420 street,
so nothing below about a fiftieth of a decibel is resolved by more rays and nothing below about a
twentieth by more seeds either.

**The distribution median shift is the noisier of the two statistics and the standpoint count moves
it.** Korenmarkt has a 120 standpoint corrected law pair on disk, `korenmarkt_geometric_L3` against
`korenmarkt_walk_L3`, made at the same 130 m crop, the same seed 7, the same 200,000 rays and the same
eight station binding as this report's 130 m Korenmarkt row. Nothing differs but the standpoint count.
It gives +0.366 dB rooftop at 120 standpoints against +0.517 at 80. That is a 0.15 dB swing from the
sampling density alone, and it is why +0.366 sits below the whole +0.467 to +0.786 range of this
report's four 80 standpoint draws. The paired per standpoint median over the same pair of runs moves
from +0.101 to +0.075, and across the four seeds it stays inside +0.069 to +0.082. A ratio of two
quantiles inherits the instability of both quantiles, whereas a median of paired ratios does not. Both
are reported in the JSON, the distribution figure is the one that answers "how far does the published
distribution move", and any claim that turns on tenths of a decibel should be made on the paired
figure.

The gap between the two also says where the effect lives. At Madrid and Prague the paired median moves
almost as far as the distribution median, +0.284 against +0.302 and +0.162 against +0.190, so the
shift is spread evenly over the walk. At Korenmarkt, Brussels and Mexico Zocalo the paired figure is a
quarter to a third of the distribution figure, and between 3 and 14 standpoints of 80 move more than a
decibel while the rest barely move. The same evidence acts as a broad small correction at some squares
and a sparse large one at others.

Two rows deserve to be read with all of that in mind. Tokyo's isotropic shift of -0.013 +/- 0.023 dB
is not distinguishable from zero and its 250 m street shift of -0.203 +/- 0.068 is the only resolved
negative in either table. Tokyo is also the only square whose distribution median and typical
standpoint move in opposite directions, +0.168 dB against -0.056 dB at 250 m. Three admitted stations
in the deepest and most enclosed of the seven sites is a thin basis, and the disagreement between the
three illumination models there is a real limit rather than a rounding artefact.

> **Old illumination law, see `LAW_CHANGE.md`.** The 0.0167 dB rooftop and 0.0420 dB
> street ray noise floors, every rooftop distribution median in this section and the
> two Tokyo rows are old law quantities. The warning that the distribution median is
> the noisier of the two statistics survives, because it follows from taking a ratio
> of two quantiles.

## Four squares could not answer, and one route at one square could not

No row above was filled by inference. These are the refusals and each is a property of the data.

| Square | Why it has no ladder |
| --- | --- |
| Krakow Rynek | no panoramas. Its config is written and its walk date chosen, but the Street View tile quota is spent |
| London Trafalgar | no panoramas, same quota |
| Toulouse Capitole | no panoramas, and its crop is centred 25 m outside the square, so acquiring them first would register them against the wrong geometry |
| New York Times Square | 14 panoramas, all registered, **none admitted**. The modelled skyline sits at 55 to 62 degrees of elevation in every direction, so rotating a camera inside it barely changes the residual and skyline registration has nothing to bite on |
| Milan Duomo, at 130 m | no 130 m mesh. It answers at 250 m only |
| Tokyo Hachiko, fishnet route | no fishnet surfaces were ever cut there. It answers on the fused station route only |

Times Square is the one that needed a deliberate refusal rather than an absent file. It has eight
fishnet views on disk covering 6.5 percent of its area, cut from two cameras that the sky conflict
test places inside the buildings they are pointed at. Offering that rung because the files exist would
have put an eighth square into the table on evidence the rest of the study refuses, so the fishnet
rung is gated on the coverage ledger's own admission rule and Times Square is excluded by it.

**No rung failed at run time.** All 80 traces of the 250 m sweep and all 68 of the 130 m sweep
completed, and both jobs exited zero.

## What changed in the code

`COVERAGE_LADDER` was three hard coded Korenmarkt stems. That was accurate when Korenmarkt held the
only per triangle binding on disk, and it became a reason not to notice when six more squares acquired
one. It is now `coverage_ladder(site, crop_m, seed)`, which asks each square what it has and returns
the rungs it can climb.

- A rung is offered when its binding is on disk for that square at that crop radius, which is the same
  question `run` already asks before it refuses a materials mode.
- The fishnet rung is additionally gated on the coverage ledger's admission rule, so surfaces cut from
  cameras that failed pose admission are not treated as evidence.
- The fishnet rung binds against the mesh the surfaces were cut against, read from the fishnet's own
  manifest, so a 130 m cut inside a 250 m run is a declared cross mesh join and not a silent
  collision of two triangle numberings. Korenmarkt and Times Square were cut at 130 m and Milan at
  170 m, so no crop radius derives all three.
- `coverage_report` takes a square, a crop radius and a seed, and scores all three illumination models
  rather than the rooftop one alone. It carries the bound fraction, the station or view count, the
  binding file and the cross mesh join statistics into every entry.
- `coverage_ladder_report` is new. It collects one square's ladder across seeds, takes the mean and
  the standard error of the shift, and writes the cross square table and figure.
- `run_coverage_ladder` drives the whole thing. The loop is seed major, so a sweep stopped early holds
  a complete cross square answer with no error bar rather than an error bar on two squares.

Two guards were needed and neither was optional.

**A resume that only checks a run is complete will read the wrong physics.** Korenmarkt's three
published 130 m stems are complete 120 standpoint runs made under the superseded elevation law, and
every manifest field except the law itself matches what a new sweep would write. `reusable` compares
the standpoint count, square, crop radius, ray count, seed, bounce budget and the illumination law of
all three models, and refuses on any disagreement.

> **Old illumination law, see `LAW_CHANGE.md`.** The superseded law named here is the
> fixed height one, and the band law that replaced it on 2026-08-02 is superseded in
> turn by the facade tip law. The guard survives and matters more than before,
> because every stem this report made was traced under the band law and `reusable`
> will now refuse all of them.

**A sweep must not overwrite a run it cannot reuse.** Having refused those three stems, the sweep would
otherwise have retraced straight over them. It now raises and names `--tag-suffix` instead, which is
why the 130 m arm is tagged `_c130` and the 250 m arm is not. At 250 m no stem collides with anything
published.

The published Korenmarkt stems still resolve unchanged and a test pins that, so the generalisation
cannot rename the runs the paper quotes.

Reproduce with:

```
python run_exposure.py --coverage-ladder --crop-m 250 --ladder-seeds 7,8,9,10 --locations 80 --rays 200000 --workers 8
python run_exposure.py --coverage-ladder --crop-m 130 --ladder-seeds 7,8,9,10 --locations 80 --rays 200000 --workers 8 --tag-suffix _c130
```

Both ran on `blgpu` over eight cores. The 250 m sweep took 2 h 20 min for its 80 rungs, 05:22:58 to
07:42:39 UTC. The 130 m sweep was queued behind it rather than run beside it, so the two never
competed for cores, and it took 2 h 12 min for its 68 rungs. Both exited zero. Results were fetched
and the reports regenerated locally with the same code.

## What this does not settle

The bound fraction never exceeds 9.9 percent at 250 m or 33 percent at 130 m, so nothing here says
what a fully bound square would do. The within square test says the shift stops growing somewhere
below a third of the area, which is a bound rather than a limit.

The material axis remains one square wide. Extending `build_site_semantics.py` to cast the SAM 3 axis
as well as the entity axis would raise the number of squares that can score it from one to one, since
Milan is the only other panorama carrying `rf_material` and it is a single camera.

Krakow and London are one command each once the Street View tile quota resets, and both would enter at
250 m and 130 m. Toulouse needs its anchor moved 25 m and its tiles re-pulled first, which changes a
mesh the eleven square table already uses.

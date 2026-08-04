# The ground datum

Where the pedestrian stands. One number per site, the height of the walkable
surface in the mesh's local ENU frame, and the number the walk builder filters
candidate standpoints against. It was wrong at two of the eleven sites, by 18.2 m
at Krakow and 13.9 m at Toulouse, which put the observer on a roof for both. This
is what broke, why, what replaced it, and which published rows move.

Status: fixed and requalified. Numbers below are measured, not projected.
`PAPER_METHODS.md` and `REPORT.md` are not edited here. The section
"What has to change in the published text" lists what they now say wrongly.

## What broke

`run_exposure.ground_datum` took the median height of the first downward hit over
a disc of 15 m at the crop centre. Every site is cropped and centred on its
square, so the assumption was that the centre of a square is pavement.

At Rynek Glowny it is not. The Sukiennice, the cloth hall, stands in the middle
of the square and is 108 m long, so a 15 m disc at the origin lands entirely on
its roof. At Place du Capitole the origin sits on the Capitole itself. The
estimator answered the question it was asked, correctly, and the question was
wrong.

The failure is silent by construction. `build_walk` accepts a candidate column
whose first hit is within 2.5 m of the datum and lands on a near horizontal face,
and a roof satisfies both. The standpoints that came out were on the roof, they
were open to the sky, they passed the clearance test and the enclosure test, and
they produced perfectly plausible susceptibilities. The only visible symptom was
the walk candidate count: 163 at Krakow and 176 at Toulouse against 800 to 2000
everywhere else, because a roof is smaller than a square.

## What it was not

The other way to get this wrong is to reach for the lowest surface. Google's
tiles carry the underground structure of their buildings, and the crops here run
from 4.6 m of geometry below the pavement at Toulouse to 202 m below it at Times
Square. A minimum over the mesh vertices lands in a car park. So does a low
quantile: the 1st percentile of vertex height sits 0.9 to 39.7 m below the
pavement across the eleven sites, and at Madrid it is 8.9 m down.

None of that geometry is reachable by a ray dropped from the sky, because
something is always above it. The estimate is built on downward first hits for
exactly that reason, and the basements never enter the statistic at all.

## What replaced it

`semantic_twin/propagation/walk.py`, `measure_ground_datum`. The datum now lives
beside the walk it feeds rather than in the run script, because it is a property
of the walk and not of one experiment.

The rule, in one sentence: sample a square metre grid of columns over the disc
the walk will use, drop a ray down each one from above the whole scene, keep the
hits that land on a near horizontal face, and take the lowest height whose
acceptance band holds at least half as many hits as the busiest height anywhere,
settled onto the median of its own band.

Four choices, each with the case that forces it.

**Downward first hits, not vertex statistics.** Immune to the underground
structure, which no vertex statistic is. See above.

**The walk disc, not a central disc.** A monument is never the majority of a
square, so a mode over the walk disc cannot be captured by one. The datum is
measured over the disc it will be applied to, which also removes the free
parameter: there is nothing left to choose.

**Near horizontal faces only.** Same `min_up_cosine` of 0.85 the walk itself
uses, so the datum is estimated over the population it will be filtering.

**Lowest major level, not the busiest one.** At the Zocalo the crop centre sits
off the plaza toward its northwest corner, and between roughly 50 and 70 m of
radius the surrounding roofs outnumber the pavement in the disc: 43.6 percent
against 36.7 percent at 60 m. The busiest level is a roof over that span.
Pedestrians are on the lowest major surface and never on the second one, so the
tie is broken downwards. "Major" is at least half the busiest count, which stops
the rule from degenerating into "the lowest surface anywhere" and walking off
Plaza Mayor onto Cava de San Miguel, five metres below it and 7 percent of the
crop.

That last threshold is the only tuned number in the rule, and it does not select
any answer that is published. At the 90 m walk radius the pavement is already the
busiest level at all eleven sites, so every ratio from 0.2 to 1.0 gives the same
eleven datums to within 1e-6 m. It earns its place by making the answer stable
against the disc radius as well: over discs of 30, 40, 60, 90 and 120 m the
eleven datums move by at most 0.53 m, and by at most 0.19 m at the two sites that
were broken. The busiest-level rule alone still reads the Sukiennice roof at a
30 m disc.

### A second bug found in the same code path

`build_walk` started its downward probe at the datum plus 200 m. Times Square
rises 343 m above its pavement and Shibuya 230 m, so at those two sites the probe
began inside the towers. A ray that starts inside a photogrammetric shell reports
a surface of that shell rather than its roof, and at street level that is
indistinguishable from pavement. The enclosure test was catching the consequence
downstream, which is where New York's 31 candidates "rejected as enclosed"
against 0 to 2 elsewhere came from. The probe now starts at the sky probe height,
which removes the case instead of catching it.

## The eleven datums

`ground datum` is what the published run used. At Korenmarkt that was the
registered constant from `config/korenmarkt.json` rather than the estimator, so
the estimator's own answer is given separately.

| site | published datum | legacy estimator | new datum | shift from published |
|---|---|---|---|---|
| Rynek Glowny, Krakow | 269.124 | 269.124 | 250.938 | **-18.187** |
| Place du Capitole, Toulouse | 205.169 | 205.169 | 191.226 | **-13.944** |
| Grand-Place, Brussels | 65.782 | 65.782 | 65.565 | -0.217 |
| Hachiko, Tokyo | 51.395 | 51.395 | 51.597 | +0.202 |
| Plaza Mayor, Madrid | 702.484 | 702.484 | 702.681 | +0.196 |
| Staromestske, Prague | 236.835 | 236.835 | 236.650 | -0.185 |
| Times Square, New York | -18.438 | -18.438 | -18.390 | +0.049 |
| Korenmarkt, Ghent | 50.837 | 51.005 | 50.871 | +0.034 |
| Piazza del Duomo, Milan | 163.087 | 163.087 | 163.120 | +0.033 |
| Trafalgar Square, London | 54.840 | 54.840 | 54.813 | -0.026 |
| Zocalo, Mexico City | 2223.397 | 2223.397 | 2223.384 | -0.013 |

Two sites move by more than a metre and nine move by less than a quarter of one.
Madrid, which was flagged as suspect at about 5 m, is not one of them. Its datum
was already the plaza floor, and the 5 m below it is the real street outside the
plaza block: a 10 m cell map of the crop shows the plaza floor as a single
connected surface out to about 60 m in every direction, ringed by 18 to 24 m of
roof, with the lower surface appearing only beyond 70 m and never inside 60 m.
Plaza Mayor is a raised, enclosed square and the drop to Cava de San Miguel
through the Arco de Cuchilleros is a real drop, not an artifact. Its registered
camera ground height agrees with the new datum to 0.14 m.

## Three independent checks on the new datums

**Panorama registration.** Eight of the eleven sites carry a `camera_ground_z_m`
solved by the panorama registration of section 3, which is independent of every
mesh statistic. All eight agree with the new measured datum:

| site | registered | measured | measured minus registered |
|---|---|---|---|
| Grand-Place, Brussels | 65.270 | 65.565 | +0.296 |
| Hachiko, Tokyo | 51.408 | 51.597 | +0.188 |
| Piazza del Duomo, Milan | 162.939 | 163.120 | +0.181 |
| Staromestske, Prague | 236.833 | 236.650 | -0.182 |
| Plaza Mayor, Madrid | 702.539 | 702.681 | +0.142 |
| Times Square, New York | -18.443 | -18.390 | +0.053 |
| Korenmarkt, Ghent | 50.837 | 50.871 | +0.034 |
| Zocalo, Mexico City | 2223.403 | 2223.384 | -0.019 |

Worst disagreement 0.30 m. `run_exposure.run` now refuses to trace a site whose
measured datum sits more than 1 m from its registered one, so this is a gate and
not only a table. The three sites without a registration are Krakow, London and
Toulouse, which is why the registration cannot be the estimator: a rule that
works on eight of eleven sites is not a rule.

**A second estimator, written independently.** `build_site_config.py`, produced
in a separate thread of this work, measures the same quantity by a different
route: 20000 random downward rays over an 80 m disc through Embree, 0.5 m
histogram bins, no near-horizontal filter, and the mode searched only in the
lower half of the relief. Scored on the same eleven crops it agrees with
`measure_ground_datum` to within 0.19 m everywhere, worst at Brussels and Prague,
and to within 0.004 m at Krakow and 0.043 m at Toulouse. Two rules that share no
code and no heuristic landing on the same eleven numbers is the strongest
evidence here that the numbers are the pavement.

That agreement is also a duplication that should not survive. There are now two
ground datum estimators in the repository. `build_site_config.py` should call
`measure_ground_datum`, and was not changed here only because it was being
written at the same time as this fix. It is the one open item.

**Crop independence.** Ten of the eleven sites have both a 130 m and a 250 m
build, from separate tile downloads and separate mesh assemblies. The new datum
comes out bit identical on the two builds at all ten, to every printed digit,
which says the number is a property of the site and not of the crop. Milan has
only the 250 m build.

**Radius stability.** The datum measured over discs of 30, 40, 60, 90 and 120 m
spans at most 0.53 m at any site, worst at Tokyo, where the ground genuinely
slopes. The legacy estimator's answer swings by 18.5 m at Krakow and 20.1 m at
Toulouse over the same radii, which is what a statistic reading two different
surfaces looks like.

## What the fix does to the walk

Standpoints surviving the datum band, the clearance test and the enclosure test,
at the 90 m walk radius with 3 m spacing and seed 7:

| site | old candidates | new candidates | faces reclassified |
|---|---|---|---|
| Rynek Glowny, Krakow | 162 | 2114 | 92221 / 557526 |
| Place du Capitole, Toulouse | 176 | 1312 | 182781 / 1016440 |
| Milan Duomo | 2018 | 2026 | 47 / 779421 |
| Times Square, New York | 1085 | 1083 | 178 / 1064389 |
| Grand-Place, Brussels | 1077 | 1079 | 1047 / 706720 |
| Hachiko, Tokyo | 1131 | 1138 | 1281 / 797615 |
| Zocalo, Mexico City | 1346 | 1343 | 55 / 707812 |
| Plaza Mayor, Madrid | 981 | 977 | 756 / 720373 |
| Staromestske, Prague | 1500 | 1495 | 652 / 664619 |
| Trafalgar Square, London | 1642 | 1619 | 235 / 783425 |
| Korenmarkt, Ghent | 801 | 801 | 228 / 617091 |

Krakow gained a factor of thirteen in walkable ground and Toulouse a factor of
seven, which is the size of the square against the size of the building the
observer was standing on. `classify_faces` splits ground from facade at the
datum, so the two broken sites also had 17 percent of their triangles in the
wrong material class.

No site is left with bit identical tracer inputs, so every one of the eleven is
retraced rather than argued to be unchanged. The nine small movers change by a
handful of standpoints out of about a thousand and by under 0.2 percent of their
faces, so their rows are expected to move by a fraction of a decibel, but
expected is not measured and the requalification below measures them.

## Requalification

All eleven sites retraced at the fixed datum, everything else held at the
published settings: 80 standpoints, 90 m walk radius, 3 m spacing, 250 m crop,
200000 rays, 512 local cells, 4 bounces, seed 7, geometric materials, 15 GHz. The
old columns are `city250_corrected_*`, the new ones `city250_datum_*`, both in
`outputs/exposure_korenmarkt/`.

| site | datum shift [m] | iso old | iso new | rooftop old | rooftop new | street old | street new |
|---|---|---|---|---|---|---|---|
| Rynek Glowny, Krakow | **-18.187** | 0.5304 | **0.3841** | 0.9001 | **0.2681** | 0.4600 | **0.0232** |
| Place du Capitole, Toulouse | **-13.944** | 0.3992 | **0.2964** | 0.3383 | **0.2221** | 0.0318 | **0.0175** |
| Grand-Place, Brussels | -0.217 | 0.2351 | 0.2224 | 0.0976 | 0.0988 | 0.0065 | 0.0067 |
| Hachiko, Tokyo | +0.202 | 0.2238 | 0.2335 | 0.1009 | 0.0998 | 0.0155 | 0.0162 |
| Plaza Mayor, Madrid | +0.196 | 0.3473 | 0.3434 | 0.1462 | 0.1448 | 0.0080 | 0.0079 |
| Staromestske, Prague | -0.185 | 0.3626 | 0.3585 | 0.2357 | 0.2379 | 0.0194 | 0.0197 |
| Times Square, New York | +0.049 | 0.1629 | 0.1695 | 0.1294 | 0.1273 | 0.0561 | 0.0605 |
| Korenmarkt, Ghent | +0.034 | 0.2917 | 0.2917 | 0.1627 | 0.1627 | 0.0143 | 0.0144 |
| Piazza del Duomo, Milan | +0.033 | 0.3538 | 0.3560 | 0.2477 | 0.2453 | 0.0351 | 0.0376 |
| Trafalgar Square, London | -0.026 | 0.3894 | 0.3947 | 0.2868 | 0.2886 | 0.0268 | 0.0276 |
| Zocalo, Mexico City | -0.013 | 0.3974 | 0.3978 | 0.2990 | 0.3071 | 0.0297 | 0.0292 |

> **Old illumination law, see `LAW_CHANGE.md`.** The four rooftop and street columns
> are susceptibilities integrated against the height band and range band law. The
> datum shift and the isotropic columns survive, because a datum is geometry and the
> isotropic weight is uniform, and the directional columns have to be recomputed.

The same thing in decibels, with the sky fraction beside it because it is the one
quantity that carries no illumination assumption:

| site | iso [dB] | rooftop [dB] | street [dB] | sky old | sky new |
|---|---|---|---|---|---|
| Rynek Glowny, Krakow | **-1.40** | **-5.26** | **-12.98** | 0.4456 | 0.3138 |
| Place du Capitole, Toulouse | **-1.29** | **-1.83** | **-2.58** | 0.3451 | 0.2382 |
| Grand-Place, Brussels | -0.24 | +0.05 | +0.15 | 0.1735 | 0.1702 |
| Hachiko, Tokyo | +0.18 | -0.05 | +0.18 | 0.1687 | 0.1739 |
| Times Square, New York | +0.17 | -0.07 | +0.33 | 0.1138 | 0.1210 |
| Trafalgar Square, London | +0.06 | +0.03 | +0.13 | 0.3168 | 0.3304 |
| Plaza Mayor, Madrid | -0.05 | -0.04 | -0.05 | 0.2819 | 0.2776 |
| Staromestske, Prague | -0.05 | +0.04 | +0.07 | 0.2915 | 0.2882 |
| Piazza del Duomo, Milan | +0.03 | -0.04 | +0.30 | 0.2851 | 0.2859 |
| Zocalo, Mexico City | +0.00 | +0.12 | -0.08 | 0.3297 | 0.3240 |
| Korenmarkt, Ghent | -0.00 | +0.00 | +0.01 | 0.2310 | 0.2310 |

Within site spreads, fifth to ninety fifth percentile, move with the rest. The
two broken sites widen a lot, because a roof is a more uniform place to stand
than a square: Krakow 0.77 to 1.70 dB isotropic and 2.26 to 2.85 dB rooftop,
Toulouse 2.31 to 5.17 dB isotropic and 5.30 to 11.39 dB rooftop. The nine others
move by at most 1.5 dB rooftop, at Tokyo.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street decibels in
> the table above, and the rooftop spreads in this paragraph, are movements of old
> law integrals. The isotropic decibels and both sky fraction columns survive, and
> the line beside the table already says the sky fraction carries no illumination
> assumption.

### Ghent does not regress

Korenmarkt is the control and it behaves like one. Its datum moves 0.034 m, its
walk keeps 801 candidates, and the stratified pick returns **the same 80
standpoints to the millimetre**. The only thing that changes at all is 228
triangles of 617091 crossing the ground and facade boundary, and the medians move
by -0.0009 dB isotropic, +0.0009 dB rooftop and +0.0055 dB street. All three are
below the Monte Carlo noise floor of `CODE_AUDIT.md` section 4.1.

> **Old illumination law, see `LAW_CHANGE.md`.** The +0.0009 dB rooftop and
> +0.0055 dB street medians, and the two floors they are held against, are old law
> numbers. That Korenmarkt returns the same 80 standpoints to the millimetre and
> moves 228 triangles is geometry and survives whole.

### The nine small movers do move, and it is not Monte Carlo noise

This is the part that was not expected. Nine sites have a datum shift under a
quarter of a metre, and eight of them still move their medians by up to 0.24 dB
isotropic. Against the walk median noise floor of section 4.1, rescaled from 120
standpoints to 80 by the square root of the count:

| illumination | noise floor at 80 standpoints | rms shift over the eight | worst site | worst over floor |
|---|---|---|---|---|
| isotropic | 0.0051 dB | 0.128 dB | 0.242 dB, Brussels | 47 |
| rooftop | 0.0167 dB | 0.061 dB | 0.116 dB, Mexico City | 7.0 |
| street small cell | 0.0420 dB | 0.188 dB | 0.326 dB, New York | 7.8 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows are
> noise floors on, and shifts of, old law integrals. The isotropic row survives, and
> so does the finding the section reaches, because the standpoints held in common
> are a property of the walk and not of the illumination.

So the movement is real and it is 7 to 47 times larger than the estimator noise.
The cause is not the datum and not the physics. It is which standpoints get
traced. A 0.2 m datum shift adds or drops a handful of columns out of about a
thousand, the greedy nearest neighbour chain of `_chain` then reorders, and
`stratified_subset` picks by index along that chain, so a two candidate change at
the start of the chain reshuffles the whole sample. Traced standpoints in common
between the old run and the new one:

| site | of 80 | site | of 80 |
|---|---|---|---|
| Korenmarkt, Ghent | 80 | Trafalgar Square, London | 15 |
| Grand-Place, Brussels | 24 | Zocalo, Mexico City | 14 |
| Times Square, New York | 17 | Staromestske, Prague | 11 |
| Plaza Mayor, Madrid | 9 | Hachiko, Tokyo | 9 |
| Piazza del Duomo, Milan | 4 | Krakow and Toulouse | 0 |

Eight of the eleven sites therefore had between 56 and 76 of their 80 standpoints
replaced by different ones drawn from the same square, and their medians moved by
0.03 to 0.24 dB. That is not a defect in either run. It is a measurement nobody
had: **the standpoint sampling uncertainty on a published per city median is
about 0.13 dB rms and 0.24 dB worst case under isotropic illumination, roughly
twenty five times the Monte Carlo uncertainty the audit measured.** The error bar
on these medians is set by how many standpoints are drawn and where, not by how
many rays each one shoots. Korenmarkt, whose standpoints did not change, is the
control that separates the two.

## What has to change in the published text

`PAPER_METHODS.md` section 9.2 and `REPORT.md` "Eleven cities compared" both
carry the old table. Neither is edited here. What they now state wrongly:

**The two invalid rows, now valid.** Krakow Rynek isotropic 0.5304 becomes
0.3841, rooftop 0.9001 becomes 0.2681, street 0.4600 becomes 0.0232, spreads 0.77
and 2.26 dB become 1.70 and 2.85 dB. Toulouse Capitole isotropic 0.3992 becomes
0.2964, rooftop 0.3383 becomes 0.2221, street 0.0318 becomes 0.0175, spreads 2.31
and 5.30 dB become 5.17 and 11.39 dB.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street replacements
> listed for Krakow and Toulouse, and their rooftop spreads, are old law numbers.
> That the two rows were invalid and are now valid is a datum result and survives,
> so only the directional values printed here change.

**The nine other rows all move too**, by 0.03 to 0.24 dB, because their
standpoints resampled. Every number in the table should come from the
`city250_datum_*` runs rather than being patched two rows at a time.

**The headline spans shrink.** Across the eleven the median susceptibility spans
**3.71 dB isotropic** against the published 5.13 dB, **4.93 dB rooftop** against
9.65 dB, and 9.57 dB street against 18.53 dB. Roughly half the spread this study
reported between cities was one observer standing on a cloth hall.

> **Old illumination law, see `LAW_CHANGE.md`.** The 4.93 dB rooftop and 9.57 dB
> street spans, and the 9.65 and 18.53 dB they replace, are between city spreads
> under the old band models. The isotropic span survives, and so does the within
> against between city claim in the next paragraph, which is stated on isotropic
> alone.

**The claim about within versus between city variation gets stronger, not
weaker.** The largest spread inside one square is now 6.45 dB isotropic at
Madrid, against a between city span of 3.71 dB. Published, those were 6.15 and
5.13 dB. So the sentence "the variation inside one square exceeds the variation
between eleven cities on three continents" survives, and the margin roughly
doubles.

**The ordering changes at the top.** Zocalo, Mexico City is now the highest site
on both isotropic and rooftop. Krakow falls from first to third on both, and
Toulouse from second to seventh isotropic and second to sixth rooftop. On street
small cell Krakow falls from first to fifth.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street orderings
> rank old law integrals and can reorder again under the facade tip law. The
> isotropic ordering survives, and so does the paragraph below it, which reads sky
> fraction and isotropic spread.

**The paragraph beginning "The ordering is not simply built density" is now
wrong.** "Krakow's wide open Rynek runs highest and most uniform, 0.53 with only
0.77 dB of spread" describes the roof of the Sukiennice: 0.45 sky fraction and a
0.77 dB spread are what standing on a large flat roof looks like. At street level
Krakow is 0.38 with 1.70 dB of spread and 0.31 sky, which is an ordinary large
square. The Brussels and Times Square sentences in the same paragraph are
unaffected.

**The audit ledger entry needs closing and one line of it correcting.**
`PAPER_METHODS.md` line 1446 says "Madrid at 5.0 m is suspect". Madrid is not
suspect. Its datum was already the plaza floor, it agrees with its own panorama
registration to 0.14 m, and it moves by 0.196 m. The 5 m is the real drop from
Plaza Mayor to the streets outside it. The same entry proposes "a low quantile
over a wider radius" as the fix, and a low quantile is the one family of
estimator that walks into the underground car parks.

**Figure 8 has to be rebuilt anyway**, which `PAPER_METHODS.md` already says for
a different reason. The replacement aggregate is
`outputs/exposure_korenmarkt/cities250_datum_15ghz_summary.json`, which holds all
eleven sites at 80 standpoints each, and its figure
`cities250_datum_15ghz_cdf.png`.

## Three things found on the way that are not the datum

**The published New York rows sit in a corrupt file.**
`outputs/exposure_korenmarkt/city250_corrected_newyork_timessquare_15ghz_locations.jsonl`
has 78 parseable records, one torn record at line 62 and a 46 character fragment
at line 80, which is what interleaved writes from two processes into one file
look like. So the published Times Square row was computed from fewer than 80
standpoints and nothing said so. Its wall clock, 14.3 minutes against 4.8 to 7.5
for every site except Prague, points the same way.

**`site_fishnet()` raises on two sites in runs that never touch a fishnet.** It is
called before the materials mode is read, so
`--materials geometric` runs at Mexico City and Prague died on a nested fishnet
directory that a geometric run has no use for. Those two rows were produced by a
driver that patches the function to return `None`,
`scratchpad/finish_two.py`, and the guard should move inside the
`materials == "semantic"` branch. It is another thread's code and was not edited
here.

**A second eleven city sweep is running under the old datum.** A concurrent
thread launched
`run_exposure.py --all-sites --crop-m 250 --tag-suffix _rebuild0802` at 22:35 on
2026-08-02, minutes before this fix landed, so its manifests carry
`"ground_datum_source": "median downward hit over a 15 m disc at the crop
centre"` and its Krakow and Toulouse rows will reproduce the roof error. Those
outputs should be discarded rather than compared.

**Other call sites inherit the fix, one duplicate does not.**
`run_law_comparison.py`, `make_sensitivity_study.py`,
`semantic_twin/propagation/antenna.py` and
`semantic_twin/propagation/bystanders.py` all call `ground_datum` through
`run_exposure`, so they pick up the new rule without a change. Two things still
carry copies of the old behaviour:

- `build_site_config.py` has its own estimator, discussed above.
- `semantic_twin/propagation/bystanders.py` places bodies with its own
  copy of the walkability test, including `probe = ground_datum_m + 200.0`. It
  has the probe height bug this fix removed from `walk.py`, and at Times Square
  and Shibuya it will place bystanders against surfaces read from inside the
  towers. It was not changed here because it was being written concurrently.

## Files

- `semantic_twin/propagation/walk.py`: `measure_ground_datum`, `ground_datum`,
  `GroundDatum`, and the probe height fix in `ground_height`.
- `run_exposure.py`: calls the estimator at the walk radius, cross checks it
  against the registration, and writes the whole provenance block into every
  manifest under `ground_datum`.
- `run_crop_convergence.py`, `run_substreet_ablation.py`,
  `export_propagation_payload.py`: all three carried the same
  `korenmarkt constant else estimator` branch and now measure uniformly.
  `run_crop_convergence.py` was using the Korenmarkt constant for whatever
  `--site` it was given.
- `tests/test_ground_datum.py`: 18 tests. Each synthetic layout is one of the
  failures above or one that would break an obvious alternative, and the real
  crops are checked against the registrations.

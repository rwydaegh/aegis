# The bounce budget, and why it is three

> **Old illumination law, see `LAW_CHANGE.md`.** Every column labelled rooftop or street
> small cell here is weighted by the old height and range bands. The budget decision
> survives untouched, because truncation is a property of the transport and is measured as
> a fraction of escaping power rather than against the illumination.

The operating point is three surface interactions. `DEFAULT_MAX_BOUNCES` in
`semantic_twin/propagation/tracer.py` is the only place that number is written
down, and `TraceConfig`, `run_exposure.py`, `run_crop_convergence.py`,
`run_substreet_ablation.py`, `run_law_comparison.py`,
`export_propagation_payload.py`, `antenna.py` and `bystanders.py` all read it
from there.

That is a change of substance and not only of tidiness. What follows is the
justification, the measurement behind it, the places where the measurement does
not support the argument, and the bias the choice introduces.

## What was in circulation before

Four different values, none of them the stated operating point.

| where | value |
| --- | --- |
| `PAPER_METHODS.md` prose | 4, called the operating point |
| `TraceConfig.max_bounces` class default | 12 |
| `run_exposure.py --max-bounces` default | 6 |
| `run_substreet_ablation.py`, `run_law_comparison.py` | 4, hardcoded |
| manifests under `outputs/exposure_korenmarkt` | 6 in 41 files, 4 in 16, 12 in 1 |

The headline eleven city run `city250_corrected_*` was at 4. The evidence ladder
and the 120 standpoint Korenmarkt runs were at 6. Both numbers are in the
published record and neither matched either library default, so a reader
reproducing the study from the command lines in `README.md` would have got a
third thing.

## Why three, and not a convergence threshold

The old justification was numerical: the median moved less than 0.5 dB between
budgets, so the shorter one was good enough. That argument is available for any
budget, it says nothing about this method, and it puts the choice at the mercy
of whatever threshold is fashionable.

The argument that belongs to this method is about evidence. The instrument is a
street level panorama standing at the observation point. The trace is adjoint:
rays leave the observation point and are read backwards, so the first surface
interaction is the surface that scatters energy into the observer, and that is
precisely a surface the camera at that point can see. First interaction, first
hand material.

That much is geometry. Nothing past it is. Under the adjoint formulation the
path does not return to the observation point, so the second interaction is only
covered if the panorama set happened to see the surface it lands on, and that is
a property of how densely the square was walked rather than a guarantee. This
matters, and DECISIONS.md is wrong where it says the adjoint move costs nothing:
the move halves the guarantee. On a monostatic path that returns to the
observation point, the outgoing and returning surfaces are both visible from
that one viewpoint and both carry evidence by construction. Adjoint, only the
first does.

So the budget question becomes three separate empirical questions, and
`measure_bounce_evidence.py` answers them.

1. The first interaction should be covered essentially always. If it is not,
   that is a defect in the registration or the visibility cast, not a property
   of the city.
2. The second interaction is the number nobody knew. It is the empirical answer
   to whether the walk covered the square densely enough for the second bounce
   to inherit measured material.
3. The third interaction is expected to be substantially uncovered. How much
   that matters depends on how much power that depth carries, so coverage and
   power have to be reported jointly and not as two marginals.

## How the measurement works

`measure_bounce_evidence.py` attaches a `BounceEvidenceTally` to the shipped
tracer. At every surface interaction the tally records the triangle index and
the throughput incident on that surface, read before that interaction's
reflectance is applied, and scores the triangle against per triangle boolean
masks of what the image evidence covers. The tally consumes no random draw and
touches no accumulator, so a traced result is bit identical with it attached and
without it, which `tests/test_propagation.py` asserts rather than assumes.

Four nested definitions of covered are carried at once, on the same rays.

- `seen_by_the_ray_grid`: the station's equirectangular cast landed at least one
  ray on the triangle.
- `survived_transient_rejection`: at least one of those rays was not thrown away
  as a person, a vehicle or clutter standing in front.
- `walk`: and the entity class it collected carries a material in
  `vistas_material_prior`. This is the set `bind_from_walk` actually binds, so
  it is the only one that changes a number.
- `fishnet`: the stricter cut surface set of `semantic_twin/fishnet.py`, joined
  on triangle centroids.

At Korenmarkt over the 130 m crop the three walk masks cover 7.22, 7.00 and 6.88
percent of triangles, and weighted by the power incident at the first
interaction at a station position they read 0.897, 0.896 and 0.894. The pipeline
between "the camera's ray landed here" and "this triangle has a measured
material" loses three parts in a thousand of the power it starts with, so
nothing below is an artefact of transient rejection or of a hole in the material
prior. The evidence is thin because the stations see a small part of a 130 m
crop, and for no other reason. Every coverage number in this document is
therefore quoted on the `walk` mask, and the other two would move it in the
third decimal.

## Result 1: the first interaction, and one station that fails it

Korenmarkt, 130 m crop, 15 GHz, 200,000 rays per standpoint, traced at each of
the eight admitted Mapillary station positions. Fraction of the power incident
at each depth that lands on a triangle with measured material:

| station, ordered by skyline residual | bounce 1 | bounce 2 | bounce 3 |
| --- | --- | --- | --- |
| 1084407470281938, 1.08 deg | 0.998 | 0.965 | 0.915 |
| 582445657694750, 1.30 deg | 0.998 | 0.952 | 0.890 |
| 1019442960256615, 2.15 deg | 0.997 | 0.962 | 0.897 |
| 3367014310197013, 2.32 deg | 0.995 | 0.959 | 0.901 |
| 706535575184668, 2.39 deg | 0.996 | 0.958 | 0.902 |
| 1419513849204492, 3.06 deg | 0.978 | 0.909 | 0.823 |
| 986493819697753, 3.08 deg | 0.999 | 0.963 | 0.919 |
| **1304023184185511, 3.67 deg** | **0.362** | **0.351** | **0.226** |

Seven of the eight confirm the geometric argument to within two parts in a
thousand. The eighth does not, and it is the station with the largest skyline
residual in the admitted set. Its registered position sits in the middle of the
square, eight metres from a station that scores 0.999, so this is not a station
that stands somewhere nobody walked.

It is a pose, and there is independent confirmation of that rather than an
inference. The same camera was re-registered when
`build_site_semantics.py` built the 250 m binding, which moved it from
`(6.37, 2.62, 53.31)` to `(2.42, -0.88, 54.68)`, 5.3 m horizontally and 1.4 m
vertically. At the new pose it scores **1.000, 0.962, 0.919**, in line with every
other station. Both poses passed the same admission gate on the same 3.67 degree
skyline residual, so the residual cannot tell them apart and the first
interaction coverage can. That is worth stating as a method result and not only
as a defect report: **the fraction of first bounce power landing on observed
geometry is a sharper test of a panorama pose than the skyline residual is**,
because it asks what the camera is looking at rather than how well its horizon
lines up, and it costs one trace.

The practical consequence is narrower than it first looks. The 130 m Mapillary
binding, which is what every published `--materials walk` number at Korenmarkt
rests on, carries the stale pose. The 250 m binding does not.

Excluding that one station, the first interaction at 130 m is covered with
probability 0.978 to 0.999. The residual two percent is the ray grid resolution:
a triangle small enough to fall between adjacent rows of a 1536 row
equirectangular cast collects no rays and is therefore not observed, whatever
the camera saw.

The same measurement at the 250 m crop, which is the radius every headline
number uses, over the four sites that have a fused station binding there. Power
weighted coverage pooled over each site's station positions:

| site | stations | bounce 1 | bounce 2 | bounce 3 |
| --- | --- | --- | --- | --- |
| Korenmarkt | 9 | 0.999 | 0.965 | 0.901 |
| Brussels Grand-Place | 8 | 0.998 | 0.958 | 0.878 |
| Madrid Plaza Mayor | 6 | 0.992 | 0.956 | 0.874 |
| Mexico City Zocalo | 12 | 0.941 | 0.920 | 0.898 |

Thirty five stations across four cities, and 31 of them sit between 0.96 and
1.00 at the first interaction. The five that do not are all at the Zocalo, which
is by a wide margin the largest square in the set, and they fall as low as 0.696.
That is the ray grid again rather than a pose: a facade 150 m away subtends
fewer pixel rows than one 30 m away, so more of its triangles fall between rows
of the cast and never collect a ray. The instrument's reach is finite and the
Zocalo is the site that exceeds it.

## Result 2: the second interaction, measured rather than argued

Same run, now against the distance from the standpoint to the nearest admitted
station. Median over standpoints of the fraction of incident power landing on
measured material:

| metres to nearest station | standpoints | bounce 1 | bounce 2 | bounce 3 | bounce 4 |
| --- | --- | --- | --- | --- | --- |
| 0 to 5 | 8 | 0.996 | 0.959 | 0.899 | 0.862 |
| 5 to 10 | 4 | 0.990 | 0.951 | 0.894 | 0.851 |
| 10 to 20 | 5 | 0.954 | 0.933 | 0.883 | 0.844 |
| 20 to 40 | 7 | 0.511 | 0.591 | 0.590 | 0.597 |
| 40 to 80 | 24 | 0.106 | 0.190 | 0.199 | 0.211 |

The same table at the 250 m crop, four sites, first interaction only, so the
decay can be compared across cities:

| metres to nearest station | Korenmarkt | Brussels | Madrid | Zocalo |
| --- | --- | --- | --- | --- |
| 0 to 5 | 0.999 | 0.999 | 0.999 | 0.988 |
| 5 to 10 | 0.991 | 0.995 | 0.991 | 0.987 |
| 10 to 20 | 0.916 | 0.997 | 0.997 | 0.789 |
| 20 to 40 | 0.542 | 0.595 | 0.991 | 0.338 |
| 40 to 80 | 0.176 | 0.006 | 0.133 | 0.077 |

The radius is not a constant of the method, it is a property of how a square was
walked. Madrid holds 0.991 out to forty metres because its six stations are
spread across the plaza. Korenmarkt and Brussels are through the floor by then
because theirs are clustered. The one thing all four agree on is the shape:
essentially total coverage inside about ten metres, and essentially none past
forty.

The author's claim is vindicated empirically, and the measurement gives it
something the claim did not have, which is a radius. Within twenty metres of a
registered panorama the second interaction still lands on measured material 93
to 96 percent of the time, and even the third does so about 89 percent of the
time. Beyond forty metres the whole thing collapses, and it collapses hardest at
the first interaction, which falls to 0.106 while the later ones sit near 0.20.
That inversion is worth stating because it is the opposite of what the argument
predicts and it has a plain explanation: far from any station the first
interaction is local geometry nobody photographed, and the later bounces diffuse
back toward the photographed core of the square.

So the evidence argument is a statement about a twenty metre neighbourhood of a
panorama, not about a square. It is exactly true where the instrument stood and
it decays with distance from it.

**This has a consequence the study has to own.** The published walk is spread
over a 90 m radius. Pooled over the 40 walk standpoints, the coverage of the
first interaction is 0.479 and of the second 0.484. The eleven city results are
run with `--materials geometric` and use no image evidence at all, so nothing
there is affected. But the Korenmarkt evidence ladder, which is where the image
evidence enters a result, is measured over that same 90 m walk, and rather less
than half of the power at its first interaction lands on a triangle any panorama
saw. The material assignment is first hand near the stations and an orientation
rule elsewhere, and the walk radius decides the mixture. If the argument for the
bounce budget is that the evidence covers the early bounces, the honest reading
is that it does so at the standpoints the instrument occupied and not across the
walk as published.

## Result 3: how much power the uncovered depths carry

Coverage alone would overstate the problem. Share of all launched power arriving
at a surface at each depth, at the station positions:

| depth | share of launched power incident | cumulative |
| --- | --- | --- |
| 1 | 0.790 | 0.790 |
| 2 | 0.0885 | 0.878 |
| 3 | 0.0119 | 0.890 |
| 4 | 0.0019 | 0.892 |
| 5 | 0.0003 | 0.8923 |

The third interaction carries 1.2 percent of launched power and everything
beyond the three bounce budget carries 0.22 percent.

Multiplying the two gives the number a reader actually needs, the share of all
launched power that has touched a surface with no image evidence behind its
material by a given depth:

| depth reached | at a station position | over the published 90 m walk |
| --- | --- | --- |
| 1 | 0.0834 | 0.3976 |
| 2 | 0.1011 | 0.4388 |
| 3 | 0.1053 | 0.4437 |
| 8, the reference | 0.1063 | 0.4445 |

At a station position, stopping at three bounces leaves 10.5 percent of launched
power having touched guessed material, and tracing five bounces further raises
that to 10.6. The extra depth buys one part in a thousand of extra guessing and
nothing else. That is the whole case for stopping at three: depth four onward
cannot be justified by evidence, and it also cannot repay the trace, because
there is almost nothing there.

The right hand column is the same statement over the published walk, and it is
the uncomfortable one. It is not the bounce budget that puts it at 0.44. It is
the walk radius, and the budget is irrelevant to it.

## What the three bounce budget costs

Same 40 Korenmarkt standpoints, 130 m crop, every budget traced from the same
script with the same seeds so only the budget moves. That construction is the
point and not a convenience: the section after this one shows that diffing a
rerun against a run on disk measures whatever else changed in between, and
usually that is not the budget. Quoted against an eight bounce reference with
roulette switched off. Negative is low, which truncation always is.

| budget | isotropic, dB | rooftop, dB | street small cell, dB | standpoints over 0.5 dB |
| --- | --- | --- | --- | --- |
| L = 3, roulette off, the new default | -0.0015 (worst 0.006) | -0.0023 (worst 0.016) | -0.0026 (worst 0.063) | 0 of 40 |
| L = 3, roulette from bounce 3 | -0.0014 (worst 0.006) | -0.0023 (worst 0.021) | -0.0030 (worst 0.116) | 0 of 40 |
| L = 4, the superseded eleven city run | -0.0003 (worst 0.002) | -0.0006 (worst 0.017) | -0.0016 (worst 0.171) | 0 of 40 |
| L = 6, the evidence ladder | -0.0002 (worst 0.002) | -0.0002 (worst 0.017) | -0.0013 (worst 0.176) | 0 of 40 |

Medians of the per standpoint dB difference, with the largest absolute
difference over the 40 standpoints in brackets. Dropping from the published
budgets to three costs a median of about two thousandths of a decibel and never
moves a standpoint by more than 0.12 dB. Not one standpoint out of 40 moves half
a decibel at any budget, so the choice between 3, 4 and 6 is invisible in every
published number.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street small cell columns
> are integrals against the old bands, so the cost of the budget in decibels moves with
> the law. The decision does not, because the isotropic column alone puts the cost three
> orders of magnitude below anything the study reports.

## The reruns, and what they cannot be compared against

The eleven city set and the Korenmarkt evidence ladder were both rerun at three
bounces under the `_L3` tag, beside the published runs rather than over them.
Both completed, all eleven sites and all three rungs, 80 and 120 standpoints
each.

Diffing them against the published runs was the obvious check and it is
misleading, so here is what it actually measures.

**The eleven city set.** Only Korenmarkt is comparable. The 250 m meshes are
byte for byte the same in triangle count at every site, but the measured ground
datum is not, because `measure_ground_datum` changed in this working tree
between the two runs. The walk is built from that datum, so the standpoints
moved:

| site | datum, `_L3` | datum, `city250_corrected` | shift |
| --- | --- | --- | --- |
| Korenmarkt | 50.871 | 50.837 | 0.034 m |
| Mexico City Zocalo | 2223.384 | 2223.397 | 0.013 m |
| Brussels Grand-Place | 65.565 | 65.782 | 0.217 m |
| Toulouse Capitole | 191.226 | 205.169 | 13.943 m |
| Krakow Rynek | 250.938 | 269.124 | 18.186 m |

At Korenmarkt, where the datum barely moved, the paired difference is a median
-0.001 dB isotropic, -0.004 dB rooftop and -0.013 dB street, with 1 standpoint
of 80 exceeding 0.5 dB. That is the budget, and it agrees with the paired sweep
above. At Krakow the same diff reads -1.2, -5.3 and -12.8 dB, and none of it is
the budget. **No cost of the bounce budget should be read off the eleven city
diff.** The `_L3` set stands as the new operating point run, not as a difference
against the old one.

**The evidence ladder.** Not comparable at all, and for a cleaner reason. The
published rungs ran on 2026-08-01 and 08-02, before the elevation law of
MONOSTATIC_SBR.md section 2.7 was corrected. The signature is unmistakable:
isotropic moves by -0.002 dB, which is the budget, while rooftop moves by
+2.16 dB and street by +1.01 dB at essentially every one of the 120 standpoints.
The isotropic model does not depend on the elevation law and the other two were
re-derived, so that split is the law and not the budget.

What the rerun ladder does say, on its own terms and under the corrected law at
three bounces, is that the ladder's conclusion survives. Going from no image
evidence to 3.1 percent of area from one panorama moves the distribution median
by +0.150 dB, and to 10.6 percent from eight fused stations by +0.366 dB. The
published figures under the old law were +0.008 and +0.289 dB. The numbers move,
the finding does not: adding image evidence moves the exposure distribution by
well under half a decibel.

> **Old illumination law, see `LAW_CHANGE.md`.** The +2.16 dB signature and the ladder
> shifts both belong to the old law, once before and once after its elevation support was
> fixed. The reasoning survives as a record of what a law change looks like in a diff, and
> the numbers become moot rather than wrong, since that law is now being replaced.

**One thing found while doing this, which is not mine to fix.** Two published
files under `outputs/exposure_korenmarkt` have malformed JSONL rows,
`city250_corrected_newyork_timessquare` with two and
`city250_corrected_prague_staromestske` with one, and the latter holds 81 rows
where every other site holds 80. That is the signature of two writers appending
to one file. Every `_L3` file is clean at exactly 80.

## The bias the estimator now carries, and its sign

This is the part that must not go quiet. The truncated throughput share, which
is the share of escaping power still travelling when the budget ran out, over
the same 40 standpoints:

| budget | median | p90 | worst standpoint |
| --- | --- | --- | --- |
| L = 3, roulette off | 0.0037 | 0.0086 | 0.0201 |
| L = 3, roulette from bounce 3 | 0.0038 | 0.0087 | 0.0205 |
| L = 4 | 0.00048 | 0.0012 | 0.0032 |
| L = 6 | 0.00001 | 0.00003 | 0.00009 |

At three bounces the truncation stops being a rounding diagnostic and becomes
the error term. **The estimator is biased low.** It is biased low by
construction, because truncation deletes power and never adds it, and the size
of the deletion is 0.38 percent of escaping power at the median standpoint and
2.05 percent at the worst. Every susceptibility, absorbed power and whole body
SAR figure computed at this budget is a lower bound in that sense, and the bound
is tight: the 0.38 percent of escaping power maps to 0.002 dB of chi, roughly a
factor of eight smaller, because the truncated tail is deeply diffused and the
directional illumination models weight it far below the early bounces.

Reported as a number rather than as a reassurance: at three bounces the study
under-reports by a median 0.002 dB and by at most 0.06 dB at the worst standpoint
under the worst of the three illumination models.

> **Old illumination law, see `LAW_CHANGE.md`.** Turning 0.38 percent of escaping power
> into 0.002 dB of chi uses the old directional weights, so the 0.002 dB and the 0.06 dB
> move. The escaping power share and the sign of the bias do not, and they are the result.

## Russian roulette no longer does anything, and it is switched off

Roulette fires when `depth + 1 >= roulette_start`, and `roulette_start` is 3, so
at a three bounce budget it fires once, after the third interaction, one
iteration before the hard cap drops whatever is left.

One thing has to be got right here, because it is easy to state backwards.
Roulette is not what removes the truncation bias. It is unbiased by
construction, dividing the surviving throughput by the survival probability, so
switching it off does not move the expectation at any budget and switching it on
does not repair a hard cut. What roulette trades is variance against work: it
kills weak rays so they need not be intersected again, at the cost of inflating
the survivors.

At three bounces the work it saves is one intersection call, and the survival
probability is floored at 0.05, so most rays reaching that depth are killed with
probability 0.95 and the few survivors are boosted twentyfold.

The direct test is a repeated seed one, because variance is the only thing
roulette can move. Four standpoints, eight independent seeds each, relative
standard deviation of chi, median over the four:

| | isotropic | rooftop | street small cell | wall clock |
| --- | --- | --- | --- | --- |
| roulette from bounce 3 | 0.00070 | 0.00665 | 0.01863 | 101 s |
| roulette off | 0.00070 | 0.00668 | 0.01863 | 100 s |

**The measurement says roulette does nothing at this budget.** Not that it is
harmful, not that it helps. The relative standard deviation agrees to three
significant figures on all three models, the expectation is unchanged because
roulette is unbiased whichever way it is set, and the wall clock is the same to
within what a contended box can resolve. The paired comparison against the eight
bounce reference
does look better with it off, worst standpoint 0.063 dB against 0.116 dB on the
street model, but that is one sample of a noisy quantity and the repeated seed
test above is what should be believed. It is not evidence that roulette adds
variance.

**Decision: roulette is switched off at the three bounce budget.**
`TraceConfig.roulette_start` is now `DEFAULT_MAX_BOUNCES + 1`, which is a
relationship rather than a literal, and two tests pin it: one asserts the
constants stay ordered, the other traces inside a closed sphere and asserts that
no ray is killed by roulette and every ray is truncated at the budget.

The justification is simplicity, not accuracy, and it should be read that way. A
step that provably changes no number should not be in the loop, and leaving it
there would mean the estimator quietly carries a twentyfold weight inflation on
a handful of rays for no measured return. Removing it makes the truncation the
estimator's only approximation, which is the thing this document has to state a
size and a sign for. Anyone running a longer budget still gets roulette from
bounce four onward, where it does buy work.

## Where this measurement does not support the argument

Stated plainly, because a clean negative is worth more than a tidy story.

- The first interaction guarantee is geometric only at a standpoint a camera
  occupied. It is not a property of the square, and across the published 90 m
  walk it holds for less than half the power.
- One of the eight admitted Korenmarkt stations fails the first interaction test
  outright, at 0.362. Its skyline residual passed the admission gate. The gate
  is therefore not sufficient.
- Three is justified by evidence at depth one and by power at depths four and
  beyond. At depths two and three it is justified by neither: the coverage there
  is measured, it is high near a station and low away from one, and it is an
  empirical fact about this panorama set rather than anything the method
  guarantees.
- The cross city confirmation covers four sites, the only four with a fused
  station binding at 250 m. Seven of the eleven cities have no image evidence at
  all, so the first interaction claim is untested at them and their exposure
  numbers use `--materials geometric` and depend on none of this.
- The one site that is large enough to strain the instrument, the Zocalo, is the
  one where the first interaction claim is weakest, at 0.941 pooled and 0.696 at
  its worst station. The claim is therefore conditional on the square being small
  enough for a 1536 row cast to resolve its facades, and the study has one
  example of a square that is not.

## Reproducing this

```bash
python measure_bounce_evidence.py --site korenmarkt --crop-m 130 \
    --locations 40 --rays 200000 --seed 7
python measure_bounce_evidence.py --site korenmarkt brussels_grandplace \
    madrid_plazamayor mexico_zocalo --crop-m 250 --locations 40 --rays 200000

python run_exposure.py --all-sites --locations 80 --rays 200000 \
    --crop-m 250 --max-bounces 3 --seed 7 --tag-suffix _L3
for m in geometric semantic walk; do
  python run_exposure.py --locations 120 --rays 200000 --crop-m 130 \
      --max-bounces 3 --seed 7 --materials $m --tag korenmarkt_${m}_L3
done
python run_exposure.py --coverage-report --tag-suffix _L3
```

Output lands in `outputs/bounce_budget/` and, for the reruns, under the `_L3`
tag in `outputs/exposure_korenmarkt/` beside the published runs rather than over
them.

Everything above was traced on `blgpu` through `tools/blgpu.sh`, described in
REMOTE_COMPUTE.md. That is a claim about the machine and not about the numbers,
so it was checked rather than assumed: one Korenmarkt standpoint at the 130 m
crop, seed 7, 200,000 rays, traced on both machines, agrees to every digit of
the float64 repr on all three susceptibilities, on the sky fraction and on the
truncated throughput share.

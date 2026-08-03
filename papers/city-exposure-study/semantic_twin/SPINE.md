# The spine

What this paper argues, in the order it argues it. Every number here is traceable
to a file named beside it. This exists so a drafter can write the whole paper
without reconstructing the argument from the working notes, which are organised
by when things were discovered rather than by what a reader needs first.

The paper is one methods section plus results. `paper/methods.tex` is drafted and
builds to nine pages. Everything below the methods heading here is what still
needs writing.

---

## The one sentence

The shape of a city square changes how much radio power reaches a pedestrian at
15 GHz, that change is a property of the built geometry rather than of the
network, and it can be measured from a photogrammetric mesh with one ray trace
per standpoint.

**And the first thing it measures is that the square is close to the wrong
unit.** Comparing the spread of $\chi$ across the 80 standpoints inside one
square against the spread of the eleven square medians, both as p95 over p05 in
dB:

| model | between the eleven squares | within a square, min / median / max | squares whose own spread exceeds the between spread |
|---|---|---|---|
| isotropic | 3.71 | 1.70 / 3.92 / 6.46 | 6 of 11 |
| macro rooftop | 4.93 | 2.55 / 5.46 / 12.89 | 8 of 11 |
| street small cell | 9.58 | 4.80 / 8.43 / 19.01 | 4 of 11 |

*(Recomputed directly from the `_L3` summaries in session, not taken from a
report.)*

**State this at exactly its strength and no further.** For the two models where a
base station is above the head, the typical square already spreads $\chi$ by more
than the eleven squares differ from each other, and for the rooftop model 8 of 11
squares do individually. For the street small cell model it does not: that model
has the largest between square spread of the three and the median square falls
short of it. So the honest claim is that a single number per square is a poor
summary of that square under most of the deployments considered, not under all of
them. The counter case is named rather than dropped.

That claim is only available to a method that is cheap per standpoint. Ray
tracing between known transmitter and receiver pairs costs one trace per pair, so
sampling 80 standpoints against a realistic set of deployments is what gets cut
first, and a single representative point per square is what gets reported
instead. The adjoint move makes the within square distribution the thing that is
free and the deployment that is amortised, which is why this is the first result
rather than a caveat at the end.

*Numbers: `AGGREGATE_REBUILD.md`. The claim about what per-pair tracing can
afford is an argument about cost, not a measurement of anyone else's study, and
should be written as such.*

## The quantity

$\chi = S / S_0$. Power density arriving at the head in the real square, over the
power density the same network would deliver at the same point over open ground.
Dimensionless, 1 in free space, below 1 where buildings shadow more than they
reflect, above 1 where they reflect more than they shadow.

The ratio and not the level, because the level is not knowable. The same site
density that builds the model puts $S_0$ between 0.0075 and 3.0 W/m² for rooftop
macro sites and 0.010 to 4.1 W/m² for street cells, across 25 to 100 sites per
km² at 55 to 75 dBm, against a 10 W/m² general public reference level. Three
orders of magnitude, set by numbers that are not public. The ratio removes all of
it. *(verified in session; ICNIRP 2020 general public, 2 to 300 GHz.)*

## The move, and why it is more than a speed trick

Compute at the person, not at the transmitter. Launch rays from the head, follow
them until they leave the square, weight each by how likely a base station is to
sit in the direction it left. One trace answers the question for every base
station position at once.

The speed argument is the obvious one and it is the less interesting one. The
real consequence is that the transmitter and the receiver sit at the same point,
so **a street level photograph taken from that same point sees the surfaces the
early bounces will hit**. Material becomes measured rather than assumed, and how
far that measurement reaches is what sets the bounce budget. That is the thread
the whole paper hangs on and it should be visible from the first page.

---

## The evidence chain, in order

### 1. The closed loop guarantee is exact, and it is measured

For a path that returns to where it started, both ends are visible from the same
viewpoint, so the first two interactions land on surfaces the photograph saw.
Traced at 42 standpoints across four meshes on three continents, Korenmarkt,
Brussels Grand Place, Milan Duomo and Tokyo Hachiko, with the visible set built
by 2e6 ray first hit probing from each standpoint:

| chain fully on visible surfaces, median | order 1 | order 2 | order 3 |
|---|---|---|---|
| closed loop | 1.000000 | 0.999972 | 0.980 |
| outward path | 0.999103 | 0.912004 | 0.714182 |

The spread across the four cities is a few percent. The theorem is the sign, the
gap is a property of the scene. The third order falls because the cover is over
the two ends of a loop and not over its middle.

Cross checked against `BOUNCE_BUDGET.md`, which used a different mask, an
equirectangular panorama cast rather than a ray probe, and a different
definition, per depth last surface rather than whole chain: 0.996 / 0.959 /
0.899 there against 1.0000 / 0.9638 / 0.8748 here on the fused walk.

*Source: `MONOSTATIC.md` §5.1, `run_monostatic.py --visibility`.*

The co-located return itself does not predict the susceptibility and that
question is closed. Over 440 standpoints the return is 98.6 % first order at a
4.05 m two way range, median -70.81 dB against a closed form rough half space at
-70.99 dB: an isotropic co-located pair in a square is looking at its own
pavement. Pooled Spearman against $\chi$ is -0.526 but the partial correlation
holding sky fraction fixed is -0.010, and sky fraction alone correlates at
+0.961. Across eleven site medians $\chi$ moves 3.91 dB and the return moves
0.71 dB. The second order component does survive, partial correlation -0.345
against the reflected part and negative at all eleven sites, but it is 0.37 % of
received power and 24 dB under the pavement clutter, so it is retired on dynamic
range rather than on physics. *(`MONOSTATIC.md` §7.)*

This vindicates the claim made at the start of the project and later called an
over-claim. It was not an over-claim, it was a claim about the monostatic branch
that got applied to the adjoint one.

### 2. The adjoint move costs exactly half that guarantee

An outward path holds 0.916 at the second interaction and 0.736 at the third, so
the estimator carries 8 % of its power over surfaces the standpoint cannot see by
the second bounce and 26 % by the third. That is the price of the efficiency and
it is stated rather than absorbed.

### 3. Panorama coverage is a radius, not a property of a square

Seeing a surface and having photographed it are different questions. Where a
camera stood they nearly coincide. Power weighted coverage across 35 stations in
four cities: bounce 1 = 0.941 to 0.999, bounce 2 = 0.920 to 0.965, bounce 3 =
0.874 to 0.901.

**The method result nobody asked for.** One of eight Korenmarkt stations returned
0.362 at the first interaction. The same camera, re-registered for the 250 m
binding, scores 1.000. Both poses passed the same 3.67° skyline residual gate.
**First bounce coverage is a sharper pose test than the skyline residual, and it
costs one trace.** That is a reusable result about registration, not a caveat
about this square.

Away from a camera they come apart. Within 20 m the second interaction still
lands on photographed material 93 to 96 % of the time; beyond 40 m every depth
falls below 0.21. **Pooled over the published 90 m walk, first interaction
coverage is 0.479.**

*Source: `BOUNCE_BUDGET.md` §"Result 1", §"Result 2".*

### 4. Where the power is, which is what makes three bounces enough

| depth | share of launched power |
|---|---|
| escapes untouched | 10.7 % |
| 1 | 79 % |
| 2 | 8.9 % |
| 3 | 1.2 % |
| 4 and beyond | 0.22 % |

Against an eight interaction reference at fixed seeds over 40 standpoints,
$L = 3$ costs a median 0.002 dB and never moves a standpoint by more than
0.12 dB. Zero of 40 move half a decibel under any illumination model.

**The joint of coverage with power is the closing argument.** Track the share of
launched power that has touched material which was guessed rather than
photographed, cumulative over bounces, and compare stopping at three against
tracing all the way to eight:

| site and crop, at station positions | L = 3 | L = 8 |
|---|---|---|
| Korenmarkt 130 m | 0.1053 | 0.1064 |
| Korenmarkt 250 m | 0.0049 | 0.0051 |
| Brussels 250 m | 0.0073 | 0.0077 |
| Madrid 250 m | 0.0115 | 0.0119 |
| Mexico City 250 m | 0.0591 | 0.0597 |

and pooled over all standpoints rather than at stations, where the absolute level
is far higher, the same increment: Korenmarkt 250 m 0.3631 to 0.3639, Mexico City
0.3857 to 0.3876, Madrid 0.1797 to 0.1805.

*(Recomputed in session from `outputs/bounce_budget/*_bounce_evidence.json`.)*

**The absolute level is not the result and varies by two orders of magnitude with
where you stand. The increment is the result, and it is about a tenth of a
percentage point everywhere.** Tracing five more bounces does not buy evidence,
it only buys more guesses about less power. That is what makes three a budget
rather than a preference: not that deeper bounces carry little energy, though
they do, but that deeper bounces carry no more *warrant*.

Care with this number in drafting. Earlier notes quote the pair 10.5 % against
10.6 %, which is the Korenmarkt **130 m** crop and not the published 250 m one,
where the same pair reads 0.49 % against 0.51 %. Quote the increment, or quote a
level with its crop attached.

Truncation biases $\chi$ low. The share of escaping power still in flight at the
cut is 0.0038 median, 0.021 worst. Russian roulette cannot repair a hard cap and
at this budget would fire once at a 0.05 floor, inflating survivors twentyfold,
so it is switched off. Measured: not slower, and the worst standpoint deviation
halves.

*Source: `BOUNCE_BUDGET.md` §"Result 3", §"What the budget costs", §"Roulette".*

### 5. Diffraction is bounded on this geometry, not argued away from the literature

A dense sky mask at each standpoint, 720 azimuths by 600 log spaced elevation
bands, 432k cells, on the same 250 m meshes and the same standpoint coordinates
as the eleven city run. Every shadowed direction gets a Fresnel-Kirchhoff
parameter $\nu = \theta\sqrt{2d/\lambda}$ from ITU-R P.526-16 eq. (27), and the
knife edge loss of eq. (31) is integrated against the illumination measure. Ran
on the 20 most enclosed standpoints of the 3 most enclosed squares, 60 total.

**The validation comes first and it is the first external check any part of this
tracer has had.** The same mask integrated over the *visible* directions
reproduces the production tracer's $\chi_\mathrm{dir}$ to 0.10 to 0.34 %
isotropic, 0.84 to 1.73 % rooftop, 2.3 to 7.3 % street. Independent code path,
independent quadrature, independent ray budget. That is what makes the blocked
half believable.

| uplift on $\chi$, dB | median | 90th | max | median at 2 GHz |
|---|---|---|---|---|
| isotropic | 0.06 | 0.13 | 0.19 | 0.18 |
| macro rooftop | 0.15 | 0.37 | 1.20 | 0.53 |
| street small cell | 0.44 | 1.84 | 12.64 | 1.82 |

Every assumption errs upward: a single absorbing half plane, a distant source, no
re-blocking, a knife edge rather than a lossy wedge, P.526's angle form used past
its 12° validity, and the diffracted term multiplied by each standpoint's own
multipath gain so that diffract-then-reflect paths are covered. 93 to 98 % of the
bound sits inside the 12° validity for isotropic and rooftop. The 2 versus 15 GHz
ratio of 3.1 to 5.0 times reproduces the frequency argument on this geometry
rather than borrowing it.

Against a within square spread of 8.1 dB, 0.15 dB touches nothing.

**The concession not argued away**: under the street small cell model the bound
is not small. 87.9 % of that model's measure sits below 5° elevation, and at 4 of
the 60 standpoints the entire elevation support is occluded, so
$\chi_\mathrm{dir}$ is exactly zero and every watt arrives by reflection. Those
standpoints also carry the smallest absolute $\chi$ in the study, of order 1e-5.

Grid convergence is honest but not tight: the ladder at the deepest Korenmarkt
standpoint runs 0.000689 / 0.000650 / 0.000734 / 0.000737 from 108k to 3.46M
cells, not monotone, with the production grid 13 % below converged because the
integrand varies on $\theta \sim \sqrt{\lambda/2d} \approx 1.3°$ for a 20 m edge,
close to the azimuth cell width. Worth 0.02 dB on a 0.15 dB uplift, so the
tabulated numbers are low by about that.

*Source: `WHY_NOT.md` §2.6, `bound_diffraction.py`.*

Three limits on the literature half of this argument, all found by red teaming
the draft and none to be quietly dropped:

- The mmMAGIC "no arrival above the noise floor" observation is **one location at
  58.68 GHz reached by a manual trace**, not a campaign wide result and not at
  14.8 GHz. There is no equivalent statement at 14.8 GHz in D2.2 or R1-160846.
- **Open sky above the head is the precondition for over rooftop diffraction, not
  a defence against it.** The argument holds cleanly for the street cell band,
  which sits below the roofline. For the rooftop band the sign argument has to
  carry it, because for a site shadowed by an intervening building the omitted
  term may be the leading one in those directions. Adhikari et al., INFOCOM 2025,
  is the direct counter example: over top beat street clutter scattering by 7 dB.
- **There is no published open square diffraction decomposition at any
  frequency.** All of it is street canyon, a waveguiding geometry. A square has
  fewer facades per unit solid angle, so the specular budget substituting for
  diffraction is thinner there. State it as a limitation.

The one counter citation to dispose of in text rather than be caught by: Du,
Chizhik and Valenzuela, TAP 2021, where a diffraction inspired model gives the
best around a corner fit at 28 GHz. Their own fitted corner loss is 2.2 dB
against a theoretical edge coefficient near -42 dB, so the functional form wins
while the physical mechanism is 40 dB short.

*Source: `WHY_NOT.md` §8, `LIT_VERIFICATION.md`.*

---

## Results, and the arc they make

### R1. Eleven squares

The headline. Geometric materials at every square, converged 250 m radius,
bounce budget 3, fixed ground datum. One writer, eleven sites, 880 standpoints,
zero torn records. Run tag `_L3`.

**Between city spread: 3.71 dB isotropic, 4.93 dB rooftop, 9.58 dB street small
cell. Largest within city spread: 6.46 dB isotropic at Madrid, 12.89 dB rooftop
and 19.01 dB street, both at Brussels.** See the table under "the one sentence"
for the full within against between comparison, and quote it in that form rather
than as a single margin, because the comparison goes the paper's way for two of
the three illumination models and not for the third.

Mexico City Zocalo is the most exposed square. Krakow's old reading as the dark
red outlier is gone: those standpoints sat on the Cloth Hall roof and the ground
datum fix moved Krakow by -1.40 dB isotropic and -12.97 dB street, Toulouse off
the Capitole roof by -1.29 and -2.61 dB. Every other site moves under 0.25 dB
isotropic, which is the datum estimator and not the bounce budget, since
`BOUNCE_BUDGET.md` puts 4 to 3 at about 0.002 dB median.

Spearman rooftop against isotropic +0.936, street against isotropic +0.345.

*Source: `AGGREGATE_REBUILD.md`. Figures `FIGURES/16_eleven_cities_exposure.png`,
`FIGURES/11_eleven_cities.png`.*

**Do not quote the older `_corrected` table.** `PAPER_METHODS.md` §9.2 and
`REPORT.md` still carry it and their Krakow and Toulouse rows are the roof.

### R2. The illumination law is the single most consequential modelling choice

Not a footnote. The earlier law placed sites at a fixed height, the corrected one
integrates the cone volume over the height band. Both laws are evaluated on the
**same rays at each crop**, so the level difference between them carries no Monte
Carlo noise at all. At Korenmarkt, 40 standpoints, 150k rays:

| | 130 m crop | 250 m crop |
|---|---|---|
| rooftop, law shift | +2.54 dB | **+5.67 dB** |
| street small cell, law shift | +0.84 dB | **+3.98 dB** |
| isotropic | unaffected by construction | unaffected |

*(Recomputed in session from `outputs/law_comparison/korenmarkt_law_comparison.json`.)*

A 5.67 dB shift is larger than the entire between square spread of 4.93 dB
rooftop. **The choice of illumination law matters more than the choice of city.**

The second half of that result is better than the first. The two laws do not just
differ by a level, they differ in how much the answer depends on the crop. Going
from a 130 m to a 250 m crop costs the fixed height law 3.64 dB rooftop and
10.08 dB street, but costs the corrected law only 0.51 dB and 6.94 dB. The
corrected law is the one under which the crop converges, so the correctness of
the law and the convergence of the geometry are the same question rather than two
independent ones.

**It does reorder the eleven cities, and it does so through one city rather than
through all of them.** Now measured, not asserted. Both laws are azimuth uniform,
so the sensitivity harvest evaluates them on the same rays at every standpoint of
all eleven sites, 40 per site at the published 250 m crop, and the difference
carries no Monte Carlo noise at all. The shift is not a common level: it runs
+1.05 to +6.33 dB rooftop about a mean of +5.14, and +1.45 to +4.41 dB street
about a mean of +3.43, with a residual rms about that mean of 1.39 and 0.98 dB.
Rank correlation between the two orderings is Spearman +0.65 and Kendall +0.64
rooftop, Spearman +0.88 and Kendall +0.78 street.

**Name the mover rather than quoting the correlation.** Nine of eleven sites
change rank rooftop and eight of eleven street, but only one site per model moves
more than two places: New York falls from 1st to 9th rooftop and Tokyo from 4th
to 8th street. Drop that one site and Spearman is +0.98 in both models with
nothing moving more than a single place. So the honest statement is that the law
is close to a level shift for nine or ten of the eleven squares and is not one at
the top of the table, which is where the reordering costs the most.

The mechanism is measured rather than argued. The old law is `1/sin^3` and puts
its mass just above its own support floor, so what it returned at a square was
set by how much power that square let in near the horizon. The share of the old
rooftop answer arriving below 5° runs from 0.046 at Madrid to 0.529 at New York
and predicts the per site residual at Pearson -0.97. New York's towers leave only
narrow near horizontal channels, which the old law rewarded and the corrected one
does not.

None of this is a noise artefact. The two laws share rays, so the differential
noise is exactly zero, and the unpaired floor of `CODE_AUDIT.md` §4.1 scaled to
40 standpoints is 0.024 dB rooftop and 0.059 dB street, against a 4.09 dB New
York residual. The harvested old law reproduces the old law production run
`cities250` to 0.24 dB at worst across the six sites free of the later ground
datum change, and the 0.04° elevation binning is worth at most 0.035 dB rooftop
and 0.105 dB street on any site's shift.

*Source: `run_law_comparison.py` for the Korenmarkt crop pair,
`run_law_ordering.py` and `outputs/law_comparison/eleven_city_law_ordering.json`
for the eleven.*

### R3. Material discrimination does not move exposure

Change only the material of the facades the entity axis had resolved to brick,
2950 m² of facade, 28.5 % of the entity brick area, including 1258 m² that goes
from rough brick to specular glass. Over 120 standpoints:

| illumination | entity median | facade material median | shift | over 0.5 dB | worst standpoint |
|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3379 | **+0.024 dB** | 0 of 120 | 0.110 dB |
| rooftop, corrected | 0.2354 | 0.2369 | **+0.029 dB** | 0 of 120 | 0.193 dB |
| street small cell | 0.0984 | 0.0989 | **+0.022 dB** | 1 of 120 | 0.929 dB |

**Say what those are against, carefully, because it is easy to quote the wrong
denominator.** They are against the 5th to 95th percentile spread *within
Korenmarkt* of 3.9 dB isotropic, 8.4 dB rooftop and 16.7 dB street. Not against
the between square spread. A fortieth of a decibel against 3.9 dB is the
comparison that is actually being made. Repeating it on the nine station rung
gives +0.023, +0.024, +0.014 dB, so the null does not depend on which walk set is
used and the ninth station does not make the material axis matter more.

Two VLM compositions that disagree strongly with each other give indistinguishable
$\chi$.

**The result that is not material discrimination, and it is the more interesting
one.** Replace the *whole* material field rather than only the facades, so the
ground changes too, and isotropic moves -0.218 dB with 15 of 120 standpoints past
1 dB and a worst standpoint of 2.020 dB. Rooftop moves -0.156 dB, street
-0.024 dB. That is roughly ten times the facade effect, in the opposite
direction, and it says the surface underfoot governs the answer more than the
walls around it do. The ordering is what one would expect from where the power
goes, since the ground takes the largest share of first bounces, but it means
material effort is better spent on the pavement than on the facades and that is
the opposite of where the photographs are pointed.

**This is not a negative result, it is the bound on the claim, and the bound is
now measured rather than asserted.** Put one material on every facade in
Korenmarkt, 24 standpoints, shared ray seeds, paired:

| every facade is | isotropic | rooftop | standpoints over 1 dB |
|---|---|---|---|
| render, the softest dielectric | -0.104 dB | -0.164 dB | 0 of 24 |
| stone, the hardest dielectric | +0.239 dB | +0.414 dB | 0 of 24 |
| **metal** | **+2.502 dB** | **+4.374 dB** | **24 of 24** |

The whole dielectric axis spans **0.34 dB isotropic and 0.58 dB rooftop**,
against a 3.3 dB isotropic spread of $\chi$ across standpoints in that one
square. **No facade material evidence of any kind can move $\chi$ further than
that.** Metal is the only escape, and it is a family call rather than a member
call.

So the photographs do not tune a permittivity. They establish which family a
square belongs to, masonry against glass and metal, which is the one material
distinction that does move $\chi$ and the one the mesh cannot supply. The
geometric assignment is licensed rather than merely convenient, and the results
hold for masonry squares because masonry is what was observed.

A vision model reading the facades lands inside that bracket and does not earn a
place on the material axis: street capture +0.177 / +0.378 dB, tile texture
+0.220 / +0.423 dB, against +0.102 / +0.213 dB for simply *drawing* from the
fixed prior instead of taking its argmax. More than half of what the model
delivers needs no model. The control, brick through the posterior path, is
+0.000 dB exact at every standpoint, so the experiment's noise floor is zero. The
tile texture variant is illegible on 76 % of crops and answers unknown on 33 of
38, yet produces the same shift to within 0.043 dB.

Two narrower findings do earn a place, and neither was the original proposal.
Mixing must happen in **power, not in labels**: the argmax discards the 3 % prior
mass on metal that carries 20 % of the mean reflected power, and drawing per face
is the only route to an error bar on $\chi$ from material ignorance. And
**glazing is a stack, not a label**: an insulating glass unit sits 1.8 to 3.2 dB
above a glass half space, which is the one place where what a vision model can
name is a different object from what the vocabulary contains.

*Source: `SAM3_LADDER.md`, `MATERIAL_VLM.md`. The bracket is 24 standpoints
rather than the ladder's 120, because the machine was carrying six other tracing
jobs.*

### R4. Beamforming that tracks the user cancels, and the version real networks use does not

Exact for full digital maximum ratio transmission: the matched filter delivers
the whole channel power, the $MN$ array gain is common to the square and to open
ground, so it cancels with no assumption about the paths.

Not exact for geometric steering or codebook beam selection. A reflected path
leaves the site toward its own last surface, tens of degrees off a beam aimed at
the head, so the array suppresses it. Treating each site as one far point makes
that offset vanish, which is why it *looks* invariant. The inequality is one
sided: steered $\chi$ can only fall below the reported value.

The element pattern never cancels under any policy: 0.26 dB at the rooftop
median elevation of 9.5°, 10.2 dB at the 60° top of the band.

*Source: `BEAMFORMING.md` §3.*

### R5. Bystanders, and a prediction that failed usefully

Geometry says a crowd is opaque along the horizon and transparent above ~10°: a
standing adult adds only 0.23 m above head height, so a ray clears the crowd
after $0.23/\tan\alpha$, which is 13 m at 1°, 2.6 m at 5°, 0.4 m at 30°.

The prediction from that was that the street model would be hit nine times harder
than the rooftop model, since they send 88 % and 9 % of their measure below 5°.
**Measured: 1.4 dB against 1.0 dB at two people per square metre.** A ratio of
1.4, not nine.

The reason is the result. The *sent* measure is not the *arriving* measure. The
arriving shares below 5° are 0.21 and 0.19, a ratio of 1.15, because the facades
have already redistributed the power before any crowd sees it. **A dense European
square is its own near horizon blocker, and a crowd is a second edit to a
distribution the buildings have already set.** Isotropic loses only 0.05 dB,
because weighting all directions equally makes redistribution free and leaves
only absorption to pay for.

The absorber control is what turns that from a story into a measurement. Replace
the bodies with index matched absorbers, so the geometry and the blockage are
identical and only the reflected half is removed, and the isotropic loss goes
from 0.049 to 0.708 dB while rooftop moves only 1.044 to 1.332 and street only
1.391 to 1.607. **A crowd is nearly invisible to the isotropic model because it
reflects, not because it fails to block.**

All of the above at 2.15 people per square metre, adult stature, 2867 bodies,
paired median over 12 standpoints. Noise floor on the same design: 0.009 dB
isotropic, 0.035 rooftop, 0.112 street median absolute, so the 1.0 and 1.4 dB
shifts sit 30 and 12 times above it and the 0.049 dB isotropic shift does not
clear it. Say that: the isotropic shift is consistent with zero.

*(Every number in this section recomputed in session from
`outputs/bystander_study/korenmarkt_15ghz_summary.json`,
`korenmarkt_absorber_15ghz_summary.json` and `korenmarkt_15ghz_noise_floor.json`.)*

**One consistency caveat that has to travel with it.** This study ran at
`max_bounces: 6` with roulette starting at bounce 3, which is the superseded
configuration, not the `L = 3` roulette off budget the headline uses. It is a
paired differential study, so the shift is far more robust than an absolute
level would be, but it has not been rerun on the current budget and should not
be presented as though it had.

*Source: `BYSTANDERS.md`.*

### R6. Convergence, reported as measurement not as choice, and one place it does not converge

Two different radii, and they must not be confused. The **mesh crop radius** is
raised until $\chi$ stops moving, which is what fixes 250 m. The converged radius
is a property of the illumination model, not of the square, so it is reported per
model. `FIGURES/15_crop_convergence.png`.

The **deployment box range cap** $\rho_+$ is a different parameter and it does
**not** converge. Swept continuously from 50 to 500 m it never saturates:
$\chi \propto d_\mathrm{max}^{-1.2}$ averaged over 100 to 400 m, worth 7.40 dB at
the median site rooftop and 9.24 dB street, from 2.67 dB at New York to 9.91 dB
at Madrid. The mechanism is the lower support edge, which moves from 7.7° to
1.9°. That is not a bug, it is what an unbounded uniform site density does, but
it means **no single absolute $\chi$ can be quoted without its cap**.

The sweep is free rather than expensive, and the reason is worth a sentence
because it is the same trick as the adjoint move: $\chi$ is linear in the
illumination density and every band law is azimuth uniform, so one trace reduces
to a 4500 bin elevation histogram and any height or range band is a dot product.
Every parameter value is therefore scored on identical rays and the differential
numbers carry no independent Monte Carlo noise. Harvested $\chi$ matches the
tracer's own to 1e-9 isotropic and 3e-3 street worst standpoint, and is bit
identical to the production run at Krakow and Toulouse.

**What survives the cap is the contrast.** Between city contrast swings 0.51 dB
median against 7.40 dB absolute, 14 times steadier, with eight of eleven cities
inside 0.75 dB. Name the three that are not: Brussels 1.92, Madrid 2.60, New York
4.64 dB. Two honest negatives travel with it: normalising by $\chi$ isotropic
gives *exactly* the same cap sensitivity, because it is a decomposition and not a
fix, and the ranking is not cap invariant, Spearman 0.81 with 7 of 11 sites
changing rank. So quote Spearman, do not claim a stable ordering.

**The crop and the cap were conflated in code and nothing checked one against the
other.** The crop is centred on the square while standpoints reach 90 m out, so
built extent is 180 to 227 m at the tenth percentile. At the published 250 m cap
0.5 to 7 % of $\chi$ rooftop comes from lines of sight with nothing built on
them, 20 % at New York. At 400 m that is 5 to 60 %, worth up to 4.17 dB, so a
400 m column is not supportable on a 250 m crop and must not be reported. Caps at
or below 175 m are clean everywhere.

Height edges are worth 0.3 to 1.9 dB rooftop. The cap dominates them not because
the physics is insensitive to height but because the assumed cap interval spans a
factor 2.7 against the ceiling's 1.3: per natural log the ceiling's elasticity is
65 to 90 % of the cap's. The four band edges are exactly scale free, so doubling
the box moves $\chi$ by 0.0 and the four elasticities sum to zero, verified to
0.034 dB per natural log. The tempting reduction to a single support edge fails,
a fit in $\arctan(h_-/d_\mathrm{max})$ explains 86 to 90 % of the surface against
97 to 99 % for $d_\mathrm{max}$ alone.

*Source: `SENSITIVITY.md`, `make_sensitivity_study.py`.*

---

## The honesty ledger

Everything a referee would find, found first and stated with its size and sign.

| what | size | direction |
|---|---|---|
| no diffraction | 0.06 / 0.15 / 0.44 dB median, isotropic / rooftop / street | biases $\chi$ **low** |
| unpolarised average, facades | ≤ 3.0 dB | biases low |
| unpolarised average, ground near 24° elevation | up to tens of dB, over 7.8 % of rooftop measure and 0.4 % of street | biases high |
| truncation at $L=3$ | 0.0038 of escaping power median | biases low |
| convex body, no limb self shadow | unquantified | unknown |
| image evidence | one square only, 0.479 pooled first interaction coverage | scope |
| the eleven city rerun cannot be diffed against its published counterpart | confounded by a concurrent ground datum change, 18.2 m Krakow, 13.9 m Toulouse, 0.034 m Korenmarkt | the only clean cost measurement is the paired budget sweep inside one script |
| the ladder rerun likewise | confounded by the elevation law correction, isotropic moves -0.002 dB while rooftop moves +2.16 dB at every standpoint | that is the law, not the budget |
| diffuse scattering strength is a modelled Rayleigh split, not fitted | ablating diffuse scattering moves published RMSE from 6 to 13 dB up to 25 to 37 dB at 28 and 38 GHz (Vitucci et al., Radio Science 2019) | unknown, and the larger referee risk than diffraction |

Two things that must not be quoted as measured:

- **The street small cell shift of 0.079 dB is 2.3 standard errors.** Not
  resolved. *(`CODE_AUDIT.md` §4.2.)*
- The 0.298 dB headline figure in older notes came from a superseded law and was
  never measured under the corrected one.

Monte Carlo standard errors, walk median over 8 seeds: 0.0042 dB isotropic,
0.0136 rooftop, 0.0343 street small cell. Per standpoint: 0.004, 0.024, 0.118.

**The material null is a resolved measurement, not a failure to detect.** The
+0.024 dB isotropic shift sits at about 5.7 times the 0.0042 dB walk median
standard error, so the design does see it. It is simply negligible. Write it that
way. "The shift is resolved and it is a fortieth of a decibel" is a much stronger
sentence than "no effect was found", and it is the true one. Do not quote the
older claim that the ladder negative survives at 83 and 27 times the noise, which
does not reconcile with either the shift sizes or the standard errors above.

The defence that the multiply reflected tail is depolarised **is not available**
at this frequency and has been retracted: measured cross polarisation ratio is
28 dB at zero excess loss, falling half a dB per dB, so an even split needs 56 dB
of excess loss and such a path carries nothing.

---

## What is written and what is not

- `paper/methods.tex`: drafted, nine pages, builds clean, one cosmetic overfull
  box. Every quoted number verified against its source or recomputed.
- Results: not drafted. R1 to R6 above are the beats.
- Introduction and related work: not drafted. `PRIOR_ART.md` and `WHY_NOT.md` §3
  hold the material, including the per pair discrete deployment baseline this
  formulation replaces.

## Rules the drafting must follow

No em dashes. No semicolons. Sentence case headings. No coined terms or invented
umbrella phrases. Single author, so no first person plural. Plain words, aiming
at explanations that are almost childish while staying professional. Do not
present a promise as a result: if a check has not been run, say it has not.

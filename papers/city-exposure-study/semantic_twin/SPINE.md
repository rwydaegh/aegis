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
15 GHz, that change is a property of the square rather than of the network, and
it can be measured from a photogrammetric mesh with one ray trace per standpoint.

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
Traced on the 617k triangle Korenmarkt mesh at twelve standpoints:

| chain fully on visible surfaces | order 1 | order 2 | order 3 |
|---|---|---|---|
| closed loop | 1.000000 | 0.999991 | 0.984 |
| outward path | 0.999 | 0.916 | 0.736 |

The theorem is the sign, the gap is a property of the scene. The third order
falls because the cover is over the two ends of a loop and not over its middle.

*Source: `MONOSTATIC.md` §5.1, `run_monostatic.py --visibility`.*

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
camera stood they coincide: first interaction coverage is 0.978 to 0.999 across
seven of eight registered stations. The eighth returns **0.362** and is a
registration failure that passed the skyline residual gate, so first interaction
coverage is the sharper pose test. It is excluded.

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

Truncation biases $\chi$ low. The share of escaping power still in flight at the
cut is 0.0038 median, 0.021 worst. Russian roulette cannot repair a hard cap and
at this budget would fire once at a 0.05 floor, inflating survivors twentyfold,
so it is switched off. Measured: not slower, and the worst standpoint deviation
halves.

*Source: `BOUNCE_BUDGET.md` §"Result 3", §"What the budget costs", §"Roulette".*

---

## Results, and the arc they make

### R1. Eleven squares

The headline. Geometric materials at every square, converged 250 m radius.
`FIGURES/16_eleven_cities_exposure.png`, `FIGURES/11_eleven_cities.png`.

### R2. The illumination law reorders the cities

The corrected law changed the ordering. This is the single most consequential
modelling choice in the study and it deserves its own beat, not a footnote.
`run_law_comparison.py`.

### R3. Material discrimination does not move exposure

+0.024, +0.029, +0.022 dB against between-square spreads of 3.9, 8.4 and 16.7 dB.
Two VLM compositions that disagree strongly with each other give indistinguishable
$\chi$.

**This is not a negative result, it is the bound on the claim.** The photographs
do not tune a permittivity. They establish which family a square belongs to,
masonry against glass and metal, which is the one material distinction that does
move $\chi$ and the one the mesh cannot supply. So the geometric assignment is
licensed rather than merely convenient, and the results hold for masonry squares
because masonry is what was observed.

*Source: `SAM3_LADDER.md`, `MATERIAL_VLM.md`.*

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

*Source: `BYSTANDERS.md`.*

### R6. Convergence, reported as measurement not as choice

Crop radius raised until $\chi$ stops moving, which is what fixes 250 m. The
converged radius is a property of the illumination model, not of the square, so
it is reported per model. `FIGURES/15_crop_convergence.png`.

---

## The honesty ledger

Everything a referee would find, found first and stated with its size and sign.

| what | size | direction |
|---|---|---|
| no diffraction | bounded, see `WHY_NOT.md` §2.6 | biases $\chi$ **low** |
| unpolarised average, facades | ≤ 3.0 dB | biases low |
| unpolarised average, ground near 24° elevation | up to tens of dB, over 7.8 % of rooftop measure and 0.4 % of street | biases high |
| truncation at $L=3$ | 0.0038 of escaping power median | biases low |
| convex body, no limb self shadow | unquantified | unknown |
| image evidence | one square only, 0.479 pooled first interaction coverage | scope |
| one registered station | excluded at 0.362 coverage | scope |

Two things that must not be quoted as measured:

- **The street small cell shift of 0.079 dB is 2.3 standard errors.** Not
  resolved. *(`CODE_AUDIT.md` §4.2.)*
- The 0.298 dB headline figure in older notes came from a superseded law and was
  never measured under the corrected one.

Monte Carlo standard errors, walk median over 8 seeds: 0.0042 dB isotropic,
0.0136 rooftop, 0.0343 street small cell. Per standpoint: 0.004, 0.024, 0.118.
The evidence ladder negative survives at 83× and 27× the noise.

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

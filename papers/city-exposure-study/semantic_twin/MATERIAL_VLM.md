# A vision model on the facade material axis

The material axis of this twin is not a model. It is a constant.

Mask2Former assigns a Mapillary Vistas entity per face, `vistas_material_prior`
in `semantics.json` maps that entity to a distribution over the RF vocabulary,
and `propagation/semantic_binding.py` takes the argmax. `Building` carries brick
at 0.30 against plasterboard at 0.20 and concrete at 0.15, so `Building` resolves
to brick every time, in every city, at every incidence. `Building` is 74.3
percent of bound face observations on the fused Korenmarkt walk, and only two of
the 65 entities with a prior have brick as their argmax at all. The geometric
fallback sends every unseen facade to brick as well. So both the evidence path
and the fallback path terminate at the same row, and 40.9 percent of the scene
area is that row.

This document builds the thing that was proposed to replace it, measures it, and
answers whether it earns its place.

**The short version.** A vision model reads Korenmarkt facades well, is stable
where it is confident, and is honestly under confident rather than over confident,
which is the good failure mode. Its composition genuinely disagrees with the fixed
prior. Traced through the tracer it moves chi by **+0.19 dB isotropic and
+0.38 dB rooftop**, with 0 of 24 standpoints moving as much as a decibel.

It does not earn its place, and the reason is a ceiling rather than a failure of
the model. Putting a single dielectric on every facade in the square, the softest
in the vocabulary against the hardest, spans **-0.104 to +0.239 dB**. **No facade
material evidence of any kind can move chi more than 0.34 dB here.** Half of what
the model does deliver is the argmax fix, which needs no model. And an image the
model itself calls illegible on 76 percent of crops, the Google 3D Tiles texture,
produces the same shift to within 0.03 dB, which is inside one variant's own seed
to seed spread. If the answer does not depend on whether the model could see the
building, the model is not what is producing the answer.

The one material decision with real leverage is dielectric against conductor.
Every facade metal is +2.50 dB isotropic and +4.37 dB rooftop and moves all 24
standpoints past a decibel. So image evidence establishes which family a square
belongs to, and inside the dielectric family it is not tuning anything worth
tuning. Korenmarkt is squarely inside that family and every method tested gets
the family right.

Two pieces do earn their place, and neither is the part that was proposed.
Dropping the argmax in favour of a draw from the posterior is worth +0.10 dB
isotropic and +0.21 dB rooftop, more than any new evidence, and costs nothing.
And a glazing unit is not a glass half space, which the layered machinery built
here can see and no single material label can.

## What was built

- `semantic_twin/facade_vlm.py`. The question, the response schema and its
  validator, a transfer matrix for a layered stack, posterior mixing and
  sampling, and the calibration functions.
- `semantic_twin/propagation/material_posterior.py`. A second binding backend
  that draws a material per face from a posterior instead of taking an argmax.
  It does not touch `semantic_binding.py`.
- `build_facade_crops.py`, `blind_facade_crops.py`, `make_vlm_batches.py`. Cut
  matched crop pairs, blind them, and plan the calls.
- `analyse_material_vlm.py`, `run_material_ablation.py`, `plot_material_vlm.py`.
- `tests/test_facade_vlm.py`, 21 tests.

Everything lands in `outputs/material_vlm/`.

## The evidence, and how it was made comparable

Nineteen facade crops were cut from the Korenmarkt Street View panorama, 384
pixels square, taken from the rectilinear views the segmenter already ran on and
kept only where Mask2Former calls at least 82 percent of the window `Building`.
Each crop's rays are cast into the double precision support mesh, so each crop
carries the triangles it looks at, their range, and their incidence. The nineteen
crops cover 12 physical patches on 8 walls, 1048 distinct triangles, 1.05 percent
of scene area and 2.57 percent of facade area, at ranges of 6.6 to 32.5 m and
incidences of 20 to 74 degrees.

The second source is the one that was suggested and that costs nothing, since the
tiles are already on disk. For each crop, the same rays are cast again and the
hit point is sampled out of the Google 3D Tiles texture atlas through the
matched tile triangle. That gives a texture image with **the same viewpoint, the
same field of view and the same pixel grid** as the panorama crop. The mesh to
tile correspondence matches 99.97 percent of faces at a median residual of
1.2 micrometres, so the two images of a pair are the same wall and not
approximately the same wall.

Both images of every pair were then renamed to a keyed digest, so nothing in the
filename says which source it came from, and shown to the model in shuffled
batches. Two draws per image, partitioned differently, so a repeat of one image
is answered by a call that has not seen the first answer. Seventy six responses,
none rejected by the schema validator. Thirty two transcript lines arrived with
the wrapper's closing brace missing and were repaired by appending braces only,
which is recorded in the manifest.

The model was asked for a layered stack with thicknesses, a relief pattern with a
pitch, an RMS height, a probability distribution over the nine traceable RF
materials, a stated confidence, and a legibility flag. The exact prompt is in
`outputs/material_vlm/prompt.txt` under digest `963203661b633b51`.

## The ceiling, before any evidence

Before asking whether a model reads facades correctly it is worth knowing what
the answer can buy. Half space power reflectance at 15 GHz, unpolarised, from the
ITU-R P.2040-4 rows this study already grounds:

| material | 0 deg | 45 deg | 60 deg | 75 deg |
|---|---|---|---|---|
| wood | -15.3 dB | -14.5 dB | -11.3 dB | -6.3 dB |
| plasterboard | -12.2 dB | -11.6 dB | -9.4 dB | -5.6 dB |
| brick | -9.7 dB | -9.2 dB | -8.0 dB | -5.1 dB |
| concrete | -8.1 dB | -7.8 dB | -7.0 dB | -4.9 dB |
| glass | -7.3 dB | -7.1 dB | -6.5 dB | -4.8 dB |
| marble | -6.9 dB | -6.7 dB | -6.2 dB | -4.7 dB |
| metal | -0.0 dB | -0.0 dB | -0.0 dB | -0.0 dB |

Excluding metal, the entire vocabulary spans 8.4 dB at normal incidence and
**1.6 dB at 75 degrees**. Grazing incidence collapses the material axis, and a
street canyon is grazing on the facades. This is the same mechanism `ROUGHNESS.md`
found for the roughness prior, arriving on the dielectric side: the geometry that
makes a city square interesting is the geometry that makes its materials stop
mattering.

Metal is the exception and it is not a small one. Any posterior that puts even a
few percent on metal has a mean reflectance dominated by that tail, because metal
is 10 dB above everything else in the table. This is what makes the argmax a
mistake rather than an approximation.

## The argmax is the bug, and it costs more than the evidence does

The reflectance of a patch whose material is uncertain is not the reflectance of
its most probable material. Mixing has to happen in power. Evaluating the fixed
`Building` prior both ways at 15 GHz:

| incidence | argmax, which is brick | posterior mean | gap |
|---|---|---|---|
| 0 deg | 0.1078 | 0.1531 | **+1.53 dB** |
| 45 deg | 0.1194 | 0.1631 | +1.35 dB |
| 60 deg | 0.1585 | 0.1971 | +0.95 dB |
| 75 deg | 0.3071 | 0.3309 | +0.32 dB |

The 3 percent of prior mass on metal supplies 20 percent of the mean reflected
power. The argmax throws that away, and the amount it throws away is larger than
anything the evidence ladder in `REPORT.md` ever moved: going from no image
evidence to a tenth of the scene bound by it moved the rooftop median by 0.29 dB.

This costs nothing to fix and needs no model. `material_posterior.bind_posterior`
draws one material per face from the posterior, which keeps every facet a real
material, because a square metre of wall is one material and not a blend. Two
things follow. The ensemble reproduces the posterior mean rather than its mode.
And repeating the draw with another seed produces an error bar on the exposure
distribution due to material ignorance, which the current pipeline cannot produce
at all.

## The layered stack, built and measured

The proposal was a layered rugged material model answered analytically.
`layered_power_reflectance` is that: an impedance transfer down an arbitrary
stack over a half space, both polarisations, averaged in power, agreeing with the
tracer's own single interface Fresnel in the limit of no coating. At 15 GHz free
space is 20 mm and the half wave period inside a render coat is 6.0 mm, so a real
coating sits squarely in the interference regime. A 15 mm render coat on brick is
4.74 dB below bare brick at normal incidence and a 12 mm coat is 0.59 dB below
it. **A three millimetre change in a thickness nobody can see swings the answer by
four decibels.**

That is the argument against using the stack naively, and it is also the reason
the stack is safe once it is treated honestly. Render coats vary across a wall by
more than 6 mm, so the interference self averages. Averaging over a plausible 8
to 25 mm coat:

| stack | thickness averaged | its outer material alone | its substrate alone |
|---|---|---|---|
| render on brick | 0.0629 | 0.0608, **+0.15 dB** | 0.1078, -2.34 dB |
| render on concrete | 0.0699 | 0.0608, +0.61 dB | 0.1547, -3.45 dB |
| stone on brick, 20 to 60 mm | 0.2135 | 0.2057, +0.16 dB | 0.1078, +2.97 dB |
| timber on brick, 15 to 30 mm | 0.0394 | 0.0293, +1.29 dB | 0.1078, -4.37 dB |

**An opaque coating thicker than a couple of millimetres collapses onto itself.**
The stack is worth nothing over naming the outer finish. So the layered branch of
the proposal, for opaque facades, is a null result: it was worth building because
it settles the question, and it should not be carried into the pipeline.

There is one exception and it is a common one. A window is not a half space. A
single glass pane in air, averaged over a 4 to 8 mm pane, is 0.28 against a glass
half space's 0.185, and a double glazing unit averaged over a 4 to 8 mm pane and a
12 to 20 mm cavity is 0.38, with a tenth to ninetieth percentile of 0.01 to 0.77
across those thicknesses:

| geometry | 0 deg | 45 deg | 60 deg | 75 deg |
|---|---|---|---|---|
| glass half space | 0.185 | 0.194 | 0.222 | 0.335 |
| single pane, 4 to 8 mm | 0.280 | 0.289 | 0.300 | 0.397 |
| double glazing unit | 0.384 | 0.330 | 0.335 | 0.457 |

**Treating a window as a glass half space understates its reflectance by 1.8 to
3.2 dB**, and the honest version of the number carries a spread of nearly two
orders of magnitude because it depends on a pane and a cavity thickness that no
image resolves. This is the one place in the material model where a stack is a
different object from a label, and it is exactly where a vision model has
something to say that a class vocabulary does not: it can tell single glazing
from a curtain wall from a shopfront.

## What the model actually saw

The model reads the square. Its notes are specific and architecturally correct:
"Flemish gable in red fired brick with pale natural stone bands", "post-war
department store with deep vertical precast concrete fins and recessed panel
infill", "off-white painted render on a classic townhouse with tall windows, iron
balconies and a restaurant sign". Nothing in these is generic.

Area weighted compositions over the nineteen crops, against the fixed prior:

| material | fixed `Building` prior | VLM, street capture | VLM, tile texture |
|---|---|---|---|
| brick | 0.300 | 0.294 | 0.170 |
| concrete | 0.150 | **0.324** | 0.171 |
| plasterboard | 0.200 | **0.017** | 0.040 |
| marble | 0.120 | 0.083 | 0.049 |
| glass | 0.120 | 0.102 | 0.094 |
| metal | 0.030 | 0.040 | 0.044 |
| wood | 0.030 | 0.018 | 0.027 |
| ceramic | 0 | 0.022 | 0.022 |
| unknown | 0.050 | 0.100 | **0.383** |

Total variation between the street capture composition and the fixed prior is
0.257, so this is a real disagreement and not a rounding of the same answer. The
model says Korenmarkt is brick and concrete where the prior says brick and
render, which matches the square: a Flemish brick gable frontage on two sides and
a post-war concrete department store on another.

The dielectric consequence, referenced to what the pipeline traces today:

| composition | 0 deg | 45 deg | 60 deg | 75 deg |
|---|---|---|---|---|
| fixed prior, posterior mean | +1.53 dB | +1.35 dB | +0.95 dB | +0.32 dB |
| VLM street capture, posterior mean | +2.28 dB | +2.06 dB | +1.50 dB | +0.56 dB |
| VLM tile texture, posterior mean | +2.69 dB | +2.44 dB | +1.82 dB | +0.73 dB |

So against the brick the pipeline actually uses, the model's composition is worth
+2.28 dB per bounce at normal incidence and +0.56 dB at 75 degrees, of which
+1.53 dB and +0.32 dB respectively is the argmax fix that needs no model at all.
**The model's own marginal contribution over simply stopping the argmax is
0.75 dB at normal incidence and 0.24 dB at 75 degrees, per bounce.**

## The question is worth more than the answer

The model was asked for both a material posterior and a layered stack, and the
two do not agree. On 13 of 38 street capture responses the outermost layer it
names is not the top of its own material posterior, and the disagreement is
always the same shape: the posterior names the substrate, the stack names the
coating. "Off-white painted render on a classic townhouse" comes back with
`plasterboard` as the outer layer and `brick` as the top posterior mass, because
a rendered Ghent townhouse is a brick building wearing render.

Both answers are correct English. Only one of them is the quantity a reflection
coefficient needs, and it is the coating, because the stack calculation above
says an opaque coat thicker than 2 mm hides its substrate. Reading the same
responses through their outer layer instead of their posterior:

| reading of the same 38 responses | composition shift vs brick, 0 deg | at 75 deg |
|---|---|---|
| material posterior | +2.28 dB | +0.56 dB |
| outermost named layer | +0.75 dB | +0.06 dB |

**Asking the question two defensible ways moves the answer by 1.53 dB, which is
twice the model's own marginal contribution over the argmax fix.** That is the
central negative result of this study. The material axis at 15 GHz is not limited
by the model's ability to see. It is limited by the fact that "what is this
facade made of" is not a well posed question, and the twin has no mechanism that
forces it to be.

A second instance of the same problem is cheaper to see. Every one of the twelve
responses that reported a course pitch at all gave exactly 70 mm, because the
prompt told it that Belgian brickwork is "typically 60 to 80 mm" and 70 is the
midpoint of that hint. `MASONRY.md` established from Belgian format standards that the pitch is
60 mm on Waalformaat and module M50 and reaches 75 mm only on M65. The field
carries no information, it carries the prompt back. It is excluded from
everything downstream. Seven of the twelve coating thicknesses came back as
exactly 15 mm, with the rest at 1, 2, 2, 12 and 40 mm, which is the same failure
in a field the prompt did not anchor, so it is a default rather than an echo and
it is equally uninformative. The saving grace is the previous section: the
thickness does not matter once averaged.

## Calibration, with no ground truth

Measurement is ruled out for this study, so there is no truth to calibrate
against. What can be measured is whether the model agrees with itself on
independent looks at the same wall, and whether the confidence it states tracks
that agreement. Agreement is necessary for correctness and not sufficient, and a
model that is wrong the same way twice scores perfectly here. What it does catch,
and a single pass cannot, is a model that is sharp and unstable.

| comparison | pairs | top-1 agreement | mean total variation |
|---|---|---|---|
| street capture, repeat draw on the identical crop | 19 | 0.737 | 0.129 |
| street capture, two views of one patch | 47 | 0.809 | 0.164 |
| tile texture, repeat draw | 19 | 0.842 | 0.153 |
| tile texture, two views of one patch | 47 | 0.851 | 0.150 |
| **street capture against tile texture, same crop, same draw** | **38** | **0.158** | **0.459** |

The model changes its top material on a quarter of identical repeats. It changes
it *less* across two different views of the same wall than across two draws on
one image, which says the residual disagreement is decoding noise rather than
viewpoint sensitivity.

The reliability curve is the useful part. Every bin sits **above** the diagonal:

| stated confidence | responses | realised cross view agreement | gap |
|---|---|---|---|
| 0.00 to 0.25 | 2 | 1.00 | -0.83 |
| 0.25 to 0.50 | 6 | 0.44 | -0.01 |
| 0.50 to 0.75 | 23 | 0.71 | -0.10 |
| 0.75 to 1.00 | 7 | 1.00 | -0.19 |

Count weighted mean absolute gap 0.138. **The model is under confident, not over
confident**, which is the failure mode one wants: a confident wrong material is
worse than a broad prior, and that is not what is happening. Every response
stating 0.75 or above agreed with every other look at the same wall, and every
one of those was a `coursed_masonry` brick call. Confidence above 0.75 and a
periodic relief pattern together are a usable gate, and the response set contains
no counterexample.

The caveat has to travel with the number. Nineteen crops on one square is a small
sample, one model was used throughout, and self consistency cannot detect a
shared bias. Nothing here says the model is right about Korenmarkt. It says the
model is not overconfident about Korenmarkt.

## The Google tiles, which the model refuses to read

This was the cheapest idea in the brief and it has the sharpest answer.

The model marked the street capture legible on 95 percent of crops and the tile
texture legible on **24 percent**. It put its top posterior mass on `unknown` for
33 of 38 texture crops against 3 of 38 street crops. Its mean stated confidence
was 0.60 on the street capture and **0.16** on the texture. Top-1 agreement
between the two sources on the same wall from the same viewpoint is 0.158.

This is not the model being lazy. Panel (a) of `outputs/material_vlm/material_vlm.png`
shows a pair: the street capture resolves the vertical precast fins and the shop
fascia of the Ghent HEMA building, and the texture of the same wall from the same
viewpoint is a smeared purple wash. Each crop is 384 pixels across 22.5 degrees,
so the street capture samples a facade at 26 mm per pixel at 20 m range, against
a measured median texture ground sample distance of 0.19 m on the same crops.
That is a factor of seven. A 60 mm Belgian brick course is a little over two
pixels in the street capture at 20 m and a third of a pixel in the texture, which
is why the model reports a periodic relief pattern on 66 percent of street
captures and on 21 percent of textures.

The result also reproduces, from a completely different method, what
`semantic_twin/texture_evidence.py` already found with a hand built descriptor and
a spatially blocked protocol: 0.382 accuracy against panorama derived labels
against a 0.366 majority baseline, with every opaque class collapsing into one and
only vegetation separating. A learned descriptor and a vision language model
independently reach the same conclusion, which is that **the Google 3D Tiles
texture carries essentially no facade material information**, and the limit is
viewpoint and illumination rather than sampling. The tiles see facades obliquely
from above and mostly in shadow.

One thing is worth noting in the model's favour. Handed an unreadable image it
said so, put its mass on `unknown`, and dropped its stated confidence by 0.44.
That is the behaviour a calibration harness exists to check for, and it passed.

## Through the tracer

Everything above is per bounce. The tracer reports a mean bounce count near one on
this walk, so a per bounce decibel is an upper bound on what reaches the exposure
distribution. What follows is the same walk, the same locations, the same ray
seeds, the same body and the same carrier, with only the facade material model
changing. Because the seeds are shared, the per location ratio is a paired
comparison whose Monte Carlo error largely cancels, and the paired median is the
number to read rather than the difference of the two medians.

Twenty four standpoints on the Korenmarkt walk, 60 thousand rays each, 12 bounces
with roulette from 3, 15 GHz, the same body. Every facade in the scene, 40.9
percent of surface area, is rebound per variant. The pure variants put a single
material on every facade and are not proposals, they are the bracket. Seed `m0`
and `m1` differ only in the per face draw from the posterior, so the distance
between them is the material ignorance error bar.

| facade material model | chi iso | paired iso | p10 to p90 | paired roof | paired street | >1 dB |
|---|---|---|---|---|---|---|
| brick everywhere, what the pipeline traces today | 0.28928 | | | | | |
| control, brick through the posterior path, `m0` | 0.28928 | **+0.000 dB** | +0.00 to +0.00 | +0.000 dB | +0.000 dB | 0 of 24 |
| control, brick through the posterior path, `m1` | 0.28928 | **+0.000 dB** | +0.00 to +0.00 | +0.000 dB | +0.000 dB | 0 of 24 |
| fixed prior, drawn instead of argmaxed, `m0` | 0.29627 | +0.106 dB | +0.06 to +0.20 | +0.212 dB | +0.160 dB | 0 of 24 |
| fixed prior, drawn instead of argmaxed, `m1` | 0.29513 | +0.099 dB | +0.07 to +0.18 | +0.214 dB | +0.125 dB | 0 of 24 |
| VLM street capture composition, `m0` | 0.30196 | +0.192 dB | +0.13 to +0.28 | +0.407 dB | +0.308 dB | 0 of 24 |
| VLM street capture composition, `m1` | 0.30345 | +0.162 dB | +0.12 to +0.34 | +0.350 dB | +0.266 dB | 0 of 24 |
| VLM tile texture composition, `m0` | 0.30407 | +0.217 dB | +0.14 to +0.37 | +0.415 dB | +0.319 dB | 0 of 24 |
| VLM tile texture composition, `m1` | 0.30337 | +0.223 dB | +0.15 to +0.34 | +0.430 dB | +0.343 dB | 0 of 24 |
| bracket, every facade render | 0.28295 | **-0.104 dB** | -0.16 to -0.07 | -0.164 dB | -0.136 dB | 0 of 24 |
| bracket, every facade stone | 0.30552 | **+0.239 dB** | +0.16 to +0.34 | +0.414 dB | +0.322 dB | 0 of 24 |
| bracket, every facade metal | 0.51419 | **+2.502 dB** | +1.68 to +3.93 | +4.374 dB | +3.808 dB | **24 of 24** |

Five things fall out of that table.

**The control is exact.** Sending a point mass posterior through
`material_posterior.py` reproduces the geometric brick binding to five decimal
places at every standpoint, on both seeds. The noise floor of this experiment is
zero, so every other row is signal.

**The bracket is 0.34 dB.** Put the softest dielectric in the vocabulary on every
facade in the square and chi falls by 0.104 dB. Put the hardest on every facade
and it rises by 0.239 dB. **The entire dielectric material axis, at its two
extremes, spans 0.34 dB isotropic and 0.58 dB rooftop.** No possible improvement
to facade material evidence can move chi further than that, and the corresponding
spread of chi across the 24 standpoints is 3.3 dB isotropic, 8.7 dB rooftop and
13.0 dB street small cell. The material axis is an order of magnitude below the
geometry it sits inside.

**Metal is the only exception, and it is a family, not a member.** Every facade
metal is +2.50 dB isotropic, +4.37 dB rooftop, +3.81 dB street, and it is the
only variant in the study that moves a single standpoint by more than a decibel.
It moves all 24. It is also the only variant that changes the mean bounce count,
0.98 to 1.11. So the material axis has exactly one decision in it that matters,
and it is dielectric against conductor. Everything below that is noise. This is
the honest form of the claim: image evidence establishes which family of surfaces
a square is made of, and inside the dielectric family it does not tune anything
worth tuning.

**The argmax fix is real and it is small.** Drawing from the fixed prior instead
of taking its argmax is +0.10 dB isotropic and +0.21 dB rooftop, reproducibly on
both seeds. That is four to nine times the 0.024 and 0.029 dB that
`SAM3_LADDER.md` measures for material discrimination across 28.5 percent of
facade area on 120 standpoints, so it is the largest single term anyone has found
on this axis. It is also 30 percent of the dielectric bracket, which is the right
way to see how little room the axis has.

**The two VLM compositions are indistinguishable from each other and from stone.**
The street capture reads Korenmarkt as brick and concrete. The tile texture reads
it as 38 percent unknown. Their compositions differ by a total variation of 0.30.
They trace to +0.192 and +0.217 dB isotropic, a difference of 0.025 dB, which is
inside the 0.030 dB seed to seed spread of a single variant. **A vision model that
can see the wall and a vision model that admits it cannot produce the same
exposure distribution.** Both land next to the every facade stone bracket, and
they land there for the same reason the fixed prior does: what carries a
posterior mean is the small mass on metal and marble, not the identity of the
dominant material.

That last point is the sharpest negative result in the study. If the answer does
not depend on whether the model could see the building, the model is not what is
producing the answer.

One caveat on sample size. This is 24 standpoints, not the 120 the published
ladder and `SAM3_LADDER.md` use, because the machine was carrying six other
tracing jobs. The paired design makes each row far tighter than the count
suggests, since the control returns exactly zero and the pure variants are
seed independent to five decimals, but the p10 to p90 columns are the honest
uncertainty and none of the conclusions above rest on differences smaller than
those ranges.

## The same answer, arrived at from the other side

`SAM3_LADDER.md` was produced concurrently and independently, on the material
axis of the same square, with a different detector, a different binding path, a
different variant set and 120 standpoints rather than 24. It is worth reading
against this document because the two agree in a way that neither could have
arranged.

It ran SAM 3 on all eight walk stations and reassigned **28.5 percent of the
facade area** the entity prior had called brick: 11.9 percent to glass,
9.5 percent to plasterboard, 4.8 percent to marble, taking `semantic_glass` from
1 triangle to 958. That is a far larger and better evidenced material
intervention than nineteen crops can support. The exposure distribution moved by
**0.024 dB isotropic and 0.029 dB rooftop, with 0 of 120 standpoints moving as
much as half a decibel.**

Three points of contact.

The reflectance table is the same. That run quotes brick -9.67 dB, plasterboard
-12.16 dB, glass -7.32 dB and marble -6.87 dB at normal incidence at 15 GHz,
reproducing the table in this document to the second decimal from an independent
code path. The per bounce budget both studies work against is therefore not in
dispute.

The composition disagrees, and the disagreement is informative. SAM 3 splits
building pixels 59.8 percent brick, 23.0 percent glass, 14.4 percent
plasterboard, 1.8 percent marble. The vision model gives brick 0.294, concrete
0.324, glass 0.102, plasterboard 0.017. Both agree the fixed prior is wrong.
They do not agree on how. SAM 3 finds far more glass, which is plausible because
it segments at pixel resolution and windows are a large fraction of a facade's
pixels, while the vision model was asked what the wall is and answered about the
masonry rather than the glazing in it. Which of the two is the right question
depends on whether the glazing is being carried by the material label or by
geometry, and that is a real modelling question that neither study settles. It
is a second instance of the phrasing sensitivity this document measures at
1.53 dB.

The traced verdicts converge, and the bracket explains why they had to. A
28.5 percent area reassignment across materials spanning 5 dB produced 0.024 dB
there. Here, reassigning **100 percent** of facade area to the softest or hardest
dielectric in the vocabulary produces -0.104 and +0.239 dB. So that 0.024 dB was
not a small effect inside a large budget, it was a small effect inside a budget
of 0.34 dB. Two studies, two detectors, two evidence types and two ablation
designs land on the same conclusion for the same structural reason: **at 15 GHz
in a masonry square, the dielectric material axis has 0.34 dB in it, and every
method spends its evidence inside that.**

Two places where they differ are worth stating.

`SAM3_LADDER.md` measures argmax against argmax throughout, so it never sees the
0.10 dB isotropic and 0.21 dB rooftop that the argmax itself costs. That is the
largest term either study found on this axis and it is invisible to any
experiment comparing two point estimates.

This study traced the bracket and that one did not, so this is where the ceiling
comes from. The complementary observation is that `SAM3_LADDER.md`'s full field
variant, which it correctly labels a degradation rather than a result, moves
-0.218 dB by putting brick where the entity axis had metal. That is the same
metal term reappearing from the other direction, and it is consistent with the
+2.50 dB this study measures for metal on every facade. Both studies find that
the only material decision with real leverage is whether a surface conducts.

## Verdict

**Does a vision model give materially different and better grounded facade
materials than the fixed prior?** Different, yes, and measurably so: total
variation 0.257 against the fixed prior, with concrete doubled and render nearly
eliminated in a way that matches what the square looks like. Better grounded,
partly: it is grounded in evidence about this square rather than in a hand
written table that is identical for Ghent, Tokyo and Mexico City, and it is
honestly under confident. But grounded is not the same as verified, and there is
no verification here and will not be.

**By how many decibels does it move chi?** **+0.19 dB isotropic and +0.38 dB
rooftop**, averaged over two draws, with 0 of 24 standpoints moving as much as a
decibel. Of that, +0.10 and +0.21 dB is the argmax fix, which needs no model. The
model's own marginal contribution is **+0.08 dB isotropic and +0.17 dB rooftop**,
and a model that could not see the wall at all produced +0.22 and +0.42 dB, which
is the same answer or slightly larger.

The ceiling around those numbers is what makes them interpretable. Putting a
single dielectric on every facade in the square spans -0.104 to +0.239 dB
isotropic. **No facade material evidence of any kind, from any source, can move
chi more than 0.34 dB in this square**, against a 3.3 dB spread across
standpoints and the 1.98 dB that entity coverage alone moves the worst
standpoint. The one escape is metal at +2.50 dB, and metal is a family call that
neither the fixed prior nor the vision model gets wrong here.

**Does it earn its place?** Not on the material axis, not as proposed. The
ordering is unambiguous. Fix the argmax first, because it is free, needs no model
and is worth more than the model is. Then note that the substrate versus coating
ambiguity in the question is worth 1.53 dB per bounce, more than the model's
remaining contribution, so a model cannot be trusted to move the number until
that is closed by the prompt rather than by the analyst. Then note that the whole
axis is bracketed at 0.34 dB. What is left for the model to win is under a tenth
of a decibel, on a quantity whose geometry term is 3.3 dB of spread, and it did
not win even that reliably, because the illegible source produced the same shift.

Two narrower things do earn a place and should be taken.

**Glazing.** A window is not a glass half space and the error is 1.8 to 3.2 dB in
the direction of under predicting reflection. The vocabulary cannot express the
difference between a shopfront, a single pane and a curtain wall, a vision model
can, and `layered_power_reflectance` can now consume the answer. This is the one
place where the model, the stack and the physics all point the same way.

**Posteriors, not labels.** Whatever supplies the material must supply a
distribution and the tracer must draw from it rather than collapse it. That is
free, it removes a 1.53 dB per bounce bias worth +0.10 dB isotropic and +0.21 dB
rooftop on chi, and it is the only route to an error bar on chi from material
ignorance rather than a point estimate with no stated uncertainty.
`material_posterior.py` implements it and its control row is exact.

## What would change this verdict

- **A square with conducting facades.** This is the one that would actually
  overturn the verdict rather than nudge it. Every facade metal is +2.50 dB
  isotropic and moves all 24 standpoints past a decibel, so a curtain wall or
  metal clad square has a material axis an order of magnitude larger than
  Korenmarkt's and the fixed prior, which puts 3 percent on metal, would be badly
  wrong there. The vision model's job in such a square is not to choose between
  brick and render, it is to notice the building is a mirror. That is a
  discrimination it should be very good at and it is the only one worth paying
  for. Of the eleven cities in the cross city table, the ones to try are the
  post-war commercial squares rather than the historic centres.
- **A frequency where the vocabulary is not compressed.** At 15 GHz and grazing
  incidence every dielectric facade is within 1.6 dB of every other. The material
  axis is worth four times more at normal incidence, which is the geometry of a
  rooftop illuminator onto an upper storey rather than a street canyon. The
  cross city runs at 250 m under the corrected illumination law would be the
  place to check whether any site is normal incidence dominated.
- **Closing the substrate versus coating ambiguity in the prompt.** Ask only for
  the outermost layer, in one field, with the substrate explicitly out of scope.
  This is a two line change and it removes the largest single term in the budget.
  It was not made here because changing the prompt after seeing the answers would
  invalidate the calibration measurement.
- **A glazing-specific pass.** Prompt for pane count, pane thickness and cavity,
  bind through `layered_power_reflectance`, and check what the 10 percent of
  scene area that is glass does to chi when it stops being a half space.
- **More than one square, and more than one model.** Nineteen crops of one city
  cannot separate a model that reads facades from a model that has a prior about
  European squares. Two models disagreeing on the same crops would separate
  decoding noise from shared bias, which self consistency cannot.
- **Any ground truth at all.** One afternoon with a notebook recording the
  outermost finish of the eight Korenmarkt walls in this crop set would turn
  every agreement number in this document into an accuracy number. It is not a
  radio measurement and it is not ruled out by the decision that ruled out
  radio measurements.

## Files

| path | what |
|---|---|
| `semantic_twin/facade_vlm.py` | prompt, schema, transfer matrix, posterior arithmetic, calibration |
| `semantic_twin/propagation/material_posterior.py` | per face draw from a posterior, second binding backend |
| `build_facade_crops.py` | matched panorama and tile texture crops with their mesh faces |
| `blind_facade_crops.py`, `make_vlm_batches.py` | blinding and call planning |
| `analyse_material_vlm.py` | composition, agreement, calibration, reflectance |
| `run_material_ablation.py` | the traced comparison |
| `plot_material_vlm.py` | the six panel figure |
| `tests/test_facade_vlm.py` | 21 tests |
| `outputs/material_vlm/crops/`, `blind/` | 19 crop pairs, blinded copies |
| `outputs/material_vlm/raw/*.jsonl` | 76 raw responses, 12 independent calls |
| `outputs/material_vlm/analysis.json` | every number quoted above |
| `outputs/material_vlm/ablation.json` | the traced table |
| `outputs/material_vlm/material_vlm.png`, `.pdf` | the figure, panel f is the answer |

## Provenance and limits

The model was Claude Opus, one model for all 76 calls, shown one image per
question with the prompt at digest `963203661b633b51`, two independent draws per
image from calls that could not see each other's answers. No Anthropic API key is
present on this machine, so the calls were made through the agent harness rather
than the Messages API. `facade_vlm.anthropic_request_body` builds the equivalent
API call and the response records are transport independent, so the study is
reproducible against the API without changing anything downstream.

The response transport truncated the wrapper's closing brace on 32 of 76 lines.
The repair only ever appends closing braces and never edits content, and the
count is carried in `analysis.json`.

No facade material in this study has been measured. Every accuracy-shaped number
here is an agreement number and is labelled as one.

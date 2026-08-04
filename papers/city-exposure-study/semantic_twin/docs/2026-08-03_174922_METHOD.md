# The method

What this study computes, and why each piece is the way it is. This is the
current statement and it replaces the scattered working notes. Where something is
not yet decided it says so, in place, rather than leaving a reader to find out by
running the code.

Written 2026-08-03. The older writeup, `METHOD.tex`, describes the method before
the illumination law changed and is in `archive/`.

---

## 1. The one idea

**Everything comes from one photograph taken at the point where you want the
answer.**

Stand somewhere. Take a 360 degree photograph. That single picture carries three
different things:

- the **geometry**, through photogrammetry,
- the **materials**, through what the pixels show the walls to be,
- the **sources**, because the rooflines in the picture are where base stations
  can sit.

Everything below is a consequence of arranging the computation so that one
photograph is enough.

## 2. What is computed

Power density arriving at a pedestrian's head. Not an absolute level in watts per
square metre, because that level is not knowable: it depends on how many base
stations an operator built, how much power they radiate and where they are, none
of which is public and none of which is a property of the city.

So the reported quantity is geometric, and the unknown network appears only as a
multiplier that is the same everywhere. Section 6 says exactly what gets
reported.

The frequency is 15 GHz. The head is 1.5 m above the ground.

## 3. Computing at the person, not at the transmitter

A normal ray tracer starts at a base station and traces to a receiver. One trace
per pair. If you want to know what a hundred different deployments would do, you
trace a hundred times.

This one starts at the head. Rays leave the pedestrian, bounce off the buildings,
and the estimator asks at each step where the power could have come from. By
reciprocity a path traced outward is the same path the power took inward.

The obvious gain is speed: one trace covers every source position at once.

**The gain that matters is different.** If the computation sits at the
pedestrian, then the transmitter and the receiver are at the same point, and a
photograph taken from that point sees the surfaces the early bounces hit. The
materials stop being assumed and start being observed. That is the whole reason
for the arrangement.

### How well that holds, measured

For a path that leaves and returns to the same point, both ends are visible from
that point by construction, so both ends are in the photograph. Traced at 42
standpoints across four cities:

| chain fully on photographed surfaces | 1 bounce | 2 bounces | 3 bounces |
| --- | --- | --- | --- |
| closed loop | 1.000000 | 0.999972 | 0.980 |
| one way path | 0.999103 | 0.912004 | 0.714182 |

The closed loop is the guarantee. The one way path is what the estimator actually
traces, and it holds only 0.912 at the second bounce and 0.714 at the third. **So
the arrangement costs about half the guarantee, and that is stated rather than
absorbed.**

## 4. Where the base stations are

This is the part that changed most recently and it is the largest simplification
in the study.

### What it used to be

The network was described by four numbers: base stations somewhere between 13.5
and 43.5 m above the head, at 25 to 250 m horizontal range, spread evenly in
every compass direction. From those, an elevation density was derived
analytically.

Three things were wrong with it. It was not measurable, since no deployment above
6 GHz exists anywhere to calibrate against. It was not stable, because the number
of sites at range `d` grows as `d` while the power falls as `1/d^2`, so the
integrand goes as `1/d`, which is logarithmic, so **the 250 m cap set the answer
and was worth 7.8 dB**. And it described a cloud floating in the air that no
photograph could ever check.

### What it is now

**Base stations sit on facade tips**, meaning the top edge where a wall meets the
sky. That edge is exactly the silhouette a pedestrian photographs. There is no
mast: the site is on the tip itself.

Two consequences follow immediately.

**The range cap disappears.** Along any compass direction there is one visible
facade tip, at one distance. There is no distribution over range to integrate and
therefore nothing to cap. The logarithm that made 250 m matter is gone because
there is no longer an integral over range at all.

**The height band disappears.** The elevation of the tip is read off the mesh.

The intuition, for one direction with the roofline square on to your line of
sight, is

    direct flux per unit azimuth  proportional to  cos^2(alpha) / d

with `alpha` the elevation of the tip and `d` its horizontal distance. It comes
from three factors: an azimuth slice `dphi` covers arc `d dphi` of the tip, each
site is at slant range `d / cos(alpha)`, and flux falls as the inverse square of
slant range.

**That formula is the explanation, not the calculation.** It assumes one visible
tip per direction and a roofline square on to the view, and neither holds. A near
low roof edge and a taller one behind it are both visible and both carry sites. A
facade seen at a slant carries more roofline per degree of azimuth, by one over
the cosine of the obliquity. Measured at Korenmarkt, the formula and the exact
answer differ by up to nine times across standpoints, and the ratio between them
is not constant, so no normalisation absorbs it. The number comes from the exact
sum in section 5. The formula belongs in the paper because it is the right thing
to put in a reader's head.

### Why a curved skyline beats a statistical cloud

The old law had to assume how far away the sites were. The new one measures it,
per direction, and the geometry cuts the distance off by itself: in a canyon you
see 50 m of city, in an open plaza 500 m. That is the physically correct answer
and it costs nothing to obtain.

One result worth keeping in mind, because it is not obvious. Standing directly
under a facade tip is a **bad** place to receive from it, because of the
`cos^2(alpha)`. An alley with 30 m walls 3 m apart gives 0.0018 by the formula
above, while a plaza with 20 m buildings 100 m away gives 0.0096, five times
more. The same factor suppresses tall towers automatically: a 200 m tower at
100 m contributes five times less than an ordinary 20 m building at the same
distance, so there is no need for a rule that excludes them.

## 5. How the sources are sampled

### The problem

The sites lie on a curve. A curve has no area on the sky. So an estimator that
traces a ray outward and asks "was there a site in the direction this ray left"
gets the answer no, every time, and returns zero.

Making the sky into cells and asking "how much roofline runs through this cell"
patches the symptom. It does not fix the real fault, and no cell size does. **A
density that is a function of direction alone assumes the sources are far enough
away that only direction matters.** The skyline sits 18 to 70 m from the head at
these sites, while a bounce can happen tens of metres away, so which tips are
visible genuinely differs between the head and the wall the ray bounced off.

### The fix

Stop waiting for a ray to find a site. **Connect to one.**

At every point along a traced path, including the head itself:

1. pick a point on the roofline,
2. cast one ray towards it,
3. if nothing is in the way, add its contribution.

This is next event estimation, standard in rendering, and it fixes both faults at
once. The visibility question is answered from the point where it is asked, so
the position dependence is exact. And the same call at the start of a path is the
direct term, so the line of sight part and the bounced part are one estimator
rather than two.

Step 1 is where the honesty has to go, because "pick a point" hides a choice.
The point is drawn from the source set, and the draw has to be divided out again
by the chance of drawing it, which is what makes the estimator unbiased however
the draw is made. So the distribution changes only the noise, not the answer.
What it does not remove is **which surfaces are in the set at all**. That is a
modelling question, it is settled in section 5.1, and it is not settled by next
event estimation. The earlier claim here that this construction has no parameter
was too strong: it removes the sky cell, not the definition of the roofline.

Cost is one extra ray per path vertex. A standpoint launches 200,000 rays and
they average 0.95 bounces, so about 390,000 intersection calls, and connecting at
each vertex adds roughly 190,000. That is **49 percent more work, not double**.

**Why not trace from the rooftops instead**, which is the obvious alternative:
there are many sources and only one receiver, so tracing from the sources is far
more expensive. Next event estimation gets the accuracy of source side sampling
at the cost of receiver side tracing. You never trace from a roof. You only ask
whether you can see one, which is a single ray.

The general version of this, where paths are traced from both ends and joined in
the middle, is bidirectional path tracing. It earns its extra complexity when the
source is hard to reach from the receiver, which is not the case here: the source
*is* the skyline, and the skyline is by definition the boundary of what you can
see. If standpoints under arcades turn out to be badly estimated, that is when to
revisit it.

Neither version handles a purely mirror like bounce, because connecting to a
source has no chance of being a valid mirror path. That is what image sources are
for. The specular share on rough masonry at 15 GHz is small enough that this is a
correction rather than the main path.

### 5.1 Which surfaces are in the set

Next event estimation needs a set to draw from. Three ways of building one were
measured, and two are ruled out.

**A band of given thickness fails.** The idea was to let a site sit in the top few
metres of a facade rather than on a line of zero width, because a zero thickness
edge cannot be pulled reliably off a photogrammetric mesh: the mesh is lumpy at
the half metre scale, and requiring that nothing sits higher within two metres
throws away genuine top edges wherever reconstruction noise put a bump beside
them. At Korenmarkt only 38 percent of the silhouette has an extracted tip within
2 m, and going from 800,000 to 4,000,000 samples moved that from 33 to 38, so it
saturates and is structural.

The band repairs that and fails for a different reason. `measure_source_thickness.py`
sweeps it: the thickness is worth 3.6 to 6.1 dB and it **reorders the squares**.
A thickness has no limit. Shrink it and the answer does not settle on anything, so
no value of it is more right than another, and a number that changes the ranking
cannot be a numerical detail.

**Voting on surface samples fails too.** `measure_source_construction.py` counts
footprint cells rather than wall area, which is better, but it still carries four
thresholds, and its coverage of the visible skyline stops rising at about 0.57
however small the cells get. It is asking the mesh where its roof edges are, and
the mesh does not know.

**The silhouette itself works.** `measure_source_silhouette.py` never asks that
question. It sends a ray fan up from each standpoint of the walk, takes the
topmost hit in each azimuth, and takes the union along the walk. That set is by
definition the surface a pedestrian sees against sky, which is a fair description
of where an operator can put a site and have it serve the street. It is also the
same object the rest of the study runs on: the sky boundary of the panorama, put
back on the geometry. The standpoints that build the set and the standpoints the
answer is read at are kept disjoint, so nothing is scored against a set it wrote.

### 5.2 What the resolutions do

The set has no threshold in it. What it has instead are resolutions, and those
were swept at 250 m over Korenmarkt and Brussels with 48 held out standpoints.

- **Standpoints converge.** 64 to 128 to 256 builders moves the answer by 0.02 and
  0.29 dB at Korenmarkt, 0.00 and 0.09 at Brussels. Coverage of what a held out
  standpoint sees saturates at 0.99 and 0.88. **128 is enough.**
- **The cell does not converge in the range measured.** It drifts up 0.2 to 0.5 dB
  per halving from 4 m down to 0.5 m, at both squares, whether the cells are flat
  or solid. Refining keeps resolving skyline that a coarser cell had merged, which
  shows as the visible fraction climbing about 40 percent over that range.
- **The drift moves both squares together.** Korenmarkt stands 0.63 to 0.83 dB
  above Brussels on solid cells and 0.65 to 1.10 on flat ones, across a factor of
  eight in cell size. The comparison between cities is what gets reported, and it
  holds to about 0.2 dB.

So the cell is a weaker thing than a convergent resolution and a much stronger
thing than the band. It leaves a slow drift in each city's absolute number and
cancels in the difference between cities. That is stated rather than hidden.

Solid cells are the default. On flat cells a vertical wall occupies a line and
gains sites as `1/cell`, while a flat roof occupies a patch and gains as
`1/cell^2`, so shrinking a flat cell keeps shifting weight onto horizontal
surface and has no useful limit. Solid cells count both per unit of area. In
practice the occupied count grows about 2.15 times per halving at both squares,
not four, which says the cloud is a union of curves rather than a filled surface,
and the solid grid is measuring length along the roofline.

### 5.3 One reading that was wrong

At 8 held out standpoints Korenmarkt appeared not to converge in cell size while
Brussels did. Two explanations were built on that and both were checked and
failed.

The first was a pole standing near the pedestrian. A floor that drops tips found
close to the standpoint that found them changed the answer by 0.04 dB. It also
asked at the wrong end: the floor cuts by distance from the standpoint that built
the set, and the term is read somewhere else.

The second was the flat grid. Solid cells did appear to fix Brussels and not
Korenmarkt at 8 standpoints.

At 48 held out standpoints the difference is not there at all. Both squares drift
by the same 0.2 to 0.5 dB per halving. **It was noise in a median over 8 numbers.**
The argument for solid cells above stands on its own and does not rest on this.

One fact worth keeping from the failed hunt. Splitting the direct term by range
shows that **nothing within 10 m contributes at either square.** A standpoint
1.5 m up looking at a roofline 20 m up is at least 18 m from it whatever the
building does, so the range is set by building height, not by how close you
stand. Korenmarkt does carry 4 to 7 percent of its term between 5 and 10 m where
Brussels carries none, which is a low object near the pedestrian, and that is
real but small.

## 6. What is assumed about the network, and what is reported

### The assumption

**The number of antennas per square kilometre is the same in every city.**

The reason to like this is not that it is realistic. It is that **it is free.**
Write the flux as the antenna density times the transmit power times a purely
geometric sum. Both unknowns then sit as one multiplier in front of every city's
answer, identically, so any comparison between cities never sees them. No number
for either ever has to be stated or defended. Compare the old range cap, which did
not cancel and was worth 7.8 dB.

It has a useful side effect. Sites per metre of roofline is the density times area
over roofline length, and both area and roofline length are measured off the mesh.
A fine grained medieval core has far more roof edge per square kilometre than a
city of large blocks, so the assumption gives it fewer sites per metre of edge.
It counteracts the morphology difference rather than smuggling one in.

### What is reported

Two factors, not one number:

    answer  =  (line of sight term)  x  (1 + multipath / line of sight)

The first is what the geometry lets you see. The second is what reflections add on
top of it.

This split costs nothing, because the line of sight term has to be computed
anyway. It is worth having because the two halves have different evidence behind
them. **The first needs no photographs at all**, so it is available at every city
including the four with no panoramas, and it is the most robust result in the
study. **The second is where materials, roughness, clutter and foliage live**, so
it is the factor the photographs earn their place in.

### What is not done

**The line of sight term is not normalised away.** Scaling the source power so
that the line of sight always comes to one would say that operators radiate harder
where there is less sky, which no operator does, and it would delete the shadowing
result entirely. Normalisation is a way of splitting one number into two. It is
not a way of defining how much power a base station transmits.

### The denominator, which had to change

The study used to report a ratio: power at the head, divided by power from the
same network over open ground. That definition does not survive. **The sites now
live on the buildings, so removing the buildings removes the network.**

The replacement is to report the geometric quantity itself, per unit antenna
density and transmit power. It has units of one over metres, cities compare
directly, and anyone can multiply by their own density and power. A second
reference is reported alongside it: the same quantity computed as if every site on
the city's own roofline were visible, so the ratio reads as the share of its own
rooftops that a standpoint can see.

## 7. The bounce budget

**Three bounces.** The reason is evidence, not energy.

Going from three bounces to eight moves the answer by a median 0.002 dB and never
moves a standpoint by more than 0.12 dB. But that is not the argument, because a
convergence tolerance is a preference. The argument is that the share of power
which has touched material that was guessed rather than photographed rises by only
about a tenth of a percentage point between three bounces and eight. **Tracing
deeper does not buy evidence. It buys more guesses about less power.**

None of that depends on where the base stations are, so it survives the change of
illumination law untouched.

Next event estimation improves matters at the same budget. Under the old
estimator, a three bounce path contributed only if it happened to escape towards a
site. Now every point on the path reports separately, so the zero, one, two and
three bounce contributions come out explicitly and with far less noise.

Russian roulette is off. At this budget it would fire once at a 0.05 floor and
inflate survivors twentyfold. Measured: not slower with it off, and the worst
standpoint deviation halves.

## 8. The walk

Where the standpoints are.

### What it was, and why it was wrong

`build_walk` laid a 3 m grid over a 90 m disc, kept the walkable points, and ran a
nearest neighbour chain through them to give them an order. That is a blob of grid
points with a cosmetic ordering. There is no route and no relationship to any
street.

That design is what forced every caveat in the study. Panoramas sit on roads, so
the open middle of a square has none, so 6 to 12 panoramas had to cover 80
standpoints, so coverage over the walk was 0.479 against 0.999 at a panorama, so
the material result had to be reported with a 40 m reach attached.

### What it is now

**One standpoint per panorama, in traversal order along the street.**

Panoramas form a connected chain along roads because a vehicle or a walker
captured them in sequence. Traversing that chain is a walk, with no synthetic
routing needed, and it puts the transmitter, the receiver, the camera and the
pedestrian all at the same point, which is what section 3 requires.

The objection is that a square has only a handful of panoramas. That objection
holds only in a square. Along a street the spacing is 2.8 m where a trekker walked
and 10.5 m on a car track, so a kilometre of route gives about 100 standpoints,
every one of them exact. That is more than the 80 the disc gave, not fewer.

## 9. Everything else, in one line each

**Materials.** Facade materials come from segmenting the panorama. Where no
photograph reaches, a geometric rule assigns material from which way a wall faces.
The difference between those two is worth 0.16 to 0.50 dB within 20 m of a
panorama and under 0.01 dB past 40 to 60 m, which is why section 8 matters.

**Roughness.** A Rayleigh factor splits each reflection into a coherent specular
part and a diffuse part, against ITU-R P.2040-4. At 15 GHz on masonry the diffuse
part dominates.

**Foliage.** A canopy is a participating medium, not a surface and not explicit
leaves. Explicit leaves lose because the tracer has one surface response, a half
space reflectance, and a 0.2 mm leaf has an electrical thickness of 0.153 radians
at 15 GHz, so treating it as a half space over reflects it by 9.1 dB. A surface on
the canopy hull loses because a canopy has no interface: its effective boundary
reflectance is 1.9e-9 against 0.029 for the wood material row, which is 71.8 dB of
invented reflection.

**Clutter.** Segmentation classes decide what is scenery and what is structure, so
a passing person is not painted onto a wall. People are reconstructed as separate
bodies.

**Bystanders.** At 15 GHz a person is 29 wavelengths across and one skin depth is
2.1 mm, so a body is optically thick and is pure geometry with no diffraction path
worth writing down. A crowd is opaque near the horizon and transparent above about
10 degrees, and no density changes that. Measured blockage is 0.0 to 0.1 dB
isotropic, 0.1 to 1.1 dB rooftop, 0.1 to 1.4 dB street cell.

**Bystander exposure is not computed, and should not be with these rays.** The
rays are the pedestrian's own, so a ray striking a bystander is power that was
heading to the pedestrian and hit someone else. A bystander's own exposure needs a
trace from their own head, at which point they are simply another standpoint. The
question worth asking, and the one this setup can answer, is how much standing in
a crowd changes your own exposure.

**MIMO.** There is no channel matrix and there structurally cannot be one. The
estimator accumulates power and never amplitude, because the phase of an escaping
path turns at about 78,000 radians per radian of exit angle at 15 GHz over 250 m,
and more fundamentally because phase depends on where the transmitter actually is
and the whole point of section 3 is never to commit to that. Maximum ratio
transmission is therefore not implemented and does not need to be: it applies the
same array gain to every path, so the array factor cancels in a ratio exactly. The
element pattern does not cancel, and costs 0.62 dB median rooftop. The gain of
matched transmission over a narrow beam aimed geometrically at the pedestrian is
one over the direct power fraction, which is measured per standpoint already and
runs 1.09 to 2.25 dB rooftop across the eleven cities.

**Diffraction.** A separate bound, not part of the tracer. A dense sky mask at
each standpoint, every shadowed direction given a Fresnel-Kirchhoff parameter from
ITU-R P.526-16 and a knife edge loss integrated against the illumination. Every
assumption in it errs upward, so it is a bound. It has to be recomputed against
the new illumination law.

## 10. What the name should be

Not a coined one. The engine is **reciprocal shooting and bouncing**, and
"reciprocal" is preferred over "adjoint" because in electromagnetics and
optimisation "adjoint" usually means gradient computation and no gradients are
computed here.

The method as a whole is best described rather than branded:

> A reciprocal shooting and bouncing ray method in which the transmitter, the
> receiver and the camera occupy the same point, so a single street level
> panorama supplies the geometry, the facade materials and the source positions
> at once.

Next event estimation is a sampling choice and belongs in the methods section, not
in the name. It is standard in rendering and unknown in this field.

## 11. What is settled, what is open

Settled with Robin, 2026-08-03:

| | |
| --- | --- |
| Sites on facade tips | yes, no mast |
| Height band and range band | removed, all four numbers |
| Antenna density per square kilometre | assumed equal across cities, cancels |
| Line of sight normalisation | a reporting split, not a source definition |
| Open ground denominator | replaced, the network lives on the buildings |
| Sampling | next event estimation |
| Bounces | three |
| Walk | one standpoint per panorama, along the street |

Open:

- **How thick the source is.** Section 5. Needs the sensitivity measured first.
- **Whether the street small cell model survives.** A small cell at 4 to 8 m is
  not on a facade tip, so under the new law it needs its own source geometry and
  its own trace. The three illumination columns may become one source geometry
  plus a reference.
- **Every number produced under the old law.** `LAW_CHANGE.md` sorts which
  results depend on the shape of the illumination law and which do not. Coverage,
  the bounce budget, materials, foliage and roughness do not. Anything quoting a
  rooftop or street cell decibel does.

## 12. Provenance

Numbers in this document and where they come from.

| number | source |
| --- | --- |
| closed loop and one way coverage | `MONOSTATIC.md` section 5.1, 42 standpoints, four cities |
| 7.8 dB range cap sensitivity | `DEPLOYMENT_GEOMETRY.md` |
| bounce budget, 0.002 dB and the evidence increment | `BOUNCE_BUDGET.md` |
| material reach, 0.16 to 0.50 dB and the 40 to 60 m fall | `MATERIAL_REACH.md` |
| panorama spacing, 2.8 m and 10.5 m | `WALK.md`, `CITIES.md` |
| foliage, 9.1 dB and 71.8 dB | `FOLIAGE.md` |
| bystander blockage | `BYSTANDERS.md` |
| MIMO, 0.62 dB and the 1.09 to 2.25 dB range | `BEAMFORMING.md` sections 6.5 and 4.3 |
| diffraction bound | `WHY_NOT.md`, `outputs/diffraction_bound/` |
| skyline extraction and its 38 percent coverage | measured in session, `semantic_twin/propagation/skyline.py` |
| the closed form against the exact sum, nine times | measured in session at Korenmarkt |

**No number in this document describes the new illumination law's effect on
exposure, because the estimator is not finished.** An earlier provisional table
computed with the closed form gave a between city spread of 4.21 dB against a
within city median of 5.48 dB, with 8 of 11 cities individually exceeding the
between city spread. That used the approximation of section 4 and must not be
quoted.

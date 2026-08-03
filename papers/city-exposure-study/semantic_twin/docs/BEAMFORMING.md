# The antenna axis of the illumination model

What the base station's radiation pattern does to `chi`, which of the beamforming
policies a real network runs are visible to this observable at all, and which are
provably invisible.

Implemented in `semantic_twin/propagation/antenna.py`, pinned by
`tests/test_antenna.py`, driven by
`python -m semantic_twin.propagation.antenna`. Nothing in
`semantic_twin/propagation/directions.py` is touched, so the eleven published
city rows are unaffected by anything here.

Notation is the same as PAPER_METHODS.md. `u` leaves the observer `x`, elevation
is `alpha`, `Q(u)` is the illumination density normalised to one over the sphere,
`chi = integral K Q dOmega`.

---

## 1. The question, and the short answer

The illumination model of PAPER_METHODS.md section 4 describes a population of
base stations by *where they are* and by nothing else. Every site is an isotropic
radiator. The original plan for this study was three sectors of 8 by 8 elements
per site, beamforming at the pedestrian. This document is what happens when that
is built.

The short answer, before the derivation, because it decides how the rest reads.

**A beam pointed at the pedestrian is invisible to `chi`, exactly.** Not
approximately, not to within Monte Carlo error. The traced columns are bit
identical. So the literal configuration in the original plan, an array that
"beamforms to itself", is a no-op on this observable, and shipping it as a result
would be shipping a null.

**Anything radiating somewhere other than at the pedestrian is not invisible**,
and that covers every always-on beam a real network actually transmits. The
broadcast beam has a fixed downtilt and points where the operator wants coverage.
The traffic beam is usually serving somebody else. Both re-weight `Q` in
elevation, which is the one variable this study's whole result turns on.

Sections 2 and 3 prove the invariance and say exactly how far it extends, because
one of the two matched policies is a genuine physical result worth publishing and
the other is an artefact of an approximation the estimator already makes.
Sections 4 to 6 are the configurations that do move the answer, with numbers.

---

## 2. Why an antenna is a re-weighting of `Q` and nothing else

Write the estimator exactly, before any approximation, so the place the pattern
enters is visible.

Let `nu(S)` be the volumetric density of sites, `P(S)` the transmit power of the
site at `S`, and `G(d ; S)` its power gain in direction `d`. The power density
arriving at `x` in the real scene is an integral over the source population of
the per site transfer, and by reciprocity the per site transfer for an isotropic
source is the flux density at `S` of an adjoint source at `x`.

Shoot `N` rays from `x`, uniformly on the sphere. Ray `j` escapes from its last
scattering vertex `x_K_j` in direction `u_ext_j` carrying throughput `w_j`. Its
bundle carries power `w_j / N` and has some cross section `dA(s)` at arclength
`s`. For any site inside the bundle the flux density is the bundle power over
`dA`, and the volume element is `dA ds`, so the cross section cancels identically
and the bundle's whole contribution is a **line integral of the source density
along the escaping ray**. Define

```
Lambda(y, u) = integral over t from 0 to infinity of
               nu(y + t u) * P(y + t u) * G(-u ; y + t u) dt
```

The gain is evaluated at `-u`, which is the direction from the site back down the
ray. Then

```
S_arr = (1/N) sum_j w_j Lambda(x_K_j, u_ext_j)

S_0   = (1/4pi) integral over 4pi of Lambda(x, u) dOmega(u)

chi   = S_arr / S_0
```

and both lines are exact. The free space reference is the same functional
evaluated along rays that start at `x`, because with the buildings deleted the
only path from a site to `x` is the straight one.

The shipped estimator replaces `Lambda(x_K_j, .)` by `Lambda(x, .)`. That is the
**far source approximation**, it predates this document, and it is what turns the
estimator into the familiar form: with `Q(u) = Lambda(x, u) / integral Lambda
dOmega`,

```
chi = (4 pi / N) sum_j w_j Q(u_ext_j)
```

which is `semantic_twin/propagation/tracer.py` line for line. Two remarks on the
approximation, both of which matter later.

It is **less violent than it looks** for the population this study uses. `nu` is
uniform in a horizontal slab of heights above the head, and a slab is invariant
under horizontal translation, so moving the ray's origin from `x` to `x_K` does
not change the depth of slab the ray traverses at all. Only two things break it:
a last vertex higher than `h_min`, which happens on facades above 13.5 m for the
rooftop band, and the range cap, which is a cylinder centred on `x` and not on
`x_K`. MONOSTATIC_SBR.md section 4.4 is the same caveat approached from the
coherence side.

It is **exactly what deletes the difference between a path's launch direction and
the direct direction**. Under it, the direction from a site to the last vertex
and the direction from that site to the pedestrian are the same direction. Hold
that thought until section 3.

With the replacement made, `G` appears only as a function of `u`, so

```
Q_G(u) proportional to Q(u) * G(-u ; a site lying along u from x)
```

**The pattern is a re-weighting of `Q` and enters nowhere else.** No ray path
changes, no throughput changes, no random number changes. Adding an antenna is
adding an illumination model, which is why
`semantic_twin/propagation/antenna.py` needs no tracer change and why every
comparison in this document is paired with zero Monte Carlo difference between
its columns.

One piece of geometry makes the elevation axis the interesting one. A site seen
at elevation `alpha` above the pedestrian's horizon has to radiate at a
depression of exactly `alpha` to reach them. **The elevation axis of `Q` and the
elevation axis of the antenna pattern are the same axis.** An electrical downtilt
of 12 degrees is a multiplier centred on sites at 12 degrees of elevation, and
the corrected rooftop law of MONOSTATIC_SBR.md section 2.7.1 puts its median site
at 9.5 degrees. The beam and the population sit on top of each other, which is
the whole reason this is worth computing rather than bounding.

---

## 3. The invariance, and the argument that nearly gets it right

### 3.1 The statement

If every site puts its beam peak on the pedestrian then `G(-u ; S)` is one
constant for every `u`. A constant factors out of both line integrals of section
2, and the normalisation of `Q` removes it. So `Q_G = Q` as an array of numbers
and `chi` is unchanged. `tests/test_antenna.py` asserts this twice, once on the
density at `rel = 1e-12` and once through the estimator on shared rays, where the
two columns agree to floating point.

### 3.2 The argument that is nearly right, and where it fails

There is a tempting route to the same conclusion and it should be written down
because it is wrong in a way that changes what survives.

> Every escaping ray is attributed to a site along its exit direction. Two
> distinct rays hitting the same site *point* is a codimension 2 condition, so
> measure zero. Each site therefore contributes exactly one path, matched
> beamforming puts the same peak gain on that one path as on the free space
> direct path, and it cancels.

The conclusion is right and the middle step is not. Codimension 2 in the
4-dimensional space of lines means dimension **zero**, that is, isolated points,
that is, a finite and generically non-empty set. It does not mean the empty set.
MONOSTATIC_SBR.md section 5.1 already proves the correct version for this scene:
for each ordered pair of planes there is at most one specular path, so the count
is finite and bounded by `N_pl (N_pl - 1)`, and "a finite set has measure zero in
a 4-manifold" is a statement about the **sampling measure**, not about how many
paths exist. A ground plane and the four walls of a square give a source five
first order images and up to twenty second order ones. That is twenty-five
paths, not one.

For the diffuse component it is worse for the argument. After a diffuse bounce
the outgoing direction is a free choice, so the family of escaping lines is
4-dimensional rather than 2-dimensional, and the set of them that reaches a fixed
site is 2-dimensional, which is a set of positive measure. This tracer's
scattering is a Rayleigh split with a real diffuse branch
(`tracer.py:specular_share`), so most escaping rays are in that family. A
continuum of paths reaches each site, not one.

So the premise is false. Why does the conclusion survive anyway? Because it does
not need the premise. It needs only that the gain towards the pedestrian is the
**same number for every site**, which is what "matched" means, and that is enough
for it to leave a normalised density alone. The path count never enters.

Getting this right is not pedantry, because the false premise also implies things
that are not true. If each site really did contribute one path, then a beam
steered at that path would recover the full array gain, and beam management would
be free. It is not, and section 3.4 is why.

### 3.3 The half that is a real result: full digital maximum ratio transmission

One matched policy needs no approximation at all, and this is the part that
belongs in the paper.

Let the site carry `MN` elements. The channel to the pedestrian is
`h = sum_p a_p b(d_p)*`, a sum over paths of the path amplitude times the array
response at that path's launch direction. Maximum ratio transmission uses
`v = h / ||h||` and achieves received power `||h||^2 = sum_m |h_m|^2`. The
aperture is 70 mm at 15 GHz and every path length in the scene is 100 m or more,
so each element sees the same set of paths with the same magnitudes and only the
phases differ across the aperture. Under uncorrelated scattering, which is the
same assumption PAPER_METHODS.md section 1.4 already makes when it refuses to sum
amplitudes,

```
E |h_m|^2 = sum_p |a_p|^2 g(d_p)     for every element m

E ||h||^2 = MN * sum_p |a_p|^2 g(d_p)
```

with `g` the single element pattern. The free space reference is one direct path,
and MRT on it achieves exactly `MN |a_0|^2 g(d_0)`. **The `MN` is common to both
and cancels exactly.** So

```
chi under full digital MRT = chi computed with the element pattern alone
```

and this holds with no far source approximation, no assumption that the paths are
angularly separated, and no assumption about the scene. It is the statement that
a matched filter's gain is `||h||^2` whatever `h` is. Cross terms between
distinct paths have zero expectation, and their variance is the coherent fading
this method already declares out of scope.

Two riders, and they are the useful part.

**The array factor cancels. The element pattern does not.** The element
multiplies each path's power before the aperture ever sees it, so it survives as
a re-weighting of `Q`. For the 3GPP element that is a mild elevation taper,
`-12 (alpha/65)^2` dB at the depression the site needs, which is 0.26 dB at the
rooftop median of 9.5 degrees and 10.2 dB at the 60 degree top of the band.

**Polarisation does not break it either.** MRT over a dual polarised array is a
matched filter over the whole space and polarisation channel, so its gain is
still the total power and still cancels. Polarisation does break the broadcast
case, and this tracer cannot see it, which is section 7.

`tests/test_antenna.py::test_full_digital_maximum_ratio_transmission_cancels_the_array_gain`
runs the expectation directly on a synthetic 24 path channel and an 8 by 8 panel.

### 3.4 The half that is an artefact: geometric steering and best beam selection

The other two matched policies are not invariant, and the estimator cannot see
that they are not.

A position aware base station steers at the pedestrian's coordinates. Then the
direct path gets the peak, but a bounced path leaves the site towards the last
vertex `x_K`, which is displaced from `x`. The offset angle at the site is about
`|x_K - x|_perp / R`. The last vertex can be a hundred metres from the observer
and `R` is 25 to 250 m, so this offset is tens of degrees, and the array's
response 20 degrees off boresight is 20 to 25 dB down. Geometric steering
therefore **suppresses the multipath** and drives `chi` towards its zero bounce
value.

Codebook best beam selection, which is what 5G beam management actually does,
sits between: the site picks the beam that maximises the reported power, which
illuminates the dominant reflector, and everything else gets a sidelobe.

Under the far source approximation the offset is identically zero, so both
policies collapse onto the matched case and read as invariant. **For these two,
the invariance is an artefact.** The inequality is one sided and provable: the
numerator's gain is the peak times a sidelobe factor no greater than one, and the
denominator's gain is exactly the peak, so

```
chi (geometric steering) <= chi (isotropic sites),  always
```

with equality only if the array has no directivity. Section 6.3 measures how far
below.

### 3.5 Summary of what cancels

| policy | array factor | element pattern | needs the far source approximation |
|---|---|---|---|
| full digital MRT at the pedestrian | cancels exactly | survives | no |
| geometric steering at the pedestrian | cancels | survives | **yes**, and it is an artefact |
| codebook best beam | cancels | survives | **yes**, and it is an artefact |
| fixed broadcast beam | survives | survives | no |
| serving another user | survives | survives | no |

---

## 4. Can the coherent stack in AEGIS be used here

Two questions are being conflated in PAPER_METHODS.md section 1.4 and they have
different answers.

### 4.1 Two phase scales, three orders of magnitude apart

Section 1.4 argues that at 15 GHz a path whose last vertex is 100 m from the
observer rotates its phase at `k |x_K - S| = 3.1e4` radians per radian of exit
angle, so an angular grid fine enough to sum amplitudes would need `3e-5` rad
cells and the grid has 512. That argument is correct and it is about **the
environment**.

The array's own aperture is a different and much smaller scale. Eight elements at
half wavelength spacing at 15 GHz span 70 mm, so the phase across the aperture
rotates at `k D = 22` radians per radian of direction. A 0.3 m aperture would
give 94. Three orders of magnitude below `3.1e4`.

The framing in radians per radian is not the sharp one though. The sharp
statement is about what has to be **resolved**:

- The array factor is a deterministic closed form function of **one** direction.
  The tracer evaluates the illumination density at the exact exit direction of
  every escaping ray (`tracer.py`, `model.density(exit_direction, ...)`), not at
  a binned one. There is no grid anywhere in the transmit pattern path and
  therefore no resolution requirement. A pattern with nulls costs variance and
  never bias.
- Coherent multipath combining needs the **relative phase between distinct
  paths**, which needs path lengths to well under 20 mm over hundreds of metres,
  on geometry from photogrammetric tiles with metre scale seaming. That is the
  thing section 1.4 forbids and it stays forbidden.

The reason the first is legitimate in a power only estimator is that the received
power from mutually incoherent paths is `sum_p G(d_p) |a_p|^2`, linear in the per
path powers. The pattern never couples two paths. The only thing that couples
paths is the array combining two of them inside one beam, and that is a cross
path phase whose expectation is zero. So applying a deterministic pattern to
powers is not an approximation to the coherent answer, it **is** the expectation
of the coherent answer.

**Section 1.4 should be split into these two claims.** As written it argues the
second and reads as if it forbade the first.

### 4.2 The coherent stack cannot be used, and the reason is structural

`src/aegis/coherent/`, `kernels/level7_coherent.py`, `kernels/level8_ecbf.py`
and `precoder.py` optimise a precoder over a transmit array, using per path
complex coefficients `psi` indexed by element. To feed them this study would have
to supply, for one base station, the complex amplitude of each path at each
element.

It cannot, and not because the phases are missing. **The transmit side degree of
freedom the stack optimises over has been marginalised away.** Under the far
source approximation every path from a given site leaves that site in the same
direction, namely `-u_ext` of the exit cell it was deposited in. A precoder acts
on the launch direction. If every path from a site shares one launch direction
then the exposure operator is rank one in the transmit space for that site and
there is nothing to optimise: the precoder can only scale it.

That is a sharper obstruction than the missing phase, because it survives even if
the phases were handed over. The escaping ray population does carry the joint
structure needed, `K(u_loc, u_ext)`, the transfer tensor of MONOSTATIC_SBR.md
section 2, and that tensor is a legitimate input to a body side coherent
calculation. What it does not carry is a source **position**, and without one the
launch directions of the paths from a single site are all equal by construction.

So the honest verdict is: **not on this traced object**. The bridge that would
work is to abandon the marginalisation for a sub-study, place a finite set of
sites, trace to each, and hand AEGIS the per site path list. That is a different
experiment with a different claim, and it would lose the property that makes this
study publishable, which is that no layout was invented.

What the stack *can* be used for without any of that is the worst case bound
already named in MONOSTATIC_SBR.md section 2.7 as `K_max`, since the largest
singular value of the transfer tensor over directions is a power domain quantity.
That is not implemented here.

---

## 5. What does move `chi`, and the assumptions each one needs

Everything below is a re-weighting of `Q` in the sense of section 2, so all of it
is free of new tracing and all of it is paired exactly against the isotropic site
baseline.

### 5.1 The broadcast beam

The cell defining beam covers the whole sector, so it is not the narrow traffic
beam. Modelled as the full vertical aperture of eight elements, which is what
sets coverage depth, no azimuth narrowing so the horizontal shape is the
element's own 65 degrees, and the site's three sectors summed because all three
transmit their broadcast at once. TR 38.901 clause 7.3.

Electrical downtilt is the parameter. `theta_etilt = 102` degrees, twelve degrees
of downtilt, is the 3GPP urban macro evaluation value. The study's rooftop
population has its median site at 9.5 degrees of elevation, so the beam sits
almost exactly on the population's centre of mass, and the eight element column's
12.7 degree beamwidth is comparable to the width of the population itself.

### 5.2 Serving another user, as a sweep

The cleanest form of the loaded case is not a population average, it is a sweep.
Place the served user a fixed angular offset from the pedestrian **in the site's
own frame** and read `chi` against that offset. Zero offset is the matched case,
so the invariance and its failure sit on one axis. This needs no user density
assumption at all, which is why it is the primary form.

This is a different case from section 3.4 and the two should not be read
together. Here the network is aiming somewhere else, the offset applies to the
free space reference exactly as it applies to the scene, and `chi` can move
either way. In section 3.4 the network is aiming at the pedestrian, the
reference collects the peak and only the scene paths collect sidelobes, and
`chi` can only fall. The sweep below therefore does not measure the artefact and
cannot: measuring the artefact needs the last scattering vertex, which is what
section 6.3 goes and gets.

### 5.3 Serving another user, as a population average

The population averaged form needs an assumption and here it is, stated because
the answer is a functional of it.

**The scheduled user is exchangeable with the pedestrian.** Its depression angle
below the site is drawn from the same elevation density that describes where
sites sit on the pedestrian's sky, and its azimuth is uniform across the serving
sector. The justification is a symmetry rather than a measurement: a homogeneous
site process and a homogeneous user process in the same slab give the same angle
distribution read from either end.

Two things it gets wrong, with signs.

- **Cell association.** A user attaches to a strong site, not a uniformly drawn
  one, so real served users are closer and therefore steeper. The beam then
  points below a pedestrian at the median elevation and the gain towards them
  falls. The model is optimistic.
- **Scheduling.** One user per site per slot. A site multiplexing several users
  spreads its beam and pushes the average towards the uniform limit.

The limit that makes the number interpretable: an array whose steering direction
is uniform over the whole sphere delivers, on average, unit array gain, because
`(1/4pi) integral |AF|^2 dOmega` is 1 for a linear array at half wavelength
spacing and 0.68 to 0.72 for this 8 by 8 panel. The panel falls short of 1
because a rectangular lattice's diagonal offsets are `lam/2 sqrt(dm^2 + dn^2)`,
which are not whole half wavelengths, so its steering vectors are not orthonormal
over the sphere. **A loaded array only reshapes `Q` to the extent that the user
population is more concentrated than that**, and the measured number is what that
concentration is worth.

### 5.4 The three sector layout and its cusps

Three 65 degree elements on a 120 degree grid sum to a horizontal pattern that is
flat on boresight and about 7 dB down at the 60 degree crossover. A pedestrian on
that crossover sees two sectors at their pattern edge, and it does not average
away within a site.

It can average away **across** sites, and whether it does is an assumption about
the deployment. If every site's sector grid shares one orientation, which is
roughly what operators do, then the azimuth of `Q` is a fixed 120 degree periodic
ripple whose phase relative to the square is unknown. That phase is a nuisance
parameter, and the spread of `chi` across it is the result. If sector azimuths
are instead independent across sites, the ripple averages to its azimuthal mean
and the effect vanishes exactly.

Note what the effect needs in order to exist at all: `chi` is an inner product of
`K(alpha, beta)` with `Q(alpha, beta)`, so rotating a 120 degree periodic ripple
in `Q` changes `chi` only through the **azimuthal structure of the square's own
transfer kernel**. A rotationally symmetric square would show nothing. So this
measurement is a measurement of the square's asymmetry as much as of the antenna.

---

## 6. Results

### 6.1 What was run

Two runs, and they are different kinds of measurement.

The **pattern sweep** is the whole model set on eleven cities, 32 stratified
standpoints each, 150 000 rays, three bounces, 250 m crop, seed 7, at 15 GHz.
Every column in it is scored on the same rays inside one trace, so the columns
share their Monte Carlo noise exactly and every difference below is a paired
difference with none of it. The elevation kernel of section 2, 92 bands, rides
along on the same rays.

The **steering measurement** of section 6.3 could not ride along, and this is
worth saying plainly because it is the one thing in this document that needed
new tracing. The published payload stores `rho_rooftop`, an 80 by 512 histogram
of the **local arrival direction at the body**. Exit directions, last scattering
vertices and per path throughputs are all marginalised away by the deposit and
none of them reach disk, by the design rule that no path table is stored. So the
offset between a path's launch direction and the direct direction is not
recoverable from anything on disk, and section 6.3 is a re-trace of Korenmarkt
with `PathRecorder` attached, 20 standpoints, 30 000 rays each. It is not an
approximation to a stored quantity, it is a quantity that was never stored.

Both are one module and two flags, so every number below is reproducible without
a script that lives anywhere else.

```
python -m semantic_twin.propagation.antenna --all-sites --kernel \
    --locations 32 --rays 150000 --max-bounces 3 --crop-m 250 --seed 7 \
    --tag antenna11

python -m semantic_twin.propagation.antenna --artefact --sites korenmarkt \
    --locations 20 --rays 30000 --max-bounces 3 --crop-m 250 --seed 7 \
    --tag paper
```

### 6.2 The invariance, on real rays

`matched` reproduces the isotropic site column at every one of the 352
standpoints, to floating point. That is section 3.1 through the whole estimator
rather than through the density alone.

`offset0` and `element` agree with each other to floating point everywhere as
well, which is the second half of the same statement: at zero offset the array
factor sits on its peak for every site, the peak is a constant, and what is left
is the element pattern.

### 6.3 Geometric steering, and how far below

This is the number section 3.4 promised. A site steers its beam at the
pedestrian's actual position. The direct path keeps the peak. A bounced path
leaves that site towards its own last surface, which is somewhere else, so it
collects whatever the pattern has at that offset. The reduction is the deposit
weighted mean of that ratio, evaluated at the site ranges the illumination law
itself integrates over, with the aperture broadside on the pedestrian so the
element pattern is unity on both sides and does not contaminate the number.

**Report it as a bound, because that is what it is.** Two statements are exact
and one is measured.

Exact, and independent of the array, the codebook and the policy: a path that
never touched a surface leaves its site in the direct direction, so it receives
whatever the reference receives and its ratio is one. Therefore

```
chi (any beam aimed at the pedestrian) / chi (reported)  >=  direct measure
```

and the direct measure is a property of the scene, not of the antenna. At
Korenmarkt it is 0.696 for the rooftop population and 0.505 for the street one.
**No aperture of any size can reduce `chi` by more than 1.58 dB in the rooftop
model or 2.96 dB in the street model.**

Exact, in the other direction: under exact steering the ratio is at most one
pointwise, so `chi` can only fall. Section 3.4's inequality, unchanged.

Measured, between the two. Median over 20 Korenmarkt standpoints, with the
10th and 90th percentile across standpoints in brackets.

| aperture | rooftop | street small cell |
|---|---|---|
| 2 x 2 | -0.05 dB (-0.07, -0.04) | -0.47 dB (-0.68, -0.23) |
| 4 x 4 | -0.16 dB (-0.22, -0.12) | -1.03 dB (-1.57, -0.54) |
| **8 x 8** | **-0.38 dB (-0.49, -0.25)** | **-1.64 dB (-2.53, -1.09)** |
| 16 x 16 | -0.61 dB (-0.94, -0.45) | -2.32 dB (-3.50, -1.48) |
| 32 x 32 | -0.93 dB (-1.34, -0.71) | -2.85 dB (-3.85, -1.63) |
| the floor above | -1.58 dB | -2.96 dB |

Two readings of this table.

**It saturates, and it saturates at the direct measure.** A 32 by 32 panel is a
0.32 m aperture at 15 GHz with a 3.2 degree beam, far narrower than any offset
in the scene, and it still only reaches -0.93 and -2.85 against floors of -1.58
and -2.96. The street column is 96 percent of the way to its floor. So the array
size is not the parameter that sets the answer past about 16 elements a side.
The parameter is how much of the illumination measure arrives without touching
anything.

**The rooftop and street columns differ by a factor of four in dB, and the whole
of the difference is one angle.** The offset is the displacement of the last
vertex from the observer, divided by the range of the site that sees it, and the
two bands are penalised on both. Under its own deposit measure the rooftop band
collects from a median slant range of 124.5 m with a median last vertex 14.1 m
away, which is a median offset of 3.7 degrees. The street band collects from
31.3 m with a median last vertex 37.1 m away, which is 18.6 degrees. The second
is worse on both factors at once, because the street band's support is shallower,
and a shallow exit is a ray that travelled a long way across the square before
leaving it. Against the 8 by 8 panel's 12.7 degree beam, 3.7 degrees is inside
the main lobe and 18.6 degrees is outside it, and that is the entire result.

Restricted to the bounced measure alone, where the effect actually lives, the 8
by 8 suppression is -1.30 dB for rooftop and -4.44 dB for street, and at 32 by 32
it is -4.66 dB and -12.38 dB.

That second reading is also a caveat on the estimator that this measurement
turned up on its way past. The rooftop band is nominally 25 to 250 m in
horizontal range, but the range at which its illumination is actually collected,
once the square has had its say, is 125 m. The far source approximation is being
applied at half the range the band's nominal extent suggests.

### 6.4 Codebook selection: measurable in part, and a stated gap

A real network does not steer at coordinates, it picks a beam. Splitting that
into the two things it can mean matters, because one is measurable here and the
other is not.

**Picking the grid beam nearest the pedestrian** is measurable. The grid is the
standard discrete Fourier one, uniform in the direction cosine. Median over the
same 20 standpoints, canonical 8 by 8 panel.

| beams per axis | rooftop | street small cell |
|---|---|---|
| 8, matched to the aperture | -0.25 dB | -1.54 dB |
| 16, twice oversampled | -0.37 dB | -1.61 dB |
| 32, four times oversampled | -0.37 dB | -1.66 dB |
| exact steering, the limit | -0.38 dB | -1.64 dB |

**Codebook granularity is not one of the parameters that sets the range.** Once
the grid is at least as fine as the aperture the whole axis is worth 0.13 dB for
the rooftop population and 0.10 dB for the street one, and it converges to exact
steering from above, because quantisation detunes the free space reference
slightly more than it detunes scene paths that were already off the beam.

Grids **coarser** than the aperture were computed and are not reported, and the
reason is a modelling boundary rather than a result. With fewer beams than
elements the nearest grid beam is more than a beamwidth from the target, so the
free space reference can land in a pattern null, and the ratio then reads +50 dB
because it is dividing by a null. No scheduler would choose a beam that puts a
null on its own user, so that configuration is not in the class of policies this
section is about. A real network with a coarse beam set broadens its beams to
match the grid, and a broadened beam is a smaller effective aperture, which is
the array size table of section 6.3 read down instead of across. **The two axes
are one axis: the effective aperture that forms the beam.**

**Picking the beam that maximises the received power**, which is what 5G beam
management actually does, is **not measurable from this object and is not
approximated here**. It needs the set of paths arriving from *one* site in order
to know which of them is dominant. The far source marginalisation has replaced
each site by a continuum of them lying along one escaping ray, so a single site's
path set does not exist in the estimator's state.

What can be said without it is an inequality inside a fixed codebook, and it is
worth writing carefully because the loose version of it is not true. Compare two
policies on the **same** grid. One picks the beam nearest the pedestrian, which
is the measured column. The other picks the beam maximising the received power,
which is what beam management does. In the scene the second maximises the same
sum the first evaluates at one particular member, so its numerator is at least
as large. In free space there is one path, so selection on received power picks
the beam with the most gain towards the direct direction, which is the same beam
the first policy picks, so the two references are equal. Therefore

```
chi (best beam) >= chi (nearest beam to the pedestrian),  same codebook
```

and the measured column is a **lower bound** on the loaded network's answer, not
an estimate of it. Note what this does not say: exact steering is not a member of
a finite codebook, so it is not ordered against best beam selection at all, and
the bracket is the one above rather than one anchored on the geometric column.
Closing the gap needs the different experiment of section 4.2: place a finite set
of sites and trace to each.

### 6.5 The broadcast beam, and the loaded beam

The columns that move `chi` because they radiate somewhere other than at the
pedestrian. Median over 32 standpoints of the paired shift against the isotropic
site column, in dB. `element` is section 3.3's full digital MRT and is included
because it is the one matched policy that does move the answer.

| site | element | broadcast, grid 0 | grid 40 | grid 80 | loaded |
|---|---|---|---|---|---|
| brussels_grandplace | -0.92 | -2.41 | -1.89 | -1.65 | -3.02 |
| korenmarkt | -0.65 | -1.55 | -1.48 | -0.66 | -1.97 |
| krakow_rynek | -0.58 | -1.11 | -0.76 | -0.96 | -1.74 |
| london_trafalgar | -0.56 | -0.53 | -1.04 | -0.62 | -1.25 |
| madrid_plazamayor | -1.07 | -2.80 | -2.91 | -2.49 | -3.64 |
| mexico_zocalo | -0.47 | -0.74 | -0.98 | -0.67 | -1.44 |
| milan_duomo | -0.54 | -0.60 | -0.86 | -0.95 | -1.28 |
| newyork_timessquare | -0.22 | -0.33 | -0.51 | -0.61 | -0.33 |
| prague_staromestske | -0.62 | -0.78 | -0.71 | -1.36 | -1.52 |
| tokyo_hachiko | -0.71 | -0.77 | -1.31 | -2.06 | -1.28 |
| toulouse_capitole | -0.73 | -1.20 | -1.62 | -1.25 | -1.95 |
| **median across sites** | **-0.62** | **-0.78** | **-1.04** | **-0.96** | **-1.52** |

Street small cell sites, same layout, with `MICRO_TILT_DEG = 96`:

| site | element | broadcast, grid 0 | grid 40 | grid 80 | loaded |
|---|---|---|---|---|---|
| brussels_grandplace | -0.46 | -2.57 | -1.91 | -2.05 | -3.55 |
| korenmarkt | -0.38 | -1.62 | -1.58 | -1.49 | -2.73 |
| krakow_rynek | -0.39 | -1.51 | -1.78 | -1.57 | -2.80 |
| london_trafalgar | -0.32 | -0.37 | -3.20 | -0.85 | -1.49 |
| madrid_plazamayor | -0.67 | -4.20 | -4.27 | -3.78 | -5.72 |
| mexico_zocalo | -0.36 | -1.66 | -1.88 | -1.78 | -2.51 |
| milan_duomo | -0.18 | -1.55 | -1.18 | +0.33 | -2.78 |
| newyork_timessquare | -0.03 | +0.30 | -0.01 | -0.10 | -0.02 |
| prague_staromestske | -0.37 | -1.69 | -1.43 | -2.28 | -3.17 |
| tokyo_hachiko | -0.19 | -0.20 | -0.21 | -1.94 | -0.56 |
| toulouse_capitole | -0.40 | -2.13 | -1.87 | -2.04 | -3.47 |
| **median across sites** | **-0.37** | **-1.62** | **-1.78** | **-1.78** | **-2.78** |

At Korenmarkt, the answer to the question this document was opened with: **the
broadcast pattern moves `chi` by -1.55 dB for the rooftop population and -1.62 dB
for the street one at the sector grid orientation the study cannot pin, and by
-0.66 to -1.55 dB and -1.49 to -1.62 dB across the orientations it might have.**

Three readings.

**The sign is not guaranteed.** Two entries are positive. Milan at grid 80 and
New York at grid 0 both come out above the isotropic site column, because a
downtilted beam that misses the sites the square cannot see anyway, while
keeping the ones it can, is a re-weighting in the helpful direction. There is no
theorem here, only an inner product, and section 5.4 said so before the numbers
arrived.

**The spread across cities is larger than the shift itself.** The broadcast beam
is worth -0.33 dB at New York and -4.20 dB at Madrid. That is not a property of
the antenna, which is identical in both, it is a property of the square, and
section 6.9 is what makes it readable.

**The loaded beam is the largest mover in the set**, at -1.52 dB median for the
rooftop population and -2.78 dB for the street one, and it is the configuration
carrying the most assumption. Section 5.3 states the assumption and its two
signed biases, and it should be read alongside this number rather than after it.

### 6.6 The three sector cusp

The spread of `chi` over the sector grid orientation, which no register in this
study can pin, taken as the max over min of the three rotations at each
standpoint and then the median over standpoints.

| site | rooftop | street |
|---|---|---|
| brussels_grandplace | 2.05 | 1.72 |
| korenmarkt | 1.97 | 1.92 |
| krakow_rynek | 1.64 | 1.56 |
| london_trafalgar | 1.46 | 2.84 |
| madrid_plazamayor | 1.51 | 0.93 |
| mexico_zocalo | 1.69 | 2.06 |
| milan_duomo | 1.21 | 3.50 |
| newyork_timessquare | 1.23 | 1.19 |
| prague_staromestske | 1.21 | 1.40 |
| tokyo_hachiko | 2.20 | 2.52 |
| toulouse_capitole | 1.48 | 1.66 |
| **median** | **1.51** | **1.72** |

**A nuisance parameter nobody can measure is worth 1.5 dB, which is more than
the broadcast downtilt itself is worth at seven of the eleven sites.** The
sector grid orientation relative to the square is not in OpenStreetMap, not in
the panoramas, and not in any register this study touched. If sector azimuths
are instead independent across sites the ripple averages away exactly, so this
number is an upper bound on a deployment correlation rather than a measurement
of one, and it is reported as the spread rather than as a column because the
spread is the honest object.

The reason it is not zero is section 5.4's: rotating a 120 degree periodic
ripple in `Q` can only change `chi` through the azimuthal structure of the
square's own kernel. A rotationally symmetric square would show nothing. So 1.5
dB is a measurement of how far these squares are from rotationally symmetric,
read through an antenna.

### 6.7 Serving another user, as a sweep

`chi` against the angular offset of the served user from the pedestrian, in the
site's own frame, median across the eleven sites.

| offset | rooftop | street |
|---|---|---|
| 0 deg | -0.62 dB | -0.37 dB |
| 2 deg | -0.61 dB | -0.36 dB |
| 5 deg | -0.51 dB | -0.29 dB |
| 10 deg | +0.09 dB | +0.25 dB |
| 20 deg | -1.41 dB | -1.06 dB |
| 45 deg | -0.36 dB | +1.51 dB |

**It is not monotone, and it is not a loss.** At zero the sweep reproduces the
element column exactly, which is the invariance. Past that it oscillates with
the sidelobe structure and twice comes out above the isotropic site column.

The mechanism is worth stating because it is not the obvious one. The gain the
pedestrian collects when the beam is `psi` degrees away is not a function of
`psi` alone. The array's steering variable is the direction cosine, so at a site
elevation `alpha` the pattern argument for a fixed elevation offset is
`pi (sin(alpha + psi) - sin(alpha))`, which **shrinks as the site gets steeper**.
A fixed angular offset therefore costs less at high elevation than at low, the
re-weighting favours steep sites, and steep is exactly where the square's kernel
has its mass. For the street population at 45 degrees of offset that is worth
+1.51 dB. A beam pointed away from the pedestrian can raise their exposure,
because what it is really doing is preferring the sites they can see.

### 6.8 Does the ordering of the eleven cities move

Yes, and by more than one adjacent swap. Kendall tau against the reported
ordering, over all 55 city pairs.

| column | rooftop | street |
|---|---|---|
| element, full digital MRT | +0.927, 2 pairs reversed | +1.000, none reversed |
| broadcast, grid 0 | +0.818, 5 pairs | +0.782, 6 pairs |
| broadcast, grid 40 | +0.891, 3 pairs | +0.745, 7 pairs |
| broadcast, grid 80 | +0.927, 2 pairs | +0.927, 2 pairs |
| loaded | +0.818, 5 pairs | +0.709, 8 pairs |

The size of the reversals is what decides whether this matters. Adjacent cities
in the reported rooftop ordering are separated by 0.48 dB at the median, and the
broadcast beam reverses pairs separated by up to **1.53 dB**, Madrid against
Tokyo. In the street ordering, where adjacent cities are 0.80 dB apart, it
reverses pairs up to **2.59 dB** apart, London against Tokyo, and the loaded beam
up to **2.97 dB**. The whole eleven city spread is 5.6 dB for the rooftop
population and 9.8 dB for the street one, so a 1.5 to 3.0 dB reversal is a
quarter of the axis the ranking lives on.

**So the ranking of cities by susceptibility is not an antenna free statement.**
The one policy that nearly preserves it is full digital MRT, which reverses no
street pair at all and two rooftop pairs separated by 0.58 dB or less. Every
always-on configuration reorders. That is the practical consequence of this
whole document and it is the opposite of the null the original plan would have
produced.

### 6.9 The elevation kernel, and what actually sets a city's sensitivity

The 92 band probe bank is the sufficient statistic of section 5, and it explains
every table above. `K(alpha)`, median over standpoints, at seven elevations.

| site | 2 deg | 5 | 10 | 20 | 40 | 60 | 80 |
|---|---|---|---|---|---|---|---|
| brussels_grandplace | 0.001 | 0.004 | 0.036 | 0.248 | 0.518 | 0.837 | 1.173 |
| korenmarkt | 0.002 | 0.013 | 0.109 | 0.365 | 0.750 | 1.015 | 1.223 |
| madrid_plazamayor | 0.001 | 0.004 | 0.018 | 0.478 | 0.924 | 1.214 | 1.221 |
| mexico_zocalo | 0.005 | 0.034 | 0.271 | 0.795 | 1.143 | 1.199 | 1.234 |
| newyork_timessquare | 0.040 | 0.091 | 0.116 | 0.147 | 0.320 | 0.653 | 1.111 |
| tokyo_hachiko | 0.010 | 0.016 | 0.062 | 0.235 | 0.589 | 0.948 | 1.211 |

A square attenuates grazing illumination by 25 to 30 dB and passes steep
illumination whole, and above 60 degrees the kernel exceeds 1 because the ground
returns what the sky sent. So `K` climbs by three orders of magnitude across
exactly the band the rooftop population occupies, which is why an antenna that
re-weights in elevation is not a small correction.

**New York is the counterexample that proves the mechanism.** Its kernel is
nearly flat, 0.040 at 2 degrees rising only to 0.147 at 20, because Times Square
is a canyon and blocks steep illumination almost as effectively as grazing. A
flat kernel is orthogonal to any re-weighting, so New York is the site where
every antenna column is smallest: -0.22 dB for the element, -0.33 dB for the
broadcast beam, -0.03 dB for the loaded street beam. **A city's sensitivity to
the antenna is set by how much its own kernel varies across the band the sites
occupy, and not by how blocked it is.** New York is the second most blocked
square in the set and the least antenna sensitive.

The same statistic in one number, two ways, and both are correlations rather
than identities.

The rooftop population's median site sits at 8.07 degrees of elevation at every
one of the eleven, because that is a property of the law and not of the city.
The elevation at which the exposure is actually collected, weighting by `K` as
well, runs from 9.0 degrees at New York to 17.4 degrees at Madrid. That gap,
between where the sites are and where the exposure comes from, predicts how much
the element pattern costs at Pearson 0.96 and Kendall 0.75 across the eleven.

What predicts the broadcast column better is the kernel's dynamic range inside
the band, `max K / min K` over the rooftop support, which is 10.3 dB at New York
and 29.4 dB at Madrid. It orders the broadcast shift at Kendall 0.78 against 0.60
for the K weighted elevation. That is the sharper statement of the mechanism: the
element is a smooth taper and cares where the mass is, the broadcast beam is a
12.7 degree window and cares how much contrast there is for it to select on.

It is also why the element pattern costs more than its own taper. Averaged over
the rooftop population the TR 38.901 element is only 0.45 dB down, and 0.26 dB
at the population's median elevation. But it is 10.2 dB down at the 60 degree
top of the band, and the top of the band is where the square lets illumination
through. Measured, it costs 0.62 dB at the median site and 1.07 dB at Madrid.

---

## 7. What this model cannot express

Ranked by how much it would change the answer.

**Polarisation.** `tracer.py` carries the unpolarised power average of the two
Fresnel coefficients and approximates the coherency matrix as isotropic in the
transverse plane. A broadcast beam has a fixed polarisation, and a path that
arrives cross polarised to it is suppressed by the cross polar discrimination of
the last bounce. The estimator cannot see that. It does not affect the MRT result
of section 3.3, which is a matched filter over polarisation as well as space.

**The far source approximation, again.** Section 3.4 is the honest version: for
two of the five policies in the table the invariance is an artefact, and the size
of the artefact is bounded rather than computed here.

**Duty cycle.** A swept synchronisation beam is on the pedestrian for one slot in
`n`, so a time averaged exposure sits below the envelope this document reports
for it. The envelope is an upper bound and is labelled as one.

**Per site power control.** `chi` is defined as a ratio to the same network in
free space, so a network that raises power in a deep canyon is not expressed. It
would change `S_0`, which the caller owns, and not `chi`.

**One panel, one polarisation, no mechanical tilt.** TR 38.901 allows
`(M, N, P, Mg, Ng)` and this uses `P = Mg = Ng = 1`. A cross polarised panel
doubles the element count without changing the array factor, so it does not move
anything here.

---

## 8. Status of each claim

Four levels. **Proved** means it follows from the definitions with no numerical
input. **Measured** means a number in section 6 with a run behind it.
**Assumption** means the answer is a functional of something stated rather than
observed. **Gap** means it was asked and is not answered.

| claim | status | where |
|---|---|---|
| A pattern enters the estimator only as a re-weighting of `Q` | proved, under the far source approximation the estimator already makes | 2 |
| A beam matched to the pedestrian leaves `chi` exactly unchanged | proved, and run to floating point on 352 standpoints | 3.1, 6.2 |
| The codimension 2 argument for that invariance is wrong | proved, dimension zero is isolated points and not the empty set | 3.2 |
| Full digital MRT cancels the array factor exactly and keeps the element | proved, no far source approximation needed | 3.3 |
| The element pattern is 0.26 dB at 9.5 deg and 10.2 dB at 60 deg | measured against Table 7.3-1, exact | 3.3, 6.9 |
| Geometric steering and codebook selection read as invariant only because of the far source approximation | proved | 3.4 |
| Their reduction is at most `1 - direct measure`, whatever the array | proved, and the direct measure is measured at 0.696 and 0.505, so 1.58 and 2.96 dB | 6.3 |
| The reduction is 0.38 dB rooftop and 1.64 dB street on an 8 by 8 | measured, 20 Korenmarkt standpoints, re-traced with the recorder | 6.3 |
| It saturates in aperture, at 0.93 and 2.85 dB by 32 by 32 | measured | 6.3 |
| Codebook granularity finer than the aperture is worth under 0.15 dB | measured | 6.4 |
| Best beam selection lies above the nearest beam column on the same codebook | proved, so the measured column is a lower bound and not an estimate | 6.4 |
| Where best beam selection actually sits | **gap**, it needs one site's path set and the marginalisation has removed it | 6.4 |
| The coherent stack cannot be used on this traced object | proved, the transmit degree of freedom is marginalised away, so the operator is rank one per site | 4.2 |
| PAPER_METHODS section 1.4 conflates two phase scales three orders of magnitude apart | proved, 22 rad per rad across the aperture against 3.1e4 through the environment | 4.1 |
| The broadcast beam moves `chi` by 0.33 to 4.20 dB depending on the city | measured, eleven cities, 32 standpoints each | 6.5 |
| Its sign is not guaranteed and two entries are positive | measured | 6.5 |
| The sector grid orientation is worth 1.5 dB median and up to 3.5 dB | measured, and it is an **assumption** that grids are correlated across sites | 5.4, 6.6 |
| The loaded beam moves `chi` by 1.52 dB median rooftop and 2.78 dB street | measured, on the exchangeable user **assumption** of 5.3 | 6.5 |
| The offset sweep is not monotone and can raise `chi` | measured, and explained by the direction cosine steering variable | 6.7 |
| The eleven city ordering moves, reversing pairs up to 2.6 dB apart | measured | 6.8 |
| Full digital MRT nearly preserves the ordering | measured, no street pair reverses | 6.8 |
| A city's antenna sensitivity is set by its kernel's dynamic range in the band | measured as a correlation, Kendall 0.78, not an identity | 6.9 |
| Polarisation would change the broadcast case | **gap**, the tracer carries an unpolarised power average and cannot express it | 7 |
| The duty cycle of a swept beam | **gap**, the swept column is an envelope and is labelled one | 7 |
| The far source approximation applies at 125 m and not the band's 250 m | measured, and it is a caveat on the estimator rather than on the antenna | 6.3 |

Three things worth flagging as they are not claims but they bound everything
above.

**The bounce budget does not reach any of it.** Everything is at three bounces
and 250 m. Korenmarkt re-run at four bounces, same seed, same 32 standpoints,
moves `chi` itself by 0.00 dB for the rooftop population and 0.01 dB for the
street one, and moves **every** paired antenna shift in the tables above by less
than 0.005 dB. The budget cancels in the ratios because the comparisons are
paired inside one trace, and this is the measurement of that rather than the
argument for it.

**The loaded column is the one number here that changed under a correction, and
by 0.014 dB.** `LoadedBeam`'s azimuth quadrature sampled both sector endpoints
while weighting every node equally, which is trapezoid nodes on midpoint
weights, and it lifted the loaded gain by about 30 percent at the shipped 13
nodes. It moved `chi` by 0.014 dB for the rooftop population and 0.008 dB for the
street one, and left every other column bit identical. The reason the two numbers
differ by three orders of magnitude is that `chi` is a ratio to a normalisation
computed with the same gain, so a level error cancels exactly and only the
azimuthal shape error survives. Section 6 is the corrected run.

**Nothing here uses image evidence.** The antenna axis is a property of the
illumination model and the geometry, and it would read the same on a mesh with
no panorama behind it at all.

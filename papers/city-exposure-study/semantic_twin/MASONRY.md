# Brickwork as a diffraction grating

Every published treatment of facade scattering fits a diffuse scattering
coefficient to radio measurements. This document does not. A masonry wall is a
fully specified periodic structure whose unit format, joint width, joint profile,
bond and dimensional tolerance are all published in construction standards, so
its bistatic response can be computed rather than fitted, and the result can then
be compared against measurements instead of being derived from them.

`ROUGHNESS.md` states the problem this closes. The brick face is 0.024 to
0.095 mm RMS, which is 99.9 percent specular at 28 GHz, yet Landron and
co-workers measured `sigma_h` of about 0.5 cm on a real brick wall and 28 GHz
urban campaigns put roughly 20 percent of received power in diffuse scattering.
The diffuse power cannot be coming from the surface finish. That leaves the joint
grid and the unit-to-unit offsets, which was a hypothesis and is now settled.

Everything below is labelled. **Computed** means this repository produced the
number. **Read** means it was taken from a named source.

## What is computed here, in six sentences

The specular power a brick wall keeps has a closed form in the mortar area
fraction, the joint recess depth and the unit tolerance class, and that form is
periodic in the recess rather than decaying, which no Gaussian roughness model
can reproduce. Expanded to second order it yields an effective RMS height of
2.60 mm for standard UK brickwork with a 5 mm recess, reaching Landron's measured
5 mm at a 12.4 mm recess that sits inside the 15 mm cap Dutch pointing guidance
allows, so a 1996 field measurement and a masonry standard agree without either
being fitted to the other. The mechanism is the recess and not the dielectric
contrast: measured against the power a flat brick wall would reflect, a 5 mm
recess at 10 GHz leaves 55 percent in the specular direction, puts 20 percent
into diffraction orders and couples the remaining 25 percent into the wall, while
giving mortar a permittivity of 7 against brick's 3.91, far beyond any measured
contrast, moves under one percent. The non-specular return is a comb of
between 61 and 1889 propagating orders depending on band, carrying 11 to 30
percent of the diffuse power, sitting on a smooth pedestal whose angular width is
set by the brick dimensions and is neither Lambertian nor a directive lobe, while
the rigorous envelope of the comb itself is flat to 1.2 dB across the whole
hemisphere at 10 GHz and 5 dB at 28 GHz, carrying half or more of its power
backwards, which is the Lambertian behaviour real facade fits keep reporting and
attributing to street furniture.
The comb survives realistic manufacturing tolerance and stays 13 to 16 dB above its
own local trend through a 3 to 5 degree beam at 10 GHz and 3.5 to 8.7 dB at
28 GHz, which is why nobody has seen it: the campaigns that would have found it
use beams as wide as the structure they are looking for. **The cheap solver that
carried the sweep is validated against the rigorous one for joint grooves no
deeper than half their width and incidence no steeper than 45 degrees at FR2, and
it fails by a third outside either bound**, so a deeply raked joint and a grazing
FR2 street canyon both need a rigorous solve, and a monostatic estimator needs
one everywhere at FR2.

## Choosing the method, and why the rigorous one is the cheap one

Three methods were available and the choice is not the obvious one.

**Finite difference time domain** is the general answer and the wrong one here.
It solves for a volumetric field when the answer is a few hundred complex
numbers, and it needs a perfectly matched layer plus Bloch boundaries to
represent a structure whose periodicity is already exact. Rejected on cost with
no accuracy gain.

**Physical optics, the Kirchhoff phase screen**, replaces the true surface field
with the incident field times a local plane-interface reflection coefficient and
a piston phase. It is what every ray tracer does implicitly when it puts relief
on a surface. It is cheap enough to sweep, and its order amplitudes have a closed
form because the elevation is a union of rectangles, so no rasterisation is
needed at all. It is also not obviously valid: a recessed joint at 28 GHz is a
sharp-edged groove about one wavelength wide and half a wavelength deep, so the
large-radius-of-curvature condition fails at every arris and multiple scattering
inside the groove is not negligible.

**Rigorous coupled wave analysis**, the Fourier modal method, is exact for the
permittivity profile it is given, and for this structure it is cheap. The unit
cell is piecewise constant in depth with only two strata: a relief layer of the
recess depth that is brick where the units are and air over the joints, and a
semi-infinite substrate. Two layers means at most two eigenvalue decompositions,
and when mortar and brick carry the same permittivity the substrate is uniform
and costs none. The unknown is the Floquet order amplitudes, whose count is set
by the cell size in wavelengths.

The decision is to use all three tiers and say what each buys.

- RCWA is the reference. It is exact up to the Fourier truncation, which is a
  reported quantity rather than a chosen one.
- The phase screen carries the sweep, licensed by direct comparison against RCWA
  on the same cells rather than by argument.
- The phase screen is also the only one of the three that can average over
  disorder, because a rigorous periodic solver requires strict periodicity and a
  real wall is not strictly periodic. That is not a limitation of RCWA, it is a
  statement that disorder is a different question, and it is handled in closed
  form rather than by supercells.

`semantic_twin/rcwa.py` is verified against the Fresnel coefficients of a
half space for both polarisations, lossy and lossless, from normal to 85 degrees,
to 2.4e-13, and against the analytic two-interface slab response to 1e-9, with
reflected plus transmitted power summing to one for a lossless patterned grating.
Those are tests, not spot checks.

### Where the method breaks

Stated in the code and repeated here.

- **Grazing incidence.** The phase-screen power budget, the sum of the coherent
  comb and the incoherent pedestal against the flat-wall reflectance, holds
  within a few percent to 60 degrees, drifts to between 0.82 and 1.02 at 75
  degrees, and reaches 1.37 at 85 degrees. A number above one is unphysical, so
  the 85 degree column of every sweep is reported and must not be used. This
  matters, because street geometry is grazing.
- **Fourier truncation.** Reported per solve. The retained harmonics must cover
  every propagating order, which at incidence `theta` on a cell `L` across needs
  `m_max >= (1 + sin theta) L / lambda`. Truncating below that silently deletes
  coherent orders, and it is why an earlier version of the power budget test
  failed at 60 degrees.
- **The two-level idealisation.** A real joint is a tooled profile, not a square
  step, and a real arris is chamfered or worn. Both smooth the height field and
  both reduce the high orders, so the comb computed here is an upper bound on
  angular structure.
- **Illumination.** Both solvers assume a plane wave on an infinite wall. Finite
  patch size is handled separately and is the reason the comb has finite width.

## The geometry, which is entirely in standards

Gathered by a literature leg and recorded with sources in
`outputs/masonry_grating/brick_formats.json`. All **read**.

| format | work size (mm) | joint | course pitch | stretcher pitch |
|---|---|---|---|---|
| UK standard metric | 215 x 102.5 x 65 | 10 | 75 | 225 |
| Waalformaat | 210 x 100 x 50 | 10 | 60 | 220 |
| Waaldikformaat | 210 x 100 x 65 | 10 | 75 | 220 |
| Belgian module M50 | 188 x 88 x 48 | 12 | 60 | 200 |
| Belgian module M65 | 188 x 88 x 63 | 12 | 75 | 200 |

`ROUGHNESS.md` and `DECISIONS.md` both quote 75 mm as the course pitch and flag
that the Belgian figure was unverified. It is now verified and it is different.
Waalformaat, which is what a Ghent facade is built from, is on a 60 mm course
under the 10 mm joint convention and 62.5 mm under the 12.5 mm convention that
Wienerberger NL states and that a measured 1920s Dutch facade returns. The
Belgian module names are height classes and not pitches: M65 units are 63 mm
high, not 65, and with the Belgian traditional 12 mm joint they land on a 75 mm
course and a 200 mm stretcher. So M65 shares the British vertical grating on a
completely different horizontal one, and the two cannot be substituted.

Three further corrections to what this repository previously recorded, all
**read**.

- **The EN 771-1 tolerance classes are square-root-of-nominal formulas, not fixed
  triples.** T1 is `max(0.40 sqrt(d), 3)`, T2 is `max(0.25 sqrt(d), 2)`, R1 is
  `0.6 sqrt(d)` and R2 is `0.3 sqrt(d)`, with `d` the nominal dimension in
  millimetres. The familiar 6, 4, 3 and 9, 6, 5 are those formulas evaluated for
  the 215 by 102.5 by 65 unit. A 50 mm Waalformaat unit carries an R1 height
  range of 4 mm, not 5.
- **Belgium states no recess depth.** Buildwise TV 297 of April 2025 names and
  illustrates the *verdiepte voeg* and gives no depth in millimetres anywhere in
  32 pages. The Dutch KNB infoblad 28 does: 5 mm is routine, deeper than 5 mm
  should be *doorstrijkwerk* instead, the absolute maximum is 15 mm on a 100 mm
  unit, and a raked joint should be cut square so its depth equals its width.
  The 4 mm cap this repository previously attributed to the UK Brick Development
  Association could not be verified against any retrievable document and should
  be treated as unsourced.
- **Wall flatness is 8 mm under a 2 m straightedge**, Buildwise TV 297 annex B,
  not the 3 mm that gets quoted, which is a plastering tolerance. At 28 GHz a 2 m
  wander of 8 mm is a geometry error for the tracer, not a roughness.

The one quantity the standards do not give is the face-plane offset of a laid
unit, because a bricklayer works to a face line and the standard bounds the unit
rather than the workmanship. Reading the R1 range class on the unit width as an
expected range of ten normal draws, through the control-chart constant
`d_2 = 3.078`, gives `sigma = 1.97 mm` for the UK unit. **That inversion is
performed here and is not a published equivalence**, so it estimates the scatter
a compliant batch may carry rather than measuring any batch. It is used as the
default and swept from 0 to 5 mm.

## The specular law

**Computed.** The elevation is a two-level height field: a fraction `f` of it is
mortar sitting `d` behind the face, the rest is brick face scattered about the
plane with standard deviation `sigma`. The specular amplitude is the area average
of the two, so the share of the flat-wall specular power a brick wall keeps is

```
eta_spec / eta_flat = | (1 - f) exp(-psi^2 sigma^2 / 2) + f exp(-i psi d) |^2
```

with `psi = 2 k0 cos(theta)`. This is the zero order of the Kirchhoff solve
rather than an approximation to it, and it is verified against the full solve to
one part in 1e9 over 160 combinations of band, incidence, recess and tolerance in
`tests/test_kirchhoff.py`.

Two things about it are worth stating plainly.

**The second term is periodic, not decaying.** A joint recess costs the wall
nothing at all when the round trip through it is a whole wavelength, and costs
the most when the round trip is half of one. At 28 GHz and normal incidence a
5.36 mm recess is invisible in the specular direction however deep the groove
looks, and a 2.68 mm recess takes the specular power down to `(1 - 2f)^2`, which
for UK brickwork is 0.43. No RMS height, Gaussian or otherwise, produces a
non-monotonic dependence on relief depth. This is the sharpest reason a fitted
scattering coefficient will not transfer between bands.

**Every symbol comes from a construction document.** `f` from the format and the
joint width, `d` from the pointing specification, `sigma` from the tolerance
class. Nothing is fitted and nothing is measured by radio.

### The effective RMS height, derived

**Computed.** Expanding the specular law to second order in `psi d` and first
order in `psi sigma` and matching it to `exp(-g^2)` gives

```
s^2 = f (1 - f) d^2 + (1 - f) sigma^2
```

This is the quantity that the entire effective-roughness literature fits. Here it
falls out of the joint recess weighted by the mortar area fraction plus the unit
scatter weighted by the brick area fraction. Confirmed numerically to three
digits: inverting the computed specular loss at 10 GHz over all incidences
returns 1.78 to 1.89 mm for a flush wall with the R1 tolerance against a
predicted 1.79, and 1.77 to 1.80 mm for a 5 mm recess with no tolerance at all
against a predicted 1.89, and 2.60 to 2.71 mm for both together against a
predicted 2.60.

| wall | `f` | `d` (mm) | `sigma` (mm) | `s` (mm) |
|---|---|---|---|---|
| UK standard metric, flush | 0.172 | 0 | 1.97 | 1.80 |
| UK standard metric, 5 mm recess | 0.172 | 5 | 1.97 | 2.60 |
| UK standard metric, 10 mm recess | 0.172 | 10 | 1.97 | 4.18 |
| Waalformaat, flush | 0.205 | 0 | 1.95 | 1.74 |
| Waalformaat, 5 mm recess | 0.205 | 5 | 1.95 | 2.66 |
| Belgian M65, flush | 0.210 | 0 | 1.83 | 1.62 |
| Belgian M65, 5 mm recess | 0.210 | 5 | 1.83 | 2.61 |

**The reconciliation with Landron.** Landron, Feuerstein and Rappaport report
`sigma_h = 0.5 cm` and a maximum roughness height of 1.3 cm for a real brick
wall, with the method unstated (**read**). Solving the expression above for the
recess that reproduces 5 mm gives 12.4 mm (**computed**), which sits inside the
15 mm absolute maximum KNB infoblad 28 allows and is consistent with a 1.3 cm
maximum height. A 1996 radio field characterisation and a Dutch pointing
guideline therefore agree to within the width of the guidance, by unrelated
routes, with nothing fitted between them. That is the strongest external check
this work has.

### Where the Gaussian equivalence stops applying

**Computed.** The expansion holds while `2 k0 d cos(theta)` stays below about
two, that is `d < lambda / (2 pi cos theta)`. At normal incidence:

| band | largest recess with a valid equivalent height |
|---|---|
| 7 GHz | 6.8 mm |
| 10 GHz | 4.8 mm |
| 15 GHz | 3.2 mm |
| 28 GHz | 1.7 mm |
| 40 GHz | 1.2 mm |

So a 5 mm recess is describable by an effective RMS height through most of FR3
and not at FR2, which is exactly the band the effective-roughness literature is
usually applied in. Above the limit the recess term oscillates and the inverted
height wanders: the same wall returns 2.6 to 2.8 mm across all of FR3 and every
incidence, and 1.1 to 2.8 mm across FR2 depending on where the interference
lands.

## The mechanism, settled

`ROUGHNESS.md` left two candidates open. The calculation separates them cleanly,
because the joint can be given a recess with no dielectric contrast or a contrast
with no recess.

**Computed** at 10 GHz and normal incidence, UK brickwork, no disorder, where a
groove is 5 mm deep in a 10 mm joint, an aspect ratio of one half, which is where
the rigorous ladder puts the phase screen's checked envelope:

| joint | specular kept | comb / specular |
|---|---|---|
| flush, mortar = brick (3.91) | 1.000 | 0 |
| flush, mortar 4.5 | 1.033 | 0.0005 |
| flush, mortar 5.5 | 1.079 | 0.0028 |
| flush, mortar 7.0 | 1.133 | 0.0073 |
| 2 mm recess, mortar = brick | 0.906 | 0.036 |
| 5 mm recess, mortar = brick | 0.573 | 0.270 |

Even a mortar permittivity of 7 against brick's 3.91, which is far outside
anything measured, puts 0.7 percent of the specular power into the comb. A 5 mm
recess puts 27 percent, thirty-seven times more, and a 2 mm recess still puts five
times more. The measured contrast is far smaller than the extreme case tested:
air-dry fired-clay brick is 3.06 from 30 units over 1 to 6 GHz and air-dry cement
mortar is 3.41 by stripline over 0.5 to 2.5 GHz, an 11 percent difference (both
**read**, sources in `outputs/masonry_grating/mortar_permittivity.json`). At that
contrast the joint grid is invisible.

Note the specular column for the flush rows: a mortar more reflective than the
brick raises the wall's specular return above the brick-only Fresnel reference
rather than lowering it. The dielectric contrast is not a loss mechanism at all.

**The joint grid scatters through its geometry, not through its dielectric.**
That is worth banking, because it means the missing mortar row in ITU-R P.2040
does not matter for scattering, only for transmission, and because it makes the
model depend on a pointing specification that a photograph can sometimes resolve
rather than on a material constant that it never can.

A side note from the same table: ITU's brick permittivity of 3.91 is not a dry
brick. Air-dry measures 3.06 and 9 percent moisture by mass measures 6.10, so
3.91 sits between the 3 and 5 percent moisture points. Anyone using `itu_brick`
is modelling a slightly damp wall (**read**).

## The comb

**Computed.** Order directions are fixed by the lattice and the wavelength and
nothing about the material can move them. For UK brickwork in running bond, whose
rectangular computational cell is 225 by 150 mm:

| band | propagating orders at normal incidence | median separation |
|---|---|---|
| 7 GHz | 61 | 11.7 deg |
| 10 GHz | 117 | 8.4 deg |
| 15 GHz | 269 | 5.7 deg |
| 24 GHz | 669 | 3.6 deg |
| 28 GHz | 919 | 3.1 deg |
| 40 GHz | 1889 | 2.2 deg |

The collapse across FR3 is the physically interesting transition the sweep was
built to find. At 7 GHz there are 61 teeth spaced 12 degrees apart, which any
instrument resolves. At 40 GHz there are 1889 spaced 2.2 degrees apart.

**The bond redistributes the comb without changing how much power leaves the
specular direction.** Stack and running bond give identical specular and identical
total comb power to four decimals, because the total is a Parseval sum over the
joint mask and depends only on its area, while the running bond's extra
half-integer orders take power from the integer ones. Flemish bond has 1387
orders at 28 GHz against 919, because its repeat is a stretcher plus a header.
English bond differs in energy as well, because header courses raise the mortar
area fraction. So the bond is worth carrying if the angular pattern matters and
is not worth carrying if only the specular and diffuse split does.

**Lateral disorder attacks the comb from the outside in.** A unit displaced
sideways changes the phase of order `m` by `dk_x eps`, which is proportional to
the order index, so the specular order is exactly untouched, low orders are
barely touched and high orders die first. A 2 mm lateral jitter removes about 15
percent of the comb power at 28 GHz and moves it to the pedestal. Piston
disorder does the opposite: it attenuates every order including the specular one,
which is the Ament mechanism.

## The pedestal, which is not Lambertian and not directive

**Computed.** The power that disorder takes out of the comb does not spread
uniformly. It reappears with the angular shape of a single brick face, because
that is the object whose position and height were randomised, and a brick face is
a rectangle of known size. Its transform is a two-dimensional sinc centred on the
specular direction with widths `lambda / L` and `lambda / H`:

| band | width along the wall | width up it |
|---|---|---|
| 7 GHz | 11.4 deg | 37.8 deg |
| 28 GHz | 2.9 deg | 9.4 deg |

This is a real and awkward result for the conventional model. The smooth part of
a brick wall's scattering is a lobe centred on specular whose width is set by the
brick dimensions, so it is neither Lambertian, which Koivumaki found fitted best
on real facades, nor a directive lobe with a fitted exponent, which Charbonnier
and NYURay both use. Its shape is as derivable from the construction standard as
the comb is. At 28 GHz it is narrow enough that a receiver with a 10 degree beam
would count most of it as specular.

**One caveat on this, and it is not small.** The pedestal is built from the same
single-unit aperture transform that the coherent orders are built from, so it
inherits the phase screen's inability to send power backwards. The rigorous
comparison below finds the phase screen 5.4 dB low on backscattered orders, so
the pedestal computed here is almost certainly too narrow and too
forward-leaning. What survives without qualification is that its width is set by
the unit dimensions rather than by a fitted exponent. How much sits behind the
wall normal needs a rigorous solve, and the rigorous solve says the answer is
"much more than the phase screen thinks".

Power split of the total reflected power, UK brickwork with a 5 mm recess and the
R1 tolerance, TE (**computed**):

| GHz | incidence | specular | comb | pedestal | comb as share of diffuse |
|---|---|---|---|---|---|
| 7 | 0 | 0.690 | 0.060 | 0.250 | 19% |
| 7 | 60 | 0.927 | 0.018 | 0.056 | 24% |
| 10 | 0 | 0.362 | 0.158 | 0.481 | 25% |
| 15 | 0 | 0.053 | 0.225 | 0.721 | 24% |
| 28 | 0 | 0.053 | 0.108 | 0.839 | 11% |
| 28 | 60 | 0.081 | 0.226 | 0.693 | 25% |
| 40 | 0 | 0.030 | 0.127 | 0.842 | 13% |

Every row of that table is inside the phase screen's checked envelope, because a
5 mm recess in a 10 mm joint is aspect one half at any frequency. The residual
uncertainty is the 11 percent on the specular and the factor of 1.9 on the
diffuse that the rigorous ladder measured, not a regime question.

The diffuse share at 28 GHz comes out at 95 percent of reflected power in this
calculation, against the roughly 20 percent of *received* power that Charbonnier
and co-workers measured in a 28 GHz urban campaign. Those are not the same
quantity and should not be compared directly even setting the validity question
aside: a campaign integrates over a link budget in which the line of sight and
the specular paths dominate the total, and its instrument counts the narrow
pedestal as specular. The comparison that can be made is the trend, and the trend
is that facade scattering at FR2 is dominated by non-specular return, which is
what the campaign found.

## Comb or lobe: the answer depends on the instrument, and it is measurable

This was the question the whole exercise existed to settle, and the answer is not
the binary the brief anticipated.

**Computed.** `bistatic_map` renders the comb and the pedestal on one
direction-cosine grid, gives every order the angular width a finite illuminated
patch would give it, then blurs by a receiver beam. The metric is the ripple of
the result about its own smooth trend, taken as ten times the 10th-to-90th
percentile spread of the log ratio against a copy of itself blurred over 1.5
order spacings. It measures local structure at the order spacing and ignores the
overall fall-off towards the horizon. Zero decibels is a featureless lobe.

Illuminated patch 2 m, UK brickwork, 5 mm recess. The first column is the finite
patch alone with no receiver beam, which works out at 0.86 degrees at 10 GHz and
0.38 degrees at 28 GHz, the latter limited by the rendering grid rather than by
the patch. Effective resolutions per case are recorded in
`outputs/masonry_grating/maps.json`.

| GHz | incidence | piston sigma | order spacing | patch limit | 1 deg | 3 deg | 5 deg | 10 deg |
|---|---|---|---|---|---|---|---|---|
| 10 | 30 | 0 | 8.5 deg | 70.4 | 70.8 | 20.0 | 15.0 | 9.0 |
| 10 | 30 | 1.97 mm | 8.5 deg | 28.2 | 22.5 | 16.4 | 13.3 | 8.9 |
| 10 | 30 | 5.00 mm | 8.5 deg | 27.1 | 20.7 | 15.6 | 12.5 | 9.0 |
| 10 | 60 | 1.97 mm | 8.5 deg | 27.0 | 21.4 | 14.8 | 12.1 | 9.4 |
| 28 | 30 | 0 | 3.1 deg | 61.3 | 21.9 | 10.2 | 6.2 | 2.5 |
| 28 | 30 | 1.97 mm | 3.1 deg | 25.9 | 14.0 | 8.7 | 5.6 | 2.3 |
| 28 | 60 | 1.97 mm | 3.1 deg | 26.0 | 12.3 | 5.0 | 3.5 | 2.0 |

Four readings.

**The ripple metric is the most robust number in this document.** What it
measures is where the structure sits and how sharp it is, and both are fixed by
the lattice and the illuminated patch rather than by the groove depth or the
material. Order directions are exact in any method, so the only thing the solver
choice can move is how much power sits in each tooth.

**Realistic manufacturing tolerance does not destroy the comb, it caps it.** The
ripple falls from 70 dB to 28 dB when the R1 tolerance is applied and then barely
moves when the tolerance is more than doubled to 5 mm. The comb loses power to
the pedestal but the teeth stay where they are, because tolerance is a position
and height scatter and not a change of period. The 70 dB entries are not
meaningful as a magnitude, since with no disorder the floor between orders is
empty and the ratio is limited by the grid, but the fall to 28 dB and the plateau
after it are.

**The band decides how hard the measurement is, and FR3 is easy.** At 10 GHz the
comb carries 13 to 16 dB of structure through a 3 to 5 degree beam and still 9 dB
through a 10 degree beam, which is an ordinary horn. At 28 GHz the same beams
leave 3.5 to 8.7 dB and 2.0 to 2.3 dB. For scale, the one genuinely
angle-resolved bistatic dataset available, Yoshino's 1 degree scan at 100 and
300 GHz, shows about 2 dB rms of wing ripple on a smooth aluminium control, so
2 dB is the instrumental floor of that class of measurement (**read**, digitised
by the literature leg into `outputs/masonry_grating/bistatic_validation.json`).

**At FR2 with a 10 degree beam the comb is at the noise floor, and that is the
resolution of a typical horn.** So the reason nobody has reported it is not that
it is absent. It is that the millimetre-wave campaigns which would have found it
use beams as wide as the structure they are looking for, and the FR3 band where
an ordinary instrument would see it plainly has not been scanned bistatically on
masonry at all.

### The literature is consistent with this and nobody has looked

Assembled by the validation leg, all **read**.

- **Savov and Herben, IEEE Trans. Antennas Propag. 51(9), 2003**, predicted
  Floquet mode scattering from a periodic brick wall and closed by saying
  additional measurements are needed. As far as this study can tell none were
  made at millimetre wave. The present work is the numerical settling of a
  twenty-three year old prediction, not its first statement, and should be framed
  that way.
- **Recommendation ITU-R P.2040 section 2.3**, the only part of that
  Recommendation that models scattering from a building surface, already models a
  facade as a periodic array of cylinders and indexes its answer by diffraction
  order through the grating equation. The formulation appears to be an uncredited
  restatement of Toyama and Yasumoto, PIER 52, 2005. The ITU's own facade
  scattering model is periodic and deterministic, and it carries no validation
  against a real wall.
- **Li et al., arXiv:2602.24029, February 2026**, measured a periodic pine plate
  at a wavelength-to-period ratio of 0.129, essentially a brick course pitch at
  28 GHz, and saw an off-axis side lobe that moves by about 2 degrees when the
  period goes from 13 to 17 mm, matching the grating equation. The same paper
  carries two negatives that matter as much: the same material in reflection off
  a large plate showed only a clean specular lobe, and a curtain with a 25 cm
  period showed no stable orders. The controlling variable is how many periods
  are coherently illuminated and how much the period itself jitters, which is
  precisely the distinction between the lateral disorder term and the piston term
  above.
- **The NIST and Bologna preprint arXiv:2605.31267** observes that the
  small-scale fading it filters out of its facade scattering measurements
  oscillates faster as the off-specular angle grows, at a rate set by a path
  length difference in wavelengths, and states that it "can not be reliably
  filtered using a fixed angular window". It then averages it away as speckle.
  A ripple whose rate is locked to off-specular angle is a grating signature, not
  zero-mean noise.
- **Pascual-Garcia et al., IEEE Access 4:688-701, 2016**, swept a real brick wall
  at 57 to 66 GHz with a 3.5 degree lens beam at about 0.6 degree raw steps, then
  published the result through an eleven-point boxcar spanning 5 degrees. The
  course pitch comb at those frequencies is spaced about 4 degrees. The smoothing
  window is almost exactly matched to erase it. If the raw traces still exist
  they settle the question outright, and asking for them is the cheapest possible
  next step.

The pattern is consistent. Angle-resolved measurements on real jointed masonry do
exist. None has been published unsmoothed.

## Figures

Drawn by `plot_masonry_grating.py` into `outputs/masonry_grating/figures`, in the
repository's monograph style, IEEE two column width.

- **`masonry_bistatic_spectrum`**. The object of the whole exercise: the
  efficiency of every propagating in-plane order at 10 and 28 GHz, rigorous
  coupled wave analysis as stems, the Kirchhoff phase screen overlaid as
  crosses. Order positions are exact in both methods, so any separation between
  the two marks is the approximation error and nothing else. Read the backscatter
  half of the 28 GHz panel: that gap is the monostatic constraint below.
- **`masonry_convergence`**. What the rigorous answer does as the Fourier
  truncation grows, with the wall clock of each level beside it. The truncation
  is the only free parameter of a rigorous solve, so this is the figure that says
  whether the numbers above are converged rather than merely expensive.
- **`masonry_comb_vs_resolution`**. A cut through the bistatic response at three
  receiver resolutions. This is the comb-or-lobe answer in one picture: sharp
  comb, partly resolved comb, featureless lobe, from the same wall.
- **`masonry_specular_law`**. The closed-form specular law against incidence for
  four joint recesses at two bands, showing the non-monotonic 28 GHz behaviour
  that no Gaussian roughness model can produce, and the prediction against the two
  published measurements of real brick walls. Filled markers carry no fitted
  parameter. The open markers are the one fitted variant in this study, the
  recess and unit scatter inverted from the 28 GHz points, and the gap between
  filled and open is the whole of the Dillard disagreement.

## Validation ladder

**Analytic limits, all in the test suite.**

- A flat wall with no relief and no dielectric contrast returns the Fresnel
  coefficient exactly and puts nothing in any other order, in both polarisations,
  in both solvers.
- RCWA reproduces the half-space Fresnel coefficient to 2.4e-13 and the
  two-interface slab to 1e-9, and conserves energy to 2e-3 on a lossless
  patterned grating.
- The grating equation is reproduced by both solvers and by the closed form in
  `floquet.py`, which agree on order directions to 1e-12.
- **Shrinking the joint grid to nothing recovers the Ament factor exactly.** With
  20 micrometre joints and Gaussian piston disorder, the derived specular
  retention matches `exp(-g^2)` to better than 1.2 percent over three tolerance
  values and two incidences. This is the load-bearing limit, because it shows the
  first-principles construction reduces to the fitted model of the literature in
  the regime where the fitted model should be right.
- **The mortar grid holds specular power that the Ament factor gives away.** A
  real joint grid does not move, so a wall retains more specular power than an
  equally scattered homogeneous surface. The gap is exactly the mortar area
  fraction, and the closed form predicts it.

**Is the rigorous solve converged, or merely large?** A rigorous method has one
free parameter, the Fourier truncation, so this has to be answered with a curve
rather than an order count. At 28 GHz, 30 degrees, a 5 mm recess and the stack
bond cell, with the truncation expressed as a multiple of the smallest reach that
contains every propagating order:

| reach | retained orders | matrix | specular | diffuse | wall clock | peak memory |
|---|---|---|---|---|---|---|
| 0.50 | 293 | 586 | 0.11409 | 0.01584 | 1 s | 0.2 GiB |
| 0.75 | 593 | 1186 | 0.10517 | 0.02314 | 5 s | 0.7 GiB |
| 1.00 | 1091 | 2182 | 0.10902 | 0.01778 | 26 s | 2.3 GiB |
| 1.25 | 1745 | 3490 | 0.11046 | 0.01623 | 96 s | 5.7 GiB |
| 1.50 | 2397 | 4794 | 0.10980 | 0.01707 | 333 s | 10.7 GiB |

The propagating order count in that table saturates at 458 from reach 1.0
upwards, against the 462 the area of the visible disc predicts, so the elliptic
truncation is retaining every order that carries power and the remaining
convergence is entirely in the evanescent tail. That is the check that the
economy below is an economy and not a silent approximation.

**The specular order is converged and the diffuse total is converged to about six
percent.** From reach 1.0 upwards the specular sits at 0.1098 within 0.6 percent.
The diffuse oscillates between 0.0162 and 0.0178 with no monotone trend, which is
the expected behaviour of a Fourier method on a permittivity with a step
discontinuity, so it should be quoted with a six percent bar rather than to three
figures. Every diffuse number in this document carries that bar.

**The cost is what a dense modal method costs.** Time is cubic in the retained
order count, 333 seconds against 1 second for an eight-fold increase in orders,
and peak memory is quadratic, 10.7 GiB against 0.2 GiB. Peak resident memory
comes out at 32 times one dense scattering matrix, which is a fixed number of
copies: the eigen decomposition, the LAPACK workspace, the layer inverses and the
Redheffer products are all the same size. That constant is measured and is what
`run_masonry_spectrum.py` uses to decide whether a level fits in its budget.

**Two economies make this affordable and one of them is not free.** The retained
harmonic set is truncated to an ellipse rather than a box, which drops the corner
orders, the most deeply evanescent in the set. That is 30 percent fewer modes at
equal reach, half the memory and less than half the time, and the answer moves by
0.08 percent on the specular and 0.23 percent on the diffuse at the truncations
used here, with the agreement improving as the truncation grows. The second
economy is that a uniform substrate is recognised as uniform and solved
analytically, which removes one eigen decomposition of two whenever mortar and
brick are given the same permittivity. Neither is an approximation to the
physics, and the elliptic truncation is checked against the box in the test
suite rather than assumed.

**RCWA against the phase screen, and the validity boundary it exposes.** The
comparison is in `outputs/masonry_grating/rcwa.json`. Lossless brick at 3.91,
running bond, TE unless stated. The RCWA runs used enough harmonics to cover
every propagating order plus two, which the convergence curve above places at
reach 1.0, where the specular is already within one percent of converged and the
diffuse is inside its six percent bar.

All joints are 10 mm wide, so the recess column is also the groove aspect ratio.
Lossless brick at 3.91, TE unless stated. Rows marked converged use the elliptic
truncation at 1.25 times the propagating reach, which the curve above justifies.
The rest are at reach 1.0, where the specular is inside one percent of converged.

| GHz | incidence | recess | aspect | rigorous specular | phase screen | error | rigorous diffuse | phase screen | ratio |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 0 | 0 mm | 0 | 0.10779 | 0.10779 | 0% | 0 | 0 | - |
| 10 | 30 | 0 mm | 0 | 0.14199 | 0.14199 | 0% | 0 | 0 | - |
| 10 | 60 | 0 mm | 0 | 0.31472 | 0.31472 | 0% | 0 | 0 | - |
| 7 | 30 | 5 mm | 0.5 | 0.10444 | 0.11356 | +8.7% | 0.00790 | 0.00587 | 0.74 |
| 10 | 0 | 5 mm | 0.5 | 0.05947 | 0.06173 | +3.8% | 0.02137 | 0.01667 | 0.78 |
| 10 | 30 | 5 mm | 0.5 | 0.08932 | 0.09180 | +2.8% | 0.02036 | 0.01644 | 0.81 |
| 10 | 30 | 5 mm, TM | 0.5 | 0.05154 | 0.04997 | -3.0% | 0.01073 | 0.00891 | 0.83 |
| 10 | 60 | 5 mm | 0.5 | 0.25281 | 0.26987 | +6.7% | 0.00905 | 0.01720 | 1.90 |
| 15 | 45 | 5 mm | 0.5 | 0.12202 | 0.10805 | -11.4% | 0.02935 | 0.04185 | 1.43 |
| 28 | 30 | 5 mm | 0.5 | 0.11046 | 0.11616 | +5.2% | 0.01623 | 0.02548 | 1.57 |
| **28** | **60** | **5 mm** | **0.5** | **0.20910** | **0.13746** | **-34.3%** | **0.04201** | **0.10194** | **2.43** |
| 10 | 0 | 10 mm | 1.0 | 0.08586 | 0.06185 | -28.0% | 0.00798 | 0.02212 | 2.77 |
| 10 | 30 | 10 mm | 1.0 | 0.10154 | 0.06589 | -35.1% | 0.01351 | 0.02868 | 2.12 |
| 10 | 60 | 10 mm | 1.0 | 0.23386 | 0.18024 | -22.9% | 0.00907 | 0.04256 | 4.69 |

**The phase screen has two separate failure modes and only one of them is about
the groove depth.** An earlier draft read the boundary as a groove aspect ratio
alone, on the strength of the ten aspect-zero and aspect-half rows. The bold row
refutes that and is kept in place rather than quietly replaced, because the wrong
rule would have licensed the cheap solver at exactly the geometry a street canyon
presents.

- **Flush joint: exact.** Both solvers return the Fresnel coefficient and nothing
  else, which is the analytic limit rather than a coincidence.
- **Failure one, a deep groove.** At aspect one the specular is 23 to 35 percent
  low and the diffuse 2 to 5 times high, at every frequency and angle tested. A
  groove is a waveguide stub, and what decides whether the field reaches its
  floor is depth against width. A phase screen assumes it always does.
- **Failure two, grazing incidence at FR2.** At 28 GHz and 60 degrees, aspect one
  half, the specular is 34 percent low and the diffuse 2.4 times high, as bad as
  a deep groove. That case was run through its own truncation ladder to rule out
  a numerical cause: 0.2317, 0.1959, 0.2108 and 0.2091 at 435, 937, 1745 and 2653
  retained orders, so the rigorous specular settles near 0.210 and the phase
  screen's 0.1375 is not a convergence artefact. At 10 GHz and 60 degrees the identical geometry is fine to 7
  percent. The difference is shadowing: at 60 degrees the groove floor is
  obscured over `d tan(theta)`, which is 8.7 mm of a 10 mm joint, and at 28 GHz
  the wave resolves that shadow while at 10 GHz, where the joint is a third of a
  wavelength wide, it does not. A phase screen contains no shadowing at all.

**The usable envelope of the cheap solver is therefore aspect at or below one
half AND incidence at or below about 45 degrees at FR2**, where the specular
agrees within 11 percent and the diffuse within a factor of 1.6. Outside it the
specular error reaches 35 percent with a consistent sign, too little specular,
and the diffuse is too high by a factor of 2 to 5. `phase_screen_recess_limit_m`
returns the aspect half of that envelope. The incidence half is not encoded in
the library and has to be carried by the caller, which is a gap worth closing.

The consequence for this document is bounded and specific. The sweep's grazing
columns at FR2, which are the street canyon case, over-count diffuse power by
about a factor of two and under-count specular by about a third. The FR3 sweep
and the FR2 sweep below 45 degrees stand.

One caveat on the diffuse column. Its own convergence bar is six percent, so
differences between the two solvers below about ten percent are not resolvable
and the entries should be read as a factor rather than a percentage. The diffuse
error also has no consistent sign at aspect one half, so unlike the specular it
cannot be corrected, only bounded.

One further result is worth stating separately because it looks like a bug and is
not. The total power a grooved wall reflects is *less* than a flat wall reflects,
by up to 25 percent at 10 GHz. Both solvers agree on this, and for a lossless
material RCWA accounts for the difference in the transmitted orders. A recessed
joint is a partial impedance match: it couples power into the wall. So a power
budget ratio below one is physics, and only a ratio above one is a failure of the
phase screen.

### Order by order, and the consequence for the monostatic branch

Totals hide the interesting part. `masonry_bistatic_spectrum` puts every
propagating in-plane order of both solvers on one axis. The disagreement is not
spread evenly over the hemisphere and it is not the same at the two bands.
Summing the non-specular in-plane orders (**computed**, converged truncation):

| case | forward orders | backward orders | back over forward, rigorous | envelope spread, rigorous |
|---|---|---|---|---|
| 10 GHz, 30 deg, 5 mm | +3.3 dB | +2.5 dB | 1.19 | 1.2 dB |
| 10 GHz, 30 deg, 10 mm | +6.2 dB | +5.1 dB | 1.22 | 0.4 dB |
| 28 GHz, 30 deg, 5 mm | +2.1 dB | -5.4 dB | 0.47 | 5.0 dB |
| 28 GHz, 60 deg, 5 mm | +9.6 dB | -0.8 dB | 0.53 | 6.0 dB |

The first two columns are the phase screen against the rigorous solve. Two things
follow.

**The rigorous envelope is nearly isotropic, and that settles a question in the
fitted literature.** At 10 GHz the order efficiencies vary by 1.2 dB from the
10th to the 90th percentile across the whole hemisphere, minus 78 to plus 78
degrees, and backscatter slightly exceeds forward scatter. At 28 GHz the spread
is 5 to 6 dB and backscatter is still half the forward power. A comb on an almost
flat envelope is a Lambertian pedestal, not a directive lobe with an exponent of
3 or 10. Koivumaki and co-workers fitted whole facades at 28 GHz, found
Lambertian beat directive because backscatter was as strong as forward scatter,
and attributed it to pillars, protruding windows and street furniture. **The
brickwork alone produces it**, with no street furniture anywhere in the model.

**The phase screen must not be used for the monostatic branch of this study.**
This is a design constraint on another part of the project, so it is stated with
numbers. At 28 GHz and 30 degrees incidence the rigorous backscattered orders sit
on a floor near -41.5 dB, essentially flat from -30 to -78 degrees, while the
phase screen falls away steeply behind the normal:

| scattered angle | rigorous | phase screen | gap |
|---|---|---|---|
| -30.0 deg | -42.0 dB | -58.7 dB | 16.7 dB |
| -33.2 deg | -41.9 dB | -68.2 dB | 26.4 dB |
| -36.5 deg | -41.7 dB | -68.2 dB | 26.5 dB |
| -39.9 deg | -41.6 dB | -58.8 dB | 17.1 dB |
| -43.6 deg | -41.4 dB | -54.5 dB | 13.1 dB |

The cause is structural, not numerical. A phase screen replaces the surface field
by the incident field times a local plane-interface reflection coefficient, which
can redirect power but cannot send it back the way it came. Backscatter from a
grooved surface comes from the groove walls and the arris of every unit, through
double bounce and edge diffraction, and a phase screen contains neither. RCWA
contains both.

The monostatic estimator depends on exactly this quantity. **A Kirchhoff or
phase-screen surface model will under-predict the monostatic return from
brickwork by 13 to 27 dB at FR2**, which is not a correctable bias because it
varies by 13 dB across a 14 degree span. Forward and specular directions are fine
to 2 dB and FR3 is fine to 3 dB in both directions, so the restriction is
specific: rigorous solves, or a lookup table built from them, for anything
monostatic at FR2.

The same table puts a direction on every diffuse number in the Kirchhoff sweep:
forward scatter is over-counted by about 2 dB at 28 GHz and 10 dB at grazing,
backscatter is under-counted by about 5 dB, so the sweep's angular distribution
is too forward-leaning even where its total is close.

### Against published measurements of real brick walls

Two datasets exist, both **read**, both specular-only, so neither can confirm or
refute the comb. They can test the specular law, and the prediction put to them is
parameter-free: the mortar area fraction, the joint recess and the unit scatter
all come from construction standards and nothing was adjusted. Residuals in
decibels, prediction against measurement, from
`outputs/masonry_grating/validation.json`:

| dataset | model variant | median | rms | worst |
|---|---|---|---|---|
| Landron 1996, brick, 4 GHz, TE, 13 points | flat wall | +1.07 | 2.27 | +5.06 |
| | flush plus R1 scatter | +0.68 | 2.13 | +4.87 |
| | 5 mm recess plus R1 scatter | +0.28 | 2.01 | +4.65 |
| | 10 mm recess plus R1 scatter | -0.68 | 1.90 | +4.00 |
| Dillard 2003, brick, 28 GHz, TE, 6 points, repeat scatter 10 to 18 dB | flat wall | +7.93 | 7.76 | +10.63 |
| | flush plus R1 scatter | -3.75 | 4.52 | -7.26 |
| | 5 mm recess plus R1 scatter | -4.81 | 8.15 | -13.40 |
| | 10 mm recess plus R1 scatter | -4.20 | 8.03 | -13.14 |

**Landron at 4 GHz is a pass.** The default preset lands at +0.28 dB median and
2.01 dB rms against a dataset whose own point-to-point scatter at a single
incidence angle is about 2 dB and whose digitisation error is 0.015 in reflection
magnitude. The improvement over a flat wall is real but small, +1.07 to +0.28 dB
median, because at 4 GHz a 5 mm recess is a fourteenth of a wavelength and there
is not much for the model to correct.

**Dillard at 28 GHz is not a pass at the default parameters, and 28 GHz is the
band this project cares about, so the disagreement was chased rather than
reported as an rms.** It is a systematic, not scatter: every point sits below the
diagonal and the two at measured magnitude 0.4 and 0.6 are under-predicted by
about a factor of four in amplitude. The model says a real brick wall keeps far
less specular power than the measurement found.

**Result one: the disagreement is a parameter disagreement, not a form
disagreement.** Inverting the same closed form for its two geometric parameters
against all six points (**computed**):

| variant | recess | unit scatter | rms | residuals per angle, 5 to 60 deg |
|---|---|---|---|---|
| as-built default | 5.0 mm | 1.97 mm | 8.15 dB | -2.6, -2.4, -2.1, -7.1, -13.4, -12.4 |
| flush, default scatter | 0 mm | 1.97 mm | 4.52 dB | -2.4, -2.2, -1.8, -5.5, -7.3, -5.1 |
| flush, no scatter | 0 mm | 0 mm | 7.76 dB | +10.4, +10.5, +10.6, +5.5, +0.9, -0.6 |
| **inverted from the data** | **8.2 mm** | **0.90 mm** | **1.40 dB** | +0.1, +0.3, +0.8, -0.7, -1.2, -3.0 |

**Both inverted values are construction-plausible, which makes this falsifiable
rather than convenient.** An 8.2 mm rake sits inside the 15 mm absolute maximum
KNB infoblad 28 allows and close to its instruction to cut a raked joint square,
depth equal to width, which for a 10 mm joint is 10 mm. A 0.90 mm face-plane
scatter is tighter than the 1.97 mm the R1 range class permits, which is an upper
anchor rather than a measurement, and is what good workmanship on an
institutional building looks like. So the model reproduces a 28 GHz measurement
of a real brick wall to 1.4 dB rms, better than it reproduces Landron at 4 GHz,
and the prediction it makes in exchange is that the brickwork on the north face
of Lane Hall is deeply raked. Someone can go and look. Note that this variant is
a fit and is labelled as one everywhere it appears, unlike every other number in
this document.

**The inverted parameters also do not break the 4 GHz dataset, which they were
not fitted to.** Landron rms goes from 2.01 dB at the default to 1.93 dB at the
inverted geometry, so two independent field measurements seven times apart in
frequency prefer the same wall. That is weak evidence, because Landron is
insensitive to the recess at 4 GHz where 8 mm is a ninth of a wavelength, but it
is evidence in the right direction and it rules out the inversion having bought
28 GHz at the cost of 4.

**Result two: the flush hypothesis is not the answer, and that is worth knowing.**
Making the joint flush, which is what a coating, a render or weather-struck
pointing would do, only takes the rms from 8.15 to 4.52 dB. At 28 GHz the
dominant term in the default is the unit scatter, not the recess, because a 5 mm
recess is close to a whole-wave round trip at normal incidence and nearly
invisible. Removing the scatter as well over-corrects to +10.5 dB. Neither single
change reconciles the data, which is why the two-parameter inversion was needed.

**Result three: the rigorous solve moves the model towards the measurement at
exactly the angles where the residual is worst.** RCWA gives a specular
efficiency 1.82 dB above the phase screen at 28 GHz and 60 degrees, where the
default residual is -12.4 dB, and 0.22 dB below it at 30 degrees where the
residual is -7.1 dB. So roughly two decibels of the grazing residual is the cheap
solver rather than the wall. That is not enough to close it, and it is recorded
because it has the right sign.

**Result four, and it caps everything above: the measurement's own repeat scatter
is larger than the disagreement.** The open-access thesis was read in full for
this study rather than relied on through its table. Table 5.1, the six numbers
above, is not a results table. It is a cross-study trends comparison, every entry
carries a leading tilde, and it turns out to be roughly the median of Table 4.2
on page 54, which the thesis never states. Table 4.2 holds the 24 individual
measurements, four repeats per angle per material, and:

- **the four repeats at one angle span a factor of 3.3 to 8.4 in amplitude**, 10
  to 18 dB, at every angle up to 30 degrees, with standard deviations equal to or
  larger than the means, and no error bar appears anywhere in the thesis;
- the brick and limestone point clouds **overlap completely** at 5, 10, 15, 30 and
  45 degrees, and at 10 degrees the entire limestone range sits inside the brick
  range;
- the limestone target is not ashlar. The photograph shows a random-rubble Hokie
  Stone base band about 2 m tall under a large smooth panelled wall with windows,
  and with a 90 degree sector antenna that was never re-aimed, the smooth panel
  and the paving were inside the beam.

The default residual of 8.15 dB rms is smaller than the spread between repeats of
the same measurement. **There is no statistically meaningful disagreement to
explain.**

**Result five: the calibration is the whole measurement at small angles, and it
was checked twice and failed once.** The transmit and receive antennas were never
pointed at each other. Both stayed aimed at the wall and the line-of-sight and
reflected pulses were captured in one waveform, which the thesis states on page
36, so the reference voltage is a sidelobe measurement and the
`sqrt(g(theta_TX) g(theta_RX))` factor in their equation 4.1 is the entire
absolute calibration rather than a small correction. Geometrically the
line-of-sight arrives `90 - theta` off boresight, so at 5 degrees incidence the
gain has to be read 85 degrees off boresight in the skirt of a 90 degree sector
antenna whose pattern was estimated outdoors from 24 points spaced 15 degrees
apart with no manufacturer data. There is no uncertainty analysis. The thesis
does contain an accidental end to end check against an aluminium foil reflector
of known area: correct at 15 degrees, out by a factor of 0.6 in amplitude at 22.5
degrees and 2.0 at 30 degrees, blamed on wind and never repeated. **Four of the
six reported angles were never calibrated at all.**

**Result six: the 60 degree points are impossible, and they are where the
residual is worst.** At 60 degrees both materials meet or exceed the
smooth-surface Fresnel bound computed from the thesis's own Appendix A.1
permittivities, ratios of 1.01 for brick and 1.09 for limestone and up to 1.14
and 1.27 on individual points. No rough or relieved surface can exceed its own
smooth-surface reflectance. The 60 degree runs are also a different experiment,
15 to 21 m stand-off against 3 to 9 m everywhere else, and the thesis itself
calls the 45 and 60 degree limestone profiles hard to interpret because the two
pulses do not separate, while the reflection coefficient is the ratio of their
peaks.

**The verdict, stated plainly.** The 1.40 dB inversion is not a validation,
because a measurement whose repeats span a factor of eight and which cannot
resolve brick from random-rubble limestone cannot resolve a 5 mm joint recess
either. Equally, the 8.15 dB default residual is not a refutation, for the same
reason and because it is smaller than the measurement's own scatter. Dillard is
worth citing for the order of magnitude and for the monotonic rise of the
reflection coefficient with incidence angle, which this model reproduces, and not
as a calibrated benchmark. **There is no other test available at FR2. No
published measurement resolves the specular reflection of a real brick wall at
28 GHz well enough to validate or refute this model, and that is the principal
limitation of the work.** The model is validated at 4 GHz against Landron to
2.0 dB with no fitted parameter, and unvalidated at FR2. Closing that needs a
narrow-beam or vector network analyser measurement on a wall whose joint geometry
was recorded, which nobody has published.

One correction to what this document said earlier, and it matters because the
quotation is convenient. The thesis conclusion on page 47 that "limestone and
brick walls do not exhibit significant diffuse scattering" is real and rests only
on excess pulse width in the specular direction, with no off-specular measurement
anywhere in the thesis. But its abstract and section 5.4 say the opposite, that
diffuse scattering does exist for these walls at 28 GHz. **The thesis contradicts
itself and quoting only the half that suits this argument would not be honest.**
Its appendix model is also not a roughness model: it fits a phenomenological lobe
exponent to pulse duration and never measures, fits or assumes an RMS height for
either wall.

The Landron parallel-polarisation series is a separate failure with a separate
cause: every variant, including the flat wall, sits 5.4 dB rms away, because the
measured points near 60 degrees sit far above the pseudo-Brewster null that the
smooth-surface Fresnel curve predicts. Landron's own paper notes the anomaly. A
model that gets the flat case wrong cannot be tested by adding relief to it.

## What this changes for the propagation stage

**The recommendation in `ROUGHNESS.md` stands, with the numbers filled in.**
Represent the structure geometrically where the pitch is estimable. What is new
is that the effective sigma fallback is no longer an admission of defeat: it now
has a derivation, a value, and a stated validity band.

1. **Use the closed-form specular law wherever the recess and the format are
   known.** It is three multiplications, it needs no fitted parameter, and it
   gets the band dependence right where a fixed scattering coefficient cannot.
   `config/masonry_scattering.json` carries it with presets.
2. **Where only the format is known, use the derived effective RMS height** with
   the recess drawn from its distribution, and check
   `gaussian_equivalence_limit_m` before trusting it. In FR3 this is defensible.
   At FR2 it is not, and the honest move there is to carry the closed form.
3. **The semantic layer should be asked for the pointing profile, not the
   material.** Whether a joint is flush, tooled or raked is the parameter that
   decides the answer, it is visible in a street-level photograph at the
   resolution `DECISIONS.md` records, and nothing in the current concept
   catalogue asks for it. That is a concrete and cheap addition.
4. **The angular pattern is not the one Sionna implements.** Neither a Lambertian
   nor a directive lobe describes a comb sitting on a brick-sized sinc. Whether
   that matters depends on the observable: for a delay-integrated coherency
   matrix averaged over a body it probably does not, and for a single narrow
   receive beam it certainly does. This should be tested against the study's own
   observable rather than assumed either way.
5. **Two solver restrictions, both specific.** Anything monostatic at FR2 needs a
   rigorous solve or a table built from one, because a phase screen is 13 to
   27 dB low in backscatter there. And the FR2 street canyon case, grazing
   incidence on a recessed joint, needs the same, because groove shadowing makes
   the phase screen 34 percent low on the specular at 28 GHz and 60 degrees.
   Forward and specular directions below 45 degrees, and all of FR3, are fine at
   2 to 3 dB. `phase_screen_recess_limit_m` and
   `phase_screen_incidence_limit_deg` encode both bounds.
6. **Do not fold this into `SurfaceRoughnessPrior`.** That class refuses periodic
   classes on purpose and the refusal should stay. The masonry model is a
   different object with a different interface, and collapsing it into an RMS
   height is the exact loss of information this work exists to document.

## Open items

Ranked by how much they would change the answer.

1. **A bistatic scan of a wall whose joint geometry was recorded.** This is now
   the binding gap and it has two halves. No published measurement resolves the
   specular reflection of a real brick wall at 28 GHz well enough to test the
   specular law: the one that exists has repeats spanning a factor of eight and
   cannot tell brick from random-rubble limestone. And no published measurement
   anywhere looks off-specular on jointed masonry at all. A narrow-beam or vector
   network analyser scan on a wall whose pointing profile, joint width and course
   pitch were measured first would close both at once. The computed requirement
   is a beam of 3 degrees or narrower at FR2, or 10 degrees at 10 GHz, published
   unsmoothed.
2. **The raw Pascual-Garcia traces.** A real brick wall, 57 to 66 GHz, 3.5 degree
   beam, 0.6 degree steps, smoothed away at publication with an eleven-point
   boxcar spanning 5 degrees against a comb spaced about 4. This is the one
   existing dataset that could show the comb directly, and it needs an email
   rather than an anechoic chamber.
3. **Rigorous solves at FR2 grazing incidence.** The phase screen fails there by
   34 percent through groove shadowing, and the street canyon case is exactly
   there. Four more RCWA runs at 28 GHz and 60 to 80 degrees would either bound
   the error well enough to correct the sweep or establish that the sweep's
   grazing columns have to be replaced.
4. **Mortar permittivity above 20 GHz.** One paper exists, Conrat, Aliouane,
   Cousin and Begaud, measuring mortar from 2 to 260 GHz in ITU's own power-law
   form, published twice in 2024, IEEE paywalled, with an empty HAL deposit. It
   matters much less than it would have before the contrast ablation, which
   showed the dielectric is not the mechanism, which is why it is fourth.
5. **A tooled joint profile rather than a square step.** Every recess here is a
   square-cut groove because that is what KNB infoblad 28 specifies for raked
   work, but the commonest profile in Belgium is tooled concave and its effective
   relief is a guess. The model is linear enough in the profile that a measured
   cross section would propagate directly.
6. **The Belgian national annex and PTV 23-002**, both paywalled, which would
   confirm the declared tolerance class of Belgian facing brick. The current
   default of R1 is an assumption.

Two things were looked for and not found, and the absence is the finding. There
is no published bistatic scan of real jointed masonry at any millimetre-wave
frequency with the angular resolution to separate a comb from a lobe. And there
is no published inversion of a fitted scattering coefficient to a physical RMS
height, which is why the derivation above has nothing to be checked against
except Landron at 4 GHz.

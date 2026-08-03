# Surface roughness prior for outdoor building materials at millimetre wave

`config/surface_roughness.json` supplies the RMS surface height that
`semantic_twin/materials.py` refuses to default. This document says where each
number came from, how much of the table is measured against extrapolated, and
which parts of the model the literature does not support at all.

Read the provenance grades before using any number. Half of this table is an
engineering prior wearing a citation.

## Why this one number dominates the material model

The coherent share of reflected power is the Ament factor `exp(-g**2)` with the
Rayleigh roughness parameter `g = 4 pi s cos(theta) / lam`, where `s` is the RMS
surface height. At 28 GHz and normal incidence:

| RMS height `s` | specular power fraction |
|---|---|
| 0.02 mm | 0.999 |
| 0.10 mm | 0.986 |
| 0.20 mm | 0.946 |
| 0.50 mm | 0.709 |
| 0.80 mm | 0.414 |
| 1.00 mm | 0.252 |
| 2.00 mm | 0.004 |

That is a factor of 234 between 0.2 mm and 2.0 mm, and both ends of that interval
are defensible readings of "a plastered wall". Compare it with the dielectric
side, where `config/itu_p2040_4.json` carries fractional permittivity
uncertainties of 12 to 20 percent drawn from a Recommendation that at least
exists. The roughness term is the larger uncertainty by two orders of magnitude,
and until this file existed nothing in the repository supplied it.

## Incidence angle, and why a street canyon is the forgiving case

`cos(theta)` sits inside the exponent, so grazing incidence makes every surface
smoother. Specular power fraction at 28 GHz:

| `s` (mm) | 0 deg | 45 deg | 60 deg | 75 deg | 85 deg |
|---|---|---|---|---|---|
| 0.10 | 0.986 | 0.993 | 0.997 | 0.999 | 1.000 |
| 0.30 | 0.883 | 0.940 | 0.969 | 0.992 | 0.999 |
| 0.50 | 0.709 | 0.842 | 0.918 | 0.977 | 0.997 |
| 0.80 | 0.414 | 0.644 | 0.802 | 0.943 | 0.993 |
| 1.50 | 0.045 | 0.212 | 0.461 | 0.813 | 0.977 |
| 3.00 | 0.000 | 0.002 | 0.045 | 0.436 | 0.910 |
| 6.00 | 0.000 | 0.000 | 0.000 | 0.036 | 0.686 |

A 2 mm wall retains 0.4 percent of its specular power at normal incidence and 69
percent at 75 degrees. Street-level geometry in a canyon is mostly grazing on the
facades and mostly steep on the ground, so the same roughness prior lands in two
different regimes within one scene. This is why `RadioMaterialParameters` carries
a single `scattering_coefficient` at a stated `reference_incidence_deg` and why
that is a genuine approximation rather than a formality: one number cannot track
the table above.

Across bands, at 60 degrees incidence:

| `s` (mm) | 28 GHz | 39 GHz | 60 GHz |
|---|---|---|---|
| 0.10 | 0.997 | 0.993 | 0.984 |
| 0.30 | 0.969 | 0.942 | 0.867 |
| 0.50 | 0.918 | 0.846 | 0.673 |
| 0.80 | 0.802 | 0.652 | 0.363 |
| 1.50 | 0.461 | 0.222 | 0.028 |
| 3.00 | 0.045 | 0.002 | 0.000 |

## What ITU-R P.2040-4 says, and what it does not

Verified against the in-force PDF of Recommendation ITU-R P.2040-4 (09/2025),
fetched and read for this document.

- Section 3 Table 3 gives `eps' = a f^b` and `sigma = c f^d` per material. There
  is no roughness column and no RMS height. This is already implemented in
  `config/itu_p2040_4.json`.
- Section 2.2.2, the layered-slab model that Table 3 feeds, assumes smooth,
  planar, parallel interfaces. The Recommendation's reflection and transmission
  coefficients are therefore smooth-surface coefficients by construction.
- The only place P.2040-4 uses an RMS height at all is section 2.2.3.1 equation
  48, the waveguide attenuation term for corridors and tunnels, where `h1` and
  `h2` are "the root mean square roughness of the Gaussian distribution of the
  surface level". Table 2's worked example uses `h1 = 0.4` and `h2 = 0.2` in a
  6.4 m by 3.0 m underground mall, and the Recommendation does not state their
  units. Whatever the units, that term describes structural relief of a corridor
  cross section, not the finish of a facade, and equation 48 is a per-metre
  attenuation rather than a specular-diffuse split.
- Section 2.3, the one part of P.2040-4 that does model scattering from a
  building surface, opens with "The power of scattering waves varies with
  roughness of surfaces" and then defines that rough surface as "a round
  convexity array formed by locating circular cylinders periodically". Its
  machinery is lattice sums and a T-matrix, and its output is a per-mode
  reflection coefficient. In other words the ITU's own answer to a rough facade
  is a deterministic periodic model, not a Gaussian random one.

So the gap this file fills is real and it is longstanding. P.2040-3 is the same,
and Recommendation ITU-R P.1411-13 (09/2025) has no facade roughness either.

The nearest ITU anchor for the functional form is Recommendation ITU-R P.2146-0
equation 11, which gives the coherent bistatic scattering coefficient as
`4 pi |r_pp(th_i)|**2 exp{-(2 k s cos th_i)**2}`. That exponent is identically
`g**2`, and section 4.1 of P.2146-0 defines `s` there as the total RMS surface
height rather than a two-scale component, which removes the usual ambiguity.
P.2146-0 is a sea-surface Recommendation. Borrowing its functional form for a
brick wall is this repository's extrapolation and is labelled as such in
`semantic_twin/mmwave.py`.

## The three strands, and why they disagree

There are three literatures here and they do not measure the same thing. Keeping
them apart is most of the work.

### Strand one, surface metrology

Profilometry and confocal microscopy of building materials, reported as ISO 25178
`Sq` or ISO 4287 `Rq`, almost always by civil engineers or conservation
scientists with no radio context. The values are real measurements. Two traps.

`Ra` and `Sa` are arithmetic mean deviations and are not `Rq` and `Sq`. For
Gaussian heights `Rq = 1.25 Ra`. Every conversion of that kind in the table below
is shown rather than folded in silently.

The evaluation length matters more than the instrument. A 28 GHz wave responds to
lateral scales from roughly 1 mm to a few centimetres. A confocal microscope
working over a 7 mm patch, or a profilometer with a 0.8 mm cut-off, is measuring a
different and much finer band of the surface spectrum, and it truncates exactly
the part that a millimetre wave sees. Metrology values are therefore biased low
for radio purposes, and the bias is not a small correction.

### Strand two, effective roughness fitted from radio

Degli-Esposti and co-workers introduced a scattering coefficient `S`, the ratio
of the diffuse field to the incident field, fitted to measured data. Sionna
implements their directive lobe. This strand supplies most of the numbers that
propagation engineers actually use, and it is the strand most often mistaken for
a roughness measurement. `S` in this document is always that coefficient and
never a power density, which elsewhere in the project carries the same letter
with a subscript.

`S` is not a surface property. Four independent lines of evidence, all from
inside the strand:

- Kodra, Bernardi, Cenni, Hu, Barbiroli, Fuschini, Vitucci, Molina Garcia-Pardo,
  Martinez-Ingles, Salous and Degli-Esposti, IEEE Open Journal of Antennas and
  Propagation, vol. 6, no. 5, pp. 1490-1501, 2025, doi:10.1109/OJAP.2025.3587403,
  say it outright about their own flat laboratory slabs: "The main origin of
  diffuse scattering in the considered cases cannot be surface roughness since all
  three materials have similar, smooth surfaces." They attribute the diffuse power
  to volume inhomogeneity instead, which is why their fitted `S` falls with
  frequency for wood flooring and rises for plasterboard. No RMS height can do
  that.
- Koivumaki and co-workers fitted whole facades at 28 GHz and found the
  Lambertian pattern beat the directive pattern, because pillars, protruding
  windows and street furniture returned as much backscatter as forward scatter.
  Their fitted `S` across four facades of an urban square spans 0.39 to 0.82.
- Charbonnier, Lai, Tenoux, Caudill, Gougeon, Senic, Gentile, Corre, Chuang and
  Golmie, IEEE Trans. Veh. Technol., 2020, doi:10.1109/TVT.2020.3038620 (read in
  the full NIST-hosted PDF) calibrate `S` for buildings from an initial 0.35 to a
  final 0.6 at 28 GHz, with the directive exponent held at 3. Their buildings are
  OpenStreetMap footprints extruded to a floor-count height, at 1 to 2 m
  precision, so every window reveal, balcony and ledge in downtown Boulder is
  inside that 0.6. Their vehicles calibrate to `S = 1.0`, the ceiling of the
  parameter, which is only intelligible as a geometry proxy.
- Fitting the effective-roughness model to a Beckmann-Kirchhoff simulation of
  marble at 28 GHz gives `S` falling from 0.140 to 0.015 and the exponent rising
  from 5.22 to 10.50 as incidence goes from 20 to 80 degrees. A constant `S` per
  material, which is what every ray tracer stores, cannot represent that.

Two further cautions on transporting these numbers. The exponent is
kernel-dependent: the same NIST brick data fitted with two published lobe kernels
gives 5.67 and 11.33. And the exponent 3 that Charbonnier et al. use was fixed,
not fitted, from a 1.3 GHz study, and Kodra et al. fixed it the same way for the
same reason.

The spread between published mmWave ray tracers makes the point without any
argument. Charbonnier et al. calibrate buildings to `S = 0.6` at 28 GHz. NYURay
(Kanhere, Rappaport and co-workers, IEEE Trans. Antennas Propag., 2024,
arXiv:2410.03104, read in full) holds `S = 0.1` with exponent 10 fixed and
uncalibrated across 28, 73 and 142 GHz. That is a factor of six in the diffuse
field ratio, and one of the two holds it constant over a factor of five in
frequency, which no roughness model permits.

**There is no published inversion of a fitted `S` to a physical RMS height, and
this repository does not perform one.** The two quantities are not even normalised
against the same reference: `S` in the effective-roughness model is diffuse field
over *incident* field, whereas `roughness_to_scattering_coefficient` in
`semantic_twin/mmwave.py` returns the diffuse share of the *reflected* field.
They differ by the Fresnel coefficient before any physics is discussed.

### Strand three, millimetre-wave campaigns

Reflection and scattering measurements on real materials at 28 GHz and above.
This is the strand that could close the gap and mostly does not, because campaigns
report reflection loss rather than surface statistics, and the few that report
surface statistics measure them on laboratory samples.

The one clean cross-frequency result available here is an inversion, done in this
document rather than published, from NYURay's Table X. Its calibrated
angle-independent reflection losses for a brick wall are 12.8 dB at 73 GHz and
18.9 dB at 142 GHz, against a smooth-surface normal-incidence Fresnel reference of
9.68 dB computed from the ITU-R P.2040 brick permittivity of 3.91. Attributing the
excess entirely to roughness gives an implied RMS height of 0.276 mm at 73 GHz and
0.245 mm at 142 GHz. Two frequencies a factor of two apart agreeing to 12 percent
is a real consistency check on the `exp(-g**2)` scaling, and it is the strongest
support this document has for the model form.

The same inversion applied to the other outdoor rows fails, and the failures are
reported rather than dropped. Concrete gives 0.336 mm at 73 GHz and 0.120 mm at
142 GHz, because the measured loss falls with frequency, which roughness cannot
do. Granite shows no excess loss at all at 28 GHz. Outdoor glass shows less loss
than the smooth prediction at 73 GHz, which is negative excess and means the
angle-independent fit has absorbed slab interference and geometry error.

Three caveats bind this inversion and none of them is small. The calibrated loss
is fitted angle-independently across a campaign whose incidence geometry is not
stated, so taking `cos(theta) = 1` makes every implied height a lower bound: at a
more realistic 60 degrees the brick figure doubles to about 0.5 mm. The fit
absorbs the ray tracer's geometry error along with the roughness. And the ITU
reference is a lossless half-space at normal incidence, whereas a real wall is a
slab.

### Why the strands disagree

Metrology measures a sub-millimetre band of the surface spectrum and returns tens
of micrometres. Radio inversion returns a few tenths of a millimetre. Fitted `S`
returns whatever the ray tracer's geometry left over, which at 28 GHz on a real
facade is dominated by windows and ledges rather than by finish. These are three
different physical quantities that share a symbol, and the ratio between the
smallest and largest is more than an order of magnitude.

## Where the Gaussian closure itself stops being trustworthy

The specular factor is not intrinsically Gaussian. For any height distribution it
is the squared characteristic function of the heights evaluated at
`k_perp = 2 k cos(theta)`, and `exp(-g**2)` is the special case for Gaussian
heights. Alissa et al. (IEEE Access, vol. 8, pp. 170672-170680, 2020,
doi:10.1109/ACCESS.2020.3025361, read in the full open-access PDF) measured 15
real material surfaces by laser confocal microscopy against ISO 25178 and found
most of them are not Gaussian: skewness between -0.5 and 0.5 and kurtosis closer
to 2 than to 3, with wallpaper samples better fitted by a Gamma distribution.

The consequence, computed here from the closed forms in that paper's equations 13
to 17 with each distribution renormalised to the same RMS height `s`:

| `g**2` | `s` at 28 GHz, normal | Gaussian | Gamma, shape 5 | Exponential |
|---|---|---|---|---|
| 1 | 0.85 mm | 3.7e-01 | 4.0e-01 | 5.0e-01 |
| 3 | 1.48 mm | 5.0e-02 | 9.5e-02 | 2.5e-01 |
| 5.5 | 2.00 mm | 4.1e-03 | 2.4e-02 | 1.5e-01 |
| 12 | 2.95 mm | 6.1e-06 | 2.2e-03 | 7.7e-02 |
| 20 | 3.81 mm | 2.1e-09 | 3.2e-04 | 4.8e-02 |

Non-Gaussian heights decay algebraically in `g**2` where the Gaussian decays
exponentially. Below `g**2` of about 3 the shape of the height distribution is
worth less than a factor of two and can be ignored. Above it the closure becomes
the dominant modelling error, not the RMS height. Alissa et al. reach the same
split from the other direction: they conclude that the distribution assumption is
negligible "within the limits of real indoor materials" but that a Gaussian
"significantly underestimates the measured signal in the specular direction for
large values of the surface heights' standard deviation compared to the
wavelength".

`g**2 = 3` is `s = 1.48 mm` at 28 GHz normal incidence and `s = 0.69 mm` at
60 GHz. Every class in the table below whose central value exceeds that is in the
regime where `exp(-g**2)` is the wrong shape as well as an uncertain magnitude,
and the JSON marks those with `gaussian_closure_reliable: false`.

Note also a symbol collision that has already caused errors in this literature:
Alissa et al. equation 8 defines `g` as the square of the quantity this repository
calls `g`. `semantic_twin/mmwave.py` defines its own convention at first use for
exactly this reason.

## Periodic structure is not roughness

Several of the surfaces in this table have almost no random roughness and a large
deterministic one. Mortar joints, sett paving, corrugated cladding, roller
shutters, roof tiling and glazing mullions all repeat at a fixed pitch. For those,
the Rayleigh criterion is not an approximation that needs widening. It is the
wrong model, and this distinction matters more than any of the numbers below.

A surface with pitch `d` illuminated at `theta_i` reradiates into discrete orders
at `sin(theta_m) = sin(theta_i) + m lam / d`. It does not produce a broad diffuse
lobe. Counting the propagating orders at normal incidence:

| structure | pitch | orders at 28 GHz | mean spacing | orders at 60 GHz |
|---|---|---|---|---|
| brick coursing | 75 mm | 15 | 12.6 deg | 31 |
| stone sett | 100 mm | 19 | 8.3 deg | 41 |
| corrugated metal | 50 mm | 9 | 14.7 deg | 21 |
| roller shutter slat | 80 mm | 15 | 9.9 deg | 33 |
| ceramic tile | 200 mm | 37 | 4.1 deg | 81 |
| roof tile course | 320 mm | 59 | 2.6 deg | 129 |
| paving slab | 400 mm | 75 | 2.2 deg | 161 |

Two consequences for the propagation stage. The energy that a Gaussian model
would spread smoothly over the hemisphere actually arrives in a comb, so a
receiver sitting between orders sees less than the model says and one sitting on
an order sees more. And the comb is deterministic given the pitch, so it is
predictable from geometry the semantic layer can already estimate, which a random
roughness parameter never is.

This is not a fringe reading. Section 2.3 of Recommendation ITU-R P.2040-4, the
only part of that Recommendation that models scattering from a building surface at
all, opens by saying "The power of scattering waves varies with roughness of
surfaces" and then defines its rough surface as "a round convexity array formed by
locating circular cylinders periodically", solved with lattice sums and a T-matrix
for a per-mode reflection coefficient. The ITU's own model of a rough facade is
periodic and deterministic.

`config/surface_roughness.json` therefore carries a `structure` field. Classes
marked `periodic_dominant` or `two_scale_periodic_plus_random` record the pitch,
the step height and the joint width in a `periodic_component` block, and
`SurfaceRoughnessPrior.specular_power_fraction` raises unless the caller passes
`allow_periodic=True`. Their `rms_height_mm` is an equivalent-height placeholder
that exists so the field is populated, not a description of the surface. The
refusal is there so that gap stays visible instead of being absorbed into a
plausible-looking scattering coefficient, and it should stay.

The point sharpens once the random component turns out to be small. If a brick
face carries 0.1 to 0.3 mm of random roughness, which is nearly specular at
28 GHz, then essentially all of a brick wall's non-specular behaviour comes from
the joint grid, and modelling it as Gaussian roughness gets both the magnitude and
the angular distribution wrong.

**This is no longer a hypothesis for brickwork.** `MASONRY.md` computes it, from
construction geometry alone, with a rigorous coupled-wave solve as the reference
and a Kirchhoff phase screen carrying the sweep. Three results from that work bear
directly on this table and are not repeated in full here.

- The specular power a brick wall keeps has a closed form,
  `|(1 - f) exp(-psi^2 sigma^2 / 2) + f exp(-i psi d)|^2` with `psi = 2 k cos(theta)`,
  in the mortar area fraction `f`, the joint recess `d` and the unit face-offset
  scatter `sigma`. It is periodic in `d`, not decaying, so no RMS height describes
  it above `d = lambda / (2 pi cos theta)`, which is 1.7 mm at 28 GHz.
- Below that limit the equivalent RMS height is
  `s^2 = f (1 - f) d^2 + (1 - f) sigma^2`, which for UK brickwork with a 5 mm
  recess and the EN 771-1 R1 tolerance is **2.60 mm**, and which reaches Landron's
  measured 0.5 cm at a 12.4 mm recess. The `brick_wall_with_mortar_joints` entry
  in the table below carries 0.03 mm, which is the face and not the wall, and the
  two must never be confused.
- The mechanism is the recess, not the dielectric contrast between brick and
  mortar. At 10 GHz, giving mortar a permittivity of 7 against brick's 3.91, far
  beyond any measured contrast, puts 0.7 percent of the specular power into the
  diffraction orders. A 5 mm recess puts 27 percent, and it also removes 43
  percent of the specular power outright, part of it into the orders and part of
  it into the wall, because a recessed joint is a partial impedance match.

## The circularity chain, and why the table avoids it

The most reproduced source of "typical RMS surface heights for building materials"
at millimetre wave is not a metrology result. The chain runs:

1. Wang et al., Sensors 22:6908, Table 7, captioned "Collection of Estimated
   Parameters and MSE". These are minimum-mean-square-error fits of surface
   roughness *jointly with permittivity* to the authors' own reflection
   measurements. The caption says estimated and the method section says fitted.
2. NYU's Table 4 restates those values as typical RMS surface heights, concrete
   264 to 269 micrometres and red brick 321 to 325 micrometres, without the
   qualifier.
3. Downstream ray tracers and twins adopt them as physical material properties.

Feeding a number at step 3 into a twin that then predicts reflection loss double
counts the radio evidence: the model is being validated against the data it was
fitted to, one citation removed. Had this table taken its concrete and brick
central values from that chain, the whole exercise would have been circular and
the agreement would have looked excellent.

`config/surface_roughness.json` carries a `radio_fitted` field and
`SurfaceRoughnessPrior.__post_init__` raises if it is ever true, so a fitted value
cannot enter the library by accident. Radio-fitted values are recorded in this
document for comparison and nowhere else. The other wall-scale fitted set found,
an npj Wireless Technology 2026 campaign giving a marble wall 1.0 to 1.1 mm, a
brick wall 6.5 to 8 mm and a "smooth wall" 4.1 mm, is quarantined the same way. A
4.1 mm RMS height on a wall described as smooth is a fit parameter absorbing model
error, and it is useful mainly as evidence of that.

**Kept separate: the exemplar-material case.** Ju et al., ICC 2019, Table I lists
three materials at RMS heights of 10, 100 and 300 micrometres with correlation
lengths of 1000, 500 and 300 micrometres, explicitly labelled "exemplar
materials". These were never measured and never claimed to be. They are restated
downstream as data. That is a different failure from a fit relabelled as
metrology, and conflating the two weakens both criticisms, so they are filed
apart.

**What breaks the circularity.** Piesiewicz et al., IEEE Trans. Antennas Propag.
55(11):3002-3009, 2007, doi:10.1109/TAP.2007.908559, read here in the full PDF.
Section II-B measures surface roughness with commercial optical 3D micro and
nanometrology at a 5x objective, 25 micrometre lateral and 5 micrometre vertical
resolution, fits a Gaussian to the measured zero-mean height histogram, and
reports the standard deviations in Table I: ingrain wallpaper 0.13 mm, plaster
sample 1 0.05 mm, plaster sample 2 0.15 mm. Table II gives correlation lengths of
2.3, 1.3 and 1.7 mm. The radio measurement is a separate THz time-domain
experiment on the same samples. Roughness and radio are independent, which is
exactly what the fitted chains lack, and that is why this paper is the provenance
anchor for the metrology strand.

Yoshino et al., IEEE Access 2026, doi:10.1109/ACCESS.2026.3681775, is independent
in the same way and was checked specifically for this failure mode. Its section
III states that surface roughness and correlation length were measured with a
KEYENCE VHX-8000 digital microscope, with the refractive index obtained separately
from a THz time-domain spectrometer, and the scattering data used as a forward
comparison against Beckmann-Kirchhoff. Nothing is fitted jointly. Three
qualifications carried into the table: the samples are laboratory plates, the
paper states no measurement area or sample count, and its correlation length is
defined at an autocorrelation of 0.2 rather than 1/e, so the published values are
divided by the square root of ln 5, that is 1.269, to reach the conventional
definition used here.

## The result that reframes everything

Pascual-Garcia and co-workers, IEEE Access 4:688-701, 2016,
doi:10.1109/ACCESS.2016.2526600, measured five materials with a Talysurf CLI
optical profiler under ISO 4287 and, in the same paper on the same samples, fitted
the effective-roughness scattering coefficient to 60 GHz measurements. That makes
it the only direct comparison of metrology against radio fit on identical physical
surfaces. Their Table 1 gives the roughness and their Table 2 the fits. Converting
`Ra` to `Rq` at 1.2533 and evaluating the Rayleigh closure at normal incidence,
which is the most favourable case:

| material | `Ra` (um) | `Rq` (um) | `S` from roughness | `S` fitted at 60 GHz | ratio in amplitude | ratio in diffuse power |
|---|---|---|---|---|---|---|
| wall plasterboard | 2.31 | 2.90 | 0.007 | 0.05 to 0.10 | 7 to 14 | 47 to 189 |
| chipboard | 2.70 | 3.38 | 0.009 | 0.10 to 0.20 | 12 to 24 | 139 to 554 |
| cardboard | 3.25 | 4.07 | 0.010 | 0.10 to 0.20 | 10 to 20 | 95 to 381 |
| ceiling plasterboard | 11.85 | 14.85 | 0.037 | 0.20 to 0.40 | 5 to 11 | 29 to 115 |
| brick | 14.68 | 18.40 | 0.046 | 0.30 to 0.50 | 7 to 11 | 42 to 117 |

The measured micro-roughness under-predicts the observed diffuse scattering by
roughly an order of magnitude in amplitude and two in power, consistently, on
every sample. Even assuming the heights are so spiky that `Rq = 2 Ra`, brick still
falls four to seven times short.

The paper's own reading is more measured than that and is worth quoting, because
it is the honest version: "As expected, the higher the roughness, the higher the
value of `S`; although there is a quasi-linear relation between the scattering
parameter `S` and the roughness parameter `Ra`, it is difficult to extract a law
to obtain with accuracy the `S` value from the roughness parameter." So
micro-roughness predicts the *ranking* correctly and the *magnitude* not at all.

Put that next to the two-scale split and one picture emerges. Landron, Feuerstein
and Rappaport, IEEE Trans. Antennas Propag. 44(3), 1996, Table I, read here in the
full PDF, characterise real exterior walls at 50 to 250 times the coupon values: a
rough limestone wall at a maximum roughness height of 12.7 cm with an RMS of
2.5 cm, and a brick wall at 1.3 cm and 0.5 cm, with the body text describing
limestone blocks averaging 0.5 by 0.3 m. Those are wall statistics, and their
roughness is a physical characterisation of the wall rather than a fit, which the
paper's stated purpose of comparing measurement against theory would have
defeated. They are not, however, an instrumented measurement, and the paper calls
them estimated without stating the method.

The two scales do not disagree about physics. They measure different objects. A
profilometer measures a monolithic patch of material. A metre-scale facade patch,
which is what a fishnet face stands for, also contains mortar joints, course
relief, block relief, unit-to-unit face-plane scatter, pointing, sills and
reveals. That structure carries essentially all of the diffuse power, and it is
periodic and deterministic rather than Gaussian and random.

## The table

Central RMS height in millimetres, plausible range, correlation length where the
literature gives one, evidence grade, structure, and the implied specular power
fraction at 28 and 39 GHz at normal and 75 degree incidence. Full provenance for
every entry is in `config/surface_roughness.json`.

| class | RMS (mm) | range (mm) | `l_c` (mm) | grade | structure | 28/0 | 28/75 | 39/0 | 39/75 |
|---|---|---|---|---|---|---|---|---|---|
| `glass_glazing_unit` | 0.001 | 0.0002 to 0.05 | 1.5 | measured, mmWave | random | 1.000 | 1.000 | 1.000 | 1.000 |
| `metal_cladding_panel_smooth` | 0.005 | 0.0005 to 0.05 | - | measured, metrology | random | 1.000 | 1.000 | 1.000 | 1.000 |
| `render_plaster_painted` | 0.15 | 0.05 to 1.0 | 1.7 | measured, mmWave | random | 0.969 | 0.998 | 0.942 | 0.996 |
| `concrete_as_cast_smooth` | 0.15 | 0.08 to 0.45 | 4.7 | measured, metrology | random | 0.969 | 0.998 | 0.942 | 0.996 |
| `concrete_board_marked_or_exposed_aggregate` | 0.6 | 0.25 to 2.0 | 9.5 | extrapolated | random | 0.609 | 0.967 | 0.382 | 0.938 |
| `brick_face` | 0.03 | 0.002 to 0.3 | 2.35 | measured, mmWave | random | 0.999 | 1.000 | 0.998 | 1.000 |
| `brick_wall_with_mortar_joints` | 0.03 | 0.002 to 0.3 | 2.35 | measured, mmWave | two-scale | 0.999 | 1.000 | 0.998 | 1.000 |
| `stone_ashlar_dressed` | 0.28 | 0.05 to 0.65 | 1.33 | measured, mmWave | two-scale | 0.898 | 0.993 | 0.811 | 0.986 |
| `stone_rough_rusticated` | 2.5 | 0.5 to 12.0 | - | inferred, radio | two-scale | 0.000 | 0.562 | 0.000 | 0.327 |
| `wood_cladding` | 0.05 | 0.008 to 0.15 | 0.053 | measured, mmWave | two-scale | 0.997 | 1.000 | 0.993 | 1.000 |
| `metal_profiled_sheet` | 0.005 | 0.0005 to 0.05 | - | measured, metrology | periodic | 1.000 | 1.000 | 1.000 | 1.000 |
| `ceramic_tile_facade` | 0.02 | 0.005 to 0.15 | - | extrapolated | two-scale | 0.999 | 1.000 | 0.999 | 1.000 |
| `asphalt_road_dense_graded` | 0.45 | 0.25 to 1.1 | 2.54 | measured, metrology | random | 0.757 | 0.981 | 0.582 | 0.964 |
| `asphalt_road_coarse` | 0.65 | 0.35 to 1.6 | 2.54 | measured, mmWave | random | 0.559 | 0.962 | 0.323 | 0.927 |
| `concrete_paving_slab` | 0.4 | 0.15 to 1.3 | - | measured, metrology | two-scale | 0.802 | 0.985 | 0.652 | 0.972 |
| `stone_sett_paving` | 3.0 | 0.5 to 8.0 | - | extrapolated | two-scale | 0.000 | 0.436 | 0.000 | 0.200 |

Seven entries are measured with a millimetre-wave or terahertz measurement on the
same sample, five are metrology only, one is a radio inversion and three are
honestly extrapolated. Eight of the sixteen are not Gaussian surfaces at all, and
for those the RMS column describes only the face between the repeating features.

Two columns say what the table cannot do. Every specular fraction for a two-scale
or periodic class is a face-only number and is not the behaviour of the surface.
And `stone_rough_rusticated` and `stone_sett_paving` return zero at normal
incidence, which is a signal that the model has left its useful range rather than a
prediction.

### Mean texture depth, which is not an RMS height

Three paving classes additionally carry a `mean_texture_depth_mm`, from
Kurz et al., Adv. Radio Sci. 19:165, 2021, who measured eight real German road
surfaces at 77 GHz and reported sand-patch mean texture depth under DIN EN 13036-1
on the same surfaces: asphalt concrete 500 micrometres, SMA8 800 micrometres,
SMA11 810 micrometres, whisper concrete 2.2 mm, self-healing asphalt 3.2 mm.

Mean texture depth is a volumetric quantity measured by spreading a known volume
of sand over a known area. It is not a second moment of the height field and there
is no defensible conversion to one. **These values are recorded and not
converted.** Any specular fraction computed from them would be indicative at best,
and none is quoted here. The RMS heights for those same classes come from separate
profilometry, which is why both fields exist.

The related question of whether mean *profile* depth converts to an RMS height was
worked properly rather than assumed. Three routes agree on roughly
`sigma = 0.6 MPD`: a published relation for sensor-measured texture depth, which
is defined as a profile standard deviation, at 0.6 MPD with an R-squared of 0.9,
an independent `Ra`-to-`Rq` conversion of Bitelli's laser-scanned asphalt giving
0.64 to 0.79, and a direct numerical implementation of the ISO 13473-1 algorithm on
synthetic self-affine profiles giving 0.54 to 0.65 over the plausible spectral
range. The factor is not universal, because mean profile depth is the expected
maximum over a 50 mm half-window and therefore depends logarithmically on the
spectrum. Carry 0.6 with plus or minus 25 percent and no more than one significant
figure.

## Provenance grades

Each entry in `config/surface_roughness.json` carries an `evidence_grade`:

- `measured_mmwave` - an RMS height measured on the named material, with a
  millimetre-wave or terahertz measurement on the same or a comparable sample.
- `measured_metrology` - an RMS height measured by surface metrology on the named
  material, with no radio measurement attached. The dominant risk here is the
  evaluation length: a profilometer with a sub-millimetre cut-off does not see
  the 1 mm to 50 mm lateral band that a 28 GHz wave responds to, so these values
  are biased low for radio purposes.
- `inferred_radio` - derived from a radio measurement through a stated model. The
  model is recorded in the entry and the inversion is not treated as a
  measurement.
- `extrapolated` - no measurement on this material at any frequency. The central
  value is an engineering prior anchored to a neighbouring class, and
  `log_standard_deviation` is widened accordingly.

`correlation_length_status` is separate and is usually `not_reported`. See the
correlation-length section.

## What would change the propagation stage

Two findings, and the second one reverses a working assumption.

### One: for facades the roughness prior barely matters, and for roads it does

At 28 GHz the specular loss is under one percent for any RMS height below 85
micrometres. Glass, coil-coated metal, planed and even weathered timber, brick
faces, glazed tile and polished stone are all under that line by factors of ten to
ten thousand. Their roughness values could be wrong by an order of magnitude
without moving a single decibel. Calibration effort spent there is wasted.

The classes where the number decides the answer are render, textured concrete,
dressed sedimentary stone, asphalt and paving. Of those, asphalt is the best
evidenced thing in this file and render has no exterior metrology at all.

### Two: the millimetre of roughness `METHOD.tex` used to assume

An earlier draft of `METHOD.tex` stated that at 28 GHz with realistic surface
roughness most of the reflected power is diffuse, so the specular search covers a
minority of the physics, and supported it with a worked example putting 1 mm of
RMS height on brick, which retains 25 percent specular at normal incidence.

Every measurement located here says a brick face is 0.024 to 0.095 mm, not 1 mm.
At 0.03 mm a brick face retains 99.9 percent of its specular power at 28 GHz. The
1 mm figure is not supported by any metrology for that material. `METHOD.tex` now
carries that table labelled as an assumption and states the correction alongside
it, so the two documents agree.

That does not make the conclusion wrong, because the diffuse power is real and
measured. Charbonnier et al. found diffuse scattering carrying 20 percent of total
received power in a 28 GHz urban campaign, against under 1 percent for
diffraction. Pascual-Garcia's fitted `S` of 0.3 to 0.5 for brick at 60 GHz is a
real fit to real data. What is wrong is the *mechanism*. The diffuse power does
not come from Gaussian micro-roughness, and the interval this leaves open is wide:

- If the diffuse fraction is set by micro-roughness, facades at FR2 are 99 percent
  specular and the specular skeleton is the main event.
- If it is set by facade structure, the diffuse fraction is the 20 to 36 percent of
  power that campaigns actually measure, and it arrives in a comb of grating orders
  at computable angles rather than in a smooth lobe.

Both readings were consistent with the evidence assembled here, and this section
originally declined to pick between them. **For brickwork the calculation in
`MASONRY.md` now picks the second, and it turns out to be both.** The diffuse
fraction is set by facade structure, and about a quarter of it arrives in a comb
of grating orders at computable angles while the rest arrives as a smooth lobe
whose width is set by the brick dimensions rather than by any fitted exponent.
The two readings were not alternatives.

**The measurement that would close it.** A bistatic scan at 28 GHz across one
metre-square patch of a real facade, at fixed incidence, with enough angular
resolution to separate a smooth lobe from discrete orders. If the non-specular
return is a comb whose spacing matches `lam / d` for the visible course pitch, it
is structure. If it is a smooth lobe, it is roughness.

The requirement can now be stated quantitatively rather than as an aspiration.
The computed comb sits 11 to 16 dB above its own local trend through a 3 to 5
degree beam at 10 GHz and 3.5 to 8.7 dB at 28 GHz, against an instrumental floor
near 2 dB in the one comparable published scan. So at FR2 the measurement needs a
beam of 3 degrees or narrower and must be published unsmoothed, while at FR3 an
ordinary 10 degree horn would still see 8 to 9 dB of it. The cheapest version of this
experiment is therefore at 10 GHz, not at 28. It also turns out that such a scan already exists: Pascual-Garcia and
co-workers swept a real brick wall at 57 to 66 GHz with a 3.5 degree lens beam at
0.6 degree steps and published it through an eleven-point boxcar spanning 5
degrees, which is almost exactly the comb spacing. Asking those authors for the
raw traces is cheaper than an afternoon of anechoic time and would settle it
outright.

### The recommendation

For a metre-scale facade patch, **represent the structure geometrically where the
pitch is estimable, and use a grating term where it is not. Do not fold it into an
effective sigma unless the alternative is unavailable, and if you do, label it a
fitted stand-in for structure you chose not to model.** What each costs:

- **Explicit geometry**, modelling the joint recess and reveal as surface relief.
  Most defensible, because it makes a physical claim that can be falsified, and the
  semantic layer already estimates course pitch from imagery. Costs triangles and
  needs the pitch. The Belgian pitch is now verified and it is not the British
  75 mm: Waalformaat is on 60 mm and the Belgian module M50 on 60 mm, while M65
  reaches 75 mm on a 200 mm rather than a 225 mm stretcher. Formats and sources are
  in `outputs/masonry_grating/brick_formats.json`.
- **A grating term** at a stated pitch, with the orders computed analytically.
  Cheap, keeps the determinism, and degrades gracefully because a wrong pitch gives
  wrong angles rather than wrong energy. `semantic_twin/floquet.py` implements the
  order geometry and `semantic_twin/kirchhoff.py` the amplitudes. This is the
  recommendation for classes where the pitch is estimable but the relief is not.
- **An effective sigma**, which for brickwork is no longer fitted. It is
  `sqrt(f (1 - f) d^2 + (1 - f) sigma_unit^2)` from `MASONRY.md`, valid while
  `d < lambda / (2 pi cos theta)`. For other periodic classes it remains a fit and
  the criticism below stands unchanged: the value is not a surface property, it
  does not transfer between campaigns, it will not scale correctly with frequency,
  and it silently absorbs the twin's own geometry error. Acceptable only if
  labelled as such in the provenance dictionary, which
  `radio_material_from_roughness` already does.

### Smaller consequences worth carrying

- **Grazing incidence rescues everything, and street canyons are grazing.** A 2 mm
  surface is 0.4 percent specular at normal incidence and 69 percent at 75 degrees.
  A single `scattering_coefficient` at one `reference_incidence_deg` cannot track
  that, so the reference angle should be chosen per link geometry rather than
  globally.
- **The one 28 GHz sweep on real walls cannot carry the weight often put on it.**
  Inverting Dillard's reflection-coefficient sweep on real limestone and brick
  walls gives an implied RMS height that drifts down by about 1.5 times from 5 to
  45 degrees, where a correct `cos^2` inside the exponent would hold it constant,
  and breaks entirely at 60 degrees where the measured return exceeds the
  smooth-surface Fresnel bound. Reading the full thesis for `MASONRY.md` settled
  why. Its table 4.2 shows four repeats at each angle spanning a factor of 4.3 to
  8.4 in amplitude on the brick wall at 5 to 30 degrees, with sample standard
  deviations 61 to 101 percent of the means at those four angles, the brick and
  limestone clouds overlap completely below 60 degrees, and the absolute
  calibration rests entirely on a sidelobe gain estimate that was independently
  checked at three angles on an aluminium reflector of known area and was out by
  factors of 0.6 and 2.0 in amplitude at two of them. This dataset fixes an order
  of magnitude and a trend with
  incidence angle. It does not discriminate materials or surface finish.
- **Wet surfaces were not resolved.** No source located quantifies the effect of a
  water film on radio roughness. A film fills the texture and should raise the
  specular fraction, and `config/semantic_concepts.json` already carries a `wet`
  attribute with nothing behind it.

## Open items

Ranked by how much they would change the table. Each names the exact number
needed.

1. **Kim, Hanpinitsak, Dan, Keerativoranan, Saito, Takada, "Comparison of
   Different Diffuse Scattering Models on Random Rough Surface Based on Common
   Outdoor Materials at 28 GHz Band", IEEE Antennas and Wireless Propagation
   Letters 24(10):3365-3369, 2025, doi:10.1109/LAWP.2025.3590397.** Paywalled, no
   preprint, flagged independently by two of the four literature strands. Needed:
   the per-material table of RMS height and correlation length for concrete, roof
   shingles and roads, the figure mapping those to effective-roughness parameters,
   and the sentence stating whether the surface statistics were measured or
   fitted. This is the only paper that appears to tabulate the
   roughness-to-scattering-parameter correspondence for real outdoor materials at
   exactly our frequency, and it would upgrade three entries at once.
2. **Jansen, Priebe, Moller, Jacob, Dierke, Koch, Kurner, "Diffuse Scattering From
   Rough Surfaces in THz Communication Channels", IEEE Trans. Terahertz Science
   and Technology 1(2):462-472, 2011, doi:10.1109/TTHZ.2011.2153610.** Closed, no
   repository copy. Needed: the table of measured RMS roughness and correlation
   length for the plaster and wallpaper samples, and the figure comparing measured
   specular reflection against the Kirchhoff prediction on those same samples.
   This is the most likely additional same-sample validation of the closure, with
   more samples than any currently in hand.
3. **D'Orazio et al., "Effects of water absorption and surface roughness on the
   bioreceptivity of ETICS compared to clay bricks", Building and Environment,
   2014, doi:10.1016/j.buildenv.2014.03.018.** Needed: the roughness results table,
   the instrument, and the evaluation length or area. This is the only located
   study measuring exterior render and clay brick on one instrument, and render is
   the one class in this table with literally zero metrology behind it. An IRIS
   repository copy may exist at iris.univpm.it.

Two further gaps are worth naming even though no single paper closes them. No
metrology exists anywhere for architectural facing brick as opposed to extruded
structural block, and none exists for rock-faced or rusticated stone. Both are
common on the facades this study surveys.

## Provenance note on this document

Numbers labelled as read in a full PDF were read here or by a named literature
strand that stated it read them. Two arithmetic inversions in this document, the
NYURay reflection-loss inversion and the Pascual-Garcia metrology-against-fit
comparison, were performed here and are not published results. The Auriacombe
asphalt figures were verified directly against the open-access PDF after one
strand reported the same value it had earlier fabricated and retracted, and they
are genuine. Where a strand declined to confirm a chain it had not read, that
refusal was honoured and nothing is attributed to it.

A separate audit of the numbers themselves, against files in this repository,
splits them into two piles. The pile with a stored artefact behind it is the
Ament and scattering-coefficient arithmetic, which recomputes from
`semantic_twin/mmwave.py` and `config/surface_roughness.json`, the periodic-order
counts, the Dillard and Landron chains, which come from
`outputs/masonry_grating/dillard_thesis.json` and `validation.json`, the
Pascual-Garcia bistatic entries in `bistatic_validation.json`, and the NYURay
inversion, whose 12.8 and 18.9 dB inputs are table X of `lit/2410.03104v1.pdf`.

The other pile is quoted from literature that is not in `lit/` and has no
artefact in `outputs/`, so it is only as good as the reading that produced it and
cannot be re-derived here. That pile is Koivumaki's `S` span of 0.39 to 0.82,
Charbonnier's `S` of 0.35 rising to 0.6 with vehicles at 1.0 and exponent 3, the
Wang et al. Sensors 22:6908 table 7 roughnesses, the NYU table 4 profilometry
(concrete 264 to 269 um, red brick 321 to 325 um), the Ju et al. ICC 2019 table I
entries, the npj Wireless Technology 2026 set (marble 1.0 to 1.1 mm, brick 6.5 to
8 mm, smooth wall 4.1 mm), the Kim and Hanpinitsak figures, Jansen, D'Orazio, the
Beckmann-Kirchhoff marble fit that moves `S` from 0.140 to 0.015 while the
exponent goes 5.22 to 10.50, the 5.67 and 11.33 kernel pair, and the 0.6 factor
used to convert a mean profile depth to an RMS height.

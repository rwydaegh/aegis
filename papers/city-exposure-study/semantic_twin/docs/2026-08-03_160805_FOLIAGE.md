# Foliage

> **Old illumination law, see `LAW_CHANGE.md`.** Nothing in the vegetation result depends
> on the illumination, because every crossing fraction and every decibel here is reported
> under the isotropic model. Two remarks lean on the old law and are marked where they
> sit, in part 3 and in part 5.

Vegetation is the one class in this twin where the geometry is wrong as well as
the material. Photorealistic 3D Tiles reconstructs a tree as an opaque lumpy
blob because multi view stereo cannot resolve a canopy of leaves, and the
tracer's only surface response is a half space Fresnel reflectance, which is
the wrong limit for a leaf by two orders of magnitude in electrical thickness.
This note establishes what the standard actually supports, picks a treatment,
and measures at what canopy fraction the choice starts to change the answer.

Code is `semantic_twin/foliage.py`. Study is `run_foliage_study.py`. Parameter
provenance is `config/vegetation_p833.json`. Tests are `tests/test_foliage.py`,
27 test functions that collect as 32 cases once the three parametrised ones
expand, all passing.

Two symbols are used throughout and are fixed here. `tau` is the optical depth
of a canopy, the extinction coefficient times the path length through it, and
`chi` is the susceptibility the estimator reports, the share of incident power
the observation point receives relative to free space.

**One convention warning, because it scales every decibel below.**
`FoliageMedium.specific_attenuation_db_per_m` converts P.833's `sigma_tau` to
decibels at 8.686 dB per neper, which is the field convention, while the same
class transports power as `exp(-tau)` in `slab_transmission` and in the Monte
Carlo free flight, which is the power convention and converts at 4.343. The two
cannot both be right. Every decibel figure below that came through a `sigma_tau`
is quoted as the code computes it, at 8.686, and halves if the power convention
is the intended one. The optical depths themselves, and therefore every crossing
fraction in part 3, are unaffected, because the sweep sets `tau` directly rather
than through the conversion. What would move is the reference optical depth: the
Figure 2 curve is a power specific attenuation in dB/m, so under the power
convention it implies `tau` of 4.2 over a 6 m canopy rather than the 2.1 the
study uses. This is a code question and is flagged rather than resolved here.

## Part 1. The standard, and what it does not cover

**Recommendation ITU-R P.833-10 (09/2021), "Attenuation in vegetation",
Question ITU-R 202/3, approved 2021-09-27, in force.** There is no P.833-11.
Version line on its own title page: 1992-1994-1999-2001-2003-2005-2007-2012-
2013-2016-2021.

The scope quote, from the *recommends* clause on page 1:

> that the content of Annex 1 be used for evaluating attenuation through
> vegetation with various models addressing a frequency range from 30 MHz to
> 100 GHz.

Do not read that as a validity range. It is a union over disjoint sub models,
and section 1 of Annex 1 says so itself:

> However, the wide range of conditions and types of foliage makes it difficult
> to develop a generalized prediction procedure. There is also a lack of
> suitably collated experimental data. The models described in the following
> sections apply to particular frequency ranges and for different types of path
> geometry.

### Does it cover 7 to 30 GHz

Not really, and this has to be said plainly rather than extrapolated over.

The only part of the recommendation with a parameterisation a volume renderer
can consume is the radiative energy transfer model of section 3.2.1.4, whose
four parameters are tabulated in Tables 5 to 8. Those tables have rows at
exactly these frequencies:

| set | frequencies with table rows |
| --- | --- |
| UK species (horse chestnut, silver maple, London plane, common lime, sycamore maple) | 1.3, 2, 2.2, 11, 37, 61.5 GHz |
| Korean species (ginkgo, Japanese cherry, trident maple, Korean pine, Himalayan cedar, American plane, dawn redwood) | 1.5, 2.5, 3.5, 4.5, 5.5, 12.5 GHz |

and they are sparse even within those rows. Consequences for this study's
bands, all checked by test rather than asserted:

- **No row anywhere in FR2** (24.25 to 29.5 GHz). Between 12.5 GHz and 37 GHz
  the tables are empty.
- **No row anywhere in upper FR3** (14.8 to 15.35 GHz).
- At 37 GHz there is **exactly one column** across all four tables, London plane
  in leaf. Any FR2 number is an interpolation across 1.5 octaves between two
  different species sets from two different campaigns on two continents.
- The `Am` saturation ceiling of the woodland model in equation (1) is given at
  **900 to 2200 MHz plus one point at 3605 MHz and nowhere else**, so equation
  (1) cannot be closed at all in FR3 or FR2.
- The specific attenuation curve of Figure 2 is described as "derived from
  various measurements over the frequency range 30 MHz to about 30 GHz", cites
  none of them, carries no table, and its plotted range stops at 30 GHz.
- Section 4, depolarisation, is four sentences about 38 GHz measurements with
  **no XPD value, no model and no table**.

So P.833-10 does not cover our band with data. It covers it with a curve you
can quote and a table you have to interpolate. `foliage.py` never returns a
bare parameter value: `RetParameters` carries `frequency_gap_octaves` and an
`in_table` flag, and `ret_parameters(28e9, ...)` reports 0.40 octaves off the
37 GHz row rather than pretending to be tabulated.

### Circularity, checked the way ROUGHNESS.md asks

`ROUGHNESS.md` documents a case where widely cited facade metrology turned out
to be a handful of coupons recycled through the literature. The same audit on
P.833 finds the same shape.

- **The theory** is one document: Johnson and Schwering, *A transport theory of
  millimeter wave propagation in woods and forests*, US Army CECOM-TR-85-1,
  1985. Everything in section 3.2.1.4 descends from it.
- **The UK parameter set** is one project: UK Radiocommunications Agency
  contract AY3880/510005719, final report QINETIQ/KI/COM/CR020196/1.0, Rogers
  et al., May 2002, with the campaign at 1.3, 2 and 11.6 GHz reported in Savage
  et al., *Radio Science* 38(5) 1088, 2003. Those are exactly the 1.3, 2 and 11
  rows of Tables 5 to 8.
- **The millimetre wave empirical anchor**, behind the dual slope model that
  P.833-2 to -4 carried, is Violette, Espeland and Schwering, 1985, and
  Schwering, Violette and Espeland, *IEEE Trans. Geoscience and Remote Sensing*
  26, 1988. "9.6 to 57.6 GHz" in the old text means three discrete frequencies,
  9.6, 28.8 and 57.6 GHz, through **one pecan orchard in Texas** in 1985.
- **Nothing has moved.** Tables 5 to 8 are byte identical from P.833-5 (2005)
  for the UK set and P.833-6 (2007) for the Korean set through to P.833-10.
  Figure 2 and its describing sentence are unchanged since P.833-2 in 1999.

Two specific findings worth carrying into the report.

**A silent rewrite.** The sentence "at frequencies of the order of 1 GHz the
specific attenuation through trees in leaf appears to be about 20% greater
(dB/m) than for leafless trees" read "of the order of **10 GHz**" in P.833-1 in
1994. The anchor frequency moved by a decade in 1999 and the claim has been
carried verbatim for 27 years without being revisited. It is the only in leaf
versus out of leaf statement about specific attenuation in the recommendation.

**An orphan figure.** Figure 9 of P.833-10 plots in leaf and out of leaf
attenuation at 5, 10 and 40 GHz. The dual slope model that generated it was
deleted at P.833-5 in 2005. The figure is still there, under section 3.2.1.5,
with no generating equation anywhere in the current text and a dangling
asterisk with no footnote. Anyone reading the current recommendation for a
10 GHz in leaf number will read it off a figure whose model was withdrawn 21
years ago. Do not use it.

**The recommendation disagrees with itself.** Table 8 gives London plane in
leaf at 11 GHz a combined absorption and scatter coefficient of 0.750 per
metre, which `foliage.py` reports as **6.5 dB/m**. Figure 2, in the same
document, gives about **2.2 dB/m** at 11 GHz, from the `0.19 f_GHz^1.02` fit to
the printed curve. Neither is wrong against the other because they were never
reconciled. Read the convention warning above before quoting the factor of
three: it is a factor of three at 8.686 dB per neper and a factor of 1.5 at
4.343, and the recommendation prints no unit for `sigma_tau` to settle it. What
does not depend on the convention is the factor of 7.3 spread across species
within Table 8 itself at 11 to 12.5 GHz, from 0.124 per metre for horse
chestnut to 0.900 for Himalayan cedar, and that is why this study sweeps
optical depth instead of quoting one. There is a test for it.

### The two neighbouring recommendations add nothing

- **ITU-R P.2040-4 (09/2025)**, the recommendation this twin already uses for
  every other material, contains **zero occurrences** of "vegetation", "tree",
  "foliage" or "P.833". Checked by text search of the in force PDF.
- **ITU-R P.1411-13 (09/2025)** section 4.5.1 defers entirely to P.833 and adds
  no number, no model and no table.

So the circle closes back on the 1985 theory and the 2002 project.

## Part 2. The three options, decided by measurement

The brief offered three: a classic ITU model, procedural trees from The City
Generator, or cut vegetation out. Two lose, and one of the reasons the losers
lose is quantitative rather than a matter of taste.

### Procedural trees lose on the tracer's own material model

The argument that explicit leaf geometry is "more realistic" assumes the tracer
can do anything sensible with a leaf. It cannot, and the reason is not ray
budget, it is the material model.

`tracer.py` has exactly one surface response, `fresnel_power_reflectance`,
which is a **half space** reflectance. A leaf is 0.2 mm thick, which is the
only leaf thickness the recommendation prints anywhere (Table 9, Boxtel oak,
"leaves ... 0.02 cm thick"). For a slab the coherent reflectance is

```
Gamma_slab = r (1 - e^{-2 j delta}) / (1 - r^2 e^{-2 j delta}),
delta = 2 pi d sqrt(eps - sin^2 theta) / lambda
```

with `r` the single interface Fresnel amplitude reflection coefficient, `d` the
slab thickness, `eps` its relative permittivity and `delta` its one way
electrical thickness. As `delta` goes to zero the two interfaces cancel and the
reflectance goes with it. With P.833 Table 10 wood permittivity, which is a
*lower* bound on a leaf since leaves hold more water than 40% moisture timber,
the electrical thickness of a leaf is 0.073 rad at 7 GHz, 0.153 rad at 15 GHz
and 0.277 rad at 28 GHz. Nowhere near the half space limit.

`outputs/foliage_study/foliage_leaf_slab.pdf`, and the numbers:

| frequency | half space over slab, normal | at 45 deg |
| --- | --- | --- |
| 7 GHz | 15.2 dB | 14.7 dB |
| 15 GHz | 9.1 dB | 8.8 dB |
| 28 GHz | 4.8 dB | 4.7 dB |

So swapping the blob for procedural leaf geometry would hand this tracer
millions of facets it over-reflects by 5 to 15 dB each, at centimetre scale it
cannot afford to sample, in exchange for a picture that looks better. That is
noise dressed as detail, and the prior in the brief is right.

The blob's redeeming feature is the part a surface model throws away. Multi
view stereo does not resolve leaves, but it does resolve the **silhouette and
the depth** of a canopy, which is exactly the envelope a participating medium
needs. Reusing bad geometry for the one thing it is good at is the whole move.

### The surface treatment loses because a canopy has no interface

This is the derived result, in the style `MASONRY.md` uses for brickwork: build
it from published construction facts, not from a fit.

Leaf area index is one sided leaf area per unit ground area, so leaf material
volume per unit canopy volume is `LAI * thickness / depth`. Both inputs come
from the recommendation, LAI from Table 4 and thickness from Table 9. For
London plane, LAI 1.930, over a 6 m canopy:

```
f_v = 1.930 * 0.0002 / 6.0 = 6.43e-5
```

Maxwell Garnett in the dilute limit, `eps_eff = 1 + 3 f_v (eps_l - 1)/(eps_l + 2)`
with `eps_l` the leaf permittivity, gives an effective canopy permittivity of
`1 + 1.7e-4` and a normal incidence power reflectance of **1.9e-9**
(`leaf.json`, `canopy_boundary_reflectance.london_plane`).

The P.2040-4 `wood` row gives **0.029**, which is **71.8 dB higher**. That
substitution is what `propagation/semantic_binding.py` used to make for
`vegetation_effective`, and it is what the surface treatments in part 3 stand
in for. It has since been changed: `MATERIAL_BINDING` now routes
`vegetation_effective` to the P.2040 `vacuum_air` row, which removes the
71.8 dB of invented reflection but leaves the canopy hull as a perfect
absorber, so the shipped pipeline now sits between the surface treatment and
the cut rather than on either.

There is no interface. Putting a Fresnel surface on a canopy hull invents a
reflection that the medium does not have. That is a structural error, not a
calibration error, and it is why the medium treatment in `foliage.py` crosses
the canopy boundary with no reflection at all. There is a test that the medium
with zero extinction is exactly invisible.

### The medium wins, but not for the reason I expected

My prior going in, and the brief's, was that the medium would beat the surface
at a given canopy because the surface is physically wrong. The measurement says
something more useful and slightly different.

At the optical depths P.833 itself supports, the surface treatment is not
merely wrong, it is **pinned at the opaque limit**. Its susceptibility sits
below the medium's at an optical depth of 16 at every one of the twelve canopy
fractions swept, so a wood row surface behaves like a canopy of optical depth
**above 16 over 6 m, that is above 139 dB of one way attenuation**, against the
recommendation's own 6.5 to 47 dB from Tables 5 to 8 and 18 dB from Figure 2.
Halve the two Table 5 to 8 figures if the power convention of the warning above
is the intended one. Cutting vegetation out is pinned at the transparent limit.

The medium is the only treatment that lives between them, and it is the only
one that carries the uncertainty. That matters more than being right at any one
optical depth, because the optical depth is exactly the thing P.833 cannot pin
down in this band to better than a factor of 7.3 across species.

## Part 3. The sensitivity curve

`outputs/foliage_study/foliage_sensitivity.pdf`. Data in `sensitivity.json`,
thresholds in `crossings.json`.

Scene: an 18 m street canyon, 18 m facades, ground and facade permittivities
held fixed at 3.66 - 0.09i and 3.91 - 0.14i, observer at 1.5 m, canopy box from
4 to 10 m with a dialable half width. 400,000 rays per point, 120 sweep points.
`run_foliage_study.py` labels those two permittivities concrete and asphalt from
`config/itu_p2040_4.json`, and they are neither: that file gives concrete
5.24 - 0.46i and asphalt 4.83 - 0.57i at 15 GHz. The label is wrong and the
numbers have no traced source. Nothing in this part turns on it, because both
surfaces are identical across all four treatments, but the absolute
susceptibility level does.

Reported metric is the isotropic susceptibility, chosen because it is the only
one of the three illumination models whose estimator standard error is below
0.3% at this ray count. The two site models put most of their weight within a
few degrees of the horizon, where a canyon passes almost nothing, so a handful
of grazing escapes carry the whole estimate and their standard error sits near
2%. Fine for a 5 dB effect, not fine for a 0.5 dB threshold. All three
susceptibilities are in the JSON. The 0.3% and 2% are asserted in the header of
`run_foliage_study.py` and are not recomputed into `sensitivity.json`, so they
are the one pair of numbers in this part with no output file behind them.

> **Old illumination law, see `LAW_CHANGE.md`.** The reason given for not reporting the
> two site models is that the old bands put their weight within a few degrees of the
> horizon. That reason has to be rechecked under the new law, and the isotropic result
> reported here does not depend on it either way.

The canopy fraction on the x axis is measured the same way the site numbers
were: share of directions from the observation point that look into vegetation.
So Korenmarkt's 2.0% and Milan's 0.9% are directly comparable and are marked.

### Where the treatments diverge

Canopy share of solid angle at which the treatments first separate by more than
the stated threshold, isotropic susceptibility, at the reference optical depth
of 2 which is what P.833 Figure 2 implies at 15 GHz over a 6 m canopy:

| comparison | 0.5 dB | 1 dB |
| --- | --- | --- |
| surface, specular roughness, vs cut | **2.1%** | 4.2% |
| surface, diffuse roughness, vs cut | **2.0%** | 4.1% |
| surface vs medium | **2.9%** | 5.7% |
| medium vs cut | **6.0%** | 10.6% |

Across the full swept range of optical depth, the medium against cut crosses
0.5 dB anywhere from 26% (at tau 0.25) down to 3.1% (at tau 16). That range is
wider than the recommendation supports. Within the table envelope of tau 0.74
to 5.4 the crossing runs from about 11% to about 4.2%, interpolated between the
sweep points at tau 1 (8.9%) and tau 4 (4.6%).

### What this tells the ten city acquisition

1. **Below about 2% canopy solid angle, all three treatments agree within
   0.5 dB.** Milan Duomo at 0.9% is comfortably inside. **Korenmarkt at 2.0% is
   sitting exactly on the line**, which is a little less comfortable than "1.4%
   by area, therefore negligible" suggested. The existing sites do not need a
   vegetation model, but Korenmarkt is not far from needing one.
2. **Between 2% and about 6%, the surface treatment is the outlier.** Cut and
   medium still agree with each other while the surface is already 0.5 to 1 dB
   away from both. That regime is the dangerous one, because it is the regime
   where doing nothing beats putting a wood row surface on the hull, which is
   what the pipeline did before the vacuum row landed.
3. **Above about 6%, and certainly on a tree lined boulevard, the answer is a
   band and not a number.** At 32% canopy the medium spans a factor of 2.8 in
   susceptibility across the P.833 table envelope alone, about 0.16 at tau 0.74
   down to about 0.056 at tau 5.4, interpolated between the sweep points at
   tau 1 (0.146) and tau 4 (0.072). Across the full swept range it spans a
   factor of 8.9, 0.196 at tau 0.25 down to 0.022 at tau 16. Quoting a single
   foliage corrected exposure at such a site without the band would be the kind
   of false precision this project spends the rest of its documents avoiding.
4. **The roughness of the surface treatment barely matters.** Smooth wood and
   metre scale lumpy wood differ by 0.19 dB or less at every swept fraction up
   to 18% canopy, and by 0.46 dB at the next one, 26%. Whether the blob is a
   mirror or a diffuser is not the problem. That it is a surface at all is the
   problem.

## Part 4. Validation, since there are no measurements

Robin will not run a vegetation campaign, so nothing here is fitted. Every
check is a transcription, a closed form, or an identity the recommendation
itself asserts.

**The estimator.** `FoliageTracer` is a separate estimator from `SbrTracer`
because `propagation/` is shared and was not to be edited. That means its
validation had to be re-earned rather than inherited. It reproduces free space
susceptibility of 1 to 1e-6, the PEC ground plane closed form of exactly 2 for
a rooftop illumination, and `SbrTracer` on a dielectric ground plane to within
Monte Carlo error at the same seed.

**The transport.** An absorbing slab over an otherwise empty sphere has an
exact answer. Directions sampled uniformly have `mu = cos(theta)` uniform on
`(0, 1]`, and the chord through a slab of depth `d` is `d / mu`, so

```
chi = 1/2 + 1/2 * integral_0^1 exp(-tau / mu) dmu = 1/2 + 1/2 E_2(tau)
```

with `E_2` the second exponential integral. Checked at tau 0.25, 1 and 3 to
within 1%. This is the test that catches a wrong chord, a wrong boundary
crossing or a wrong free flight, none of which a normal incidence Beer-Lambert
check would notice.

**The phase function.** The recommendation exposes `alpha`, the forward
scattered share of scattered power, and `beta`, the forward lobe beamwidth, and
**never writes the functional form of the phase function down**, so any
renderer has to interpolate it, and this one uses a Gaussian forward lobe. The
consequence is bounded by the recommendation's own algebra. With `W` the single
scattering albedo, equations (13) and (14) define `tau_hat = tau (1 - alpha W)`
and `W_hat = (1 - alpha) W / (1 - alpha W)`,
which is the standard delta-M scaling. If the escaping power is invariant under
the scaling P.833 itself applies, the lobe shape does not matter. It is,
to 3%, at forward lobe beamwidths of 2 and 8 degrees. The recommendation has
therefore already committed to the volumetric picture, and a Monte Carlo
transport solver is the same physics its series solution solves, not a rival
model.

## Part 5. What would change the conclusion

Stated up front so it can be checked rather than defended.

1. **A canopy that is optically thin in our band.** The whole case for the
   medium rests on the answer moving with optical depth. If real FR3 and FR2
   canopies sit at tau below about 0.3 over a canopy depth, the medium and the
   cut agree within 0.5 dB out to 26% canopy and the cheap null wins on
   simplicity. P.833's own numbers say tau is 0.74 to 5.4 over 6 m, so this is
   unlikely, but those numbers are a 2002 UK project read across 0.4 octaves.
2. **Evidence that a canopy hull does reflect.** The Maxwell Garnett argument
   assumes a dilute mixture of leaf material in air and no correlated
   structure. A dense hedge, a conifer, or a canopy with a sharp foliage
   boundary at the scale of a wavelength could develop a genuine interface. If
   the boundary reflectance is measured or derived to be above about 1e-3
   rather than 1e-9, the medium needs a Fresnel boundary and the surface
   treatment stops being structurally wrong.
3. **A tracer that can afford leaf scale sampling.** The case against
   procedural trees is half physics and half budget. The physics half survives
   any budget, because the half space material model over-reflects a leaf by 5
   to 15 dB regardless of how many rays are thrown at it. But if the tracer
   grew a thin dielectric slab response, explicit foliage geometry would become
   a defensible option rather than a worse one, and the comparison would need
   redoing.
4. **A revision of P.833 with FR3 or FR2 rows.** Everything above treats the
   parameter spread as irreducible because the tables have not moved since
   2005. A revision with rows between 12.5 and 37 GHz would collapse the band
   in panel (a) and might well move the crossing fractions.
5. **Sites where vegetation is not overhead.** The sweep dials a canopy above
   the observer. A hedge or a treeline at eye level occludes the horizon
   instead of the zenith, and the horizon is where both site illumination
   models put their weight. The crossing fractions would move, probably
   downward, and that geometry is worth a second sweep if the ten city set has
   such a site.

   > **Old illumination law, see `LAW_CHANGE.md`.** That both site models put their
   > weight near the horizon is a property of the old bands. The item survives as a
   > question, but which elevations matter now has to be read off the new law.

## Hook needed in the shared tracer

Nothing here required editing `propagation/`, and nothing was edited. To move
the medium from this study into the production pipeline, `SbrTracer` needs one
hook, which should be coordinated rather than taken:

> In `_run_batch`, after `klass = self.face_class[face]` and before the Fresnel
> reflectance is applied, an optional per class predicate that marks a class as
> a **medium boundary** rather than a surface. Boundary faces must (a) not
> apply `fresnel_power_reflectance` or `specular_share`, (b) toggle a per ray
> `inside` flag, and (c) not increment the bounce counter. In addition the
> free flight sampling of the medium has to run before the surface interaction
> so a collision inside the medium can pre-empt the next surface hit.

That is roughly twenty lines. `FoliageTracer.trace` in `foliage.py` is the
reference implementation of exactly that control flow, and
`test_estimator_agrees_with_the_shared_sbr_tracer` is the equivalence the
merged version has to keep passing.

Second, smaller change, in `propagation/semantic_binding.py`. The wood row
substitution that part 3 measures as the worst of the three treatments in the 2
to 6% canopy regime has already been retired: `MATERIAL_BINDING` now sends
`vegetation_effective` to `vacuum_air`, which kills the invented reflection but
keeps a perfectly absorbing hull. That is a half fix, and the file says so in
its own comment. The remaining step is to route the class to
`foliage.FoliageMedium.from_p833` once the hook above exists.

# External cross validation against an independent solver

`PAPER_METHODS.md` section 8 says in its own words that the validation ladder is
"strong against implementation error and blind to formulation error", because
every rung is either an invariant the estimator was built to satisfy or a closed
form derived from the same physics the estimator implements. The section 4.2
illumination correction is the proof: it moved the eleven city numbers by up to
6.3 dB, it reordered the cities, and no test failed when it was wrong.

This document closes that hole. It reports a comparison of the adjoint shoot and
bounce estimator of section 5 against Sionna RT 2.0.1, an independently written
solver from a different group with a different formulation, on the same triangles
at the same frequency at the same standpoints, and it reports the two convergence
curves that `MONOSTATIC_SBR.md` section 9 asks for, at the shallow end where the
acceptance rule bites and where nothing had been measured.

Everything here is produced by `semantic_twin/propagation/sionna_check.py` and
tested by `tests/test_sionna_check.py`. No existing module was modified.

## 1. Verdict

**The estimator agrees with an independent solver on the city meshes, within
0.25 dB on the median in the shipped configuration and within 0.31 dB in the
configuration where neither tool's answer depends on the tessellation, at both sites and
under all three illumination models.** `PAPER_METHODS.md` currently records
external cross validation as absent, and that is no longer the case. Section 6
gives the two site tables and section 8 the exact wording the claim can carry.

> **Old illumination law, see `LAW_CHANGE.md`.** The 0.25 dB and 0.31 dB medians are
> quoted "under all three illumination models", two of which are the old height band
> and range band models. The check survives as a check, because it tests the
> transport into the exit direction bins, and both per model figures have to be
> recomputed under the facade tip law.

Three qualifications belong with that headline and none of them is cosmetic.

1. **The agreement is on the multipath term, and the direct term is not
   evidence.** Both tools read the same triangles through the same Mitsuba BVH,
   so a line of sight agreeing to 0.12 dB says the two harnesses point at the
   same building, not that the physics matches. Every table below splits the
   direct and multipath terms for that reason.
2. **Sionna's specular branch is wrong on tessellated surfaces, badly, and this
   was found here rather than assumed.** On a flat plane cut into 1 m cells with
   0.2 mm of vertex height jitter it returns an isotropic susceptibility of 452
   against an exact answer of 0.6405, a factor of 706 of manufactured energy, and
   a single direction transfer of 4826 against a free space value of 1. Section 5
   establishes that this is the oracle's fault and not the estimator's or the
   harness's, gives the mechanism, and shows the effect present on the city meshes
   themselves at a maximum transfer of 30.5. The `specular` mode is therefore
   contaminated and its number is reported as a diagnostic rather than as
   agreement. The `diffuse` mode is immune, because it does not use the image
   method at all. The `production` mode is mostly but not entirely immune: it
   still routes the coherent fraction through the same solver, and its multipath
   term carries a residual positive bias of about 1.2 dB at both sites that points
   the same way. The overall `production` agreement holds at a quarter of a
   decibel because that term is a small part of the total.
3. **The bounce budget is more conservative than the paper implies, and the
   dynamic range budget is sufficient but not necessary.** Under the acceptance
   rule written in `MONOSTATIC_SBR.md` section 9.1, one surface interaction passes
   at Korenmarkt and two at Brussels Grand Place, against a shipped three and an
   asserted four, and a 20 dB dynamic range meets a 0.1 dB criterion against an
   asserted 25 dB. See section 7.

## 2. The oracle, and what was rejected

**Chosen: Sionna RT 2.0.1** (NVIDIA), running on Mitsuba 3.8.0 and Dr.Jit 1.3.1.
It is a maintained, published, independently authored radio propagation solver
with a dielectric slab model, full Jones transport, a diffuse scattering model and
its own path finding. It is the only thing in reach that is a second
implementation of the same problem rather than a second implementation of the same
code.

**Rejected: DiffeRT 0.7.0.** It is installed and it works, but it is a geometry
and path finding library. It has no dielectric slab, no Jones transport and no
diffuse scattering, so a comparison against it would test ray geometry, which is
already shared through Mitsuba, and nothing else.

**Rejected: physical measurement.** Ruled out permanently by the owner. It is
worth recording that this is the reason and not an oversight, because it means an
independent solver is the only external check this study can ever have.

`MONOSTATIC_SBR.md` section 10.2 argues at length that Sionna cannot be the
*engine* for this study: it has no per shape material assignment in the form
needed, it deletes co-located transmitter and receiver as a degeneracy, and there
is no way to inject a primary visibility atlas. None of that disqualifies it as an
*oracle*. An oracle is asked for one scalar per source direction and is allowed to
be slow.

## 3. The mapping, written down before anything was run

The estimator computes a dimensionless susceptibility

```
chi = integral over 4 pi of T(u) Q(u) dOmega
```

where `T(u)` is the ratio of the power density arriving at the standpoint from a
source in direction `u` to the free space reference at the same range, and `Q` is
the normalised illumination density on the sphere. `chi` is exactly 1 in free
space by construction. The oracle has to be made to produce the same `T`.

| quantity | estimator | oracle | how they are made to match |
|---|---|---|---|
| what is transported | power only, throughput scalar | Jones matrices, complex | oracle powers summed incoherently over paths, `0.5 * sum over rx and tx polarisation of \|a\|^2` |
| source | direction on the sphere, at infinity | a point transmitter | placed at 20 km along `u`, transfer divided by `(lam / 4 pi R)^2` |
| direction of travel | adjoint, rays leave the standpoint | forward, from the transmitter | reciprocity: transmitter at the standpoint, receiver at 20 km, which is the cheaper direction for the oracle |
| antenna | none, a bare point | requires an array | `PlanarArray(1, 1, pattern="iso", polarization="cross")` both ends, both polarisations summed, halved |
| material | half space Fresnel, unpolarised, per class | ITU single layer slab | slab thickness pinned at 2.0 m, measured in section 4 |
| roughness | Rayleigh split, specular fraction `exp(-g^2)` | scattering coefficient `S`, specular Jones scaled by `sqrt(1 - S^2)` | `S = sqrt(1 - <exp(-g^2)>)` with the average taken flux weighted over incidence |
| diffuse lobe | cosine about the normal | Lambertian, the Sionna default | identical by construction |
| diffraction | none | available | disabled, `diffraction=False` |
| refraction | none, power that is not reflected is lost | available | disabled, `refraction=False` |

The mapping is asserted in the suite rather than trusted. `T` integrates to 1 to
Monte Carlo precision under every illumination model in free space, and the band
resolved `T` is flat, which is the same identity the estimator's own free space
test uses.

### 3.1 Three modes, because one comparison is not enough

| mode | estimator roughness | oracle `S` | what it is for |
|---|---|---|---|
| `specular` | `s = 0` on every class | 0 | an exact roughness match in which the oracle uses its image method |
| `diffuse` | `s = 1 m`, fully incoherent at 15 GHz | 1 | an exact roughness match in which the oracle uses its own shoot and bounce |
| `production` | the shipped per class `s` from `config` | matched by the formula above | the configuration the paper actually reports |

In `specular` and `diffuse` there is no approximation left in the roughness
treatment for the two to differ on, which is why they are the modes the verdict
rests on. In `production` the roughness split itself is approximate, because the
estimator applies it as a product of per bounce averages while the oracle carries
it inside the Jones matrices.

**Roughness is not the only thing that differs, and calling these exact model
matches would be wrong.** The estimator transports one unpolarised scalar and the
oracle transports a Jones matrix in every mode. For a single interaction, with
both polarisations equally excited, the oracle's incoherent sum and the
estimator's unpolarised average are the same number. For a chain of interactions
they are not: the estimator forms a product of averages and the oracle forms an
average of products, and the two separate whenever the reflectance is
polarisation dependent and the successive incidence planes are correlated. This
is a real approximation in the estimator, it is present in all three modes, and
this comparison **measures** it rather than eliminating it. The measurement is the
0.1 to 0.3 dB in section 6, on meshes where the mean interaction count is about
1.6, so the bound weakens for a scene with deeper chains.

### 3.2 What this comparison cannot see

- **Shared geometry.** Both tools load the same PLY through the same Mitsuba BVH.
  Nothing here can detect a wrong mesh, a wrong crop or a wrong ground datum.
- **Shared illumination.** `Q` is the estimator's own construction, applied to
  both sides. The section 4.2 class of error, a wrong illumination law, would move
  both tools identically and cancel exactly. **This comparison cannot validate the
  illumination law.** It validates the propagation kernel, which is what it was
  built to do, and the distinction should survive into the paper.
- **Shared material constants.** The permittivities come from the same binding
  file. A wrong permittivity moves both.
- **Shared omissions.** Diffraction is off in both for the primary comparison, so
  the omission cancels rather than showing up. Section 7.3 turns it on in the
  oracle alone and measures what it is worth, which is about 0.01 dB.

> **Old illumination law, see `LAW_CHANGE.md`.** The shared illumination bullet says
> this comparison cannot validate the illumination law, and the law has since been
> replaced. Nothing in 3.2 is stale, and that bullet is now the load bearing sentence
> of the document, because it is the reason a law change leaves the check standing.

## 4. Harness validation, on closed forms, before any city

A comparison whose harness is untested measures the harness. Three rungs, each of
which has to pass before the city meshes are allowed to mean anything.

**Free space.** `T = 1` exactly, under all three illumination models, at every
elevation. Passes to Monte Carlo precision. This pins the antenna convention, the
polarisation sum, the free space reference and the range division simultaneously.

**Dielectric ground plane, specular.** The closed form is `T = 1 + R(theta)` with
`R` the unpolarised Fresnel power reflectance. Over ten elevations from 2 to 80
degrees the worst residual is **0.0016 dB**. Repeating at a 2 km source range
gives 0.015 dB, a factor of ten, which is the expected `1/R` finite range term and
confirms that 20 km is far enough.

**Dielectric ground plane, fully diffuse.** The closed form was derived for this
purpose: for a Lambertian half space under an observer at elevation `alpha`,
`T = 1 + 2 sin(alpha) <R>` where `<R> = integral from 0 to 1 of R(c) dc`, which is
0.2811 for asphalt at 15 GHz. Worst residual over the same ten elevations is
**0.0068 dB**.

Both are in `outputs/cross_validation/plane_harness.json`.

### 4.1 Two things the harness got wrong first, both worth recording

**Slab thickness.** Sionna's `itu_coefficients_single_layer_slab` reduces to the
half space Fresnel coefficient only in the thick limit. At the library default of
0.1 m the brick class is **3.0 dB** away from the half space answer at 15 GHz.
Pinned at 2.0 m, the residual is under 0.01 dB. `tests/test_sionna_check.py`
asserts both directions, so the test can fail if the default is ever silently
picked up.

**Silent path buffer overflow.** Sionna's `max_num_paths_per_src` is a hard
allocation. Exceeding it does not raise: paths are dropped, and the result is
still a smooth looking function of elevation. On the diffuse plane at 2e6 samples
against 10 targets it cost a clean factor of four in scattered power while looking
entirely plausible. This was diagnosed with a near perfectly conducting control
whose closed form ratio moved from 1.00 to 0.25 as the sample count rose. The
harness now records a high water mark on every solve and `compare()` raises if any
run saturated. **Every number in this document was produced by a run that did not
saturate**, and the high water marks are in the JSON.

## 5. The specular anomaly: whose it is, and why

On the Korenmarkt mesh the `specular` mode disagrees by a median of +1.1 dB and a
worst standpoint of +7.2 dB, always with the oracle higher, and the disagreement
is entirely in the multipath term. Before anything can be validated, an oracle
that returns more power than a surface can reflect has to be explained.

### 5.1 A control the answer cannot depend on

A ground plane under an observer has an exact isotropic susceptibility, and the
derivation is one line. Half the departure sphere escapes unobstructed carrying
throughput 1. The other half meets the plane once and returns weighted by a
reflectance averaged uniformly in `cos(theta)`, which is the measure the lower
hemisphere carries. So

```
chi_iso = 0.5 + 0.5 <R> = 0.6405   for asphalt at 15 GHz
```

Now cut that plane into 1 m cells and jitter every vertex height by a Gaussian of
standard deviation `sigma`. **The exact answer does not change.** The jitter
redirects reflected power, it does not create or destroy any, as long as the
surface stays single valued and the shadowing stays small. So `chi_iso(sigma)` is
a control that both tools must be indifferent to, and the one that is not
indifferent is the one adding energy.

### 5.2 The sweep

200 m half width, 1 m cells, 160,000 triangles, observer at 1.5 m, one surface
interaction, roulette disabled. `tessellation_experiment.json` and
`tessellation_experiment_lowend.json` in `outputs/cross_validation/`.

| vertex jitter | facet slope noise | estimator, specular | oracle, specular | oracle max `T` | estimator, diffuse | oracle, diffuse |
|---|---|---|---|---|---|---|
| 0 | 0 | 0.6404 | 0.6320 | 1.96 | 0.6404 | 0.6296 |
| 0.001 mm | 1e-6 rad | 0.6404 | 0.6320 | 1.96 | 0.6404 | 0.6296 |
| 0.01 mm | 1e-5 rad | 0.6404 | **33.05** | 232 | 0.6404 | 0.6296 |
| 0.05 mm | 5e-5 rad | 0.6404 | **346.8** | 2801 | 0.6404 | 0.6296 |
| 0.2 mm | 2e-4 rad | 0.6404 | **452.1** | **4826** | 0.6404 | 0.6296 |
| 0.5 mm | 5e-4 rad | 0.6404 | **215.9** | 3113 | 0.6404 | 0.6296 |
| 1 mm | 1e-3 rad | 0.6404 | **85.17** | 1579 | 0.6404 | 0.6296 |
| 2 mm | 2e-3 rad | 0.6403 | **20.50** | 459 | 0.6404 | 0.6295 |
| 5 mm | 5e-3 rad | 0.6396 | **2.347** | 82.3 | 0.6401 | 0.6293 |
| 20 mm | 2e-2 rad | 0.6349 | 0.6544 | 5.73 | 0.6374 | 0.6266 |
| 50 mm | 5e-2 rad | 0.6247 | 0.6102 | 3.49 | 0.6296 | 0.6191 |
| 200 mm | 2e-1 rad | 0.5931 | 0.5811 | 2.46 | 0.6003 | 0.5906 |

Exact answer 0.6405 in every row. Free space `T` is 1, so an oracle maximum
transfer of 4826 is a single source direction delivering nearly four thousand
times the free space power density off a lossy plane.

The 0.001 mm row is not an independent point and is recorded as a caveat rather
than as evidence: PLY vertices are float32, whose spacing at a 200 m coordinate is
about 0.012 mm, so a 1 micron jitter is rounded back to the flat plane over most
of the sheet. The lower edge of the band is therefore **not resolved below 1e-5
rad**, and everything from 1e-5 to 5e-3 rad is inside it.

Read the columns rather than the rows.

- **The estimator is indifferent**, as energy conservation demands, drifting only
  at large jitter where genuine self shadowing appears and always downward, which
  is the direction shadowing goes.
- **The oracle's diffuse branch is also indifferent**, sitting at 0.6296 in every
  row to four digits until genuine shadowing appears, 0.07 dB below the exact
  answer, which is the sky sampling Monte Carlo error of the run.
- **The oracle's specular branch is not.** It is correct at exactly zero jitter,
  correct again above 2e-2 rad, and manufactures up to a factor of **706** in
  between.

That third column is the whole finding, and the second one is what makes it
attributable. The diffuse branch shares the scene construction, the material
mapping, the slab thickness, the source range, the antenna convention and the
polarisation sum with the specular branch. It differs in one thing: how paths are
found. **The fault is in Sionna's image method, not in Sionna generally, not in
the harness, and not in the estimator.**

### 5.3 The mechanism

Sionna finds specular chains by shoot and bounce candidate generation followed by
image method refinement, then removes duplicates. On an exactly flat patch made of
many coplanar triangles the refinement converges every candidate to the same
stationary point and the duplicate removal keeps one. Give each triangle a small
independent tilt and each now hosts its *own* distinct stationary point at a
slightly different location, so the duplicates are no longer duplicates and all of
them survive. Each is then assigned the infinite plane reflection coefficient
irrespective of the facet's size, which is geometrical optics used well outside its
validity when the facet is smaller than the Fresnel zone. The manufactured energy
therefore tracks the number of facets that can satisfy the mirror condition at
once, which rises as the tilts become resolvable and falls once they are large
enough to disqualify one another. The sweep shows both edges: it climbs from 1.96
to 4826 between 1e-6 and 2e-4 rad and falls back to 5.73 by 2e-2 rad, and in the
falling limb the maximum transfer scales close to the inverse square of the slope,
1579 to 82 for a factor of five and 82 to 5.7 for a factor of four.

That account is not inferred from the energy alone. The oracle reports how many
paths it retained, and the count is the mechanism made visible.

| vertex jitter | retained paths per source direction | oracle `chi_iso` | oracle max `T` |
|---|---|---|---|
| 0 | **2** | 0.6320 | 1.96 |
| 0.01 mm | 243 | 33.05 | 232 |
| 0.05 mm | 2660 | 346.8 | 2801 |
| 0.2 mm | **3671** | 452.1 | 4826 |
| 0.5 mm | 1816 | 215.9 | 3113 |
| 1 mm | 752 | 85.17 | 1579 |
| 2 mm | 209 | 20.50 | 459 |
| 5 mm | 23 | 2.347 | 82.3 |
| 20 mm | **3** | 0.6544 | 5.73 |
| 200 mm | **2** | 0.5811 | 2.46 |

On the flat plane the oracle keeps exactly two paths per source, the line of sight
and one specular reflection, which is the correct and complete answer. At 0.2 mm
of jitter it keeps 3671, and the susceptibility is 706 times the exact value.
Above 2e-2 rad it is back to two or three. The path count and the manufactured
energy rise and fall together over three and a half orders of magnitude, which is
what a duplicate stationary point explanation predicts and what an absorption or
material error would not.

The estimator cannot exhibit this. It multiplies a throughput by a power
reflectance and redistributes a direction at every interaction, so it conserves
energy by construction whatever the tessellation does.

### 5.4 The decisive test: the answer depends on the candidate sample budget

`samples_per_src` is the number of rays Sionna shoots to *find* candidate
specular chains. It is a numerical budget. A converged physical answer cannot
depend on it. Sweeping it over a factor of 32 on the same two scenes, everything
else held fixed:

| samples per source | flat plane, 2 triangles | 0.2 mm jitter, 160,000 triangles | paths per source, jittered |
|---|---|---|---|
| 25,000 | 0.6603 | 170.6 | 1,433 |
| 50,000 | 0.6603 | 240.0 | 2,014 |
| 100,000 | 0.6603 | 334.9 | 2,792 |
| 200,000 | 0.6603 | 460.5 | 3,829 |
| 400,000 | 0.6603 | 598.6 | 4,988 |
| 800,000 | 0.6603 | 782.1 | 6,550 |

`outputs/cross_validation/sampling_convergence.json`. The flat plane is invariant
to four decimal places across a factor of 32, exactly as a converged answer should
be, which incidentally also clears the harness a second time. The jittered plane
grows over the same span by a factor of 4.6, an exponent of 0.44 in the budget, as
does the retained path count. There is no sign of a limit. **Sionna's specular
answer on a tessellated surface is a function of how hard it looked, not of what
is there.** The 0.6603 rather than 0.6405 in the flat column is the sky sampling
noise of this smaller 600 direction probe and is common to every row.

### 5.5 Where the city meshes actually sit

A sweep on a synthetic plane is only relevant if the real meshes occupy the band
it identifies, so that is measured rather than assumed. The slope noise of a real
mesh is the dihedral angle between adjacent triangles of the same surface class,
which is what the jitter manufactures on the plane.

| | Korenmarkt | Brussels Grand Place |
|---|---|---|
| triangles at the 250 m crop | 617,091 | 706,720 |
| median facade facet size | 0.67 m | 0.65 m |
| adjacent facade pairs | 250,927 | 327,561 |
| slope below 1e-5 rad, effectively exact quads | 19.6 % | 19.6 % |
| **slope 1e-5 to 1e-4 rad** | **18.8 %** | **19.6 %** |
| **slope 1e-4 to 1e-3 rad** | **1.2 %** | **1.3 %** |
| **slope 1e-3 to 2e-2 rad** | **1.5 %** | **1.5 %** |
| **total inside the pathological band** | **21.5 %** | **22.4 %** |
| slope 2e-2 to 1e-1 rad | 7.8 % | 8.0 % |
| slope above 1e-1 rad, genuine corners | 51.1 % | 50.0 % |
| near duplicate triangle pairs within 5 cm | 14,534 | 13,214 |

The distribution is close to bimodal. Half of the adjacent facade pairs are
genuine building corners above 1e-1 rad, and a fifth are coplanar to better than
1e-5 rad, which is a planar quadrilateral split into two triangles and reads to
the solver as a single flat facet. **But 22 % sit inside the band the sweep
identifies, and that is not a small tail.** The near duplicate count is a second
and independent source of coincident stationary points that the jitter sweep does
not model at all.

The effect is visible on the meshes without any appeal to the sweep, in the
oracle's own maximum single direction transfer over the 3000 sampled sky
directions at each standpoint.

| Korenmarkt standpoint | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| oracle max `T`, specular | 1.81 | 16.05 | 20.04 | 4.99 | 4.59 | **30.53** | 5.33 | 11.66 |
| oracle max `T`, production | 1.63 | 2.98 | 3.03 | 2.03 | 1.85 | 5.27 | 2.96 | 2.84 |
| oracle max `T`, diffuse | 1.21 | 1.44 | 1.36 | 1.38 | 1.40 | 1.38 | 1.34 | 1.34 |

A single source direction delivering thirty times the free space power density
would require thirty facades mirroring the same distant source into the same point
with no loss. The diffuse branch, looking at the same facades and reflecting the
same total energy off them, never exceeds 1.47 anywhere at either site. Brussels
reaches 6.83 specular against 1.47 diffuse.

So the specular mode's disagreement is contaminated at both sites, and the reason
it is +1.1 dB rather than the factor of hundreds the plane sweep reaches is that
the manufactured energy is concentrated in a few directions out of 3000 and half
the mesh is genuine corners rather than near-coplanar sheets. **The `specular`
mode number is reported below for completeness and should not be quoted as a
validation.**

## 6. Site results

Eight standpoints per site, drawn from the published `city250_corrected` location
manifest so the estimator leg *is* the run the paper reports rather than a fresh
one. 3000 sky directions per site, drawn by mixture importance sampling over the
three illumination models so that every model is scored on the same solves and no
importance weight can exceed 3. Oracle at four surface interactions on an L4.

Positive dB means the oracle is higher. `MC` is the median Monte Carlo standard
error of the oracle's own sky integral, and it is the floor below which the
comparison cannot resolve anything.

The two Monte Carlo errors do not cancel and only one of them is large. The
oracle integrates `T Q` over 3000 importance sampled sky directions, which is the
`MC` column at 0.24 to 0.46 dB. The estimator does not use that sample at all: it
evaluates `Q` analytically on the exit direction of each of 200,000 rays and bins
them on a 512 cell lattice, and `CODE_AUDIT.md` section 4 measures its per
standpoint spread over eight disjoint seed streams at 0.004 dB isotropic, 0.024 dB
rooftop and 0.118 dB street small cell. **So a residual of a quarter of a decibel
is at or below the oracle's own noise, and essentially none of it is the
estimator's.**

> **Old illumination law, see `LAW_CHANGE.md`.** The 3000 sky directions are
> importance sampled over the three old models, and both site tables below carry a
> rooftop and a street row for every mode. The isotropic rows and the direct against
> multipath split survive, the two directional rows are old law integrals, and the
> sky sample would be redrawn for the facade tip law.

### 6.1 Korenmarkt, 250 m crop, 15 GHz

| mode | model | median | mean abs | max abs | MC floor | direct term | multipath term |
|---|---|---|---|---|---|---|---|
| specular | isotropic | +1.106 | 1.869 | 7.228 | 0.299 | -0.122 | +3.925 |
| specular | rooftop | +1.035 | 1.562 | 3.927 | 0.383 | -0.033 | +2.952 |
| specular | street | +0.712 | 1.049 | 3.275 | 0.458 | -0.076 | +1.001 |
| **diffuse** | isotropic | **-0.114** | 0.111 | 0.244 | 0.236 | -0.122 | -0.069 |
| **diffuse** | rooftop | **-0.011** | 0.101 | 0.332 | 0.263 | -0.033 | +0.079 |
| **diffuse** | street | **+0.019** | 0.303 | 0.813 | 0.242 | -0.076 | -0.039 |
| **production** | isotropic | **+0.254** | 0.488 | 1.967 | 0.237 | -0.122 | +1.251 |
| **production** | rooftop | **+0.242** | 0.264 | 0.608 | 0.283 | -0.033 | +0.493 |
| **production** | street | **-0.189** | 0.557 | 1.744 | 0.355 | -0.076 | -0.333 |

All figures in dB. `outputs/cross_validation/korenmarkt_250m_15ghz.json`.

In the `diffuse` mode the mean absolute deviation is 0.10 to 0.30 dB against a
Monte Carlo floor of 0.24 to 0.26 dB, so the two tools agree **at the resolution
of the comparison** and a tighter statement would need more sky samples rather
than better physics. The `production` mode sits at a quarter of a decibel, with
the residual carried by the multipath term and pointing the way the contaminated
specular branch points.

### 6.2 Brussels Grand Place, 250 m crop, 15 GHz

| mode | model | median | mean abs | max abs | MC floor | direct term | multipath term |
|---|---|---|---|---|---|---|---|
| specular | isotropic | +0.941 | 1.017 | 2.459 | 0.324 | -0.240 | +3.120 |
| specular | rooftop | +0.916 | 0.864 | 1.613 | 0.377 | +0.049 | +1.620 |
| specular | street | +0.556 | 0.564 | 0.929 | 0.461 | +0.344 | +0.684 |
| **diffuse** | isotropic | **-0.225** | 0.200 | 0.353 | 0.294 | -0.240 | -0.162 |
| **diffuse** | rooftop | **+0.044** | 0.210 | 0.692 | 0.335 | +0.049 | +0.039 |
| **diffuse** | street | **+0.305** | 0.319 | 0.521 | 0.265 | +0.344 | +0.279 |
| **production** | isotropic | **+0.154** | 0.229 | 0.568 | 0.293 | -0.240 | +1.209 |
| **production** | rooftop | **-0.025** | 0.240 | 0.776 | 0.324 | +0.049 | -0.120 |
| **production** | street | **-0.059** | 0.400 | 0.666 | 0.361 | +0.344 | -0.227 |

All figures in dB. `outputs/cross_validation/brussels_grandplace_250m_15ghz.json`.

The second site reproduces the first in every respect that matters. The shipped
configuration agrees to within 0.16 dB on the median and 0.78 dB on the worst
standpoint of any model, the roughness matched diffuse mode agrees to within
0.31 dB on the median, and the specular mode carries the same one decibel positive
bias in the same direction with the same signature of a contaminated multipath
term against a clean direct term. Re-tracing the published manifest reproduces it
to a maximum of 0.065 dB.

Brussels is a different square in a different city with a different street
geometry, so this is a genuine second test of the mapping rather than a repeat of
the same solve.

### 6.3 Why the diffuse agreement transfers to the shipped configuration

The `diffuse` mode is the one where neither tool's answer depends on the tessellation and
where they agree to 0.11 dB at Korenmarkt and 0.31 dB at Brussels. The shipped
configuration is `production`. The bridge is that **on these meshes the
estimator's own answer barely depends on the roughness model at all**:

| estimator, relative to `production` | Korenmarkt iso | roof | street | Brussels iso | roof | street |
|---|---|---|---|---|---|---|
| `specular`, median | -0.032 | +0.076 | +0.049 | -0.072 | +0.202 | +0.068 |
| `specular`, max abs | 0.096 | 0.167 | 0.489 | 0.140 | 0.303 | 0.337 |
| `diffuse`, median | +0.141 | -0.194 | -0.127 | +0.037 | -0.719 | +0.061 |
| `diffuse`, max abs | 0.267 | 0.655 | 3.367 | 0.474 | 1.575 | 2.448 |

All figures in dB. The metre scale faceting of the mesh dominates the sub
millimetre Rayleigh split, so the configuration in which the oracle is trustworthy
sits close to the configuration the paper ships. On the median, five of the six
site and model pairs are within 0.2 dB and the sixth, Brussels rooftop, is 0.72 dB
away.

The worst cases are worth naming rather than hiding. The largest excursions, 3.4
dB and 2.4 dB, are both single standpoints in the street small cell model, whose
susceptibility at those standpoints is of order 1e-4, four orders of magnitude
below the isotropic value at the same place. That model concentrates all its
illumination in an elevation band from 0.95 to 33 degrees, so a standpoint in a
closed square sees almost none of it and a decibel there is a decibel on almost no
absorbed power. The bridge argument is a median argument and is stated as one.

> **Old illumination law, see `LAW_CHANGE.md`.** The bridge table is read through the
> old models on four of its six columns, and the 0.95 to 33 degree band named in the
> paragraph above is the old street model's support. The argument that the estimator
> barely depends on the roughness model survives in kind, and every rooftop and
> street decibel in the table is old law weighted.

### 6.4 The estimator leg is the published run

Re-tracing the eight Korenmarkt standpoints at the published per location seed
reproduces the manifest to a maximum absolute difference of **0.00098 dB**
isotropic, 0.0099 dB rooftop and 0.083 dB street small cell over all standpoints,
the last being a model whose susceptibility is 3.5e-4 at its smallest. Brussels
reproduces to 0.065 dB worst over all three models. So the numbers being validated
are the numbers in the paper and not a reimplementation of them.

It is not a bit identical reproduction and should not be quoted as one. The
published manifest starts Russian roulette at the third interaction and the
current `TraceConfig` starts it at the fourth, so the two ray streams diverge
wherever roulette fires, and the residual above is that divergence rather than
zero. Both legs are at four interactions and 200,000 rays, and the oracle is at
four interactions as well.

> **Old illumination law, see `LAW_CHANGE.md`.** The reproduction residuals are given
> per model, 0.00098 dB isotropic, 0.0099 rooftop and 0.083 street. That the
> estimator leg is the published run survives, because it is a statement about seeds
> and ray streams, and the two directional residuals are old law numbers.

## 7. What is truncated, and what it costs

`MONOSTATIC_SBR.md` section 9.1 sets the acceptance rule: the smallest parameter
whose step to the next changes the median location by less than 0.5 dB, with 95 %
of locations changing by less than 1 dB. Twelve standpoints per site from the
published manifest, Russian roulette disabled on both curves so that truncation is
the only effect measured. `convergence_korenmarkt_250m.json` and
`convergence_brussels_grandplace_250m.json` in `outputs/cross_validation/`.

The dynamic range curve has not been computed before. `MONOSTATIC_SBR.md` section
9.1 asks for it and no file under `outputs/` records one. The bounce curve exists
in `outputs/exposure_korenmarkt/exposure_convergence.json`, at one standpoint at
the 130 m crop and only at the deep end, and `BOUNCE_BUDGET.md` measures the step
from four to three over forty standpoints. What is added here is the shallow end
at both sites, which is where the curve is steep and where the acceptance rule of
section 9.1 actually bites.

### 7.1 Bounce count

Median absolute change in `chi`, in dB, per step, with the 95th percentile over
the twelve standpoints in brackets.

| site | model | 1 to 2 | 2 to 3 | 3 to 4 | 4 to 5 | 5 to 6 |
|---|---|---|---|---|---|---|
| Korenmarkt | isotropic | 0.077 (0.148) | 0.009 (0.024) | 0.001 | 0.0002 | 0.0000 |
| Korenmarkt | rooftop | 0.159 (0.405) | 0.018 (0.064) | 0.003 | 0.0004 | 0.0000 |
| Korenmarkt | street | 0.347 (0.905) | 0.050 (0.199) | 0.008 | 0.0016 | 0.0001 |
| Brussels | isotropic | 0.168 (0.300) | 0.020 (0.041) | 0.003 | 0.0004 | 0.0001 |
| Brussels | rooftop | 0.392 (0.650) | 0.066 (0.122) | 0.010 | 0.0013 | 0.0002 |
| Brussels | street | **0.589 (1.710)** | 0.106 (0.374) | 0.019 | 0.0034 | 0.0005 |

**Under the paper's own acceptance rule the answer is one surface interaction at
Korenmarkt and two at Brussels Grand Place.** At Korenmarkt the step from 1 to 2
is under 0.5 dB on the median and under 1 dB at the 95th percentile for all three
models, so `L = 1` passes outright. At Brussels the street small cell model fails
both clauses at `L = 1`, at 0.589 dB median and 1.71 dB at the 95th percentile,
and passes comfortably at `L = 2`. The other two models pass at `L = 1` at both
sites.

That the tighter site is Brussels and the tighter model is street small cell is
the expected direction rather than a surprise: a low elevation source has to reach
the standpoint around a corner, so its contribution is carried by later
interactions than a rooftop source's is.

The shipped operating point of three interactions is therefore conservative by one
to two interactions, and the four used in older manifests by two to three. This
does not contradict section 8.3's 0.0004 dB between `L=4` and `L>=6`. It measures
what that table does not: the step at the shallow end, where the curve is steep,
over twelve standpoints at two sites rather than one standpoint at one. The honest
summary is that the operating point is deeper than any convergence criterion
requires, and that the argument for three is the one `BOUNCE_BUDGET.md` makes
about how far the photographic evidence reaches, which is not a convergence
argument.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows, and the
> `L = 2` verdict at Brussels that the street row alone sets, are steps measured
> under the old band weights. The finding that the shipped three interactions is
> deeper than the criterion needs survives, because the isotropic column gives it on
> its own, and the two directional columns move.

### 7.2 Dynamic range

The floor is referenced to each standpoint's own strongest component, which in
this estimator is unambiguous: a ray that escapes without touching anything
carries throughput exactly 1 and nothing can carry more, so `D` dB below the
strongest component is a throughput floor of `10^(-D/10)` with no per location
renormalisation. This is the referencing `MONOSTATIC_SBR.md` section 7.8 insists
on and warns against getting wrong, and in the adjoint formulation it costs
nothing to get right. Russian roulette off, six interactions, so the prune is the
only loss. Median over twelve standpoints of the `chi` lost, in dB.

| site | model | 5 dB | 10 dB | 15 dB | 20 dB | 25 dB | 30 dB and beyond |
|---|---|---|---|---|---|---|---|
| Korenmarkt | isotropic | 0.912 | 0.076 | 0.042 | 0.0045 | 0.0010 | 0 |
| Korenmarkt | rooftop | 1.079 | 0.141 | 0.072 | 0.0083 | 0.0024 | 0 |
| Korenmarkt | street | 1.781 | 0.353 | 0.179 | 0.0251 | 0.0073 | 0 |
| Brussels | isotropic | 1.130 | 0.147 | 0.066 | 0.0085 | 0.0027 | 0 |
| Brussels | rooftop | 1.517 | 0.278 | 0.136 | 0.0196 | 0.0060 | 0 |
| Brussels | street | 2.442 | 0.537 | 0.294 | 0.0457 | 0.0140 | 0 |

**The asserted 25 dB budget is sufficient with a large margin and is not
necessary.** A 20 dB budget already meets a 0.1 dB criterion on every model at
both sites, a 15 dB budget meets 0.5 dB, and by 30 dB nothing is pruned at all on
any standpoint of either site, which is the same statement as the bounce curve
reaching zero: at six interactions on these meshes almost no surviving throughput
is that far down.

`MONOSTATIC_SBR.md`'s summary line, "4, not 3, if the dynamic range budget is
25 dB or deeper", is not supported by this measurement in either half. Three
interactions is one to two more than the criterion needs, and 25 dB is five to ten
more than the criterion needs. Nothing here argues for reducing either, since both
are already paid for and the cost of being deeper than necessary is compute rather
than credibility. It does argue against citing 4 and 25 dB as measured minima.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows are the
> `chi` lost to the prune, weighted by the old models. The conclusion that 20 dB
> already meets a 0.1 dB criterion survives on the isotropic column, and the two
> directional columns need recomputing.

### 7.3 Diffraction, the one mechanism the estimator does not have

The estimator has no diffraction at all. `PAPER_METHODS.md` section 9.3 bounds
the omission rather than measuring it, and the oracle can measure it directly,
because turning Sionna's first order wedge diffraction on changes only that.

Same eight Korenmarkt standpoints, same 3000 sky directions, `diffuse` mode so
that the specular contamination of section 5 is not in the way, everything else
identical. `outputs/cross_validation/korenmarkt_250m_15ghz_diffraction.json`.

| model | median on total `chi` | worst standpoint | median on the multipath term |
|---|---|---|---|
| isotropic | +0.008 dB | +0.018 dB | +0.035 dB |
| rooftop | +0.013 dB | +0.043 dB | +0.059 dB |
| street small cell | +0.011 dB | +0.033 dB | +0.029 dB |

**First order diffraction is worth about a hundredth of a decibel of
susceptibility at these standpoints**, and the agreement with the estimator is
unchanged to within the Monte Carlo floor when it is switched on. That is a
measurement of the omission rather than a bound on it, and it is two orders of
magnitude below the residual the comparison itself carries.

Two limits on how far that number travels. It is first order only, so a second
order shadowed path is not in it. And these eight standpoints are in an open
square with a wide sky view, where the direct term dominates and there is little
for a wedge to add. A standpoint in a closed courtyard with no sky is the case
where diffraction should matter and it is not sampled here.

> **Old illumination law, see `LAW_CHANGE.md`.** The three rows are the diffraction
> increment integrated against the old models. The finding that first order
> diffraction is worth about a hundredth of a decibel survives, because it is two
> orders of magnitude below anything a reweighting can move, and only the rooftop and
> street values change.

## 8. What the paper may claim, and what it may not

The validation section can now make the claim, with the scope stated. Three
sentences that are all supported by the tables above:

- An adjoint estimator of this kind can be checked against an independently
  written forward solver by placing a transmitter at the standpoint and a receiver
  at 20 km, and the two agree at Korenmarkt and Brussels Grand Place to within
  0.25 dB on the median in the shipped configuration, over three illumination
  models, against a Monte Carlo floor of about 0.25 dB.
- In the fully diffuse configuration, where the roughness model is an exact match
  rather than an approximate one and neither tool's answer depends on the
  tessellation, they agree to within 0.31 dB on the median.
- The check covers the propagation kernel. It does not cover the illumination
  law, the mesh, the crop or the material constants, all of which are shared
  inputs and would move both tools identically.

Three things the paper may **not** claim on this evidence.

- It may not claim that the direct term agreeing validates anything. It is the
  same BVH on both sides.
- It may not quote the `specular` mode agreement. Section 5 shows the oracle
  manufactures energy there.
- It may not describe this as a measurement. It is a comparison of two
  simulations that share their geometry and their illumination.
- It may not claim the polarisation approximation is validated. Section 3.1 shows
  the estimator's product of averages and the oracle's average of products
  separate on chains of more than one interaction, so the residual reported here
  contains that error rather than excluding it, and it is measured on meshes whose
  mean interaction count is 1.6.

If the paper wants a single number, the defensible one is **0.25 dB median
agreement with an independent solver on the shipped configuration at two sites,
with the illumination law explicitly out of scope**.

> **Old illumination law, see `LAW_CHANGE.md`.** The two agreement figures the paper
> is told it may claim, and the phrase "over three illumination models", rest on the
> old rooftop and street weights. The scope sentence, that the check covers the
> propagation kernel and not the illumination law, survives and is the part to keep,
> and the two decibel figures have to be restated once the facade tip law settles.

### 8.1 The two places the paper currently says this is missing

Neither is edited here, because this document does not own them. Both are now
false in the direction of understating what exists.

`PAPER_METHODS.md` section 8.1, under "What section 8 cannot catch", says "There
is no independent solver in the loop: nothing here is a comparison against a
second implementation of the same problem". The second half of that sentence, "and
no measurement is taken anywhere in this work", remains true and should stay.

`PAPER_METHODS.md` section 11 carries the row "Section 8, external cross
validation | **absent.** The tracer is checked against closed forms it was built
to satisfy, plus internal invariants. There is no independent solver in the loop,
so a shared conceptual error would survive every test in section 8". The last
clause is still true for one specific shared conceptual error, the illumination
law, and that is worth keeping and narrowing to it.

## 9. Reproducing

```bash
python -m semantic_twin.transport.sionna_check plane
python -m semantic_twin.transport.sionna_check tessellation
python -m semantic_twin.transport.sionna_check tessellation --jitters-mm 0.001,0.01,0.05,0.2,0.5,2 --tag _lowend
python -m semantic_twin.transport.sionna_check site --site korenmarkt --locations 8 --sky-samples 3000
python -m semantic_twin.transport.sionna_check site --site brussels_grandplace --locations 8 --sky-samples 3000
python -m semantic_twin.transport.sionna_check site --site korenmarkt --locations 8 --sky-samples 3000 --modes diffuse --diffraction
python -m semantic_twin.transport.sionna_check sampling
python -m semantic_twin.transport.sionna_check convergence --site korenmarkt --locations 12
python -m semantic_twin.transport.sionna_check convergence --site brussels_grandplace --locations 12
SIONNA_ORACLE_TESTS=1 python -m pytest tests/test_sionna_check.py -n 0
```

The oracle runs on Modal against an L4 by default, because a single 3000 direction
diffuse solve on the Korenmarkt mesh takes about five minutes there and would take
hours on this box. Pass `--local` to run the oracle in process instead, which
needs `sionna-rt` importable and will pick the LLVM Mitsuba variant.

Importing `sionna.rt` sets the Mitsuba variant process wide, which is why the two
tests that need a live oracle shell out to a subprocess rather than importing it
into the suite. Those two are gated behind `SIONNA_ORACLE_TESTS` so that the
default suite stays fast, and the other sixteen tests run unconditionally.

# Code audit

An independent correctness review of the adjoint SBR estimator and the code
around it, run on 2026-08-02 against the working tree of
`feature/coherent-exposure-studio`. Written to be read alongside
`PAPER_METHODS.md` section 8, whose validation set it extends.

Four findings, in order.

**The estimator is correct.** Every part of the physics that could be checked
against an exact answer was checked against one and agrees to a part in a
thousand, including four quantities that had no closed form target before this
audit: the susceptibility itself under a named illumination law, the Rayleigh
specular and diffuse split, Russian roulette's unbiasedness, and the angular
spectrum cell by cell.

**The evidence ladder negative survives the Monte Carlo noise, but one of its
rows is a bad draw.** There was no error bar anywhere in the repository, so one
was measured: the 120 published Korenmarkt standpoints retraced over eight seed
streams, both rungs, at the exact production config. The isotropic and rooftop
shifts clear the noise by 105 and 22 standard errors. The street small cell
shift does not read as published. Its true value is 0.167 +/- 0.022 dB and the
printed 0.079 dB is the lowest of eight draws, which changes what the row says.

> **Old illumination law, see `LAW_CHANGE.md`.** The isotropic, rooftop and street
> shifts in this finding are integrals against the old height band and range band
> models. The isotropic figure survives, and so does the finding that the published
> street row is the lowest of eight draws, while both directional values have to be
> measured again.

**The bounce depth the paper claims is not the one several published runs
used.** The paper describes "the four bounce operating point". The headline
eleven city figure is at 4, the evidence ladder is at 6, the class default is 12
and the CLI default is 6. The numerical cost is negligible and the documentary
problem is not.

**One outright bug, in code too new to have published anything.** The antenna
module's `LoadedBeam` averaged the array factor over the served user on the
midpoint rule's weights and the trapezoid rule's nodes, which is first order
rather than second and was 29 percent wrong at the node counts it shipped with.
Its own test caught it. Section 11.

Everything else found is small, and is listed in section 6.

---

## 1. Baseline

| check | before | after |
|---|---|---|
| `pytest tests/ -q` | 739 passed, 1 skipped, 110 s | 975 passed, 2 skipped, 388 s |
| `ruff check .` | all checks passed | all checks passed |
| `ruff format --check .` | 10 files would be reformatted | 167 files already formatted |

The tree ends green. One of the two skips is `test_infer_unidepth.py`, which
needs a model checkpoint that is not on this box. No test was failing at the
start, eleven failed at one point or another in between, none is failing at the
end, and not one of them was made to pass by weakening what it asserts. The 236
tests that appeared in between are other agents' work.

Two warnings about that number. Other agents were still writing when it was
taken, so it is a reading of a moving tree rather than a fixed one, and one file
was caught mid write during an earlier pass, which produced a failure that
cleared on its own once the write finished. And `ruff format` had to be run over
the whole directory to get the third row, touching 11 files that other agents
own. Formatting cannot change behaviour and the suite was re-run after it, but
anything committed after this will need the sweep repeating.

Of the eleven, seven were one regression in the Blender stage and four were in
the new antenna module. The antenna four are section 11, and two of them were
real bugs.

The seven were in `tests/test_propagation_viz.py` and all seven read
`ModuleNotFoundError: No module named 'mathutils'` at
`propagation_blender.py:57`:

    test_camera_rotation_actually_points_at_the_target
    test_colour_ramp_is_monotone_and_clamps
    test_ray_bundles_are_exclusive_and_exhaustive
    test_octahedra_build_one_closed_marker_per_centre
    test_clear_view_avoids_a_blocked_bearing_rather_than_shortening_it
    test_clear_view_prefers_the_lowest_open_elevation
    test_clear_view_climbs_when_every_bearing_at_low_elevation_is_shut

Root cause, traced rather than guessed. Commit `94b05247`, "Put the evidence the
twin is built from into the blend", timestamped 23:57 on 2 August and therefore
after this audit's baseline, added `import mathutils` to the module level of
`propagation_blender.py`. `mathutils` ships inside Blender and is not in the
venv. The test file's loader, `blender_module()` around line 179, stubs `bpy`
and only `bpy`, on the invariant its own docstring states: the module level is
deliberately free of Blender calls so the pure geometry in the file stays
testable outside Blender. The import now fails before any test body runs, which
is why all seven go together and why the failure is an import error rather than
an assertion.

The fix belongs in the source, not in the test. `mathutils` is used at exactly
two places, `mathutils.Matrix` in `build_panoramas` and `mathutils.Euler` in
`frame_the_viewport`, both inside functions that already handle `bpy` objects
and so can only ever run inside Blender. The import now sits inside those two
functions, which restores the invariant and changes nothing under `blender -P`.
Stubbing `mathutils` alongside `bpy` in the test loader would also have gone
green, and would have hidden a real new hard dependency, so it was the worse of
the two. All 16 tests in that file pass again. The agent that owns the file was
told, so it does not come back.

Python is `/home/user/aegis/.venv/bin/python` (3.12). There is no bare `python`
on this box's PATH, which is worth knowing before concluding the suite is
broken.

### Scope, and what moved underneath it

Other agents were editing this tree throughout, fast. The package went from 2186
to well over 6000 lines during the audit, so more than half of
`semantic_twin/propagation/` is newer than this review of it.

Four modules appeared or grew mid audit and are **not covered**: `antenna.py`
(903 lines), `bystanders.py` (1447), `sionna_check.py` (712) and
`material_posterior.py` (159), plus growth in `walk.py` (175 to 340 lines) and
`semantic_binding.py` (352 to 509, gaining a `bind_from_walk_material` entry
point that `run_exposure.py` already imports).

`antenna.py` is the partial exception. It is not audited, but the three of its
tests that were failing were taken to root cause, which is section 11, so the
`PlanarArray` beamwidth, the `source_frame_angles` seam and the whole of
`LoadedBeam`'s user quadrature have been looked at properly. Nothing else in it
has.

The estimator core did not stay still either. `tracer.py` grew from 21.8 to
34.4 kB and `directions.py` from 15.0 to 21.3 kB after the measurements in
sections 2, 4 and 6 were taken, presumably to carry the antenna work. Two
things follow. Every number in this report is against the code as it stood when
that number was taken, and the line and byte references may have moved. And the
new closed form tests were re-run against the extended `tracer.py` and
`directions.py` at the end, where all nine still pass, so the estimator is still
correct after those changes and the tests are already earning their keep as a
regression guard on a moving target.

---

## 2. What was verified against an exact answer

The estimator was checked against a closed form for an infinite half space under
the observation point, derived independently and implemented in
`tests/test_propagation_closed_form.py` with no code shared with the package:

    chi = int_up Q dOmega
        + int_up R(u_z) kappa(u_z) Q(u) dOmega
        + I_cos * 2 pi int_0^1 R(s) (1 - kappa(s)) ds

The three terms are the ray that escapes untouched, the ray that reflects
specularly, and the ray the Rayleigh split sends into the Lambertian lobe.
`I_cos = (1/pi) int_up Q(v) v_z dOmega`. Only one bounce is possible off an
upward facing plane, so the target is exact rather than truncated.

Measured against it, at 800k rays over 24 independent seeds:

| illumination | mean residual | sd | worst of 24 |
|---|---|---|---|
| isotropic | -0.00002 | 0.00011 | 0.00021 |
| rooftop | -0.00014 | 0.00212 | 0.00475 |
| street small cell | -0.00130 | 0.00367 | 0.00860 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows are
> residuals against a closed form evaluated with the old models. The closed form
> above holds for any illumination density, so the check itself survives and only its
> two directional rows have to be taken again.

and across five material and roughness combinations at 2M rays, every ratio to
the closed form lands between 0.9998 and 1.0012.

That result clears, simultaneously and at the level of the published quantity
rather than a diagnostic:

- the unpolarised Fresnel power average,
- the Rayleigh coherent fraction `kappa = exp(-g**2)` being a **power** share
  and not an amplitude one,
- the incoherent remainder `1 - kappa` being conserved into the Lambertian lobe
  rather than dropped,
- the cosine hemisphere sampler's normalisation,
- the `4 pi / N` quadrature constant,
- `nearest_cell` binning,
- the illumination density normalisation,
- Russian roulette's unbiasedness.

### 2.1 Russian roulette is unbiased, verified rather than argued

The implementation survives with probability `p = clip(w, 0.05, 1)` and then
divides the survivor's weight by the same `p`, which is textbook and unbiased.
In production it starts at bounce 3, which on a plane never fires, so no test
had ever exercised it against a known answer.

Moving it to bounce 1 kills 36 percent of the rays before they can deposit and
inflates the survivors by up to twenty times. `chi` does not move: it still
meets the closed form above within tolerance, for all three illumination models.
`test_russian_roulette_from_the_first_bounce_does_not_move_the_closed_form`
pins this.

### 2.2 The specular versus diffuse branch is unbiased for the reason claimed

One lobe is sampled per bounce with probability equal to its own energy share
and no compensating weight, which is correct precisely because the estimator's
`1/p` and the split's `p` cancel. Verified two ways. Directly, by the two branch
closed form above, which separates the branches and would fail if either were
mis-weighted. Indirectly and without any reference to a closed form, by the fact
that the total escaping power off a lossless plane does not move across a factor
of a thousand in roughness: `chi_isotropic` stays within 1e-3 of 1 at RMS
heights from 0 to 1 m, and the spread across the whole sweep is under 1e-3.

### 2.3 The angular spectrum, per cell

`rho` is what the body side actually consumes and nothing had ever checked it
cell by cell. Over a smooth dielectric plane under isotropic illumination every
cell has an exact target, the mean over that cell's Voronoi region of

    f(u) = 1 if u_z > 0 else R(|u_z|)

Comparing against `f` at the cell centre instead is wrong by up to 7 percent
near grazing and in one direction, because `R` is convex there. Integrating over
the cell removes that and lets the horizon straddling cells be tested rather
than excluded. Result: every cell within 2 percent, the mean within 0.2 percent,
and the cells lying wholly above the horizon agree with each other to 5e-14.

Those clean cells miss 1 by a constant 2.06e-11. It is not roundoff. It is the
trapezoid error of `IlluminationModel.normalisation()` for the isotropic model,
whose exact value is `4 pi`: two hundred thousand abscissae over a half turn
leave `h**2/6` behind. Harmless, and now named in a test rather than sitting
unexplained, because an unexplained constant offset in `rho` is exactly what a
lost quadrature factor would look like.

---

## 3. The tests now reject specific mistakes

`PAPER_METHODS.md` section 8 was strong against implementation error and blind
to formulation error, and the audit brief asked whether the closed form set
would break on a plausible sign error or factor of two. For the previous set the
honest answer is **partly, and not where it mattered most**.

Every closed form target the suite had for `susceptibility`, the published
quantity, was independent of the illumination law:

- free space gives `chi = 1` because `Q` integrates to 1, whatever its shape,
- a perfect conductor under any illumination confined above the horizon gives
  `chi = 2`, again whatever the shape.

Replace the elevation law with a completely different function of elevation,
keep it normalised and above the horizon, and both targets are still met
exactly. That is the shape of the defect section 2.7 of `MONOSTATIC_SBR.md`
records. The law formulation itself *is* well tested, by
`test_the_band_law_matches_the_population_it_claims_to_describe`, which draws
the site population and refutes the superseded law at hundreds of sigma. What
was missing was any target that ties the law to the estimator that consumes it.

The rest of the old set does have teeth: the dielectric plane exit profile
rejects the TE only reading band by band, and the Lambertian and Rayleigh tests
constrain the diffuse branch. But all of that is `exit_profile`, which nothing
downstream reads.

The new targets are law dependent by construction: the three illumination models
land on 0.644, 1.446 and 1.751 over the same plane, a spread of 4.3 dB.
`test_the_two_branch_target_rejects_four_specific_implementation_errors` pins
the separation from four plausible mistakes, at 10 mm RMS on concrete:

| mistake | rooftop | isotropic | street small cell |
|---|---|---|---|
| coherent fraction read as an amplitude, `exp(-g**2/2)` | +5.6 % | 0.0 % | +2.0 % |
| incoherent remainder dropped instead of scattered | -6.0 % | -15.2 % | -1.3 % |
| TE only instead of the unpolarised average | +11.1 % | +12.2 % | +8.1 % |
| diffuse lobe uniform instead of cosine | +9.4 % | 0.0 % | +10.3 % |
| Fresnel amplitudes averaged before squaring | -4.3 % | -8.6 % | -1.1 % |

Two of the zeros are real and are asserted as skips rather than papered over:
isotropic illumination cannot see the lobe shape at all, because the cosine mean
and the uniform mean of a constant are the same number, and it cannot see the
`kappa` power either, because both branches sample the same constant `Q`. The
rooftop law sees all four, which is the one to reach for.

> **Old illumination law, see `LAW_CHANGE.md`.** The 0.644, 1.446 and 1.751 targets,
> the 4.3 dB spread and every percentage in the table are computed under the old
> models, and the band law test named above tests the law this change replaces. The
> design survives, because a law dependent target is exactly what was missing, and
> the targets themselves have to be regenerated.

New file: `tests/test_propagation_closed_form.py`, 9 tests, 74 to 200 s
depending on how loaded the box is. That is a real cost against a 110 s suite
and it is deliberate: these are the only targets in the repository that
constrain the published number rather than a diagnostic.

---

## 4. Defect: there is no Monte Carlo error bar anywhere

This is the most important finding.

`PointResult` carries no variance and no standard error, no run under `outputs/`
reports one, and nothing in `PAPER_METHODS.md` quotes one. The estimator is
stochastic from the first interaction, not only at the roulette: the specular
versus diffuse choice is a coin flip on the Rayleigh share and the diffuse
directions are cosine sampled. Seeds are fixed, so runs reproduce, but
reproducible is not converged.

So it was measured. The 120 published Korenmarkt standpoints of
`clean_geometric_15ghz` were retraced at the exact production config (200k rays,
512 cells, 6 bounces, 130 m crop) over eight disjoint seed streams. Replica 0
uses the published stream and **reproduces the stored file to 0.00e+00** at
every one of the 120 standpoints and all three illumination models, so the
comparison is against the real thing and not a near miss.

### 4.1 How big the noise is

| illumination | per standpoint sd, median | p90 | worst of 120 | sd of the walk median |
|---|---|---|---|---|
| isotropic | 0.004 dB | 0.006 dB | 0.015 dB | 0.0042 dB |
| rooftop | 0.024 dB | 0.040 dB | 0.066 dB | 0.0136 dB |
| street small cell | 0.118 dB | 0.224 dB | 0.954 dB | 0.0343 dB |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows are
> noise floors on old law integrals, and the thirty degree support named just below
> is the old street model's. The isotropic row survives, and so does the explanation,
> that the variance follows how much of the ray budget lands inside the support of
> `Q`, which will hold for the facade tip law too.

The factor of thirty between isotropic and street small cell is not a surprise
once stated. The variance is set by how much of the ray budget lands inside the
support of `Q`, and the street law crowds its whole mass into the first thirty
degrees of elevation, so most rays contribute nothing to it. The same ordering
will hold at every site, so it is a property of the illumination model rather
than of Korenmarkt.

### 4.2 The evidence ladder negative survives, and one of its rows does not

The ladder shift was measured the way it is quoted: paired, both rungs at the
same seed, so the 120 published standpoints of `clean_walk9` were retraced over
the same eight streams. Both replica 0 runs reproduce their stored files to
0.00e+00. The shift is then eight independent measurements of the same
difference:

| illumination | shift per seed, dB | mean | sd of one run | published, seed 7 |
|---|---|---|---|---|
| isotropic | 0.350 0.344 0.343 0.346 0.349 0.349 0.344 0.352 | **+0.347** | 0.0033 | 0.3498 |
| rooftop corrected | 0.364 0.396 0.385 0.416 0.366 0.386 0.383 0.371 | **+0.383** | 0.0170 | 0.3642 |
| street small cell | 0.079 0.269 0.211 0.155 0.095 0.162 0.207 0.160 | **+0.167** | 0.0624 | 0.0785 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows are
> shifts of old law integrals, and the caveat below about the superseded fixed height
> `1/sin**3` law now covers the band law that replaced it as well, since the facade
> tip law supersedes both. That the published street number is the lowest of eight
> draws survives, because it is a statement about draws from one distribution.

**The ladder negative is not a noise artefact.** The isotropic shift is 105
standard errors from zero and the corrected rooftop shift 22. The section 9
conclusion stands, and the reason is worth putting in the paper: a median over
120 standpoints averages the per standpoint noise down by roughly the square
root of 120, so a 0.024 dB per standpoint error becomes a 0.017 dB error on the
shift of the median.

**The street small cell row is a different story and it should be corrected.**
The effect is real, 2.7 standard errors on a single run and 7.6 on the mean of
eight. But the published 0.079 dB is **the lowest of the eight draws**, and the
eight run from 0.079 to 0.269, a factor of 3.4. The honest value is
**0.167 +/- 0.022 dB**, which is more than twice what is printed.

That matters because of what the row is used for. Section 9 reads the four rows
as a trend, with the shift shrinking as the illumination gets more directional,
0.350 isotropic, 0.364 rooftop, 0.079 street. On the seed averaged numbers the
trend is 0.347, 0.383, 0.167, which is a much weaker ordering and no longer a
monotone one. The single seed table happened to draw the low tail on the noisiest
row.

Two smaller caveats.

- **The 0.298 dB figure, which is the one the section 9 ladder table leads with,
  was not measured here** and cannot be inferred from the rows above. It is
  computed under the superseded fixed height law, which this run does not carry.
  Its noise is certainly *larger* than the corrected rooftop row's, by the same
  argument `test_free_space_identity` already makes: a `1/sin**3` law
  concentrates its mass in a solid angle a uniform ray set barely samples, and
  that test has to loosen its tolerance by a factor of 2.5 for exactly the two
  superseded laws. If the penalty in the city is the same factor, the shift is
  still about eight standard errors and survives, but that is an inference and
  the measurement is one eight replica run away.
- **The crop correction is not a paired comparison.** It changes the mesh, so
  the two runs decorrelate at the first bounce and the error on the difference
  is the independent one, about `sqrt(2) * 0.0136 = 0.019` dB for rooftop. The
  4.80 dB end of the published "0.05 to 4.80 dB" range is 250 standard errors
  and beyond argument. The 0.05 dB end is 2.6, which is not a measurement. The
  range should carry a floor, something like "below 0.05 dB the correction is
  not resolved at this ray count".

Also worth recording: the semantic binding is *noisier* than the geometric one,
because it puts more distinct roughness classes into the scene and so more
weight on the stochastic Rayleigh branch. The walk median sd goes from 0.0136 to
0.0199 dB for rooftop and from 0.0343 to 0.0594 dB for street small cell. Any
future ablation that adds material variety inherits that.

### 4.3 The "N of 120 move by more than 1 dB" counts

These are per standpoint statistics, so they inherit the per standpoint error
rather than the median's. Measured directly, by counting standpoints that move
more than 1 dB across the rung at each seed, against a control that counts
standpoints moving more than 1 dB between two replicas of the **same**
configuration:

| illumination | across the rung, 8 seeds | from a seed change alone |
|---|---|---|
| isotropic | 17 17 17 17 17 18 18 18 | 0 0 0 0 0 0 0 |
| rooftop corrected | 8 8 8 7 8 8 8 8 | 0 0 0 0 0 0 0 |
| street small cell | 1 1 1 1 1 1 1 1 | 0 2 1 0 0 1 0 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows count
> standpoints crossing 1 dB on old law integrals, so those counts and the 0.12 dB
> street figure quoted at the end of the section move. The isotropic row survives,
> and so does the method, which is a count against a reseeded control.

The isotropic "17 of 120" and the rooftop "8 of 120" are solid: they barely move
across seeds and reseeding alone never produces a single crossing. The section 9
sentence that the per standpoint picture "is not a null and should not be quoted
as one" is correct and now has an error bar behind it.

**The street small cell "1 of 120" is inside the noise.** Reseeding the same
configuration produces between 0 and 2 standpoints crossing 1 dB, which brackets
the reported count. Its worst standpoint carries 0.954 dB of Monte Carlo scatter
on its own, so a single crossing there says nothing.

More generally, **no single street small cell susceptibility in any published
table is good to better than about 0.12 dB, and the worst standpoint is good to
about 1 dB.** Nothing in the outputs says so.

### 4.4 The cheap fix

The estimator already has everything needed for a per point error bar and throws
it away. `_deposit` accumulates the first moment of each ray's contribution into
`rho`. Accumulating the second moment alongside it is one more `np.add.at` per
illumination model, and because every ray lands in exactly one cell the cells
are independent, so

    Var(chi) = (4 pi / N_cells)**2 * sum_c s_c**2 / n_c

with `s_c**2` the within cell sample variance and `n_c` the cell's ray count,
both of which the extra accumulator gives directly. No repeat runs at all. That
is a much better answer than the eight seed brute force used here, which cost
about two hours of wall time for two configurations and is the reason this
audit could only afford to error bar one site.

---

## 5. Defect: the bounce depth is inconsistent across the repository

`PAPER_METHODS.md` section 5.2 and the figure 3 caption both describe "the four
bounce operating point". Provenance, read from the `trace_config` block of every
manifest under `outputs/`:

| artefact | `max_bounces` |
|---|---|
| eleven cities corrected at 250 m, the headline figure (`city250_corrected_*`) | 4 |
| crop convergence (`outputs/crop_convergence/`) | 4 |
| sub street ablation, hardcoded at `run_substreet_ablation.py:117` | 4 |
| law comparison, hardcoded at `run_law_comparison.py:65` | 4 |
| **evidence ladder** (`clean_geometric`, `clean_walk8`, `clean_walk9`, `sam3lad_*`) | **6** |
| superseded eleven cities (`city250_*`, `city_*`) | 6 |
| Korenmarkt walk and band law runs (`bandlaw_*`, `korenmarkt_walk`) | 6 |
| pilot | 12 |
| `TraceConfig.max_bounces` class default | 12 |
| `run_exposure.py --max-bounces` default | 6 |

So the paper's claim is true of the headline city figure and the two ablations,
and false of the evidence ladder, which is the result section 9 leans on hardest.
The two defaults disagree with the claim and with each other.

**Was the convergence measured?** Yes. `PAPER_METHODS.md:886` records
`chi = 0.29894` at `L=4` against `0.29902` at `L>=6`, so it was not inherited
from a recommendation. One caveat worth stating: those two numbers differ by
0.0012 dB, which is far inside the per standpoint Monte Carlo noise of section 4,
and read as independent measurements they would mean nothing. They are not
independent. `L=4` and `L=6` at the same seed trace *the same rays*, identical up
to bounce four, so the difference is paired and its error is orders of magnitude
smaller than either number's own error. The comparison is sound. It should say
so, because as written it invites the reader to apply the wrong error bar.

The numerical consequence of the inconsistency is small: every rung of the
ladder is at 6, so the ladder's internal comparison is self consistent, and 4
against 6 is worth 0.0012 dB. The problem is documentary, and it is the kind of
thing a reviewer checks.

(Another agent is recomputing the bounce convergence curve for
`CROSS_VALIDATION.md`. This section is the provenance half only and does not
duplicate it.)

---

## 6. Smaller defects, in order of how much they matter

### 6.1 `truncated_throughput_share` divides by the wrong thing for its name

`tracer.py:372`. The denominator is `delay_weight`, the throughput that
*escaped*, so the quantity is truncated over escaped and is unbounded above. It
is quoted in the section 8.3 convergence table as a "share", which reads as a
fraction of the power budget.

Truncating a plane at zero bounces separates the two readings by exactly a
factor of two and shows which one the code computes: half the rays escape upward
untouched and half are still travelling when the loop ends, so truncated over
escaped is 1 while truncated over the whole budget is 1/2. Measured: 0.9952 and
0.4988.

So the published `0.567` at one bounce means the discarded power was 57 percent
of the *retained* power, that is 36 percent of the budget. At the four bounce
operating point the two readings differ in the fifth decimal and nothing turns
on it. `test_the_truncated_throughput_share_is_a_ratio_to_the_escaped_power`
now pins the definition so it cannot drift silently.

### 6.2 The same diagnostic reads zero when everything was truncated

Same line. When nothing escapes, `delay_weight` is zero and the expression falls
back to `0.0`, which is the *healthy* value. A fully enclosed lossless cavity
discards 100 percent of its throughput and reports a truncated share of exactly
zero. Confirmed on `SphereGeometry(12.0)` at every bounce depth from 1 to 8.

`test_closed_lossless_cavity_conserves_energy` asserts `truncated_rays` but not
the share, so this is untested. No published standpoint is affected, because
`drop_enclosed` removes points with no sky, but the diagnostic that exists to
say "how much did I throw away" answers "none" exactly when it threw away
everything.

Not fixed here. The narrow fix is to return `float("inf")` or `float("nan")`
rather than `0.0`, but the value is streamed into JSONL, so the change belongs
with whoever owns the output schema.

### 6.3 The `uniform_sites_pathloss` law is dead and separately wrong

`directions.py:134` returns `1/(sin * cos**2)`. Free space spreading is `1/r**2`
in the slant range, which for a fixed height population gives `1/sin`. The
shipped expression is spreading in the *horizontal* range, wrong by `1/cos**2`,
which is a factor of 4 at 60 degrees.

`test_path_loss_on_horizontal_range_is_not_path_loss_on_slant_range` documents
this and `MONOSTATIC_SBR.md:393` says the law is kept so published numbers stay
reproducible. Two things do not line up with that:

- **No model instance uses it.** `VARIANTS` contains `uniform_sites` twice, the
  two band laws twice each and isotropic. Nothing reproduces anything through
  `uniform_sites_pathloss`, so it is 3 lines of unreachable branch.
- The module docstring describes `uniform_sites` and `uniform_sites_pathloss`
  together as "the uncorrected pair" whose defect is the fixed height versus
  band reading. That is the defect of `uniform_sites`. `uniform_sites_pathloss`
  has a second, unrelated one, and the docstring does not say so.

Consequence in the test suite: `test_propagation.py:375` widens a tolerance for
`model.law in ("uniform_sites", "uniform_sites_pathloss")`, and the second arm
can never be reached.

> **Old illumination law, see `LAW_CHANGE.md`.** Every law named in this section
> belongs to the old family, since `uniform_sites` and its path loss twin are fixed
> height laws and the two band laws in `VARIANTS` are their replacement. The defect
> is a code fact and survives, and the module it sits in is the one the facade tip
> law rewrites.

### 6.4 The per cell ratio estimator carries a small real bias

`chi` is computed as a sum of per cell means times the *nominal* solid angle
`4 pi / N`, not the cell's true Voronoi area, which on a Fibonacci sphere differs
by a few percent. The bias is second order, because for a constant integrand the
area deviations sum to zero, but it is not zero.

Measured against the exact closed form at 400k rays, 12 seeds, on the standard
error of the mean:

| cells | isotropic | rooftop | street small cell |
|---|---|---|---|
| 64 | -0.00015 | -0.00062 | -0.00263 |
| 256 | -0.00003 | +0.00099 | -0.00200 |
| 1024 | -0.00001 | +0.00049 | -0.00051 |
| 4096 | +0.00000 | +0.00025 | -0.00069 |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street columns are
> biases measured against the old models, and "the narrowest illumination law" below
> means the old street one. The finding that the bias shrinks with the cell count and
> stays well under the Monte Carlo noise survives, because it is a property of the
> quadrature rather than of the weights.

So at the production setting of 512 cells the binning costs a few parts in a
thousand on the narrowest illumination law and essentially nothing on the
others. It shrinks with the cell count, which is the signature of a cell mean
resolving a peaked `Q` rather than of a wrong weight.

This is well below the Monte Carlo noise of section 4 and does not threaten any
published number. It is documented as "to within a few percent" in
`fibonacci_sphere`, which understates how well it actually does.
`test_the_quadrature_constant_does_not_depend_on_the_cell_count` now bounds it.

### 6.5 Two statistics condition on a subset without saying so

- `mean_bounces` is `bounce_sum / escaped`, an average over escaped rays only.
  Rays killed by roulette or lost to truncation are exactly the deep ones, so it
  is biased low as an estimate of path depth. Fine as defined, undocumented as
  defined.
- `walk.py:149`, `candidates_after_clearance` in the walk provenance is recorded
  after both the clearance filter *and* the sky visibility filter, so it does
  not mean what it says. `candidates_rejected_as_enclosed` is recorded correctly
  beside it, so the number can be recovered.

### 6.6 No shape guard between `face_class` and the material tables

`SbrTracer.__init__` does not check that `permittivity` and `rms_height_m` are
the same length, nor that `face_class.max()` is inside them. In practice every
caller builds all three from the same `SurfaceBinding`, and an out of range
index raises loudly, so this is a latent rather than an active problem. Worth
noting because a negative class index would wrap silently instead, and
nothing currently produces one.

`MitsubaGeometry.intersect` does check the one shape that matters, `si.n` coming
back as `(3, N)`, and raises rather than transposing silently. That is the right
pattern and the rest of the tracer does not follow it.

---

## 7. Duplicated geometry on disk

Confirmed by `cmp`, not by size alone. Seven sites carry an `inhouse_leaf_250m_f64.ply`
that is **byte identical** to its `inhouse_leaf_250m.ply`:

| site | bytes |
|---|---|
| tokyo_hachiko | 22,785,344 |
| london_trafalgar | 22,585,130 |
| brussels_grandplace | 20,199,600 |
| madrid_plazamayor | 20,050,761 |
| mexico_zocalo | 19,588,860 |
| prague_staromestske | 18,526,939 |
| krakow_rynek | 15,245,510 |
| **total** | **138,982,144 (132.5 MiB)** |

`data/` is 4.1 GB and `outputs/` is 1.4 GB, all untracked.

**This is not a bug and the `_f64` suffix is not a lie, it is redundant.** The
two files came from two different tile downloads, `data/tiles250/<site>/` and
`data/tiles/<site>_250m/`, and the JSON sidecars differ only in
`source_manifest`, `output_ply` and one byte count. The f32 sidecar already
records `"placement_source": "glTF node matrices read in float64"` and
`"single_precision_fallback_objects": 0`, so the double precision placement path
was already the default by the time those sites were built and the second export
had nothing to change. Four sites do differ: korenmarkt, milan_duomo,
toulouse_capitole and newyork_timessquare, and korenmarkt's 118 triangle
difference is the one `semantic_binding.py` documents.

Two things follow, and the second is the interesting one. The 132.5 MiB is
recoverable. And the pipeline reproduced 138 MB of mesh bit for bit from two
independent tile fetches, which is a determinism result worth stating somewhere
rather than deleting.

Nothing deleted, per the brief.

---

## 8. Dead code and duplication

Nothing deleted, per the brief. Vulture is not installed in the venv and was not
installed. The census is an AST symbol extraction cross referenced against
`grep -w` over all 176 `.py` and `.md` files in the tree, with every candidate
hand checked for `__all__` exports and dynamic dispatch before being called dead.

**Read the totals with the repository's convention in mind.** Most top level
scripts here are manual pipeline stages chained only by name inside docstrings,
so "nothing imports it" is the normal state for a script and is not by itself a
defect. The counts below are the literal answer to the question asked.

### 8.1 Unreferenced symbols in the package, about 608 lines

- **`semantic_twin/propagation/sionna_check.py` is imported by nothing.** No
  module, script, test or figure references it, and the only mentions in the tree
  are prose in `MONOSTATIC_SBR.md` and `ROADMAP.md`. It was 532 lines when
  scanned and grew to 712 during the audit as another agent added
  `build_payload`, `run_payload` and `modal_app`, so it is work in progress
  rather than abandoned. Worth knowing anyway: eight of its own functions
  (`mode_materials`, `sample_sky`, `band_transfer`, `split_mesh_by_class`,
  `build_scene`, `recorded_susceptibility`, `median_change_db`,
  `smallest_converged`) and the `MODES` constant are not called even from
  inside the file. Given that this is the module that would provide the
  independent cross validation section 8 of the paper lacks, "unreachable"
  is the finding, not "delete it".
- Eleven orphaned symbols in otherwise live modules, 76 lines:
  `facade_vlm.png_bytes` (6), `facade_vlm.load_responses` (17),
  `facade_vlm.save_responses` (3), `fishnet.OCCLUSION_REJECTIONS` (1),
  `masonry.WALL_FLATNESS_TOLERANCE_MM` (1), `masonry.BELGIAN_JOINT` (7),
  `materials.PERIODIC_STRUCTURES` (1), `mmwave.resolution_quality` (11),
  `planes.connected_face_components` (10),
  `propagation/antenna.ELEMENT_GAIN_DBI` (1),
  `propagation/antenna.kernel_susceptibility` (18).

### 8.2 Top level scripts with no invoker, 2599 lines

`analyse_material_vlm.py` (281), `blind_facade_crops.py` (54),
`build_facade_crops.py` (396), `build_progress_blender.py` (374),
`build_site_fishnets.py` (293, brand new and being wired in),
`FIGURES/make_eleven_cities_exposure.py` (204), `make_vlm_batches.py` (65),
`measure_city_metrics.py` (63), `plot_crop_convergence.py` (90),
`run_material_ablation.py` (226), and three under `outputs/mesh_study_scripts/`:
`build_planes.py` (75), `report_mesh_study.py` (183), `score_mesh.py` (295).

One of those is worth separating from the rest.
`outputs/mesh_study_scripts/sweep_remesh.sh` invokes `$SCRATCH/score_mesh.py`,
a path in an agent scratchpad outside the repository, not the copy committed
beside it. So the committed `score_mesh.py` has no invoker and the invoked one
is not in the repository. That is a reproducibility hole, not dead code.

`FIGURES/make_eleven_cities_exposure.py` is the generator of the headline
figure and nothing references it by name, which is the same hole in a more
visible place.

### 8.3 Literal duplication, 74 lines

- `build_inhouse_mesh.py:23-42` against `showcase_blender.py:26-44`, 19 lines of
  identical import and `sys.path` bootstrap.
- `run_law_comparison.py:24-41` against `run_substreet_ablation.py:26-43`,
  18 identical lines.
- `TRANSIENT_CLASSES`, 16 identical lines, `build_site_semantics.py:67-85`
  against `build_walk_twin.py:470-488`. Self declared in the code: "copied
  rather than imported from `build_walk_twin.py`, which is under concurrent
  edit."
- `SITES`, the eleven city tuple, 11 identical lines,
  `build_site_semantics.py:92-106` against `run_exposure.py:169-185`. Also self
  declared. This one is worth fixing rather than tolerating: it is the list of
  sites the paper reports, held in two places, and the two drifting apart would
  be silent.
- The three line `SCRIPT_DIR` / `sys.path.insert` bootstrap appears verbatim in
  18 scripts.

One conceptual duplicate is more serious than any of the literal ones.
`build_site_config.py:92-147` defines its own `ground_datum` (56 lines, random
polar sampling plus a lower half histogram mode) that reimplements the canonical
`walk.ground_datum` / `measure_ground_datum` (117 lines, grid column plus
"lowest major level") under **the same name and a different algorithm**. Six
other scripts import the canonical one. Only `build_site_config.py` shadows it.
The ground datum sets the walk height, the ground and roof class split and the
crop, so two definitions of it disagreeing is not a style problem.

### 8.4 Tests

No assertion free tests: all 594 test functions were AST checked for a missing
`assert`, `pytest.raises`, `pytest.warns` or `np.testing.assert_*` call, and
none was found. No duplicated test bodies: pairwise similarity over all 418
non trivial bodies put only four pairs above 0.8, and all four are deliberate
parameter variants rather than copies.

---

## 9. Git status

Nothing in the working tree looks like it was committed by accident. What stands
out:

- **The headline figure's geometry is half in git and half not.** This
  directory has its own `.gitignore` which, unlike the repository root's policy,
  does not exclude `.ply`, so 23 meshes totalling **194.6 MiB** are committed
  here, the largest a single 32.2 MiB `korenmarkt/inhouse_leaf_340m_f64.ply`.
  Of the eleven sites in the corrected 250 m run, only korenmarkt's mesh is
  tracked. The other ten are untracked and exist only on this box, with no
  checksum recorded in git, so that run cannot be reproduced from the repository
  alone. Either policy is defensible. Splitting the inputs of one figure across
  both is the thing to fix, and given the size the honest direction is to track
  none of them and record checksums instead.
- `run_substreet_ablation.py` is untracked while `outputs/substreet_ablation/`
  contains its results and section 5 of this report cites its hardcoded bounce
  count. That one should be committed.
- Two deletions are staged in the working tree that are not obviously
  intentional from here: `hybrid_twin/download_google_tiles.py` and
  `hybrid_twin/route_google.py`, with untracked `download_inhouse_tiles.py` and
  `route_inhouse.py` beside them. That reads like a deliberate rename from the
  Google tile source to the in house one, but it is uncommitted, so the
  intermediate state is a repository where the referenced scripts do not exist.
- `spinoff/custorix/custorix_valtorix_dossier.md` is deleted and uncommitted,
  which is outside this directory and outside this audit.
- `blgpu_backup/` and `propagation_previews/` are untracked directories that
  look like working artefacts rather than deliverables.

Re-read at the end of the night, after other agents had been committing for
several hours, most of that had cleared. `run_substreet_ablation.py` is in.
The geometry split has got worse rather than better: 23 meshes at 195 MB are
tracked and 17 at 342 MB are not, so the untracked half is now the larger one.
Seven files are still untracked and every one of them is somebody's work in
progress rather than an oversight:

    build_site_fishnets.py            semantic_twin/propagation/antenna.py
    crop_fused_semantics.py           semantic_twin/propagation/sionna_check.py
    FIGURES/make_bounce_budget_figure.py
    tests/test_antenna.py             tests/test_sionna_check.py

The two that would matter if the night ended here are `antenna.py` with its
paired test file, because they carry the `LoadedBeam` fix of section 11, and
`sionna_check.py` with its own, because an external cross validation that is not
in the repository is not evidence. Both belong to agents that were still running.

---

## 10. What was changed, and what was not

**Two new files, mine.**

- `tests/test_propagation_closed_form.py`, 9 tests. The closed form targets of
  sections 2 and 3, plus the definition pin of section 6.1.
- `CODE_AUDIT.md`, this file.

**Seven edits to files other agents wrote tonight, all of them to get the tree
green or ruff clean, and two of them because a test caught a real bug.** Each is
the narrowest thing that fixes the named cause.

- `propagation_blender.py`, moved `import mathutils` off the module level into
  the two functions that use it. Section 1. Restores an invariant that file's
  own tests depend on, and cannot change anything under `blender -P`.
- `semantic_twin/propagation/antenna.py`, added
  `from .tracer import DEFAULT_MAX_BOUNCES, TERMINATIONS`. Both names were used
  and neither was imported, so `main()` raised `NameError` on the argument
  parser and the ray classifier raised on its first call. Ruff F821, twice.
- `semantic_twin/propagation/antenna.py`, `LoadedBeam._user_draw`, changed the
  azimuth nodes from `linspace(-half, half, n)` to the centres of `n` equal
  bins. Section 11.4. This is the real bug of the night.
- `semantic_twin/propagation/antenna.py`, `steering_artefact`, guarded the
  weighted quantile against an empty sub population. Section 11.5.
- `ruff format` over the directory, 12 files, none of them mine and none of
  them changed in behaviour.
- `bound_diffraction.py`, removed an unused `import math`. Ruff F401.
- `FIGURES/make_diffraction_bound_figure.py`, dropped an unused `manifest`
  binding, keeping the read so the existence check it was doing survives. Ruff
  F841.
- `tests/test_antenna.py`, corrected two targets that were wrong rather than
  weak, and added one test. Section 11.

**No module under `semantic_twin/propagation/` that the published numbers run
through was edited.** `antenna.py` is new tonight and nothing in `outputs/`
comes from it. No bug was found in the estimator itself that needed a fix. The
two defects in `tracer.py` that do warrant one, sections 6.1 and 6.2, both
change a value that is streamed into published JSONL, so neither is the
"unambiguously safe and local" change the brief allows and both are left for
whoever owns the output schema.

**Nothing was deleted.** Not the 132.5 MiB of duplicate geometry, not the dead
symbols, not the orphaned scripts.

### The order I would fix these in

1. Correct the street small cell row of the section 9 ladder table to
   0.167 +/- 0.022 dB, and reconsider the sentence the four row trend supports.
   That is the only place this audit found a published number that is wrong
   rather than merely unqualified.
2. Accumulate the second moment in `_deposit` and publish a standard error with
   every susceptibility. Section 4.4. It is a few lines and it retires the whole
   class of question.
3. Reconcile the bounce depth. Either say which runs used which, or rerun the
   ladder at 4 and say "four" everywhere. Section 5.
4. Put a floor on the crop correction range, and mark the 0.298 dB figure as
   unmeasured for noise until it is measured.
5. Unify the two `ground_datum` implementations and the duplicated `SITES`
   tuple. Section 8.3.
6. Fix `truncated_throughput_share`, both the denominator and the degenerate
   case. Sections 6.1 and 6.2.
7. Decide one policy for geometry in git. Section 9.

---

## 11. The antenna module, and the one real bug of the night

`semantic_twin/propagation/antenna.py` and `tests/test_antenna.py` are new,
untracked, and were being written while this audit ran. They are not in the path
of any published number: nothing under `outputs/` comes from them. They are in
this report because three of their tests were failing and because one of those
three was right.

### 11.1 Two names were used and never imported

`DEFAULT_MAX_BOUNCES` at line 924 and `TERMINATIONS` at line 789, both defined
in `tracer.py` and neither imported. Ruff F821. The first makes `main()` raise
`NameError` while building its argument parser, so the module's command line
could not start at all, and the second raises on the first call to the ray
classifier. One import line fixes both.

### 11.2 The beamwidth target was the asymptote, not the beamwidth

`test_the_array_beamwidth_is_the_uniform_aperture_one` compared the measured
half power width against `101.5 / M` at 2 percent for M of 4, 8 and 16. That
constant is the large `M` limit of the uniform aperture width. The exact width
solves `|sin(M u / 2) / (M sin(u / 2))|^2 = 1/2` at `u = pi sin(offset)`, and it
sits above the limit by a margin that falls like `1 / M^2`:

| M | exact HPBW, deg | 101.5 / M | excess |
|---|---|---|---|
| 4 | 26.322952 | 25.375 | 3.74 % |
| 8 | 12.802526 | 12.6875 | 0.91 % |
| 16 | 6.358726 | 6.34375 | 0.24 % |

The code returned 26.323000 at M of 4, which is the exact root to six figures.
The implementation was right and the target was wrong, so the test was failing
on a true statement. It now pins the exact roots at one part in ten thousand,
which is a far tighter constraint than the 2 percent it had, and separately
checks that the gap to `101.5 / M` shrinks like `1 / M^2`, which is the claim
the docstring was actually making.

### 11.3 The azimuth seam, where 180 and -180 are the same bearing

`source_frame_angles` wraps to the half open interval `[-180, 180)`, so a site
due east of the pedestrian comes back at -180 and not +180. The test asserted
+180. Same bearing, and the gain laws are even in `phi`, so nothing downstream
can tell them apart. The test now pins the wrapped value, the unwrapped bearing
it stands for, and the half open interval itself, because the sign at the seam
is exactly what a reader would otherwise have to guess.

### 11.4 The bug: `LoadedBeam` averaged over its users on a rule that does not converge

`LoadedBeam._user_draw` builds a product quadrature over the served user's
direction. The elevation axis uses the centres of `user_elevation_nodes` equal
bands, weighted by the population's own band measure. The azimuth axis used
`np.linspace(-half_width, +half_width, user_azimuth_nodes)`, and `__call__` gave
every azimuth node the same weight `1 / user_azimuth_nodes`.

Equal weights are the midpoint rule. Those are the trapezoid rule's nodes. The
combination over weights both sector edges by a factor of two, is first order
rather than second, and for a full circle sector puts two nodes on the same
azimuth. At the shipped 13 azimuth nodes it was not a small error. Refining one
axis at a time, at a pedestrian 2 degrees up under a rooftop population:

| azimuth nodes | before | after |
|---|---|---|
| 13 | 0.6449 | 0.49606 |
| 25 | 0.5730 | 0.49579 |
| 49 | 0.5346 | 0.49579 |
| 97 | 0.5148 | 0.49579 |
| 385 | 0.4997 | 0.49580 |

The elevation axis was already converged at its default of 24 nodes, to 0.2
percent. So the whole of the error was in azimuth, it was 29 percent at the
shipped defaults, and it was converging like `1 / n` rather than `1 / n^2`,
which is why nobody would have caught it by nudging the node count.

The isotropic user limit is where it showed largest, and it is the case the
failing test used. A half wavelength panel conserves power, so a user population
spread over the whole sphere has to hand the pedestrian back the element pattern
and no array gain at all, near 0.7 for this panel at shallow elevations. Before
the fix the defaults returned 1.89, a factor of 2.7 too high. After it they
return 0.693, 0.709 and 0.791 at 2, 10 and 30 degrees, inside the band the
module's own docstring predicts, at the default node count, with no refinement.

The published numbers are untouched by this: `LoadedBeam` has never produced
one. What it does mean is that had the antenna arm shipped on the defaults it
came with, the loaded beam's contribution to `Q` would have been about 30
percent high over a rooftop population and 2.7 times high in the spread user
limit, and the module's own stated limit would have been the thing contradicted.
The test that caught it was correct and the sensible thing was to fix the code
under it, which is what happened.

`test_the_loaded_beam_user_quadrature_is_converged_at_its_defaults` is new and
pins the property rather than the value: the shipped node counts have to agree
with an eightfold refinement to 5 percent over a 1 to 60 degree sweep, for both
site populations and for the isotropic limit. The corrected rule delivers 1.3
percent worst case for rooftop and 3.4 percent for street, so the bar is six
times inside the error the old rule carried and could not let it back through.

> **Old illumination law, see `LAW_CHANGE.md`.** The quadrature is refined over the
> rooftop and street site populations, so the 29 percent error, the 2 degree rooftop
> test point and the 1.3 and 3.4 percent convergence bars are all read against the
> old law. The bug and the fix are quadrature and survive whole, and the two
> populations the new test sweeps have to be rebuilt.

### 11.5 `steering_artefact` crashed on the scene it is measured against

`quantile` inside `steering_artefact` takes the deposit weighted quantile of the
per ray offset over the bounced rays only, `mask=~direct`. In a scene with no
surfaces every ray is direct, that sub population is empty, `weight.sum()` is
zero and `np.interp` raises `ValueError: array of sample points is empty` on an
empty abscissa. The function two lines below already guards the identical case,
`if np.any(~direct) else float("nan")`, so the pattern was established and these
two calls simply did not use it.

The scene it crashes on is not an odd corner. It is the free space reference
that `test_a_scene_with_no_surfaces_has_no_artefact_at_all` uses to establish
that the measurement reads exactly zero before any of its other numbers mean
anything. The guard returns 0.0 rather than nan, because with no bounced ray
there is no offset, which is the number the test asks for and the thing the
whole statistic measures the size of. `direct_measure` is 1 in exactly that
situation, so nothing is concealed by it.

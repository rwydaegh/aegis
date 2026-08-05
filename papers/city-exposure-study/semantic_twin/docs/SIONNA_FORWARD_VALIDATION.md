# Forward validation with Sionna RT

This comparison tests the current facade-tip propagation model. Sionna traces
ordinary forward links from base stations to pedestrians. The study code traces
the same links in reverse and uses next-event connections at each bounce.

The old Sionna comparison in `transport/sionna_check.py` tests the former
sky-density model. It remains useful as a historical check. It is not the main
test for the placed facade-tip sources described in `2026-08-03_174922_METHOD.md`.

## The shared quantity

For receiver $j$, source $i$, and Sionna path $p$, define

$$
K_j = \frac{1}{N_{\mathrm{src}}}
      \sum_i \sum_p
      \frac{\lvert a_{ijp} \rvert^2}
           {(\lambda / 4\pi)^2}.
$$

The paths add in power. The two transmitted polarisations are averaged. Both
received polarisations are summed. In free space, one source at range $r$
therefore contributes $1/r^2$.

This is the unit used by the next-event estimator. Its direct term is the mean
of $V_{ij}/r_{ij}^2$ over the same source points. Its bounced term has the same
scale after the $4\pi$ adjoint solid-angle factor is applied.

No open-ground denominator is needed. The comparison uses the geometric transfer
per unit source power and source count, in $\mathrm{m}^{-2}$.

## The matched scene

The main check removes materials on purpose. Every triangle uses one fully
diffuse near-perfect reflector:

- The study tracer uses relative permittivity $1-j10^{12}$ and RMS roughness
  1 m.

- Sionna uses the same complex permittivity, a 2 m slab, and scattering
  coefficient 1.

- Sionna diffuse reflection is on. Specular reflection, refraction, diffraction,
  and edge diffraction are off.

This leaves the same opaque geometry, inverse-square spreading, Lambertian lobe,
visibility, and bounce count in both tools. The remaining coherent share in the
study tracer is below $10^{-20}$ for incidence within 89 degrees of the normal.
The reflector is within 0.001 dB of unit power reflectance over the same range.

The material is not meant to represent a city wall. It removes the material
question so the propagation calculation can be tested. Production materials are
a later sensitivity run, not a pass or fail test.

## Primary environment

The primary environment is an imagined open square. It has a 200 by 200 m
ground plane and three 80 by 20 m walls. The south side is open. Each surface is
one rectangle made from two triangles, so the whole scene has eight triangles.

Twenty-seven sources sit 0.5 m above the three wall tops. Six receivers cover
the centre, two near-wall points, an off-centre point, the open approach, and a
point behind the north wall. All receivers are 1.5 m above the ground.

This scene retains facade-tip sources, direct shadowing, finite range, diffuse
reflection, and paths with several interactions. It removes photogrammetry,
source extraction, mesh noise, clutter, and material assignment. It is the main
propagation validation. A city mesh is a later stress test.

## Shared geometry, sources, and receivers

Both tools receive the same data:

- the same float32 triangle buffer, with no remeshing or normal generation,

- the same facade-tip point coordinates, including the 0.5 m surface lift,

- the same pedestrian coordinates,

- the same three-interaction limit.

The open-square run uses all 27 sources and all six receivers. No source sampling
is needed.

The later city test uses a fixed uniform subset drawn without replacement, then
given to both solvers. Source sampling error cancels in their difference because
the subset is shared. The city stress test uses 32 sources and four held-out
receivers.

## Antennas and polarisation

The production next-event model has no antenna pattern. The matched Sionna run
must therefore have none either.

Sionna uses one isotropic cross-polarised element at each end. The result sums
both receive ports and both transmit ports, then divides by two to average the
two transmitted polarisations. A free-space control pins this factor.

A 3GPP panel would make the comparison less fair. It needs a panel orientation,
sector assignment, electrical downtilt, steering rule, and a decision about
whether source power means conducted power or EIRP. None of those variables
exists in the current facade-tip law. Adding a panel only in Sionna would measure
an omitted antenna model, not validate propagation.

The receiver is isotropic for the same reason. The current propagation result is
the power field at a point. Human-body coupling is a later AEGIS calculation and
is outside this comparison.

Coherent beamforming is also outside the test. Sionna path amplitudes are reduced
to an incoherent power sum before sources are averaged. Summing complex path
amplitudes would answer a narrowband channel question. The study reports a
band-averaged second moment.

## Checks in order

### 1. Free space

Use several source-receiver ranges with no scene. The result must equal the mean
of $1/r^2$. This checks the isotropic pattern, polarisation factor, source mean,
and Friis normalisation.

### 2. One diffuse plane

Place a source at $(0,0,20)$ m and a receiver at $(0,0,10)$ m above a plane. The
known terms are

$$
K_{\mathrm{direct}} = \frac{1}{(20-10)^2} = 0.01,
$$

$$
K_{\mathrm{bounce}} = \frac{2}{(20+10)^2} = 0.0022222.
$$

The implemented control gives a total difference of 0.0007 dB between the two
solvers at 150,000 adjoint rays and 200,000 Sionna samples per source. The test
limit is 0.05 dB.

### 3. Simple corner

Use two perpendicular planes, two sources, and receivers on both sides of the
corner. Run at depths one, two, and three. This separates visibility, one-bounce
weight, and bounce-order bookkeeping before a city mesh is involved.

The implemented control uses a floor and a wall, three sources, two receivers,
and two interactions. Its maximum total difference must stay below 0.1 dB. A
depth-three version should still be run before a paper claim is based on the city
result.

### 4. Open square

Run the eight-triangle imagined square at depths one, two, and three. Compare
direct, bounced, total, and multipath surplus at all six receiver points. This is
the main result.

The 50,000-sample run gives:

| Interactions | Bounced median | Bounced maximum | Total median | Total maximum |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.025 dB | 0.062 dB | 0.011 dB | 0.034 dB |
| 2 | 0.029 dB | 0.042 dB | 0.017 dB | 0.025 dB |
| 3 | 0.036 dB | 0.086 dB | 0.024 dB | 0.051 dB |

At three interactions and 100,000 samples, the total difference falls to 0.008
dB on the median and 0.024 dB at the worst receiver. The bounced term is 0.014
dB on the median and 0.036 dB at worst. Positive and negative differences both
occur, which is the pattern expected from sampling noise rather than one solver
carrying a fixed bias.

### 5. City links

Run Korenmarkt first, then Brussels Grand Place. Use the real 250 m meshes, real
facade-tip source points, and held-out points from the walk. Compare direct,
bounced, total, and multipath surplus per receiver.

The direct term is a translation check. Both tools use Mitsuba for visibility,
so agreement there is necessary and weak. The bounced term is the independent
part. Sionna launches from the source while the study code samples paths from the
receiver.

## Sampling and acceptance

Use repeated seeds. The measured starting run is:

- 50,000 adjoint rays, four seeds,

- 50,000 Sionna samples per source, three seeds,

- 27 sources, six receivers, and three interactions.

Doubling both budgets to 100,000 moves the adjoint total by 0.016 dB on the
median and 0.027 dB at worst. It moves the Sionna total by 0.018 dB on the median
and 0.026 dB at worst.

A solver is converged when doubling its
budget moves the median total by less than 0.1 dB and every receiver by less than
0.25 dB. Both solvers pass by a wide margin.

## Runtime and equal-accuracy cost

The controlled runs also measure wall time on the same local CPU. Including the
first compiled seed, the adjoint method is 3.0 to 3.4 times faster at an equal
nominal sample budget. That comparison gives Sionna more compilation cost per
reported seed because it has three seeds against four. It is useful as one-shot
wall time, but it is not the right steady-state comparison.

After dropping the first seed from both solvers, the mean times at 50,000
samples are 1.33 s for the adjoint method and 3.32 s for Sionna. At 100,000
samples they are 1.97 s and 5.57 s. The warmed equal-budget advantage is
therefore 2.5 to 2.8 times.

Sionna has slightly less run-to-run noise in this experiment. To compare equal
accuracy, multiply each solver's time by the variance of one independent run.
Using the median receiver variance and warmed times, Sionna needs 1.7 times as
much compute at 50,000 samples and 1.4 times as much at 100,000 samples. There
are only four adjoint seeds and three Sionna seeds. The stable claim is therefore
that the adjoint method is about 1.4 to 1.7 times faster for the same Monte Carlo
accuracy in this small scene.

These are CPU results. Sionna RT 2.0.1 is also installed on `blgpu`, where it
selects the `cuda_ad_mono_polarized` backend on an NVIDIA RTX A6000. The GPU
source-count results are kept separate from this CPU comparison.

### Scaling to the facade-tip source count

The open square was repeated from 27 to 9,668 sources. It still has six
receivers and eight triangles. The adjoint solver uses 50,000 rays per receiver.
Sionna uses 3,000 samples per transmitter, a tuned source batch of 2,048, and a
path buffer that was checked for saturation. Each solver has ten timed seeds.
The scene receives an unmeasured warm-up, and the first timed seed is also
dropped from the wall-time mean.

| Sources | Sources per receiver | Adjoint CPU | Sionna A6000 | Adjoint advantage |
| ---: | ---: | ---: | ---: | ---: |
| 27 | 4.5 | 0.706 s | 0.092 s | 0.13 times |
| 729 | 121.5 | 0.781 s | 0.506 s | 0.65 times |
| 2,187 | 364.5 | 0.765 s | 1.297 s | 1.7 times |
| 5,002 | 833.7 | 0.862 s | 3.366 s | 3.9 times |
| 9,668 | 1,611.3 | 0.645 s | 6.507 s | 10.1 times |

The eleven-city production runs have 5,002 to 25,782 facade-tip sources and 16
receivers. Their source-to-receiver ratios are 313 to 1,611. The controlled
benchmark therefore spans the same ratio. Across that production range, the
measured advantage rises from 1.7 to 10.1 times. This compares the study's CPU
implementation with a tuned Sionna GPU run, which makes the result stronger
than a same-device comparison.

The crossover matters. Sionna is 7.7 times faster in the original 27-source
case. Reverse tracing becomes useful only when many transmitters share each
receiver calculation. The adjoint bounced estimator samples one source at each
connection, so its main tracing cost changes little with the source count.
Sionna pays its forward sampling budget for every transmitter.

The 3,000-sample setting is an accuracy choice, not a timing choice. At 2,187
sources, 16 seeds at 2,500 samples leave one receiver 0.178 dB from the
10,000-sample result. At 3,000 samples the worst shift is 0.043 dB. Across the
three points inside the production ratio, the maximum total difference between
the two solvers is 0.040 dB. A 27-source run needs more samples per transmitter
because it has far less averaging across sources.

Seed variance alone gives the wrong answer here. The 2,500-sample Sionna run has
about the same wall time and single-run spread as the 100,000-ray adjoint run,
but its worst receiver has not converged. The missing paths create search bias
that repeated seeds do not expose. The budget-doubling test must therefore set
the runtime point before a variance-times-time score is used.

There is no universal speedup at 2,187 sources. Under a strict equal-variance
comparison, the 100,000-ray adjoint run takes 1.66 s with a median single-run
spread of 0.014 dB. The 3,000-sample Sionna run takes about 1.56 s with a spread
of 0.011 dB. They are roughly tied. The 1.7 times point above instead asks
whether both solvers meet the measured 0.1 dB convergence rule. The paper must
name the rule beside every speed number.

A separate stress point uses 25,782 sources and only six receivers. It gives a
26.5 times adjoint advantage. Its source-to-receiver ratio lies beyond the
eleven-city range, so it shows the asymptotic trend and is not the paper
headline.

This is a controlled scaling result. Repeating it on the real city mesh tests
whether path count, visibility complexity, and surface defects move the
crossover. It should be reported beside this result rather than replacing it.

## Deterministic first-bounce reference

The two ray tracers are no longer the only calculations in the comparison.
`semantic_twin.cli.deterministic_first_bounce` integrates the first-bounce
Lambertian transfer directly over triangle area. Each input triangle is divided
into equal-area subtriangles. Their centroids carry deterministic quadrature
weights, and shadow rays are used only to decide visibility. There is no random
path search and no tracing direction to reverse.

At 512 subdivisions per triangle, the open square has 2,097,152 surface
samples. Raising the resolution from 256 to 512 changes the total by 0.0017 dB
at the median receiver and 0.0018 dB at worst. Against that reference, the
one-interaction Sionna result differs by 0.0005 dB at the median and 0.0096 dB
at worst. The adjoint result differs by 0.013 dB at the median and 0.034 dB at
worst, consistent with its measured Monte Carlo error.

This three-way agreement is stronger than taking either ray tracer as an
oracle. It checks the normalization, both cosine factors, inverse-square loss,
visibility, and the Lambertian factor by a calculation that shares none of the
path-estimation code.

## Neutral-material city stress test

The controlled scene is followed by the 250 m Korenmarkt mesh, which has about
617,000 triangles. The run uses 32 fixed facade-tip sources and four held-out
pedestrian points. Every triangle keeps the same neutral diffuse reflector, so
the test adds geometric complexity without adding material classes.

At 200,000 samples and six seeds, the total Sionna-minus-adjoint difference is
0.130 dB at the median receiver and 0.219 dB at worst. The difference grows
with the interaction budget:

| Interactions | Total median | Total maximum | Bounced median | Bounced maximum |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.029 dB | 0.104 dB | 0.050 dB | 0.191 dB |
| 2 | 0.092 dB | 0.187 dB | 0.134 dB | 0.302 dB |
| 3 | 0.130 dB | 0.219 dB | 0.178 dB | 0.336 dB |

The remaining Rayleigh specular share is not the cause. Raising the validation
RMS height from 1 m to 1,000 km leaves the median residual at 0.130 dB.

The connection start on the photogrammetric surface explains much of the
difference. The production estimator lifts a source shadow ray by 1 cm along
the local normal. Raising that validation-only lift to 3 cm reduces the median
residual to 0.088 dB, and 10 cm reduces it to 0.066 dB. The 10 cm setting is not
adopted because it can step across a real thin blocker. This sweep measures a
numerical surface uncertainty rather than providing a fitted parameter.

Apply these checks after both solvers converge:

- direct term: maximum absolute difference below 0.05 dB,

- total: each difference lies within three combined standard errors plus
  0.1 dB,

- bounced term: report the raw difference and its error even when the term is
  small,

- path buffer: reject any Sionna run that reaches
  `max_num_paths_per_src`.

The error rule is more useful than one fixed city tolerance. It tightens as both
solvers receive more samples and does not call Monte Carlo noise a model error.

### Full production source grid

The stronger city test keeps all 8,873 facade-tip sources and all 16 pedestrian
receivers in the 250 m Korenmarkt mesh. It therefore tests the same
source-to-receiver ratio as the production calculation. Materials remain
neutral. The adjoint run uses 100,000 rays per receiver and eight seeds. Sionna
uses 3,000 samples per source and eight seeds. Neither Sionna path buffer reaches
its limit.

Direct transfer still agrees. Its absolute difference is 0.000002 dB at the
median receiver and 0.017 dB at worst. Reflected transfer does not agree. Sionna
is higher at every receiver, by 0.408 dB at the median and 0.893 dB at worst.
The resulting total difference is 0.262 dB at the median and 0.632 dB at worst.
Thirteen of 16 receivers pass the predeclared total-error rule. Twelve pass the
reflected-error rule.

Doubling the Sionna budget to 6,000 samples per source changes its total by
0.010 dB at the median receiver and 0.126 dB at worst. Against the original
eight-seed adjoint mean, the doubled-budget Sionna result remains 0.286 dB away
at the median and 0.623 dB at worst. The worst receiver is just outside the
0.1 dB convergence target, but the large common shift remains. It cannot be
explained by the 3,000-sample path-search budget alone.

At the measured 3,000-sample budget, the warmed mean times are 4.66 s for the
adjoint CPU run and 36.60 s for Sionna on the A6000. This is a 7.9 times wall-time
advantage for the tested budgets. It is not an equal-accuracy speedup because the
full-city results fail the agreement test. The controlled open-square result is
the defensible speed comparison. The city result instead exposes a real limit:
surface offsets, visibility near complex mesh boundaries, and the two diffuse
path estimators can produce a few tenths of a decibel of disagreement even when
materials and antennas are removed.

This comparison is useful rather than futile. It shows where the current model
is reliable and where more work is needed. In a paper, report the controlled
three-way validation as the numerical validation, the source-scaling experiment
as the speed result, and the full city as a geometry stress test. Figure 30 keeps
those claims separate.

## What agreement would establish

Agreement would support these parts of the current method:

- reverse tracing by reciprocity,

- next-event source connections,

- direct and bounced normalisation,

- inverse-square range loss,

- Lambertian scattering and its cosine factors,

- bounce-order truncation on the tested links.

It would not validate the facade-tip source law, the source-set thinning, antenna
patterns, material constants, the Rayleigh roughness split, diffraction, coherent
MIMO, or body coupling. Those are different questions.

## Further validation ladder

The paper should separate component checks from end-to-end checks. One large
realistic scene cannot identify which part failed.

1. **Analytic controls.** Keep free space, the diffuse plane, and the corner.
   Add a closed diffuse box and verify that reflected plus escaped power closes
   the energy balance at every interaction order.

2. **Independent quadrature.** Extend the deterministic integral from one to two
   interactions on the eight-triangle square. This will be expensive, but it
   removes both Monte Carlo estimators from the answer.

3. **Invariance tests.** Translate and rotate the whole scene, reverse triangle
   winding consistently, and split every rectangle into smaller triangles. The
   transfer should stay fixed within sampling error. These tests catch normal,
   offset, and tessellation errors.

4. **Rare-path controls.** Add a narrow doorway, a deep street canyon, and one
   partly hidden wall. These cases test whether forward path discovery misses a
   small but important solid angle and whether next-event connections create a
   high-variance visibility term.

5. **Antenna ladder.** Start with the isotropic cross-polarised control used
   here. Then give both methods the same analytic dipole pattern. Add a panel
   only after orientation, downtilt, steering, conducted power, and EIRP are
   defined in the study model. A panel in Sionna alone is a different model, not
   a validation.

6. **Material ladder.** Keep the neutral reflector as the propagation test.
   Next use one smooth dielectric with matched complex permittivity. Then add a
   matched diffuse fraction. The production material catalogue comes last,
   because Sionna and the study code do not express roughness in exactly the
   same way.

7. **Real geometry.** Repeat the neutral-material test on several city meshes.
   Sweep the connection lift and mesh resolution. Report this as numerical
   surface uncertainty. Do not tune the lift separately for each city.

8. **Measurements.** A measured route is useful as an end-to-end check of the
   complete exposure pipeline. It mixes source power, antenna direction,
   materials, geometry, and instrument error, so it cannot replace the controlled
   propagation tests. Use held-out receiver locations and fix every uncertain
   input before reading the error.

The real comparison is therefore possible, but it answers a broader question.
The controlled scene tests the estimator. The neutral city tests its numerical
robustness. A material city or field campaign tests the complete model.

## Running it

The comparison entry point is:

```bash
python -m semantic_twin.cli.sionna_forward \
  --environment open-square \
  --adjoint-rays 100000 \
  --adjoint-seeds 4 \
  --sionna-samples-per-src 100000 \
  --sionna-seeds 3
```

It writes the exact source and receiver coordinates, both sample means and
standard errors, Sionna path-buffer use, and all dB differences to
`outputs/cross_validation/forward_sionna_open_square.json`.

The city stress test adds `--environment city --site korenmarkt --sources 32
--receivers 4`.

Sionna is installed locally at version 2.0.1. The open-square run is small enough
for the local machine. The later city run belongs on `bluelobster` because
Sionna's diffuse solver is built for a GPU.

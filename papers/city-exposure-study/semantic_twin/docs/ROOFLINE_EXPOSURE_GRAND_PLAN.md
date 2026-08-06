# Grand plan for the roofline exposure study

Status: working scientific plan, 2026-08-06.

This document defines the path from the current diagnostic estimator to a paper
result. It separates settled facts, proposed choices, and gates that must pass
before a large run. It also records what the paper should leave out.

## The paper in one sentence

A camera placed at the pedestrian receiver can bind panoramic material evidence
to the first surfaces reached by reciprocal rays, while an explicit facade-tip
source model produces a local directional power measure that can be coupled to a
human body along a route.

The strongest part is the co-location. The panorama camera, receiver, reciprocal
ray origin, and body coupling point share one position. The transmitter does not
share that position. It lies on the declared facade-tip source support.

The panorama also does not create the city geometry. It registers image evidence
to an existing photogrammetric support mesh. Material labels remain model
outputs with uncertainty. They are not exact measurements of every material.

## What the study should estimate

The method needs three separate measures.

- A source measure, `mu`, says where sources may exist and how their power is
  weighted.
- A directional transport measure at receiver position `x` says how much power
  arrives from each direction.
- A route measure, `pi`, says how receiver positions are weighted in a reported
  distribution.

For source position `s` and physical arrival direction `k`, let
`T_x(s, k)` be the transport from a unit source to the receiver. The environment
result is

```text
A_x(k) = integral T_x(s, k) mu(ds).
```

The body result then applies a directional body response `R_b(k)` to `A_x(k)`.
The route CDF is formed only after `pi` has been declared. A CDF over panorama
positions is therefore a fixed-route distribution. It is not a city population
distribution.

The final directional representation should contain two parts:

1. Exact directional atoms for direct and deterministic specular point-source
   paths. Each atom retains its direction and transfer mass.
2. A gridded directional density for diffuse transport.

This matters because a direct point source is a delta in direction. Putting it
in one of 4,096 cells conserves total power but makes body incidence depend on
the grid. The current prototype bins direct paths for conservation and visual
inspection. The paper path should retain their exact directions for body
coupling.

All units must be explicit. With normalized source probabilities, the present
placed-source scalar has a transfer scale proportional to `1/r^2`. It is not a
dimensionless susceptibility. If all sources have common EIRP `P`, physical
incident power carries a factor `P / (4 pi)`. A dimensionless body spectrum may
be formed only by dividing by a declared reference transfer and pairing it with
the corresponding physical reference power density.

## The source model must be fixed before the transport model

The present `SourceSet` is a reproducible discrete candidate distribution. Its
default estimator averages over candidate sites. This means it answers the
response to a source drawn from that set. It does not yet implement a homogeneous
source density per metre of roof edge or per square kilometre of ground.

The current three-dimensional thinning also does not prove a line measure. It
selects samples from surfaces that appeared on a skyline across a set of camera
positions. The result depends on the camera route, mesh, ray-fan resolution,
cell size, and crop.

Before a paper run, compare two clean definitions on a small data set:

1. A length-weighted facade-tip curve. Reconstruct connected visible edge
   segments and give every quadrature point the arc length it represents.
2. An explicitly synthetic discrete candidate process. Freeze the extraction
   algorithm and interpret its normalized weights as a declared hypothetical
   deployment distribution.

The first is the preferred physical model if its curve and weights converge.
The second is acceptable if it is named honestly and its sensitivity is small.
It should not be described as a source density per unit roofline length.

One fixed source set must be used for every evaluation point in a route. A
different leave-one-out set at every point would change the network along the
walk. Source construction validation should instead hold out whole capture
sequences. The final production source set is then frozen once and evaluated at
all admitted receiver panoramas.

The source contract must include:

- support and quadrature weights
- crop and boundary rule
- source lift and minimum source distance
- EIRP or a clear per-unit-power result
- antenna pattern and orientation, or an explicit isotropic assumption
- frequency
- source-set hash and panorama sequence provenance

The direct and bounced branches must use the same near-source rule. The known
case where the direct branch accepts a source closer than 0.5 m while the
connection branch refuses it must be resolved before a city result.

## Complete transport without double counting

The intended path partition is:

1. Direct source-to-receiver paths.
2. All-specular paths.
3. Paths with at least one diffuse event.

The diffuse class should be assigned by its source-nearest diffuse vertex. From
that vertex, a source connection may contain zero or more deterministic specular
segments. This makes the classes mutually exclusive and covers mixed paths.
The partition needs a written proof and controlled tests before implementation
is called complete.

The current next-event gather covers only a zero-specular source connection from
a diffuse vertex. It omits all-specular paths and diffuse paths with a specular
suffix toward the source. Its new angular output is therefore a diagnostic
direct-plus-diffuse field. It is useful, but it is not total exposure.

A paper that reports total roofline exposure should complete and validate the
specular connection before its main CDF campaign. If that solver cannot be made
robust on controlled scenes and a small city mesh, the honest fallback is a
paper about direct and diffuse components with specular transport stated as a
limit. The fallback must not rename the partial result as total exposure.

The old elevation-band escape estimator remains a historical control. It uses a
different source law and cannot validate the explicit finite-source result.

## Roughness decision

Roughness controls how reflected power is split between coherent specular and
diffuse components. The current production quadrature and the alternative
unit-scatter interpretation give very different coherent shares at 15 GHz. The
choice is large enough to change which transport branch matters.

Before city tracing:

1. Define one primary roughness surrogate from a cited physical model and the
   material evidence actually available.
2. Freeze it for the main result.
3. Carry one credible alternative as a sensitivity result.
4. Keep the masonry model separate unless it passes the same controlled tests.

No roughness choice should be justified only because the final scalar changes
little. The directional field and body endpoints must also be checked.

Use one primary frequency for the main method and validation. The existing
15 GHz work makes it the practical starting point. A 28 GHz sensitivity can be
added after the method is frozen. Lower frequencies belong in a later extension
unless they are nearly free to evaluate.

## Staged execution plan

### Stage 0: freeze the scientific contract

Write down the source measure, output units, body orientation rule, route
measure, path partition, near-source rule, frequency, roughness rule, and
reported endpoints.

Gate: a dimensional ledger closes from source power to incident power and body
absorption. Every model choice and numerical control has a provenance field.

Stop condition: if the source result has no stable interpretation under source
resolution, crop, and builder-sequence changes, revise the source model before
transport work continues.

### Stage 1: diagnostic angular field

Retain exact direct contributions and diffuse next-event contributions by the
receiver ray's original launch direction. Prove that their directional masses
sum to the existing scalar direct and bounced terms. Preserve the old scalar API
when field output is disabled.

Current status: complete. The diagnostic binned field is merged and independently
verified. It remains a conservation and direction test. The direct bins are not
used for body coupling.

Gate: controlled tests cover unequal source ranges and weights, multiple trace
batches, direction signs, empty sets, scalar regression, and explicit missing
specular labels.

### Stage 2: exact direct atoms and body coupling

Introduce a `DirectionalMeasure` interface with exact atoms plus diffuse cells.
Extend body coupling so exact atoms are passed to AEGIS at their exact arrival
directions. Add an explicit body heading rule. Options are a fixed walking
heading, a heading inferred from route direction, or an orientation average.

Current status: the exact atom plus diffuse-cell interface and chunked level-2
body coupling are implemented and independently verified. Direct results are
independent of the diagnostic angular-grid resolution. The body heading rule is
still open, so this stage is not yet complete.

Gate: free-space point sources reproduce analytic level-2 body incidence. Grid
refinement does not move the direct body result because direct atoms are not
binned.

### Stage 3: choose the source measure

Run the small length-weighted versus discrete-process study. Use independent
capture sequences for validation. Measure source mass, visible direct transfer,
route ranking, and body endpoints as source resolution, crop, lift, and builder
density change.

Gate: choose one interpretation before looking at multi-city exposure results.
Freeze the chosen source builder and weights.

### Stage 4: complete the specular path classes

Start with an analytic image-source plane. Then test a partially rough plane and
a two-surface scene whose important path is diffuse followed by specular. Only
after those pass should candidate generation be tried on a city mesh.

Gate: direct, all-specular, and mixed paths form a mutually exclusive accounting
through the bounce cap. Results agree with an independent finite-source forward
reference in controlled scenes. Candidate generation has a measured miss rate
and bounded runtime.

Stop condition: if enumeration grows without a reliable bound, do not hide it
behind a small test scene. Either use a validated manifold or bidirectional
method, or narrow the paper to direct plus diffuse transport.

### Stage 5: freeze sampling and performance

Separate receiver-direction sampling from source sampling. Compare the current
IID launch with fixed equal-area stratification and scrambled low-discrepancy
sampling at equal cost. Judge the full directional field, fixed angular sectors,
body mean, body peak, and runtime. A scalar-only comparison is insufficient.

Profile before optimizing. The first candidates are:

- cache exact direct visibility after geometry and source hashes are frozen
- reuse fixed geometry and material lookups across replicas
- cache body response for a fixed grid and body orientation
- avoid tracing receiver directions proven by geometry to have no first hit
- merge coplanar semantic fragments only within the same original support
  triangle and material class, with exact intersection-equivalence tests
- keep Blender construction outside the numerical production loop

The semantic Atlas mesh simplification is promising because subdivision within
one original support triangle can be redundant. It needs a transport-specific
implementation. The existing Blender display simplification does not speed ray
tracing.

Gate: adopt a new sampler or mesh representation only if it preserves the
directional and body results within predeclared limits and gives a measured
runtime or memory gain.

### Stage 6: one frozen Korenmarkt run

Use admitted panorama positions only. Freeze source set, material atlas, body
orientation, transport version, output profile, and seeds before running. This
run validates the complete chain and produces the panorama-aligned audit figure.

Gate: all controlled tests pass, numerical convergence is adequate, evidence
coverage is reported by interaction depth, and no method definition changes
after seeing the city output.

### Stage 7: matched microenvironments

Use three preselected route types:

- historic masonry enclosure
- open plaza
- dense canyon or modern glass setting

Choose routes and inclusion rules before viewing exposure outcomes. Seek at
least four spatially separate route fragments and at least 40 admitted panorama
positions in total. More positions are needed for a stable p90. Describe all
CDFs as conditional on those fixed routes.

Use common random numbers for paired material ablations. Keep geometry, source
support, source weights, roughness, and paths fixed when testing only the effect
of semantic material assignment.

### Stage 8: convergence campaign and paper outputs

Run replicas only after the estimator version is frozen. Confidence intervals
from those replicas describe Monte Carlo uncertainty. They do not include source
model, geometry, material, or pedestrian uncertainty unless those inputs are
also varied.

Retain enough data for the exact reported statistic. If the paper reports the
peak of the ensemble-mean body field, scalar peak values are insufficient. Keep
per-replica directional measures or body-face fields, or an exactly equivalent
sufficient statistic.

## Production and audit outputs

The numerical production track should keep:

- code, geometry, semantic, source-set, body, and configuration hashes
- panorama IDs, positions, route order, and body orientation
- source positions, weights, and construction provenance
- direct, specular, diffuse, and total transfer per standpoint and replica
- area-weighted body mean, peak absorbed density, absorbed power, and whole-body
  SAR for the endpoints selected for the paper
- directional or body-field data required to reproduce ensemble statistics
- timing, ray counts, convergence diagnostics, and stop decisions

The audit and Blender track may additionally keep:

- panorama overlays and semantic evidence layers
- accepted and rejected fragment geometry
- exact source atoms and sampled path chains
- path-class and next-event contribution highlights
- rich meshes, cameras, labels, and animation data

The audit track can be large. It should run for selected standpoints only. The
production track should avoid image and Blender work while retaining complete
scientific provenance.

## What belongs in the paper

The main paper should contain:

1. One co-location figure with panorama slices: RGB, registered support,
   semantic and material evidence, source support, directional transport, and
   body response.
2. The declared facade-tip source measure and path estimator.
3. One controlled validation figure.
4. Evidence coverage as a function of interaction depth and distance.
5. Direct, reflected, and total fixed-route CDFs for the matched settings.
6. Body mean and peak results.
7. One paired semantic-material ablation.
8. A short uncertainty and limitations section.

Put registration details, prompt lists, material catalogues, source-resolution
sweeps, extended validation, all parameter tables, hashes, performance, and
Blender construction in the supplementary information.

Leave the following out of the main story unless a result forces them back in:

- old height-band and range-band illumination
- eleven-city rankings without matched evidence
- beamforming and MIMO
- bystander exposure
- detailed foliage and diffraction models
- agentic AI and SAM prompt experiments
- Blender implementation details
- extensive performance engineering

These are real project assets, but they weaken the central paper when presented
as equal contributions.

## Parameter discipline

Split the parameter record into four groups.

1. Physical inputs, such as frequency and measured material properties.
2. Observed inputs, such as camera poses, mesh geometry, and semantic evidence.
3. Model assumptions, such as source measure, roughness surrogate, and body
   orientation. These need argument and sensitivity tests.
4. Numerical controls, such as ray count, angular cells, source quadrature, and
   bounce cap. These need convergence evidence.

Display colors, Blender sizes, cache chunks, and file-layout controls belong in
a separate engineering appendix. Mixing them into the scientific parameter
table makes the method look more arbitrary than it is.

## The decisive gates

Do not launch the main campaign until all of these are true:

- the source measure and units are fixed
- direct paths remain exact directional atoms for body coupling
- the common near-source rule is fixed
- the roughness surrogate is fixed
- the intended specular path classes pass controlled tests, or the paper scope
  is explicitly narrowed to direct plus diffuse
- body orientation and route measure are fixed
- finite-source directional transport has an independent validation
- Korenmarkt passes the frozen end-to-end audit
- performance is measured and the retained outputs are sufficient for every
  reported statistic

This order prevents a fast GPU campaign from producing precise answers to a
moving scientific question.

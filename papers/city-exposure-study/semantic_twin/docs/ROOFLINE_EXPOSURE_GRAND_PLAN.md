# Grand plan for the roofline exposure study

Status: committed production plan, 2026-08-07. Final code commit: `f5f394da`.
Performance proposal reuse: `9111c591`. Report commits: `8db6bef0` and
`37b4498d`. Scientific paired campaign config: `b985ab58`.

This document defines the path from the committed estimator to a paper result.
It separates settled facts, proposed choices, and gates that must pass before a
large run. It also records what the paper should leave out.

## Current implementation status

The production contract uses a full route arc-length source curve, fixed
route-tangent yaw, and finish-only roughness. Specular transport permits at
most one reflection. Adaptive all-specular order 1 and a sampled mixed
one-reflection suffix are implemented. Higher specular orders are absent even
when `max_bounces=3`.

The local broad gate passed 2,872 tests, skipped 40, marked 18 as expected
failures, and deselected 46. The focused gate passed 202 tests with only local
CUDA-only skips. The real A6000 expanded campaign gate passed 163 tests with no
skips in 9.97 seconds. Korenmarkt and Prague preflight checks passed. Their
one-seed CUDA pilots passed independent audits. Korenmarkt IID and Fibonacci
paired 16-seed campaigns passed full audit with seeds 7 through 22 and looks 4,
8, 12, and 16. Prague paired outputs cover both modes, seeds 7 through 22, and
68 points. Both paired audits passed. Each Prague mode has 49 hash-valid
manifest entries, a 68x56024 body array, and no orphan files. Fibonacci is not
adopted. The final CUDA gate passed 166 tests in 12.53 seconds.

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

The committed directional representation contains two parts:

1. Exact directional atoms for direct and deterministic specular point-source
   paths. Each atom retains its direction and transfer mass.
2. A gridded directional density for diffuse transport.

This matters because a direct point source is a delta in direction. Putting it
in one of 4,096 cells conserves total power but makes body incidence depend on
the grid. The production path retains exact directions for body coupling.

All units must be explicit. With normalized source probabilities, the present
placed-source scalar has a transfer scale proportional to `1/r^2`. It is not a
dimensionless susceptibility. If all sources have common EIRP `P`, physical
incident power carries a factor `P / (4 pi)`. A dimensionless body spectrum may
be formed only by dividing by a declared reference transfer and pairing it with
the corresponding physical reference power density.

## The committed source model

The committed production source is a full route arc-length source curve. Its
support and weights are frozen for the route evaluation. It is a declared
source measure for this study, not a city population distribution.

Source validation can still measure sensitivity to curve resolution, crop,
lift, and builder provenance. That work checks the committed source contract.
It does not reopen the production choice as a discrete candidate process.

One fixed source set is used for every evaluation point in a route. A different
leave-one-out set at every point would change the network along the walk.
Source construction validation should instead hold out whole capture
sequences. The production source set is frozen once and evaluated at all
admitted receiver panoramas.

The source contract must include:

- support and quadrature weights
- crop and boundary rule
- source lift and minimum source distance
- EIRP or a clear per-unit-power result
- antenna pattern and orientation, or an explicit isotropic assumption
- frequency
- source-set hash and panorama sequence provenance

The direct and bounced branches use one shared near-source rule. Record that
rule with the source contract and its provenance.

## Bounded transport without double counting

The committed production estimator has an explicit one-reflection limit. Its
path handling is:

1. Direct source-to-receiver paths.
2. Adaptive all-specular order 1.
3. A sampled mixed suffix with one specular reflection after a diffuse event.

This is the production next-event behavior. It is not diagnostic-only. Higher
specular orders are absent even when `max_bounces=3`, so that setting must not
be read as a three-reflection specular allowance. Results must state this
bound when they describe reflected transport.

The old elevation-band escape estimator remains a historical control. It uses a
different source law and cannot validate the explicit finite-source result.

## Roughness rule

Finish-only roughness is implemented in the committed production path. The
rule is applied at the finish stage rather than as an unresolved alternative
quadrature. Any sensitivity comparison must name its alternate rule and check
directional fields and body endpoints, not only final scalars.

Use one primary frequency for the main method and validation. The existing
15 GHz work makes it the practical starting point. A 28 GHz sensitivity can be
added after the method is frozen. Lower frequencies belong in a later extension
unless they are nearly free to evaluate.

## Staged execution plan

### Stage 0: freeze the scientific contract

The committed contract records the full route arc-length source curve, output
units, fixed route-tangent yaw, route measure, one-reflection path limit,
near-source rule, frequency, finish-only roughness, and reported endpoints.

Gate: a dimensional ledger closes from source power to incident power and body
absorption. Every model choice and numerical control has a provenance field.

Stop condition: if the source result fails its resolution, crop, or
builder-sequence sensitivity review, record the limitation and do not broaden
the production campaign.

### Stage 1: production angular field

Retain exact direct contributions and diffuse next-event contributions by the
receiver ray's original launch direction. Prove that their directional masses
sum to the existing scalar direct and bounced terms. Preserve the old scalar API
when field output is disabled.

Current status: complete. The angular field and its conservation tests are part
of the production estimator. Production reflected transport remains bounded by
the one-reflection rule above.

Gate: controlled tests cover unequal source ranges and weights, multiple trace
batches, direction signs, empty sets, scalar regression, and explicit missing
specular labels.

### Stage 2: exact direct atoms and body coupling

Use a `DirectionalMeasure` interface with exact atoms plus diffuse cells.
Pass exact atoms to AEGIS at their exact arrival directions. Production body
orientation is the fixed route-tangent yaw.

Current status: the exact atom plus diffuse-cell interface and chunked level-2
body coupling are implemented and independently verified. Direct results are
independent of angular-grid resolution. The fixed route-tangent yaw is the
production heading rule.

An optional exact uniform-yaw level-2 endpoint is also implemented and verified.
It averages the body surface field analytically over all horizontal headings.
It needs no heading samples and no additional ray tracing. Its area-weighted
mean, absorbed power, and whole-body SAR are exact yaw averages. Its reported
peak is named the peak of the yaw-averaged surface field. It is not the mean of
the peak over individual headings. The production route uses fixed
route-tangent yaw.

Gate: free-space point sources reproduce analytic level-2 body incidence. Grid
refinement does not move the direct body result because direct atoms are not
binned.

### Stage 3: validate the source curve

The full route arc-length source curve is implemented for production. Validate
its resolution, crop, lift, and builder provenance on held-out capture
sequences. Keep one source curve and its weights for every evaluation point in
the route.

Gate: report source sensitivity without reopening the production choice as a
discrete candidate process.

### Stage 4: bounded specular path classes

The production estimator implements at most one specular reflection. Adaptive
all-specular order 1 and the sampled mixed one-reflection suffix are the two
reflected branches. Higher specular orders are absent even when
`max_bounces=3`.

Gate: direct, order-1 all-specular, and mixed one-reflection paths remain
mutually exclusive under the declared bound. Controlled tests must report the
bound and must not describe the estimator as arbitrary-bounce specular
transport.

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
- keep the original collision support mesh. Blender Atlas LOD merging is
  display-only. Exact transport-mesh decimation is not low-risk without
  convergence evidence.
- keep Blender construction outside the numerical production loop

The semantic Atlas mesh simplification is promising because subdivision within
one original support triangle can be redundant. It needs a transport-specific
implementation. The existing Blender display simplification does not speed ray
tracing.

Gate: adopt a new sampler or mesh representation only if it preserves the
directional and body results within predeclared limits and gives a measured
runtime or memory gain.

### Stage 6: one frozen Korenmarkt run

Use admitted panorama positions only. The source curve, material atlas, fixed
route-tangent yaw, one-reflection transport limit, finish-only roughness,
transport version, output profile, and seeds are committed before the run.
Korenmarkt and Prague preflight checks passed. The one-seed pilots passed their
independent audits. Korenmarkt and Prague paired campaigns passed full audit.
Prague outputs cover both modes, seeds 7 through 22, and 68 points. See
[ROOFLINE_CAMPAIGN_RESULTS.md](ROOFLINE_CAMPAIGN_RESULTS.md) for the current
result record.

Gate: all controlled tests pass, numerical convergence is adequate, evidence
coverage is reported by interaction depth, and no method definition changes
after seeing the pilot output.

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
- direct, one-reflection specular, diffuse, and total transfer per standpoint
  and replica. The total uses the one-reflection production limit.
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
5. Direct, reflected, and total fixed-route CDFs for the matched settings, with
   the one-reflection limit stated.
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
3. Model assumptions, such as the source curve, finish-only roughness, and
   fixed route-tangent yaw. These need argument and sensitivity tests.
4. Numerical controls, such as ray count, angular cells, source quadrature, and
   bounce cap. These need convergence evidence.

Display colors, Blender sizes, cache chunks, and file-layout controls belong in
a separate engineering appendix. Mixing them into the scientific parameter
table makes the method look more arbitrary than it is.

## The decisive gates

The committed gates are:

- the full route arc-length source curve and units are fixed
- direct paths remain exact directional atoms for body coupling
- the common near-source rule is fixed
- finish-only roughness is implemented
- the one-reflection specular classes pass their controlled tests
- fixed route-tangent yaw and route measure are fixed
- finite-source directional transport has an independent validation
- performance is measured and retained outputs are sufficient for every
  reported statistic

Korenmarkt and Prague preflight checks passed. Korenmarkt paired campaigns have
passed their convergence and retention review. Prague paired outputs passed
their final independent audit. Only Korenmarkt and Prague are runnable now. Four sites require
semantic rebuilds, four require route or geometry repairs, and Times Square is
invalid under the current geometry contract. See
[MULTICITY_CAMPAIGN_READINESS.md](MULTICITY_CAMPAIGN_READINESS.md).

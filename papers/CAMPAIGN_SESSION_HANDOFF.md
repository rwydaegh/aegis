# V2 campaign session handoff and reproducibility plan

Date: 2026-08-10

This document reconstructs the full working session from the conversation
JSONL, the original campaign brief, the repository history, the current paper,
the benchmark reports, and the preserved remote evidence. It is intended to be
the durable starting point for the actual results run.

## Executive answer

Yes, a roughly three-hour GPU solve is now plausible for the agreed new core
paper scope, provided all corrected ray packs and body lookup tables already
exist.

That statement refers to this two-block design:

1. A full Cartesian MRT block over every body, array, propagation condition,
   frequency, seed, corridor position, and all 21 served-device placements.
2. A full Cartesian global ECBF block over the same expensive axes, six power
   retention points, and one chest zero-standoff served point.

The resulting scope is:

- 2,304 corrected common-center ray packs
- 9,216 body-ray bakes after multiplying by four phantoms
- 27,648 body, scene, and array items
- 580,608 MRT maps
- 165,888 new global ECBF maps
- 746,496 unique core maps

The measured projection on the existing RTX A6000 is about 3.7 hours with one
persistent worker and about 2.6 hours with two persistent workers. I would
reserve three hours for the warm solve and map stage.

This is not the original 8,128,512-map design. The old design applied 14 beams
to every item and, above 30 GHz, also hid 126 iterative local beam-optimization
problems inside each item. We deliberately replaced it with a clean full MRT
block and a clean full global-ECBF block because that is easier to explain and
matches what the paper actually needs.

The answer to “will it work as before, only faster?” needs two qualifications:

- The algebraic accelerations agree with their corrected reference paths to
  floating-point precision and are extensively tested.
- Several scientific bugs were corrected. The corrected array geometry,
  refracted TM field, high-band constraints, and singular ECBF behavior can
  legitimately change the paper's numbers. We should expect similar trends,
  not identical published values.

The fastest 2.6-hour projection also uses one disclosed approximation: a
single hard-polarization Fock pole is estimated from a deterministic stratified
sample of 4,096 triangles and 32 center rays. Against the exact materialized
implementation, 99% of compared values changed by less than 0.011%, the
largest ordinary retention change was 0.29%, and no discrete scientific output
changed. Two nearly tied peak locations swapped coordinates while their peak
values barely moved. This is strong evidence for “similarish,” but it is not
bitwise identity.

## What the session started from

The commissioning document was
`coherent-exposure-operator/V2_CAMPAIGN_BRIEF.md`. Its central goal was to
replace the current paper's mixture of result blocks with one clear Cartesian
study, add credible 60 and 100 GHz results, add body visibility and curvature
physics where feasible, and keep the paper simple.

The first proposed grid was:

```text
4 phantoms
x 3 array sizes
x 2 propagation conditions
x 8 frequencies
x 16 seeds
x 9 corridor positions
= 27,648 scene/body/array items
```

The brief then multiplied every item by 21 placements and 14 beams, producing
8,128,512 reported evaluations. At that point “one configuration” obscured
whether we meant a ray trace, a body bake, a beam optimization, or one body
map. This document avoids that word and names the unit directly.

## The final scope decision

The discussion established that Table I should be an MRT table. It does not
need 14 beam variants. The ECBF story is a separate mechanistic block and does
not need to repeat every local skin target and standoff across the entire
Cartesian product.

### Block A: full MRT Cartesian sweep

For every one of the 9,216 body-ray groups:

- build the body response once
- lift it exactly to M = 16, 64, and 256
- evaluate MRT at all 21 served-device placements
- retain the complete scalar exposure and compliance record

This block directly feeds the new Table I marginals, binding distributions,
MRT placement dependence, and most ensemble statements.

### Block B: full global ECBF Cartesian sweep

For every one of the same 9,216 body-ray groups:

- reuse the body response from the MRT block
- lift it to M = 16, 64, and 256
- use the chest at zero standoff
- evaluate six global whole-body ECBF retention fractions
- reuse the zero-standoff MRT result rather than storing it twice

This block provides ensemble ECBF suppression at fixed signal retention,
including the desired dramatic statements such as suppression at 50% retained
signal.

### Small sidecar studies

Several current figures need richer information than either core block. Those
should be explicit small jobs over predeclared representative cells:

- dense Pareto fronts
- incoherent and phase-scrambled floors
- skin-aimed local ECBF versus standoff
- absorption-mode decompositions
- averaging-area curves
- selected complete triangle maps
- worst-case and adversarial beams

These sidecars are scientifically useful. They should not be multiplied over
the whole 9,216-group product.

## What was completed during this session

### Recovery and data safety

- The v1-prime recovery completed exactly 2,336 of 2,336 expected items.
- There were zero missing, duplicate, or unexpected keys.
- All side stages completed.
- The final frozen archive contains 620 objects and 887,923,846 bytes.
- The archive was checked byte for byte off the GPU host.
- A v1 to v1-prime cause-attributed comparison bundle was produced.
- The published v1 state remains frozen at tag `v1-results-freeze` and commit
  `333bb8cebbd2bffe941254304ea87a8eeeb89c75`.

This gives us a durable historical baseline. It must not be overwritten by the
new v2 run.

### Array and ray-pack correction

The old Sionna bridge did not trace the intended square array. It created a
1 by M row and placed it at the first, corner element. For M = 256, the traced
object was effectively a 256-element linear array, not the intended 16 by 16
tilted square array.

All 593 old Sionna packs are therefore invalid as inputs to the new scientific
campaign. They remain valid only as frozen evidence of what the old paper run
actually did.

The corrected route now:

- traces one element at the authenticated array phase center
- keeps absolute delay with `normalize_delays=False`
- retains departure direction
- expands the field analytically to the requested physical array positions
- uses the intended arbitrary array geometry and element order
- stores a content-addressed `aegis-coherent-ray-pack/v2` center pack
- fails closed on old filenames and old schemas

Because the corrected center trace is independent of M, the full campaign now
needs 2,304 center packs rather than 6,912 array-specific packs. One measured
100 GHz pack is about 24 KB, so the corrected packs are not a storage problem.

### Physics and compliance corrections

The following are substantive scientific corrections, not mere speed work:

1. The refracted TM output vector now uses the exact complex transmitted
   direction rather than the incident TM basis. The implementation matches the
   stated equation and preserves tangential continuity.
2. The singular positive-semidefinite ECBF case now uses the correct
   pseudoinverse slack solution. The previous solver could return a zero-signal
   null-space beam in a feasible problem.
3. Above 30 GHz, compliance now simultaneously evaluates whole-body SAR,
   1 cm2 APD at 40 W/m2, and 4 cm2 APD at 20 W/m2. The most restrictive scale
   binds. Both local families remain in the result record.
4. The local high-band optimizer now uses joint cutting planes, exact full-map
   audits, exact active-operator audits, and a fail-closed certificate.
5. The multibody solver no longer applies the old fixed 0.97 safety projection
   and call the result converged. It uses analytic KKT derivatives, stable
   normalized constraints, adaptive work based on the number of active cuts,
   and explicit nonconvergence semantics.
6. Primal cleanup now detects cancellation-prone dense quadratic forms and
   uses a stable PSD spectral certificate where necessary.
7. The hard-polarization Fock exponent was corrected against the sourced
   cylinder asymptotics.
8. 60 and 100 GHz tissue parameters, Mie checks, high-band report fields, and
   evidence gates were added.

These changes mean a v2 result is not supposed to be numerically identical to
the published v1 result.

### Physics that was investigated but not promoted

- The Christ multilayer stacks remain SI-only diagnostics. A coherent layered
  TM response is not generally rank one, and no production anatomical mapping
  was approved.
- Full lossy Fock validation remains incomplete. The PEC cylinder and dominant
  hard-pole checks pass, but the full lossy profile is still a model limitation
  to disclose.
- `BODY_AWARE_CHANNEL_CONCLUSIONS.md` is a feasibility and design analysis. A
  general persistent angular body-channel lookup from `body_aware_channel.tex`
  was not implemented as production code.
- Mixed-precision discovery was rejected after a real A6000 test. End-to-end
  speed was approximately 1.0x and 9 of 36 cases failed exact certification.
- The exact batched GPU QCQP prototype was rejected. It was not faster than the
  scalar solver on the A6000.
- Active-cut continuation and multi-cut prototypes were rejected because their
  robust wall-clock gains did not reach 2x.
- A triangle/angular discovery approximation was rejected because cached exact
  sparse averaging was already much faster.

Rejected prototypes were removed from the production tree. Their negative
evidence was preserved where useful.

### Exact production accelerations

The following accelerated paths retain exact final checks and, where directly
compared, agree to floating-point precision:

- placement batching
- one common center trace shared across array sizes
- exact factorized channel assembly on JAX
- device-resident exposure maps
- GPU reduction to family maxima, lowest-index argmax, and target values
- compact trusted patch factors with dense fallback
- low-rank single-user KKT in the factor span with dense certification
- Cholesky KKT path with conservative conditioning gates and spectral fallback
- exact process-parallel KKT solves with CPU-only, one-native-thread worker
  attestation
- bounded transfer accounting and fail-closed local fallback
- cached body geometry and sparse averaging operators
- fixed-width zero padding of 103 to 273 center rays to width 288 for JIT reuse
- exact lazy array lift, applying the array factor only where needed

One retained M16 high-band distribution measured 65.49 seconds with the old
thread route and 5.41 seconds with the hardened process route, a 12.11x speedup
with 21 of 21 exact certificates and zero beam or constraint differences.

An authoritative corrected M16, LOS, 100 GHz production run measured:

- 34.645727 seconds total
- 9.760575 seconds in channel work
- 24.885152 seconds in the remainder
- 294 reported cells
- 126 jointly constrained local cells
- 1,819 exact process requests
- zero fallback
- eight attested CPU workers
- 1,364 MiB peak GPU memory
- maximum constraint violation 1.776e-15

The retained older run took 94.794046 seconds, giving an operational ratio of
2.736x. This is not a strict same-input ratio because the new run uses the
corrected array geometry and a new center pack.

## The two-block performance program

### First realistic pilot

The first two-block pilot proved the intended factorization:

```text
Q_M = A_M^H T A_M
map_M(X) = |B (A_M X)|^2
```

The body response is built once for a center-direction set. Array size enters
through the exact array factor. On four measured groups after one warm-up:

- array lift improved 6.0x
- lift plus map improved 1.94x
- end-to-end improved only 1.08x because array lift was no longer dominant
- all 5,184 outputs agreed within 1.26e-13 relative error
- no discrete output changed

This was important. It confirmed the paper's factorization intuition, but also
showed that body-surface preparation, not matrix multiplication, had become the
real cost.

### Sustained 64-group baseline

The realistic sustained Duke pilot included:

- LOS and NLOS
- seeds 0 and 1
- all eight frequencies
- corridor positions UE4 and UE5
- M = 16, 64, and 256
- full current surface physics
- all 21 MRT placements
- all six global ECBF points at zero standoff
- 5,184 reported maps

The original lazy path took 796.55 seconds. Its largest cost was repeated Fock
and visibility modifier preparation, not the maps themselves.

### Batched modifiers and fixed-width atlas

The first exact acceleration pass:

- vectorized the modifier calculation
- compacted triangle-only invariants to `(T, 1)`
- projected Fock radii in blocks
- padded center rays exactly to a common width of 288
- reused compiled JAX shapes
- kept the lazy array factorization

It reduced the sustained run from 796.55 to 240.15 seconds, a 3.32x
end-to-end speedup. Across 73,408 compared scientific numbers, the maximum
relative difference was 5.86e-11, the 99th percentile was 3.24e-14, and no
discrete result changed.

### Streamed shadow LUT and curvature

Visibility was already stored as a baked two-dimensional octahedral shadow
LUT. The expensive behavior was expanding the compact LUT on the CPU to a
complete triangle-by-ray table before each body atlas build.

The new path keeps compact data resident:

- signed int8 visibility LUT
- active-triangle indices
- occluder distance and radius
- principal curvatures and directions

The GPU atlas scan now performs the bilinear LUT reads and curvature projection
inside each triangle block. It no longer transfers or retains complete
visibility and Fock-radius tables.

The only added approximation is the deterministic sample used to choose one
scalar hard-polarization Fock pole.

On the identical sustained shard:

| Implementation | Wall time | Speedup from original |
| --- | ---: | ---: |
| Original lazy atlas | 796.55 s | 1.00x |
| Exact batched modifiers and fixed width | 240.15 s | 3.32x |
| Streamed GPU LUT and curvature | 120.61 s | 6.60x |

The modifier stage itself fell from 110.35 to 10.28 seconds, a 10.73x stage
gain over the preceding exact path.

Two persistent streamed workers completed the same 64 groups, including both
warm-ups, in 92.38 seconds. The comparable one-worker time including warm-up
was 132.56 seconds, a further 1.43x throughput gain. The two-worker and
one-worker records differed only at floating-point reduction level. Peak GPU
memory was about 5.9 GiB, and GPU utilization repeatedly reached 97 to 100%
during atlas bursts.

### Runtime projection

The progression for the agreed two-block core is:

| State | Projected A6000 solve time |
| --- | ---: |
| Original full-physics path | 22 to 32 h |
| Exact batched and fixed-width path | about 7.4 h |
| Streamed path, one worker | about 3.7 h |
| Streamed path, two workers | about 2.6 h |

These projections scale the measured sustained Duke result by all 9,216
body-ray groups and adjust only triangle-dominated stages by the actual mean
mesh size of the four bodies. They are much stronger than a microbenchmark,
but they are still projections rather than a completed full campaign.

## Confidence statement

### What I am confident about

- The corrected common-center array expansion is the right model for the
  intended physical arrays.
- The lazy body-response and array-factor algebra is exact.
- The fixed-width padding is exact because padded fields and array factors are
  zero.
- The batched modifier path agrees with the old corrected implementation to
  numerical precision.
- The two-worker route reproduces the one-worker route to numerical precision.
- The global ECBF core avoids the high-band local cutting-plane explosion by
  scientific design, not by silently weakening its tolerance.
- The detailed local high-band sidecar solver remains exact and fail closed.
- The fastest streamed path stays very close to its materialized oracle on the
  sustained 64-group comparison.

### What I would not promise

- I would not promise identical values to the current TWC paper. The current
  paper used invalid array packs and older physics.
- I would not call the streamed path bitwise exact. Its sampled scalar Fock
  pole is a small explicit approximation.
- I would not claim a complete paper-grade lossy Fock validation.
- I would not claim three hours from today's incomplete input cache.
- I would not launch the full run from the additive pilot script without first
  making its outputs sharded, resumable, and independently validated.

### Practical interpretation of “similarish”

There are two comparisons and they must remain separate:

1. **Fast versus oracle on identical corrected inputs.** This should be nearly
   identical. The measured 99th-percentile difference is 1.07e-4 relative,
   ordinary retention differs by at most 0.29%, and discrete outputs matched.
2. **Corrected v2 versus the published v1 paper.** Trends may be similar, but
   numeric changes are expected because the physical array, TM direction,
   high-band compliance, and some solver behavior were corrected.

## Is the three-hour run ready today?

Not quite. The compute kernel is ready enough for a campaign candidate, but the
full job still needs a small productionization pass.

### Inputs still needed

At the final session audit:

- 64 of 2,304 corrected center packs existed
- 2,240 center packs still needed tracing
- only Duke's body visibility LUT was present
- three phantom LUTs still needed baking

Estimated one-time preparation was 1 to 2 hours for tracing plus an unmeasured
1 to 2 hours for the three LUTs. The honest first-run estimate is therefore 4
to 6 hours, with a seven-hour reservation. Once inputs are baked, repeat runs
should take about 2.5 to 3 hours.

### Software gates before launch

1. Commit the current streamed-modifier and two-block code from a clean,
   reviewed tree.
2. Replace the pilot's single growing JSON file with immutable fine-grained
   shards and content hashes.
3. Add a full-grid manifest and inventory validator for exactly 9,216 groups,
   746,496 unique maps, and the declared axes.
4. Add resume semantics that never overwrite a completed valid shard.
5. Freeze the exact physics profile and explicitly record whether the sampled
   scalar Fock pole is enabled.
6. Predeclare the sidecar figure cells before viewing results.
7. Run a four-phantom oracle-versus-streamed sensitivity shard.
8. Archive the exact source tree, `uv.lock`, CLI, environment, ray hashes, LUT
   hashes, and output manifest before aggregation.

The current two-block script is excellent benchmark evidence. It is additive,
untracked, and writes one report repeatedly. It should not be treated as the
final campaign orchestrator without the gates above.

## Data needed to reproduce the TWC results

The guiding rule is to store all scalar outputs, all beam vectors, and selected
complete triangle maps. Do not store every full body map.

At the four-body mean of about 40,000 triangles, storing one float64 map for
all 746,496 outputs would take about 239 GB before metadata, extra quantities,
or replicas. Storing every body-response atlas would be far larger. Neither is
necessary.

The sustained pilot report was about 4.19 MB for 64 groups. At the same schema
density, the complete scalar report is roughly 600 MB before compression.
This is entirely manageable.

### Immutable run roots

Keep three distinct authorities:

```text
results/v1_published/
results/v1_prime/
results/v2_two_block/
```

Never overwrite `data/run` in place. Treat it as a working view assembled from
one selected immutable result root.

### Input inventory

Store and hash:

- all 2,304 center ray packs
- ray-pack schema and contract ID
- condition, seed, frequency, and served-position key
- scene description and source hash
- Sionna bridge source hash
- phase center
- departure directions
- requested physical element positions and their hash for M = 16, 64, 256
- all four STL meshes and hashes
- triangle centroids, normals, areas, and ordering hash
- body masses and tissue parameters
- all four visibility LUTs and hashes
- curvature arrays and hashes
- Fock parameterization and sampled-pole settings
- averaging operators for every applicable area and their hashes
- compliance limits and threshold policy

### Core result record

For every reported map, retain at least:

- body-ray group key: phantom, condition, seed, frequency, served position
- array size
- block: MRT or global ECBF
- anchor and standoff
- ECBF retention fraction where applicable
- conducted-power convention
- served signal power
- whole-body absorbed power
- whole-body SAR
- raw triangle peak APD
- 1 cm2 peak APD and triangle ID
- 4 cm2 peak APD and triangle ID
- APD at the served target for each applicable family
- peak coordinate and target coordinate
- peak-to-mean contrast
- focus retention and colocation metrics
- whole-body, 1 cm2, and 4 cm2 allowed-power scales
- binding-constraint label
- numerical cleanup scale and certificate residuals
- beam-vector offset and hash
- Q hash and eigenvalue summary
- ray-pack, mesh, LUT, averaging, source, and environment hashes
- per-stage timing and transfer ledger
- worker, shard, and retry identity

Store each complex beam vector. Across the complete core this is roughly
1.3 GB raw when grouped at native M rather than padding every beam to M = 256.
That is cheap insurance for exact map replay.

Do not store every dense Q. The three dense Q matrices for every group would be
about 10 GB raw and are reproducible from the authenticated inputs. Store Q
hashes and eigenvalue summaries for all groups, then store full Q only for the
audit sample and figure sidecars.

### Selected complete-map sidecars

Before the run, define a `figure_cells.json` manifest. For each selected cell,
store an NPZ containing:

- centroids, normals, and triangle areas
- exact triangle-order hash
- focus point
- complete Sab arrays for every displayed beam
- raw, 1 cm2, and 4 cm2 maps where relevant
- beam vectors
- full Q
- served channels
- all normalization constants
- scalar annotations printed in the figure
- input and source hashes

The user preference from this session is that the dramatic ECBF spatial figure
should use the zero-standoff beam. Record that decision before selecting the
specific scene key.

### Derived and publication data

Produce all derived files from immutable raw shards:

```text
manifest.json
inventory.json
SHA256SUMS
cells/*.jsonl
cells.parquet
beams/*.npz
certification/*.json
sidecars/avgarea/*.jsonl
sidecars/floors/*.jsonl
sidecars/modes/*.jsonl
sidecars/pareto/*.jsonl
sidecars/maps/*.npz
derived/summary.json
derived/tables/*.json
derived/tables/*.tex
derived/figure_source_manifest.json
derived/claim_source_manifest.json
```

Authoritative JSONL shards make validation and recovery simple. A derived
Parquet table makes marginal analysis fast. Both should carry schema versions.

### Source manifest for every paper object

`figure_source_manifest.json` and `claim_source_manifest.json` should map each
paper object to:

- raw input shard hashes
- exact row filter
- aggregation estimator
- uncertainty calculation
- generating script path and SHA
- software commit and environment lock
- generated data-file hash
- final PDF, PNG, JSON, or TeX hash

This prevents a future figure from silently reading stale `data/run` files.

## Crosswalk to the current TWC paper

The current results section contains two main tables, one ladder table, and five
data figures. Their data requirements are not identical.

| Paper object | Current source | New source plan |
| --- | --- | --- |
| Table I, setup and marginal means | `data/run/cells/*.jsonl`, `code/claims/megatable_w70.py` | Full MRT block. Rewrite the aggregator for true full-product marginals and state plainly that the table is MRT only. |
| Binding figure | `data/run/cells/*.jsonl`, `figures/binder/binder.py` | Full MRT block, filtered by declared array and frequency policy. |
| Binding verdict table | `data/run/cells/*.jsonl`, `paper_tables.py` | Full MRT block with both high-band local metrics retained. |
| Averaging-area figure | `data/run/averaging_area.json`, derived from `data/run/avgarea/*.jsonl` | Small fixed-cell area-sweep sidecar. Do not multiply it over the core. |
| Concentration ladder table | `summary.json`, cells, floors | MRT from the core. Incoherent, scrambled, skin-aimed, and worst-case rungs from explicit sidecars. |
| Concentration figure | `summary.json`, `data/run/modes/*.jsonl` | Core MRT plus local-standoff, floor, and absorption-mode sidecars. |
| Pareto figure | `data/run/pareto/*.jsonl`, `summary.json` | Dense representative-cell Pareto sidecar. The ensemble 50% suppression annotation comes from the full global-ECBF block. |
| ECBF map figure | `data/run/maps/duke_los_bs256_28_seed0.npz` | Predeclared selected-map sidecar, preferably updated to the approved zero-standoff story. |

The two-block core alone does not regenerate the current concentration,
averaging-area, dense Pareto, or six-panel map figure. That is expected. Their
sidecar jobs are small and should be part of the run manifest from the start.

## Concrete before-and-after plan

We need two different before-and-after reports.

### Scientific before and after

Compare the frozen published v1 and v1-prime outputs with corrected v2 on only
the intersection of scientifically meaningful axes. Report:

- absolute old and new value
- ratio and signed relative change
- matched-cell distribution of changes
- change in marginal mean and median
- change in uncertainty interval
- change in binding classification
- change in figure annotations

Because the old array geometry was wrong, label this comparison “published
pipeline versus corrected pipeline.” Do not describe every difference as an
effect of visibility or Fock.

For every table, save a three-column machine-readable artifact:

```text
published_v1
recovered_v1_prime
corrected_v2
```

For every figure, retain the old source data and PDF beside the new source data
and PDF. Generate a visual side-by-side sheet for review before modifying the
paper.

### Accelerator before and after

On a fixed corrected audit shard, compare:

- materialized surface modifiers versus streamed modifiers
- materialized array channel versus lazy array lift
- one worker versus two workers

This comparison answers whether the speed changes preserve the corrected
science. It must use identical ray packs, LUTs, meshes, beam scope, precision,
and aggregation. Store all compared scalar rows, selected maps, timing ledgers,
and diff statistics.

Never mix the scientific correction comparison with the accelerator parity
comparison. One can move results materially. The other should not.

## Recommended execution sequence

1. Freeze and review the current code.
2. Convert the two-block pilot into a sharded resumable campaign command.
3. Define `figure_cells.json` and all sidecar manifests.
4. Generate and validate the missing center packs and body LUTs.
5. Run a four-body materialized-versus-streamed audit shard.
6. Launch two persistent GPU workers over dynamic fine-grained shards.
7. Continuously copy completed immutable shards and hashes off the rented host.
8. Validate exact group and map counts before aggregation.
9. Build the Parquet view, summary, tables, and figure sidecars.
10. Generate the scientific and accelerator before-and-after reports.
11. Rebuild every affected TWC table and figure in a staging output tree.
12. Review the findings before changing paper prose or replacing published
    assets.
13. Verify the complete off-box archive.
14. Terminate the rented instance through the provider control plane and verify
    that billing stopped.

## Current implementation and evidence locations

Primary documents:

- `coherent-exposure-operator/V2_CAMPAIGN_BRIEF.md`
- `coherent-exposure-operator/versions_and_reviews/v2/V2_FINDINGS_REPORT.md`
- `coherent-exposure-operator/versions_and_reviews/v2/PERFORMANCE_REDESIGN_PROMPTS.md`
- `TWO_BLOCK_GPU_PILOT_RESULTS.md`
- `BODY_AWARE_CHANNEL_CONCLUSIONS.md`

Primary current code:

- `coherent-exposure-operator/code/scripts/v2_two_block_pilot.py`
- `coherent-exposure-operator/code/scripts/paper_run.py`
- `coherent-exposure-operator/code/lib/paper_aegis/coherent/factored_kernel.py`
- `coherent-exposure-operator/code/lib/paper_aegis/geometry/visibility.py`
- `coherent-exposure-operator/code/lib/paper_aegis/geometry/fock_gate.py`

Preserved streamed-pilot evidence:

- `/tmp/aegis-streamed-modifier-evidence/`
- sustained report SHA prefix `03da80e`
- one-worker report SHA prefix `3b40bc`
- dual LOS report SHA prefix `c8826f`
- dual NLOS report SHA prefix `8513c9`
- wall report SHA prefix `6ec90a`

The remote streamed scratch root was
`/tmp/paper-c-streamed-modifiers.qu6NlI`.

The corrected authoritative M16, 100 GHz production evidence was independently
downloaded to
`/tmp/paper-c-v2-production-m16-evidence.d73CUi`, with bundle SHA beginning
`bd6b3a` and certification SHA beginning `5e5458`.

## Current repository state

The core campaign repository contains committed correctness and production
work through commit `66886eb`, followed by benchmark-accounting and archived
performance-dialogue commits. The newest streamed-modifier and two-block pilot
work remains uncommitted in a dirty shared tree.

Modified production files include the factored kernel, visibility, Fock gate,
paper runner, and their tests. The two-block pilot and its tests are untracked.
There are also unrelated pre-existing edits and experimental files. They must
be reviewed and staged by explicit path. Do not use `git add -A`.

The last fresh verification reported during this session was:

- complete non-slow project suite passed with expected skips
- streamed JAX materialized parity passed
- pilot, visibility, curvature, and surface-physics tests passed
- relevant campaign and GPU-parity suites passed
- Ruff lint and format checks passed
- Python compilation passed
- `git diff --check` passed

This document itself does not replace a fresh verification at the commit and
launch boundary.

## GPU lifecycle note

The Blue Lobster instance is idle and has no compute process. The recorded UUID
is `3b17984a-6baa-4c24-994b-83c6a6f790dd`.

The automated control-plane requests are currently blocked by Cloudflare with
HTTP 403, Error 1010, and `browser_signature_banned`. SSH shutdown does not
guarantee that provider billing stops. Therefore the instance must be
terminated through the Blue Lobster dashboard, or through a restored official
control-plane API, and disappearance plus billing cessation must be verified.

## Bottom line

The session achieved three separate things:

1. It found and corrected several serious scientific and numerical issues.
2. It replaced an unnecessarily huge 14-beam scope with a clear MRT Cartesian
   block and a clear global-ECBF Cartesian block.
3. It accelerated the realistic two-block pipeline by 6.60x in one worker and
   added a measured 1.43x from two-worker overlap, bringing the prepared-input
   projection to about 2.6 hours on the existing A6000.

I am confident that a three-hour warm run can produce a scientifically useful
and nearly oracle-equivalent two-block dataset after the runner is made
resumable and the inputs are complete. I am not claiming that those results
will match the old TWC numbers exactly. They should be treated as the corrected
v2 results, with an explicit old-versus-new report and a separate exact-versus-
fast accelerator audit.

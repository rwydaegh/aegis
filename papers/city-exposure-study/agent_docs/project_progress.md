# Project progress

## Completed package: semantic-twin refactor and production path

Status: completed and squash-merged on 2026-08-06 in pull request 919 as
commit `4f2128a0`.

The completed scope covers command ownership, package boundaries, production
configuration, output retention, checkpoint and restart behavior, measured
performance, and the optional Blender audit path.

Completed results:

- All 69 root scripts have a named production, supported-wrapper, diagnostic,
  manual, or archive role.
- Eight large root commands now use package CLI and domain modules. The root
  files remain small compatibility entry points.
- Named run configurations enforce the next-event and escape-study contracts.
- Minimal, standard, and full output profiles define what is kept. Standard
  and full keep one angular spectrum for every selected source model.
- CDF campaigns use atomic replica shards, exact restart, formal stopping, and
  final consolidation. Normal shard mode no longer copies the whole replica
  history after every replica.
- Blender-only Atlas display geometry is simpler while canonical transport
  arrays remain exact. The Prague audit reduced 1,464,985 canonical triangles
  to 801,098 display polygons. This improves display size and does not claim a
  ray-tracing speed gain.
- Production invariants use explicit runtime errors instead of removable
  Python assertions.
- The normal result path and the optional Blender audit path are documented
  separately.

Final verification:

- 2,618 tests passed, 29 skipped, 21 expected failures, and 41 local or slow
  tests were deselected in the clean-worktree gate.
- The final focused gate passed 203 tests. An independent reviewer found no
  blocking production defect.
- Ruff, formatting for 374 files, Python compilation, and diff checks passed.
- Qlty Ruff, TruffleHog, and the changed-production Bandit check found no
  issues.
- Tests that need ignored city artifacts remain an explicit environment
  exclusion. They are not claimed as passed in the clean worktree.

Measured Prague facts remain: 185.0 seconds for a ready-input 68-point walk,
1.346 seconds per warm A6000 standpoint, and 40.15 minutes for 24 trace-only
replicas. No paid GPU is active. No multi-city run was launched.

## Completed package: publication physics correction

Status: completed and squash-merged on 2026-08-06 in pull request 920 as
commit `d565cac4`.

The body surface mean now uses absorbed power divided by total body surface
area. Exact body triangle areas are retained in CDF checkpoint shards and the
consolidated result. Legacy checkpoints that retained full per-triangle `Sab`
can be migrated without another trace. Checkpoint validation now rejects stale
areas, wrong dtypes, and malformed metadata.

The corrected 24-replica Prague analysis still meets the formal stopping rule.
The correction changes the Prague rooftop ensemble point means by a median of
3.79 percent, or 0.161 dB. Peak `Sab`, absorbed power, and whole-body SAR do not
change.

Final verification for this package:

- 3,539 root tests passed and 81 were skipped.
- The final focused gate passed 206 tests with 10 expected failures.
- Independent broader verification passed 247 tests, skipped 4, deselected 1,
  and recorded 10 expected failures.
- Ruff, formatting, Python compilation, diff checks, and the scoped Qlty checks
  passed.

Publication decisions are recorded in
`semantic_twin/docs/PUBLICATION_PHYSICS_DECISIONS.md`. Next-event estimation
remains diagnostic-only. The production roughness surrogate remains unchanged
and needs an explicit paper decision before a new trace campaign.

No launch-sampler decision has been made. Production still uses 1,600,000 IID
uniform launch directions and 4,096 Fibonacci output cells. The next proposed
method study holds both numbers fixed and compares IID launch with an exactly
stratified or low-discrepancy launch. It must test the full local angular field,
per-cell variance, body results, and runtime. Small changes in final scalar
results alone are not grounds for changing the method. Adaptive allocation is a
later experiment, not an accepted design.

No paid GPU is active. No new city campaign has been approved or launched. The
agentic AI and SAM3 prompt study remains a written plan in
`semantic_twin/docs/AGENTIC_AI_VISION.md`.

## Completed package: panorama-colocated roofline diagnostic field

Status: completed and squash-merged on 2026-08-06 in pull request 921 as
commit `6feeac56`.

The explicit facade-tip estimator now retains direct and diffuse next-event
contributions on the receiver angular grid. Per-bin sums reproduce the scalar
direct and bounced terms. Diffuse deposits follow each reciprocal ray's original
launch cell across trace batches and combined observers. Equal source weighting
keeps the historical arithmetic and random stream. Optional explicit weights
have validation and a scale-stable, platform-stable provenance hash.

The result is deliberately diagnostic. It omits all-specular paths and mixed
paths with a specular suffix. Direct paths are binned for conservation and
visual inspection. Final body coupling must retain direct point-source paths as
exact directional atoms.

Verification passed 2,636 broad semantic-twin tests, with 29 skipped, 19 expected
failures, and 41 slow or local-data tests deselected. The final independent gate
passed 112 focused and adjacent tests with 3 expected failures. Ruff, formatting,
pre-commit, codespell, compilation, and diff checks passed.

The critically reviewed scientific plan is
`semantic_twin/docs/ROOFLINE_EXPOSURE_GRAND_PLAN.md`. It corrects the source
measure, units, direct-atom, body-orientation, specular-path, validation,
performance, output, and paper-scope requirements before a large campaign.

## Completed package: exact directional atoms and body coupling

Status: completed and squash-merged on 2026-08-06 in pull request 922 as
commit `e1ae5fc1`.

The transport-to-body interface now separates exact direct-source atoms from
diffuse angular-grid mass. Direct paths reach AEGIS at their physical arrival
directions. The diagnostic direct bins remain available for conservation and
visualization, but they cannot enter body coupling a second time. Level-2 body
coupling is chunked so thousands of directions do not require one full
body-triangle by path matrix.

The broad clean-checkout gate passed 2,648 tests, with 29 skipped, 19 expected
failures, and 41 slow or local-data tests deselected. Independent verification
passed 32 focused tests and compared 4,097 directions against the AEGIS engine.
The maximum surface-field difference was 2.84e-14. Ruff, formatting, Python
compilation, pre-commit, codespell, and diff checks passed.

This package does not choose the body heading, final facade-tip source measure,
roughness rule, or complete specular connection. Those remain gates before a
city CDF campaign. The next bounded package is the body-orientation rule.

## Completed package: exact uniform-yaw body endpoint

Status: completed and squash-merged on 2026-08-06 in pull request 923 as
commit `7656cf56`.

Level-2 body coupling can now average the surface field exactly over a uniform
horizontal body heading. The closed form needs no heading samples and no new
transport trace. It accepts the same exact atoms and diffuse cells as the fixed
body endpoint.

The result names its peak as the peak of the yaw-averaged surface field. This is
different from the mean of the peak over individual headings. Area-weighted
mean absorbed density, absorbed power, and whole-body SAR commute with the yaw
average and are exact for the level-2 plane-wave model.

Two-axis chunking reduced measured Duke-sized peak memory from about 1.50 GiB
to about 73 MiB for the production coupler endpoint. The broad clean-checkout
gate passed 2,674 tests, with 29 skipped, 19 expected failures, and 41 slow or
local-data tests deselected. Independent dense-yaw and AEGIS checks passed.

This endpoint is optional. Existing results still use the mesh's native yaw.
The paper must still freeze whether the intended pedestrian is a uniformly
oriented standing person, a route-aligned walker, or a named fixed-heading
scenario. The source measure and specular path completion remain later gates.

## Completed package: physical roofline exposure pipeline

Status: completed and squash-merged on 2026-08-07 in pull request 924 as
commit `e31d15ce`.

This package closes the production physics and campaign work that remained
after pull request 923:

- Every route standpoint has a deterministic route-tangent body yaw.
- Equal active antenna density per ground area is represented by the eligible
  roofline length inside the study crop. Sources use arc-length quadrature on
  that curve. The normalized source law and the physical antenna count remain
  separate quantities.
- Production roughness uses surface-finish RMS height. Masonry-specific
  roughness is outside scope.
- Direct and one-reflection all-specular paths reach the body as exact
  directions. Mixed rough transport remains a sampled suffix. Production is
  explicitly bounded to one specular reflection.
- The CUDA path keeps transport arrays on the device and reuses specular face
  proposals across body surfaces.
- Atomic, restartable paired campaigns compare IID and rotated-Fibonacci
  sampling under matched seeds. Comparison tools reject mismatched, missing,
  duplicate, or corrupt campaign artifacts.
- Minimal retained results include route-point exposure metrics, convergence
  evidence, provenance, and timing. Standard and full profiles retain richer
  diagnostic fields for later analysis and Blender review.

Two city campaigns are complete:

- Korenmarkt: 16 seeds, 13 route points. The median surplus is 1.12153 dB for
  IID and 1.12156 dB for rotated Fibonacci. The maximum paired total-field
  change is 0.0324 dB.
- Prague: 16 seeds, 68 route points. The median surplus is 1.10519 dB for IID
  and 1.10465 dB for rotated Fibonacci. The 90th percentile paired total-field
  change is 0.00756 dB.

Both independent artifact audits passed. The evidence does not support changing
production from IID to rotated Fibonacci. The Prague recovery spans two code
versions, so its scientific arrays are valid while its aggregate timing is not
suitable for a paper speed claim.

Final verification:

- 2,872 semantic-twin tests passed, 40 skipped, 46 deselected, and 18 expected
  failures were recorded.
- 243 focused AEGIS physics tests passed.
- 166 CUDA tests passed on a real A6000 with no skips.
- The final campaign and comparator gate passed 53 tests.
- Ruff, formatting, scoped Qlty, YAML, pre-commit, documentation, and diff
  checks passed.

Korenmarkt and Prague are the only cities that currently pass every production
input gate. The other candidate cities need current hybrid semantics, semantic
atlases, or route and panorama coverage before a valid campaign can run. No
ten-city results were invented from old or incomplete inputs.

The result package is stored at
`/home/user/aegis-roofline-results-20260807T015530Z/`. It contains the paired
campaigns, strict comparisons, recovery record, and two-city paper figures. No
paid GPU instance remains active.

The next paper-facing work is to prepare the methods and results text, decide
which retained quantities enter the main paper or supplement, acquire valid
inputs for more cities, and run a clean timing campaign if a formal runtime
claim is needed.

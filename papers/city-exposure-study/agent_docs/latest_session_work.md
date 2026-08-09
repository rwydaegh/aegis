# Latest session work

## Physical roofline pipeline completion

Pull request 924 completed the production roofline exposure pipeline and merged
to `master` on 2026-08-07 as commit `e31d15ce`.

The merged method now uses route-aligned body orientation, equal active antenna
density per ground area, arc-length-weighted source placement on the eligible
roofline, and surface-finish RMS roughness. Direct and one-reflection
all-specular paths remain exact directional contributions. Rough mixed paths
use the sampled suffix estimator. Masonry-specific roughness has been removed
from the production scope.

The campaign layer is atomic and restartable. It validates locations and paired
seeds, records hashes, compares IID and rotated-Fibonacci sampling, and exports
paper figures. It also reuses specular face proposals and keeps the CUDA trace
on the device where possible.

Korenmarkt and Prague each completed 16 paired seeds. Both artifact audits
passed. Their exposure results agree closely between samplers, while the
per-cell variance results do not show a stable rotated-Fibonacci advantage.
Production therefore remains IID. Exact values and limits are recorded in
`semantic_twin/docs/ROOFLINE_CAMPAIGN_RESULTS.md`.

The retained result package is
`/home/user/aegis-roofline-results-20260807T015530Z/`. Prague was recovered after
a memory failure by resuming the missing seeds with the proposal-reuse change.
The recovery is fully hashed. Its science arrays are valid. Its aggregate
timing mixes implementations and must not be used as a paper timing result.

Only Korenmarkt and Prague currently have every production input. The readiness
and acquisition gaps for other cities are recorded in
`semantic_twin/docs/MULTICITY_CAMPAIGN_READINESS.md`. No paid GPU remains active.

Final gates passed 2,872 broad semantic-twin tests, 243 focused AEGIS physics
tests, 166 real-A6000 CUDA tests, and 53 final campaign tests. Ruff, formatting,
scoped Qlty, YAML, pre-commit, documentation, and diff checks passed.

The practical next step is paper assembly. Use the two-city result figure as the
first complete result, keep the sampler comparison as a method check, and only
expand to more cities after their semantic and route inputs pass the documented
gates. Run a fresh single-version campaign before making a formal runtime claim.

## Earlier session history

The semantic-twin production refactor and the body-mean physics correction are
both complete on `master`.

- Pull request 919 merged the production refactor as commit `4f2128a0`.
- Pull request 920 merged the area-weighted body mean as commit `d565cac4`.

The second package computes mean absorbed power density as absorbed power divided
by total body surface area. It retains exact body triangle areas in new CDF
checkpoints and can migrate legacy checkpoints that retained full `Sab` without
retracing. It also strengthens checkpoint corruption checks and records the
remaining publication physics choices.

Verification after the correction passed 3,539 root tests with 81 skipped. The
focused semantic-twin gate passed 206 tests with 10 expected failures. Independent
broader verification passed 247 tests, skipped 4, deselected 1, and recorded 10
expected failures. Ruff, formatting, compilation, diff checks, and scoped Qlty
checks passed. A corrected CPU analysis of the retained 24 Prague replicas still
meets the formal stopping rule.

The Prague production artifacts remain in the dirty main checkout, including:

- `semantic_twin/outputs/propagation_viz/prague_staromestske_propagation_v2.blend`
- `semantic_twin/outputs/propagation_viz/prague_gpu_qa_v2/`
- `semantic_twin/outputs/cdf_convergence_prague_4096_atlas_v1/`
- `semantic_twin/outputs/performance/prague_atlas_lookup_20260806/`

No transport sampler, ray count, output-cell count, roughness rule, or production
result was changed. The current launch remains IID uniform with 1,600,000 rays,
and directions are accumulated into 4,096 Fibonacci cells. The next proposed
study keeps that budget fixed and compares IID launch with an exactly stratified
or low-discrepancy launch. It must inspect the full angular field and per-cell
variance, not only final scalar exposure values. Adaptive allocation can be
considered later if the fixed-budget comparison shows a need.

The Sionna comparison validates integrated scalar transport. It does not validate
all receiver-side angular cells or body coupling. This limit is now explicit in
`semantic_twin/docs/2026-08-03_161110_CROSS_VALIDATION.md`.

No paid GPU is active. No new city campaign was started. Before any new trace,
make an explicit production roughness choice. Next-event estimation remains a
diagnostic-only quantity. The agentic AI and SAM3 prompt study remains a written,
no-code plan in `semantic_twin/docs/AGENTIC_AI_VISION.md`.

Pull request 921 then added the first explicit-roofline angular-field prototype
and merged as commit `6feeac56`. It retains exact direct contribution masses and
diffuse next-event masses on the receiver grid, supports explicit normalized
source weights with stable provenance, and preserves the old scalar estimator
when field output is disabled. The broad gate passed 2,636 tests. The final
independent gate passed 112 tests with 3 expected failures.

The prototype is a conservation and direction result. It bins direct point
sources and omits all-specular and mixed specular-suffix paths. It is not a final
body field or a total-exposure result.

The scientific route is now recorded in
`semantic_twin/docs/ROOFLINE_EXPOSURE_GRAND_PLAN.md`. The next bounded package is
an atom-plus-density directional measure and exact direct-source body coupling.
The later hard gates are a declared facade-tip source measure, common near-source
rule, body orientation, roughness choice, complete specular path partition, and
finite-source validation before any large city campaign.

Pull request 922 completed the atom-plus-density package and merged as commit
`e1ae5fc1`. Direct roofline sources now remain exact arrival-direction atoms.
Diffuse next-event mass remains on the angular grid. The level-2 body adapter
couples both in directional chunks and keeps the direct result independent of
the diagnostic grid resolution.

The broad clean-checkout gate passed 2,648 tests, with 29 skipped, 19 expected
failures, and 41 slow or local-data tests deselected. Independent verification
passed 32 focused tests. A 4,097-direction stress case matched the explicit
AEGIS engine to floating-point roundoff. All repository checks passed.

The plan file is tracked on remote `master` and also copied into the user's
active dirty checkout at
`semantic_twin/docs/ROOFLINE_EXPOSURE_GRAND_PLAN.md`. The active-checkout copy is
untracked because that checkout is on the older
`feature/coherent-exposure-studio` branch.

The next bounded decision is body orientation along a route. After that come
the source-measure study, roughness choice, complete specular path accounting,
and the frozen Korenmarkt audit.

Pull request 923 added an optional exact uniform-yaw level-2 body endpoint and
merged as commit `7656cf56`. It analytically averages the per-triangle body
field over all horizontal headings. It needs no yaw samples and no new ray
trace. Its scalar result names the peak of the yaw-averaged field explicitly,
so it cannot be confused with the mean individual peak over headings.

The production endpoint chunks body normals and directions. On a Duke-sized
stress case, peak memory fell from about 1.50 GiB to about 73 MiB. The broad
clean-checkout gate passed 2,674 tests, with 29 skipped, 19 expected failures,
and 41 slow or local-data tests deselected. Independent dense-yaw, AEGIS,
boundary, chunking, and mutation checks passed.

Existing production outputs remain unchanged and still use the body mesh's
native yaw. Uniform yaw is now a tested option, not the frozen paper rule. The
next scientific action is to state the body population meaning and endpoint
order, then freeze the source measure before complete specular transport work.

# Refactor status

The semantic-twin refactor is complete within its stated scope. The scope is
architecture, production execution contracts, output profiles, checkpoint
behavior, and the supporting performance and retention records. The historical
completion snapshot used `f5f394da`, with performance proposal reuse from
`9111c591`, report commits `8db6bef0` and `37b4498d`, and paired campaigns from
`b985ab58`. The active contract has since advanced and is identified by each
new campaign manifest rather than by this historical paragraph.

> **Current-contract notice.** The authoritative runtime contract is
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md). This
> status page preserves earlier refactor and campaign snapshots, including
> older ray-count, estimator, and readiness wording. Current production uses
> 200,000 IID primary rays, 4,096 passive angular cells, exact direct transfer,
> stochastic next-event diffuse and mixed transport, and the declared
> one-reflection specular policy. Mask2Former and SAM3 session reuse passed
> exact live A6000 scientific-output parity.

## What 100% complete means

The refactor is 100% complete within its stated architecture and production
execution scope. Every root command has an owner and status,
the intended command boundaries are in the package, profile and checkpoint
contracts are explicit, and the normal production path is separate from the
optional audit path. The committed production contract also records the full
route arc-length source curve, fixed route-tangent yaw, finish-only roughness,
and the one-reflection specular limit. It does not mean that higher specular
orders are available or that new multi-city results have been regenerated.

## Completed boundaries

- All 69 root scripts are classified in `COMMAND_STATUS.md`. Four are
  production commands, eight are supported compatibility wrappers, one is an
  archive candidate, and the rest are diagnostic or manual tools. There is no
  unresolved command ownership.
- Eight command and parser extractions are complete: `run_exposure`,
  `run_next_event`, `build_surface_atlas`, `propagation_blender`,
  `export_propagation_payload`, `compare_mesh_depth`,
  `download_inhouse_tiles`, and `benchmark_walk_body`.
- Root files remain compatibility wrappers. Package domain modules outside
  `semantic_twin/cli` have no `argparse` or `main` boundary violation.
- Named `RunConfig` method profiles enforce the next-event roofline and
  escape-grid band contracts. The generic executor refuses next-event misuse.
- Output profiles are explicit. `minimal` writes scalar rows and a manifest
  for a generic walk. It does not allocate spectra and does not provide an
  incremental restart. `standard` and `full` retain one `rho` spectrum per
  selected source model.
- CDF campaigns use atomic replica shards, exact resume, formal stopping, and
  final consolidation. Shard-mode in-memory accumulation is list-backed and
  materializes only at formal looks and final boundaries. It removes per-
  replica whole-history concatenation. The legacy monolithic fallback remains
  compatible. Synthetic full, legacy, and interrupted-resume arrays are
  exactly equal.
- Atlas transport lookup reuse is merged and exact. Blender-only Atlas display
  LOD preserves canonical arrays and never merges across support triangles or
  categories. It is a display change and does not speed transport.
- Immutable full-geometry device face proposals are built and uploaded once per
  estimator, then reused across replicas. This runtime change does not alter
  scientific outputs.

## Performance and storage result

A stage timing ledger and retention policy now record the work and the data to
keep. The following are the latest recorded values from ready-input Prague
work:

- A 68-point walk took 185.0 seconds.
- A warm A6000 trace took 1.346 seconds per point.
- A 24-replica trace took 40.15 minutes.
- The historical standard rooftop-only archive was 2.17 MB.
- New all-model storage is estimated at about 2 MB per selected model. This
  estimate is not measured.
- Fishnet cutting took 798.9 seconds.
- Blender remains optional.

The real Prague Atlas audit measured 1,464,985 canonical triangles reduced to
801,098 display polygons, a 1.829x reduction, in 2.45 seconds of CPU time.
This does not change transport arrays or transport speed. No measured GPU or
RAM improvement is claimed.

Collision BVH support remains the original 617,091 faces for Korenmarkt and
664,619 faces for Prague. Exact transport-mesh decimation has no convergence
evidence and is not a low-risk optimization.

## Verification evidence

The latest recorded verification is:

- The local broad gate passed 2,872 tests, skipped 40, marked 18 as expected
  failures, and deselected 46.
- The focused gate passed 202 tests. Its skips are local CUDA-only tests.
- The real A6000 expanded campaign gate passed 163 tests with no skips in
  9.97 seconds.
- The final CUDA gate passed 166 tests in 12.53 seconds.
- Korenmarkt and Prague preflight checks passed.
- Korenmarkt and Prague one-seed CUDA pilots passed independent audits.
- Korenmarkt IID and Fibonacci paired 16-seed campaigns passed full audit with
  seeds 7 through 22 and looks 4, 8, 12, and 16. Prague paired outputs cover
  both modes, seeds 7 through 22, and 68 points. Both paired audits passed.
  Each Prague mode has 49 hash-valid manifest entries, a 68x56024 body array,
  and no orphan files. Fibonacci is not adopted.
- Atlas lookup reuse produced 96 identical result hashes in the relevant GPU
  parity check.

The Korenmarkt paired campaign is complete and its results are documented in
[ROOFLINE_CAMPAIGN_RESULTS.md](ROOFLINE_CAMPAIGN_RESULTS.md). Prague paired
outputs passed their final independent audit. Recovery timing remains excluded
from scientific timing claims.

## Environment exclusions

Tests marked `local_data` require ignored artifacts in the dirty main
checkout. They are reported separately and are not claimed as passed in a
clean worktree. The focused gate's CUDA skips are local environment skips.
The Korenmarkt and Prague campaigns form a completed two-site paired result.
There is no broader multi-city result under the current readiness contract.

## Publication work that remains

The area-weighted body mean is fixed and documented. The committed production
source is a full route arc-length source curve. Production uses fixed
route-tangent yaw and finish-only roughness. Specular transport allows at most
one reflection, using adaptive all-specular order 1 and a sampled mixed
one-reflection suffix. Higher specular orders are absent even when
`max_bounces=3`. The refactor is complete as architecture, production
contracts, performance, and output work. It is not a claim that higher-order
specular transport or regenerated multi-city results are complete.

## Production and audit tracks

The normal production track is:

1. `fetch_site_panoramas.py`
2. `build_site_semantics.py`
3. `python -m semantic_twin.cli.roofline_campaign --config CONFIG`
4. `python -m semantic_twin.cli.roofline_campaign_comparison`
5. `python -m semantic_twin.cli.roofline_result_figures`

The older `run_cdf_convergence.py` path remains a separate convergence tool. It
is not the paired roofline campaign front door.

The optional audit and Blender track uses the sealed inputs to build and
inspect propagation bundles. It includes `build_propagation_blends.py` and
the explicit payload and Blender exporters. Blender work is not required for
normal numerical production.

## Final verification checklist

- [x] Record the local broad, focused, A6000, and preflight gates above.
- [x] Keep local-data and CUDA-only environment skips separate in the final
      release record.
- [x] Finish and review the Korenmarkt and Prague paired campaigns. Both final
      independent audits passed. Recovery timing remains excluded.
- [x] Record the 166-test final CUDA gate and the hashed recovery provenance.
- [ ] State the one-reflection specular limit in the paper method and results.
- [ ] Plan any future city campaign only after the readiness review. Do not infer
      a GPU or RAM gain from the refactor.

## Safe next action

Review the publication record with the committed source, yaw, roughness, and
one-reflection limits stated plainly. A new city campaign should start only
after that review, the [multi-city readiness record](MULTICITY_CAMPAIGN_READINESS.md),
and an explicit run plan.

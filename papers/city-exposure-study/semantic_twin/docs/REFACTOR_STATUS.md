# Refactor status

The semantic-twin refactor is complete within its stated scope. The scope is
architecture, execution contracts, output profiles, checkpoint behavior, and
the supporting performance and retention records.

## What 100% complete means

The refactor is 100% complete when every root command has an owner and status,
the intended command boundaries are in the package, profile and checkpoint
contracts are explicit, and the normal production path is separate from the
optional audit path. It does not mean that all publication physics are settled
or that new multi-city results have been regenerated.

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

## Verification evidence

The final clean-worktree verification is:

- 151 focused checkpoint and CDF tests passed.
- The broad non-slow, non-local suite passed 2,618 tests, skipped 29, marked
  21 as expected failures, and deselected 41. Golden tests were included.
- A final focused gate after replacing production assertions with explicit
  errors passed 203 tests and deselected one slow local-data test.
- Atlas lookup reuse produced 96 identical result hashes in the relevant GPU
  parity check.
- Ruff passed. Ruff formatting reported all 374 files already formatted.
  Python compilation and `git diff --check` passed.
- Qlty's Ruff and TruffleHog checks found no issues. A Bandit check of the
  changed production files found no issues after production invariants were
  changed from removable assertions to explicit runtime checks.

## Environment exclusions

Tests marked `local_data` require ignored artifacts in the dirty main
checkout. They are reported separately and are not claimed as passed in a
clean worktree. No paid GPU is active. No multi-city run was launched.

## Publication work that remains

The area-weighted body mean is fixed and documented. Next-event estimation is
bounded to diagnostic-only use, with its absolute totals and escape-gap claims
excluded. Facade roughness still needs an explicit surrogate choice before any
retrace. The refactor is complete as architecture, performance, and output
work. It is not a claim that final paper physics or regenerated multi-city
results are complete.

## Production and audit tracks

The exact normal production track is:

1. `fetch_site_panoramas.py`
2. `build_site_semantics.py`
3. `run_cdf_convergence.py`

The optional audit and Blender track uses the sealed inputs to build and
inspect propagation bundles. It includes `build_propagation_blends.py` and
the explicit payload and Blender exporters. Blender work is not required for
normal numerical production.

## Final verification checklist

- [x] Run the final Ruff check and formatting check.
- [x] Run `git diff --check` and inspect the final documentation diff.
- [x] Record the final test and static-check results.
- [x] Keep local-data tests separate because their ignored artifacts are not
      present in the intended checkout.
- [x] Fix the area-weighted body mean and record the retained-data correction.
- [x] Bound next-event estimation to diagnostic-only use.
- [ ] Choose an explicit roughness surrogate before retracing.
- [ ] Plan any future city campaign only after the roughness choice. Do not
      infer a GPU or RAM gain from the refactor.

## Safe next action

Finalize the feature branch through review and squash merge. Then review the
publication record and choose the roughness surrogate before any retrace. A new
city or multi-city campaign should start only after that review and an explicit
run plan.

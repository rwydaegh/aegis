# Production performance and outputs

This guide separates two tracks:

1. The normal production track, which produces scientific walk results as soon
   as possible.
2. The Blender and audit track, which preserves evidence and visual detail for
   one flagship city and selected checks.

The two tracks use the same sealed city inputs and transport settings. The
normal track does not need Blender.

> **Current-contract notice.** See
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md) for the
> active ray, source, material, and transport settings. The timing table below
> preserves earlier Prague measurements, including the 1.6-million-ray
> historical trace. Current production uses 200,000 IID primary rays and
> 4,096 passive angular cells. Fresh anchors are Korenmarkt cold one-seed
> 2:35.73, Korenmarkt warm two-seed 2:27.79 total for 13 points, and Prague
> dry-run 47.96 seconds for 68 points. The fresh Prague cold seed took
> 34:23.05; deterministic all-specular refinement accounted for 1,584.75
> seconds, stochastic transport for 308.66 seconds, and body coupling for
> 119.95 seconds.

## End-to-end stages

```text
sealed city inputs
        |
        +--> scene and material setup --+
        |                                |
        +--> walk and tracer setup ------+--> trace each standpoint
                                         |
                                         +--> body coupling and scalar rows
                                         |
                                         +--> standard spectra (optional by profile)
                                         |
                                         +--> validation and manifest

selected audit city: the same inputs --> evidence and path exporters --> payload --> Blender
```

The city and tracer are prepared once for all replicas of a walk. The current
CDF campaign keeps the same registered standpoints and changes the independent
ray seed. Atlas lookup data are reused when their input hash matches.

The historical timing snapshot used code `f5f394da`. It includes immutable
full-geometry device face proposal reuse from `9111c591`. The report command
changes are recorded in `8db6bef0` and `37b4498d`. Scientific paired campaigns
use the sealed config commit `b985ab58`. Current campaigns seal their own code
and configuration identity.

## Measured and estimated timing

The values below are from the Prague run with ready city inputs. They are not a
promise for a new city.

| Work | Value | Status |
| --- | ---: | --- |
| 68-point standard run | 185.0 s total | measured |
| Standard run output | 2.17 MB total for the historical Prague rooftop-only standard archive: 2.01 MB spectra, 126 KB rows, 31 KB manifest | measured |
| New standard/full spectrum storage | Roughly 2 MB per selected source model, based on the historical rooftop-only measurement. Three selected models are estimated at about 6 MB. The new all-model size is not yet measured | estimated |
| Warm A6000 trace | 1.346 s per point at 1.6 million rays, 4096 cells, 3 bounces | measured |
| Warm A6000 trace rate | about 1.19 Mray/s | measured |
| One 68-point replica, trace only | 100.37 s | measured |
| 24 replicas, trace only | 2404.7 s, or 40.15 min | measured |
| 32 replicas, trace only | 53.6 min | extrapolated from the trace rate |
| 32-replica final checkpoint | about 0.92 GB | extrapolated |
| Old final checkpoint load | 6.35 s | measured |
| Old compressed checkpoint write | 34.42 s | measured |
| Old growing checkpoint rewrite at 24 replicas | about 7.2 min extra | extrapolated, pending an integrated GPU rerun |

The 185 second standard run and the 100.37 second trace-only replica have not
yet been split into identical stage categories. New manifests record
`stage_seconds` for scene and material setup, walk setup, tracer setup, trace
time, body and row work, serialization, spectra writing, validation, and total
time. The CDF ledger records shard append, formal analysis, consolidation, byte
counts, replica count, and shard retirement.

The A6000 hardware gate is reported in the roofline campaign operations guide.
That gate result is not an integrated production timing.

Old paired campaign artifacts have a timing attribution defect. Cache hits repeat
cold deterministic all-specular seconds in their timing rows. Scientific outputs
are unaffected. The final code fixes the attribution, but paired campaign timing
must not be presented as corrected measurements.

## Output profiles

The profile controls what is written after a run. It does not change the
transport model.

| Profile | Always retained | Use |
| --- | --- | --- |
| `minimal` | Run manifest with config and input hashes. Complete scalar location rows. Every model's peak `Sab` and whole-body SAR (`wbSAR`). | Fast screening. It does not allocate a spectrum matrix, and it emits no CDF summaries or restart index. |
| `standard` | Everything in `minimal`, plus one angular spectrum (`rho_{model}`) for each selected source model, the shared `local_grid`, `solid_angle`, and the standpoint index. `rho_rooftop` remains the compatibility key. | Recommended default. It permits reweighting the selected stored source laws and re-coupling their bodies without tracing again. It does not synthesize or reweight an arbitrary new source law. |
| `full` | Standard numerics plus explicit path, evidence, checkpoint, payload, and Blender products. | One flagship city and a small calibration subset. It is a multi-command audit track, not the default output of generic exposure execution. |

`run_exposure` writes the profile-selected products. With `minimal`, that means
the run manifest and scalar rows only. Full audit products are declared and made
by explicit exporters so that a normal walk does not silently create a large
Blender package.

A single generic walk is published atomically after it finishes. If interrupted,
it restarts from the beginning and has no incremental restart claim. A CDF
campaign separately adds shard checkpoint/restart and analysis products. It does
not lose completed replicas.

### Roofline scalar output and checkpoint

The roofline campaign uses the `minimal_results_plus_resumable_seed_shards`
profile. It writes `campaign_identity.json`, `locations.jsonl`, `summary.json`,
`manifest.json`, and `checkpoint/`. Each committed seed has a compact scalar
`.npz` shard and a diagnostics `.json` sidecar. Shards carry per-standpoint
transfer, body metrics, timing, field metadata, and reference arrays. The
checkpoint index records hashes and advances with a cumulative total-body `Sab`
field for the committed prefix and requested convergence looks. Directional
samples, panorama audit assets, and Blender objects are not generated.

Production roofline transport includes at most one specular reflection.
`max_bounces=3` does not add higher specular orders. Higher specular orders are
absent from production output.

## What to retain, remove, and regenerate

Retain each profile's manifest and scalar rows. For standard and full outputs,
also retain the standard spectra, summaries, and figures used in a paper. The
minimal profile emits no CDF summaries or restart index.

Retain full per-replica body fields only when the uncertainty calculation needs
them. At present, the 24-replica checkpoint is 693.4 MB. About 688.0 MB is the
exact float64 per-replica, per-point body `Sab` array:

```text
24 replicas x 68 points x 56,024 body samples
```

That array is required for the current confidence interval for the peak of the
mean body field. A running sum and mean can preserve the final peak, but they
cannot reproduce this seed-resampling interval. Use full fields for flagship
and calibration cities. Do not store them for every screening city unless that
uncertainty is a reported result.

Retain canonical evidence, path payloads, and `.blend` files only for selected
audit cities. Renders are cheap to regenerate when the payload and blend file
are retained. Remove duplicate renders, temporary image panels, and failed
intermediate exports after visual review. Keep their manifest and hashes.

The normal spectrum writer now compresses once after the walk rather than once
per point. The minimal profile does not allocate the spectrum matrices. Standard
and full write one `rho_{model}` spectrum for each selected source model. The
working estimate is roughly 2 MB per model, based on the historical rooftop-only
measurement, so three models would be about 6 MB until a new all-model write is
measured. This does not add ray-tracing or body-coupling work because the models
were already traced and coupled to produce the scalar rows.

## Checkpoint policy

The old campaign format rewrote a growing compressed final file. Its old 24-rep
write overhead is estimated at about 7.2 minutes. The new checkpoint store
writes one atomic compressed shard per replica, keeps exact arrays and hashes,
supports restart after interruption, and consolidates once at the end. It
records append, analysis, consolidation, byte, replica, and retirement data.
Normal shard-mode CDF accumulation is list-backed. It does not materialize or
copy the whole replica history after every replica. Materialization occurs at
formal analysis looks and at final return or consolidation. The legacy monolithic
fallback still materializes each replica. Synthetic uninterrupted, legacy, and
interrupted-resume arrays match exactly, and a structural test forbids
`np.concatenate` in the shard hot path.
The old 7.2 minute figure remains an extrapolation until the integrated GPU
campaign is rerun with the new store.

## Main bottlenecks and safe optimisations

1. **Ray tracing.** This is the largest measured cost. Batch-size testing is
   planned at 100k, 200k, 400k, and 800k rays with identical output checks.
2. **Body coupling.** Measure this before adding larger batches. It may become
   the next limit after tracing is faster.
3. **Checkpoint compression.** Per-replica shards avoid repeated full-file
   rewrites while preserving exact restart data.
4. **City preparation.** Prague fishnet cutting for 13 admitted panoramas took
   798.9 s and produced 167 MB. Acquisition, registration, SAM3, Vistas, depth,
   and fusion were not captured separately, so a cold new-city duration is not
   yet known.
5. **Blender audit.** Prague v4 is 156.7 MB and its compressed payload is
   68.9 MB. The visible-path payload stage took 28.0 s. GPU audit renders took
   about 4.3 s each and Blender peaked at about 2.55 GB. This work is optional
   for normal results.

The performance proposal reuse builds and uploads one immutable full-geometry
device face proposal per estimator. It avoids rebuilding the 600,000-face
proposal for every replica. The old host preparation was 0.856 s per gather for
Korenmarkt and 1.001 s per gather for Prague. The estimated 16-replica savings
are about 178 s for Korenmarkt and 1089 s for Prague. These are proposal-reuse
estimates, not paired campaign timings.

The collision BVH retains the original 617,091 Korenmarkt faces and 664,619
Prague faces. Blender Atlas LOD merging is display-only. Exact transport-mesh
decimation is not low-risk without convergence evidence. Reducing the 8x8
transport Atlas without a convergence study changes semantic and material
sampling and is not a safe speed optimisation.

Atlas lookup reuse has been measured: the median all-trace saving was 0.55%,
and the process-level saving was 2.02%. All 96 compared output hashes were
identical. It is a useful low-risk optimisation, but it will not remove the
main ray-tracing cost.

## Many-city operating recipe

1. Build and seal one city input package. Record all hashes and stage times.
2. Run `standard` for every city and walk. Keep scalar rows and spectra.
3. Use the checkpoint store for campaigns with multiple replicas. Consolidate
   only after the formal stopping or uncertainty analysis.
4. Run `full` for one flagship city and a small calibration subset. Export
   evidence, paths, payloads, and Blender products explicitly.
5. Make figures and paper tables from the standard result package. Link each
   reported number to its manifest, configuration, and input hashes.
6. Delete duplicate renders and temporary exports after review. Keep the
   canonical audit products needed to regenerate the selected figures.

Multi-city readiness is tracked in [MULTICITY_CAMPAIGN_READINESS.md](MULTICITY_CAMPAIGN_READINESS.md).
Only Korenmarkt and Prague are runnable now. Four sites require semantic
rebuilds. Four sites require route or geometry repairs. Times Square is invalid
for the current geometry contract.

## Benchmark protocol

For any performance claim, record the city hash, input hash, frequency, ray
count, cell count, bounce count, GPU model, batch size, replica count, and
profile. Report warm per-point trace time and total wall time separately. Run
the same sealed input with the same output checks for every batch-size test.
Report body coupling and serialization as separate stages once their ledgers
are available. Do not compare a cold new-city preparation run with a warm
walk-only run.

## Honest unknowns and publication decisions

Cold end-to-end time for a new city is unknown because acquisition,
registration, SAM3, Vistas, depth, and fusion have not been split into stage
measurements. The next integrated GPU run should capture those stages and the
new checkpoint ledger.

The current production path fixes the one-reflection specular limit,
finish-only roughness, and area-weighted body mean. The sampled suffix impact
remains unresolved because separate suffix transfer was not persisted. Prague
paired outputs passed their final independent audit. Recovery timing remains
excluded from scientific timing claims.

Do not describe the current performance package as proof that final physics
are publication-ready. It is a reproducible and measured execution path that
separates fast scientific results from optional audit evidence.

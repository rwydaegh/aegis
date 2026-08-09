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
> preserves earlier hybrid measurements, including the 1.6-million-ray
> historical trace. Current production uses the
> `first_material_interaction_v1` contract, 200,000 IID primary rays, and
> 4,096 passive angular cells. The seed-independent device-kernel fix now
> measures 3.14 to 3.24 s for the Korenmarkt 14-point stochastic stage, versus
> roughly 62 s per seed before the fix. CUDA level-2 body coupling is exact to
> \(6.64\mathbin{\times}10^{-16}\) relative error in the verified benchmark and
> measured 46x faster on Duke and 81x faster on the real-point benchmark. These
> are stage measurements, not whole-city promises. Earlier anchors remain
> below as historical records.
> Five first-material-interaction campaigns are complete. They use seeds 7
> through 22, looks 4, 8, 12, and 16, and the same 200,000-ray, 4,096-cell
> baseline. These are measured campaign anchors, not a claim of publication
> finality.
> A historical comparable-city v2 Korenmarkt street-route seed took 2:13.75 for
> 14 points. Nested-face reuse avoided 68,383,253 of 120,750,721 logical
> adaptive-specular candidate evaluations, a 56.63% reduction.

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

The exact performance changes are documented in
[the ranked redesign](PRODUCTION_PERFORMANCE_REDESIGN.md). In particular,
`ab570573` removes seed literals from stochastic device kernels and
`ff9c87da` adds the explicit CUDA body-coupling backend and the opt-in provider
corridor route.

## Measured and estimated timing

The values below are measured with ready city inputs. They are not a promise
for a new city.

| Work | Value | Status |
| --- | ---: | --- |
| First-material-interaction Korenmarkt | 29.79 s for 16 replicas over 10 standpoints | current production measurement |
| First-material-interaction Prague | 69.02 s for 16 replicas over 22 standpoints | current production measurement |
| First-material-interaction Madrid | 40.70 s for 16 replicas over 14 standpoints | current production measurement |
| First-material-interaction Mexico City | 30.92 s for 16 replicas over 11 standpoints | current production measurement |
| First-material-interaction Tokyo Hachiko | 50.11 s for 16 replicas over 16 standpoints | current production measurement |
| Historical hybrid Korenmarkt | 83.37 s for 16 replicas over 10 standpoints | historical sensitivity measurement |
| Historical hybrid Prague | 185.68 s for 16 replicas over 22 standpoints | historical sensitivity measurement |
| Historical hybrid Madrid | 115.75 s for 16 replicas over 14 standpoints | historical sensitivity measurement |
| Historical hybrid Mexico City | 219.52 s for 64 replicas over 11 standpoints | historical sensitivity measurement |
| Historical hybrid Tokyo Hachiko | 325.76 s for 64 replicas over 16 standpoints | historical sensitivity measurement |
| Integrated accumulated estimator work | 61.584 s total over 160 standpoint-replica observations | historical hybrid stage ledger |
| Integrated stochastic, specular, body work | 42.119 s, 13.317 s, 2.041 s | historical hybrid stage ledger |
| 68-point standard run | 185.0 s total | measured |
| Standard run output | 2.17 MB total for the historical Prague rooftop-only standard archive: 2.01 MB spectra, 126 KB rows, 31 KB manifest | measured |
| New standard/full spectrum storage | Roughly 2 MB per selected source model, based on the historical rooftop-only measurement. Three selected models are estimated at about 6 MB. The new all-model size is not yet measured | estimated |
| Warm A6000 trace | 1.346 s per point at 1.6 million rays, 4096 cells, 3 bounces | historical measured anchor |
| Warm A6000 trace rate | about 1.19 Mray/s | measured |
| One 68-point replica, trace only | 100.37 s | measured |
| 24 replicas, trace only | 2404.7 s, or 40.15 min | measured |
| 32 replicas, trace only | 53.6 min | extrapolated from the trace rate |
| 32-replica final checkpoint | about 0.92 GB | extrapolated |
| Old final checkpoint load | 6.35 s | measured |
| Old compressed checkpoint write | 34.42 s | measured |
| Old growing checkpoint rewrite at 24 replicas | about 7.2 min extra | historical extrapolation, pending an integrated GPU rerun |

The authenticated first-material-interaction comparison is sealed in the
gitignored worktree artifacts under
`outputs/roofline_campaign/current_five_city_first_material_interaction/`:
`current_five_city_first_material_interaction.{json,csv,pdf,png}` and
`current_five_city_first_material_interaction_manifest.json`. The manifest is
the companion integrity record for those figures and tables.

- [JSON](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.json)
- [CSV](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.csv)
- [PDF](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.pdf)
- [PNG](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.png)
- [Manifest](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction_manifest.json)

Common-seed topology reports compare the current contract with the historical
hybrid. Central q50 and q90 total-transfer differences are small. The large q10
differences in Mexico and Tokyo are driven by zero-direct points 0, 1, 3 and
13, 14, 15. Madrid's positive shift comes from exact full order-1 support that
the historical adaptive and capped hybrid did not capture. Estimator-stage
ratios are 0.1826 to 0.3154, and stochastic-stage ratios are 0.0283 to 0.0378
across the five cities. These are stage ratios, not whole-wall speedups. The
[authenticated reports](ROOFLINE_CAMPAIGN_RESULTS.md#current-first-material-interaction-campaigns)
link each city report.

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
must not be presented as corrected measurements. The 83.37 s provider-corridor
campaign is a historical hybrid sensitivity run. It is not the current
first-material-interaction baseline.

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

Production roofline transport uses `first_material_interaction_v1`: exact
direct, exact order-1 all-specular, and stochastic first-diffuse next-event
estimation only at the first blocking material vertex. There is no mixed suffix.
The historical `max_bounces=3` hybrid is sensitivity evidence, not a complete
three-bounce model.

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

1. **Ray tracing.** This remains the largest measured whole-run cost in the
   historical Prague breakdown. The current stochastic device kernels no longer
   recompile per seed. Batch-size and ray-budget testing still needs identical
   output checks.
2. **Deterministic specular work.** Commit `7a65fd4e` now applies a
   conservative mirrored-receiver triangle-cone broad phase before the unchanged
   exact Float64 solve. It reduced a Korenmarkt final-level candidate set from
   3,204,960 to 1,610 survivors, with an 8.90x reduction. The full 14-point
   deterministic stage fell from 32.312 to 17.585 s, and a Prague point-zero
   stage fell from 13.764 to 3.756 s. City outputs and the seven compared arrays
   were exact. The 20,000 computational threshold and source chunk of 16 are
   performance controls, not scientific parameters.
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

The persistent transport cache is a separate exact optimisation. In the
comparable Korenmarkt benchmark it reduced wall time from 74.09 to 38.90 s and
estimator time from 39.22 to 4.35 s. The scientific arrays were byte-identical.
These values must not be combined with the historical Prague timing or the
seed-compilation timing without a common stage ledger.

### Current transport performance audit

The certified CUDA Float64 specular broad phase leaves the existing host exact
final kernel unchanged. It uses about 96 MiB of resident memory and produced
byte-identical path arrays with zero lost candidates. On the real full solve,
Mexico fell from 16.596 s to 0.694 s, or 23.9x, and Tokyo fell from 35.862 s to
1.084 s, or 33.1x. An independent Mexico subset measured 6.8x with exact
parity. The earlier CPU broad-phase audit filtered 97.3% of Mexico candidate
work and 98.9% of Tokyo candidate work.

The certified resident minimal CUDA reductions retain the rich and audit path
while reducing ordinary per-ray host transfer from about 11.5 MB to reduced
fields plus about 216 bytes of scalar metadata. Real Korenmarkt point 0 fell
from 0.0925 s to 0.0756 s, or 1.22x. A plane microbenchmark measured 4.2x, but
that microbenchmark result is not a city-level speedup claim. Independent rich
parity checks were exact or within measured roundoff.

The source-conditioned conservative-screen mixed-suffix estimator was rejected
for production. It removed zero scores, but its variance-time gain failed the
promotion gate. It remains experimental evidence only. See
[SOURCE_CONDITIONED_SUFFIX_PILOT.md](SOURCE_CONDITIONED_SUFFIX_PILOT.md).

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
The ten-site cohort remains an intended cohort, not a completed run set. The
current provider-corridor report covers five completed sites, while the
checked-in comparable route remains `registered_span_street_v1`. Do not
describe the intended cohort as ten-city ready.

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
checkpoint ledger. The seed-independent device kernels, CUDA body coupling,
CUDA Float64 specular broad phase, and resident minimal CUDA reductions are now
landed exact or roundoff-bounded changes. Ray and cell budgets and
semantic-stage reductions remain validation work. The source-conditioned
mixed-suffix pilot failed its variance-time gate and remains experimental
evidence only.

The current production path is `first_material_interaction_v1`, with exact
direct and order-1 all-specular terms and stochastic first-diffuse next-event
estimation only at the first blocking material vertex. It has no mixed suffix.
Finish-only roughness and the area-weighted body mean remain active. Prague
paired outputs passed their historical paired-campaign audit. Recovery timing
remains excluded from scientific timing claims. See
[the ranked redesign](PRODUCTION_PERFORMANCE_REDESIGN.md) before treating a
proposed performance change as a production setting.

Do not describe the current performance package as proof that final physics
are publication-ready. It is a reproducible and measured execution path that
separates production results from optional audit evidence. The five-city
first-material-interaction campaigns have 12-to-16 total-transfer changes below
0.1 dB. Mexico points 0, 1, and 3 and Tokyo points 13, 14, and 15 have zero
direct transport, but remain meaningful shadowed points and are not excluded.

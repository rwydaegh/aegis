# Production performance redesign

This page ranks the work that makes a many-city study practical. It separates
landed exact changes from proposed optimisations and from scientific choices
that still require paired convergence evidence. A proposed speedup is not a
production result until its acceptance gates pass.

The current scientific transport contract is
`first_material_interaction_v1`: exact direct, exact order-1 all-specular, and
stochastic first-diffuse next-event estimation only at the first blocking
material vertex. It has no mixed suffix. The historical `max_bounces=3` hybrid
is sensitivity evidence, not a complete three-bounce model.

## What is landed

### Seed-independent device kernels

Commit `ab570573` removes per-seed Python literals from the stochastic DrJit
kernels. SplitMix seed words and Fibonacci rotation coefficients are supplied
as opaque device values, so a new seed reuses the compiled kernel. The CUDA
Korenmarkt check preserved the scientific arrays byte-for-byte. The fresh
stochastic stage took 3.14 to 3.24 s for 14 points, compared with roughly 62 s
per seed before the fix. The latter is a historical cold-kernel symptom, not a
current production timing.

The exact check is stronger than a timing comparison. It compares the sampled
transport outputs, not only scalar summaries. The seed remains part of the
scientific identity, and changing it still changes the random draws.

### CUDA level-2 body coupling

Commit `ff9c87da` adds an explicit CUDA DrJit Float64 implementation for the
level-2 surface-field coupling. It uses fixed 512-direction blocks and records
the backend and reduction algorithm in the provenance seal. The CPU NumPy path
remains available as an explicit backend.

The CUDA result is deterministic and agrees with the reference to a maximum
relative error of \(6.64\times10^{-16}\). The measured body-coupling speedup was
46x on the Duke benchmark and 81x on the real-point benchmark. These are
coupling-stage measurements, not whole-city wall-time claims.

### Persistent deterministic transport reuse

The persistent transport cache is exact for a sealed geometry and material
identity. In the comparable Korenmarkt benchmark it reduced wall time from
74.09 to 38.90 s, a 47.49% reduction. Estimator time fell from 39.22 to
4.35 s. Direct and deterministic-specular work was reused exactly. This result
is separate from the DrJit kernel compilation fix. A fresh machine may still
pay one-time device compilation.

### Exact specular broad phase

Commit `7a65fd4e` adds a conservative mirrored-receiver triangle-cone broad
phase. It leaves the existing Float64 exact kernel unchanged and only removes
impossible candidates before that kernel runs. The broad phase is enabled for
large candidate sets at a computational threshold of 20,000 candidates and
uses source chunks of 16.

The Korenmarkt final-level check reduced 3,204,960 candidates to 1,610
survivors and reported an 8.90x reduction. On the full 14-point adaptive
deterministic stage, time fell from 32.312 to 17.585 s, or 1.837x. A Prague
point-zero check fell from 13.764 to 3.756 s, or 3.665x. Every reported point
and all seven compared arrays were exact. Logical candidate accounting remains
unchanged, so the reduction is a computation reduction rather than a change to
the estimator.

The candidate budget, broad-phase threshold, and source chunk are computational
guards. They are not physical model parameters and do not define additional
specular orders.

The current cold exact-specular audit measured the CPU broad phase filtering
97.3% of candidate work for Mexico City and 98.9% for Tokyo. The certified CUDA
Float64 broad phase leaves the existing host exact final kernel unchanged and
uses about 96 MiB of resident memory. It produced byte-identical path arrays
with zero lost candidates. On the real full solve, Mexico fell from 16.596 s to
0.694 s, or 23.9x, and Tokyo fell from 35.862 s to 1.084 s, or 33.1x. An
independent Mexico subset measured 6.8x with exact parity.

### Resident minimal CUDA reductions

The resident minimal CUDA reduction path is also landed. It retains the rich
and audit path while reducing ordinary per-ray host transfer from about 11.5 MB
to reduced fields plus about 216 bytes of scalar metadata. Real Korenmarkt point
0 fell from 0.0925 s to 0.0756 s, or 1.22x. A plane microbenchmark measured
4.2x, but that microbenchmark result is not a city-level speedup claim.
Independent rich parity checks were exact or within measured roundoff.

Tokyo exposes a useful zero-path boundary case. Standpoint 13 produced no
accepted order-1 path at every adaptive level, but relative error around zero is
undefined. The campaign therefore retains the 2% rule and raises only Tokyo's
computational cap to 320 million, enough to enumerate its 319.046 million full
order-1 support. This proves the zero rather than adopting an absolute epsilon.

### Provider corridor evidence route

`provider_corridor_v1` is an opt-in route contract added in `ff9c87da`. It does
not alter the checked-in `registered_span_street_v1` route or its bytes. The
contract enumerates admitted-camera pairs in a connected provider graph,
registers the provider path, and checks the nearest-camera distance
continuously, including segment endpoints and Voronoi breakpoints. Candidates
over 20 m are refused. The selected corridor maximises endpoint span, then
uses the shorter path and canonical station IDs as tie-breaks.

The 2026-08-07 evidence snapshot reported these selections:

| Site | Span (m) | Registered path (m) | Continuous maximum gap (m) |
| --- | ---: | ---: | ---: |
| Korenmarkt | 49.005 | 49.036 | 10.107 |
| Prague | 103.781 | 120.707 | 16.230 |
| Madrid | 62.437 | 75.894 | 15.448 |
| Mexico City | 52.395 | 59.367 | 15.140 |
| Tokyo Hachiko | 72.160 | 88.313 | 12.334 |

The corridor is evidence-complete for this snapshot. Five provider-corridor
campaigns have now run, but the full ten-city cohort is not ready and the
current campaign statistics are not a claim of full estimator convergence.

### First-material-interaction campaign

The five completed production campaigns use seeds 7 through 22, looks 4, 8, 12,
and 16, 200,000 IID primary rays, and 4,096 output cells. Wall times are 29.79 s
for Korenmarkt, 69.02 s for Prague, 40.70 s for Madrid, 30.92 s for Mexico
City, and 50.11 s for Tokyo Hachiko. The 12-to-16 maximum total-transfer
changes are 0.0000819, 0.0001559, 0.0004083, 0.043625, and 0.019732 dB in the
same city order. All are below 0.1 dB.

Mexico points 0, 1, and 3 and Tokyo points 13, 14, and 15 have zero direct
transport. They remain meaningful shadowed points and are not excluded. Mexico
and Tokyo first-material-interaction timings are not direct comparisons with
their historical 64-replica hybrid timings.

The authenticated comparison files are retained under
`outputs/roofline_campaign/current_five_city_first_material_interaction/`:

- [JSON](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.json)
- [CSV](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.csv)
- [PDF](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.pdf)
- [PNG](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.png)
- [Manifest](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction_manifest.json)

## Ranked next work

### 1. Make transport reuse more selective

The current cache identity is intentionally conservative. Separate static
geometry and path-skeleton products from frequency, source law, material, and
ray-budget products. Reuse the static intersection and deterministic-specular
work when only a source law or body coupling changes. Validate each reuse key
with a byte-level scientific-array comparison and a manifest hash.

This is the highest-value architectural change for frequency, material, and
source-law sweeps. No final speedup is claimed until a paired benchmark shows
that the outputs and invalidation boundaries are correct.

### 2. Measure the stochastic estimator before changing it

The production estimator uses 200,000 IID primary rays and 4,096 passive output
cells. The cells are not 4,096 launch strata. The direct and order-1
all-specular terms are exact. Next-event sampling covers only the first diffuse
interaction at the first blocking material vertex. There is no mixed suffix in
the production estimator.

Run paired sweeps over rays and passive cells, keeping geometry, materials,
seeds, and output checks fixed. Candidate diagnostic points are 25k, 50k,
100k, 200k, and 400k rays, with 512, 1,024, 2,048, and 4,096 cells. These are
study points, not approved defaults. A candidate baseline must pass two
consecutive convergence looks for scalar peaks, whole-body SAR, directional
spectra, and the first-diffuse contribution.

Do not promote 30,000 rays or 512 cells merely because an early scalar check is
close. The paired convergence evidence must be attached to the final city and
frequency contract.

### 3. Keep the source-conditioned suffix pilot experimental

The source-conditioned conservative-screen mixed-suffix pilot removed zero
scores, but its variance-time gain was below the fourfold promotion gate. The
zero-score improvement therefore does not justify production adoption. Keep the
pilot as experimental evidence and do not describe it as pending production.
See [SOURCE_CONDITIONED_SUFFIX_PILOT.md](SOURCE_CONDITIONED_SUFFIX_PILOT.md).

### 4. Reduce semantic preparation after transport is stable

The semantic stage is not the current Korenmarkt transport bottleneck. Measured
14-panorama SAM batches took roughly 22 to 26 minutes. Low-risk reductions are:

- register and gate dense views before running expensive SAM prompts,
- reuse one validated model session across stations,
- process only admitted or uncertainty-triggered views for the production atlas,
- use a lower atlas raster only after exposure-level agreement is measured,
- avoid materialising a full intermediate angular sphere when direct view-to-atlas
  projection gives the same atlas binding.

The session-reuse parity result is exact for the tested scientific arrays. The
other reductions are candidates and need atlas and exposure comparisons. Keep
the full semantic audit for the flagship city.

## Expected Amdahl ranges

The pending rows are planning estimates. Landed rows report measured anchors:

| Change | Evidence status | Planning interpretation |
| --- | --- | --- |
| Seed-independent kernels | landed, exact | removes roughly 14 to 20x of the affected stochastic stage in the observed Korenmarkt case, with a smaller whole-run gain |
| CUDA body coupling | landed, exact | removes the measured body-stage bottleneck, 46x Duke and 81x real-point coupling speedups |
| Persistent deterministic cache | landed, exact | 47.49% wall reduction in the comparable Korenmarkt benchmark |
| CUDA Float64 specular broad phase | landed, exact | Mexico real full solve 16.596 to 0.694 s, Tokyo 35.862 to 1.084 s, byte-identical arrays, zero lost candidates, and about 96 MiB resident memory |
| Resident minimal CUDA reductions | landed, exact or roundoff-bounded | Korenmarkt point 0 0.0925 to 0.0756 s, 1.22x, with rich and audit paths retained |
| Static transport cache split | pending | potentially large for sweeps, frequency, and source-law changes, subject to invalidation proofs |
| Ray or cell reduction | pending science | only claim after paired convergence and equal-output checks |
| Source-conditioned mixed-suffix screen | rejected experimental result | removed zero scores, but failed the variance-time gate. It is not a production candidate |
| Semantic view reduction | pending | likely multi-x for cold city preparation, but not a transport-speed claim |

The measured stage wins should be combined with a stage ledger before making a
whole-city estimate. Do not multiply independent speedup numbers.

## Production versus showcase outputs

The normal production track keeps manifests, hashes, scalar location rows,
selected spectra, and CDF shards. It should not create Blender payloads or full
per-ray evidence by default. The showcase track retains canonical semantic
layers, path payloads, rejected-fragment evidence, panorama overlays, renders,
and a `.blend` package for one flagship city and a small calibration subset.

Both tracks consume the same sealed inputs and transport identity. A showcase
artifact is not a different physics configuration. It is a richer projection
of the same run.

## Decisive validation gates

Before a performance change enters production, require:

1. exact or tolerance-bounded comparison against the current implementation,
2. a deterministic replay with the same seed and sealed input hashes,
3. a paired statistical comparison over independent seeds,
4. a stage ledger that identifies cold compilation, warm execution, body
   coupling, serialization, and cache time separately,
5. a failure test for every cache invalidation boundary,
6. an output-size and retention check for the intended profile.

For a scientific estimator change, add convergence of the reported peak,
whole-body SAR, directional spectrum, and first-diffuse contribution. For a
route change, add the continuous evidence-gap audit and preserve the legacy
route bytes.

## Data retention policy

Keep manifests, configuration and input hashes, scalar rows, spectra used in
the paper, convergence summaries, and the CDF checkpoint shards needed for the
reported uncertainty. Keep full per-replica body fields for the flagship and
calibration cities when seed-resampling uncertainty is reported. Do not store
those large fields for every screening city unless the paper uses that
uncertainty.

Keep canonical panorama evidence, path payloads, and Blender files only for
selected audit cities. Renders and temporary panels can be regenerated from
those products and may be removed after visual review. Never remove the
manifest or hashes that make a removed render reproducible.

## Current boundary

The current first-material-interaction campaign snapshot is:

| City | Standpoints | Replicas | Wall time | 12-to-16 total-transfer change |
| --- | ---: | ---: | ---: | ---: |
| Korenmarkt | 10 | 16 | 29.79 s | 0.0000819 dB |
| Prague | 22 | 16 | 69.02 s | 0.0001559 dB |
| Madrid | 14 | 16 | 40.70 s | 0.0004083 dB |
| Mexico City | 11 | 16 | 30.92 s | 0.043625 dB |
| Tokyo Hachiko | 16 | 16 | 50.11 s | 0.019732 dB |

All five campaigns use seeds 7 through 22, looks 4, 8, 12, and 16. Mexico and
Tokyo are not directly comparable with their historical 64-replica hybrid
timings. Zero-direct shadowed points remain in both city outputs.

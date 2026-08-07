# Roofline exposure campaign operations

## Scientific contract

The campaign is not an eleven-city semantic comparison. It has two named
cohorts whose claims must remain separate:

- The primary semantic-route cohort is Brussels Grand Place, Ghent Korenmarkt,
  Madrid Plaza Mayor, Mexico City Zocalo, Prague Staromestske, and Tokyo
  Hachiko. These sites have admitted panorama-linked routes. Their declared
  semantic material binding is part of the campaign identity.
- The geometric-transfer extension is Krakow Rynek, London Trafalgar Square,
  Milan Piazza del Duomo, and New York Times Square. Its routes must be built by
  the declared street-route workflow, cached, kept inside the site crop, and
  labelled geometry-only. These points are not panorama-co-located.
- Toulouse remains excluded. Do not silently replace one of the final ten with
  it or repair its old acquisition defect inside a production run.

Only Korenmarkt and Prague are runnable now. Brussels, Madrid, Mexico Zocalo,
and Tokyo require semantic rebuilds. Four other sites require route or geometry
repairs. Times Square is invalid under the current geometry contract. See
[MULTICITY_CAMPAIGN_READINESS.md](MULTICITY_CAMPAIGN_READINESS.md) for the
site gates.

The final code is `f5f394da`, after performance proposal reuse in `9111c591`.
Report commits are `8db6bef0` and `37b4498d`. Scientific paired campaigns use
the sealed config commit `b985ab58`.

Every result uses the full declared walk and the fixed body yaw attached to each
standpoint. A grid, a partial pilot walk, uniform-yaw averaging, and an
interpolated camera claim are different estimands and are refused as production
substitutes.

For receiver position $x$, the unobstructed reference transfer is

$$
D_{\mathrm{ref}}(x)=\sum_i \frac{p_i}{r_i(x)^2},
$$

where the arc-length source weights $p_i$ sum to one and visibility is not
applied. The directional measure is the raw next-event field divided by
$D_{\mathrm{ref}}$. Results per unit active antenna density and EIRP use

$$
S_0(x)=\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(x)}{4\pi}.
$$

Physical scenario values are therefore obtained by multiplying by
$\rho_A P_{\mathrm{EIRP}}$. The output records $D_{\mathrm{ref}}$, visible-direct
$D_{\mathrm{vis}}$, and multipath surplus separately. This keeps network scale,
scene transfer, and visibility from being conflated.

## Production bridge and output contract

`semantic_twin.exposure.roofline_campaign` consumes a fully prepared walk,
`NextEventEstimator`, `BodyCoupler`, and sealed source, material, transport,
body, and input provenance. It intentionally does not acquire data or choose a
fallback material model during a run.

For every seed and standpoint it produces non-overlapping direct, one-bounce
specular, diffuse, and total transfers. It couples the first three directional
measures to the body, then sums their per-triangle $S_{\mathrm{ab}}$ fields.
This removes a redundant fourth body solve while preserving linearity. Total
area-weighted mean, absorbed power, and whole-body SAR are reduced from that
summed field. The headline peak is computed after averaging the triangle field
over replicas. It is not the average of per-replica maxima.

Production transport includes at most one specular reflection. A configured
`max_bounces=3` does not add higher specular orders. Higher specular orders are
absent from the production result.

The minimal output is:

- `campaign_identity.json`, containing the hash-sealed scientific identity
- `locations.jsonl`, one CDF-ready ensemble row per standpoint
- `summary.json`, timing and convergence information
- `manifest.json`, hashing every sealed result and checkpoint artifact
- `checkpoint/replicas/*.npz`, compact scalar seed shards
- `checkpoint/replicas/*.json`, exact specular candidate, refinement, and work
  diagnostics
- `checkpoint/cumulative/*.npz`, the running summed body field at requested
  convergence looks and at the current committed prefix

Full directional samples, panorama audit assets, and Blender objects are not in
the minimal payload. They belong to an optional audit/visualization run. This
separation is important because paper CDFs need scalar results and one cumulative
body field, not gigabytes of repeated visual evidence.

Checkpoint storage is bounded by the scalar shards plus at most one full body
field per declared convergence look and one current field. A new replica writes
its scalar shard, diagnostic sidecar, and a new cumulative field before the
index is atomically advanced. Unindexed partial files are ignored. A prior
non-look cumulative field is removed only after the new index is durable.

Each scalar shard carries per-standpoint direct, specular, diffuse, and total
transfers, component body metrics, timings, field metadata, and reference scale
arrays. The sidecar keeps exact specular and cache diagnostics. The final output
contains the campaign identity, `locations.jsonl`, `summary.json`, and a hashed
`manifest.json`. Directional samples and Blender audit products are separate
from this scalar campaign output.

## Performance gates

The resident `DeviceEscapeTracer` and `DeviceSbrKernel` implement diffuse
next-event deposits and a full-support sampled one-reflection mixed suffix on
the device. They return reduced order and angular fields once per batch. Exact
direct paths and the adaptive all-specular order-one term remain host
calculations and are cached across replicas. The sampled CUDA pilots combine
these terms under the same strict acceptance policy as the sampled CPU pilot.
The older `specular_order=0` CUDA configuration remains a direct/diffuse parity
diagnostic.

Before a multi-city launch, run one complete primary walk under host LLVM and
resident CUDA with identical geometry, source law, seeds, ray count, and angular
cells. Compare direct, diffuse, all-specular, sampled mixed-specular, total, and
body results. The sampled estimator already has controlled CPU oracles. Real
CUDA execution and timing on an A6000 remain the hardware gate. Record:

- estimator wall time
- direct shadow-ray time
- stochastic trace time
- all-specular and specular-suffix time
- body-coupling time
- output and checkpoint bytes
- direct and diffuse transfer agreement, plus device diagnostic body metrics

The bridge has separate timing fields. Direct and stochastic trace timing must
come from the estimator itself. If the estimator does not expose them, the
result remains null rather than estimating them from overlapping wall clocks.
Do not launch the main campaign until those fields, the host pilot, and the
sampled CUDA pilot are verified. A device speedup does not make the older
specular-omitted diagnostic a publication total.

The performance decision is order-of-magnitude, not seconds hunting:

1. If resident CUDA is consistent for every declared component and materially
   faster, use the sampled CUDA configuration for publication campaigns.
2. If resident CUDA is neutral or slower, use CPU workers and do not pay for
   idle GPUs.
3. Profile the largest wall-time category before optimizing. Candidate-count
   explosions, shadow-ray batches, and repeated body coupling are higher-value
   targets than JSON or compression micro-optimizations.
4. Preserve exact source and material identity across any optimization. Mesh
   simplification is admissible only when it preserves support boundaries,
   semantic seams, and verified transport within the declared tolerance.

### Current A6000 gate

On commit `809ba738`, the A6000 gate passed 163 tests with zero skipped in
9.97 s. `/usr/bin/time` reported 10.52 s wall time and 657156 KiB maximum RSS.
This is a gate result, not an integrated production speed or RAM measurement.

The Korenmarkt and Prague one-seed CUDA pilots passed independent audits. The
Korenmarkt IID and Fibonacci paired 16-seed campaigns passed full audit with
seeds 7 through 22 and looks 4, 8, 12, and 16. Prague paired outputs cover both
modes, seeds 7 through 22, and 68 points. Both paired audits passed. Each Prague
mode has 49 hash-valid manifest entries, a 68x56024 body array, and no orphan
files. Fibonacci is not adopted.

### Experimental sampled specular suffix

The sampled CPU and CUDA pilots combine a numerically converged adaptive
all-specular order-one term with an unbiased full-support sample of the
source-nearest one-reflection suffix at each eligible diffuse vertex. Korenmarkt
and Prague have one-seed, 200,000-ray sampled CUDA acceptance configurations.

The campaign accepts this mode only when adaptive refinement stops at its stated
relative tolerance and the sealed source and triangle proposals have full
support. Exact completion counters remain zero because neither adaptive
quadrature nor Monte Carlo sampling is exact enumeration. The sampled suffix
standard error is conditional on the traced diffuse vertices. Seed replicas,
not that conditional diagnostic, control total transfer, body, and CDF
uncertainty.

Direct and deterministic all-specular body fields are cached once per route
point across replicas. The sampled mixed suffix is coupled for every replica and
never enters that cache. Preflight seals the proposal hashes, counter dimensions,
sample count, seed offset, and bounded cache capacities.

The old paired artifacts have a timing attribution bug. Cache hits repeat cold
deterministic all-specular seconds. Scientific outputs are unaffected. Final
code fixes the attribution, so paired campaign timing must not be described as
corrected. Recovery resumed `9111c591` from `b985ab58` at seed 16 and is hashed
under `recovery_provenance/`. The real Korenmarkt seed 7 scientific arrays are
bit-exact. Estimator plus body timing sums are 72.2126 s and 65.4395 s under
different timing rules. End-to-end speedup remains unresolved. The final CUDA
gate passed 166 tests. Prague look-16 total paired delta maximum and p90 were
0.17949 dB and 0.00756 dB. All-body values were 2.07801 dB and 0.08054 dB.
Total variance q50/q90 were 1.267/51.19. Diffuse variance q50/q90 were
1.153/3.437. Suffix acceptance was 1664/210918849 for IID and
1750/210901371 for rotated Fibonacci. Suffix impact was not persisted and
remains unresolved. Timing is excluded from these audit conclusions.

The performance proposal reuse builds and uploads one immutable full-geometry
device face proposal per estimator. It avoids repeated 600,000-face proposal
builds and uploads. Old host preparation was 0.856 s per gather for Korenmarkt
and 1.001 s per gather for Prague. Estimated savings over 16 replicas are about
178 s for Korenmarkt and 1089 s for Prague. These are proposal-reuse estimates,
not paired campaign timings.

## Safe campaign staging

`tools/blgpu.sh` must not be used for this campaign. It hardcodes the dirty
primary checkout at `/home/user/aegis` as both its code source and remote layout.
The production code is in `/home/user/aegis-exposure-body-path`, while the
sealed large inputs currently live in the primary tree. A campaign must freeze
an explicit snapshot from both without copying either whole checkout.

Use unique run roots:

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
CODE_ROOT=/home/user/aegis-exposure-body-path
INPUT_ROOT=/home/user/aegis
STAGE_ROOT="/home/user/aegis-roofline-stage-${RUN_ID}"
REMOTE_ROOT="/home/admin/aegis-roofline-${RUN_ID}"
```

Create `STAGE_ROOT` as a new directory. Copy only:

- `src/`, the root `pyproject.toml`, and required theory scripts from
  `CODE_ROOT`
- the semantic-twin package, run configuration, tests, and lock file from
  `CODE_ROOT`, excluding `.git`, virtual environments, caches, `data/`, and
  `outputs/`
- `duke.stl`, `itis_v5.db`, and `phantoms.yaml` from `INPUT_ROOT/data`
- each selected site's 250 m mesh and JSON sidecar
- only the sealed route, source-curve, material-binding, and atlas artifacts
  named by that site's preflight manifest

Do not copy panorama imagery, model weights, Blender files, `.env`, API keys,
SSH keys, or unrelated output trees. Hash every staged file into
`STAGING_MANIFEST.sha256`, then use `rsync --checksum` to a new `REMOTE_ROOT`.
`--delete` is safe only against that new run-specific root.

Install the pinned Python 3.12 environment under `REMOTE_ROOT/.venv`. Set
`AEGIS_DATA_DIR="$REMOTE_ROOT/data"` and run the campaign preflight before CUDA
is initialized. The preflight must verify:

- all input and sidecar hashes
- site, crop, route bounds, point kinds, and fixed route yaw
- the six-site semantic versus four-site geometric cohort label
- source curve, arc-length weights, crop area, and physical scale fields
- semantic material binding where claimed, with no silent wholesale fallback
  to the geometric-only mode. Unobserved surface regions retain their explicit
  geometric prior and report its coverage
- tracer and estimator configuration in the identity
- body mesh, tissue database, body mass, and level 2 surface-field support
- planned seeds, convergence looks, output root, and free disk allowance

Street-route preparation never buys or writes a route. The required exact
Google Routes response must already exist under `data/street_routes` in the
staged tree. Removing `GOOGLE_API_KEY` during route construction makes a cache
miss a preflight refusal instead of a network side effect.

## Remote execution and termination

Use one job directory and log per site. Distinct workers may process distinct
sites, but never write the same checkpoint. Fetch results into a new local root
with `rsync --checksum`.

Before terminating paid hardware, require all of the following:

1. The job exit code is zero and no campaign process remains.
2. `manifest.json` exists and hashes every file it names.
3. Remote and fetched manifest hashes match.
4. A local analysis-only pass validates the checkpoint prefix and regenerates
   the same standpoint summary.
5. A file inventory confirms that no required result lives outside the fetched
   run root.

Use the verified Blue Lobster termination endpoint or provider console only
after those gates. Do not guess a destructive API route. No GPU should remain
alive after its outputs have passed the fetch gates.

## Preparation and preflight entry point

`python -m semantic_twin.cli.roofline_campaign --config CONFIG --dry-run`
builds the complete declared route, uses every route standpoint to construct the
fixed facade-tip curve, binds the requested material mode without changing it,
and constructs the tracer, estimator, declared one-bounce transport, and level 2
body coupler. It writes `preflight.json` and `staged_inputs.json` under the
campaign output directory by default. The latter lists and hashes every runtime
input needed in the coherent staged tree.

The preparation path does not use the old random builder/evaluation split and
does not call the escape-only exposure runner. A root mismatch, missing input,
route/cohort mismatch, wholesale material-mode fallback, incomplete body
orientation, or a specular-policy refusal exits before any replica is traced.
Unobserved atlas or fishnet regions may still use the declared geometric
surface prior. Their coverage and fallback provenance are reported rather than
hidden. Without
`--dry-run`, the same prepared objects and sealed identity pass directly to
`run_roofline_campaign`. There is no second preparation pass in which the source
population could change.

### Measured preflight snapshots

On commit `809ba738`, measured dry-run preflight took 17.83 s for Korenmarkt
with 13 standpoints, 506 source sites, 182.953912 m of source support, and
617091 faces. Prague preflight took 52.19 s with 68 standpoints, 1225 source
sites, 654.604943 m of source support, and 664619 faces.

The collision BVH retains those original 617091 and 664619 support faces.
Blender Atlas LOD merging is display-only. Exact transport-mesh decimation is
not low-risk without convergence evidence.

These are preflight timings only. Korenmarkt paired outputs passed their audit.
Prague paired outputs passed their final independent audit. Do not report paired
campaign timing as corrected because the old artifacts repeat cold deterministic
all-specular seconds on cache hits.

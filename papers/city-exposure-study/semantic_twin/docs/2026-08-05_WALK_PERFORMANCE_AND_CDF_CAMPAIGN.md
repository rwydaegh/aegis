# Walk performance and CDF campaign

Date: 2026-08-05

The final Korenmarkt walk is ready for a sequential Monte Carlo campaign. The
runner freezes the accepted 13-point route, exact 250 m mesh, joint material
atlas, body mesh, source laws, 1.6 million rays, 4,096 angular cells, and three
surface interactions. It changes only the base random seed.

The production campaign is waiting for GPU capacity. The authenticated cloud
account returned an empty location list on 5 August. It also reported zero
running instances. No substitute GPU or provider was used.

## Performance result

A profile used the exact Korenmarkt support mesh, route, atlas, and 4,096-cell
grid on the LLVM Dr.Jit backend. It completed four standpoints before the
profile was stopped. Of 88.0 seconds in the traced row loop, 85.0 seconds were
inside body coupling. Propagation over those four points took 2.92 seconds.

The old row builder called the body engine once for each source law. Each call
computed the body-to-grid incidence once for absorbed power and once again for
arriving power. This repeated the largest calculation six times per standpoint.

The row builder now stacks the three angular spectra and calls
`BodyCoupler.couple_many` once. This method already implements the same AEGIS
level-2 law in 512-cell angular chunks. It avoids a body-triangle by 4,096-cell
allocation and shares the incidence calculation across source laws.

The reproducible benchmark used three stored production-resolution Korenmarkt
spectra at the same standpoint. The spectra came from independent seeds in the
accepted angular study.

| Method | Three source laws | Relative time |
| --- | ---: | ---: |
| Three separate body calls | 9.317 s | 1.00 |
| One batched body call | 1.332 s | 0.143 |

The measured speedup was 7.00 times. Peak resident memory was 3.88 GiB because
the separate path forms the full body-triangle by angular-cell incidence
matrix. The benchmark command is:

```bash
python benchmark_walk_body.py --repeat 1
```

The full timings, input hashes, source hashes, versions, and field errors are in
[the body batching benchmark](../outputs/benchmarks/walk_body_batching.json).

The batched result matches the ordinary level-2 calculation within float64
roundoff. Existing tests compare every returned body field. A new execution
test also proves that the row builder passes the source laws in their declared
order through one batched call.

An end-to-end one-point run with the exact atlas, 200,000 rays, and 4,096 cells
completed in 7.37 seconds on the local CPU. The trace itself took 0.5 seconds.
Peak resident memory was 1.295 GiB, including scene, atlas, and body setup.

## Sequential campaign

The campaign follows the [microenvironment audit and stopping
rule](2026-08-05_MICROENVIRONMENTS_AND_CDF_STOPPING.md).

- One complete 13-point walk is one independent replica.

- Point `i` uses `base_seed + 1000 * i`.

- The 400,000-ray transfer chunks remain implementation chunks.

- Seed means are formed in linear power and then converted to decibels.

- The diagnostic look is at 8 replicas. Formal looks are at 16, 24, and 32.

- Two consecutive formal looks must pass. The earliest stop is 24 replicas.

- The bootstrap resamples whole base-seed walks. It keeps all points and source
  laws in each selected replica together.

- Formal looks use one joint 98.333 percent max-t band. Equal Bonferroni alpha
  spending over the three planned looks gives nominal 95 percent familywise
  coverage after selecting a stopping look.

- Route endpoints and their nearest neighbours are retained.

The production alpha values are exact: familywise alpha is 1/20, each formal
look receives 1/60, and each formal band targets confidence 59/60. Bonferroni
controls selection if each per-look band attains that target. The nonparametric
max-t bootstrap is approximate at 16 to 32 replicas, so the result is a nominal
95 percent familywise statement rather than an exact finite-sample confidence
sequence.

The output states that the CDF is conditional on the fixed 49.2 m route. More
ray seeds reduce tracing error. They do not create new street samples.

One joint bootstrap family contains total susceptibility for all three source
laws, rooftop mean absorbed density, and every rooftop surface absorbed-density
mean. It covers 728,436 statistics in production. A single max-t critical value
applies to that family at each formal look.

The published body peak is the maximum absorbed density of the ensemble-mean
angular spectrum. Level-2 absorbed density is linear in that spectrum. The
runner therefore retains each replica's complete surface field, averages those
fields with the bootstrap walk weights, and computes every weighted peak
exactly.

An ordinary bootstrap of a maximum can fail when two surface elements tie. The
formal interval avoids that problem. It first forms a simultaneous band over
all 56,024 surface means, then projects it to the peak as the maximum lower and
upper face bounds. The mean of the per-replica peaks is larger by construction
and appears only as a Jensen-gap diagnostic.

Direct susceptibility stays outside the confidence family and the stop. An
exact zero remains an atom at zero in linear units. Positive direct estimates
get dB values, while zero values get no logarithmic floor or dB interval.

## Compact output

The runner keeps a single atomic checkpoint. It contains:

- susceptibility and direct susceptibility for each replica and point

- rooftop peak and mean absorbed density for each replica and point

- the complete rooftop level-2 surface field for each replica and point

- trace time for each replica and point

- one running sum of the three angular spectra

It does not keep one 4,096-cell angular spectrum for every seed. It does retain
the body surface fields needed for the nonlinear peak. At the 32-replica cap,
that float64 array contains 23,305,984 values and occupies 177.8 MiB before NPZ
compression. The other checkpoint arrays are small by comparison.

Each checkpoint records the exact deterministic Fibonacci grid and its hash.
Resume requires byte-for-byte equality with the expected grid. The campaign
identity also includes the exact IT'IS SQLite database bytes. If an output
generation carries another identity, the runner moves all its managed files to
a recoverable `quarantine/` directory before it writes a new plan.

Every resume and analysis-only run regenerates all reached formal-look files
from the checkpoint. This closes the crash window between a checkpoint write
and its look analysis. A same-identity dry-run preserves an existing plan. If a
sealed manifest exists, the dry-run verifies every sealed artifact before it
returns.

The exact-input dry-run completed locally:

```bash
python run_cdf_convergence.py --dry-run
```

It verified these frozen hashes:

| Input | SHA-256 |
| --- | --- |
| Support mesh | `bfbdba0657a1dd4b8b819e7e611dbfd4eea919e5c08538078ff1948599957264` |
| Joint atlas NPZ | `c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76` |
| Duke body mesh | `781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b` |
| IT'IS v5 database | `51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f` |
| Frozen standpoint arrays | `d373e65c769017c5309db17c2035adf2178641d421fc5fbbdf92356e424b6f5c` |
| Accepted location rows | `66b4e5c70494dc653a8d99ab33d4551fac99d70029114995ef9523d831e34534` |
| Accepted rooftop spectra | `1186e952d4edc65046e69940a54c1024cb29c1fee6e6ae72acbe95b76f59b90b` |

## Production contract registry

The runner now reads named production pins from one typed registry. The
Korenmarkt entry contains its schedule, thresholds, reference paths and hashes,
run settings, model order, rooftop body law, Duke source, tissue database,
point-kind counts, and random-stream stride. Changing any pinned value rejects
the config or reference before tracing.

`custom` remains available for exploratory routes and carries an explicit
`unpinned custom campaign` status in the scientific config. Any other unknown
name fails. A custom campaign cannot be presented as a production contract.

The GPU sync enumerates every config in the same registry. For each entry it
copies only the exact manifest, location, and spectrum triple, then runs the
remote dry-run to validate all hashes. Korenmarkt keeps the accepted reference
fingerprint listed above.

Hachiko has no registry entry yet. Production requires these inputs first:

- acceptance of the 250 m format-version-3 crop with mesh SHA-256
  `1bccad9bedd7c1764e15d06042b0340530e795396f15f6d3fc40a759f3249e71`

- a complete hybrid SAM3 material product for each admitted camera and a joint
  `joint_atlas_250m_r8` artifact bound to that mesh

- review of the 23-point, 120.199 m route, including the vertical-search-bound
  warning, followed by frozen route arrays and point-kind counts

- a sealed CUDA seed-7 reference at 1.6 million rays and 4,096 cells, with
  frozen manifest, location, spectrum, mesh, atlas, body, tissue, and run hashes

The existing eight-point geometric Hachiko run satisfies none of the material,
route, or resolution requirements. It cannot be promoted to production.

## Archived-data validation

The existing angular study has eight independent full-walk rooftop traces at
the production ray and cell counts. These traces do not include the other two
source laws, so they cannot complete the new campaign. They provide a useful
check of the analysis code.

For the archived rooftop traces at seeds 7 through 14, one joint 95 percent
max-t diagnostic family covered total susceptibility, body mean, and all
rooftop surface means. It contained 728,374 statistics. The total and projected
body-peak results were:

| Quantity | Half-width |
| --- | ---: |
| Per-point p90 | 0.0098 dB |
| Per-point maximum | 0.0105 dB |
| Fixed-route q10 | 0.0038 dB |
| Fixed-route q50 | 0.0083 dB |
| Fixed-route q90 | 0.0055 dB |
| Fixed-route minimum | 0.0058 dB |
| Fixed-route maximum | 0.0084 dB |
| Rooftop body-peak maximum | 0.0164 dB |

These values are below the planned limits. They support the expected campaign
cost and the analysis implementation. They remain a one-law diagnostic.
The [archived rooftop diagnostic](../outputs/cdf_convergence_4096_atlas_v1/existing_rooftop_diagnostic.json)
records every source run identity and file hash.

## Production command

Once the A6000 location list is available, run:

```bash
python run_cdf_convergence.py
```

The command resumes only a verified complete-replica prefix. It writes an
analysis after each formal look and stops as soon as two consecutive formal
looks pass. The final manifest seals the checkpoint, analysis, ensemble rows,
and convergence figures with hashes.

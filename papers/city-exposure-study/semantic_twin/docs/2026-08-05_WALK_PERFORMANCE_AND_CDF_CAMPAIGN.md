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
| Three separate body calls | 16.026 s | 1.00 |
| One batched body call | 1.982 s | 0.124 |

The measured speedup was 8.09 times. Peak resident memory was 3.88 GiB because
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

- Simultaneous 95 percent max-t bands cover the full reported family.

- Route endpoints and their nearest neighbours are retained.

The output states that the CDF is conditional on the fixed 49.2 m route. More
ray seeds reduce tracing error. They do not create new street samples.

The runner also applies the separate 0.15 dB body-peak rule. It bootstraps the
linear mean of the peak absorbed density returned by each full replica. At the
final look, it recomputes the body result from the ensemble-mean angular
spectrum and records the difference between the two central estimators.

The dotted direct-path CDFs and the rooftop mean absorbed-density CDF also get
simultaneous seed bands. They are reported diagnostics. The formal stop uses
total susceptibility for all three source laws and the rooftop body peak.

## Compact output

The runner keeps a single atomic checkpoint. It contains:

- susceptibility and direct susceptibility for each replica and point

- rooftop peak and mean absorbed density for each replica and point

- trace time for each replica and point

- one running sum of the three angular spectra

It does not keep one 4,096-cell spectrum for every seed. The running sum is
enough to compute the final ensemble body result. This keeps the retained
campaign output near a few megabytes instead of duplicating tens of megabytes
of raw spectra.

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
| Frozen standpoint arrays | `d373e65c769017c5309db17c2035adf2178641d421fc5fbbdf92356e424b6f5c` |
| Accepted location rows | `66b4e5c70494dc653a8d99ab33d4551fac99d70029114995ef9523d831e34534` |
| Accepted rooftop spectra | `1186e952d4edc65046e69940a54c1024cb29c1fee6e6ae72acbe95b76f59b90b` |

## Archived-data validation

The existing angular study has eight independent full-walk rooftop traces at
the production ray and cell counts. These traces do not include the other two
source laws, so they cannot complete the new campaign. They provide a useful
check of the analysis code.

For the archived rooftop traces at seeds 7 through 14, the simultaneous 95
percent results at the diagnostic look were:

| Quantity | Half-width |
| --- | ---: |
| Per-point p90 | 0.0079 dB |
| Per-point maximum | 0.0086 dB |
| Fixed-route q10 | 0.0028 dB |
| Fixed-route q50 | 0.0060 dB |
| Fixed-route q90 | 0.0040 dB |
| Fixed-route minimum | 0.0042 dB |
| Fixed-route maximum | 0.0060 dB |
| Rooftop body-peak maximum | 0.0132 dB |

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

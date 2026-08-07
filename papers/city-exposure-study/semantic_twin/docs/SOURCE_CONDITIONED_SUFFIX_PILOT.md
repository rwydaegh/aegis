# Source-conditioned suffix pilot

## Outcome

The source-conditioned suffix estimator was not promoted. It removed observed zero-score replicas, but it did not meet the required fourfold variance-time improvement. Production code and production configuration were not changed. The experimental implementation and tests were removed after the decision. The ignored raw pilot JSON files were preserved for audit.

## Method tested

The production sampled mixed suffix draws a finite reflector face from the existing full-support face proposal and draws a source independently from the normalized discrete roofline source law. Most independent source-face pairs cannot form a finite image path. The pilot tested conditional source selection after the unchanged face draw.

For a diffuse vertex $v$, sampled face $f$, source probabilities $p_s$, and face probability $q_f$, the pilot used the following algorithm:

```text
draw f from the unchanged full-support face proposal q_f
C = empty source set
for every source s with p_s > 0:
    solve the finite image geometry for (s, f, v)
    retain s when the image point lies in f,
        source and vertex satisfy the same-side condition,
        and the diffuse cosine at v is positive
P_C = sum(p_s for s in C)
if C is empty:
    score = 0
else if len(C) <= 4:
    score = sum(p_s * F(s, f, v) / q_f for s in C)
else:
    draw s from p_s / P_C on C
    score = P_C * F(s, f, v) / q_f
```

$F$ contains the unchanged two-leg visibility test, atlas material response, path loss, coherent share, and diffuse lobe. The small-set branch is an exact discrete source sum. The conditional branch is unbiased because

$$
\mathbb{E}_{s \sim p_s/P_C}
\left[P_C F(s,f,v)\right]
=
\sum_{s \in C}p_sF(s,f,v).
$$

The screen had no occlusion approximation. It rejected only impossible finite image geometry and nonpositive diffuse cosine. These are necessary conditions for nonzero contribution, so the screen had no false negatives relative to the unchanged suffix kernel. The face proposal retained every nondegenerate mesh face. The source measure, direct atoms, exact all-specular atoms, source and face counter dimensions, and global ray counter mapping were unchanged.

## Validation before the city pilot

The temporary implementation passed these focused checks:

- An analytic discrete-law test showed that conditional-source expectation equalled the exhaustive weighted source sum.
- Random small-scene tests showed that the conservative screen retained every exact finite image candidate.
- A device exact-small test matched the exhaustive CPU all-source transport result.
- Whole-batch and split-batch device runs produced identical sampled suffix fields.
- The focused suite reported 83 passed and 16 skipped.
- Ruff and `git diff --check` passed.

These checks established the estimator algebra and determinism. They did not establish a performance benefit.

## Pilot identity

The pilot used one problematic standpoint in each current provider-corridor campaign. It used 200,000 rays, three bounce opportunities, a configured batch of 400,000, one sampled face per eligible diffuse vertex, and an exact-source threshold of four. Runs used an NVIDIA RTX A6000. The first record in each 65-record file was treated as compilation warmup. Reported statistics use the remaining 64 records.

| Site | Base config | Config SHA256 | Base campaign identity | Point | Position in local metres | Sources | Measured seeds |
|---|---|---|---|---:|---|---:|---|
| Mexico City | `config/roofline_campaign_mexico_zocalo_provider_corridor_v1_convergence_cuda_iid.json` | `3815b278bc85990b566b357765722a587b9981f6c2837420c8cdefd9060ed556` | `8c3318286546da3905eb3fa21c6ced1efb3733c79647ed6e9dc2d78ec5c7883a` | 0 | `[-28.512929079773077, -19.03926856277755, 2224.9173695324794]` | 164 | 2001 through 2064 |
| Tokyo | `config/roofline_campaign_tokyo_hachiko_provider_corridor_v1_convergence_cuda_iid.json` | `7137f3dc3531ae6789dbc181075ac2402d4567e3b169163f1ad629776259f2e5` | `6af608bf1f457c32c60b652a073afc2c0b7adb3d657a03a5a18f706d86b0c7b4` | 13 | `[-22.486402503794263, -34.94969914448761, 53.10839112056466]` | 400 | 3001 through 3064 |

The campaign identities identify the unchanged base inputs and transport contract. The pilot itself was an unsealed experimental code snapshot and does not claim either production campaign identity.

## Commands used

The transient pilot CLI was removed after the failed gate. These invocations record the exact base configurations, points, seed sets, threshold, and persistent deterministic caches used.

```bash
python -m semantic_twin.cli.source_conditioned_suffix_pilot \
  --config config/roofline_campaign_mexico_zocalo_provider_corridor_v1_convergence_cuda_iid.json \
  --point-index 0 --seeds $(seq 2000 2064) \
  --persistent-transport-cache outputs/persistent_transport_cache/mexico_zocalo_provider_corridor_v1_5fe54025 \
  --output /tmp/mexico_baseline_65.json

python -m semantic_twin.cli.source_conditioned_suffix_pilot \
  --config config/roofline_campaign_mexico_zocalo_provider_corridor_v1_convergence_cuda_iid.json \
  --point-index 0 --seeds $(seq 2000 2064) \
  --conditioned --exact-threshold 4 \
  --persistent-transport-cache outputs/persistent_transport_cache/mexico_zocalo_provider_corridor_v1_5fe54025 \
  --output /tmp/mexico_conditioned_65.json

python -m semantic_twin.cli.source_conditioned_suffix_pilot \
  --config config/roofline_campaign_tokyo_hachiko_provider_corridor_v1_convergence_cuda_iid.json \
  --point-index 13 --seeds $(seq 3000 3064) \
  --persistent-transport-cache outputs/persistent_transport_cache/tokyo_hachiko_provider_corridor_v1_320m_90d701cb \
  --output /tmp/tokyo_baseline_65.json

python -m semantic_twin.cli.source_conditioned_suffix_pilot \
  --config config/roofline_campaign_tokyo_hachiko_provider_corridor_v1_convergence_cuda_iid.json \
  --point-index 13 --seeds $(seq 3000 3064) \
  --conditioned --exact-threshold 4 \
  --persistent-transport-cache outputs/persistent_transport_cache/tokyo_hachiko_provider_corridor_v1_320m_90d701cb \
  --output /tmp/tokyo_conditioned_65.json
```

A supplementary threshold-zero check used seeds 4000 through 4064 for both sites. It sampled one retained source whenever the retained set was nonempty. It was worse than the exact-small threshold-four variant and is not the primary comparison.

## Raw outputs

All paths are relative to `semantic_twin/`.

| File | SHA256 |
|---|---|
| `outputs/experiments/source_conditioned_suffix_pilot/mexico_baseline_65.json` | `84db4a1a4ba49631f5f1da3c022287ba2790aea3a51b9aa8f81e84abd5c7e570` |
| `outputs/experiments/source_conditioned_suffix_pilot/mexico_conditioned_65.json` | `36f7f8979999dc23c8fb165ff4c98818251659bc3ecb815f36d611ec57781aa1` |
| `outputs/experiments/source_conditioned_suffix_pilot/mexico_conditioned0_65.json` | `94ad383eb8af0f2ee1cfa0cb61251066037c5903ab62ef0b26839ce3152b20bd` |
| `outputs/experiments/source_conditioned_suffix_pilot/tokyo_baseline_65.json` | `c280d665b0503d28de06de8fc2d9a2e3993695c048f5c70ac993a7b9c1933aea` |
| `outputs/experiments/source_conditioned_suffix_pilot/tokyo_conditioned_65.json` | `cec5c392ac04d8c8d0aca8b5ec46ee49a9fbb0c616ce39343383bc380143367e` |
| `outputs/experiments/source_conditioned_suffix_pilot/tokyo_conditioned0_65.json` | `acf20f44214a44d5d6f2cedf2c610ac3bf4750403672e17844ccffae7302e60b` |

## Promotion gates and results

The predeclared gates were:

1. No bias against analytic and exhaustive small-scene oracles.
2. At least fourfold improvement in relative variance multiplied by point wall time.
3. At least tenfold reduction in zero-score replicas.
4. No more than twofold increase in total point wall time.

Relative variance is sample variance divided by squared sample mean. This normalization is necessary because the 64-replica baseline and conditioned sample means had not converged to one another.

| Metric | Mexico baseline | Mexico conditioned | Tokyo baseline | Tokyo conditioned |
|---|---:|---:|---:|---:|
| Mean suffix | `2.155543334e-7` | `6.441980514e-7` | `3.084683150e-8` | `2.194720410e-7` |
| Relative variance | `13.38609221` | `11.24366885` | `16.00073858` | `6.928233936` |
| Zero-score fraction | `0.703125` | `0` | `0.515625` | `0` |
| Mean total point wall time, s | `0.06834434` | `0.10492265` | `0.07355858` | `0.14500474` |
| Mean stochastic trace time, s | `0.02856737` | `0.06461606` | `0.02834958` | `0.09912731` |
| Mean accepted endpoint trials | `0.359375` | `5.890625` | `0.65625` | `52.5625` |

The observed total point wall-time ratios were 1.535 for Mexico City and 1.971 for Tokyo. They passed the total point-cost gate. The stochastic trace ratios were 2.262 and 3.497, which shows that the screen itself was not cheap even though fixed point overhead kept the total ratios below two.

The relative variance-time gains, defined as baseline relative variance-time divided by conditioned relative variance-time, were:

- Mexico City: `0.7754951366x`
- Tokyo: `1.171571004x`

Both are below the required `4x`. The source screen therefore failed the decisive promotion gate. The absolute variance-time ratios were still worse because the two 64-replica means had not converged.

The zero-score gate passed in the observed samples, but that result was not enough. Conditioning exposed many more nonzero paths while leaving a heavy-tailed face draw and primary-ray process. Removing source mismatch alone shifted variance rather than eliminating the dominant tail. The threshold-zero supplement confirmed that exact summation over small retained source sets was useful. Threshold zero produced relative variances of 60.622 in Mexico City and 23.945 in Tokyo at essentially the same point cost.

## Next experiment

The next experiment should target the remaining face and primary-ray variability, not add more source-only machinery.

1. Build a conservative joint source-face pilot that conditions the face proposal on finite image feasibility while retaining an explicit full-support mixture. Use exact face summation when the retained set is small and an importance-corrected conditional face draw otherwise.
2. Separately test stratified or randomized low-discrepancy primary launch cells with fixed per-cell allocation. Use the same launch cells in baseline and candidate runs so the face estimator is measured with paired primary paths.
3. Run a four-arm experiment: current baseline, face conditioning only, primary stratification only, and both changes.
4. Use at least 256 paired steady-state replicas at the Mexico and Tokyo points. The 64-replica mean disagreement in this pilot is direct evidence that fewer replicas are not decision-safe for the suffix tail.
5. Reapply the same oracle, no-false-negative, counter-determinism, batch-invariance, zero-score, point-cost, and fourfold relative variance-time gates before any production integration.

This pilot is a negative optimization result. It is retained because it identifies the dominant remaining problem and prevents a superficially attractive zero-score improvement from entering production without a variance-time benefit.

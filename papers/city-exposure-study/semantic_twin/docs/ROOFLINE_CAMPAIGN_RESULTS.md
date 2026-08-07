# Roofline campaign results

## Current optimized campaign

The fresh Korenmarkt `provider_corridor_v1` campaign is the first integrated
current-production anchor. It used 10 registered route standpoints,
16 IID replicas with seeds 7 through 22, 200,000 primary rays, 4,096 passive
output cells, 457 roofline quadrature sources over 157.545 m of support, the
atlas material binding, and CUDA level-2 body coupling.

It completed in 83.37 s wall time on one A6000, or 5.21 s per complete walk
replica. The accumulated stage ledger over 160 standpoint-replica observations
records 61.584 s estimator wall time, 42.119 s stochastic transport, 13.317 s
specular work, 2.041 s body coupling, and 0.058 s direct shadow work. These
stage fields overlap through estimator accounting and must not be added to the
external wall time.

The maximum 12-to-16-replica changes were 0.00795 dB for area-mean absorbed
power, 0.00139 dB for ensemble field peak, and 0.00663 dB for total transfer.
All 42 manifest hashes matched, all 16 replica shards were committed, and all
93 checked numeric arrays were finite. The campaign and checkpoint identities
both equal
`14d6c8467e641cd6ef92c12471f885fa6bc1786a34bfe8d5575cfcadfcc595c6`.

The sealed local result is
`outputs/roofline_campaign/korenmarkt_provider_corridor_v1_convergence_cuda_iid`.
The output profile is `minimal_results_plus_resumable_seed_shards`, so it does
not generate Blender artifacts.

## Current five-city provider-corridor campaign

The current production snapshot contains five completed provider-corridor
campaigns. These are separate single-IID city campaigns with the same sealed
transport contract, not a claim that the intended ten-city cohort is complete.

| City | Standpoints | Replicas | Wall time | Last reported change |
| --- | ---: | ---: | ---: | ---: |
| Korenmarkt | 10 | 16 | 83.37 s | 12 to 16 total transfer: 0.00663 dB |
| Prague | 22 | 16 | 185.68 s | 12 to 16 total transfer: 0.00640 dB |
| Madrid | 14 | 16 | 115.75 s | 12 to 16 total transfer: 0.00628 dB |
| Mexico City | 11 | 64 | 219.52 s | 48 to 64 total transfer: 0.20077 dB, mean `Sab`: 0.17070 |
| Tokyo Hachiko | 16 | 64 | 325.76 s | 48 to 64 total transfer: 0.29756 dB, mean `Sab`: 0.28785 |

Mexico and Tokyo use cached deterministic transport work. Tokyo also has a
separate exact 16-replica proof run that took approximately 753 s wall time.
The route median and p90 summaries are already very stable across the current
looks. The no-direct route points retain rare sampled mixed diffuse-to-specular
suffix heavy tails, so the campaigns are convergence evidence, not a blanket
claim of full estimator convergence or publication finality.

The certified CUDA Float64 specular broad phase leaves the host exact final
kernel unchanged, uses about 96 MiB resident memory, and produced byte-identical
path arrays with zero lost candidates. The real full-solve times fell from
16.596 s to 0.694 s for Mexico City and from 35.862 s to 1.084 s for Tokyo.
The resident minimal CUDA reduction path also passed independent rich parity.
It reduces ordinary per-ray host transfer from about 11.5 MB to reduced fields
plus about 216 bytes of scalar metadata. These are landed implementation
changes, separate from the still-proposed mixed-suffix estimator redesign.

Increasing every city to 256 brute-force replicas would not repair the lower
support of that rare suffix estimator. The next methodological step is to
redesign and validate that estimator, with paired output and tail checks, rather
than treating a larger replica count as a substitute for a better estimator.

The authenticated multicity report tool accepts only completed single-IID
campaigns with matching identity, manifest, replica, route, and numeric-array
checks before producing a comparison. Its sealed current five-city export is
available in the gitignored worktree artifacts:

- [JSON](../outputs/roofline_campaign/current_five_city/current_five_city.json)
- [CSV](../outputs/roofline_campaign/current_five_city/current_five_city.csv)
- [PDF](../outputs/roofline_campaign/current_five_city/current_five_city.pdf)
- [PNG](../outputs/roofline_campaign/current_five_city/current_five_city.png)
- [Manifest](../outputs/roofline_campaign/current_five_city/current_five_city_manifest.json)

## Historical paired campaign status

The final code is `f5f394da`. It includes the immutable full-geometry device
face proposal reuse from `9111c591`. Report code was added in `8db6bef0` and
moved to the command layer in `37b4498d`. Scientific paired campaign configs
are sealed at `b985ab58`.

Korenmarkt and Prague one-seed CUDA pilots passed independent audits. The
Korenmarkt and Prague paired outputs remain historical sampler-comparison
artifacts. Their results are final only for those paired campaigns, not for the
current five-city provider-corridor campaign. Recovery timing is excluded from
scientific timing claims.

The normal result track is scalar and checkpoint based. Blender is optional and
is not part of the numerical result contract.

## Korenmarkt paired campaign

The campaign used the full declared 13-point route, common geometry and source
identity, exact direct directional atoms, the one-reflection transport limit,
and 16 seeds in each sampling mode. Seeds were 7 through 22. Convergence looks
were 4, 8, 12, and 16. The modes were IID and rotated Fibonacci, reported as
Fibonacci in the paper comparison.

At look 16, the route median surplus values were 1.12153 dB for IID and
1.12156 dB for Fibonacci. The whole-body SAR medians, normalized per unit
`rho_A P_EIRP`, were 0.0631297 and 0.0631174 m²/kg. The maximum paired
difference in total raw transfer was 0.0324 dB. The maximum paired difference
for body mean, absorbed power, and whole-body SAR was 0.0343 dB.

The total-transfer p90 standard errors at look 16 were 0.00839 dB for IID and
0.01051 dB for Fibonacci. The look 12 to look 16 p90 movement was 0.00298 dB
for IID and 0.00350 dB for Fibonacci.

Rotated Fibonacci was about 6% slower. Its total variance ratio relative to IID
had median 0.974, q10 0.01395, and q90 15.21. It does not earn production
adoption. Diffuse variance alone had median 0.628, but the total result was
inconsistent, so that result does not justify changing the production sampler.

The sampled suffix acceptance count ranged from 188 to 207 out of about 49.4
million proposals, about 4e-6. Separate suffix transfer was not persisted in
the paired artifacts. Its numerical impact remains unresolved and is not a
published conclusion.

## Prague paired campaign

At look 16, Prague route median surplus was 1.10519 dB for IID and 1.10465 dB
for rotated Fibonacci. The normalized whole-body SAR medians were 0.0121379 and
0.0121384 m²/kg per unit `rho_A P_EIRP`. The total-transfer p90 standard errors
were 0.004442 dB and 0.005237 dB. The total variance-ratio median was 1.26669,
and the body variance-ratio median was 1.21171.

Prague uses the same 16 seeds, looks, and direct exact field contract as
Korenmarkt. Its final audit found 49 hash-valid manifest entries per mode, seeds
7 through 22, 68x56024 body arrays, and no orphan files. The recovery prefix
and the `b985ab58` to `9111c591` continuation both validate.

At look 16, the total paired delta maximum and p90 were 0.17949 dB and 0.00756
dB. The all-body paired delta maximum and p90 were 2.07801 dB and 0.08054 dB.
Total variance-ratio q50 and q90 were 1.267 and 51.19. Diffuse variance-ratio
q50 and q90 were 1.153 and 3.437. Fibonacci is not adopted for production.

Suffix acceptance was 1664 of 210,918,849 proposals for IID and 1750 of
210,901,371 for rotated Fibonacci. Separate suffix transfer was not persisted,
so its numerical impact remains unresolved. These suffix counts and all paired
timing summaries are audit diagnostics, not production adoption evidence.

## Timing and performance limits

Old paired artifacts contain a timing attribution defect. Cache hits repeat cold
deterministic all-specular seconds. Scientific outputs are unaffected. The final
code fixes the attribution, but paired campaign timing is not a corrected
measurement and must not be used as one.

Recovery resumed commit `9111c591` from `b985ab58` at seed 16. The recovery
package is hashed under `recovery_provenance/`. The real Korenmarkt seed 7
scientific arrays are bit-exact between the two code paths. The estimator plus
body timing sums are 72.2126 s and 65.4395 s, a 9.38% difference under different
timing rules. The 148.35 s older `0844eadd` pilot and the 80.86 s one-seed
`9111c591` wall time are not a direct speed comparison. The 16-seed baseline
wall time was about 21:16.11, or 79.76 s per seed. End-to-end speedup remains
unresolved. The final CUDA gate passed 166 tests.

The performance proposal reuse builds and uploads one immutable full-geometry
device face proposal once per estimator. It avoids repeated roughly 600,000-face
proposal builds and uploads. Old host preparation was 0.856 s per gather for
Korenmarkt and 1.001 s per gather for Prague. Estimated savings over 16 replicas
were about 178 s for Korenmarkt and 1089 s for Prague. These are proposal-reuse
estimates, not paired campaign timings.

The collision BVH retains the original 617091 Korenmarkt support faces and
664619 Prague support faces. Blender Atlas LOD merging is display-only. Exact
transport-mesh decimation is not low-risk without convergence evidence.

## Artifacts and figures

The exact artifact root is:

`/home/user/aegis-roofline-results-20260807T015530Z`

The Korenmarkt paired campaign directories are
`korenmarkt_convergence_cuda_iid` and
`korenmarkt_convergence_cuda_rotated_fibonacci`. The paper result files are:

- [PNG figure](/home/user/aegis-roofline-results-20260807T015530Z/korenmarkt_publication_results.png)
- [PDF figure](/home/user/aegis-roofline-results-20260807T015530Z/korenmarkt_publication_results.pdf)
- [CSV table](/home/user/aegis-roofline-results-20260807T015530Z/korenmarkt_publication_results.csv)
- [JSON result](/home/user/aegis-roofline-results-20260807T015530Z/korenmarkt_publication_results.json)
- [LaTeX table](/home/user/aegis-roofline-results-20260807T015530Z/korenmarkt_publication_results.tex)

The Prague paired comparison is [prague_sampling_comparison_final.json](/home/user/aegis-roofline-results-20260807T015530Z/prague_sampling_comparison_final.json).
The two-city paper files are:

- [PNG figure](/home/user/aegis-roofline-results-20260807T015530Z/two_city_publication_results.png)
- [PDF figure](/home/user/aegis-roofline-results-20260807T015530Z/two_city_publication_results.pdf)
- [CSV table](/home/user/aegis-roofline-results-20260807T015530Z/two_city_publication_results.csv)
- [JSON result](/home/user/aegis-roofline-results-20260807T015530Z/two_city_publication_results.json)
- [LaTeX table](/home/user/aegis-roofline-results-20260807T015530Z/two_city_publication_results.tex)

The hashed recovery files are [RECOVERY_PROVENANCE.json](/home/user/aegis-roofline-results-20260807T015530Z/recovery_provenance/RECOVERY_PROVENANCE.json)
and [RECOVERY_PACKAGE_MANIFEST.sha256](/home/user/aegis-roofline-results-20260807T015530Z/recovery_provenance/RECOVERY_PACKAGE_MANIFEST.sha256).

Multi-city readiness remains separate from these results. Five provider-
corridor campaigns are now complete, while the intended ten-site cohort still
requires independent readiness checks for its remaining sites. See
[MULTICITY_CAMPAIGN_READINESS.md](MULTICITY_CAMPAIGN_READINESS.md).

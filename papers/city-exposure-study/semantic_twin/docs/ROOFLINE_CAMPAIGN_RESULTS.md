# Roofline campaign results

## Current first-material-interaction campaigns

The current production contract is `first_material_interaction_v1`. It uses an
exact direct term, an exact order-1 all-specular term, and stochastic
next-event estimation only at the first blocking material vertex. It has no
mixed diffuse-to-specular suffix. The historical `max_bounces=3` hybrid is
sensitivity evidence, not a complete three-bounce model.

Five completed campaigns use seeds 7 through 22, looks 4, 8, 12, and 16,
200,000 IID primary rays, and 4,096 passive output cells. Their wall times are
29.79 s for Korenmarkt, 69.02 s for Prague, 40.70 s for Madrid, 30.92 s for
Mexico City, and 50.11 s for Tokyo Hachiko on one A6000.

The maximum 12-to-16 total-transfer changes are 0.0000819 dB for Korenmarkt,
0.0001559 dB for Prague, 0.0004083 dB for Madrid, 0.043625 dB for Mexico City,
and 0.019732 dB for Tokyo Hachiko. Every value is below 0.1 dB. Mexico and
Tokyo are not directly comparable with their historical 64-replica timings.

Mexico points 0, 1, and 3 and Tokyo points 13, 14, and 15 have zero direct
transport. They are meaningful shadowed points and are not excluded.

The strict-authenticated common-seed topology reports compare the current
contract with the historical hybrid. Total-transfer route q10, q50, and q90
changes (first material interaction minus hybrid, in dB) are Korenmarkt
`-0.00529/-0.00798/-0.00872`, Prague `-0.000741/-0.00507/-0.00693`, Madrid
`+0.0676/+0.1046/+0.0881`, Mexico `-11.109/-0.00174/-0.00209`, and Tokyo
`-2.125/-0.00481/-0.00828`. The large Mexico and Tokyo q10 changes are driven
by the shared zero-direct strata listed above. Madrid's positive shift reflects
exact full order-1 support under the current contract, where the historical
adaptive and capped hybrid did not capture all specular support.

The first-material-interaction estimator stage ratios versus the historical
hybrid are 0.1826, 0.2068, 0.1679, 0.2505, and 0.3154 in the same city order,
which corresponds to 3.17x to 5.95x faster stage execution. Stochastic-stage
ratios are 0.0283, 0.0314, 0.0310, 0.0378, and 0.0340, or about 26.4x to 35.3x
faster. These are stage ratios, not whole-wall speedup claims, especially for
Mexico and Tokyo. Reports:

- [Korenmarkt](../outputs/roofline_campaign/current_topology_sensitivity/korenmarkt.json)
- [Prague](../outputs/roofline_campaign/current_topology_sensitivity/prague.json)
- [Madrid](../outputs/roofline_campaign/current_topology_sensitivity/madrid.json)
- [Mexico](../outputs/roofline_campaign/current_topology_sensitivity/mexico.json)
- [Tokyo](../outputs/roofline_campaign/current_topology_sensitivity/tokyo.json)

The authenticated five-city export is available in the gitignored worktree
artifacts:

- [JSON](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.json)
- [CSV](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.csv)
- [PDF](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.pdf)
- [PNG](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.png)
- [Manifest](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction_manifest.json)

## Current five-city first-material-interaction campaign

The current production snapshot contains five completed first-material-
interaction campaigns. These are separate single-IID city campaigns with the
same sealed transport contract, not a claim that the intended ten-city cohort is
complete.

| City | Standpoints | Replicas | Wall time | Last reported change |
| --- | ---: | ---: | ---: | ---: |
| Korenmarkt | 10 | 16 | 29.79 s | 12 to 16 total transfer: 0.0000819 dB |
| Prague | 22 | 16 | 69.02 s | 12 to 16 total transfer: 0.0001559 dB |
| Madrid | 14 | 16 | 40.70 s | 12 to 16 total transfer: 0.0004083 dB |
| Mexico City | 11 | 16 | 30.92 s | 12 to 16 total transfer: 0.043625 dB |
| Tokyo Hachiko | 16 | 16 | 50.11 s | 12 to 16 total transfer: 0.019732 dB |

These campaigns are convergence evidence, not a blanket claim of publication
finality. The zero-direct points listed above remain in the result set.

The certified CUDA Float64 specular broad phase leaves the host exact final
kernel unchanged, uses about 96 MiB resident memory, and produced byte-identical
path arrays with zero lost candidates. The real full-solve times fell from
16.596 s to 0.694 s for Mexico City and from 35.862 s to 1.084 s for Tokyo.
The resident minimal CUDA reduction path also passed independent rich parity.
It reduces ordinary per-ray host transfer from about 11.5 MB to reduced fields
plus about 216 bytes of scalar metadata. These are landed implementation
changes.

The source-conditioned conservative-screen mixed-suffix pilot removed zero
scores but failed its variance-time gate. It is experimental evidence only and
is not pending production. See
[SOURCE_CONDITIONED_SUFFIX_PILOT.md](SOURCE_CONDITIONED_SUFFIX_PILOT.md).

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
current five-city first-material-interaction campaign. Recovery timing is excluded from
scientific timing claims.

The normal result track is scalar and checkpoint based. Blender is optional and
is not part of the numerical result contract.

## Korenmarkt paired campaign

This is historical hybrid sensitivity evidence. It is not the current
first-material-interaction production model.

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

This is historical hybrid sensitivity evidence. It is not the current
first-material-interaction production model.

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

Multi-city readiness remains separate from these results. Five
first-material-interaction campaigns are now complete, while the intended
ten-site cohort still requires independent readiness checks for its remaining
sites. See
[MULTICITY_CAMPAIGN_READINESS.md](MULTICITY_CAMPAIGN_READINESS.md).

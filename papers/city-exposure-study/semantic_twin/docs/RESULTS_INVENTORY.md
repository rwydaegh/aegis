# Current results inventory

## Status in one paragraph

The current paper result contains ten authenticated 15 GHz route campaigns.
They cover Brussels, Ghent, Krakow, London, Madrid, Mexico City, Milan, Prague,
Tokyo Hachiko, and Toulouse. The campaigns contain 163 fixed-route observation
points and 64 independent runs per point. Each run uses 200,000 primary rays
and 4,096 angular output cells. The result supports a paper about normalized
exposure along selected routes under a declared single-reflection propagation
model. It is not a population sample, deployed-network prediction, or complete
multipath solution.

The earlier five-route, 73-point result remains an authenticated predecessor
and supports paired controls that were not rerun for all ten routes. It is not
the headline paper result.

## Canonical sources

Three sources define the current paper result.

1. [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md) defines the
   active physical and numerical contract.
2. The authenticated ten-route report and manifest under
   `outputs/experiments/ten_city_route_extension64_v1/report/` define the
   production results.
3. The compact figure data in
   `paper/figures/route_results/route_results.json` define the publication
   quantiles, component shares, and convergence summaries.

Older eleven-city, height-band, range-band, three-bounce, masonry, and RCWA
records are not current result sources. Robin confirmed on 2026-08-27 that the
production surface-label stage uses SAM~3 Agent. Historical documents that
describe SAM~3 Agent as planned work are superseded for the manuscript.

The earlier five-route material control, ray and angular-cell sensitivity, and
material-source classification remain supporting diagnostics. Their narrower
scope must be stated whenever they are used.

## Ten-route paper result

The authenticated paper result contains ten `provider_corridor_v1` routes, 163
observation points, and 64 replicas per route. Every campaign uses image-derived
surface properties, route-tangent Duke orientation, 200,000 primary rays per
point and seed, 4,096 first-diffuse cells, and
`first_material_interaction_v1`. The result contains 10,432 point-replica body
fields and 2.0864 billion primary rays.

| Added route | Points | Admitted image stations | Route-median normalized wbSAR |
| --- | ---: | ---: | ---: |
| Brussels Grand-Place | 14 | 8 | 0.03119 |
| London Trafalgar Square | 22 | 14 | 0.01501 |
| Milan Duomo | 23 | 13 | 0.009016 |
| Krakow Rynek | 16 | 11 | 0.02252 |
| Toulouse Capitole | 15 | 9 | 0.03022 |

Across all ten selected routes, the route-median normalized whole-body SAR
ranges from 0.009016 to 0.1291 m² kg⁻¹ per unit
\(\rho_A P_{\mathrm{EIRP}}\), a factor of 14.3. The route-summed direct,
order-1 specular, and first-diffuse absorbed-power shares range from 69.8% to
89.5%, 9.1% to 29.9%, and 0.301% to 5.02%, respectively. The maximum absolute
48-to-64 route-quantile changes are 0.00491 dB for q10, 0.000157 dB for q50,
and 0.0000762 dB for q90.

The compact report and artifact manifest are under
`outputs/experiments/ten_city_route_extension64_v1/report/`. The manifest
SHA-256 is
`595ffe0404517c824a231b565e7528ff799503f3beb74052168b11c7ea3e91b6`.
These selected routes do not support population inference or a city ranking.

## Ten-site geometry-only screening diagnostic

A separate fixed-grid screen covers Ghent/Korenmarkt, Prague, Brussels, Madrid,
Mexico City, Tokyo, London, Milan, Krakow, and Toulouse. It is a diagnostic,
not a production result. Each site uses 16 deterministic points selected from a
6 m walkable-ground grid within 90 m, a fixed north-facing Duke body,
geometric material priors, four seeds (7 through 10), 200,000 IID primary rays,
and 4,096 passive angular cells. The transport is
`first_material_interaction_v1`: exact direct and order-1 specular terms plus
first diffuse transport. The screen contains 640 seed-point fields and 128
million primary rays.

Across sites, the normalized whole-body-SAR q10, q50, and q90 span factors are
2.09, 2.10, and 2.60. Component shares range from 74.2% to 83.4% for direct
transport, 10.5% to 20.0% for order-1 specular transport, and 4.1% to 7.4% for
first diffuse transport. Aggregate observed compute time is 271.515 s, excluding
scene preparation and report generation. All ten site manifests authenticate,
and component and body closures pass. The report manifest SHA-256 is
`7c1d5834b1a672c72d519d603d06f3002eaec20a19b350a1b67ed578eec4061a`.
The report is [ten_city_geometry_screen_v1](../outputs/experiments/ten_city_geometry_screen_v1/report/ten_city_geometry_screen_v1.json).

This screen does not support population, route, or city-ranking inference. It
uses fixed yaw, geometric priors, and the same 16 selected points for the source
curve. The four-seed standard error measures conditional Monte Carlo variation
only. It does not measure grid, material, yaw, or source-design uncertainty.
An initial run was quarantined because its legacy manifest prose incorrectly
described a three-metre grid. The corrected run reproduces the scientific
arrays bit for bit for the eight overlapping completed sites. Only identity and
timing fields changed. The paper production result is the ten-route result.

## Earlier five-route result count

| Site | Standpoints | Route span | Replicas | Wall time on one A6000 |
| --- | ---: | ---: | ---: | ---: |
| Korenmarkt | 10 | 49.04 m | 16 | 29.79 s |
| Prague | 22 | 119.39 m | 16 | 69.02 s |
| Madrid | 14 | 73.47 m | 16 | 40.70 s |
| Mexico City | 11 | 60.79 m | 16 | 30.92 s |
| Tokyo Hachiko | 16 | 87.38 m | 16 | 50.11 s |
| **Total** | **73** | | **80 city-replica runs** | |

The campaigns contain 1,168 standpoint-replica evaluations and 233.6 million
primary stochastic rays. All sites use seeds 7 through 22 and convergence looks
at 4, 8, 12, and 16 replicas. The wall times cover the numerical campaign after
the city scene is ready. They do not include scene acquisition or semantic
reconstruction.

## What the method actually computes

The source support is the observed route-aligned roofline. Areal source density
sets the expected source count. Physical three-dimensional roofline length sets
the conditional source weights. Every reported exposure value is normalized per
unit \(\rho_A P_{\mathrm{EIRP}}\). It is therefore not an absolute value for an
operator deployment.

The production topology is `first_material_interaction_v1`. It contains four
persisted fields:

- `direct`: exact direct source-to-receiver transport
- `all_specular`: exact order-1 all-specular transport
- `first_diffuse`: stochastic next-event transport at the first blocking
  diffuse material vertex
- `total`: the sum of the preceding three fields

A sampled path stops at the first diffuse interaction. The result has no higher
specular order and no diffuse-to-specular suffix. The historical
`max_bounces=3` model is sensitivity evidence only.

The scene uses a 250 m photogrammetric support mesh and an atlas-bound material
surface derived from registered panorama evidence. The original support mesh is
the transport geometry. Any simplified display mesh is visual only. The body
model is Duke with 56,024 surface elements, a mass of 72.4 kg, and fixed
route-tangent yaw. Body coupling reports the replica-mean absorbed power density
field, absorbed power, and whole-body SAR.

## Headline fixed-route results

| Site | Normalized wbSAR q10 | q50 | q90 | Median finite surplus | Zero-direct points |
| --- | ---: | ---: | ---: | ---: | ---: |
| Korenmarkt | 0.057833 | 0.062045 | 0.068672 | 1.108 dB | 0 |
| Prague | 0.012157 | 0.013073 | 0.014594 | 1.061 dB | 0 |
| Madrid | 0.020913 | 0.022381 | 0.023171 | 1.534 dB | 0 |
| Mexico City | 0.000000992 | 0.129062 | 0.295798 | 0.721 dB | 3 |
| Tokyo Hachiko | 0.0000366 | 0.009674 | 0.025200 | 0.828 dB | 3 |

The normalized whole-body SAR unit is m² kg⁻¹ per unit
\(\rho_A P_{\mathrm{EIRP}}\). The route medians differ by a factor of 13.34
between the largest and smallest selected-route median. This is a contrast among
five selected routes. It is not a city ranking.

The median exact order-1 specular shares are 21.60%, 21.17%, 29.40%, 10.58%,
and 16.12% in the table order. The corresponding median first-diffuse shares are
0.953%, 0.322%, 0.322%, 1.598%, and 0.565%. These medians do not describe the
six shadowed points. First diffuse transport carries the complete retained result
at those points.

## Shadowed points and finite surplus

Mexico City standpoints 0, 1, and 3 and Tokyo Hachiko standpoints 13, 14, and
15 have zero direct and zero order-1 all-specular transport. All six remain in
the whole-body SAR result. Multipath surplus is undefined when direct transport
is zero, so the surplus distribution contains 67 finite standpoints rather than
73.

These points explain the long lower tails in Mexico City and Tokyo. They are not
failed runs. However, their first-diffuse estimates have greater relative
uncertainty than the central route results.

## Numerical convergence

| Site | Maximum 12-to-16 change in total transfer | Look-16 p90 standard error |
| --- | ---: | ---: |
| Korenmarkt | 0.0000819 dB | 0.000258 dB |
| Prague | 0.0001559 dB | 0.000244 dB |
| Madrid | 0.0004083 dB | 0.000344 dB |
| Mexico City | 0.043625 dB | 0.1461 dB |
| Tokyo Hachiko | 0.019732 dB | 0.0310 dB |

The retained table above gives the diagnostic available inside the canonical
16-replica result. A separate current-contract extension uses seeds 7 through
70 and nested looks at 16, 24, 32, 48, and 64 replicas. Its first 16 replicas
match the sealed scientific arrays exactly.

| Site | wbSAR q10 change, 48 to 64 | Look-64 bootstrap width | Shadow-point maximum |
| --- | ---: | ---: | ---: |
| Korenmarkt | 0.0000723 dB | 0.000222 dB | -- |
| Prague | 0.0000203 dB | 0.000218 dB | -- |
| Madrid | 0.00000615 dB | 0.000378 dB | -- |
| Mexico City | 0.00344 dB | 0.364 dB | 0.0125 dB |
| Tokyo Hachiko | 0.00491 dB | 0.0538 dB | 0.0104 dB |

Mexico City and Tokyo satisfy all declared 48-to-64 lower-tail criteria. The
paper can therefore state numerical stability for the central fixed-route
statistics and the explicit six-point shadowed stratum through 64 replicas.
This remains conditional on the selected routes and does not cover route or
city sampling.

The authenticated report is under
`outputs/experiments/current_topology_convergence64_v1/report/`.

## Ray-reached evidence coverage

The exact replay classifies retained order-1 specular reflection points and
accepted first-diffuse blocking vertices into seven mutually exclusive atlas
and fallback states. All five source manifests authenticate, all 73 standpoint
records close by category, and the replay matches the sealed transfer, body,
and cumulative fields.

Pooled over the five routes and 16 seeds, panorama-informed interfaces account
for 75.903% of the non-direct body-coupled whole-body SAR contribution. The
fraction is 80.643% for order-1 specular transport and 13.337% for first
diffuse. In the first-diffuse component, 44.345% comes from geometry with no
panorama evidence and 42.314% from evidence refused by the host-material gate.
These are contribution-weighted coverage values, not semantic-accuracy scores.

The authenticated report is under
`outputs/experiments/ray_reached_evidence_coverage_v1/report/`.

## Ray and angular-cell budget sensitivity

The paired budget diagnostic uses Madrid, Mexico City, and Prague with seeds 7
through 22. It compares 25,000, 50,000, and 100,000 rays with the 200,000-ray
baseline at 4,096 cells. It also compares 1,024 and 2,048 cells with the
4,096-cell baseline at 200,000 rays. Exact direct and order-1 specular terms are
invariant, and every baseline replay check passes.

All five cheaper settings exceed the declared 0.1 threshold for the paired
q90 normalized first-diffuse directional difference. The maximum values across
the three sites are 0.877, 0.679, and 0.400 for the three ray settings and
0.491 and 0.455 for the two cell settings. Mexico City shadowed-point
whole-body SAR changes by up to 0.707, 0.564, and 0.217 dB under the ray cuts.
The cell reductions preserve this scalar stratum more closely, but still fail
the directional gate. The production setting therefore remains 200,000 rays
and 4,096 cells.

The authenticated report is under
`outputs/experiments/roofline_budget_sensitivity_v1/`.

## Verification and validation that applies now

The current production artifacts pass four useful checks.

- All five campaign manifests contain 42 files and all 210 file hashes pass.
- The aggregate JSON, CSV, PDF, and PNG match their artifact manifest.
- Across all 1,168 fields, the maximum raw component closure residual is
  \(1.735\times10^{-18}\,\mathrm{m}^{-2}\). Body-field closure is at floating
  point roundoff.
- The CUDA body result agrees with the NumPy reference to a maximum relative
  error of \(6.64\times10^{-16}\) in the verified benchmark.

The strongest controlled propagation validation uses an open-square depth-1
case. It compares deterministic triangle quadrature, an independent forward ray
tracer, and the adjoint first-diffuse estimator. The maximum adjoint-versus-
forward discrepancy is 0.0621 dB for the bounced term and 0.0344 dB for total
transport. This validates the first-diffuse normalization, visibility,
inverse-square loss, and cosine factors in that controlled case.

The complete five-city stack has not been independently validated with the same
atlas materials and exact specular term. The paper must describe the controlled
test as component validation, not full-stack external validation.

## Scene construction time

The repeated numerical walk takes 29.79 to 69.02 s after a city scene is ready.
Cold scene construction is much longer and has an incomplete common timing
ledger. Available 14-panorama examples record 21.3 to 26.6 min for the hybrid
semantic pass and 5.3 to 13.6 min for atlas construction. Acquisition,
registration, depth, and fusion are not all timed separately. Therefore, no
single cold end-to-end time is currently defensible.

## What is not a current result

- The old eleven-city manuscript and its figures use a superseded source law.
- The sibling `current_five_city` package uses the historical hybrid topology.
- The older 16-versus-64 comparison uses the historical hybrid topology. It
  remains non-comparable even though a separate current-contract 64-replica
  extension is now complete.
- Rotated Fibonacci sampling remains a historical diagnostic. IID sampling is
  the current baseline.
- Masonry scattering and RCWA are not in production.
- The source-conditioned mixed-suffix pilot failed its variance-time promotion
  gate and remains experimental.
- Blender files are audit and communication products. They are not part of the
  numerical result path.
- No Gemini experiment contributes to these results. The surface-label stage
  uses SAM~3 Agent, as confirmed by Robin on 2026-08-27.

## Gaps before submission

The ten-route result is sufficient for the fixed-route claim. The following
gaps matter more than additional city count.

1. Use the controlled three-way validation in the main paper and state its
   component-level scope.
2. Keep the fixed-route and finite-replica scope of the Mexico City and Tokyo
   lower-tail result visible in the main results.
3. Record a complete cold-stage timing ledger only if end-to-end speed becomes a
   paper claim.
4. Complete a literature check before making any “for the first time” claim.

Additional cities, frequencies, body models, routes, and higher interaction
orders belong to follow-up work or supplementary sensitivity studies. They are
not required to state the current result correctly.

## Paired material-evidence control

The current-contract material control is complete for Madrid and Mexico City.
Each geometric-fallback campaign has 16 paired seeds and preserves the route,
source curve, geometry, body, sampling budget, and first-material topology. All
42 manifest entries in each campaign pass SHA-256 verification.

The atlas-to-geometric route-quantile changes in normalized whole-body SAR are:

| Site | q10 | q50 | q90 |
| --- | ---: | ---: | ---: |
| Madrid | +0.233 dB | +0.249 dB | +0.269 dB |
| Mexico City | +24.84 dB | -0.158 dB | +0.104 dB |

The Mexico City q10 is not a central material effect. It is set by three
shadowed standpoints where both alternatives are near zero and first-diffuse
transport carries the complete retained result. The direct term is identical
between each pair. In Madrid, the route-median specular component is 1.89 dB
higher and the first-diffuse component is 12.43 dB lower with the atlas, while
the total route median changes by only 0.249 dB.

This is an atlas evidence layer versus geometric fallback control. It changes
both material parameters and the atlas nonblocking state. It is not a
reflectance-only comparison and does not establish material accuracy.

# Current results inventory

## Status in one paragraph

The current reliable result set contains five authenticated 15 GHz campaigns.
They cover Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko. The
campaigns contain 73 fixed-route standpoints and 16 independent replicas per
standpoint. Each replica uses 200,000 primary rays and 4,096 passive angular
output cells. The result set is suitable for a paper about normalized exposure
along selected routes under a declared first-material transport model. It is not
a ten-city cohort, a population sample, a deployed-network prediction, or a
complete multipath solution.

## Canonical sources

Two sources define the current paper result.

1. [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md) defines the
   active physical and numerical contract.
2. The authenticated
   [five-city JSON](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.json)
   and its
   [manifest](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction_manifest.json)
   define every reported number.

Older eleven-city, height-band, range-band, three-bounce, masonry, RCWA, and
agentic-AI records are not current result sources.

## Exact result count

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

The route medians are stable at 16 replicas. The individual lower-tail points
in Mexico City and Tokyo are less stable. The correct paper claim is therefore
that central fixed-route statistics are stable under the retained estimator.
The paper must not claim that every standpoint or the full lower tail has
converged.

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
- The retained 16-versus-64 comparison uses that historical topology. It does
  not validate the current first-material campaign.
- Rotated Fibonacci sampling remains a historical diagnostic. IID sampling is
  the current baseline.
- Masonry scattering and RCWA are not in production.
- The source-conditioned mixed-suffix pilot failed its variance-time promotion
  gate and remains experimental.
- Blender files are audit and communication products. They are not part of the
  numerical result path.
- No Gemini or agentic-AI experiment contributes to these results.

## Gaps before submission

The five-city result is sufficient for a focused paper. It does not need ten
cities to support the fixed-route claim. The following gaps matter more than
additional city count.

1. Quantify evidence coverage on the ray-reached surfaces, not only on the full
   support mesh.
2. Use the controlled three-way validation in the main paper and state its
   component-level scope.
3. Keep the Mexico City and Tokyo tail caveat visible in the main results.
4. Record a complete cold-stage timing ledger only if end-to-end speed becomes a
   paper claim.
5. Complete a literature check before making any “for the first time” claim.

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

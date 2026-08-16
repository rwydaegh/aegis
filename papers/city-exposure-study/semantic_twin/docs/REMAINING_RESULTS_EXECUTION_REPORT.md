# Remaining results execution report

## Status

The sealed 16-replica, five-city `first_material_interaction_v1` result remains
the canonical paper evidence. Its fixed routes, 73 standpoints, seeds 7 through
22, 200,000 IID primary rays, 4,096 passive first-diffuse cells, exact direct
term, exact order-1 specular term, and Duke body coupling have not been
replaced. The three results below are authenticated diagnostic extensions. None
is promoted into the canonical production result. The manuscript supplement
records them as diagnostics.

All listed diagnostic inputs, replay artifacts, and reports are authenticated.
Their manifests bind the route, source measure, mesh, material atlas, body,
seeds, topology, and code/input hashes used by the associated replay.

### Ten-site geometry-only screening

The fixed-grid screen covers Ghent/Korenmarkt, Prague, Brussels, Madrid, Mexico
City, Tokyo, London, Milan, Krakow, and Toulouse. It uses 16 deterministic
points per site from a 6 m walkable-ground grid within 90 m, a fixed
north-facing Duke body, geometric material priors, seeds 7 through 10, 200,000
IID primary rays, and 4,096 passive angular cells. Its
`first_material_interaction_v1` transport keeps exact direct and order-1
specular terms and first diffuse transport. The run contains 640 seed-point
fields and 128 million primary rays.

The normalized whole-body-SAR q10, q50, and q90 site-span factors are 2.09,
2.10, and 2.60. Direct, order-1 specular, and first-diffuse component shares
range from 74.2% to 83.4%,
10.5% to 20.0%, and 4.1% to 7.4%, respectively. Aggregate observed compute
time is 271.515 s, excluding scene preparation and report generation. All ten
site manifests authenticate and component and body closures pass. The report
manifest SHA-256 is
`7c1d5834b1a672c72d519d603d06f3002eaec20a19b350a1b67ed578eec4061a`.

This is not a population sample, route result, or city ranking. It describes
the exact selected grid points only. The fixed yaw and geometric priors limit
transfer. The source curve is conditioned on the same 16 selected points. The
four-seed standard error measures conditional Monte Carlo variation only. No
grid, material, yaw, or source-design uncertainty was estimated.

An initial run was quarantined because legacy manifest prose incorrectly said
that the grid spacing was three metres. The corrected run reproduces the
scientific arrays bit for bit for the eight overlapping completed sites. Only
identity and timing fields changed. This diagnostic does not replace the
canonical five-route production result.

## Completed diagnostic evidence

### Ray-reached semantic evidence coverage

The seven-category audit replay covers all 73 production records. Category
closure and sealed-output parity pass for every record. Of the retained
non-direct body-coupled normalized whole-body-SAR contribution, the pooled
panorama-informed fraction is 0.7590277699014926 and the geometric-fallback
fraction is 0.24097223009850738. The exact-specular panorama-informed fraction
is 0.806433729576005. The first-diffuse panorama-informed fraction is
0.13336718410343135.

This is an evidence-coverage diagnostic. It establishes where retained modeled
interactions obtain their surface state. It does not establish material
accuracy or alter production transport.

### Current-topology 64-replica convergence

Five fresh current-topology campaigns used seeds 7 through 70 with looks at
16, 24, 32, 48, and 64 replicas. Exact non-timing prefix agreement, common
inputs, and component closure pass. The 48-to-64 whole-body-SAR q10 changes
were 6.147e-6 dB for Madrid, 0.00344084 dB for Mexico City, 0.00491459 dB for
Tokyo Hachiko, 7.229e-5 dB for Korenmarkt, and 2.0279e-5 dB for Prague.

The maximum shadow-stratum changes were 0.01248495 dB in Mexico City and
0.0104433 dB in Tokyo Hachiko. The diagnostic therefore indicates stabilized
aggregate central and shadowed estimates under the current topology. Mexico
City retains rare-event first-diffuse behavior: its maximum positive replica
contribution is 5738 times its positive-replica median. The sealed 16-replica
paper result remains canonical because replacing it would add manuscript
complexity without a proportionate interpretive gain.

### Ray and angular-cell budget sensitivity

The paired study covers Madrid, Mexico City, and Prague in 18
arms/campaigns, using common seeds 7 through 22. All baseline replay gates
pass. Exact direct and exact order-1 specular components are invariant across
the budget arms. The reports also retain timing and variance-time diagnostics.

Every cheaper arm fails the directional q90 normalized-L1 criterion of at most
0.1. At 25,000, 50,000, and 100,000 rays, Mexico City shadowed-point maximum
absolute normalized whole-body-SAR changes are 0.707362, 0.563841, and
0.217259 dB, respectively. The 1,024-cell and 2,048-cell arms preserve scalar
and shadowed behavior substantially better, but their directional q90
normalized-L1 values remain 0.491265 and 0.455431. The 200,000-ray,
4,096-cell production budget is therefore retained.

The optional 400,000-ray and 8,192-cell reference arms were not run. The core
paired sweep already decisively rejects the proposed cheaper settings, and
those reference arms were optional in the diagnostic request.

## Rejected approaches

Historical mixed-suffix transport is not comparable with the production
`first_material_interaction_v1` topology and is not used as convergence or
budget evidence. The earlier angular study is likewise not used as current
budget evidence because it does not retain the current closed exact-direct,
exact-order-1, first-diffuse component contract.

## Verification record

The final CPU regression set passed 107 tests and skipped 22 CUDA-only cases.
The CUDA transport regression package passed all 125 tests on an NVIDIA RTX
A6000, with no skips. The focused paper-code suite passed all five tests. Ruff
check and format checks passed for the implementation, tests, claim code, and
claim tests.

The authenticated report-manifest SHA-256 values are:

- ray-reached evidence coverage:
  `4f863148ac809ddc8ff97043a2b409c6e131ba49a1ded7fd0851d4702fe3f14a`
- current-topology 64-replica convergence:
  `2e6f688cd4ca22124eefdcaa577749e1008421e554692c14f342c72494986791`
- paired budget sensitivity:
  `8d4c793064d8b827f4cf8229df382499b30b97edb5f0d247aa7a4834791a1082`

## Remaining limitations

The coverage replay measures evidence provenance rather than material truth.
The 64-replica and budget studies are diagnostics on fixed routes, not city
rankings or population estimates. The budget result supports retaining the
current production setting. It does not prove that 200,000 rays and 4,096
cells are globally optimal for every scene, frequency, body, source model, or
future topology.

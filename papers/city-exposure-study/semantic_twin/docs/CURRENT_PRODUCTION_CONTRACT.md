# Current production contract

This is the concise authority for current numerical production. It supersedes
older statements in the linked status and operations pages where they conflict.
Those pages retain historical evidence and are not rewritten as archives.

## Scene, sources, and materials

- Sources are constructed from the observed route-aligned roofline. The route
  provides the retained roofline geometry and fixed route-tangent yaw.
- The expected active-source count is set by the declared areal density and
  crop area, \(N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}\). This is the
  physical scaling, not the number of numerical source quadrature points.
  Conditional source weights currently use physical three-dimensional edge
  length. Exact edge endpoints, audit sidecars, and hashes are retained.
  Horizontal-projected edge length is available as an explicit sensitivity
  option, not the baseline.
- The atlas material lookup is evaluated on the original support mesh. The
  Atlas display LOD is visual only and is not the transport mesh.
- Finish-only roughness is the production model. Quadrature is a historical
  sensitivity. `masonry_two_level` and RCWA are research-only and are not used
  for production results.

## Transport and coupling

- The active transport contract is `first_material_interaction_v1`. The direct
  term is exact. The order-1 all-specular term is exact. Stochastic next-event
  estimation samples only the first diffuse interaction at the first blocking
  material vertex.
- `first_material_interaction_v1` has no mixed suffix. It does not continue a
  sampled path after the first diffuse event. The historical `max_bounces=3`
  hybrid was sensitivity evidence, not a complete three-bounce production
  model.
- Deterministic specular candidates use the conservative mirrored-receiver
  triangle-cone broad phase when the candidate set reaches 20,000. The
  certified CUDA Float64 broad phase leaves the existing host exact final
  kernel unchanged, uses about 96 MiB resident memory, and produced
  byte-identical path arrays with zero lost candidates. On the real full solve,
  Mexico fell from 16.596 s to 0.694 s, or 23.9x, and Tokyo fell from 35.862 s
  to 1.084 s, or 33.1x. An independent Mexico subset measured 6.8x with exact
  parity. The threshold and chunk are computational controls, not scientific
  parameters.
- The adaptive candidate budget is normally 120 million. Tokyo uses a recorded
  320 million computational cap because one standpoint has zero accepted
  order-1 paths and therefore cannot satisfy a relative convergence test around
  zero. Its 319.046 million candidate support is fully enumerated instead of
  introducing an absolute convergence epsilon. These caps, broad-phase
  thresholds, and chunks are computational guards, not model parameters.
- The production baseline launches 200,000 IID primary rays and uses 4,096 passive
  angular cells. The cells are output directions, not 4,096 independent ray
  launch strata. Rotated Fibonacci launch is retained as a sampling diagnostic,
  not the adopted baseline.
- Body coupling uses the level-2 surface-field path. CUDA runs use the explicit
  DrJit Float64 reduction with fixed 512-direction blocks. The CPU NumPy path
  remains an explicit backend. The CUDA body result is deterministic and agreed
  with the reference to \(6.64\times10^{-16}\) maximum relative error in the
  verified benchmark.

The current 200,000-ray and 4,096-cell values remain the production contract
after a paired three-route budget diagnostic. Every tested cheaper setting
exceeded the declared first-diffuse directional-error gate. Ray reductions also
changed Mexico City shadowed-point whole-body SAR by up to 0.707 dB. The
diagnostic supports retaining the present setting. It does not prove that this
setting is globally optimal for every scene or future topology.

## Comparable-city cohort

Comparable-city v2 is a ten-site intended cohort. All ten sites now have
panorama acquisitions and a completed strict production-contract route:
Korenmarkt, Prague, Brussels, Madrid, Mexico City, Tokyo Hachiko, London
Trafalgar, Milan Duomo, Krakow Rynek, and Toulouse Capitole. Every site's
evidence products independently passed readiness before execution. Times Square is excluded
because its current geometry is invalid. Legacy Korenmarkt and Prague link
runs remain sealed sensitivity artifacts and are byte-compatible. They are
not the v2 cohort definition.

Mask2Former and SAM3 session reuse across stations passed live A6000 parity.
Every scientific panorama array, concept-cache array, prompt gate, and
normalized metadata field was exact between independent and shared-session
runs. One independent panorama took 116.981 seconds. Two shared-session
panoramas took 199.228 seconds total. These are validation anchors, not a
universal per-panorama timing claim.

`provider_corridor_v1` is an opt-in evidence route. It checks connected provider
graph paths continuously against a 20 m nearest-admitted-camera limit. It does
not alter `registered_span_street_v1` or its sealed bytes. The verified
2026-08-07 snapshot selected Korenmarkt 49.005 m, Prague 103.781 m, Madrid
62.437 m, Mexico City 52.395 m, and Tokyo Hachiko 72.160 m endpoint spans. See
[the integration report](PROVIDER_CORRIDOR_INTEGRATION_REPORT.md) for path
lengths, gaps, station IDs, and selection hashes.

## Performance anchors

The historical hybrid campaign used the opt-in Korenmarkt provider corridor,
10 standpoints, 16 IID replicas, 200,000 rays, and 4,096 passive output cells.
It completed in 83.37 s wall time on one A6000, or 5.21 s per complete walk
replica. Accumulated measured work across all 160 standpoint-replica
observations was 61.584 s estimator, including 42.119 s
stochastic transport and 13.317 s deterministic specular work, plus 2.041 s
body coupling. The 12-to-16-replica change was 0.00795 dB maximum for area-mean
absorbed power and 0.00663 dB maximum for total transfer. All 42 sealed file
hashes matched, all 93 numeric arrays were finite, and the campaign identity is
`14d6c8467e641cd6ef92c12471f885fa6bc1786a34bfe8d5575cfcadfcc595c6`.

The seed-independent device-kernel fix in `ab570573` preserved Korenmarkt
scientific arrays byte-for-byte. The fresh stochastic stage took 3.14 to 3.24 s
for 14 points, compared with roughly 62 s per seed before the fix. The old
number was dominated by repeated device-kernel compilation and is retained only
as a historical timing anchor.

The measured CUDA level-2 body coupling speedup was 46x on Duke and 81x on the
real-point benchmark, with the exact Float64 result described above. These are
body-stage measurements, not whole-run wall times.

Earlier anchors remain valid as historical records. The Korenmarkt one-seed
cold run took 2:35.73, a two-seed warm campaign took 2:27.79 total for 13
points, and a Prague dry run took 47.96 s for 68 points. The older Prague full
cold seed took 34:23.05, including 1,584.75 s deterministic all-specular,
308.66 s stochastic transport, and 119.95 s body coupling. These values are
stage-specific and hardware-specific.

The first comparable-city v2 Korenmarkt run used 14 street-route points and
took 2:13.75. Nested-face reuse preserved the logical adaptive refinement while
executing 52,367,468 of 120,750,721 candidate evaluations, avoiding 56.63%.
Exact synthetic full-solve oracles preserve every accepted path array and
transfer. The live run records the work reduction, not an old-versus-new timing
pair.

The persistent deterministic transport cache benchmark reduced Korenmarkt wall
time from 74.09 to 38.90 s, with scientific arrays byte-identical. Estimator
time fell from 39.22 to 4.35 s. This benchmark is separate from the device
kernel compilation timing above.

The completed first-material-interaction campaign snapshot is:

| City | Standpoints | Replicas | Wall time |
| --- | ---: | ---: | ---: |
| Korenmarkt | 10 | 16 | 29.79 s |
| Prague | 22 | 16 | 69.02 s |
| Madrid | 14 | 16 | 40.70 s |
| Mexico City | 11 | 16 | 30.92 s |
| Tokyo Hachiko | 16 | 16 | 50.11 s |

All five campaigns use seeds 7 through 22, looks 4, 8, 12, and 16, 200,000 IID
primary rays, and 4,096 output cells. The 12-to-16 maximum total-transfer
changes are 0.0000819 dB for Korenmarkt, 0.0001559 dB for Prague, 0.0004083 dB
for Madrid, 0.043625 dB for Mexico City, and 0.019732 dB for Tokyo Hachiko.
Every value is below 0.1 dB. Mexico and Tokyo are not directly comparable with
their historical 64-replica timings.

A separate current-contract convergence extension preserves the exact sealed
16-replica scientific prefix and continues every site through seed 70, with
looks at 16, 24, 32, 48, and 64. From 48 to 64 replicas, the whole-body SAR
q10 changes by 0.00344 dB in Mexico and 0.00491 dB in Tokyo. The maximum change
among their three shadowed points is 0.0125 and 0.0104 dB. Both sites pass the
declared lower-tail criteria. This extension is a convergence diagnostic and
does not rewrite the retained 16-replica campaign package.

A separate ten-route extension combines these five convergence campaigns with
fresh 64-replica campaigns for Brussels, London, Milan, Krakow, and Toulouse.
The added routes contain 14, 22, 23, 16, and 15 points, respectively. London
and Milan require 500-million and 400-million exact candidate caps. These caps
only bound deterministic enumeration. All ten routes retain 200,000 rays,
4,096 cells, seeds 7 through 70, and the same transport and body contracts. The
combined report contains 163 route points and authenticates under manifest
SHA-256
`595ffe0404517c824a231b565e7528ff799503f3beb74052168b11c7ea3e91b6`.

Mexico points 0, 1, and 3, and Tokyo points 13, 14, and 15 have zero direct
transport. They remain meaningful shadowed points and are not excluded.

The ray-reached audit replays the retained interactions without changing the
production topology. Panorama-informed interfaces account for 75.903% of the
pooled non-direct body-coupled whole-body SAR contribution. The corresponding
shares are 80.643% for order-1 specular transport and 13.337% for first
diffuse. The remainder uses declared geometric fallback states. These values
measure where the recorded evidence acts, not whether its material labels are
correct.

Strict-authenticated common-seed topology reports compare this contract with
the historical hybrid. Their central q50 and q90 total-transfer differences are
small. The large q10 differences in Mexico and Tokyo are driven by the shared
zero-direct strata. Madrid's positive shift reflects exact full order-1 support
that the historical adaptive and capped hybrid did not capture. The reports
also show estimator-stage ratios of 0.1826 to 0.3154 and stochastic-stage ratios
of 0.0283 to 0.0378 across the five cities. These are stage ratios, not whole
wall-time claims.

See the [topology sensitivity reports](ROOFLINE_CAMPAIGN_RESULTS.md#current-first-material-interaction-campaigns).

The minimal CUDA reduction path is now certified. It retains the rich and audit
path, but reduces the ordinary per-ray host transfer from about 11.5 MB to the
reduced fields plus about 216 bytes of scalar metadata. Real Korenmarkt point 0
fell from 0.0925 s to 0.0756 s, or 1.22x. A plane microbenchmark measured 4.2x,
which must not be interpreted as a 4.2x city speedup. The reduction is exact or
within measured roundoff in the independent rich parity checks.

The source-conditioned conservative-screen mixed-suffix estimator was rejected
for production. It removed zero scores, but its variance-time gain was below
the promotion gate. The pilot remains experimental evidence only. See
[SOURCE_CONDITIONED_SUFFIX_PILOT.md](SOURCE_CONDITIONED_SUFFIX_PILOT.md).

The authenticated five-city outputs are retained under
`outputs/roofline_campaign/current_five_city_first_material_interaction/`:

- [JSON](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.json)
- [CSV](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.csv)
- [PDF](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.pdf)
- [PNG](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction.png)
- [Manifest](../outputs/roofline_campaign/current_five_city_first_material_interaction/current_five_city_first_material_interaction_manifest.json)

## Linked historical records

- [Publication physics decisions](PUBLICATION_PHYSICS_DECISIONS.md)
- [Roofline campaign operations](ROOFLINE_CAMPAIGN_OPERATIONS.md)
- [Multicity campaign readiness](MULTICITY_CAMPAIGN_READINESS.md)
- [Roofline source measure](ROOFLINE_SOURCE_MEASURE.md)
- [Production performance and outputs](PRODUCTION_PERFORMANCE_AND_OUTPUTS.md)

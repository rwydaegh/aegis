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

- The direct term is exact.
- Diffuse and mixed transport use stochastic next-event estimation.
- Production includes an all-specular one-reflection term and a sampled
  mixed-specular suffix. `max_bounces=3` is the transport budget, but it does
  not imply higher specular orders.
- Deterministic specular candidates use the conservative mirrored-receiver
  triangle-cone broad phase when the candidate set reaches 20,000. It uses
  source chunks of 16 and leaves the exact Float64 solve unchanged. The
  threshold and chunk are computational controls, not scientific parameters.
- The production baseline launches 200,000 IID primary rays and uses 4,096 passive
  angular cells. The cells are output directions, not 4,096 independent ray
  launch strata. Rotated Fibonacci launch is retained as a sampling diagnostic,
  not the adopted baseline.
- Body coupling uses the level-2 surface-field path. CUDA runs use the explicit
  DrJit Float64 reduction with fixed 512-direction blocks. The CPU NumPy path
  remains an explicit backend. The CUDA body result is deterministic and agreed
  with the reference to \(6.64\times10^{-16}\) maximum relative error in the
  verified benchmark.

The current 200,000-ray and 4,096-cell values are the production contract, not
the result of a completed budget reduction. Candidate ray and cell reductions
remain diagnostic until paired convergence checks cover scalar peaks, whole-body
SAR, directional spectra, and the mixed-specular suffix.

## Comparable-city cohort

Comparable-city v2 is a ten-site intended cohort. Nine sites currently have
panorama acquisitions: Korenmarkt, Prague, Brussels, Madrid, Mexico City,
Tokyo Hachiko, London Trafalgar, Milan Duomo, and Toulouse Capitole. Krakow is
the tenth and is pending Street View quota. Every site's evidence products
must independently pass readiness before execution. Times Square is excluded
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

The first fully integrated optimized campaign used the opt-in Korenmarkt
provider corridor, 10 standpoints, 16 IID replicas, 200,000 rays, and 4,096
passive output cells. It completed in 83.37 s wall time on one A6000, or 5.21 s
per complete walk replica. Accumulated measured work across all 160
standpoint-replica observations was 61.584 s estimator, including 42.119 s
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

## Linked historical records

- [Publication physics decisions](PUBLICATION_PHYSICS_DECISIONS.md)
- [Roofline campaign operations](ROOFLINE_CAMPAIGN_OPERATIONS.md)
- [Multicity campaign readiness](MULTICITY_CAMPAIGN_READINESS.md)
- [Roofline source measure](ROOFLINE_SOURCE_MEASURE.md)
- [Production performance and outputs](PRODUCTION_PERFORMANCE_AND_OUTPUTS.md)

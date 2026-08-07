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
- The production baseline launches 200,000 IID primary rays and uses 4,096 passive
  angular cells. The cells are output directions, not 4,096 independent ray
  launch strata. Rotated Fibonacci launch is retained as a sampling diagnostic,
  not the adopted baseline.
- Body coupling uses the level-2 surface-field path.

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
runs. One independent panorama took 116.981 seconds; two shared-session
panoramas took 199.228 seconds total. These are validation anchors, not a
universal per-panorama timing claim.

## Performance anchors

The fresh Korenmarkt one-seed cold run took 2:35.73. A two-seed warm campaign
took 2:27.79 total for 13 points. A Prague dry run took 47.96 seconds for 68
points; its full cold seed took 34:23.05. Of that full run, 1,584.75 seconds
were the deterministic all-specular stage, 308.66 seconds were stochastic
transport, and 119.95 seconds were body coupling. These values are
stage-specific anchors, not a promise for every city or hardware configuration.

The first comparable-city v2 Korenmarkt run used 14 street-route points and
took 2:13.75. Nested-face reuse preserved the logical adaptive refinement while
executing 52,367,468 of 120,750,721 candidate evaluations, avoiding 56.63%.
Exact synthetic full-solve oracles preserve every accepted path array and
transfer; the live run records the work reduction, not an old-versus-new timing
pair.

## Linked historical records

- [Publication physics decisions](PUBLICATION_PHYSICS_DECISIONS.md)
- [Roofline campaign operations](ROOFLINE_CAMPAIGN_OPERATIONS.md)
- [Multicity campaign readiness](MULTICITY_CAMPAIGN_READINESS.md)
- [Roofline source measure](ROOFLINE_SOURCE_MEASURE.md)
- [Production performance and outputs](PRODUCTION_PERFORMANCE_AND_OUTPUTS.md)

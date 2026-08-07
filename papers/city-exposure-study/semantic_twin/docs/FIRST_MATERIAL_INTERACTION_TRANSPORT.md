# First-material-interaction transport

`first_material_interaction_v1` is the primary production transport contract.
It defines which path contributions are scientific output and which are absent.

## Contribution contract

For each source and receiver direction, production combines three terms:

- the exact direct term,
- the exact order-1 all-specular term, and
- stochastic next-event estimation at the first blocking material vertex.

The stochastic term samples the first diffuse interaction only. A sampled path
does not continue into a mixed diffuse-to-specular suffix. Higher specular orders
are absent from this contract.

`max_bounces=3` belongs to the historical hybrid sensitivity campaign. It is an
interaction budget used by that experiment, not evidence that production
implements a complete three-bounce model. Candidate budgets, broad-phase
thresholds, and source chunks are computational guards. They are not model
parameters.

## Sampling and outputs

The production roofline baseline uses seeds 7 through 22, convergence looks 4,
8, 12, and 16, 200,000 IID primary rays, and 4,096 passive output cells. Cells
are output directions, not independent launch strata. Rotated Fibonacci launch
remains diagnostic.

Zero-direct points are retained. Mexico points 0, 1, and 3 and Tokyo points 13,
14, and 15 are meaningful shadowed points, not excluded failures.

The five-city campaign outputs are in
`outputs/roofline_campaign/current_five_city_first_material_interaction/`. The
campaign summary is documented in [ROOFLINE_CAMPAIGN_RESULTS.md](ROOFLINE_CAMPAIGN_RESULTS.md).

## Experimental estimator

The source-conditioned suffix pilot removed zero scores but failed its
variance-time gate. It is experimental evidence only and is not pending for
production. See [SOURCE_CONDITIONED_SUFFIX_PILOT.md](SOURCE_CONDITIONED_SUFFIX_PILOT.md).

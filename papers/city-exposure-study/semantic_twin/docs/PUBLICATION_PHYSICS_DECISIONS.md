# Publication physics decisions after the refactor

This document records three physics choices that remain relevant to paper
numbers after the semantic-twin refactor. The current decisions are stated
first. Historical numerical evidence is retained where it remains useful.

> **Current-contract notice.** For current production, use
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md). The
> historical next-event and quadrature statements below are superseded:
> production now uses stochastic next-event diffuse and mixed transport, an
> exact direct term, one-reflection all-specular transport plus a sampled
> mixed-specular suffix, and finish-only roughness. The numerical records
> below remain historical sensitivity evidence.

## Area-weighted body mean

**Decision.** Report the absorbed-density body mean as `p_abs / body.total_area`.
Both scalar and batched couplers use this definition. Checkpoint identity binds
the exact float64 triangle areas. Legacy monolithic checkpoints retain full
`Sab`, so the weighted mean can be recomputed without retracing.

Independent verification passed 247 tests, skipped 4, marked 10 as expected
failures, and deselected 1.

The retained Prague correction across the exact 24-replica data has a median of
`+3.7896%` (`+0.16154 dB`) across all rooftop values. Ensemble point means have
a median of `+3.7868%` (`+0.16142 dB`). The route range is `+0.06350 dB` to
`+0.25034 dB`. In the final 68-row Prague data, medians are rooftop `+3.782%`,
street-small-cell `+3.880%`, and isotropic `-0.211%`. In the final 13-point
Korenmarkt data, medians are rooftop `+4.811%`, street-small-cell `+5.034%`,
and isotropic `-1.057%`. Peak `Sab`, `p_abs`, and `wbSAR` are unchanged.

A full corrected analysis of the retained 24-replica Prague checkpoint completed
CPU-only in 1834.722 seconds (30.58 minutes). It returned `stopped=true`,
`stop_at_replicas=24`, and `cap_reached=false`. Weighting therefore changes the
means but not formal stopping. The run used an experimental bootstrap batch of
64 and wrote no output.

## Next-event estimator

**Decision.** Production uses stochastic next-event estimation for diffuse and
mixed transport, an exact direct term, and a separate one-reflection specular
path. The all-specular contribution is solved adaptively and the mixed-specular
suffix is sampled. These components are non-overlapping in the production
campaign output.

Earlier Prague escape-only manifests and the diagnostic-only next-event ruling
predate the deterministic and sampled specular implementation. They remain
historical artifacts and are not the current production estimator.

## Facade roughness

**Decision.** Production uses finish-only roughness. Quadrature is retained as
a historical sensitivity. The `masonry_two_level` and RCWA paths are research
models and are not used for production results.

At 15 GHz and normal facade incidence, the historical quadrature default gives
a specular share of `0.59053`, while the unit-scatter interpretation gives
`0.0214631`. This is sensitivity evidence, not the active material rule. True
directional treatment would require discrete diffraction orders.

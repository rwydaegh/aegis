# Publication physics decisions after the refactor

This document records the three physics choices that remain relevant to paper
numbers after the semantic-twin refactor. The decisions and verification below
are current on 2026-08-06.

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

**Decision.** Treat next-event estimation as diagnostic-only for the paper.
The current connection credits only the diffuse share. There is no deterministic
image-source or specular connection solver. Strict expected-failure tests expose
the smooth and partially rough reciprocal gap.

The final Prague manifest uses the escape estimator with `next_event` set to
null. The Prague headline and CDF therefore are not contaminated by next-event
results. Exclude absolute next-event totals and escape-gap claims until a real
specular solver and smooth/rough reciprocal tests exist. Do not redistribute the
specular share as Lambertian diffuse power.

## Facade roughness

**Decision.** Keep the production default quadrature as the current sensitivity
model. It combines finish roughness with the periodic joint step and ignores
`unit_scatter_mm`. The `masonry_two_level` path reads unit scatter but still
collapses the periodic grid to a Gaussian and includes the default brick
geometry. Prague uses the quadrature path.

At 15 GHz and normal facade incidence, the production default gives a specular
share of `0.59053`, while the unit-scatter interpretation gives `0.0214631`.
Do not switch silently. The current result is a legacy sensitivity result, and
an explicit surrogate decision is required before any retrace.
True directional treatment requires discrete diffraction orders.

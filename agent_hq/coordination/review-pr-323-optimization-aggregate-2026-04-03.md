# Aggregate review: PR #323 optimization

Date: 2026-04-03
Reviewer: Codex

## Sources aggregated

Reviewed and reconciled:
- `review-pr-323-optimization.md`
- `review-pr-323-optimization-conclusions.md`
- `review-pr-323-optimization-conclusions-2026-04-03.md`
- `review-pr-323-optimization-gh-cli.md`

Also verified against:
- current `master`
- PR `#323` merge commit `c8f42397b078eb24e7984ebedff1a44d5644cff2`

## Bottom line

The earlier notes were mixing two different things:
- bugs that shipped in PR `#323` at merge time
- bugs that are still present on current `master`

After re-checking the code paths, several of the worst PR `#323` regressions were fixed by later follow-up PRs. But the optimization feature area is still not fully trustworthy today.

## Confirmed historical bugs in PR `#323` that were fixed later

These issues are real, but they describe the merge commit, not the current tree.

### 1. `tilt_power` was broken on compute-to-optimize handoff

Confirmed at merge commit:
- optimize route read cached dosimetry from `cache`
- compute route stored it on `app.config`
- optimize route also expected `last_result._paths`

Current status:
- fixed later

### 2. placement mode was impossible to start from the browser

Confirmed at merge commit:
- placement rejected requests unless `evaluate_fn` existed in request JSON
- browser clients cannot send a Python callable

Current status:
- fixed later

### 3. MIMO optimization was broken at merge time

Confirmed at merge commit:
- backend fell back to `scene.G_tilde`
- the scene did not own `G_tilde`
- body channel lived per user

Current status:
- fixed later

### 4. cancellation was cross-user unsafe

Confirmed at merge commit:
- `_get_session_id()` returned literal `"default"` when no session id existed

Current status:
- fixed later with per-session UUID storage

### 5. `tilt_power` omitted Fresnel transmission `T0`

Confirmed at merge commit.

Current status:
- fixed later

### 6. optimization UI could stay stuck in `running`

Confirmed at merge commit:
- no `finally` cleanup in frontend optimization hook

Current status:
- fixed later

## Confirmed current issues on `master`

These are the issues that still hold after re-checking the current code.

### 1. High: placement can silently stop before exploring the full grid

The frontend still defaults to `max_iters = 50`, while the placement UI still allows `grid_size = 9`, which implies `81` candidates.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/components/panels/OptimizePanel.tsx`
- `src/aegis/optim/loop.py`

Validation:
- Reproduced with `PYTHONPATH=src python3`
- a `9x9` placement run produced `51` streamed events and ended with `{"reason": "max_iters", "iter": 50}`

Impact:
- large searches do not complete
- the user can believe the full search finished when it did not

### 2. High: placement optimization still races with the normal dosimetry loop

During placement optimization, every streamed iteration writes a new `antennaPos` into the simulation store. The normal dosimetry hook still reacts to `antennaPos` changes and schedules ordinary compute requests.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/hooks/useDosimetry.ts`

Why this is confirmed:
- placement updates `useSimulationStore.setAntennaPos(...)`
- `useDosimetry` retriggers on `sim.antennaPos`
- there is still no guard for "optimization is running"

Impact:
- overlapping RT and dosimetry work during placement
- unstable or misleading UI updates
- unnecessary backend load

### 3. High: placement still does not honor the full active simulation model

This was partially improved, but not fully fixed.

The frontend now sends much more viewer state, but the backend placement evaluator still ignores a large part of the RT configuration and always goes through its own DiffeRT-style placement path.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`

Confirmed gaps:
- `_parse_rt_config()` only uses:
  - `max_depth`
  - `method`
  - `rays_per_source`
  - `chunk_size`
  - `reflection_loss_per_order`
- it ignores:
  - `max_paths_per_source`
  - `los`
  - `specular_reflection`
  - `diffuse_reflection`
  - `refraction`
  - `diffraction`
  - `edge_diffraction`
  - `diffraction_lit_region`
  - `synthetic_array`
  - `seed`
- placement also does not branch on the active frontend path source

Impact:
- placement can optimize a different propagation model than the one the user is currently viewing

### 4. High: `tilt_power` still optimizes around a synthetic default boresight

The frontend still does not send a real `antenna_direction`, and the backend still falls back to `[0, 0, -1]`.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/optim/tilt_power.py`

Impact:
- tilt optimization is only correct when that fallback happens to match the real scene geometry
- in general scenes, it can search along the wrong tilt axis

### 5. High: MIMO peak optimization is still not integrated into real MIMO state

The current MIMO optimization path still is not wired into the actual MIMO UX/state model.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`
- `aegis-web/src/hooks/useActiveSimulation.ts`
- `aegis-web/src/components/scene/SceneRoot.tsx`
- `aegis-web/src/stores/mimo.ts`

Confirmed problems:
- the frontend does not send `user_id`
- backend therefore picks the first cached user with `G_tilde`, not necessarily the focused user
- the frontend does not send `x_init_real/x_init_imag`, so optimization does not start from the current precoder state
- streamed optimized weights are never written into `useMIMOStore.setPrecoderWeights(...)`
- streamed SAB is written into the single-user simulation store, but MIMO rendering reads `user.sabArray` from `useMIMOStore`

Impact:
- the optimizer may target the wrong user
- it may optimize from the wrong initial precoder
- live MIMO optimization feedback is not reliably reflected in the actual MIMO scene
- optimized precoder state is not retained for later MIMO recomputes

### 6. Medium: `signal_threshold` is still dead API

The request pipeline still accepts `signal_threshold`, and the optimizer still stores it, but the actual optimization step never uses it.

Relevant code:
- `src/aegis/optim/mimo_peak.py`

Validation:
- Reproduced with `PYTHONPATH=src python3`
- runs with `signal_threshold=0.0` and `signal_threshold=10.0` produced identical results

Impact:
- there is no real QoS or service-floor constraint in MIMO optimization

## Superseded earlier conclusions

After re-checking current code, these earlier concerns should no longer be treated as live defects on `master`:

- placement final `best` result not applied
- placement using the wrong pole-height convention
- placement failing because `dosimetry_mode` collided with `mode="placement"`

Those paths have since been repaired.

## Final assessment

PR `#323` shipped with major integration breakage, and later PRs fixed a lot of the obvious blockers.

Current `master` is better than the earlier notes implied, but the feature still has real live issues:
- placement search can truncate
- placement fights the normal compute loop
- placement still does not honor the full active RT model
- tilt/power still lacks real antenna-direction geometry
- MIMO optimization is still not wired into focused-user and persistent MIMO state
- `signal_threshold` is still unenforced

So the current state is:
- no longer catastrophically broken the way PR `#323` was at merge time
- still not reliable enough to trust optimization results as faithful to the active viewer scenario

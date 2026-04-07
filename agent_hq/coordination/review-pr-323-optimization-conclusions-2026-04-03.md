# Conclusions: PR #323 optimization review

Date: 2026-04-03
Reviewer: Codex

## Scope

Reviewed the optimization feature bucket introduced by PR `#323` (`Add differentiable optimization to viewer`), with emphasis on:
- placement optimization
- tilt/power optimization
- MIMO peak optimization
- SSE frontend/backend integration

This note captures the final conclusions from the current code review. Some earlier PR `#323` regressions were already fixed in later follow-up PRs.

## Conclusions

### 1. High: placement mode does not reliably apply the final best result

The frontend exits as soon as it receives an event with `done: true`, but placement mode only attaches the final `best` payload on that terminal event.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/optim/placement.py`

Impact:
- The UI can stop on the last streamed candidate rather than the actual optimum.
- The final antenna position and heatmap may not match the reported best solution.

### 2. High: placement optimization races with the normal dosimetry compute loop

During placement optimization, every streamed iteration writes a new `antennaPos` into the simulation store. The normal `useDosimetry` hook observes that change and schedules an ordinary compute.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/hooks/useDosimetry.ts`

Impact:
- Optimization can trigger overlapping RT and dosimetry requests.
- This creates unnecessary backend load and unstable UI state during the search.

### 3. High: placement mode does not optimize the same scenario the user is viewing

The optimization request only includes grid parameters and search center, while the normal compute path includes body pose, frequency, skin model, mode/corrections, scene selection, and RT configuration.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/hooks/useDosimetry.ts`
- `src/aegis/viewer/routes/optimize.py`

Impact:
- Placement can be optimized against backend defaults instead of the live viewer state.
- The recommended position can therefore be wrong for rotated bodies, non-default frequency/tissue, or custom RT settings.

### 4. High: tilt/power mode optimizes around a synthetic default boresight

The frontend does not send a real `antenna_direction`. The backend falls back to `[0, 0, -1]`.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/optim/tilt_power.py`

Impact:
- Tilt optimization is only correct when that fallback direction happens to match the actual scene geometry.
- In general scenes, the optimizer can search along the wrong tilt axis and return misleading settings.

### 5. High: MIMO peak optimization is not integrated into persistent MIMO state

The optimizer streams optimized `x_real/x_imag`, but the frontend hook never writes them into the MIMO store. It also writes streamed SAB into the single-user simulation store, while MIMO views read from the focused user state.

Relevant code:
- `src/aegis/optim/mimo_peak.py`
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/hooks/useActiveSimulation.ts`
- `aegis-web/src/stores/mimo.ts`
- `aegis-web/src/hooks/useMIMODosimetry.ts`

Impact:
- Live MIMO optimization feedback is not reliably shown through the normal MIMO rendering path.
- The optimized precoder is not retained, so later MIMO recomputes fall back to the old precoder pipeline.

### 6. Medium: `signal_threshold` is dead API

The MIMO optimizer accepts and stores `signal_threshold`, but never uses it in the objective or update rule.

Relevant code:
- `src/aegis/optim/mimo_peak.py`

Impact:
- The optimizer has no actual communication-quality constraint.
- Any intended tradeoff between exposure reduction and service quality is currently unenforced.

Validation:
- Reproduced with `PYTHONPATH=src python3`.
- Runs with different `signal_threshold` values produced identical objectives and identical optimized `x`.

## Overall assessment

The optimization feature area is directionally strong, but still not trustworthy as an end-user decision tool.

The main problem is not numerical instability inside the optimizer kernels. The main problem is integration correctness:
- placement is not isolated from the normal compute loop
- placement is not optimizing full live viewer state
- tilt/power does not use the real antenna geometry
- MIMO optimization is not connected to persistent MIMO state

Until those integration issues are fixed, the optimization panel can produce results that look plausible while not matching the actual scenario being simulated.

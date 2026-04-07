# Review: PR #323 `Add differentiable optimization to viewer`

Date: 2026-04-03
Reviewer: Codex

## Scope

Reviewed merged PR `#323` found via `gh pr list --state merged`.

Feature area covered:
- placement optimization
- tilt/power optimization
- MIMO peak optimization
- SSE streaming route and frontend consumer

## Conclusions

### 1. High: MIMO `signal_threshold` is dead API and not enforced

The MIMO optimizer accepts `signal_threshold` from the request pipeline, but the optimizer step never uses it.

Relevant code:
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/optim/loop.py`
- `src/aegis/optim/mimo_peak.py`

Impact:
- The optimizer can reduce exposure by simply collapsing transmit power.
- If the intent was to preserve service quality while reducing peak `S_ab`, the current implementation does not do that.

Validation:
- Reproduced with `PYTHONPATH=src python3`.
- After 40 steps, optimizer power dropped from `1.0` to about `0.087`.
- Running with `signal_threshold=0.0` and `signal_threshold=10.0` produced identical outputs.

### 2. High: placement mode silently truncates larger searches

The frontend defaults optimization runs to `max_iters = 50`, while placement mode allows `grid_size = 9`, which implies `81` candidates.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/components/panels/OptimizePanel.tsx`
- `src/aegis/optim/loop.py`

Impact:
- Larger placement searches stop early and report `reason = "max_iters"` without exploring the full grid.
- The user can believe a full search completed when it did not.

Validation:
- Reproduced with `PYTHONPATH=src python3`.
- A `9x9` grid emitted `51` events and terminated at iteration `50` instead of evaluating all `81` positions.

### 3. High: placement mode optimizes a different antenna position than normal dosimetry uses

Normal dosimetry treats `antennaPos` as the pole base and adds pole height before sending physics coordinates. Placement optimization uses the raw store position as the search center and evaluates that directly as `tx_pos`.

Relevant code:
- `aegis-web/src/hooks/useDosimetry.ts`
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`

Impact:
- The optimizer solves for one coordinate convention.
- The normal compute pipeline later recomputes dosimetry using a different physical antenna location.
- Final placement results can drift when the regular compute hook runs again.

### 4. Medium: placement SSE updates can trigger redundant normal compute requests

Each placement iteration writes a new `antennaPos` into the simulation store. The normal dosimetry hook retriggers on `antennaPos` changes and has no guard for “optimization is running”.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `aegis-web/src/hooks/useDosimetry.ts`

Impact:
- Placement optimization can race with ordinary compute requests.
- This adds unnecessary RT and dosimetry work during optimization.
- It can produce unstable UI behavior and wasted backend load.

### 5. Medium: tilt/power mode uses a synthetic default boresight instead of actual scene geometry

The frontend does not send an actual antenna-to-body direction. The backend falls back to `[0, 0, -1]`.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/optim/tilt_power.py`

Impact:
- Tilt optimization is only physically correct when that default vector matches the real scene geometry.
- In general scenes, it can optimize the wrong tilt direction.

## Test status

Existing optimization tests passed:

`PYTHONPATH=src python3 -m pytest tests/test_optim_loop.py tests/test_optim_mimo_peak.py tests/test_optim_placement.py tests/test_optim_tilt_power.py tests/test_viewer_optimize_route.py -q`

Result:
- `25 passed in 28.96s`

Gap:
- The current test suite does not catch the issues listed above.

# Conclusions: PR #323 `Add differentiable optimization to viewer`

Date: 2026-04-03
Reviewer: Codex
Reviewed at merge commit: `c8f42397b078eb24e7984ebedff1a44d5644cff2`

## Conclusions

### 1. High: `mimo_peak` was broken from the shipped frontend

The frontend did not send `G_tilde`, so the backend fell back to `scene.G_tilde`. In PR `#323`, `MIMOScene` had no `G_tilde` field. The body channel lived per-user instead. That made the advertised MIMO optimization path fail at runtime instead of starting.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/mimo/scene.py`
- `src/aegis/mimo/user.py`

### 2. High: `tilt_power` was broken on the normal compute-to-optimize handoff

The optimize route read `_last_dosimetry_result` and `_last_dosimetry_body` from the shared `cache` dict, but the compute routes stored them on `app.config`. Even if that cache mismatch were fixed, the route then expected `last_result._paths`, but `DosimetryResult` did not define `_paths`.

Impact:
- A user could run compute successfully and still be unable to start tilt/power optimization.

Relevant code:
- `src/aegis/viewer/routes/optimize.py`
- `src/aegis/viewer/routes/compute.py`
- `src/aegis/result.py`

### 3. High: placement mode was exposed in the UI but impossible to invoke from the browser

The UI enabled placement mode and sent normal JSON parameters, but the backend rejected placement unless the request body contained `evaluate_fn`. Browser clients cannot send a Python callable, so one of the three headline optimization modes was effectively unimplemented.

Relevant code:
- `aegis-web/src/components/panels/OptimizePanel.tsx`
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`

### 4. High: cancellation was cross-user unsafe

PR `#323` used the literal session id `"default"` whenever Flask session state did not already contain a `session_id`. Since the cancellation registry was keyed by that id, anonymous tabs or users could cancel each other's optimization runs.

Relevant code:
- `src/aegis/viewer/routes/optimize.py`

### 5. Medium: `tilt_power` used the wrong physics target

The optimizer computed `sab` without Fresnel transmission factor `T0`, while the viewer dosimetry pipeline reported and enforced results with `T0`. That made the optimization objective physically inconsistent with the main compute path.

Relevant code:
- `src/aegis/optim/tilt_power.py`
- `src/aegis/viewer/routes/compute.py`

## Overall assessment

PR `#323` introduced a substantial feature surface, but at merge time two of the three advertised optimization modes were non-functional end-to-end, the third had a multi-user cancellation bug, and the tilt/power objective was not aligned with the actual dosimetry model.

## Test gap

The main missing coverage was end-to-end testing of the real frontend request shapes against `/api/optimize`, especially:
- browser-driven placement mode
- normal compute to tilt/power handoff
- MIMO compute to `mimo_peak` handoff

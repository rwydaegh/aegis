# QA coverage log

Append-only log of QA sessions. Newest at the TOP (below the Log
heading). Canonical feature surface lives in
`docs/internal/features.md` -- this file only records which sections
have been exercised and how well.

## How to use this file

**Before testing** (agents and interactive `/qa` alike):

1. Read the section headers in `docs/internal/features.md`
   (`grep '^## ' docs/internal/features.md`).
2. Skim the last 20-30 entries of the Log section below.
3. Pick a section that is **absent** from recent entries, or whose
   last entry was shallow ("smoke") and is due for a deeper pass.
4. Bias toward sections touched by recent commits when in doubt.

**After testing**: append one rich entry at the TOP of the Log
section. Commit directly to master (not a PR -- this is metadata,
not code):

```bash
git add agent_hq/coordination/qa-coverage.md
git commit -m "Log QA coverage for <section>"
git push origin master
```

## Entry format

```
### YYYY-MM-DD HH:MM UTC -- "<section name from features.md>"

- Actor: cron-qa | swarm-tester-N | interactive
- Depth: smoke | medium | thorough
- Findings: <count> bugs filed: #NNN, #NNN (or "none")
- Notes: <2-4 sentences. Be candid. What did you try? What worked?
  What felt shaky but not broken-enough to file? Would you say
  "confident this area is healthy" or "should come back soon"?
```

Depth guide:

- **smoke** -- 2-5 interactions, one happy path, under 5 minutes.
  Useful for recently shipped features where you just want to verify
  nothing is obviously broken.
- **medium** -- 8-12 interactions, hit the main controls of the
  section plus a couple of edge cases. 15-25 minutes.
- **thorough** -- 15+ interactions including stress tests, invalid
  inputs, rapid toggling, combinations with adjacent features.
  30-45 minutes. This is where real bugs usually surface.

## Log

<!-- newest entries at the top -->

### 2026-04-17 13:12 UTC -- "Frontend stores, hooks, and physics/movement"

- Actor: swarm-tester-3
- Depth: medium
- Findings: 0 bugs filed
- Notes: Walked through the targeted checklist on production. Quantity
  store transitions work both ways: 28→5 GHz enables SARwb and keeps
  Sab(4cm²); 5→35 GHz removes SARwb and swaps to Sab(1cm²). Display
  quantity stayed Sab across all transitions. `?scenario=open_ground`
  loaded with expected freq, antenna position, body pose, colormap,
  and PASS compliance. Reloading without a scenario param preserved
  the NICT skin model I had picked -- commit 02ac45a fix visibly
  holding. useScenario switching (Close-range, Urban Ghent) cleared
  prior antennas, applied new freq and restriction quantity per-band,
  and updated the URL to `?scenario=...`. Urban Ghent triggered OSM
  ground load. useKeyboard: ArrowUp on canvas nudged antenna and
  triggered recompute (80→12 mW/m²); Delete removed the antenna and
  showed the "Click the scene to place an antenna" prompt. Text-input
  guard holds: arrows in the freq spinbutton only tick the value and
  Delete there does not kill the antenna. Follow-camera + W/D in
  Urban Ghent walked the phantom smoothly with camera follow and
  heatmap recompute each step -- no clipping or jitter observed.
  Placement optimize converged in 25 iterations with 66% reduction,
  final best applied (max went 0.085 → 0.032 W/m², margin +23.7 →
  +30.4 dB), grid preview rendered correctly. MIMO enable flipped the
  header to 1/1 USER and re-ran compute with the expected degraded
  Max TX (70.4 → 56.8 dBm). Console clean (0 errors). Did not drive
  low-height or all-zero MIMO warning paths, GPU-unavailable RT path,
  or voxel step-up/wall-slide collisions -- those need a worked-out
  voxel env and more canvas-coordinate plumbing than I had budget for.
  Confident this area is healthy; those three gaps are worth a
  targeted follow-up.

### 2026-04-17 13:08 UTC -- "Compute orchestrator + voxel meshing + base station processing + interleaved fixes"

- Actor: swarm-tester-2
- Depth: thorough
- Findings: 0 bugs filed
- Notes: Exercised the compute API (`/api/compute` with `X-Stats` header) and
  confirmed the full timings dict is populated -- `body_transform_ms`,
  `engine_compute_ms`, `kernel_ms`, `avg_build_G_4cm2_ms`,
  `avg_matvec_4cm2_ms`, `compliance_stats_ms`, `route_total_ms`,
  `total_ms`. `distance_m` (5.19 m) matches antenna-to-body-center.
  Zero-antenna edge case returns p_abs=0 with no crash. Exposure modes
  reduce as expected (theoretical 100 % -> actual_max 72 % -> typical 36 %).
  `corrections.curvature=true` (mode=spatial) bumps peak_sab from 0.024
  to 0.055 W/m^2 vs Fresnel-only baseline. MSI parser
  (`tests/test_msi_parser.py`, `tests/test_merge.py`) green: 11+14
  passing; spot-checked `FREQUENCY 1.88-1.93 GHz` -> 1905 MHz, `GAIN
  12.86 dBd` -> 15.01 dBi, and zenith convention detection. #535
  Belgium geocoding verified: Ghent/Bruges/Antwerp -> `gov:flanders`,
  Brussels -> `gov:brussels`. #543 ECBF slack-regime tests
  (`test_ecbf_power_slack_regime`, `test_tight_constraint_invertible_Q_uses_slack_regime`)
  pass. #537 MIMO graceful fallback observed: degenerate channels fall
  back to MRT with a clear warning, brief production blip surfaced as a
  friendly toast ("Network error during MIMO compute") rather than a JS
  exception. Voxel-meshing endpoints could not be exercised end-to-end
  because production has no voxel data loaded; both
  `/api/voxels/hull-mesh` and `/api/compute/voxel-rt` returned clean
  400 errors -- skipped this checklist section. Production was rolling
  through redeploys mid-session (commit 4801fb4 -> ccf2b0f -> 09fcc4c)
  which produced a couple of transient `ERR_CONNECTION_REFUSED`
  bursts; these were brief and recovered on retry, not bug-worthy.
  Confidence the orchestrator + base-station + ECBF + geocoding
  surfaces are healthy. Voxel meshing v2 still needs an end-to-end pass
  on a deployment that loads voxels.


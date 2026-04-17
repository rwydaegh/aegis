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

### 2026-04-17 20:15 UTC -- "Compliance and regulatory"

- Actor: interactive
- Depth: medium
- Findings: 0 bugs filed (intentional design path reviewed and
  flagged below as a UX oddity, not bug-worthy)
- Notes: Exercised the compliance surface on Open ground at 28 GHz.
  Happy path is healthy: Sab(4cm²), Sinc(local), Sinc(wb) all PASS
  with expected values and margins, limit scaling is correct on the
  General Public -> Occupational toggle (every limit exactly 5×,
  Summary Margin +22.1 -> +29.2 dB = +10log10(5) as expected).
  Power sweep produced a clean curve and reported Max compliant
  65.0 dBm, matching the CompliancePanel Summary's 65.1 dBm Max TX
  value. Frequency sweep and Compliance heatmap both render without
  NaN/empty cells (heatmap all green at 43 dBm, which is correct
  since 65 dBm is the boundary). Clicking "Max TX power" from the
  Summary correctly bumps power to 65.1 dBm, which produces an
  OVERALL FAIL because SAR_wb tips over the 0.08 W/kg limit at
  exactly ratio 1.00 -- and that row appears in the panel *only
  once it starts failing* (the `visibleChecks` filter keeps passing
  disabled checks hidden). The resulting UX is: user sees PASS rows
  for Sab/Sinc with +1.9 to +4.8 dB margin at Max TX, but the
  header badge flips to FAIL with SAR_wb row suddenly popping in.
  **Not filed**: this is the intentional design from issue #235
  ("Margin/Max TX/badge always use all compliance.checks, not
  visibleChecks") merged via #236, which was chosen specifically to
  avoid misreporting PASS when a disabled check is exceeded. The
  remaining wart is that at 28 GHz the backend still returns a
  SAR_wb check with limit 0.08 W/kg, while ICNIRP 2020 Table 5
  restricts SAR_wb to 100 kHz - 6 GHz (the docstring of
  `icnirp_limits` is honest that "Above 6 GHz all limits are
  returned", i.e. the backend is deliberately conservative). Worth
  thinking about someday: either (a) drop SAR_wb from checks above
  6 GHz to match ICNIRP strictly, or (b) keep the conservative
  extension but render a muted SAR_wb row in the panel so the
  Summary margin/Max TX never refer to an invisible constraint.
  /api/compliance/spatial: drove it with invalid bbox shapes, bad
  receiver_height values, and an unknown scenario -- all returned
  400 but with the prior-guard error "No base stations loaded"
  firing before the #544 validators. The #544 input validators
  themselves are present in routes/analysis.py:386-419; didn't
  exercise them behind the basestation guard. Console was clean
  apart from the expected 400s from my probe and WebGL/THREE
  deprecation noise. Confident happy-path compliance flows are
  healthy; the SAR_wb-at-mmWave conservatism is a design call
  worth discussing rather than a bug.

### 2026-04-17 18:25 UTC -- "Coherent MIMO and beamforming"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #567
- Notes: Drove the MIMO panel end-to-end on Open ground. Toggled Enable
  MIMO: header flipped to 1/1 USER, margin +22.1 -> +13.9 dB, Max TX
  65.1 -> 56.9 dBm as expected. Added Duke as user 2 and swept all
  four beamforming modes at 4x4 UPA: User 1 peak stayed 0.11 W/m^2
  (consistent with per-user normalization), User 2 exposure differed
  by mode (MRT 77.99, ZF 69.61, MMSE 81.74, ZF+Exp 69.61 mW/m^2).
  ZF=ZF+Exp at low regularization is expected. MMSE > MRT is slightly
  surprising but plausible since MMSE trades off per-link MSE not
  "minimize user 2 exposure"; not bug-worthy without deeper analysis.
  UPA array sizing exercised at 1x1 (13.62 mW/m^2, +26 dB margin),
  4x4 (baseline), 8x8 (peak 0.31 W/m^2, +12.4 dB), and 12x12
  (144 elements, 0.12 W/m^2 at User 1, +16.6 dB). All sizes compute
  and update compliance without crashes. #566 gating verified:
  Tilt+power button is disabled on Open ground (no RT paths).
  #565 NaN colorbar fix verified: labels are numeric
  (5.0e-7, 3.8e-7, 2.5e-7, 1.3e-7, 0), not NaN -- fix from commit
  0068eeb holds. **Bug 1 (#567)**: ColorLegend scale gets stuck at
  the optimizer's internal peak (e.g. 5.0e-7 W/m^2) after MIMO peak
  optimize completes. Compliance panel and per-user HUD correctly
  show the current beamforming state (0.11 W/m^2 compliant, +16.9
  dB margin), and the body heatmap clearly renders bright red/orange
  peaks, but the legend ticks are 5-6 orders of magnitude too small
  and stay stale even when the user switches beamforming mode to
  force a new compute. Root cause traced to `ColorLegend.tsx`:114
  reading `useSimulationStore.stats` directly rather than via
  `useActiveSimulation`, which is what the compliance panel uses.
  In MIMO mode the simulation store's `stats.peak_sab` is only ever
  updated by `useOptimization.ts`:50 during optimize, never by
  `useMIMODosimetry` (which writes to `mimo.setUserResult`). Clicking
  the lock button (🔒) snaps the legend to the actual peak, so the
  data is available, just not being read. Console was clean apart
  from the THREE.Clock deprecation warning (known not-a-bug).
  Confident the beamforming math, multi-user, UPA sizing, and
  optimize gating are healthy; the ColorLegend stale-state is the
  only real bug and is documented with a surgical fix sketch in #567.

### 2026-04-17 16:25 UTC -- "Optimization"

- Actor: interactive
- Depth: medium
- Findings: 2 bugs filed: #563, #564
- Notes: Drove all three optimize strategies on the Open ground
  scenario. Placement optimizer is healthy: 3x3 through 50x50 grids
  all complete and improve the margin monotonically (+22.1 → +28.0 dB
  at 5x5, +36.0 at 11x11, +44.4 dB eventual after stacking moves),
  and server clamps grid_size to [1,50] and spacing to [0.1,500] as
  documented in routes/optimize.py. The #553 race guard (stop writes
  no longer stomp a subsequent start) held up in code review;
  in-browser I couldn't actually catch the button showing "Stop
  (iter X)" even on the biggest run because each placement iter is
  a full /api/compute round-trip and the accessible-tree snapshot
  seems to lag the text swap -- left as a gap rather than a finding.
  Edge inputs: spacing=0 collapses to a single position, still
  "converges" after N iterations with 1% reduction, not a crash but
  cosmetically pointless. Grid size HTML attrs say min=3/max=9/step=2
  but Playwright fill bypasses validation; backend clamps anyway, so
  users can only hit the values the UI exposes -- fine. **Bug 1
  (#563)**: after MIMO peak optimizer converges, ColorLegend ticks
  render as 5 NaN strings. Root cause traced: mimo_peak.py step()
  result dict has no `stats` key, useOptimization.handleIterationEvent
  coerces missing stats to `{}`, ColorLegend computes
  `maxSab = stats.peak_sab` = undefined → NaN through formatLegendValue.
  Body heatmap and compliance panel still show valid numbers, so the
  bug is silent unless you look at the legend. **Bug 2 (#564)**:
  Tilt+power button is enabled in non-RT scenarios (Open ground),
  clicking Optimize dumps the raw 400 JSON payload into a toast
  ("No RT paths cached. Run an RT compute (/api/compute/rt) first.").
  Missing gating + raw JSON leakage. Console stayed clean apart from
  the expected 400 and the password-gate 401. Confident placement is
  healthy. MIMO peak and tilt+power need the fixes in #563/#564 before
  either surface can be called clean.

### 2026-04-17 14:17 UTC -- "3D environment reconstruction"

- Actor: interactive
- Depth: medium
- Findings: none filed
- Notes: Drove the Environment panel across all four sources on
  production. Urban Ghent scenario preset loads compute + compliance
  PASS immediately (7.80 mW/m^2, +34.1 dB margin), but the OSM
  buildings fail to render because `/api/environment/osm` returns
  504 repeatedly (Overpass upstream timeout, listed as known
  tradeoff). The Environment panel does surface the error inline
  ("Overpass query timed out. Try a smaller radius..."), so it is
  not silent -- but only if the user expands Environment. Smaller
  radii still timed out during this window. Switching source to
  "3D Tiles" and geocoding "Times Square, New York" correctly
  resolved (40.7580, -73.9855) and fired `POST /api/environment/
  3dtiles`, but no tiles appeared in either first-person or globe
  camera toggle, and no error surfaced in the panel after ~45 s.
  Unclear whether this is slow tile traversal or a silent fail
  (Google API key / geometric error handoff). Worth a follow-up
  pass with a known-good 3D-tiles region. Sionna scene load/clear
  is healthy: Simple Street Canyon (~1.5 s) and Box Two Screens
  (~1.3 s) both load; phantom sits on floor (#7103cfe fix holding,
  no clipping or floating); Clear Scene removes geometry both times
  (#20881a9 verified visually). Minor curiosity: Sab dropped from
  7.80 to 7.00 mW/m^2 after the first scene load and stayed at
  7.00 through Clear Scene -- not flagged as a bug because the
  scene load may change antenna or compliance basis, needs deeper
  repro. Coverage source flips the view into globe mode, renders
  the 416,171-site heatmap over Europe, and the "Hide Coverage"
  HUD toggle correctly shows/hides the CoverageHud pill widget
  (it does NOT hide the heatmap itself -- that is the HudToggle
  contract, not a bug). Mid-session brief 502/ERR_CONNECTION_
  REFUSED burst during a deploy, recovered in <30 s. Confident
  OSM (when upstream cooperates), Sionna scenes, and Coverage
  globe are healthy. 3D Tiles load needs a targeted follow-up.

### 2026-04-17 13:46 UTC -- "Sidebar panels (PR-5, PR-F, PR-J)"

- Actor: swarm-tester-4
- Depth: thorough
- Findings: none
- Notes: Exercised every sidebar panel on open_ground scenario.
  Analysis: Exposure distribution, SAB histogram, Power sweep,
  Frequency sweep, Distance sweep, and Compliance heatmap all
  compute and render without NaN/empty values. Ray Tracing:
  verified PARAM_CAPS dispatch -- DiffeRT exposes
  Exhaustive/SBR/Hybrid with edge-diffraction and diffraction
  lit-region gating; Sionna RT pins method to SBR with
  "(fixed for Sionna RT)" label. Fresnel T(theta) toggle shows
  angle-dependence tooltip (#539 verified). Antennas panel MIMO
  guard shows the "Antenna config managed in MIMO and Antenna
  tabs" empty-state; operator filter filters 411 -> 72
  antennas when Orange+Telenet unchecked. Environment panel shows
  only terrain + coverage source count, no dead CloudRF
  checkbox (#540 verified). Scene panel load/clear works (816ms
  for Simple Street Canyon). Optimize panel: Placement strategy
  converges ("Converged after 25 iterations. 68% reduction"),
  Tilt+power and MIMO peak strategies selectable. Export panel
  shows all 6 export buttons (Screenshot PNG, CSV/JSON/NPZ
  dosimetry, Compliance TXT, Config JSON) enabled and clickable.
  Bug reporter opens via Shift+B with screenshot, textarea,
  Cancel/Submit buttons; Escape closes cleanly. Pattern browser
  search filters list correctly (0 results for nonsense terms;
  all Kathrein when filtered by "Kathrein"). Noted but not
  filed: Pattern browser renders all 10000 patterns to DOM at
  once (causes intermittent input timeouts); "10000 results"
  counter is a cap label rather than a per-filter count; several
  Commscope dBi values show excess precision (e.g.
  "17.689999999999998 dBi") -- cosmetic float formatting,
  flagged to Sentry-free. Overall confident this area is
  healthy; Pattern browser DOM virtualization would be a nice
  polish.

### 2026-04-17 13:25 UTC -- "HUD + R3F scene components + AnnotationCanvas + share link"

- Actor: swarm-tester-5
- Depth: medium
- Findings: 0 bugs filed
- Notes: Verified the recent decompositions held up in production.
  MIMOPanel: added user rows, compliance title updated to "2 users".
  CompliancePanel: all 4-5 CheckRow entries render with label, value,
  limit, and PASS/FAIL state against the 60 GHz mmWave scenario.
  ColorLegend: linear/dB toggle works, lock colormap button present,
  floor spinbutton clamps at -80 and -5 dB boundaries. AnnotationCanvas
  (bugReporter modal): drew a multi-point stroke -> Undo + Clear
  appeared (gated on strokeCount > 0); Zoom in enabled Zoom out +
  Reset zoom and showed the "1.5x hold Space to pan" hint; Clear
  removed the stroke; Reset zoom restored 1x. Share link: generated
  via Toolbar share button (clipboard write intercepted to capture
  URL), navigated to /#s=<payload>, state decoded and restored without
  crash on a fresh reload. #537 globe camera toggle did not crash.
  Feels healthy; didn't stress AntennaArray phase-color selection or
  multi-body colormap-lock coordination, worth a deeper pass next
  swarm.

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

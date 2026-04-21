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

### 2026-04-21 12:25 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-174381)
- Depth: smoke (unintended overlap — should have rotated)
- Findings: none filed
- Notes: Another Viz/Analysis pass on the same prod commit 8bd6962.
  Echoes qa-agent-163229's 10:20 UTC entry almost exactly: confirmed
  `/api/analyze/path-contributions` still 404s on prod (PR #712 not
  deployed yet), click-to-jump on the compliance heatmap lands in
  the red band and correctly flips PASS->FAIL, colormap lock at
  93.4 W/m^2 preserved across frequency swap to 100 GHz where real
  peak is 100.44, unlock rescaled to 101. All already-deployed viz
  surfaces remain healthy. Admitting up front this adds almost no
  new signal beyond the ~8 prior same-commit passes today -- the
  previous entry's recommendation stands: next agent should rotate
  to a colder section (Body geometry, Coherent MIMO, Optimization,
  Compliance, Web viewer backend) until a deploy past 4428201
  lands and PathInsightsSection can actually be exercised.

### 2026-04-21 10:20 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-163229)
- Depth: smoke (rotated to be honest about over-coverage)
- Findings: none filed
- Notes: Picked this section before pulling — `git fetch` after my
  run revealed 5+ "Log QA coverage for Visualization and analysis"
  commits already on master today (e90d54a, b246799, e1b8f62,
  ed27749, 5659ef3 plus the 08:30 UTC entry below from
  qa-agent-147315). Heavy over-coverage — strongly recommend the
  next agent rotate to a colder section (Body geometry / Coherent
  MIMO / Optimization / Compliance / Web viewer backend). Two
  small additions worth recording from my own pass on
  `8bd6962`: (a) the new `/api/analyze/path-contributions`
  endpoint introduced by PR #712 returns 404 from an authenticated
  in-page `fetch()` ("404 Not Found" Flask default page), confirming
  via a different path than the 08:30 entry that the deploy lag
  blocks PR #712 + #713 (ECBF HUD warnings). (b) the colorbar
  Floor `<input type=number min=-80 max=-5 step=5>` is a
  React-controlled input where `playwright fill -25` to `-40`
  appears to fill but the React state is not updated — the only
  way I got it to apply was the standard React-aware setter
  workaround (call the native value setter then dispatch
  `input` + `change`), then the ticks switched 0/-6/-13/-19/-25
  → 0/-10/-20/-30/-40 dB. After a freq switch (28→60 GHz) the
  Floor snapped back to -25, defensible per-frequency reset.
  Lock toggle confirmed working: 28 GHz peak 0.081 W/m² scale
  preserved across switch to 60 GHz where actual peak is
  0.094 W/m², body shows red where it exceeds the locked scale;
  unlock auto-rescales to 0.094/0.071/0.047/0.024/0. Export
  endpoints (`/api/export/dosimetry-{csv,json,npz}`) all 200,
  CSV well-formed (12 cols, 23828 triangle rows + header).
  Console clean (only deprecation/WebGL noise + my own debug
  404 calls). Marking as smoke depth even though I touched many
  controls, since the actual signal added beyond the 6 prior
  passes today is small.

### 2026-04-21 08:30 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-147315)
- Depth: medium
- Findings: none filed
- Notes: Picked this section because it was absent from recent 20+
  log entries and commit 4428201 (PR #712 "Surface path contributions
  to the viewer Analysis panel") just landed — directly relevant.
  **PR #712 is NOT yet deployed**: prod is at `8bd6962`, #712
  (`4428201`) is 9 commits ahead of deployed. Verified by grepping
  the deployed AnalysisPanel.tsx at that commit — no PathInsights
  import/Section, and the live DOM confirms no "Path insights"
  heading or any "Path" text in the Analysis accordion. When this
  ships the next QA agent should force an RT compute on Simple
  Street Canyon and verify the top-K path table populates with LOS
  #1 dominating (expected given open geometry). Drove the existing
  viz surface end-to-end on open_ground + Simple Street Canyon
  Sionna scene with RT enabled (DiffeRT backend, depth 2, 1M rays).
  RT compute successful in 14.8s first run, Peak 0.124 W/m²
  (+22.1 dB margin, PASS). **Exposure distribution**: pre-RT
  43.8% illuminated (10.436 / 23.826 k triangles, 3669 cm²), post-RT
  100% illuminated (23.826 / 23.826 k, 7905 cm²) — makes sense
  since Street Canyon walls reflect rays to body back. Stats table
  Peak/P99/P95/Mean/Median values all monotonic and consistent
  across frequency swap (28→10 GHz: Peak 0.124→0.113, mean
  0.024→0.023). **SAB histogram**: Plotly log-scale histogram
  rendered with green "Below limit" bars correctly binned (no
  "Above limit" red bars since PASS). **Power sweep**: plot shows
  margin-vs-TX-power curve crossing y=0 at 62.0 dBm; "Max
  compliant: 62.0 dBm" + Set button both work. **Frequency
  sweep**: margin-vs-freq curve rendered cleanly. **Distance
  sweep**: "Current distance: 2.6 m" (antenna scenario center is
  ~3m but closest body point is 2.6m), "Min. compliant distance:
  0.3 m" — both physically consistent with +22.1 dB margin at 2.6m
  via 1/r² (reducing to 0.3m adds ~19 dB, leaving ~3 dB headroom
  which rounds near-boundary). **Compliance heatmap**: 2D
  (freq × TX power) grid rendered all-green at current operating
  point, with legend Compliant/Exceeded/Boundary — boundary line
  off-grid because we're well inside compliant region. **Colormap
  controls**: dB toggle correctly switches Sab(W/m²) → Sab(dB re
  peak) with floor -25 dB and phantom redraws with expanded color
  range; lock toggle 🔓→🔒 persists scale across computes.
  **Tissue spectrum**: live update confirmed at 28 GHz (eps_r=16.6,
  sigma=25.8 S/m, T0=0.54) and 10 GHz (eps_r=31.3, sigma=8.01 S/m,
  T0=0.49) — dots on curves move correctly, all three plots
  (permittivity / conductivity / T0) sync. **Exports**: CSV
  (3.16 MB, 12 columns: cx/cy/cz, area_m2, nx/ny/nz, sab_w_m2,
  sab_4cm2_w_m2, sinc_w_m2, sinc_4cm2_w_m2; header + ~23826 rows
  matches triangle count), TXT compliance report (S_ab 4cm² 0.11,
  SAR_wb 0.00, S_inc local 0.23, wb 0.04, all PASS, +19.1 dB at
  10 GHz/43 dBm), and config JSON (17.9 KB, full antenna +
  rendering config) all download cleanly. **Q eigenvalue / rho
  gauge**: listed in features.md as visualizations but searched
  the DOM with MIMO enabled and found zero "Q eigenvalue" /
  "eigenvalue" / "rho" / "ρ" strings — these live in
  `src/aegis/viz/` Python matplotlib/plotly dashboards, not the
  React viewer. Features doc could clarify this to avoid future
  confusion. **Three minor observations not filed**: (a) clicking
  Analysis section accordions collapses Export (accordion behaves
  as single-open), defensible UX not a bug; (b) during the session
  3× `/api/capabilities` 404s surfaced in the console — not
  reproducible from a clean reload, possibly a race against
  session refresh; the store seems to cope so no user-visible
  impact; (c) RT compute trace label still reads "Spatial +F"
  in the header even though the compute actually came from
  `/api/compute/rt` — the label reflects the physics corrections
  toggled, not the path source, and is consistent but slightly
  misleading when RT is enabled. Worth a UX tweak ("RT + F") but
  not bug-filing. Confident the deployed visualization surface is
  healthy. Next pass should verify Path insights after the next
  deploy catches up to master.

### 2026-04-21 06:15 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-129852)
- Depth: medium
- Findings: none filed
- Notes: Sixth consecutive Viz/Analysis pass. Re-confirmed what
  81118, 63437, 99366, and 116685 already found: prod still on
  `8bd6962` so PR #712's Path Insights panel isn't live —
  `GET /api/analyze/path-contributions?top_k=5` returned a Flask
  HTML 404 (route unknown), not the JSON 404 the live route would
  emit. Not filing; waiting on a deploy past 4428201.
  New ground I covered over the prior passes: (a) the legend
  **Floor input** in dB mode accepts arbitrary values — set
  -25 → -10 and watched the heatmap redistribute its gradient
  (labels are 0/-3/-5/-8/-10 after integer rounding of evenly-spaced
  -2.5-step ticks, a minor cosmetic quirk, not a bug); (b) the
  **Lock colormap** toggle holds the locked max across big
  dosimetry changes — locked at 0.124 W/m² peak, bumped antenna
  power 43→55 dBm, peak shot to 15.85 W/m², body went fully red
  as expected; (c) **RT DiffeRT on Simple Street Canyon** runs
  cleanly (14.9 s, GPU asleep → ready, peak 0.08 → 0.124 W/m²,
  illumination 43.8% → 100%) with no stale-cache carryover after
  resetting power, complementing 81118's non-RT regression check.
  Did NOT encounter the MIMO HUD margin-loss bug qa-agent-116685
  filed as #729 (didn't exercise MIMO in this pass). Confident
  the non-Path-Insights viz surface is healthy on `8bd6962`;
  the one thing worth doing on the NEXT pass is skipping the
  re-test and only touching this section again AFTER a deploy
  lands PR #712 — further covergae on 8bd6962 Viz/Analysis is
  diminishing returns.

### 2026-04-21 04:25 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-116685)
- Depth: medium
- Findings: 1 bug filed: #729
- Notes: Picked this section because last pass was 2026-04-18 (3 days
  stale) and PR #712 (Surface path contributions to the viewer Analysis
  panel) just landed on master at 4428201. Wanted to exercise the new
  `PathInsightsSection`. **Prod deployment lag caught immediately**:
  prod runs commit 8bd6962, which is 9 commits behind master
  (before #707, #709, #710, #712, #713). The frontend bundle
  `index-fsql_BQa.js` contains zero matches for `Path insights`,
  `PathInsightsSection`, or `path-contributions`, so the new panel is
  not deployable-testable yet. Not a bug to file — a release hasn't
  fired since v0.30.0 metadata bump at 6149aea; next deploy will pick
  it all up. Flagging so a follow-up agent picks this up post-deploy.
  Pivoted to exercising the rest of the Viz/Analysis surface on prod:
  Analysis panel -> Exposure distribution (Peak 0.081, P99 0.073,
  P95 0.058, illuminated 43.8% / 3695 cm²), SAB histogram (log-scale
  bins from 6.2e-10 to 3e-3 W/m², green below-limit / orange
  above-limit colors correct), Power sweep (linear slope, dashed red
  line at 0 dB, Max compliant 65.0 dBm with Set button), Frequency
  sweep (flat ~+22 dB across 7-100 GHz for isotropic antenna — fine
  for this scenario), Distance sweep (1/r² curve, Min compliant
  distance 0.3 m, consistent with current +22 dB at 4 m), Compliance
  heatmap (all green at 28 GHz x wide power range, expected).
  Export surface: Screenshot PNG (canvas only, no HUD/compliance
  overlay — a real-user pain point but the PNG export clearly says
  "Screenshot", not "dashboard export", so not bug-worthy), CSV/JSON/NPZ
  dosimetry (5 MB JSON with 23826-triangle centroids, well-formed),
  Compliance TXT (all 4 checks PASS with +22.1 dB overall margin),
  Configuration JSON (full app snapshot). Optimize -> Placement
  strategy ran 25 iterations converging to 65% reduction
  (+22.1 → +27.9 dB margin, peak Sab 0.081 → 0.016 W/m², max TX
  power 65.0 → 70.8 dBm); replay slider and Best button render but
  I didn't drag-interact. MIMO toggle: enabling MIMO with 1 user
  (thelonious) gave Sab 0.22 W/m² compliant, and that's where the
  bug surfaced. **#729 filed**: MIMO HUD loses the per-check
  `+X.XdB` margin label AND the entire Margin/Max TX power/Frequency
  summary row. Root cause is `_compliance_summary` in
  `src/aegis/viewer/routes/mimo.py:296-317` omitting `margin_db`
  per check while `src/aegis/viewer/routes/compute/_responses.py:239-263`
  includes it. Frontend (`CompliancePanel.tsx:110`) hides the whole
  summary block when `tightestMarginDb()` returns null. Clear
  copy-pasteable one-line backend fix. dB colorbar toggle works
  (Sab (dB re peak) goes 0 to -25 dB). Share link updates URL to
  `?scenario=open_ground` but does NOT encode MIMO / optim / antenna
  state — probably by design for a simple bookmark share, but a
  power user who wants to reproduce a MIMO+optim session will hit
  this wall. Not filed — share-link scope is ambiguous. Overall:
  healthy surface except for the MIMO HUD info loss; should revisit
  once PR #712 is live to actually test the Path Insights feature.

### 2026-04-21 02:30 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-99366)
- Depth: medium
- Findings: 1 bug filed: #726 (possibly adjacent to the closed #719 / PR #720 SAR_wb-above-6-GHz cluster)
- Notes: Fifth consecutive pass on Visualization and analysis (see
  47079, 17564, 63437, 81118 earlier). Prod still at `8bd6962` so Path
  insights (PR #712) remains unexercisable end-to-end from live site —
  the earlier agents confirmed via bundle inspection and I re-confirmed
  via DOM snapshot (Analysis accordion only lists Exposure distribution
  / SAB histogram / Power sweep / Frequency sweep / Distance sweep /
  Compliance heatmap; no Path insights entry). Covered the deployed
  surface on `urban_ghent` (28 GHz, 43 dBm ref, thelonious, Spatial +F):
  Exposure stats are self-consistent (Peak 7.85 mW/m² matches HUD
  numeric overlay, illuminated 44.1% of 23,826 faces), SAB histogram
  shows all log-binned counts below limit, Distance sweep's 1/r² trend
  is clean, Compliance heatmap generates an all-green rectangle and
  does not show the boundary line (consistent with max compliant being
  outside the swept range). Frequency sweep I re-tested on
  `open_ground` and saw the 23.95 → 22.07 dB 1.9 dB swing that
  qa-agent-63437 observed post-#720, so the SAR_wb-leak fix from #719
  is live — good. Legend dB/Lin toggles round-trip correctly; lock
  (🔓→🔒) persists across scenario switch. **Bug #726**: HUD "Max TX
  power" (75 dBm) advertises a value that is not actually compliant
  — clicking it sets power to 75 dBm, top bar turns WARN, Margin
  collapses to +0.0 dB while the panel's only visible check row
  (Sab 4cm²) still reads +2.1 dB PASS. Cross-checked with direct call
  to `/api/compliance/power-sweep` which returned `p_max_compliant_dbm
  = 72.03 dBm` with the same stats values. The 3 dB gap suggests
  `CompliancePanel.computeMaxPowerDbm` (frontend) and `power_sweep`
  (backend) are iterating over different check sets — the frontend is
  apparently missing a binding check the backend uses. This rhymes
  with #719 (unconditional SAR_wb check leak above 6 GHz) so #726 may
  turn into a duplicate once the same filter is applied to the HUD
  surface; leaving linking decision to the maintainer.

### 2026-04-21 00:24 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-81118)
- Depth: medium
- Findings: none filed
- Notes: Independent re-run on prod (commit 8bd6962, 9 behind master)
  targeting PR #712's Path insights surface that earlier qa-agent
  passes (47079, 63437) could not exercise. Confirmed the PR has NOT
  reached prod: bundle `index-fsql_BQa.js` contains no
  `/api/analyze/path-contributions` reference, the DOM has no "Path
  insights" section header, and GET on the endpoint returns Flask
  HTML 404 rather than the JSON 404 the route would emit without a
  cache. Needs a deploy before that surface can be tested live.
  Pivoted to the rest of Visualization and analysis on Simple Street
  Canyon + RT (DiffeRT). Exposure distribution, SAB histogram, and
  Power/Frequency/Distance sweeps all rendered coherent values
  (Peak 0.629 W/m^2, P99 > P95 > Mean > Median monotonic; +12.1 dB
  overall margin tracks the tightest SAR_wb check at ~0.005 /
  0.08 W/kg). Compliance heatmap built in one shot; timing breakdown
  populated post-compute; Export panel enumerated report buttons
  without errors. Toggled RT off mid-session -> Peak dropped to
  0.221 W/m^2, margin widened to +18.0 dB with a clean 1.4 s non-RT
  recompute -- no stale cache carryover, complementing PR #722.
  Deployed surface feels healthy. Flagging Path insights for the
  next cron pass once prod catches up.

### 2026-04-20 22:30 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-63437)
- Depth: medium
- Findings: none filed
- Notes: Followed qa-agent-47079's 20:15 UTC pass (which filed #719,
  fixed via PR #720 / ec64270). Independent re-run on the now-patched
  build focused on PR #713 (ECBF infeasibility surfacing) which the
  earlier pass did not exercise. Open ground, 28 GHz, thelonious,
  MIMO enabled: MRT / ZF / MMSE / ZF+Exp precoder buttons all re-ran
  cleanly; MIMO peak optimizer converged in 6 iterations with the
  per-iteration chart updating live. Pushed to 4-user MIMO on adult
  phantoms to provoke the gateway timeout — `/api/mimo/compute`
  returned ERR_TIMED_OUT (600s gunicorn limit, expected), and PR
  #713's HUD surfacing worked as intended: "MIMO compute failed:
  timeout" banner plus per-user "Compute failed" badges, no silent
  swallowing. Colormap dB↔Linear toggle re-rendered the heatmap
  correctly both directions. Frequency sweep now varies 23.95 →
  22.07 dB on the deployed build, confirming PR #720 took effect.
  Path Contributions panel (PR #712) not exercised — Urban Ghent
  OSM fetch hit the known Overpass timeout, no RT compute. Minor
  cosmetic: optimizer console logs "Converged after 6 iterations,
  -0% reduction" when reduction rounds to a tiny negative; not
  worth filing. Area is healthy post-#720; PR #712 still needs a
  live pass once an RT path is exercisable.

### 2026-04-20 20:15 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-47079)
- Depth: medium
- Findings: 1 bug filed: #719
- Notes: Picked this section because PR #712 (4428201, "Surface path
  contributions to the viewer Analysis panel") landed at 15:01 UTC
  today and the Analysis surface had not been directly covered since
  2026-04-18 08:22 UTC. Prod build at session start was `8bd6962`
  (6 commits behind master) so the new PathInsightsSection is NOT yet
  deployed — verified by reading `PathInsightsSection.tsx` locally
  (empty-state copy: "Run a ray-traced compute to see which paths
  drive the peak exposure") and confirming the Analysis accordion on
  prod only has Exposure distribution / SAB histogram / Power sweep /
  Frequency sweep / Distance sweep / Compliance heatmap. Follow-up
  agent should re-test #712 once the deploy lag closes. **Section
  collision**: qa-agent-977949 (16:15) and qa-agent-17564 (18:25)
  also covered this area earlier today — rebase merged both entries
  below. qa-agent-977949 flagged the frequency-sweep flatness
  observationally ("+29 dB flat on Urban Ghent") but accepted it as
  "by design — denominator-only sweep". I went deeper on Open ground
  and confirmed via direct API probing that the flatness is actually
  a SAR_wb-inclusion bug above 6 GHz (see below); filed as #719.
  **Drove the rest of Analysis end-to-end on Open ground (28 GHz,
  65 dBm, thelonious, Peak 80.46 mW/m², +22.1 dB)**:
  Exposure distribution stats match HUD (Peak 0.081, P99 0.073, P95
  0.058, Mean all 0.012, Mean illuminated 0.027, Median illuminated
  0.023 W/m², Illuminated 43.8%, area 3695 cm²) — healthy.
  SAB histogram renders a log-scale x (6.2e-10 to 3.6e-3 W/m²) with
  linear count y (0-3400); bars all green "Below limit" consistent
  with +22 dB margin. Y-axis labels "3400" and "1700" overlap each
  other at the top of the axis — cosmetic quibble, not filed.
  Power sweep renders the green margin curve from 22-63 dBm with
  the red FAIL threshold dashed at 0 dB; reports "Max compliant
  65.0 dBm" which matches current operating point. Healthy.
  **Bug 1 (#719)**: Frequency sweep renders a PERFECTLY FLAT
  green line at +22.04 dB across 7-100 GHz. Captured the fetch URL
  — frontend calls `GET /api/compliance/frequency-sweep?sab_4cm2=...
  &sinc_local=...&sar_wb=0.0005&sinc_wb=0.0204`, and `sar_wb`
  (always 0.0005 W/kg from the compute) pins the tightest margin
  at `10·log10(0.08/0.0005) = 22.04 dB` constant across the full
  band. Re-ran the same URL with sar_wb removed → margin correctly
  varied 23.95 → 22.07 dB (1.9 dB swing driven by Sinc_local ∝
  1/f^0.177). Per ICNIRP 2020 Tables 2-3 SAR_wb is the basic
  restriction for 100 kHz - 6 GHz; above 6 GHz the BR is Sab.
  `icnirp_limits` (`compliance/__init__.py:234`) always returns
  `sar_wb=0.08` regardless of frequency, and `evaluate_compliance`
  (`:332-339`) creates a check whenever the value is passed —
  SAR_wb leaks into checks at every frequency > 6 GHz.
  `FrequencySweepSection.tsx:49` + `PowerSweepSection.tsx:53`
  both pass sar_wb unconditionally. Suggested 3 independent
  fixes in the issue body; cleanest is `frequency_sweep`
  (`compliance/__init__.py:632`) setting `sar_wb=None` when
  the iteration point is above 6 GHz. **Compliance heatmap**:
  generated cleanly, all-green rectangle across the sampled
  (freq, power) window — no visible artifacts. **Distance
  sweep**: skipped live test — read `DistanceSweepSection.tsx`
  and confirmed it's a pure client-side `20·log10(d/d0)`
  transform on the current margin, so doesn't hit the API and
  can't inherit the SAR_wb bug. Other observations (NOT filed):
  (a) Power sweep has the same sar_wb unconditional-pass
  pattern but since all metrics scale linearly with power, all
  margin curves move together and the dominant metric doesn't
  matter for the output shape — no user-visible bug. (b) Chart
  current-frequency indicator (white dashed vertical line at
  28 GHz on the sweep) renders correctly even when the
  underlying data is flat. Confidence: the non-sweep Analysis
  pieces (Exposure, Histogram, Power sweep, Distance sweep,
  Heatmap) are healthy; Frequency sweep is actively misleading
  and should be prioritized. Path Insights (#712) remains
  untested on live site — blocked on deploy of commits
  `4428201..6149aea`.

### 2026-04-20 18:25 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-17564)
- Depth: medium
- Findings: 1 bug filed: #716
- Notes: Picked this section because last entry was 2026-04-18 08:22 (~2
  days) and PR #712 (4428201, Surface path contributions to the viewer
  Analysis panel) landed earlier today, so the Analysis sidebar has
  fresh code. Wanted to exercise the new PathInsightsSection end-to-end
  but the Urban Ghent OSM fetch 504'd on this session (Overpass timeout,
  known external flake) so no ray-traced compute could run and
  `rtPaths`/`rt_paths` never populated — thus Path insights stayed
  hidden. Re-testing once OSM is warm (or using a scene file) is the
  obvious follow-up; I did not try Sionna RT / voxel RT because the
  frontend already errored on env before any backend selection
  mattered. Exercised the rest of the Analysis panel on the Spatial
  Urban Ghent result: Exposure distribution stats (illum 44.1%, peak
  7.9e-3 W/m², P99 7.1e-3), SAB histogram (log-binned, all bins below
  limit as expected), Power sweep (reported Max compliant 72.0 dBm but
  chart X-axis only spans 23-63 dBm so the compliance crossover isn't
  visible on the plot — plausibly by design), Frequency sweep 7-100
  GHz (margin line is near-flat which for the 20 W/m² band-wide Sab
  basic restriction above 6 GHz is physically fine), Distance sweep
  1-64 m with current 12.7 m / min compliant 0.3 m (looks like a clean
  1/r² curve), Compliance heatmap (all-green, white boundary not shown
  because max compliant is above the 63 dBm top tick — consistent with
  Power sweep). Colorbar "dB" toggle flipped correctly from linear
  W/m² to "Sab (dB re peak)" with floor -25 dB and the phantom
  re-coloured to emphasise sub-peak distribution. dB → Lin → dB round
  trip worked.
  The bug I filed (#716) surfaced while sanity-checking that frequency
  change re-drives compute: with RT enabled but env 504'd, switching
  presets 0.9 → 5.8 → 10 GHz and changing P_TX 43 → 30 dBm produced
  zero `/api/compute*` calls (checked via
  `performance.getEntriesByType('resource')`) yet the HUD gave no
  warning. Unchecking RT immediately fired a 705 ms spatial compute
  and the HUD snapped to the currently-selected frequency. The
  "No environment mesh available" toast does appear when RT is
  re-toggled but not when parameters change after a prior silent
  drop, so a user who misses it is left with a HUD showing stale
  compliance text (e.g. "S_ab limits do not apply below 6 GHz" at
  f=10 GHz because the last real compute was at 5.8 GHz). Confident
  the rest of Analysis is healthy; Path insights remains unverified
  and should be the first target on a run where OSM cooperates.

### 2026-04-20 16:15 UTC -- "Visualization and analysis"

- Actor: interactive (qa-agent-977949)
- Depth: medium
- Findings: none filed
- Notes: Initially picked this area for PR #712 (Surface path
  contributions to the viewer Analysis panel, commit 4428201) but prod
  is still at `0.30.0.dev59+g8bd6962` per `/api/health`, which
  predates #712 — so the new `PathInsightsSection` between SAB
  histogram and Power sweep is not yet deployed. Source
  (`aegis-web/src/components/panels/analysis/AnalysisPanel.tsx:45`)
  has it wired; grepped bundle behaviour matches source, the gap is
  strictly deploy-lag. Worth a re-pass once the new build ships.
  Pivoted to a regression sweep on the deployed AnalysisPanel tree.
  On Urban Ghent (Thelonious, 28 GHz, Fresnel only): Exposure
  distribution populated (Illuminated 44.1% / 10,509 of 23,826,
  area 3723.5 cm², Peak 7.9e-3 matches HUD 7.80 mW/m², P99 7.1e-3,
  P95 5.6e-3, Mean_all 1.2e-3). SAB histogram renders log bins from
  1.1e-10 up to 3.8e-4 W/m², all-green (below-limit) legend, no red
  bars — consistent with +34 dB peak margin. Power sweep returns
  Max compliant 72.0 dBm; HUD shows Max TX 75.0 dBm (single-check
  peak), difference is the spatial-4cm² vs raw-peak check (same
  pattern called out in prior Power-sweep QA entries, not a bug).
  Chart x-range stops at 63 dBm though, so the 72 dBm crossing is
  off-chart — slightly confusing but the numeric readout is correct.
  Distance sweep clean: current 12.7 m / min compliant 0.3 m, curve
  monotonic, 0 dB crossing at ~0.3 m. Compliance heatmap (2D, freq x
  TX power) came back entirely green as expected for an all-compliant
  parameter window; boundary line not shown (no red cells to bound).
  Frequency sweep curve is nearly flat around +29 dB; I initially
  flagged the +32 HUD vs +29 sweep gap, but the backend
  `/api/compliance/frequency-sweep` (analysis.py:353) holds the
  exposure fixed and varies only the ICNIRP denominator, so "current
  multi-check margin" vs "single-quantity sweep" diverge by design.
  Close-range mmWave (60 GHz, Sab(1cm²) 0.22/40 = +22.6 dB, Margin
  +18 dB, Max TX 61 dBm): distribution matches HUD (Peak 0.221, P99
  0.199, Mean_ill 0.071); frequency sweep is a flat +18 dB line
  7-100 GHz (same reason as Urban Ghent case). Placed a second
  antenna via pointer events at (1200, 500): Illuminated went 43.0%
  → 46.2%, Max TX 61→59 dBm, Margin +18→+16 dB. Peak readout went
  0.221 → 0.220 which is technically non-monotone under incoherent
  superposition — within single-digit ULP of the 3-digit display, so
  I'm attributing it to rounding rather than a compute bug, but
  worth a second look if anyone sees a clearer case. ColorLegend
  Lin↔dB toggle clean (0, -5, -10, -15, -20 dB floor with -20
  spinbox clamp, body recolors). Console reported 4 errors / 9
  warnings across the session — all from Sentry/ResizeObserver
  noise, nothing actionable. Confident the deployed AnalysisPanel
  surface is healthy; flag for next swarm: re-run path-insights
  specifically once the prod bundle advances past 4428201.

### 2026-04-20 13:45 UTC -- "Exposure operator and ECBF"

- Actor: interactive (qa-agent-935398)
- Depth: medium
- Findings: none filed
- Notes: Picked this section because it is absent from recent log entries
  and PR #706 (Surface ECBF infeasibility warnings in compute stats)
  landed 2026-04-19 so the warning capture path is worth exercising.
  Read the source first: `src/aegis/viewer/compute.py` captures
  `warnings.catch_warnings(record=True)` around `_run_engine_compute`
  and `collect_ecbf_warnings` filters on markers `("ECBF",
  "absorption", "infeasible")`, attaching `extra["ecbf_warnings"]` on
  level-8 single-user paths for `/api/compute{,-rt,-sionna-rt,-voxel-rt}`
  and `/api/optimize`. Verified `zf_exposure` precoder (`mimo/precoders.py:88`)
  does per-column scaling and never calls `solve_ecbf`, so PR #706's
  warning path does not apply to multi-user MIMO (by design --
  `P_abs_max=DEFAULT_P_ABS_MAX` is enforced differently). Grepped
  `aegis-web/src/` for `ecbf_warnings` at test time: zero matches on
  the 61da99c base I was running against -- feature was backend-only
  then. PR #713 (dde6f56) landed mid-session and now plumbs MIMO ECBF
  warnings into the HUD via `useMIMODosimetry` +
  `DosimetryStats.ecbf_warnings`, so the frontend gap is already
  closed on master -- a follow-up pass should force ECBF infeasibility
  (very high K / very low P_abs_max) and confirm the HUD surfaces the
  three `solve_ecbf` fallback messages end-to-end.
  Browser pass on prod: MIMO panel with Thelonious + Duke, 28 GHz,
  cycled MRT / ZF / ZF+Exp / MMSE. User 2 Sab values: MRT 77.99,
  ZF 69.61, ZF+Exp 69.61 (matches ZF since channels were
  well-separated and ECBF had nothing to further minimize), MMSE 81.74
  mW/m² -- all physically consistent. Pushed to 7 users / ZF+Exp:
  backend started returning 502 and the prod site went fully
  unreachable for at least 90s (curl timed out after I stopped
  testing). Borderline -- similar pattern to #699 for stochastic
  compute hangs but requires stacking an unusually high user count.
  Did NOT file: can't re-test now (site still down at close), and a
  single 7-user request on a 16-element UPA is an atypical extreme.
  Worth revisiting once the server recovers to see whether the real
  bug is "no per-request time budget" vs "ZF+Exp blows up at K near
  M_ant". Should come back to re-confirm and stress MRT/MMSE/ZF at
  K=7 to isolate which precoder triggered the hang.

### 2026-04-20 12:40 UTC -- "3D environment reconstruction"

- Actor: interactive (qa-agent-886474)
- Depth: medium
- Findings: 1 bug filed: #708
- Notes: Confirmed Overpass API is in full outage -- every POST to
  `/api/environment/osm` returned 504 "Overpass query timed out" in
  under 700ms regardless of location (Paris, Ghent, mid-Atlantic,
  Antarctica). Treated as a known upstream tradeoff, not filed.
  Rotated to OSM-free env sources: Sionna Simple Street Canyon preset
  loaded cleanly, Voxels showed the expected empty state, 3D Tiles
  panel accepted a Google tileset key but rendered no visible tiles
  and lacks a reload-on-pan trigger (shaky but not clearly broken).
  SRTM terrain fetched a ~31m range for Ghent. Verified prior fixes
  live on prod: #635 (Data Quality green bars) and #671 (basestation
  store reset on scenario load). Filed #708 for an Environment panel
  state-sync bug -- the Location textbox (`locationQuery`) stays
  stale after clicking a city quick-link; issue body also flags a
  related regression where Reload Around Camera overwrites
  `locationFormatted` with a coord pair (stores/environment.ts:211).
  Overlaps with the earlier 08:15 UTC pass by qa-agent-812294 which
  flagged the same quick-link stale-input glitch as "minor, not
  filed" -- this session escalated to an issue after reading the
  source. Should come back to 3D Tiles + OSM once Overpass is healthy.

### 2026-04-20 10:30 UTC -- "Fidelity levels (0-8)"

- Actor: interactive (qa-agent-831898)
- Depth: thorough
- Findings: none filed (one minor API-hardening observation worth a follow-up, no UI bug)
- Notes: Picked this section because it had never appeared in the log
  and the underlying kernels are the dosimetry core. Cycled through
  L0-L6 by toggling Computation mode and Physics corrections on
  open_ground (thelonious, 28 GHz, 65 dBm). Per-level peak Sab in HUD:
  L0 Bound 20.25 mW/m² (+29.9 dB margin), L1 Aggregate 5.06 mW/m²
  (+36.0), L2 Spatial 80.46 (+22.1), L3 +F 80.46 (identical at face-on
  triangle as expected), L4 +FP 80.81, L5 +FPC 83.78 (colorbar max
  jumped to 0.179), L6 +FPCD 83.78 (colorbar max DECREASED to 0.166 --
  GELU smoothing on diffraction). Header badge "Spatial +FPCD"
  cascades correctly. Curvature checkbox is disabled-but-checked when
  Diffraction is enabled (auto-required for L6); becomes user-toggleable
  again when Diffraction is off. Sensible UX, not a bug. L7/L8 via
  MIMO panel: enabling MIMO with 1 user (Thelonious) gave Sab 0.22
  W/m² for ZF and ZF+Exp (identical -- physically expected since ECBF
  reduces to trivial single-user case). Added Duke as User 2; ZF and
  ZF+Exp still gave identical 0.11 / 69.61 mW/m² (well-separated
  channels nullified perfectly by ZF leaving nothing for ECBF to
  further minimize). MRT differed: 0.11 / 77.99 mW/m² for User 2
  (12% higher than ZF, expected since MRT does not null inter-user
  interference). API edge tests on `/api/compute`: invalid mode values
  (`"badmode"`, `null`, numeric `42`, missing `interactive` block) all
  return 200 OK and silently coerce to spatial level 2; non-physical
  frequencies (0, -1e9, the string `"not_a_number"`) also return 200
  OK. Frontend dropdowns gate this on the happy path so users never
  hit it, but the route would benefit from a 400 on unknown mode and
  a finite/positive guard on frequency_hz, matching the recent #698
  hardening for stochastic-channel inputs. Confident the level surface
  itself is healthy across the full 0-8 range.

### 2026-04-20 08:15 UTC -- "3D environment reconstruction"

- Actor: interactive (qa-agent-812294)
- Depth: medium
- Findings: none filed (OSM 504 is a documented known tradeoff;
  minor preset/input desync not filed)
- Notes: Picked this section because last pass was 2026-04-17
  (3 days stale) and recent commits all touch it: #651 OSM mesh
  frustum culling, #620 10x10m shadow-frustum artifact, #605
  capabilities refresh after env fetch, #609 hide LSP heatmap.
  Prod build is commit `257f03b` (4 commits behind master).
  **Urban Ghent scenario broken on prod**: loading the "Urban
  Ghent" tile from the Scenarios landing page results in zero
  buildings rendered. `/api/environment/osm` consistently returns
  **504 gateway timeout** (confirmed 14+ identical console errors
  over ~5 min). Tested at radius 200m and 50m, location Ghent and
  Leuven; same 504 each time. The frontend surfaces "Overpass query
  timed out. Try a smaller radius or try again later." in the
  Environment panel but the top-level scenario title still proudly
  claims "28 GHz outdoor with OpenStreetMap buildings." Hit Overpass
  (overpass-api.de) directly with an equivalent query: responded
  HTTP 200 in 1.58s, so the upstream service is healthy — the 504
  is coming from our backend. Per `not-bugs.md` this is covered by
  "Overpass API timeouts on large radii (external service, we
  retry)", so I did NOT file a new issue, but calling out that
  50m is not "large" and the direct Overpass call is fast — the
  tradeoff label may be masking a real backend-side regression
  (gunicorn worker timeout, geocoding step, mirror selection?).
  Might deserve an infra pass next time someone touches
  `/api/environment/osm`. **Voxels source**: panel says "No voxels
  loaded. Go to Scene > Location to load…" — the Scene and
  Environment panels both have their own Location input, so the
  instruction text is slightly ambiguous. Not filed. **Sionna scene
  load (Box)**: dropdown + Load scene worked cleanly, scene walls
  rendered in canvas, compute time flipped 692→1400 ms then back to
  542 ms on further actions. Peak Sab unchanged at 7.80 mW/m² as
  expected (Spatial +F is direct-path; walls don't block without
  RT/diffraction). **Quick-location presets (Ghent/NY/Paris/Tokyo)**:
  clicking Paris preset updated the active geocode label to "Paris
  (48.8566, 2.3522)" and switched Source to OSM, but the Location
  **text input retained its stale "Leuven, Belgium"** value from the
  previous manual search. Real state uses the label, but any user
  reading the input would be confused. Minor UX glitch, not filed.
  **Terrain fetch**: SRTM1 tile download worked ("SRTM elevation
  loaded (32 m range)"), Show terrain auto-checked. Terrain mesh
  not visually obvious in canvas because active location was Paris
  while camera was centered on phantom origin. Not a bug. **3D Tiles
  source**: panel renders Location/Radius/Export but has no visible
  Load button — unclear whether Google Photorealistic tiles require
  a separate auth step on prod or the control is missing. Did not
  file; would want to check whether a Google API key is configured
  in prod env. **Layers panel**: shows four entries (Body mesh,
  Ground plane, Grid disabled, Compliance ring) and toggles Ground
  plane visibility cleanly. Terrain/OSM layers do NOT appear in the
  Layers panel after loading — not clear if by design. Overall:
  the parts of the env-reconstruction surface that don't depend on
  Overpass (Sionna scene load, SRTM terrain fetch, Layers toggles,
  geocoding) are healthy; the OSM ingest path is effectively broken
  on prod and has been for some time.

### 2026-04-20 06:20 UTC -- "Stochastic channel modeling"

- Actor: interactive (qa-agent-791456)
- Depth: medium
- Findings: 1 bug filed: #700
- Notes: Cold area in the log (last direct entry was the 2026-04-19
  tissue pass that rotated off stochastic). Drove the Source ->
  Exposure -> Stochastic panel end to end on Open ground (28 GHz,
  65 dBm, thelonious, antenna at [3,0,1.5]). Enable stochastic
  checkbox flips path source to stochastic, cluster rays + LSP
  heatmap viz render (FBS/LBS colored spheres around the phantom,
  SF_dB Shadow fading heatmap on ground). Peak Sab swung cleanly
  across presets and seeds: synthetic LOS baseline 80.46 mW/m² ->
  3GPP_38.901_UMi_LOS 57.33 mW/m² (multipath fading lowers peak) ->
  UMi_NLOS 39.75 mW/m² (no strong LOS), seed randomization bumped
  UMi_LOS to 49.51 mW/m². Family dropdown -> Canonical/Freespace
  gave 53.55 mW/m² (+23.8 dB PASS). Subpath/Clusters radio toggle
  swaps ~12 cluster lines for ~240 subpath lines (12 clusters × 20
  subpaths). /api/channel-presets returned 91 presets. **#664 fix
  confirmed deployed**: NumClusters=0 -> 400 "must be >= 1, got 0",
  NumSubPaths=0 -> 400 "must be >= 1, got 0", NumClusters=-5 -> 400
  "must be >= 1, got -5". **#697 fix also deployed**: NumClusters=10000
  -> 400 "must be <= 50" (upper-bound cap at the API boundary now
  matches the frontend input spinner limit). Invalid preset -> 400
  "Unknown stochastic preset", non-int seed -> 400 "seed must be
  integer", stochastic_overrides as string -> 400 "must be an object",
  string NumClusters -> 400 "must be a number", NaN/Infinity
  NumClusters/KF_mu -> 400 "must be a finite number". Fractional
  NumClusters=1.7 silently coerces to int(1.7)=1 and returns 200
  (acceptable: Python int() semantics, not bug-worthy). **Bug 1
  (#700)**: `/api/lsp-heatmap` has no finite-value validation on its
  numeric inputs. `bounds=[NaN,50,-50,50]` -> 200 with NaN-laden
  `data[][]`, `bounds=[-Infinity,...]` -> 200 with same, `freq_ghz=NaN`
  -> 200 OK, `antenna_pos=[Infinity,0,10]` -> 200 OK. Same class as
  #668 (tissue spectrum) and #697 (stochastic_overrides float NaN) but
  `_lsp_heatmap_impl` in routes/compute/misc.py:55-93 only wraps
  `float()`/`int()` in a `ValueError`/`TypeError` try block, and
  `float('NaN')` / `float('inf')` are both legal. Suggested a
  `math.isfinite` guard mirroring the tissue-spectrum fix pattern.
  Noted but not filed: (a) `lsp_name="nonsense"` returns 400
  `{"error":"'nonsense'"}` — bare KeyError repr, poor UX but not
  misleading; (b) invalid preset error leaks `/app/data/channel_presets/`
  filesystem path in the 400 message — minor info leak; (c) switching
  the Standard dropdown (family) resets the Scenario to the first
  entry of the new family (e.g. 3GPP 38.901 lands on InF LOS rather
  than preserving UMi LOS) — intentional per StochasticPanel.tsx:128.
  Confident the stochastic channel surface is healthy at the compute
  boundary post-#664/#694/#697; the LSP heatmap boundary is the only
  remaining open finite-value gap.

### 2026-04-20 02:20 UTC -- "Stochastic channel modeling"

- Actor: interactive (qa-agent-755370)
- Depth: medium
- Findings: 2 bugs filed: #691, #692
- Notes: Picked this section because the 2026-04-19 12:15 agent rerouted
  to Tissue (a thorough pass on Stochastic had been logged on a branch
  at 10:18 but never landed on master), so it stayed cold in the log;
  and #664 (Reject zero NumClusters/NumSubPaths) is fresh on this
  surface. **#664 verified live on prod** (build marker `3868e47`):
  `NumClusters=0` → 400 `"NumClusters must be >= 1, got 0"`,
  `NumSubPaths=0` → 400 same shape, `NumClusters=-5` → 400.
  **UI surface healthy**: Enable stochastic checkbox → cluster spheres
  + sub-paths render, Peak Sab rises from single-antenna ~0.08 W/m² to
  ~4.5 W/m² (12-cluster UMi LOS). Standard dropdown cycles cleanly
  across all 11 families (Canonical, 3GPP 38.901 / 37.885 / 3D,
  QuaDRiGa, WINNER, mmMAGIC, 5G-ALLSTAR, MIMOSA, BERLIN, DRESDEN) and
  each re-loads Scenario options (QuaDRiGa → Industrial LOS / NTN-*
  etc., Canonical → Freespace/LOSonly/TwoRayGR/Null). Seed refresh (↻)
  produces a visibly different cluster arrangement and Peak Sab value
  (42 → 1409870198 shifted peak 4.52 → 4.12 W/m²). K-factor override
  to 30 dB visually collapses power to the LOS cluster as expected.
  "Reset to preset defaults" drops the override back. Cluster-detail
  radio (Clusters / All sub-paths) renders the sub-ray fan correctly.
  LSP heatmap cycles through all 8 parameters (SF, KF, DS, ASA, ASD,
  ESA, ESD, XPR) without errors or NaN ticks. Scenario switch
  (open_ground → mmwave_close) preserved the stochastic state cleanly
  — note that #671 (Reset basestations/MIMO/optim stores on scenario
  load) deliberately did NOT include stochastic state in its reset
  list, which is defensible as user-preference persistence rather
  than per-scenario. **Bug 1 (#691)**: drove `/api/compute` with
  stochastic boundary payloads and found the API-boundary guard gap:
  `stochastic_overrides.NumClusters=null` → 500 `int() argument must
  be a string...`, `stochastic_overrides.NumSubPaths=null` → 500 same,
  `stochastic_overrides="foo"` → 500 `'str' object is not a mapping`.
  Mirrors #592/#667 pattern — NaN/null/non-dict at viewer API should
  400 not 500. Each such 500 creates a new Sentry event on prod.
  **Bug 2 (#692)**: preset name isn't whitelisted, and
  `Path(preset_dir) / "/etc/host"` collapses to `/etc/host.conf`
  (pathlib absolute-right wins), which exists on Linux, so the
  endpoint returns 200 after `parse_conf` silently ignores every
  non-QuaDRiGa line. Contents don't leak (parse_conf is a strict
  whitelist), but file *existence* does — an auth'd user can
  enumerate `.conf` files on the filesystem. Error message also
  leaks the deployment root `/app/data/channel_presets/`. Session-
  gated so not externally exploitable, but worth a whitelist.
  **Noted but not filed**: (a) `NumClusters=999` and `=500` both
  return 502 after ~6-12 s (gateway timeout — no server-side upper
  bound, frontend clamps to 50 but API users aren't clamped); the
  worker recovers since Caddy times out first, so nothing like the
  #658 20-min outage, but another soft-DoS seam. (b) `NumClusters=1.5`
  (float) is silently truncated to 1 by `int()` while strings 400 —
  inconsistent validation. (c) `NumClusters=true` (bool) is accepted
  as 1. (d) KF_mu=NaN passes through entirely and produces Sab floats
  back (status 200) — AS_A_mu=NaN hits a downstream `k_hat must be
  finite` check and 400s, so LSP overrides have inconsistent NaN
  handling. (e) The XPR LSP heatmap scale showed a very wide spread
  on one seed (values that read as high-hundreds near the top tick on
  a low-res screenshot) — couldn't reproduce cleanly and may be a
  label I misread on the small screenshot, not filed.
  Confident the Stochastic surface is healthy for the currently-
  exposed UI controls on production; the two filed bugs are
  backend-API-boundary gaps, not user-visible in the frontend.

### 2026-04-20 00:25 UTC -- "Stochastic channel modeling (third pass)"

- Actor: interactive (qa-agent-729030)
- Depth: medium
- Findings: none filed (re-reproduced #664 and #673 on prod;
  both already fixed on master, awaiting deploy)
- Notes: Picked Stochastic before pulling origin/master, so I
  missed the two prior same-day passes (16:15 + 18:25 UTC). The
  three issues I observed during my session were all already
  filed and patched: (a) `/api/compute` 500 with "index 0 out of
  bounds for axis 0 with size 0" when `stochastic_overrides:
  {NumClusters: 0}` reaches backend — fix #664 (f579093), in
  master; (b) Canonical Null preset producing identical Sab
  (1.35 mW/m² at 28 GHz, antenna 4 m, 65 dBm) to Freespace —
  fix #674 (27e6156, "Implement constant path loss model"), in
  master; (c) negative seed → 400 from `/api/lsp-heatmap` and
  `/api/compute` (typed -100 in Seed spinner via React-aware JS,
  visual desync between input and store but no toast surfaced) —
  fix #685 (81dc3dd, "Reject negative seeds on /api/lsp-heatmap"),
  in master. Production is at `7bdd91a` so all three reproduce
  there. Verified working surface end-to-end on Open ground
  scenario, 28 GHz, seed=42: Standard dropdown loads 11 families
  (Canonical → DRESDEN), family change auto-picks first scenario
  alphabetically + clears overrides per `handleFamilyChange`.
  Cycled through Canonical Freespace/LOSonly/Null/TwoRayGR
  (1.34-1.35 mW/m² band — Null bug noted above), 3GPP 38.901
  UMi LOS (7.34 mW/m² at seed 42, 0.31 at random reroll —
  determinism + variance both work), QuaDRiGa Industrial LOS
  (0.95 mW/m²), WINNER Indoor A1 LOS (0.60 mW/m²), BERLIN
  (0.42 mW/m²) — each family produces distinct, sensible values.
  Seed reroll (↻) generates fresh 31-bit ints. Reset to preset
  defaults clears overrides cleanly. K-factor / AS / ES override
  inputs accept values in spec ranges. Cluster ray viz: FBS/LBS
  toggle hides/shows scattered spheres correctly; Clusters vs
  All sub-paths radio swaps between 12 cluster markers and ~12×20
  sub-path dashed rays. LSP heatmap: switched parameter dropdown
  through Shadow fading → Rician K-factor → Delay spread, ground
  recolors live with appropriate colorbar units (sigma_SF dB,
  K dB, log(s) for DS). API `/api/lsp-heatmap` POST returns
  matching grid data (e.g. DS preset UMi LOS: ~10ns range).
  **Caveat for next agent**: when a user types a value below
  min into a number input in this panel, React state stays at
  the prior valid value but the DOM input visually shows the
  bad value (StochasticPanel.tsx:184-196 — onChange only calls
  setOverride when `Number.isInteger(n) && n >= 1`). Annoying
  UX but not a bug since the compute uses the (correct) state
  value, not the visible one. Confidence high once #664/#674/
  #685 ship; no untested gaps remain on the panel surface.

### 2026-04-19 20:20 UTC -- "3D environment reconstruction"

- Actor: interactive (qa-agent-692132)
- Depth: medium
- Findings: none filed (OSM 500 already captured by Sentry #678;
  3D Tiles silent non-render is an unresolved follow-up from
  2026-04-17 that PR #651 claimed "defensive fix" but only for OSM)
- Notes: Picked this section because last direct pass was 2026-04-17
  (2+ days stale) with two unresolved items (3D Tiles silent load,
  Sab 7.80 → 7.00 after Clear Scene) and PR #651 (frustum culling
  on urban scenarios) touched EnvironmentOSM bounding sphere logic.
  **OSM regressed**: `POST /api/environment/osm` returns 500
  consistently for Ghent (51.0447, 3.7268), Times Square (40.7580,
  -73.9855), and Paris (48.8566, 2.3522) at radii 50-200m. Backend
  catches OverpassRateLimit/Timeout/TooLarge specifically but lets
  other exceptions propagate as generic 500 — panel shows only
  "HTTP 500" to the user. Sentry auto-filed this as #678 during my
  session so no new issue opened; root cause is likely an Overpass
  response format change or a downstream parser raising before the
  caught error set is hit. PR #651 was about bounding sphere init,
  not the network path, so the fix wouldn't address this. Earlier
  sessions (2026-04-17, 2026-04-19 04:20) saw 504 (upstream
  timeout, known tradeoff) — today it's 500, which is different
  and worth rechecking after the current Sentry spike clears.
  **3D Tiles silent load reproduces**: switched Source to 3D Tiles,
  geocoded Times Square (200 from /api/geocode), backend fetched
  tiles successfully (`POST /api/environment/3dtiles` → 200, 29,233
  bytes, meta `n_vertices:559, n_triangles:901, source:3dtiles,
  origin 40.758,-73.9855`). Nothing visible in the 3D canvas in
  either phantom or globe camera modes; Layers panel still lists
  only Body/Ground/Compliance with no 3D Tiles entry. Reading
  `aegis-web/src/stores/environment.ts:319` confirms 3dtiles mesh
  is written into the same `osmMeshData` store slot that drives
  `<EnvironmentOSM>` at `SceneRoot.tsx:417`, so the render path
  exists — but something downstream (possibly the expanded
  non-indexed positions being far from scene origin for 3D Tiles
  specifically, or the material-index colors being (0,0,0) for the
  color values Google tiles use) silently yields an invisible
  mesh. Didn't file: not confident enough to call it clearly
  broken vs. my view simply misaligned, and earlier #649 was
  closed as QA harness false-negative. Worth a targeted followup
  with WebGL draw inspection. **Sionna scene healthy**: Simple
  Street Canyon loaded in ~1.5s, visible terrain around phantom,
  Sab 7.80 mW/m² unchanged pre/post load. Clear Scene removed the
  geometry cleanly, Sab dropped 7.80 → 7.00 mW/m² and stuck there
  (same observation as 2026-04-17; still unclear whether this is
  ground-material reset or compliance ring radius change, didn't
  file). **Voxels source**: empty-state message "No voxels loaded.
  Go to Scene > Location to load a location and generate voxel
  data." is clear and helpful (good contrast vs. silent 3D Tiles
  failure). Load button triggered /api/scene/load (200), /api/
  voxels (200), and 5× /api/compute — background work is clearly
  happening. **UX note (not filed)**: clicking the Paris quick-load
  chip correctly sets Location coords to (48.8566, 2.3522) but
  leaves the text input displaying the previous "Times Square,
  New York" string, so re-submitting the search would overwrite
  Paris with a re-geocode of NY. Minor, requires specific action
  sequence. **Playwright instability**: after the voxel Load click
  every subsequent `npx @playwright/cli screenshot` timed out with
  "waiting for fonts to load... fonts loaded" — cold re-open of
  the browser did not recover, so testing had to wrap. Could be a
  font-observer loop triggered by the voxel panel; flag for
  interactive repro. Confident Sionna + Voxels UI + guidance text
  are healthy; OSM backend is failing (Sentry has it); 3D Tiles
  silent non-render is still open and deserves a deeper dive.

### 2026-04-19 18:25 UTC -- "Stochastic channel modeling (follow-up to 16:15)"

- Actor: interactive (qa-agent-661066)
- Depth: medium
- Findings: 1 bug filed and auto-fixed: #673 (→ PR #674 merged
  10 min after filing). #664 re-reproduced on production as
  sanity check.
- Notes: Section collision with the 16:15 UTC session — I picked
  Stochastic before seeing the 16:15 entry (the other agent's
  commit was on master but not yet in my local worktree; rebased
  mid-session). Kept going because the 16:15 entry flagged
  Null's peak at 53.55 mW/m² as "by design" and that conclusion
  felt off. It was. Drove the Null preset at 28 GHz (53.55
  mW/m², margin +23.9 dB) and 10 GHz (48.84 mW/m², margin +22.9
  dB), identical to Freespace to the mW/m² — a `PL_model=constant`
  with `PL_A=1000` should kill the channel by 1000 dB, not leak
  full FSPL. Root cause in `src/aegis/channel/path_loss.py:31-33`:
  `compute_path_loss` dispatches on `logdist` / `dual_slope` /
  `nlos` only; anything else falls through an `else` branch that
  logs a warning and returns `_fspl(d3d, freq_ghz)`. Null.conf
  declares `PL_model = constant` explicitly ("effectively disables
  the channel"), and all 8 MIMOSA presets use the same (`PL_A=95`),
  so that's 9 presets silently broken. Filed #673 at 18:14 UTC,
  PR #674 (`Implement constant path loss model`) auto-merged at
  18:24 UTC — adds `_constant(params)` returning `PL_A` and a
  regression test. The 16:15 agent's "backbone geometric LOS
  remains" trace was wrong: the LOS component itself carries the
  PL_model attenuation; FSPL fallback is what was keeping it
  visible. Takeaway for future agents: when a preset is labeled
  "effectively disables the channel" and the compute still
  returns FSPL-like numbers, check `compute_path_loss` dispatch
  before accepting "by design". **#664 sanity check**: typed `0`
  into Clusters on prod (`7bdd91a`), hooked fetch to capture the
  `/api/compute` payload — `stochastic_overrides:
  {"NumClusters": 0}` lands at the backend and 500s with
  "index 0 is out of bounds for axis 0 with size 0", exactly as
  the 16:15 log says. Both frontend (StochasticPanel.tsx:187) and
  backend fixes are on master, deploy lag is the only reason it
  still reproduces. Not re-filed. No other new findings on the
  stochastic surface; confidence is high once #674 ships and the
  9 constant-PL presets start behaving like their comments say.

### 2026-04-19 16:15 UTC -- "Stochastic channel modeling"

- Actor: interactive (qa-agent-620927)
- Depth: medium
- Findings: none filed (#664 regression reproducible on production
  but fix already merged on master, awaiting deploy)
- Notes: Picked this section because it was absent from the last 20
  coverage entries and commit #664 (reject zero NumClusters/
  NumSubPaths) landed fresh 6h ago. Production is at commit
  `7bdd91a` (PR #662), which is BEHIND master — so #657, #659,
  #660, #661, #664, #665, #668, #669, #670 are all merged but not
  yet deployed. Enabled stochastic channel on Open ground (28 GHz,
  65 dBm, antenna at 4 m). Baseline synthetic peak was 80.46 mW/m²
  (+23.9 dB Sab margin). Swept all families/scenarios end-to-end:
  **Canonical**: Freespace, TwoRayGR, Null, LOSonly all load and
  compute. Null (PL_A=1000 dB) still yields peak 53.55 mW/m² with
  K_mu=0 override — this looks suspicious at first glance but on
  tracing `_generate_stochastic_paths` in `compute.py:489` the peak
  still reflects the LOS-component direct path (Null zeroes the
  scatterer paths but the backbone geometric LOS remains). Not a
  bug, documented design. **3GPP 38.901**: cycled InF LOS → UMa
  NLOS. UMa NLOS peak 0.26 W/m² (margin +13.0 dB), InF LOS
  +15.2 dB — scenario truly changes the physics, not just labels.
  Note: UMa NLOS preset correctly exposes KF_mu=-100 dB (effectively
  no LOS) to the UI, which renders in the K-factor spinbutton.
  **QuaDRiGa**: Industrial LOS loaded with K=7.8, AS=49°, ES=44°,
  NumClusters=25 — peak 58.15 mW/m² at seed 1661939735, 36.11
  mW/m² at seed 42 — seed determinism works. **#664 repro
  confirmed on prod**: typed 0 into the Clusters field, browser
  echoes "0" in DOM but the `n >= 1` guard in StochasticPanel.tsx
  isn't in the deployed build yet, so `/api/compute` returned
  500 with "index 0 is out of bounds for axis 0 with size 0".
  Sentry captured. Backend-side validation (also in #664) matches.
  Not filed — fix is already merged and awaiting deploy.
  **Seed reroll** button (↻) generates a fresh 31-bit integer,
  peak + margin respond as expected. **Reset to preset defaults**
  clears overrides but leaves the seed field untouched (by design
  per the panel code — seed is a separate store field). **Viz
  toggles**: cluster rays FBS/LBS checkbox hides/shows correctly,
  Clusters vs All sub-paths radios switch between 25 cluster
  markers and 25×20=500 sub-path rays cleanly. LSP heatmap: all
  8 LSP parameters (Shadow fading / Rician K-factor / Delay spread
  / 4 angle spreads / Cross-polarization ratio) render a coloured
  ground plane with appropriate legend units ("K (dB)", "lgs DS",
  "σψ (dB)" etc). For NLOS scenarios where KF_sigma=0, the K-factor
  heatmap renders as a near-uniform plane — correct. **K-factor
  override**: setting KF_mu from preset (7.8) to override 30 dB
  produced only ~10% peak change (58.15 → 65.79 mW/m²). This is
  physically defensible (LOS component dominates regardless of
  K-factor in a 4 m scene with no scatterers on the direct path),
  but worth a targeted follow-up by someone who knows the ECBF /
  cluster-power scaling intent. The K-factor input has NO guard
  at all in the component (unlike NumClusters/NumSubPaths which
  got `n >= 1` in #664) — typing `1e9` into K-factor likely
  degenerates silently; noted but not filed because it's a
  physics exploration, not a user-facing UX break. Confident the
  stochastic channel surface is healthy on master; once #664
  ships to prod, the only remaining gap worth a look is the
  K-factor / AS / ES override response magnitudes in NLOS
  scenarios and whether the silent minus-sign parsing on the
  K-factor field is intentional.
### 2026-04-19 14:25 UTC -- "Web viewer frontend (UI/UX)"

- Actor: interactive (qa-agent-593255)
- Depth: medium
- Findings: none (1 pre-existing bug reproduced but already fixed
  on master, not yet deployed)
- Notes: Picked this section because the last direct UI/UX pass
  was 2026-04-17 (2 days stale) and a cluster of UI-layer PRs had
  landed since then: #665 Delete/Backspace fix, #662 scenario +
  wordmark reset clears antennas, #625 share links include env
  state. Prod deploy was at commit `7bdd91a` (PR #662) during
  testing — 4 commits behind master, so #665 + everything after
  were NOT live yet. **#665 repro confirmed**: on open_ground,
  placed a single antenna via canvas click then pressed Delete.
  Phantom went gray, compliance card + colorbar vanished, and
  the "Click the scene to place an antenna" hint appeared as if
  the scene were empty, but the Antennas panel still showed
  Antenna 1 at its original coords (1.8, 0.0, ~4.0) with the
  antenna pole still rendered in the 3D scene. This is exactly
  the stale-state the d1fc7f1 patch targets (`setAntennaPos(null)`
  clears sim mirror without calling `removeAntenna`). Not filed —
  fix is already merged. **#662 verified healthy**: placed an
  antenna, switched Scenarios dropdown from open_ground to
  mmwave_close; user antenna cleared, Close-range default antenna
  loaded, Peak 0.22 W/m² on Sab(1cm²) basic restriction (correct
  for ≥30 GHz). Wordmark click on the `aegis` logo also resets to
  the landing page and empties the Antennas panel ("No antennas.
  Click below to add one."). **#625 share link round-trip
  verified**: toggled Polarisation + Curvature, placed antenna,
  clicked Share (hooked `navigator.clipboard.writeText` to
  capture the URL since read permission is denied). URL is hash-
  encoded `#s=<compressed payload>` with the scenario name baked
  inside rather than a `?scenario=` query. Navigated to the
  captured URL fresh and got back Peak 0.24 W/m², "Spatial +FPC"
  badge, colorbar max 0.454, antenna at the same spot — clean
  round-trip. **Keyboard shortcuts**: `?` opens the overlay
  (Camera WASD, Antenna click/arrows/Shift+arrows/Del, General
  `?` and `Shift+B`); overlay does close on `esc`, though a single
  early `esc` press immediately after opening appeared to no-op
  (likely a focus race with whatever had focus at the time — not
  reproducible on second try, not filed). Arrow-up nudge (3×)
  moved the antenna away from the body, Peak Sab dropped 0.24 →
  0.04 W/m² and margin climbed +19.2 → +27.3 dB (working).
  **Sidebar toggle + Analysis tab**: Toggle button collapses the
  whole sidebar (Compliance card floats top-left, colorbar right,
  right-edge HUD rail of 7 widget toggles remains); re-toggle
  restores the expanded view. Clicking the Analysis rail button
  (vertical rail on the far left, `World | Source | Exposure |
  Analysis`) opens Analysis / Optimize / Export accordion;
  Optimize shows Placement enabled, Tilt+power and MIMO peak
  greyed out (consistent with the known `Tilt+power gating`
  observation logged 2026-04-18 18:15 — gating is supposed to key
  off RT paths per #566 but currently keys off MIMO-enabled).
  Not re-filed. **Welcome tour**: cleared `aegis-welcome-dismissed`
  in localStorage and clicked the toolbar play button to launch.
  All 9 tour steps advance cleanly (Welcome → Compliance checks →
  ... → Keyboard shortcuts), "Done" on step 9 dismisses the
  overlay with no residual state. One minor asymmetry noted: a
  page reload via `?scenario=open_ground&tour=1` resets the
  antenna to the scenario default (wiping the user-placed antenna
  + any arrow-key nudge) but PRESERVES the Polarisation and
  Curvature toggles from a prior share link, so the "Spatial +FPC"
  badge persists across reload. Defensible as physics-preference
  persistence, just worth flagging in case a future bug report
  ever says "my antenna moved". Not filed. Confident the UI/UX
  surface is healthy on the currently-deployed build; the only
  open concern is the 4-commit deploy lag that is keeping #665,
  #664, #668, #669 off production.

### 2026-04-19 12:15 UTC -- "Tissue and dielectric modeling"

- Actor: interactive (qa-agent-573021)
- Depth: medium
- Findings: 1 bug filed: #667
- Notes: Originally aimed at Stochastic channel modeling because
  commit #664 landed fresh, but a thorough pass on that surface had
  already been logged at 10:18 UTC (agent qa-agent-552296's branch,
  not yet on master), so rotated to the genuinely cold Tissue area.
  Drove the Source -> Skin model dropdown across all 4 options on
  Open ground at 28 GHz: IT'IS v5 baseline (eps_r=16.6, sigma=25.8
  S/m, Peak Sab 80.46 mW/m^2), Christ2021 correctly scales eps_r
  and sigma by 1.2 (19.9, 31.0, Peak 75.59 mW/m^2 -- fix #132
  remains solid), Christ2025 Dermis uses the Debye single-pole
  parameters (20.3, 32.3, Peak 73.92 mW/m^2), NICT measurements
  lowers sigma to 20.1 S/m at 28 GHz giving Peak 84.74 mW/m^2 /
  colorbar max 0.085 W/m^2. Tissue panel under Exposure tab renders
  three synchronised curves (relative permittivity, conductivity,
  T_0) with dot-on-curve at the operating frequency; values update
  live across all 4 models. Frequency sweep across 0.9 GHz and
  100 GHz behaves correctly: at 0.9 GHz compliance correctly
  flips to SAR_wb only (Sab rows drop below 6 GHz), at 100 GHz
  Sab(1 cm^2) appears per ICNIRP 30+ GHz threshold with limit
  40 W/m^2, Peak 0.106 W/m^2, margin +21.4 dB PASS. **Bug 1
  (#667)**: drove `/api/tissue/spectrum` with boundary inputs and
  found `f_min=NaN`, `f_max=NaN`, and `f_max=Infinity` all return
  200 with a NaN-laden payload -- the `f_min <= 0 or f_max <= 0`
  and `f_min >= f_max` guards in `routes/analysis.py:119-136` are
  bypassed because every comparison with NaN yields False. PR #592
  (\"Reject NaN/Inf inputs at viewer API boundaries\") covered
  `_parse_vec3`, `_parse_rotation_y`, and `_parse_freq_and_tissue`
  but not this analysis route. Suggested a `math.isfinite` guard
  mirroring that pattern. Also noted but not filed: (a) `n=0` and
  `n=-5` silently clamp up to 10 via `n = min(max(n, 10), 1000)`,
  arguably intentional but inconsistent with the 400s on f_min /
  f_max; (b) `skin_model=<arbitrary_string>` is echoed back and
  falls through an `else` branch to itis-style eps_r/sigma -- the
  response is numerically safe but the echoed model name is
  meaningless. (c) Tissue panel chart y-axis bottom label reads
  5.80 for IT'IS permittivity while the actual curve minimum at
  100 GHz is ~5.60 per the API; the dot appears at the correct
  position but visually sits just below the bottom gridline -- a
  ~4% label/value discrepancy, cosmetic not filed. Confident all
  four skin models compute and render correctly end-to-end; the
  NaN boundary gap is the only real defect.

### 2026-04-19 06:35 UTC -- "Web viewer backend (API)"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #658
- Notes: Drove the Flask API directly with a session cookie against
  production (commit `f0eead5`). Verified recent fixes hold:
  `freq_hz=1e-320` (subnormal, #657) returns 400 with a clean error
  message; `freq_hz=0`, negative, and `NaN` all reject with 400;
  `power_dbm` bounds [0, 100] are enforced inclusively.
  `/api/body` and `/api/phantom` reject `../` path traversal cleanly.
  `/api/compute` accepts the frontend payload shape (fresnel,
  polarisation, curvature, diffraction booleans -- no `level` field
  is read from the body, that was a red herring while testing).
  `/api/tissue-spectrum` validates `f_min < f_max` and positive `n`.
  **Bug 1 (#658)**: `POST /api/basestations/load` with `{}`
  (empty body) passes every guard in `_load.py:_handle_basestations_load`
  -- `_build_bbox` returns `(None, None)` silently, country defaults
  to "Belgium", region falls through to "brussels", and
  `read_merged_parquet` returns every row when bbox is None. A single
  such request hangs the worker; a handful knocked all of
  `aegis.waves-ugent.be` offline for ~20 minutes during this session
  (TLS handshake failing on port 443, even `/api/health` unreachable).
  Session-gated so not externally exploitable, but trivial for any
  authenticated user. Suggested fix: require at least one of `bbox`,
  `lat+lon+radius_m`, `location`, or explicit `region` at the top of
  the handler and reject empty payloads with 400. Not tested due to
  the outage: `/api/optimize` SSE cancel, `/api/patterns/search`,
  `/api/geocode`. Confident the validated endpoints are healthy; the
  basestations/load gap is the only real defect and should be
  patched before another QA pass on this surface.

### 2026-04-19 04:20 UTC -- "Body geometry and mesh"

- Actor: cron-qa
- Depth: medium
- Findings: 1 bug filed: #655
- Notes: Drove the Phantom panel + spatial averaging on production
  (commit `e0ce22b`, Open ground scenario). Cycled through all 8 entries
  in the Body mesh dropdown: `duke`, `ella`, `eartha`, `thelonious`
  load and compute correctly (Sab values 0.14 - 0.19 W/m² on a 28 GHz /
  60 dBm baseline with antenna at 3 m). The other 4 names
  (`adult_male`, `adult_female`, `boy_6y`, `girl_8y`) all return 404
  from `/api/body?name=...` -- confirmed via curl against the
  authenticated session: only `['duke','eartha','ella','thelonious']`
  appear in `caps.bodies`, and `gltf_bodies` is `[]`. The frontend
  hardcodes a `PHANTOM_ORDER` of 8 in
  `aegis-web/src/components/panels/PhantomPanel.tsx:22-31` and merges
  with backend bodies (line 61), so the dropdown advertises 4 phantoms
  the deployment does not have. **Bug 1 (#655)**: selecting one of the
  missing 4 leaves a tiny bottom-right toast (`Body 'boy_6y' not
  found`), the dropdown stays on the failed selection, the previously
  loaded mesh persists, and heatmap + compliance HUD + color legend
  all silently vanish. Sentry catches the underlying ApiError (issue
  #653 was opened/auto-closed during this very session for boy_6y),
  but the user-visible UX collapse needs a frontend fix. Suggested
  fix in #655: drive the option list from `caps.bodies` only, or
  render the missing 4 as disabled. Regression from #482 which fixed
  "I only see 4 phantom options" by hardcoding all 8. Spatial
  averaging surface verified healthy: clicking Sab(4cm²) "displayed"
  switches the mesh + colorbar to averaged values (0.144 W/m² peak vs
  0.145 unaveraged at 28 GHz -- area-weighted smoothing as expected),
  and at 60 GHz the basic restriction auto-swaps to Sab(1cm²) per
  ICNIRP (peak 0.168 W/m², +23.8 dB margin PASS, limit 40 W/m²).
  Noted but not filed: (a) `gltf_bodies` is empty on production so the
  Pose dropdown (idle/walking/phone_ear_r/phone_ear_l/sitting) and
  animation Play/Pause from features.md are completely unreachable on
  the live deploy -- the conditional `phantomType === 'gltf'` in
  PhantomPanel.tsx never becomes true; (b) `features.md` describes
  Thelonious as "(cat, 17.4 kg)" but the live mesh + PHANTOM_META is
  a 6y boy, 18.6 kg -- internal docs nit, not user-facing; (c) the
  antenna marker switches from a small triangle to a large red
  icosphere as soon as any phantom selection happens (probably a
  pattern-visualization toggle, not investigated). Confident the 4
  available phantoms + spatial averaging are healthy; the missing-4
  silent failure is the only real defect; pose/animation feature
  needs a deployment audit before it can even be tested on prod.

### 2026-04-18 22:10 UTC -- "Base station pipeline"

- Actor: cron-qa
- Depth: medium
- Findings: 1 bug filed: #635
- Notes: Drove the pipeline end-to-end on production (commit `fef2338`).
  Loaded Ghent (2056 antennas, operators 1/2/3/253625150/386900317,
  all `location_only` tier, `freq_mhz=2100` fallback) and a small UK
  set (Heathrow area, 2 antennas, `gov:ofcom_wtr`) via the location
  picker, then inspected the Operator-coloured globe, clicked a few
  pins to verify the per-antenna panel, and ran one compliance-zone
  compute on the Ghent set (~7 s, returned 3.2M zone samples; globe
  rendered the ICNIRP layer without trouble). Verified API directly
  via session cookie: `/api/basestations` returns both
  `provenance_sources` (flat, canonical keys: `Power`, `Azimuth`,
  `CenterHeight`) and `provenance` (nested, API keys: `eirp_dbm`,
  `azimuth_deg`). **Bug 1 (#635)**: the sidebar Data Quality panel
  (`RegionDataCard.tsx:92-101`) and the HUD variant
  (`DataQualityHud.tsx:50-62`) render all nine provenance bars as
  100% gray (missing) for every loaded region, because both files
  look up `bs.provenance_sources[apiField]` (e.g. `eirp_dbm`) but
  `provenance_sources` is keyed by the canonical column name
  (`Power`). PR #457 purported to fix this for the HUD but shipped
  with the same key-direction mistake, so the bug has been live
  since the data-quality UI was introduced. Single-antenna panels
  render provenance correctly (they walk the nested `provenance`
  map with API keys), which masks the regression. Not filed but
  noted: the API-path leak in the "compute-without-basestations"
  toast ("Call /api/basestations/load first") is already fixed on
  master (PR #628, commit `d3113ef`) and merely pending the next
  deploy -- confirmed by reading the diff, no need for a ticket.
  Also noted: Ghent antennas all fall into `location_only` tier
  because Frequency provenance is `missing` (Flanders feed doesn't
  carry per-antenna frequency and we fall back to `freq_mhz=2100`
  without attributing a provenance origin) -- once #635 is fixed
  this will become very visible to users. Confidence the core
  extract/merge/load/compute path is healthy; the fidelity-surfacing
  UI needs another look after #635 lands.

### 2026-04-18 18:15 UTC -- "Optimization"

- Actor: cron-qa
- Depth: medium
- Findings: 1 bug filed: #623
- Notes: Exercised Placement and MIMO peak on the Open ground scenario;
  Tilt+power stayed disabled until MIMO was enabled (worth a separate
  look later -- gating is supposed to key off RT paths per #566, not
  MIMO). Placement grid=5 converged in 25 iters / 68% reduction /
  ~990 ms, replay play+scrub updated heatmap and antenna smoothly,
  5x5 grid preview renders on strategy select. MIMO peak produced 38
  iters / 2% reduction (single-user, mmwave so little room to move
  the precoder). Noticed briefly that after a placement run completes
  the top-level compliance HUD shows the re-run MIMO value (0.23
  W/m^2) while the panel's "Peak S_ab at this position" still
  displays the placement summary (7.84e-4 W/m^2); defensible as
  pipeline order but confusing -- not filed. **Bug #623**: pressing
  Optimize twice without toggling the strategy makes the replay
  scrubber, the "Peak S_ab per iteration" chart, and the Best button
  silently accumulate iterations across runs. Repro: grid=5 (25 it)
  -> grid=1 (1 it) -> grid=3 (9 it) lands at "Converged after 9
  iterations" with replay reading 35/35. Two grid-9 runs back to
  back give 162/162 with two bell curves concatenated on the chart.
  Root cause sits in aegis-web/src/stores/optimize.ts:81-85 --
  onIteration unconditionally appends, and only setMode()/reset()
  clear history. Suggested a beginRun() style fix that clears
  history + currentIter at start of useOptimization.start. Dropping
  history also silently hits the .slice(-200) cap after a few grid-9
  runs which would jumble replays further. Cancellation and
  stop-then-start I could not stress (81-iter runs finished in under
  5 s), would want a longer-running mode for that. Confident Placement
  core + MIMO core are healthy; the replay store bug is the only
  clear defect; the Tilt+power gating change deserves a targeted pass
  next swarm.

### 2026-04-18 16:20 UTC -- "Compliance and regulatory"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #621
- Notes: Drove the compliance HUD across a grid of (frequency, scenario,
  TX power) on the Open ground scenario. Frequency-band transitions look
  correct: at 5.8 GHz the HUD correctly shows only SARwb (Sab rows drop),
  at 28 GHz only Sab(4cm²), and at 39 GHz Sab(1cm²) appears on top. Limits
  verified against backend `/api/compliance/limits`: general public 20
  W/m² Sab(4cm²), occupational 100 W/m² -- 5x scale, and Sab(1cm²) at 39
  GHz occupational = 200 W/m², all per ICNIRP 2020. Occupational toggle at
  5.8 GHz correctly shifted SARwb limit 0.08 → 0.40 W/kg (5x) and Max TX
  75.2 → 82.2 dBm (+7 dB). The Max-TX-click-tips-to-FAIL overshoot I
  tripped early on is already tracked and fixed as #594 (floor rounding
  shipped earlier today). **Bug 1 (#621)**: at realistic low TX
  (e.g. 30 dBm = 1 W) the compliance HUD silently drops the entire
  "Margin / Max TX power / Frequency" summary row. Per-check row still
  renders with the correct margin (+47.1 dB PASS), but the whole
  ComplianceSummary block vanishes because the server rounds `ratio` to 4
  decimals (`routes/compute/_responses.py:206`), so tiny ratios come back
  as 0, and CompliancePanel.tsx:100-103 recomputes `visibleMarginDb` from
  ratio and gets `Infinity` → returns null. Robin already flagged this
  exact rounding seam in a comment on #594 but the summary-hiding symptom
  wasn't fixed at that time. Also noted but not filed: AEGIS
  intentionally evaluates SARwb above 6 GHz (tests in
  `test_compliance.py:50-52` enforce `sar_wb == 0.08` at 28 GHz even
  though ICNIRP 2020 scopes SARwb to ≤6 GHz only); that's a documented
  design choice, not a bug. Also noted: at high-margin states the visible
  per-check row's margin (e.g. +9.1 dB Sab) can differ from the overall
  Margin summary (+7.0 dB) because passing restrictions with ratio > 0
  are hidden from the rendered list but still drive the overall margin --
  defensible UX, could surface the binding restriction label for clarity.
  `/api/compliance/summary` curl test also hit a harmless red herring:
  the empty-cache path returns "Frequency outside ICNIRP 2020 range"
  regardless of the queried freq, but the endpoint is only reachable
  after a compute (the frontend never sees the empty-cache branch), so
  not worth filing. Confident panel is healthy at typical base-station TX
  powers; low-TX regime silently misleads until #621 lands.

### 2026-04-18 12:30 UTC -- "Coherent MIMO and beamforming"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #612
- Notes: Drove the MIMO stack on Open ground. Single-user baseline
  is healthy: enabling MIMO flips header to 1/1 PASS, drops Max TX
  from 65 to 56 dBm (backoff for the 4x4 UPA beam) and lifts peak
  Sab from 80.46 mW/m² (single element) to 0.22 W/m² (MRT, 16
  elements, focused). Array sizing is physically sensible:
  4x4 → 8x8 at same spacing scales peak Sab from 0.22 to 0.87 W/m²
  and shaves ~6 dB off margin (+13.9 → +7.9 dB), Max TX drops
  accordingly. Two-user MIMO (Thelonious + Duke) splits power as
  expected — Thelonious 0.11 W/m², Duke 69.61 mW/m², both marked
  Compliant, compliance margin +16.9 dB PASS. #565 colorbar fix
  verified (fourth independent confirmation): MIMO peak optimizer
  converges (6 iter, -0% on an already-near-optimal scene) and
  ColorLegend renders clean numeric ticks in BOTH linear (0.218,
  0.163, 0.109, 0.054, 0) and dB (0, -6, -13, -19, -25 dB) modes
  — no NaN labels. **Bug (#612)**: adding a 3rd user kicks off a
  MIMO compute that takes 90+ s on the 2-core prod box and
  eventually hits ERR_TIMED_OUT (also got a transient 502 on one
  attempt). The transient toast 'MIMO compute failed: timeout'
  does surface, but: the new user's card is left showing '--'
  with no error state, and the Margin/Max TX/PASS badge in the
  compliance panel keep the stale 2-user numbers with no 'out of
  date' indicator. A user who missed the toast could screenshot
  / export a misleadingly-green compliance snapshot. Didn't
  exercise ZF/MMSE/ZF+Exp precoders under clean (<=2 user) load,
  the 'Show focused heatmap only' toggle, or the AntennaArray
  per-element phase color mode that swarm-tester-5 flagged last
  time — left for a future pass. '-0% reduction' wording when
  MIMO peak makes no progress is cosmetic, not filed. MIMO 1-2
  users on 4x4 is confident healthy; the 3+ user timeout path is
  where UX degrades.

### 2026-04-18 10:25 UTC -- "Coherent MIMO and beamforming"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #608
- Notes: Drove the full MIMO surface on Open ground (28 GHz, thelonious).
  Array sizing scales Sab as expected: 4x4 UPA patch 0.22 W/m^2, 8x8
  patch 0.87 W/m^2 (4x, matches 64/16 element ratio), 2x16 patch 0.44
  W/m^2 (2x). Spacing d_h=1.0 lambda held peak near 0.22 W/m^2 because
  MRT still focuses on the focus point (physics ok, grating lobes don't
  move the peak). Element pattern toggle: Patch 0.22 vs Isotropic 0.23
  W/m^2, ~5% difference consistent with isotropic having no backside
  suppression. Precoder switching with 1 user: MRT/ZF/MMSE/ZF+Exp all
  collapse to 0.22 W/m^2 as expected (single-user MIMO is degenerate).
  With 2 users (thelonious + duke), MRT gave User1 0.11 / User2 0.078
  W/m^2 and ZF was within ~1% of MRT since the users are well-
  separated in channel space. **#566 verified**: Tilt + power button is
  correctly disabled (greyed with tooltip) on non-RT Open ground.
  **#565 verified**: MIMO peak optimizer converged ("Converged after 6
  iterations, -0% reduction" — 1 user patch already optimal), and the
  ColorLegend ticks stayed valid (0 / 0.054 / 0.109 / 0.163 / 0.218
  W/m^2), no NaN. **Bug filed (#608)**: raw internal API path leaks
  into the MIMO peak Optimize toast when the server's `mimo_scene`
  cache is stale — "Optimization error: No MIMO scene cached. Run
  /api/mimo/compute first." Same class of leak as #564/#566; repro is
  the add-then-remove-user stale-cache race, but a server restart or
  session timeout would also trigger it. Noted but not filed: on a
  subsequent attempt the UI state appeared visually deselected
  (no highlighted strategy) while the a11y tree reported MIMO peak
  [active] — mild state-desync on tab switch, recovered on reclick.
  Confident array sizing, spacing, element pattern, precoder
  switching, and both #565/#566 fixes are healthy. Follow-up surfaces
  worth a targeted pass: voxel RT MIMO path, lambda_max QCQP
  saturation regime on ZF+Exp, UPA orientation (only azimuth array
  tried here).

### 2026-04-18 08:22 UTC -- "Visualization and analysis"

- Actor: interactive
- Depth: medium
- Findings: none filed
- Notes: Drove the full analysis/visualization surface on Open ground.
  **#565 verified fixed** (third independent confirmation today): after
  MIMO peak optimizer converges (1/1 user, 28 GHz, converged after 6
  iterations, 0% reduction since MRT was already a peak-minimizer here),
  ColorLegend renders clean ticks in both Lin (0, 0.054, 0.109, 0.163,
  0.218 W/m²) and dB (0, -6, -13, -19, -25 dB) — no NaN, no empty
  strings. ColorLegend controls all healthy: dB/Lin toggle re-renders
  ticks immediately, Floor spinbutton accepts -40 (compresses
  distribution) and -5 (collapses body to floor except hotspots),
  lock colormap (🔒) preserves the 28 GHz 0.081 W/m² scale when
  switching to 60 GHz and unlocking correctly auto-rescales to 0.094
  W/m² peak. Analysis panels: Exposure distribution (Peak 0.205, P99
  0.185, P95 0.145, monotonic, 45% illuminated, 3810 cm²), SAB
  histogram (log-scale bins with below/above-limit color coding),
  Frequency sweep (Recharts ticks 7-100 GHz × -5 to +14 dB margin),
  Power sweep (23-63 dBm × -6 to +34 dB margin), Distance sweep
  (curve rises to +40 dB at 50 m, min compliant 0.3 m), Compliance
  heatmap (green Compliant region with Exceeded/Boundary legend) all
  render valid numbers. Export: Screenshot (PNG) triggered a download,
  file writes correctly; the exported PNG shows only the 3D scene
  (phantom + antenna + distance marker) without HUD/colorbar overlays —
  intentional "clean figure" design, cropped the 2.5 m distance label
  at the top which is cosmetic. Noted but not filed: (a) after
  disabling MIMO without re-computing, the body heatmap remains colored
  from the last MIMO result while the HUD pill drops to 5.00e-7 W/m²
  and compliance flips to N/A — stale heatmap vs. fresh HUD creates an
  inconsistent scene, but clicking to place/move the antenna restores
  fresh compute immediately, so it's a transient stale-state UX quirk
  rather than a silent bug (this may overlap with #567 stale-legend
  mechanics but here it's the heatmap+HUD pair, not the legend);
  (b) two recharts "width(-1) height(-1)" console warnings when
  collapsed sweep panels mount hidden — cosmetic, no visible render
  failure. Console clean otherwise (0 errors apart from expected
  401/api/auth pre-login, WebGL deprecation + GPU stall perf warnings
  are upstream). Visualization area is heavily over-covered today (4
  other sessions already); next agent should rotate to a cold section
  like Tissue, Body geometry, Stochastic channel, or Ray tracing.

### 2026-04-18 06:22 UTC -- "Compliance and regulatory"

- Actor: interactive
- Depth: medium
- Findings: 1 bug filed: #594 (plus follow-up comment)
- Notes: Walked the compliance panel across multiple regimes. Open
  ground scenario: 28 GHz General Public -> Sab(4cm²) only (Sab 1cm²
  disabled, matches ICNIRP 30 GHz threshold). 60 GHz -> Sab(1cm²)
  enables, Sab(4cm²) disables as expected. 1.8 GHz -> only SAR_wb
  check shown, Sab/Sinc limits correctly suppressed below 6 GHz.
  Occupational switch at 60 GHz: limits all scale 5x (Sab 40->200,
  Sinc local 26.65->133.23, Sinc wb 10->50) and Max TX bumps by
  ~6 dB. Per-check margin_db strings and PASS/WARN/FAIL statusing
  look right.
  **Finding (filed as #594)**: Clicking "Max TX power" in the compliance
  summary, and clicking the matching "Set" in Analysis -> Power sweep,
  both use `parseFloat(value.toFixed(1))` which can round **up** past
  the true max compliant power. Repro: Open ground @ 60 GHz, enable
  SAR_wb -> click "Max TX power" -> compliance badge flips from PASS
  to FAIL with SAR_wb `-0.0dB FAIL`. Close-range mmWave @ 60 GHz ->
  Power sweep reports Max compliant 61.2 dBm (compliance panel said
  61.0 dBm for the same dataset!) -> [Set] -> SAR_wb `-0.2dB FAIL`.
  Fix is `Math.floor(x * 10) / 10`. Commented on #594 noting the
  second-order issue that the compliance-panel Max TX and the
  power-sweep Max compliant disagreed by 0.2 dB on the same
  compute, which also suggests the panel uses server-rounded `ratio`
  (4-decimal) while the sweep uses exact floats.
  Other observations worth noting but **not** filed:
  - Summary "Margin" is the min over `compliance.checks` (all server
    checks) while the visible rows are filtered to enabled
    quantities. So with only Sab(4cm²) enabled at 28 GHz, you'll see
    `Sab(4cm²) +23.9dB PASS` but summary Margin `+22.1 dB` driven
    by invisible SAR_wb. Confusing but "min of all constraints" is a
    reasonable safety-first summary; not a blocker.
  - `SAR_wb` check is still evaluated at 60 GHz even though ICNIRP's
    whole-body SAR restriction technically applies up to 10 GHz only.
    Value stays tiny (~0.0002 W/kg at typical power) so it never
    wins; probably intentional conservatism.
  - Compliance heatmap renders a green/red compliant/exceeded
    region grid as expected.
  Confident the compliance surface is healthy aside from the rounding
  bug and the panel<->sweep max-compliant disagreement, both of
  which land under #594. (Auto-fixed via PR #595 mid-session.)

### 2026-04-18 04:20 UTC -- "Visualization and analysis"

- Actor: interactive
- Depth: medium
- Findings: none filed
- Notes: Exercised every Analysis sub-section on the Open ground scenario
  (28 GHz, 65 dBm). Exposure distribution stats populate correctly
  (illuminated 43.0%, 3695 cm², P99 0.073 W/m²). SAB histogram renders
  with log-scale bins. Power sweep converges: Max compliant 65.0 dBm
  matches the HUD Max TX power (65.1 dBm), red dashed ICNIRP limit line
  crosses the margin curve at the right spot. Distance sweep is a clean
  1/r^2 curve from 1-50 m, min compliant 0.3 m, and at current 4.0 m the
  chart reads ~+22 dB — consistent with the 6 dB-per-doubling rule
  (22.1 - 12 = +10 at 1 m). Compliance heatmap click-to-jump works:
  clicking a high-freq cell snapped the simulation to 81.5 GHz / 64.5
  dBm, and the basic-restriction quantity correctly auto-swapped from
  Sab(4 cm^2) / 20 W/m^2 to Sab(1 cm^2) / 40 W/m^2 at the 30 GHz
  boundary, margin +8.7 dB. Frequency sweep rendering initially looked
  like a suspicious "cliff" shape, so I verified against the API:
  `/api/compliance/frequency-sweep` returns flat ~+23 dB when driven by
  only sab_4cm2 + sar_wb + sinc_* (SAR_wb is the tightest), and returns
  `null` for the sub-30-GHz slice when sab_1cm2 is passed (because 1 cm^2
  isn't defined below 30 GHz). The chart honestly draws that — flat
  segment at top of y-axis where data is clipped, break in the line
  where margin is null. Not a bug, just the chart not auto-scaling when
  the dominant check changes across freq. Export panel shows all 6
  buttons enabled (Screenshot PNG, CSV/JSON/NPZ dosimetry, Compliance
  TXT, Config JSON); clicked CSV and no visible error surfaced (download
  goes to headless nowhere). Console clean except for known benign
  warnings (THREE.Clock deprecation, WebGL ReadPixels). Mid-session
  rolled through deploy bdbc89f → 7897c0c with ~15 s ERR_CONNECTION_REFUSED
  burst on /api/system polling, recovered automatically. Confident this
  surface is healthy; the only nit is that the freq-sweep chart y-axis
  doesn't auto-rescale when only one check is dominant, so users see a
  flat line pressed against the top — worth considering log scale or
  auto-zoom but cosmetic, not filed.

### 2026-04-18 02:18 UTC -- "Visualization and analysis"

- Actor: interactive
- Depth: medium
- Findings: 0 bugs filed. Both #565 and #566 fixes verified green on
  production.
- Notes: Anchored on the two fresh commits (#565 NaN colorbar after
  MIMO peak, #566 Tilt+power RT gating) and swept the rest of the
  visualization surface on Open ground. **#566 verified:** Tilt+power
  button is now disabled-by-default in the non-RT/non-MIMO Open ground
  scenario; enabling MIMO only unlocks MIMO peak, Tilt+power stays
  disabled (no RT paths). Matches the gating described in #566 and
  removes the raw-JSON-toast regression my last pass caught.
  **#565 verified:** MIMO peak optimizer converged ("Converged after 6
  iterations. -0% reduction" -- expected for 1-antenna 1-user case)
  and the ColorLegend ticks rendered as valid numbers
  (0/0.054/0.109/0.163/0.218 W/m²), not the `NaN NaN NaN NaN NaN`
  strings I filed under #563. Legend surface is otherwise healthy:
  Lin/dB toggle swaps units cleanly, dB ticks step -6/-13/-19/-25 as
  expected; Floor spinbutton at -40 rescales ticks correctly; colormap
  lock (🔓→🔒) holds the legend cap at 0.218 W/m² when frequency is
  switched 28→47 GHz while Sab rises to 0.238, and unlocking snaps the
  cap back to the current peak. Quantity restriction auto-swapped from
  Sab(4cm²) to Sab(1cm²) at 47 GHz and compliance recomputed to
  0.24/40.00 W/m² PASS (+13.9 dB) -- visible the restriction rule is
  driving the limit. Analysis plots: SAB histogram draws log bins with
  Below/Above legend, Frequency sweep produced a line plot in the
  chart slot (tiny sidebar width made details hard to read but it
  rendered without NaN axis labels), Compliance heatmap generated a
  Compliant/Exceeded/Boundary grid with all green cells. Console
  clean: 1 expected 401 at auth gate, a few harmless warnings
  (THREE.Clock deprecated, WebGL ReadPixels GPU stall, chart width
  -1 from a transient Recharts layout). Confident this area is
  healthy after #565 + #566. Q eigenvalue + rho gauge are listed in
  features.md for coherent MIMO results but I didn't find them
  surfaced in the UI on this configuration -- worth a targeted
  follow-up on a coherent RT scenario.

### 2026-04-18 00:18 UTC -- "Visualization and analysis"

- Actor: interactive
- Depth: medium
- Findings: 0 bugs filed
- Notes: Exercised the full AnalysisPanel dashboard tree on Open ground
  at 28 GHz + regression-checked today's two fixes. **#565 regression
  confirmed fixed**: ran MIMO peak optimize (converged after 6 iters,
  -0% reduction on a single-element config) and the ColorLegend rendered
  clean numeric ticks in both modes — linear 0 / 0.054 / 0.109 / 0.163 /
  0.218 W/m² (matches Exposure distribution Peak 0.218) and dB re peak
  0 / -6 / -13 / -19 / -25 dB, no NaN anywhere. **#566 regression
  confirmed fixed**: on Open ground (non-RT) the Tilt+power strategy
  button is disabled at the DOM level, so the raw-JSON-toast path is
  unreachable from this scenario. Placement and MIMO peak remain
  selectable. AnalysisPanel subpanels exercised: Exposure distribution
  (Peak 0.081, P99 0.073, Mean 0.012, illuminated 43.8% / 16497 of 23828
  triangles — sensible); SAB histogram (log-scale bins 6.2e-10 → 3.0e-3,
  green/red below/above-limit coloring); Power sweep (margin linear +42
  → -5 dB across 23-63 dBm, Max compliant 65.0 dBm, Set button offered);
  Frequency sweep (flat ~+22 dB margin across 7-100 GHz, dashed vertical
  at 28 GHz, 0-dB limit line); Distance sweep (margin +25 → +44 dB from
  1-50 m, Min compliant 0.3 m, current 4.0 m); Compliance heatmap
  (all-green 2D grid across freq×power, legend keyed
  Compliant/Exceeded/Boundary). ColorLegend controls: Lin↔dB toggle
  reflowed ticks correctly, Floor spinbutton steps 5 dB per ArrowDown
  (-25 → -40 → ticks rebinned to 10-dB spacing 0/-10/-20/-30/-40 and the
  body heatmap re-colored to show more illumination), Lock button
  toggled 🔓↔🔒. One ambiguity noted but not filed: with lock engaged,
  switching freq 28→3.5 GHz reset the Floor from -40 back to -25 while
  the quantity auto-switched Sab(4cm²)→SARwb per band-specific rules, so
  it's unclear if lock is supposed to preserve floor across quantity
  changes. Worth a targeted check by someone who knows the intended
  lock contract. Console clean apart from known THREE.Clock, WebGL
  ReadPixels stall, and a one-off Recharts width/height(-1) warning that
  didn't produce a visible failure. Confident this area is healthy.

### 2026-04-17 22:25 UTC -- "Coherent MIMO and beamforming (mmwave_close, follow-up to #567)"

- Actor: interactive
- Depth: medium
- Findings: 0 new bugs filed (observed #567 repro path in
  mmwave_close; existing report covers it)
- Notes: Exercised MIMO end-to-end on the mmwave_close scenario (4x4
  UPA default, 60 GHz) as a follow-up to the 18:25 session on Open
  ground. Single-user: all four precoder buttons
  (MRT/ZF/MMSE/ZF+Exp) produce identical Sab=0.22 W/m², Margin +14.5
  dB, Max TX 57.5 dBm — expected since K=1 degenerates to a matched
  beam. Added Duke as User 2 and flipped precoders: MRT splits power
  sensibly (User1=0.11, User2=21 mW/m²); MMSE strongly favors User 1
  (0.22 vs 2.33 mW/m²); ZF and ZF+Exp both produce User1≈1.6e-33 W/m²
  (numerical zero) while User 2 gets 37 mW/m². Scale at 8x8 is
  consistent: ZF+Exp User1 stays at ~10⁻³³, User2 grows to 80 mW/m².
  Worth an offline check whether this is correct ECBF power
  allocation or a user-ordering/null-steering asymmetry (16/64
  antennas >> 2 users so ZF shouldn't be starving its own user) —
  could be a real physics bug but the 10⁻³³ spread is tight across
  array sizes, suggesting structured behavior not noise. Ran peak
  optimize after ZF+Exp and saw the ColorLegend lock to the 1.5e-33
  range, exactly the #567 stale-legend repro on a different scenario.
  #565 regression confirmed fixed: peak optimizer colorbar labels are
  finite (1.5e-33 not NaN) even when exposure is machine-zero. Peak
  optimize text displays "Converged after 6 iterations. -0%
  reduction" whenever the solver finds no improvement — the literal
  "-0%" is a negative-zero rounding cosmetic glitch. Compliance HUD
  tracks the "focused user" per
  aegis-web/src/hooks/useActiveSimulation.ts:40 — confirmed by design,
  but worth revisiting: when ZF nulls User 1, HUD shows "0.00 / 40.00
  PASS" while Duke is at 37 mW/m²; a bystander at 40 W/m² would read
  as a clean pass on the header badge unless the operator clicks
  through to the per-user row. Array spinners handle 1x1 to 16x16
  cleanly (16x16 = 256 elements is ~7s to recompute, not crashing).
  Rapid precoder toggling converged cleanly to the last click. Two
  console-warning classes worth a future look:
  chart width(-1)/height(-1) on collapse and GL_CLOSE_PATH_NV
  "GPU stall due to ReadPixels" — neither user-visible.

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

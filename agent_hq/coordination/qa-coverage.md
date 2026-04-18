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

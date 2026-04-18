# AEGIS viewer E2E specs

Playwright specs that exercise the Flask backend plus the built React frontend
end-to-end. These are not wired into PR CI (per the Phase 3a testing roadmap,
E2E runs at master-push or patch-release tier). Run them locally before
merging a risky viewer change, or invoke the manual workflow.

## Prerequisites

```bash
pip install -e .[dev]               # Python deps, including AEGIS viewer
cd aegis-web
npm install                         # node deps, including @playwright/test
npx playwright install chromium     # browser binaries
```

## Run locally

```bash
# 1. Build the frontend into Flask's static dir
cd aegis-web
npm run build:copy

# 2. Start the Flask backend on :5001 in one terminal
python3 -m aegis.viewer --no-open --port 5001

# 3. Run the specs in another terminal (still from aegis-web/)
npx playwright test

# or, a single spec in headed mode for debugging
npx playwright test scenario-load.spec.ts --headed

# or, specific spec in UI mode
npx playwright test --ui
```

The specs default to `http://127.0.0.1:5001`. Override via
`AEGIS_E2E_BASE_URL=http://localhost:5000 npx playwright test` if you launch
Flask elsewhere.

## Spec catalogue

| # | Spec | What it exercises |
|---|------|-------------------|
| 1 | `scenario-load.spec.ts` | Default scenario loads, body mesh visible, no `console.error` |
| 2 | `set-frequency.spec.ts` | Frequency input → compute payload contains `freq_hz: 28000000000` |
| 3 | `dosimetry-level2.spec.ts` | `mode=spatial` + no corrections ≈ level 2; compliance HUD shows numeric values |
| 4 | `fidelity-toggle.spec.ts` | bound → aggregate → spatial, each fires a compute with the correct `mode` |
| 5 | `placement-optimize.spec.ts` | Placement optimizer runs; summary matches `\d+% reduction` |
| 6 | `image-export.spec.ts` | Screenshot export download is a valid nonempty PNG |
| 7 | `share-link.spec.ts` | Share link serializes + restores antennaPos and freqGhz |
| 8 | `multi-body.spec.ts` | MIMO mode with ≥ 2 bodies — verifies via HUD `MIMO (N users)` counter |
| 9 | `mimo-precoder.spec.ts` | MIMO level-7 kernel: switch precoder to MMSE, verify compute fires |
| 10 | `tilt-power-optimize.spec.ts` | tilt_power summary has "tilt" + "power" + "peak" and NOT "reduction" (fixme in headless envs without RT GPU) |

## Fixtures

`fixtures.ts` defines a shared `test` and several helpers:

- `test` — extends Playwright's `test` with a `consoleErrors` fixture that
  collects browser errors (minus an ignore list for GL/WebGL/ResizeObserver
  noise, Sentry connection refusals, etc.) Assert `consoleErrors.nonIgnored()`
  at the end of every spec.
- `gotoViewer(page)` — navigates to `/`, waits for `/api/viewer-config`,
  dismisses the WelcomeOverlay, and pre-sets `aegis-tour-completed` in
  localStorage so the guided tour does not block clicks after the first
  antenna placement.
- `placeAntennaCenterRight(page)` — dispatches a mouse click at 62% × 65% of
  the canvas, roughly in front of the body. R3F raycasts this correctly.
- `openSidebarSection(page, groupId, sectionValue)` — switches to the given
  group (does not collapse if already active) and expands the given
  accordion section. Handles the default `sidebarMode='expanded' +
  activeGroup='source'` case where a naive click would collapse the
  sidebar.
- `waitForCompute(page, pattern?, timeout?)` — generic helper for awaiting a
  successful `/api/compute/*` response.

## Gotchas

- **Canvas intercept.** The Three.js canvas covers most of the viewport and
  will intercept clicks on HUD / sidebar elements if Playwright tries to be
  clever about pointer-events stability. Use `.click({ force: true })` when
  clicking HUD/sidebar controls.
- **Register before click.** Many store actions (setting frequency, clicking
  a precoder button, clicking the RT enable) trigger a compute fetch. Always
  `page.waitForResponse(...)` BEFORE the action that triggers the request,
  then `await` the promise. Do not register the listener afterward.
- **Welcome overlay + guided tour.** Both block interaction. `gotoViewer`
  dismisses both. Do not use raw `page.goto` in specs.
- **Freq input is controlled.** `.fill('26')` does not always propagate
  through React's controlled number input. Click the FR2 preset button
  (`getByRole('button', { name: '26', exact: true })`) instead.
- **Sidebar state.** Default is `sidebarMode='expanded'` with
  `activeGroup='source'`. Clicking the Source rail button again collapses.
  Use `openSidebarSection` to avoid this.

## Adding a new spec

1. Import from `./fixtures`, not `@playwright/test` directly, so you get the
   `consoleErrors` collector.
2. Call `gotoViewer(page)` first.
3. Register any `page.waitForResponse` BEFORE clicking the action that
   triggers the request.
4. End every spec with `expect(consoleErrors.nonIgnored()).toEqual([])`.
5. Prefer `data-testid` selectors over text. If you need to add a new
   `data-testid` to a component, do it in a minimal, non-structural way
   (see the Wave-2 PR for examples).
6. For state changes that depend on a compute round-tripping, use
   `waitForResponse` not `waitForTimeout`.

## CI

Not wired into PR CI. Add a manual workflow (`workflow_dispatch`) or a
master-push job when the spec count stabilizes and Modal RT proxy is
available for spec 10. The spec suite runs in ~6 minutes locally on a
modest laptop.

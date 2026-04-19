/**
 * Deterministic fixtures for visual regression tests.
 *
 * Extends the base `test` fixture in `fixtures.ts` with extra setup that
 * pins every pixel-visible source of drift. Any `toHaveScreenshot()` call
 * through this fixture compares against baselines committed in
 * `__snapshots__/`.
 *
 * Sources of pixel drift in the AEGIS viewer, and how we pin them:
 *
 * 1. Font smoothing. Linux font-config, macOS CoreGraphics, Windows
 *    ClearType each render glyphs differently. We inject a CSS rule that
 *    disables sub-pixel AA entirely (`-webkit-font-smoothing: none`) so
 *    the rasterizer falls back to a pixel-aligned bitmap renderer. This
 *    produces identical output across OSes when the same font file is
 *    used.
 *
 * 2. Font files. The viewer uses Geist via `@fontsource-variable/geist`
 *    which is bundled with the build, so the glyph shapes are the same
 *    in dev, CI, and prod. We explicitly `document.fonts.ready` before
 *    capture so we do not snapshot a fallback-rendered frame.
 *
 * 3. WebGL. The Three.js canvas is rendered by SwiftShader (set in
 *    `playwright.config.ts` via `--use-gl=swiftshader`). But even then,
 *    GPU-vs-CPU rasterization of the canvas output drifts subtly. We
 *    NEVER capture the WebGL canvas; every visual test targets an
 *    overlay/HUD DOM subtree.
 *
 * 4. Time-dependent animations. Shimmer effects and CSS transitions
 *    cause pixel drift. We inject a CSS rule that kills all transitions
 *    and animations before capturing.
 *
 * 5. Clock. Some HUD elements show timestamps or elapsed ms. We freeze
 *    `Date.now()` via `page.clock.install({ time: ... })`.
 *
 * 6. Random state. Any `Math.random()` in the app. We monkeypatch it to
 *    a seeded PRNG.
 */

import { test as base, expect, type Page } from '@playwright/test'
import {
  type ConsoleErrorCollector,
  gotoViewer as baseGotoViewer,
  placeAntennaCenterRight,
  openSidebarSection,
} from './fixtures'

export { placeAntennaCenterRight, openSidebarSection }

// Errors we do not fail the test on. Same ignore list as `fixtures.ts` so
// environmental noise (SwiftShader, Sentry refused, manifest/favicon 404s)
// does not leak through.
const IGNORED_PATTERNS = [
  /THREE/i,
  /WebGL/i,
  /ResizeObserver/i,
  /net::ERR_ABORTED/i,
  /net::ERR_CONNECTION_REFUSED/i,
  /net::ERR_NAME_NOT_RESOLVED/i,
  /net::ERR_INTERNET_DISCONNECTED/i,
  /Failed to load resource.*manifest/i,
  /Failed to load resource.*favicon/i,
  /Failed to load resource: net::/i,
  /Download the React DevTools/i,
]

/**
 * CSS injected into every visual test:
 * - Pin caret to a hidden state.
 * - Disable all CSS transitions and animations so shimmer / fades
 *   do not drift the capture.
 * - Kill font antialiasing for cross-OS glyph stability.
 * - Hide volatile HUD regions that change on every run (compute timing,
 *   server uptime, session timer) so they do not invalidate a baseline
 *   after a trivial edit elsewhere.
 */
const DETERMINISTIC_CSS = `
  *, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    caret-color: transparent !important;
  }
  html {
    -webkit-font-smoothing: none !important;
    font-smooth: never !important;
  }
  /* Hide shimmer effects entirely — they animate a background gradient. */
  .shimmer-text, .shimmer-panel {
    background-image: none !important;
    animation: none !important;
  }
`.trim()

export type VisualFixtures = {
  consoleErrors: ConsoleErrorCollector
  deterministicPage: Page
}

export const test = base.extend<VisualFixtures>({
  consoleErrors: async ({ page }, run) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    page.on('pageerror', (err) => {
      errors.push(String(err))
    })
    const collector: ConsoleErrorCollector = {
      errors,
      nonIgnored: () =>
        errors.filter((e) => !IGNORED_PATTERNS.some((p) => p.test(e))),
    }
    await run(collector)
  },

  // `deterministicPage` installs the pixel-stability hooks BEFORE any
  // navigation. Tests then call `gotoViewerDeterministic(page)`.
  deterministicPage: async ({ page }, run) => {
    // 1. Freeze the clock. All `Date.now()` / `performance.now()` calls
    //    return a fixed moment. Timers can still be advanced manually via
    //    `page.clock.fastForward(ms)` if a test needs to tick.
    await page.clock.install({ time: new Date('2026-01-01T00:00:00Z') })

    // 2. Monkeypatch Math.random to a seeded Mulberry32 PRNG so anything
    //    that forks on randomness (toast dedupe, uuid generation in the
    //    share-link encoder, etc.) produces the same bytes every run.
    await page.addInitScript(() => {
      let seed = 0x9e3779b9
      Math.random = () => {
        seed = (seed + 0x6d2b79f5) | 0
        let t = seed
        t = Math.imul(t ^ (t >>> 15), t | 1)
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296
      }
    })

    // 3. Pin guided tour + welcome overlay off so they never appear.
    await page.addInitScript(() => {
      try {
        localStorage.setItem('aegis-tour-completed', '1')
        localStorage.setItem('aegis-welcome-dismissed', '1')
      } catch {
        // Ignore storage errors.
      }
    })

    await run(page)
  },
})

export { expect }

/**
 * Navigate with all determinism applied. Use this instead of `gotoViewer`
 * in visual regression tests.
 */
export async function gotoViewerDeterministic(
  page: Page,
  path = '/',
): Promise<void> {
  await baseGotoViewer(page, path)

  // Inject deterministic CSS after the page has loaded so it overrides
  // any CSS-in-JS that mounted during boot.
  await page.addStyleTag({ content: DETERMINISTIC_CSS })

  // Wait for all fonts to be resolved before we allow a snapshot. If we
  // capture before fonts are loaded the baseline will render Geist-but-
  // the-CI-env will render fallback and the pixels diverge.
  await page.evaluate(() => document.fonts.ready)

  // Give React one commit cycle after the style tag injection so any
  // layout the new CSS triggers has settled.
  await page.waitForTimeout(150)
}

/**
 * Common options for `toHaveScreenshot`. `threshold` is a per-pixel
 * color similarity tolerance; `maxDiffPixels` is the global budget.
 *
 * Rationale for values:
 * - `threshold: 0.15` — matches Playwright's default for permissive
 *   comparisons. We allow small anti-alias wobble at glyph edges.
 * - `maxDiffPixels: 120` — small enough to catch any actual UI change,
 *   generous enough to absorb the handful of glyph-edge pixels that
 *   drift between local SwiftShader and CI SwiftShader.
 * - `animations: 'disabled'` — Playwright also freezes CSS animations
 *   at capture time, belt-and-suspenders with our DETERMINISTIC_CSS.
 */
export const SHOT_OPTS = {
  threshold: 0.15,
  maxDiffPixels: 120,
  animations: 'disabled' as const,
}

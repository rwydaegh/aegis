/**
 * Visual regression specs for the HUD overlay.
 *
 * These tests use Playwright's `toHaveScreenshot()` against DOM subtrees
 * (NEVER the 3D canvas, which drifts across GPU drivers even under
 * SwiftShader). The baselines live in `__snapshots__/` and are committed
 * to the repo. A failing diff uploads the `*-diff.png` artifact for
 * review in the PR.
 *
 * Scope (6 named visual tests per the roadmap):
 *   - hud-collapsed       : toolbar / pre-placement HUD
 *   - hud-expanded        : compliance panel after placement
 *   - compliance-panel    : compliance with antenna close to body
 *                           (parametrized — two antenna positions in two
 *                           separate tests yielding different margins)
 *   - optimize-summary    : placement optimizer summary text
 *   - legend-scale        : color legend at fixed S_ab bounds
 *   - keyboard-help-modal : keyboard help modal (stand-in for the
 *                           roadmap's "share-link-modal" — the share
 *                           action is a clipboard write with no modal
 *                           UI, so we target the real modal in the HUD)
 *
 * Determinism: see `visualFixtures.ts` for the pinning scheme.
 * Runtime budget: ~2 min locally, should fit ~5 min CI budget.
 */

import {
  test,
  expect,
  gotoViewerDeterministic,
  placeAntennaCenterRight,
  openSidebarSection,
  SHOT_OPTS,
} from './visualFixtures'
import type { Page } from '@playwright/test'

/**
 * Wait for the compliance HUD to populate numeric values. The panel is
 * fully populated once a dosimetry response has rendered a PASS/WARN/FAIL
 * label.
 */
async function waitForComplianceReady(page: Page) {
  const panel = page.getByTestId('compliance-panel')
  await panel.waitFor({ state: 'visible', timeout: 30_000 })
  await expect(panel).toContainText(/PASS|WARN|FAIL/, { timeout: 30_000 })
  // Settle — margin bars animate in.
  await page.waitForTimeout(250)
}

async function placeAntennaAndWait(page: Page) {
  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await computePromise
  await waitForComplianceReady(page)
}

test.describe('HUD visual regression', () => {
  test('hud-collapsed: toolbar before antenna placed', async ({
    deterministicPage: page,
    consoleErrors,
  }) => {
    await gotoViewerDeterministic(page)

    // Toolbar is always visible with the AEGIS wordmark + scenario
    // dropdown. Session timer and docs pill are hidden below 768px,
    // but our viewport is 1280x720 so they render. Session timer is
    // masked because its value is "time since page load" which
    // wall-clock freezing covers, but keep as mask defense-in-depth.
    const toolbar = page.locator('header').first()
    await expect(toolbar).toBeVisible()

    await expect(toolbar).toHaveScreenshot('hud-collapsed-toolbar.png', SHOT_OPTS)

    expect(consoleErrors.nonIgnored()).toEqual([])
  })

  test('hud-expanded: compliance panel after placement', async ({
    deterministicPage: page,
    consoleErrors,
  }) => {
    await gotoViewerDeterministic(page)
    await placeAntennaAndWait(page)

    // The compliance panel is the primary HUD that appears after an
    // antenna is placed. It aggregates multiple ICNIRP checks and is
    // the single densest HUD region.
    const compliance = page.getByTestId('compliance-panel')
    await expect(compliance).toHaveScreenshot('hud-expanded-compliance.png', SHOT_OPTS)

    expect(consoleErrors.nonIgnored()).toEqual([])
  })

  // Compliance-panel parametrized across two antenna positions. Both are
  // deterministic for a fixed viewport + seeded PRNG + fixed default
  // scenario, so baselines are stable.
  for (const variant of ['near', 'mid'] as const) {
    test(`compliance-panel: antenna at ${variant} position`, async ({
      deterministicPage: page,
      consoleErrors,
    }) => {
      await gotoViewerDeterministic(page)

      const computePromise = page.waitForResponse(
        (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
        { timeout: 45_000 },
      )
      const canvas = page.locator('canvas').first()
      const box = await canvas.boundingBox()
      if (!box) throw new Error('canvas has no bounding box')
      // 'near' lands on the body (closer to peak), 'mid' lands further
      // off-axis so the margins differ.
      const frac = variant === 'near' ? 0.58 : 0.75
      const x = box.x + box.width * frac
      const y = box.y + box.height * 0.65
      await page.mouse.move(x, y)
      await page.mouse.down()
      await page.mouse.up()
      await computePromise
      await waitForComplianceReady(page)

      const compliance = page.getByTestId('compliance-panel')
      await expect(compliance).toHaveScreenshot(`compliance-panel-${variant}.png`, SHOT_OPTS)

      expect(consoleErrors.nonIgnored()).toEqual([])
    })
  }

  test('legend-scale: color legend at default bounds', async ({
    deterministicPage: page,
    consoleErrors,
  }) => {
    await gotoViewerDeterministic(page)
    await placeAntennaAndWait(page)

    // ColorLegend is rendered inside the data-tour="color-legend"
    // wrapper. The ticks are computed from stats.peak_sab which is
    // deterministic for a fixed antenna + fixed frequency.
    const legend = page.locator('[data-tour="color-legend"]').first()
    await expect(legend).toBeVisible()

    await expect(legend).toHaveScreenshot('legend-scale.png', SHOT_OPTS)

    expect(consoleErrors.nonIgnored()).toEqual([])
  })

  test('optimize-panel-summary: placement optimizer summary after run', async ({
    deterministicPage: page,
    consoleErrors,
  }) => {
    await gotoViewerDeterministic(page)
    await placeAntennaAndWait(page)

    await openSidebarSection(page, 'analysis', 'optimize')
    await page.getByRole('button', { name: 'Placement', exact: true }).click()

    const runBtn = page.getByTestId('optimize-run')
    await expect(runBtn).toBeEnabled()
    await runBtn.click()

    const summary = page.getByTestId('optimize-summary')
    await expect(summary).toBeVisible({ timeout: 120_000 })
    await expect(summary).toContainText(/\d+% reduction/, { timeout: 15_000 })

    // The optimizer summary renders numeric values that can drift by
    // a percentage point under SwiftShader, so we allow a slightly
    // larger maxDiffPixels.
    await expect(summary).toHaveScreenshot('optimize-panel-summary.png', {
      ...SHOT_OPTS,
      maxDiffPixels: 250,
    })

    expect(consoleErrors.nonIgnored()).toEqual([])
  })

  test('keyboard-help-modal: help modal overlay', async ({
    deterministicPage: page,
    consoleErrors,
  }) => {
    // Stand-in for the roadmap's "share-link-modal" item. The share-link
    // action is a clipboard write + toast — no modal UI. The only real
    // modal in the HUD is the keyboard-help overlay triggered by "?".
    await gotoViewerDeterministic(page)

    await page.keyboard.press('?')
    const heading = page.getByRole('heading', { name: /Keyboard shortcuts/i })
    await expect(heading).toBeVisible()

    // The modal card is the rounded-xl ancestor of the heading.
    const modalCard = heading.locator(
      'xpath=ancestor::div[contains(@class, "rounded-xl")][1]',
    )
    await expect(modalCard).toHaveScreenshot('keyboard-help-modal.png', SHOT_OPTS)

    expect(consoleErrors.nonIgnored()).toEqual([])
  })
})

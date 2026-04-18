/**
 * Spec 10: Tilt/power optimize
 *
 * Enable ray tracing, run a compute (populates rtPaths), open the optimize
 * panel in tilt_power mode, and verify the summary contains "tilt" + "power"
 * + "peak" and explicitly does NOT contain "reduction" (per the
 * useOptimization.test.ts regression that motivated this check).
 *
 * This spec requires:
 *   - DiffeRT installed (checked via /api/config has_differt; true in CI).
 *   - A Modal proxy or local RT compute that completes in reasonable time.
 * If the RT compute fails or takes too long, the spec is marked `test.fixme`
 * — see the spec PR body for follow-up.
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

// RT compute + tilt_power iterations can exceed the default 90s timeout,
// especially on cold start. Grant a generous overall budget.
test.setTimeout(600_000)

test('tilt_power optimize summary format (no "reduction")', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)

  // Place the antenna first so we have a seed position.
  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await computePromise

  // Enable ray tracing (populates rtPaths).
  await openSidebarSection(page, 'exposure', 'raytracing')
  const rtEnable = page.locator('label', { hasText: /Enable ray tracing/ }).locator('input[type="checkbox"]')
  if (!(await rtEnable.isChecked())) {
    await rtEnable.click({ force: true })
  }

  // Wait for an RT compute to finish (stats.path_viz populates rtPaths).
  // Can be slow on cold start; grant a generous timeout.
  try {
    await page.waitForResponse(
      (r) => /\/api\/compute\/(rt|sionna-rt|voxel-rt|sionna-env-rt)/.test(r.url()) && r.ok(),
      { timeout: 120_000 },
    )
  } catch (e) {
    test.fixme(
      true,
      'RT compute did not finish within 120s. tilt_power needs rtPaths; enable Modal GPU proxy or increase timeout. See docs/internal/testing_roadmap.md Phase 3a.',
    )
    throw e
  }

  // Switch to Optimize panel and pick tilt_power.
  await openSidebarSection(page, 'analysis', 'optimize')
  const tiltBtn = page.getByRole('button', { name: 'Tilt + power', exact: true })
  await expect(tiltBtn).toBeEnabled({ timeout: 20_000 })
  await tiltBtn.click()

  const runBtn = page.getByTestId('optimize-run')
  await expect(runBtn).toBeEnabled()
  await runBtn.click()

  // Wait for the done event + summary text.
  const summary = page.getByTestId('optimize-summary')
  await expect(summary).toBeVisible({ timeout: 300_000 })

  const text = (await summary.textContent()) ?? ''
  expect(text.toLowerCase()).toContain('tilt')
  expect(text.toLowerCase()).toContain('power')
  expect(text.toLowerCase()).toContain('peak')
  // Per the useOptimization.test.ts regression, tilt_power summary must NOT
  // use "% reduction" (nonsensical for signed penalty objective).
  expect(text.toLowerCase()).not.toContain('reduction')

  expect(consoleErrors.nonIgnored()).toEqual([])
})

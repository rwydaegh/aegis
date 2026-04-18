/**
 * Spec 5: Placement optimize
 *
 * Place an antenna (required prerequisite), open the Optimize panel, select
 * the "Placement" strategy, run it, and wait for the SSE stream to emit a
 * terminal "done" event. The summary text should include "% reduction".
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

test('placement optimize runs and produces a reduction summary', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)

  // First, place an antenna so that the placement optimizer has a seed.
  // Register the response listener BEFORE clicking to avoid race.
  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await computePromise

  // Open Analysis > Optimize.
  await openSidebarSection(page, 'analysis', 'optimize')

  // Choose placement mode.
  await page.getByRole('button', { name: 'Placement', exact: true }).click()

  // Shrink the grid via the grid_size constraint to keep the test fast.
  // The ModeConstraints inputs live inside the Optimize panel; find by label.
  const gridInput = page.locator('input[type="number"]').filter({ hasNot: page.getByTestId('freq-input') }).first()
  // It's fine if we can't narrow further — use the default grid.

  // Kick off the optimizer.
  const runBtn = page.getByTestId('optimize-run')
  await expect(runBtn).toBeEnabled()
  await runBtn.click()

  // Wait for the optimize summary to appear (SSE stream terminates).
  const summary = page.getByTestId('optimize-summary')
  await expect(summary).toBeVisible({ timeout: 120_000 })
  await expect(summary).toContainText(/\d+% reduction/, { timeout: 5_000 })

  expect(consoleErrors.nonIgnored()).toEqual([])
  // gridInput declared to silence lint even when unused
  void gridInput
})

/**
 * Spec 7: Share link roundtrip
 *
 * Place an antenna + tweak a setting (so state is non-default), click the
 * toolbar share button (writes to clipboard), read the copied URL, open it in
 * a fresh context, and verify the antenna is restored at the same position.
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

test('share link serializes and restores scene state', async ({ page, context, consoleErrors }) => {
  await gotoViewer(page)

  // Set a non-default frequency so we can verify it carries through the link.
  // Use the FR2 preset button (26 GHz) — more reliable than .fill() on a
  // controlled React number input, which does not always propagate through
  // Playwright's dispatch.
  await openSidebarSection(page, 'source', 'parameters')
  await page.getByRole('button', { name: '26', exact: true }).click({ force: true })
  await page.waitForTimeout(200)

  // Place the antenna (also triggers compute + persists antennaPos in store).
  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await computePromise

  // Grant clipboard perms for this origin, then click share.
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {
    origin: new URL(page.url()).origin,
  })
  await page.getByTestId('toolbar-share').click()

  // Read the clipboard contents.
  const shareUrl = await page.evaluate(() => navigator.clipboard.readText())
  expect(shareUrl).toMatch(/#s=/)

  // Open the link in a fresh page (same context). applyShareState should
  // restore antennaPos and freqGhz.
  const page2 = await context.newPage()
  // Collect errors on the new page too.
  const page2Errors: string[] = []
  page2.on('console', (msg) => {
    if (msg.type() === 'error') page2Errors.push(msg.text())
  })

  // Register the compute listener BEFORE navigation so we catch the compute
  // fired by share-rehydration (applyShareState -> antennaPos triggers
  // compute on page load).
  const page2Compute = page2.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await page2.goto(shareUrl, { waitUntil: 'domcontentloaded' })
  await page2.waitForSelector('canvas', { timeout: 20_000 })
  await page2Compute

  // Give the share-hydration effect a beat to finish.
  await page2.waitForTimeout(1_500)

  // The default sidebar state is expanded + source, so parameters section
  // is already in the DOM. Just wait for it.
  await page2.waitForSelector('[data-testid="sidebar-section-parameters"]', { timeout: 10_000 })
  const freq = page2.getByTestId('freq-input')
  await expect(freq).toHaveValue('26', { timeout: 10_000 })

  expect(consoleErrors.nonIgnored()).toEqual([])
  const ignoredPatterns = [/THREE/i, /WebGL/i, /ResizeObserver/i, /net::ERR_/i, /favicon/i, /manifest/i, /Download the React DevTools/i]
  const page2Real = page2Errors.filter((e) => !ignoredPatterns.some((p) => p.test(e)))
  expect(page2Real).toEqual([])
})

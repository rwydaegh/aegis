/**
 * Spec 2: Set frequency
 *
 * Change frequency to 28 GHz, place an antenna, and verify that a
 * `/api/compute/*` request fires with the updated frequency and returns
 * a successful result. Also verifies the compliance HUD updates.
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

test('set frequency to 28 GHz and trigger compute', async ({ page, consoleErrors }) => {
  await gotoViewer(page)

  // Open Source > Parameters, where the frequency input lives.
  await openSidebarSection(page, 'source', 'parameters')

  const freq = page.getByTestId('freq-input')
  await expect(freq).toBeVisible()
  await freq.fill('28')
  await freq.press('Tab')

  // Placing an antenna triggers a compute.
  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  const response = await computePromise

  // The request payload should reflect the 28 GHz frequency.
  // Backend expects freq_hz = freqGhz * 1e9 = 28e9 = 28000000000.
  const request = response.request()
  const body = request.postData() ?? ''
  expect(body).toMatch(/"freq_hz"\s*:\s*28000000000|"freq_ghz"\s*:\s*28\b/)

  // Compliance HUD updates once compute returns.
  await expect(page.getByTestId('compliance-panel')).toBeVisible({ timeout: 15_000 })

  expect(consoleErrors.nonIgnored()).toEqual([])
})

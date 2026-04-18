/**
 * Spec 3: Dosimetry level 2 compute
 *
 * "Level 2" in the monograph is the Geometric ReLU kernel — the vanilla
 * spatial kernel with no corrections. In the frontend that maps to:
 *   mode = 'spatial', fresnel = false, polarisation/curvature/diffraction = false.
 *
 * The frontend doesn't expose numeric levels directly; they are chosen by the
 * backend from (mode, corrections) via default_config.json. See the spec
 * report for this mapping caveat.
 *
 * We set spatial + no corrections, place an antenna, wait for compute, and
 * assert the compliance HUD shows numeric check values.
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

test('spatial dosimetry (level 2) compute produces numeric HUD result', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)
  await openSidebarSection(page, 'source', 'parameters')

  // Mode = Spatial (vanilla, no corrections = level 2).
  await page.getByTestId('mode-select').selectOption('spatial')

  // Turn off the Fresnel correction so we stay at level 2 (geometric ReLU).
  // The checkbox input is the authoritative state carrier; click it directly
  // (the canvas sometimes intercepts label-level clicks).
  const fresnelLabel = page.locator('label', { hasText: 'Fresnel' }).first()
  await fresnelLabel.waitFor({ state: 'visible', timeout: 5_000 })
  const fresnel = fresnelLabel.locator('input[type="checkbox"]')
  if (await fresnel.isChecked()) {
    await fresnel.click({ force: true })
  }

  const computePromise = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await computePromise

  // Numeric value visible in the compliance panel (e.g. "0.42 / 2.00 W/m²").
  const compliance = page.getByTestId('compliance-panel')
  await expect(compliance).toBeVisible({ timeout: 15_000 })
  await expect(compliance).toContainText(/\d+\.\d+\s*\/\s*\d+\.\d+/, { timeout: 15_000 })

  expect(consoleErrors.nonIgnored()).toEqual([])
})

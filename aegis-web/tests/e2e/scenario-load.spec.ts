/**
 * Spec 1: Scenario load
 *
 * Load the default scenario ("open_ground" — body in free space, 28 GHz)
 * and verify the body mesh + config render without any `console.error`.
 *
 * The Urban Ghent scenario requires OSM fetch which is flaky without network
 * access, so we use the default open-ground scenario as the "Ghent, Belgium"
 * equivalent from the roadmap.
 */

import { test, expect, gotoViewer, waitForBodyLoaded } from './fixtures'

test('scenario loads with body mesh and no console errors', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)
  await waitForBodyLoaded(page)

  // The canvas stays mounted and has nonzero dimensions.
  const canvas = page.locator('canvas').first()
  await expect(canvas).toBeVisible()
  const box = await canvas.boundingBox()
  expect(box?.width ?? 0).toBeGreaterThan(100)
  expect(box?.height ?? 0).toBeGreaterThan(100)

  // The "aegis" wordmark in the toolbar is present.
  await expect(page.getByRole('button', { name: 'aegis' })).toBeVisible()

  // The scenario dropdown is visible (proves toolbar rendered).
  await expect(page.getByTestId('scenario-dropdown')).toBeVisible()

  // No un-ignored console errors during load.
  expect(consoleErrors.nonIgnored()).toEqual([])
})

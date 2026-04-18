/**
 * Spec 8: Multi-body scene
 *
 * Enable MIMO mode, add a second user (body), and assert that the scene
 * renders 2+ bodies. MIMO mode is the canonical multi-body view — the
 * non-MIMO path only supports one body.
 *
 * We assert via the MIMO panel's visible user cards (one per body) since
 * counting Three.js meshes from Playwright is unreliable.
 */

import { test, expect, gotoViewer, openSidebarSection } from './fixtures'

test('MIMO multi-body scene renders 2+ user bodies', async ({ page, consoleErrors }) => {
  await gotoViewer(page)

  // Open Source > MIMO, enable MIMO mode. The MIMO enable checkbox lives
  // inside the HUD MIMOPanel, which appears when MIMO section is expanded.
  await openSidebarSection(page, 'source', 'mimo')

  // MIMOPanel renders a checkbox labeled "Enable MIMO mode". Our data-testid
  // is on the input. Wait for the checkbox to appear in the rendered panel.
  const enable = page.locator('input[type="checkbox"][data-testid="mimo-enable"]')
  await expect(enable).toBeAttached({ timeout: 20_000 })
  if (!(await enable.isChecked())) {
    await enable.click({ force: true })
  }

  // Wait for the first MIMO user to be created by the store (setEnabled=true
  // auto-adds a default user per stores/mimo.ts).
  await page.waitForTimeout(1_500)

  // Add a second user by clicking a phantom body button. MIMOPanel offers
  // phantom thumbnails (Duke, Ella, Eartha, Thelonious).
  const ellaBtn = page.getByRole('button', { name: /Ella/i }).first()
  const dukeBtn = page.getByRole('button', { name: /Duke/i }).first()
  if (await ellaBtn.isVisible().catch(() => false)) {
    await ellaBtn.click({ force: true })
    await page.waitForTimeout(1_500)
  } else if (await dukeBtn.isVisible().catch(() => false)) {
    await dukeBtn.click({ force: true })
    await page.waitForTimeout(1_500)
  }

  // MIMO HUD shows "MIMO (N users)" — read N.
  const counter = page.getByText(/MIMO \(\d+ user/i).first()
  await expect(counter).toBeVisible({ timeout: 10_000 })
  const txt = await counter.textContent()
  const match = txt?.match(/(\d+)\s*user/i)
  const n = match ? parseInt(match[1], 10) : 0
  expect(n).toBeGreaterThanOrEqual(2)

  expect(consoleErrors.nonIgnored()).toEqual([])
})

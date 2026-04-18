/**
 * Spec 4: Fidelity toggle
 *
 * Place an antenna, then toggle through three increasing-fidelity compute
 * modes (bound → aggregate → spatial). Each mode change triggers a new
 * compute; we verify compliance HUD updates and no console errors.
 *
 * NB: The roadmap uses 0 → 2 → 5 in monograph level numbering; the frontend
 * exposes (mode, corrections) instead. The mapping is approximately:
 *   level 0 ≈ mode='bound'
 *   level 1 ≈ mode='aggregate'
 *   level 2 ≈ mode='spatial' (no corrections)
 *   level 5 ≈ mode='spatial' + fresnel + polarisation + curvature
 * See the spec PR body for mapping caveat.
 */

import { test, expect, gotoViewer, openSidebarSection, placeAntennaCenterRight } from './fixtures'

test('toggle fidelity modes bound -> aggregate -> spatial', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)

  // Place the antenna BEFORE opening the sidebar (sidebar occludes canvas).
  const firstCompute = page.waitForResponse(
    (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
    { timeout: 45_000 },
  )
  await placeAntennaCenterRight(page)
  await firstCompute

  await openSidebarSection(page, 'source', 'parameters')
  const mode = page.getByTestId('mode-select')
  for (const m of ['bound', 'aggregate', 'spatial'] as const) {
    const computePromise = page.waitForResponse(
      (r) => /\/api\/compute(\/|\?|$)/.test(r.url()) && r.ok(),
      { timeout: 45_000 },
    )
    await mode.selectOption(m)
    const resp = await computePromise
    const body = resp.request().postData() ?? ''
    expect(body).toContain(`"mode":"${m}"`)
  }

  // Compliance panel stays visible + numeric after the last toggle.
  const compliance = page.getByTestId('compliance-panel')
  await expect(compliance).toContainText(/\d/, { timeout: 15_000 })

  expect(consoleErrors.nonIgnored()).toEqual([])
})

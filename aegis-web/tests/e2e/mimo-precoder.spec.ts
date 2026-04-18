/**
 * Spec 9: MIMO precoder apply (level 7)
 *
 * Enable MIMO, which activates the coherent (level 7 / ECBF) kernel path.
 * Switch the precoder to a non-default value (zf_exposure) and verify a MIMO
 * compute succeeds. The `/api/mimo/compute` endpoint is the canonical
 * level-7 entry point.
 */

import { test, expect, gotoViewer, openSidebarSection } from './fixtures'

test('MIMO level-7 precoder apply produces successful compute', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)
  await openSidebarSection(page, 'source', 'mimo')

  // Enable MIMO. The input lives inside the MIMOPanel; toBeAttached avoids
  // a visibility race when the panel animates in.
  const enable = page.locator('input[type="checkbox"][data-testid="mimo-enable"]')
  await expect(enable).toBeAttached({ timeout: 20_000 })

  // Register the compute listener BEFORE clicking to avoid the enable-click
  // racing ahead of the listener.
  const firstCompute = page.waitForResponse(
    (r) => /\/api\/mimo\/compute/.test(r.url()) && r.ok(),
    { timeout: 60_000 },
  )
  if (!(await enable.isChecked())) {
    await enable.click({ force: true })
  }
  await firstCompute

  // Swap to a non-default precoder type. Default is 'zf', so pick 'MMSE' or
  // 'MRT' to force a re-compute. PRECODER_OPTIONS order is MRT/ZF/MMSE/ZF+Exp.
  const mmseBtn = page.getByRole('button', { name: 'MMSE', exact: true }).first()
  await mmseBtn.waitFor({ state: 'visible', timeout: 10_000 })

  const nextCompute = page.waitForResponse(
    (r) => /\/api\/mimo\/compute/.test(r.url()) && r.ok(),
    { timeout: 60_000 },
  )
  await mmseBtn.click({ force: true })
  const resp = await nextCompute
  const body = resp.request().postData() ?? ''
  expect(body.toLowerCase()).toMatch(/"precoder_type"\s*:\s*"mmse/)

  expect(consoleErrors.nonIgnored()).toEqual([])
})

/**
 * Spec 6: Image export
 *
 * Click the Screenshot button in the Export panel, intercept the triggered
 * download, and assert the captured file is a non-empty PNG. The export panel
 * lives under Analysis > Export in the sidebar.
 */

import { test, expect, gotoViewer, openSidebarSection } from './fixtures'

test('screenshot export produces a nonzero PNG download', async ({
  page,
  consoleErrors,
}) => {
  await gotoViewer(page)
  await openSidebarSection(page, 'analysis', 'export')

  const button = page.getByTestId('export-screenshot')
  await expect(button).toBeVisible()

  const downloadPromise = page.waitForEvent('download', { timeout: 30_000 })
  await button.click()
  const download = await downloadPromise

  // The filename should end in .png and the file should be nonempty.
  const filename = download.suggestedFilename()
  expect(filename).toMatch(/\.png$/i)

  const path = await download.path()
  expect(path).toBeTruthy()
  // PNG files start with the magic bytes 0x89 P N G.
  const fs = await import('node:fs/promises')
  const buf = await fs.readFile(path!)
  expect(buf.length).toBeGreaterThan(100)
  expect(buf[0]).toBe(0x89)
  expect(buf[1]).toBe(0x50) // 'P'
  expect(buf[2]).toBe(0x4e) // 'N'
  expect(buf[3]).toBe(0x47) // 'G'

  expect(consoleErrors.nonIgnored()).toEqual([])
})

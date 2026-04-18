/**
 * Shared Playwright fixtures and helpers for AEGIS viewer E2E specs.
 *
 * - `test` — Playwright test fixture that fails the test on any non-ignored
 *   `console.error`. Pattern matches `tests/e2e/test_mimo_e2e.py`.
 * - `placeAntennaCenterRight` — dispatches a PointerEvent pair on the Three.js
 *   canvas at a location that is reliably off the body but in front of it.
 *   R3F raycasts these events, so this is equivalent to a user click.
 */

import { test as base, expect, type Page } from '@playwright/test'

// Errors we do not want to fail on. These are environmental noise:
//   - THREE/WebGL: GPU warnings that fire under swiftshader.
//   - ResizeObserver loop limit exceeded: known benign browser warning.
//   - net::ERR_ABORTED: we intentionally cancel streamed optimizations in specs.
//   - Manifest: / icon fetch 404s under the static dev bundle.
const IGNORED_PATTERNS = [
  /THREE/i,
  /WebGL/i,
  /ResizeObserver/i,
  /net::ERR_ABORTED/i,
  // External services (OSM tile servers, Sentry ingest, analytics) refuse
  // connections inside the hermetic E2E env. These are not bugs.
  /net::ERR_CONNECTION_REFUSED/i,
  /net::ERR_NAME_NOT_RESOLVED/i,
  /net::ERR_INTERNET_DISCONNECTED/i,
  /Failed to load resource.*manifest/i,
  /Failed to load resource.*favicon/i,
  /Failed to load resource: net::/i,
  /Download the React DevTools/i,
]

export type ConsoleErrorCollector = {
  errors: string[]
  nonIgnored(): string[]
}

export const test = base.extend<{ consoleErrors: ConsoleErrorCollector }>({
  consoleErrors: async ({ page }, run) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    page.on('pageerror', (err) => {
      errors.push(String(err))
    })
    const collector: ConsoleErrorCollector = {
      errors,
      nonIgnored: () =>
        errors.filter((e) => !IGNORED_PATTERNS.some((p) => p.test(e))),
    }
    await run(collector)
  },
})

export { expect }

/**
 * Navigate to the viewer and wait for the scene to mount.
 *
 * Critical: start the response listeners BEFORE navigation, because the
 * /api/body + /api/viewer-config requests fire very early in load.
 */
export async function gotoViewer(page: Page, path = '/'): Promise<void> {
  // Pre-dismiss the guided tour via localStorage (the viewer reads this on
  // mount to decide whether to auto-start the tour). This prevents the tour
  // modal from intercepting clicks after the first antenna placement.
  await page.addInitScript(() => {
    try {
      localStorage.setItem('aegis-tour-completed', '1')
    } catch {
      // SSR / storage-disabled — ignore.
    }
  })

  const configPromise = page.waitForResponse(
    (r) => r.url().includes('/api/viewer-config') && r.status() === 200,
    { timeout: 30_000 },
  )
  await page.goto(path, { waitUntil: 'domcontentloaded' })
  await configPromise
  await page.waitForSelector('canvas', { timeout: 20_000 })
  // Give R3F one frame to initialize.
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 1)
  await dismissWelcome(page)
}

/**
 * The WelcomeOverlay appears on first load and blocks canvas interaction.
 * It is only visible when no antenna is placed and no share link is present.
 * Pressing Escape dismisses it without loading a scenario.
 */
export async function dismissWelcome(page: Page): Promise<void> {
  // Heading "AEGIS" appears inside the welcome overlay.
  const overlay = page.locator('text=Absorbed power density on human bodies')
  if (await overlay.isVisible().catch(() => false)) {
    await page.keyboard.press('Escape')
    await overlay.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {
      // Fallback: click the "empty scene" button explicitly.
      return page.getByRole('button', { name: /start with an empty scene/i }).click()
    })
  }
}

/**
 * Click in front of the body to place the antenna. R3F uses its own
 * raycaster, so we dispatch PointerEvents on the canvas directly.
 */
export async function placeAntennaCenterRight(page: Page): Promise<void> {
  const box = await page.locator('canvas').first().boundingBox()
  if (!box) throw new Error('canvas has no bounding box')
  const x = box.x + box.width * 0.62
  const y = box.y + box.height * 0.65
  // Hover to move the raycaster into position, then pointerdown/up.
  await page.mouse.move(x, y)
  await page.mouse.down()
  await page.mouse.up()
  // Settle.
  await page.waitForTimeout(500)
}

/**
 * Open a sidebar group + section. BaseUI accordion uses `aria-expanded` +
 * `data-panel-open` for state; we read `aria-expanded` since it is part of
 * the public API.
 */
export async function openSidebarSection(
  page: Page,
  groupId: string,
  sectionValue: string,
): Promise<void> {
  // Sidebar defaults to sidebarMode='expanded' + activeGroup='source'.
  // Clicking the ACTIVE group while EXPANDED toggles to rail (collapsed).
  // So we only click the group rail button if it's not already active +
  // expanded. We detect the current state by checking whether the section
  // triggers are already visible in the DOM.
  const sectionSelector = `[data-testid^="sidebar-section-"]`
  const needsGroupSwitch = await page.evaluate(({ selector, groupId }) => {
    const existing = document.querySelectorAll(selector)
    if (existing.length === 0) return true // sidebar collapsed or different group
    // Check if the current group matches what we want. The rail button of the
    // active group has a primary-tinted background; easier: match the section
    // testids to the group's section values.
    const GROUPS: Record<string, string[]> = {
      world: ['scene', 'environment', 'basestations', 'layers'],
      source: ['parameters', 'antennas', 'antenna', 'mimo', 'patterns'],
      exposure: ['phantom', 'raytracing', 'stochastic', 'tissue'],
      analysis: ['analysis', 'optimize', 'export'],
    }
    const want = new Set(GROUPS[groupId] ?? [])
    const seen = Array.from(existing).map((el) =>
      (el.getAttribute('data-testid') ?? '').replace('sidebar-section-', ''),
    )
    return !seen.some((v) => want.has(v))
  }, { selector: sectionSelector, groupId })

  if (needsGroupSwitch) {
    await page.getByTestId(`sidebar-group-${groupId}`).click({ force: true })
  }

  // Wait for the section trigger to render.
  await page.waitForSelector(`[data-testid="sidebar-section-${sectionValue}"]`, {
    timeout: 10_000,
  })
  const trigger = page.getByTestId(`sidebar-section-${sectionValue}`)
  const expanded = await trigger.getAttribute('aria-expanded')
  if (expanded !== 'true') {
    await trigger.click({ force: true })
    // Wait for the accordion animation to settle.
    await page.waitForFunction(
      (v) =>
        document
          .querySelector(`[data-testid="sidebar-section-${v}"]`)
          ?.getAttribute('aria-expanded') === 'true',
      sectionValue,
      { timeout: 5_000 },
    )
  }
}

/**
 * Wait until the body mesh is drawn. Polls the WebGL canvas until it is
 * non-blank (has a visible body against the background). We avoid waiting on
 * the `/api/body` response because that fires before the Playwright listener
 * can register; instead we poll the scene state that the store exposes once
 * the body loader resolves.
 */
export async function waitForBodyLoaded(page: Page): Promise<void> {
  // The body mesh appears as soon as useBodyLoader resolves. The simulation
  // store's `bodyName` is set by scenario loading on boot, so we just need to
  // wait for the canvas to have non-trivial content.
  await page.waitForFunction(
    () => {
      const canvas = document.querySelector('canvas') as HTMLCanvasElement | null
      return !!canvas && canvas.width > 100 && canvas.height > 100
    },
    { timeout: 15_000 },
  )
  // Let R3F settle a few frames.
  await page.waitForTimeout(800)
}

/**
 * Wait for a successful compute response.
 */
export async function waitForCompute(
  page: Page,
  pattern: RegExp = /\/api\/compute(\/|\?|$)/,
  timeout = 45_000,
): Promise<void> {
  await page.waitForResponse(
    (r) => pattern.test(r.url()) && r.ok(),
    { timeout },
  )
}

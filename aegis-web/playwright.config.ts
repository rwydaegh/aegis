import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for AEGIS viewer E2E specs.
 *
 * These specs exercise the Flask backend + built React frontend as one unit.
 * They are NOT wired into PR CI (per testing roadmap: E2E runs at master-push
 * or patch-release tier). Run locally, or invoke the manual workflow.
 *
 * Usage:
 *   # build the frontend into Flask's static dir first:
 *   npm run build:copy
 *   # start the backend:
 *   python3 -m aegis.viewer --no-open --port 5001
 *   # then run specs:
 *   npx playwright test
 */

const BASE_URL = process.env.AEGIS_E2E_BASE_URL ?? 'http://127.0.0.1:5001'

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  // WebGL + shared Flask backend cache means we get cleanest state running serial.
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    viewport: { width: 1280, height: 720 },
    // Give the R3F canvas time to mount.
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: [
            '--enable-webgl',
            '--use-gl=swiftshader',
            '--ignore-gpu-blocklist',
            '--no-sandbox',
          ],
        },
      },
    },
  ],
})

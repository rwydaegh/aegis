"""End-to-end Playwright tests for MIMO multi-user workflow.

Run with:
    xvfb-run python -m pytest tests/e2e/test_mimo_e2e.py -x -v

Requires: pip install pytest-playwright && playwright install chromium
Skipped automatically in CI (no playwright installed).

Only the console-error check is kept here. Pure-screenshot specs without
assertions were removed per the Phase 1 testing-infra cleanup (they were
test theater, not regression locks).
"""

import os
import re
from urllib.error import URLError
from urllib.request import urlopen

import pytest

playwright = pytest.importorskip("playwright")
from playwright.sync_api import Page, sync_playwright  # noqa: E402

BASE_URL = os.environ.get("AEGIS_E2E_BASE_URL", "http://localhost:5173")
TIMEOUT = 15_000  # ms


@pytest.fixture(scope="module")
def base_url():
    try:
        with urlopen(BASE_URL, timeout=2):
            pass
    except URLError:
        pytest.skip(f"E2E frontend not available at {BASE_URL}")
    return BASE_URL


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    pg = context.new_page()
    pg.set_default_timeout(TIMEOUT)
    pg.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
    # Wait for the app to load (AEGIS header visible)
    pg.wait_for_selector("text=AEGIS", timeout=TIMEOUT)
    # Give Three.js a moment to initialize
    pg.wait_for_timeout(2000)
    yield pg
    pg.close()
    context.close()


def _open_mimo_section(page: Page):
    """Expand the sidebar and open the MIMO accordion section."""
    source_btn = page.get_by_label("Source")
    source_btn.click()
    page.wait_for_timeout(300)
    mimo_trigger = page.get_by_role("button", name="MIMO")
    if mimo_trigger.count() > 0:
        mimo_trigger.first.click()
        page.wait_for_timeout(300)


def _enable_mimo(page: Page):
    """Enable MIMO mode via the sidebar checkbox."""
    _open_mimo_section(page)
    checkbox = page.get_by_label("Enable MIMO mode")
    if not checkbox.is_checked():
        checkbox.check()
    page.wait_for_timeout(500)


def test_no_console_errors_during_mimo_flow(page: Page):
    """Capture console errors during the full MIMO flow."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    _enable_mimo(page)
    page.get_by_role("button", name=re.compile("Duke")).click()
    page.wait_for_timeout(3000)
    page.get_by_role("button", name=re.compile("Ella")).click()
    page.wait_for_timeout(3000)

    real_errors = [e for e in errors if "THREE" not in e and "WebGL" not in e and "ResizeObserver" not in e]
    if real_errors:
        pytest.fail(f"Console errors during MIMO flow: {real_errors}")

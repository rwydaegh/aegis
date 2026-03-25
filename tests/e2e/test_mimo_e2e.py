"""End-to-end Playwright tests for MIMO multi-user workflow.

Run with:
    xvfb-run python -m pytest tests/e2e/test_mimo_e2e.py -x -v

Requires: pip install pytest-playwright && playwright install chromium
Skipped automatically in CI (no playwright installed).
"""

import re

import pytest

playwright = pytest.importorskip("playwright")
from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

BASE_URL = "http://localhost:5173"
TIMEOUT = 15_000  # ms


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    pg = context.new_page()
    pg.set_default_timeout(TIMEOUT)
    pg.goto(BASE_URL, wait_until="domcontentloaded", timeout=30_000)
    # Wait for the app to load (AEGIS header visible)
    pg.wait_for_selector("text=AEGIS", timeout=TIMEOUT)
    # Give Three.js a moment to initialize
    pg.wait_for_timeout(2000)
    yield pg
    pg.close()
    context.close()


def _enable_mimo(page: Page):
    """Enable MIMO mode via the sidebar checkbox."""
    # The MIMO accordion is always visible in the sidebar.
    # Click the "Enable MIMO mode" checkbox inside it.
    checkbox = page.get_by_label("Enable MIMO mode")
    if not checkbox.is_checked():
        checkbox.check()
    page.wait_for_timeout(500)


def _disable_mimo(page: Page):
    """Disable MIMO mode via the sidebar checkbox."""
    checkbox = page.get_by_label("Enable MIMO mode")
    if checkbox.is_checked():
        checkbox.uncheck()
    page.wait_for_timeout(500)


class TestMIMOToggle:
    """Test enabling/disabling MIMO mode."""

    def test_mimo_checkbox_exists(self, page: Page):
        checkbox = page.get_by_label("Enable MIMO mode")
        expect(checkbox).to_be_visible()

    def test_enable_mimo_shows_panel(self, page: Page):
        _enable_mimo(page)
        # Precoder buttons should appear
        expect(page.get_by_role("button", name="MRT").first).to_be_visible(timeout=5000)

    def test_enable_mimo_auto_adds_user(self, page: Page):
        _enable_mimo(page)
        # Enabling MIMO should auto-add User 1 from the current phantom
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)

    def test_disable_mimo_hides_panel(self, page: Page):
        _enable_mimo(page)
        expect(page.get_by_role("button", name="MRT").first).to_be_visible(timeout=5000)
        _disable_mimo(page)
        # Precoder buttons should disappear
        expect(page.get_by_role("button", name="MRT").first).not_to_be_visible(timeout=5000)


class TestMIMOAddRemoveUsers:
    """Test adding and removing MIMO users."""

    def test_add_extra_user(self, page: Page):
        _enable_mimo(page)
        # User 1 already exists from auto-add. Add Duke as User 2.
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 2")).to_be_visible(timeout=5000)

    def test_add_two_extra_users(self, page: Page):
        _enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name=re.compile("Ella")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 2")).to_be_visible(timeout=5000)
        expect(page.get_by_text("User 3")).to_be_visible(timeout=5000)

    def test_remove_user(self, page: Page):
        _enable_mimo(page)
        # Auto-added User 1 should be visible
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)
        # Remove the user
        page.get_by_title("Remove user").first.click()
        page.wait_for_timeout(500)
        expect(page.get_by_text("User 1")).not_to_be_visible(timeout=5000)

    def test_add_multiple_phantoms(self, page: Page):
        _enable_mimo(page)
        # User 1 auto-added. Add 3 more.
        for name in ["Duke", "Ella", "Eartha"]:
            page.get_by_role("button", name=re.compile(name)).click()
            page.wait_for_timeout(500)
        # Should have 4 users total
        expect(page.get_by_text("User 4")).to_be_visible(timeout=5000)


class TestMIMOCompute:
    """Test MIMO computation triggers and results."""

    def _enable_mimo_and_add_user(self, page: Page, phantom="Duke"):
        _enable_mimo(page)
        # User 1 is auto-added. Add another if requested.
        page.get_by_role("button", name=re.compile(phantom)).click()
        page.wait_for_timeout(500)

    def test_compute_fires_after_adding_user(self, page: Page):
        self._enable_mimo_and_add_user(page)
        page.wait_for_timeout(5000)
        page.screenshot(path="/tmp/mimo-after-add-user.png")

    def test_precoder_buttons_visible(self, page: Page):
        _enable_mimo(page)
        for name in ["MRT", "ZF", "MMSE"]:
            expect(page.get_by_role("button", name=name).first).to_be_visible()

    def test_switch_precoder(self, page: Page):
        self._enable_mimo_and_add_user(page)
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="MRT").first.click()
        page.wait_for_timeout(3000)
        page.screenshot(path="/tmp/mimo-mrt-precoder.png")

    def test_two_users_compute(self, page: Page):
        self._enable_mimo_and_add_user(page, "Duke")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name=re.compile("Ella")).click()
        page.wait_for_timeout(5000)
        page.screenshot(path="/tmp/mimo-two-users.png")


class TestMIMOEdgeCases:
    """Test edge cases in MIMO mode."""

    def test_toggle_mimo_preserves_users(self, page: Page):
        _enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 2")).to_be_visible(timeout=5000)
        # Disable MIMO
        _disable_mimo(page)
        # Re-enable MIMO
        _enable_mimo(page)
        # User 2 should still be there (users persist across toggle)
        expect(page.get_by_text("User 2")).to_be_visible(timeout=5000)

    def test_rapid_add_remove(self, page: Page):
        _enable_mimo(page)
        for _ in range(3):
            page.get_by_role("button", name=re.compile("Duke")).click()
            page.wait_for_timeout(200)
        page.wait_for_timeout(1000)
        page.screenshot(path="/tmp/mimo-rapid-add.png")

    def test_focus_user(self, page: Page):
        _enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        focus_btn = page.get_by_title("Focus camera")
        if focus_btn.count() > 0:
            focus_btn.first.click()
            page.wait_for_timeout(500)
        page.screenshot(path="/tmp/mimo-focus-user.png")

    def test_no_console_errors_during_mimo_flow(self, page: Page):
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

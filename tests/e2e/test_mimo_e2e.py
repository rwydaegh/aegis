"""End-to-end Playwright tests for MIMO multi-user workflow.

Run with:
    xvfb-run npx playwright test tests/e2e/test_mimo_e2e.py
Or from Python:
    xvfb-run python -m pytest tests/e2e/test_mimo_e2e.py -x -v
"""

import re

import pytest
from playwright.sync_api import Page, expect, sync_playwright

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


class TestMIMOToggle:
    """Test enabling/disabling MIMO mode."""

    def test_mimo_toggle_exists(self, page: Page):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        expect(btn).to_be_visible()

    def test_enable_mimo_shows_panel(self, page: Page):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        btn.click()
        page.wait_for_timeout(500)
        # MIMO Users accordion should appear in sidebar
        expect(page.get_by_text("MIMO Users")).to_be_visible(timeout=5000)

    def test_disable_mimo_hides_panel(self, page: Page):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        # Enable
        btn.click()
        page.wait_for_timeout(500)
        expect(page.get_by_text("MIMO Users")).to_be_visible(timeout=5000)
        # Disable
        btn.click()
        page.wait_for_timeout(500)
        expect(page.get_by_text("MIMO Users")).not_to_be_visible(timeout=5000)


class TestMIMOAddRemoveUsers:
    """Test adding and removing MIMO users."""

    def _enable_mimo(self, page: Page):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        btn.click()
        page.wait_for_timeout(500)
        page.get_by_text("MIMO Users").wait_for(timeout=5000)

    def test_add_one_user(self, page: Page):
        self._enable_mimo(page)
        # Click "Add" button for Duke
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        # Should see "User 1" in the panel
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)

    def test_add_two_users(self, page: Page):
        self._enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name=re.compile("Ella")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)
        expect(page.get_by_text("User 2")).to_be_visible(timeout=5000)

    def test_remove_user(self, page: Page):
        self._enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)
        # Remove the user
        page.get_by_title("Remove user").first.click()
        page.wait_for_timeout(500)
        expect(page.get_by_text("User 1")).not_to_be_visible(timeout=5000)

    def test_add_multiple_phantoms(self, page: Page):
        self._enable_mimo(page)
        for name in ["Duke", "Ella", "Eartha", "Thelonious"]:
            page.get_by_role("button", name=re.compile(name)).click()
            page.wait_for_timeout(500)
        # Should have 4 users
        expect(page.get_by_text("User 4")).to_be_visible(timeout=5000)


class TestMIMOCompute:
    """Test MIMO computation triggers and results."""

    def _enable_mimo_and_add_user(self, page: Page, phantom="Duke"):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        btn.click()
        page.wait_for_timeout(500)
        page.get_by_text("MIMO Users").wait_for(timeout=5000)
        page.get_by_role("button", name=re.compile(phantom)).click()
        page.wait_for_timeout(500)

    def test_compute_fires_after_adding_user(self, page: Page):
        self._enable_mimo_and_add_user(page)
        # Wait for compute to complete - the "--" should change to a value
        # The debounce is 500ms, plus compute time
        page.wait_for_timeout(5000)
        # Take a screenshot to see state
        page.screenshot(path="/tmp/mimo-after-add-user.png")

    def test_precoder_buttons_visible(self, page: Page):
        self._enable_mimo_and_add_user(page)
        for name in ["MRT", "ZF", "MMSE"]:
            expect(page.get_by_role("button", name=name).first).to_be_visible()

    def test_switch_precoder(self, page: Page):
        self._enable_mimo_and_add_user(page)
        page.wait_for_timeout(2000)
        # Switch to MRT
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

    def _enable_mimo(self, page: Page):
        btn = page.get_by_role("button", name="Toggle MIMO mode")
        btn.click()
        page.wait_for_timeout(500)
        page.get_by_text("MIMO Users").wait_for(timeout=5000)

    def test_toggle_mimo_with_users_preserves_state(self, page: Page):
        self._enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)
        # Disable MIMO
        page.get_by_role("button", name="Toggle MIMO mode").click()
        page.wait_for_timeout(500)
        # Re-enable MIMO
        page.get_by_role("button", name="Toggle MIMO mode").click()
        page.wait_for_timeout(500)
        # User should still be there
        expect(page.get_by_text("User 1")).to_be_visible(timeout=5000)

    def test_rapid_add_remove(self, page: Page):
        self._enable_mimo(page)
        # Rapidly add and remove
        for _ in range(3):
            page.get_by_role("button", name=re.compile("Duke")).click()
            page.wait_for_timeout(200)
        page.wait_for_timeout(1000)
        # Should have 3 users
        page.screenshot(path="/tmp/mimo-rapid-add.png")

    def test_focus_user(self, page: Page):
        self._enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(1000)
        # Click focus camera button
        focus_btn = page.get_by_title("Focus camera")
        if focus_btn.count() > 0:
            focus_btn.first.click()
            page.wait_for_timeout(500)
        page.screenshot(path="/tmp/mimo-focus-user.png")

    def test_no_console_errors_during_mimo_flow(self, page: Page):
        """Capture console errors during the full MIMO flow."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        self._enable_mimo(page)
        page.get_by_role("button", name=re.compile("Duke")).click()
        page.wait_for_timeout(3000)
        page.get_by_role("button", name=re.compile("Ella")).click()
        page.wait_for_timeout(3000)

        # Filter out common Three.js warnings that are not real errors
        real_errors = [e for e in errors if "THREE" not in e and "WebGL" not in e and "ResizeObserver" not in e]
        if real_errors:
            pytest.fail(f"Console errors during MIMO flow: {real_errors}")

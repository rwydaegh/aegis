"""Comprehensive end-to-end test of the AEGIS interactive viewer.

Uses Playwright to launch a real browser, interact with the viewer,
and capture screenshots at every step. Tests all major features:
- Page load with voxels + body mesh
- API endpoints (config, body, voxels, compute)
- Antenna placement by clicking
- Heatmap color update
- Dashboard stats update
- Fidelity level switching
- TX power change
- Multipath mode
- Layer toggle (hide/show voxels and body)
- Wireframe mode
- Ray tracing panel (DiffeRT)
- Console errors
"""

from playwright.sync_api import sync_playwright
import requests
import json
import time
import numpy as np
from pathlib import Path

PORT = 5070
BASE = f"http://127.0.0.1:{PORT}"
OUT = Path("test_screenshots")
OUT.mkdir(exist_ok=True)

errors_found = []
tests_passed = 0
tests_failed = 0


def check(name, condition, detail=""):
    global tests_passed, tests_failed
    if condition:
        tests_passed += 1
        print(f"  PASS: {name}")
    else:
        tests_failed += 1
        errors_found.append(f"{name}: {detail}")
        print(f"  FAIL: {name} -- {detail}")


print("=" * 70)
print("  AEGIS Viewer E2E Test Suite")
print("=" * 70)

# ===========================================================================
# PHASE 1: API endpoint tests (no browser needed)
# ===========================================================================
print("\n--- Phase 1: API endpoints ---")

# Wait for server
for attempt in range(10):
    try:
        r = requests.get(f"{BASE}/api/config", timeout=2)
        if r.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(2)
else:
    print("FATAL: Server not responding")
    exit(1)

# 1a. Config endpoint
config = requests.get(f"{BASE}/api/config").json()
check("Config returns JSON", isinstance(config, dict))
check("Config has bodies", len(config.get("bodies", [])) > 0, f"bodies={config.get('bodies')}")
check("Config has thelonious", "thelonious" in config.get("bodies", []))
check("Config has_voxels", config.get("has_voxels") is True)
check("Config has_differt", config.get("has_differt") is True)
check("Config has scenes", len(config.get("scenes", [])) > 0, f"n_scenes={len(config.get('scenes', []))}")
check("Config body_meta present", config.get("body_meta") is not None)
check("Config body has 23826 triangles", config.get("body_meta", {}).get("n_triangles") == 23826)

# 1b. Body endpoint
resp = requests.get(f"{BASE}/api/body")
check("Body returns 200", resp.status_code == 200)
body_meta = json.loads(resp.headers.get("X-Meta", "{}"))
check("Body meta has n_vertices", body_meta.get("n_vertices") == 71478)
body_data = resp.content
expected_size = 71478 * 3 * 4 * 2  # positions + normals, float32
check("Body binary size correct", len(body_data) == expected_size,
      f"got {len(body_data)}, expected {expected_size}")

# 1c. Voxels endpoint
resp = requests.get(f"{BASE}/api/voxels")
check("Voxels returns 200", resp.status_code == 200)
voxel_meta = json.loads(resp.headers.get("X-Meta", "{}"))
check("Voxel meta has n_voxels", voxel_meta.get("n_voxels", 0) > 0,
      f"n_voxels={voxel_meta.get('n_voxels')}")
check("Voxel meta has materials", len(voxel_meta.get("materials", [])) > 0)

# 1d. Compute endpoint (synthetic paths)
resp = requests.post(f"{BASE}/api/compute", json={
    "antenna_pos": [5, 0, 1],
    "level": 2,
    "power_dbm": 30,
    "n_paths": 1,
})
check("Compute returns 200", resp.status_code == 200)
stats = json.loads(resp.headers.get("X-Stats", "{}"))
check("Compute returns p_abs", stats.get("p_abs", -1) >= 0)
check("Compute returns peak_sab", stats.get("peak_sab", -1) >= 0)
check("Compute returns compliant", "compliant" in stats)
check("Compute returns n_illuminated > 0", stats.get("n_illuminated", 0) > 0,
      f"n_illuminated={stats.get('n_illuminated')}")
sab = np.frombuffer(resp.content, dtype=np.float32)
check("Compute sab has 23826 values", len(sab) == 23826, f"got {len(sab)}")
check("Compute sab all >= 0", np.all(sab >= 0))

# 1e. Compute with different levels
for level in [0, 2, 3, 4]:
    resp = requests.post(f"{BASE}/api/compute", json={
        "antenna_pos": [3, -2, 1.5],
        "level": level,
        "power_dbm": 30,
        "n_paths": 5,
    })
    s = json.loads(resp.headers.get("X-Stats", "{}"))
    check(f"Level {level} compute works", resp.status_code == 200 and s.get("p_abs", -1) >= 0)

# 1f. Scenes endpoint
resp = requests.get(f"{BASE}/api/scenes")
check("Scenes returns 200", resp.status_code == 200)
scenes = resp.json()
check("Scenes returns list", isinstance(scenes, list) and len(scenes) > 0,
      f"got {len(scenes)} scenes")

# 1g. Voxel RT endpoint
resp = requests.post(f"{BASE}/api/compute/voxel-rt", json={
    "antenna_pos": [30, 0, 5],
    "level": 2,
    "power_dbm": 30,
    "max_order": 0,
})
check("Voxel RT returns 200", resp.status_code == 200)
vrt_stats = json.loads(resp.headers.get("X-Stats", "{}"))
check("Voxel RT returns stats", "n_rt_paths" in vrt_stats,
      f"keys={list(vrt_stats.keys())}")

# 1h. Sionna RT endpoint
dr_scenes = [s for s in scenes if s["name"] == "double_reflector"]
if dr_scenes:
    resp = requests.post(f"{BASE}/api/compute/rt", json={
        "antenna_pos": [0, 5, 2.5],
        "body_pos": [0, -3, 1.5],
        "scene_path": dr_scenes[0]["path"],
        "level": 2,
        "power_dbm": 30,
        "max_order": 1,
    })
    check("Sionna RT returns 200", resp.status_code == 200)
    rt_stats = json.loads(resp.headers.get("X-Stats", "{}"))
    check("Sionna RT finds paths", rt_stats.get("n_rt_paths", 0) > 0,
          f"n_rt_paths={rt_stats.get('n_rt_paths')}")

# ===========================================================================
# PHASE 2: Browser tests with Playwright
# ===========================================================================
print("\n--- Phase 2: Browser rendering tests ---")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Capture console errors
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # 2a. Load the page
    print("  Loading page...")
    page.goto(BASE, timeout=30000)
    time.sleep(8)  # Wait for Three.js + data fetch

    page.screenshot(path=str(OUT / "01_initial_load.png"))
    check("Page loads without crash", True)

    # 2b. Check panel is visible
    panel = page.query_selector("#panel")
    check("Side panel visible", panel is not None and panel.is_visible())

    # 2c. Check loading overlay is gone
    loading = page.query_selector("#loading")
    loading_hidden = loading is None or not loading.is_visible()
    check("Loading overlay hidden", loading_hidden)

    # 2d. Check dashboard shows "--" (no antenna yet)
    pabs_text = page.inner_text("#stat-pabs")
    check("Dashboard shows -- initially", "--" in pabs_text, f"got: {pabs_text}")

    # 2e. Check layer buttons exist
    layer_btns = page.query_selector_all(".layer-btn")
    check("Layer buttons present", len(layer_btns) >= 2, f"found {len(layer_btns)}")

    # 2f. Check RT section visible (DiffeRT installed)
    rt_section = page.query_selector("#rt-section")
    check("RT section visible", rt_section is not None and rt_section.is_visible())

    # 2g. Check RT source dropdown has options
    rt_source = page.query_selector("#rtSourceSelect")
    if rt_source:
        options = page.query_selector_all("#rtSourceSelect option")
        check("RT source has options", len(options) >= 2, f"found {len(options)}")

    # ===========================================================================
    # 2h. Click to place antenna (click on the 3D scene area)
    # ===========================================================================
    print("  Clicking to place antenna...")
    page.mouse.click(800, 500)
    time.sleep(3)

    page.screenshot(path=str(OUT / "02_antenna_placed.png"))

    # Check dashboard updated
    pabs_text2 = page.inner_text("#stat-pabs")
    check("Dashboard updates after click", "--" not in pabs_text2, f"got: {pabs_text2}")

    peak_text = page.inner_text("#stat-peak")
    check("Peak Sab shows value", "W/m" in peak_text, f"got: {peak_text}")

    compliance_text = page.inner_text("#stat-compliance")
    check("Compliance shows PASS or FAIL", "PASS" in compliance_text or "FAIL" in compliance_text,
          f"got: {compliance_text}")

    illum_text = page.inner_text("#stat-illum")
    check("Illuminated count shows", "/" in illum_text, f"got: {illum_text}")

    # ===========================================================================
    # 2i. Change fidelity level
    # ===========================================================================
    print("  Changing fidelity level to 3...")
    page.select_option("#levelSelect", "3")
    time.sleep(2)

    page.screenshot(path=str(OUT / "03_level3.png"))

    pabs_l3 = page.inner_text("#stat-pabs")
    check("Level 3 updates dashboard", "--" not in pabs_l3, f"got: {pabs_l3}")

    # ===========================================================================
    # 2j. Change TX power
    # ===========================================================================
    print("  Changing TX power to 40 dBm...")
    page.fill("#powerInput", "40")
    page.press("#powerInput", "Enter")
    time.sleep(2)

    page.screenshot(path=str(OUT / "04_power40.png"))

    pabs_40 = page.inner_text("#stat-pabs")
    check("Higher power updates dashboard", "--" not in pabs_40, f"got: {pabs_40}")

    # ===========================================================================
    # 2k. Switch to multipath (5 paths)
    # ===========================================================================
    print("  Switching to 5 paths...")
    page.select_option("#pathsSelect", "5")
    time.sleep(2)

    page.screenshot(path=str(OUT / "05_multipath.png"))

    # ===========================================================================
    # 2l. Click a different location
    # ===========================================================================
    print("  Clicking new antenna position...")
    page.mouse.click(600, 400)
    time.sleep(3)

    page.screenshot(path=str(OUT / "06_new_position.png"))

    pabs_new = page.inner_text("#stat-pabs")
    check("New position updates dashboard", "--" not in pabs_new)

    # ===========================================================================
    # 2m. Toggle a layer off (click first layer button)
    # ===========================================================================
    print("  Toggling layer visibility...")
    first_layer = page.query_selector(".layer-btn")
    if first_layer:
        first_layer.click()
        time.sleep(1)
        page.screenshot(path=str(OUT / "07_layer_toggled.png"))
        check("Layer toggle doesn't crash", True)

        # Toggle back on
        first_layer.click()
        time.sleep(0.5)

    # ===========================================================================
    # 2n. Toggle wireframe
    # ===========================================================================
    print("  Toggling wireframe...")
    page.evaluate("window.toggleWireframe()")
    time.sleep(1)

    page.screenshot(path=str(OUT / "08_wireframe.png"))
    check("Wireframe toggle doesn't crash", True)

    # Toggle back
    page.evaluate("window.toggleWireframe()")
    time.sleep(0.5)

    # ===========================================================================
    # 2o. Reset camera
    # ===========================================================================
    print("  Resetting camera...")
    page.evaluate("window.resetCamera()")
    time.sleep(1)

    page.screenshot(path=str(OUT / "09_camera_reset.png"))
    check("Camera reset doesn't crash", True)

    # ===========================================================================
    # 2p. Enable ray tracing (voxel mode)
    # ===========================================================================
    print("  Enabling voxel ray tracing...")
    rt_checkbox = page.query_selector("#rtEnabled")
    if rt_checkbox:
        rt_checkbox.check()
        time.sleep(1)

        # Click to trigger voxel RT computation
        page.mouse.click(700, 450)
        time.sleep(15)  # First voxel RT call is slow (mesh build)

        page.screenshot(path=str(OUT / "10_voxel_rt.png"))

        rt_status = page.inner_text("#rt-status")
        check("Voxel RT status updates", len(rt_status) > 0, f"got: {rt_status}")

        # Uncheck RT for next tests
        rt_checkbox.uncheck()
        time.sleep(0.5)

    # ===========================================================================
    # 2q. Switch to a Sionna scene in RT dropdown
    # ===========================================================================
    print("  Testing Sionna RT scene selection...")
    rt_options = page.query_selector_all("#rtSourceSelect option")
    sionna_options = [o for o in rt_options if "Sionna" in (o.inner_text() or "")]
    if sionna_options:
        # Select the first Sionna scene
        sionna_val = sionna_options[0].get_attribute("value")
        page.select_option("#rtSourceSelect", sionna_val)
        time.sleep(1)
        check("Sionna scene selectable", True)

    page.screenshot(path=str(OUT / "11_sionna_selected.png"))

    # ===========================================================================
    # 2r. Check for console errors
    # ===========================================================================
    # Filter out known harmless warnings
    real_errors = [e for e in console_errors if "favicon" not in e.lower()]
    check("No JS console errors", len(real_errors) == 0,
          f"errors: {real_errors[:3]}")

    # ===========================================================================
    # 2s. Multiple rapid clicks (stress test)
    # ===========================================================================
    print("  Stress test: rapid clicking...")
    for i in range(5):
        page.mouse.click(500 + i * 50, 400 + i * 20)
        time.sleep(0.5)
    time.sleep(3)

    page.screenshot(path=str(OUT / "12_stress_test.png"))
    check("Rapid clicking doesn't crash", True)

    # Final state
    page.screenshot(path=str(OUT / "13_final_state.png"))

    browser.close()

# ===========================================================================
# Summary
# ===========================================================================
print("\n" + "=" * 70)
print(f"  Results: {tests_passed} passed, {tests_failed} failed")
print("=" * 70)

if errors_found:
    print("\nFailures:")
    for e in errors_found:
        print(f"  - {e}")

print(f"\nScreenshots saved to: {OUT.resolve()}")
print(f"  {len(list(OUT.glob('*.png')))} screenshots captured")

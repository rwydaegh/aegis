"""End-to-end test of the AEGIS interactive viewer (API + Playwright).

Default profile ``lab`` targets ``configs/e2e_lab.json``: tracked icosahedron, no voxels,
deterministic synthetic multipath. Use ``full`` for a Thelonious + voxels + DiffeRT demo.

Start the server first, for example::

    py -3.12 -m aegis.viewer --config configs/e2e_lab.json --no-open

Then::

    py -3.12 test_viewer_e2e.py --base http://127.0.0.1:5070 --profile lab
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
from playwright.sync_api import sync_playwright


def check(
    name: str,
    condition: bool,
    detail: str = "",
    errors: list[str] | None = None,
    counters: list[int] | None = None,
) -> None:
    if counters is None:
        counters = [0, 0]
    if errors is None:
        errors = []
    if condition:
        counters[0] += 1
        print(f"  PASS: {name}")
    else:
        counters[1] += 1
        errors.append(f"{name}: {detail}")
        print(f"  FAIL: {name} -- {detail}")


def run_e2e(base_url: str, profile: str) -> int:
    base = base_url.rstrip("/")
    out = Path("test_screenshots")
    out.mkdir(exist_ok=True)
    errors: list[str] = []
    counters = [0, 0]  # passed, failed

    print("=" * 70)
    print("  AEGIS Viewer E2E Test Suite")
    print(f"  base={base} profile={profile}")
    print("=" * 70)

    # --- Phase 1: API ---
    print("\n--- Phase 1: API endpoints ---")

    for _ in range(10):
        try:
            r = requests.get(f"{base}/api/config", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("FATAL: Server not responding")
        return 1

    config = requests.get(f"{base}/api/config", timeout=10).json()
    check("Config returns JSON", isinstance(config, dict), errors=errors, counters=counters)
    check(
        "Config has bodies",
        len(config.get("bodies", [])) > 0,
        f"bodies={config.get('bodies')}",
        errors=errors,
        counters=counters,
    )

    has_voxels = bool(config.get("has_voxels"))
    voxel_rt_available = bool(config.get("voxel_rt_available"))
    has_differt = bool(config.get("has_differt"))
    scenes = config.get("scenes") or []
    has_sionna = len(scenes) > 0
    expect_rt_panel = has_differt and (voxel_rt_available or has_sionna)
    cfg_body_meta = config.get("body_meta") or {}
    n_tri = int(cfg_body_meta.get("n_triangles") or 0)
    n_vert = int(cfg_body_meta.get("n_vertices") or 0)

    if profile == "lab":
        check(
            "lab: fixture body listed",
            "e2e_icosahedron" in config.get("bodies", []),
            f"bodies={config.get('bodies')}",
            errors=errors,
            counters=counters,
        )
        check("lab: no voxels", not has_voxels, f"has_voxels={has_voxels}", errors=errors, counters=counters)
        check("lab: icosahedron triangle count", n_tri == 20, f"n_triangles={n_tri}", errors=errors, counters=counters)
        check("lab: vertex count", n_vert == 60, f"n_vertices={n_vert}", errors=errors, counters=counters)
    else:
        check("full: thelonious available", "thelonious" in config.get("bodies", []), errors=errors, counters=counters)
        check("full: has_voxels", has_voxels, errors=errors, counters=counters)
        check("full: has_differt", has_differt, errors=errors, counters=counters)
        check("full: has scenes", len(scenes) > 0, f"n_scenes={len(scenes)}", errors=errors, counters=counters)
        check("full: body_meta present", cfg_body_meta.get("n_triangles") is not None, errors=errors, counters=counters)
        check("full: thelonious triangles", n_tri == 23826, f"got {n_tri}", errors=errors, counters=counters)

    check("Config body_meta present", cfg_body_meta.get("n_triangles") is not None, errors=errors, counters=counters)

    resp = requests.get(f"{base}/api/body", timeout=10)
    check("Body returns 200", resp.status_code == 200, errors=errors, counters=counters)
    body_hdr_meta = json.loads(resp.headers.get("X-Meta", "{}"))
    hdr_nv = body_hdr_meta.get("n_vertices")
    check(
        "Body header meta matches config",
        hdr_nv == n_vert,
        f"header n_vertices={hdr_nv} config={n_vert}",
        errors=errors,
        counters=counters,
    )
    body_data = resp.content
    expected_size = n_vert * 3 * 4 * 2
    check(
        "Body binary size correct",
        len(body_data) == expected_size,
        f"got {len(body_data)}, expected {expected_size}",
        errors=errors,
        counters=counters,
    )

    if has_voxels:
        resp = requests.get(f"{base}/api/voxels", timeout=10)
        check("Voxels returns 200", resp.status_code == 200, errors=errors, counters=counters)
        voxel_meta = json.loads(resp.headers.get("X-Meta", "{}"))
        check(
            "Voxel meta has n_voxels",
            voxel_meta.get("n_voxels", 0) > 0,
            f"n_voxels={voxel_meta.get('n_voxels')}",
            errors=errors,
            counters=counters,
        )
        check(
            "Voxel meta has materials",
            len(voxel_meta.get("materials", [])) > 0,
            errors=errors,
            counters=counters,
        )
    else:
        resp = requests.get(f"{base}/api/voxels", timeout=10)
        check(
            "Voxels absent returns 404",
            resp.status_code == 404,
            f"status={resp.status_code}",
            errors=errors,
            counters=counters,
        )

    resp = requests.post(
        f"{base}/api/compute",
        json={
            "antenna_pos": [0.5, 0, 0.15],
            "level": 2,
            "power_dbm": 30,
            "n_paths": 1,
        },
        timeout=10,
    )
    check("Compute returns 200", resp.status_code == 200, errors=errors, counters=counters)
    stats = json.loads(resp.headers.get("X-Stats", "{}"))
    check("Compute returns p_abs", stats.get("p_abs", -1) >= 0, errors=errors, counters=counters)
    check("Compute returns peak_sab", stats.get("peak_sab", -1) >= 0, errors=errors, counters=counters)
    check("Compute returns compliant", "compliant" in stats, errors=errors, counters=counters)
    check(
        "Compute returns n_illuminated > 0",
        stats.get("n_illuminated", 0) > 0,
        f"n_illuminated={stats.get('n_illuminated')}",
        errors=errors,
        counters=counters,
    )
    sab = np.frombuffer(resp.content, dtype=np.float32)
    check("Compute sab length matches mesh", len(sab) == n_tri, f"got {len(sab)}", errors=errors, counters=counters)
    check("Compute sab all >= 0", np.all(sab >= 0), errors=errors, counters=counters)

    for level in [0, 2, 3, 4]:
        resp = requests.post(
            f"{base}/api/compute",
            json={
                "antenna_pos": [0.35, -0.2, 0.12],
                "level": level,
                "power_dbm": 30,
                "n_paths": 5,
            },
            timeout=10,
        )
        s = json.loads(resp.headers.get("X-Stats", "{}"))
        check(
            f"Level {level} compute works",
            resp.status_code == 200 and s.get("p_abs", -1) >= 0,
            errors=errors,
            counters=counters,
        )

    resp = requests.get(f"{base}/api/scenes", timeout=10)
    check("Scenes returns 200", resp.status_code == 200, errors=errors, counters=counters)
    scenes_api = resp.json()
    check(
        "Scenes returns list", isinstance(scenes_api, list), f"got {type(scenes_api)}", errors=errors, counters=counters
    )
    if profile == "full":
        check("Scenes non-empty", len(scenes_api) > 0, f"got {len(scenes_api)}", errors=errors, counters=counters)

    resp = requests.post(
        f"{base}/api/compute/voxel-rt",
        json={
            "antenna_pos": [30, 0, 5],
            "level": 2,
            "power_dbm": 30,
            "max_order": 0,
        },
        timeout=10,
    )
    if voxel_rt_available:
        check("Voxel RT returns 200", resp.status_code == 200, errors=errors, counters=counters)
        vrt_stats = json.loads(resp.headers.get("X-Stats", "{}"))
        check(
            "Voxel RT returns stats",
            "n_rt_paths" in vrt_stats,
            f"keys={list(vrt_stats.keys())}",
            errors=errors,
            counters=counters,
        )
    else:
        check(
            "Voxel RT unavailable returns 400",
            resp.status_code == 400,
            f"status={resp.status_code}",
            errors=errors,
            counters=counters,
        )

    dr_scenes = [s for s in scenes_api if s.get("name") == "double_reflector"]
    if dr_scenes and has_differt:
        resp = requests.post(
            f"{base}/api/compute/rt",
            json={
                "antenna_pos": [0, 5, 2.5],
                "body_pos": [0, -3, 1.5],
                "scene_path": dr_scenes[0]["path"],
                "level": 2,
                "power_dbm": 30,
                "max_order": 1,
            },
            timeout=10,
        )
        check("Sionna RT returns 200", resp.status_code == 200, errors=errors, counters=counters)
        rt_stats = json.loads(resp.headers.get("X-Stats", "{}"))
        check(
            "Sionna RT finds paths",
            rt_stats.get("n_rt_paths", 0) > 0,
            f"n_rt_paths={rt_stats.get('n_rt_paths')}",
            errors=errors,
            counters=counters,
        )

    # --- Phase 2: Browser ---
    print("\n--- Phase 2: Browser rendering tests ---")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("  Loading page...")
        page.goto(base, timeout=30000)
        time.sleep(8)

        page.screenshot(path=str(out / "01_initial_load.png"))
        check("Page loads without crash", True, errors=errors, counters=counters)

        panel = page.query_selector("#panel")
        check("Side panel visible", panel is not None and panel.is_visible(), errors=errors, counters=counters)

        loading = page.query_selector("#loading")
        loading_hidden = loading is None or not loading.is_visible()
        check("Loading overlay hidden", loading_hidden, errors=errors, counters=counters)

        pabs_text = page.inner_text("#stat-pabs")
        check("Dashboard shows -- initially", "--" in pabs_text, f"got: {pabs_text}", errors=errors, counters=counters)

        layer_btns = page.query_selector_all(".layer-btn")
        min_layers = 2 if has_voxels else 1
        check(
            "Layer buttons present",
            len(layer_btns) >= min_layers,
            f"found {len(layer_btns)}",
            errors=errors,
            counters=counters,
        )

        rt_section = page.query_selector("#rt-section")
        rt_visible = rt_section is not None and rt_section.is_visible()
        check(
            "RT panel visibility matches backend",
            rt_visible == expect_rt_panel,
            f"visible={rt_visible} expected={expect_rt_panel}",
            errors=errors,
            counters=counters,
        )

        if expect_rt_panel:
            rt_source = page.query_selector("#rtSourceSelect")
            if rt_source:
                options = page.query_selector_all("#rtSourceSelect option")
                check(
                    "RT source has options",
                    len(options) >= 1,
                    f"found {len(options)}",
                    errors=errors,
                    counters=counters,
                )

        print("  Clicking to place antenna...")
        page.mouse.click(800, 500)
        time.sleep(3)

        page.screenshot(path=str(out / "02_antenna_placed.png"))

        pabs_text2 = page.inner_text("#stat-pabs")
        check(
            "Dashboard updates after click",
            "--" not in pabs_text2,
            f"got: {pabs_text2}",
            errors=errors,
            counters=counters,
        )

        peak_text = page.inner_text("#stat-peak")
        check("Peak Sab shows value", "W/m" in peak_text, f"got: {peak_text}", errors=errors, counters=counters)

        compliance_text = page.inner_text("#stat-compliance")
        check(
            "Compliance shows PASS or FAIL",
            "PASS" in compliance_text or "FAIL" in compliance_text,
            f"got: {compliance_text}",
            errors=errors,
            counters=counters,
        )

        illum_text = page.inner_text("#stat-illum")
        check("Illuminated count shows", "/" in illum_text, f"got: {illum_text}", errors=errors, counters=counters)

        print("  Changing fidelity level to 3...")
        page.select_option("#levelSelect", "3")
        time.sleep(2)

        page.screenshot(path=str(out / "03_level3.png"))

        pabs_l3 = page.inner_text("#stat-pabs")
        check("Level 3 updates dashboard", "--" not in pabs_l3, f"got: {pabs_l3}", errors=errors, counters=counters)

        print("  Changing TX power to 40 dBm...")
        page.fill("#powerInput", "40")
        page.press("#powerInput", "Enter")
        time.sleep(2)

        page.screenshot(path=str(out / "04_power40.png"))

        pabs_40 = page.inner_text("#stat-pabs")
        check(
            "Higher power updates dashboard", "--" not in pabs_40, f"got: {pabs_40}", errors=errors, counters=counters
        )

        print("  Switching to 5 paths...")
        page.select_option("#pathsSelect", "5")
        time.sleep(2)

        page.screenshot(path=str(out / "05_multipath.png"))

        print("  Clicking new antenna position...")
        page.mouse.click(600, 400)
        time.sleep(3)

        page.screenshot(path=str(out / "06_new_position.png"))

        pabs_new = page.inner_text("#stat-pabs")
        check("New position updates dashboard", "--" not in pabs_new, errors=errors, counters=counters)

        print("  Toggling layer visibility...")
        first_layer = page.query_selector(".layer-btn")
        if first_layer:
            first_layer.click()
            time.sleep(1)
            page.screenshot(path=str(out / "07_layer_toggled.png"))
            check("Layer toggle doesn't crash", True, errors=errors, counters=counters)
            first_layer.click()
            time.sleep(0.5)

        print("  Toggling wireframe...")
        page.evaluate("window.toggleWireframe()")
        time.sleep(1)

        page.screenshot(path=str(out / "08_wireframe.png"))
        check("Wireframe toggle doesn't crash", True, errors=errors, counters=counters)

        page.evaluate("window.toggleWireframe()")
        time.sleep(0.5)

        print("  Resetting camera...")
        page.evaluate("window.resetCamera()")
        time.sleep(1)

        page.screenshot(path=str(out / "09_camera_reset.png"))
        check("Camera reset doesn't crash", True, errors=errors, counters=counters)

        if voxel_rt_available:
            print("  Enabling voxel ray tracing...")
            rt_checkbox = page.query_selector("#rtEnabled")
            if rt_checkbox:
                rt_checkbox.check()
                time.sleep(1)
                page.mouse.click(700, 450)
                time.sleep(15)

                page.screenshot(path=str(out / "10_voxel_rt.png"))

                rt_status = page.inner_text("#rt-status")
                check(
                    "Voxel RT status updates", len(rt_status) > 0, f"got: {rt_status}", errors=errors, counters=counters
                )

                rt_checkbox.uncheck()
                time.sleep(0.5)

        if expect_rt_panel and has_sionna:
            print("  Testing Sionna RT scene selection...")
            rt_options = page.query_selector_all("#rtSourceSelect option")
            sionna_options = [o for o in rt_options if "Sionna" in (o.inner_text() or "")]
            if sionna_options:
                sionna_val = sionna_options[0].get_attribute("value")
                page.select_option("#rtSourceSelect", sionna_val)
                time.sleep(1)
                check("Sionna scene selectable", True, errors=errors, counters=counters)

            page.screenshot(path=str(out / "11_sionna_selected.png"))

        real_errors = [e for e in console_errors if "favicon" not in e.lower()]
        check(
            "No JS console errors",
            len(real_errors) == 0,
            f"errors: {real_errors[:3]}",
            errors=errors,
            counters=counters,
        )

        print("  Stress test: rapid clicking...")
        for i in range(5):
            page.mouse.click(500 + i * 50, 400 + i * 20)
            time.sleep(0.5)
        time.sleep(3)

        page.screenshot(path=str(out / "12_stress_test.png"))
        check("Rapid clicking doesn't crash", True, errors=errors, counters=counters)

        page.screenshot(path=str(out / "13_final_state.png"))

        browser.close()

    tests_passed, tests_failed = counters[0], counters[1]
    print("\n" + "=" * 70)
    print(f"  Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)

    if errors:
        print("\nFailures:")
        for e in errors:
            print(f"  - {e}")

    print(f"\nScreenshots saved to: {out.resolve()}")
    print(f"  {len(list(out.glob('*.png')))} screenshots captured")

    return 1 if tests_failed else 0


def main() -> None:
    default_base = os.environ.get("AEGIS_E2E_BASE", "http://127.0.0.1:5070")
    default_profile = os.environ.get("AEGIS_E2E_PROFILE", "lab")
    parser = argparse.ArgumentParser(description="AEGIS viewer E2E (start the server separately).")
    parser.add_argument("--base", default=default_base, help="Viewer base URL")
    parser.add_argument(
        "--profile",
        choices=["lab", "full"],
        default=default_profile,
        help="lab: e2e_lab.json fixture. full: Thelonious + voxels + DiffeRT demo.",
    )
    args = parser.parse_args()
    sys.exit(run_e2e(args.base, args.profile))


if __name__ == "__main__":
    main()

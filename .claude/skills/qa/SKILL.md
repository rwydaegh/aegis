---
name: qa
description: Open the AEGIS viewer and investigate it for bugs
user-invocable: true
---

# /qa - QA the AEGIS viewer

Launch the viewer, open it in a browser with Playwright, look around, and report any bugs you find.

## What to do

1. Kill any stale process on the viewer port from config (default **5000**), then start the viewer in the background.
2. Open `http://127.0.0.1:5000` (or the printed URL) with `npx playwright screenshot` / `open --headed` as needed.
3. Interact with the viewer naturally — place an antenna, move the body, change settings, toggle layers, check compliance. Use your judgment about what to exercise.
4. Take screenshots with `npx @playwright/cli screenshot --filename=test_screenshots/<name>.png` and read each one. You are multimodal — look at what is on screen.
5. Check the browser console with `npx @playwright/cli console` for JS errors.
6. Report what you found: what works, what looks wrong, any crashes or errors.

Use `npx @playwright/cli snapshot` to get element refs before clicking. After actions that change the scene, wait 2-3 seconds before screenshotting.

When done, close the browser and kill the server.

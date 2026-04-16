---
name: qa
description: Open the AEGIS viewer and investigate it for bugs
user-invocable: true
---

# /qa - QA the AEGIS viewer

Exercise the AEGIS viewer as a real user would. The goal is to find bugs that
automated tests miss: wrong values, broken interactions, inconsistent states,
silent failures. Not a checklist walkthrough.

## What to test

If invoked with a specific focus (e.g. "test the MIMO panel"), test that area
deeply. If invoked generally, pick an area and explore it like a curious user.

For inspiration on what the app can do, skim `docs/internal/features.md` (the
complete feature inventory). But do not try to cover everything. Go deep on a
few things rather than shallow on many.

Be a real user first, a detective second. Place antennas, move the phantom,
change settings, load scenes, toggle options. If something looks wrong, dig in.
If everything looks fine, move on. A clean session with no bugs is a valid
outcome. Do not invent problems.

**Time budget:** 10-15 meaningful interactions. Each one: act, screenshot, read,
assess. Do not spend more than 5 minutes on a single feature unless you found
something suspicious. Thorough 45-minute session beats a 4-hour crawl.

## Setup

### Local
1. Kill stale processes on the viewer port (default 5000).
2. Start the viewer: `.venv/bin/python -m aegis.viewer` in background.
3. Wait for "Running on http://127.0.0.1:5000" in output.
4. Save screenshots to `/tmp/qa_screenshots/`. Read every screenshot with the Read tool.

### Production
- **URL**: `https://aegis.waves-ugent.be`
- **Auth**: POST `{"password":"WiCa2026#"}` to `/api/auth` first, then use the session cookie for all subsequent requests.
- For Playwright, authenticate by navigating to the URL, filling the password gate, then proceeding.
- For curl, use `-c cookies.txt` to save and `-b cookies.txt` to send cookies.

## Tooling: Playwright CLI

Use `npx @playwright/cli` for browser interaction. This is a persistent,
stateful CLI: you open a browser once and issue commands against it. The
session stays alive between commands.

Prefer the CLI over `node -e` scripts or the Playwright Node.js API. The CLI
avoids re-launching, re-authenticating, and sleep-polling. If you hit a case
where the CLI genuinely cannot do what you need (complex async sequences,
programmatic assertions), use `node -e` as a fallback.

### Workflow

```bash
# 1. Open browser (persistent session, stays alive)
npx @playwright/cli open https://aegis.waves-ugent.be
npx @playwright/cli resize 1920 1080

# 2. Authenticate
npx @playwright/cli fill 'input[type="password"]' 'WiCa2026#'
npx @playwright/cli click 'button[type="submit"]'
npx @playwright/cli screenshot /tmp/qa_screenshots/step01.png
# Read the screenshot with Read tool, then decide next action

# 3. Interact one command at a time
npx @playwright/cli click 'text=Load'
npx @playwright/cli screenshot /tmp/qa_screenshots/step02.png
# Read screenshot, decide next action...

# 4. Done
npx @playwright/cli close
```

### Key commands

| Command | Example |
|---------|---------|
| Open browser | `npx @playwright/cli open <url>` |
| Screenshot | `npx @playwright/cli screenshot /tmp/qa_screenshots/stepNN.png` |
| Click | `npx @playwright/cli click 'text=Button'` or `npx @playwright/cli click eNN` |
| Type | `npx @playwright/cli fill 'input' 'text'` |
| Evaluate JS | `npx @playwright/cli eval "document.querySelector('canvas')..."` |
| Snapshot (a11y tree) | `npx @playwright/cli snapshot` |
| Press key | `npx @playwright/cli press Shift+b` |
| Key down/up | `npx @playwright/cli keydown w` then `npx @playwright/cli keyup w` |
| Mouse events | `npx @playwright/cli mousedown` / `npx @playwright/cli mouseup` |
| Move mouse | `npx @playwright/cli mousemove 900 650` |
| Console | `npx @playwright/cli console` |
| Close | `npx @playwright/cli close` |

## How to interact with the 3D scene

R3F (React Three Fiber) uses its own raycaster. Standard DOM `click` does NOT
work on the canvas. Use mouse events via `eval` or the CLI mouse commands:

```bash
# Place antenna - move mouse to position, then mousedown + mouseup
npx @playwright/cli mousemove 900 650
npx @playwright/cli mousedown
npx @playwright/cli mouseup
```

Or via eval for PointerEvents (more reliable for R3F):

```bash
npx @playwright/cli eval "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerdown',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
npx @playwright/cli eval "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerup',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
```

- Click to the RIGHT of the phantom (clientX=800-1000, clientY=600-700) to place an antenna.
- After placing, wait 3-5 seconds for the debounced compute, then screenshot.

## Keyboard controls

| Key | Action |
|-----|--------|
| W/A/S/D | Move phantom |
| Q/E | Rotate phantom |
| Arrow keys | Nudge antenna (1m) |
| Shift+Arrow | Nudge antenna (3m) |
| Shift+B | Open bug reporter |
| ? | Keyboard help |

**Antenna must be placed first** before arrow keys do anything.

Use `press`, `keydown`, and `keyup`:

```bash
npx @playwright/cli press w                # tap
npx @playwright/cli keydown w              # hold (physics runs while held)
sleep 1
npx @playwright/cli keyup w
```

## Reading elements

Use `npx @playwright/cli snapshot` to get the accessibility tree with element refs
(eNN). Then click/fill/select by ref: `npx @playwright/cli click e42`.

After actions that change the scene, wait 2-3 seconds before screenshotting.
Always read each screenshot with the Read tool before deciding the next action.

## What to watch for

- Values that seem wrong (zero, NaN, `--`, nonsensical units)
- UI elements that disappear, overlap, or render incorrectly
- Controls that do not respond or produce no visible change
- States that seem inconsistent (e.g. compliance says PASS but values are extreme)
- Visual glitches in the 3D scene (missing meshes, wrong colors, clipping)
- Panels that fail to update after an action
- HUD elements that vanish or show stale data

Check the browser console periodically: `npx @playwright/cli console`

## Judgment calls

Not every oddity is a bug. Use your judgment:

- If unsure whether something is wrong, do not file it. Move on.
- Only file issues for things clearly broken, producing wrong results, or blocking a user.
- Do not file cosmetic issues (alignment, spacing, font size).
- Do not file edge cases no real user would hit.
- Check `agent_hq/context/not-bugs.md` before filing.

## Filing issues

Only file if the problem is NOT a JavaScript error (Sentry handles those).

```bash
# Check for duplicates first
gh issue list --label "qa-bot" --state open --limit 20

# File with screenshot
npx @playwright/cli screenshot /tmp/qa_screenshots/bug_description.png

gh issue create \
  --title "Short description of the problem" \
  --label "qa-bot,bug" \
  --body "## What happened

[2-4 sentences: what you were doing, what you expected, what you saw instead]

## Steps to reproduce

1. Go to https://aegis.waves-ugent.be
2. [Steps]
3. [What went wrong]

---
*Filed by QA agent.*"
```

## Cleanup

```bash
npx @playwright/cli close
```

## Report format

Report bugs with severity (High/Medium/Low), what you did, what you expected, and what happened. Note what works correctly too.

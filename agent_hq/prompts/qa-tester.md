# QA tester

You are a user of AEGIS, a 3D electromagnetic dosimetry viewer at
https://aegis.waves-ugent.be. Your job is to USE the application the way a real
person would -- place antennas, move the phantom around, change settings, load
scenes, toggle options -- and see what happens. Exercise the core features hard.
If things break or crash, that is fine (Sentry catches JS errors automatically).
But keep a sharp eye out for things that LOOK wrong without crashing: values that
do not make sense, UI elements that vanish, controls that silently do nothing,
inconsistent states. Those silent bugs are the ones only you can catch.

## Setup

```bash
npx playwright open --browser chromium https://aegis.waves-ugent.be
npx @playwright/cli resize 1920 1080
```

## How to interact

**UI elements:** `npx @playwright/cli snapshot` to get refs, then
`npx @playwright/cli click eNN` or `npx @playwright/cli select eNN "value"`.

**3D canvas:** R3F uses its own raycaster. Dispatch PointerEvents via eval:
```bash
npx @playwright/cli evaluate "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerdown',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
npx @playwright/cli evaluate "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerup',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
```
Click right of the phantom (clientX=800-1000, clientY=600-700) to place an antenna.

**Keyboard:** Dispatch on `document` via eval:
```bash
npx @playwright/cli evaluate "document.dispatchEvent(new KeyboardEvent('keydown',{key:'q',code:'KeyQ',bubbles:true}))"
npx @playwright/cli evaluate "document.dispatchEvent(new KeyboardEvent('keyup',{key:'q',code:'KeyQ',bubbles:true}))"
```
Q/E: rotate phantom. Arrow keys: nudge antenna (1m), Shift+Arrow: 3m. Always keydown+keyup.

**Screenshots:** Save to `/tmp/qa_screenshots/` and read with the Read tool:
```bash
mkdir -p /tmp/qa_screenshots
npx @playwright/cli screenshot /tmp/qa_screenshots/step_01.png
```

## How to test

Be a real user first, a detective second. Actually use the features:
- Place an antenna and check dosimetry computes (heatmap appears, HUD shows values)
- Change settings and see if the result updates
- Open panels, toggle checkboxes, select dropdown values
- Try edge cases: empty inputs, extreme values, rapid toggling, unusual combos

### Environment loading (important, often broken)

The Environment panel lets users load real-world buildings. This feature is buggy
and needs regular testing. To test it:

1. Open the Environment panel in the sidebar
2. Select "OSM" source
3. Enter coordinates: lat=40.748, lon=-73.986 (New York) or lat=51.054, lon=3.725 (Ghent)
4. Set radius to 200m
5. Click "Fetch OSM" and wait for buildings to appear
6. Check: do buildings render? Are they positioned correctly? Any console errors?

Also test "3D Tiles" source (needs globe camera mode). And test switching between
sources, changing coordinates, increasing radius. These are all known pain points.

After each meaningful action, take a screenshot and read it. Ask yourself:
"Does this look right? Would a user be confused by this?"

Things to watch for:
- Values that seem wrong (zero, NaN, --, nonsensical units)
- UI elements that disappear, overlap, or render incorrectly
- Controls that do not respond or produce no visible change
- States that seem inconsistent (e.g., compliance says PASS but values are extreme)
- Visual glitches in the 3D scene (missing meshes, wrong colors, clipping)
- Panels or sections that fail to update after an action
- HUD elements that vanish or show stale data
- Dropdowns or toggles that reset unexpectedly

Check the browser console periodically with `npx @playwright/cli console`.

Explore for 8-12 meaningful interactions. Do not rush through a checklist. Actually
look at each screen and think about whether what you see makes sense.

## Judgment calls

Not every oddity is a bug. Use your judgment:

- If you are not sure whether something is wrong, **do not file it**. Move on.
- If the app works but something is slightly ugly or mildly confusing, that is not
  a bug. Only file issues for things that are clearly broken, produce wrong results,
  or would genuinely block a user.
- If everything looks fine, say "LGTM" and close the browser. A clean session with
  no bugs found is a perfectly valid outcome. Do not invent problems.
- Do not file issues about edge cases that no real user would hit.
- Do not file issues about cosmetic details (alignment, spacing, font size).

## When you find something clearly wrong

Only file an issue if the problem is NOT a JavaScript error (Sentry handles those).
Check `agent_hq/context/not-bugs.md` before filing.

**Check for duplicates first:**
```bash
gh issue list --label "qa-bot" --state open --limit 20
```

**Labeling:** Run `gh label list` to see available labels. Always include `qa-bot`
and `bug`. Add relevant area labels (`viewer`, `frontend`, `physics`, `MIMO`, etc.).

```bash
npx @playwright/cli screenshot /tmp/qa_screenshots/bug_description.png

gh issue create \
  --title "Short description of the problem" \
  --label "qa-bot,bug,<other labels>" \
  --body "## What happened

[2-4 sentences: what you were doing, what you expected, what you saw instead]

## Steps to reproduce

1. Go to https://aegis.waves-ugent.be
2. [Steps]
3. [What went wrong]

---
*Filed by QA agent · the \`qa-bot\` label triggers an autofix workflow.*"
```

## When you are done

Close the browser and write a short summary of what you tested and any issues filed.
```bash
npx @playwright/cli close
```

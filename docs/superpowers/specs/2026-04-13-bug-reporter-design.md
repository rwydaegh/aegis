# In-app bug reporter

## Problem

AEGIS has many half-baked features and subtle bugs that are hard to detect with automated testing (Playwright struggles with 3D canvas, camera interactions, drag-and-drop). The highest-quality bug detection is a human using the app - but there is no low-friction way to turn "I see something wrong" into a tracked, fixable issue. The existing Sentry pipeline proves that well-structured issues get fixed autonomously. This feature bridges the gap for non-crash bugs.

## User flow

1. User presses `Shift+B` anywhere in the app
2. Screenshot is captured (full page including 3D canvas)
3. Overlay appears with the screenshot and a red freehand pen active
4. User draws/circles the problem area. Undo and Clear buttons available.
5. User types a one-line description in a text field below the screenshot
6. User clicks Submit (or presses Enter)
7. Backend creates a GitHub issue with annotated screenshot, description, and full app state
8. Toast notification shows "Bug reported - #NNN" with a clickable link. Overlay closes.

## Frontend

### New files

**`aegis-web/src/components/hud/BugReportOverlay.tsx`**
- Registers global `keydown` listener for `Shift+B` (same pattern as `KeyboardHelp.tsx`)
- On trigger: captures screenshot via `html2canvas(document.body)` (same as `ExportPanel.tsx`)
- Renders full-screen overlay with:
  - Captured screenshot as background of annotation canvas
  - Annotation toolbar: Undo, Clear buttons
  - Text input for description (placeholder: "Describe what's wrong...")
  - Submit and Cancel buttons
- On submit: collects annotated image (composite screenshot + drawing), state snapshot, description. POSTs to `/api/bug-report`.
- On success: shows toast via `useNotificationStore.getState().addNotification('info', 'Bug reported - #NNN', issueUrl)`, closes overlay.
- On cancel or Escape: closes overlay, discards everything.

**`aegis-web/src/components/hud/AnnotationCanvas.tsx`**
- Receives screenshot as a data URL prop
- Renders two layered canvases: bottom = screenshot image, top = transparent drawing surface
- Mouse/pointer events on drawing canvas:
  - `pointerdown`: start stroke, record point
  - `pointermove`: draw line segment in red (#ff3333), 3px width, round caps
  - `pointerup`: end stroke, push to undo stack
- Undo: pops last stroke from stack, redraws remaining strokes
- Clear: empties stroke stack, clears drawing canvas
- Exposes `getCompositeImage(): Promise<Blob>` that merges both canvases into a single JPEG (quality 0.85, capped at 1920px wide)

**`aegis-web/src/api/bugReport.ts`**
- `collectBugReportState(): object` - calls `collectState()` from `lib/shareLink.ts` (already reads simulation, scene, UI, antenna stores) and adds browser metadata:
  - Simulation: mode, freqGhz, powerDbm, fresnel, polarisation, curvature, diffraction, skinModel, antennaPos
  - UI: sidebarMode, cameraMode, legendScale, wireframe
  - Scene: activeScenario, pathSource, bodyName
  - MIMO: enabled, precoderType, userCount
  - Browser: userAgent, viewport dimensions, current URL
- `submitBugReport(screenshot: Blob, description: string, state: object): Promise<{issueUrl: string, issueNumber: number}>` - POSTs to `/api/bug-report`

### Integration point
- `BugReportOverlay` is added to `HudOverlay.tsx` (alongside `KeyboardHelp`, `WelcomeOverlay`, `GuidedTour`)

## Backend

### New file

**`src/aegis/viewer/routes/bugreport.py`**
- Module with `register(app, cache, cache_lock)` function (same pattern as all other route modules)
- Requires session auth (default behavior, no exempt_paths entry needed)
- `POST /api/bug-report`
  - Receives: `{screenshot: <base64 JPEG>, description: <string>, state: <object>}`
  - Validates: description is non-empty, screenshot is valid base64
  - Screenshot size mitigation: cap at 1920px wide, JPEG quality 0.85 (done frontend-side)
  - Uploads screenshot to GitHub repo via contents API (`PUT /repos/{owner}/{repo}/contents/bug-screenshots/{timestamp}.jpg`)
  - Creates GitHub issue via REST API (using `GITHUB_ISSUES_TOKEN`, same as `sentry_webhook.py`):
    - Title: description text (truncated to 72 chars)
    - Body: screenshot image, formatted state table, "Filed via in-app bug reporter" footer
    - Labels: `user-report`, `bug`
  - Returns: `{issueUrl, issueNumber}`

### Registration
- `bugreport.register(app, _cache, _cache_lock)` added in `server.py` alongside existing route registrations (~line 664)

## GitHub issue format

```markdown
## Bug report

> {user's description}

![screenshot]({github raw URL})

## App state
| Key | Value |
|-----|-------|
| Mode | spatial |
| Frequency | 28.0 GHz |
| Power | 23 dBm |
| Body | thelonious |
| Skin model | dry |
| Corrections | F, P, C |
| Camera | orbit |
| Sidebar | antenna |
| Scenario | Open Ground |
| MIMO | off |
| Browser | Chrome 124 / Linux |
| Viewport | 1920x1080 |

---
*Filed via in-app bug reporter. The `user-report` label triggers the fix pipeline.*
```

## What we reuse

| Component | Source | What we take |
|-----------|--------|-------------|
| Screenshot capture | `ExportPanel.tsx` lines 84-112 | html2canvas config, canvas fallback |
| State collection | `lib/sentry.ts` lines 25-72 | Zustand store reads pattern |
| GitHub issue creation | `sentry_webhook.py` | Token handling, API pattern |
| Overlay styling | `KeyboardHelp.tsx` lines 95-140 | Backdrop + animation pattern |
| Toast notifications | `stores/notifications.ts` | `addNotification()` |
| Keyboard handling | `KeyboardHelp.tsx` lines 44-58 | Global keydown listener pattern |

## Not in scope

- Shape tools (circle, arrow, rectangle) - freehand pen only for now
- Multiple colors or brush sizes
- Severity/priority selection - keep the UI minimal, triage is the fix agent's job
- Offline support
- Rate limiting (trust the password gate)

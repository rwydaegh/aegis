# Bug reporter implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-app bug reporter (Shift+B) that captures an annotated screenshot plus full app state and creates a GitHub issue, feeding the automated fix pipeline.

**Architecture:** Frontend overlay captures a screenshot via html2canvas, lets the user draw on it with a freehand red pen, collects Zustand store state, and POSTs everything to a new Flask endpoint. Backend uploads the screenshot to GitHub and creates a labeled issue.

**Tech Stack:** React 19, Zustand, html2canvas, Canvas 2D API, Flask, GitHub REST API

**Spec:** `docs/superpowers/specs/2026-04-13-bug-reporter-design.md`

---

## File map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `aegis-web/src/api/bugReport.ts` | State collection, POST to backend |
| Create | `aegis-web/src/components/hud/AnnotationCanvas.tsx` | Freehand drawing on screenshot |
| Create | `aegis-web/src/components/hud/BugReportOverlay.tsx` | Overlay shell, keyboard listener, orchestration |
| Create | `src/aegis/viewer/routes/bugreport.py` | Flask endpoint, GitHub issue creation |
| Create | `tests/test_bugreport.py` | Backend endpoint tests |
| Modify | `aegis-web/src/components/layout/HudOverlay.tsx` | Add BugReportOverlay as peer of KeyboardHelp |
| Modify | `aegis-web/src/components/hud/KeyboardHelp.tsx` | Add Shift+B to shortcut list |
| Modify | `src/aegis/viewer/server.py` | Register bugreport route |

---

### Task 1: Backend endpoint

**Files:**
- Create: `src/aegis/viewer/routes/bugreport.py`
- Create: `tests/test_bugreport.py`
- Modify: `src/aegis/viewer/server.py`

- [ ] **Step 1: Write failing test for the endpoint**

Create `tests/test_bugreport.py`:

```python
"""Tests for the bug report endpoint."""

import base64
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from aegis.viewer.server import create_app


@pytest.fixture
def client(tmp_path):
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    app = create_app(data_dir=data_dir)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_bug_report_missing_description(client):
    resp = client.post(
        "/api/bug-report",
        json={"screenshot": "data:image/jpeg;base64,/9j/4AAQ", "state": {}},
    )
    assert resp.status_code == 400
    assert "description" in resp.get_json()["error"].lower()


def test_bug_report_missing_screenshot(client):
    resp = client.post(
        "/api/bug-report",
        json={"description": "something is broken", "state": {}},
    )
    assert resp.status_code == 400
    assert "screenshot" in resp.get_json()["error"].lower()


@patch("aegis.viewer.routes.bugreport._upload_screenshot_to_github")
@patch("aegis.viewer.routes.bugreport._create_github_issue")
def test_bug_report_success(mock_create_issue, mock_upload, client):
    mock_upload.return_value = "https://raw.githubusercontent.com/rwydaegh/aegis/bug-screenshots/test.jpg"
    mock_create_issue.return_value = {"number": 999, "html_url": "https://github.com/rwydaegh/aegis/issues/999"}

    # Minimal valid 1x1 JPEG as base64
    pixel = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAFRABAAAAAAAAAAAAAAAAAAAAAf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAB//2Q=="

    resp = client.post(
        "/api/bug-report",
        json={
            "screenshot": f"data:image/jpeg;base64,{pixel}",
            "description": "tooltip clips behind sidebar",
            "state": {"mode": "spatial", "freqGhz": 28.0},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["issueNumber"] == 999
    assert "github.com" in data["issueUrl"]
    mock_upload.assert_called_once()
    mock_create_issue.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_bugreport.py -x -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create the bugreport route module**

Create `src/aegis/viewer/routes/bugreport.py`:

```python
"""Bug report endpoint - creates GitHub issues from in-app reports."""

import base64
import json
import logging
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from flask import Flask, Response, request

log = logging.getLogger(__name__)

GITHUB_REPO = "rwydaegh/aegis"


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach the bug report route to *app*."""

    @app.route("/api/bug-report", methods=["POST"])
    def bug_report() -> Response:
        data = request.get_json(silent=True)
        if not data:
            return Response(
                json.dumps({"error": "Invalid JSON body"}),
                status=400,
                mimetype="application/json",
            )

        description = (data.get("description") or "").strip()
        screenshot_data = data.get("screenshot") or ""
        state = data.get("state") or {}

        if not description:
            return Response(
                json.dumps({"error": "Missing description"}),
                status=400,
                mimetype="application/json",
            )

        if not screenshot_data:
            return Response(
                json.dumps({"error": "Missing screenshot"}),
                status=400,
                mimetype="application/json",
            )

        github_token = os.environ.get(
            "GITHUB_ISSUES_TOKEN", ""
        ) or os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            log.error("No GITHUB_TOKEN or GITHUB_ISSUES_TOKEN set")
            return Response(
                json.dumps({"error": "Bug reporting not configured"}),
                status=503,
                mimetype="application/json",
            )

        # Strip data URL prefix if present
        if "," in screenshot_data:
            screenshot_data = screenshot_data.split(",", 1)[1]

        try:
            screenshot_bytes = base64.b64decode(screenshot_data)
        except Exception:
            return Response(
                json.dumps({"error": "Invalid screenshot data"}),
                status=400,
                mimetype="application/json",
            )

        # Upload screenshot to GitHub repo
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        filename = f"bug-screenshots/{timestamp}.jpg"
        try:
            screenshot_url = _upload_screenshot_to_github(
                github_token, filename, screenshot_bytes
            )
        except Exception:
            log.exception("Failed to upload screenshot to GitHub")
            screenshot_url = None

        # Format and create the issue
        title = description[:72]
        body = _format_issue_body(description, screenshot_url, state)

        try:
            result = _create_github_issue(github_token, title, body)
        except Exception:
            log.exception("Failed to create GitHub issue")
            return Response(
                json.dumps({"error": "Failed to create issue on GitHub"}),
                status=502,
                mimetype="application/json",
            )

        return Response(
            json.dumps(
                {
                    "issueNumber": result["number"],
                    "issueUrl": result["html_url"],
                }
            ),
            status=200,
            mimetype="application/json",
        )


def _upload_screenshot_to_github(
    token: str, path: str, content: bytes
) -> str:
    """Upload a file to the GitHub repo via the contents API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = json.dumps(
        {
            "message": f"Bug report screenshot {path}",
            "content": base64.b64encode(content).decode(),
            "branch": "master",
        }
    ).encode()
    req = Request(
        url,
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    return result["content"]["download_url"]


def _create_github_issue(token: str, title: str, body: str) -> dict:
    """Create an issue on GitHub via the REST API. Returns the issue object."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "labels": ["user-report", "bug"],
        }
    ).encode()
    req = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    log.info("Created bug report issue #%s: %s", result.get("number"), title)
    return result


def _format_issue_body(
    description: str, screenshot_url: str | None, state: dict
) -> str:
    """Build a Markdown issue body."""
    lines: list[str] = []

    lines.append("## Bug report")
    lines.append("")
    lines.append(f"> {description}")
    lines.append("")

    if screenshot_url:
        lines.append(f"![screenshot]({screenshot_url})")
        lines.append("")

    if state:
        lines.append("## App state")
        lines.append("")
        lines.append("| Key | Value |")
        lines.append("|-----|-------|")
        for key, value in state.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")

    lines.append("---")
    lines.append(
        "*Filed via in-app bug reporter. "
        "The `user-report` label triggers the fix pipeline.*"
    )

    return "\n".join(lines)
```

- [ ] **Step 4: Register the route in server.py**

In `src/aegis/viewer/server.py`, add import and registration alongside existing routes.

Add import near the other route imports (~line 30):
```python
from aegis.viewer.routes import bugreport
```

Add registration after the existing `optimize.register(...)` call (~line 666):
```python
    bugreport.register(app, _cache, _cache_lock)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_bugreport.py -x -v`
Expected: 3 tests PASS

- [ ] **Step 6: Run lint**

Run: `python3 -m ruff check src/aegis/viewer/routes/bugreport.py tests/test_bugreport.py`
Expected: clean

- [ ] **Step 7: Commit**

```bash
git add src/aegis/viewer/routes/bugreport.py tests/test_bugreport.py src/aegis/viewer/server.py
git commit -m "Add /api/bug-report endpoint for in-app bug reporting"
```

---

### Task 2: Frontend API client and state collection

**Files:**
- Create: `aegis-web/src/api/bugReport.ts`

- [ ] **Step 1: Create the bug report API module**

Create `aegis-web/src/api/bugReport.ts`:

```typescript
import { postJson } from './client'
import { collectState } from '@/lib/shareLink'

interface BugReportResponse {
  issueNumber: number
  issueUrl: string
}

/** Collect app state for the bug report (extends shareLink state with browser metadata). */
export function collectBugReportState(): Record<string, unknown> {
  const appState = collectState()
  return {
    ...appState,
    browser: navigator.userAgent,
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    url: window.location.href,
    timestamp: new Date().toISOString(),
  }
}

/** Submit a bug report to the backend. */
export async function submitBugReport(
  screenshot: Blob,
  description: string,
): Promise<BugReportResponse> {
  // Convert blob to base64 data URL
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(screenshot)
  })

  const state = collectBugReportState()

  return postJson<BugReportResponse>('/api/bug-report', {
    screenshot: dataUrl,
    description,
    state,
  })
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit 2>&1 | head -20`
Expected: clean (or only pre-existing errors unrelated to this file)

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/api/bugReport.ts
git commit -m "Add bug report API client with state collection"
```

---

### Task 3: Annotation canvas component

**Files:**
- Create: `aegis-web/src/components/hud/AnnotationCanvas.tsx`

- [ ] **Step 1: Create the annotation canvas**

Create `aegis-web/src/components/hud/AnnotationCanvas.tsx`:

```tsx
import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'

export interface AnnotationCanvasHandle {
  /** Merge the screenshot + drawings into a single JPEG blob. */
  getCompositeImage: () => Promise<Blob>
}

interface Props {
  /** Screenshot as a data URL (image/png or image/jpeg). */
  screenshotUrl: string
  width: number
  height: number
}

interface Stroke {
  points: { x: number; y: number }[]
}

const AnnotationCanvas = forwardRef<AnnotationCanvasHandle, Props>(
  function AnnotationCanvas({ screenshotUrl, width, height }, ref) {
    const bgCanvasRef = useRef<HTMLCanvasElement>(null)
    const drawCanvasRef = useRef<HTMLCanvasElement>(null)
    const strokesRef = useRef<Stroke[]>([])
    const currentStrokeRef = useRef<Stroke | null>(null)
    const isDrawingRef = useRef(false)

    // Draw the screenshot onto the background canvas
    useEffect(() => {
      const canvas = bgCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const img = new Image()
      img.onload = () => {
        ctx.clearRect(0, 0, width, height)
        ctx.drawImage(img, 0, 0, width, height)
      }
      img.src = screenshotUrl
    }, [screenshotUrl, width, height])

    const redrawStrokes = useCallback(() => {
      const canvas = drawCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, width, height)
      ctx.strokeStyle = '#ff3333'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      for (const stroke of strokesRef.current) {
        if (stroke.points.length < 2) continue
        ctx.beginPath()
        ctx.moveTo(stroke.points[0].x, stroke.points[0].y)
        for (let i = 1; i < stroke.points.length; i++) {
          ctx.lineTo(stroke.points[i].x, stroke.points[i].y)
        }
        ctx.stroke()
      }
    }, [width, height])

    const getCanvasPoint = (e: React.PointerEvent) => {
      const canvas = drawCanvasRef.current
      if (!canvas) return { x: 0, y: 0 }
      const rect = canvas.getBoundingClientRect()
      return {
        x: (e.clientX - rect.left) * (width / rect.width),
        y: (e.clientY - rect.top) * (height / rect.height),
      }
    }

    const handlePointerDown = (e: React.PointerEvent) => {
      isDrawingRef.current = true
      const point = getCanvasPoint(e)
      currentStrokeRef.current = { points: [point] }
      ;(e.target as Element).setPointerCapture(e.pointerId)
    }

    const handlePointerMove = (e: React.PointerEvent) => {
      if (!isDrawingRef.current || !currentStrokeRef.current) return
      const point = getCanvasPoint(e)
      currentStrokeRef.current.points.push(point)

      // Draw the current segment immediately for responsiveness
      const canvas = drawCanvasRef.current
      const ctx = canvas?.getContext('2d')
      if (!ctx) return
      const pts = currentStrokeRef.current.points
      if (pts.length < 2) return
      ctx.strokeStyle = '#ff3333'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      ctx.moveTo(pts[pts.length - 2].x, pts[pts.length - 2].y)
      ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y)
      ctx.stroke()
    }

    const handlePointerUp = () => {
      if (currentStrokeRef.current && currentStrokeRef.current.points.length > 1) {
        strokesRef.current.push(currentStrokeRef.current)
      }
      currentStrokeRef.current = null
      isDrawingRef.current = false
    }

    useImperativeHandle(ref, () => ({
      getCompositeImage: () => {
        return new Promise<Blob>((resolve, reject) => {
          const composite = document.createElement('canvas')
          composite.width = width
          composite.height = height
          const ctx = composite.getContext('2d')
          if (!ctx) return reject(new Error('Cannot get canvas context'))

          // Draw background screenshot
          if (bgCanvasRef.current) ctx.drawImage(bgCanvasRef.current, 0, 0)
          // Draw annotations on top
          if (drawCanvasRef.current) ctx.drawImage(drawCanvasRef.current, 0, 0)

          composite.toBlob(
            blob => {
              if (blob) resolve(blob)
              else reject(new Error('Failed to export canvas'))
            },
            'image/jpeg',
            0.85,
          )
        })
      },
    }))

    // Expose undo and clear for the parent
    const undo = useCallback(() => {
      strokesRef.current.pop()
      redrawStrokes()
    }, [redrawStrokes])

    const clear = useCallback(() => {
      strokesRef.current = []
      redrawStrokes()
    }, [redrawStrokes])

    return (
      <div className="relative" style={{ width, height }}>
        {/* Background: screenshot */}
        <canvas
          ref={bgCanvasRef}
          width={width}
          height={height}
          className="absolute inset-0"
        />
        {/* Foreground: drawing surface */}
        <canvas
          ref={drawCanvasRef}
          width={width}
          height={height}
          className="absolute inset-0 cursor-crosshair"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        />
        {/* Toolbar */}
        <div className="absolute top-2 right-2 flex gap-1">
          <button
            onClick={undo}
            className="px-2 py-1 rounded text-[11px] font-medium bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
          >
            Undo
          </button>
          <button
            onClick={clear}
            className="px-2 py-1 rounded text-[11px] font-medium bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
          >
            Clear
          </button>
        </div>
      </div>
    )
  },
)

export default AnnotationCanvas
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/hud/AnnotationCanvas.tsx
git commit -m "Add annotation canvas component with freehand drawing"
```

---

### Task 4: Bug report overlay

**Files:**
- Create: `aegis-web/src/components/hud/BugReportOverlay.tsx`

- [ ] **Step 1: Create the overlay component**

Create `aegis-web/src/components/hud/BugReportOverlay.tsx`:

```tsx
import { useState, useEffect, useRef, useCallback } from 'react'
import AnnotationCanvas, { type AnnotationCanvasHandle } from './AnnotationCanvas'
import { submitBugReport } from '@/api/bugReport'
import { useNotificationStore } from '@/stores/notifications'

/** Maximum screenshot dimension (wider screenshots are downscaled). */
const MAX_WIDTH = 1920
const MAX_HEIGHT = 1080

export default function BugReportOverlay() {
  const [open, setOpen] = useState(false)
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const canvasRef = useRef<AnnotationCanvasHandle>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const close = useCallback(() => {
    setOpen(false)
    setScreenshotUrl(null)
    setDescription('')
  }, [])

  // Keyboard: Shift+B to open, Escape to close
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'B' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        if (!open) capture()
      }
      if (e.key === 'Escape' && open) {
        e.preventDefault()
        close()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, close])

  // Focus the description input when overlay opens
  useEffect(() => {
    if (open && screenshotUrl) {
      setTimeout(() => inputRef.current?.focus(), 200)
    }
  }, [open, screenshotUrl])

  async function capture() {
    try {
      const html2canvas = (await import('html2canvas')).default
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        scale: window.devicePixelRatio || 1,
        backgroundColor: null,
      })

      // Cap dimensions
      let w = canvas.width
      let h = canvas.height
      if (w > MAX_WIDTH) {
        h = Math.round(h * (MAX_WIDTH / w))
        w = MAX_WIDTH
      }
      if (h > MAX_HEIGHT) {
        w = Math.round(w * (MAX_HEIGHT / h))
        h = MAX_HEIGHT
      }

      // Resize if needed
      let finalCanvas = canvas
      if (w !== canvas.width || h !== canvas.height) {
        const resized = document.createElement('canvas')
        resized.width = w
        resized.height = h
        const ctx = resized.getContext('2d')
        if (ctx) {
          ctx.drawImage(canvas, 0, 0, w, h)
          finalCanvas = resized
        }
      }

      setScreenshotUrl(finalCanvas.toDataURL('image/png'))
      // Scale for display: fit in viewport with padding
      const displayW = Math.min(w, window.innerWidth - 80)
      const displayH = Math.round(displayW * (h / w))
      setDimensions({ width: displayW, height: displayH })
      setOpen(true)
    } catch {
      // Fallback: capture largest canvas (3D viewport)
      const allCanvases = Array.from(document.querySelectorAll('canvas'))
      const canvas = allCanvases.reduce<HTMLCanvasElement | null>((best, c) => {
        if (!best) return c
        return c.width * c.height > best.width * best.height ? c : best
      }, null)
      if (!canvas) {
        useNotificationStore.getState().addNotification('error', 'Screenshot capture failed')
        return
      }
      const w = Math.min(canvas.width, MAX_WIDTH)
      const h = Math.round(w * (canvas.height / canvas.width))
      setScreenshotUrl(canvas.toDataURL('image/png'))
      const displayW = Math.min(w, window.innerWidth - 80)
      const displayH = Math.round(displayW * (h / w))
      setDimensions({ width: displayW, height: displayH })
      setOpen(true)
    }
  }

  async function handleSubmit() {
    if (!canvasRef.current || !description.trim()) return
    setSubmitting(true)
    try {
      const blob = await canvasRef.current.getCompositeImage()
      const result = await submitBugReport(blob, description.trim())
      useNotificationStore
        .getState()
        .addNotification('info', `Bug reported - #${result.issueNumber}`, result.issueUrl)
      close()
    } catch (err) {
      useNotificationStore
        .getState()
        .addNotification('error', 'Failed to submit bug report', String(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (!open || !screenshotUrl) return null

  return (
    <>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 z-50 pointer-events-auto" onClick={close} />
      {/* Content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-50 pointer-events-none p-10">
        <div
          className="bg-card/95 backdrop-blur-md rounded-xl border border-border shadow-2xl pointer-events-auto animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[90vh] overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
            <h2 className="text-sm font-medium text-heading">Report a bug</h2>
            <button
              onClick={close}
              className="text-muted-foreground hover:text-foreground transition-colors text-xs"
            >
              Esc
            </button>
          </div>

          {/* Screenshot with annotation */}
          <div className="overflow-auto p-4 flex-1 flex justify-center">
            <AnnotationCanvas
              ref={canvasRef}
              screenshotUrl={screenshotUrl}
              width={dimensions.width}
              height={dimensions.height}
            />
          </div>

          {/* Description + submit */}
          <div className="px-4 py-3 border-t border-border/50 flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && description.trim() && !submitting) handleSubmit()
              }}
              placeholder="Describe what's wrong..."
              className="flex-1 px-3 py-1.5 rounded border border-border bg-muted text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              disabled={submitting}
            />
            <button
              onClick={handleSubmit}
              disabled={!description.trim() || submitting}
              className="px-4 py-1.5 rounded text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/hud/BugReportOverlay.tsx
git commit -m "Add bug report overlay with screenshot capture and annotation"
```

---

### Task 5: Integration and wiring

**Files:**
- Modify: `aegis-web/src/components/layout/HudOverlay.tsx`
- Modify: `aegis-web/src/components/hud/KeyboardHelp.tsx`

- [ ] **Step 1: Add BugReportOverlay to HudOverlay**

In `aegis-web/src/components/layout/HudOverlay.tsx`:

Add import:
```typescript
import BugReportOverlay from '@/components/hud/BugReportOverlay'
```

Add component after `<KeyboardHelp />` (~line 94):
```tsx
      {/* Bug report overlay (Shift+B) */}
      <BugReportOverlay />
```

- [ ] **Step 2: Add Shift+B to keyboard help shortcuts**

In `aegis-web/src/components/hud/KeyboardHelp.tsx`, add to the `General` shortcuts group (the last group in the `groups` array):

```typescript
    {
      title: 'General',
      shortcuts: [
        { keys: ['?'], description: 'Toggle this help' },
        { keys: ['Shift', 'B'], description: 'Report a bug' },
      ],
    },
```

- [ ] **Step 3: Verify TypeScript compiles and build succeeds**

Run: `cd aegis-web && npx tsc --noEmit && npm run build`

- [ ] **Step 4: Run backend tests**

Run: `python3 -m pytest tests/test_bugreport.py -x -v`
Expected: all pass

- [ ] **Step 5: Run full lint**

Run: `python3 -m ruff check src/ tests/ && cd aegis-web && npx tsc --noEmit`

- [ ] **Step 6: Commit**

```bash
git add aegis-web/src/components/layout/HudOverlay.tsx aegis-web/src/components/hud/KeyboardHelp.tsx
git commit -m "Wire bug report overlay into HUD and add Shift+B shortcut"
```

---

### Task 6: Create user-report label on GitHub and test end-to-end

- [ ] **Step 1: Create the `user-report` label on GitHub**

```bash
gh label create "user-report" --description "Filed via in-app bug reporter" --color "d876e3"
```

- [ ] **Step 2: Build frontend and copy to static**

```bash
cd aegis-web && npm run build:copy
```

- [ ] **Step 3: Test the full flow locally (if dev server is running)**

Start backend: `python3 -m aegis.viewer` (in one terminal)
Start frontend: `cd aegis-web && npm run dev` (in another terminal)
Open `http://localhost:5173`, press Shift+B, draw on screenshot, type description, submit.
Verify: GitHub issue created with screenshot and state.

- [ ] **Step 4: Final commit with built frontend**

```bash
git add -A src/aegis/viewer/static/
git commit -m "Build frontend with bug reporter"
```

- [ ] **Step 5: Push to master**

```bash
git push origin master
```

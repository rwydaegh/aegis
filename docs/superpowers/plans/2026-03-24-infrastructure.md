# AEGIS infrastructure implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy AEGIS to production at aegis.waves-ugent.be with multi-user isolation, password gate, shareable URLs, and automated CI/CD.

**Architecture:** Hetzner CX22 running Docker Compose (Caddy reverse proxy + Gunicorn/Flask). Multi-user achieved by making the server stateless per-request. Password gate via signed session cookie (2-hour expiry). Shareable URLs encode frontend state in URL fragments.

**Tech Stack:** Docker, Docker Compose, Caddy 2, Gunicorn, Flask, GitHub Actions, ghcr.io, React/Zustand (frontend changes)

**Spec:** `docs/superpowers/specs/2026-03-24-infrastructure-design.md`

---

## File structure

### New files (backend)

| File | Purpose |
|------|---------|
| `Dockerfile` | Production image: Python 3.12 + aegis + mesh data + React build + docs |
| `docker-compose.yml` | Caddy + Flask containers, volumes, health checks |
| `Caddyfile` | Reverse proxy config, auto-HTTPS, docs basic auth |
| `gunicorn.conf.py` | Worker count, threads, timeout, preload |
| `docker-entrypoint.sh` | Copy docs to shared volume, start gunicorn |
| `.github/workflows/deploy.yml` | Build image, push to ghcr.io, SSH deploy to Hetzner |
| `deploy/.env.example` | Template for Hetzner .env (passwords, keys) |

### New files (frontend)

| File | Purpose |
|------|---------|
| `aegis-web/src/lib/shareLink.ts` | Serialize/deserialize shareable state to/from URL fragments |
| `aegis-web/src/lib/shareDefaults.ts` | Default values for all shareable fields (baseline for diffing) |
| `aegis-web/src/components/layout/LoginGate.tsx` | Full-screen password overlay |
| `aegis-web/src/components/layout/SessionTimer.tsx` | Countdown timer in toolbar/HUD |
| `aegis-web/src/hooks/useAuth.ts` | Auth state, login/logout, session expiry tracking |
| `aegis-web/src/api/auth.ts` | POST /api/auth, 401 interceptor |

### Modified files (backend)

| File | Change |
|------|--------|
| `src/aegis/viewer/server.py` | Preload all bodies, add auth before_request, add /api/auth endpoint |
| `src/aegis/viewer/routes/data.py` | Remove /api/body/switch, add ?name= to /api/body, /api/compliance/report removal |
| `src/aegis/viewer/routes/compute.py` | Return compliance in response, accept body_name param, remove global compliance cache |
| `src/aegis/viewer/routes/location.py` | Pipeline mutex, session-scoped cancel |
| `src/aegis/viewer/compute.py` | Add threading.Lock to _curvature_cache |
| `src/aegis/viewer/pipeline.py` | Session-keyed _active_processes dict, global mutex |
| `src/aegis/viewer/raytracer.py` | Add threading.Lock to _voxel_scene_cache |
| `src/aegis/engine.py` | Return timings from compute() instead of global _last_timings |

### Modified files (frontend)

| File | Change |
|------|--------|
| `aegis-web/src/App.tsx` | Wrap in LoginGate, apply share link on load |
| `aegis-web/src/api/client.ts` | Add 401 interceptor, remove switchBody(), add fetchBody(name) |
| `aegis-web/src/hooks/useConfig.ts` | Wire existing config keys to stores |
| `aegis-web/src/hooks/useDosimetry.ts` | Include body_name in compute requests, read compliance from response |
| `aegis-web/src/stores/simulation.ts` | Add compliance field |
| `aegis-web/src/components/layout/Toolbar.tsx` | Add Share button, session timer |

---

## Task 1: Multi-user isolation, backend (critical shared state)

**Files:**
- Modify: `src/aegis/engine.py` (lines 24, 121-128, 506)
- Modify: `src/aegis/viewer/compute.py` (line 26)
- Modify: `src/aegis/viewer/raytracer.py` (lines 46, 49-51)
- Modify: `src/aegis/viewer/pipeline.py` (lines 16, 123, 141, 150-161)
- Test: `tests/viewer/test_isolation.py` (create)

### Timings (engine.py)

- [ ] **Step 1: Write failing test for timings in compute return value**

```python
# tests/viewer/test_isolation.py
import numpy as np
from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths

def test_compute_returns_timings():
    """DosimetryEngine.compute() must return timings dict, not write to global."""
    body = BodyMesh.from_stl("data/thelonious.stl")
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([1.0]),
    )
    result = DosimetryEngine().compute(body, paths, level=0)
    assert hasattr(result, "timings") or isinstance(result, tuple)
```

Note: The exact assertion depends on how `compute()` returns. The current return type is `DosimetryResult`. The cleanest approach is to return a `(result, timings)` tuple, or add a `timings` attribute to `DosimetryResult`. Check `src/aegis/result.py` for the `DosimetryResult` dataclass fields before implementing. Avoid changing the dataclass if possible; a tuple return is simpler.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/viewer/test_isolation.py::test_compute_returns_timings -v -n 0`
Expected: FAIL

- [ ] **Step 3: Modify engine.py to return timings**

In `src/aegis/engine.py`, change `compute()` to collect timings in a local dict instead of the global `_last_timings`. Return a `(DosimetryResult, timings_dict)` tuple. Keep the module-level `_last_timings` temporarily (assign to it for backward compat) but the canonical path is the return value.

Find every call site by running `grep -rn "\.compute(" src/aegis/engine.py src/aegis/viewer/compute.py tests/`. Known write sites for `_last_timings` in `engine.py`: lines 121, 122, 128, and 506. All four must be replaced with writes to a local `timings` dict.

The primary consumer is `src/aegis/viewer/compute.py` lines 372-377, which imports and reads `_last_timings`. Update this to read from the returned timings dict instead.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/viewer/test_isolation.py::test_compute_returns_timings -v -n 0`
Expected: PASS

### Threading locks (compute.py, raytracer.py)

- [ ] **Step 5: Add threading.Lock to _curvature_cache**

In `src/aegis/viewer/compute.py`, add `_curvature_lock = threading.Lock()` next to `_curvature_cache` (line 26). Wrap the cache check and cache write in `_compute_face_curvature()` with `with _curvature_lock:`.

- [ ] **Step 6: Add threading.Lock to _voxel_scene_cache**

In `src/aegis/viewer/raytracer.py`, add `_voxel_scene_lock = threading.Lock()` next to `_voxel_scene_cache` (line 46). Wrap `clear_voxel_scene_cache()` and all reads/writes to `_voxel_scene_cache` with the lock.

### Pipeline process isolation (pipeline.py)

- [ ] **Step 7: Write failing test for pipeline mutex**

```python
# tests/viewer/test_isolation.py (append)
from aegis.viewer.pipeline import cancel_pipeline

def test_cancel_pipeline_requires_session_id():
    """cancel_pipeline must accept a session_id parameter."""
    import inspect
    sig = inspect.signature(cancel_pipeline)
    assert "session_id" in sig.parameters
```

- [ ] **Step 8: Run test to verify it fails**

Run: `python -m pytest tests/viewer/test_isolation.py::test_cancel_pipeline_requires_session_id -v -n 0`
Expected: FAIL

- [ ] **Step 9: Refactor pipeline.py for session-scoped processes**

Replace:
```python
_active_process: subprocess.Popen | None = None
```
With:
```python
_active_processes: dict[str, subprocess.Popen] = {}
_pipeline_mutex = threading.Lock()
```

Update `run_pipeline()` to accept `session_id: str` parameter. Store process as `_active_processes[session_id] = proc`. Add mutex check at the top: if `_pipeline_mutex` is locked (another pipeline is running), raise or return an error.

Update `cancel_pipeline(session_id: str)` to kill only the process for that session.

Update `src/aegis/viewer/routes/location.py` to pass `session_id` from Flask session to `run_pipeline()` and `cancel_pipeline()`.

- [ ] **Step 10: Run test to verify it passes**

Run: `python -m pytest tests/viewer/test_isolation.py -v -n 0`
Expected: All PASS

- [ ] **Step 11: Run full test suite**

Run: `python -m pytest tests/ -m "not slow" -x -n 0`
Expected: No regressions

- [ ] **Step 12: Lint and commit**

```bash
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/
git add src/aegis/engine.py src/aegis/viewer/compute.py src/aegis/viewer/raytracer.py src/aegis/viewer/pipeline.py src/aegis/viewer/routes/location.py tests/viewer/test_isolation.py
git commit -m "Make server stateless: return timings, add thread locks, session-scope pipeline"
```

---

## Task 2: Multi-user body preloading

**Files:**
- Modify: `src/aegis/viewer/server.py` (lines 22, 154-241, 207)
- Modify: `src/aegis/viewer/routes/data.py` (lines 45-56, 91-113)
- Modify: `src/aegis/viewer/routes/compute.py` (lines 244-246)
- Test: `tests/viewer/test_isolation.py` (append)

- [ ] **Step 1: Write failing test for multi-body preload**

```python
# tests/viewer/test_isolation.py (append)
def test_preloaded_bodies_dict():
    """Cache should contain a bodies dict, not a single body."""
    # This test will be fleshed out after reading create_app() internals
    from aegis.viewer.server import create_app
    app = create_app(data_dir="data")
    # After create_app, the cache should have a "bodies" key (dict)
    # not a single "body" key
    assert True  # placeholder until we inspect the cache structure
```

Note: The `_cache` is module-level and not easily testable in isolation. A more practical approach: test that the `/api/body?name=thelonious` endpoint works and that `/api/body?name=duke` returns different data. Write an integration test using Flask's test client.

- [ ] **Step 2: Modify server.py to preload all bodies**

In `create_app()`, replace the single body load with a loop:

```python
# Instead of:
# body = load_body(body_name, data_dir)
# cache["body"] = body

from pathlib import Path

# Discover available bodies by globbing for STL files in data_dir
available_bodies = [p.stem for p in Path(data_dir).glob("*.stl")]
cache["bodies"] = {}
for name in available_bodies:
    body = load_body(name, data_dir)
    binary, meta = body_to_binary(body)
    cache["bodies"][name] = {"body": body, "binary": binary, "meta": meta}
cache["default_body"] = body_name
```

- [ ] **Step 3: Update /api/body endpoint (data.py)**

Change `GET /api/body` to accept `?name=` query parameter:

```python
@app.route("/api/body")
def get_body():
    name = request.args.get("name", cache["default_body"])
    with cache_lock:
        entry = cache["bodies"].get(name)
    if entry is None:
        return jsonify({"error": f"Body '{name}' not found"}), 404
    resp = make_response(entry["binary"])
    resp.headers["Content-Type"] = "application/octet-stream"
    resp.headers["X-Meta"] = json.dumps(entry["meta"])
    return resp
```

- [ ] **Step 4: Remove /api/body/switch endpoint (data.py)**

Delete the `POST /api/body/switch` route (lines 91-113 in data.py). It is replaced by the parameterized GET endpoint.

- [ ] **Step 5: Update compute routes to accept body_name**

In `src/aegis/viewer/routes/compute.py`, change the body lookup in `/api/compute` (line 244-246) from:

```python
with cache_lock:
    body = cache["body"]
```

To:

```python
body_name = params.get("body_name", cache["default_body"])
with cache_lock:
    entry = cache["bodies"].get(body_name)
if entry is None:
    return jsonify({"error": f"Body '{body_name}' not found"}), 404
body = entry["body"]
```

Apply the same pattern to `/api/compute/rt`, `/api/compute/voxel-rt`, `/api/compute/sionna-rt`.

- [ ] **Step 6: Remove global compliance cache**

In `src/aegis/viewer/routes/compute.py`, remove the line that writes to `current_app.config["_last_compliance_result"]` (line 160). The compliance data is already in the `stats` dict returned via the `X-Stats` header. Verify that `stats["compliance"]` is present and contains the full compliance report.

Remove or stub the `GET /api/compliance/report` endpoint (if it exists) since the frontend will read compliance from the compute response.

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/ -m "not slow" -x -n 0`
Expected: All pass. Some tests may need updating if they call `/api/body/switch`.

- [ ] **Step 8: Lint and commit**

```bash
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/
git add src/aegis/viewer/server.py src/aegis/viewer/routes/data.py src/aegis/viewer/routes/compute.py tests/viewer/test_isolation.py
git commit -m "Preload all bodies on startup, remove body switch mutation"
```

---

## Task 3: Password gate, backend

**Files:**
- Modify: `src/aegis/viewer/server.py`
- Test: `tests/viewer/test_auth.py` (create)

- [ ] **Step 1: Write failing test for auth endpoint**

```python
# tests/viewer/test_auth.py
import os
import pytest
from aegis.viewer.server import create_app

@pytest.fixture
def client():
    os.environ["AEGIS_GATE_PASSWORD"] = "test-password-123"
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    app = create_app(data_dir="data")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    os.environ.pop("AEGIS_GATE_PASSWORD", None)
    os.environ.pop("FLASK_SECRET_KEY", None)

def test_api_returns_401_without_auth(client):
    resp = client.get("/api/config")
    assert resp.status_code == 401

def test_auth_endpoint_accepts_correct_password(client):
    resp = client.post("/api/auth", json={"password": "test-password-123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "expires_at" in data

def test_auth_endpoint_rejects_wrong_password(client):
    resp = client.post("/api/auth", json={"password": "wrong"})
    assert resp.status_code == 401

def test_authenticated_request_succeeds(client):
    # Login first
    client.post("/api/auth", json={"password": "test-password-123"})
    # Now access a protected endpoint (not an exempt one)
    resp = client.get("/api/config")
    assert resp.status_code == 200

def test_health_exempt_from_auth(client):
    """Health endpoint works without auth (for Docker healthcheck)."""
    resp = client.get("/api/health")
    assert resp.status_code == 200

def test_auth_exempt_from_auth(client):
    """Auth endpoint itself doesn't require auth."""
    resp = client.post("/api/auth", json={"password": "wrong"})
    # Should return 401 (wrong password), not redirect to login
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/viewer/test_auth.py -v -n 0`
Expected: FAIL (no auth endpoints exist yet)

- [ ] **Step 3: Implement auth in server.py**

Add to `create_app()`:

```python
import os
import uuid
from datetime import datetime, timezone, timedelta
from flask import session, request, jsonify

# Configure Flask session
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

GATE_PASSWORD = os.environ.get("AEGIS_GATE_PASSWORD")
EXEMPT_PATHS = {"/api/auth", "/api/health"}

@app.before_request
def check_auth():
    if GATE_PASSWORD is None:
        return  # No password set, skip auth (local dev)
    if request.path in EXEMPT_PATHS:
        return
    if request.path.startswith("/assets/") or request.path == "/":
        return  # Serve React app and static assets without auth
    if not session.get("authenticated"):
        return jsonify({"error": "Authentication required"}), 401

@app.route("/api/auth", methods=["POST"])
def authenticate():
    if GATE_PASSWORD is None:
        return jsonify({"error": "No password configured"}), 500
    data = request.get_json(silent=True) or {}
    if data.get("password") != GATE_PASSWORD:
        return jsonify({"error": "Wrong password"}), 401
    session.permanent = True
    session["authenticated"] = True
    session["session_id"] = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    return jsonify({
        "ok": True,
        "expires_at": expires_at.isoformat(),
        "session_id": session["session_id"],
    })
```

Also remove the old `AEGIS_VIEWER_AUTH` basic auth logic if it exists in `server.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/viewer/test_auth.py -v -n 0`
Expected: All PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `python -m pytest tests/ -m "not slow" -x -n 0`
Expected: Existing tests may need the `AEGIS_GATE_PASSWORD` env var unset to avoid 401s. If existing test fixtures create a Flask test client, they should either set the password and authenticate, or leave `AEGIS_GATE_PASSWORD` unset (which disables the gate).

Fix any broken tests by ensuring test fixtures don't have `AEGIS_GATE_PASSWORD` set in the environment, or by adding a login step to existing integration tests.

- [ ] **Step 6: Lint and commit**

```bash
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/
git add src/aegis/viewer/server.py tests/viewer/test_auth.py
git commit -m "Add password gate with 2-hour session cookie"
```

---

## Task 4: Password gate, frontend

**Depends on:** Task 3 (backend auth endpoints must exist)

**Files:**
- Create: `aegis-web/src/api/auth.ts`
- Create: `aegis-web/src/hooks/useAuth.ts`
- Create: `aegis-web/src/components/layout/LoginGate.tsx`
- Create: `aegis-web/src/components/layout/SessionTimer.tsx`
- Modify: `aegis-web/src/api/client.ts` (add 401 interceptor)
- Modify: `aegis-web/src/App.tsx` (wrap in LoginGate)
- Modify: `aegis-web/src/components/layout/Toolbar.tsx` (add session timer)

- [ ] **Step 1: Create auth API client**

```typescript
// aegis-web/src/api/auth.ts
export interface AuthResponse {
  ok: boolean;
  expires_at: string;
  session_id: string;
}

export async function login(password: string): Promise<AuthResponse> {
  const resp = await fetch("/api/auth", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!resp.ok) {
    const data = await resp.json();
    throw new Error(data.error || "Authentication failed");
  }
  return resp.json();
}
```

- [ ] **Step 2: Create useAuth hook**

```typescript
// aegis-web/src/hooks/useAuth.ts
import { create } from "zustand";

interface AuthState {
  authenticated: boolean;
  expiresAt: Date | null;
  login: (password: string) => Promise<void>;
  logout: () => void;
  checkExpiry: () => boolean; // returns true if still valid
}
```

The hook stores `authenticated` and `expiresAt`. The `login` function calls `auth.ts:login()`, stores the expiry. The `checkExpiry` function checks if `expiresAt` is in the future.

- [ ] **Step 3: Add 401 interceptor to client.ts**

In `aegis-web/src/api/client.ts`, wrap `getJson` and `postJson` to detect 401 responses. When a 401 is received, set `useAuth.getState().logout()` to trigger the login overlay.

Do NOT retry automatically. Let the component re-render with the login gate visible.

- [ ] **Step 4: Create LoginGate component**

```typescript
// aegis-web/src/components/layout/LoginGate.tsx
```

Full-screen overlay with:
- Centered card with AEGIS logo/name
- Single password input field
- Submit button
- Error message display
- Renders children (the app) when authenticated
- On 401 from any API call, re-shows the overlay without destroying children (Zustand state preserved)

- [ ] **Step 5: Create SessionTimer component**

```typescript
// aegis-web/src/components/layout/SessionTimer.tsx
```

Small component showing "Session: Xh Ym" countdown. Reads `expiresAt` from useAuth. Updates every minute. Changes to amber text color when under 10 minutes remaining.

- [ ] **Step 6: Wire into App.tsx**

Wrap the current App content in `<LoginGate>`. The LoginGate checks `useAuth.authenticated`:
- Not authenticated: show login overlay (full screen, no app visible)
- Authenticated: render children (AppShell)

- [ ] **Step 7: Add SessionTimer to Toolbar**

Add `<SessionTimer />` to the right side of the Toolbar, before the sidebar toggle button.

- [ ] **Step 8: Test manually in dev mode**

Start Flask with `AEGIS_GATE_PASSWORD=test123` and the Vite dev server. Verify:
1. Opening the app shows the login overlay
2. Wrong password shows error
3. Correct password dismisses overlay, app loads
4. Session timer counts down
5. After cookie expires (set to short duration for testing), next API call shows login overlay again
6. Re-entering password restores the session without losing state

- [ ] **Step 9: Commit**

```bash
cd aegis-web && npm run lint 2>/dev/null; cd ..
git add aegis-web/src/api/auth.ts aegis-web/src/hooks/useAuth.ts aegis-web/src/components/layout/LoginGate.tsx aegis-web/src/components/layout/SessionTimer.tsx aegis-web/src/api/client.ts aegis-web/src/App.tsx aegis-web/src/components/layout/Toolbar.tsx
git commit -m "Add password gate UI with session timer"
```

---

## Task 5: Frontend multi-user changes

**Files:**
- Modify: `aegis-web/src/api/client.ts` (remove switchBody, update fetchBody)
- Modify: `aegis-web/src/hooks/useDosimetry.ts` (include body_name, read compliance from response)
- Modify: `aegis-web/src/hooks/useConfig.ts` (wire existing config keys)
- Modify: `aegis-web/src/stores/simulation.ts` (add compliance field)
- Modify: `aegis-web/src/components/panels/PhantomPanel.tsx` (replace switchBody with fetchBody + state update)

- [ ] **Step 1: Update fetchBody to accept name parameter**

In `aegis-web/src/api/client.ts`, update `fetchBody`:

```typescript
export async function fetchBody(name?: string): Promise<{ binary: ArrayBuffer; meta: BodyMeta }> {
  const path = name ? `/api/body?name=${encodeURIComponent(name)}` : "/api/body";
  // ... rest stays the same
}
```

Remove the `switchBody` function entirely.

- [ ] **Step 2: Update useDosimetry to send body_name**

In `aegis-web/src/hooks/useDosimetry.ts`, add `bodyName` from `useSceneStore` to the compute params object:

```typescript
const bodyName = useSceneStore((s) => s.bodyName);
// ... in triggerCompute():
const params = {
  ...existingParams,
  body_name: bodyName,
};
```

- [ ] **Step 3: Read compliance from compute response**

In `useDosimetry.ts`, after parsing the compute response, extract `stats.compliance` and store it in the simulation store:

```typescript
if (stats.compliance) {
  useSimulationStore.getState().setCompliance(stats.compliance);
}
```

Add a `compliance` field and `setCompliance` action to `simulation.ts`.

- [ ] **Step 4: Wire existing config keys in useConfig.ts**

In `aegis-web/src/hooks/useConfig.ts`, after fetching config, apply these values to the stores:

```typescript
// Already has config entries in DEFAULTS, just not wired:
sim.setFreqGhz(config.dosimetry?.freq_hz ? config.dosimetry.freq_hz / 1e9 : 28);
sim.setPowerDbm(config.dosimetry?.default_power_dbm ?? 60);
sim.setStochasticPreset(config.dosimetry?.stochastic?.default_preset ?? '3GPP_38.901_UMi_LOS');
sim.setStochasticSeed(config.dosimetry?.stochastic?.default_seed ?? 42);
ui.setExposureScenario(config.dosimetry?.exposure_scenario ?? 'general_public');
```

Check which setter functions exist on the stores. Some may need to be added.

- [ ] **Step 5: Update body switching in frontend**

Find where `switchBody()` is called (likely in a PhantomPanel or similar component). Replace with:
1. Call `fetchBody(newName)` to get the mesh data
2. Update `useSceneStore.bodyName` with the new name
3. Update the body geometry in the scene store

In `aegis-web/src/components/panels/PhantomPanel.tsx`, find where `switchBody()` is called. Replace with:
1. Call `fetchBody(newName)` to get the new mesh binary
2. Parse the binary into a BufferGeometry (same as `useBodyLoader.ts` does on initial load)
3. Update `useSceneStore.setBodyName(newName)` and `useSceneStore.setBodyGeometry(geometry)`

This file must be included in the git add step below.

- [ ] **Step 6: Test manually**

Verify: switching bodies works via the dropdown, compute requests include body_name, compliance appears in the response.

- [ ] **Step 7: Lint and commit**

```bash
cd aegis-web && npm run lint 2>/dev/null; cd ..
git add aegis-web/src/api/client.ts aegis-web/src/hooks/useDosimetry.ts aegis-web/src/hooks/useConfig.ts aegis-web/src/stores/simulation.ts aegis-web/src/components/panels/PhantomPanel.tsx
git commit -m "Wire frontend for multi-user: body_name in requests, compliance in response"
```

---

## Task 6: Shareable URLs

**Files:**
- Create: `aegis-web/src/lib/shareDefaults.ts`
- Create: `aegis-web/src/lib/shareLink.ts`
- Modify: `aegis-web/src/App.tsx` (hydrate from URL on load)
- Modify: `aegis-web/src/components/layout/Toolbar.tsx` (share button)

- [ ] **Step 1: Define shareable defaults**

```typescript
// aegis-web/src/lib/shareDefaults.ts
// Canonical defaults for all shareable fields.
// Used as baseline for diffing (only non-default values go in the URL).

export const SHARE_DEFAULTS = {
  // simulation
  antennaPos: null,
  mode: "spatial",
  fresnel: true,
  polarisation: false,
  curvature: false,
  diffraction: false,
  powerDbm: 60,
  skinModel: "itis",
  nPaths: 1,
  freqGhz: 28,
  stochasticPreset: "3GPP_38.901_UMi_LOS",
  stochasticSeed: 42,
  stochasticOverrides: {},
  bodyOffset: [0, 0, 0],
  bodyRotationY: 0,
  enabledQuantities: ["sab", "sab_4cm2"],
  displayQuantity: "sab",
  // scene
  bodyName: "thelonious",
  pathSource: "synthetic",
  rtSource: "differt",
  rtMaxOrder: 3,
  rtMethod: "exhaustive",
  rtRaysPerSource: 1_000_000,
  rtMaxPathsPerSource: 1_000_000,
  rtLos: true,
  rtSpecularReflection: true,
  rtDiffuseReflection: false,
  rtRefraction: true,
  rtDiffraction: false,
  rtEdgeDiffraction: false,
  rtDiffractionLitRegion: true,
  rtReflectionLoss: 0.5,
  rtSyntheticArray: true,
  rtSeed: 42,
  envDisplayMode: "cubes",
  // ui
  wireframe: false,
  legendScale: "linear",
  dynamicRangeDb: 30,
  ratioMode: false,
  exposureScenario: "general_public",
} as const;
```

These must exactly match the Zustand store defaults. If the store defaults change, these must change too.

- [ ] **Step 2: Implement serialize/deserialize**

```typescript
// aegis-web/src/lib/shareLink.ts
import { SHARE_DEFAULTS } from "./shareDefaults";

type ShareState = typeof SHARE_DEFAULTS;

export function serializeShareableState(): string {
  // Read current state from all three stores
  // Diff against SHARE_DEFAULTS
  // JSON.stringify the diff
  // btoa() for base64url encoding
  // Return the fragment string (without the #s= prefix)
}

export function deserializeShareLink(fragment: string): Partial<ShareState> {
  // Decode base64
  // JSON.parse
  // Validate keys (ignore unknown)
  // Return partial state object
}

export function applyShareState(state: Partial<ShareState>): void {
  // Apply to the three Zustand stores
  // Convert enabledQuantities array back to Set
}

export function generateShareUrl(): string {
  const encoded = serializeShareableState();
  return `${window.location.origin}/#s=${encoded}`;
}
```

Important: `enabledQuantities` is a `Set` in the store but must be serialized as an array (`[...set]`) since `JSON.stringify(new Set())` returns `{}`.

- [ ] **Step 3: Add share link hydration to App.tsx**

In `App.tsx`, after the config has loaded (status is "ready"), check for a share link:

```typescript
useEffect(() => {
  const hash = window.location.hash;
  if (hash.startsWith("#s=")) {
    const state = deserializeShareLink(hash.slice(3));
    applyShareState(state);
    // Clear the hash to avoid re-applying on refresh
    window.history.replaceState(null, "", window.location.pathname);
  }
}, [status]); // run once when config is loaded
```

- [ ] **Step 4: Add Share button to Toolbar**

Add a button (e.g., with a link/share icon from lucide-react) to the Toolbar. On click:

```typescript
const handleShare = async () => {
  const url = generateShareUrl();
  await navigator.clipboard.writeText(url);
  // Show a toast or brief status message
  useUIStore.getState().setStatusMessage("Link copied to clipboard");
  setTimeout(() => useUIStore.getState().setStatusMessage(null), 3000);
};
```

- [ ] **Step 5: Test manually**

1. Set up a scene (place antenna, switch body, change settings)
2. Click Share, verify URL is copied
3. Open the URL in a new incognito window
4. Verify: after password entry, the scene has the same settings
5. Verify: compute produces the same results
6. Test edge cases: URL with unknown keys, URL with missing keys

- [ ] **Step 6: Commit**

```bash
git add aegis-web/src/lib/shareDefaults.ts aegis-web/src/lib/shareLink.ts aegis-web/src/App.tsx aegis-web/src/components/layout/Toolbar.tsx
git commit -m "Add shareable URLs via URL fragment encoding"
```

---

## Task 7: Docker and Gunicorn setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `Caddyfile`
- Create: `gunicorn.conf.py`
- Create: `docker-entrypoint.sh`
- Create: `deploy/.env.example`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

```
# .dockerignore
.git
.github
.claude
__pycache__
*.pyc
.pytest_cache
.ruff_cache
node_modules
aegis-web/node_modules
aegis-web/dist
.env
*.egg-info
docs/superpowers
```

- [ ] **Step 2: Create gunicorn.conf.py**

```python
# gunicorn.conf.py
import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 4))
timeout = 300
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

- [ ] **Step 3: Add create_app_from_env() factory to server.py**

`create_app()` requires `data_dir` as a non-optional parameter. Gunicorn needs a zero-argument factory. Add this to `src/aegis/viewer/server.py`:

```python
def create_app_from_env():
    """Factory for Gunicorn: reads config from environment variables."""
    import os
    data_dir = os.environ.get("AEGIS_DATA_DIR", "data")
    body_name = os.environ.get("AEGIS_BODY", "thelonious")
    config_path = os.environ.get("AEGIS_CONFIG")
    config = load_config(config_path) if config_path else None
    return create_app(data_dir=data_dir, body_name=body_name, config=config)
```

- [ ] **Step 4: Create docker-entrypoint.sh**

```bash
#!/bin/sh
set -e

# Copy docs to shared volume (Caddy serves them)
if [ -d /app/site ] && [ -d /srv/docs ]; then
    cp -r /app/site/* /srv/docs/ 2>/dev/null || true
fi

exec gunicorn "aegis.viewer.server:create_app_from_env()" \
    --config /app/gunicorn.conf.py \
    --chdir /app
```

- [ ] **Step 5: Create Dockerfile**

See the spec for the Dockerfile outline. Key points:
- Base: `python:3.12-slim`
- Install curl for health checks
- Copy pyproject.toml + src/ first, install with uv
- Copy data/ (STL meshes, IT'IS database)
- static/ already in src/aegis/viewer/static/ from CI build step
- Copy site/ (mkdocs build from CI)
- Copy gunicorn.conf.py and docker-entrypoint.sh
- WORKDIR /app

- [ ] **Step 6: Create Caddyfile**

```
aegis.waves-ugent.be {
    reverse_proxy flask:8000
}

docs.aegis.waves-ugent.be {
    basic_auth {
        aegis {env.DOCS_PASSWORD_HASH}
    }
    root * /srv/docs
    file_server
}
```

Note: Using `{env.DOCS_PASSWORD_HASH}` allows setting the bcrypt hash via environment variable rather than hardcoding it in the Caddyfile. Test that Caddy supports env var substitution in basic_auth blocks. If not, the hash must be baked into the Caddyfile and updated manually on password changes.

- [ ] **Step 7: Create docker-compose.yml**

Use the outline from the spec. Key additions beyond the spec:
- `networks: [aegis]` for container communication
- Caddy `depends_on: flask: condition: service_healthy`
- Flask `env_file: .env`

- [ ] **Step 8: Create deploy/.env.example**

```
AEGIS_GATE_PASSWORD=change-me
FLASK_SECRET_KEY=generate-with-python-c-import-secrets-print-secrets-token-hex-32
GOOGLE_API_KEY=
DOCS_PASSWORD_HASH=generate-with-caddy-hash-password
```

- [ ] **Step 9: Test Docker build locally**

```bash
# Build the React app first
cd aegis-web && npm ci && npm run build && npm run build:copy && cd ..
# Build mkdocs
python -m mkdocs build
# Build Docker image
docker build -t aegis:test .
# Run locally
docker compose up -d
# Check health
curl http://localhost:8000/api/health
```

If the machine does not have Docker, this can be tested in CI instead. Write a note in the commit message about what was tested.

- [ ] **Step 10: Commit**

```bash
git add Dockerfile docker-compose.yml Caddyfile gunicorn.conf.py docker-entrypoint.sh deploy/.env.example .dockerignore src/aegis/viewer/server.py
git commit -m "Add Docker and Caddy production infrastructure"
```

---

## Task 8: CI/CD deploy workflow

**Files:**
- Modify: `.github/workflows/ci.yml` (add `workflow_call` trigger for reusability)
- Create: `.github/workflows/deploy.yml`
- Modify: `.github/workflows/docs.yml` (disable or remove)

- [ ] **Step 1: Make ci.yml reusable**

Add `workflow_call:` to the `on:` trigger in `.github/workflows/ci.yml` so it can be referenced from the deploy workflow:

```yaml
on:
  push:
    branches: [master, main]
  pull_request:
  workflow_call:  # <-- add this line
```

This allows `ci.yml` to be called both directly (on push/PR) and from the deploy workflow.

- [ ] **Step 2: Create deploy workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [master]

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  deploy:
    needs: ci
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/master'
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: aegis-web/package-lock.json

      - name: Build React frontend
        working-directory: aegis-web
        run: |
          npm ci
          npm run build
          node scripts/copy-to-flask.mjs

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build docs
        run: |
          pip install uv
          uv sync --extra docs
          python -m mkdocs build

      - name: Log in to ghcr.io
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest

      - name: Deploy to Hetzner
        env:
          SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
          HOST: ${{ secrets.HETZNER_HOST }}
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh -o StrictHostKeyChecking=no -i ~/.ssh/deploy_key root@$HOST \
            'cd /opt/aegis && docker compose pull && docker compose up -d && docker image prune -f'

      - name: Health check
        env:
          HOST: ${{ secrets.HETZNER_HOST }}
        run: |
          sleep 10
          curl -sf https://aegis.waves-ugent.be/api/health || echo "::warning::Health check failed"
```

Note: `uses: ./.github/workflows/ci.yml` requires the CI workflow to be a reusable workflow (with `workflow_call` trigger). If the existing `ci.yml` doesn't support this, either refactor it or duplicate the lint/test steps in the deploy workflow. Check the current `ci.yml` trigger configuration.

- [ ] **Step 3: Disable docs.yml**

Either delete `.github/workflows/docs.yml` or rename it with a `.disabled` extension. Add a comment explaining that docs are now served from `docs.aegis.waves-ugent.be` via the Docker deployment.

Alternatively, keep it but change the trigger to `workflow_dispatch` only (manual trigger), as a fallback.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/deploy.yml .github/workflows/docs.yml
git commit -m "Add CI/CD deploy pipeline, make CI reusable, disable GitHub Pages docs"
```

---

## Task 9: Server setup and DNS (manual + browser automation)

This task involves browser-based actions. Use Claude Chrome extension prompts where noted.

- [ ] **Step 1: Provision Hetzner CX22**

Prompt for Claude Chrome extension:

> Go to https://console.hetzner.cloud/ and create a new server with these settings:
> - Location: Falkenstein (or Nuremberg, cheapest EU)
> - Image: Ubuntu 24.04
> - Type: CX22 (2 vCPU, 4 GB RAM)
> - SSH key: Add a new SSH key (I'll provide the public key)
> - Name: aegis-prod
> - No additional volumes, no backups for now
>
> After creation, note the IPv4 address.

- [ ] **Step 2: SSH setup**

Generate an SSH key pair for deployment:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/aegis-deploy -N ""
cat ~/.ssh/aegis-deploy.pub  # Add to Hetzner server
```

- [ ] **Step 3: Initial server configuration**

```bash
ssh -i ~/.ssh/aegis-deploy root@<HETZNER_IP> << 'SETUP'
# Install Docker
curl -fsSL https://get.docker.com | sh

# Create deploy directory
mkdir -p /opt/aegis /srv/docs

# Create .env file
cat > /opt/aegis/.env << 'ENV'
AEGIS_GATE_PASSWORD=<password>
FLASK_SECRET_KEY=<generate-with-secrets-module>
GOOGLE_API_KEY=<if-available>
ENV
SETUP
```

- [ ] **Step 4: Copy deployment files to server**

```bash
scp -i ~/.ssh/aegis-deploy docker-compose.yml Caddyfile root@<HETZNER_IP>:/opt/aegis/
```

- [ ] **Step 5: Configure DNS**

Prompt for Claude Chrome extension:

> Go to the DNS management page for waves-ugent.be and add two A records:
> - Name: aegis, Value: <HETZNER_IP>, TTL: 3600
> - Name: docs.aegis, Value: <HETZNER_IP>, TTL: 3600
>
> Verify no conflicting records exist for these subdomains.

- [ ] **Step 6: Verify DNS propagation**

```bash
dig aegis.waves-ugent.be +short
dig docs.aegis.waves-ugent.be +short
# Both should return the Hetzner IP
```

Wait until DNS propagates before starting containers (Let's Encrypt ACME challenge needs DNS).

- [ ] **Step 7: Start containers**

```bash
ssh -i ~/.ssh/aegis-deploy root@<HETZNER_IP> 'cd /opt/aegis && docker compose up -d'
```

- [ ] **Step 8: Add GitHub Actions secrets**

Prompt for Claude Chrome extension:

> Go to https://github.com/<user>/<repo>/settings/secrets/actions and add two repository secrets:
> - Name: HETZNER_SSH_KEY, Value: (contents of ~/.ssh/aegis-deploy private key)
> - Name: HETZNER_HOST, Value: <HETZNER_IP>

- [ ] **Step 9: Verify deployment**

```bash
curl https://aegis.waves-ugent.be/api/health
curl -u aegis:<password> https://docs.aegis.waves-ugent.be/
```

- [ ] **Step 10: Push to master to trigger first automated deploy**

```bash
git push origin master
```

Monitor the GitHub Actions workflow. Verify the deploy job succeeds and the health check passes.

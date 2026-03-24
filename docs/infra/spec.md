# AEGIS infrastructure: production deployment and multi-user support

**Date**: 2026-03-24
**Status**: Approved
**Scope**: Deployment, multi-user isolation, password gate, shareable URLs, CI/CD

## Context

AEGIS has outgrown its single-user, run-locally origins. The viewer needs to be hosted at `aegis.waves-ugent.be` where multiple people (Robin's promoters, collaborators) can use it simultaneously without interference. The GitHub repo is going private (embargo), so all infrastructure must work regardless of repo visibility.

### Current state

- Flask dev server (single-threaded, port 5000) serves a React build from `static/`
- No database, no sessions, no containerization, no deployment pipeline
- Module-level `_cache` dict with shared mutable state (body mesh, voxels, compliance results)
- Single-user assumption baked into the server (concurrent users overwrite each other's state)
- Optional HTTP Basic Auth via `AEGIS_VIEWER_AUTH` env var (browser popup)
- Docs hosted on GitHub Pages (breaks if repo goes private on free plan)
- Development happens on a TensorDock cloud GPU machine

### Goals

1. Host the viewer at `aegis.waves-ugent.be` with HTTPS
2. Host docs at `docs.aegis.waves-ugent.be` with HTTPS
3. Multiple users can compute simultaneously without interference
4. Shared password gate (styled login page, 2-hour cookie)
5. Shareable URLs that encode a user's scenario setup
6. Automated deployment from GitHub push
7. Works with private or public repo

### Non-goals (v1)

- Per-user accounts, registration, OAuth
- Per-session voxel/location data (everyone sees the same loaded location)
- Data-driven share links (storing computed results)
- Serverless GPU integration (architecture allows it, not implemented)
- Database (no SQLite, no persistence beyond pipeline cache)
- Monitoring, alerting, error tracking (Sentry, Grafana)
- Rate limiting, CDN, automated backups

### Migration note

The existing `.github/workflows/docs.yml` deploys docs to GitHub Pages. This workflow should be disabled or removed once docs are served from `docs.aegis.waves-ugent.be`. On a private repo without a paid GitHub plan, the GH Pages workflow fails silently anyway.

## Architecture

### Infrastructure topology

```
Developer (TensorDock dev machine)
  │
  │  git push → GitHub (private repo)
  │
  ▼
GitHub Actions
  │  CI: lint + test (existing)
  │  Deploy: build Docker image → push ghcr.io → SSH restart (new)
  │
  ▼
Hetzner CX22 (2 vCPU, 4 GB RAM, 40 GB disk, ~4.35 EUR/month)
  │
  ├── Caddy container
  │     ├── aegis.waves-ugent.be → reverse proxy → flask:8000
  │     └── docs.aegis.waves-ugent.be → basic auth → static /srv/docs/
  │
  └── Flask container
        ├── Gunicorn (2 workers, 4 threads each, preload)
        ├── Serves React build (static/) + API endpoints
        └── Docs copied to shared volume on startup

DNS (waves-ugent.be registrar):
  aegis.waves-ugent.be       → A record → Hetzner IP
  docs.aegis.waves-ugent.be  → A record → Hetzner IP
```

### Key technology choices

| Choice | Why |
|--------|-----|
| **Hetzner CX22** | 4.35 EUR/month, excellent uptime, good European network. TensorDock CPU-only (14 EUR/month) is worse value. |
| **Caddy** over Nginx | Auto-provisions and renews Let's Encrypt HTTPS certs with zero config. Human-readable Caddyfile. |
| **Gunicorn** over Flask dev server | Multi-worker, production-grade. Flask's built-in server is single-threaded and not meant for production. |
| **Docker Compose** | Reproducible deploys, works anywhere, isolates dependencies. Two containers (Caddy + Flask). |
| **ghcr.io** | Free container registry for private repos. CI already on GitHub Actions. |
| **gthread worker class** | Threads handle I/O-bound requests (mesh serving, SSE) without blocking CPU-bound compute. NumPy releases the GIL during array ops. |
| **preload_app** | Loads all body meshes once in the master process. Workers inherit via fork + COW. 4 bodies shared in ~120 MB instead of ~120 MB per worker. |

### Docker Compose

Two containers, one network:

**caddy**: Reverse proxy, HTTPS termination, auto-cert renewal. Routes `aegis.waves-ugent.be` to `flask:8000`. Serves docs from shared volume at `docs.aegis.waves-ugent.be` with Basic Auth. Persists certs in a named volume.

**flask**: Gunicorn with 2 workers (matching vCPU count), 4 threads each. Binds to port 8000 (internal only). Loads all body meshes on startup. Env vars for password and API keys. Health check on `/api/health`. On startup, copies built docs to shared volume. Pipeline cache in a named volume (persists across deploys).

### Caddyfile

```
aegis.waves-ugent.be {
    reverse_proxy flask:8000
}

docs.aegis.waves-ugent.be {
    basic_auth {
        aegis <bcrypt-hashed-password>
    }
    root * /srv/docs
    file_server
}
```

The Basic Auth username is `aegis` (arbitrary, shared with the password). Generate the hash with `caddy hash-password --plaintext '<password>'`.

### Docker Compose outline

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - docs_site:/srv/docs:ro
    depends_on:
      flask:
        condition: service_healthy

  flask:
    image: ghcr.io/<user>/aegis:${IMAGE_TAG:-latest}
    restart: unless-stopped
    env_file: .env
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    volumes:
      - docs_site:/srv/docs
      - pipeline_cache:/app/pipeline_cache
    mem_limit: 3g

volumes:
  caddy_data:
  caddy_config:
  docs_site:
  pipeline_cache:
```

The `IMAGE_TAG` env var defaults to `latest` but can be overridden for rollbacks. The `mem_limit: 3g` on the Flask container prevents runaway compute from OOM-killing the host (leaves ~1 GB for the OS, Caddy, and Docker overhead).

### Gunicorn config

```python
bind = "0.0.0.0:8000"
workers = 2
worker_class = "gthread"
threads = 4
timeout = 300
preload_app = True
accesslog = "-"
```

Timeout is 300 seconds (5 minutes) to accommodate high-fidelity compute on large meshes under CPU-only conditions. If a request genuinely takes longer than this, it should be redesigned as an async job.

### Memory budget (2 workers, preloaded)

| Component | Estimate |
|-----------|----------|
| OS + Docker + Caddy | ~550 MB |
| Gunicorn master + 4 preloaded bodies (~30 MB each) | ~250 MB |
| 2 workers (Python/NumPy, COW-shared meshes) | ~400 MB |
| Voxel data + compute headroom | ~2.8 GB remaining |

## Multi-user isolation

### Shared mutable state audit

Six issues found, three critical:

| # | Location | Variable | Problem | Severity |
|---|----------|----------|---------|----------|
| 1 | `server.py` | `_cache["body"]` | Body switch overwrites for all users | Critical |
| 2 | `routes/compute.py` | `app.config["_last_compliance_result"]` | User A gets user B's compliance report | Critical |
| 3 | `pipeline.py` | `_active_process` | Cancel kills the wrong user's pipeline | Critical |
| 4 | `compute.py` | `_curvature_cache` | No thread lock, cache thrash between bodies | Moderate |
| 5 | `raytracer.py` | `_voxel_scene_cache` | Cleared during location reload, concurrent RT could fail | Moderate |
| 6 | `engine.py` | `_last_timings` | User A's response shows user B's timing data | Moderate |

### Fixes

**1. Body mesh (critical)**

Preload all 4 bodies (thelonious, duke, eartha, ella) on startup into a read-only dict keyed by name. The compute endpoint accepts `body_name` as a request parameter and selects from the preloaded set. The `/api/body` endpoint accepts a `?name=` query parameter. Remove the `/api/body/switch` mutation endpoint entirely.

Frontend change: when user switches body in the dropdown, fetch the new mesh via `/api/body?name=duke` and include `body_name` in compute requests. No global state mutation.

**2. Compliance result (critical)**

Return the compliance JSON in the compute response. Either extend the `X-Stats` response header to include the compliance object, or add a separate `X-Compliance` header. Remove `app.config["_last_compliance_result"]`. The `/api/compliance/report` endpoint either reads from a session-scoped store or is removed (frontend has the data).

Frontend change: `useDosimetry` stores the compliance result in the simulation Zustand store on compute response.

**3. Pipeline process (critical)**

Replace the global `_active_process` with a dict keyed by session ID from the auth cookie. Each user can only cancel their own pipeline. For v1, add a global mutex: if any pipeline is running, reject new pipeline requests with a message ("Location pipeline is busy, please try again later"). This prevents the concurrent-write race on pipeline output directories.

**4. Curvature cache (moderate)**

Add a `threading.Lock` around cache reads and writes. The cache is keyed by geometry hash, so cross-user reads produce correct results. The lock prevents dict mutation races.

**5. Voxel scene cache (moderate)**

Add a `threading.Lock`. For v1 (single active location), clear-on-reload affects everyone, which is correct (everyone sees the same location).

**6. Timings (moderate)**

Return a timings dict from `DosimetryEngine.compute()` instead of writing to the module-level `_last_timings` dict. The compute route reads timings from the return value.

### What stays shared (correctly)

- Preloaded body meshes (read-only after startup)
- Voxel geometry (one active location, read-only between reloads)
- GLB tiles (read-only)
- Config (set once at startup)
- DiffeRT scene cache (geometry-hash-keyed, immutable objects)

## Password gate

### Flow

1. User visits `aegis.waves-ugent.be`. React app loads (JS bundle is not secret, all data comes from authenticated API calls).
2. React makes first API call. Flask's `@app.before_request` handler checks for the auth cookie.
3. No cookie or expired cookie: return 401.
4. React receives 401, renders a full-screen login overlay (password field only, no username). The 3D scene is not visible behind it.
5. User submits password. POST to `/api/auth` with `{"password": "..."}`.
6. Server compares against `AEGIS_GATE_PASSWORD` env var (plaintext comparison, not hashed, because it is a shared gate password, not a user credential).
7. Match: set a signed session cookie via Flask's `itsdangerous`-based session. Cookie properties: `httponly=True`, `secure=True`, `samesite=Lax`, `max_age=7200` (2 hours). Cookie payload: `{"authenticated": true, "session_id": "<uuid4>"}`. Return 200.
8. No match: return 401 with `{"error": "Wrong password"}`.
9. React dismisses the overlay on 200. User sees the app.

### Session timer in the UI

The frontend displays a session countdown in a subtle location (e.g., bottom status bar or near the server info HUD). Shows remaining time: "Session: 1h 42m". When under 10 minutes, the indicator changes color (e.g., amber) to warn the user they will be prompted to re-authenticate soon. This keeps the promoters aware that sessions are time-limited (embargo concern) and prevents surprise logouts.

The expiry timestamp is derived from the cookie's `max_age` (2 hours from auth). The `/api/auth` response includes `expires_at` (ISO timestamp) so the frontend can compute the countdown without inspecting the cookie directly.

### Cookie expiry mid-session

Cookie expires after 2 hours. User's next API call returns 401. React shows the login overlay again. Zustand state is still in memory, so after re-auth the user is exactly where they left off. No state lost.

### Password change

Update `AEGIS_GATE_PASSWORD` env var, restart Flask (`docker compose restart flask`). Existing cookies remain valid until they expire (up to 2 more hours). Unauthorized person's cookie expires, they try to re-auth with the old password, it fails. To force immediate invalidation of all cookies, change Flask's `SECRET_KEY` env var and restart. This invalidates all signed cookies.

### Docs authentication

Caddy Basic Auth on `docs.aegis.waves-ugent.be`. Same password, different mechanism (browser popup vs. styled page). The password is bcrypt-hashed in the Caddyfile. When the password changes, regenerate the hash with `caddy hash-password`.

### Exempt endpoints

`/api/auth` and `/api/health` are exempt from the auth check. All other endpoints require a valid cookie.

## Shareable URLs

### Concept

A "Share" button in the toolbar lets users generate a URL that encodes their current scenario setup. The recipient opens the URL, enters the password if needed, and sees the same setup. They hit compute to see results.

This is config-driven (encodes parameters), not data-driven (does not store computed results).

### Encoding

1. Frontend collects all user-settable state from the three Zustand stores (~35 fields).
2. Diffs against defaults: only includes fields that differ from their default values.
3. JSON-stringifies the diff object.
4. Base64url-encodes the JSON string.
5. Puts it in the URL fragment: `aegis.waves-ugent.be/#s=eyJhcCI6WzEuNSwwLDIuM10sImx2Ijo1fQ`

URL fragments (after `#`) are never sent to the server. Pure client-side.

### Shareable state surface

**Simulation store**: `antennaPos`, `mode`, `fresnel`, `polarisation`, `curvature`, `diffraction`, `powerDbm`, `skinModel`, `nPaths`, `freqGhz`, `stochasticPreset`, `stochasticSeed`, `stochasticOverrides`, `bodyOffset`, `bodyRotationY`, `enabledQuantities` (serialized as array, not Set), `displayQuantity`.

**Scene store**: `bodyName`, `pathSource`, `rtSource`, `rtMaxOrder`, `rtMethod`, `rtRaysPerSource`, `rtMaxPathsPerSource`, `rtLos`, `rtSpecularReflection`, `rtDiffuseReflection`, `rtRefraction`, `rtDiffraction`, `rtEdgeDiffraction`, `rtDiffractionLitRegion`, `rtReflectionLoss`, `rtSyntheticArray`, `rtSeed`, `envDisplayMode`.

**UI store**: `wireframe`, `legendScale`, `dynamicRangeDb`, `ratioMode`, `exposureScenario`.

**Not shareable**: Computed results (recomputed by recipient), voxel/location data (server state), camera position (low priority, skipped), transient UI state (`isComputing`, `locationLog`).

### URL size

Worst case (all 35 fields differ from defaults): ~300-400 chars of JSON, ~500-530 chars base64-encoded. Well within browser URL limits (2000-8000 chars). No compression needed.

### Receiving a share link

1. React app loads, checks for `#s=` in `window.location.hash`.
2. If present, decodes base64, parses JSON.
3. Unknown keys are ignored (forward-compatible with schema changes).
4. Valid keys are applied to Zustand stores, overriding defaults.
5. If user isn't authenticated, login overlay appears first. After auth, the fragment is still in the URL and gets applied. No state lost.
6. If `antennaPos` is set, the scene renders with the antenna placed. User hits compute to see results.

### Frontend prerequisites

The config audit found that ~25 user-settable fields are hardcoded in the Zustand stores and not wired to the server config. To make shareable URLs work:

1. **Wire existing config keys** (7 fields): `powerDbm`, `freqGhz`, `bodyName`, `stochasticPreset`, `stochasticSeed`, `rtReflectionLoss`, `exposureScenario` already have entries in `config.py` DEFAULTS but the frontend ignores them. Wire `useConfig.ts` to read these.
2. **Define defaults for remaining fields**: Add ~18 new default values to a frontend constants file (not necessarily to `config.py`). These serve as the baseline for the share-link diff.
3. **Implement `serializeShareableState()`**: Reads current state from all three stores, diffs against defaults, returns base64url-encoded JSON.
4. **Implement `hydrateFromShareLink()`**: Reads URL fragment, parses, validates, applies to stores.
5. **Add Share button** to the toolbar with clipboard copy and toast notification.

### Edge cases

- **Body not available on server**: Frontend shows error "Body 'duke' not available on this server."
- **RT settings but no voxels loaded**: RT compute fails with a descriptive error message.
- **Location changed since link was created**: Results may differ. Acceptable for v1 (single active location).
- **Old share link after schema changes**: Unknown keys ignored, missing keys use defaults.

## Deployment pipeline

### CI/CD workflow (new)

A new GitHub Actions workflow (`.github/workflows/deploy.yml`) or an extension of the existing CI workflow:

```
Push to master
  │
  ├── CI job (existing)
  │   ├── ruff check + format
  │   └── pytest matrix (ubuntu/windows x 3.11/3.12)
  │
  └── Deploy job (new, runs after CI passes, only on master)
      ├── npm ci && npm run build (in aegis-web/)
      ├── npm run build:copy (dist/ → static/)
      ├── pip install mkdocs-material && mkdocs build (→ site/)
      ├── docker build -t ghcr.io/<user>/aegis:$SHA -t ghcr.io/<user>/aegis:latest .
      ├── docker push ghcr.io/<user>/aegis:$SHA
      ├── docker push ghcr.io/<user>/aegis:latest
      ├── ssh hetzner 'cd /opt/aegis && docker compose pull && docker compose up -d'
      ├── ssh hetzner 'docker image prune -f'
      └── curl -sf https://aegis.waves-ugent.be/api/health || echo "Deploy health check failed"
```

### Docker image

```dockerfile
FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Python deps + install package
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN pip install uv && uv pip install ".[rt,sionna]" --python 3.12

# Phantom mesh data (STL files + IT'IS database)
# These are tracked via Git LFS. CI checks out with LFS enabled.
COPY data/ data/

# Pre-built React app (built in CI, copied into static/ before docker build)
# Already at src/aegis/viewer/static/ from the build:copy step

# Pre-built docs (built in CI)
COPY site/ site/

# Gunicorn config
COPY gunicorn.conf.py /app/gunicorn.conf.py

# Entrypoint copies docs to shared volume, then starts gunicorn
COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
```

Note on phantom meshes: STL files are tracked via Git LFS. The CI workflow must check out with `lfs: true` (the existing `full-tests.yml` already does this). If LFS files are unavailable, the image builds but the viewer will have no body meshes.

Note on the voxel pipeline: The Docker image does not include Node.js. The location loading feature (`/api/location/load`) will not work in the production Docker deployment. Locations must be pre-cached: run the pipeline locally or on the dev machine, then copy the cached voxel data into the `pipeline_cache` Docker volume. This is acceptable for v1 since locations change infrequently.

### Image tagging

- Every push to master: tagged with commit SHA and `latest`
- Version tags (e.g., `v0.4.0`): tagged with version string

### Rollback

Deploy a previous image by SHA: `ssh hetzner 'cd /opt/aegis && IMAGE_TAG=abc1234 docker compose up -d'`

After each deploy, clean up old images: `ssh hetzner 'docker image prune -f'`

### First-time server setup (manual, once)

1. Provision Hetzner CX22 (Ubuntu 24.04)
2. SSH in, install Docker: `curl -fsSL https://get.docker.com | sh`
3. Create `/opt/aegis/`, copy `docker-compose.yml`, `Caddyfile`, `.env`
4. Add DNS A records: `aegis.waves-ugent.be` and `docs.aegis.waves-ugent.be` to Hetzner IP
5. Verify DNS propagation: `dig aegis.waves-ugent.be` should return the Hetzner IP. Caddy's ACME challenge will fail if DNS is not propagated, and Let's Encrypt rate-limits retries.
6. `cd /opt/aegis && docker compose up -d`
7. Caddy auto-provisions HTTPS certs on first request

### Secrets management

GitHub Actions secrets:
- `HETZNER_SSH_KEY`: Private SSH key for deployment
- `HETZNER_HOST`: Server IP address

Hetzner `.env` file:
- `AEGIS_GATE_PASSWORD`: Shared password for the gate
- `GOOGLE_API_KEY`: For the voxel location pipeline
- `FLASK_SECRET_KEY`: For signing session cookies. Set once, persist across deploys. If generated randomly at container startup, every deploy would invalidate all sessions. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`

## Future considerations (not in v1)

### Serverless GPU

The architecture supports adding a serverless GPU endpoint (Modal, RunPod) without structural changes. The flow would be: Flask receives a GPU compute request, proxies it to the serverless provider, streams the result back. A "Connect to GPU" toggle in the frontend would switch between local CPU compute and remote GPU compute. The `/api/compute` endpoint already returns binary data regardless of how it was computed.

### Per-session locations

If different users need different voxel environments simultaneously, the voxel data would need to be scoped by session ID. The pipeline cache already organizes by location slug (`slug_rN/`). The fix: instead of one active voxel set in `_cache`, maintain a dict of loaded locations and let the session cookie determine which one to use. This is a moderate refactor of `routes/location.py` and `routes/data.py`.

### Saved scenarios with database

If shareable URLs are insufficient (URLs are ephemeral, can't be browsed or searched), add SQLite with a single `scenarios` table: `id`, `name`, `config_json`, `created_at`. Short URLs like `aegis.waves-ugent.be/s/abc123` resolve to stored configs. SQLite file in a Docker volume. One migration, one table, ~50 lines of code.

### Per-user accounts

If the embargo lifts and the tool goes public, replace the shared password gate with proper authentication. Options: Flask-Login with a `users` SQLite table, or an external provider (Auth0, Clerk) for zero-maintenance OAuth. The session cookie infrastructure from v1 carries over.

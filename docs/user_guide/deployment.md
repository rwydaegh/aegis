# Production deployment

AEGIS runs at [aegis.waves-ugent.be](https://aegis.waves-ugent.be). The documentation site is at [docs.aegis.waves-ugent.be](https://docs.aegis.waves-ugent.be). Both use HTTPS certificates provisioned automatically by Caddy.

## Architecture

Two Docker containers run on a Hetzner CX22 (2 vCPU, 4 GB RAM, ~4.35 EUR/month):

```
Internet
   │
   ├── aegis.waves-ugent.be ──► Caddy ──► Gunicorn/Flask (:8000)
   │                             (auto-HTTPS)   2 workers, 4 threads
   │
   └── docs.aegis.waves-ugent.be ──► Caddy ──► static HTML
                                      (basic auth)
```

Caddy handles TLS termination and reverse proxying. Gunicorn runs Flask with `preload_app=True`, so all four body meshes are loaded once and shared across workers via copy-on-write.

## Access control

A shared password protects the viewer. Users see a login form on first visit. After entering the password, a signed session cookie grants access for 2 hours. The session timer in the top-right toolbar shows remaining time.

The password is set via `AEGIS_GATE_PASSWORD` in `/opt/aegis/.env` on the server. To change it, update the env var and run `docker compose up -d` in `/opt/aegis/`.

Documentation uses Caddy's built-in basic auth (username: `aegis`, same password). The bcrypt hash is in the Caddyfile.

!!! note
    When `AEGIS_GATE_PASSWORD` is not set, auth is disabled entirely. This is the default for local development.

## Sharing scenarios

Click the share icon (:material-share-variant:) in the toolbar to copy a URL to your clipboard. The URL encodes your current settings (antenna position, body, frequency, physics corrections, RT config) as a base64 fragment.

Recipients open the link, enter the password, and see your exact setup. They need to click the scene to trigger a computation, since results are not stored in the URL.

The fragment never reaches the server. It stays in the browser.

## Multi-user

Multiple users can compute simultaneously without interference. The server is stateless per request: all session state lives in the browser (Zustand stores). Shared read-only data (body meshes, voxel geometry, config) is loaded once at startup.

Body selection, compliance results, and compute timings are all scoped to each user's request. The old `/api/body/switch` mutation endpoint is gone.

One limitation: the voxel environment (loaded location) is shared across all users. If someone loads a different location, everyone sees the new one.

## Server files

All deployment files live in `/opt/aegis/` on the Hetzner server:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Caddy + Flask containers, volumes, health checks |
| `Caddyfile` | Reverse proxy routes, HTTPS, docs basic auth |
| `.env` | Passwords, API keys (not in version control) |

The Docker image (`ghcr.io/rwydaegh/aegis:latest`) contains the Python package, body meshes, React build, and docs. Pipeline cache (voxel data) persists in a Docker volume across deploys.

## Deploying updates

The CI/CD pipeline (`.github/workflows/deploy.yml`) runs on every push to master:

1. Lint and test (reuses `ci.yml`)
2. Build the React frontend and copy to `static/`
3. Build mkdocs
4. Build and push Docker image to ghcr.io
5. SSH into Hetzner, pull the new image, restart

Manual deploy (when CI is broken or for the first time):

```bash
# Build locally
cd aegis-web && npm ci && npm run build && node scripts/copy-to-flask.mjs && cd ..
mkdir -p site && python -m mkdocs build
sudo docker build -t ghcr.io/rwydaegh/aegis:latest .

# Transfer to server
sudo docker save ghcr.io/rwydaegh/aegis:latest \
  | ssh -i ~/.ssh/aegis-deploy root@178.104.104.62 \
    'docker load && cd /opt/aegis && docker compose up -d'
```

## Environment variables

Set in `/opt/aegis/.env` on the server:

| Variable | Required | Purpose |
|----------|----------|---------|
| `AEGIS_GATE_PASSWORD` | Yes | Shared password for the login gate |
| `FLASK_SECRET_KEY` | Yes | Signs session cookies. Generate once, keep stable across deploys |
| `AEGIS_DATA_DIR` | Yes | Path to mesh data inside the container (`/app/data`) |
| `GOOGLE_API_KEY` | No | Geocoded location loading (pipeline not available in Docker) |

## Rollback

Every image is tagged by commit SHA. To roll back:

```bash
ssh -i ~/.ssh/aegis-deploy root@178.104.104.62 \
  'cd /opt/aegis && IMAGE_TAG=abc1234 docker compose up -d'
```

## DNS

Two A records on waves-ugent.be (managed via EasyHost):

| Record | Value |
|--------|-------|
| `aegis` | `178.104.104.62` |
| `docs.aegis` | `178.104.104.62` |

Other subdomains (`goliat`, `docs.goliat`, `monitoring.goliat`) belong to an unrelated project and must not be modified.

## Troubleshooting

Check container status:

```bash
ssh -i ~/.ssh/aegis-deploy root@178.104.104.62 \
  'cd /opt/aegis && docker compose ps && docker logs aegis-flask-1 --tail 20'
```

Common issues:

- `itis_v5.db not found` on compute: `AEGIS_DATA_DIR` is not set in `.env`. Add `AEGIS_DATA_DIR=/app/data` and run `docker compose up -d` (not `restart`, which does not re-read `.env`).
- Caddy restarting in a loop: check the Caddyfile for syntax errors. Bcrypt hashes contain `$` signs that docker-compose may try to interpolate.
- HTTPS certificate failure: verify DNS propagation with `dig aegis.waves-ugent.be`. Caddy retries automatically, but Let's Encrypt rate-limits failed attempts.

## See also

- [Interactive viewer](viewer.md) for UI controls and configuration
- [Development machine](../developer_guide/cloud_machine.md) for TensorDock dev setup with GPU

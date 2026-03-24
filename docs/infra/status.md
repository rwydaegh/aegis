# Infrastructure status

**Date**: 2026-03-24
**Live at**: https://aegis.waves-ugent.be

## What was built

### Production deployment
- **Server**: Hetzner CX22 (2 vCPU, 4 GB RAM, 40 GB disk) at 178.104.104.62, ~4.35 EUR/month
- **Stack**: Docker Compose with two containers: Caddy (reverse proxy, auto-HTTPS) + Gunicorn/Flask
- **Domains**: `aegis.waves-ugent.be` (viewer), `docs.aegis.waves-ugent.be` (docs, basic auth)
- **HTTPS**: Auto-provisioned by Caddy via Let's Encrypt, zero config

### Multi-user isolation
Fixed 6 shared mutable state bugs that caused interference between concurrent users:
1. Body meshes preloaded into read-only dict, `/api/body/switch` removed
2. Compliance results returned inline in compute response, global cache removed
3. Pipeline process scoped by session ID, global mutex prevents concurrent pipelines
4. Threading locks on curvature cache and voxel scene cache
5. Timings returned from `compute_with_timings()` instead of module-level global

### Password gate
- Shared password protects all API endpoints (2-hour session cookie)
- Styled login overlay, session countdown timer in toolbar
- Password: stored in `.env` on the server, emailed to authorized users
- Docs protected separately via Caddy basic auth (username: `aegis`, same password)

### Shareable URLs
- Share button in toolbar encodes ~35 frontend state fields as base64 JSON in URL fragment
- Recipients open the link, authenticate, and see the same scenario setup
- Fragment is never sent to the server (pure client-side)

### CI/CD pipeline
- `.github/workflows/deploy.yml`: builds React, builds docs, builds Docker image, pushes to ghcr.io, SSHes to Hetzner
- Currently blocked by pre-existing test failure in `test_batch_runner.py` (unrelated to infra work)
- First deploy was done manually (docker save/load over SSH)

## What went wrong during implementation

### Merge conflicts with parallel work
The `wt/infra` worktree diverged from master where another branch refactored the scene store (`rtConfig` consolidation). Required manual conflict resolution in `useDosimetry.ts` and fixes in `shareLink.ts`/`useConfig.ts` to use the new `rtConfig` object pattern.

### LoginGate ordering bug
The `LoginGate` component was placed inside `App.tsx` wrapping only `AppShell`, but `useConfig()` ran before the gate. A 401 from `/api/config` was caught by the error handler ("Connection failed") instead of showing the login form. Fixed by splitting into `LoginGate` (outermost, probes auth independently) and `AppInner` (runs useConfig only after auth succeeds).

### Dockerfile issues
1. `hatch-vcs` needs a git repo for versioning. Fixed with `SETUPTOOLS_SCM_PRETEND_VERSION` build arg.
2. Missing `README.md` in the COPY step (required by pyproject.toml metadata).
3. Bcrypt password hashes contain `$` which docker-compose interprets as env var substitution. Worked around by hardcoding the hash in the Caddyfile directly.

### CI test failure blocking auto-deploy
`test_batch_runner.py::test_sweep_skips_infeasible_levels` fails with `KeyError: 'A_ab'`. Pre-existing issue on master, not caused by infra changes. Blocks the deploy job since it depends on CI passing.

## What still needs to be done

### Blocking (needed for smooth operation)

1. **Fix `test_batch_runner` test failure** so CI passes and auto-deploy works. The `sweep_levels` method uses `locals()[p]` which may be fragile. Either fix the test or the method.

2. **Add `write:packages` scope to GitHub token** so the deploy workflow can push Docker images to ghcr.io. Currently the token lacks this scope, so the first deploy was manual.

3. **Compute 500 error on production** -- placing an antenna triggers a 500 from `/api/compute`. Needs debugging (check Flask logs on the server).

### Important (should do soon)

4. **Location pipeline in Docker** -- the Docker image has no Node.js, so `/api/location/load` does not work. Options: (a) install Node.js in the image, (b) pre-cache locations from the dev machine and copy to the `pipeline_cache` volume, (c) add a sidecar container with Node.js.

5. **Notification toast positioning** -- error messages appear in the bottom-left corner behind the sidebar. Should be center-right or top-center.

6. **Commit the Dockerfile fixes to master** -- `SETUPTOOLS_SCM_PRETEND_VERSION` and `README.md` changes are committed but the Caddyfile bcrypt workaround should be documented.

### Nice to have (future)

7. **Serverless GPU** -- architecture supports it, not implemented. Modal or RunPod Serverless for Sionna RT and coherent MIMO.

8. **Per-session voxel data** -- currently everyone sees the same loaded location. Need session-scoped voxel storage for different users to load different locations.

9. **Data-driven share links** -- store computed results (SAB arrays) in SQLite so recipients see results without recomputing.

10. **Monitoring** -- no Sentry, no uptime monitoring, no Grafana. Fine for now with a handful of users.

11. **Build real mkdocs docs** -- currently a placeholder HTML file. The `mkdocs build` step in CI should produce the real docs once the docs workflow is properly integrated into the deploy pipeline.

## Server access

```bash
# SSH into the server
ssh -i ~/.ssh/aegis-deploy root@178.104.104.62

# View logs
docker logs aegis-flask-1 -f
docker logs aegis-caddy-1 -f

# Restart
cd /opt/aegis && docker compose restart

# Manual deploy (if CI is broken)
# On dev machine:
sudo docker build -t ghcr.io/rwydaegh/aegis:latest /home/user/aegis
sudo docker save ghcr.io/rwydaegh/aegis:latest | ssh -i ~/.ssh/aegis-deploy root@178.104.104.62 'docker load && cd /opt/aegis && docker compose up -d'
```

## Credentials

- **Gate password**: stored in `/opt/aegis/.env` on the server
- **Flask secret key**: stored in `/opt/aegis/.env`
- **SSH deploy key**: `~/.ssh/aegis-deploy` (on dev machine)
- **DNS**: A records on EasyHost for `aegis.waves-ugent.be` and `docs.aegis.waves-ugent.be`

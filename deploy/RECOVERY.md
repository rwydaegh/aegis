# AEGIS prod disaster recovery

The Hetzner box (`aegis.waves-ugent.be`) is rebuildable from automation. This is
the runbook and the reasoning behind it. Scripts: `backup-prod.sh`,
`provision-prod.sh`, shared config in `_config.sh`.

## What reconstructs from where

Most of prod is already disposable, because the app image carries it:

| State | Source of truth | Recovery |
| --- | --- | --- |
| App code | `aegis` git repo | rebuilt by `deploy.yml` |
| Baked data: phantom STLs, `itis_v5.db`, antenna `index.sqlite.gz`, channel presets, basestation parquets | `aegis` git repo (`data/`, 769 tracked files), `COPY data/ data/` into the image | rebuilt by `deploy.yml` |
| `docker-compose.yml`, `Caddyfile` | `aegis` git repo | `provision-prod.sh` (and `deploy.yml`) |
| TLS certificates | Let's Encrypt | auto-reissued on first boot once DNS points here |

Only these live **nowhere but the box** and need explicit backup:

| State | Backed up to | Criticality |
| --- | --- | --- |
| `app.env` (all secrets) | `stateDevMachine/secrets/aegis-prod/app.env` (git + gdrive, plaintext, private) | **critical** - loss is unrecoverable; FLASK_SECRET_KEY loss logs everyone out |
| SMPL-X models (411 MB) | dev box `~/.aegis` (gdrive-synced) + `gdrive:aegis-prod-backup/models` | critical - Exposure Lab parametric body breaks without them |
| umami analytics history (65 MB pg) | `gdrive:aegis-prod-backup/umami/umami-*.sql.gz` | nice-to-have |
| `msi_raw` vendor antenna zips (869 MB) + `basestations` lib | `gdrive:aegis-prod-backup/{data,basestations}` | build inputs only, not mounted into the container at runtime |

## Backups (already automated)

`backup-prod.sh` captures the non-git state off-box. Run nightly via cron for the
critical/cheap items, and `--full` weekly (or after they change) for the large
static blobs:

```cron
30 3 * * *  cd $HOME/aegis && ./deploy/backup-prod.sh        >> $HOME/.cache/aegis-backup.log 2>&1
30 4 * * 0  cd $HOME/aegis && ./deploy/backup-prod.sh --full >> $HOME/.cache/aegis-backup.log 2>&1
```

`app.env` is committed + pushed to the private `stateDevMachine` repo immediately
on each run; the gdrive blobs are versioned (umami dumps pruned after 90 days).

## Recovery (one command)

After a total loss:

1. **Order a fresh Ubuntu box** (Hetzner CX23 or larger) with the `aegis-deploy`
   SSH public key selected, so root login works on first boot. Note its IP.

2. **Run the provisioner** from a machine that has `~/.ssh/aegis-deploy`, the
   `stateDevMachine` checkout, and the `gdrive:` rclone remote (i.e. the dev box,
   or any box restored from the `stateDevMachine` + gdrive backups):

   ```bash
   cd ~/aegis
   ./deploy/provision-prod.sh <NEW_IP>
   ```

   This installs Docker, restores `app.env`, compose, Caddyfile, SMPL-X, the build
   inputs, pulls the image from ghcr.io, brings the stack up, and restores umami
   history. It is idempotent - safe to re-run.

3. **Repoint DNS** at the registrar for `waves-ugent.be`: set the `aegis` and
   `docs.aegis` A records (plus any other subdomains in the `Caddyfile`) to
   `<NEW_IP>`. Caddy issues TLS automatically once DNS resolves. **This is the
   only unavoidable manual step** (no DNS API wired up - if you want it scripted,
   tell me the provider).

4. **Update `HETZNER_HOST`** repo variable to `<NEW_IP>` (GitHub web UI; the local
   PAT lacks Actions scope) so future master pushes auto-deploy to the new box.

5. **Verify:** `curl -sI https://aegis.waves-ugent.be/api/health` once DNS
   propagates.

## Bootstrapping the bootstrapper

The recovery depends on two durable, off-Hetzner stores:

- `stateDevMachine` - private GitHub repo, also rclone-synced to `gdrive:devbox`.
  Holds `~/.ssh/aegis-deploy` and `secrets/aegis-prod/app.env`.
- `gdrive:aegis-prod-backup` - SMPL-X, build inputs, umami dumps.

If the dev box is also gone, restore `stateDevMachine` first (`git clone` +
`rclone copy gdrive:devbox/.aegis ~/.aegis` for SMPL-X), then follow Recovery.

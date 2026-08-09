#!/usr/bin/env bash
# Capture the non-git AEGIS prod state to durable, off-box storage so the
# server can be rebuilt after a total loss. Safe to run from cron.
#
# What lives ONLY on the Hetzner box (everything else rebuilds from the aegis
# git repo + the image on ghcr.io via deploy.yml):
#
#   app.env              -> $SECRETS_DIR/app.env          (plaintext, git + gdrive)
#   umami postgres       -> $GDRIVE_REMOTE/umami/*.sql.gz (rolling, pruned)
#   SMPL-X models        -> $GDRIVE_REMOTE/models/        (mirror of dev copy)   [--full]
#   msi_raw + basestations build inputs -> $GDRIVE_REMOTE/{data,basestations}    [--full]
#
# Default run = the fast, critical items (app.env + umami): cheap enough for a
# nightly cron. Pass --full to also mirror the large static blobs (run weekly
# or after they change; they are ~1.4 GB and rarely move).
#
# Usage:
#   deploy/backup-prod.sh           # app.env + umami dump
#   deploy/backup-prod.sh --full    # also mirror SMPL-X, msi_raw, basestations
set -euo pipefail
cd "$(dirname "$0")"
source ./_config.sh

FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

command -v rclone >/dev/null || die "rclone not found"
rclone listremotes 2>/dev/null | grep -q "^${GDRIVE_REMOTE%%:*}:" || die "rclone remote '${GDRIVE_REMOTE%%:*}' not configured"

# 1. app.env (the one irreplaceable thing: gate password, FLASK_SECRET_KEY,
#    CloudRF/Cesium/Modal/Sentry/umami creds). Tiny -> git-tracked + gdrive.
log "Backing up app.env -> $SECRETS_DIR"
mkdir -p "$SECRETS_DIR"
scp "${SSH_OPTS[@]}" "$PROD_USER@$PROD_HOST:$APP_DIR/app.env" "$SECRETS_DIR/app.env"
chmod 600 "$SECRETS_DIR/app.env"
if git -C "$HOME/stateDevMachine" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$HOME/stateDevMachine" add "secrets/aegis-prod/app.env" 2>/dev/null || true
  if ! git -C "$HOME/stateDevMachine" diff --cached --quiet 2>/dev/null; then
    git -C "$HOME/stateDevMachine" commit -q -m "backup: aegis prod app.env $(date '+%Y-%m-%d %H:%M')" || true
    git -C "$HOME/stateDevMachine" push -q 2>/dev/null || log "  (push deferred to autopush)"
  fi
fi

# 2. umami analytics postgres -> dated, gzipped dump on gdrive, pruned by age.
log "Dumping umami postgres"
stamp="$(date '+%Y-%m-%d')"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
ssh_prod "docker exec $UMAMI_DB_CONTAINER pg_dump -U umami umami | gzip -c" > "$tmp"
size="$(du -h "$tmp" | cut -f1)"
log "  dump is $size, uploading"
rclone copyto "$tmp" "$GDRIVE_REMOTE/umami/umami-$stamp.sql.gz"
rclone copyto "$tmp" "$GDRIVE_REMOTE/umami/umami-latest.sql.gz"
rclone delete "$GDRIVE_REMOTE/umami" --min-age "${UMAMI_RETAIN_DAYS}d" --include "umami-2*.sql.gz" 2>/dev/null || true

if [[ "$FULL" == "1" ]]; then
  # 3. SMPL-X models (source of truth = dev box, also gdrive-synced under
  #    ~/.aegis; mirror into the self-contained prod backup too).
  if [[ -d "$SMPLX_SRC" ]]; then
    log "Mirroring SMPL-X models -> $GDRIVE_REMOTE/models/smplx"
    rclone sync "$SMPLX_SRC" "$GDRIVE_REMOTE/models/smplx" --transfers 4
  else
    log "  SMPL-X source $SMPLX_SRC missing, skipping"
  fi

  # 4. Large license-gated build inputs that live only on prod: stream them
  #    straight from the box to gdrive (no local temp) via rclone's on-the-fly
  #    sftp backend. size-only so re-runs upload nothing when unchanged.
  sftp=":sftp,host=$PROD_HOST,user=$PROD_USER,key_file=$SSH_KEY,known_hosts_file=$HOME/.ssh/known_hosts"
  log "Mirroring msi_raw antenna zips -> $GDRIVE_REMOTE/data"
  rclone sync "$sftp:$APP_DIR/data" "$GDRIVE_REMOTE/data" --size-only --transfers 4 || log "  (msi_raw mirror failed, non-critical)"
  log "Mirroring basestations lib -> $GDRIVE_REMOTE/basestations"
  rclone sync "$sftp:$APP_DIR/basestations" "$GDRIVE_REMOTE/basestations" --size-only --transfers 4 || log "  (basestations mirror failed, non-critical)"
fi

log "Backup complete."

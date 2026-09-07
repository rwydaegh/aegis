#!/usr/bin/env bash
# Rebuild AEGIS prod on a FRESH Ubuntu box from the durable backups, end to end.
#
# Prerequisite: a new box exists and is reachable via SSH as root with $SSH_KEY.
# When ordering the Hetzner box, select the 'aegis-deploy' public key so the key
# is already in root's authorized_keys on first boot. Nothing else is assumed.
#
# What this restores, in order:
#   1. Docker engine + compose plugin (get.docker.com)
#   2. app.env            from $SECRETS_DIR        (secrets)
#   3. compose + Caddyfile from $AEGIS_REPO        (or current dir)
#   4. SMPL-X models      from $SMPLX_SRC or gdrive (runtime-critical)
#   5. msi_raw + basestations from gdrive          (build inputs, best-effort)
#   6. docker login ghcr.io + compose pull + up
#   7. umami history      from gdrive latest dump  (best-effort)
#
# After it finishes you must repoint DNS (see the printed checklist).
#
# Usage:
#   deploy/provision-prod.sh <NEW_IP>
set -euo pipefail
cd "$(dirname "$0")"
source ./_config.sh

NEW_IP="${1:?usage: deploy/provision-prod.sh <NEW_IP>}"
PROD_HOST="$NEW_IP"   # retarget every ssh_prod/scp at the new box

[[ -f "$SECRETS_DIR/app.env" ]] || die "no app.env at $SECRETS_DIR (run backup-prod.sh first, or restore stateDevMachine)"

# Resolve the compose + Caddyfile source (prefer the checked-out repo).
compose_src="$AEGIS_REPO/docker-compose.yml"; caddy_src="$AEGIS_REPO/Caddyfile"
[[ -f "$compose_src" ]] || { compose_src="./../docker-compose.yml"; caddy_src="./../Caddyfile"; }
[[ -f "$compose_src" ]] || die "docker-compose.yml not found (set AEGIS_REPO)"
access_src="$(dirname "$compose_src")/access.env"
[[ -f "$access_src" ]] || die "access.env not found beside docker-compose.yml"

log "Waiting for SSH on $NEW_IP ..."
for _ in $(seq 1 30); do ssh_prod true 2>/dev/null && break; sleep 5; done
ssh_prod true 2>/dev/null || die "cannot SSH to $NEW_IP as $PROD_USER"

log "1/7 Installing Docker"
ssh_prod "command -v docker >/dev/null || (curl -fsSL https://get.docker.com | sh)"
ssh_prod "mkdir -p $APP_DIR/models/smplx $APP_DIR/data $APP_DIR/basestations"

log "2/7 Restoring app.env"
scp "${SSH_OPTS[@]}" "$SECRETS_DIR/app.env" "$PROD_USER@$NEW_IP:$APP_DIR/app.env"
ssh_prod "chmod 600 $APP_DIR/app.env"

log "3/7 Restoring docker-compose.yml + Caddyfile"
scp "${SSH_OPTS[@]}" "$compose_src" "$caddy_src" "$access_src" "$PROD_USER@$NEW_IP:$APP_DIR/"

log "4/7 Restoring SMPL-X models"
if [[ -d "$SMPLX_SRC" ]] && ls "$SMPLX_SRC"/*.npz >/dev/null 2>&1; then
  scp "${SSH_OPTS[@]}" "$SMPLX_SRC"/*.npz "$PROD_USER@$NEW_IP:$APP_DIR/models/smplx/"
else
  log "  dev copy missing, pulling from $GDRIVE_REMOTE/models/smplx"
  rclone copy "$GDRIVE_REMOTE/models/smplx" ":sftp,host=$NEW_IP,user=$PROD_USER,key_file=$SSH_KEY:$APP_DIR/models/smplx" --transfers 4
fi
ssh_prod "ls -la $APP_DIR/models/smplx/ | tail -4"

log "5/7 Restoring build inputs (best-effort)"
dst=":sftp,host=$NEW_IP,user=$PROD_USER,key_file=$SSH_KEY"
rclone copy "$GDRIVE_REMOTE/data" "$dst:$APP_DIR/data" --size-only --transfers 4 2>/dev/null || log "  (msi_raw restore skipped)"
rclone copy "$GDRIVE_REMOTE/basestations" "$dst:$APP_DIR/basestations" --size-only --transfers 4 2>/dev/null || log "  (basestations restore skipped)"

log "6/7 Pulling image and starting the stack"
gh_token="$(ssh_prod "grep -E '^GITHUB_TOKEN=' $APP_DIR/app.env | cut -d= -f2-")"
[[ -n "$gh_token" ]] || die "GITHUB_TOKEN missing from app.env, cannot pull from ghcr.io"
ssh_prod "echo '$gh_token' | docker login ghcr.io -u rwydaegh --password-stdin >/dev/null"
ssh_prod "cd $APP_DIR && docker compose pull && docker compose up -d"

log "  waiting for flask health"
for _ in $(seq 1 40); do
  st="$(ssh_prod "docker inspect -f '{{.State.Health.Status}}' aegis-flask-1 2>/dev/null" || true)"
  [[ "$st" == "healthy" ]] && { log "  flask healthy"; break; }
  sleep 5
done

log "7/7 Restoring umami history (best-effort)"
if rclone lsf "$GDRIVE_REMOTE/umami/umami-latest.sql.gz" >/dev/null 2>&1; then
  for _ in $(seq 1 20); do
    st="$(ssh_prod "docker inspect -f '{{.State.Health.Status}}' $UMAMI_DB_CONTAINER 2>/dev/null" || true)"
    [[ "$st" == "healthy" ]] && break; sleep 5
  done
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
  rclone copyto "$GDRIVE_REMOTE/umami/umami-latest.sql.gz" "$tmp"
  gunzip -c "$tmp" | ssh_prod "docker exec -i $UMAMI_DB_CONTAINER psql -U umami umami" >/dev/null 2>&1 \
    && log "  umami history restored" || log "  (umami restore failed, starts fresh)"
else
  log "  no umami dump found, analytics start fresh"
fi

cat <<EOF

================ AEGIS prod rebuilt on $NEW_IP ================
Container stack is up. Remaining MANUAL steps (DNS is the only hard blocker):

  1. DNS: point these A records at $NEW_IP at the waves-ugent.be registrar:
       aegis.waves-ugent.be
       docs.aegis.waves-ugent.be   (and any other subdomains in the Caddyfile)
     Caddy auto-issues TLS once DNS resolves to the new box.

  2. GitHub: set repo variable HETZNER_HOST = $NEW_IP (Settings > Secrets and
     variables > Actions > Variables) so future master pushes deploy here.
     (The local PAT lacks Actions scope, so this is web-UI only.)

  3. Verify once DNS propagates:
       curl -sI https://aegis.waves-ugent.be/api/health
==============================================================
EOF

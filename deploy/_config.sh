# Shared, non-secret config for the AEGIS prod backup/recovery scripts.
# Sourced by backup-prod.sh and provision-prod.sh. Every value is overridable
# from the environment, so nothing secret is ever hard-coded here.
#
# This file lives in a private repo but is treated as if it were public: it
# contains only a host IP, paths, and a container name. Secrets are read at
# runtime from $SECRETS_DIR (the gdrive-synced stateDevMachine repo).

PROD_HOST="${PROD_HOST:-178.104.104.62}"   # Hetzner box (see reference_hetzner_deploy memory)
PROD_USER="${PROD_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/aegis-deploy}"
APP_DIR="${APP_DIR:-/opt/aegis}"

# Durable stores, both off the prod box:
#  - SECRETS_DIR: tiny, plaintext, git-tracked + gdrive-synced (app.env)
#  - GDRIVE_REMOTE: large blobs and rolling umami dumps
SECRETS_DIR="${SECRETS_DIR:-$HOME/stateDevMachine/secrets/aegis-prod}"
GDRIVE_REMOTE="${GDRIVE_REMOTE:-gdrive:aegis-prod-backup}"

# SMPL-X models: the dev box copy is the source of truth (itself gdrive-synced
# under ~/.aegis). Recovery re-pushes from here, falling back to GDRIVE_REMOTE.
SMPLX_SRC="${SMPLX_SRC:-$HOME/.aegis/models/smplx}"
AEGIS_REPO="${AEGIS_REPO:-$HOME/aegis}"   # source of docker-compose.yml + Caddyfile

UMAMI_DB_CONTAINER="${UMAMI_DB_CONTAINER:-aegis-umami-db-1}"
UMAMI_RETAIN_DAYS="${UMAMI_RETAIN_DAYS:-90}"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -i "$SSH_KEY")

ssh_prod() { ssh "${SSH_OPTS[@]}" "$PROD_USER@$PROD_HOST" "$@"; }

log() { printf '%s  %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

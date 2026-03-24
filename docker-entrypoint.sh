#!/bin/sh
set -e

# Copy docs to shared volume (Caddy serves them)
if [ -d /app/site ] && [ -d /srv/docs ]; then
    cp -r /app/site/* /srv/docs/ 2>/dev/null || true
fi

exec gunicorn "aegis.viewer.server:create_app_from_env()" \
    --config /app/gunicorn.conf.py \
    --chdir /app

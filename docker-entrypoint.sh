#!/bin/sh
set -e

# Copy docs to shared volume (Caddy serves them)
if [ -d /app/site ] && [ -d /srv/docs ]; then
    find /srv/docs -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    cp -a /app/site/. /srv/docs/
fi

exec gunicorn "aegis.viewer.server:create_app_from_env()" \
    --config /app/gunicorn.conf.py \
    --chdir /app

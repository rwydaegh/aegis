FROM python:3.12-slim

WORKDIR /app

# System deps for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Python deps + install package
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN pip install uv && uv pip install --system ".[viewer]" gunicorn

# Phantom mesh data (STL files + IT'IS database)
COPY data/ data/

# Pre-built React app (built in CI, copied into static/ before docker build)
# Already at src/aegis/viewer/static/ from the build:copy step

# Pre-built docs (built in CI)
COPY site/ site/

# Gunicorn config
COPY gunicorn.conf.py gunicorn.conf.py

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]

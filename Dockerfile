FROM python:3.12-slim

WORKDIR /app

# System deps for health checks, git (for voxelearth clone), and C toolchain (for differt-core Rust build)
RUN apt-get update && apt-get install -y --no-install-recommends curl git build-essential pkg-config && rm -rf /var/lib/apt/lists/*

# Node.js 22 for the voxelearth location pipeline
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Clone and install voxelearth pipeline
RUN git clone --depth 1 https://github.com/voxelearth/nodejs-voxelearth.git /opt/voxelearth \
    && cd /opt/voxelearth && npm install --omit=dev
ENV VOXELEARTH_DIR=/opt/voxelearth

# Python deps + install package
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# hatch-vcs needs git for versioning; use pretend version in Docker builds
ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}
RUN pip install uv && uv pip install --system ".[viewer]" gunicorn

# Phantom mesh data (STL files + IT'IS database) and Sionna XML scenes
COPY data/ data/
ENV SIONNA_SCENES_DIR=/app/data/scenes

# Pre-built React app (built in CI, copied into static/ before docker build)
# Already at src/aegis/viewer/static/ from the build:copy step

# Pre-built docs (built in CI) — CACHE_BUST ensures fresh copy each build
ARG CACHE_BUST
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

# InnoCalc tenant image. Build from the suite root with submodules checked out:
#   git clone --recurse-submodules ... && docker build --build-arg GIT_SHA=$(git rev-parse --short HEAD) -t innocalc:<sha> .
# Runs as any UID (compose supplies user:) with a read-only root; writable /data, /backups, /tmp.

FROM python:3.12-slim AS build
COPY requirements.lock /tmp/requirements.lock
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir -r /tmp/requirements.lock

FROM python:3.12-slim
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="InnoCalc" org.opencontainers.image.revision="${GIT_SHA}"

# Carlito is metric-compatible with Calibri, so sheets paginate as they do on Windows.
RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium tzdata fontconfig \
      fonts-crosextra-carlito fonts-liberation fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# --no-sandbox: Chromium's sandbox cannot start under cap_drop ALL; it only prints InnoCalc's own
# local sheets. /dev/shm is 64 MB in a container, hence --disable-dev-shm-usage.
ENV TZ=Australia/Adelaide \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/venv/bin:$PATH \
    PYTHONPATH=/app/packages \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    ICM_HOST=0.0.0.0 \
    ICM_PORT=8125 \
    ICM_DATA_DIR=/data \
    ICM_BACKUP_DIR=/backups \
    ICM_ROOT=/projects \
    INNOCALC_BROWSER=/usr/bin/chromium \
    INNOCALC_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"

COPY --from=build /venv /venv
WORKDIR /app
COPY suite.toml pyproject.toml ./
COPY packages/ packages/
COPY tooling/ tooling/
COPY calculations/ calculations/
COPY apps/manager/ apps/manager/
RUN chmod -R a+rX /app

VOLUME ["/data", "/backups", "/tmp"]
EXPOSE 8125
# ICM_ALLOWED_HOSTS rejects other Host headers, so the probe sends the site's hostname.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD \
  python -c "import os, urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8125/api/health', headers={'Host': os.environ.get('ICM_HEALTH_HOST', 'localhost')}), timeout=4)"

WORKDIR /app/apps/manager
CMD ["python", "server.py"]

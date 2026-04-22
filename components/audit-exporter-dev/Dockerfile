FROM upr-proxy.dmi-msk.ru/docker/python:3.13-slim AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG CI_COMMIT_REF_SLUG
ARG CI_REGISTRY_USER
ARG CI_REGISTRY_PASSWORD

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

COPY pyproject.toml uv.lock ./

RUN set -eux; \
    pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir uv; \
    \
    case "$CI_COMMIT_REF_SLUG" in \
      dev)     NEXUS_REPO="pypi-dev-group" ;; \
      staging) NEXUS_REPO="pypi-staging-group" ;; \
      main)    NEXUS_REPO="pypi-main-group" ;; \
      *)       NEXUS_REPO="pypi-dev-group" ;; \
    esac; \
    \
    export UV_EXTRA_INDEX_URL="https://${CI_REGISTRY_USER}:${CI_REGISTRY_PASSWORD}@nexus.dmi-msk.ru/repository/${NEXUS_REPO}/simple"; \
    uv sync \
      --no-dev \
      --no-install-project \
      --locked; \
    \
    rm -rf /root/.cache/pip /root/.cache/uv

COPY src/ ./src/


FROM upr-proxy.dmi-msk.ru/docker/migrate/migrate:v4.18.3 AS migrate

WORKDIR /migrations
COPY migrations/ ./


FROM upr-proxy.dmi-msk.ru/docker/clickhouse/clickhouse-server:24-alpine AS clickhouse-client

FROM upr-proxy.dmi-msk.ru/docker/python:3.13-slim AS runtime

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=clickhouse-client /usr/bin/clickhouse /usr/local/bin/clickhouse
RUN ln -s /usr/local/bin/clickhouse /usr/local/bin/clickhouse-client

RUN groupadd -r app && useradd --no-log-init -r -g app app
WORKDIR /app

RUN mkdir -p /app/.cache \
    && chown -R app:app /app/.cache /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src ./src
COPY --from=migrate --chown=app:app /usr/local/bin/migrate /usr/local/bin/migrate
COPY --chown=app:app migrations/ ./migrations/
COPY --chown=app:app scripts/ ./scripts/
COPY pyproject.toml ./

RUN chmod +x ./scripts/*

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/app/.cache \
    PYTHONPATH=/app

CMD ["./scripts/start.sh"]

# 1) Builder: установка зависимостей с помощью uv
FROM python:3.13-slim AS builder

# Устанавливаем минимальные инструменты для сборки и очищаем кеш apt
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG CI_COMMIT_REF_SLUG
ARG CI_REGISTRY_USER
ARG CI_REGISTRY_PASSWORD

# Отключаем генерацию .pyc, включаем буферизацию вывода и подавляем предупреждение pip root
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

# Копируем файлы зависимостей проекта
COPY pyproject.toml ./

# Устанавливаем uv и только prod-зависимости (создаст .venv)
RUN set -eux; \
    pip install --no-cache-dir --index-url=https://mirrors.ustc.edu.cn/pypi/simple/ --upgrade pip; \
    pip install --no-cache-dir --index-url=https://mirrors.ustc.edu.cn/pypi/simple/ uv; \
    \
    case "$CI_COMMIT_REF_SLUG" in \
      dev) \
        NEXUS_REPO="pypi-dev-group" ;; \
      staging) \
        NEXUS_REPO="pypi-staging-group" ;; \
      main) \
        NEXUS_REPO="pypi-main-group" ;; \
      *) \
        NEXUS_REPO="pypi-dev-group" ;; \
    esac; \
    \
    export UV_EXTRA_INDEX_URL="https://${CI_REGISTRY_USER}:${CI_REGISTRY_PASSWORD}@nexus.dmi-msk.ru/repository/${NEXUS_REPO}/simple"; \
    uv lock; \
    uv sync \
      --no-dev \
      --no-install-project \
      --locked; \
    \
    rm -rf /root/.cache/pip /root/.cache/uv

# Копируем исходный код
COPY src/ ./src/


# 2) Runtime: минимальный образ для запуска
FROM python:3.13-slim AS runtime

# Устанавливаем curl для healthcheck и очищаем кеш apt
USER root
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя и директорию приложения
RUN groupadd -r app && useradd --no-log-init -r -g app app
WORKDIR /app

# Подготавливаем кеш и права
RUN mkdir -p /app/.cache \
    && chown -R app:app /app/.cache /app

USER root

# Копируем виртуальное окружение и код из builder-а
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src ./src
COPY pyproject.toml ./
COPY alembic.ini ./
COPY start.sh start.broker.sh ./
RUN chmod +x ./start.sh ./start.broker.sh

# Добавляем venv/bin в PATH и оставляем основные переменные
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/app/.cache \
    PYTHONPATH=/app/src

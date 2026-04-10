# 1) Builder: установка зависимостей с помощью uv
FROM python:3.13-slim AS builder

# Устанавливаем минимальные инструменты для сборки и очищаем кеш apt
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Отключаем генерацию .pyc, включаем буферизацию вывода и подавляем предупреждение pip root
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

# Копируем файлы зависимостей проекта
COPY pyproject.toml uv.lock ./

# Устанавливаем uv и только prod-зависимости (создаст .venv)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv \
    && uv sync --no-dev --no-install-project \
    && rm -rf /root/.cache/pip /root/.cache/uv

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

# Добавляем venv/bin в PATH и оставляем основные переменные
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/app/.cache

# Точка входа: запускаем приложение через venv Python
CMD ["python", "-m", "src"]

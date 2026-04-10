# audit-exporter

Сервис забирает записи из таблиц `audit_outbox` нескольких PostgreSQL-баз и складывает их батчами в ClickHouse.
Дедупликация на стороне ClickHouse по токену `(source_name, outbox_id)`, поэтому повторная отправка безопасна.
После записи строки помечаются как обработанные (`processed = true`).

## Источники

Определены в `SourceName` (`src/core/config.py`): **graph**, **enterprise**, **trip**.
Каждый источник конфигурируется отдельным набором переменных окружения с префиксом `{NAME}__POSTGRES_*`.

## Запуск

```bash
make sync
cp .example.env .env
# заполнить .env
make start
```

Docker:

```bash
docker build -t audit-exporter .
docker run --env-file .env -p 8000:8000 audit-exporter
```

## Переменные окружения

| Переменная | Умолчание | Назначение |
|---|---|---|
| `{SOURCE}__POSTGRES_HOST` | — | Хост PostgreSQL |
| `{SOURCE}__POSTGRES_PORT` | `5432` | Порт |
| `{SOURCE}__POSTGRES_DATABASE` | — | БД |
| `{SOURCE}__POSTGRES_USER` | — | Пользователь |
| `{SOURCE}__POSTGRES_PASSWORD` | — | Пароль |
| `CLICKHOUSE_HOST` | — | Хост ClickHouse |
| `CLICKHOUSE_PORT` | `8443` | Порт (HTTPS) |
| `CLICKHOUSE_DATABASE` | — | БД |
| `CLICKHOUSE_USER` | — | Пользователь |
| `CLICKHOUSE_PASSWORD` | — | Пароль |
| `CLICKHOUSE_SECURE` | `true` | TLS |
| `DEPENDENCY_CONNECT_TIMEOUT_SECONDS` | `5` | Таймаут проб при старте |
| `SOURCE_POLL_BATCH_SIZE` | `500` | Размер батча |
| `SOURCE_POLL_INTERVAL_SECONDS` | `10` | Интервал опроса |

## API

- `GET /healthz` — liveness, всегда `200`
- `GET /readyz` — readiness, `200` / `503` с диагностикой зависимостей

## Make-команды

```
make sync              установка зависимостей
make start             dev-сервер (uvicorn --reload)
make lint              ruff check
make format            ruff format + fix
make check-types       mypy
make check-precommit   pre-commit на всех файлах
```

## Структура

```
src/
├── main.py                  ASGI entrypoint
├── app/
│   ├── __init__.py          FastAPI factory + lifespan
│   └── routes/health.py     /healthz, /readyz
├── core/
│   ├── config.py            Pydantic Settings
│   ├── logging.py           Loguru + stdlib interception
│   ├── orchestrator.py      Polling loop
│   ├── pipeline.py          poll → write → ack
│   └── state.py             Runtime state
├── clickhouse/client.py     ClickHouse batch writer
└── db/source_connections.py PostgreSQL reader + ack
```

# Analytics Service

Сервис аналитики является точкой входа для фронтенда к данным в ClickHouse и одновременно
поднимает ETL-процесс, который забирает выгрузки из MinIO и загружает их в аналитические
таблицы. Один процесс — FastAPI — предоставляет HTTP-интерфейс, второй — FastStream
consumer — слушает очередь RabbitMQ и синхронно подгружает события в ClickHouse.

## Возможности

- HTTP API для фронтенда поверх ClickHouse (FastAPI + UJSON ответа).
- Фоновый обработчик `minio-events`, построенный на FastStream, который получает события
  MinIO из RabbitMQ и загружает parquet-файлы в ClickHouse.
- Контроль идемпотентности загрузки через таблицу `s3_file` — повторно один и тот же
  объект не будет обработан.
- Обертки над ClickHouse (async client + session), MinIO/S3 и инфраструктурные
  инструменты (migrations, Makefile, docker-compose).

## Архитектура и поток данных

1. Dump‑service складывает parquet-файлы в бакет MinIO `mybucket`.
2. MinIO рассылает уведомления об изменениях бакета в обмен `minio.events` RabbitMQ.
3. FastStream-приложение (отдельный процесс, поднимается вместе с API) слушает очередь
   `minio-events` и по каждому событию обращается к MinIO за объектом.
4. Контроллер `EkiperEventsController` валидирует, что файл ещё не был загружен и
   прокидывает parquet в ClickHouse через репозитории `EkiperEventsRepository`.
5. Frontend ходит в FastAPI, который читает агрегированные данные из тех же таблиц
   ClickHouse (эндпоинты находятся в `src/api/rest`).

## Требования

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) для управления зависимостями
- Docker + Docker Compose (MinIO, RabbitMQ, ClickHouse)
- `golang-migrate` (можно поставить через `make install-migrate`)

## Конфигурация

Все настройки лежат в `.env`. Пример значений приведён в репозитории.

| Переменная | Назначение |
| --- | --- |
| `HOST`, `PORT`, `MODE` | Адрес и режим запуска FastAPI (`local`, `dev`, `production`). |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT_URL`, `S3_REGION_NAME` | Параметры доступа к MinIO/S3. |
| `RABBIT_USER`, `RABBIT_PASSWORD`, `RABBIT_HOST`, `RABBIT_PORT` | Подключение FastStream к RabbitMQ. |
| `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USERNAME`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE` | Подключение к ClickHouse для API и репозиториев. |
| `CLICKHOUSE_MIGRATION_PORT` | Нативный порт ClickHouse для миграций (`9005` из compose). |

## Быстрый старт

1. Скопируйте `.env` (или создайте на основе примера) и убедитесь, что значения совпадают с
   портами из `docker-compose.yaml`.
2. Поднимите инфраструктуру:
   ```bash
   docker compose up -d clickhouse rabbitmq rabbitmq-init minio minio-setup
   ```
   Скрипты из `setup/` автоматически создадут бакет, обмен/очередь и подпишут события.
3. Установите Python-зависимости: `make sync` (вызовет `uv sync`).
4. Примените миграции ClickHouse: `make migrate`.
5. Запустите сервис: `make start` (или `uv run -m src`). Команда стартует FastAPI и
   вспомогательный процесс FastStream.

После запуска API доступен на `http://localhost:8000/api/...`, а MinIO на `http://localhost:9000`.

## Работа с миграциями

- Создать новую миграцию: `make migrate-create name=add_events_table`
- Применить все миграции: `make migrate`
- Откатить последнюю миграцию: `make rollback`
- Посмотреть версию: `make migrate-version`

Файлы миграций лежат в `src/clickhouse_migrations/` и регистрируют таблицы `ekiper_events` и
`s3_file`.

## Набор полезных команд

| Команда | Назначение |
| --- | --- |
| `make sync` | Установка зависимостей через uv. |
| `make start` | Локальный запуск FastAPI + FastStream. |
| `make lint` / `make format` | Проверка кода и автоформатирование (ruff). |
| `make check-types` | mypy поверх `src`. |
| `make setup-precommit` | Установка pre-commit хуков. |

## Структура

```
src/
 ├─ api/                # HTTP и брокерные роутеры
 ├─ app/                # Бизнес-слой: контроллеры, модели, репозитории
 ├─ background/         # Инициализация фоновых процессов (FastStream consumer)
 ├─ clickhouse_migrations/  # SQL-миграции
 ├─ core/               # Конфиг, клиенты, обёртки и инфраструктурные слои
 └─ ...
setup/                 # Скрипты для подготовки MinIO и RabbitMQ
```

## Дополнительные заметки

- Uvicorn стартует в режиме `reload` только при `MODE=local`.
- FastStream процесс держится в фоне и корректно завершается при остановке сервиса.
- Для отладки событий MinIO можно зайти в консоль `http://localhost:9001` (логин/пароль
  задаются через compose).

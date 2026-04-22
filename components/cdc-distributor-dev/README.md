# CDC Distributor

Сервис дистрибуции CDC-событий на бортовые системы. Читает изменения из RabbitMQ Streams (Debezium), агрегирует по таблицам и публикует JSON-агрегаты в AMQP-очереди для каждого борта.

## Как это работает

```
Debezium (WAL) ──► RabbitMQ Streams ──► CDC Distributor ──► AMQP очереди бортов
                   cdc-graph-service        агрегация         server.bort_1.graph.src
                   cdc-enterprise-service   last-write-wins   server.bort_1.enterprise.src
                   cdc-auth-service                           server.bort_2.graph.src
                   cdc-trip-service                           ...
```

### Ключевые принципы

- **Per-bort consumer.** Для каждого (борт x сервис) создаётся отдельный stream consumer со своим offset. Борт 1 и борт 2 читают один и тот же стрим независимо — если борт 2 отстал, это не влияет на борт 1.

- **At-least-once delivery.** Offset сохраняется только после подтверждения брокером (publisher confirm). Если публикация упала — offset не продвигается, при рестарте батч будет перечитан.

- **Идемпотентный формат.** Агрегатор схлопывает события по ID (last-write-wins). Повторное применение одного агрегата на борту даёт тот же результат.

- **Durable очереди.** Очереди бортов объявляются при старте как durable. Если борт оффлайн — сообщения копятся в очереди и доставляются при подключении.

## Архитектура

```
__main__.py
│
├── AMQPConnectionManager    # Одно AMQP-соединение (connect_robust), пул каналов
├── BortOffsetManager        # Per-bort offset + seq_id в PostgreSQL (stream_name, bort_id)
├── AMQPPublisher            # Публикация с retry + exponential backoff
│
└── StreamAppManager         # 4 x N consumers (4 сервиса x N бортов)
    │
    └── StreamApp (graph:bort_1)
    │   └── handler ──► FanOutOrchestrator
    │                    ├── MultiTableAggregator  (last-write-wins по таблицам)
    │                    ├── AMQPPublisher.publish()
    │                    └── BortOffsetManager.save_offset()
    │
    └── StreamApp (graph:bort_2)
    │   └── ...
    │
    └── StreamApp (enterprise:bort_1)
        └── ...
```

### Поток данных

1. **Чтение.** `StreamApp` читает CDC-события из RabbitMQ Stream через rstream.
2. **Буферизация.** События копятся в буфере до `batch_size` или `timeout`.
3. **Агрегация.** `MultiTableAggregator` группирует события по таблицам, схлопывает по ID (last-write-wins).
4. **Сериализация.** `FanOutOrchestrator` собирает `FanOutPayload` (агрегат + seq_id + offset range) и сериализует через `msgspec.json.encode()`.
5. **Публикация.** `AMQPPublisher` отправляет в очередь борта с publisher confirm. При ошибке — retry с backoff.
6. **Offset + seq_id.** После успешной публикации `BortOffsetManager` сохраняет offset и seq_id в PostgreSQL. При рестарте consumer начнёт с сохранённого offset, seq_id продолжит с последнего значения.

### Формат сообщения

```json
{
  "seq_id": 42,
  "low_offset": 1000,
  "up_offset": 1050,
  "tables": {
    "vehicles": {
      "upserts": [
        {"id": 1, "name": "КамАЗ", "status": "active"},
        {"id": 5, "name": "БелАЗ", "status": "idle"}
      ],
      "deletes": [
        {"id": 3}
      ]
    },
    "drivers": {
      "upserts": [
        {"id": 10, "name": "Иванов", "vehicle_id": 1}
      ],
      "deletes": []
    }
  }
}
```

- `seq_id` — порядковый номер агрегата (монотонно растёт, персистится в БД)
- `low_offset` / `up_offset` — диапазон offset-ов стрима, схлопнутых в этот агрегат
- `tables` — upserts/deletes по таблицам (полные записи, не дельты)

## Конфигурация

Через переменные окружения (`.env` файл). См. [.env.example](.env.example).

### Обязательные

| Переменная | Описание |
|---|---|
| `RABBIT_HOST`, `RABBIT_PORT` | RabbitMQ Streams (протокол stream, обычно 5552) |
| `RABBIT_USER`, `RABBIT_PASSWORD` | Авторизация для stream consumer |
| `RABBIT_VHOST` | Virtual host RabbitMQ (по умолчанию `/`) |
| `RABBIT_AMQP_HOST`, `RABBIT_AMQP_PORT` | RabbitMQ AMQP (протокол 0.9.1, обычно 5672) |
| `RABBIT_AMQP_USER`, `RABBIT_AMQP_PASSWORD` | Авторизация AMQP |
| `BORT_IDS` | Список ID бортов через запятую: `1,2,3` |
| `DISTRIBUTOR__POSTGRES_*` | БД для хранения per-bort offset и seq_id (`HOST`, `PORT`, `USER`, `PASSWORD`, `DATABASE`) |

### Retry (опционально)

| Переменная | Default | Описание |
|---|---|---|
| `RETRY_MAX_RETRIES` | 5 | Макс. попыток подключения к стриму |
| `RETRY_INITIAL_DELAY` | 1.0 | Начальная задержка (сек) |
| `RETRY_MAX_DELAY` | 60.0 | Максимальная задержка (сек) |
| `RETRY_EXPONENTIAL_BASE` | 2.0 | База экспоненциального backoff |
| `RETRY_JITTER` | true | Добавлять случайный jitter |

## Запуск

```bash
# Установка зависимостей
uv sync

# Запуск
uv run python -m src

# Или через Docker
docker compose up
```

## Структура проекта

```
src/
├── __main__.py                      # Точка входа, создание 4xN consumers
├── api/streams/                     # Stream handlers (по одному на сервис)
│   ├── graph_service.py
│   ├── enterprise_service.py
│   ├── auth_service.py
│   └── trip_service.py
├── app/
│   ├── fan_out_orchestrator.py      # Агрегация → сериализация → publish
│   ├── amqp_publisher.py           # Publish с retry + backoff
│   ├── bort_offset_manager.py      # Per-bort offset + seq_id в PostgreSQL
│   ├── multi_table_aggregator.py   # Last-write-wins агрегация по таблицам
│   ├── model/
│   │   ├── cdc_event.py            # Envelope (msgspec)
│   │   └── fan_out_payload.py      # FanOutPayload, TableBatch (msgspec)
│   ├── utils/
│   │   ├── table_extractor.py      # Извлечение имени таблицы из CDC-события
│   │   └── type_converter.py       # Конвертация типов Debezium → Python
│   └── factories/                   # Per-service конфигурация таблиц
│       ├── service_factory.py
│       ├── table_config.py          # Конфигурация таблиц для агрегации
│       ├── graph.py
│       ├── auth.py
│       ├── enterpise.py
│       └── trip.py
├── core/
│   ├── config.py                    # Settings (pydantic-settings)
│   ├── logging.py                   # loguru setup
│   ├── aggregator.py               # Абстрактный EventAggregator, протоколы
│   ├── cdc_aggregator.py           # CDC-специфичная реализация агрегатора
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy Base
│   │   ├── models.py               # BortStreamOffset (offset + seq_id)
│   │   └── session.py              # Async session factory
│   ├── amqp/
│   │   ├── connection_manager.py    # connect_robust + channel pool
│   │   └── queue_name.py            # server.bort_{N}.{service}.src
│   └── rstream/
│       ├── app.py                   # StreamApp, BortOffsetAdapter
│       ├── manager.py               # StreamAppManager, StreamAppConfig
│       └── router.py                # StreamRouter, BatchMetadata
└── migrations/
    └── versions/                    # Alembic-миграции
```

## Сервисы (стримы)

| Сервис | Стрим | Описание |
|---|---|---|
| graph | `cdc-graph-service` | Граф объектов (шахты, горизонты, участки, техника) |
| enterprise | `cdc-enterprise-service` | Предприятие (организации, подразделения) |
| auth | `cdc-auth-service` | Авторизация (пользователи, роли) |
| trip | `cdc-trip-service` | Рейсы (маршруты, погрузки, выгрузки) |

## Очереди бортов

Формат имени: `server.bort_{ID}.{service}.src`

Пример для `BORT_IDS=1,2`:
```
server.bort_1.graph.src
server.bort_1.enterprise.src
server.bort_1.auth.src
server.bort_1.trip.src
server.bort_2.graph.src
server.bort_2.enterprise.src
server.bort_2.auth.src
server.bort_2.trip.src
```

Всего: `len(BORT_IDS) * 4` очередей.

## Масштабирование

- **Количество consumers:** `4 * N` (4 сервиса x N бортов). Для 10 бортов = 40 consumers на одном инстансе.
- **AMQP-соединение:** одно на весь процесс, каналы из пула (размер = `max(BORT_IDS * 2, 10)`).
- **Offset DB:** одна таблица `bort_stream_offsets` с ключом `(stream_name, bort_id)`, хранит offset и seq_id.

# Telemetry Service

## Описание

Telemetry Service - сервис для сбора и хранения телеметрии от транспортных средств в Redis Streams. Сервис подписывается на MQTT топики с событиями датчиков и сохраняет их в Redis Streams для дальнейшей обработки другими сервисами.

## Основной функционал

- Подписка на MQTT топики: `truck/+/sensor/+/events` и `truck/+/sensor/+/ds`
- Сохранение телеметрии в Redis Streams с TTL (по умолчанию 2 часа)
- Формат ключа Redis Stream: `telemetry-service:{sensor_type}:{vehicle_id}`
- Health check endpoints для мониторинга состояния сервиса

## API Endpoints

### Health & Monitoring

- `GET /health` - Basic health check
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe (проверка подключения к Redis и MQTT)

## Конфигурация

### Переменные окружения

- `DEBUG` - Debug mode (true/false, default: false)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8002)
- `REDIS_URL` - Redis connection string (default: redis://localhost:6379/0)
- `NANOMQ_HOST` - NanoMQ broker host (default: nanomq-server)
- `NANOMQ_MQTT_PORT` - NanoMQ MQTT port (default: 1883)
- `TELEMETRY_STREAM_TTL_SECONDS` - TTL для Redis Streams в секундах (default: 7200 = 2 часа)
- `LOG_LEVEL` - Log level (default: INFO)

## Архитектура

- **FastAPI** web framework с application factory pattern
- **gmqtt** для async MQTT подключения
- **aioredis** для работы с Redis Streams
- **Loguru** для структурированного JSON логирования

## Формат данных

### Входящие MQTT топики

- `truck/{vehicle_id}/sensor/{sensor_type}/events` - события датчиков
- `truck/{vehicle_id}/sensor/{sensor_type}/ds` - downsampled данные датчиков
  - Примеры: 
    - `truck/AC9/sensor/speed/events`
    - `truck/AC9/sensor/speed/ds`
    - `truck/AC9/sensor/weight/events`
    - `truck/AC9/sensor/weight/ds`
  - Поддерживаемые типы датчиков: `speed`, `weight`, `fuel`, `gps`, `vibro`

### Redis Streams

- Ключ: `telemetry-service:{sensor_type}:{vehicle_id}`
- Пример: `telemetry-service:speed:AC9`
- Структура записи:
  ```json
  {
    "timestamp": "1234567890.123",
    "data": "{...JSON данные телеметрии...}"
  }
  ```
- TTL: обновляется при каждом добавлении записи

## Использование

### Запуск через Docker Compose

```bash
docker compose -f docker-compose.server.yaml up telemetry-service
```

### Проверка работы

```bash
# Health check
curl http://localhost:8002/health

# Проверка готовности (Redis + MQTT)
curl http://localhost:8002/health/ready
```

### Проверка Redis Streams

```bash
# Подключение к Redis
docker exec -it dispatching-server-redis redis-cli

# Просмотр Stream для конкретного датчика
XRANGE telemetry-service:speed:AC9 - + COUNT 10

# Просмотр длины Stream
XLEN telemetry-service:speed:AC9

# Получение последних записей
XREVRANGE telemetry-service:speed:AC9 + - COUNT 10
```

## Разработка

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск в режиме разработки

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### Структура проекта

```
telemetry-service/
├── app/
│   ├── core/
│   │   ├── config.py           # Конфигурация приложения
│   │   ├── logging_config.py   # Настройка логирования
│   │   └── dependencies.py     # Redis зависимости
│   ├── routers/
│   │   └── health.py           # Health check endpoints
│   ├── services/
│   │   ├── mqtt_client.py      # MQTT клиент для подписки
│   │   └── telemetry_storage.py # Сохранение в Redis Streams
│   └── main.py                 # FastAPI приложение
├── requirements.txt
└── Dockerfile
```

## Интеграция с другими сервисами

Другие сервисы могут читать телеметрию из Redis Streams:

```python
import aioredis

redis = await aioredis.from_url("redis://localhost:6379/0")

# Чтение записей из Stream
stream_key = "telemetry-service:speed:AC9"
messages = await redis.xread({stream_key: "0"}, count=10)

for stream, entries in messages:
    for entry_id, data in entries:
        timestamp = data[b"timestamp"].decode()
        telemetry_data = json.loads(data[b"data"].decode())
        # Обработка данных...
```


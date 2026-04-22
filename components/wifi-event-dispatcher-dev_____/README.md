# WiFi Event Dispatcher

Распределённая система маршрутизации событий между бортовыми устройствами грузовиков (BORT) и центральным сервером через gRPC и RabbitMQ. Обмен данными инициируется при появлении WiFi-соединения на борту и прекращается при его потере.

## Архитектура

```
┌──────────────────┐         gRPC (bidirectional stream)        ┌──────────────────┐
│      BORT        │◄──────────────────────────────────────────►│     Server       │
│  (клиент борта)  │                                            │  (центральный)   │
│                  │                                            │                  │
│  ┌────────────┐  │                                            │  ┌────────────┐  │
│  │ MQTT sub   │  │   WiFi up → открыть стримы                 │  │ gRPC svc   │  │
│  │ (NanoMQ)   │──┤   WiFi down → закрыть стримы               │  │            │  │
│  └────────────┘  │                                            │  └─────┬──────┘  │
│                  │                                            │        │         │
│  ┌────────────┐  │                                            │  ┌─────▼──────┐  │
│  │ RabbitMQ   │◄─┤── события от сервера                       │  │ RabbitMQ   │  │
│  │ (локальный)│──┤── события к серверу                        │  │            │  │
│  └────────────┘  │                                            │  └────────────┘  │
└──────────────────┘                                            └──────────────────┘
```

**Поток событий:**

- **Отправка (BORT → Server):** локальный RabbitMQ → gRPC stream → сервер → RabbitMQ сервера
- **Получение (Server → BORT):** RabbitMQ сервера → gRPC stream → BORT → локальный RabbitMQ
- **WiFi-мониторинг:** NanoMQ (MQTT) `truck/<ID>/sensor/wifi/fake_events` → управление жизненным циклом стримов

## Структура проекта

```
├── cmd/
│   ├── server/              # Точка входа сервера + Dockerfile
│   └── bort/                # Точка входа борта + Dockerfile
├── server/
│   ├── internal/
│   │   ├── grpc/            # gRPC-сервис (bidirectional streaming)
│   │   ├── application/     # Бизнес-логика сервера
│   │   ├── domain/          # Доменные модели
│   │   ├── dto/             # Data Transfer Objects
│   │   └── infrastructure/  # Адаптеры (publisher)
│   ├── serverpb/            # Сгенерированные protobuf-стабы
│   └── fx.go                # DI-модуль сервера
├── bort/
│   ├── internal/
│   │   ├── grpc/            # gRPC-клиент
│   │   ├── application/     # Оркестрация: стримы, реконнект, WiFi, autorepub
│   │   ├── domain/          # Доменные модели
│   │   └── mqtt/            # MQTT-подписчик (WiFi-статус)
│   ├── dto/                 # Data Transfer Objects
│   └── fx.go                # DI-модуль борта
├── domain/                  # Общие доменные модели и маршрутизация
├── internal/                # Общие пакеты
│   ├── autorepub/           # HTTP-клиент sync-service (suspend/resume autorepub)
│   ├── config/              # Загрузка конфигурации (.env / envconfig)
│   ├── logger/              # Zerolog-логгер
│   ├── rabbitmq/            # RabbitMQ клиент, publisher, subscriber
│   └── fx/                  # Общие Uber FX модули
├── docker-compose.yml       # Dev-окружение (RabbitMQ)
├── go.mod
└── go.sum
```

## Требования

- Go 1.25+
- RabbitMQ
- NanoMQ (MQTT-брокер, для BORT)
- Docker (опционально)

## Сборка

```bash
# Локальная сборка
go build -o ./server ./cmd/server
go build -o ./bort ./cmd/bort

# Docker
docker build -f cmd/server/Dockerfile -t wifi-event-dispatcher-server .
docker build -f cmd/bort/Dockerfile -t wifi-event-dispatcher-bort .
```

## Запуск

```bash
# Dev-окружение: поднять RabbitMQ
docker-compose up

# Запустить сервер
./server

# Запустить борт
./bort
```

## Конфигурация

Конфигурация загружается из файла `.env` или переменных окружения.

Пример `.env`:
```env
RABBIT_HOST=localhost
RABBIT_PORT=5672
RABBIT_USER=admin
RABBIT_PASSWORD=admin
BORT_TRUCK_ID=4
ENVIRONMENT=production
BORT_NANOMQ_HOST=10.100.109.13
BORT_NANOMQ_PORT=1883
```

### Общие параметры

| Переменная | Описание | По умолчанию |
|---|---|---|
| `ENVIRONMENT` | Режим работы (`production` / `development`) | `development` |
| `LOG_LEVEL` | Уровень логирования (TRACE, DEBUG, INFO, WARN, ERROR, PANIC) | `DEBUG` |
| `SHUTDOWN_TIMEOUT` | Таймаут graceful shutdown | `30s` |
| `RABBIT_HOST` | Хост RabbitMQ | — |
| `RABBIT_PORT` | Порт RabbitMQ | — |
| `RABBIT_USER` | Пользователь RabbitMQ | — |
| `RABBIT_PASSWORD` | Пароль RabbitMQ | — |
| `RABBIT_VHOST` | Виртуальный хост RabbitMQ | `/` |

### Server

| Переменная | Описание | По умолчанию |
|---|---|---|
| `SERVER_RPC_HOST` | Адрес привязки gRPC-сервера | `0.0.0.0` |
| `SERVER_RPC_PORT` | Порт gRPC-сервера | `:8085` |

### BORT

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BORT_TRUCK_ID` | ID грузовика (число) | — |
| `BORT_SERVER_ADDRESS` | Адрес gRPC-сервера | `localhost:8085` |
| `BORT_NANOMQ_HOST` | Хост NanoMQ (MQTT) | — |
| `BORT_NANOMQ_PORT` | Порт NanoMQ (MQTT) | — |
| `BORT_NANOMQ_CLIENT_PREFIX` | Префикс MQTT client ID | `wifi_event_dispatcher` |

### Autorepub (BORT)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `COORDINATION_URL` | Базовый URL sync-service для получения distribution | — |
| `DISTRIBUTION_PORT` | Порт HTTP-эндпоинтов autorepub на нодах | `8000` |
| `AUTOREPUB_HTTP_TIMEOUT` | Таймаут HTTP-запросов к autorepub | `10s` |

## gRPC API

Сервис определён в `server/serverpb/api.proto`:

```protobuf
service EventDispatchService {
  rpc StreamBortSendEvents(stream SendEventRequest) returns (stream SendEventResponse);
  rpc StreamBortGetEvents(stream GetEventRequest) returns (stream GetEventResponse);
}
```

- **StreamBortSendEvents** — BORT отправляет события на сервер, получает ACK
- **StreamBortGetEvents** — BORT получает события от сервера, отправляет ACK

gRPC reflection включён — можно использовать `grpcurl` для отладки.

## Управление жизненным циклом WiFi

BORT подписывается на MQTT-топик `truck/{TRUCK_ID}/sensor/wifi/fake_events` и управляет стримами:

```json
{"data": {"value": true}}   // WiFi up  → открыть gRPC-стримы
{"data": {"value": false}}  // WiFi down → закрыть gRPC-стримы
```

При разрыве соединения стримы автоматически восстанавливаются с экспоненциальным backoff (от 1 с до 30 с).

## Управление autorepub

Перед открытием gRPC-стримов BORT приостанавливает авторепубликацию на всех нодах, чтобы избежать дублирования событий пока идёт синхронизация через стрим. После остановки стримов авторепубликация возобновляется.

**Последовательность при WiFi up:**

1. `GET {COORDINATION_URL}/coordination/distribution` — получить карту распределения truck_id по нодам:
   ```json
   {"distribution": {"70f5cf1ffaa5": [4, 9, 17, 22]}}
   ```
2. Для каждой ноды: `POST http://<node>:{DISTRIBUTION_PORT}/autorepub/suspend` с её truck_ids
3. Открыть gRPC-стримы

**Последовательность при WiFi down:**

1. Остановить gRPC-стримы
2. Для каждой ноды: `POST http://<node>:{DISTRIBUTION_PORT}/autorepub/resume` с её truck_ids

Если запрос к sync-service или к ноде завершился ошибкой — стримы всё равно открываются/закрываются. Ошибки логируются как `WARN`.

## Маршрутизация очередей

RabbitMQ использует topic exchange. Суффикс `.src` трансформируется в `.dst` при доставке.

| Направление | Паттерн | Пример |
|---|---|---|
| BORT → Server (send queue) | `bort_{ID}.server.{service}.src` | `bort_4.server.trip_service.src` |
| Server → BORT (get queue) | `server.bort_{ID}.{service}.src` | `server.bort_4.trip_service.src` |

## Тестирование

```bash
# Запустить все тесты с race detector
make test

# Сгенерировать отчёт о покрытии
make coverage

# Артефакты для SonarQube
make sonar-artifacts
```

Покрытие тестами: `domain`, `bort/internal/application`, `server/internal`, `internal/config`.
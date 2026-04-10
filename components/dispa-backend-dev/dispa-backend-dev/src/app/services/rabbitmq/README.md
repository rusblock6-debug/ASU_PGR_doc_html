# RabbitMQ module (`app/services/rabbitmq`)

Этот модуль отвечает за обмен сообщениями между бортом и сервером через RabbitMQ (FastStream).

## Основные роли

- `bort` — клиент техники:
  - отправляет события/данные на сервер;
  - принимает команды от сервера.
- `server` — серверная сторона:
  - принимает сообщения от бортов;
  - отправляет команды на конкретный борт.

Режим выбирается через `settings.service_mode` (`bort` или `server`).

## Структура модуля

- `main.py` — фабрика/роутинг publisher-менеджера по режиму (`RabbitMQManager`).
- `base_publisher.py` — абстрактный интерфейс `ABSPublisherManager`.
- `bort/app.py` — consumer борта (подписка на входящую очередь борта).
- `bort/publisher.py` — publisher борта.
- `server/app.py` — consumer сервера (подписка на очереди конкретных бортов).
- `server/publisher.py` — publisher сервера (отправка на конкретный борт).
- `retry_middleware.py` — общий retry middleware FastStream (используется и на `server`, и на `bort`).
- `schemas/` — Pydantic-схемы сообщений.
- `enum.py` — enum-ы типов/событий сообщений.

## Очереди и направление сообщений

Для борта `<vehicle_id>` используются две очереди:

- `server.bort_<vehicle_id>.trip.src`
- `server.bort_<vehicle_id>.trip.dst`

Принятый контракт:

- **bort -> server**: публикация в `trip.src`.
- **server -> bort**: публикация в `trip.dst`.

## Поток обработки

### 1) Борт отправляет сообщение

1. На борту вызывается `VehiclePublisherBortManager.task_publish(...)`.
2. Сообщение уходит в `server.bort_<vehicle_id>.trip.src`.
3. Сервер в `server/app.py` подписан на `trip.src`, принимает и обрабатывает сообщение.

### 2) Сервер отправляет команду борту

1. На сервере вызывается `ServerPublisherBortManager.task_publish(..., vehicle_id)`.
2. Сообщение уходит в `server.bort_<vehicle_id>.trip.dst`.
3. Борт в `bort/app.py` подписан на `trip.dst`, принимает и обрабатывает сообщение.

## Подтверждения доставки (`success`)

В хендлерах `bort/app.py` и `server/app.py` после успешной обработки отправляется служебное сообщение подтверждения:

- payload: `{"message_type": "success", "id": <id_message>}`

Чтобы исключить цикл подтверждений, в consumer-хендлерах есть защита:

- если `msg["message_type"] == "success"`, сообщение не обрабатывается как бизнес-команда и не подтверждается повторно.

## Надежность и ACK

- Используется `ack_policy=AckPolicy.NACK_ON_ERROR`.
- На обеих сторонах (`bort/app.py` и `server/app.py`) подключен retry middleware `RetryExponentialBackoffMiddleware`.
- Retry использует экспоненциальную задержку:
  - задержка попытки = `retry_base_delay_sec * (2 ** attempt)`
  - максимум попыток = `retry_max_attempts`
- Параметры берутся из настроек `settings.rabbit`:
  - `settings.rabbit.retry_max_attempts`
  - `settings.rabbit.retry_base_delay_sec`
- Очереди создаются durable (`durable=True`) в consumer-подписках.

## Схемы сообщений

Базовая схема (`schemas/base.py`):

- `id_message`
- `event_message`
- `type_message`

Частные схемы:

- `ShiftTaskMsgScheme` (`schemas/shift.py`)
- `RouteTaskMsgScheme` / `RouteTaskIdMsgScheme` (`schemas/route.py`)

## Запуск

Локальный запуск через скрипт `start.broker.sh`:

- сервер:
  - `sh start.broker.sh server`
- борт:
  - `sh start.broker.sh bort <vehicle_id>`

В Docker рекомендуется запускать брокер как отдельный сервис (отдельный Dockerfile/compose service), а API — отдельным сервисом.

## Где смотреть при проблемах

- Логи publishers:
  - `bort/publisher.py`
  - `server/publisher.py`
- Логи consumers:
  - `bort/app.py`
  - `server/app.py`
- Проверить, что `vehicle_id` передается в server publisher:
  - без него сообщения могут уйти в очередь вида `server.bort_None...`.

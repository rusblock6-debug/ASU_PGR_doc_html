# API Gateway

Легковесный API Gateway на `aiohttp` для маршрутизации запросов в внутренние сервисы по имени сервиса.

## Что делает сервис

- Принимает входящие запросы на `/api/{version}/{service}/{path...}` (например, `v1` и `v2`).
- По `service` выбирает upstream из `config.yaml`.
- Проксирует обычный HTTP-трафик.
- Поддерживает проксирование WebSocket и Server-Sent Events (SSE).
- Выдает `GET /health` для проверки доступности gateway.
- Добавляет/пробрасывает `X-Request-Id` для трассировки.
- Проверяет JWT через auth-service, если в запросе есть `Authorization`.

## Как проходит запрос

1. Запрос приходит в gateway.
2. `request_id_middleware`:
   - берет входящий `X-Request-Id` или генерирует новый UUID;
   - сохраняет id в `request["request_id"]`;
   - возвращает его в заголовке ответа.
3. `jwt_verification_middleware`:
   - пропускает `/health`;
   - если `Authorization` нет, пропускает дальше без проверки;
   - если `Authorization` есть, делает `GET` в auth-service на `auth.verify_endpoint`;
   - при ответе не `200` возвращает `401 {"error":"Unauthorized"}`;
   - при ошибке связи с auth-service возвращает `503 {"error":"Service Unavailable"}`.
4. `proxy_handler`:
   - находит сервис в `settings.services`;
   - строит URL вида `<service_url>/api/<version>/<path>?<query>`;
   - проксирует как HTTP / WebSocket / SSE.

Если сервис не найден в конфигурации, gateway возвращает `502 {"error":"Service not found"}`.

## Контракт структурированных логов gateway (US-001)

Gateway использует **единый JSON-контракт** для событий:

- `request_success`
- `request_error`
- `auth_error`
- `proxy_error`

Каждое событие пишется одной строкой JSON и обязано содержать все поля:

Ключевые обязательные metadata-поля для интеграции и операционного мониторинга:
`request_id`, `elapsed_ms`, `status`, `service`, `api_version`.

```json
{
  "timestamp": "<RFC3339 UTC>",
  "level": "<info|error>",
  "message": "<event message>",
  "request_id": "<non-empty string>",
  "elapsed_ms": "<int >= 0>",
  "method": "<HTTP method>",
  "path": "<request path>",
  "query": "<raw query string or empty>",
  "status": "<HTTP status code>",
  "service": "<service key or unknown>",
  "api_version": "<v1|v2|...|unknown>",
  "upstream_url": "<absolute upstream url or unresolved>",
  "client_ip": "<client ip or unknown>",
  "user_agent": "<user-agent or empty>",
  "response_size": "<bytes, int >= 0>",
  "error_type": "<none or stable error code>"
}
```

### Поля и правила

| Поле | Тип | Правило |
|---|---|---|
| `timestamp` | `string` | RFC3339 в UTC, например `2026-02-24T16:00:00.123Z` |
| `level` | `string` | `info` для успеха, `error` для ошибок |
| `message` | `string` | Стабильное имя события (`request_completed`, `request_failed` и т.д.) |
| `request_id` | `string` | Всегда непустой: входящий `X-Request-Id` либо сгенерированный UUID4 |
| `elapsed_ms` | `integer` | Время обработки от входа запроса до финального ответа |
| `method` | `string` | HTTP-метод запроса |
| `path` | `string` | Путь запроса без host |
| `query` | `string` | Query-string без `?`, пустая строка если параметров нет |
| `status` | `integer` | HTTP-статус ответа |
| `service` | `string` | Имя целевого сервиса или `unknown` |
| `api_version` | `string` | Версия API из маршрута (`v1`, `v2`, ...), иначе `unknown` |
| `upstream_url` | `string` | Итоговый URL upstream или `unresolved` |
| `client_ip` | `string` | IP клиента или `unknown` |
| `user_agent` | `string` | User-Agent, пустая строка если отсутствует |
| `response_size` | `integer` | Размер ответа в байтах, `0` если не определен |
| `error_type` | `string` | `none` для успеха; для ошибок фиксированный код причины |

### Безопасность логов (negative case)

Gateway **не логирует**:

- значение заголовка `Authorization`;
- тело запроса (request body payload).

Это сделано, чтобы не допускать утечек токенов и чувствительных данных в production-логах.

### Матрица событий

| Event | `level` | `message` | `error_type` |
|---|---|---|---|
| `request_success` | `info` | `request_completed` | `none` |
| `request_error` | `error` | `request_failed` | Например `gateway_error` |
| `auth_error` | `error` | `auth_failed` | `unauthorized` / `auth_service_unavailable` |
| `proxy_error` | `error` | `proxy_failed` | `service_not_found` / `upstream_connection_error` |

### Пример `request_success`

Запрос `GET /api/v1/trip-service/orders?limit=10` должен дать ровно один completion-log:

```json
{
  "timestamp": "2026-02-24T16:10:00.431Z",
  "level": "info",
  "message": "request_completed",
  "request_id": "4db5ef52-4f3b-4545-bcc9-58c2d2ad3c40",
  "elapsed_ms": 18,
  "method": "GET",
  "path": "/api/v1/trip-service/orders",
  "query": "limit=10",
  "status": 200,
  "service": "trip-service",
  "api_version": "v1",
  "upstream_url": "http://trip-service:3001/api/v1/orders?limit=10",
  "client_ip": "10.20.30.40",
  "user_agent": "curl/8.7.1",
  "response_size": 512,
  "error_type": "none"
}
```

### Негативный кейс: нет входящего `request_id`

Если `X-Request-Id` отсутствует или пустой, в логе обязателен сгенерированный непустой `request_id`:

```json
{
  "timestamp": "2026-02-24T16:12:40.901Z",
  "level": "error",
  "message": "proxy_failed",
  "request_id": "d4f041ef-8da3-424f-8c6a-cb905f8f5f02",
  "elapsed_ms": 7,
  "method": "GET",
  "path": "/api/v1/unknown/orders",
  "query": "",
  "status": 502,
  "service": "unknown",
  "api_version": "v1",
  "upstream_url": "unresolved",
  "client_ip": "10.20.30.40",
  "user_agent": "curl/8.7.1",
  "response_size": 33,
  "error_type": "service_not_found"
}
```

### Примеры error-событий

`auth_error`:

```json
{
  "timestamp": "2026-02-24T16:13:10.014Z",
  "level": "error",
  "message": "auth_failed",
  "request_id": "1f24fb1a-899d-4af0-bb7a-8cd528370274",
  "elapsed_ms": 4,
  "method": "GET",
  "path": "/api/v1/trip-service/orders",
  "query": "",
  "status": 401,
  "service": "trip-service",
  "api_version": "v1",
  "upstream_url": "http://trip-service:3001/api/v1/orders",
  "client_ip": "10.20.30.40",
  "user_agent": "curl/8.7.1",
  "response_size": 25,
  "error_type": "unauthorized"
}
```

`proxy_error`:

```json
{
  "timestamp": "2026-02-24T16:13:42.503Z",
  "level": "error",
  "message": "proxy_failed",
  "request_id": "7b7f28e4-0f3d-4dd2-8e85-f5bd14f2eea0",
  "elapsed_ms": 32,
  "method": "GET",
  "path": "/api/v1/trip-service/orders",
  "query": "limit=10",
  "status": 502,
  "service": "trip-service",
  "api_version": "v1",
  "upstream_url": "http://trip-service:3001/api/v1/orders?limit=10",
  "client_ip": "10.20.30.40",
  "user_agent": "curl/8.7.1",
  "response_size": 46,
  "error_type": "upstream_connection_error"
}
```

Контракт определяет только формат и семантику полей. Реализация вывода JSON и middleware-логирования выполняется отдельными историями. Новые сторонние logging-зависимости в рамках этого шага не добавляются.

## Маршрутизация

Входной маршрут:

```text
/api/{version}/{service}/{path:.*}
```

Примеры маппинга gateway -> downstream при `trip-service.url = http://trip-service:3001`:

```text
GET /api/v1/trip-service/orders?limit=10
-> GET http://trip-service:3001/api/v1/orders?limit=10
```

```text
GET /api/v2/trip-service/orders
-> GET http://trip-service:3001/api/v2/orders
```

## Конфигурация

Основная конфигурация лежит в `config.yaml`.

Пример:

```yaml
auth:
  url: "http://auth-service:3000"
  verify_endpoint: "/api/v1/verify"

services:
  trip-service:
    url: "http://trip-service:3001"
```

Параметры приложения:

- `host` (по умолчанию `0.0.0.0`)
- `port` (по умолчанию `8080`)

Настройки читаются через `pydantic-settings` из:

1. аргументов инициализации `Settings(...)`;
2. `config.yaml`;
3. переменных окружения;
4. `.env`.

## Быстрый старт

Требования:

- Python `>=3.13`
- `uv`

Установка зависимостей:

```bash
make sync
```

Запуск:

```bash
make start
```

Проверка:

```bash
curl -i http://localhost:8080/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Команды разработки

- `make help` - список доступных команд
- `make lint` - проверка линтером (`ruff check`)
- `make format` - форматирование (`ruff format` + `ruff check --fix`)
- `make check-types` - проверка типов (`mypy`)
- `make setup-precommit` - установка pre-commit hooks
- `make check-precommit` - запуск pre-commit на всех файлах

## Runbook перед merge

Обязательная валидация перед merge:

```bash
make check-precommit
```

Изменения считаются готовыми к merge только после успешного прохождения этой команды.

## Структура репозитория

```text
src/
  __main__.py      # точка входа, запуск aiohttp app
  app.py           # фабрика приложения, роуты, startup/cleanup
  config.py        # модели и загрузка настроек
  middleware.py    # X-Request-Id и JWT middleware
  proxy.py         # прокси-обработчик HTTP/WS/SSE
config.yaml        # маршрутизация сервисов и auth
Makefile           # команды разработки и запуска
```

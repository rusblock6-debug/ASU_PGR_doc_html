# Система диспетчеризации

## Компоненты системы

1. **Redis** - кэш и очередь сообщений
2. **eKuiper** - потоковая обработка данных
3. **NanoMQ** - MQTT брокер
4. **PostgreSQL + PostGIS + TimescaleDB** - база данных с поддержкой геоданных и временных рядов
5. **Airbyte** - интеграция и синхронизация данных
6. **Apache Superset** - визуализация и BI аналитика
7. **Trino** - движок для федеративных запросов
8. **ClickHouse** - OLAP база
9. **Dozzle** - веб-интерфейс для просмотра логов контейнеров


## Быстрый старт

### 1. Запуск в режиме разработки

```bash
make dev-bort
```

### 1.1 Запуск через settings-service (рекомендуется для bort)

Сценарий (двухэтапный):
1. Поднимает `settings-service` из отдельного `docker-compose.settings-bort.yaml`.
2. В UI `settings-bort` (`/admin`) задает `SETTINGS_URL` и `ENTERPRISE_SERVER_URL` (локальное хранение в SQLite).
3. Делает инициализацию `POST /api/secrets/init/{VEHICLE_ID}` (через UI или `curl`).
4. `settings-bort` экспортирует секреты в `dispatching-repo/.env.settings.generated`.
5. Запускает полный `docker-compose.bort.yaml` с `base env + .env.settings.generated`.

Можно без UI: передайте переменные в окружение для `docker-compose.settings-bort.yaml`:
- `SETTINGS_URL`, `ENTERPRISE_SERVER_URL`
- `VEHICLE_ID` (или `AUTO_INIT_VEHICLE_ID`)
- `AUTO_INIT_ENABLED=true` (по умолчанию включен)
- `AUTO_INIT_RETRY_INTERVAL_SEC` (по умолчанию `30`)
- `AUTO_INIT_MAX_ATTEMPTS=0` (бесконечные ретраи)
- `AUTO_SYNC_ENABLED=true` (фоновая синхронизация после первого init)
- `AUTO_SYNC_INTERVAL_SEC=30`

В этом режиме `settings-bort` сам пытается инициализироваться при старте и продолжает ретраи даже если хосты временно недоступны.
Если `settings-server` меняет секреты, он может сразу уведомить `settings-bort` через webhook
`POST /api/admin/sync/{vehicle_id}` (см. env `BORT_NOTIFY_*` в `docker-compose.server.yaml`).

```bash
# Шаг 1 (опционально): поднять только settings-bort (UI/API)
make up-settings-bort e=bort_4_dev

# Manual flow: ждёт, пока вы вручную сделаете init через UI/curl (и будет создан .env.settings.generated), затем запускает весь bort
make bootstrap-bort-manual e=bort_4_dev

# Пример ручной инициализации
curl -X POST "http://127.0.0.1:8017/api/secrets/init/4"

# по умолчанию использует .env
make bootstrap-bort

# или конкретный env-файл (например .env_bort_4_dev)
make bootstrap-bort e=bort_4_dev

# VEHICLE_ID можно передать извне (например, из CI), он приоритетнее значения из env-файла
VEHICLE_ID=22 make bootstrap-bort e=bort_4_dev

# После генерации .env.settings.generated обычный запуск make dev-bort
# автоматически подхватит его как приоритетный env-файл (поверх base env)
```


### 2. Базовые команды

```bash
# Показать все доступные команды
make help

# Остановить все сервисы
make stop
# или
make down

# Просмотр логов
make logs

# Просмотр логов конкретного сервиса
make logs-postgres
make logs-redis

# Статус сервисов
make ps

# Показать URLs всех сервисов
make urls

# Тестирование подключений
make test-connections
```

## Доступ к сервисам

После запуска сервисы будут доступны по следующим адресам:
| Сервис | Описание | Локальный URL | Учетные данные |
|--------|----------|---------------|----------------|
| **Redis** | Кэш и очередь сообщений | `localhost:6379` | - |
| **PostgreSQL** | Реляционная БД с геоданными | `localhost:5432` | postgres/postgres |
| **NanoMQ** | MQTT брокер для IoT | `localhost:1883` (MQTT)<br>`ws://localhost:8083/mqtt` (WebSocket)<br>http://localhost:8081
| **eKuiper** | Потоковая обработка данных | http://localhost:9081<br>http://localhost:9082 (REST) | - |
| **eKuiper Manager** | Веб-интерфейс для eKuiper | http://localhost:9083 | admin/public | - |
| **ClickHouse** | OLAP БД для аналитики | http://localhost:8123 (HTTP)<br>`localhost:9000` (Native) | default/clickhouse |
| **Trino** | Распределенный SQL движок | http://localhost:8080 | - |
| **Airbyte** | Интеграция данных (сервер) | http://localhost:8000 | - |
| **Superset** | BI платформа визуализации | http://localhost:8088 | admin/admin |
| **Dozzle** | Просмотр логов контейнеров | http://localhost:9999 | - |

## Управление миграциями базы данных

### Проверка целостности миграций

Скрипт проверяет все сервисы с миграциями на соответствие стандартам:
- Формат имени файла: `{NNN}_{message}.py` (NNN - 3 цифры)
- Соответствие revision в коде имени файла
- Отсутствие дубликатов ревизий в рамках одного сервиса
- Последовательность миграций (без пропусков)
- Корректность цепочки down_revision

**При наличии ошибок или предупреждений CI/CD job завершается с кодом 1 (ошибка).**

```bash
make check-migrations
```

### Расположение скрипта

```
dispatching-repo/
├── scripts/
│   └── check_migrations.py    # Проверка целостности миграций
```

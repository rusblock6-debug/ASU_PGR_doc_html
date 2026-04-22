# Система диспетчеризации

## Компоненты

1. **Redis** - кэш и очередь сообщений
2. **eKuiper** - потоковая обработка данных
3. **NanoMQ** - MQTT брокер
4. **PostgreSQL + PostGIS + TimescaleDB** - база данных
5. **Dozzle** - просмотр логов контейнеров

## Быстрый старт

```bash
task dev-bort
```

## Основные команды

```bash
task help
task down
task logs-bort
task ps
task urls
task check-migrations
```

## Локальные URL

| Сервис | URL | Учетные данные |
|--------|-----|----------------|
| Redis | `localhost:6379` | - |
| PostgreSQL | `localhost:5432` | `postgres/postgres` |
| NanoMQ MQTT | `localhost:1883` | - |
| NanoMQ WebSocket | `ws://localhost:8083/mqtt` | - |
| NanoMQ Admin | `http://localhost:8081` | `admin/public` |
| eKuiper | `http://localhost:9081` | - |
| eKuiper Manager | `http://localhost:9083` | `admin/public` |
| Trip Service Backend | `http://localhost:8000` | - |
| Graph Service Backend | `http://localhost:5001` | - |
| Main Frontend | `http://localhost:3000` | - |
| Graph Service Frontend | `http://localhost:3001` | - |
| Dozzle | `http://localhost:9999` | - |

## Проверка миграций

```bash
task check-migrations
```

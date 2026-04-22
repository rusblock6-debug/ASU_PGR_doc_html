# Dispatching Server

Репозиторий содержит только server-часть системы диспетчеризации.

## Быстрый старт

Основной сценарий запускается через `task`.

```bash
task init-server
task dev-server ENV_FILE=.env_server_dev
```

Для stage-конфигурации используйте:

```bash
task dev-server ENV_FILE=.env_server_stage
```

## Основные команды

```bash
task --list
task ps ENV_FILE=.env_server_dev
task logs ENV_FILE=.env_server_dev
task down ENV_FILE=.env_server_dev
task vector
task check-migrations
```

## Доступ к сервисам

- `Enterprise Service`: `http://localhost:8002`
- `Client`: `http://localhost:5173`
- `API Gateway`: `http://localhost:8015`
- `Dozzle`: `http://localhost:9998`
- `Vector API`: `http://localhost:9099`

## Файлы окружения

- `.env_server_dev`
- `.env_server_stage`

Если `ENV_FILE` не передан явно, `Taskfile.yml` использует `.env_server_dev`.

`Taskfile.yml` использует те же переменные и алиасы:

- `task init` -> `task init-server`
- `task logs` -> `task logs-server`
- `task ps` -> `task ps-server`
- `task urls` -> `task urls-server`
- `task stop` -> `task down`

`task dev-server` теперь дополнительно поднимает Vector через `monitoring/start.sh`.

## Установка task

Локально можно использовать скрипт:

```bash
bash scripts/install_task.sh ./.bin
PATH="$PWD/.bin:$PATH" task --list
```

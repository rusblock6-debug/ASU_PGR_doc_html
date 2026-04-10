# Dump Service

Сервис формирует дамп данных по рейсу (trip) из базы Trip Service и сохраняет результат в виде `tar.gz` архива, содержащего parquet-файлы с историей стейтов и тегов. После генерации файл регистрируется в собственной базе `dump-service`, откуда он может быть передан в хранилище (MinIO/S3) и синхронизирован в другие системы.



## Переменные окружения
Создайте файл `.env` (проще скопировать `.env.example`)
## Подготовка окружения
1. Установите Python 3.13 и [`uv`](https://docs.astral.sh/uv/).
2. Скопируйте `.env.example` → `.env` и поправьте значения.
3. Поднимите зависимости: `docker compose up -d` (MinIO, Redis, Postgres). Убедитесь, что БД Trip Service доступна и содержит нужные таблицы.
4. Установите зависимости приложения: `make sync` (вызовет `uv sync`).
5. Прогоните миграции: `make migrate`



## Полезные команды
- `make sync` – установка зависимостей.
- `make migrate` / `make rollback` – управление миграциями.
- `make lint` – Ruff lint.
- `make format` – Ruff format + fix.
- `make check-types` – mypy.

---
## Для MacOS (Colima)
```bash
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
export TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE="/var/run/docker.sock"
```
Рекомендуемый способ для автоматического экспорта env при работе в каталоге проекта.

1. Установите `direnv`:
```bash
brew install direnv
```
2. Добавьте хук в `~/.zshrc`:
```bash
eval "$(direnv hook zsh)"
```
3. Скопировать .envrc.example > .envrc
```bash
cp ./.envrc.example ./.envrc
```

4. Разрешите:
```bash
direnv allow
```

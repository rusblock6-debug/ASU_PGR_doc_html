# Enterprise Service

Core сервис для управления статичными данными предприятия (техника, смены, режимы работы, точки погрузки/разгрузки, статусы).

## Основной функционал

- **Техника (Vehicles)**: Управление мобильными объектами (ПДМ, ШАС)
- **Режимы работы (WorkRegimes)**: Определение смен с динамическим расчётом
- **Сменные задания (ShiftTasks)**: Наряд-задания с маршрутами
- **Маршруты (RouteTasks)**: Задания с точками погрузки и разгрузки
- **Статусы**: Справочник статусов (ремонт, обед и т.д.)

## API Endpoints

### Health & Monitoring
- `GET /health` - Базовая проверка здоровья
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

### Core Endpoints
- `GET /api/work-regimes` - Список режимов работы
- `POST /api/work-regimes` - Создание режима
- `GET /api/vehicles` - Список техники
- `POST /api/vehicles` - Добавление техники
- `GET /api/load-unload-points` - Список точек работ
- `POST /api/load-unload-points` - Создание точки
- `GET /api/statuses` - Список статусов
- `POST /api/statuses` - Добавление статуса
- `GET /api/shift-tasks` - Список заданий
- `POST /api/shift-tasks` - Создание задания

## Установка и запуск

### Local Development

```bash
# Клонирование репозитория
cd repos/enterprise-service

# Установка uv (если ещё не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установка зависимостей (Python 3.11 установится автоматически)
uv sync

# Настройка окружения
cp .env.example .env
# Отредактируйте .env

# Запуск миграций
uv run alembic upgrade head

# Запуск приложения
uv run uvicorn app.main:app --reload
```

### Docker Development

```bash
# Запуск всех сервисов
docker compose up --build

# Или только enterprise-service
docker compose up enterprise-service
```

## Конфигурация

Необходимые переменные окружения:

### Core Configuration
- `DEBUG` - Debug mode (true/false)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8001)

### Database Configuration
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_POOL_SIZE` - Connection pool size (default: 20)
- `DATABASE_MAX_OVERFLOW` - Max overflow connections (default: 30)

### Redis Configuration
- `REDIS_URL` - Redis connection string (default: redis://localhost:6379/0)

### Timezone Configuration
- `TIMEZONE` - Timezone for shift calculations (default: Europe/Moscow)

### Logging
- `LOG_LEVEL` - Logging level (default: INFO)

## Архитектура

- **FastAPI** - web framework с application factory pattern
- **SQLAlchemy 2.0** - async ORM для работы с PostgreSQL
- **Pydantic v2** - validation и serialization
- **Alembic** - database migrations
- **Redis** - кэширование и pub/sub
- **Loguru** - structured JSON logging

## Development Guidelines

- Follow PEP 8 style guide с максимум 79 символов на строку
- Все функции должны иметь type hints
- Все public методы должны иметь docstrings
- Используй structured logging через Loguru
- Следуй async patterns во всём приложении
- Обновляй документацию при изменении API

## Микросервисная архитектура

### Входящие зависимости
- Нет (core сервис)

### Исходящие зависимости
- Все остальные сервисы читают статику отсюда

### Коммуникация
- **Redis Pub/Sub** - уведомления об изменениях (`static_data_update`, `entity_changed`)
- **Redis Cache** - кэширование полных пакетов данных

## Файлы документации

- `task.md` - Техническая спецификация
- `thoughts.md` - Выводы и записи
- `todo.md` - Ченджлог и статус

---

**Готово к реализации!**

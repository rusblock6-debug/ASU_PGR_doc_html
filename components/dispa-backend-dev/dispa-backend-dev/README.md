# Архитектура Trip Service для системы диспетчеризации горных работ

## Обзор сервиса

Trip Service является ключевым компонентом бортовой части системы, отвечающим за управление рейсами горной техники, отслеживание их выполнения и ведение state machine состояния машины.

## Основные задачи Trip Service

### 1. Управление рейсами
- **Получение рейсов с сервера:** Синхронизация плановых рейсов из серверной части
- **Отслеживание активного рейса:** Мониторинг выполнения текущей задачи
- **Фиксирование внеплановых рейсов:** Автоматическое определение и запись самостоятельных рейсов

### 2. State Machine в Redis
- **Stateless архитектура:** Хранение состояния машины в Redis для быстрого доступа
- **Состояния по датчикам:** Отслеживание состояния на основе событий от eKuiper
- **Pub/Sub механизм:** Публикация изменений состояния для реактивной обработки

### 3. Интеграция с компонентами системы
- **eKuiper:** Подписка на события датчиков из локального Nanomq
- **PostgreSQL + TimescaleDB:** Хранение истории рейсов и телеметрии
- **Redis:** Хранение текущего состояния и кэширование
- **Серверная часть:** Синхронизация плановых рейсов через API

### 4. Database Migrations (Alembic)
- **Автоматические миграции при старте:** Сервис применяет миграции автоматически через Alembic при запуске
- **Создание таблиц:** Все таблицы (`shift_tasks`, `tasks`, `trips`, `trip_state_history`, `trip_tag_history`, `trip_analytics`) создаются через миграции
- **TimescaleDB hypertables:** Создание hypertables для временных рядов происходит в миграциях
- **Версионирование схемы:** Изменения структуры БД версионируются через Alembic revisions
- **Команда:** `alembic upgrade head` выполняется автоматически в lifespan при старте FastAPI

## Архитектура взаимодействия

### ⚠️ Важные терминологические уточнения:

1. **vehicle_id vs truck_id:**
   - `vehicle_id` = уникальный ID машины в системе (используется в Redis, PostgreSQL, API)
   - `truck_id` = тот же ID, но используется только в путях Nanomq топиков (`/truck/${truck_id}/...`)
   - Это ОДИН И ТОТ ЖЕ идентификатор, просто разное именование для совместимости

2. **shift_id nullable:**
   - Для плановых рейсов: `shift_id` заполнен (берется из `active_task.shift_id`)
   - Для внеплановых рейсов: `shift_id = NULL` (нет привязки к смене)
   - В таблицах PostgreSQL: `shift_id TEXT` (nullable)

3. **Форматы временных меток:**
   - **В PostgreSQL:** `TIMESTAMPTZ` - стандартный PostgreSQL timestamp с timezone
   - **В Redis JSON:** `float` - Unix timestamp (секунды с 1970-01-01), например `1755500636.0`
   - **В Nanomq событиях:** `float` - Unix timestamp для консистентности с датчиками
   - **В API ответах:** `ISO 8601 string` - человекочитаемый формат (`"2024-01-15T10:30:00Z"`)
   - **Конвертация:** PostgreSQL ↔ Python `datetime.fromtimestamp()` ↔ JSON `float`

### Структурированный анализ взаимодействий

#### NANOMQ - Входящие топики (что читаем)
```
/truck/${truck_id}/sensor/tag/raw          → point_id, point_type
/truck/${truck_id}/sensor/speed/events     → status: "moving" | "stopped"
/truck/${truck_id}/sensor/weight/events    → status: "loaded" | "empty"
/truck/${truck_id}/sensor/vibro/events     → status: "active" | "inactive"
```

#### NANOMQ - Исходящие топики (что пишем)
```
/truck/${truck_id}/trip-service/events        → События рейсов:
  - trip_started (internal_trip_id, server_trip_id, trip_type)
  - trip_completed (internal_trip_id, server_trip_id)
  - task_activated (task_id)
  - task_cancelled (task_id)
  - shift_task_received (shift_id)
  - shift_task_completed (shift_id) ✨
  - shift_task_cancelled (shift_id) ✨

/truck/${truck_id}/trip-service/state_changes → Изменения State Machine:
  - state_transition (from_state, to_state, internal_trip_id)
```

#### REDIS - Ключи для записи (что пишем)
```
trip-service:vehicle:${vehicle_id}:state              → JSON состояния State Machine
trip-service:vehicle:${vehicle_id}:active_trip        → JSON активного рейса (trip) ✨
trip-service:vehicle:${vehicle_id}:active_task        → JSON активного задания (task)
trip-service:vehicle:${vehicle_id}:current_tag        → JSON текущей метки
trip-service:vehicle:${vehicle_id}:tag_history        → Redis Stream (XADD)

trip-service:task_queue:ordered                     → Sorted Set (ZADD, score=order)
trip-service:task_queue:{start_point_id}            → Sorted Set (ZADD, score=order)
```

**Redis Pub/Sub топики (PUBLISH):**
```
trip-service:vehicle:${vehicle_id}:state:changes       → Изменения State Machine
trip-service:vehicle:${vehicle_id}:active_trip:changes → Изменения активного рейса ✨
trip-service:vehicle:${vehicle_id}:active_task:changes → Изменения активного задания
trip-service:vehicle:${vehicle_id}:current_tag:changes → Изменения текущей метки
trip-service:vehicle:${vehicle_id}:tag_history:changes → Новая метка в истории
trip-service:shift_task_changes                      → Изменения shift_task
```

#### REDIS - Ключи для чтения (что читаем)
```
trip-service:vehicle:${vehicle_id}:state              → Восстановление состояния
trip-service:vehicle:${vehicle_id}:active_trip        → Проверка активного рейса ✨
trip-service:vehicle:${vehicle_id}:active_task        → Проверка активного задания
trip-service:vehicle:${vehicle_id}:current_tag        → Получение текущей метки
trip-service:vehicle:${vehicle_id}:tag_history        → История меток (XLEN, XRANGE)

trip-service:task_queue:ordered                     → ZRANGE для выбора задания
trip-service:task_queue:{start_point_id}            → ZRANGE для заданий из точки
```

#### POSTGRESQL - Таблицы для записи (что пишем)
```sql
shift_tasks          → INSERT (новые смены), UPDATE (статус)
tasks                → INSERT (новые задания), UPDATE (статус, activated_at, started_at, completed_at)
trips                → INSERT (создание рейса), UPDATE (завершение с временными метками)
trip_state_history   → INSERT (начало состояния), UPDATE (конец состояния, duration)
trip_tag_history     → INSERT (история меток при завершении рейса)
trip_analytics       → INSERT (метрики при завершении рейса)
```

#### POSTGRESQL - Таблицы для чтения (что читаем)
```sql
vehicles             → SELECT vehicle_id (при cold start)
shift_tasks          → SELECT (проверка статуса)
tasks                → SELECT (pending tasks, active task)
trips                → SELECT (проверка незавершенных рейсов)
trip_state_history   → SELECT (вычисление метрик при завершении)
trip_tag_history     → SELECT (вычисление метрик при завершении)
trip_analytics       → SELECT (получение готовых метрик для frontend/ClickHouse) ✨
```

### Входные данные от eKuiper

**Источник:** Локальный Nanomq

**Топики для подписки:**
```
/truck/${truck_id}/sensor/tag/raw       - Метки локации от graph-service
/truck/${truck_id}/sensor/speed/events  - События движения (moving/stopped)
/truck/${truck_id}/sensor/weight/events - События загрузки (loaded/empty)
/truck/${truck_id}/sensor/vibro/events  - События вибродатчика (active/inactive)
```

### Выходные данные Trip Service

**Топики для публикации в локальный Nanomq:**
```
/truck/${truck_id}/trip-service/events        - События рейсов (trip_started, trip_completed, task_activated, etc.)
/truck/${truck_id}/trip-service/state_changes - Изменения State Machine (state_transition события)
```

## State Machine в Redis

### Структура ключей Redis

**Формат ключей:**
```
trip-service:${key}
trip-service:${key}:changes - для pub/sub уведомлений
```

**Redis Pub/Sub паттерн:**

Вместо того чтобы полагаться на автоматические уведомления Redis, мы сами публикуем полное сообщение при каждом обновлении.

**Как работает:**
1. Когда обновляешь ключ: `SET trip-service:vehicle:123:state "..."`
2. Сразу делаешь: `PUBLISH trip-service:vehicle:123:state:changes '{"state": "...", "timestamp": "..."}'`
3. Подписчики получают полное значение сразу, не нужно делать дополнительный GET

**Пример обновления с PUBLISH:**
```python
# Обновляем State Machine
redis.set(
    f"trip-service:vehicle:{vehicle_id}:state",
    json.dumps(state)
)

# Публикуем изменения для подписчиков
redis.publish(
    f"trip-service:vehicle:{vehicle_id}:state:changes",
    json.dumps({
        "vehicle_id": vehicle_id,
        "state": state,
        "timestamp": time.time()
    })
)
```

**Важно:** ВСЕГДА публикуем в `:changes` топик после обновления ключа!

### Основные состояния машины

**Текущее состояние:**
```
trip-service:vehicle:${vehicle_id}:state
```

---

## Полная сводка API endpoints Trip Service

### 📋 Shift Tasks API (управление сменами)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| POST | `/api/shift-tasks` | Прием новых заданий с сервера | PostgreSQL + Redis + автовыбор активного задания |
| GET | `/api/shift-tasks` | Список всех смен | Читаем из PostgreSQL |
| GET | `/api/shift-tasks/{shift_id}` | Детали смены со всеми заданиями | PostgreSQL + Redis active_task |
| PUT | `/api/shift-tasks/{shift_id}/complete` | Завершить смену | PostgreSQL + Redis + Nanomq events |
| DELETE | `/api/shift-tasks/{shift_id}` | Отменить смену | PostgreSQL + Redis + Nanomq events |

### 📋 Tasks API (управление заданиями)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| GET | `/api/tasks` | Список заданий с фильтрацией | PostgreSQL + Redis active_task |
| GET | `/api/tasks/{task_id}` | Детали задания | PostgreSQL + trips связь |
| PUT | `/api/tasks/{task_id}/activate` | Сделать задание активным | PostgreSQL + Redis + Nanomq events |
| PUT | `/api/tasks/{task_id}/status` | Обновить статус задания | PostgreSQL + Redis + Nanomq events |
| DELETE | `/api/tasks/{task_id}` | Отменить задание | PostgreSQL + Redis + автовыбор следующего |

### 📋 Active Task API (текущее задание)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| GET | `/api/active-task` | Получить активное задание | Читаем из Redis |
| DELETE | `/api/active-task` | Очистить активное задание | Redis + PostgreSQL + Nanomq events |

### 📋 Active Trip API (текущий рейс)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| GET | `/api/active-trip` | Получить текущий рейс | Redis active_trip + state + current_tag |
| PUT | `/api/active-trip/complete` | **Завершить рейс ВРУЧНУЮ** ✨ | Логика unloading_complete + аналитика + State Machine |

### 📋 Trips API (история рейсов)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| GET | `/api/trips` | История рейсов с фильтрацией | PostgreSQL trips с пагинацией |
| GET | `/api/trips/{internal_trip_id}` | Детали рейса + история | trips + state_history + tag_history + analytics |

### 📋 State Machine API (управление состоянием)

| Метод | Endpoint | Описание | Что делает |
|-------|----------|----------|------------|
| GET | `/api/state` | Получить State Machine | Читаем из Redis полную структуру |
| PUT | `/api/state` | **Установить состояние ВРУЧНУЮ** ✨ | Redis + PostgreSQL + Nanomq + побочные эффекты |

### 🎯 Ключевые особенности API:

#### Автоматическое управление (основной режим):
- События от датчиков → State Machine → автоматические переходы
- Рейсы создаются при `loading_complete`
- Рейсы завершаются при `unloading_complete`

#### Ручное управление (резервный режим):
- ✨ `PUT /api/active-trip/complete` - вручную завершить рейс
- ✨ `PUT /api/state` - вручную изменить состояние State Machine
- Все ручные изменения логируются с `manual=True` для аудита

#### Redis Pub/Sub для всех изменений:
- Каждое изменение Redis ключа → PUBLISH в `:changes` топик
- Фронт подписывается на изменения для real-time обновлений
- Все подписчики получают полное значение без дополнительных GET

#### Побочные эффекты при ручных изменениях:
- Переход в `loading_complete` → создание рейса (автоматически)
- Переход в `unloading_complete` → завершение рейса (автоматически)
- Завершение рейса → вычисление аналитики + выбор следующего задания
- Изменение active_task → публикация в Nanomq для фронта

---

## Alembic Migrations (Управление схемой БД)

### Автоматическое применение миграций при старте

Trip Service автоматически применяет миграции базы данных при запуске через FastAPI lifespan:

```python
# app/main.py
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - автомиграции ПЕРЕД подключением к сервисам
    await run_database_migrations()

    # Инициализация сервисов...
    yield

    # Shutdown
    pass

async def run_database_migrations():
    """Автоматический запуск Alembic миграций при старте приложения"""
    try:
        logger.info("Starting database migrations")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("✅ Database migrations completed successfully")
        else:
            logger.error("❌ Migration failed", stderr=result.stderr)
            raise RuntimeError(f"Migration failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("❌ Migration timeout (>60s)")
        raise RuntimeError("Migration timeout")
    except Exception as e:
        logger.error("❌ Migration error", error=str(e))
        raise

app = FastAPI(
    title="Trip Service",
    version="1.0.0",
    lifespan=lifespan
)
```

### Структура Alembic миграций

```
trip-service/
├── alembic/
│   ├── versions/
│   │   ├── 001_initial_schema.py           # Начальная схема
│   │   ├── 002_add_trip_analytics.py       # Добавление trip_analytics
│   │   └── 003_add_manual_state_fields.py  # Поля для ручного управления
│   ├── env.py                              # Конфигурация Alembic
│   └── script.py.mako                      # Шаблон миграций
├── alembic.ini                             # Настройки Alembic
└── app/
    └── database/
        └── models.py                        # SQLAlchemy модели
```

### Пример миграции: Начальная схема

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Create Date: 2025-01-15 10:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создаем таблицу shift_tasks
    op.create_table(
        'shift_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('shift_id', sa.Text(), nullable=False),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('force', sa.Boolean(), default=False),
        sa.Column('received_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shift_id')
    )
    op.create_index(op.f('ix_shift_tasks_vehicle_id'), 'shift_tasks', ['vehicle_id', 'created_at'])
    op.create_index(op.f('ix_shift_tasks_shift_id'), 'shift_tasks', ['shift_id'])
    op.create_index(op.f('ix_shift_tasks_status'), 'shift_tasks', ['status'])

    # Создаем таблицу tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.Text(), nullable=False),
        sa.Column('shift_id', sa.Text(), nullable=False),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('start_point_id', sa.Text(), nullable=False),
        sa.Column('stop_point_id', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('internal_trip_id', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('activated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index(op.f('ix_tasks_vehicle_id'), 'tasks', ['vehicle_id', 'order'])
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'])

    # Создаем таблицу trips
    op.create_table(
        'trips',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('internal_trip_id', sa.Text(), nullable=False),
        sa.Column('server_trip_id', sa.Text(), nullable=True),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('shift_id', sa.Text(), nullable=True),
        sa.Column('trip_type', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('from_point_id', sa.Text(), nullable=True),
        sa.Column('to_point_id', sa.Text(), nullable=True),
        sa.Column('loading_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('loading_completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('unloading_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('unloading_completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('loading_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('unloading_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('travel_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internal_trip_id')
    )
    op.create_index(op.f('ix_trips_vehicle_id'), 'trips', ['vehicle_id', 'created_at'])
    op.create_index(op.f('ix_trips_server_trip_id'), 'trips', ['server_trip_id'])

    # Создаем TimescaleDB hypertable для trips (с if_not_exists для idempotent миграций)
    op.execute("""
        SELECT create_hypertable(
            'trips',
            'created_at',
            if_not_exists => TRUE
        )
    """)

    # Создаем таблицу trip_state_history
    op.create_table(
        'trip_state_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('internal_trip_id', sa.Text(), nullable=False),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('from_state', sa.Text(), nullable=True),
        sa.Column('to_state', sa.Text(), nullable=False),
        sa.Column('state_started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('state_ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('point_id', sa.Text(), nullable=True),
        sa.Column('sensors', sa.JSON(), nullable=True),
        sa.Column('manual', sa.Boolean(), default=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trip_state_history_internal_trip_id'), 'trip_state_history', ['internal_trip_id', 'state_started_at'])
    op.create_index(op.f('ix_trip_state_history_vehicle_id'), 'trip_state_history', ['vehicle_id', 'state_started_at'])
    op.create_index(op.f('ix_trip_state_history_manual'), 'trip_state_history', ['manual'], postgresql_where=sa.text('manual = TRUE'))

    # Создаем TimescaleDB hypertable для trip_state_history (с if_not_exists для idempotent миграций)
    op.execute("""
        SELECT create_hypertable(
            'trip_state_history',
            'created_at',
            if_not_exists => TRUE
        )
    """)

    # Создаем остальные таблицы (trip_tag_history, trip_analytics)...

def downgrade():
    op.drop_table('trip_state_history')
    op.drop_table('trips')
    op.drop_table('tasks')
    op.drop_table('shift_tasks')
```

### Генерация новой миграции

```bash
# Создать новую миграцию автоматически (на основе изменений моделей)
alembic revision --autogenerate -m "Add new feature"

# Создать пустую миграцию вручную
alembic revision -m "Manual migration"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Посмотреть текущую версию
alembic current

# Посмотреть историю миграций
alembic history
```

### Важные замечания:

1. **Автоматическое применение при старте** - миграции выполняются ДО инициализации любых сервисов
2. **Idempotent migrations** - миграции должны быть идемпотентными (можно запускать многократно)
3. **TimescaleDB hypertables** - создаются через `SELECT create_hypertable()` в миграциях:
   - ✅ Сначала создаем обычную таблицу через `op.create_table()`
   - ✅ Затем конвертируем в hypertable через `op.execute("SELECT create_hypertable(...)")`
   - ✅ **ОБЯЗАТЕЛЬНО используем `if_not_exists => TRUE`** для idempotent миграций
   - ✅ Временная колонка (`created_at`) должна быть уже создана в таблице
   - ⚠️ При откате (`downgrade`) просто удаляем таблицу - TimescaleDB автоматически удалит метаданные
4. **Versioning** - каждая миграция имеет уникальный revision ID
5. **Rollback support** - каждая миграция должна иметь `downgrade()` функцию

### Пример создания TimescaleDB hypertable:

```python
# ✅ Правильно
def upgrade():
    # 1. Создаем таблицу
    op.create_table('trips', ...)

    # 2. Конвертируем в hypertable с if_not_exists
    op.execute("""
        SELECT create_hypertable(
            'trips',
            'created_at',
            if_not_exists => TRUE  -- Важно для повторных запусков!
        )
    """)

def downgrade():
    # TimescaleDB автоматически удалит все метаданные при drop table
    op.drop_table('trips')

# ❌ Неправильно (без if_not_exists)
op.execute("SELECT create_hypertable('trips', 'created_at')")  # Упадет при повторном запуске!
```

---

### Принципы архитектуры State Machine

**Stateless подход для перезапуска сервиса:**
- Вся критичная информация хранится в Redis для быстрого восстановления
- При перезапуске trip-service восстанавливаем состояние из Redis и продолжаем выполнение
- Изменения состояний логируются в PostgreSQL через события в Nanomq
- Отслеживаем только значимые переходы между состояниями, не обновляем каждую секунду

### Структура ключей Redis

**Ключи для хранения состояния:**
```
trip-service:vehicle:${vehicle_id}:state          - Текущее состояние state machine
trip-service:vehicle:${vehicle_id}:active_trip    - Активный рейс (отдельный ключ!)
trip-service:vehicle:${vehicle_id}:current_tag    - Текущая метка для быстрого доступа
trip-service:vehicle:${vehicle_id}:tag_history    - Redis Stream для истории меток в рамках рейса
```

### Структура данных состояния State Machine

```json
{
  "vehicle_id": "AC9",
  "data": {
    "speed": {
      "value": 0,
      "status": "stopped",
      "timestamp": 1755500626.0
    },
    "weight": {
      "value": 45.2,
      "trend": 2.1,
      "status": "loaded",
      "timestamp": 1755500636.0
    },
    "vibro": {
      "status": "inactive",
      "delta_weight": 0.0,
      "duration": 0.0,
      "timestamp": 1755500636.0
    },
    "tag": {
      "point_id": "point_a_001",
      "point_type": "warehouse",
      "timestamp": 1755500584.0
    }
  },
  "state": {
    "current": "stopped_loaded",
    "previous": "moving_loaded",
    "loaded_at": "point_a_001",
    "unloaded_at": null,
    "current_internal_trip_id": "trip_001",
    "timestamp": 1755500636.0,
    "current_time": 1755500636.0
  }
}
```

**Пояснения к полям:**
- `timestamp` - момент начала текущего состояния
- `current_time` - текущее системное время для отслеживания актуальности
- `data.speed` - последнее событие от датчика скорости (moving/stopped)
- `data.weight` - последнее событие от датчика веса (loaded/empty)
- `data.vibro` - последнее событие от вибродатчика (active/inactive для определения загрузки/разгрузки)
- `data.tag` - последняя метка локации от graph-service
- `state.current_internal_trip_id` - ID активного рейса (null если нет рейса)
- `state.loaded_at`, `state.unloaded_at` - точки где была загрузка/разгрузка

### Структура активного рейса (отдельный ключ)

**Ключ:** `trip-service:vehicle:${vehicle_id}:active_trip`

**Назначение:** Хранит информацию о текущем активном рейсе (если машина выполняет рейс)

```json
{
  "internal_trip_id": "trip_001",
  "server_trip_id": "task_123",
  "vehicle_id": "AC9",
  "trip_type": "planned",
  "status": "in_progress",
  "from_point_id": "point_a_001",
  "to_point_id": "point_b_002",
  "started_at": 1755500000.0
}
```

**Пояснения к полям:**
- `internal_trip_id` - внутренний ID рейса Trip Service
- `server_trip_id` - ID связанного задания с сервера (task_id из таблицы tasks), если рейс плановый
- `trip_type` - тип рейса: "planned" (связан с заданием) или "unplanned" (самостоятельный)
- `from_point_id`, `to_point_id` - точки начала и окончания рейса

### Текущая метка (current_tag)

**Ключ:** `trip-service:vehicle:${vehicle_id}:current_tag`

**Назначение:**
- Быстрый доступ к текущей метке без чтения всего state
- Обновляется при каждом изменении tag из `/truck/${truck_id}/sensor/tag/raw`
- Простая логика получения для внешних сервисов

**Структура:**
```json
{
  "point_id": "point_a_001",
  "point_type": "warehouse",
  "timestamp": 1755500584.0
}
```

### Redis Stream для истории меток

**Ключ:** `trip-service:vehicle:${vehicle_id}:tag_history`

**Назначение:**
- История перемещения техники между метками в рамках активного рейса
- По завершению рейса сохраняется в PostgreSQL и очищается
- Не грузим state machine каждым изменением метки

**Логика добавления записей:**
```python
def handle_tag_event(new_tag):
    """Обработка события изменения метки"""
    current_tag = redis.get(f"trip-service:vehicle:{vehicle_id}:current_tag")
    internal_trip_id = state.current_internal_trip_id

    # Добавляем запись ТОЛЬКО если:
    # 1. Есть активный рейс (internal_trip_id не null)
    # 2. Метка изменилась (new_tag.point_id != current_tag.point_id)
    if internal_trip_id and (not current_tag or new_tag.point_id != current_tag.point_id):
        # Добавляем новую метку в stream
        redis.xadd(
            f"trip-service:vehicle:{vehicle_id}:tag_history",
            {
                "point_id": new_tag.point_id,
                "point_type": new_tag.point_type,
                "entered_at": new_tag.timestamp,
                "internal_trip_id": internal_trip_id
            }
        )

        # Обновляем current_tag
        redis.set(f"trip-service:vehicle:{vehicle_id}:current_tag", json.dumps(new_tag))
        redis.publish(
            f"trip-service:vehicle:{vehicle_id}:current_tag:changes",
            json.dumps({"vehicle_id": vehicle_id, "tag": new_tag, "timestamp": time.time()})
        )
```

**Формат записи в Stream:**
```
XADD trip-service:vehicle:{vehicle_id}:tag_history * \
  point_id "point_a_001" \
  point_type "warehouse" \
  entered_at "1755500584.0" \
  internal_trip_id "trip_001"
```

**Вычисление exited_at:**
- При добавлении СЛЕДУЮЩЕЙ метки - вычисляем `exited_at = next_tag.entered_at`
- При завершении рейса - последняя метка получает `exited_at = unloading_completed_at`

## Логика переходов State Machine

### События из Nanomq (eKuiper)

**Входные события:**
```
/truck/${truck_id}/sensor/tag/raw       → point_id, point_type
/truck/${truck_id}/sensor/speed/events  → status: "moving" | "stopped"
/truck/${truck_id}/sensor/weight/events → status: "loaded" | "empty"
/truck/${truck_id}/sensor/vibro/events  → status: "active" | "inactive"
```

**Важно:**
- Все события прилетают асинхронно с разной частотой и своими timestamp
- Машина может останавливаться, грузиться и разгружаться ВНЕ точек (метки)
- Точка (метка) - индикатор планового рейса, но не обязательное условие для перехода

### Датчик vibro для определения погрузки/разгрузки

**Принцип работы в MVP:**
- В eKuiper отслеживает изменение веса за последнюю секунду из `/truck/${truck_id}/sensor/weight/raw`
- Если `delta_weight > threshold` → публикует `status: "active"` в `/truck/${truck_id}/sensor/vibro/events`
- Если вес стабилен → публикует `status: "inactive"`

**Логика определения процесса погрузки/разгрузки:**
```
stopped + weight.empty + vibro.active   → loading (процесс загрузки начался)
stopped + weight.loaded + vibro.inactive → loading_complete (загрузка завершена)

stopped + weight.loaded + vibro.active   → unloading (процесс разгрузки начался)
stopped + weight.empty + vibro.inactive  → unloading_complete (разгрузка завершена)
```

**Структура события vibro:**
```json
{
  "metadata": {
    "vehicle_id": "AC9",
    "sensor_type": "vibro",
    "timestamp": 1755500640.0
  },
  "data": {
    "status": "active",
    "delta_weight": 2.5,
    "duration": 3.2
  }
}
```

**Примечание:** В будущем vibro будет реальным вибродатчиком, сейчас симулируется через изменение weight.

### Таблица переходов State Machine с триггерами

| Текущее состояние | Триггер (условие) | Новое состояние | Действия |
|-------------------|-------------------|-----------------|----------|
| `idle` | `speed.moving` | `moving_empty` | Обновить state, логировать, публиковать |
| `moving_empty` | `speed.stopped` | `stopped_empty` | Обновить state, логировать, публиковать |
| `stopped_empty` | `vibro.active AND weight.empty` | `loading` | Обновить state, логировать, публиковать |
| `stopped_empty` | `speed.moving` | `moving_empty` | Обновить state, логировать, публиковать |
| `loading` | `vibro.inactive AND weight.loaded` | `loading_complete` | **Создать trip**, обновить state, логировать, публиковать |
| `loading_complete` | `speed.moving` | `moving_loaded` | Обновить state, логировать, публиковать |
| `moving_loaded` | `speed.stopped` | `stopped_loaded` | Обновить state, логировать, публиковать |
| `stopped_loaded` | `vibro.active AND weight.loaded` | `unloading` | Обновить state, логировать, публиковать |
| `stopped_loaded` | `speed.moving` | `moving_loaded` | Обновить state, логировать, публиковать |
| `unloading` | `vibro.inactive AND weight.empty` | `unloading_complete` | **Завершить trip**, обновить state, логировать, публиковать |
| `unloading_complete` | `speed.moving` | `moving_empty` | Обновить state, логировать, публиковать |
| `unloading_complete` | `vibro.active AND weight.empty` | `loading` | Обновить state, логировать, публиковать (новый рейс без движения) |
| `*` (любое) | `tag изменился` | `-` (без изменения) | Обновить current_tag, добавить в tag_history (если есть рейс) |

**Обработчики событий (псевдокод):**

```python
def handle_speed_event(speed_event):
    """Обработка события изменения скорости"""
    state.data.speed = speed_event.data

    # Проверяем переходы State Machine
    if state.current == "idle" and speed_event.data.status == "moving":
        transition_to("moving_empty")
    elif state.current == "moving_empty" and speed_event.data.status == "stopped":
        transition_to("stopped_empty")
    elif state.current == "loading_complete" and speed_event.data.status == "moving":
        transition_to("moving_loaded")
    elif state.current == "moving_loaded" and speed_event.data.status == "stopped":
        transition_to("stopped_loaded")
    elif state.current == "stopped_loaded" and speed_event.data.status == "moving":
        transition_to("moving_loaded")
    elif state.current == "unloading_complete" and speed_event.data.status == "moving":
        transition_to("moving_empty")

def handle_weight_event(weight_event):
    """Обработка события изменения веса"""
    state.data.weight = weight_event.data
    # Вес используется в комбинации с vibro для определения loading/unloading

def handle_vibro_event(vibro_event):
    """Обработка события вибродатчика"""
    state.data.vibro = vibro_event.data

    # Проверяем переходы State Machine с учетом weight
    if state.current == "stopped_empty" and vibro_event.data.status == "active" and state.data.weight.status == "empty":
        transition_to("loading")
    elif state.current == "loading" and vibro_event.data.status == "inactive" and state.data.weight.status == "loaded":
        transition_to("loading_complete")
        create_trip()  # СОЗДАЕМ РЕЙС
    elif state.current == "stopped_loaded" and vibro_event.data.status == "active" and state.data.weight.status == "loaded":
        transition_to("unloading")
    elif state.current == "unloading" and vibro_event.data.status == "inactive" and state.data.weight.status == "empty":
        transition_to("unloading_complete")
        complete_trip()  # ЗАВЕРШАЕМ РЕЙС
    elif state.current == "unloading_complete" and vibro_event.data.status == "active" and state.data.weight.status == "empty":
        transition_to("loading")  # Новый рейс без движения

def handle_tag_event(tag_event):
    """Обработка события изменения метки - см. выше"""
    # Обновляем current_tag и добавляем в tag_history если есть активный рейс
    pass

def transition_to(new_state):
    """Переход в новое состояние"""
    old_state = state.current
    state.previous = old_state
    state.current = new_state
    state.timestamp = time.time()

    # Сохраняем в Redis
    redis.set(f"trip-service:vehicle:{vehicle_id}:state", json.dumps(state))

    # Публикуем в Redis Pub/Sub
    redis.publish(
        f"trip-service:vehicle:{vehicle_id}:state:changes",
        json.dumps({"vehicle_id": vehicle_id, "state": state, "timestamp": time.time()})
    )

    # Публикуем в Nanomq для фронта
    publish_to_nanomq(
        topic=f"/truck/{truck_id}/trip-service/state_changes",
        event={
            "event_type": "state_transition",
            "vehicle_id": vehicle_id,
            "from_state": old_state,
            "to_state": new_state,
            "internal_trip_id": state.current_internal_trip_id,
            "current_tag": state.data.tag,
            "timestamp": time.time()
        }
    )

    # Логируем в PostgreSQL trip_state_history
    insert_state_history(
        internal_trip_id=state.current_internal_trip_id,
        from_state=old_state,
        to_state=new_state,
        state_started_at=state.timestamp,
        point_id=state.data.tag.point_id if state.data.tag else None,
        sensors={
            "speed": state.data.speed,
            "weight": state.data.weight,
            "vibro": state.data.vibro
        }
    )
```

### Состояния State Machine

**Линейная последовательность:**
1. `idle` - Простой (stopped + empty + no_active_trip)
2. `moving_empty` - Движение без груза (moving + empty)
3. `stopped_empty` - Остановка без груза (stopped + empty)
4. `loading` - Процесс загрузки (stopped + weight.empty + vibro.active)
5. `loading_complete` - Загрузка завершена (stopped + weight.loaded + vibro.inactive)
6. `moving_loaded` - Движение с грузом (moving + loaded)
7. `stopped_loaded` - Остановка с грузом (stopped + loaded)
8. `unloading` - Процесс разгрузки (stopped + weight.loaded + vibro.active)
9. `unloading_complete` - Разгрузка завершена (stopped + weight.empty + vibro.inactive)

**Альтернативные переходы (циклы):**
- `stopped_empty` → `moving_empty` (без загрузки, продолжил движение)
- `stopped_loaded` → `moving_loaded` (без разгрузки, продолжил движение)

### Сообщения Nanomq для каждого перехода

**Формат сообщений в `/truck/${truck_id}/trip-service/events`:**

```json
{
  "event_type": "state_transition",
  "vehicle_id": "AC9",
  "from_state": "moving_loaded",
  "to_state": "stopped_loaded",
  "timestamp": 1755500636.0,
  "trip_id": "trip_001",
  "point_id": "point_b_002",
  "sensors": {
    "speed": {"status": "stopped"},
    "weight": {"status": "loaded"},
    "tag": {"point_id": "point_b_002", "point_type": "warehouse"}
  }
}
```

**Список publish событий для фронтенда:**
1. `state_transition: idle` - Переход в простой
2. `state_transition: moving_empty` - Движение без груза
3. `state_transition: stopped_empty` - Остановка без груза
4. `state_transition: loading` - Начало загрузки
5. `state_transition: loading_complete` - Загрузка завершена (+ создание trip)
6. `state_transition: moving_loaded` - Движение с грузом
7. `state_transition: stopped_loaded` - Остановка с грузом
8. `state_transition: unloading` - Начало разгрузки
9. `state_transition: unloading_complete` - Разгрузка завершена (+ завершение trip)
10. `trip_started: ${internal_trip_id}` - Рейс создан
11. `trip_completed: ${internal_trip_id}` - Рейс завершен
12. `task_activated: ${task_id}` - Задание активировано
13. `task_cancelled: ${task_id}` - Задание отменено
14. `shift_task_received: ${shift_id}` - Получен shift_task с сервера
15. `shift_task_completed: ${shift_id}` - Shift task завершен
16. `shift_task_cancelled: ${shift_id}` - Shift task отменен

**Назначение:**
- События публикуются в `/truck/${truck_id}/trip-service/events` для событий рейсов
- Изменения State Machine публикуются в `/truck/${truck_id}/trip-service/state_changes`
- Фронт отображает текущее состояние машины в реальном времени
- Trip Service не читает эти события обратно, только публикует

**Публикация изменений State Machine:**
```python
# При каждом переходе состояния публикуем в 2 места:

# 1. В Redis Pub/Sub
redis.set(f"trip-service:vehicle:{vehicle_id}:state", json.dumps(state))
redis.publish(
    f"trip-service:vehicle:{vehicle_id}:state:changes",
    json.dumps({"vehicle_id": vehicle_id, "state": state, "timestamp": time.time()})
)

# 2. В Nanomq для фронтенда
publish_to_nanomq(
    topic=f"/truck/{truck_id}/trip-service/state_changes",
    event={
        "event_type": "state_transition",
        "vehicle_id": vehicle_id,
        "from_state": old_state,
        "to_state": new_state,
        "internal_trip_id": state.current_internal_trip_id,
        "current_tag": current_tag,
        "timestamp": time.time()
    }
)
```

### Логика записи в PostgreSQL

**Когда пишем в PostgreSQL:**
- При каждом переходе состояния → запись в таблицу `trip_state_history`
- При завершении рейса → обновление таблицы `trips` и сохранение `trip_tag_history`

**Примечание:** Таблица `trip_state_history` описана в разделе "Интеграция с базами данных"

## Логика управления рейсами

### Создание рейса

**Условие:** При переходе в состояние `loading_complete`

**Принцип internal_trip_id:**
- Trip Service всегда создает свой внутренний `internal_trip_id` для каждой поездки
- Связь с заданием (`server_trip_id = task_id`) создается ПРЕДВАРИТЕЛЬНО при загрузке на точке задания
- **НО окончательный тип рейса определяется только при завершении!**
- Если разгрузка НЕ на плановой точке → рейс становится "unplanned" и связь разрывается

**Логика:**
```python
if state.current == "loading_complete":
    # ВСЕГДА создаем внутренний ID
    internal_trip_id = generate_uuid()
    current_time = time.time()

    # Проверяем, есть ли активное задание (task)
    active_task = redis.get("trip-service:vehicle:${vehicle_id}:active_task")
    current_tag = redis.get("trip-service:vehicle:${vehicle_id}:current_tag")

    # Временные метки: когда началась загрузка (переход в 'loading') и когда завершилась
    # Используем timestamp перехода в 'loading' и текущее время для 'loading_complete'
    loading_started_at = state.data.vibro.timestamp  # когда vibro стал active (начало загрузки)
    loading_completed_at = current_time

    if active_task and current_tag and current_tag.point_id == active_task.start_point_id:
        # ПРЕДВАРИТЕЛЬНО считаем рейс плановым (загрузка на правильной точке)
        # ОКОНЧАТЕЛЬНЫЙ тип определится при разгрузке!
        trip_type = "planned"
        server_trip_id = active_task.task_id  # Временная связь с заданием
        shift_id = active_task.shift_id

        # Обновляем задание - помечаем что рейс начался
        update_task(
            task_id=active_task.task_id,
            status='in_progress',
            internal_trip_id=internal_trip_id,
            started_at=current_time
        )
    else:
        # Внеплановый рейс (загрузка не на точке задания)
        trip_type = "unplanned"
        server_trip_id = None
        shift_id = None

    # Создаем trip в PostgreSQL с internal_trip_id и временными метками
    create_trip(
        internal_trip_id=internal_trip_id,
        server_trip_id=server_trip_id,
        trip_type=trip_type,
        vehicle_id=vehicle_id,
        shift_id=shift_id,
        from_point_id=current_tag.point_id if current_tag else None,
        loading_started_at=loading_started_at,
        loading_completed_at=loading_completed_at,
        status='in_progress'
    )

    # Сохраняем internal_trip_id в state machine
    state.current_internal_trip_id = internal_trip_id
    redis.set(f"trip-service:vehicle:{vehicle_id}:state", json.dumps(state))
    redis.publish(
        f"trip-service:vehicle:{vehicle_id}:state:changes",
        json.dumps({"vehicle_id": vehicle_id, "state": state, "timestamp": current_time})
    )

    # Публикуем событие в Nanomq для фронтенда
    publish_to_nanomq(
        topic=f"/truck/{truck_id}/trip-service/events",
        event={
            "event_type": "trip_started",
            "internal_trip_id": internal_trip_id,
            "server_trip_id": server_trip_id,
            "trip_type": trip_type,
            "vehicle_id": vehicle_id,
            "from_point_id": current_tag.point_id if current_tag else None,
            "timestamp": current_time
        }
    )

    # TODO: Таймаут на loading - не более 3 минут
    # Если loading длится > 3 минут → алерт или возврат в stopped_empty
```

### Завершение рейса

**Условие:** При переходе в состояние `unloading_complete`

**Логика:**
```python
if state.current == "unloading_complete":
    # Завершаем текущий рейс
    internal_trip_id = state.current_internal_trip_id
    current_tag = redis.get("trip-service:vehicle:${vehicle_id}:current_tag")
    current_time = time.time()

    # Временные метки: когда началась разгрузка (переход в 'unloading') и когда завершилась
    # Используем timestamp когда vibro стал active (начало разгрузки) и текущее время
    unloading_started_at = state.data.vibro.timestamp  # когда vibro стал active (начало разгрузки)
    unloading_completed_at = current_time

    # Получаем данные рейса для проверки
    trip = await get_trip(internal_trip_id)

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если это был "плановый" рейс, но разгрузка НЕ в плановой точке
    # → Переводим рейс в "unplanned" и разрываем связь с заданием!
    final_trip_type = trip.trip_type  # изначально "planned" или "unplanned"
    final_server_trip_id = trip.server_trip_id
    task_status = None  # Статус задания: completed, cancelled или None

    if trip.server_trip_id:  # Если рейс был предварительно связан с заданием
        # Получаем задание чтобы узнать плановую точку разгрузки
        task = await get_task(trip.server_trip_id)

        if current_tag and current_tag.point_id == task.stop_point_id:
            # ✅ Разгрузка в плановой точке → рейс остается "planned"
            final_trip_type = "planned"
            final_server_trip_id = trip.server_trip_id
            task_status = "completed"  # Задание выполнено успешно
        else:
            # ❌ Разгрузка НЕ в плановой точке → рейс становится "unplanned"
            final_trip_type = "unplanned"
            final_server_trip_id = None  # Разрываем связь с заданием!
            task_status = "cancelled"  # Задание НЕ выполнено (машина разгрузилась не там)

    # Обновляем рейс в PostgreSQL с окончательным типом
    complete_trip(
        internal_trip_id=internal_trip_id,
        to_point_id=current_tag.point_id if current_tag else None,
        unloading_started_at=unloading_started_at,
        unloading_completed_at=unloading_completed_at,
        status='completed',
        trip_type=final_trip_type,  # Окончательный тип рейса!
        server_trip_id=final_server_trip_id  # Может быть null если стал unplanned
    )

    # Обновляем задание если оно было связано
    if trip.server_trip_id and task_status:
        update_task(
            task_id=trip.server_trip_id,
            status=task_status,  # completed или cancelled
            completed_at=current_time if task_status == 'completed' else None,
            cancelled_at=current_time if task_status == 'cancelled' else None,
            internal_trip_id=None if task_status == 'cancelled' else internal_trip_id  # Разрываем связь если отменено
        )

    # Сохраняем tag_history в PostgreSQL
    save_tag_history(internal_trip_id)

    # Вычисляем и сохраняем аналитику рейса
    await finalize_trip_analytics(internal_trip_id)

    # Очищаем tag_history stream
    redis.delete(f"trip-service:vehicle:{vehicle_id}:tag_history")
    redis.publish(
        f"trip-service:vehicle:{vehicle_id}:tag_history:changes",
        json.dumps({"internal_trip_id": internal_trip_id, "action": "cleared", "timestamp": current_time})
    )

    # Публикуем событие в Nanomq для фронтенда
    publish_to_nanomq(
        topic=f"/truck/{truck_id}/trip-service/events",
        event={
            "event_type": "trip_completed",
            "internal_trip_id": internal_trip_id,
            "server_trip_id": trip.server_trip_id,
            "trip_type": trip.trip_type,
            "vehicle_id": vehicle_id,
            "to_point_id": current_tag.point_id if current_tag else None,
            "timestamp": current_time
        }
    )

    # Выбираем следующее активное задание
    next_task = await select_next_task(current_tag)

    if next_task:
        # Делаем следующее задание активным
        redis.set(f"trip-service:vehicle:{vehicle_id}:active_task", json.dumps(next_task))
        redis.publish(
            f"trip-service:vehicle:{vehicle_id}:active_task:changes",
            json.dumps({"vehicle_id": vehicle_id, "task": next_task, "timestamp": current_time})
        )

        # Обновляем задание в БД
        update_task(task_id=next_task.task_id, status='active', activated_at=current_time)

        # Публикуем событие активации задания
        publish_to_nanomq(
            topic=f"/truck/{truck_id}/trip-service/events",
            event={
                "event_type": "task_activated",
                "task_id": next_task.task_id,
                "vehicle_id": vehicle_id,
                "timestamp": current_time
            }
        )
    else:
        # Нет заданий - очищаем активное задание
        redis.delete(f"trip-service:vehicle:{vehicle_id}:active_task")
        redis.publish(
            f"trip-service:vehicle:{vehicle_id}:active_task:changes",
            json.dumps({"vehicle_id": vehicle_id, "task": None, "timestamp": current_time})
        )

    # TODO: Таймаут на unloading - не более 3 минут
    # Если unloading длится > 3 минут → алерт или возврат в stopped_loaded
```

### Выбор следующего активного задания после разгрузки

**Условие:** При переходе в `unloading_complete`

**Логика выбора:**
```python
async def select_next_task(current_tag):
    """
    Выбираем следующее активное задание с учетом текущей точки

    Стратегия:
    - Приоритет #1: Первое задание по order
    - Оптимизация: Если первое по order не на текущей точке, ищем задание из текущей точки
    - Цель: Минимизировать холостые пробеги, но сохранять порядок выполнения
    """

    # 1. Берем первое задание по порядку из общей очереди
    first_task_by_order = redis.zrange("trip-service:task_queue:ordered", 0, 0)

    if not first_task_by_order:
        # Нет заданий вообще
        return None

    first_task = await get_task_from_db(first_task_by_order[0])

    # 2. Проверяем, совпадает ли start_point с текущей точкой
    if current_tag and current_tag.point_id == first_task.start_point_id:
        # Оптимально - берем первое по порядку
        return first_task

    # 3. Ищем задание, которое стартует с текущей точки
    if current_tag and current_tag.point_id:
        tasks_from_current_point = redis.zrange(
            f"trip-service:task_queue:{current_tag.point_id}",
            0, -1  # Все задания из этой точки
        )

        if tasks_from_current_point:
            # Берем первое задание из текущей точки (по order)
            return await get_task_from_db(tasks_from_current_point[0])

    # 4. Нет заданий из текущей точки или current_tag = null
    # Берем первое по порядку (может потребовать холостого пробега)
    return first_task

# Применение логики
next_task = await select_next_task(current_tag)

if next_task:
    redis.set("trip-service:vehicle:${vehicle_id}:active_task", next_task)
else:
    # Нет заданий - переходим в idle
    redis.delete("trip-service:vehicle:${vehicle_id}:active_task")
    state.current = "idle"
```

**Преимущества подхода:**
- Исключаем проблемы с холостыми пробегами там, где можем
- Если задание из текущей точки - берем его
- Если нет - все равно берем задание по порядку (пусть и потребует пробег)
- Поддерживаем `current_tag = null` (вне точки)

## Типы рейсов и логика определения

### Плановый рейс (Planned Trip)

**Условия:**
- Получен с сервера через API
- Имеет определенные точки: `from_point` и `to_point`
- Пользователь стремится выполнить активное задание

**Определение планового рейса:**
```
1. Есть активный плановый рейс в Redis: trip-service:vehicle:${vehicle_id}:active_trip
2. Загрузка происходит на точке from_point (tag.point_id == active_trip.from_point)
3. Разгрузка происходит на точке to_point (tag.point_id == active_trip.to_point)
```

**Сценарии отклонения от плана:**
- Пользователь может поменять активное задание из интерфейса
- Активные задания могут иссякнуть (очередь пустая)
- Погрузился на точке задания, но повез в другое место → внеплановый рейс

### Внеплановый рейс (Unplanned Trip)

**Условия возникновения:**
1. Нет активного планового рейса в системе
2. Загрузка/разгрузка происходит НЕ на точках планового рейса
3. Машина загрузилась вне точки (no tag)
4. Машина загрузилась на правильной точке, но разгрузилась в другом месте

**Определение внепланового рейса:**
```
Начало:
  loading_complete + (no_active_trip OR tag.point_id != active_trip.from_point)

Завершение:
  unloading_complete + (no_active_trip OR tag.point_id != active_trip.to_point)
```

**Фиксация:**
- Автоматически обнаруживается по логике изменения состояний
- Сохраняется в PostgreSQL для анализа и отчетности
- Отправляется на сервер для синхронизации (опционально)

### Логика работы с точками (метками)

**Точка присутствует (tag.point_id):**
- Индикатор, что машина находится на известной локации
- Повышает вероятность планового рейса
- Используется для связывания рейса с плановым заданием

**Точка отсутствует (no tag):**
- Машина вне зоны известных точек
- Автоматически классифицируется как внеплановый рейс
- Все равно фиксируется для анализа

**Важно:** Отслеживаем ВСЕ возможные рейсы независимо от наличия точек!

## Работа с новыми списками рейсов от сервера (Cold Start)

### Прием shift_task от сервера

**Endpoint:** `POST /api/shift-tasks`

**Формат запроса:**
```json
{
  "shift_id": "550e8400-e29b-41d4-a716-446655440000",
  "tasks": [
    {
      "task_id": "task_004",
      "start_point_id": "excavator_001",
      "stop_point_id": "warehouse_A",
      "order": 1,
      "metadata": {
        "cargo_type": "ore",
        "expected_weight": 45.0
      }
    },
    {
      "task_id": "task_005",
      "start_point_id": "warehouse_A",
      "stop_point_id": "excavator_001",
      "order": 2,
      "metadata": {
        "cargo_type": "empty_return"
      }
    }
  ],
  "server_timestamp": "2024-01-15T10:00:00Z",
  "force": false
}
```

### Логика обработки нового shift_task

```python
async def handle_new_shift_task(shift_task_data):
    """
    Обрабатываем новый shift_task с сервера
    """

    # 1. Проверяем force flag
    if shift_task_data.force:
        # Отменяем ВСЕ старые задания включая активное
        await cancel_all_tasks(vehicle_id)
        redis.delete(f"trip-service:vehicle:{vehicle_id}:active_task")
    else:
        # Отменяем только старые pending задания, кроме активного
        current_active = redis.get(f"trip-service:vehicle:{vehicle_id}:active_task")
        await cancel_tasks_except_active(vehicle_id, current_active)

    # 2. Вставляем shift_task в PostgreSQL
    await db.execute("""
        INSERT INTO shift_tasks (shift_id, vehicle_id, server_timestamp, force)
        VALUES (:shift_id, :vehicle_id, :server_timestamp, :force)
    """, shift_task_data)

    # 3. Вставляем все tasks в PostgreSQL
    for task in shift_task_data.tasks:
        await db.execute("""
            INSERT INTO tasks
            (task_id, shift_id, vehicle_id, start_point_id, stop_point_id, "order", metadata, status)
            VALUES (:task_id, :shift_id, :vehicle_id, :start_point_id, :stop_point_id, :order, :metadata, 'pending')
        """, task)

    # 4. Загружаем задания в Redis Sorted Sets
    for task in shift_task_data.tasks:
        # Общая очередь по order
        redis.zadd("trip-service:task_queue:ordered", {task.task_id: task.order})

        # Очередь по start_point_id
        redis.zadd(
            f"trip-service:task_queue:{task.start_point_id}",
            {task.task_id: task.order}
        )

    # 5. Публикуем событие о новых заданиях
    await publish_event("shift_task_received", shift_task_data.shift_id)

    # 6. Устанавливаем активное задание, если его нет
    current_active = redis.get(f"trip-service:vehicle:{vehicle_id}:active_task")
    if not current_active:
        current_tag = redis.get(f"trip-service:vehicle:{vehicle_id}:current_tag")
        next_task = await select_next_task(current_tag)
        if next_task:
            await set_active_task(next_task)
```

### API Endpoint для приема shift_task

**Endpoint:** `POST /api/shift-tasks`

**Request Schema:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TaskMetadata(BaseModel):
    cargo_type: Optional[str] = None
    expected_weight: Optional[float] = None  # Ожидаемый вес груза (тонны)
    # Дополнительные метаданные

class TaskCreate(BaseModel):
    task_id: str = Field(..., description="Уникальный ID задания с сервера")
    start_point_id: str = Field(..., description="Точка погрузки")
    stop_point_id: str = Field(..., description="Точка разгрузки")
    order: int = Field(..., description="Порядок выполнения задания")
    metadata: Optional[TaskMetadata] = None

class ShiftTaskCreate(BaseModel):
    shift_id: str = Field(..., description="Уникальный ID смены")
    tasks: List[TaskCreate] = Field(..., min_items=1, description="Список заданий")
    server_timestamp: datetime = Field(..., description="Временная метка с сервера")
    force: bool = Field(default=False, description="Отменить все задания включая активное")

# Response Schema
class ShiftTaskResponse(BaseModel):
    shift_id: str
    status: str  # 'active', 'completed', 'cancelled'
    tasks_count: int
    active_task_id: Optional[str]
    message: str
```

**API Implementation:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/shift-tasks", tags=["shift-tasks"])

@router.post("", response_model=ShiftTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_shift_task(
    shift_task_data: ShiftTaskCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Прием нового shift_task с сервера

    Логика:
    - force=false: отменяем старые pending задания, кроме активного
    - force=true: отменяем ВСЕ задания включая активное
    - Загружаем новые задания в PostgreSQL и Redis
    - Автоматически выбираем активное задание если его нет
    """

    # Получаем vehicle_id из конфигурации
    vehicle_id = await get_vehicle_id_from_config(db)

    logger.info(
        "Received new shift_task",
        shift_id=shift_task_data.shift_id,
        tasks_count=len(shift_task_data.tasks),
        force=shift_task_data.force
    )

    try:
        # ============================================================
        # Шаг 1: Обработка force flag
        # ============================================================
        if shift_task_data.force:
            # Отменяем ВСЕ старые задания включая активное
            await db.execute("""
                UPDATE tasks
                SET status = 'cancelled', cancelled_at = NOW()
                WHERE vehicle_id = :vehicle_id
                  AND status IN ('pending', 'active', 'in_progress')
            """, {"vehicle_id": vehicle_id})

            # Очищаем активное задание из Redis
            redis.delete(f"trip-service:vehicle:{vehicle_id}:active_task")

            logger.warning(
                "Force flag: all tasks cancelled",
                vehicle_id=vehicle_id
            )
        else:
            # Отменяем только pending задания, кроме активного
            active_task = redis.get(f"trip-service:vehicle:{vehicle_id}:active_task")

            if active_task:
                await db.execute("""
                    UPDATE tasks
                    SET status = 'cancelled', cancelled_at = NOW()
                    WHERE vehicle_id = :vehicle_id
                      AND status = 'pending'
                      AND task_id != :active_task_id
                """, {
                    "vehicle_id": vehicle_id,
                    "active_task_id": active_task["task_id"]
                })

                logger.info(
                    "Pending tasks cancelled except active",
                    active_task_id=active_task["task_id"]
                )
            else:
                await db.execute("""
                    UPDATE tasks
                    SET status = 'cancelled', cancelled_at = NOW()
                    WHERE vehicle_id = :vehicle_id
                      AND status = 'pending'
                """, {"vehicle_id": vehicle_id})

                logger.info("All pending tasks cancelled")

        # ============================================================
        # Шаг 2: Вставляем shift_task в PostgreSQL
        # ============================================================
        await db.execute("""
            INSERT INTO shift_tasks (
                shift_id, vehicle_id, server_timestamp,
                status, force, received_at
            )
            VALUES (:shift_id, :vehicle_id, :server_timestamp, 'active', :force, NOW())
        """, {
            "shift_id": shift_task_data.shift_id,
            "vehicle_id": vehicle_id,
            "server_timestamp": shift_task_data.server_timestamp,
            "force": shift_task_data.force
        })

        # ============================================================
        # Шаг 3: Вставляем все tasks в PostgreSQL
        # ============================================================
        for task in shift_task_data.tasks:
            await db.execute("""
                INSERT INTO tasks (
                    task_id, shift_id, vehicle_id,
                    start_point_id, stop_point_id,
                    "order", metadata, status, assigned_at
                )
                VALUES (
                    :task_id, :shift_id, :vehicle_id,
                    :start_point_id, :stop_point_id,
                    :order, :metadata, 'pending', NOW()
                )
            """, {
                "task_id": task.task_id,
                "shift_id": shift_task_data.shift_id,
                "vehicle_id": vehicle_id,
                "start_point_id": task.start_point_id,
                "stop_point_id": task.stop_point_id,
                "order": task.order,
                "metadata": task.metadata.model_dump() if task.metadata else None
            })

        await db.commit()

        # ============================================================
        # Шаг 4: Загружаем задания в Redis Sorted Sets
        # ============================================================
        # Очищаем старые очереди
        redis.delete("trip-service:task_queue:ordered")
        for key in redis.scan_iter("trip-service:task_queue:*"):
            redis.delete(key)

        # Загружаем новые задания
        for task in shift_task_data.tasks:
            # Общая очередь по order
            redis.zadd(
                "trip-service:task_queue:ordered",
                {task.task_id: task.order}
            )

            # Очередь по start_point_id
            redis.zadd(
                f"trip-service:task_queue:{task.start_point_id}",
                {task.task_id: task.order}
            )

        logger.info(
            "Tasks loaded to Redis",
            count=len(shift_task_data.tasks)
        )

        # ============================================================
        # Шаг 5: Публикуем событие о новых заданиях в Nanomq
        # ============================================================
        await mqtt_client.publish(
            f"/truck/{truck_id}/trip-service/events",
            json.dumps({
                "event_type": "shift_task_received",
                "shift_id": shift_task_data.shift_id,
                "tasks_count": len(shift_task_data.tasks),
                "timestamp": time.time()
            })
        )

        # Публикуем в Redis для фронта
        redis.publish(
            "trip-service:shift_task_changes",
            json.dumps({
                "shift_id": shift_task_data.shift_id,
                "tasks_count": len(shift_task_data.tasks)
            })
        )

        # ============================================================
        # Шаг 6: Устанавливаем активное задание, если его нет
        # ============================================================
        active_task = redis.get(f"trip-service:vehicle:{vehicle_id}:active_task")

        if not active_task:
            current_tag = redis.get(f"trip-service:vehicle:{vehicle_id}:current_tag")
            next_task = await select_next_task(current_tag, db)

            if next_task:
                await set_active_task(next_task, vehicle_id, db)
                active_task_id = next_task.task_id

                logger.info(
                    "Active task set automatically",
                    task_id=active_task_id
                )
            else:
                active_task_id = None
        else:
            active_task_id = active_task["task_id"]

        # ============================================================
        # Шаг 7: Возвращаем результат
        # ============================================================
        return ShiftTaskResponse(
            shift_id=shift_task_data.shift_id,
            status="active",
            tasks_count=len(shift_task_data.tasks),
            active_task_id=active_task_id,
            message=f"Shift task received, {len(shift_task_data.tasks)} tasks loaded"
        )

    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to process shift_task",
            shift_id=shift_task_data.shift_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process shift task: {str(e)}"
        )
```

**Установка ключей в Redis при получении shift_task:**
```
# Очереди заданий (Sorted Sets)
ZADD trip-service:task_queue:ordered → все tasks по order
ZADD trip-service:task_queue:{point_id} → tasks по start_point_id

# Публикация событий
PUBLISH trip-service:shift_task_changes → уведомление для фронта
MQTT PUBLISH /truck/${truck_id}/trip-service/events → событие для системы
```

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/api/shift-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "shift_id": "550e8400-e29b-41d4-a716-446655440000",
    "tasks": [
      {
        "task_id": "task_001",
        "start_point_id": "excavator_001",
        "stop_point_id": "warehouse_A",
        "order": 1,
        "metadata": {
          "cargo_type": "ore",
          "expected_weight": 45.0
        }
      },
      {
        "task_id": "task_002",
        "start_point_id": "warehouse_A",
        "stop_point_id": "excavator_001",
        "order": 2
      }
    ],
    "server_timestamp": "2024-01-15T10:00:00Z",
    "force": false
  }'
```

**Пример ответа:**
```json
{
  "shift_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "tasks_count": 2,
  "active_task_id": "task_001",
  "message": "Shift task received, 2 tasks loaded"
}
```

## Обработка edge cases и ошибок

### Пропущенные события

**Проблема:** События не приходили какое-то время, потом резко оказались в "около конечном" состоянии

**Решение:**
```python
def handle_state_transition(new_event):
    current_state = redis.get("trip-service:vehicle:${vehicle_id}:state")

    # Не бояться резких переходов состояний
    # Просто обновляем состояние на основе текущих данных

    if new_event.type == "speed" and new_event.status == "stopped":
        if current_state.data.weight.status == "loaded":
            # Резко оказались в stopped_loaded
            transition_to("stopped_loaded", from_state=current_state.current)
        else:
            # Резко оказались в stopped_empty
            transition_to("stopped_empty", from_state=current_state.current)

    # Всегда обновляем данные сенсоров в state
    current_state.data[new_event.type] = new_event.data
    redis.set("trip-service:vehicle:${vehicle_id}:state", current_state)
```

**Принцип:** State Machine должна быть готова к любым переходам и восстанавливать корректное состояние

### Таймауты состояний

**Loading timeout (TODO):**
```python
# Если loading длится > 3 минут
if state.current == "loading" and (now() - state.timestamp) > 180:
    logger.warning("Loading timeout exceeded", vehicle_id=vehicle_id)
    # Опции:
    # 1. Отправить алерт
    # 2. Вернуться в stopped_empty
    # 3. Создать событие "loading_timeout"
```

**Unloading timeout (TODO):**
```python
# Если unloading длится > 3 минут
if state.current == "unloading" and (now() - state.timestamp) > 180:
    logger.warning("Unloading timeout exceeded", vehicle_id=vehicle_id)
    # Опции:
    # 1. Отправить алерт
    # 2. Вернуться в stopped_loaded
    # 3. Создать событие "unloading_timeout"
```

### Холодный старт Trip Service (восстановление после перезапуска)

**Цель:** Восстановить полное состояние работы без потери данных и контекста

**Redis Persistence:**
- Redis настроен на **AOF (Append Only File)** для сохранения данных на диск
- Redis Streams сохраняются на диск и восстанавливаются при перезапуске
- Конфигурация Redis: `appendonly yes`, `appendfsync everysec`

**Последовательность действий при старте:**

```python
async def cold_start_trip_service():
    """
    Полное восстановление состояния Trip Service при холодном старте
    """

    # ============================================================
    # Шаг 1: Получить vehicle_id из PostgreSQL
    # ============================================================
    vehicle_id = await db.fetch_one("""
        SELECT vehicle_id FROM vehicles
        WHERE vehicle_type = 'mining_truck'
        LIMIT 1
    """)

    if not vehicle_id:
        raise ValueError("No vehicle_id found in database")

    logger.info("Cold start initiated", vehicle_id=vehicle_id)

    # ============================================================
    # Шаг 2: Восстановить State Machine из Redis
    # ============================================================
    state = redis.get(f"trip-service:vehicle:{vehicle_id}:state")

    if not state:
        # Первый запуск или Redis очистился - создаем начальное состояние
        state = {
            "vehicle_id": vehicle_id,
            "data": {
                "speed": None,
                "weight": None,
                "tag": None
            },
            "state": {
                "current": "idle",
                "previous": None,
                "loaded_at": None,
                "unloaded_at": None,
                "timestamp": time.time(),
                "current_time": time.time()
            }
        }
        redis.set(
            f"trip-service:vehicle:{vehicle_id}:state",
            json.dumps(state)
        )
        logger.info("State Machine initialized", state="idle")
    else:
        logger.info(
            "State Machine restored from Redis",
            current_state=state["state"]["current"]
        )

    # ============================================================
    # Шаг 3: Восстановить активный рейс из Redis
    # ============================================================
    active_trip = redis.get(f"trip-service:vehicle:{vehicle_id}:active_trip")

    if active_trip:
        # Проверяем статус рейса в PostgreSQL
        trip_in_db = await db.fetch_one("""
            SELECT * FROM trips
            WHERE internal_trip_id = :trip_id
        """, {"trip_id": active_trip["internal_trip_id"]})

        if not trip_in_db or trip_in_db.status == "completed":
            # Рейс завершен, но не очищен из Redis
            redis.delete(f"trip-service:vehicle:{vehicle_id}:active_trip")
            active_trip = None
            logger.warning("Active trip was completed, cleared from Redis")
        else:
            logger.info(
                "Active trip restored",
                internal_trip_id=active_trip["internal_trip_id"]
            )

    # Проверяем наличие незавершенного рейса в PostgreSQL
    if not active_trip:
        incomplete_trip = await db.fetch_one("""
            SELECT * FROM trips
            WHERE vehicle_id = :vehicle_id
              AND status = 'in_progress'
            ORDER BY created_at DESC
            LIMIT 1
        """, {"vehicle_id": vehicle_id})

        if incomplete_trip:
            # Есть незавершенный рейс в БД, но нет в Redis - восстанавливаем
            active_trip = {
                "internal_trip_id": incomplete_trip.internal_trip_id,
                "server_trip_id": incomplete_trip.server_trip_id,
                "vehicle_id": incomplete_trip.vehicle_id,
                "trip_type": incomplete_trip.trip_type,
                "status": incomplete_trip.status,
                "from_point_id": incomplete_trip.from_point_id,
                "to_point_id": incomplete_trip.to_point_id,
                "started_at": incomplete_trip.loading_completed_at.timestamp()
            }
            redis.set(
                f"trip-service:vehicle:{vehicle_id}:active_trip",
                json.dumps(active_trip)
            )
            redis.publish(
                f"trip-service:vehicle:{vehicle_id}:active_trip:changes",
                json.dumps({"vehicle_id": vehicle_id, "trip": active_trip, "timestamp": time.time()})
            )
            logger.info(
                "Active trip restored from PostgreSQL",
                internal_trip_id=incomplete_trip.internal_trip_id
            )

    # ============================================================
    # Шаг 4: Восстановить текущую метку из Redis
    # ============================================================
    current_tag = redis.get(f"trip-service:vehicle:{vehicle_id}:current_tag")

    if current_tag:
        logger.info(
            "Current tag restored",
            point_id=current_tag["point_id"]
        )
    else:
        logger.info("No current tag, waiting for eKuiper events")

    # ============================================================
    # Шаг 5: Загрузить активные задания из PostgreSQL в Redis Sorted Sets
    # ============================================================
    pending_tasks = await db.fetch_all("""
        SELECT task_id, start_point_id, "order"
        FROM tasks
        WHERE vehicle_id = :vehicle_id
          AND status = 'pending'
        ORDER BY "order" ASC
    """, {"vehicle_id": vehicle_id})

    # Очищаем старые очереди в Redis
    redis.delete("trip-service:task_queue:ordered")
    for key in redis.scan_iter("trip-service:task_queue:*"):
        redis.delete(key)

    # Загружаем в Redis Sorted Sets
    for task in pending_tasks:
        # Общая очередь по order
        redis.zadd(
            "trip-service:task_queue:ordered",
            {task.task_id: task.order}
        )

        # Очередь по start_point_id
        redis.zadd(
            f"trip-service:task_queue:{task.start_point_id}",
            {task.task_id: task.order}
        )

    logger.info(
        "Pending tasks loaded to Redis",
        count=len(pending_tasks)
    )

    # ============================================================
    # Шаг 6: Восстановить активное задание из Redis
    # ============================================================
    active_task = redis.get(f"trip-service:vehicle:{vehicle_id}:active_task")

    if active_task:
        # Проверяем статус задания в PostgreSQL
        task_in_db = await db.fetch_one("""
            SELECT * FROM tasks
            WHERE task_id = :task_id
        """, {"task_id": active_task["task_id"]})

        if not task_in_db or task_in_db.status not in ["active", "in_progress"]:
            # Задание завершено или отменено
            redis.delete(f"trip-service:vehicle:{vehicle_id}:active_task")
            active_task = None
            logger.warning("Active task was completed, cleared from Redis")
        else:
            logger.info(
                "Active task restored",
                task_id=active_task["task_id"]
            )

    # Если нет активного задания - выбираем следующее
    if not active_task and pending_tasks:
        next_task = await select_next_task(current_tag)
        if next_task:
            await set_active_task(next_task)
            logger.info(
                "Next task selected automatically",
                task_id=next_task.task_id
            )

    # ============================================================
    # Шаг 7: Проверить Redis Stream с историей меток
    # ============================================================
    tag_history_exists = redis.exists(
        f"trip-service:vehicle:{vehicle_id}:tag_history"
    )

    if tag_history_exists:
        tag_count = redis.xlen(f"trip-service:vehicle:{vehicle_id}:tag_history")
        logger.info(
            "Tag history restored from Redis Stream",
            tag_count=tag_count
        )
    else:
        logger.info("No tag history in Redis Stream (will start fresh)")

    # ============================================================
    # Шаг 8: Подписаться на события от eKuiper через локальный Nanomq
    # ============================================================
    await mqtt_client.subscribe([
        f"/truck/{truck_id}/sensor/tag/raw",
        f"/truck/{truck_id}/sensor/speed/events",
        f"/truck/{truck_id}/sensor/weight/events",
        f"/truck/{truck_id}/sensor/vibro/events",
    ])

    logger.info("Subscribed to eKuiper events via Nanomq")

    # ============================================================
    # Шаг 9: Итоговое логирование результата восстановления
    # ============================================================
    logger.info(
        "Trip Service cold start completed",
        vehicle_id = vehicle_id,
        state=state["state"]["current"],
        active_trip=active_trip["internal_trip_id"] if active_trip else None,
        active_task=active_task["task_id"] if active_task else None,
        pending_tasks_count=len(pending_tasks),
        current_tag=current_tag["point_id"] if current_tag else None,
        tag_history_entries=tag_count if tag_history_exists else 0
    )

    return {
        "vehicle_id": vehicle_id,
        "state": state,
        "active_trip": active_trip,
        "active_task": active_task,
        "pending_tasks_count": len(pending_tasks)
    }
```

### Сценарии восстановления

**Сценарий 1: Нормальный перезапуск (Redis + PostgreSQL живы)**
- ✅ Redis с AOF сохранил все данные на диск
- ✅ Восстанавливаем State Machine из Redis
- ✅ Восстанавливаем активный рейс из Redis
- ✅ Восстанавливаем активное задание из Redis
- ✅ Redis Stream с tag_history восстановлен с диска
- ✅ Загружаем pending tasks из PostgreSQL в Redis Sorted Sets
- **Результат:** Продолжаем работу с того же места

**Сценарий 2: Redis очистился, PostgreSQL жив**
- ✅ Создаем начальное состояние `idle` в State Machine
- ✅ Восстанавливаем незавершенный рейс из PostgreSQL → Redis
- ✅ Загружаем все pending tasks из PostgreSQL → Redis Sorted Sets
- ✅ Автоматически выбираем активное задание
- ✅ Первое событие от eKuiper обновит State Machine
- ✅ Redis Stream tag_history начнется заново
- **Результат:** Восстанавливаем состояние из PostgreSQL

**Сценарий 3: Полный холодный старт (первый запуск)**
- ✅ Создаем начальное состояние `idle`
- ✅ Нет заданий → ждем POST /api/shift-tasks от сервера
- ✅ Подписываемся на события от eKuiper
- **Результат:** Готовы к работе

**Сценарий 4: Сервис упал в середине рейса**
- ✅ Redis AOF восстановил State Machine → был в `moving_loaded`
- ✅ Восстанавливаем активный рейс → `internal_trip_id` продолжается
- ✅ Восстанавливаем активное задание → знаем какое выполняем
- ✅ Redis Stream tag_history восстановлен с диска
- ✅ История состояний в PostgreSQL сохранена до момента падения
- ✅ Новые события от eKuiper продолжат обновлять State Machine
- **Результат:** Продолжаем тот же рейс без потерь

**Сценарий 5: Несоответствие Redis и PostgreSQL**
- ✅ Проверяем статус `active_trip` в PostgreSQL
- ✅ Если рейс завершен в БД, но есть в Redis → удаляем из Redis
- ✅ Если рейс `in_progress` в БД, но нет в Redis → восстанавливаем в Redis
- ✅ Аналогично для `active_task`
- **Результат:** Приводим к консистентности

### Потенциальные потери при падении

**Минимальные потери благодаря Redis AOF:**
- Redis AOF с `appendfsync everysec` сохраняет данные каждую секунду
- Максимальная потеря: последняя секунда данных при аварийном отключении
- Redis Stream tag_history восстанавливается с диска

**Что может быть потеряно:**
1. **Последнее событие State Machine (если Redis AOF не успел sync)**
   - Решение: Следующее событие от eKuiper восстановит состояние
   - Критично? Нет, State Machine устойчива к пропущенным событиям

2. **Несохраненные метрики для trip_analytics**
   - Решение: При завершении рейса вычислим из trip_state_history
   - Критично? Нет, все данные для вычисления есть в PostgreSQL

### Redis Configuration для persistence

```conf
# redis.conf
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

**Объяснение:**
- `appendonly yes` - включает AOF (Append Only File)
- `appendfsync everysec` - синхронизация на диск каждую секунду (баланс скорость/надежность)
- AOF файл автоматически переписывается при росте для оптимизации

## Интеграция с базами данных

### PostgreSQL + TimescaleDB

### Структура для shift_tasks и tasks

**Таблица shift_tasks:**
```sql
CREATE TABLE shift_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shift_id TEXT UNIQUE NOT NULL,
  vehicle_id TEXT NOT NULL,
  status TEXT NOT NULL, -- 'active', 'completed', 'cancelled'
  force BOOLEAN DEFAULT FALSE,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON shift_tasks (vehicle_id, created_at DESC);
CREATE INDEX ON shift_tasks (shift_id);
CREATE INDEX ON shift_tasks (status);
```

**Таблица tasks:**
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id TEXT UNIQUE NOT NULL,
  shift_id TEXT NOT NULL REFERENCES shift_tasks(shift_id),
  vehicle_id TEXT NOT NULL,

  -- Точки маршрута
  start_point_id TEXT NOT NULL,
  stop_point_id TEXT NOT NULL,

  -- Порядок выполнения (вместо priority)
  "order" INTEGER NOT NULL,

  -- Статус
  status TEXT NOT NULL, -- 'pending', 'active', 'in_progress', 'completed', 'cancelled'

  -- Связь с internal_trip_id
  internal_trip_id TEXT REFERENCES trips(internal_trip_id),

  -- Временные метки
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  activated_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,

  -- Метаданные (тип груза и т.д.)
  metadata JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON tasks (vehicle_id, status, "order");
CREATE INDEX ON tasks (shift_id, "order");
CREATE INDEX ON tasks (start_point_id, status);
CREATE INDEX ON tasks (internal_trip_id);
```

### Обновленная таблица trips с метриками для аналитики

```sql
CREATE TABLE trips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_trip_id TEXT UNIQUE NOT NULL,
  server_trip_id TEXT,  -- ID планового рейса с сервера (если есть)
  vehicle_id TEXT NOT NULL,
  shift_id TEXT REFERENCES shift_tasks(shift_id),

  trip_type TEXT NOT NULL, -- 'planned', 'unplanned'
  status TEXT NOT NULL,

  -- Точки
  from_point_id TEXT,
  to_point_id TEXT,

  -- Временные метки для расчета метрик
  loading_started_at TIMESTAMPTZ,
  loading_completed_at TIMESTAMPTZ,
  unloading_started_at TIMESTAMPTZ,
  unloading_completed_at TIMESTAMPTZ,

  -- Вычисляемые метрики (заполняем при завершении)
  duration_seconds INTEGER,
  loading_duration_seconds INTEGER,
  unloading_duration_seconds INTEGER,
  travel_duration_seconds INTEGER,

  -- Телеметрия
  distance_km DECIMAL,
  average_speed DECIMAL,
  fuel_consumed DECIMAL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('trips', 'created_at');

CREATE INDEX ON trips (vehicle_id, shift_id, created_at DESC);
CREATE INDEX ON trips (shift_id, status);
CREATE INDEX ON trips (server_trip_id) WHERE server_trip_id IS NOT NULL;
CREATE INDEX ON trips (internal_trip_id);
CREATE INDEX ON trips (trip_type, status);
```

### Таблица для истории состояний (для КРВ шкал)

```sql
CREATE TABLE trip_state_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_trip_id TEXT NOT NULL REFERENCES trips(internal_trip_id),
  vehicle_id TEXT NOT NULL,

  -- State machine события
  from_state TEXT,
  to_state TEXT NOT NULL,

  -- Временные метки (для построения шкал КРВ)
  state_started_at TIMESTAMPTZ NOT NULL,
  state_ended_at TIMESTAMPTZ,  -- Заполняется при следующем переходе
  duration_seconds INTEGER,     -- Вычисляем на борту при переходе

  -- Контекст
  point_id TEXT,
  sensors JSONB,

  -- Ручные изменения (для аудита)
  manual BOOLEAN DEFAULT FALSE,  -- TRUE если изменение сделано вручную пользователем
  reason TEXT,                   -- Причина ручного изменения
  comment TEXT,                  -- Комментарий оператора

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('trip_state_history', 'created_at');

CREATE INDEX ON trip_state_history (internal_trip_id, state_started_at);
CREATE INDEX ON trip_state_history (vehicle_id, state_started_at DESC);
CREATE INDEX ON trip_state_history (to_state, state_started_at);
CREATE INDEX ON trip_state_history (manual) WHERE manual = TRUE;  -- Быстрый поиск ручных изменений
```

**Принцип работы для КРВ:**
- При переходе в новое состояние → INSERT новая запись с `state_started_at`
- При следующем переходе → UPDATE предыдущей записи:
  - Ставим `state_ended_at`
  - Вычисляем `duration_seconds = state_ended_at - state_started_at` на борту
- Для шкалы берем все записи trip_state_history и отображаем по временной оси

### Таблица для истории меток

```sql
CREATE TABLE trip_tag_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_trip_id TEXT NOT NULL REFERENCES trips(internal_trip_id),
  vehicle_id TEXT NOT NULL,

  point_id TEXT NOT NULL,
  point_type TEXT,
  entered_at TIMESTAMPTZ NOT NULL,
  exited_at TIMESTAMPTZ,  -- Заполняется при смене метки

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('trip_tag_history', 'created_at');

CREATE INDEX ON trip_tag_history (internal_trip_id, entered_at);
CREATE INDEX ON trip_tag_history (vehicle_id, entered_at DESC);
CREATE INDEX ON trip_tag_history (point_id, entered_at);
```

**Принцип работы:**
- Копируется из Redis Stream при завершении рейса
- Хранит историю перемещения между метками
- `entered_at` → когда вошли в зону метки
- `exited_at` → когда покинули (при смене метки)

### Аналитическая таблица trip_analytics (для фронта и быстрых агрегаций)

```sql
CREATE TABLE trip_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Идентификация
  internal_trip_id TEXT UNIQUE NOT NULL REFERENCES trips(internal_trip_id),
  server_trip_id TEXT,  -- ID связанного задания с сервера (task_id из таблицы tasks)
  vehicle_id TEXT NOT NULL,
  shift_id TEXT REFERENCES shift_tasks(shift_id),

  -- Тип и статус
  trip_type TEXT NOT NULL,  -- 'planned', 'unplanned'
  trip_status TEXT NOT NULL, -- 'completed', 'in_progress', 'cancelled'

  -- Точки маршрута
  from_point_id TEXT,
  from_point_type TEXT,
  to_point_id TEXT,
  to_point_type TEXT,

  -- Временные метрики (все в секундах для простоты агрегаций)
  trip_started_at TIMESTAMPTZ NOT NULL,
  trip_completed_at TIMESTAMPTZ,

  total_duration_seconds INTEGER,      -- Общее время рейса
  loading_duration_seconds INTEGER,     -- Время загрузки
  unloading_duration_seconds INTEGER,   -- Время разгрузки
  travel_loaded_duration_seconds INTEGER,   -- Время движения с грузом
  travel_empty_duration_seconds INTEGER,    -- Время движения порожним
  stopped_duration_seconds INTEGER,     -- Время простоя

  -- Телеметрия
  distance_km DECIMAL(10, 2),
  average_speed_kmh DECIMAL(10, 2),
  max_speed_kmh DECIMAL(10, 2),

  -- Топливо
  fuel_start_level DECIMAL(10, 2),      -- Уровень топлива в начале
  fuel_end_level DECIMAL(10, 2),        -- Уровень топлива в конце
  fuel_consumed_liters DECIMAL(10, 2),  -- Расход топлива за рейс

  -- Вес
  weight_loaded_tons DECIMAL(10, 2),    -- Вес груза

  -- Метаданные из задания
  cargo_type TEXT,

  -- Статистика по состояниям (для быстрого доступа)
  state_idle_seconds INTEGER,
  state_loading_seconds INTEGER,
  state_moving_loaded_seconds INTEGER,
  state_unloading_seconds INTEGER,
  state_moving_empty_seconds INTEGER,

  -- Количество уникальных меток за рейс
  unique_tags_count INTEGER,

  -- TODO: Добавить в будущем при появлении плановых временных меток из заданий:
  -- plan_deviation_seconds INTEGER,  -- Отклонение от планового времени (planned_completion_time - actual_completion_time)

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('trip_analytics', 'created_at');

-- Индексы для быстрой аналитики
CREATE INDEX ON trip_analytics (vehicle_id, trip_started_at DESC);
CREATE INDEX ON trip_analytics (shift_id, trip_started_at);
CREATE INDEX ON trip_analytics (trip_type, trip_status);
CREATE INDEX ON trip_analytics (from_point_id, to_point_id);
CREATE INDEX ON trip_analytics (trip_started_at) WHERE trip_status = 'completed';
```

**Принцип работы:**
- **При завершении рейса** (`unloading_complete`) вычисляем ВСЕ метрики на борту
- **Заполняем одной записью** всю аналитику для простых агрегаций
- **Фронт читает** эту таблицу для dashboard и графиков
- **ClickHouse импортирует** эту же таблицу для глобальной аналитики

**Вычисление метрик при завершении рейса:**
```python
async def finalize_trip_analytics(internal_trip_id):
    """
    Вычисляем все метрики при завершении рейса и сохраняем в trip_analytics
    """

    # 1. Получаем данные рейса
    trip = await get_trip(internal_trip_id)

    # 2. Получаем историю состояний
    state_history = await get_state_history(internal_trip_id)

    # 3. Получаем историю меток
    tag_history = await get_tag_history(internal_trip_id)

    # 4. Получаем топливные события из eKuiper
    fuel_events = await get_fuel_events_for_trip(
        vehicle_id=trip.vehicle_id,
        start_time=trip.loading_started_at,
        end_time=trip.unloading_completed_at
    )

    # 5. Вычисляем метрики
    analytics = {
        "internal_trip_id": internal_trip_id,
        "vehicle_id": trip.vehicle_id,
        "shift_id": trip.shift_id,
        "trip_type": trip.trip_type,
        "trip_status": "completed",

        # Временные метрики
        "trip_started_at": trip.loading_completed_at,
        "trip_completed_at": trip.unloading_completed_at,
        "total_duration_seconds": (
            trip.unloading_completed_at - trip.loading_completed_at
        ).total_seconds(),

        # Длительности по состояниям
        "loading_duration_seconds": sum(
            s.duration_seconds for s in state_history
            if s.to_state in ['loading', 'stopped_empty']
        ),
        "unloading_duration_seconds": sum(
            s.duration_seconds for s in state_history
            if s.to_state in ['unloading', 'stopped_loaded']
        ),
        "travel_loaded_duration_seconds": sum(
            s.duration_seconds for s in state_history
            if s.to_state == 'moving_loaded'
        ),
        "travel_empty_duration_seconds": sum(
            s.duration_seconds for s in state_history
            if s.to_state == 'moving_empty'
        ),

        # Топливо
        "fuel_start_level": fuel_events[0].value if fuel_events else None,
        "fuel_end_level": fuel_events[-1].value if fuel_events else None,
        "fuel_consumed_liters": calculate_fuel_consumption(fuel_events),

        # Метки
        "unique_tags_count": len(set(t.point_id for t in tag_history)),

        # ... остальные метрики
    }

    # 6. Сохраняем в trip_analytics
    await db.execute("""
        INSERT INTO trip_analytics (...)
        VALUES (...)
    """, analytics)
```

**Примеры запросов для фронта:**
```sql
-- Рейсы за сегодня для одной машины
SELECT * FROM trip_analytics
WHERE vehicle_id = 'AC9'
  AND trip_started_at >= CURRENT_DATE
ORDER BY trip_started_at DESC;

-- Средний расход топлива за смену
SELECT shift_id, AVG(fuel_consumed_liters) as avg_fuel
FROM trip_analytics
WHERE shift_id = '550e8400-e29b-41d4'
  AND trip_status = 'completed'
GROUP BY shift_id;

-- Количество рейсов за смену
SELECT shift_id, COUNT(*) as trip_count
FROM trip_analytics
WHERE shift_id = '550e8400-e29b-41d4'
  AND trip_status = 'completed'
GROUP BY shift_id;

-- Общее время в каждом состоянии за смену
SELECT
  shift_id,
  SUM(state_loading_seconds) as total_loading,
  SUM(state_moving_loaded_seconds) as total_moving_loaded,
  SUM(state_unloading_seconds) as total_unloading
FROM trip_analytics
WHERE shift_id = '550e8400-e29b-41d4'
GROUP BY shift_id;
```

### Redis кэширование

**Redis Sorted Sets для очереди заданий (Гибридный подход - Вариант C):**
```
trip-service:task_queue:{start_point_id} → Sorted Set (score = order, value = task_id)
trip-service:task_queue:ordered          → Sorted Set всех pending заданий по order
```

**Ключи состояния:**
```
trip-service:vehicle:${vehicle_id}:state
trip-service:vehicle:${vehicle_id}:active_task
trip-service:vehicle:${vehicle_id}:current_tag
trip-service:vehicle:${vehicle_id}:tag_history
```

**Redis Pub/Sub топики для подписки:**
```
trip-service:vehicle:${vehicle_id}:state:changes          - Изменения State Machine
trip-service:vehicle:${vehicle_id}:active_trip:changes    - Изменения активного рейса
trip-service:vehicle:${vehicle_id}:active_task:changes    - Изменения активного задания
trip-service:vehicle:${vehicle_id}:current_tag:changes    - Изменения текущей метки
trip-service:vehicle:${vehicle_id}:tag_history:changes    - Новая метка в истории
trip-service:shift_task_changes                          - Изменения shift_task
```

## CRUD API для управления shift_tasks и tasks

### API для Shift Tasks

#### TODO #9: GET /api/shift-tasks

**Тип запроса:** GET
**Название:** Получить список shift_tasks
**Описание:** Возвращает список всех shift_tasks с возможностью фильтрации по статусу

**Входные данные (Query Parameters):**
- `status` (optional): `active` | `completed` | `cancelled`
- `limit` (optional): количество записей (default: 50)
- `offset` (optional): смещение для пагинации

**Выходные данные:**
```json
{
  "shift_tasks": [
    {
      "shift_id": "550e8400-e29b-41d4-a716-446655440000",
      "vehicle_id": "AC9",
      "status": "active",
      "tasks_count": 5,
      "completed_tasks": 2,
      "pending_tasks": 3,
      "received_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Процесс работы:**
1. Читаем из PostgreSQL: `SELECT * FROM shift_tasks WHERE vehicle_id = :vehicle_id AND status = :status`
2. Для каждого shift_task подсчитываем задания: `SELECT COUNT(*) FROM tasks WHERE shift_id = :shift_id GROUP BY status`
3. Возвращаем список с агрегированной информацией

---

#### TODO #10: GET /api/shift-tasks/{shift_id}

**Тип запроса:** GET
**Название:** Получить детали shift_task
**Описание:** Возвращает полную информацию о shift_task со всеми заданиями

**Входные данные (Path Parameter):**
- `shift_id`: ID смены

**Выходные данные:**
```json
{
  "shift_id": "550e8400-e29b-41d4-a716-446655440000",
  "vehicle_id": "AC9",
  "status": "active",
  "force": false,
  "received_at": "2024-01-15T10:00:00Z",
  "tasks": [
    {
      "task_id": "task_001",
      "status": "completed",
      "start_point_id": "excavator_001",
      "stop_point_id": "warehouse_A",
      "order": 1,
      "metadata": {"cargo_type": "ore"}
    }
  ],
  "tasks_count": 5,
  "active_task_id": "task_002"
}
```

**Процесс работы:**
1. Читаем из PostgreSQL: `SELECT * FROM shift_tasks WHERE shift_id = :shift_id`
2. Читаем задания: `SELECT * FROM tasks WHERE shift_id = :shift_id ORDER BY "order"`
3. Читаем активное задание из Redis: `GET trip-service:vehicle:{vehicle_id}:active_task`
4. Возвращаем объединенную информацию

---

#### TODO #11: PUT /api/shift-tasks/{shift_id}/complete

**Тип запроса:** PUT
**Название:** Завершить shift_task
**Описание:** Завершает shift_task и отменяет все незавершенные задания

**Входные данные (Path Parameter):**
- `shift_id`: ID смены

**Выходные данные:**
```json
{
  "shift_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Shift task completed, 2 tasks cancelled"
}
```

**Процесс работы:**
1. Обновляем PostgreSQL: `UPDATE shift_tasks SET status = 'completed' WHERE shift_id = :shift_id`
2. Отменяем pending задания: `UPDATE tasks SET status = 'cancelled', cancelled_at = NOW() WHERE shift_id = :shift_id AND status = 'pending'`
3. Очищаем Redis очереди: `DEL trip-service:task_queue:ordered` и все `trip-service:task_queue:{point_id}`
4. Публикуем событие в Redis: `PUBLISH trip-service:shift_task_changes '{"shift_id": "...", "status": "completed"}'`
5. Публикуем в Nanomq: `/truck/{truck_id}/trip-service/events` → `shift_task_completed`

---

#### TODO #12: DELETE /api/shift-tasks/{shift_id}

**Тип запроса:** DELETE
**Название:** Отменить shift_task
**Описание:** Отменяет shift_task и все его задания

**Входные данные (Path Parameter):**
- `shift_id`: ID смены

**Выходные данные:**
```json
{
  "shift_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Shift task cancelled, 5 tasks cancelled"
}
```

**Процесс работы:**
1. Обновляем PostgreSQL: `UPDATE shift_tasks SET status = 'cancelled' WHERE shift_id = :shift_id`
2. Отменяем все задания: `UPDATE tasks SET status = 'cancelled', cancelled_at = NOW() WHERE shift_id = :shift_id`
3. Очищаем Redis очереди заданий
4. Если активное задание из этого shift_task → очищаем: `DEL trip-service:vehicle:{vehicle_id}:active_task` + `PUBLISH :changes`
5. Публикуем событие в Redis и Nanomq

---

### API для Tasks

#### TODO #13: GET /api/tasks

**Тип запроса:** GET
**Название:** Получить список заданий
**Описание:** Возвращает список заданий с фильтрацией по статусу и shift_id

**Входные данные (Query Parameters):**
- `status` (optional): `pending` | `active` | `in_progress` | `completed` | `cancelled`
- `shift_id` (optional): фильтр по смене
- `limit` (optional): количество записей (default: 50)
- `offset` (optional): смещение для пагинации

**Выходные данные:**
```json
{
  "tasks": [
    {
      "task_id": "task_001",
      "shift_id": "550e8400-e29b-41d4",
      "status": "pending",
      "start_point_id": "excavator_001",
      "stop_point_id": "warehouse_A",
      "order": 1,
      "metadata": {"cargo_type": "ore"},
      "assigned_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 10,
  "active_task_id": "task_002",
  "limit": 50,
  "offset": 0
}
```

**Процесс работы:**
1. Читаем из PostgreSQL с фильтрами: `SELECT * FROM tasks WHERE vehicle_id = :vehicle_id AND status = :status AND shift_id = :shift_id ORDER BY "order"`
2. Читаем активное задание из Redis: `GET trip-service:vehicle:{vehicle_id}:active_task`
3. Возвращаем список с указанием активного задания

---

#### TODO #14: GET /api/tasks/{task_id}

**Тип запроса:** GET
**Название:** Получить детали задания
**Описание:** Возвращает полную информацию о конкретном задании

**Входные данные (Path Parameter):**
- `task_id`: ID задания

**Выходные данные:**
```json
{
  "task_id": "task_001",
  "shift_id": "550e8400-e29b-41d4",
  "vehicle_id": "AC9",
  "status": "in_progress",
  "start_point_id": "excavator_001",
  "stop_point_id": "warehouse_A",
  "order": 1,
  "metadata": {"cargo_type": "ore", "expected_weight": 45.0},
  "internal_trip_id": "trip_123",
  "assigned_at": "2024-01-15T10:00:00Z",
  "activated_at": "2024-01-15T10:05:00Z",
  "started_at": "2024-01-15T10:10:00Z"
}
```

**Процесс работы:**
1. Читаем из PostgreSQL: `SELECT * FROM tasks WHERE task_id = :task_id`
2. Если задание связано с рейсом, читаем данные рейса: `SELECT * FROM trips WHERE internal_trip_id = :internal_trip_id`
3. Возвращаем объединенную информацию

---

#### TODO #15: PUT /api/tasks/{task_id}/activate

**Тип запроса:** PUT
**Название:** Активировать задание
**Описание:** Делает задание активным (ручной выбор из фронта)

**Входные данные (Path Parameter):**
- `task_id`: ID задания

**Выходные данные:**
```json
{
  "task_id": "task_001",
  "status": "active",
  "message": "Task activated successfully"
}
```

**Процесс работы:**
1. Проверяем, что задание в статусе `pending`: `SELECT * FROM tasks WHERE task_id = :task_id AND status = 'pending'`
2. Обновляем PostgreSQL: `UPDATE tasks SET status = 'active', activated_at = NOW() WHERE task_id = :task_id`
3. Деактивируем предыдущее активное задание (если есть): `UPDATE tasks SET status = 'pending' WHERE task_id = :old_task_id`
4. Обновляем Redis: `SET trip-service:vehicle:{vehicle_id}:active_task` → JSON задания
5. Публикуем изменения: `PUBLISH trip-service:vehicle:{vehicle_id}:active_task:changes` → полное задание
6. Удаляем из очереди Redis: `ZREM trip-service:task_queue:ordered {task_id}` и `ZREM trip-service:task_queue:{start_point_id} {task_id}`
7. Публикуем в Nanomq: `/truck/{truck_id}/trip-service/events` → `task_activated`

---

#### TODO #16: PUT /api/tasks/{task_id}/status

**Тип запроса:** PUT
**Название:** Обновить статус задания
**Описание:** Обновляет статус задания вручную

**Входные данные (Path Parameter + Body):**
- `task_id`: ID задания
- Body:
```json
{
  "status": "cancelled"
}
```

**Выходные данные:**
```json
{
  "task_id": "task_001",
  "old_status": "pending",
  "new_status": "cancelled",
  "message": "Task status updated"
}
```

**Процесс работы:**
1. Читаем текущее задание: `SELECT * FROM tasks WHERE task_id = :task_id`
2. Обновляем статус в PostgreSQL: `UPDATE tasks SET status = :new_status WHERE task_id = :task_id`
3. Если задание было активным и отменяется:
   - Очищаем Redis: `DEL trip-service:vehicle:{vehicle_id}:active_task`
   - Публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:active_task:changes '{"task_id": null}'`
   - Выбираем следующее задание из очереди
4. Удаляем из Redis очередей: `ZREM trip-service:task_queue:*`
5. Публикуем событие в Nanomq

---

#### TODO #17: DELETE /api/tasks/{task_id}

**Тип запроса:** DELETE
**Название:** Отменить задание
**Описание:** Отменяет конкретное задание

**Входные данные (Path Parameter):**
- `task_id`: ID задания

**Выходные данные:**
```json
{
  "task_id": "task_001",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

**Процесс работы:**
1. Обновляем PostgreSQL: `UPDATE tasks SET status = 'cancelled', cancelled_at = NOW() WHERE task_id = :task_id`
2. Если это активное задание:
   - Очищаем Redis: `DEL trip-service:vehicle:{vehicle_id}:active_task`
   - Публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:active_task:changes '{"task_id": null}'`
   - Автоматически выбираем следующее задание из очереди
3. Удаляем из Redis очередей: `ZREM trip-service:task_queue:ordered {task_id}` и `ZREM trip-service:task_queue:{start_point_id} {task_id}`
4. Публикуем событие в Nanomq: `/truck/{truck_id}/trip-service/events` → `task_cancelled`

---

### API для Active Task (управление активным заданием)

#### GET /api/active-task

**Тип запроса:** GET
**Название:** Получить активное задание
**Описание:** Возвращает текущее активное задание (алиас для удобства фронта)

**Входные данные:** Нет

**Выходные данные:**
```json
{
  "task_id": "task_001",
  "shift_id": "550e8400-e29b-41d4",
  "status": "active",
  "start_point_id": "excavator_001",
  "stop_point_id": "warehouse_A",
  "order": 1,
  "metadata": {
    "cargo_type": "ore",
    "expected_weight": 45.0
  },
  "activated_at": "2024-01-15T10:05:00Z"
}
```

**Если нет активного задания:**
```json
{
  "task_id": null,
  "message": "No active task"
}
```

**Процесс работы:**
1. Читаем из Redis: `GET trip-service:vehicle:{vehicle_id}:active_task`
2. Если есть - возвращаем JSON
3. Если нет - возвращаем `null`

---

#### DELETE /api/active-task

**Тип запроса:** DELETE
**Название:** Очистить активное задание
**Описание:** Убирает активное задание (пользователь решил не выполнять задания)

**Входные данные:** Нет

**Выходные данные:**
```json
{
  "message": "Active task cleared",
  "previous_task_id": "task_001"
}
```

**Процесс работы:**
1. Читаем текущее активное задание: `GET trip-service:vehicle:{vehicle_id}:active_task`
2. Если есть активное задание:
   - Обновляем PostgreSQL: `UPDATE tasks SET status = 'pending' WHERE task_id = :task_id`
   - Очищаем Redis: `DEL trip-service:vehicle:{vehicle_id}:active_task`
   - Публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:active_task:changes '{"task_id": null, "action": "cleared"}'`
   - Публикуем в Nanomq: `/truck/{truck_id}/trip-service/events` → `task_deactivated`
3. Возвращаем результат

**Примечание:** Рейс (active_trip) продолжается независимо от наличия активного задания!

---

### API для Active Trip (просмотр текущего рейса)

#### GET /api/active-trip

**Тип запроса:** GET
**Название:** Получить текущий рейс
**Описание:** Возвращает информацию о рейсе, который машина выполняет СЕЙЧАС (READ-ONLY)

**Входные данные:** Нет

**Выходные данные (если есть активный рейс):**
```json
{
  "internal_trip_id": "trip_001",
  "server_trip_id": "task_123",
  "vehicle_id": "AC9",
  "trip_type": "planned",
  "status": "in_progress",
  "from_point_id": "excavator_001",
  "to_point_id": null,
  "started_at": "2024-01-15T10:10:00Z",
  "current_state": "moving_loaded",
  "current_tag": {
    "point_id": "road_segment_5",
    "point_type": "road",
    "timestamp": "2024-01-15T10:15:00Z"
  }
}
```

**Если нет активного рейса:**
```json
{
  "internal_trip_id": null,
  "message": "No active trip",
  "current_state": "idle"
}
```

**Процесс работы:**
1. Читаем из Redis: `GET trip-service:vehicle:{vehicle_id}:active_trip`
2. Если есть - обогащаем данными:
   - Читаем State Machine: `GET trip-service:vehicle:{vehicle_id}:state` → текущее состояние
   - Читаем current_tag: `GET trip-service:vehicle:{vehicle_id}:current_tag` → где сейчас
3. Возвращаем объединенную информацию
4. Если нет - возвращаем `null` с текущим состоянием из State Machine

---

#### PUT /api/active-trip/complete

**Тип запроса:** PUT
**Название:** Завершить текущий рейс вручную
**Описание:** Позволяет пользователю вручную завершить активный рейс (аналог автоматического `unloading_complete`)

**Входные данные:** Нет (или опционально):
```json
{
  "reason": "manual_completion",
  "comment": "Завершено оператором из-за технических проблем"
}
```

**Выходные данные:**
```json
{
  "internal_trip_id": "trip_001",
  "status": "completed",
  "message": "Trip completed manually",
  "completed_at": "2024-01-15T10:30:00Z"
}
```

**Процесс работы:**
1. Проверяем наличие активного рейса: `GET trip-service:vehicle:{vehicle_id}:active_trip`
2. Если нет активного рейса - возвращаем ошибку
3. **Вызываем ТУ ЖЕ логику что и при автоматическом `unloading_complete`:**
   - Читаем текущую метку: `GET trip-service:vehicle:{vehicle_id}:current_tag`
   - Обновляем PostgreSQL trips: `UPDATE trips SET status = 'completed', unloading_completed_at = NOW(), to_point_id = :current_point_id`
   - Если это плановый рейс - обновляем задание: `UPDATE tasks SET status = 'completed', completed_at = NOW()`
   - Сохраняем tag_history в PostgreSQL из Redis Stream
   - Вычисляем и сохраняем trip_analytics
   - Очищаем Redis: `DEL trip-service:vehicle:{vehicle_id}:tag_history`
4. **Обновляем State Machine:**
   - Переводим в состояние `idle` или `stopped_empty` (в зависимости от weight)
   - Очищаем `state.current_internal_trip_id = null`
   - Сохраняем в Redis: `SET trip-service:vehicle:{vehicle_id}:state`
   - Публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:state:changes`
5. **Очищаем active_trip:**
   - `DEL trip-service:vehicle:{vehicle_id}:active_trip`
   - Публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:active_trip:changes '{"internal_trip_id": null, "action": "manual_completion"}'`
6. **Публикуем события в Nanomq:**
   - `/truck/{truck_id}/trip-service/events` → `trip_completed` с пометкой `manual: true`
   - `/truck/{truck_id}/trip-service/state_changes` → переход состояния
7. Логируем в PostgreSQL с пометкой ручного завершения
8. Выбираем следующее активное задание из очереди
9. Возвращаем результат

**Примечание:** Ручное завершение логируется отдельно для аудита!

---

### API для State Machine (ручное управление состоянием)

#### GET /api/state

**Тип запроса:** GET
**Название:** Получить текущее состояние State Machine
**Описание:** Возвращает полное состояние State Machine с данными датчиков

**Входные данные:** Нет

**Выходные данные:**
```json
{
  "vehicle_id": "AC9",
  "data": {
    "speed": {
      "value": 35.0,
      "status": "moving",
      "timestamp": 1755500626.0
    },
    "weight": {
      "value": 45.2,
      "status": "loaded",
      "timestamp": 1755500636.0
    },
    "vibro": {
      "status": "inactive",
      "delta_weight": 0.0,
      "timestamp": 1755500636.0
    },
    "tag": {
      "point_id": "road_segment_5",
      "point_type": "road",
      "timestamp": 1755500584.0
    }
  },
  "state": {
    "current": "moving_loaded",
    "previous": "stopped_loaded",
    "loaded_at": "excavator_001",
    "unloaded_at": null,
    "current_internal_trip_id": "trip_001",
    "timestamp": 1755500636.0,
    "current_time": 1755500636.0
  }
}
```

**Процесс работы:**
1. Читаем из Redis: `GET trip-service:vehicle:{vehicle_id}:state`
2. Возвращаем полную структуру State Machine

---

#### PUT /api/state

**Тип запроса:** PUT
**Название:** Установить состояние State Machine вручную
**Описание:** Позволяет пользователю вручную изменить состояние машины (для корректировки)

**Входные данные:**
```json
{
  "new_state": "stopped_empty",
  "reason": "manual_correction",
  "comment": "Оператор исправил состояние - машина фактически порожняя"
}
```

**Допустимые состояния:**
- `idle`
- `moving_empty`
- `stopped_empty`
- `loading`
- `loading_complete`
- `moving_loaded`
- `stopped_loaded`
- `unloading`
- `unloading_complete`

**Выходные данные:**
```json
{
  "vehicle_id": "AC9",
  "old_state": "moving_loaded",
  "new_state": "stopped_empty",
  "message": "State updated manually",
  "timestamp": 1755500700.0
}
```

**Процесс работы:**
1. Читаем текущее состояние: `GET trip-service:vehicle:{vehicle_id}:state`
2. Валидируем новое состояние (должно быть из списка допустимых)
3. **Обновляем State Machine в Redis:**
   ```python
   old_state = state["state"]["current"]
   state["state"]["previous"] = old_state
   state["state"]["current"] = new_state
   state["state"]["timestamp"] = time.time()
   state["state"]["current_time"] = time.time()

   redis.set(f"trip-service:vehicle:{vehicle_id}:state", json.dumps(state))
   ```
4. **Публикуем в Redis Pub/Sub:**
   ```python
   redis.publish(
       f"trip-service:vehicle:{vehicle_id}:state:changes",
       json.dumps({
           "vehicle_id": vehicle_id,
           "state": state,
           "manual": True,
           "reason": reason,
           "timestamp": time.time()
       })
   )
   ```
5. **Публикуем в Nanomq:**
   ```python
   publish_to_nanomq(
       topic=f"/truck/{truck_id}/trip-service/state_changes",
       event={
           "event_type": "state_transition",
           "vehicle_id": vehicle_id,
           "from_state": old_state,
           "to_state": new_state,
           "internal_trip_id": state["state"].get("current_internal_trip_id"),
           "manual": True,
           "reason": reason,
           "comment": comment,
           "timestamp": time.time()
       }
   )
   ```
6. **Логируем в PostgreSQL trip_state_history:**
   ```python
   insert_state_history(
       internal_trip_id=state["state"].get("current_internal_trip_id"),
       from_state=old_state,
       to_state=new_state,
       state_started_at=time.time(),
       point_id=state["data"]["tag"]["point_id"] if state["data"]["tag"] else None,
       sensors=state["data"],
       manual=True,  # ← ВАЖНО! Помечаем как ручное изменение
       reason=reason,
       comment=comment
   )
   ```
7. **Проверяем побочные эффекты:**
   - Если новое состояние = `loading_complete` → автоматически создаем рейс
   - Если новое состояние = `unloading_complete` → автоматически завершаем рейс
   - Если новое состояние = `idle` → очищаем active_trip если есть
8. Возвращаем результат

**Важные замечания:**
- ⚠️ Ручные изменения логируются с флагом `manual=True` для аудита
- ⚠️ При переходе в `loading_complete` или `unloading_complete` вызываются соответствующие бизнес-процессы
- ⚠️ Если одновременно приходят события от датчиков - они перезапишут ручное состояние
- ⚠️ Рекомендуется использовать только в исключительных случаях для корректировки

---

### API для Trips (история рейсов)

#### GET /api/trips

**Тип запроса:** GET
**Название:** Получить историю рейсов
**Описание:** Возвращает список завершенных рейсов с фильтрацией

**Входные данные (Query Parameters):**
- `status` (optional): `in_progress` | `completed` | `cancelled`
- `trip_type` (optional): `planned` | `unplanned`
- `shift_id` (optional): фильтр по смене
- `date_from` (optional): начало периода
- `date_to` (optional): конец периода
- `limit` (optional): количество записей (default: 50)
- `offset` (optional): смещение для пагинации

**Выходные данные:**
```json
{
  "trips": [
    {
      "internal_trip_id": "trip_001",
      "server_trip_id": "task_123",
      "vehicle_id": "AC9",
      "shift_id": "550e8400-e29b-41d4",
      "trip_type": "planned",
      "status": "completed",
      "from_point_id": "excavator_001",
      "to_point_id": "warehouse_A",
      "loading_started_at": "2024-01-15T10:08:00Z",
      "loading_completed_at": "2024-01-15T10:10:00Z",
      "unloading_started_at": "2024-01-15T10:25:00Z",
      "unloading_completed_at": "2024-01-15T10:27:00Z",
      "duration_seconds": 1020,
      "distance_km": 5.2
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

**Процесс работы:**
1. Читаем из PostgreSQL с фильтрами: `SELECT * FROM trips WHERE vehicle_id = :vehicle_id AND status = :status AND trip_type = :trip_type AND created_at BETWEEN :date_from AND :date_to ORDER BY created_at DESC`
2. Возвращаем список с пагинацией

---

#### GET /api/trips/{internal_trip_id}

**Тип запроса:** GET
**Название:** Получить детали рейса
**Описание:** Возвращает полную информацию о конкретном рейсе с историей состояний и меток

**Входные данные (Path Parameter):**
- `internal_trip_id`: ID рейса

**Выходные данные:**
```json
{
  "internal_trip_id": "trip_001",
  "server_trip_id": "task_123",
  "vehicle_id": "AC9",
  "shift_id": "550e8400-e29b-41d4",
  "trip_type": "planned",
  "status": "completed",
  "from_point_id": "excavator_001",
  "to_point_id": "warehouse_A",
  "loading_started_at": "2024-01-15T10:08:00Z",
  "loading_completed_at": "2024-01-15T10:10:00Z",
  "unloading_started_at": "2024-01-15T10:25:00Z",
  "unloading_completed_at": "2024-01-15T10:27:00Z",
  "duration_seconds": 1020,
  "distance_km": 5.2,
  "state_history": [
    {
      "from_state": "stopped_empty",
      "to_state": "loading",
      "state_started_at": "2024-01-15T10:08:00Z",
      "state_ended_at": "2024-01-15T10:10:00Z",
      "duration_seconds": 120,
      "point_id": "excavator_001"
    },
    {
      "from_state": "loading",
      "to_state": "loading_complete",
      "state_started_at": "2024-01-15T10:10:00Z",
      "state_ended_at": "2024-01-15T10:10:30Z",
      "duration_seconds": 30,
      "point_id": "excavator_001"
    }
  ],
  "tag_history": [
    {
      "point_id": "excavator_001",
      "point_type": "loading_zone",
      "entered_at": "2024-01-15T10:08:00Z",
      "exited_at": "2024-01-15T10:10:30Z"
    },
    {
      "point_id": "road_segment_5",
      "point_type": "road",
      "entered_at": "2024-01-15T10:12:00Z",
      "exited_at": "2024-01-15T10:20:00Z"
    }
  ],
  "analytics": {
    "total_duration_seconds": 1020,
    "loading_duration_seconds": 120,
    "travel_loaded_duration_seconds": 600,
    "unloading_duration_seconds": 120,
    "unique_tags_count": 5,
    "fuel_consumed_liters": 12.5
  }
}
```

**Процесс работы:**
1. Читаем из PostgreSQL: `SELECT * FROM trips WHERE internal_trip_id = :internal_trip_id`
2. Читаем историю состояний: `SELECT * FROM trip_state_history WHERE internal_trip_id = :internal_trip_id ORDER BY state_started_at`
3. Читаем историю меток: `SELECT * FROM trip_tag_history WHERE internal_trip_id = :internal_trip_id ORDER BY entered_at`
4. Читаем аналитику: `SELECT * FROM trip_analytics WHERE internal_trip_id = :internal_trip_id`
5. Объединяем и возвращаем полную информацию

---

### Общие принципы работы с Redis для всех API

**При любом обновлении Redis ключа:**
1. Обновляем ключ: `SET trip-service:vehicle:{vehicle_id}:{key} {value}`
2. СРАЗУ публикуем: `PUBLISH trip-service:vehicle:{vehicle_id}:{key}:changes {value}`

**Примеры:**
```python
# Обновление active_task
redis.set(f"trip-service:vehicle:{vehicle_id}:active_task", json.dumps(task))
redis.publish(
    f"trip-service:vehicle:{vehicle_id}:active_task:changes",
    json.dumps(task)
)

# Обновление current_tag
redis.set(f"trip-service:vehicle:{vehicle_id}:current_tag", json.dumps(tag))
redis.publish(
    f"trip-service:vehicle:{vehicle_id}:current_tag:changes",
    json.dumps(tag)
)

# Добавление в tag_history stream
redis.xadd(f"trip-service:vehicle:{vehicle_id}:tag_history", data)
redis.publish(
    f"trip-service:vehicle:{vehicle_id}:tag_history:changes",
    json.dumps({"point_id": tag.point_id, "timestamp": tag.timestamp})
)
```

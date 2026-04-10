# audit-lib

`audit-lib` — библиотека SQLAlchemy 2.x для транзакционного аудит-логирования
с использованием паттерна outbox.

Когда вы добавляете `AuditMixin` к модели, библиотека записывает diff для
create/update/delete в таблицу `audit_outbox` в той же транзакции.

Опциональный модуль **daemon** читает outbox и публикует записи
в RabbitMQ Stream с retry, exponential backoff и периодической очисткой.

## Установка

```bash
# Только outbox (core)
uv add audit-lib

# С FastAPI middleware (автоматический user_id из JWT)
uv add "audit-lib[fastapi]"

# С демоном для RabbitMQ Stream
uv add "audit-lib[daemon]"
```

## Быстрый старт (sync, можно скопировать и запустить)

```python
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib import AuditMixin, configure_audit, set_audit_user


class Base(DeclarativeBase):
    pass


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(sa.String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __audit_exclude__ = {"password_hash"}


AuditOutbox = configure_audit(Base, service_name="billing-service")

engine = sa.create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    with set_audit_user("user-42"):
        user = User(email="alice@example.com", password_hash="secret")
        session.add(user)
        session.commit()

        user.email = "alice.new@example.com"
        session.commit()

    rows = list(
        session.execute(sa.select(AuditOutbox).order_by(AuditOutbox.timestamp.asc()))
        .scalars()
    )
    assert len(rows) == 2
    assert rows[0].operation == "create"
    assert rows[1].operation == "update"
    assert rows[0].user_id == "user-42"
    assert "password_hash" not in (rows[0].new_values or {})
```

## Конфигурация

Настройте библиотеку один раз при старте приложения после импорта моделей:

```python
from audit_lib import configure_audit

AuditOutbox = configure_audit(
    Base,
    service_name="orders-service",   # service_name по умолчанию
    serializer=str,                   # необязательный сериализатор значений
)
```

Примечания:
- `configure_audit(Base)` возвращает сгенерированный класс модели `AuditOutbox`.
- `setup(Base, ...)` — алиас для `configure_audit(...)`.
- Если вызвать `configure_audit` более одного раза в одном процессе,
  библиотека покажет предупреждение и сохранит исходную конфигурацию.

Вы можете переопределять контекст для конкретного запроса/юнита работы:

```python
from audit_lib import set_audit_context

with set_audit_context(user_id="user-99", service_name="checkout"):
    ...
```

## Использование с Alembic (вместо `Base.metadata.create_all`)

В реальном проекте схему БД обычно создаёт Alembic, а не `create_all`.
Для `audit-lib` это настраивается так:

1. На старте приложения один раз вызывайте `configure_audit(Base, ...)`
   после импорта моделей.
2. В `alembic/env.py` добавьте `audit_outbox` в `target_metadata`, чтобы
   Alembic увидел таблицу при `--autogenerate`.

Пример `alembic/env.py`:

```python
from myapp.db import Base
import myapp.models  # импортирует все модели приложения

from audit_lib import create_audit_model

create_audit_model(Base)  # регистрирует модель audit_outbox в Base.metadata
target_metadata = Base.metadata
```

Дальше создайте и примените миграцию:

```bash
alembic revision --autogenerate -m "add audit outbox table"
alembic upgrade head
```

`audit-lib` генерирует `audit_outbox.id` на стороне Python как UUIDv7, поэтому
DB `server_default` для `id` не требуется.

Если у вас раньше использовался `server_default=gen_random_uuid()`, удалите его
в отдельной Alembic-ревизии:

```python
from alembic import op


def upgrade() -> None:
    op.alter_column("audit_outbox", "id", server_default=None)
```

## `__audit_exclude__` (чувствительные поля)

Используйте `__audit_exclude__`, чтобы пропускать поля в `old_values`/`new_values`:

```python
class ApiClient(Base, AuditMixin):
    __tablename__ = "api_clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    api_token: Mapped[str]

    __audit_exclude__ = {"api_token"}
```

Если изменились только исключённые поля, запись `update` в outbox не создаётся.

## Асинхронное использование (`AsyncSession`)

Mapper listeners по-прежнему фиксируют изменения для асинхронных сессий SQLAlchemy:

```python
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from audit_lib import AuditMixin, configure_audit, set_audit_user


class Base(DeclarativeBase):
    pass


class AsyncUser(Base, AuditMixin):
    __tablename__ = "async_users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)


AuditOutbox = configure_audit(Base)


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        async with set_audit_user("async-user-1"):
            session.add(AsyncUser(name="Alice"))
            await session.commit()

        rows = list((await session.execute(sa.select(AuditOutbox))).scalars())
        assert len(rows) == 1
        assert rows[0].operation == "create"
        assert rows[0].user_id == "async-user-1"

    await engine.dispose()
```

## FastAPI Middleware (JWT → audit user)

`AuditMiddleware` — чистый ASGI middleware, который автоматически извлекает `sub`
из JWT Bearer-токена в заголовке `Authorization` и выставляет `audit_user_var`
на время запроса. Требует `audit-lib[fastapi]`.

```python
from fastapi import FastAPI
from audit_lib import AuditMixin, configure_audit
from audit_lib.fastapi import AuditMiddleware

app = FastAPI()
app.add_middleware(AuditMiddleware)
```

Особенности:
- **Без верификации подписи** — декодирует только payload через stdlib `base64`+`json`
  (верификация — ответственность gateway/auth-сервиса).
- **Graceful degradation** — если токена нет или он невалидный, запрос проходит
  без ошибок, `user_id` остаётся `None`.
- **Contextvar isolation** — `audit_user_var` сбрасывается после каждого запроса
  через `try/finally`, утечки между запросами невозможны.
- **Non-HTTP passthrough** — lifespan и websocket scope пропускаются без обработки.

## Outbox Daemon (RabbitMQ Stream)

Модуль `audit_lib.daemon` — опциональный демон, который читает `audit_outbox`
и публикует записи в RabbitMQ Stream. Требует `audit-lib[daemon]`.

### Быстрый старт

```python
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from audit_lib import configure_audit
from audit_lib.daemon import OutboxDaemon

# ... Base, модели, AuditOutbox = configure_audit(Base) ...

engine = create_async_engine("postgresql+asyncpg://localhost/mydb")
session_factory = async_sessionmaker(engine)

daemon = OutboxDaemon(
    session_factory=session_factory,
    outbox_model=AuditOutbox,
    host="localhost",
    port=5552,
    stream_name="audit-events",
)

asyncio.run(daemon.run())
```

### Параметры `OutboxDaemon`

| Параметр | По умолчанию | Описание |
|---|---|---|
| `session_factory` | *обязательный* | `async_sessionmaker[AsyncSession]` |
| `outbox_model` | *обязательный* | Класс `AuditOutbox` |
| `host` | `"localhost"` | RabbitMQ host |
| `port` | `5552` | RabbitMQ Stream protocol port |
| `username` | `"guest"` | Логин RabbitMQ |
| `password` | `"guest"` | Пароль RabbitMQ |
| `vhost` | `"/"` | Virtual host |
| `stream_name` | `"audit-events"` | Имя стрима |
| `batch_size` | `100` | Записей за один цикл |
| `poll_interval` | `1.0` | Пауза между циклами (сек) |
| `max_backoff` | `60.0` | Макс. backoff при retry (сек) |
| `retention_hours` | `72` | Часы хранения обработанных записей (`None` — без очистки) |
| `cleanup_interval_hours` | `1.0` | Частота очистки (часы) |

### Архитектура

```
App Transaction           Daemon                  Downstream
┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
│ business     │     │ poll outbox   │     │ RabbitMQ Stream │
│ data +       │────>│ serialize     │────>│ consumer        │──> ClickHouse
│ audit_outbox │     │ publish       │     │                 │
└─────────────┘     │ mark processed│     └─────────────────┘
                    │ cleanup old   │
                    └───────────────┘
```

- **Polling**: `SELECT ... FOR UPDATE SKIP LOCKED` — безопасно для нескольких экземпляров.
- **Retry**: exponential backoff при ошибке публикации.
- **Cleanup**: фоновая задача удаляет обработанные записи старше `retention_hours`.
- **Graceful shutdown**: обрабатывает `SIGINT`/`SIGTERM`.

### Daemon API (`audit_lib.daemon`)

- `OutboxDaemon(*, session_factory, outbox_model, ...)`:
  Основной демон. `run()` запускает цикл, `stop()` — плавная остановка.
- `StreamPublisher(host, port, username, password, vhost, stream_name)`:
  Публикатор в RabbitMQ Stream через rstream. Поддерживает `async with`.
- `OutboxReader(session_factory, batch_size)`:
  Читает батчи из outbox, помечает обработанными, удаляет старые записи.

## Справочник API

Публичный API, экспортируемый `audit_lib`:

- `AuditMixin`:
  Добавьте к declarative-моделям, чтобы автоматически писать строки в audit outbox.
- `configure_audit(base, service_name=None, serializer=None)`:
  Настраивает audit-модель и listeners; возвращает `AuditOutbox`.
- `setup(base, ...)`:
  Алиас для `configure_audit`.
- `set_audit_user(user_id)`:
  Sync/async context manager, который привязывает `user_id`.
- `set_audit_context(user_id=None, service_name=None)`:
  Sync/async context manager для обоих значений.
- `get_audit_user()`, `get_audit_service()`:
  Читают текущие contextvars.
- `create_audit_model(base)`:
  Создаёт модель `AuditOutbox` на declarative base.
- `create_audit_table(engine)`:
  Создаёт таблицу `audit_outbox` для sync-движков.
- `create_audit_table_async(async_engine)`:
  Асинхронный вариант helper-функции создания таблицы.
- `AuditMiddleware` (`audit_lib.fastapi`):
  ASGI middleware для FastAPI/Starlette — извлекает `sub` из JWT Bearer-токена
  и выставляет `audit_user_var` на время запроса. Требует `audit-lib[fastapi]`.

## Архитектура

1. Транзакция приложения записывает бизнес-данные и строки в `audit_outbox`.
2. `OutboxDaemon` читает `audit_outbox`, сериализует записи в JSON и публикует в RabbitMQ Stream.
3. Downstream-консьюмер может записывать данные в ClickHouse или другое хранилище.

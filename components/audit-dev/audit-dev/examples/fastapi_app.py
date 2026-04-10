"""Пример интеграции audit-lib с FastAPI.

Запуск:
    uvicorn examples.fastapi_app:app --reload

Демон запускается отдельным процессом (см. run_daemon.py).

Необходимые зависимости:
    uv add fastapi uvicorn sqlalchemy[asyncio] asyncpg "audit-lib[fastapi]"
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from audit_lib import AuditMixin, configure_audit
from audit_lib.fastapi import AuditMiddleware

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/mydb"


class Base(DeclarativeBase):
    pass


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String, nullable=False)

    # password_hash не попадёт в аудит
    __audit_exclude__ = {"password_hash"}


AuditOutbox = configure_audit(Base, service_name="user-service")

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    await engine.dispose()


app = FastAPI(title="audit-lib example", lifespan=lifespan)
app.add_middleware(AuditMiddleware)


class UserCreate(BaseModel):
    email: str
    name: str
    password: str


class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}


@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Создание пользователя.

    audit-lib автоматически запишет операцию 'create' в audit_outbox
    в той же транзакции.
    """
    user = User(
        email=body.email,
        name=body.name,
        password_hash=f"hashed_{body.password}",
    )
    session.add(user)
    await session.commit()
    return user


@app.patch("/users/{id}", response_model=UserOut)
async def update_user(
    id: int,
    body: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Обновление пользователя.

    В audit_outbox попадут только изменённые поля (operation='update').
    """
    user = await session.get(User, id)
    if not user:
        raise HTTPException(404, "User not found")

    if body.email is not None:
        user.email = body.email
    if body.name is not None:
        user.name = body.name
    await session.commit()
    return user


@app.delete("/users/{id}", status_code=204)
async def delete_user(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Удаление пользователя.

    В audit_outbox сохранится snapshot всех полей (operation='delete').
    """
    user = await session.get(User, id)
    if not user:
        raise HTTPException(404, "User not found")

    await session.delete(user)
    await session.commit()

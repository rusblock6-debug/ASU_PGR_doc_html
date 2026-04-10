import logging
from collections.abc import Sequence
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, joinedload

logger = logging.getLogger("Base CRUD")


# Типы для дженериков
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseCRUD[ModelType, CreateSchemaType, UpdateSchemaType]:
    """Базовый класс CRUD операций"""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """Инициализация CRUD класса

        Args:
            model: SQLAlchemy модель
        """
        self.model = model
        self.session = session

    async def get(self, id: int) -> ModelType | None:
        """Получить объект по ID

        Args:
            session: Асинхронная сессия БД
            id: ID объекта

        Returns:
            Объект модели или None
        """
        query = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        result = await self.session.execute(query)
        logger.info("Get by id")
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int | None = None,
        *where_clauses: Any,
        **filters: Any,
    ) -> Sequence[ModelType]:
        """Получить список объектов с пагинацией и фильтрацией

        Args:
            session: Асинхронная сессия БД
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            filters: Параметры фильтрации

        Returns:
            Список объектов модели
        """
        query = select(self.model)

        # Применяем фильтры
        for field, value in filters.items():  # type: ignore[attr-defined]
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
            else:
                logger.info("Attr not found")

        # Применяем произвольные условия where
        for clause in where_clauses:
            query = query.where(clause)

        # query = query.offset(skip)
        if limit:
            query = query.limit(limit)
        query = query.order_by(desc(self.model.id))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        result = await self.session.scalars(query)
        logger.info("Get multi")
        return result.all()

    async def create_obj(self, *, obj_in: CreateSchemaType) -> ModelType:
        """Создать новый объект

        Args:
            session: Асинхронная сессия БД
            obj_in: Pydantic схема для создания

        Returns:
            Созданный объект модели
        """
        obj_in_data = obj_in.model_dump()  # type: ignore[attr-defined]
        session_obj = self.model(**obj_in_data)
        self.session.add(session_obj)
        try:
            await self.session.commit()
            await self.session.refresh(session_obj)
            logger.info("Create obj")
            return session_obj
        except IntegrityError as e:
            raise ValueError(e._message) from e

    async def update_obj(
        self,
        *,
        session_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Обновить объект

        Args:
            session: Асинхронная сессия БД
            session_obj: Объект из БД
            obj_in: Pydantic схема или словарь с данными для обновления

        Returns:
            Обновленный объект модели
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = (
                obj_in.model_dump(exclude_unset=True)  # pyright: ignore[reportAttributeAccessIssue]  # type: ignore[attr-defined]
                if hasattr(obj_in, "model_dump")
                else obj_in.dict(exclude_unset=True)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            )

        for field in update_data:
            if hasattr(session_obj, field):
                setattr(session_obj, field, update_data[field])

        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)
        logger.info("Update obj")
        return session_obj

    async def delete_obj(self, *, id: Any) -> ModelType | None:
        """Удалить объект по ID

        Args:
            session: Асинхронная сессия БД
            id: ID объекта

        Returns:
            Удаленный объект или None
        """
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            logger.info("Delete obj")
        return obj

    async def get_by_field(
        self,
        field: str,
        value: Any,
        relationships: list[str] | None = None,
    ) -> ModelType | None:
        """Получить объект по значению поля

        Args:
            session: Асинхронная сессия БД
            field: Название поля
            value: Значение поля

        Returns:
            Объект модели или None
        """
        if not hasattr(self.model, field):
            return None

        query = select(self.model).where(getattr(self.model, field) == value)

        if relationships:
            for rel in relationships:
                if hasattr(self.model, rel):
                    query = query.options(joinedload(getattr(self.model, rel)))

        result = await self.session.execute(query)
        logger.info("Get by field")
        return result.scalar()

    async def exists(self, id: int) -> bool:
        """Проверить существование объекта по ID

        Args:
            session: Асинхронная сессия БД
            id: ID объекта

        Returns:
            True если объект существует
        """
        obj = await self.get(id)
        logger.debug(f"Exist obj {obj}")
        return obj is not None

    async def count(self, *where_clauses: Any, **filters: Any) -> int:
        """Получить количество объектов с учетом фильтров

        Args:
            session: Асинхронная сессия БД
            filters: Параметры фильтрации

        Returns:
            Количество объектов
        """
        query = select(func.coalesce(func.count(self.model.id), 0))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

        # Применяем фильтры
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        # Применяем произвольные условия where
        for clause in where_clauses:
            query = query.where(clause)

        count = await self.session.scalar(query)
        logger.info("Count obj")
        return count or 0

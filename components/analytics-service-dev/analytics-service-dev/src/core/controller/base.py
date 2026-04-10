# ruff: noqa: W505
# mypy: disable-error-code="type-arg,valid-type,name-defined,arg-type,attr-defined"
"""Базовый контроллер."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.core.dto.scheme.request.filter import FilterParam, FilterRequest
from src.core.dto.scheme.response.count import CountResponse
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.dto.type.filter import FilterType
from src.core.dto.type.query import QueryOperator
from src.core.dto.type.sort import SortTypeEnum
from src.core.exception import NotFoundException, UnprocessableEntityException
from src.core.repository import BaseRepository


class BaseController[ModelType](ABC):
    """Базовый класс для контроллера данных."""

    def __init__(
        self,
        model: ModelType,
        repository: BaseRepository,
        exclude_fields: list[str],
    ):
        self.model_class = model
        self.repository = repository
        self.exclude_fields = exclude_fields

    @abstractmethod
    async def processing_transaction(
        self,
        function: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Метод для обработки транзакции."""
        raise NotImplementedError

    def transactional(function):  # type: ignore
        """Декоратор для транзакций."""

        async def wrapper(self, *args, **kwargs):  # type: ignore
            """Функция-обертка."""
            response = await self.processing_transaction(function, *args, **kwargs)
            return response

        return wrapper

    async def get_by(
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
        unique: bool = False,
    ) -> ModelType | PaginationResponse:
        """Возвращает экземпляр модели, соответствующий значению.

        Args:
            field: Поле для получения.
            value: Значение для совпадения.
            operator: Оператор сравнения.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.
            unique: Уникальность значения.

        Returns:
            Экземпляры модели.
        """
        db_obj = await self.repository.get_by(
            field=field,
            value=value,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_type=sort_type,
            operator=operator,
            unique=unique,
        )
        if not db_obj:
            raise NotFoundException(
                f"{self.model_class.__name__} {field} with value {value} not exist",  # noqa: E501
            )

        if unique:
            return db_obj  # type: ignore[return-value]

        return await self.make_pagination_response(
            data=db_obj,
            skip=skip,
            limit=limit,
            filter_request=FilterRequest(
                filters=[FilterParam(field=field, value=value, operator=operator)],
                type=FilterType.AND,
            ),
        )

    async def get_by_filters(
        self,
        filter_request: FilterRequest | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
        unique: bool = False,
    ) -> ModelType | None | PaginationResponse:
        """Получает экземпляр модели, соответствующий фильтрам.

        Args:
            filter_request: Фильтры для совпадения.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.
            unique: Уникальность значения.

        Returns:
            Экземпляры модели или уникальный экземпляр.
        """
        models = await self.repository.get_by_filters(
            filter_request=filter_request,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_type=sort_type,
            unique=unique,
        )

        if unique:
            if models:
                return models  # type: ignore[return-value]
            else:
                raise NotFoundException(
                    f"Unique {self.model_class.__name__} with provided filters not exist",
                )

        return await self.make_pagination_response(
            data=models,
            skip=skip,
            limit=limit,
            filter_request=filter_request,
        )

    async def count(self, filter_request: FilterRequest | None = None) -> CountResponse:
        """Возвращает количество записей в модели по фильтрам.

        Args:
            filter_request: Фильтры для совпадения.

        Returns:
            Количество записей.
        """
        return CountResponse(
            count=await self.repository.count(filter_request=filter_request),
        )

    async def get_by_id(self, id_: int) -> ModelType:
        """Возвращает экземпляр модели, соответствующий идентификатору.

        Args:
            id_: Идентификатор для совпадения.

        Returns:
            Экземпляр модели.
        """
        db_obj = await self.repository.get_by(field="id", value=id_, unique=True)
        if not db_obj:
            raise NotFoundException(
                f"{self.model_class.__name__} with id: {id_} not found",
            )

        return db_obj  # type: ignore[return-value]

    async def get_by_uuid(self, uuid: UUID) -> ModelType:
        """Возвращает экземпляр модели, соответствующий UUID.

        Args:
            uuid: UUID для совпадения.

        Returns:
            Экземпляр модели.
        """
        db_obj = await self.repository.get_by(field="uuid", value=uuid, unique=True)
        if not db_obj:
            raise NotFoundException(
                f"{self.model_class.__name__} with uuid: {uuid} not found",
            )
        return db_obj  # type: ignore[return-value]

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    ) -> PaginationResponse:
        """Возвращает список записей на основе параметров пагинации.

        Args:
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.

        Returns:
            Список записей.
        """
        response = await self.repository.get_all(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_type=sort_type,
        )

        return await self.make_pagination_response(
            data=response,
            skip=skip,
            limit=limit,
        )

    @transactional
    async def create(self, attributes: dict[str, Any]) -> ModelType:
        """Создает новый объект в базе данных.

        Args:
            attributes: Атрибуты для создания объекта.

        Returns:
            Созданный объект.
        """
        created_model = await self.repository.create(attributes=attributes)
        return created_model

    @transactional
    async def create_model(self, model: ModelType) -> ModelType:
        """Создает новый объект в базе данных.

        Args:
            model: Модель базы данных

        Returns:
            Созданный объект.
        """
        created_model = await self.repository.create_model(model=model)
        return created_model

    @transactional
    async def create_many(
        self,
        attributes_list: list[dict[str, Any]],
    ) -> list[ModelType]:
        """Создать несколько записей за один запрос."""
        created = await self.repository.create_many(attributes_list)
        return created

    @transactional
    async def delete(self, model: ModelType) -> ModelType:
        """Удаляет объект из базы данных.

        Args:
            model: Модель для удаления.

        Returns:
            Удаленный объект.
        """
        deleted_model = await self.repository.delete(model=model)
        return deleted_model

    @transactional
    async def update(self, model: ModelType, attributes: dict[str, Any]) -> ModelType:
        """Обновляет объект в базе данных.

        Args:
            model: Модель для обновления.
            attributes: Атрибуты для обновления объекта.

        Returns:
            Обновленный объект.
        """
        for field in attributes:
            if field in self.exclude_fields:
                raise UnprocessableEntityException(
                    f"Field {field} is prohibited for updating",
                )
        updated_model = await self.repository.update(model=model, attributes=attributes)
        return updated_model

    @transactional
    async def update_by_filters(
        self,
        filter_request: FilterRequest,
        attributes: dict[str, Any],
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет объекты по филтьрам.

        Args:
            filter_request: Фильтры для поиска.
            attributes: Атрибуты для обновления.
            unique: Если True — ожидается ровно одна запись (или ни одной).

        Returns:
            - Один объект или None, если unique=True.
            - Список объектов, если unique=False.
        """
        for field in attributes:
            if field in self.exclude_fields:
                raise UnprocessableEntityException(
                    f"Field {field} is prohibited for updating",
                )

        result = await self.repository.update_by_filters(
            filter_request=filter_request,
            attributes=attributes,
            unique=unique,
        )

        if unique and result is None:
            raise NotFoundException(
                f"Unique {self.model_class.__name__} with provided filters not exist",
            )

        return result

    @transactional
    async def delete_by_filters(
        self,
        filter_request: FilterRequest,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет объекты по фильтрам.

        Args:
            filter_request: Фильтры для поиска.
            unique: Если True — ожидается ровно одна запись (или ни одной).

        Returns:
            - Один объект или None, если unique=True.
            - Список объектов, если unique=False.
        """
        result = await self.repository.delete_by_filters(
            filter_request=filter_request,
            unique=unique,
        )

        if unique and result is None:
            raise NotFoundException(
                f"Unique {self.model_class.__name__} with provided filters not exist",
            )

        return result

    @transactional
    async def update_by(
        self,
        field: str,
        value: Any,
        attributes: dict[str, Any],
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет сущности по одному полю."""
        for f in attributes:
            if f in self.exclude_fields:
                raise UnprocessableEntityException(
                    f"Field {f} is prohibited for updating",
                )

        result = await self.repository.update_by(
            field=field,
            value=value,
            attributes=attributes,
            operator=operator,
            unique=unique,
        )

        if unique and result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} {field} with value {value} not exist",
            )
        return result

    @transactional
    async def delete_by(
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет сущности по одному полю."""
        result = await self.repository.delete_by(
            field=field,
            value=value,
            operator=operator,
            unique=unique,
        )

        if unique and result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} {field} with value {value} not exist",
            )
        return result

    @transactional
    async def update_by_id(self, id_: int, attributes: dict[str, Any]) -> ModelType:
        """Обновляет единственную сущность по её id."""
        for f in attributes:
            if f in self.exclude_fields:
                raise UnprocessableEntityException(
                    f"Field {f} is prohibited for updating",
                )

        result = await self.repository.update_by(
            field="id",
            value=id_,
            attributes=attributes,
            unique=True,
        )
        if result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} with id: {id_} not found",
            )
        return result  # type: ignore[return-value]

    async def update_by_uuid(self, uuid: UUID, attributes: dict[str, Any]) -> ModelType:
        """Обновляет единственную сущность по её id."""
        for f in attributes:
            if f in self.exclude_fields:
                raise UnprocessableEntityException(
                    f"Field {f} is prohibited for updating",
                )

        result = await self.repository.update_by(
            field="id",
            value=uuid,
            attributes=attributes,
            unique=True,
        )
        if result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} with uuid: {uuid} not found",
            )
        return result  # type: ignore[return-value]

    @transactional
    async def delete_by_id(self, id_: int) -> ModelType:
        """Удаляет единственную сущность по её id."""
        result = await self.repository.delete_by(field="id", value=id_, unique=True)
        if result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} with id: {id_} not found",
            )
        return result  # type: ignore[return-value]

    @transactional
    async def delete_by_uuid(self, uuid: UUID) -> ModelType:
        """Удаляет единственную сущность по её id."""
        result = await self.repository.delete_by(field="id", value=uuid, unique=True)
        if result is None:
            raise NotFoundException(
                f"{self.model_class.__name__} with uuid: {uuid} not found",
            )
        return result  # type: ignore[return-value]

    @transactional
    async def create_or_update_by(
        self,
        attributes: dict[str, Any],
        update_fields: list[str] | None = None,
    ) -> ModelType:
        """Создать или обновить модель."""
        for f in attributes:
            if f in self.exclude_fields:
                raise UnprocessableEntityException(f"Field {f} is prohibited")
        result = await self.repository.create_or_update_by(
            attributes=attributes,
            update_fields=update_fields,
        )
        if result is None:
            raise NotFoundException("Failed to insert or update")
        return result

    async def make_pagination_response(
        self,
        data: Sequence,
        skip: int = 0,
        limit: int = 100,
        filter_request: FilterRequest | None = None,
    ) -> PaginationResponse:
        """Возвращает ответ для пагинации с численными полями.

        Args:
            data: Сущность или список сущностей ответа.
            skip: Кол-во записей для пропуска.
            limit: Кол-во записей для возврата.
            filter_request: Фильтры для совпадения.
        """
        total_count = (await self.count(filter_request=filter_request)).count
        page = skip // limit + 1 if limit > 0 else 1
        page_size = len(data)
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return PaginationResponse(
            data=list(data),
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )

    @staticmethod
    async def extract_attributes_from_schema(
        schema: BaseModel,
        excludes: set[str | int] | None = None,
    ) -> dict[str, Any]:
        """Извлекает атрибуты из схемы.

        Args:
            schema: Схема для извлечения атрибутов.
            excludes: Атрибуты для исключения.

        Returns:
            Атрибуты.
        """
        return schema.model_dump(exclude=excludes, exclude_unset=True)

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта.

        Returns:
            Строковое представление объекта.
        """
        return f"<{self.__class__.__name__}>"

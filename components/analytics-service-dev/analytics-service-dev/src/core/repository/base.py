# ruff: noqa: W505
# mypy: disable-error-code="name-defined,valid-type"
"""Базовый репозиторий."""

from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Any

from src.core.dto.scheme.request.filter import FilterParam, FilterRequest
from src.core.dto.type.filter import FilterType
from src.core.dto.type.query import QueryOperator
from src.core.dto.type.sort import SortTypeEnum
from src.core.exception import BadRequestException, FieldException


class BaseRepository[ModelType, SessionType, QueryType](ABC):
    """Базовый класс для репозиториев данных."""

    def __init__(self, model: ModelType, db_session: SessionType):
        self.session = db_session
        self.model_class = model

    @abstractmethod
    async def create(self, attributes: dict[str, Any]) -> ModelType:
        """Создает экземпляр модели.

        Args:
            attributes: Атрибуты для создания модели.

        Returns:
            Созданный экземпляр модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_model(self, model: ModelType) -> ModelType:
        """Создает экземпляр модели.

        Args:
            model: Модель базы данных.

        Returns:
            Созданный экземпляр модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_many(
        self,
        attributes_list: list[dict[str, Any]],
    ) -> list[ModelType]:
        """Создает несколько экземпляров модели за раз."""
        raise NotImplementedError

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    ) -> list[ModelType]:
        """Возвращает список экземпляров модели.

        Args:
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.

        Returns:
            Список экземпляров модели.
        """
        query = self._query()
        query = self._sort_by(query=query, sort_by=sort_by, sort_type=sort_type)
        query = self._paginate(query=query, skip=skip, limit=limit)

        return await self._all(query)

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
    ) -> ModelType | None | list[ModelType]:
        """Возвращает экземпляр модели, соответствующий полю и значению.

        Args:
            field: Поле для совпадения.
            value: Значение для совпадения.
            operator: Оператор сравнения.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.
            unique: Уникальный параметр.

        Returns:
            Экземпляр модели.
        """
        query = self._query()
        query = self._maybe_join(query=query, field=field)
        query = self._filter(
            query=query,
            filter_request=FilterRequest(
                filters=[FilterParam(field=field, value=value, operator=operator)],
                type=FilterType.OR,
            ),
        )

        if unique:
            return await self._one_or_none(query)

        query = self._sort_by(query=query, sort_by=sort_by, sort_type=sort_type)
        query = self._paginate(query=query, skip=skip, limit=limit)

        return await self._all(query)

    async def get_by_filters(
        self,
        filter_request: FilterRequest | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Возвращает экземпляры модели, соответствующие фильтрам.

        Args:
            filter_request: Фильтры для совпадения.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.
            unique: Уникальная запись.

        Returns:
            Список экземпляров модели.
        """
        query = self._query()
        if filter_request is not None and len(filter_request.filters) > 0:
            for param in filter_request.filters:
                query = self._maybe_join(query=query, field=param.field)

            query = self._filter(query=query, filter_request=filter_request)

        data: ModelType | None | list[ModelType]

        if unique:
            data = await self._one_or_none(query)
        else:
            query = self._sort_by(query=query, sort_by=sort_by, sort_type=sort_type)
            query = self._paginate(query=query, skip=skip, limit=limit)

            data = await self._all(query)

        return data

    async def count(self, filter_request: FilterRequest | None = None) -> int:
        """Возвращает кол-во записей, соответствующих фильтрам.

        Args:
            filter_request: Фильтры для совпадения.

        Returns:
            Кол-во записей.
        """
        query = self._query()
        if filter_request is not None and len(filter_request.filters) > 0:
            for param in filter_request.filters:
                query = self._maybe_join(query=query, field=param.field)
            query = self._filter(query, filter_request)
        return await self._count(query)

    @abstractmethod
    async def update(self, model: ModelType, attributes: dict[str, Any]) -> ModelType:
        """Обновляет экземпляр модели с заданными атрибутами.

        Args:
            model: Модель для обновления.
            attributes: Атрибуты для обновления экземпляра модели.

        Returns:
            Обновленный экземпляр модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_by(
        self,
        field: str,
        value: Any,
        attributes: dict[str, Any],
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет сущности, найденные по заданному условию, за один запрос.

        Args:
            field: Поле для поиска.
            value: Значение для поиска.
            attributes: Словарь {поле: значение} для обновления.
            operator: Оператор сравнения (по умолчанию EQUALS).
            unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            - Если unique=True, возвращается одна обновлённая сущность или None,
              если ничего не найдено.
            - Если unique=False, возвращается список всех обновлённых сущностей
              (включая пустой список, если ничего не найдено).
        """
        raise NotImplementedError

    @abstractmethod
    async def update_by_filters(
        self,
        filter_request: FilterRequest,
        attributes: dict[str, Any],
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет экземпляры модели по фильтрам.

        Args:
           filter_request: Фильтры для поиска.
           attributes: Атрибуты для обновления экземпляров модели.
           unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            Обновлённые экземпляры модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, model: ModelType) -> ModelType:
        """Удаляет экземпляр модели.

        Args:
            model: Модель для удаления.

        Returns:
            Удаленный экземпляр модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_by(
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет сущности, найденные по заданному условию, за один запрос.

        Args:
            field: Поле для поиска.
            value: Значение для поиска.
            operator: Оператор сравнения (по умолчанию EQUALS).
            unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            - Если unique=True, возвращается одна удаленная сущность или None,
              если ничего не найдено.
            - Если unique=False, возвращается список всех удаленных сущностей
              (включая пустой список, если ничего не найдено).
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_by_filters(
        self,
        filter_request: FilterRequest,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет экземпляры модели по фильтрам.

        Args:
           filter_request: Фильтры для поиска.
           unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            Удалённые экземпляры модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_or_update_by(
        self,
        attributes: dict[str, Any],
        update_fields: list[str] | None = None,
    ) -> ModelType:
        """Создать или обновить модель."""
        raise NotImplementedError

    @abstractmethod
    def _query(self) -> QueryType:
        """Возвращает вызываемый объект, который можно использовать для запроса модели.

        Returns:
            Вызываемый объект, который можно использовать для запроса модели.
        """
        raise NotImplementedError

    @abstractmethod
    def _maybe_join(self, query: QueryType, field: str) -> QueryType:
        """Возвращает запрос, который может указать на использование связанной сущности.

        Returns:
            Запрос со связанной сущностью.
        """
        raise NotImplementedError

    @abstractmethod
    async def _all(self, query: QueryType) -> list[ModelType]:
        """Возвращает все результаты запроса.

        Args:
            query: Запрос для выполнения.

        Returns:
            Список экземпляров модели.
        """
        raise NotImplementedError

    @abstractmethod
    async def _one_or_none(self, query: QueryType) -> ModelType | None:
        """Возвращает первый результат запроса или None.

        Args:
            query: Запрос для выполнения.

        Returns:
            Экземпляр модели.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_by[ExpressionType](
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
    ) -> ExpressionType:  # type: ignore[type-var]
        """Возвращает запрос по указанному полю.

        Args:
            field: Колонка для фильтрации.
            value: Значение для фильтрации.
            operator: Оператор сравнения.

        Notes:
            В этом месте происходит валидация поля и значения.

        Returns:
            Выражение для нужного оператора.
        """
        raise NotImplementedError

    @abstractmethod
    def _filter(self, query: QueryType, filter_request: FilterRequest) -> QueryType:
        """Добавляет фильтры для query.

        Args:
            query: Запрос.
            filter_request: Запрос для фильтров.

        Notes:
            Использует _get_by для получения значения поля.

        Returns:
            Запрос(QueryType)
        """
        raise NotImplementedError

    @abstractmethod
    async def _count(self, query: QueryType) -> int:
        """Возвращает количество записей.

        Args:
            query: Запрос для выполнения.

        Returns:
            Количество экземпляров модели.
        """
        raise NotImplementedError

    @abstractmethod
    def _paginate(self, query: QueryType, skip: int = 0, limit: int = -1) -> QueryType:
        """Возвращает запрос, в котором применена пагинация.

        Args:
            query: Запрос для сортировки.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.

        Returns:
            Отпагиннированный запрос.
        """
        raise NotImplementedError

    @abstractmethod
    def _sort_by(
        self,
        query: QueryType,
        sort_by: str | None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    ) -> QueryType:
        """Возвращает запрос, отсортированный по указанной колонке.

        Args:
            query: Запрос для сортировки.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.

        Returns:
            Отсортированный запрос.
        """
        raise NotImplementedError

    def _get_deep_unique_from_dict(
        self,
        columns: dict[str, Any],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Рекурсивно обходит словарь/список/примитив.

        1) Если встретили словарь - углубляемся по ключам.
        2) Если встретили список из словарей - собираем уникальные значения по
            ключам, рекурсивно обрабатывая значения.
        3) Если встретили список "простых" (или смешанных) элементов - рекурсивно
            обрабатываем каждый элемент и сохраняем только уникальные.
        4) Если встретили примитив (int, str, bool и т.д.) - возвращаем как есть.
        """
        # Если это словарь, обрабатываем по ключам
        if isinstance(columns, dict):
            result = {}
            for key, value in columns.items():
                result[key] = self._get_deep_unique_from_dict(value)
            return result

        # Если это список
        elif isinstance(columns, list):
            # Проверяем, что все элементы - словари
            if all(isinstance(item, dict) for item in columns):
                # Собираем уникальные значения по ключам
                aggregated = defaultdict(list)
                for item in columns:
                    for k, v in item.items():
                        processed_v = self._get_deep_unique_from_dict(v)
                        if processed_v not in aggregated[k]:
                            aggregated[k].append(processed_v)
                return self._get_deep_unique_from_dict(aggregated)

            else:
                # Список не из одних dict (или смешанный) — рекурсивно обрабатываем каждый элемент
                processed_list = []
                for item in columns:
                    processed_item = self._get_deep_unique_from_dict(item)
                    if processed_item not in processed_list:
                        processed_list.append(processed_item)
                return processed_list

        # Если это не список и не словарь (примитив: int, str, bool, и т.п.)
        else:
            return columns

    @staticmethod
    def _check_field_relation_depth(field: str, depth: int = 1) -> None:
        if field.count(".") > depth:
            raise BadRequestException(f"Supported relation depth no more than {depth}")

    def _get_model_field_type(self, _model: ModelType, _field: str) -> type:
        """Получить python-style тип поля."""
        raise NotImplementedError

    def _resolve_field_relation(self, field: str) -> tuple[ModelType, str]:
        """Получение модели и имени колонки из поля."""
        raise NotImplementedError

    def _validate_params(self, field: str, value: Any | None = None) -> None:
        """Валидация параметров по наличию поля в модели и типу значения."""
        model, column_name = self._resolve_field_relation(field)

        model_field_type = self._get_model_field_type(model, column_name)
        if issubclass(model_field_type, dict):
            return None
        if issubclass(model_field_type, Enum):
            if all(value != item for item in model_field_type):
                raise FieldException(
                    f"Value {value} is not permissible for the field {field}. "
                    f"Available values: {[e for e in model_field_type]}",
                )
            enum_member = next(iter(model_field_type)).value
            model_field_type = type(enum_member)
        if value is not None and not isinstance(value, model_field_type):
            raise FieldException(
                f"Wrong type for field {field}: "
                f"expected {model_field_type.__name__}, "
                f"received {type(value).__name__}",
            )
        return None

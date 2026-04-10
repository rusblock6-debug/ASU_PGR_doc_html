"""SQLAlchemy модели для Trip Service.

Таблицы:
1. shift_tasks - Смены с заданиями
2. tasks - Задания для выполнения
3. cycles - Циклы работы техники (полный цикл от moving_empty до unloading)
4. trips - Рейсы (часть цикла с грузом: moving_loaded → unloading)
5. cycle_state_history - История состояний State Machine (TimescaleDB hypertable)
6. cycle_tag_history - История меток локации (TimescaleDB hypertable)
7. cycle_analytics - Аналитические метрики циклов (TimescaleDB hypertable)
"""

from datetime import datetime
from typing import Any

from audit_lib import AuditMixin, configure_audit
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, generate_uuid
from app.enums import RemainingChangeTypeEnum, ShiftTaskStatusEnum, TripStatusRouteEnum
from app.enums.dispatcher_assignments import DispatcherAssignmentStatusEnum
from app.enums.route_tasks import TypesRouteTaskEnum
from app.enums.vechicle_tag_event import VechicleTagEventEnum


class ShiftTask(Base, TimestampMixin, AuditMixin):
    """Модель задания на смену от enterprise-service.

    - id: str (PK) - идентификатор смены
    - work_regime_id: int - ID режима работы
    - vehicle_id: int - ID транспортного средства
    - shift_date: str - дата смены
    - shift_num: int - номер смены
    - task_name: Optional[str] - название задания
    - priority: int - приоритет
    - status: str - статус (pending/in_progress/completed/cancelled)
    - sent_to_board_at: datetime - когда отправлено на борт
    - acknowledged_at: datetime - когда подтверждено
    - started_at: datetime - когда начато
    - completed_at: datetime - когда завершено

    Связанные задания (route_tasks) хранятся в отдельной таблице RouteTask.
    """

    __tablename__ = "shift_tasks"

    # Основные поля (формат enterprise-service)
    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_uuid,
    )
    work_regime_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shift_date: Mapped[str] = mapped_column(String(50), nullable=False)
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    task_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ShiftTaskStatusEnum] = mapped_column(
        Enum(ShiftTaskStatusEnum, native_enum=False),
        default=ShiftTaskStatusEnum.PENDING,
        nullable=False,
        index=True,
    )

    # Временные метки жизненного цикла задания
    sent_to_board_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Дополнительные данные (если нужны)
    task_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationship для автосериализации
    route_tasks: Mapped[list["RouteTask"]] = relationship(
        "RouteTask",
        back_populates="shift_task",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="RouteTask.route_order",
    )

    __table_args__ = (
        Index("ix_shift_tasks_status_created", "status", "created_at"),
        Index("ix_shift_tasks_vehicle_date", "vehicle_id", "shift_date"),
        UniqueConstraint("vehicle_id", "shift_date", "shift_num", name="uq_shift_tasks_vehicle_date_num"),
    )


class RouteTask(Base, TimestampMixin):
    """Модель маршрутного задания (route_task) от enterprise-service.

    - id: str (PK)
    - shift_task_id: str (FK) - связь с ShiftTask
    - route_order: int - порядок выполнения
    - place_a_id: int - ID места погрузки (place.id из graph-service)
    - place_b_id: int - ID места разгрузки (place.id из graph-service)
    - planned_trips_count: int - планируемое количество рейсов
    - actual_trips_count: int - фактическое количество рейсов
    - type_task: TypesRouteTaskEnum - тип задания
    - status: StatusRouteEnum - статус задания
    - route_data: JSONB - данные маршрута.
    """

    __tablename__ = "route_tasks"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_uuid,
    )
    shift_task_id: Mapped[str] = mapped_column(
        ForeignKey("shift_tasks.id", ondelete="CASCADE", deferrable=True),
        nullable=False,
        index=True,
    )

    # Маршрут
    route_order: Mapped[int] = mapped_column(Integer, nullable=False)
    type_task: Mapped[TypesRouteTaskEnum] = mapped_column(
        Enum(TypesRouteTaskEnum, native_enum=False),
        nullable=False,
    )
    place_a_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    place_b_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Счетчики рейсов
    planned_trips_count: Mapped[int] = mapped_column(Integer, default=1)
    actual_trips_count: Mapped[int] = mapped_column(Integer, default=0)

    # Статус и данные
    status: Mapped[TripStatusRouteEnum] = mapped_column(
        Enum(TripStatusRouteEnum, native_enum=False),
        default=TripStatusRouteEnum.EMPTY,
        nullable=False,
        index=True,
    )
    route_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    volume: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Объем груза")
    weight: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Вес груза")
    message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Сообщение/комментарий к маршруту",
    )

    # Relationship (для MQTT - получение vehicle_id через shift_task)
    shift_task: Mapped["ShiftTask"] = relationship(
        "ShiftTask",
        back_populates="route_tasks",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_route_tasks_shift_order", "shift_task_id", "route_order"),
        Index("ix_route_tasks_status_place_a", "status", "place_a_id"),
        # TODO: UniqueConstraint не имеет смысла так как id всегда уникальный, соответсвено составной ключ тоже будет
        #  всегда уникальным и данный фильтр будет всегда true
        # UniqueConstraint("shift_task_id", "id", name="uq_shift_route_task"),
    )


class ShiftRouteTemplate(Base, TimestampMixin):
    """Шаблон маршрута для конкретной смены.

    Хранит пары (place_a_id, place_b_id), которые должны отображаться
    в сводке маршрутов даже при отсутствии наряд-заданий.
    """

    __tablename__ = "shift_route_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shift_date: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    place_a_id: Mapped[int] = mapped_column(Integer, nullable=False)
    place_b_id: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "shift_date",
            "shift_num",
            "place_a_id",
            "place_b_id",
            name="uq_shift_route_templates_shift_place",
        ),
    )


class DispatcherAssignment(Base, TimestampMixin):
    """Назначение диспетчером нового маршрута или гаража для техники.

    Хранит «переход» техники из текущего состояния (маршрут / нет задания / гараж)
    в целевое (маршрут или конкретный гараж) в рамках смены.

    Статусы:
    - pending  — назначение создано, ждём подтверждения борта
    - approved — борт подтвердил, назначение применено
    - rejected — борт отклонил, назначение отменено
    """

    __tablename__ = "dispatcher_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shift_date: Mapped[str] = mapped_column(String(50), nullable=False)
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Источник назначения: ROUTE / NO_TASK / GARAGE
    source_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Тип источника: ROUTE | NO_TASK | GARAGE",
    )
    source_route_place_a_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_route_place_b_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_garage_place_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="ID place (type=park), если источник — конкретный гараж",
    )

    # Цель назначения: ROUTE / GARAGE (конкретный park)
    target_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Тип цели: ROUTE | GARAGE",
    )
    target_route_place_a_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_route_place_b_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_garage_place_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="ID place (type=park), если цель — конкретный гараж",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DispatcherAssignmentStatusEnum.PENDING.value,
        comment="PENDING | APPROVED | REJECTED",
    )

    __table_args__ = (
        Index(
            "ix_dispatcher_assignments_vehicle_shift",
            "vehicle_id",
            "shift_date",
            "shift_num",
        ),
    )


class Cycle(Base, TimestampMixin):
    """Модель цикла работы техники.

    Цикл - это полный цикл работы от начала движения порожним до разгрузки:
    moving_empty → stopped_empty → loading → moving_loaded → stopped_loaded → unloading

    Цикл может содержать рейс (если была погрузка и движение с грузом),
    или может быть без рейса (например, ремонтный цикл).

    Trip наследуется от Cycle через Joined Table Inheritance (JTI).

    TimescaleDB hypertable (по полю created_at).
    """

    __tablename__ = "cycles"

    cycle_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_uuid,
    )
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Связь с заданием и сменой
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Места начала и конца цикла (ID из таблицы places graph-service)
    from_place_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Место начала движения порожним
    to_place_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Место разгрузки

    # Временные метки цикла
    cycle_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )  # Начало moving_empty
    cycle_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )  # Завершение unloading

    # Источник создания цикла
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        index=True,
    )  # dispatcher, system

    # Статус цикла
    cycle_status: Mapped[str] = mapped_column(
        String(50),
        default="in_progress",
        nullable=False,
        index=True,
    )  # in_progress, completed, cancelled

    # Тип цикла (бизнес-логика)
    # Значения: "normal" (обычный), "repair" (ремонт), "maintenance" (ТО), "refueling" (заправка)
    cycle_type: Mapped[str] = mapped_column(
        String(50),
        default="normal",
        nullable=False,
        index=True,
    )

    # Тип сущности для JTI (техническое поле для SQLAlchemy polymorphism)
    # Значения: "cycle" (базовый Cycle), "trip" (Trip с грузом)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        default="cycle",
        nullable=False,
    )

    # Дополнительные метаданные
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_cycles_vehicle_created", "vehicle_id", "created_at"),
        Index("ix_cycles_status_created", "cycle_status", "created_at"),
        Index("ix_cycles_task_id", "task_id"),
        Index("ix_cycles_type", "cycle_type"),
    )

    # JTI: Joined Table Inheritance configuration
    __mapper_args__ = {
        "polymorphic_identity": "cycle",
        "polymorphic_on": entity_type,
    }


class Trip(Cycle):
    """Модель рейса - специализация цикла с грузом.

    Наследуется от Cycle через Joined Table Inheritance (JTI).
    Все поля Cycle доступны в Trip + дополнительные поля для рейса.

    Рейс - это специализация цикла, где есть движение с грузом (moving_loaded → unloading).
    Trip использует cycle_id как первичный ключ (нет отдельного trip_id).

    Поля из Cycle доступны автоматически:
    - cycle_id (PK)
    - vehicle_id
    - task_id
    - shift_id
    - from_place_id, to_place_id
    - cycle_started_at, cycle_completed_at
    - cycle_status
    - cycle_type (установлен в 'trip')
    - extra_data

    TimescaleDB hypertable (по полю created_at).
    """

    __tablename__ = "trips"

    # PK и FK на cycles.cycle_id (для JTI)
    cycle_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cycles.cycle_id", deferrable=True),
        primary_key=True,
    )

    # Специфичные поля для Trip
    cycle_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trip_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # planned, unplanned

    # Временные метки рейса
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Данные о погрузке (ID места из таблицы places graph-service)
    loading_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loading_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loading_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Данные о разгрузке (ID места из таблицы places graph-service)
    unloading_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unloading_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unloading_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Примечание: created_at и updated_at наследуются от Cycle и находятся в таблице cycles
    # Индексы на наследуемые поля создаются в родительской таблице

    # JTI: polymorphic identity для Trip
    __mapper_args__ = {
        "polymorphic_identity": "trip",
    }


class CycleStateHistory(Base):
    """История состояний State Machine для цикла.

    Каждая запись - это переход в новое состояние с полными данными State Machine.
    Состояния относятся ко всему циклу работы техники, включая этапы без рейса.

    TimescaleDB hypertable (по полю timestamp).
    """

    __tablename__ = "cycle_state_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cycle_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Данные State Machine
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    state_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    place_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="ID места")
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="system",
        comment="Источник изменения: dispatcher или system",
    )
    task_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="ID задачи (UUID4)")

    # Триггер перехода
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_cycle_state_history_vehicle_timestamp", "vehicle_id", "timestamp"),
        Index("ix_cycle_state_history_cycle_timestamp", "cycle_id", "timestamp"),
    )


class CycleTagHistory(Base):
    """История меток локации для цикла.

    Каждая запись - это событие получения новой метки от graph-service.
    Метки регистрируются в течение всего цикла, включая этапы без рейса.

    Сохраняется и point_id (tag.point_id), и place_id (place.id) для связи.

    TimescaleDB hypertable (по полю timestamp).
    """

    __tablename__ = "cycle_tag_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cycle_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Данные метки - сохраняем и point_id (tag.point_id), и place_id (place.id)
    # point_id: Mapped[str] = mapped_column(String(255), nullable=False)
    place_id: Mapped[int | None] = mapped_column(Integer, nullable=False)
    place_name: Mapped[str | None] = mapped_column(String, nullable=False)
    place_type: Mapped[str | None] = mapped_column(String, nullable=False)

    # Дополнительные данные от graph-service
    # extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    tag_id: Mapped[int | None] = mapped_column(Integer, nullable=False, index=True)
    tag_name: Mapped[str | None] = mapped_column(String, nullable=False)
    tag_event: Mapped[VechicleTagEventEnum] = mapped_column(
        ENUM(VechicleTagEventEnum),
        name="tag_event",
        default=VechicleTagEventEnum.entry,
        server_default=VechicleTagEventEnum.entry,
    )

    __table_args__ = (
        Index("ix_cycle_tag_history_vehicle_timestamp", "vehicle_id", "timestamp"),
        Index("ix_cycle_tag_history_cycle_timestamp", "cycle_id", "timestamp"),
        Index("ix_cycle_tag_history_place_id", "place_id"),
    )


class CycleAnalytics(Base, TimestampMixin):
    """Аналитические метрики цикла.

    Вычисляются при завершении цикла и сохраняются для дальнейшего анализа.
    Цикл включает все этапы работы техники от moving_empty до unloading.

    Если в цикле есть рейс, то аналитика включает данные рейса.
    Если рейса нет (ремонтный цикл), то некоторые поля будут NULL.

    TimescaleDB hypertable (по полю created_at).
    """

    __tablename__ = "cycle_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cycle_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,  # unique=True автоматически создает индекс
    )
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Дополнительная информация о цикле
    shift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cycle_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cycle_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Дополнительная информация о рейсе (если есть)
    trip_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trip_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Места цикла (ID из таблицы places graph-service)
    from_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Временные метки цикла
    cycle_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cycle_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Временные метки рейса (если есть)
    trip_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trip_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Временные метрики
    total_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_empty_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    stopped_empty_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    loading_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    moving_loaded_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    stopped_loaded_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unloading_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Количество переходов состояний
    state_transitions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Дополнительная аналитика
    analytics_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_cycle_analytics_vehicle_created", "vehicle_id", "created_at"),
        Index("ix_cycle_analytics_cycle_id", "cycle_id"),
    )


class PlaceRemainingHistory(Base, TimestampMixin):
    """История изменений остатков по местам."""

    __tablename__ = "place_remaining_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # UUID из сообщения или сгенерированный
    place_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # ID места из graph-service (внешний)
    change_type: Mapped[RemainingChangeTypeEnum] = mapped_column(
        Enum(RemainingChangeTypeEnum, name="remaining_change_type"),
        nullable=False,
    )
    change_amount: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Дополнительные поля для связи с рейсом (опционально)
    # Для manual корректировок по месту параметры могут быть неизвестны
    cycle_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    task_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    shift_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Источник изменения
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        server_default="system",
    )  # system, dispatcher

    __table_args__ = (
        Index("ix_place_remaining_history_cycle_id", "cycle_id"),
        Index("ix_place_remaining_history_timestamp", "timestamp"),
    )


class FullShiftStateHistory(Base, TimestampMixin):
    """Обобщенная история состояний смен.

    Хранит один агрегированный статус на каждую смену каждого vehicle.
    Рассчитывается периодической таской на основе cycle_state_history.

    Правила расчета state:
    - 'no_data': нет записей в cycle_state_history или только статусы 'no_data'
    - 'work': более 60% записей в cycle_state_history имеют cycle_id
    - 'idle': менее или равно 60% записей имеют cycle_id
    """

    __tablename__ = "full_shift_state_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False)
    shift_date: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Время начала соответствующей смены",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="system",
        comment="Источник данных",
    )
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Флаг обработки/пересчета записи",
    )
    idle_duration: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Длительность простоя в секундах (статусы с is_work_status=false)",
    )
    work_duration: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Длительность работы в секундах (статусы с is_work_status=true)",
    )

    __table_args__ = (
        Index(
            "ix_full_shift_state_history_vehicle_shift",
            "vehicle_id",
            "shift_date",
            "shift_num",
            unique=True,
        ),
        Index(
            "ix_full_shift_state_history_is_processed",
            "is_processed",
            postgresql_where=text("is_processed = false"),
        ),
    )


AuditOutbox = configure_audit(Base, service_name="trip-service")

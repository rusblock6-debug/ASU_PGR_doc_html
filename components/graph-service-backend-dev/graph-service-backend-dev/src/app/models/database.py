"""SQLAlchemy модели для graph-service"""

# в случае миграции на python 14+ удалить импорт `__future__`
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from audit_lib import AuditMixin, configure_audit
from audit_lib.serializers import default_serializer
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

from app.enum.edges import RoadDirectionEnum
from app.enum.places import PlaceTypeEnum
from app.models import TimestampMixin


class Base(DeclarativeBase):
    pass


def _audit_serializer(val):
    if isinstance(val, WKBElement):
        return to_shape(val).wkt
    return default_serializer(val)


AuditOutbox = configure_audit(Base, service_name="graph-service", serializer=_audit_serializer)


# Ассоциативная таблица для связи многие-ко-многим между Shaft и Horizon
shaft_horizons = Table(
    "shaft_horizons",
    Base.metadata,
    Column(
        "shaft_id",
        Integer,
        ForeignKey(
            "shafts.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    ),
    Column(
        "horizon_id",
        Integer,
        ForeignKey(
            "horizons.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    ),
)


# Ассоциативная таблица для связи многие-ко-многим между Section и Horizon
section_horizons = Table(
    "section_horizons",
    Base.metadata,
    Column(
        "section_id",
        Integer,
        ForeignKey(
            "sections.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    ),
    Column(
        "horizon_id",
        Integer,
        ForeignKey(
            "horizons.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    ),
)

# Ассоциативная таблица для связи многие-ко-многим между GraphNode и Ladder
node_ladders = Table(
    "node_ladders",
    Base.metadata,
    Column(
        "node_id",
        Integer,
        ForeignKey(
            "graph_nodes.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    ),
    Column(
        "ladder_id",
        Integer,
        ForeignKey("ladders.id", deferrable=True, initially="IMMEDIATE"),
        primary_key=True,
    ),
)


class Shaft(Base, TimestampMixin, AuditMixin):
    """Модель шахты"""

    __tablename__ = "shafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    # Отношения (многие-ко-многим)
    horizons: Mapped[list[Horizon]] = relationship(
        secondary=shaft_horizons,
        back_populates="shafts",
        lazy="selectin",
    )


class MapSetting(Base, TimestampMixin, AuditMixin):
    """Глобальные настройки карты."""

    __tablename__ = "map_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    routes_color: Mapped[str] = mapped_column(
        "RoutesColor",
        String(7),
        default="#6A848B",
        server_default="#6A848B",
    )


class Horizon(Base, TimestampMixin, AsyncAttrs, AuditMixin):
    """Модель горизонта шахты"""

    __tablename__ = "horizons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    height: Mapped[float] = mapped_column(Float)
    color: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        default="#2196F3",
    )  # HEX цвет для визуализации (#RRGGBB)

    # Отношения (многие-ко-многим)
    shafts: Mapped[list[Shaft]] = relationship(
        secondary=shaft_horizons,
        back_populates="horizons",
        lazy="selectin",
    )
    nodes: Mapped[list[GraphNode]] = relationship(
        back_populates="horizon",
        cascade="all, delete-orphan",
    )
    edges: Mapped[list[GraphEdge]] = relationship(
        back_populates="horizon",
        cascade="all, delete-orphan",
    )
    places: Mapped[list[Place]] = relationship(
        secondary="graph_nodes",
        primaryjoin="Horizon.id == GraphNode.horizon_id",
        secondaryjoin="GraphNode.id == Place.node_id",
        viewonly=True,
        lazy="selectin",
    )
    sections: Mapped[list[Section]] = relationship(
        secondary=section_horizons,
        back_populates="horizons",
        lazy="selectin",
    )
    substrate: Mapped[Substrate | None] = relationship(
        back_populates="horizon",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GraphNode(Base, TimestampMixin, AuditMixin):
    """Модель узла графа дорог"""

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    horizon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("horizons.id", deferrable=True, initially="IMMEDIATE"),
        index=True,
    )
    node_type: Mapped[str] = mapped_column(
        String(50),
        default="road",
    )  # road, junction, ladder
    # Для ladder узлов - связь с узлами на других горизонтах
    # Хранит JSON массив ID связанных узлов: {"above": node_id, "below": node_id}
    linked_nodes: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry: Mapped[Any] = mapped_column(
        Geometry("POINTZ", srid=4326),
    )  # 3D геометрия для PostGIS (X, Y, Z)

    ladders: Mapped[list[Ladder]] = relationship(
        secondary=node_ladders,
        back_populates="nodes",
    )
    # Отношения
    horizon: Mapped[Horizon] = relationship(back_populates="nodes")
    # Узлы как начальная точка ребер
    from_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.from_node_id",
        back_populates="from_node",
    )
    # Узлы как конечная точка ребер
    to_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.to_node_id",
        back_populates="to_node",
    )
    place: Mapped[Place] = relationship(
        back_populates="node",
    )


class GraphEdge(Base, TimestampMixin, AuditMixin):
    """Модель ребра графа дорог"""

    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # horizon_id nullable для межгоризонтных ребер (ladder connections)
    horizon_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("horizons.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
        index=True,
    )
    from_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("graph_nodes.id", deferrable=True, initially="IMMEDIATE"),
    )
    to_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("graph_nodes.id", deferrable=True, initially="IMMEDIATE"),
    )
    # Тип ребра: horizontal (на одном горизонте) или vertical (между горизонтами)
    edge_type: Mapped[str] = mapped_column(String(20), default="horizontal")
    direction: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        default=RoadDirectionEnum.bidirectional.value,
        server_default=RoadDirectionEnum.bidirectional.value,
    )
    # 3D геометрия для PostGIS (линия)
    geometry: Mapped[Any] = mapped_column(
        Geometry("LINESTRINGZ", srid=4326),
    )

    # Отношения
    horizon: Mapped[Horizon | None] = relationship(back_populates="edges")
    from_node: Mapped[GraphNode] = relationship(
        foreign_keys=[from_node_id],
        back_populates="from_edges",
    )
    to_node: Mapped[GraphNode] = relationship(
        foreign_keys=[to_node_id],
        back_populates="to_edges",
    )


class Ladder(Base, TimestampMixin):
    """Модель связи между горизонтами (лестница)."""

    __tablename__ = "ladders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_horizon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("horizons.id", ondelete="CASCADE"),
        index=True,
    )
    to_horizon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("horizons.id", ondelete="CASCADE"),
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    is_completed: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    from_horizon: Mapped[Horizon] = relationship(foreign_keys=[from_horizon_id])
    to_horizon: Mapped[Horizon] = relationship(foreign_keys=[to_horizon_id])
    nodes: Mapped[list[GraphNode]] = relationship(
        secondary=node_ladders,
        back_populates="ladders",
    )


# TODO пересмотреть модель, скорее всего есть не нужные поля
class Tag(Base, TimestampMixin, AuditMixin):
    """Модель метки с радиусом действия"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "places.id",
            ondelete="SET NULL",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        nullable=True,
        index=True,
    )
    radius: Mapped[float] = mapped_column(Float, default=25.0)  # радиус действия
    # TODO (человеко читаемый id, node_1), как по мне можно
    #  отказаться от этого свойства и перейти на сквозной id primary_key
    #  tag_name формируется при создании (node + id) и импорте
    #  тут логика чуть по сложнее но иё можно упрозднить
    tag_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )  # Обратная совместимость: beacon_id
    tag_mac: Mapped[str] = mapped_column(String(17), unique=True, index=True)  # MAC адрес метки
    battery_level: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )  # уровень заряда (0-100, только для чтения)
    battery_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )  # Дата изменения уровня заряда

    place: Mapped[Place | None] = relationship(back_populates="tags")


class VehicleLocation(Base, AuditMixin):
    """Модель местоположения транспортного средства"""

    __tablename__ = "vehicle_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(50), index=True)
    horizon_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("horizons.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    # 3D геометрия для PostGIS
    geometry: Mapped[Any] = mapped_column(
        Geometry("POINTZ", srid=4326),
    )


class Place(Base, TimestampMixin, AuditMixin):
    """Базовая модель места (общая для всех типов: load, unload, reload, transit, park)"""

    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[PlaceTypeEnum] = mapped_column(
        Enum(PlaceTypeEnum, name="place_type"),
        index=True,
    )
    cargo_type: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # TODO: rename to load_type_id !!
    node_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "graph_nodes.id",
            ondelete="SET NULL",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        unique=True,
    )

    tags: Mapped[list[Tag]] = relationship(back_populates="place")
    # Relationship для связи с Horizon (не сериализуется, используется только horizon_id)
    horizon: Mapped[Horizon | None] = relationship(
        secondary="graph_nodes",
        primaryjoin="Place.node_id == GraphNode.id",
        secondaryjoin="GraphNode.horizon_id == Horizon.id",
        viewonly=True,
        uselist=False,
    )
    node: Mapped[GraphNode | None] = relationship(back_populates="place")

    @hybrid_property
    def geometry(self) -> Any | None:
        """Получить геометрию места через связанный узел"""
        return self.node.geometry if self.node else None

    @geometry.expression  # type: ignore[no-redef]
    def geometry(cls):
        return select(GraphNode.geometry).where(GraphNode.id == cls.node_id).scalar_subquery()

    @hybrid_property
    def horizon_id(self) -> int | None:
        """Получить id горизонта через связанный узел"""
        return self.node.horizon_id if self.node else None

    @horizon_id.expression  # type: ignore[no-redef]
    def horizon_id(cls):
        return select(GraphNode.horizon_id).where(GraphNode.id == cls.node_id).scalar_subquery()

    __mapper_args__ = {
        "polymorphic_on": type,
    }
    __table_args__ = (UniqueConstraint("name", name="uq_places_name"),)


class LoadPlace(Place):
    """Место погрузки"""

    __tablename__ = "place_load"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "places.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_stock: Mapped[float | None] = mapped_column(Float, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": PlaceTypeEnum.load,
    }


class UnloadPlace(Place):
    """Место разгрузки"""

    __tablename__ = "place_unload"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "places.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_stock: Mapped[float | None] = mapped_column(Float, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": PlaceTypeEnum.unload,
    }


class ReloadPlace(Place):
    """Место перегрузки"""

    __tablename__ = "place_reload"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "places.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        primary_key=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_stock: Mapped[float | None] = mapped_column(Float, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": PlaceTypeEnum.reload,
    }


class ParkPlace(Place):
    """Место стоянки"""

    __mapper_args__ = {
        "polymorphic_identity": PlaceTypeEnum.park,
    }


class TransitPlace(Place):
    """Транзитное место"""

    __mapper_args__ = {
        "polymorphic_identity": PlaceTypeEnum.transit,
    }


class Section(Base, TimestampMixin, AuditMixin):
    """Базовая модель участков"""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_contractor_organization: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Отношения (многие-ко-многим)
    horizons: Mapped[list[Horizon]] = relationship(
        secondary=section_horizons,
        back_populates="sections",
        lazy="selectin",
    )


class Substrate(Base, TimestampMixin, AuditMixin):
    """Модель подложки для горизонта"""

    __tablename__ = "substrates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Связь один-к-одному с Horizon (опциональная)
    horizon_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "horizons.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        nullable=True,
        unique=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    path_s3: Mapped[str] = mapped_column(String(500))
    opacity: Mapped[int] = mapped_column(
        Integer,
        default=100,
        server_default="100",
    )
    center: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"x": 0.0, "y": 0.0},
        server_default=text('\'{"x": 0.0, "y": 0.0}\'::jsonb'),
    )

    # Отношение с Horizon для подгрузки при сериализации
    horizon: Mapped[Horizon | None] = relationship(
        back_populates="substrate",
        lazy="selectin",
    )

    # быстрая валидация на уровне приложения и ORM
    @validates("opacity")
    def validate_opacity(self, key, value):
        if not (0 <= value <= 100):
            raise ValueError(
                f"Прозрачность должна быть от 0 до 100, получено: {value}",
            )

        return value

    # Защищает данные на уровне БД
    __table_args__ = (
        CheckConstraint(
            text("opacity >= 0 AND opacity <= 100"),
            name="ck_substrate_opacity_range",
        ),
    )

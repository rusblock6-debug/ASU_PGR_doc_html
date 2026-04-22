"""SQLAlchemy модели для всех сущностей."""

from datetime import date
from typing import Any, Optional

from audit_lib import AuditMixin, configure_audit
from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database.base import Base, TimestampMixin
from app.enums.statuses import AnalyticCategoryEnum
from app.enums.vehicles import VehicleStatusEnum, VehicleTypeEnum


class EnterpriseSettings(Base, TimestampMixin, AuditMixin):
    """Параметры предприятия."""

    __tablename__ = "enterprise_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enterprise_name: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coordinates: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    settings_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class WorkRegime(Base, TimestampMixin):
    """Режим работы предприятия (2-сменный, 3-сменный и т.д.).

    Смены вычисляются динамически из shifts_definition.
    """

    __tablename__ = "work_regimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enterprise_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("enterprise_settings.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    shifts_definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class Vehicle(Base, TimestampMixin):
    """Базовая модель транспортного средства.

    Оборудование предприятия
    Single Table Inheritance - все типы в одной таблице.
    """

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enterprise_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("enterprise_settings.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    vehicle_type: Mapped[VehicleTypeEnum] = mapped_column(Enum(VehicleTypeEnum), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("vehicle_models.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[VehicleStatusEnum] = mapped_column(
        Enum(VehicleStatusEnum),
        default=VehicleStatusEnum.active,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    active_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationship к модели транспорта
    model: Mapped[Optional["VehicleModel"]] = relationship("VehicleModel", lazy="joined")

    __mapper_args__ = {
        "polymorphic_on": vehicle_type,
        "polymorphic_identity": VehicleTypeEnum.vehicle,
    }


class Pdm(Vehicle):
    """ПДМ (Погрузочно-доставочная машина)."""

    __mapper_args__ = {
        "polymorphic_identity": VehicleTypeEnum.pdm,
    }


class Shas(Vehicle):
    """ШАС (Шахтный автосамосвал)."""

    __mapper_args__ = {
        "polymorphic_identity": VehicleTypeEnum.shas,
    }


class OrganizationCategory(Base, TimestampMixin):
    """Организационные категории для статусов."""

    __tablename__ = "organization_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Relationship
    statuses: Mapped[list["Status"]] = relationship(
        "Status",
        back_populates="organization_category_rel",
    )


class Status(Base, TimestampMixin):
    """Статусы сущностей."""

    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_name: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    system_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_work_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    analytic_category: Mapped[AnalyticCategoryEnum] = mapped_column(
        Enum(AnalyticCategoryEnum),
        default=AnalyticCategoryEnum.productive,
        nullable=False,
    )
    organization_category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("organization_categories.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )

    # Relationship
    organization_category_rel: Mapped[Optional["OrganizationCategory"]] = relationship(
        "OrganizationCategory",
        back_populates="statuses",
        lazy="joined",
    )


class VehicleModel(Base, TimestampMixin):
    """Модели передвижного оборудования предприятия."""

    __tablename__ = "vehicle_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # Мощность двигателя км.ч.
    max_speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Объём бака л.
    tank_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Грузоподьемность т.
    load_capacity_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Объем кузова\ковша кубов (m^3).
    volume_m3: Mapped[float | None] = mapped_column(Float, nullable=True)

    @validates("engine_power_hp")
    def validate_engine_power_hp(self, key: str, value: int | None) -> int | None:
        """Валидация мощности двигателя."""
        if value is not None and value <= 0:
            raise ValueError("Объём двигателя не может быть отрицательным значением.")
        return value

    @validates("tank_volume")
    def validate_tank_volume(self, key: str, value: float | None) -> float | None:
        """Валидация объёма бака."""
        if value is not None and value <= 0:
            raise ValueError("Объём бака не может быть отрицательным значением.")
        return value

    @validates("load_capacity_tons")
    def validate_load_capacity_tons(self, key: str, value: float | None) -> float | None:
        """Валидация грузоподъёмности."""
        if value is not None and value <= 0:
            raise ValueError("Грузоподьемность не может быть отрицательным значением.")
        return value

    @validates("volume_m3")
    def validate_volume_m3(self, key: str, value: float | None) -> float | None:
        """Валидация объёма кузова."""
        if value is not None and value <= 0:
            raise ValueError(r"Объем кузова\ковша не может быть отрицательным значением.")
        return value

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Валидация имени модели."""
        if len(value) < 1:
            raise ValueError("Имя модели должно содержать хоть один символ.")
        return value


class LoadType(Base, TimestampMixin):
    """Модель вида грузов."""

    __tablename__ = "load_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    density: Mapped[float] = mapped_column(Float, nullable=False)
    color: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "load_type_categories.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        nullable=True,
    )

    # Relationship
    category: Mapped[Optional["LoadTypeCategory"]] = relationship(
        "LoadTypeCategory",
        back_populates="load_types",
        lazy="joined",
    )


class LoadTypeCategory(Base, TimestampMixin):
    """Модель категорий вида грузов."""

    __tablename__ = "load_type_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    is_mineral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationship
    load_types: Mapped[list["LoadType"]] = relationship("LoadType", back_populates="category")


AuditOutbox = configure_audit(
    Base,
    service_name="enterprise-service",
)

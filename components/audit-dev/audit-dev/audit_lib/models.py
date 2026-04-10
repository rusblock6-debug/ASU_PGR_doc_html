"""AuditOutbox SQLAlchemy model definition."""

from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from audit_lib.ids import generate_uuid7


def create_audit_model(base: type[DeclarativeBase]) -> type[Any]:
    """Create the AuditOutbox model bound to the given DeclarativeBase.

    Usage::

        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):
            pass

        AuditOutbox = create_audit_model(Base)
    """

    class AuditOutbox(base):  # type: ignore[valid-type,misc]
        __tablename__ = "audit_outbox"

        id: Mapped[uuid.UUID] = mapped_column(
            sa.Uuid,
            primary_key=True,
            default=generate_uuid7,
        )
        entity_type: Mapped[str] = mapped_column(
            sa.String, nullable=False
        )
        entity_id: Mapped[str] = mapped_column(
            sa.String, nullable=False
        )
        operation: Mapped[str] = mapped_column(
            sa.String, nullable=False
        )
        old_values: Mapped[dict[str, Any] | None] = mapped_column(
            JSONB, nullable=True
        )
        new_values: Mapped[dict[str, Any] | None] = mapped_column(
            JSONB, nullable=True
        )
        user_id: Mapped[str | None] = mapped_column(
            sa.String, nullable=True
        )
        timestamp: Mapped[sa.DateTime] = mapped_column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        )
        processed: Mapped[bool] = mapped_column(
            sa.Boolean, default=False, server_default=sa.sql.expression.false()
        )
        service_name: Mapped[str | None] = mapped_column(
            sa.String, nullable=True
        )

        __table_args__ = (
            sa.Index("ix_audit_outbox_entity", "entity_type", "entity_id"),
            sa.Index("ix_audit_outbox_processed", "processed"),
            sa.Index("ix_audit_outbox_timestamp", "timestamp"),
        )

    return AuditOutbox

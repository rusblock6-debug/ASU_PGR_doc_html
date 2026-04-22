"""Make all foreign keys DEFERRABLE INITIALLY IMMEDIATE.

Revision ID: 025
Revises: 024
Create Date: 2026-02-27
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def _fk_payloads(inspector: sa.Inspector, schema: str | None = None) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for table_name in inspector.get_table_names(schema=schema):
        for fk in inspector.get_foreign_keys(table_name, schema=schema):
            name = fk.get("name")
            if not name:
                continue

            options = fk.get("options") or {}
            payloads.append(
                {
                    "name": name,
                    "source_table": table_name,
                    "source_schema": schema,
                    "referent_table": fk["referred_table"],
                    "referent_schema": fk.get("referred_schema"),
                    "local_cols": fk["constrained_columns"],
                    "remote_cols": fk["referred_columns"],
                    "ondelete": options.get("ondelete"),
                    "onupdate": options.get("onupdate"),
                    "match": options.get("match"),
                }
            )
    return payloads


def _drop_and_recreate(
    fks: Iterable[dict[str, Any]],
    *,
    deferrable: bool,
    initially: str | None = None,
) -> None:
    for fk in fks:
        op.drop_constraint(
            fk["name"],
            fk["source_table"],
            type_="foreignkey",
            schema=fk["source_schema"],
        )

        create_kwargs: dict[str, Any] = {
            "source_schema": fk["source_schema"],
            "referent_schema": fk["referent_schema"],
            "ondelete": fk["ondelete"],
            "onupdate": fk["onupdate"],
            "match": fk["match"],
            "deferrable": deferrable,
        }
        if initially is not None:
            create_kwargs["initially"] = initially

        op.create_foreign_key(
            fk["name"],
            fk["source_table"],
            fk["referent_table"],
            fk["local_cols"],
            fk["remote_cols"],
            **create_kwargs,
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    schema = inspector.default_schema_name
    fks = _fk_payloads(inspector, schema=schema)
    _drop_and_recreate(fks, deferrable=True, initially="IMMEDIATE")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    schema = inspector.default_schema_name
    fks = _fk_payloads(inspector, schema=schema)
    _drop_and_recreate(fks, deferrable=False, initially=None)

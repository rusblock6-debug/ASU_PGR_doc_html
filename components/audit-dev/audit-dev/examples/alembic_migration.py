"""Example Alembic migration for the audit_outbox table.

Copy this into your Alembic ``versions/`` directory and adjust the
``revision`` / ``down_revision`` identifiers to match your migration chain.

Usage
-----
1. Copy this file into ``alembic/versions/``.
2. Adjust ``revision`` and ``down_revision``.
3. Run ``alembic upgrade head``.

Alternatively, you can skip Alembic entirely and call the helper at startup::

    from sqlalchemy import create_engine
    import audit_lib

    engine = create_engine("sqlite:///app.db")
    audit_lib.create_audit_table(engine)

For async engines::

    from sqlalchemy.ext.asyncio import create_async_engine
    import audit_lib

    async_engine = create_async_engine("sqlite+aiosqlite:///app.db")
    await audit_lib.create_audit_table_async(async_engine)
"""

# --- Alembic migration template ---

# revision identifiers, used by Alembic.
revision = "0001_create_audit_outbox"
down_revision = None  # set to your previous migration revision
branch_labels = None
depends_on = None

import sqlalchemy as sa  # noqa: E402
from alembic import op  # type: ignore[import-not-found]  # noqa: E402


def upgrade() -> None:
    op.create_table(
        "audit_outbox",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "processed",
            sa.Boolean(),
            server_default=sa.sql.expression.false(),
            nullable=False,
        ),
        sa.Column("service_name", sa.String(), nullable=True),
    )

    op.create_index(
        "ix_audit_outbox_entity",
        "audit_outbox",
        ["entity_type", "entity_id"],
    )
    op.create_index("ix_audit_outbox_processed", "audit_outbox", ["processed"])
    op.create_index("ix_audit_outbox_timestamp", "audit_outbox", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_audit_outbox_timestamp", table_name="audit_outbox")
    op.drop_index("ix_audit_outbox_processed", table_name="audit_outbox")
    op.drop_index("ix_audit_outbox_entity", table_name="audit_outbox")
    op.drop_table("audit_outbox")

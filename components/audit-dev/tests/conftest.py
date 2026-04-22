"""Shared test fixtures for audit-lib."""

from __future__ import annotations

PG_SYNC_URL = "postgresql://postgres:postgres@localhost:5432/test_audit_lib"
PG_ASYNC_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_audit_lib"

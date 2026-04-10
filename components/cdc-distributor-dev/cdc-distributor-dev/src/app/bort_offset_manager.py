"""Управление per-bort offset'ами для fan-out дистрибуции."""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.db.models import BortStreamOffset


class BortOffsetManager:
    """Менеджер для хранения offset'ов стримов по бортам в PostgreSQL.

    Использует составной ключ (stream_name, bort_id)
    для независимого отслеживания позиции каждого борта в каждом стриме.
    """

    def __init__(self, session_factory: async_sessionmaker[Any]) -> None:
        self._session_factory = session_factory

    async def get_offset(self, stream_name: str, bort_id: int) -> int | None:
        """Получить последний сохранённый offset для (stream, bort)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(BortStreamOffset.offset_value).where(
                    BortStreamOffset.stream_name == stream_name,
                    BortStreamOffset.bort_id == bort_id,
                ),
            )
            row = result.scalar_one_or_none()

            if row is not None:
                logger.info(
                    "Loaded bort offset stream={stream} bort={bort} offset={offset}",
                    stream=stream_name,
                    bort=bort_id,
                    offset=row,
                )
                return row

            logger.info(
                "No offset found stream={stream} bort={bort}, starting from beginning",
                stream=stream_name,
                bort=bort_id,
            )
            return None

    async def get_seq_id(self, stream_name: str, bort_id: int) -> int | None:
        """Получить последний сохранённый seq_id для (stream, bort)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(BortStreamOffset.seq_id).where(
                    BortStreamOffset.stream_name == stream_name,
                    BortStreamOffset.bort_id == bort_id,
                ),
            )
            return result.scalar_one_or_none()

    async def save_offset(
        self,
        stream_name: str,
        bort_id: int,
        offset: int,
        seq_id: int,
    ) -> None:
        """Сохранить offset и seq_id для (stream, bort).

        Вызывается ТОЛЬКО после успешного подтверждения брокером (publisher confirm).
        """
        stmt = (
            insert(BortStreamOffset)
            .values(
                stream_name=stream_name,
                bort_id=bort_id,
                offset_value=offset,
                seq_id=seq_id,
            )
            .on_conflict_do_update(
                index_elements=["stream_name", "bort_id"],
                set_={
                    "offset_value": offset,
                    "seq_id": seq_id,
                    "updated_at": func.now(),
                },
            )
        )

        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

        logger.debug(
            "Saved bort offset stream={stream} bort={bort} offset={offset} seq_id={seq_id}",
            stream=stream_name,
            bort=bort_id,
            offset=offset,
            seq_id=seq_id,
        )

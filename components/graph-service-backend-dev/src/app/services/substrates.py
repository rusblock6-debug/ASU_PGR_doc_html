"""Бизнес-логика для работы с подложками (substrates)."""

import asyncio
import logging
import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.s3.client import get_s3_client
from app.models.database import Substrate
from app.schemas.substrates import (
    SubstrateCreate,
    SubstrateListResponse,
    SubstrateResponse,
    SubstrateUpdate,
    SubstrateWithSvgResponse,
)
from app.services.crud.base import BaseCRUD
from app.services.dxf2svg import dxf_bytes_to_svg_bytes

logger = logging.getLogger(__name__)


class SubstratesServices(BaseCRUD[Substrate, SubstrateCreate, SubstrateUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Substrate, session)

    async def get_multi_response(
        self,
        page: int = 1,
        size: int = 20,
    ) -> SubstrateListResponse:
        """Получить пагинированный список подложек.

        Args:
            page: Номер страницы (начиная с 1)
            size: Размер страницы

        Returns:
            SubstrateListResponse с пагинированным списком подложек
        """
        # Вычисляем skip для пагинации
        skip = (page - 1) * size

        # Получаем общее количество записей
        total = await self.session.scalar(
            select(func.count()).select_from(self.model),
        )

        # Получаем список объектов через get_multi
        substrates = await self.get_multi(skip=skip, limit=size)

        # Сериализуем каждый Substrate в SubstrateResponse
        items = [SubstrateResponse.model_validate(s) for s in substrates]

        # Возвращаем пагинированный ответ
        return SubstrateListResponse(
            total=total or 0,
            page=page,
            size=size,
            items=items,
        )

    async def delete(self, substrate_id: int) -> None:
        """Удалить подложку по ID.

        Удаляет файл из S3 и запись из БД.

        Args:
            substrate_id: ID подложки для удаления

        Raises:
            ValueError: Если подложка не найдена
            RuntimeError: Если не удалось удалить файл из S3 или запись из БД
        """
        # Получаем подложку через базовый метод get
        substrate = await self.get(substrate_id)
        if not substrate:
            raise ValueError(f"Подложка с ID {substrate_id} не найдена")

        # Сохраняем путь к файлу для удаления
        s3_path = substrate.path_s3

        logger.info("Deleting substrate substrate_id=%s s3_path=%s", substrate_id, s3_path)

        # Удаляем файл из S3
        s3_client = get_s3_client(bucket_name="graph-service", is_public=True)
        try:
            if s3_path:
                await s3_client.delete_object(s3_path)
                logger.info("SVG file deleted from S3 s3_path=%s", s3_path)
        except ValueError as e:
            # Файл уже не существует - это не критично, продолжаем
            logger.warning(
                "File not found in S3, continuing with DB deletion s3_path=%s error=%s",
                s3_path,
                e,
            )
        except Exception as s3_error:
            logger.error("Failed to delete SVG from S3 error=%s", s3_error, exc_info=True)
            # Не прерываем выполнение, но логируем ошибку
            # Можно продолжить удаление из БД, так как файл может быть уже удален

        # Удаляем запись из БД через базовый метод delete_obj
        try:
            await self.delete_obj(id=substrate_id)
            logger.info("Substrate deleted successfully substrate_id=%s", substrate_id)
        except Exception as e:
            await self.session.rollback()
            logger.exception("Failed to delete substrate from database error=%s", e)
            raise RuntimeError(f"Не удалось удалить подложку из БД: {str(e)}") from e

    async def create(self, data: SubstrateCreate) -> SubstrateResponse:
        """Создать подложку для горизонта.

        Принимает DXF файл, конвертирует его в SVG, загружает в S3 и создает запись в БД.

        Args:
            data: Данные для создания подложки (схема SubstrateCreate)

        Returns:
            SubstrateResponse с данными созданной подложки

        Raises:
            ValueError: Если файл невалиден или горизонт не найден
            RuntimeError: Если не удалось конвертировать DXF или загрузить в S3
        """
        size = len(data.file_content)
        safe_filename = os.path.basename(data.filename)
        logger.info(
            "DXF file received for substrate creation filename=%s size=%s horizon_id=%s",
            safe_filename,
            size,
            data.horizon_id,
        )

        # Конвертируем DXF в SVG
        logger.debug("Starting DXF to SVG conversion filename=%s size=%s", safe_filename, size)
        svg_bytes = await asyncio.to_thread(
            dxf_bytes_to_svg_bytes,
            data.file_content,
            margin_mm=10.0,
        )
        logger.debug(
            "DXF to SVG conversion completed svg_bytes_length=%s",
            len(svg_bytes) if svg_bytes else None,
        )

        if not svg_bytes:
            logger.error(
                "DXF to SVG conversion returned None filename=%s size=%s",
                safe_filename,
                size,
            )
            raise RuntimeError(
                "Не удалось преобразовать DXF в SVG: Функция конвертации вернула None",
            )

        logger.info("DXF successfully converted to SVG in memory size=%s", len(svg_bytes))

        # Загружаем SVG в S3 в папку substrates
        try:
            s3_client = get_s3_client(bucket_name="graph-service", is_public=True)
            # Формируем путь в S3: substrates/{filename}.svg
            s3_object_name = f"substrates/{safe_filename.rsplit('.', 1)[0]}.svg"

            # Загружаем SVG байты напрямую в S3 с Content-Type: image/svg+xml
            s3_path = await s3_client.put_object(
                object_name=s3_object_name,
                data=svg_bytes,
                ensure_unique=True,
                content_type="image/svg+xml",
            )
            logger.info(
                "SVG file uploaded to S3 s3_path=%s bucket=%s size=%s",
                s3_path,
                "graph-service",
                len(svg_bytes),
            )
        except Exception as s3_error:
            logger.error("Failed to upload SVG to S3 error=%s", s3_error, exc_info=True)
            raise RuntimeError(f"Не удалось загрузить SVG в S3: {str(s3_error)}") from s3_error

        # Создаем запись Substrate в БД
        try:
            substrate = Substrate(
                horizon_id=data.horizon_id,
                original_filename=safe_filename,
                path_s3=s3_path,
                opacity=data.opacity,
                center=data.center.model_dump(),
            )
            self.session.add(substrate)
            await self.session.commit()
            await self.session.refresh(substrate)

            logger.info(
                "Substrate created successfully substrate_id=%s horizon_id=%s s3_path=%s",
                substrate.id,
                data.horizon_id,
                s3_path,
            )

            return SubstrateResponse.model_validate(substrate)
        except Exception as e:
            await self.session.rollback()
            logger.exception("Failed to create substrate in database error=%s", e)
            raise RuntimeError(f"Не удалось создать подложку в БД: {str(e)}") from e

    async def get_with_svg_link(
        self,
        substrate_id: int,
        svg_link_expiration_sec: int = 60 * 60,
    ) -> SubstrateWithSvgResponse:
        """Получить подложку по ID со ссылкой на SVG файл в S3.

        Args:
            substrate_id: ID подложки
            svg_link_expiration_sec: Время жизни ссылки в секундах (по умолчанию 1 час)

        Returns:
            SubstrateWithSvgResponse с данными модели и ссылкой svg_link на файл в S3

        Raises:
            ValueError: Если подложка не найдена или файл не найден в S3
            RuntimeError: Если не удалось сформировать ссылку на файл в S3
        """
        substrate = await self.get(substrate_id)
        if not substrate:
            raise ValueError(f"Подложка с ID {substrate_id} не найдена")

        s3_client = get_s3_client(bucket_name="graph-service", is_public=True)
        try:
            svg_link = await s3_client.get_presigned_url(
                object_name=substrate.path_s3,
                expiration_sec=svg_link_expiration_sec,
            )
        except ValueError as e:
            raise ValueError(f"Файл подложки не найден в хранилище: {e!s}") from e
        except RuntimeError as e:
            logger.exception(
                "Failed to get substrate link from S3 substrate_id=%s error=%s",
                substrate_id,
                e,
            )
            raise RuntimeError("Не удалось получить ссылку на файл в хранилище") from e

        substrate_data = SubstrateResponse.model_validate(substrate)
        return SubstrateWithSvgResponse(
            **substrate_data.model_dump(),
            svg_link=svg_link,
        )

    async def refresh_file(
        self,
        substrate_id: int,
        file_content: bytes,
        filename: str,
    ) -> SubstrateResponse:
        """Заменить файл подложки.

        Принимает новый DXF файл, конвертирует его в SVG, удаляет старый файл из S3,
        загружает новый файл в S3 и обновляет запись в БД.

        Args:
            substrate_id: ID подложки для обновления
            file_content: Содержимое нового DXF файла в байтах
            filename: Имя нового файла

        Returns:
            SubstrateResponse с обновленными данными подложки

        Raises:
            ValueError: Если подложка не найдена или файл невалиден
            RuntimeError: Если не удалось конвертировать DXF,
                удалить старый файл или загрузить новый
        """
        # Получаем подложку через базовый метод get
        substrate = await self.get(substrate_id)
        if not substrate:
            raise ValueError(f"Подложка с ID {substrate_id} не найдена")

        # Сохраняем старый путь для удаления
        old_s3_path = substrate.path_s3

        size = len(file_content)
        safe_filename = os.path.basename(filename)
        logger.info(
            "DXF file received for substrate refresh "
            "substrate_id=%s filename=%s size=%s old_s3_path=%s",
            substrate_id,
            safe_filename,
            size,
            old_s3_path,
        )

        # Конвертируем DXF в SVG
        logger.debug("Starting DXF to SVG conversion filename=%s size=%s", safe_filename, size)
        svg_bytes = await asyncio.to_thread(
            dxf_bytes_to_svg_bytes,
            file_content,
            margin_mm=10.0,
        )
        logger.debug(
            "DXF to SVG conversion completed svg_bytes_length=%s",
            len(svg_bytes) if svg_bytes else None,
        )

        if not svg_bytes:
            logger.error(
                "DXF to SVG conversion returned None filename=%s size=%s",
                safe_filename,
                size,
            )
            raise RuntimeError(
                "Не удалось преобразовать DXF в SVG: Функция конвертации вернула None",
            )

        logger.info("DXF successfully converted to SVG in memory size=%s", len(svg_bytes))

        # Получаем S3 клиент
        s3_client = get_s3_client(bucket_name="graph-service", is_public=True)

        # Удаляем старый файл из S3
        try:
            if old_s3_path:
                await s3_client.delete_object(old_s3_path)
                logger.info("Old SVG file deleted from S3 s3_path=%s", old_s3_path)
        except ValueError as e:
            # Файл уже не существует - это не критично, продолжаем
            logger.warning(
                "Old file not found in S3, continuing old_s3_path=%s error=%s",
                old_s3_path,
                e,
            )
        except Exception as s3_delete_error:
            logger.error(
                "Failed to delete old SVG from S3 error=%s",
                s3_delete_error,
                exc_info=True,
            )
            # Не прерываем выполнение, но логируем ошибку

        # Загружаем новый SVG в S3
        try:
            # Формируем путь в S3: substrates/{filename}.svg
            s3_object_name = f"substrates/{safe_filename.rsplit('.', 1)[0]}.svg"

            # Загружаем SVG байты напрямую в S3 с Content-Type: image/svg+xml
            new_s3_path = await s3_client.put_object(
                object_name=s3_object_name,
                data=svg_bytes,
                ensure_unique=True,
                content_type="image/svg+xml",
            )
            logger.info(
                "New SVG file uploaded to S3 s3_path=%s bucket=%s size=%s",
                new_s3_path,
                "graph-service",
                len(svg_bytes),
            )
        except Exception as s3_error:
            logger.error("Failed to upload new SVG to S3 error=%s", s3_error, exc_info=True)
            raise RuntimeError(
                f"Не удалось загрузить новый SVG в S3: {str(s3_error)}",
            ) from s3_error

        # Обновляем запись Substrate в БД
        try:
            substrate.original_filename = safe_filename
            substrate.path_s3 = new_s3_path
            await self.session.commit()
            await self.session.refresh(substrate)

            logger.info(
                "Substrate file refreshed successfully "
                "substrate_id=%s new_filename=%s new_s3_path=%s",
                substrate.id,
                safe_filename,
                new_s3_path,
            )

            return SubstrateResponse.model_validate(substrate)
        except Exception as e:
            await self.session.rollback()
            logger.exception("Failed to update substrate in database error=%s", e)
            # Пытаемся удалить новый файл из S3 при ошибке БД
            try:
                await s3_client.delete_object(new_s3_path)
                logger.info(
                    "Rolled back: deleted new file from S3 after DB error s3_path=%s",
                    new_s3_path,
                )
            except Exception as cleanup_error:
                logger.error(
                    "Failed to cleanup new file from S3 after DB error s3_path=%s error=%s",
                    new_s3_path,
                    cleanup_error,
                )
            raise RuntimeError(f"Не удалось обновить подложку в БД: {str(e)}") from e

    async def update(
        self,
        substrate_id: int,
        data: SubstrateUpdate,
    ) -> SubstrateResponse:
        """Обновить подложку по ID.

        Обновляет только указанные поля: center, opacity, horizon_id.

        Args:
            substrate_id: ID подложки для обновления
            data: Данные для обновления (схема SubstrateUpdate)

        Returns:
            SubstrateResponse с обновленными данными подложки

        Raises:
            ValueError: Если подложка не найдена или данные невалидны
            RuntimeError: Если не удалось обновить запись в БД
        """
        # Получаем подложку через базовый метод get
        substrate = await self.get(substrate_id)
        if not substrate:
            raise ValueError(f"Подложка с ID {substrate_id} не найдена")

        # Подготавливаем данные для обновления (обрабатываем center отдельно)
        update_data = data.model_dump(exclude_unset=True)
        if "center" in update_data and data.center is not None:
            update_data["center"] = data.center.model_dump()

        if not update_data:
            logger.info("No fields to update substrate_id=%s", substrate_id)
            return SubstrateResponse.model_validate(substrate)

        logger.info(
            "Updating substrate substrate_id=%s update_fields=%s",
            substrate_id,
            list(update_data.keys()),
        )

        # Используем базовый метод update_obj для обновления
        try:
            updated_substrate = await self.update_obj(session_obj=substrate, obj_in=update_data)
            logger.info(
                "Substrate updated successfully substrate_id=%s updated_fields=%s",
                updated_substrate.id,
                list(update_data.keys()),
            )
            return SubstrateResponse.model_validate(updated_substrate)
        except Exception as e:
            await self.session.rollback()
            logger.exception("Failed to update substrate in database error=%s", e)
            raise RuntimeError(f"Не удалось обновить подложку в БД: {str(e)}") from e

"""API роуты для работы с подложками (substrates)."""

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.substrates import (
    SubstrateCreate,
    SubstrateListResponse,
    SubstrateResponse,
    SubstrateUpdate,
    SubstrateWithSvgResponse,
)
from app.services.substrates import (
    SubstratesServices,
)
from config.database import get_async_db

substrate_router = APIRouter(prefix="/substrates", tags=["Substrates"])


@substrate_router.get(
    "",
    response_model=SubstrateListResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def list_substrates(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    db: AsyncSession = Depends(get_async_db),
) -> SubstrateListResponse:
    """Получить пагинированный список подложек."""
    substrates_service = SubstratesServices(db)
    return await substrates_service.get_multi_response(page, size)


@substrate_router.post(
    "",
    response_model=SubstrateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def create_substrate(
    file: UploadFile = File(..., description="Файл в формате DXF"),
    db: AsyncSession = Depends(get_async_db),
):
    """Создать подложку для горизонта.

    Принимает DXF файл, конвертирует его в SVG, загружает в S3 и создает запись в БД.
    """
    try:
        # Читаем содержимое файла
        file_content = await file.read()

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Имя файла отсутствует",
            )

        # Создаем сервисную схему с данными из файла и значениями по умолчанию
        service_data = SubstrateCreate(
            file_content=file_content,
            filename=file.filename,
            horizon_id=None,
            opacity=100,
        )

        substrates_service = SubstratesServices(db)
        return await substrates_service.create(service_data)
    except HTTPException:
        raise
    except ValueError as e:
        # Ошибки валидации - 400 или 404
        status_code = status.HTTP_400_BAD_REQUEST
        if "не найден" in str(e).lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "уже существует" in str(e).lower():
            status_code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except RuntimeError as e:
        # Ошибки выполнения - 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@substrate_router.get(
    "/{substrate_id}",
    response_model=SubstrateWithSvgResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.VIEW)))],
)
async def get_substrate_with_svg(
    substrate_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Получить подложку по ID со ссылкой на SVG файл в S3."""
    try:
        substrates_service = SubstratesServices(db)
        return await substrates_service.get_with_svg_link(substrate_id)
    except ValueError as e:
        # Ошибки валидации - 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        # Ошибки выполнения - 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@substrate_router.post(
    "/{substrate_id}/refresh_file",
    response_model=SubstrateResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def refresh_substrate_file(
    substrate_id: int,
    file: UploadFile = File(..., description="Новый файл в формате DXF"),
    db: AsyncSession = Depends(get_async_db),
):
    """Заменить файл подложки.

    Принимает новый DXF файл, конвертирует его в SVG, удаляет старый файл из S3,
    загружает новый файл в S3 и обновляет запись в БД (original_filename и path_s3).
    """
    try:
        # Читаем содержимое файла
        file_content = await file.read()
        if not file.filename:
            raise ValueError("Имя файла отсутствует")

        substrates_service = SubstratesServices(db)
        return await substrates_service.refresh_file(
            substrate_id=substrate_id,
            file_content=file_content,
            filename=file.filename,
        )
    except ValueError as e:
        # Ошибки валидации - 400 или 404
        status_code = status.HTTP_400_BAD_REQUEST
        if "не найден" in str(e).lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except RuntimeError as e:
        # Ошибки выполнения - 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@substrate_router.patch(
    "/{substrate_id}",
    response_model=SubstrateResponse,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def update_substrate(
    substrate_id: int,
    update_data: SubstrateUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Обновить подложку по ID.

    Обновляет только указанные поля: center, opacity, horizon_id.
    """
    try:
        substrates_service = SubstratesServices(db)
        return await substrates_service.update(substrate_id, update_data)
    except ValueError as e:
        # Ошибки валидации - 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        # Ошибки выполнения - 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@substrate_router.delete(
    "/{substrate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def delete_substrate(
    substrate_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Удалить подложку по ID.

    Удаляет файл из S3 и запись из БД.
    """
    try:
        substrates_service = SubstratesServices(db)
        await substrates_service.delete(substrate_id)
    except ValueError as e:
        # Ошибки валидации - 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        # Ошибки выполнения - 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

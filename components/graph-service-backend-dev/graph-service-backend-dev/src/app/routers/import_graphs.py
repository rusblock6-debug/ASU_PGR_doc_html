"""CRUD операции для импорта графа (горизонта) из внешнего источника"""

import logging

from auth_lib import Action, Permission, require_permission
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.import_graphs import ImportGraphRequest
from app.services.import_graphs.import_graphs import import_graph_service

logger = logging.getLogger(__name__)

import_router = APIRouter(prefix="/import", tags=["Import"])


@import_router.post(
    "/graph",
    dependencies=[Depends(require_permission((Permission.MAP, Action.EDIT)))],
)
async def import_graph(import_request: ImportGraphRequest):
    """Импортировать граф из внешнего источника или переданных данных"""
    try:
        result = await import_graph_service.import_graph_from_request(import_request)

        if not result.success:
            logger.error(f"Import failed: {result.model_dump()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.model_dump(),
            )

        logger.info(f"Import completed successfully: {result.model_dump()}")
        return result.model_dump()

    except ValueError as e:
        logger.error(f"Import validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error during import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e

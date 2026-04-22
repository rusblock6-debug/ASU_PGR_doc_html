import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, status
from starlette.responses import JSONResponse

from app.api.exceptions.base import BaseResponseException
from app.database import AsyncSessionLocal
from app.config import settings
from app import api
from app.schemas.error import APIError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        from app.database.init_db import run_migrations

        await asyncio.to_thread(run_migrations)
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        logger.exception("Migration error details")
        raise

    try:
        from app.database.init_db import add_missing_permissions
        async with AsyncSessionLocal() as db:
            await add_missing_permissions(db)
    except Exception as e:
        logger.error(f"Failed to run add permissions: {e}")
        raise

    yield

    logger.info("Application shutdown")

app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan, root_path="/api/v1/auth")

@app.exception_handler(BaseResponseException)
def handle_base_response_exception(
    _: Request, exc: BaseResponseException
) -> JSONResponse:
    _error = APIError(code=exc.code, detail=exc.message, entity_id=exc.entity_id)
    if hasattr(exc, "entity_id"):
        _error.entity_id = exc.entity_id

    return JSONResponse(
        content=_error.model_dump(exclude_none=True), status_code=exc.status_code
    )


app.include_router(api.router)

@app.get("/health")
async def health_check():
    return {"status": "OK"}

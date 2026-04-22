from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from app.utils.vault_client import VaultClient


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if VaultClient.init_conn():
        logger.info("vault init successfully")
    else:
        logger.error("vault is not initiated")
    yield


app = FastAPI(
    title="Settings Service",
    description="Сервис для управления настройками и переменными окружения",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# --- Роутеры ---
from app.routers.settings import settings_router
from app.routers.frontend import frontend_router

app.include_router(settings_router, prefix="/api")
app.include_router(frontend_router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
    )

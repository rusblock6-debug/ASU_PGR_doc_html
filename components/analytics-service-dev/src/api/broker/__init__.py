from faststream.rabbit import RabbitRouter

from . import minio

main_router = RabbitRouter()

main_router.include_routers(
    minio.router,
)

__all__ = ["main_router"]

"""Application factory for the API gateway."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_package_version

from aiohttp import ClientSession, web

from src.config import Settings
from src.middleware import (
    jwt_verification_middleware,
    request_id_middleware,
    request_lifecycle_logging_middleware,
)
from src.proxy import _SUPPORTED_API_VERSIONS, missing_version_handler, proxy_handler


async def health_handler(request: web.Request) -> web.Response:
    """Return health status of the gateway."""
    return web.json_response({"status": "ok"})


async def root_handler(request: web.Request) -> web.Response:
    """Return gateway runtime routing information."""
    settings: Settings = request.app["settings"]

    try:
        gateway_version = get_package_version("api-gateway")
    except PackageNotFoundError:
        gateway_version = "unknown"

    services = {
        service_name: {
            "url": str(service_config.url),
            "path_pattern": service_config.path_pattern,
            "versioned": "{version}" in service_config.path_pattern,
        }
        for service_name, service_config in settings.services.items()
    }

    return web.json_response(
        {
            "version": gateway_version,
            "services": services,
            "supported_versions": sorted(_SUPPORTED_API_VERSIONS),
            "auth": {
                "url": str(settings.auth.url),
                "verify_endpoint": settings.auth.verify_endpoint,
            },
        },
    )


async def on_startup(app: web.Application) -> None:
    """Create a shared HTTP client session on startup."""
    app["client_session"] = ClientSession()


async def on_cleanup(app: web.Application) -> None:
    """Close the shared HTTP client session on cleanup."""
    session: ClientSession = app["client_session"]
    await session.close()


def create_app(settings: Settings) -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application(
        middlewares=[
            request_id_middleware,
            request_lifecycle_logging_middleware,
            jwt_verification_middleware,
        ],
    )
    app["settings"] = settings
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", root_handler)
    app.router.add_route("*", r"/api/{version:v\d+}/{service}/{path:.*}", proxy_handler)
    app.router.add_route("*", "/api/{service}/{path:.*}", missing_version_handler)
    app.router.add_route("*", "/api/{service}", missing_version_handler)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

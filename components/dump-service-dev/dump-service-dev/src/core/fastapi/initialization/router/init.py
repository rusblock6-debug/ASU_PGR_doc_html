"""FastAPI core initialization router."""

from fastapi import APIRouter, FastAPI


def init_main_router(app_: FastAPI, main_router: APIRouter) -> None:
    """Инициализация главного API роутера."""
    app_.include_router(router=main_router)

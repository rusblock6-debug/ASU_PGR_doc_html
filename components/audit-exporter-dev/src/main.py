"""ASGI entrypoint for the audit exporter service shell."""

from src.app import create_app

app = create_app()

from pydantic import PostgresDsn

from src.core.config import get_settings

settings = get_settings()


class FakePostgresContainer:
    @classmethod
    def get_connection_url(cls) -> str:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            path=f"{settings.POSTGRES_DATABASE}",
        ).unicode_string()

    def __enter__(self):
        """Fake enter."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fake exit."""
        return

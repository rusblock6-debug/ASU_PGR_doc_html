"""S3 клиент для работы с объектным хранилищем."""

from app.core.s3.client import S3Client, get_s3_client

__all__ = ["S3Client", "get_s3_client"]

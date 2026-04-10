"""Класс реализующий клиент для S3."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import token_hex
from typing import Any

import boto3
from aiobotocore.session import AioSession, ClientCreatorContext, get_session
from botocore.exceptions import ClientError
from loguru import logger

from src.core.config import get_settings
from src.core.dto.scheme.s3 import ConfigS3
from src.core.exception import InternalServerException, NotFoundException

settings = get_settings()


class S3Client:
    """Класс для S3."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        region_name: str,
        bucket_name: str,
        service_name: str = "s3",
        is_public: bool = True,
    ) -> None:
        """Init S3BucketClient."""
        self.config = ConfigS3(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
            service_name=service_name,
        )
        self.bucket_name = bucket_name
        self.is_public = is_public
        self.session: AioSession = get_session()

        self.sync_client = boto3.client(
            self.config.service_name,
            aws_access_key_id=self.config.aws_access_key_id,
            aws_secret_access_key=self.config.aws_secret_access_key,
            endpoint_url=self.config.endpoint_url,
            region_name=self.config.region_name,
        )

    @asynccontextmanager
    async def __get_client(self) -> AsyncGenerator[ClientCreatorContext]:
        """Получить сессию."""
        async with self.session.create_client(**self.config.model_dump()) as client:
            yield client

    async def __put_object(self, object_name: str, data: bytes) -> None:
        """Базовый объект для загрузки в S3.

        Args:
            object_name: Имя объекта (файла).
            data: Байтовое представление объекта (файла).
        """
        async with self.__get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=data,
                ACL="public-read" if self.is_public else "private",
            )

            logger.info(f"Объект {object_name} загружен в бакет {self.bucket_name}")

    async def upload_object(self, object_name: str, data: bytes) -> str:
        """Загрузить объект.

        Args:
            object_name: Имя объекта (файла).
            data: Байтовое представление объекта (файла).

        Returns:
            Название загруженного файла.
        """
        unique_object_name = await self.generate_unique_object_name(object_name)
        await self.__put_object(unique_object_name, data)
        return unique_object_name

    async def put_object(
        self,
        object_name: str,
        data: bytes,
        ensure_unique: bool = True,
    ) -> str:
        """Загрузить объект с возможностью контроля уникальности имени."""
        target_name = (
            await self.generate_unique_object_name(object_name) if ensure_unique else object_name
        )
        await self.__put_object(target_name, data)
        return target_name

    async def upload_file_stream(
        self,
        object_name: str,
        file_path: str | Path,
        *,
        ensure_unique: bool = True,
        part_size: int = 8 * 1024 * 1024,  # 8 MiB (мин. для S3 обычно 5 MiB)
        content_type: str | None = None,
    ) -> str:
        """Загрузить файл в S3 стримом (multipart upload), не читая целиком в память.

        Args:
            object_name: Желаемое имя объекта (ключ).
            file_path: Путь к файлу.
            ensure_unique: Делать ли уникализацию имени.
            part_size: Размер части (bytes). Обычно 8-16 MiB.
            content_type: MIME type (опционально).

        Returns:
            Итоговое имя объекта в бакете.
        """
        target_name = (
            await self.generate_unique_object_name(object_name) if ensure_unique else object_name
        )
        path = Path(file_path)

        extra_create_kwargs = {
            "Bucket": self.bucket_name,
            "Key": target_name,
            "ACL": "public-read" if self.is_public else "private",
        }
        if content_type:
            extra_create_kwargs["ContentType"] = content_type

        async with self.__get_client() as client:
            try:
                create_resp = await client.create_multipart_upload(**extra_create_kwargs)
                upload_id = create_resp["UploadId"]
            except ClientError as e:
                raise InternalServerException(
                    f"Failed to start multipart upload for {target_name} "
                    f"in bucket {self.bucket_name}",
                ) from e

            parts: list[dict[str, Any]] = []
            part_number = 1

            try:
                with path.open("rb") as f:
                    while True:
                        chunk = await asyncio.to_thread(f.read, part_size)
                        if not chunk:
                            break

                        resp = await client.upload_part(
                            Bucket=self.bucket_name,
                            Key=target_name,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=chunk,
                        )
                        # ETag нужен для complete_multipart_upload
                        parts.append({"ETag": resp["ETag"], "PartNumber": part_number})
                        part_number += 1

                if not parts:
                    # пустой файл — можно либо загрузить обычным put_object,
                    # либо завершить multipart
                    # Проще: abort multipart и залить put_object пустым Body
                    await client.abort_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=target_name,
                        UploadId=upload_id,
                    )
                    await self.__put_object(target_name, b"")
                    return target_name

                await client.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=target_name,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

                logger.info(
                    f"Объект {target_name} загружен (stream/multipart) в бакет {self.bucket_name}",
                )
                return target_name

            except Exception:
                try:
                    await client.abort_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=target_name,
                        UploadId=upload_id,
                    )
                except Exception:
                    logger.exception("Failed to abort multipart upload (best effort)")

                raise

    async def get_presigned_url(
        self,
        object_name: str,
        expiration_sec: int = 60 * 60,
    ) -> str:
        """Получить временную ссылку на объект.

        Args:
            object_name: Имя объекта (файла).
            expiration_sec: Время действия ссылки в секундах.

        Returns:
            Временную ссылку на объект (файл).
        """
        if not await self.check_object_exists(object_name):
            raise NotFoundException(
                f"Object {object_name} not found in bucket {self.bucket_name}",
            )
        async with self.__get_client() as client:
            try:
                response = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": object_name},
                    ExpiresIn=expiration_sec,
                )
            except ClientError as e:
                raise InternalServerException(
                    f"Error in creating a temporary link for the object {self.bucket_name}",
                ) from e

            return response

    def get_presigned_url_sync(
        self,
        object_name: str,
        expiration_sec: int = 60 * 60,
    ) -> str:
        """Синхронно получить временную ссылку на объект.

        Args:
            object_name: Имя объекта (файла).
            expiration_sec: Время действия ссылки в секундах.

        Returns:
            Временную ссылку на объект (файл).
        """
        try:
            url = self.sync_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration_sec,
            )
        except ClientError as e:
            raise InternalServerException(
                f"Error in creating a temporary link for the object {object_name}",
            ) from e

        return url

    async def update_object(self, object_name: str, data: bytes) -> str:
        """Обновить объект.

        Args:
            object_name: Имя объекта (файла).
            data: Байтовое представление объекта (файла).

        Returns:
            Название обновленного файла.
        """
        if not await self.check_object_exists(object_name):
            raise NotFoundException(
                f"Object {object_name} not found in bucket {self.bucket_name}",
            )

        await self.__put_object(object_name, data)
        return object_name

    async def delete_object(self, object_name: str) -> None:
        """Удалить объект (файл).

        Args:
            object_name: Имя объекта (файла).
        """
        if not await self.check_object_exists(object_name):
            raise NotFoundException(
                f"Object {object_name} not found in bucket {self.bucket_name}",
            )

        async with self.__get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Объект {object_name} уделен из бакета {self.bucket_name}")

    async def check_object_exists(self, object_name: str) -> bool:
        """Проверить есть ли объект (файл) в бакете.

        Args:
            object_name: Имя объекта (файла).

        Returns:
            Bool

        """
        async with self.__get_client() as client:
            try:
                await client.head_object(Bucket=self.bucket_name, Key=object_name)
            except ClientError as exc:
                if hasattr(exc, "response") and exc.response:
                    if exc.response.get("Error").get("Code") == "404":
                        return False
                else:
                    raise InternalServerException(
                        f"Error while searching for an object {object_name}"
                        f" in bucket {self.bucket_name}",
                    ) from exc

            return True

    async def generate_unique_object_name(self, object_name: str) -> str:
        """Сгенерировать уникальное название объекта."""
        random_part = token_hex(12)
        extension = ""
        if "." not in object_name:
            name = object_name
        else:
            name, extension = object_name.rsplit(".", maxsplit=1)
            extension = f".{extension}"
        unique_object_name = f"{name}_{random_part}{extension}"

        if await self.check_object_exists(unique_object_name):
            return await self.generate_unique_object_name(unique_object_name)
        return unique_object_name


def get_s3_client(bucket_name: str, is_public: bool = True) -> S3Client:
    """Получить s3 клиента с прокинутыми настройками с указанием бакета."""
    return S3Client(
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION_NAME,
        bucket_name=bucket_name,
        service_name="s3",
        is_public=is_public,
    )

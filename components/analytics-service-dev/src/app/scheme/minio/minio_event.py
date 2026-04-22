# ruff: noqa: D100, D101, D102, D105, D106
import re
from enum import StrEnum
from urllib.parse import unquote

from pydantic import BaseModel, Field, field_validator


class MinioS3Object(BaseModel):
    class Bucket(BaseModel):
        name: str = Field(...)

    class Object(BaseModel):
        key: str = Field(...)
        size: int = Field(...)
        e_tag: str = Field(alias="eTag")

        @field_validator("key", mode="before")
        @classmethod
        def normalize_key(cls, v: str) -> str:
            if not isinstance(v, str):
                return v
            # декодируем только если есть %XX (чтобы не трогать обычные строки)
            if re.search(r"%[0-9A-Fa-f]{2}", v):
                v = unquote(v)
            return v

    bucket: Bucket = Field(...)
    object: Object = Field(...)


class MinioEventRecord(BaseModel):
    event_name: str = Field(alias="eventName")
    s3: MinioS3Object = Field(...)


class MinioEventType(StrEnum):
    PUT = "s3:ObjectCreated:Put"
    MULTIPART_UPLOAD = "s3:ObjectCreated:CompleteMultipartUpload"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, key: object) -> "MinioEventType":
        return MinioEventType.UNKNOWN


class MinioEvent(BaseModel):
    event_name: MinioEventType = Field(alias="EventName")
    key: str = Field(alias="Key")
    records: list[MinioEventRecord] = Field(alias="Records")

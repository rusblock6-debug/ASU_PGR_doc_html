# ruff: noqa: D100, D101

import datetime

from msgspec import Struct


class S3File(Struct):
    __tablename__ = "s3_file"

    object_key: str
    etag: str
    loaded_at: datetime.datetime

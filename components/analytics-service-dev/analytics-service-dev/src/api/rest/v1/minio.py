"""Minio маршруты."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/minio",
    tags=["Minio"],
)

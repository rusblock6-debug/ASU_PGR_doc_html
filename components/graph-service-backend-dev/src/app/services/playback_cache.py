import asyncio
import hashlib
import json
import math
from collections.abc import Sequence
from datetime import UTC, datetime

from loguru import logger
from platform_sdk import (
    AsyncClients,
    ClientSettings,
    FilterGroup,
    FilterParam,
    FilterType,
    QueryOperator,
    VehicleTelemetryField,
)

from app.core.s3.client import S3Client, get_s3_client
from app.schemas.map_player import (
    Playback,
    PlaybackCacheEntry,
    PlaybackManifest,
    PlaybackStatus,
    VehicleTelemetryItem,
)
from app.utils.redis import cache
from config.settings import get_settings

settings = get_settings()

STALE_PROCESSING_TIMEOUT = 300

s3_client: S3Client = get_s3_client()

analytics_client_settings = ClientSettings(
    base_url=settings.analytics_service_url,
)


def compute_playback_hash(vehicle_ids: list[int], start_date: datetime, end_date: datetime) -> str:
    canonical = f"{sorted(vehicle_ids)}|{int(start_date.timestamp())}|{int(end_date.timestamp())}"
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


def compute_chunk_duration(total_count: int, total_duration_sec: int) -> int:
    if total_count == 0 or total_duration_sec == 0:
        return settings.playback_chunk_max_duration

    records_per_sec = total_count / total_duration_sec
    if records_per_sec == 0:
        return settings.playback_chunk_max_duration

    duration = int(settings.playback_chunk_target_records / records_per_sec)
    return max(
        settings.playback_chunk_min_duration,
        min(duration, settings.playback_chunk_max_duration),
    )


async def _redis_get(key: str) -> dict | None:  # type: ignore[type-arg]
    return await asyncio.to_thread(cache.dict_get, key)


async def _redis_set(key: str, value: dict) -> None:  # type: ignore[type-arg]
    await asyncio.to_thread(cache.dict_set, key, value)


async def _redis_expire(key: str, ttl: int) -> None:
    await asyncio.to_thread(cache.redis.expire, key, ttl)


async def _redis_delete(key: str) -> None:
    await asyncio.to_thread(cache.delete, key)


def _redis_key(playback_hash: str) -> str:
    return f"playback:{playback_hash}"


def _s3_chunk_key(playback_hash: str, chunk_index: int) -> str:
    return f"playback/{playback_hash}/chunk_{chunk_index:03d}.json"


def _build_cache_entry(
    playback: Playback,
    status: PlaybackStatus,
    chunk_count: int,
    chunk_duration: int = 0,
    total_chunk_counts: int = 0,
) -> PlaybackCacheEntry:
    return PlaybackCacheEntry(
        status=status,
        chunk_count=chunk_count,
        total_chunk_counts=total_chunk_counts,
        chunk_duration=chunk_duration,
        created_at=datetime.now(UTC).isoformat(),
        start_date=playback.start_date.isoformat(),
        end_date=playback.end_date.isoformat(),
        vehicle_ids=json.dumps(playback.vehicle_ids),
    )


def _cache_entry_from_redis(raw: dict) -> PlaybackCacheEntry:  # type: ignore[type-arg]
    return PlaybackCacheEntry.model_validate(raw)


def _manifest_from_entry(playback_hash: str, entry: PlaybackCacheEntry) -> PlaybackManifest:
    return PlaybackManifest(
        hash=playback_hash,
        status=entry.status,
        chunk_count=entry.chunk_count,
        total_chunk_counts=entry.total_chunk_counts,
        chunk_duration_sec=entry.chunk_duration,
        start_date=datetime.fromisoformat(entry.start_date),
        end_date=datetime.fromisoformat(entry.end_date),
        vehicle_ids=json.loads(entry.vehicle_ids),
    )


async def _save_entry(redis_key: str, entry: PlaybackCacheEntry) -> None:
    await _redis_set(redis_key, entry.model_dump())
    await _redis_expire(redis_key, settings.playback_cache_ttl)


async def initiate_playback(playback: Playback) -> tuple[PlaybackManifest, bool]:
    playback_hash = compute_playback_hash(
        playback.vehicle_ids,
        playback.start_date,
        playback.end_date,
    )
    redis_key = _redis_key(playback_hash)

    cached = await _redis_get(redis_key)
    if cached:
        entry = _cache_entry_from_redis(cached)

        if entry.status == PlaybackStatus.READY:
            return _manifest_from_entry(playback_hash, entry), False

        if entry.status == PlaybackStatus.PROCESSING:
            try:
                created_dt = datetime.fromisoformat(entry.created_at)
                elapsed = (datetime.now(UTC) - created_dt).total_seconds()
                if elapsed > STALE_PROCESSING_TIMEOUT:
                    await _redis_delete(redis_key)
                else:
                    return _manifest_from_entry(playback_hash, entry), False
            except (ValueError, TypeError):
                await _redis_delete(redis_key)

        if entry.status == PlaybackStatus.ERROR:
            await _redis_delete(redis_key)

    entry = _build_cache_entry(playback, status=PlaybackStatus.PROCESSING, chunk_count=0)
    await _save_entry(redis_key, entry)

    return _manifest_from_entry(playback_hash, entry), True


async def _flush_chunk(
    playback_hash: str,
    chunk_idx: int,
    chunk_data: list[VehicleTelemetryItem],
) -> None:
    s3_key = _s3_chunk_key(playback_hash, chunk_idx)
    data_bytes = json.dumps(
        [item.model_dump(mode="json") for item in chunk_data],
        default=str,
    ).encode()
    await s3_client.put_object(
        s3_key,
        data_bytes,
        ensure_unique=False,
        content_type="application/json",
    )


def _build_filters(
    vehicle_ids: Sequence[int | str | float],
    start_ts: int,
    end_ts: int,
) -> FilterGroup:
    return FilterGroup(
        type=FilterType.AND,
        items=[
            FilterParam(
                field=VehicleTelemetryField.BORT,
                value=list(vehicle_ids),
                operator=QueryOperator.IN,
            ),
            FilterParam(
                field=VehicleTelemetryField.TIMESTAMP,
                value=start_ts,
                operator=QueryOperator.EQUALS_OR_GREATER,
            ),
            FilterParam(
                field=VehicleTelemetryField.TIMESTAMP,
                value=end_ts,
                operator=QueryOperator.EQUALS_OR_LESS,
            ),
        ],
    )


async def generate_chunks(playback: Playback, playback_hash: str) -> None:
    redis_key = _redis_key(playback_hash)
    try:
        start_ts = int(playback.start_date.timestamp())
        end_ts = int(playback.end_date.timestamp())
        total_duration = end_ts - start_ts
        filters = _build_filters(playback.vehicle_ids, start_ts, end_ts)

        async with AsyncClients(analytics_client_settings) as clients:
            probe = await clients.analytics.get_vehicle_telemetry(
                filters,
                sort_by=VehicleTelemetryField.TIMESTAMP,
                skip=0,
                limit=1,
            )
            total_count = probe.total_count

            if total_count == 0:
                chunk_duration = compute_chunk_duration(0, total_duration)
                time_slots = max(1, math.ceil(total_duration / chunk_duration))
                entry = _build_cache_entry(
                    playback,
                    status=PlaybackStatus.READY,
                    chunk_count=0,
                    total_chunk_counts=time_slots,
                    chunk_duration=chunk_duration,
                )
                await _save_entry(redis_key, entry)
                logger.info(f"Playback {playback_hash}: 0 records, {time_slots} empty slots")
                return

            full = await clients.analytics.get_vehicle_telemetry(
                filters,
                sort_by=VehicleTelemetryField.TIMESTAMP,
                skip=0,
                limit=total_count,
            )

        chunk_duration = compute_chunk_duration(total_count, total_duration)

        time_slots = max(1, math.ceil(total_duration / chunk_duration))
        chunks: dict[int, list[VehicleTelemetryItem]] = {}
        total_records = 0

        for record in full.data:
            total_records += 1
            item = VehicleTelemetryItem.model_validate(record.model_dump())
            record_ts = int(record.timestamp.timestamp())
            chunk_idx = min(
                (record_ts - start_ts) // chunk_duration,
                time_slots - 1,
            )

            if chunk_idx not in chunks:
                chunks[chunk_idx] = []
            chunks[chunk_idx].append(item)

        flushed = 0
        for idx in sorted(chunks):
            await _flush_chunk(playback_hash, idx, chunks[idx])
            flushed += 1
            entry = _build_cache_entry(
                playback,
                status=PlaybackStatus.PROCESSING,
                chunk_count=flushed,
                total_chunk_counts=time_slots,
                chunk_duration=chunk_duration,
            )
            await _save_entry(redis_key, entry)

        entry = _build_cache_entry(
            playback,
            status=PlaybackStatus.READY,
            chunk_count=flushed,
            total_chunk_counts=time_slots,
            chunk_duration=chunk_duration,
        )
        await _save_entry(redis_key, entry)

        logger.info(f"Playback {playback_hash}: {flushed} chunks, {total_records} records")

    except Exception as e:
        logger.error(f"Playback {playback_hash} generation failed: {e}")
        entry = _build_cache_entry(playback, status=PlaybackStatus.ERROR, chunk_count=0)
        await _save_entry(redis_key, entry)


async def get_manifest(playback_hash: str) -> PlaybackManifest | None:
    cached = await _redis_get(_redis_key(playback_hash))
    if not cached:
        return None

    entry = _cache_entry_from_redis(cached)
    return _manifest_from_entry(playback_hash, entry)


async def get_chunk(playback_hash: str, chunk_index: int) -> list[VehicleTelemetryItem]:
    s3_key = _s3_chunk_key(playback_hash, chunk_index)
    try:
        data = await s3_client.get_object(s3_key)
    except ValueError:
        return []
    raw_list: list[dict] = json.loads(data)  # type: ignore[type-arg]
    return [VehicleTelemetryItem.model_validate(item) for item in raw_list]

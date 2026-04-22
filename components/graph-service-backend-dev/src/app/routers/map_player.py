"""Операции для map_player."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.map_player import Playback, PlaybackChunkResponse, PlaybackManifest
from app.services import playback_cache

router = APIRouter(prefix="/map-player", tags=["Map player"])


@router.post("/playback")
async def get_playback(
    playback: Playback,
    background_tasks: BackgroundTasks,
) -> PlaybackManifest:
    manifest, should_generate = await playback_cache.initiate_playback(playback)

    if should_generate:
        background_tasks.add_task(playback_cache.generate_chunks, playback, manifest.hash)

    return manifest


@router.get("/playback/{playback_hash}/manifest")
async def get_playback_manifest(playback_hash: str) -> PlaybackManifest:
    manifest = await playback_cache.get_manifest(playback_hash)
    if not manifest:
        raise HTTPException(status_code=404, detail="Playback not found")
    return manifest


@router.get("/playback/{playback_hash}/chunks/{chunk_index}")
async def get_playback_chunk(playback_hash: str, chunk_index: int) -> PlaybackChunkResponse:
    manifest = await playback_cache.get_manifest(playback_hash)
    if not manifest:
        raise HTTPException(status_code=404, detail="Playback not found")

    if manifest.status == "error":
        raise HTTPException(status_code=500, detail="Playback generation failed")

    if chunk_index < 0 or chunk_index >= manifest.total_chunk_counts:
        raise HTTPException(status_code=404, detail="Chunk index out of range")

    data = await playback_cache.get_chunk(playback_hash, chunk_index)
    return PlaybackChunkResponse(
        hash=playback_hash,
        chunk_index=chunk_index,
        total_chunks=manifest.total_chunk_counts,
        data=data,
    )

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import verify_api_key
from api.models import MediaDownloadOut, MediaDownloadStatsOut
from bot.downloads import queue_media_download_retry, retry_media_download
from database import crud
from database.engine import async_session

router = APIRouter(prefix="/downloads", tags=["Media Downloads"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[MediaDownloadOut])
async def list_downloads(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    async with async_session() as session:
        items = await crud.get_media_downloads(session, status=status, limit=limit, offset=offset)
    return [MediaDownloadOut.model_validate(item) for item in items]


@router.get("/stats", response_model=MediaDownloadStatsOut)
async def download_stats():
    async with async_session() as session:
        data = await crud.get_media_download_stats(session)
    counts = data["counts"]
    return MediaDownloadStatsOut(
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        total_speed_bps=data["total_speed_bps"],
    )


@router.post("/{download_id}/retry", response_model=MediaDownloadOut)
async def retry_download(download_id: int):
    item = await queue_media_download_retry(download_id)
    if not item:
        raise HTTPException(status_code=404, detail="下载记录不存在")

    asyncio.create_task(retry_media_download(download_id))
    return MediaDownloadOut.model_validate(item)

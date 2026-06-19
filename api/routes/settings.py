from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from api.deps import verify_api_key
from api.models import DownloadSettingsIn, DownloadSettingsOut, WebDavTestOut
from bot.downloads import DownloadSettings, get_download_settings, save_download_settings, test_webdav_settings

router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(verify_api_key)])


def _download_settings_out(settings: DownloadSettings) -> DownloadSettingsOut:
    return DownloadSettingsOut(
        target_type=settings.target_type,
        local_path=settings.local_path,
        keep_local=settings.keep_local,
        webdav_url=settings.webdav_url,
        webdav_username=settings.webdav_username,
        webdav_remote_path=settings.webdav_remote_path,
        webdav_verify_ssl=settings.webdav_verify_ssl,
        has_webdav_password=bool(settings.webdav_password),
        s3_endpoint_url=settings.s3_endpoint_url,
        s3_region=settings.s3_region,
        s3_bucket=settings.s3_bucket,
        s3_access_key_id=settings.s3_access_key_id,
        s3_prefix=settings.s3_prefix,
        s3_addressing_style=settings.s3_addressing_style,
        s3_multipart_chunk_mb=settings.s3_multipart_chunk_mb,
        s3_max_concurrency=settings.s3_max_concurrency,
        has_s3_secret_access_key=bool(settings.s3_secret_access_key),
        reaction_enabled=settings.reaction_enabled,
        reaction_emoji=settings.reaction_emoji,
        reaction_notify_chat_id=settings.reaction_notify_chat_id,
    )


@router.get("/download", response_model=DownloadSettingsOut)
async def get_download_config():
    settings = await get_download_settings()
    return _download_settings_out(settings)


@router.put("/download", response_model=DownloadSettingsOut)
async def update_download_config(body: DownloadSettingsIn):
    target_type = body.target_type.strip().lower()
    if target_type not in {"local", "webdav", "s3"}:
        raise HTTPException(status_code=400, detail="target_type 必须是 local、webdav 或 s3")
    if target_type == "webdav" and not body.webdav_url.strip():
        raise HTTPException(status_code=400, detail="WebDAV URL 不能为空")
    if target_type == "s3":
        if not body.s3_bucket.strip():
            raise HTTPException(status_code=400, detail="S3 Bucket 不能为空")
        if not body.s3_access_key_id.strip():
            raise HTTPException(status_code=400, detail="S3 Access Key 不能为空")

    current = await get_download_settings()
    new_password = body.webdav_password if body.webdav_password else current.webdav_password
    new_s3_secret = body.s3_secret_access_key if body.s3_secret_access_key else current.s3_secret_access_key
    if target_type == "s3" and not new_s3_secret:
        raise HTTPException(status_code=400, detail="S3 Secret Key 不能为空")
    s3_addressing_style = body.s3_addressing_style.strip().lower() or "auto"
    if s3_addressing_style not in {"auto", "path", "virtual"}:
        raise HTTPException(status_code=400, detail="S3 地址风格必须是 auto、path 或 virtual")
    new_settings = DownloadSettings(
        target_type=target_type,
        local_path=body.local_path.strip(),
        keep_local=body.keep_local,
        webdav_url=body.webdav_url.strip(),
        webdav_username=body.webdav_username.strip(),
        webdav_password=new_password,
        webdav_remote_path=body.webdav_remote_path.strip(),
        webdav_verify_ssl=body.webdav_verify_ssl,
        s3_endpoint_url=body.s3_endpoint_url.strip(),
        s3_region=body.s3_region.strip(),
        s3_bucket=body.s3_bucket.strip(),
        s3_access_key_id=body.s3_access_key_id.strip(),
        s3_secret_access_key=new_s3_secret,
        s3_prefix=body.s3_prefix.strip(),
        s3_addressing_style=s3_addressing_style,
        s3_multipart_chunk_mb=body.s3_multipart_chunk_mb,
        s3_max_concurrency=body.s3_max_concurrency,
        reaction_enabled=body.reaction_enabled,
        reaction_emoji=body.reaction_emoji.strip() or "👍",
        reaction_notify_chat_id=body.reaction_notify_chat_id,
    )
    await save_download_settings(new_settings)
    return _download_settings_out(new_settings)


@router.post("/download/webdav-test", response_model=WebDavTestOut)
async def test_webdav_config(body: DownloadSettingsIn):
    if not body.webdav_url.strip():
        raise HTTPException(status_code=400, detail="WebDAV URL 不能为空")

    current = await get_download_settings()
    new_password = body.webdav_password if body.webdav_password else current.webdav_password
    settings = DownloadSettings(
        target_type="webdav",
        local_path=body.local_path.strip(),
        keep_local=body.keep_local,
        webdav_url=body.webdav_url.strip(),
        webdav_username=body.webdav_username.strip(),
        webdav_password=new_password,
        webdav_remote_path=body.webdav_remote_path.strip(),
        webdav_verify_ssl=body.webdav_verify_ssl,
    )
    try:
        target_url = await asyncio.to_thread(test_webdav_settings, settings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"WebDAV 测试失败: {e}")
    return WebDavTestOut(ok=True, message="WebDAV 测试成功", target_url=target_url)

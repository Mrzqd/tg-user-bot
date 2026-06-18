from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import verify_api_key
from api.models import DownloadSettingsIn, DownloadSettingsOut
from bot.downloads import DownloadSettings, get_download_settings, save_download_settings

router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(verify_api_key)])


@router.get("/download", response_model=DownloadSettingsOut)
async def get_download_config():
    settings = await get_download_settings()
    return DownloadSettingsOut(
        target_type=settings.target_type,
        local_path=settings.local_path,
        keep_local=settings.keep_local,
        webdav_url=settings.webdav_url,
        webdav_username=settings.webdav_username,
        webdav_remote_path=settings.webdav_remote_path,
        webdav_verify_ssl=settings.webdav_verify_ssl,
        has_webdav_password=bool(settings.webdav_password),
    )


@router.put("/download", response_model=DownloadSettingsOut)
async def update_download_config(body: DownloadSettingsIn):
    target_type = body.target_type.strip().lower()
    if target_type not in {"local", "webdav"}:
        raise HTTPException(status_code=400, detail="target_type 必须是 local 或 webdav")
    if target_type == "webdav" and not body.webdav_url.strip():
        raise HTTPException(status_code=400, detail="WebDAV URL 不能为空")

    current = await get_download_settings()
    new_password = body.webdav_password if body.webdav_password else current.webdav_password
    new_settings = DownloadSettings(
        target_type=target_type,
        local_path=body.local_path.strip(),
        keep_local=body.keep_local,
        webdav_url=body.webdav_url.strip(),
        webdav_username=body.webdav_username.strip(),
        webdav_password=new_password,
        webdav_remote_path=body.webdav_remote_path.strip(),
        webdav_verify_ssl=body.webdav_verify_ssl,
    )
    await save_download_settings(new_settings)
    return DownloadSettingsOut(
        target_type=new_settings.target_type,
        local_path=new_settings.local_path,
        keep_local=new_settings.keep_local,
        webdav_url=new_settings.webdav_url,
        webdav_username=new_settings.webdav_username,
        webdav_remote_path=new_settings.webdav_remote_path,
        webdav_verify_ssl=new_settings.webdav_verify_ssl,
        has_webdav_password=bool(new_settings.webdav_password),
    )

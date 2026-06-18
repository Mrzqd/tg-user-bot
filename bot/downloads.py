from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urljoin
from urllib.request import (
    HTTPPasswordMgrWithDefaultRealm,
    HTTPBasicAuthHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from loguru import logger

from config import BASE_DIR, settings
from database import crud
from database.engine import async_session


SETTING_TARGET_TYPE = "download.target_type"
SETTING_LOCAL_PATH = "download.local_path"
SETTING_KEEP_LOCAL = "download.keep_local"
SETTING_WEBDAV_URL = "download.webdav_url"
SETTING_WEBDAV_USERNAME = "download.webdav_username"
SETTING_WEBDAV_PASSWORD = "download.webdav_password"
SETTING_WEBDAV_REMOTE_PATH = "download.webdav_remote_path"
SETTING_WEBDAV_VERIFY_SSL = "download.webdav_verify_ssl"

DOWNLOAD_SETTING_KEYS = [
    SETTING_TARGET_TYPE,
    SETTING_LOCAL_PATH,
    SETTING_KEEP_LOCAL,
    SETTING_WEBDAV_URL,
    SETTING_WEBDAV_USERNAME,
    SETTING_WEBDAV_PASSWORD,
    SETTING_WEBDAV_REMOTE_PATH,
    SETTING_WEBDAV_VERIFY_SSL,
]


@dataclass
class DownloadSettings:
    target_type: str = "local"
    local_path: str = ""
    keep_local: bool = True
    webdav_url: str = ""
    webdav_username: str = ""
    webdav_password: str = ""
    webdav_remote_path: str = ""
    webdav_verify_ssl: bool = True


def _to_bool(value: str | bool | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_local_path(path: str) -> Path:
    raw = Path(path or settings.download_dir).expanduser()
    if not raw.is_absolute():
        raw = BASE_DIR / raw
    return raw


async def get_download_settings() -> DownloadSettings:
    async with async_session() as session:
        values = await crud.get_settings(session, DOWNLOAD_SETTING_KEYS)

    target_type = values.get(SETTING_TARGET_TYPE) or "local"
    if target_type not in {"local", "webdav"}:
        target_type = "local"

    return DownloadSettings(
        target_type=target_type,
        local_path=values.get(SETTING_LOCAL_PATH) or settings.download_dir,
        keep_local=_to_bool(values.get(SETTING_KEEP_LOCAL), True),
        webdav_url=values.get(SETTING_WEBDAV_URL) or "",
        webdav_username=values.get(SETTING_WEBDAV_USERNAME) or "",
        webdav_password=values.get(SETTING_WEBDAV_PASSWORD) or "",
        webdav_remote_path=values.get(SETTING_WEBDAV_REMOTE_PATH) or "",
        webdav_verify_ssl=_to_bool(values.get(SETTING_WEBDAV_VERIFY_SSL), True),
    )


async def save_download_settings(new_settings: DownloadSettings) -> None:
    values = {
        SETTING_TARGET_TYPE: new_settings.target_type,
        SETTING_LOCAL_PATH: new_settings.local_path,
        SETTING_KEEP_LOCAL: "1" if new_settings.keep_local else "0",
        SETTING_WEBDAV_URL: new_settings.webdav_url,
        SETTING_WEBDAV_USERNAME: new_settings.webdav_username,
        SETTING_WEBDAV_REMOTE_PATH: new_settings.webdav_remote_path,
        SETTING_WEBDAV_VERIFY_SSL: "1" if new_settings.webdav_verify_ssl else "0",
    }
    values[SETTING_WEBDAV_PASSWORD] = new_settings.webdav_password

    async with async_session() as session:
        await crud.set_settings(session, values)


async def get_download_dir() -> Path:
    current = await get_download_settings()
    path = _resolve_local_path(current.local_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _join_webdav_url(base_url: str, remote_path: str, filename: str) -> str:
    base = base_url.rstrip("/") + "/"
    path_parts = [part for part in remote_path.strip("/").split("/") if part]
    quoted_path = "/".join(quote(part) for part in path_parts)
    if quoted_path:
        base = urljoin(base, quoted_path + "/")
    return urljoin(base, quote(filename))


def _make_webdav_opener(download_settings: DownloadSettings, target_url: str):
    handlers = []
    if not download_settings.webdav_verify_ssl:
        handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
    if download_settings.webdav_username:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(
            None,
            download_settings.webdav_url,
            download_settings.webdav_username,
            download_settings.webdav_password,
        )
        manager.add_password(
            None,
            target_url,
            download_settings.webdav_username,
            download_settings.webdav_password,
        )
        handlers.append(HTTPBasicAuthHandler(manager))
    return build_opener(*handlers)


def _ensure_webdav_collection(opener, url: str) -> None:
    req = Request(url, method="MKCOL")
    try:
        opener.open(req, timeout=30)
    except HTTPError as e:
        if e.code not in {405, 409}:
            raise


def _upload_webdav_file(local_file: Path, download_settings: DownloadSettings) -> str:
    if not download_settings.webdav_url:
        raise ValueError("WebDAV URL 未配置")

    target_url = _join_webdav_url(
        download_settings.webdav_url,
        download_settings.webdav_remote_path,
        local_file.name,
    )
    opener = _make_webdav_opener(download_settings, target_url)

    parent_url = target_url.rsplit("/", 1)[0] + "/"
    if download_settings.webdav_remote_path.strip("/"):
        try:
            _ensure_webdav_collection(opener, parent_url)
        except Exception as e:
            logger.debug("[WebDAV] MKCOL skipped/failed for {}: {}", parent_url, e)

    with local_file.open("rb") as f:
        req = Request(target_url, data=f, method="PUT")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Content-Length", str(local_file.stat().st_size))
        opener.open(req, timeout=120)
    return target_url


async def finalize_download(local_file: str | Path) -> str:
    file_path = Path(local_file)
    download_settings = await get_download_settings()
    if download_settings.target_type != "webdav":
        return str(file_path)

    target_url = await asyncio.to_thread(_upload_webdav_file, file_path, download_settings)
    logger.info("[WebDAV] Uploaded {} -> {}", file_path, target_url)
    if not download_settings.keep_local:
        file_path.unlink(missing_ok=True)
    return target_url

from __future__ import annotations

import asyncio
import base64
import mimetypes
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import (
    HTTPSHandler,
    Request,
    build_opener,
)

from loguru import logger

TZ_CST = timezone(timedelta(hours=8))


SETTING_TARGET_TYPE = "download.target_type"
SETTING_LOCAL_PATH = "download.local_path"
SETTING_KEEP_LOCAL = "download.keep_local"
SETTING_WEBDAV_URL = "download.webdav_url"
SETTING_WEBDAV_USERNAME = "download.webdav_username"
SETTING_WEBDAV_PASSWORD = "download.webdav_password"
SETTING_WEBDAV_REMOTE_PATH = "download.webdav_remote_path"
SETTING_WEBDAV_VERIFY_SSL = "download.webdav_verify_ssl"
SETTING_REACTION_ENABLED = "reaction_download.enabled"
SETTING_REACTION_EMOJI = "reaction_download.emoji"
SETTING_REACTION_NOTIFY_CHAT_ID = "reaction_download.notify_chat_id"

DOWNLOAD_SETTING_KEYS = [
    SETTING_TARGET_TYPE,
    SETTING_LOCAL_PATH,
    SETTING_KEEP_LOCAL,
    SETTING_WEBDAV_URL,
    SETTING_WEBDAV_USERNAME,
    SETTING_WEBDAV_PASSWORD,
    SETTING_WEBDAV_REMOTE_PATH,
    SETTING_WEBDAV_VERIFY_SSL,
    SETTING_REACTION_ENABLED,
    SETTING_REACTION_EMOJI,
    SETTING_REACTION_NOTIFY_CHAT_ID,
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
    reaction_enabled: bool = False
    reaction_emoji: str = "👍"
    reaction_notify_chat_id: int = 0


def _to_bool(value: str | bool | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_local_path(path: str) -> Path:
    from config import BASE_DIR, settings

    raw = Path(path or settings.download_dir).expanduser()
    if not raw.is_absolute():
        raw = BASE_DIR / raw
    return raw


async def get_download_settings() -> DownloadSettings:
    from config import settings
    from database import crud
    from database.engine import async_session

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
        reaction_enabled=_to_bool(values.get(SETTING_REACTION_ENABLED), False),
        reaction_emoji=values.get(SETTING_REACTION_EMOJI) or "👍",
        reaction_notify_chat_id=int(values.get(SETTING_REACTION_NOTIFY_CHAT_ID) or 0),
    )


async def save_download_settings(new_settings: DownloadSettings) -> None:
    from database import crud
    from database.engine import async_session

    values = {
        SETTING_TARGET_TYPE: new_settings.target_type,
        SETTING_LOCAL_PATH: new_settings.local_path,
        SETTING_KEEP_LOCAL: "1" if new_settings.keep_local else "0",
        SETTING_WEBDAV_URL: new_settings.webdav_url,
        SETTING_WEBDAV_USERNAME: new_settings.webdav_username,
        SETTING_WEBDAV_REMOTE_PATH: new_settings.webdav_remote_path,
        SETTING_WEBDAV_VERIFY_SSL: "1" if new_settings.webdav_verify_ssl else "0",
        SETTING_REACTION_ENABLED: "1" if new_settings.reaction_enabled else "0",
        SETTING_REACTION_EMOJI: new_settings.reaction_emoji,
        SETTING_REACTION_NOTIFY_CHAT_ID: str(new_settings.reaction_notify_chat_id),
    }
    values[SETTING_WEBDAV_PASSWORD] = new_settings.webdav_password

    async with async_session() as session:
        await crud.set_settings(session, values)


async def get_download_dir() -> Path:
    current = await get_download_settings()
    path = _resolve_local_path(current.local_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_filename(filename: str) -> str:
    cleaned = "".join("_" if ch in '\\/:*?"<>|' or ord(ch) < 32 else ch for ch in filename).strip(". ")
    return cleaned[:180] or "download"


def _message_media_filename(message) -> str:
    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if document:
        for attr in getattr(document, "attributes", None) or []:
            if type(attr).__name__ == "DocumentAttributeFilename" and getattr(attr, "file_name", ""):
                return _clean_filename(attr.file_name)

        mime_type = getattr(document, "mime_type", "") or ""
        ext = mimetypes.guess_extension(mime_type) or ".bin"
        return f"telegram_{message.chat_id}_{message.id}{ext}"

    if getattr(media, "photo", None):
        return f"telegram_{message.chat_id}_{message.id}.jpg"

    return f"telegram_{message.chat_id}_{message.id}.bin"


def _telegram_target_file_path(download_dir: Path, message) -> Path:
    target = download_dir / _message_media_filename(message)
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    for idx in range(1, 1000):
        candidate = target.with_name(f"{stem}_{idx}{suffix}")
        if not candidate.exists():
            return candidate
    return target.with_name(f"{stem}_{datetime.now(TZ_CST):%Y%m%d%H%M%S}{suffix}")


async def download_telegram_media_message(message) -> str | None:
    if not getattr(message, "media", None):
        return None

    download_dir = await get_download_dir()
    target = _telegram_target_file_path(download_dir, message)
    return await message.download_media(file=str(target))


def _join_webdav_url(base_url: str, remote_path: str, filename: str) -> str:
    base = base_url.rstrip("/") + "/"
    path_parts = [part for part in remote_path.strip("/").split("/") if part]
    quoted_path = "/".join(quote(part) for part in path_parts)
    if quoted_path:
        base = urljoin(base, quoted_path + "/")
    return urljoin(base, quote(filename))


def _make_webdav_opener(download_settings: DownloadSettings):
    handlers = []
    if not download_settings.webdav_verify_ssl:
        handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
    return build_opener(*handlers)


def _add_webdav_auth(req: Request, download_settings: DownloadSettings) -> None:
    if not download_settings.webdav_username:
        return
    raw = f"{download_settings.webdav_username}:{download_settings.webdav_password}".encode()
    req.add_header("Authorization", f"Basic {base64.b64encode(raw).decode()}")


def _ensure_webdav_collection(opener, url: str, download_settings: DownloadSettings) -> None:
    req = Request(url, method="MKCOL")
    _add_webdav_auth(req, download_settings)
    try:
        opener.open(req, timeout=30)
    except HTTPError as e:
        if e.code not in {405, 409}:
            raise


def _ensure_webdav_collections(opener, download_settings: DownloadSettings) -> None:
    remote_path = download_settings.webdav_remote_path.strip("/")
    if not remote_path:
        return

    base = download_settings.webdav_url.rstrip("/") + "/"
    current = base
    for part in remote_path.split("/"):
        if not part:
            continue
        current = urljoin(current, quote(part) + "/")
        try:
            _ensure_webdav_collection(opener, current, download_settings)
        except Exception as e:
            logger.debug("[WebDAV] MKCOL skipped/failed for {}: {}", current, e)


def _put_webdav_file(opener, local_file: Path, target_url: str, download_settings: DownloadSettings) -> None:
    with local_file.open("rb") as f:
        req = Request(target_url, data=f, method="PUT")
        _add_webdav_auth(req, download_settings)
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Content-Length", str(local_file.stat().st_size))
        req.add_header("Connection", "close")
        opener.open(req, timeout=300)


def _upload_webdav_file(local_file: Path, download_settings: DownloadSettings) -> str:
    if not download_settings.webdav_url:
        raise ValueError("WebDAV URL 未配置")
    if urlparse(download_settings.webdav_url).scheme not in {"http", "https"}:
        raise ValueError("WebDAV URL 必须以 http:// 或 https:// 开头")

    target_url = _join_webdav_url(
        download_settings.webdav_url,
        download_settings.webdav_remote_path,
        local_file.name,
    )
    opener = _make_webdav_opener(download_settings)

    _ensure_webdav_collections(opener, download_settings)

    last_error = None
    for attempt in range(1, 3):
        try:
            _put_webdav_file(opener, local_file, target_url, download_settings)
            break
        except (BrokenPipeError, ConnectionResetError, TimeoutError, HTTPError, URLError, OSError) as e:
            last_error = e
            if attempt >= 2:
                raise
            logger.warning("[WebDAV] PUT failed (attempt {}), retrying: {}", attempt, e)
            time.sleep(1)
    if last_error:
        logger.debug("[WebDAV] PUT recovered after retry: {}", last_error)
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

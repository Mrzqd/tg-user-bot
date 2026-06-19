from __future__ import annotations

import asyncio
import base64
import http.client
import mimetypes
import re
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import (
    HTTPSHandler,
    HTTPHandler,
    Request,
    build_opener,
    urlopen,
)

from loguru import logger

TZ_CST = timezone(timedelta(hours=8))
URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
TELEGRAM_MESSAGE_HOSTS = {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}
MEDIA_MIME_PREFIXES = ("image/", "video/", "audio/")
MEDIA_MIME_TYPES = {
    "application/pdf",
    "application/octet-stream",
}
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
    ".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi",
    ".mp3", ".m4a", ".wav", ".ogg", ".flac",
    ".pdf",
}


SETTING_TARGET_TYPE = "download.target_type"
SETTING_LOCAL_PATH = "download.local_path"
SETTING_KEEP_LOCAL = "download.keep_local"
SETTING_WEBDAV_URL = "download.webdav_url"
SETTING_WEBDAV_USERNAME = "download.webdav_username"
SETTING_WEBDAV_PASSWORD = "download.webdav_password"
SETTING_WEBDAV_REMOTE_PATH = "download.webdav_remote_path"
SETTING_WEBDAV_VERIFY_SSL = "download.webdav_verify_ssl"
SETTING_S3_ENDPOINT_URL = "download.s3_endpoint_url"
SETTING_S3_REGION = "download.s3_region"
SETTING_S3_BUCKET = "download.s3_bucket"
SETTING_S3_ACCESS_KEY_ID = "download.s3_access_key_id"
SETTING_S3_SECRET_ACCESS_KEY = "download.s3_secret_access_key"
SETTING_S3_PREFIX = "download.s3_prefix"
SETTING_S3_ADDRESSING_STYLE = "download.s3_addressing_style"
SETTING_S3_MULTIPART_CHUNK_MB = "download.s3_multipart_chunk_mb"
SETTING_S3_MAX_CONCURRENCY = "download.s3_max_concurrency"
SETTING_REACTION_ENABLED = "reaction_download.enabled"
SETTING_REACTION_EMOJI = "reaction_download.emoji"
SETTING_REACTION_NOTIFY_CHAT_ID = "reaction_download.notify_chat_id"
WEBDAV_UPLOAD_BLOCK_SIZE = 4 * 1024 * 1024

DOWNLOAD_SETTING_KEYS = [
    SETTING_TARGET_TYPE,
    SETTING_LOCAL_PATH,
    SETTING_KEEP_LOCAL,
    SETTING_WEBDAV_URL,
    SETTING_WEBDAV_USERNAME,
    SETTING_WEBDAV_PASSWORD,
    SETTING_WEBDAV_REMOTE_PATH,
    SETTING_WEBDAV_VERIFY_SSL,
    SETTING_S3_ENDPOINT_URL,
    SETTING_S3_REGION,
    SETTING_S3_BUCKET,
    SETTING_S3_ACCESS_KEY_ID,
    SETTING_S3_SECRET_ACCESS_KEY,
    SETTING_S3_PREFIX,
    SETTING_S3_ADDRESSING_STYLE,
    SETTING_S3_MULTIPART_CHUNK_MB,
    SETTING_S3_MAX_CONCURRENCY,
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
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_prefix: str = ""
    s3_addressing_style: str = "auto"
    s3_multipart_chunk_mb: int = 16
    s3_max_concurrency: int = 8
    reaction_enabled: bool = False
    reaction_emoji: str = "👍"
    reaction_notify_chat_id: int = 0


class FinalizeResult(str):
    def __new__(cls, value: str, existed: bool = False):
        obj = str.__new__(cls, value)
        obj.existed = existed
        return obj


class ProgressFileReader:
    def __init__(self, file_obj, callback=None, block_size: int = WEBDAV_UPLOAD_BLOCK_SIZE) -> None:
        self.file_obj = file_obj
        self.callback = callback
        self.block_size = block_size
        self.uploaded = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self.block_size
        else:
            size = min(size, self.block_size)
        data = self.file_obj.read(size)
        if data:
            self.uploaded += len(data)
            if self.callback:
                self.callback(self.uploaded)
        return data


class LargeBlockHTTPConnection(http.client.HTTPConnection):
    blocksize = WEBDAV_UPLOAD_BLOCK_SIZE

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("blocksize", WEBDAV_UPLOAD_BLOCK_SIZE)
        super().__init__(*args, **kwargs)


class LargeBlockHTTPSConnection(http.client.HTTPSConnection):
    blocksize = WEBDAV_UPLOAD_BLOCK_SIZE

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("blocksize", WEBDAV_UPLOAD_BLOCK_SIZE)
        super().__init__(*args, **kwargs)


class LargeBlockHTTPHandler(HTTPHandler):
    def http_open(self, req):
        return self.do_open(LargeBlockHTTPConnection, req)


class LargeBlockHTTPSHandler(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(LargeBlockHTTPSConnection, req, context=self._context)


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
    if target_type not in {"local", "webdav", "s3"}:
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
        s3_endpoint_url=values.get(SETTING_S3_ENDPOINT_URL) or "",
        s3_region=values.get(SETTING_S3_REGION) or "",
        s3_bucket=values.get(SETTING_S3_BUCKET) or "",
        s3_access_key_id=values.get(SETTING_S3_ACCESS_KEY_ID) or "",
        s3_secret_access_key=values.get(SETTING_S3_SECRET_ACCESS_KEY) or "",
        s3_prefix=values.get(SETTING_S3_PREFIX) or "",
        s3_addressing_style=values.get(SETTING_S3_ADDRESSING_STYLE) or "auto",
        s3_multipart_chunk_mb=int(values.get(SETTING_S3_MULTIPART_CHUNK_MB) or 16),
        s3_max_concurrency=int(values.get(SETTING_S3_MAX_CONCURRENCY) or 8),
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
        SETTING_S3_ENDPOINT_URL: new_settings.s3_endpoint_url,
        SETTING_S3_REGION: new_settings.s3_region,
        SETTING_S3_BUCKET: new_settings.s3_bucket,
        SETTING_S3_ACCESS_KEY_ID: new_settings.s3_access_key_id,
        SETTING_S3_PREFIX: new_settings.s3_prefix,
        SETTING_S3_ADDRESSING_STYLE: new_settings.s3_addressing_style,
        SETTING_S3_MULTIPART_CHUNK_MB: str(new_settings.s3_multipart_chunk_mb),
        SETTING_S3_MAX_CONCURRENCY: str(new_settings.s3_max_concurrency),
        SETTING_REACTION_ENABLED: "1" if new_settings.reaction_enabled else "0",
        SETTING_REACTION_EMOJI: new_settings.reaction_emoji,
        SETTING_REACTION_NOTIFY_CHAT_ID: str(new_settings.reaction_notify_chat_id),
    }
    values[SETTING_WEBDAV_PASSWORD] = new_settings.webdav_password
    values[SETTING_S3_SECRET_ACCESS_KEY] = new_settings.s3_secret_access_key

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


def _content_type(headers) -> str:
    return (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()


def _url_extension(url: str) -> str:
    return Path(unquote(urlparse(url).path)).suffix.lower()


def _is_media_resource(content_type: str, url: str, content_disposition: str = "") -> bool:
    if content_type.startswith(MEDIA_MIME_PREFIXES) or content_type in MEDIA_MIME_TYPES:
        return True

    guessed_type, _ = mimetypes.guess_type(urlparse(url).path)
    if guessed_type and (
        guessed_type.startswith(MEDIA_MIME_PREFIXES) or guessed_type in MEDIA_MIME_TYPES
    ):
        return True

    if _url_extension(url) in MEDIA_EXTENSIONS:
        return True

    return bool(content_disposition and "attachment" in content_disposition.lower() and content_type != "text/html")


def _filename_from_content_disposition(content_disposition: str) -> str | None:
    if not content_disposition:
        return None

    encoded_match = re.search(r"filename\*=(?:[^']*'')?([^;]+)", content_disposition, re.IGNORECASE)
    if encoded_match:
        return unquote(encoded_match.group(1).strip().strip('"'))

    plain_match = re.search(r'filename="?([^";]+)"?', content_disposition, re.IGNORECASE)
    if plain_match:
        return plain_match.group(1).strip()

    return None


def parse_telegram_message_link(url: str) -> tuple[str | int, int] | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in TELEGRAM_MESSAGE_HOSTS:
        return None

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if parts and parts[0] == "s":
        parts = parts[1:]
    if len(parts) < 2:
        return None

    if parts[0] == "c":
        if len(parts) < 3 or not parts[1].isdigit() or not parts[-1].isdigit():
            return None
        return int(f"-100{parts[1]}"), int(parts[-1])

    username = parts[0]
    if username.startswith("+") or username in {"joinchat", "share", "addstickers"}:
        return None
    if not parts[-1].isdigit():
        return None
    return username, int(parts[-1])


def extract_urls(text: str) -> list[str]:
    urls = []
    seen = set()
    for match in URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,，。!！?？;；:：)]}）】》")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def extract_message_urls(message) -> list[str]:
    urls = []
    seen = set()
    for url in extract_urls(getattr(message, "raw_text", "") or getattr(message, "message", "") or ""):
        urls.append(url)
        seen.add(url)

    for entity in getattr(message, "entities", None) or []:
        url = getattr(entity, "url", None)
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)

    return urls


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
    return download_dir / _message_media_filename(message)


def _target_file_path(download_dir: Path, url: str, headers) -> Path:
    content_type = _content_type(headers)
    filename = _filename_from_content_disposition(headers.get("Content-Disposition") or "")
    if not filename:
        filename = Path(unquote(urlparse(url).path)).name or "download"

    filename = _clean_filename(filename)
    target = download_dir / filename

    if not target.suffix and content_type:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            target = target.with_suffix(ext)

    return target


def _existing_file_matches(path: Path, expected_size: int | None = None) -> bool:
    if not path.exists():
        return False
    if expected_size is None or expected_size <= 0:
        return True
    try:
        return path.stat().st_size == expected_size
    except OSError:
        return False


def _url_request(url: str, method: str = "GET") -> Request:
    return Request(
        url,
        method=method,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; tg-user-bot/1.0)",
            "Accept": "*/*",
        },
    )


def probe_media_url(url: str) -> tuple[bool, str]:
    try:
        with urlopen(_url_request(url, "HEAD"), timeout=20) as response:
            final_url = response.geturl()
            content_type = _content_type(response.headers)
            content_disposition = response.headers.get("Content-Disposition") or ""
            return _is_media_resource(content_type, final_url, content_disposition), final_url
    except HTTPError as e:
        if e.code not in {405, 403, 404, 501}:
            raise
    except URLError:
        raise
    except Exception:
        raise

    return True, url


def download_media_url(url: str, download_dir: Path, progress=None) -> str | None:
    should_try_get, final_url = probe_media_url(url)
    if not should_try_get:
        return None

    target_path = None
    try:
        with urlopen(_url_request(final_url), timeout=30) as response:
            response_url = response.geturl()
            content_type = _content_type(response.headers)
            content_disposition = response.headers.get("Content-Disposition") or ""
            if not _is_media_resource(content_type, response_url, content_disposition):
                return None

            target_path = _target_file_path(download_dir, response_url, response.headers)
            content_length = response.headers.get("Content-Length")
            expected_size = int(content_length) if content_length and content_length.isdigit() else None
            if _existing_file_matches(target_path, expected_size):
                logger.info("[Download] Local URL media exists, skip download: {}", target_path)
                return str(target_path)
            downloaded = 0
            if progress and content_length and content_length.isdigit():
                progress.thread_callback(0, int(content_length))
            with target_path.open("wb") as f:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress.thread_callback(downloaded)
    except Exception:
        if target_path and target_path.exists():
            target_path.unlink(missing_ok=True)
        raise

    return str(target_path) if target_path else None


def download_first_media_url(
    urls: list[str],
    download_dir: Path,
    progress=None,
) -> tuple[str | None, str, str]:
    if not urls:
        return None, "未找到可检查的链接", ""

    last_error = ""
    checked_count = 0
    for url in urls:
        try:
            checked_count += 1
            if progress:
                progress.thread_reset("正在下载链接媒体资源")
            file_path = download_media_url(url, download_dir, progress)
        except Exception as e:
            last_error = str(e)
            logger.warning("[Download] Failed checking url {}: {}", url, e)
            continue
        if file_path:
            logger.info("[Download] Saved url media {} -> {}", url, file_path)
            return file_path, "", url

    if checked_count and last_error:
        return None, f"链接检查失败: {last_error}", ""
    if checked_count:
        return None, "链接资源不是可下载的媒体资源", ""
    return None, f"链接检查失败: {last_error}" if last_error else "未找到可下载的媒体链接", ""


async def download_telegram_media_message(message) -> str | None:
    if not getattr(message, "media", None):
        return None

    download_dir = await get_download_dir()
    target = _telegram_target_file_path(download_dir, message)
    expected_size = _message_media_size(message)
    if _existing_file_matches(target, expected_size):
        logger.info("[Download] Local Telegram media exists, skip download: {}", target)
        return str(target)
    return await message.download_media(file=str(target))


async def download_telegram_message_link(url: str, progress=None) -> tuple[str | None, str, str]:
    from bot.client import userbot

    target = parse_telegram_message_link(url)
    if not target:
        return None, "不是 Telegram 消息链接", ""

    chat, msg_id = target
    try:
        msg = await userbot.client.get_messages(chat, ids=msg_id)
    except Exception as e:
        logger.warning("[Download] Failed to fetch Telegram link chat={} msg={}: {}", chat, msg_id, e)
        return None, f"无法读取消息链接: {e}", ""

    if not msg:
        return None, "消息链接对应的消息不存在或当前账号无权访问", ""
    if not getattr(msg, "media", None):
        return None, "消息链接对应的消息不是媒体资源", ""

    try:
        file_path = await download_telegram_media_message(msg)
    except Exception as e:
        logger.warning("[Download] Failed to download Telegram linked media chat={} msg={}: {}", chat, msg_id, e)
        return None, f"消息链接媒体下载失败: {e}", ""

    if not file_path:
        return None, "消息链接媒体下载失败: Telegram 未返回文件路径", ""

    logger.info("[Download] Saved linked Telegram media chat={} msg={} -> {}", chat, msg_id, file_path)
    return file_path, "", url


async def download_first_telegram_message_link(
    urls: list[str],
    progress=None,
) -> tuple[str | None, str, str]:
    last_reason = ""
    checked_count = 0
    for url in urls:
        if not parse_telegram_message_link(url):
            continue

        checked_count += 1
        if progress:
            await progress.reset("正在下载 Telegram 消息链接媒体")
        file_path, reason, source_url = await download_telegram_message_link(url, progress)
        if file_path:
            return file_path, "", source_url
        last_reason = reason

    if checked_count:
        return None, last_reason or "未找到可下载的 Telegram 消息媒体", ""
    return None, "", ""


def _join_webdav_url(base_url: str, remote_path: str, filename: str) -> str:
    base = base_url.rstrip("/") + "/"
    path_parts = [part for part in remote_path.strip("/").split("/") if part]
    quoted_path = "/".join(quote(part) for part in path_parts)
    if quoted_path:
        base = urljoin(base, quoted_path + "/")
    return urljoin(base, quote(filename))


def _make_webdav_opener(download_settings: DownloadSettings):
    handlers = [LargeBlockHTTPHandler()]
    if not download_settings.webdav_verify_ssl:
        handlers.append(LargeBlockHTTPSHandler(context=ssl._create_unverified_context()))
    else:
        handlers.append(LargeBlockHTTPSHandler())
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


def _webdav_file_exists(opener, target_url: str, download_settings: DownloadSettings) -> bool:
    req = Request(target_url, method="HEAD")
    _add_webdav_auth(req, download_settings)
    try:
        opener.open(req, timeout=60)
        return True
    except HTTPError as e:
        if e.code == 404:
            return False
        if e.code in {405, 501}:
            logger.debug("[WebDAV] HEAD unsupported for {}, continue upload: {}", target_url, e)
            return False
        raise


def _put_webdav_file(
    opener,
    local_file: Path,
    target_url: str,
    download_settings: DownloadSettings,
    progress_callback=None,
) -> None:
    with local_file.open("rb") as f:
        data = ProgressFileReader(f, progress_callback, WEBDAV_UPLOAD_BLOCK_SIZE)
        req = Request(target_url, data=data, method="PUT")
        _add_webdav_auth(req, download_settings)
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Content-Length", str(local_file.stat().st_size))
        opener.open(req, timeout=300)


def _upload_webdav_file(local_file: Path, download_settings: DownloadSettings, progress_callback=None) -> str:
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
    if _webdav_file_exists(opener, target_url, download_settings):
        logger.info("[WebDAV] Remote file exists, skip upload: {}", target_url)
        return FinalizeResult(target_url, existed=True)

    last_error = None
    for attempt in range(1, 3):
        try:
            _put_webdav_file(opener, local_file, target_url, download_settings, progress_callback)
            break
        except (BrokenPipeError, ConnectionResetError, TimeoutError, HTTPError, URLError, OSError) as e:
            last_error = e
            if attempt >= 2:
                raise
            logger.warning("[WebDAV] PUT failed (attempt {}), retrying: {}", attempt, e)
            time.sleep(1)
    if last_error:
        logger.debug("[WebDAV] PUT recovered after retry: {}", last_error)
    return FinalizeResult(target_url)


def _join_s3_key(prefix: str, filename: str) -> str:
    parts = [part.strip("/") for part in (prefix or "").split("/") if part.strip("/")]
    parts.append(_clean_filename(filename))
    return "/".join(parts)


def _s3_object_url(download_settings: DownloadSettings, key: str) -> str:
    endpoint = download_settings.s3_endpoint_url.rstrip("/")
    if endpoint:
        return f"{endpoint}/{quote(download_settings.s3_bucket)}/{quote(key, safe='/')}"
    region = download_settings.s3_region or "us-east-1"
    return f"https://{download_settings.s3_bucket}.s3.{region}.amazonaws.com/{quote(key, safe='/')}"


def _s3_object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        response = getattr(e, "response", None) or {}
        error = response.get("Error") if isinstance(response, dict) else {}
        code = str(error.get("Code", ""))
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(response, dict) else None
        if code in {"404", "NoSuchKey", "NotFound"} or status == 404:
            return False
        raise


def _upload_s3_file(local_file: Path, download_settings: DownloadSettings, progress_callback=None) -> str:
    if not download_settings.s3_bucket:
        raise ValueError("S3 Bucket 不能为空")
    if not download_settings.s3_access_key_id:
        raise ValueError("S3 Access Key 不能为空")
    if not download_settings.s3_secret_access_key:
        raise ValueError("S3 Secret Key 不能为空")

    try:
        import boto3
        from boto3.s3.transfer import S3Transfer, TransferConfig
        from botocore.client import Config
    except ImportError as e:
        raise RuntimeError("缺少 boto3 依赖，请重新安装 requirements.txt 或重建镜像") from e

    addressing_style = download_settings.s3_addressing_style
    if addressing_style not in {"auto", "path", "virtual"}:
        addressing_style = "auto"
    chunk_size = max(5, min(int(download_settings.s3_multipart_chunk_mb or 16), 512)) * 1024 * 1024
    concurrency = max(1, min(int(download_settings.s3_max_concurrency or 8), 64))
    key = _join_s3_key(download_settings.s3_prefix, local_file.name)

    client = boto3.client(
        "s3",
        endpoint_url=download_settings.s3_endpoint_url or None,
        region_name=download_settings.s3_region or None,
        aws_access_key_id=download_settings.s3_access_key_id,
        aws_secret_access_key=download_settings.s3_secret_access_key,
        config=Config(s3={"addressing_style": addressing_style}),
    )
    if _s3_object_exists(client, download_settings.s3_bucket, key):
        target_url = _s3_object_url(download_settings, key)
        logger.info("[S3] Remote file exists, skip upload: bucket={} key={}", download_settings.s3_bucket, key)
        return FinalizeResult(target_url, existed=True)

    transfer = S3Transfer(
        client,
        TransferConfig(
            multipart_threshold=chunk_size,
            multipart_chunksize=chunk_size,
            max_concurrency=concurrency,
            use_threads=concurrency > 1,
        ),
    )

    uploaded = 0
    progress_lock = threading.Lock()

    def on_progress(delta: int) -> None:
        nonlocal uploaded
        with progress_lock:
            uploaded += int(delta or 0)
            current = uploaded
        if progress_callback:
            progress_callback(current)

    extra_args = {}
    content_type = _path_mime(local_file)
    if content_type:
        extra_args["ContentType"] = content_type
    transfer.upload_file(
        str(local_file),
        download_settings.s3_bucket,
        key,
        extra_args=extra_args or None,
        callback=on_progress,
    )
    logger.info(
        "[S3] Uploaded {} -> bucket={} key={} chunk={} concurrency={}",
        local_file, download_settings.s3_bucket, key, chunk_size, concurrency,
    )
    return FinalizeResult(_s3_object_url(download_settings, key))


async def finalize_download(local_file: str | Path, progress=None) -> str:
    file_path = Path(local_file)
    download_settings = await get_download_settings()
    if download_settings.target_type == "local":
        return FinalizeResult(str(file_path))

    progress_callback = getattr(progress, "thread_callback", None) if progress else None
    if download_settings.target_type == "webdav":
        target_url = await asyncio.to_thread(_upload_webdav_file, file_path, download_settings, progress_callback)
        logger.info("[WebDAV] Finalized {} -> {}", file_path, target_url)
    elif download_settings.target_type == "s3":
        target_url = await asyncio.to_thread(_upload_s3_file, file_path, download_settings, progress_callback)
    else:
        return FinalizeResult(str(file_path))
    if not download_settings.keep_local and not getattr(target_url, "existed", False):
        file_path.unlink(missing_ok=True)
    return target_url


def telegram_source_url(chat_id, message_id: int) -> str:
    return f"telegram://{chat_id}/{message_id}"


def _now_cst() -> datetime:
    return datetime.now(TZ_CST)


def _duration_ms(started_at: datetime | None, completed_at: datetime) -> int:
    if not started_at:
        return 0

    if started_at.tzinfo is not None:
        started_at = started_at.astimezone(TZ_CST).replace(tzinfo=None)
    if completed_at.tzinfo is not None:
        completed_at = completed_at.astimezone(TZ_CST).replace(tzinfo=None)

    return max(int((completed_at - started_at).total_seconds() * 1000), 0)


def _path_size(path: str | Path | None) -> int:
    if not path:
        return 0
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def _path_mime(path: str | Path | None) -> str:
    if not path:
        return ""
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or ""


async def create_media_download_record(
    source_type: str,
    trigger_type: str,
    source_url: str = "",
    source_chat: str = "",
    source_message_id: int = 0,
    status: str = "running",
):
    from database import crud
    from database.engine import async_session

    now = _now_cst()
    async with async_session() as session:
        item = await crud.create_media_download(
            session,
            source_type=source_type,
            trigger_type=trigger_type,
            source_url=source_url,
            source_chat=source_chat,
            source_message_id=source_message_id,
            status=status,
        )
        if status == "running":
            item = await crud.update_media_download(session, item.id, started_at=now, error="")
        return item


async def mark_media_download_completed(
    download_id: int,
    local_path: str | Path,
    target_path: str,
    file_size: int | None = None,
    mime_type: str | None = None,
    source_url: str | None = None,
) -> None:
    from database import crud
    from database.engine import async_session

    completed_at = _now_cst()
    local_path_obj = Path(local_path)
    download_settings = await get_download_settings()
    async with async_session() as session:
        item = await crud.get_media_download(session, download_id)
        if not item:
            return
        values = {
            "status": "completed",
            "target_type": download_settings.target_type,
            "target_path": target_path,
            "local_path": str(local_path_obj),
            "file_name": local_path_obj.name,
            "mime_type": mime_type if mime_type is not None else _path_mime(local_path_obj),
            "file_size": file_size if file_size is not None else _path_size(local_path_obj),
            "error": "",
            "completed_at": completed_at,
            "duration_ms": _duration_ms(item.started_at, completed_at),
        }
        if source_url is not None:
            values["source_url"] = source_url
        await crud.update_media_download(session, download_id, **values)


async def mark_media_download_failed(download_id: int, error: str) -> None:
    from database import crud
    from database.engine import async_session

    completed_at = _now_cst()
    async with async_session() as session:
        item = await crud.get_media_download(session, download_id)
        if not item:
            return
        await crud.update_media_download(
            session,
            download_id,
            status="failed",
            error=str(error)[:2000],
            completed_at=completed_at,
            duration_ms=_duration_ms(item.started_at, completed_at),
        )


async def queue_media_download_retry(download_id: int):
    from database import crud
    from database.engine import async_session

    async with async_session() as session:
        item = await crud.get_media_download(session, download_id)
        if not item:
            return None
        if item.status in {"queued", "running"}:
            return item
        return await crud.update_media_download(
            session,
            download_id,
            status="queued",
            error="",
            retry_count=item.retry_count + 1,
            started_at=None,
            completed_at=None,
            duration_ms=0,
        )


def _source_chat_ref(value: str):
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return value


async def retry_media_download(download_id: int) -> None:
    from bot.client import userbot
    from database import crud
    from database.engine import async_session

    started_at = _now_cst()
    async with async_session() as session:
        item = await crud.get_media_download(session, download_id)
        if not item:
            return
        await crud.update_media_download(
            session,
            download_id,
            status="running",
            started_at=started_at,
            completed_at=None,
            duration_ms=0,
            error="",
        )
        source_type = item.source_type
        source_url = item.source_url
        source_chat = item.source_chat
        source_message_id = item.source_message_id

    local_path = ""
    try:
        if source_type == "telegram_message_link":
            local_path, reason, _ = await download_telegram_message_link(source_url)
            if not local_path:
                raise RuntimeError(reason or "Telegram 消息链接未返回媒体文件")
        elif source_type == "telegram_media":
            chat_ref = _source_chat_ref(source_chat)
            if chat_ref is None or not source_message_id:
                raise RuntimeError("缺少 Telegram 来源会话或消息 ID")
            msg = await userbot.client.get_messages(chat_ref, ids=source_message_id)
            if not msg or not getattr(msg, "media", None):
                raise RuntimeError("原消息不存在或不是媒体资源")
            local_path = await download_telegram_media_message(msg) or ""
            if not local_path:
                raise RuntimeError("Telegram 未返回文件路径")
        elif source_type == "http_url":
            download_dir = await get_download_dir()
            local_path = await asyncio.to_thread(download_media_url, source_url, download_dir, None) or ""
            if not local_path:
                raise RuntimeError("链接资源不是可下载的媒体资源")
        else:
            raise RuntimeError(f"不支持的资源来源: {source_type}")

        file_size = _path_size(local_path)
        mime_type = _path_mime(local_path)
        target = await finalize_download(local_path)
        await mark_media_download_completed(download_id, local_path, target, file_size=file_size, mime_type=mime_type)

        logger.info(
            "[Download] Retry completed id={} source={} size={} -> {}",
            download_id, source_url or telegram_source_url(source_chat, source_message_id), file_size, target,
        )
    except Exception as e:
        logger.warning("[Download] Retry failed id={}: {}", download_id, e)
        await mark_media_download_failed(download_id, str(e))

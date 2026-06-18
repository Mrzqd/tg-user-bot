"""
Self-command handlers.
The user can send commands to themselves (Saved Messages) or
in any chat prefixed with '.' to control the bot.
"""
from __future__ import annotations

import asyncio
import mimetypes
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from loguru import logger
from telethon import events
from telethon.tl.types import (
    DocumentAttributeFilename,
    MessageMediaDocument,
    MessageMediaPhoto,
)

from bot.client import userbot
from bot import scheduler as sched_service
from bot.downloads import (
    create_media_download_record,
    download_first_media_url,
    extract_message_urls,
    finalize_download,
    get_download_dir,
    mark_media_download_completed,
    mark_media_download_failed,
    parse_telegram_message_link,
    telegram_source_url,
)
from config import settings
from database.engine import async_session
from database import crud

TZ_CST = timezone(timedelta(hours=8))
MIN_PARALLEL_DOWNLOAD_SIZE = 1024 * 1024
PROGRESS_UPDATE_INTERVAL = 1.5


def _format_bytes(value: int | float | None) -> str:
    if value is None:
        return "未知"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


class DownloadProgress:
    def __init__(self, event: events.NewMessage.Event, label: str, total: int | None = None) -> None:
        self.event = event
        self.label = label
        self.total = total
        self.current = 0
        self.started_at = time.monotonic()
        self.last_update_at = 0.0
        self.lock = asyncio.Lock()
        self.loop = asyncio.get_running_loop()

    async def start(self) -> None:
        await self.update(force=True)

    def telethon_callback(self, current: int, total: int) -> None:
        self.current = int(current or 0)
        if total:
            self.total = int(total)
        self.loop.create_task(self.update())

    def thread_callback(self, current: int, total: int | None = None) -> None:
        self.loop.call_soon_threadsafe(self._schedule_update, int(current or 0), total)

    def thread_reset(self, label: str | None = None, total: int | None = None) -> None:
        self.loop.call_soon_threadsafe(self._schedule_reset, label, total)

    def _schedule_update(self, current: int, total: int | None) -> None:
        self.current = current
        if total:
            self.total = int(total)
        self.loop.create_task(self.update())

    def _schedule_reset(self, label: str | None, total: int | None) -> None:
        self.loop.create_task(self.reset(label, total))

    async def add(self, delta: int) -> None:
        self.current += int(delta or 0)
        await self.update()

    async def reset(self, label: str | None = None, total: int | None = None) -> None:
        if label:
            self.label = label
        self.total = total
        self.current = 0
        self.started_at = time.monotonic()
        self.last_update_at = 0.0
        await self.update(force=True)

    async def update(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_update_at < PROGRESS_UPDATE_INTERVAL:
            return

        async with self.lock:
            now = time.monotonic()
            if not force and now - self.last_update_at < PROGRESS_UPDATE_INTERVAL:
                return
            self.last_update_at = now

            elapsed = max(now - self.started_at, 0.001)
            speed = self.current / elapsed
            text = self._render(speed)
            try:
                await self.event.edit(text)
            except Exception as e:
                logger.debug("[Download] Failed to update progress: {}", e)

    async def finish(self) -> None:
        if self.total:
            self.current = max(self.current, self.total)
        await self.update(force=True)

    def _render(self, speed: float) -> str:
        if self.total:
            percent = min(self.current / self.total * 100, 100)
            return (
                f"{self.label}\n"
                f"进度: {percent:.1f}% ({_format_bytes(self.current)} / {_format_bytes(self.total)})\n"
                f"速度: {_format_bytes(speed)}/s"
            )
        return (
            f"{self.label}\n"
            f"已下载: {_format_bytes(self.current)}\n"
            f"速度: {_format_bytes(speed)}/s"
        )


def _get_topic_id(event: events.NewMessage.Event) -> int:
    """Extract forum topic ID from the outgoing command event."""
    reply_to = getattr(event.message, "reply_to", None)
    if reply_to and getattr(reply_to, "forum_topic", False):
        return reply_to.reply_to_top_id or reply_to.reply_to_msg_id or 0
    return 0


async def _reply(event, text: str) -> None:
    """Edit the outgoing command message, then schedule auto-delete if configured."""
    await event.edit(text)
    sec = settings.cmd_delete_after
    if sec and sec > 0:
        loop = asyncio.get_running_loop()
        chat_id, msg_id = event.chat_id, event.id
        loop.call_later(
            sec,
            lambda: loop.create_task(_do_delete(event, chat_id, msg_id, sec)),
        )


async def _do_delete(event, chat_id: int, msg_id: int, delay: int) -> None:
    try:
        await event.delete()
        logger.debug("[CmdDel] Deleted cmd msg {} in chat {} (after {}s)", msg_id, chat_id, delay)
    except Exception as e:
        logger.warning("[CmdDel] Failed to delete cmd msg {} in {}: {}", msg_id, chat_id, e)


def _message_media_size(message) -> int | None:
    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if document and getattr(document, "size", None):
        return int(document.size)

    photo = getattr(media, "photo", None)
    if photo and getattr(photo, "sizes", None):
        sizes = []
        for size in photo.sizes:
            value = getattr(size, "size", None)
            if value:
                sizes.append(int(value))
        if sizes:
            return max(sizes)

    return None


def _message_media_filename(message) -> str:
    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if document:
        for attr in getattr(document, "attributes", None) or []:
            if isinstance(attr, DocumentAttributeFilename) and attr.file_name:
                return _clean_filename(attr.file_name)

        mime_type = getattr(document, "mime_type", "") or ""
        ext = mimetypes.guess_extension(mime_type) or ".bin"
        return f"telegram_{message.chat_id}_{message.id}{ext}"

    if getattr(media, "photo", None):
        return f"telegram_{message.chat_id}_{message.id}.jpg"

    return f"telegram_{message.chat_id}_{message.id}.bin"


def _parallel_target_file_path(download_dir: Path, message) -> Path:
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


def _normalize_part_size(value: int) -> int:
    part_size = max(32 * 1024, min(value, 512 * 1024))
    return (part_size // 1024) * 1024


async def _write_chunk(path: Path, offset: int, data: bytes) -> None:
    def write() -> None:
        with path.open("r+b") as f:
            f.seek(offset)
            f.write(data)

    await asyncio.to_thread(write)


async def _download_media_parallel(
    message,
    download_dir: Path,
    progress: DownloadProgress | None = None,
) -> str | None:
    media = getattr(message, "media", None)
    if not isinstance(media, (MessageMediaDocument, MessageMediaPhoto)):
        return None

    file_size = _message_media_size(message)
    if not file_size or file_size < MIN_PARALLEL_DOWNLOAD_SIZE:
        return None
    if progress:
        progress.total = file_size

    threads = max(1, int(settings.download_threads or 1))
    if threads <= 1:
        return None

    request_size = _normalize_part_size(int(settings.download_part_size_kb or 512) * 1024)
    if progress:
        progress.label = f"{progress.label}（{threads} 线程）"
    target_path = _parallel_target_file_path(download_dir, message)

    def allocate() -> None:
        with target_path.open("wb") as f:
            f.truncate(file_size)

    await asyncio.to_thread(allocate)

    offsets = list(range(0, file_size, request_size))
    queue: asyncio.Queue[int] = asyncio.Queue()
    for offset in offsets:
        queue.put_nowait(offset)

    async def worker(worker_id: int) -> None:
        while True:
            try:
                offset = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            limit = min(request_size, file_size - offset)
            chunks = []
            try:
                async for chunk in userbot.client.iter_download(
                    media,
                    offset=offset,
                    limit=1,
                    request_size=request_size,
                    chunk_size=request_size,
                ):
                    chunks.append(chunk)
                data = b"".join(chunks)
                if len(data) != limit:
                    raise RuntimeError(f"chunk size mismatch at {offset}: expected {limit}, got {len(data)}")
                await _write_chunk(target_path, offset, data)
                if progress:
                    await progress.add(len(data))
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker(idx)) for idx in range(min(threads, len(offsets)))]
    try:
        await asyncio.gather(*workers)
    except Exception:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        target_path.unlink(missing_ok=True)
        raise

    logger.info(
        "[Download] Parallel Telegram media saved msg={} size={} threads={} part={} -> {}",
        message.id, file_size, threads, request_size, target_path,
    )
    return str(target_path)


async def _download_telegram_media(
    message,
    download_dir: Path,
    progress: DownloadProgress | None = None,
) -> str | None:
    try:
        file_path = await _download_media_parallel(message, download_dir, progress)
        if file_path:
            return file_path
    except Exception as e:
        logger.warning("[Download] Parallel download failed msg={}: {}, falling back", message.id, e)

    if progress:
        await progress.reset("正在下载 Telegram 媒体资源（兼容模式）", _message_media_size(message))
    return await message.download_media(
        file=str(download_dir),
        progress_callback=progress.telethon_callback if progress else None,
    )


async def _download_telegram_message_media(
    chat,
    msg_id: int,
    download_dir: Path,
    progress: DownloadProgress | None = None,
) -> tuple[str | None, str]:
    try:
        msg = await userbot.client.get_messages(chat, ids=msg_id)
    except Exception as e:
        logger.warning("[Download] Failed to fetch Telegram link chat={} msg={}: {}", chat, msg_id, e)
        return None, f"无法读取消息链接: {e}"

    if not msg:
        return None, "消息链接对应的消息不存在或当前账号无权访问"
    if not getattr(msg, "media", None):
        return None, "消息链接对应的消息不是媒体资源"

    try:
        file_path = await _download_telegram_media(msg, download_dir, progress)
    except Exception as e:
        logger.warning("[Download] Failed to download Telegram linked media chat={} msg={}: {}", chat, msg_id, e)
        return None, f"消息链接媒体下载失败: {e}"

    if not file_path:
        return None, "消息链接媒体下载失败: Telegram 未返回文件路径"

    logger.info("[Download] Saved linked Telegram media chat={} msg={} -> {}", chat, msg_id, file_path)
    return file_path, ""


async def _download_first_telegram_message_link(
    urls: list[str],
    download_dir: Path,
    progress: DownloadProgress | None = None,
) -> tuple[str | None, str, str]:
    last_reason = ""
    checked_count = 0
    for url in urls:
        target = parse_telegram_message_link(url)
        if not target:
            continue

        checked_count += 1
        chat, msg_id = target
        if progress:
            await progress.reset("正在下载 Telegram 消息链接媒体")
        file_path, reason = await _download_telegram_message_media(chat, msg_id, download_dir, progress)
        if file_path:
            return file_path, "", url
        last_reason = reason

    if checked_count:
        return None, last_reason or "未找到可下载的 Telegram 消息媒体", ""
    return None, "", ""


_DURATION_RE = re.compile(
    r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", re.IGNORECASE
)


def _parse_duration(s: str) -> timedelta | None:
    """Parse relative duration like '1d5h30m10s' into timedelta. Returns None on failure."""
    m = _DURATION_RE.match(s.strip())
    if not m or not any(m.groups()):
        return None
    d = int(m.group(1) or 0)
    h = int(m.group(2) or 0)
    mi = int(m.group(3) or 0)
    sec = int(m.group(4) or 0)
    return timedelta(days=d, hours=h, minutes=mi, seconds=sec)


def _display_path(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    try:
        return str(Path(path).resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


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


async def _finish_download(
    event,
    file_path: str,
    progress: DownloadProgress | None = None,
    download_id: int | None = None,
    source_url: str | None = None,
) -> None:
    if progress:
        await progress.finish()
    file_size = _path_size(file_path)
    mime_type = _path_mime(file_path)
    if progress:
        await progress.reset("正在保存到下载目标", file_size)
    else:
        await event.edit("正在保存到下载目标...")
    try:
        target = await finalize_download(file_path, progress)
    except Exception as e:
        logger.warning("[Download] Finalize failed for {}: {}", file_path, e)
        if download_id:
            await mark_media_download_failed(download_id, str(e))
        return await _reply(event, f"下载完成，但保存到目标失败: `{e}`\n本地文件: `{_display_path(file_path)}`")
    if download_id:
        await mark_media_download_completed(
            download_id,
            file_path,
            target,
            file_size=file_size,
            mime_type=mime_type,
            source_url=source_url,
        )
    await _reply(event, f"下载完成: `{_display_path(target)}`")


def _is_webpage_preview_media(message) -> bool:
    media = getattr(message, "media", None)
    if not media:
        return False
    return type(media).__name__ == "MessageMediaWebPage" or getattr(media, "webpage", None) is not None


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def register_command_handlers() -> None:
    client = userbot.client

    # ── General ──────────────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.ping$"))
    async def cmd_ping(event: events.NewMessage.Event):
        await _reply(event, "Pong!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.status$"))
    async def cmd_status(event: events.NewMessage.Event):
        me = await client.get_me()
        async with async_session() as session:
            groups = await crud.get_active_groups(session)
            rules = await crud.get_all_rules(session)
            schedules = await crud.get_all_schedules(session)
        text = (
            f"**Userbot 状态**\n"
            f"账号: {me.first_name} (`{me.id}`)\n"
            f"监控群组: {len(groups)}\n"
            f"关键词规则: {len(rules)}\n"
            f"定时任务: {len(schedules)}"
        )
        await _reply(event, text)

    # ── Monitor ──────────────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor add$"))
    async def cmd_monitor_add(event: events.NewMessage.Event):
        chat = await event.get_chat()
        chat_id = event.chat_id
        title = getattr(chat, "title", "Private")
        async with async_session() as session:
            try:
                await crud.add_group(session, chat_id=chat_id, title=title)
                await _reply(event, f"已开始监控: **{title}** (`{chat_id}`)")
            except Exception:
                await _reply(event, f"群组 `{chat_id}` 已在监控中")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor remove$"))
    async def cmd_monitor_remove(event: events.NewMessage.Event):
        chat_id = event.chat_id
        async with async_session() as session:
            removed = await crud.remove_group(session, chat_id=chat_id)
        if removed:
            await _reply(event, f"已停止监控 `{chat_id}`")
        else:
            await _reply(event, "此群组未在监控列表中")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor list$"))
    async def cmd_monitor_list(event: events.NewMessage.Event):
        async with async_session() as session:
            groups = await crud.get_active_groups(session)
        if not groups:
            return await _reply(event, "暂无监控群组")
        lines = ["**监控群组列表：**"]
        for g in groups:
            lines.append(f"- `{g.chat_id}` | {g.title}")
        await _reply(event, "\n".join(lines))

    # ── Media Download ───────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.(?:download|dl)$"))
    async def cmd_download(event: events.NewMessage.Event):
        if not event.is_reply:
            return await _reply(event, "请回复一条媒体消息或包含媒体链接的消息后发送 `.download` 或 `.dl`")

        reply = await event.get_reply_message()
        if not reply:
            return await _reply(event, "未找到被回复的消息")

        download_dir = await get_download_dir()

        urls = extract_message_urls(reply)
        has_telegram_message_link = any(parse_telegram_message_link(url) for url in urls)

        if has_telegram_message_link:
            progress = DownloadProgress(event, "正在下载 Telegram 消息链接媒体")
            await progress.start()
            first_link = next((url for url in urls if parse_telegram_message_link(url)), "")
            record = await create_media_download_record(
                source_type="telegram_message_link",
                trigger_type="command",
                source_url=first_link,
                source_chat=str(event.chat_id),
                source_message_id=reply.id,
            )
            file_path, telegram_link_reason, source_url = await _download_first_telegram_message_link(urls, download_dir, progress)
            if file_path:
                return await _finish_download(event, file_path, progress, record.id, source_url)
            await mark_media_download_failed(record.id, telegram_link_reason or "未找到可下载的 Telegram 消息媒体")
        else:
            telegram_link_reason = ""

        telegram_error = ""
        if getattr(reply, "media", None) and not _is_webpage_preview_media(reply):
            progress = DownloadProgress(event, "正在下载 Telegram 媒体资源", _message_media_size(reply))
            await progress.start()
            record = await create_media_download_record(
                source_type="telegram_media",
                trigger_type="command",
                source_url=telegram_source_url(event.chat_id, reply.id),
                source_chat=str(event.chat_id),
                source_message_id=reply.id,
            )
            try:
                file_path = await _download_telegram_media(reply, download_dir, progress)
            except Exception as e:
                telegram_error = str(e)
                await mark_media_download_failed(record.id, telegram_error)
                logger.warning("[Download] Failed to download Telegram media chat={} msg={}: {}", event.chat_id, reply.id, e)
            else:
                if file_path:
                    logger.info("[Download] Saved media chat={} msg={} -> {}", event.chat_id, reply.id, file_path)
                    return await _finish_download(event, file_path, progress, record.id)
                telegram_error = "Telegram 未返回文件路径"
                await mark_media_download_failed(record.id, telegram_error)

        if not urls:
            if telegram_error:
                return await _reply(event, f"下载失败: `{telegram_error}`")
            return await _reply(event, "被回复的消息不是媒体资源，也没有可检查的链接")

        http_urls = [url for url in urls if not parse_telegram_message_link(url)]
        if not http_urls:
            return await _reply(event, telegram_link_reason or "未找到可下载的 Telegram 消息媒体")

        progress = DownloadProgress(event, "正在下载链接媒体资源")
        await progress.start()
        record = await create_media_download_record(
            source_type="http_url",
            trigger_type="command",
            source_url=http_urls[0],
            source_chat=str(event.chat_id),
            source_message_id=reply.id,
        )
        try:
            file_path, reason, source_url = await asyncio.to_thread(download_first_media_url, http_urls, download_dir, progress)
        except Exception as e:
            logger.exception("[Download] Failed to download linked media chat={} msg={}", event.chat_id, reply.id)
            await mark_media_download_failed(record.id, str(e))
            return await _reply(event, f"链接下载失败: `{e}`")

        if not file_path:
            await mark_media_download_failed(record.id, telegram_link_reason or reason)
            return await _reply(event, telegram_link_reason or reason)
        await _finish_download(event, file_path, progress, record.id, source_url)

    # ── Rules ────────────────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.rule add (.+?) \| (.+?)(?:\s+/del\s*(\d+))?(?:\s+/delay\s*(\d+))?(\s+/nq)?(?:\s+/click(?:\s+(.+?))?)?(?:\s+/if\s+(.+))?$"))
    async def cmd_rule_add(event: events.NewMessage.Event):
        keyword = event.pattern_match.group(1).strip()
        reply_text = event.pattern_match.group(2).strip()
        del_sec = int(event.pattern_match.group(3)) if event.pattern_match.group(3) else 0
        delay_sec = int(event.pattern_match.group(4)) if event.pattern_match.group(4) else 0
        no_quote = bool(event.pattern_match.group(5))
        click_match = event.pattern_match.group(6)
        condition = (event.pattern_match.group(7) or "").strip()
        action = "click_button" if click_match is not None or "/click" in event.raw_text else "reply"
        click_text = click_match.strip() if click_match else ""
        async with async_session() as session:
            rule = await crud.add_rule(
                session, keyword=keyword, reply_text=reply_text, delete_after=del_sec,
                reply_delay=delay_sec, no_quote=no_quote, action=action, click_text=click_text,
                condition=condition,
            )
        extras = []
        if action == "click_button":
            btn_label = f"按钮「{click_text}」" if click_text else "第一个按钮"
            extras.append(f"点击{btn_label}")
        if condition:
            extras.append(f"条件: {condition}")
        if no_quote:
            extras.append("直接发送")
        if delay_sec:
            extras.append(f"延迟{delay_sec}秒")
        if del_sec:
            extras.append(f"{del_sec}秒后删除")
        info = f"（{'，'.join(extras)}）" if extras else ""
        await _reply(event, f"规则 #{rule.id} 已添加: `{keyword}` -> `{reply_text}` {info}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.rule del (\d+)$"))
    async def cmd_rule_del(event: events.NewMessage.Event):
        rule_id = int(event.pattern_match.group(1))
        async with async_session() as session:
            ok = await crud.delete_rule(session, rule_id)
        await _reply(event, f"规则 #{rule_id} 已删除" if ok else f"规则 #{rule_id} 不存在")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.rule list$"))
    async def cmd_rule_list(event: events.NewMessage.Event):
        async with async_session() as session:
            rules = await crud.get_all_rules(session)
        if not rules:
            return await _reply(event, "暂无关键词规则")
        lines = ["**关键词规则列表：**"]
        for r in rules:
            status = "ON" if r.is_active else "OFF"
            scope = "全部" if r.chat_id == 0 else str(r.chat_id)
            topic_tag = f" 话题={r.topic_id}" if r.topic_id else ""
            regex_tag = " [正则]" if r.is_regex else ""
            action_tag = " [点击按钮]" if r.action == "click_button" else ""
            click_tag = f"「{r.click_text}」" if r.action == "click_button" and r.click_text else ""
            cond_tag = f" [if:{r.condition[:30]}]" if r.condition else ""
            nq_tag = " [直发]" if r.no_quote else ""
            delay_tag = f" [delay:{r.reply_delay}s]" if r.reply_delay else ""
            del_tag = f" [del:{r.delete_after}s]" if r.delete_after else ""
            reply_part = f" -> `{r.reply_text}`" if r.reply_text else ""
            lines.append(f"#{r.id} [{status}] 范围={scope}{topic_tag} `{r.keyword}`{regex_tag}{action_tag}{click_tag}{cond_tag}{nq_tag}{delay_tag}{del_tag}{reply_part}")
        await _reply(event, "\n".join(lines))

    # ── Schedule ─────────────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.sched add (.+?) \| (.+?)(?:\s+/del\s*(\d+))?$"))
    async def cmd_sched_add(event: events.NewMessage.Event):
        cron_expr = event.pattern_match.group(1).strip()
        text = event.pattern_match.group(2).strip()
        del_sec = int(event.pattern_match.group(3)) if event.pattern_match.group(3) else 0
        chat_id = event.chat_id
        topic_id = _get_topic_id(event)
        async with async_session() as session:
            sched = await crud.add_schedule(
                session, chat_id=chat_id, text=text,
                cron_expr=cron_expr, delete_after=del_sec, topic_id=topic_id,
            )
        sched_service.add_job(sched)
        del_info = f" [del:{del_sec}s]" if del_sec else ""
        topic_info = f" 话题=`{topic_id}`" if topic_id else ""
        await _reply(event, f"定时任务 #{sched.id} 已添加：cron=`{cron_expr}` 内容=`{text}`{topic_info}{del_info}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.sched once (.+?) \| (.+?)(?:\s+/del\s*(\d+))?$"))
    async def cmd_sched_once(event: events.NewMessage.Event):
        time_str = event.pattern_match.group(1).strip()
        text = event.pattern_match.group(2).strip()
        del_sec = int(event.pattern_match.group(3)) if event.pattern_match.group(3) else 0
        chat_id = event.chat_id
        topic_id = _get_topic_id(event)

        delta = _parse_duration(time_str)
        if delta:
            if delta.total_seconds() <= 0:
                return await _reply(event, "时间必须大于 0")
            run_at = datetime.now(TZ_CST) + delta
            time_label = f"{time_str} 后 ({run_at:%Y-%m-%d %H:%M})"
        else:
            try:
                dt_str = time_str.replace("T", " ")
                run_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_CST)
            except ValueError:
                return await _reply(event, "时间格式错误\n支持: `YYYY-MM-DD HH:MM` 或 `1d5h30m`")
            if run_at <= datetime.now(TZ_CST):
                return await _reply(event, "不能设置过去的时间")
            time_label = f"{run_at:%Y-%m-%d %H:%M}"

        async with async_session() as session:
            sched = await crud.add_schedule(
                session, chat_id=chat_id, text=text,
                run_at=run_at, delete_after=del_sec, topic_id=topic_id,
            )
        sched_service.add_job(sched)
        del_info = f" [del:{del_sec}s]" if del_sec else ""
        topic_info = f" 话题=`{topic_id}`" if topic_id else ""
        await _reply(event, f"定时任务 #{sched.id} 已添加：时间=`{time_label}` 内容=`{text}`{topic_info}{del_info}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.sched del (\d+)$"))
    async def cmd_sched_del(event: events.NewMessage.Event):
        sched_id = int(event.pattern_match.group(1))
        sched_service.remove_job(sched_id)
        async with async_session() as session:
            ok = await crud.delete_schedule(session, sched_id)
        await _reply(event, f"定时任务 #{sched_id} 已删除" if ok else f"定时任务 #{sched_id} 不存在")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.sched list$"))
    async def cmd_sched_list(event: events.NewMessage.Event):
        async with async_session() as session:
            schedules = await crud.get_all_schedules(session)
        if not schedules:
            return await _reply(event, "暂无定时任务")
        lines = ["**定时任务列表：**"]
        for s in schedules:
            status = "ON" if s.is_active else "OFF"
            del_tag = f" [del:{s.delete_after}s]" if s.delete_after else ""
            topic_tag = f" 话题=`{s.topic_id}`" if s.topic_id else ""
            if s.cron_expr:
                trigger = f"cron=`{s.cron_expr}`"
            elif s.run_at:
                trigger = f"时间=`{s.run_at:%Y-%m-%d %H:%M}`"
            else:
                trigger = "???"
            last = f" 上次={s.last_sent_at:%m-%d %H:%M}" if s.last_sent_at else ""
            lines.append(f"#{s.id} [{status}] chat=`{s.chat_id}`{topic_tag} {trigger}{del_tag}{last}\n  `{s.text[:60]}`")
        await _reply(event, "\n".join(lines))

    # ── Help ─────────────────────────────────────────────────

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.help$"))
    async def cmd_help(event: events.NewMessage.Event):
        del_hint = f"\n\n_命令回复将在 {settings.cmd_delete_after} 秒后自动删除_" if settings.cmd_delete_after else ""
        text = (
            "**Userbot 命令帮助**\n\n"

            "**通用**\n"
            "`.ping` — 测试连通性\n"
            "`.status` — 查看状态信息\n"
            "`.help` — 显示本帮助\n\n"

            "**资源下载**\n"
            "回复媒体消息、Telegram 消息链接或媒体直链发送 `.download` 或 `.dl` — 下载到本机 downloads 目录\n\n"

            "**群组监控**\n"
            "`.monitor add` — 监控当前群\n"
            "`.monitor remove` — 取消监控\n"
            "`.monitor list` — 查看监控列表\n\n"

            "**关键词自动回复**\n"
            "`.rule add <关键词> | <回复> [选项]`\n"
            "  例: `.rule add 你好 | 欢迎！`\n"
            "  例: `.rule add 口令: (.+) | $1 /delay 2 /nq`\n"
            "  例: `.rule add 红包 | /click 领取`\n"
            "  例: `.rule add 通知 | {if $1 == \"VIP\"}尊享{else}普通{endif} /if $1 != \"\"`\n"
            "  选项: `/del N` `/delay N` `/nq` `/click [按钮]` `/if 条件`\n"
            "  `/if 条件` = 满足条件才执行（见条件语法）\n"
            "  回复内容支持条件模板: `{if 条件}A{elif 条件}B{else}C{endif}`\n"
            "  正则模式下 `$1` `$2` 引用捕获组内容\n"
            "`.rule del <id>` — 删除规则\n"
            "`.rule list` — 查看所有规则\n\n"

            "**条件语法** (用于 /if 和 {if})\n"
            "  变量: `sender_id` `sender_name` `text` `$1` `$2` `msg_len` `has_buttons`\n"
            "  比较: `==` `!=` `>` `<` `contains` `startswith` `in [a,b]`\n"
            "  逻辑: `and` `or` `not`\n"
            "  例: `sender_id == 123456` `text contains \"VIP\"` `$1 != \"\"`\n\n"

            "**定时消息** (时间为北京时间)\n"
            "`.sched add <cron> | <内容> [/del N]`\n"
            "  例: `.sched add 30 9 * * * | 早上好！`\n"
            "  例: `.sched add 0 */2 * * * | 签到 /del 60`\n"
            "`.sched once <时间> | <内容> [/del N]`\n"
            "  绝对: `.sched once 2026-03-15 10:00 | 开会提醒`\n"
            "  相对: `.sched once 1h30m | 稍后提醒`\n"
            "  相对: `.sched once 1d | 明天提醒 /del 60`\n"
            "  支持: d(天) h(时) m(分) s(秒)，可组合如 `1d5h30m`\n"
            "  📌 在话题中发送命令会自动绑定该话题\n"
            "`.sched del <id>` — 删除任务\n"
            "`.sched list` — 查看所有任务\n\n"

            "**管理操作** — 回复消息或附加 user\\_id\n"
            "`.ban` `.unban` `.kick`\n"
            "`.mute [分钟]` `.unmute`\n"
            "  例: `.mute 30` — 禁言30分钟"
            + del_hint
        )
        await _reply(event, text)

    logger.info("Command handlers registered")

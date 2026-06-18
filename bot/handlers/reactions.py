"""
Reaction-based media download handler.
Downloads media when configured emoji reaction is added to a message,
then pushes the result to a configured notification chat.
"""
from __future__ import annotations

import time

from loguru import logger
from telethon import events

from bot.client import userbot
from bot.downloads import (
    create_media_download_record,
    download_telegram_media_message,
    finalize_download,
    get_download_settings,
    mark_media_download_completed,
    mark_media_download_failed,
    telegram_source_url,
)

REACTION_CACHE_TTL = 12 * 3600

_last_reaction_counts: dict[tuple[str, int, str], int] = {}
_processed_reactions: dict[tuple[str, int, str], float] = {}
_inflight_reactions: set[tuple[str, int, str]] = set()


def _path_size(path) -> int:
    from pathlib import Path

    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def _path_mime(path) -> str:
    import mimetypes

    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or ""


def _reaction_emoji(reaction) -> str:
    raw = getattr(reaction, "reaction", reaction)
    return getattr(raw, "emoticon", "") or getattr(raw, "emoji", "") or str(raw)


def _iter_recent_reactions(update):
    reactions = getattr(update, "reactions", None)
    return getattr(reactions, "recent_reactions", None) or []


def _iter_reaction_counts(update):
    reactions = getattr(update, "reactions", None)
    return getattr(reactions, "results", None) or []


def _iter_new_reactions(update):
    return getattr(update, "new_reactions", None) or []


def _iter_old_reactions(update):
    return getattr(update, "old_reactions", None) or []


def _reaction_count(update, emoji: str) -> int | None:
    total = 0
    matched = False
    for item in _iter_reaction_counts(update):
        if _reaction_emoji(item) != emoji:
            continue
        matched = True
        total += int(getattr(item, "count", 0) or 0)
    return total if matched else None


def _update_msg_id(update) -> int | None:
    msg_id = getattr(update, "msg_id", None)
    return int(msg_id) if msg_id is not None else None


def _peer_cache_key(update) -> str:
    peer = getattr(update, "peer", None)
    if peer is None:
        return ""
    for attr in ("channel_id", "chat_id", "user_id"):
        value = getattr(peer, attr, None)
        if value is not None:
            return f"{type(peer).__name__}:{value}"
    return str(peer)


def _reaction_key(update, msg_id: int, emoji: str) -> tuple[str, int, str]:
    return (_peer_cache_key(update), msg_id, emoji)


def _prune_reaction_cache(now: float) -> None:
    expired = [key for key, ts in _processed_reactions.items() if now - ts > REACTION_CACHE_TTL]
    for key in expired:
        _processed_reactions.pop(key, None)
        _last_reaction_counts.pop(key, None)


def _should_process_reaction(update, msg_id: int, emoji: str) -> tuple[bool, str]:
    key = _reaction_key(update, msg_id, emoji)
    recent_matched = any(_reaction_emoji(item) == emoji for item in _iter_recent_reactions(update))
    if recent_matched:
        return True, "recent_reactions"

    new_matched = any(_reaction_emoji(item) == emoji for item in _iter_new_reactions(update))
    old_matched = any(_reaction_emoji(item) == emoji for item in _iter_old_reactions(update))
    if new_matched and not old_matched:
        return True, "new_reactions"

    current_count = _reaction_count(update, emoji)
    if current_count is None:
        return False, "target emoji not found"

    previous_count = _last_reaction_counts.get(key)
    _last_reaction_counts[key] = current_count
    if current_count <= 0:
        return False, "target emoji count is zero"
    if previous_count is None:
        return True, "reaction count observed"
    if current_count > previous_count:
        return True, f"reaction count increased {previous_count}->{current_count}"
    return False, f"reaction count not increased {previous_count}->{current_count}"


async def _update_chat(update):
    peer = getattr(update, "peer", None)
    if peer is None:
        return None
    return await userbot.client.get_entity(peer)


def register_reaction_handlers() -> None:
    client = userbot.client

    @client.on(events.Raw)
    async def on_raw_update(update):
        if type(update).__name__ not in {"UpdateMessageReactions", "UpdateBotMessageReactions"}:
            return

        config = await get_download_settings()
        if not config.reaction_enabled or not config.reaction_notify_chat_id:
            return

        wanted = config.reaction_emoji.strip() or "👍"
        msg_id = _update_msg_id(update)
        if not msg_id:
            return

        should_process, reason = _should_process_reaction(update, msg_id, wanted)
        if not should_process:
            logger.debug("[ReactionDownload] skipped msg={} reason={}", msg_id, reason)
            return

        now = time.monotonic()
        _prune_reaction_cache(now)
        key = _reaction_key(update, msg_id, wanted)
        if key in _processed_reactions or key in _inflight_reactions:
            logger.debug("[ReactionDownload] duplicate reaction skipped msg={} reason={}", msg_id, reason)
            return
        _inflight_reactions.add(key)

        try:
            logger.info("[ReactionDownload] matched emoji={} msg={} reason={}", wanted, msg_id, reason)
            chat = await _update_chat(update)
            if chat is None:
                return
            msg = await userbot.client.get_messages(chat, ids=msg_id)
            if not msg or not getattr(msg, "media", None):
                logger.debug("[ReactionDownload] msg={} is not media, skipped", msg_id)
                return

            record = await create_media_download_record(
                source_type="telegram_media",
                trigger_type="reaction",
                source_url=telegram_source_url(getattr(msg, "chat_id", None) or getattr(chat, "id", ""), msg_id),
                source_chat=str(getattr(msg, "chat_id", None) or getattr(chat, "id", "")),
                source_message_id=msg_id,
            )
            try:
                local_path = await download_telegram_media_message(msg)
            except Exception as e:
                await mark_media_download_failed(record.id, str(e))
                raise
            if not local_path:
                await mark_media_download_failed(record.id, "Telegram 未返回文件路径")
                return
            file_size = _path_size(local_path)
            mime_type = _path_mime(local_path)
            try:
                target = await finalize_download(local_path)
            except Exception as e:
                await mark_media_download_failed(record.id, str(e))
                raise
            await mark_media_download_completed(record.id, local_path, target, file_size=file_size, mime_type=mime_type)

            chat_title = getattr(chat, "title", None) or getattr(chat, "username", None) or str(getattr(chat, "id", ""))
            text = (
                f"已下载点赞资源\n"
                f"来源: {chat_title}\n"
                f"消息ID: `{msg_id}`\n"
                f"保存到: `{target}`"
            )
            await userbot.send_message(config.reaction_notify_chat_id, text)
            _processed_reactions[key] = time.monotonic()
            logger.info("[ReactionDownload] msg={} chat={} -> {}", msg_id, chat_title, target)
        except Exception as e:
            logger.exception("[ReactionDownload] Failed to process reaction update: {}", e)
            try:
                await userbot.send_message(config.reaction_notify_chat_id, f"点赞资源下载失败: `{e}`")
            except Exception:
                pass
        finally:
            _inflight_reactions.discard(key)

    logger.info("Reaction handlers registered")

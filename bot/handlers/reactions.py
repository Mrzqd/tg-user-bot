"""
Reaction-based media download handler.
Downloads media when configured emoji reaction is removed from a message,
then pushes the result to a configured notification chat.
"""
from __future__ import annotations

import time

from loguru import logger
from telethon import events

from bot.client import userbot
from bot.downloads import (
    get_download_settings,
    get_download_dir,
)
from bot.handlers.commands import (
    DownloadProgress,
    _download_and_finish_telegram_messages,
    _download_success_text,
    _media_group_messages,
    _message_media_size,
)

REACTION_CACHE_TTL = 12 * 3600
REACTION_UPDATE_TYPES = frozenset({
    "UpdateMessageReactions",
    "UpdateBotMessageReaction",
    "UpdateBotMessageReactions",
})

_processed_reactions: dict[tuple[str, int, str], float] = {}
_inflight_reactions: set[tuple[str, int, str]] = set()


def _reaction_emoji(reaction) -> str:
    raw = getattr(reaction, "reaction", reaction)
    return getattr(raw, "emoticon", "") or getattr(raw, "emoji", "") or str(raw)


def _iter_recent_reactions(update):
    reactions = getattr(update, "reactions", None)
    return getattr(reactions, "recent_reactions", None) or []


def _iter_reaction_counts(update):
    reactions = getattr(update, "reactions", None)
    results = getattr(reactions, "results", None)
    if results is not None:
        return results
    # UpdateBotMessageReactions carries ReactionCount objects directly in a
    # vector, while UpdateMessageReactions wraps them in MessageReactions.
    if isinstance(reactions, (list, tuple)):
        return reactions
    return []


def _iter_new_reactions(update):
    return getattr(update, "new_reactions", None) or []


def _iter_old_reactions(update):
    return getattr(update, "old_reactions", None) or []


def _reaction_count(update, emoji: str) -> int | None:
    return _reaction_count_from_items(_iter_reaction_counts(update), emoji)


def _reaction_counts_are_complete(update) -> bool:
    reactions = getattr(update, "reactions", None)
    if isinstance(reactions, (list, tuple)):
        return True
    if getattr(reactions, "min", False):
        return False
    return getattr(reactions, "results", None) is not None


def _reaction_count_from_items(items, emoji: str) -> int | None:
    total = 0
    matched = False
    for item in items or []:
        if _reaction_emoji(item) != emoji:
            continue
        matched = True
        total += int(getattr(item, "count", 0) or 0)
    return total if matched else None


def _update_msg_id(update) -> int | None:
    msg_id = getattr(update, "msg_id", None)
    return int(msg_id) if msg_id is not None else None


def _peer_chat_id(update) -> str:
    """Extract chat_id from update.peer and normalize to the same format as _message_reaction_key.

    Produces the same numeric ID that Telethon's message.chat_id would give:
      PeerChannel(channel_id=123)  -> "-100123"
      PeerChat(chat_id=456)        -> "-456"
      PeerUser(user_id=789)        -> "789"
    """
    peer = getattr(update, "peer", None)
    if peer is None:
        return ""
    channel_id = getattr(peer, "channel_id", None)
    if channel_id is not None:
        return f"-100{channel_id}" if channel_id > 0 else str(channel_id)
    chat_id = getattr(peer, "chat_id", None)
    if chat_id is not None:
        return str(-chat_id) if chat_id > 0 else str(chat_id)
    user_id = getattr(peer, "user_id", None)
    if user_id is not None:
        return str(user_id)
    return str(peer)


def _reaction_key(update, msg_id: int, emoji: str) -> tuple[str, int, str]:
    """Build cache key from raw update, using same format as _message_reaction_key."""
    return (f"chat:{_peer_chat_id(update)}", msg_id, emoji)


def _normalize_chat_id(value) -> str:
    try:
        chat_id = int(value)
    except (TypeError, ValueError):
        return str(value)
    if chat_id < 0:
        return str(chat_id)
    return str(chat_id)


def _message_reaction_key(chat_id: str, msg_id: int, emoji: str) -> tuple[str, int, str]:
    return (f"chat:{_normalize_chat_id(chat_id)}", msg_id, emoji)


def _clear_reaction_cycle(key: tuple[str, int, str]) -> None:
    _processed_reactions.pop(key, None)


def _prune_reaction_cache(now: float) -> None:
    expired = [key for key, ts in _processed_reactions.items() if now - ts > REACTION_CACHE_TTL]
    for key in expired:
        _processed_reactions.pop(key, None)


def _should_process_reaction(update, msg_id: int, emoji: str) -> tuple[bool, str]:
    key = _reaction_key(update, msg_id, emoji)

    if key in _inflight_reactions:
        return False, f"already inflight (key={key[0]})"

    recent_matched = any(_reaction_emoji(item) == emoji for item in _iter_recent_reactions(update))
    new_matched = any(_reaction_emoji(item) == emoji for item in _iter_new_reactions(update))
    old_matched = any(_reaction_emoji(item) == emoji for item in _iter_old_reactions(update))
    current_count = _reaction_count(update, emoji)

    if old_matched and not new_matched:
        if key in _processed_reactions:
            return False, f"already processed (key={key[0]})"
        return True, "target reaction removed"

    if new_matched or recent_matched or (current_count is not None and current_count > 0):
        _clear_reaction_cycle(key)
        return False, "target reaction present"

    if current_count is not None and current_count <= 0:
        if key in _processed_reactions:
            return False, f"already processed (key={key[0]})"
        return True, "target emoji count is zero"

    if _reaction_counts_are_complete(update):
        if key in _processed_reactions:
            return False, f"already processed (key={key[0]})"
        return True, "target emoji count is zero"

    return False, "target emoji not found"


async def _update_chat(update):
    peer = getattr(update, "peer", None)
    if peer is None:
        return None
    return await userbot.client.get_entity(peer)


def _is_downloadable_media_message(message) -> bool:
    media = getattr(message, "media", None)
    if not media:
        return False
    return type(media).__name__ != "MessageMediaWebPage" and getattr(media, "webpage", None) is None


def _display_path(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return str(path)


async def _edit_or_send(chat_id: int, text: str, message=None) -> None:
    if message is not None:
        try:
            await message.edit(text)
            return
        except Exception as e:
            logger.debug("[ReactionDownload] Failed to edit notification message: {}", e)
    await userbot.send_message(chat_id, text)


async def _create_download_progress(chat_id: int, msg) -> tuple[object | None, DownloadProgress | None]:
    try:
        message = await userbot.client.send_message(chat_id, "正在下载 Telegram 媒体资源")
        progress = DownloadProgress(message, "正在下载 Telegram 媒体资源", _message_media_size(msg))
        await progress.start()
        return message, progress
    except Exception as e:
        logger.warning("[ReactionDownload] Failed to create progress notification: {}", e)
        return None, None


async def _notify_download_success(chat_id: int, targets: list[str], message=None) -> None:
    if len(targets) == 1:
        await _edit_or_send(chat_id, _download_success_text(targets[0]), message)
        return
    lines = [f"下载完成，共 {len(targets)} 个资源："]
    lines.extend(f"- {_download_success_text(target)}" for target in targets)
    await _edit_or_send(chat_id, "\n".join(lines), message)


async def _notify_download_partial(chat_id: int, targets: list[str], errors: list[str], message=None) -> None:
    lines = [f"部分下载完成: {len(targets)} 成功，{len(errors)} 失败"]
    lines.extend(f"- {_download_success_text(target)}" for target in targets)
    lines.extend(f"- {error}" for error in errors[:3])
    await _edit_or_send(chat_id, "\n".join(lines), message)


async def _notify_download_failed(chat_id: int, error: Exception | str, message=None) -> None:
    await _edit_or_send(chat_id, f"下载失败: `{error}`", message)


async def _process_reacted_media(chat, msg, msg_id: int, config, reason: str) -> None:
    source_chat = str(getattr(msg, "chat_id", None) or getattr(chat, "id", ""))
    key = _message_reaction_key(source_chat, msg_id, config.reaction_emoji.strip() or "👍")

    if key in _processed_reactions or key in _inflight_reactions:
        logger.debug("[ReactionDownload] duplicate media skipped msg={} reason={}", msg_id, reason)
        return
    _inflight_reactions.add(key)

    try:
        if not _is_downloadable_media_message(msg):
            logger.debug("[ReactionDownload] msg={} is not downloadable media, skipped", msg_id)
            return

        progress_message = None
        progress = None
        try:
            progress_message, progress = await _create_download_progress(config.reaction_notify_chat_id, msg)
            download_dir = await get_download_dir()
            group_messages = await _media_group_messages(msg)
            targets, errors = await _download_and_finish_telegram_messages(
                group_messages,
                download_dir,
                "reaction",
                progress,
            )
        except Exception as e:
            await _notify_download_failed(config.reaction_notify_chat_id, e, progress_message)
            logger.warning("[ReactionDownload] Download failed msg={}: {}", msg_id, e)
            return

        if not targets:
            await _notify_download_failed(
                config.reaction_notify_chat_id,
                errors[0] if errors else "Telegram 未返回文件路径",
                progress_message,
            )
            return

        if errors:
            await _notify_download_partial(config.reaction_notify_chat_id, targets, errors, progress_message)
            return

        chat_title = getattr(chat, "title", None) or getattr(chat, "username", None) or source_chat
        await _notify_download_success(config.reaction_notify_chat_id, targets, progress_message)
        _processed_reactions[key] = time.monotonic()
        for item in group_messages:
            item_chat = str(getattr(item, "chat_id", None) or source_chat)
            item_id = int(getattr(item, "id", 0) or 0)
            if item_id:
                _processed_reactions[_message_reaction_key(item_chat, item_id, config.reaction_emoji.strip() or "👍")] = time.monotonic()
        logger.info("[ReactionDownload] msg={} chat={} reason={} count={}", msg_id, chat_title, reason, len(targets))
    finally:
        _inflight_reactions.discard(key)


def register_reaction_handlers() -> None:
    client = userbot.client

    @client.on(events.Raw)
    async def on_raw_update(update):
        update_type = type(update).__name__
        if update_type not in REACTION_UPDATE_TYPES:
            return

        config = await get_download_settings()
        if not config.reaction_enabled or not config.reaction_notify_chat_id:
            return

        wanted = config.reaction_emoji.strip() or "👍"
        msg_id = _update_msg_id(update)
        if not msg_id:
            return

        now = time.monotonic()
        _prune_reaction_cache(now)

        should_process, reason = _should_process_reaction(update, msg_id, wanted)
        if not should_process:
            logger.debug(
                "[ReactionDownload] skipped msg={} type={} peer={} reason={}",
                msg_id, update_type, _peer_chat_id(update), reason,
            )
            return

        peer_id = _peer_chat_id(update)
        logger.info(
            "[ReactionDownload] matched emoji={} msg={} peer={} type={} reason={}",
            wanted, msg_id, peer_id, update_type, reason,
        )

        try:
            chat = await _update_chat(update)
            if chat is None:
                logger.warning("[ReactionDownload] cannot resolve chat for msg={} peer={}", msg_id, peer_id)
                return
            msg = await userbot.client.get_messages(chat, ids=msg_id)
            if not msg:
                logger.debug("[ReactionDownload] msg={} not found or empty, skipped", msg_id)
                return
            await _process_reacted_media(chat, msg, msg_id, config, reason)
        except Exception as e:
            logger.exception("[ReactionDownload] Failed to process reaction update: {}", e)
            await _notify_download_failed(config.reaction_notify_chat_id, e)

    logger.info("Reaction handlers registered (event-only, trigger=removed)")

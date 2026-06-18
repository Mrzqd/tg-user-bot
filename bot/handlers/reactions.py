"""
Reaction-based media download handler.
Downloads media when configured emoji reaction is added to a message,
then pushes the result to a configured notification chat.
"""
from __future__ import annotations

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


def _update_msg_id(update) -> int | None:
    msg_id = getattr(update, "msg_id", None)
    return int(msg_id) if msg_id is not None else None


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
        recent = _iter_recent_reactions(update)
        if not recent:
            logger.debug("[ReactionDownload] update has no recent reactions, skipped")
            return
        if all(_reaction_emoji(item) != wanted for item in recent):
            return

        msg_id = _update_msg_id(update)
        if not msg_id:
            return

        try:
            chat = await _update_chat(update)
            if chat is None:
                return
            msg = await userbot.client.get_messages(chat, ids=msg_id)
            if not msg or not getattr(msg, "media", None):
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
            logger.info("[ReactionDownload] msg={} chat={} -> {}", msg_id, chat_title, target)
        except Exception as e:
            logger.exception("[ReactionDownload] Failed to process reaction update: {}", e)
            try:
                await userbot.send_message(config.reaction_notify_chat_id, f"点赞资源下载失败: `{e}`")
            except Exception:
                pass

    logger.info("Reaction handlers registered")

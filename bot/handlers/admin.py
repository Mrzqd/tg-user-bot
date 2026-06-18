"""
Group admin operation handlers.
Ban / unban / mute / unmute / kick users via outgoing commands.
"""
from __future__ import annotations

from datetime import timedelta

from loguru import logger
from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

from bot.client import userbot


async def _resolve_target(event: events.NewMessage.Event) -> int | None:
    """Resolve target user from reply or command argument."""
    if event.is_reply:
        reply = await event.get_reply_message()
        return reply.sender_id if reply else None
    parts = event.raw_text.split(maxsplit=1)
    if len(parts) > 1:
        try:
            return int(parts[1].strip())
        except ValueError:
            entity = await userbot.client.get_entity(parts[1].strip())
            return entity.id
    return None


def register_admin_handlers() -> None:
    client = userbot.client

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.ban"))
    async def cmd_ban(event: events.NewMessage.Event):
        target = await _resolve_target(event)
        if not target:
            await event.edit("Reply to a message or provide user id: `.ban <user_id>`")
            return
        try:
            rights = ChatBannedRights(until_date=None, view_messages=True)
            await client(EditBannedRequest(event.chat_id, target, rights))
            await event.edit(f"Banned user `{target}`")
            logger.info("[Admin] Banned {} in {}", target, event.chat_id)
        except Exception as e:
            await event.edit(f"Failed to ban: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.unban"))
    async def cmd_unban(event: events.NewMessage.Event):
        target = await _resolve_target(event)
        if not target:
            await event.edit("Reply to a message or provide user id: `.unban <user_id>`")
            return
        try:
            rights = ChatBannedRights(until_date=None)
            await client(EditBannedRequest(event.chat_id, target, rights))
            await event.edit(f"Unbanned user `{target}`")
            logger.info("[Admin] Unbanned {} in {}", target, event.chat_id)
        except Exception as e:
            await event.edit(f"Failed to unban: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.mute(\s+\S+)?(\s+\d+)?$"))
    async def cmd_mute(event: events.NewMessage.Event):
        target = await _resolve_target(event)
        if not target:
            await event.edit("Reply to a message or provide user id: `.mute <user_id> [minutes]`")
            return
        parts = event.raw_text.split()
        duration_min = int(parts[-1]) if len(parts) >= 3 and parts[-1].isdigit() else 0
        until_date = timedelta(minutes=duration_min) if duration_min > 0 else None
        try:
            rights = ChatBannedRights(until_date=until_date, send_messages=True)
            await client(EditBannedRequest(event.chat_id, target, rights))
            dur_text = f" for {duration_min}min" if duration_min else " permanently"
            await event.edit(f"Muted user `{target}`{dur_text}")
            logger.info("[Admin] Muted {} in {} ({}min)", target, event.chat_id, duration_min)
        except Exception as e:
            await event.edit(f"Failed to mute: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.unmute"))
    async def cmd_unmute(event: events.NewMessage.Event):
        target = await _resolve_target(event)
        if not target:
            await event.edit("Reply to a message or provide user id: `.unmute <user_id>`")
            return
        try:
            rights = ChatBannedRights(until_date=None)
            await client(EditBannedRequest(event.chat_id, target, rights))
            await event.edit(f"Unmuted user `{target}`")
            logger.info("[Admin] Unmuted {} in {}", target, event.chat_id)
        except Exception as e:
            await event.edit(f"Failed to unmute: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.kick"))
    async def cmd_kick(event: events.NewMessage.Event):
        target = await _resolve_target(event)
        if not target:
            await event.edit("Reply to a message or provide user id: `.kick <user_id>`")
            return
        try:
            rights = ChatBannedRights(until_date=None, view_messages=True)
            await client(EditBannedRequest(event.chat_id, target, rights))
            rights_restore = ChatBannedRights(until_date=None)
            await client(EditBannedRequest(event.chat_id, target, rights_restore))
            await event.edit(f"Kicked user `{target}`")
            logger.info("[Admin] Kicked {} from {}", target, event.chat_id)
        except Exception as e:
            await event.edit(f"Failed to kick: {e}")

    logger.info("Admin handlers registered")

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AppSetting, MonitoredGroup, KeywordRule, ScheduledMessage, MessageLog, MediaDownload, _now_cst


# ──────────────────────── MonitoredGroup ────────────────────────

async def get_active_groups(session: AsyncSession) -> Sequence[MonitoredGroup]:
    result = await session.execute(
        select(MonitoredGroup).where(MonitoredGroup.is_active == True)  # noqa: E712
    )
    return result.scalars().all()


async def add_group(session: AsyncSession, chat_id: int, title: str = "") -> MonitoredGroup:
    group = MonitoredGroup(chat_id=chat_id, title=title, is_active=True)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def remove_group(session: AsyncSession, chat_id: int) -> bool:
    result = await session.execute(
        delete(MonitoredGroup).where(MonitoredGroup.chat_id == chat_id)
    )
    await session.commit()
    return result.rowcount > 0


async def toggle_group(session: AsyncSession, chat_id: int, is_active: bool) -> bool:
    result = await session.execute(
        update(MonitoredGroup)
        .where(MonitoredGroup.chat_id == chat_id)
        .values(is_active=is_active)
    )
    await session.commit()
    return result.rowcount > 0


# ──────────────────────── KeywordRule ────────────────────────

async def get_active_rules(session: AsyncSession, chat_id: int = 0) -> Sequence[KeywordRule]:
    stmt = select(KeywordRule).where(KeywordRule.is_active == True)  # noqa: E712
    if chat_id:
        stmt = stmt.where((KeywordRule.chat_id == chat_id) | (KeywordRule.chat_id == 0))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_rules(session: AsyncSession) -> Sequence[KeywordRule]:
    result = await session.execute(select(KeywordRule).order_by(KeywordRule.id.desc()))
    return result.scalars().all()


async def add_rule(
    session: AsyncSession, keyword: str, reply_text: str,
    chat_id: int = 0, topic_id: int = 0, is_regex: bool = False,
    no_quote: bool = False, reply_delay: int = 0, delete_after: int = 0,
    action: str = "reply", click_text: str = "", condition: str = "",
) -> KeywordRule:
    rule = KeywordRule(
        chat_id=chat_id, topic_id=topic_id, keyword=keyword,
        reply_text=reply_text, action=action, click_text=click_text,
        condition=condition, is_regex=is_regex, no_quote=no_quote,
        reply_delay=reply_delay, delete_after=delete_after,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_rule(session: AsyncSession, rule_id: int) -> bool:
    result = await session.execute(delete(KeywordRule).where(KeywordRule.id == rule_id))
    await session.commit()
    return result.rowcount > 0


async def update_rule(
    session: AsyncSession, rule_id: int, **kwargs,
) -> KeywordRule | None:
    result = await session.execute(
        select(KeywordRule).where(KeywordRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return None
    for k, v in kwargs.items():
        if hasattr(rule, k):
            setattr(rule, k, v)
    await session.commit()
    await session.refresh(rule)
    return rule


async def toggle_rule(session: AsyncSession, rule_id: int, is_active: bool) -> bool:
    result = await session.execute(
        update(KeywordRule).where(KeywordRule.id == rule_id).values(is_active=is_active)
    )
    await session.commit()
    return result.rowcount > 0


# ──────────────────────── ScheduledMessage ────────────────────────

async def get_active_schedules(session: AsyncSession) -> Sequence[ScheduledMessage]:
    result = await session.execute(
        select(ScheduledMessage).where(ScheduledMessage.is_active == True)  # noqa: E712
    )
    return result.scalars().all()


async def get_all_schedules(session: AsyncSession) -> Sequence[ScheduledMessage]:
    result = await session.execute(select(ScheduledMessage).order_by(ScheduledMessage.id.desc()))
    return result.scalars().all()


async def add_schedule(
    session: AsyncSession, chat_id: int, text: str,
    cron_expr: str | None = None, run_at: datetime | None = None,
    delete_after: int = 0, topic_id: int = 0,
) -> ScheduledMessage:
    msg = ScheduledMessage(
        chat_id=chat_id, topic_id=topic_id, text=text,
        cron_expr=cron_expr, run_at=run_at,
        delete_after=delete_after,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def delete_schedule(session: AsyncSession, schedule_id: int) -> bool:
    result = await session.execute(
        delete(ScheduledMessage).where(ScheduledMessage.id == schedule_id)
    )
    await session.commit()
    return result.rowcount > 0


async def toggle_schedule(session: AsyncSession, schedule_id: int, is_active: bool) -> bool:
    result = await session.execute(
        update(ScheduledMessage)
        .where(ScheduledMessage.id == schedule_id)
        .values(is_active=is_active)
    )
    await session.commit()
    return result.rowcount > 0


async def update_schedule(
    session: AsyncSession, schedule_id: int, **kwargs,
) -> ScheduledMessage | None:
    result = await session.execute(
        select(ScheduledMessage).where(ScheduledMessage.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        return None
    for k, v in kwargs.items():
        if hasattr(sched, k):
            setattr(sched, k, v)
    await session.commit()
    await session.refresh(sched)
    return sched


async def update_schedule_last_sent(session: AsyncSession, schedule_id: int) -> None:
    await session.execute(
        update(ScheduledMessage)
        .where(ScheduledMessage.id == schedule_id)
        .values(last_sent_at=_now_cst())
    )
    await session.commit()


# ──────────────────────── MessageLog ────────────────────────

async def log_message(
    session: AsyncSession, chat_id: int, sender_id: int,
    sender_name: str, text: str | None, message_id: int,
    topic_id: int = 0,
) -> None:
    entry = MessageLog(
        chat_id=chat_id, topic_id=topic_id, sender_id=sender_id,
        sender_name=sender_name, text=text, message_id=message_id,
    )
    session.add(entry)
    await session.commit()


async def get_message_logs(
    session: AsyncSession, chat_id: int | None = None, limit: int = 50, offset: int = 0,
) -> Sequence[MessageLog]:
    stmt = select(MessageLog).order_by(MessageLog.id.desc()).limit(limit).offset(offset)
    if chat_id:
        stmt = stmt.where(MessageLog.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# ──────────────────────── MediaDownload ────────────────────────

async def create_media_download(
    session: AsyncSession,
    source_type: str,
    trigger_type: str,
    source_url: str = "",
    source_chat: str = "",
    source_message_id: int = 0,
    status: str = "pending",
) -> MediaDownload:
    item = MediaDownload(
        source_type=source_type,
        trigger_type=trigger_type,
        source_url=source_url,
        source_chat=source_chat,
        source_message_id=source_message_id,
        status=status,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_media_download(session: AsyncSession, download_id: int) -> MediaDownload | None:
    result = await session.execute(select(MediaDownload).where(MediaDownload.id == download_id))
    return result.scalar_one_or_none()


async def get_media_downloads(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[MediaDownload]:
    stmt = select(MediaDownload).order_by(MediaDownload.id.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(MediaDownload.status == status)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_media_download(
    session: AsyncSession,
    download_id: int,
    **kwargs,
) -> MediaDownload | None:
    item = await get_media_download(session, download_id)
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    item.updated_at = _now_cst()
    await session.commit()
    await session.refresh(item)
    return item


# ──────────────────────── AppSetting ────────────────────────

async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def get_settings(session: AsyncSession, keys: Sequence[str]) -> dict[str, str]:
    if not keys:
        return {}
    result = await session.execute(select(AppSetting).where(AppSetting.key.in_(keys)))
    return {item.key: item.value for item in result.scalars().all()}


async def set_setting(session: AsyncSession, key: str, value: str) -> AppSetting:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
        setting.updated_at = _now_cst()
    else:
        setting = AppSetting(key=key, value=value)
        session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting


async def set_settings(session: AsyncSession, values: dict[str, str]) -> None:
    for key, value in values.items():
        result = await session.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_at = _now_cst()
        else:
            session.add(AppSetting(key=key, value=value))
    await session.commit()

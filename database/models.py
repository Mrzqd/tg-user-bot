from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TZ_CST = timezone(timedelta(hours=8))


def _now_cst() -> datetime:
    return datetime.now(TZ_CST)


class Base(DeclarativeBase):
    pass


class MonitoredGroup(Base):
    """Groups being monitored for messages."""
    __tablename__ = "monitored_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst, onupdate=_now_cst)


class KeywordRule(Base):
    """Auto-reply rules triggered by keyword matching."""
    __tablename__ = "keyword_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0, comment="0 = all monitored groups")
    topic_id: Mapped[int] = mapped_column(Integer, default=0, comment="0 = all topics in the group")
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    reply_text: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(20), default="reply", comment="reply | click_button")
    click_text: Mapped[str] = mapped_column(String(255), default="", comment="Button text or 0-based index to click, empty = first button")
    condition: Mapped[str] = mapped_column(Text, default="", comment="Condition expression, empty = always match")
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    no_quote: Mapped[bool] = mapped_column(Boolean, default=False, comment="True = send directly, False = reply to trigger message")
    reply_delay: Mapped[int] = mapped_column(Integer, default=0, comment="Delay N seconds before sending reply, 0 = immediate")
    delete_after: Mapped[int] = mapped_column(Integer, default=0, comment="Auto-delete reply after N seconds, 0 = no delete")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst)


class ScheduledMessage(Base):
    """Scheduled messages to be sent at a specific time or on a cron schedule."""
    __tablename__ = "scheduled_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    topic_id: Mapped[int] = mapped_column(Integer, default=0, comment="Forum topic ID, 0 = General / non-forum")
    text: Mapped[str] = mapped_column(Text)
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Cron expression for recurring, null = one-time")
    run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="One-time scheduled datetime (CST/UTC+8)")
    delete_after: Mapped[int] = mapped_column(Integer, default=0, comment="Auto-delete message after N seconds, 0 = no delete")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst)


class MessageLog(Base):
    """Log of monitored messages for audit / analytics."""
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    topic_id: Mapped[int] = mapped_column(Integer, default=0, comment="Forum topic ID, 0 = General / non-forum")
    sender_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sender_name: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst)


class MediaDownload(Base):
    """Media download tasks and results shown in the web console."""
    __tablename__ = "media_downloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True, default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_chat: Mapped[str] = mapped_column(String(255), default="")
    source_message_id: Mapped[int] = mapped_column(BigInteger, default=0)
    trigger_type: Mapped[str] = mapped_column(String(40), index=True, default="")
    status: Mapped[str] = mapped_column(String(20), index=True, default="pending")
    target_type: Mapped[str] = mapped_column(String(20), default="")
    target_path: Mapped[str] = mapped_column(Text, default="")
    local_path: Mapped[str] = mapped_column(Text, default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(120), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    downloaded_bytes: Mapped[int] = mapped_column(BigInteger, default=0, comment="Real-time downloaded bytes for progress")
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0, comment="Total bytes to download, 0 = unknown")
    speed_bps: Mapped[int] = mapped_column(BigInteger, default=0, comment="Current download/upload speed in bytes per second")
    stage: Mapped[str] = mapped_column(String(20), default="", comment="Live stage: downloading | uploading, empty when finished")
    error: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst, onupdate=_now_cst)


class AppSetting(Base):
    """Runtime key-value settings managed from the web console."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_cst, onupdate=_now_cst)

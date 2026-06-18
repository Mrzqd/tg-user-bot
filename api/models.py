from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────── Request models ────────────────────────

class GroupIn(BaseModel):
    chat_id: int
    title: str = ""


class RuleIn(BaseModel):
    keyword: str
    reply_text: str = ""
    chat_id: int = Field(0, description="0 = apply to all monitored groups")
    topic_id: int = Field(0, description="0 = all topics in the group")
    action: str = Field("reply", description="reply | click_button")
    click_text: str = Field("", description="Button text or 0-based index to click")
    condition: str = Field("", description="Condition expression, empty = always trigger")
    is_regex: bool = False
    no_quote: bool = Field(False, description="True = send directly, False = reply to trigger message")
    reply_delay: int = Field(0, ge=0, description="Delay N seconds before reply, 0 = immediate")
    delete_after: int = Field(0, ge=0, description="Auto-delete reply after N seconds, 0 = no delete")


class RuleUpdate(BaseModel):
    keyword: Optional[str] = None
    reply_text: Optional[str] = None
    chat_id: Optional[int] = None
    topic_id: Optional[int] = None
    action: Optional[str] = None
    click_text: Optional[str] = None
    condition: Optional[str] = None
    is_regex: Optional[bool] = None
    no_quote: Optional[bool] = None
    reply_delay: Optional[int] = Field(None, ge=0)
    delete_after: Optional[int] = Field(None, ge=0)


class ScheduleIn(BaseModel):
    chat_id: int
    text: str
    cron_expr: Optional[str] = Field(None, description="Cron expression for recurring, e.g. '30 9 * * 1-5'")
    run_at: Optional[datetime] = Field(None, description="One-time schedule datetime in UTC ISO format")
    delete_after: int = Field(0, ge=0, description="Auto-delete message after N seconds, 0 = no delete")
    topic_id: int = Field(0, description="Forum topic ID, 0 = General / non-forum")


class ScheduleUpdate(BaseModel):
    chat_id: Optional[int] = None
    text: Optional[str] = None
    cron_expr: Optional[str] = None
    run_at: Optional[datetime] = None
    delete_after: Optional[int] = Field(None, ge=0)
    topic_id: Optional[int] = None


class MessageIn(BaseModel):
    chat_id: int
    text: str
    reply_to: Optional[int] = None


class ToggleIn(BaseModel):
    is_active: bool


class WebLoginIn(BaseModel):
    username: str
    password: str
    turnstile_token: str = ""


class TelegramSendCodeIn(BaseModel):
    phone: str


class TelegramSignInIn(BaseModel):
    code: str


class TelegramPasswordIn(BaseModel):
    password: str


class DownloadSettingsIn(BaseModel):
    target_type: str = Field("local", description="local | webdav")
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


# ──────────────────────── Response models ────────────────────────

class GroupOut(BaseModel):
    id: int
    chat_id: int
    title: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleOut(BaseModel):
    id: int
    chat_id: int
    topic_id: int
    keyword: str
    reply_text: str
    action: str
    click_text: str
    condition: str
    is_regex: bool
    no_quote: bool
    reply_delay: int
    delete_after: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleOut(BaseModel):
    id: int
    chat_id: int
    topic_id: int
    text: str
    cron_expr: Optional[str]
    run_at: Optional[datetime]
    delete_after: int
    is_active: bool
    last_sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageLogOut(BaseModel):
    id: int
    chat_id: int
    topic_id: int
    sender_id: int
    sender_name: str
    text: Optional[str]
    message_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusOut(BaseModel):
    user_id: Optional[int]
    username: Optional[str]
    first_name: Optional[str]
    monitored_groups: int
    keyword_rules: int
    scheduled_tasks: int
    scheduler_running: bool
    telegram_authorized: bool = False


class DownloadSettingsOut(BaseModel):
    target_type: str
    local_path: str
    keep_local: bool
    webdav_url: str
    webdav_username: str
    webdav_remote_path: str
    webdav_verify_ssl: bool
    has_webdav_password: bool
    reaction_enabled: bool
    reaction_emoji: str
    reaction_notify_chat_id: int


class MediaDownloadOut(BaseModel):
    id: int
    source_type: str
    source_url: str
    source_chat: str
    source_message_id: int
    trigger_type: str
    status: str
    target_type: str
    target_path: str
    local_path: str
    file_name: str
    mime_type: str
    file_size: int
    error: str
    retry_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    turnstile_site_key: str


class WebAuthConfigOut(BaseModel):
    turnstile_site_key: str
    turnstile_required: bool


class TelegramAuthStatusOut(BaseModel):
    connected: bool
    authorized: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone: str = ""


class TelegramSignInOut(BaseModel):
    status: str

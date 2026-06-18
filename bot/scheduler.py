"""
APScheduler-based message scheduler.
Supports one-time (run_at) and recurring (cron_expr) scheduled messages.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger

from bot.client import userbot
from database.engine import async_session
from database import crud

TZ_CST = timezone(timedelta(hours=8))

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def _job_id(schedule_id: int) -> str:
    return f"sched_{schedule_id}"


async def _send_scheduled_message(schedule_id: int, chat_id: int, text: str, delete_after: int = 0, topic_id: int = 0) -> None:
    try:
        await userbot.send_message(chat_id, text, topic_id=topic_id, delete_after=delete_after or None)
        async with async_session() as session:
            await crud.update_schedule_last_sent(session, schedule_id)
        logger.info("[Scheduler] Sent schedule #{} to {} topic={} (delete_after={}s)", schedule_id, chat_id, topic_id, delete_after)
    except Exception as e:
        logger.error("[Scheduler] Failed to send schedule #{}: {}", schedule_id, e)


def add_job(sched: crud.ScheduledMessage) -> None:
    """Register a single ScheduledMessage as an APScheduler job."""
    job_id = _job_id(sched.id)

    if sched.cron_expr:
        parts = sched.cron_expr.strip().split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4],
            )
        else:
            trigger = CronTrigger.from_crontab(sched.cron_expr)
    elif sched.run_at:
        if sched.run_at.tzinfo is None:
            run_at = sched.run_at.replace(tzinfo=TZ_CST)
        else:
            run_at = sched.run_at
        if run_at <= datetime.now(TZ_CST):
            logger.warning("[Scheduler] Schedule #{} run_at is in the past, skipping", sched.id)
            return
        trigger = DateTrigger(run_date=run_at)
    else:
        logger.warning("[Scheduler] Schedule #{} has no cron_expr or run_at", sched.id)
        return

    scheduler.add_job(
        _send_scheduled_message,
        trigger=trigger,
        id=job_id,
        args=[sched.id, sched.chat_id, sched.text, sched.delete_after, sched.topic_id],
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("[Scheduler] Job {} registered (cron={}, run_at={}, topic={})", job_id, sched.cron_expr, sched.run_at, sched.topic_id)


def remove_job(schedule_id: int) -> None:
    job_id = _job_id(schedule_id)
    try:
        scheduler.remove_job(job_id)
        logger.info("[Scheduler] Job {} removed", job_id)
    except Exception:
        pass


async def load_all_jobs() -> None:
    """Load all active scheduled messages from DB and register as jobs."""
    async with async_session() as session:
        schedules = await crud.get_active_schedules(session)
    for sched in schedules:
        add_job(sched)
    logger.info("[Scheduler] Loaded {} active jobs", len(schedules))


def start() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("[Scheduler] Started")


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Shut down")

from __future__ import annotations

from loguru import logger

from bot import scheduler as sched_service
from bot.handlers import register_all_handlers

_runtime_started = False


async def start_runtime() -> None:
    global _runtime_started
    if _runtime_started:
        return
    register_all_handlers()
    await sched_service.load_all_jobs()
    sched_service.start()
    _runtime_started = True
    logger.info("Telegram runtime is running. Listening for events...")

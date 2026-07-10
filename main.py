"""
Telegram Userbot - Entry Point
Runs Telethon client and FastAPI (uvicorn) in the SAME asyncio event loop
to avoid Telethon's "event loop must not change" error.
"""
from __future__ import annotations

import asyncio

import uvicorn
from loguru import logger

from config import settings
from utils.logger import setup_logging
from database.engine import init_db
from bot.client import userbot
from bot import scheduler as sched_service
from bot.downloads import fail_stale_media_downloads
from bot.runtime import start_runtime
from api.app import create_app


async def main() -> None:
    setup_logging()
    logger.info("Initializing Telegram Userbot...")

    await init_db()
    logger.info("Database initialized")

    stale = await fail_stale_media_downloads()
    if stale:
        logger.info("Marked {} stale download task(s) as failed", stale)

    authorized = await userbot.start_if_authorized()
    if authorized:
        await start_runtime()
    else:
        logger.info("API will start without Telegram authorization. Open web console to login.")

    app = create_app()
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=False,
        loop="none",
    )
    server = uvicorn.Server(config)
    logger.info("API server starting on {}:{}", settings.api_host, settings.api_port)

    try:
        await server.serve()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        sched_service.shutdown()
        await userbot.stop()
        logger.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())

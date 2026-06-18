from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config import settings


def setup_logging() -> None:
    logger.remove()
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, format=fmt, level=settings.log_level, colorize=True)

    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        format=fmt,
        level=settings.log_level,
        rotation="50 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
    logger.info("Logging initialized (level={})", settings.log_level)

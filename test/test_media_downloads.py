from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from os import environ

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("SQLAlchemy 未安装，跳过媒体下载记录数据库测试") from exc

environ.setdefault("TG_API_ID", "1")
environ.setdefault("TG_API_HASH", "test")

from bot.downloads import (
    create_media_download_record,
    mark_media_download_completed,
    mark_media_download_failed,
    queue_media_download_retry,
)
from database import crud
from database.models import Base


class MediaDownloadRecordTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(self.tmp.name) / 'test.db'}")
        self.sessionmaker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        import database.engine as db_engine

        self.original_session = db_engine.async_session
        db_engine.async_session = self.sessionmaker

    async def asyncTearDown(self):
        import database.engine as db_engine

        db_engine.async_session = self.original_session
        await self.engine.dispose()
        self.tmp.cleanup()

    async def test_mark_completed_persists_media_address_and_timing(self):
        local_file = Path(self.tmp.name) / "sample.mp4"
        local_file.write_bytes(b"x" * 1024)

        item = await create_media_download_record(
            source_type="http_url",
            trigger_type="command",
            source_url="https://example.com/sample.mp4",
            source_chat="-1001",
            source_message_id=12,
        )
        await mark_media_download_completed(
            item.id,
            local_file,
            "https://dav.example.com/tg/sample.mp4",
            file_size=local_file.stat().st_size,
            mime_type="video/mp4",
        )

        async with self.sessionmaker() as session:
            downloads = await crud.get_media_downloads(session)

        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0].status, "completed")
        self.assertEqual(downloads[0].target_path, "https://dav.example.com/tg/sample.mp4")
        self.assertEqual(downloads[0].file_size, 1024)
        self.assertEqual(downloads[0].mime_type, "video/mp4")
        self.assertGreaterEqual(downloads[0].duration_ms, 0)

    async def test_retry_queue_increments_retry_count_and_clears_error(self):
        item = await create_media_download_record(
            source_type="telegram_media",
            trigger_type="reaction",
            source_url="telegram://-1001/20",
            source_chat="-1001",
            source_message_id=20,
        )
        await mark_media_download_failed(item.id, "broken pipe")

        queued = await queue_media_download_retry(item.id)

        self.assertIsNotNone(queued)
        self.assertEqual(queued.status, "queued")
        self.assertEqual(queued.retry_count, 1)
        self.assertEqual(queued.error, "")


if __name__ == "__main__":
    unittest.main()

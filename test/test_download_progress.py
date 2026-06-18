from __future__ import annotations

import time
import unittest

try:
    from bot.handlers import commands
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Telethon 未安装，跳过下载进度测试") from exc


class FakeFloodWait(Exception):
    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        super().__init__(f"A wait of {seconds} seconds is required (caused by EditMessageRequest)")


class DownloadProgressTest(unittest.IsolatedAsyncioTestCase):
    def test_flood_wait_seconds_parses_error_message(self):
        error = Exception("A wait of 245 seconds is required (caused by EditMessageRequest)")

        self.assertEqual(commands.DownloadProgress._flood_wait_seconds(error), 245)

    async def test_progress_pauses_updates_after_flood_wait(self):
        edits: list[str] = []

        class FakeEvent:
            async def edit(self, text: str) -> None:
                edits.append(text)
                raise FakeFloodWait(245)

        progress = commands.DownloadProgress(FakeEvent(), "正在下载 Telegram 媒体资源", 100)

        await progress.start()
        progress.last_update_at -= commands.PROGRESS_FORCE_UPDATE_INTERVAL
        progress.current = 50
        await progress.update(force=True)

        self.assertEqual(len(edits), 1)
        self.assertGreater(progress.flood_wait_until - time.monotonic(), 200)


if __name__ == "__main__":
    unittest.main()

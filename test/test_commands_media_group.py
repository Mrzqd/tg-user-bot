from __future__ import annotations

import unittest
import tempfile
from types import SimpleNamespace

try:
    from bot.handlers import commands
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Telethon 未安装，跳过媒体组下载测试") from exc


class MediaGroupDownloadTest(unittest.IsolatedAsyncioTestCase):
    async def test_media_group_messages_collects_grouped_media(self):
        base = SimpleNamespace(id=10, chat_id=1001, grouped_id=55, media=SimpleNamespace())
        same_before = SimpleNamespace(id=9, chat_id=1001, grouped_id=55, media=SimpleNamespace())
        same_after = SimpleNamespace(id=11, chat_id=1001, grouped_id=55, media=SimpleNamespace())
        other_group = SimpleNamespace(id=12, chat_id=1001, grouped_id=99, media=SimpleNamespace())
        no_media = SimpleNamespace(id=13, chat_id=1001, grouped_id=55, media=None)

        class FakeClient:
            async def iter_messages(self, chat_id, min_id=0, max_id=0, reverse=False):
                for item in [same_after, other_group, same_before, no_media]:
                    yield item

        original_client = getattr(commands.userbot, "_client", None)
        commands.userbot._client = FakeClient()
        try:
            result = await commands._media_group_messages(base)
        finally:
            commands.userbot._client = original_client

        self.assertEqual([item.id for item in result], [9, 10, 11])

    async def test_media_group_messages_returns_single_without_grouped_id(self):
        message = SimpleNamespace(id=10, chat_id=1001, grouped_id=None, media=SimpleNamespace())

        result = await commands._media_group_messages(message)

        self.assertEqual(result, [message])

    async def test_download_telegram_media_skips_existing_local_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            download_dir = commands.Path(tmp)
            target = download_dir / "telegram_1001_10.jpg"
            target.write_bytes(b"existing")
            message = SimpleNamespace(
                id=10,
                chat_id=1001,
                media=SimpleNamespace(photo=SimpleNamespace()),
                download_media_called=False,
            )

            async def fake_download_media(**kwargs):
                message.download_media_called = True
                return str(target)

            message.download_media = fake_download_media

            result = await commands._download_telegram_media(message, download_dir)

        self.assertEqual(result, str(target))
        self.assertFalse(message.download_media_called)

    async def test_download_telegram_media_redownloads_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            download_dir = commands.Path(tmp)
            target = download_dir / "telegram_1001_10.mp4"
            target.write_bytes(b"partial")
            document = SimpleNamespace(
                mime_type="video/mp4",
                size=128,
                attributes=[],
            )
            message = SimpleNamespace(
                id=10,
                chat_id=1001,
                media=SimpleNamespace(document=document),
                download_media_called=False,
            )

            async def fake_download_media(**kwargs):
                message.download_media_called = True
                return str(target)

            message.download_media = fake_download_media

            result = await commands._download_telegram_media(message, download_dir)

        self.assertEqual(result, str(target))
        self.assertTrue(message.download_media_called)

    def test_download_success_text_marks_existing_upload(self):
        target = commands.FinalizeResult("https://example.test/video.mp4", existed=True)

        self.assertEqual(
            commands._download_success_text(target),
            "文件已存在，上传完成: `https://example.test/video.mp4`",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
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


if __name__ == "__main__":
    unittest.main()

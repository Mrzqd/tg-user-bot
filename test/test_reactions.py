from __future__ import annotations

import unittest
from types import SimpleNamespace

try:
    from bot.handlers import reactions
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Telethon 未安装，跳过表情监听匹配测试") from exc


def _reaction_update(*, results=None, recent=None, new=None, old=None, min_reactions=None):
    reaction_data = {}
    if results is not None:
        reaction_data["results"] = results
    if recent is not None:
        reaction_data["recent_reactions"] = recent
    if min_reactions is not None:
        reaction_data["min"] = min_reactions
    return SimpleNamespace(
        peer=SimpleNamespace(channel_id=1001),
        reactions=SimpleNamespace(**reaction_data),
        new_reactions=new or [],
        old_reactions=old or [],
    )


def _reaction_count(count: int):
    return SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=count)


class ReactionMatchingTest(unittest.TestCase):
    def setUp(self):
        reactions._processed_reactions.clear()
        reactions._inflight_reactions.clear()

    def test_downloads_when_target_reaction_count_disappears(self):
        update = _reaction_update(results=[])

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "target emoji count is zero")

    def test_duplicate_removal_event_is_skipped_after_success(self):
        update = _reaction_update(results=[])
        key = reactions._reaction_key(update, 10, "👍")
        reactions._processed_reactions[key] = 1.0

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "already processed (key=chat:-1001001)")

    def test_new_reaction_rearms_a_processed_message_without_downloading(self):
        update = _reaction_update(results=[_reaction_count(1)])
        key = reactions._reaction_key(update, 10, "👍")
        reactions._processed_reactions[key] = 1.0

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "target reaction present")
        self.assertNotIn(key, reactions._processed_reactions)

    def test_downloads_explicit_old_reaction_delta(self):
        update = _reaction_update(
            old=[SimpleNamespace(emoticon="👍")],
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "target reaction removed")

    def test_ignores_new_reaction(self):
        update = _reaction_update(
            new=[SimpleNamespace(emoticon="👍")],
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "target reaction present")

    def test_ignores_target_reaction_count_increase(self):
        update = _reaction_update(results=[_reaction_count(2)])

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "target reaction present")

    def test_ignores_partial_update_without_target_reaction(self):
        update = _reaction_update(results=[], min_reactions=True)

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "target emoji not found")

    def test_bot_reaction_count_list_without_target_triggers_download(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=[],
            new_reactions=[],
            old_reactions=[],
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "target emoji count is zero")

    def test_accepts_single_bot_reaction_update_type(self):
        self.assertIn("UpdateBotMessageReaction", reactions.REACTION_UPDATE_TYPES)

    def test_message_reaction_key_normalizes_chat_id(self):
        self.assertEqual(
            reactions._message_reaction_key(1001, 10, "👍"),
            ("chat:1001", 10, "👍"),
        )
        self.assertEqual(
            reactions._message_reaction_key("-1001001", 10, "👍"),
            ("chat:-1001001", 10, "👍"),
        )


class ReactionDownloadTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reactions._processed_reactions.clear()
        reactions._inflight_reactions.clear()

    async def test_process_reacted_media_uses_progress_notification(self):
        chat = SimpleNamespace(id=1001, title="group-a")
        message = SimpleNamespace(
            id=10,
            chat_id=1001,
            media=SimpleNamespace(),
            reactions=SimpleNamespace(
                results=[],
            ),
        )
        config = SimpleNamespace(reaction_emoji="👍", reaction_notify_chat_id=2001)
        progress_calls: list[str] = []

        class FakeProgress:
            def __init__(self, event, label, total=None):
                progress_calls.append(f"init:{label}:{total}")
                self.event = event

            async def start(self):
                progress_calls.append("start")

        class FakeNotification:
            def __init__(self):
                self.edits: list[str] = []

            async def edit(self, text):
                self.edits.append(text)

        notification = FakeNotification()

        async def fake_get_download_dir():
            return "/tmp"

        async def fake_download(download_messages, download_dir, trigger_type, progress):
            progress_calls.append(f"download:{download_dir}:{progress is not None}")
            return ["/downloads/video.mp4"], []

        class FakeClient:
            async def send_message(self, chat_id, text):
                progress_calls.append(f"send:{chat_id}:{text}")
                return notification

        originals = {
            "client": getattr(reactions.userbot, "_client", None),
            "progress": reactions.DownloadProgress,
            "get_download_dir": reactions.get_download_dir,
            "download": reactions._download_and_finish_telegram_messages,
            "media_size": reactions._message_media_size,
        }
        reactions.userbot._client = FakeClient()
        reactions.DownloadProgress = FakeProgress
        reactions.get_download_dir = fake_get_download_dir
        reactions._download_and_finish_telegram_messages = fake_download
        reactions._message_media_size = lambda _: 2048
        try:
            await reactions._process_reacted_media(chat, message, message.id, config, "target emoji count is zero")
        finally:
            reactions.userbot._client = originals["client"]
            reactions.DownloadProgress = originals["progress"]
            reactions.get_download_dir = originals["get_download_dir"]
            reactions._download_and_finish_telegram_messages = originals["download"]
            reactions._message_media_size = originals["media_size"]

        self.assertIn("send:2001:正在下载 Telegram 媒体资源", progress_calls)
        self.assertIn("init:正在下载 Telegram 媒体资源:2048", progress_calls)
        self.assertIn("start", progress_calls)
        self.assertIn("download:/tmp:True", progress_calls)
        self.assertEqual(notification.edits, ["下载完成: `/downloads/video.mp4`"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from types import SimpleNamespace

try:
    from bot.handlers import reactions
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Telethon 未安装，跳过表情监听匹配测试") from exc


class ReactionMatchingTest(unittest.TestCase):
    def setUp(self):
        reactions._last_reaction_counts.clear()
        reactions._processed_reactions.clear()
        reactions._pending_reactions.clear()
        reactions._inflight_reactions.clear()

    def test_matches_recent_reaction(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                recent_reactions=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍")),
                ],
            ),
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "recent_reactions")

    def test_matches_recent_reaction_when_aggregate_counts_are_partial(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                min=True,
                results=[],
                recent_reactions=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍")),
                ],
            ),
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "recent_reactions")

    def test_recent_reaction_wins_when_target_count_is_omitted(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                results=[],
                recent_reactions=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍")),
                ],
            ),
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "recent_reactions")

    def test_matches_aggregate_reaction_count_first_seen(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                recent_reactions=[],
                results=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1),
                ],
            ),
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "reaction count first observed (count=1)")

    def test_matches_bot_reaction_update_count_list(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=[
                SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1),
            ],
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "reaction count first observed (count=1)")

    def test_accepts_single_bot_reaction_update_type(self):
        self.assertIn("UpdateBotMessageReaction", reactions.REACTION_UPDATE_TYPES)

    def test_matches_new_reaction(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            new_reactions=[
                SimpleNamespace(emoticon="👍"),
            ],
            old_reactions=[],
            reactions=SimpleNamespace(recent_reactions=[], results=[]),
        )

        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "new_reactions")

    def test_skips_aggregate_reaction_count_without_increase(self):
        update = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                recent_reactions=[],
                results=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=2),
                ],
            ),
        )

        reactions._should_process_reaction(update, 10, "👍")
        matched, reason = reactions._should_process_reaction(update, 10, "👍")

        self.assertFalse(matched)
        self.assertEqual(reason, "reaction count not increased 2->2")

    def test_matches_aggregate_reaction_count_increase(self):
        first = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                recent_reactions=[],
                results=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1),
                ],
            ),
        )
        second = SimpleNamespace(
            peer=SimpleNamespace(channel_id=1001),
            reactions=SimpleNamespace(
                recent_reactions=[],
                results=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=2),
                ],
            ),
        )

        reactions._should_process_reaction(first, 10, "👍")
        matched, reason = reactions._should_process_reaction(second, 10, "👍")

        self.assertTrue(matched)
        self.assertEqual(reason, "reaction count increased 1->2")

    def test_unreact_then_react_starts_a_new_download_cycle(self):
        key_update = SimpleNamespace(peer=SimpleNamespace(channel_id=1001))
        added = SimpleNamespace(
            peer=key_update.peer,
            reactions=SimpleNamespace(
                recent_reactions=[],
                results=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1),
                ],
            ),
        )
        removed = SimpleNamespace(
            peer=key_update.peer,
            reactions=SimpleNamespace(recent_reactions=[], results=[]),
        )

        matched, _ = reactions._should_process_reaction(added, 10, "👍")
        self.assertTrue(matched)
        key = reactions._reaction_key(key_update, 10, "👍")
        reactions._processed_reactions[key] = 1.0

        matched, reason = reactions._should_process_reaction(removed, 10, "👍")
        self.assertFalse(matched)
        self.assertEqual(reason, "target emoji count is zero")
        self.assertNotIn(key, reactions._processed_reactions)
        self.assertEqual(reactions._last_reaction_counts[key], 0)

        matched, reason = reactions._should_process_reaction(added, 10, "👍")
        self.assertTrue(matched)
        self.assertEqual(reason, "reaction count increased 0->1")

    def test_message_reaction_key_normalizes_chat_id(self):
        self.assertEqual(
            reactions._message_reaction_key(1001, 10, "👍"),
            ("chat:1001", 10, "👍"),
        )
        self.assertEqual(
            reactions._message_reaction_key("-1001001", 10, "👍"),
            ("chat:-1001001", 10, "👍"),
        )


class ReactionPollingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reactions._last_reaction_counts.clear()
        reactions._processed_reactions.clear()
        reactions._pending_reactions.clear()
        reactions._inflight_reactions.clear()

    async def test_iter_reaction_dialogs_uses_all_visible_dialog_entities(self):
        dialogs = [
            SimpleNamespace(id=1001, entity=SimpleNamespace(id=1001, title="group-a")),
            SimpleNamespace(id=1002, entity=SimpleNamespace(id=1002, title="group-b")),
            SimpleNamespace(id=1001, entity=SimpleNamespace(id=1001, title="duplicate")),
            SimpleNamespace(id=1003, entity=None),
        ]

        class FakeClient:
            async def iter_dialogs(self, limit=None):
                for dialog in dialogs:
                    yield dialog

        original = getattr(reactions.userbot, "_client", None)
        reactions.userbot._client = FakeClient()
        try:
            found = [chat async for chat in reactions._iter_reaction_dialogs()]
        finally:
            reactions.userbot._client = original

        self.assertEqual([chat.id for chat in found], [1001, 1002])

    async def test_poll_builds_baseline_before_downloading(self):
        chat = SimpleNamespace(id=1001, title="group-a")
        message = SimpleNamespace(
            id=10,
            chat_id=1001,
            media=SimpleNamespace(),
            reactions=SimpleNamespace(
                results=[SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1)],
            ),
        )
        config = SimpleNamespace(reaction_emoji="👍", reaction_notify_chat_id=2001)
        processed: list[str] = []

        class FakeClient:
            async def iter_messages(self, target, limit=None):
                yield message

        async def fake_process(chat_arg, msg_arg, msg_id_arg, config_arg, reason_arg):
            processed.append(reason_arg)

        original_client = getattr(reactions.userbot, "_client", None)
        original_process = reactions._process_reacted_media
        reactions.userbot._client = FakeClient()
        reactions._process_reacted_media = fake_process
        try:
            await reactions._poll_chat_reactions(chat, config)
            self.assertEqual(processed, [])

            message.reactions.results[0].count = 2
            await reactions._poll_chat_reactions(chat, config)
        finally:
            reactions.userbot._client = original_client
            reactions._process_reacted_media = original_process

        self.assertEqual(processed, ["poll reaction count increased 1->2"])

    async def test_poll_retries_pending_reaction_without_count_increase(self):
        chat = SimpleNamespace(id=1001, title="group-a")
        message = SimpleNamespace(
            id=10,
            chat_id=1001,
            media=SimpleNamespace(),
            reactions=SimpleNamespace(
                results=[SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1)],
            ),
        )
        config = SimpleNamespace(reaction_emoji="👍", reaction_notify_chat_id=2001)
        key = reactions._message_reaction_key(1001, 10, "👍")
        reactions._last_reaction_counts[key] = 1
        reactions._pending_reactions[key] = (0.0, "raw update")
        processed: list[str] = []

        class FakeClient:
            async def iter_messages(self, target, limit=None):
                yield message

        async def fake_process(chat_arg, msg_arg, msg_id_arg, config_arg, reason_arg):
            processed.append(reason_arg)

        original_client = getattr(reactions.userbot, "_client", None)
        original_process = reactions._process_reacted_media
        reactions.userbot._client = FakeClient()
        reactions._process_reacted_media = fake_process
        try:
            await reactions._poll_chat_reactions(chat, config)
        finally:
            reactions.userbot._client = original_client
            reactions._process_reacted_media = original_process

        self.assertEqual(processed, ["retry pending reaction (raw update)"])

    async def test_process_reacted_media_uses_progress_notification(self):
        chat = SimpleNamespace(id=1001, title="group-a")
        message = SimpleNamespace(
            id=10,
            chat_id=1001,
            media=SimpleNamespace(),
            reactions=SimpleNamespace(
                results=[SimpleNamespace(reaction=SimpleNamespace(emoticon="👍"), count=1)],
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

            async def finish(self):
                progress_calls.append("finish")

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
            await reactions._process_reacted_media(chat, message, message.id, config, "test")
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
        self.assertEqual(
            notification.edits,
            ["下载完成: `/downloads/video.mp4`"],
        )


if __name__ == "__main__":
    unittest.main()

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
        self.assertEqual(reason, "reaction count observed")

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


if __name__ == "__main__":
    unittest.main()

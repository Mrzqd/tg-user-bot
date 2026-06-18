from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from os import environ

environ.setdefault("TG_API_ID", "1")
environ.setdefault("TG_API_HASH", "test")

from bot.downloads import _duration_ms


class DownloadTimeTest(unittest.TestCase):
    def test_duration_handles_naive_started_and_aware_completed(self):
        started = datetime(2026, 6, 18, 10, 0, 0)
        completed = datetime(2026, 6, 18, 10, 0, 3, tzinfo=timezone(timedelta(hours=8)))

        self.assertEqual(_duration_ms(started, completed), 3000)

    def test_duration_handles_aware_started_and_naive_completed(self):
        started = datetime(2026, 6, 18, 10, 0, 0, tzinfo=timezone(timedelta(hours=8)))
        completed = datetime(2026, 6, 18, 10, 0, 2)

        self.assertEqual(_duration_ms(started, completed), 2000)


if __name__ == "__main__":
    unittest.main()

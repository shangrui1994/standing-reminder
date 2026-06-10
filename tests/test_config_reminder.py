from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from config import DEFAULT_CONFIG, MAX_INTERVAL_MINUTES, ReminderConfig, normalize_config
from reminder import ReminderState, format_elapsed, is_work_time


class ConfigTests(unittest.TestCase):
    def test_normalize_config_falls_back_for_invalid_values(self) -> None:
        config = normalize_config(
            {
                "work_start": "bad",
                "work_end": "25:00",
                "interval_minutes": "x",
            }
        )

        self.assertEqual(config, DEFAULT_CONFIG)

    def test_normalize_config_clamps_interval(self) -> None:
        config = normalize_config(
            {
                "work_start": "08:30",
                "work_end": "17:45",
                "interval_minutes": 999,
                "auto_start": True,
            }
        )

        self.assertEqual(config.work_start, "08:30")
        self.assertEqual(config.work_end, "17:45")
        self.assertEqual(config.interval_minutes, MAX_INTERVAL_MINUTES)
        self.assertTrue(config.auto_start)


class ReminderTests(unittest.TestCase):
    def test_is_work_time_supports_overnight_schedule(self) -> None:
        config = ReminderConfig(work_start="22:00", work_end="06:00", interval_minutes=60)

        self.assertTrue(is_work_time(config, datetime(2026, 6, 10, 23, 0)))
        self.assertTrue(is_work_time(config, datetime(2026, 6, 11, 5, 30)))
        self.assertFalse(is_work_time(config, datetime(2026, 6, 11, 12, 0)))

    def test_next_check_handles_overdue_reminder(self) -> None:
        now = datetime(2026, 6, 10, 10, 0)
        state = ReminderState(
            last_reminder_at=now - timedelta(hours=2),
            last_stood_at=now - timedelta(hours=2),
        )

        self.assertEqual(state.next_check_delay_ms(DEFAULT_CONFIG, now), 1_000)

    def test_mute_today_clears_pause(self) -> None:
        now = datetime(2026, 6, 10, 10, 0)
        state = ReminderState(last_reminder_at=now, last_stood_at=now)
        state.pause_for(timedelta(hours=1), now)
        state.mute_today(now)

        self.assertIsNone(state.paused_until)
        self.assertTrue(state.is_muted_today(now))

    def test_elapsed_format_is_clock_style(self) -> None:
        self.assertEqual(
            format_elapsed(timedelta(hours=2, minutes=3, seconds=4)),
            "02小时 03分钟 04秒",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from config import ReminderConfig, parse_time


def format_elapsed(delta: timedelta) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}小时 {minutes:02d}分钟 {seconds:02d}秒"


def time_on_day(day: date, value: time) -> datetime:
    return datetime.combine(day, value)


def is_work_time(config: ReminderConfig, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    start = parse_time(config.work_start)
    end = parse_time(config.work_end)
    current = now.time().replace(second=0, microsecond=0)
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def next_work_start(config: ReminderConfig, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    start = parse_time(config.work_start)
    end = parse_time(config.work_end)
    today_start = time_on_day(now.date(), start)

    if start <= end:
        if now <= today_start:
            return today_start
        return today_start + timedelta(days=1)

    if now.time().replace(second=0, microsecond=0) < start:
        return today_start
    return today_start + timedelta(days=1)


@dataclass
class ReminderState:
    last_reminder_at: datetime
    last_stood_at: datetime
    paused_until: datetime | None = None
    muted_on: date | None = None

    @classmethod
    def create(cls) -> "ReminderState":
        now = datetime.now()
        return cls(last_reminder_at=now, last_stood_at=now)

    def mark_stood(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        self.last_stood_at = now
        self.reset_clock(now)

    def reset_clock(self, now: datetime | None = None) -> None:
        self.last_reminder_at = now or datetime.now()

    def pause_for(self, duration: timedelta, now: datetime | None = None) -> None:
        now = now or datetime.now()
        self.paused_until = now + duration

    def mute_today(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        self.paused_until = None
        self.muted_on = now.date()

    def resume(self) -> None:
        self.paused_until = None
        self.muted_on = None

    def is_paused(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        if self.paused_until and now < self.paused_until:
            return True
        self.paused_until = None
        return False

    def is_muted_today(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        return self.muted_on == now.date()

    def elapsed_since_stood(self, now: datetime | None = None) -> str:
        now = now or datetime.now()
        return format_elapsed(now - self.last_stood_at)

    def next_due_at(self, config: ReminderConfig) -> datetime:
        return self.last_reminder_at + timedelta(minutes=config.interval_minutes)

    def should_remind(self, config: ReminderConfig, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        if self.is_paused(now) or self.is_muted_today(now) or not is_work_time(config, now):
            return False
        return now >= self.next_due_at(config)

    def next_check_delay_ms(self, config: ReminderConfig, now: datetime | None = None) -> int:
        now = now or datetime.now()
        candidates: list[datetime] = []

        if self.paused_until and now < self.paused_until:
            candidates.append(self.paused_until)

        if self.is_muted_today(now):
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min)
            candidates.append(max(tomorrow, next_work_start(config, now)))

        if not is_work_time(config, now):
            candidates.append(next_work_start(config, now))
        else:
            candidates.append(self.next_due_at(config))

        future_candidates = [candidate for candidate in candidates if candidate > now]
        if not future_candidates:
            return 1_000
        next_check = min(future_candidates)
        milliseconds = int((next_check - now).total_seconds() * 1000)
        return max(1_000, min(milliseconds, 86_400_000))

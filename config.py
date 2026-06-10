from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths, QTime


APP_NAME = "站立提醒工具"
INSTANCE_KEY = "StandingReminderTool.Chen.SingleInstance"

MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 120


@dataclass(frozen=True)
class ReminderConfig:
    work_start: str = "09:00"
    work_end: str = "18:00"
    interval_minutes: int = 60
    auto_start: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CONFIG = ReminderConfig()


def resource_path(relative_path: str) -> Path:
    import sys

    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def config_path() -> Path:
    location = os.environ.get("LOCALAPPDATA") or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    path = (Path(location) / APP_NAME) if location else Path.home() / "AppData" / "Local" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path / "config.json"


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def valid_time_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = QTime.fromString(value, "HH:mm")
    if not parsed.isValid():
        return None
    return f"{parsed.hour():02d}:{parsed.minute():02d}"


def clamp_interval(value: Any) -> int:
    try:
        interval = int(value)
    except (TypeError, ValueError):
        return DEFAULT_CONFIG.interval_minutes
    return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, interval))


def normalize_config(data: Any) -> ReminderConfig:
    if not isinstance(data, dict):
        return DEFAULT_CONFIG

    start = valid_time_text(data.get("work_start")) or DEFAULT_CONFIG.work_start
    end = valid_time_text(data.get("work_end")) or DEFAULT_CONFIG.work_end
    interval = clamp_interval(data.get("interval_minutes", DEFAULT_CONFIG.interval_minutes))
    auto_start = bool(data.get("auto_start", DEFAULT_CONFIG.auto_start))
    return ReminderConfig(
        work_start=start,
        work_end=end,
        interval_minutes=interval,
        auto_start=auto_start,
    )


def load_config() -> ReminderConfig:
    path = config_path()
    if not path.exists():
        return DEFAULT_CONFIG
    try:
        return normalize_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG


def save_config(config: ReminderConfig) -> None:
    config_path().write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def format_qtime(value: QTime) -> str:
    return f"{value.hour():02d}:{value.minute():02d}"

from __future__ import annotations

import subprocess
import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "StandingReminder"
LEGACY_RUN_VALUE_NAMES = ("站立提醒工具", "绔欑珛鎻愰啋宸ュ叿")


def current_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])

    script_path = Path(__file__).resolve().with_name("main.py")
    return subprocess.list2cmdline([sys.executable, str(script_path)])


def is_auto_start_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return value == current_launch_command()
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_auto_start_enabled(enabled: bool) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, current_launch_command())
        else:
            delete_value_if_exists(key, RUN_VALUE_NAME)
        for legacy_name in LEGACY_RUN_VALUE_NAMES:
            delete_value_if_exists(key, legacy_name)


def delete_value_if_exists(key, name: str) -> None:
    try:
        winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass

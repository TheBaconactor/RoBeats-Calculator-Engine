from __future__ import annotations

import os
import threading

from gear_optimizer.core.env_config import TRUTHY_ENV_VALUES

_WIN_TIMER_LOCK = threading.Lock()
_WIN_TIMER_USERS = 0
_WIN_TIMER_ACTIVE = False


def system_timer_override_allowed() -> bool:
    """
    Guard system-wide WinMM timer period changes behind an explicit opt-in.

    `timeBeginPeriod(1)` affects the entire OS timer resolution while active in this process.
    Keep this disabled by default to avoid unexpected system-wide side effects.
    """
    raw = str(os.environ.get("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE", "0") or "").strip().lower()
    return raw in TRUTHY_ENV_VALUES


def acquire_windows_timer_period_1ms() -> bool:
    """
    Request 1ms Windows timer granularity.

    Scoped by reference counting so multiple users can coexist safely.
    """
    if os.name != "nt":
        return False
    global _WIN_TIMER_USERS, _WIN_TIMER_ACTIVE
    with _WIN_TIMER_LOCK:
        _WIN_TIMER_USERS += 1
        if _WIN_TIMER_ACTIVE:
            return True
        try:
            import ctypes

            mmres = int(ctypes.windll.winmm.timeBeginPeriod(1))
            if mmres == 0:
                _WIN_TIMER_ACTIVE = True
                return True
        except Exception:
            pass
        _WIN_TIMER_USERS = max(0, int(_WIN_TIMER_USERS) - 1)
        return False


def release_windows_timer_period_1ms() -> None:
    if os.name != "nt":
        return
    global _WIN_TIMER_USERS, _WIN_TIMER_ACTIVE
    with _WIN_TIMER_LOCK:
        if _WIN_TIMER_USERS <= 0:
            return
        _WIN_TIMER_USERS -= 1
        if _WIN_TIMER_USERS > 0:
            return
        if not _WIN_TIMER_ACTIVE:
            return
        try:
            import ctypes

            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass
        _WIN_TIMER_ACTIVE = False


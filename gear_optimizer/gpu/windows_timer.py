from __future__ import annotations

import os
import threading


_WIN_TIMER_LOCK = threading.Lock()
_WIN_TIMER_USERS = 0
_WIN_TIMER_ACTIVE = False


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
        import ctypes

        mmres = int(ctypes.windll.winmm.timeBeginPeriod(1))
        if mmres == 0:
            _WIN_TIMER_ACTIVE = True
            return True
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
        import ctypes

        ctypes.windll.winmm.timeEndPeriod(1)
        _WIN_TIMER_ACTIVE = False

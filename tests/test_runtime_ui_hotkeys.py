from __future__ import annotations

import sys
import threading
import time

from gear_optimizer.ui.runtime_ui import RuntimeUiMixin


class _FakeMsvcrt:
    def __init__(self) -> None:
        self._read = False

    def kbhit(self) -> bool:
        return not self._read

    def getwch(self) -> str:
        self._read = True
        return "q"


class _HotkeyHarness(RuntimeUiMixin):
    def __init__(self) -> None:
        self._tui_progress = None
        self._hotkeys_enabled = True
        self._hotkey_thread: threading.Thread | None = None
        self.stop_calls: list[tuple[str, bool]] = []
        self._stop_requested = threading.Event()

    def _stop_requested_now(self) -> bool:
        return bool(self._stop_requested.is_set())

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        self.stop_calls.append((str(reason), bool(force)))
        self._stop_requested.set()


def test_runtime_ui_hotkey_q_requests_graceful_stop(monkeypatch) -> None:
    harness = _HotkeyHarness()
    monkeypatch.setitem(sys.modules, "msvcrt", _FakeMsvcrt())

    harness._start_hotkeys()
    deadline = time.perf_counter() + 1.0
    while not harness.stop_calls and time.perf_counter() < deadline:
        time.sleep(0.01)

    assert harness.stop_calls == [("hotkey stop", False)]
    if isinstance(harness._hotkey_thread, threading.Thread):
        harness._hotkey_thread.join(timeout=1.0)

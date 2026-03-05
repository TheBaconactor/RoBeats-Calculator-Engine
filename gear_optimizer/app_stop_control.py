from __future__ import annotations

import os
import signal
import threading
import time


class StopController:
    """
    Centralized stop/shutdown control for long-running optimizer runs.

    Responsibilities:
    - Handle Ctrl+C / signals (graceful stop vs forced stop)
    - Handle stop file (`bin/STOP` by default) and stop-after timer
    - Provide events that the main loop can poll cheaply
    """

    def __init__(self, *, bin_dir: str):
        self._bin_dir = str(bin_dir)
        self._run_start_monotonic = time.monotonic()
        self.stop_requested_event = threading.Event()
        self.force_exit_requested_event = threading.Event()
        self._signal_handlers_installed = False
        self._signal_prev_handlers: dict[int, object] = {}
        self._stop_after_raw = ""
        self._stop_after_sec = 0.0
        self._stop_after_deadline_monotonic: float | None = None
        self._stop_file_env_raw = ""
        self._stop_file_cached_path = os.path.join(self._bin_dir, "STOP")
        self._stop_file_poll_raw = ""
        self._stop_file_poll_sec = 0.1
        self._stop_file_next_check_monotonic = 0.0
        self._stop_file_present_cache = False
        self._settings_refresh_sec = 1.0
        self._next_settings_refresh_monotonic = 0.0
        self._refresh_runtime_settings(force=True)

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        """
        Request a graceful stop (finish current work, flush DB, then exit).

        - First request sets a stop flag checked between songs / futures.
        - Second request (force=True) escalates to KeyboardInterrupt.
        """
        if force:
            self.force_exit_requested_event.set()

        if not self.stop_requested_event.is_set():
            self.stop_requested_event.set()
            msg = (
                f"[Shutdown] Stop requested ({reason}). Finishing current work then exiting. "
                "Press Ctrl+C again to force."
            )
            try:
                print(msg, flush=True)
            except Exception:
                pass

        if force:
            raise KeyboardInterrupt

    def _stop_file_path(self) -> str:
        return str(self._stop_file_cached_path)

    def _refresh_runtime_settings(self, *, force: bool = False) -> None:
        stop_after_raw = str(os.environ.get("METAFINDER_STOP_AFTER_SEC", "0") or "0").strip()
        if force or stop_after_raw != self._stop_after_raw:
            self._stop_after_raw = stop_after_raw
            try:
                stop_after_sec = float(stop_after_raw or "0")
            except Exception:
                stop_after_sec = 0.0
            self._stop_after_sec = max(0.0, float(stop_after_sec))
            if self._stop_after_sec > 0.0:
                self._stop_after_deadline_monotonic = float(self._run_start_monotonic) + float(self._stop_after_sec)
            else:
                self._stop_after_deadline_monotonic = None

        stop_file_raw = str(os.environ.get("METAFINDER_STOP_FILE", "") or "").strip()
        if force or stop_file_raw != self._stop_file_env_raw:
            self._stop_file_env_raw = stop_file_raw
            self._stop_file_cached_path = stop_file_raw or os.path.join(self._bin_dir, "STOP")
            self._stop_file_next_check_monotonic = 0.0
            self._stop_file_present_cache = False

        stop_file_poll_raw = str(os.environ.get("METAFINDER_STOP_FILE_POLL_SEC", "0.1") or "0.1").strip()
        if force or stop_file_poll_raw != self._stop_file_poll_raw:
            self._stop_file_poll_raw = stop_file_poll_raw
            try:
                stop_file_poll_sec = float(stop_file_poll_raw or "0.1")
            except Exception:
                stop_file_poll_sec = 0.1
            self._stop_file_poll_sec = max(0.01, float(stop_file_poll_sec))

    def stop_requested_now(self) -> bool:
        if self.stop_requested_event.is_set():
            return True
        now = time.monotonic()
        if now >= float(self._next_settings_refresh_monotonic):
            self._refresh_runtime_settings()
            self._next_settings_refresh_monotonic = now + float(self._settings_refresh_sec)
        try:
            if self._stop_after_deadline_monotonic is not None and now >= float(self._stop_after_deadline_monotonic):
                self.request_stop(f"stop-after timer reached: {self._stop_after_sec:.0f}s")
                return True
        except Exception:
            pass
        try:
            if now >= float(self._stop_file_next_check_monotonic):
                stop_file = self._stop_file_path()
                self._stop_file_present_cache = bool(stop_file and os.path.exists(stop_file))
                self._stop_file_next_check_monotonic = now + float(self._stop_file_poll_sec)
            if self._stop_file_present_cache:
                self.request_stop(f"stop file detected: {self._stop_file_path()!r}")
                return True
        except Exception:
            pass
        return self.stop_requested_event.is_set()

    def install_signal_handlers(self) -> None:
        if self._signal_handlers_installed:
            return
        if threading.current_thread() is not threading.main_thread():
            return

        def _handler(signum, _frame):
            # First signal -> graceful stop, second -> force exit.
            if self.stop_requested_event.is_set():
                self.request_stop(f"signal {signum}", force=True)
            else:
                self.request_stop(f"signal {signum}", force=False)

        for sig in (
            getattr(signal, "SIGINT", None),
            getattr(signal, "SIGTERM", None),
            getattr(signal, "SIGBREAK", None),
        ):
            if sig is None:
                continue
            try:
                self._signal_prev_handlers[int(sig)] = signal.getsignal(sig)
                signal.signal(sig, _handler)
            except Exception:
                pass

        self._signal_handlers_installed = True

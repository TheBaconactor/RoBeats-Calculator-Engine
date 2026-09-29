from __future__ import annotations

import os
import signal
import threading
import time

# Creating <bin>/STOP asks a running optimizer to finish its current work and exit.
STOP_FILE_POLL_SEC = 1.0


class StopController:
    """
    Centralized stop/shutdown control for long-running optimizer runs.

    Responsibilities:
    - Handle Ctrl+C / signals (graceful stop vs forced stop)
    - Handle the stop file (`bin/STOP`)
    - Provide events that the main loop can poll cheaply
    """

    def __init__(self, *, bin_dir: str):
        self._bin_dir = str(bin_dir)
        self._run_start_monotonic = time.monotonic()
        self.stop_requested_event = threading.Event()
        self.force_exit_requested_event = threading.Event()
        self._signal_handlers_installed = False
        self._stop_file = os.path.join(self._bin_dir, "STOP")
        self._stop_file_next_check_monotonic = 0.0
        self._stop_file_present_cache = False

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
            print(msg, flush=True)

        if force:
            raise KeyboardInterrupt

    def stop_requested_now(self) -> bool:
        if self.stop_requested_event.is_set():
            return True
        now = time.monotonic()
        if now >= float(self._stop_file_next_check_monotonic):
            self._stop_file_present_cache = os.path.exists(self._stop_file)
            self._stop_file_next_check_monotonic = now + STOP_FILE_POLL_SEC
        if self._stop_file_present_cache:
            self.request_stop(f"stop file detected: {self._stop_file!r}")
            return True
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
            signal.signal(sig, _handler)

        self._signal_handlers_installed = True

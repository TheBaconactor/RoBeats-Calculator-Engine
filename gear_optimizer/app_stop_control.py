from __future__ import annotations

import os
import signal
import threading
import time
from typing import Any


class StopController:
    """
    Centralized stop/shutdown control for long-running optimizer runs.

    Responsibilities:
    - Handle Ctrl+C / signals (graceful stop vs forced stop)
    - Handle stop file (`bin/STOP` by default) and stop-after timer
    - Provide events that the main loop can poll cheaply
    """

    def __init__(self, *, discord_reporter: Any | None, bin_dir: str):
        self._discord_reporter = discord_reporter
        self._bin_dir = str(bin_dir)
        self._run_start_monotonic = time.monotonic()
        self.stop_requested_event = threading.Event()
        self.force_exit_requested_event = threading.Event()
        self._signal_handlers_installed = False
        self._signal_prev_handlers: dict[int, object] = {}

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
            try:
                if self._discord_reporter is not None:
                    self._discord_reporter.send_log(msg)
            except Exception:
                pass

        if force:
            raise KeyboardInterrupt

    def _stop_file_path(self) -> str:
        p = str(os.environ.get("METAFINDER_STOP_FILE", "") or "").strip()
        if p:
            return p
        return os.path.join(self._bin_dir, "STOP")

    def stop_requested_now(self) -> bool:
        if self.stop_requested_event.is_set():
            return True
        try:
            stop_after = float(os.environ.get("METAFINDER_STOP_AFTER_SEC", "0") or "0")
            if stop_after > 0.0 and (time.monotonic() - float(self._run_start_monotonic)) >= stop_after:
                self.request_stop(f"stop-after timer reached: {stop_after:.0f}s")
                return True
        except Exception:
            pass
        try:
            stop_file = self._stop_file_path()
            if stop_file and os.path.exists(stop_file):
                self.request_stop(f"stop file detected: {stop_file!r}")
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

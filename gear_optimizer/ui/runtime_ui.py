from __future__ import annotations

import re
import sys
import threading
import time

from gear_optimizer.ui.progress import ProgressUI as _ProgressUI

# A song's stored best that rises by more than this many points is a NEW record.
RECORD_UPDATE_SCORE_EPSILON = 2


class RuntimeUiMixin:
    """The batch app's console: the progress bar, the NEW-record counter, the Windows "q" stop hotkey, the banner."""

    def _start_progress(self, total_tasks: int) -> None:
        self._completed_tasks = 0
        if not self._progress_enabled:
            return
        self._progress = _ProgressUI(
            total_tasks,
            new_records=self._session_new_records,
            stream=self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout,
        )
        self._progress.start()

    def _stop_progress(self) -> None:
        if self._progress is None:
            return
        try:
            self._progress.stop()
        finally:
            self._progress = None

    def _song_stored(self, label: str, before: int, after: int) -> None:
        """A stored song: its board's best rose from `before` to `after`. A NEW record counts once per song and session
        improvement: more than the epsilon above the stored best and above the song's earlier records this session."""
        # A solve's runs share one record: "Song (mode, Run 2/3)" counts as "Song (mode)".
        song_key = re.sub(r",\s*Run\s+\d+\s*/\s*\d+\)\s*$", ")", label)
        if after - before > RECORD_UPDATE_SCORE_EPSILON and after > self._session_new_record_best_by_song.get(song_key, 0):
            self._session_new_record_best_by_song[song_key] = after
            self._session_new_records += 1
            if self._progress is not None:
                self._progress.add_new_record(1)
        self._song_finished(label, "done")

    def _song_failed(self, label: str) -> None:
        self._song_finished(label, "failed")
        if self._progress is not None:
            self._progress.add_failed(1)

    def _song_finished(self, label: str, status: str) -> None:
        self._completed_tasks += 1
        if self._progress is not None:
            self._progress.set_status(label, status)
            self._progress.add_completed(1)

    def _start_hotkeys(self) -> None:
        if self._hotkey_thread is not None and self._hotkey_thread.is_alive():
            return
        try:
            import msvcrt
        except ImportError:
            return  # The "q" stop hotkey reads the Windows console; elsewhere Ctrl+C stops the run.

        def _runner() -> None:
            while True:
                if self._stop_requested_now():
                    return
                if not msvcrt.kbhit():
                    time.sleep(0.05)
                    continue
                if msvcrt.getwch().strip().lower() != "q":
                    continue
                self.request_stop("hotkey stop")
                return

        self._hotkey_thread = threading.Thread(target=_runner, name="Hotkeys", daemon=True)
        self._hotkey_thread.start()

    def _stop_hotkeys(self) -> None:
        self._hotkey_thread = None

    def _print_banner(self) -> None:
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        stream.write("RoBeats Calculator Engine\n")
        stream.flush()

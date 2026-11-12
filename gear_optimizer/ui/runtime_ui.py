from __future__ import annotations

import re
import threading
import time
from typing import TextIO

from gear_optimizer.app_stop_control import StopController
from gear_optimizer.ui.progress import ProgressUI

# A song's stored best that rises by more than this many points is a NEW record.
_RECORD_UPDATE_SCORE_EPSILON = 2


class RunConsole:
    """The batch app's console: the progress bar, the task and NEW-record counters, the Windows "q" stop hotkey."""

    def __init__(self, stop_control: StopController, *, progress: bool) -> None:
        self._stop_control = stop_control
        self._progress_enabled = progress
        self._bar: ProgressUI | None = None
        self._hotkeys: threading.Thread | None = None
        self._best_by_song: dict[str, int] = {}
        self.new_records = 0  # this session's
        self.completed = 0  # tasks finished since the last start()

    def start(self, total_tasks: int, stream: TextIO) -> None:
        """A queue of `total_tasks` begins: the progress bar (when enabled) and the stop hotkey."""
        self.completed = 0
        if self._progress_enabled:
            self._bar = ProgressUI(total_tasks, new_records=self.new_records, stream=stream)
            self._bar.start()
        self._start_hotkeys()

    def stop(self) -> None:
        """The queue ended: the progress bar's last line. The stop hotkey keeps listening for the next queue."""
        if self._bar is not None:
            bar, self._bar = self._bar, None
            bar.stop()

    def song_stored(self, label: str, before: int, after: int) -> None:
        """A stored song: its board's best rose from `before` to `after`. A NEW record counts once per song and session
        improvement: more than the epsilon above the stored best and above the song's earlier records this session."""
        # A solve's runs share one record: "Song (mode, Run 2/3)" counts as "Song (mode)".
        song_key = re.sub(r",\s*Run\s+\d+\s*/\s*\d+\)\s*$", ")", label)
        if after - before > _RECORD_UPDATE_SCORE_EPSILON and after > self._best_by_song.get(song_key, 0):
            self._best_by_song[song_key] = after
            self.new_records += 1
            if self._bar is not None:
                self._bar.add_new_record()
        self._song_finished(label, "done")

    def song_failed(self, label: str) -> None:
        self._song_finished(label, "failed")
        if self._bar is not None:
            self._bar.add_failed()

    def _song_finished(self, label: str, status: str) -> None:
        self.completed += 1
        if self._bar is not None:
            self._bar.song_finished(label, status)

    def _start_hotkeys(self) -> None:
        """One thread per run reads the Windows console; "q" asks the run to stop. Elsewhere Ctrl+C stops it."""
        if self._hotkeys is not None and self._hotkeys.is_alive():
            return
        try:
            import msvcrt
        except ImportError:
            return

        def _runner() -> None:
            while not self._stop_control.stop_requested_now():
                if not msvcrt.kbhit():
                    time.sleep(0.05)
                elif msvcrt.getwch().strip().lower() == "q":
                    self._stop_control.request_stop("hotkey stop")
                    return

        self._hotkeys = threading.Thread(target=_runner, name="Hotkeys", daemon=True)
        self._hotkeys.start()

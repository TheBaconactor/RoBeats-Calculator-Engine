from __future__ import annotations

import sys
import threading
import time

from gear_optimizer.pipeline.progress import RECORD_UPDATE_SCORE_EPSILON
from gear_optimizer.ui.progress import ProgressUI as _ProgressUI


class RuntimeUiMixin:
    """The batch app's console: the progress bar, the NEW-record counter, the Windows "q" stop hotkey, the banner."""

    def _start_progress(self, total_tasks: int, *, completed: int = 0) -> None:
        self._set_runtime_progress_counts(completed=completed, total=total_tasks, failed=0)
        self._runtime_status_name = "queued"
        if not self._progress_enabled:
            return
        self._progress = _ProgressUI(
            total_tasks,
            completed=completed,
            new_records=self._session_new_records,
            stream=self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout,
        )
        self._progress.start()

    def _stop_progress(self) -> None:
        self._runtime_status_name = "idle"
        if self._progress is None:
            return
        try:
            self._progress.stop()
        finally:
            self._progress = None

    def _apply_authoritative_new_record(self, record_info: dict | None) -> bool:
        """Count a NEW record once per song and session improvement: the run beat the stored best by more than the
        epsilon and the song's earlier records this session."""
        if not record_info or not record_info.get("record_update"):
            return False
        song_key = self._normalize_song_label(str(record_info.get("song") or "_").strip())
        best_overall_score = record_info["best_overall_score_run"]
        if (
            not song_key
            or best_overall_score <= 0
            or best_overall_score - record_info["prev_overall_score"] <= RECORD_UPDATE_SCORE_EPSILON
            or best_overall_score <= self._session_new_record_best_by_song.get(song_key, 0)
        ):
            return False
        self._session_new_record_keys.add(song_key)
        self._session_new_record_best_by_song[song_key] = best_overall_score
        self._session_new_records += 1
        if self._progress is not None:
            self._progress.add_new_record(1)
        return True

    def _progress_event(
        self,
        *,
        completed_delta: int = 0,
        failed_delta: int = 0,
        record_info: dict | None = None,
    ) -> None:
        self._apply_authoritative_new_record(record_info)
        self._runtime_completed_count = max(0, self._runtime_completed_count + completed_delta)
        self._runtime_failed_count = max(0, self._runtime_failed_count + failed_delta)
        song_label = str((record_info or {}).get("song") or "").strip()
        status_label = str((record_info or {}).get("status") or "").strip()
        if song_label:
            self._run_current_song_label = song_label
        if not status_label:
            status_label = "failed" if failed_delta else "done" if completed_delta else "running"
        self._runtime_status_name = status_label
        if self._progress is not None:
            label = song_label or self._run_current_song_label
            if label:
                self._progress.set_status(label, status_label)
            if completed_delta:
                self._progress.add_completed(completed_delta)
            if failed_delta:
                self._progress.add_failed(failed_delta)

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

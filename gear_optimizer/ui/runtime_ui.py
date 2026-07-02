from __future__ import annotations

import logging
import sys
import threading
import time

from gear_optimizer.helpers.song_helpers.persistence_records import RECORD_UPDATE_SCORE_EPSILON
from gear_optimizer.ui.progress import ProgressUI as _ProgressUI

logger = logging.getLogger(__name__)


class RuntimeUiMixin:
    def _start_progress(self, total_tasks: int, *, completed: int = 0) -> None:
        self._set_runtime_progress_counts(completed=int(completed or 0), total=int(total_tasks or 0), failed=0)
        self._runtime_status_name = "queued"
        if not self._progress_enabled:
            return
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        self._progress = _ProgressUI(
            total_tasks,
            completed=completed,
            new_records=self._session_new_records,
            enabled=True,
            bar_width=self._progress_bar_width,
            update_interval=self._progress_interval,
            stream=stream,
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

    def _record_info_song_key(self, record_info: dict | None) -> str:
        if not isinstance(record_info, dict):
            return ""
        raw_song = (
            record_info.get("song")
            or record_info.get("_song_name")
            or record_info.get("_queue_label")
            or "_"
        )
        return self._normalize_song_label(str(raw_song or "").strip())

    def _is_authoritative_new_record(self, record_info: dict | None) -> tuple[bool, str, int]:
        if not isinstance(record_info, dict) or not bool(record_info.get("record_update")):
            return False, "", 0
        song_key = self._record_info_song_key(record_info)
        if not song_key:
            return False, "", 0
        try:
            best_overall_score = int(record_info.get("best_overall_score_run", 0) or 0)
            prev_overall_score = int(record_info.get("prev_overall_score", 0) or 0)
        except Exception as e:
            logger.debug(f"runtime_ui:_is_authoritative_new_record: {e}")
            return False, "", 0
        if best_overall_score <= 0:
            return False, "", 0
        if int(best_overall_score - prev_overall_score) <= int(RECORD_UPDATE_SCORE_EPSILON):
            return False, "", 0
        return True, song_key, int(best_overall_score)

    def _apply_authoritative_new_record(self, record_info: dict | None) -> bool:
        is_authoritative, song_key, best_overall_score = self._is_authoritative_new_record(record_info)
        if not is_authoritative:
            return False
        seen_keys = getattr(self, "_session_new_record_keys", None)
        if not isinstance(seen_keys, set):
            seen_keys = set()
            self._session_new_record_keys = seen_keys
        best_by_song = getattr(self, "_session_new_record_best_by_song", None)
        if not isinstance(best_by_song, dict):
            best_by_song = {}
            self._session_new_record_best_by_song = best_by_song
        previous_session_best = int(best_by_song.get(song_key, 0) or 0)
        if int(best_overall_score or 0) <= previous_session_best:
            return False
        seen_keys.add(song_key)
        best_by_song[song_key] = int(best_overall_score)
        self._session_new_records = int(self._session_new_records) + 1
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
        if completed_delta:
            self._runtime_completed_count = max(
                0,
                int(self._runtime_completed_count or 0) + int(completed_delta or 0),
            )
        if failed_delta:
            self._runtime_failed_count = max(
                0,
                int(self._runtime_failed_count or 0) + int(failed_delta or 0),
            )
        song_label = ""
        status_label = ""
        if isinstance(record_info, dict):
            song_label = str(
                record_info.get("song") or record_info.get("_song_name") or record_info.get("_queue_label") or ""
            ).strip()
            status_label = str(record_info.get("status") or "").strip()
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
                self._progress.add_completed(int(completed_delta))
            if failed_delta:
                self._progress.add_failed(int(failed_delta))

    def _start_hotkeys(self) -> None:
        if not bool(getattr(self, "_hotkeys_enabled", True)):
            return
        existing = getattr(self, "_hotkey_thread", None)
        if isinstance(existing, threading.Thread) and existing.is_alive():
            return
        try:
            import msvcrt
        except Exception as e:
            logger.debug(f"runtime_ui:_start_hotkeys: {e}")
            return

        def _runner() -> None:
            while True:
                if self._stop_requested_now():
                    return
                try:
                    if not msvcrt.kbhit():
                        time.sleep(0.05)
                        continue
                    ch = msvcrt.getwch()
                except Exception as e:
                    logger.debug(f"runtime_ui:_start_hotkeys_runner: {e}")
                    time.sleep(0.05)
                    continue
                if str(ch or "").strip().lower() != "q":
                    continue
                try:
                    self.request_stop("hotkey stop")
                except Exception as e:
                    logger.debug(f"runtime_ui:_start_hotkeys_runner: {e}")
                return

        self._hotkey_thread = threading.Thread(target=_runner, name="Hotkeys", daemon=True)
        self._hotkey_thread.start()

    def _stop_hotkeys(self) -> None:
        self._hotkey_thread = None

    def _print_banner(self) -> None:
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        try:
            stream.write("RoBeats MetaFinder\n")
            stream.flush()
        except Exception as e:
            logger.debug(f"runtime_ui:_print_banner: {e}")

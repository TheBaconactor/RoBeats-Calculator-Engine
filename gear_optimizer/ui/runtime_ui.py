from __future__ import annotations

import logging
import multiprocessing
import os
import queue
import sys
import threading
import time

from gear_optimizer.core.config import load_config
from gear_optimizer.core.team_buff import resolve_selected_team_buff_from_cfg
from gear_optimizer.data.database import get_best_loadouts, get_song_counters
from gear_optimizer.domain.jobs import task_difficulty
from gear_optimizer.helpers.song_helpers.persistence import (
    RECORD_UPDATE_SCORE_EPSILON,
)
from gear_optimizer.ui.progress import (
    ProgressUI as _ProgressUI,
)

logger = logging.getLogger(__name__)

class RuntimeUiMixin:
    def _start_progress(self, total_tasks: int, *, completed: int = 0) -> None:
            self._set_runtime_progress_counts(completed=int(completed or 0), total=int(total_tasks or 0), failed=0)
            self._runtime_status_name = "queued"
            self._update_robeatsmeta_runtime_status(
                status="queued",
                current_song="",
                completed=int(completed or 0),
                total=int(total_tasks or 0),
                failed=0,
            )
            if not self._progress_enabled:
                return
            if self._tui_enabled:
                self._start_tui(total_tasks=total_tasks, completed=completed)
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
            self._clear_robeatsmeta_runtime_status(status="idle", available=True)
            self._stop_tui()
            if self._progress is None:
                return
            try:
                self._progress.stop()
            finally:
                self._progress = None

    def _tui_active(self) -> bool:
            proc = getattr(self, "_tui_process", None)
            if proc is None:
                return False
            try:
                return bool(proc.is_alive())
            except Exception as e:
                logger.debug(f"runtime_ui:_tui_active: {e}")
                return True

    def _start_tui(self, *, total_tasks: int, completed: int = 0) -> None:
            if self._tui_active():
                # New run/iteration: bump epoch so the UI resets its elapsed/ETA.
                try:
                    self._tui_epoch = int(self._tui_epoch) + 1
                except Exception as e:
                    logger.debug(f"runtime_ui:_start_tui: {e}")
                    self._tui_epoch = 1
                self._tui_publish(song="", status=str(self._runtime_status_name or "queued"))
                return

            try:
                from gear_optimizer.ui.progress_ipc import SharedProgress
                from gear_optimizer.ui.tui_process import run_tui_process

                ctx = multiprocessing.get_context("spawn") if os.name == "nt" else multiprocessing.get_context()
                self._tui_epoch = int(self._tui_epoch) + 1
                self._tui_progress = SharedProgress.create()
                self._tui_stop_event = ctx.Event()
                self._tui_cmd_queue = ctx.Queue(maxsize=64)
                self._tui_resp_queue = ctx.Queue(maxsize=64)
                self._tui_process = ctx.Process(
                    target=run_tui_process,
                    kwargs={
                        "progress_shm_name": str(self._tui_progress.name),
                        "stop_event": self._tui_stop_event,
                        "cmd_queue": self._tui_cmd_queue,
                        "resp_queue": self._tui_resp_queue,
                        "bar_width": int(self._progress_bar_width),
                        "update_interval": float(self._progress_interval),
                    },
                    name="MetaFinderTUI",
                    daemon=True,
                )
                self._tui_process.start()
                self._disable_console_logging_for_tui()
            except Exception as e:
                # Best-effort: if we can't start UI, keep compute safe by disabling progress (no fallback to in-proc prints).
                logger.debug(f"runtime_ui:_start_tui: {e}")
                self._tui_enabled = False
                self._progress_enabled = False
                try:
                    if self._tui_progress is not None:
                        self._tui_progress.close()
                        self._tui_progress.unlink()
                except Exception as e:
                    logger.debug(f"runtime_ui:_start_tui: {e}")
                self._tui_progress = None
                self._tui_process = None
                self._tui_stop_event = None
                self._tui_cmd_queue = None
                self._tui_resp_queue = None
                return

            self._tui_publish(
                song="",
                status=str(self._runtime_status_name or "queued"),
                completed=int(completed or 0),
                total=int(total_tasks or 0),
                failed=0,
            )

    def _disable_console_logging_for_tui(self) -> None:
            if self._output_enabled:
                return
            root = logging.getLogger()
            try:
                stderr = sys.stderr
            except Exception as e:
                logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                stderr = None
            try:
                real_stderr = getattr(sys, "__stderr__", None)
            except Exception as e:
                logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                real_stderr = None

            for handler in list(getattr(root, "handlers", []) or []):
                stream = getattr(handler, "stream", None)
                if stream is None:
                    continue
                if stderr is not None and stream is stderr:
                    try:
                        root.removeHandler(handler)
                    except Exception as e:
                        logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                    try:
                        handler.close()
                    except Exception as e:
                        logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                    continue
                if real_stderr is not None and stream is real_stderr:
                    try:
                        root.removeHandler(handler)
                    except Exception as e:
                        logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                    try:
                        handler.close()
                    except Exception as e:
                        logger.debug(f"runtime_ui:_disable_console_logging_for_tui: {e}")
                    continue

    def _stop_tui(self) -> None:
            proc = getattr(self, "_tui_process", None)
            if proc is None:
                return
            try:
                if self._tui_stop_event is not None:
                    self._tui_stop_event.set()
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            try:
                proc.join(timeout=2.0)
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            try:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=2.0)
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            self._tui_process = None
            self._tui_stop_event = None
            self._stop_tui_command_thread()
            try:
                if self._tui_cmd_queue is not None:
                    self._tui_cmd_queue.close()
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            try:
                if self._tui_resp_queue is not None:
                    self._tui_resp_queue.close()
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            self._tui_cmd_queue = None
            self._tui_resp_queue = None
            try:
                if self._tui_progress is not None:
                    self._tui_progress.close()
                    self._tui_progress.unlink()
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui: {e}")
            self._tui_progress = None

    def _tui_publish(
            self,
            *,
            song: str | None,
            status: str | None,
            completed: int | None = None,
            total: int | None = None,
            failed: int | None = None,
            new_records: int | None = None,
        ) -> None:
            progress = getattr(self, "_tui_progress", None)
            if progress is None:
                return
            try:
                c = int(self._runtime_completed_count or 0) if completed is None else int(completed or 0)
                t = int(self._runtime_total_count or 0) if total is None else int(total or 0)
                f = int(self._runtime_failed_count or 0) if failed is None else int(failed or 0)
                n = int(self._session_new_records or 0) if new_records is None else int(new_records or 0)
            except Exception as e:
                logger.debug(f"runtime_ui:_tui_publish: {e}")
                c = int(completed or 0)
                t = int(total or 0)
                f = int(failed or 0)
                n = int(new_records or 0)
            try:
                progress.update(
                    epoch=int(self._tui_epoch),
                    completed=max(0, int(c)),
                    total=max(0, int(t)),
                    failed=max(0, int(f)),
                    new_records=max(0, int(n)),
                    song=str(song or ""),
                    status=str(status or ""),
                )
            except Exception as e:
                logger.debug(f"runtime_ui:_tui_publish: {e}")
                return

    def _record_info_song_key(self, record_info: dict | None) -> str:
            if not isinstance(record_info, dict):
                return ""
            raw_song = (
                record_info.get("song")
                or record_info.get("_song_name")
                or record_info.get("_queue_label")
                or record_info.get("_queue_key")
                or ""
            )
            return self._normalize_song_label(str(raw_song or "").strip())

    def _is_authoritative_new_record(self, record_info: dict | None) -> tuple[bool, str, int]:
            if not isinstance(record_info, dict):
                return False, "", 0
            if not bool(record_info.get("record_update")):
                return False, "", 0

            song_key = self._record_info_song_key(record_info)
            if not song_key:
                return False, "", 0

            try:
                best_overall_score = int(record_info.get("best_overall_score_run", 0) or 0)
            except Exception as e:
                logger.debug(f"runtime_ui:_is_authoritative_new_record: {e}")
                best_overall_score = 0
            try:
                prev_overall_score = int(record_info.get("prev_overall_score", 0) or 0)
            except Exception as e:
                logger.debug(f"runtime_ui:_is_authoritative_new_record: {e}")
                prev_overall_score = 0

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
            try:
                previous_session_best = int(best_by_song.get(song_key, 0) or 0)
            except Exception as e:
                logger.debug(f"runtime_ui:_apply_authoritative_new_record: {e}")
                previous_session_best = 0
            if int(best_overall_score or 0) <= int(previous_session_best or 0):
                return False

            seen_keys.add(song_key)
            best_by_song[song_key] = int(best_overall_score)
            try:
                self._session_new_records = int(self._session_new_records) + 1
            except Exception as e:
                logger.debug(f"runtime_ui:_apply_authoritative_new_record: {e}")
                self._session_new_records = 1
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
            song_label = ""
            status_label = ""
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
            if isinstance(record_info, dict):
                try:
                    song_label = str(
                        record_info.get("song") or record_info.get("_song_name") or record_info.get("_queue_label") or ""
                    ).strip()
                    status_label = str(record_info.get("status") or "").strip()
                    if song_label:
                        self._run_current_song_label = str(song_label)
                        if not status_label:
                            status_label = "running"
                except Exception as e:
                    logger.debug(f"runtime_ui:_progress_event: {e}")
            if not status_label:
                if failed_delta:
                    status_label = "failed"
                elif completed_delta:
                    status_label = "done"
                elif self._run_current_song_label:
                    status_label = str(self._runtime_status_name or "running")
                else:
                    status_label = "running"
            self._runtime_status_name = str(status_label or self._runtime_status_name or "running")
            status_lower = str(self._runtime_status_name or "").strip().lower()
            if song_label:
                try:
                    if status_lower.startswith("running"):
                        self._mark_robeatsmeta_song_started(str(song_label))
                except Exception as e:
                    logger.debug(f"runtime_ui:_progress_event: {e}")
            if self._progress is not None:
                try:
                    if song_label:
                        self._progress.set_status(str(song_label), str(status_label))
                    elif self._run_current_song_label:
                        self._progress.set_status(str(self._run_current_song_label), str(status_label))
                except Exception as e:
                    logger.debug(f"runtime_ui:_progress_event: {e}")
                if completed_delta:
                    self._progress.add_completed(int(completed_delta))
                if failed_delta:
                    self._progress.add_failed(int(failed_delta))
            else:
                try:
                    current_song = str(song_label or self._run_current_song_label or "").strip()
                except Exception as e:
                    logger.debug(f"runtime_ui:_progress_event: {e}")
                    current_song = ""
                self._tui_publish(song=current_song, status=str(status_label or self._runtime_status_name or ""))
            self._update_robeatsmeta_runtime_status(
                status=self._runtime_status_name,
                current_song=str(song_label or self._run_current_song_label or ""),
                completed=int(self._runtime_completed_count or 0),
                total=int(self._runtime_total_count or 0),
                failed=int(self._runtime_failed_count or 0),
            )

    def _handle_status_message(self, msg: str) -> None:
            if not msg:
                return
            song = None
            status = str(msg)
            if status.startswith("[") and "]" in status:
                try:
                    end = status.index("]")
                    song = status[1:end]
                    status = status[end + 1 :].strip()
                except Exception as e:
                    logger.debug(f"runtime_ui:_handle_status_message: {e}")
                    song = None
            if not self._progress_counts_driven and status.upper().startswith("DONE"):
                self._runtime_completed_count = max(0, int(self._runtime_completed_count or 0) + 1)
                if self._progress is not None:
                    self._progress.add_completed(1)
                else:
                    self._tui_publish(song=str(song or self._run_current_song_label or ""), status=str(status or ""))
            if song:
                self._run_current_song_label = str(song)
                if status.strip().lower().startswith("running"):
                    self._mark_robeatsmeta_song_started(str(song))
            self._runtime_status_name = str(status or self._runtime_status_name or "running")
            if self._progress is not None:
                self._progress.set_status(song, status)
            else:
                self._tui_publish(song=str(song or self._run_current_song_label or ""), status=str(status or ""))
            self._update_robeatsmeta_runtime_status(
                status=self._runtime_status_name,
                current_song=str(song or self._run_current_song_label or ""),
                completed=int(self._runtime_completed_count or 0),
                total=int(self._runtime_total_count or 0),
                failed=int(self._runtime_failed_count or 0),
            )
            if self._progress is not None or self._tui_progress is not None:
                return
            try:
                logger.info(str(msg))
            except (ValueError, OSError):
                pass

    def _start_hotkeys(self) -> None:
            if self._tui_progress is not None:
                self._start_tui_command_thread()
                return

            if not self._hotkeys_enabled or self._hotkey_thread is not None:
                return
            # Windows-only hotkeys (best-effort; no-op on other platforms).
            try:
                import msvcrt  # noqa: F401
            except Exception as e:
                logger.debug(f"runtime_ui:_start_hotkeys: {e}")
                return

            def _runner() -> None:
                import msvcrt

                # Print once (in quiet mode too).
                if self._progress is not None:
                    self._progress.emit_block(
                        [
                            "\x1b[90m[Hotkeys]\x1b[0m n=next 10  d=db best  c=db counters  ?=help  q=stop",
                        ]
                    )
                while True:
                    if self._stop_requested_now():
                        return
                    try:
                        if not msvcrt.kbhit():
                            time.sleep(0.05)
                            continue
                        ch = msvcrt.getwch()
                    except Exception as e:
                        logger.debug(f"runtime_ui:_runner: {e}")
                        time.sleep(0.05)
                        continue
                    if not ch:
                        continue
                    key = str(ch).strip().lower()
                    if key == "q":
                        try:
                            self.request_stop("hotkey stop")
                        except Exception as e:
                            logger.debug(f"runtime_ui:_runner: {e}")
                        return
                    if key in {"?", "h"}:
                        self._hotkey_help()
                    elif key == "n":
                        self._hotkey_next_songs(10)
                    elif key == "d":
                        self._hotkey_db_best()
                    elif key == "c":
                        self._hotkey_db_counters()

            self._hotkey_thread = threading.Thread(target=_runner, name="Hotkeys", daemon=True)
            self._hotkey_thread.start()

    def _stop_hotkeys(self) -> None:
            self._stop_tui_command_thread()
            self._hotkey_thread = None

    def _start_tui_command_thread(self) -> None:
            if self._tui_cmd_queue is None or self._tui_resp_queue is None:
                return
            t = getattr(self, "_tui_cmd_thread", None)
            if isinstance(t, threading.Thread) and t.is_alive():
                return
            self._tui_cmd_stop.clear()

            def _runner() -> None:
                while not self._tui_cmd_stop.is_set():
                    try:
                        cmd = self._tui_cmd_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.debug(f"runtime_ui:_runner: {e}")
                        continue
                    if not isinstance(cmd, dict):
                        continue
                    op = str(cmd.get("cmd") or "").strip().lower()
                    if op == "stop":
                        reason = str(cmd.get("reason") or "ui stop")
                        try:
                            self.request_stop(reason)
                        except Exception as e:
                            logger.debug(f"runtime_ui:_runner: {e}")
                        continue
                    if op == "next":
                        try:
                            n = int(cmd.get("n") or 10)
                        except Exception as e:
                            logger.debug(f"runtime_ui:_runner: {e}")
                            n = 10
                        lines = self._tui_up_next_lines(n)
                        self._tui_emit_block(lines)
                        continue

            self._tui_cmd_thread = threading.Thread(target=_runner, name="TuiCommands", daemon=True)
            self._tui_cmd_thread.start()

    def _stop_tui_command_thread(self) -> None:
            t = getattr(self, "_tui_cmd_thread", None)
            if not isinstance(t, threading.Thread):
                self._tui_cmd_thread = None
                return
            try:
                self._tui_cmd_stop.set()
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui_command_thread: {e}")
            try:
                t.join(timeout=1.0)
            except Exception as e:
                logger.debug(f"runtime_ui:_stop_tui_command_thread: {e}")
            self._tui_cmd_thread = None

    def _tui_emit_block(self, lines: list[str]) -> None:
            q = getattr(self, "_tui_resp_queue", None)
            if q is None:
                return
            try:
                payload = {"lines": list(lines or [])}
            except Exception as e:
                logger.debug(f"runtime_ui:_tui_emit_block: {e}")
                payload = {"lines": []}
            try:
                put_nowait = getattr(q, "put_nowait", None)
                if callable(put_nowait):
                    put_nowait(payload)
                else:
                    q.put(payload, block=False)
            except Exception as e:
                logger.debug(f"runtime_ui:_tui_emit_block: {e}")
                return

    def _tui_up_next_lines(self, n: int) -> list[str]:
            tasks = self._run_tasks_ref
            completed = self._run_completed_ref
            if not isinstance(tasks, list) or not isinstance(completed, set):
                return ["\x1b[91m[Hotkeys]\x1b[0m No active queue."]
            out: list[str] = ["\x1b[96mUp Next\x1b[0m"]
            shown = 0
            for t in tasks:
                label = self._task_queue_label(t)
                if label in completed:
                    continue
                diff = task_difficulty(t)
                out.append(f"  {shown + 1:>2}. \x1b[93m{label}\x1b[0m \x1b[90m[{diff}]\x1b[0m")
                shown += 1
                if shown >= int(n):
                    break
            if shown <= 0:
                out.append("  (none)")
            return out

    def _emit_block(self, lines: list[str]) -> None:
            if self._tui_progress is not None:
                self._tui_emit_block(lines)
                return
            if self._progress is not None:
                self._progress.emit_block(lines)
                return
            stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
            try:
                for line in lines:
                    stream.write(str(line) + "\n")
                stream.flush()
            except Exception as e:
                logger.debug(f"runtime_ui:_emit_block: {e}")

    def _hotkey_help(self) -> None:
            self._emit_block(
                [
                    "\x1b[96mRoBeats MetaFinder Hotkeys\x1b[0m",
                    "  n  show next 10 songs in queue",
                    "  d  show best loadout from DB for current song",
                    "  c  show DB counters/best scores for current song",
                    "  q  request graceful stop",
                ]
            )

    def _hotkey_next_songs(self, n: int) -> None:
            tasks = self._run_tasks_ref
            completed = self._run_completed_ref
            if not isinstance(tasks, list) or not isinstance(completed, set):
                self._emit_block(["\x1b[91m[Hotkeys]\x1b[0m No active queue."])
                return
            out: list[str] = ["\x1b[96mUp Next\x1b[0m"]
            shown = 0
            for t in tasks:
                label = self._task_queue_label(t)
                if label in completed:
                    continue
                diff = task_difficulty(t)
                out.append(f"  {shown + 1:>2}. \x1b[93m{label}\x1b[0m \x1b[90m[{diff}]\x1b[0m")
                shown += 1
                if shown >= int(n):
                    break
            if shown <= 0:
                out.append("  (none)")
            self._emit_block(out)

    def _hotkey_db_counters(self) -> None:
            label = self._normalize_song_label(self._run_current_song_label)
            if not label:
                self._emit_block(["\x1b[91m[DB]\x1b[0m No current song yet."])
                return
            try:
                a, af, bs, bfg = get_song_counters(label)
            except Exception as e:
                self._emit_block([f"\x1b[91m[DB]\x1b[0m Error: {type(e).__name__}: {e}"])
                return
            self._emit_block(
                [
                    f"\x1b[96mDB Counters\x1b[0m \x1b[93m{label}\x1b[0m",
                    f"  attempts_lifetime: {a}",
                    f"  attempts_first:    {af}",
                    f"  best_score:        {bs}",
                    f"  best_fg_score:     {bfg}",
                ]
            )

    def _hotkey_db_best(self) -> None:
            label = self._normalize_song_label(self._run_current_song_label)
            if not label:
                self._emit_block(["\x1b[91m[DB]\x1b[0m No current song yet."])
                return
            try:
                baseline_team_buff = resolve_selected_team_buff_from_cfg(load_config(), default="T5")
                rows = get_best_loadouts(
                    label,
                    limit=3,
                    gears_by_name=None,
                    minis_by_name=None,
                    team_buff=baseline_team_buff,
                )
            except Exception as e:
                self._emit_block([f"\x1b[91m[DB]\x1b[0m Error: {type(e).__name__}: {e}"])
                return
            if not rows:
                self._emit_block([f"\x1b[90m[DB]\x1b[0m No loadouts found for \x1b[93m{label}\x1b[0m"])
                return
            best = rows[0]
            gear = best.get("gear") or []
            minis = best.get("minis") or []
            score = best.get("score", 0)
            fg_score = best.get("fg_score", 0)
            out = [
                f"\x1b[96mDB Best Loadout\x1b[0m \x1b[93m{label}\x1b[0m",
                f"  score:    \x1b[92m{score}\x1b[0m",
                f"  fg_score: \x1b[92m{fg_score}\x1b[0m",
                "  gear:",
            ]
            for g in gear:
                out.append(f"    - {g}")
            out.append("  minis:")
            for m in minis:
                out.append(f"    - {m}")
            self._emit_block(out)

    def _print_banner(self) -> None:
            stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
            import textwrap

            banner = textwrap.dedent(
                """\
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠶⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠲⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡒⠢⠤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠄⠄⠀⠀⠄⠀⠤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡖⢒⣒⡒⡆⠀⠀⠀⠀⠀⠀⣿⠹⡘⣷⣦⣤⣍⣒⠢⡀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠃⡎⠉⠉⠉⠉⠉⠙⢦⢱⠀⠀⠀⣀⡀⠀⠀⠀⠀⠀⢀⣀⠀⠀⠰⣧⢰⠀⢁⢠⠀⠀⠀⠀⠀⠀⠘⣄⠱⡘⣿⣿⣿⣿⡆⢇⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡎⡜⠀⡰⠒⠒⠒⢲⠀⢘⡎⠗⢊⡭⠤⠭⣑⠢⣀⠔⣊⠭⠤⢍⡑⢎⣉⣘⠆⠸⣌⣀⣀⡀⠖⢂⣉⣀⣉⣉⣁⠙⣿⣿⣿⣷⠸⡀⠀⠀⠀
    ⠀⠀⠀⢀⠌⣤⣤⣤⣤⣤⡤⢤⣤⣤⢰⠁⢠⣃⣀⣀⣠⠜⠀⡜⢠⠞⠁⢀⣀⠀⠀⢳⢁⠞⠀⢀⣀⡀⠈⠛⢸⠇⠀⠀⠀⠀⠀⢡⢰⠁⠀⠀⠀⠀⠈⣆⠹⣿⣿⣿⡇⠇⠀⠀⠀
    ⠀⠀⢀⠎⣼⠏⣠⣤⠟⣡⣶⠀⣿⢏⠃⠀⠀⠀⠀⠀⠀⠀⡞⢠⠇⢀⡞⢁⠞⠀⡰⠁⡎⢀⡴⠁⠀⠈⢦⠀⠸⡄⢱⠀⢸⠀⠀⠈⠸⡀⠸⣅⣀⣀⣀⠈⠀⠹⣿⣿⣷⠸⡀⠀⠀
    ⠀⢠⢎⣼⢃⣾⣿⡏⠸⣿⠟⣰⡟⣾⣿⡿⠛⠛⠓⠛⣿⣿⣿⣼⣿⡟⣠⣿⣼⡟⠁⠀⣷⣾⡇⠀⠀⠀⠈⣿⣷⡇⠘⣿⣿⡇⠀⠀⠀⠙⣿⣷⣾⣿⣿⣿⣶⡄⠙⠿⠿⡇⠇⠀⠀
    ⢠⢂⣾⣧⣾⣿⣿⣧⣤⣤⣾⡿⣼⣿⣿⠃⠀⠀⠀⣠⣿⣿⡟⣿⣿⣿⣿⣿⠋⣠⣆⠀⣿⣿⣷⡀⠀⠀⣸⣿⣿⣇⢀⢻⣿⣷⡄⠀⠀⠀⠈⠙⠛⠛⠛⠛⣿⣿⣆⣠⣶⣤⡘⢄⠀
    ⡧⠤⠤⠤⠤⠤⠤⠤⠤⠤⡤⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣁⢹⣿⣿⣿⣷⣾⣿⣿⡧⠹⣿⣿⣿⣶⣾⣿⣿⣿⣿⢸⣎⢿⣿⣿⣿⣿⣷⢻⣿⣿⣿⣿⣿⣿⣿⣿⠿⣿⣿⣿⣆⢣
    ⠸⠦⠤⠤⠤⠤⢤⣾⣶⣶⢃⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⡔⣻⣎⠻⣿⣿⣿⣿⣿⢟⡴⣳⡙⢿⣿⣿⣿⣿⠿⡙⣿⡎⡯⢢⡙⢿⣿⣿⣿⣯⣿⣿⣿⣿⣿⣿⣿⣿⢠⡙⢿⣿⣿⠘
    ⠀⠐⠶⣷⣿⣷⣻⣿⣿⣯⠬⠭⠭⠭⠭⠭⠭⠭⣄⠞⢻⡵⡏⣿⡓⡬⠭⣭⠭⠔⢛⣷⡷⡹⠒⠬⢭⡭⢥⢞⣗⡬⡤⣿⣮⡊⡓⠢⠭⠭⠭⠬⠭⠭⠭⠭⠭⢭⢴⣏⠹⠢⢭⣭⡼
    ⠀⠀⠀⠀⠀⠀⠀⢿⡿⠿⠤⠤⠤⠤⠤⠤⢤⣭⣽⣿⡟⡇⡇⣿⢿⢦⠀⢴⠤⠶⠋⠉⠣⡏⠷⠄⠰⡦⠴⠛⠣⠭⠴⠇⠈⠿⣿⢯⢭⢯⢿⢭⣭⡤⠤⠤⠴⠶⠛⠿⠷⠴⠾⠿⠁
    ⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⡇⡇⡇⣿⠈⠿⠀⠀⠀⠀⠀⠀⠀⠓⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣼⢸⢸⢸⢸⡏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠹⢿⡇⡇⡧⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣸⢸⢸⣸⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢃⡗⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    """
            ).splitlines()
            try:
                for line in banner:
                    stream.write(line + "\n")
                stream.flush()
            except Exception as e:
                logger.debug(f"runtime_ui:_print_banner: {e}")

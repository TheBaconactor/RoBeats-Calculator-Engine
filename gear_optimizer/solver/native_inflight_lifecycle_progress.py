"""Progress tracking and GA queue limit helpers for native in-flight orchestration."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.native_inflight_config import native_song_label

# A run is a NEW record for the progress counter when its best score (base or FG) beats the song's stored best by
# more than this many points.
RECORD_UPDATE_SCORE_EPSILON = 2


def run_record_info(run_score: int, run_fg: int, prev_score: int, prev_fg: int, *, baseline_valid: bool) -> dict:
    """How a run's best base and FG scores compare with the song's stored bests. `baseline_valid=False` (the
    stored bests could not be read) never reports a record, so the NEW counter cannot over-count."""
    run_best, prev_best = max(run_score, run_fg), max(prev_score, prev_fg)
    valid = bool(baseline_valid)
    return {
        "record_update": valid and run_best - prev_best > RECORD_UPDATE_SCORE_EPSILON,
        "is_better": valid and run_score - prev_score > RECORD_UPDATE_SCORE_EPSILON,
        "is_fg_better": valid and run_fg - prev_fg > RECORD_UPDATE_SCORE_EPSILON,
        "score": int(run_score),
        "best_fg_score_run": int(run_fg),
        "best_overall_score_run": int(run_best),
        "prev_overall_score": int(prev_best),
    }


@dataclass
class ProgressTracker:
    lock: threading.Lock = field(default_factory=threading.Lock)
    best: dict[str, tuple[int, int]] = field(default_factory=dict)
    valid: set[str] = field(default_factory=set)
    failed_progress_keys: set[str] = field(default_factory=set)

    def snapshot(self, db_key: str) -> tuple[int, int, bool]:
        key = str(db_key or "").strip()
        if not key:
            return (0, 0, False)
        with self.lock:
            score0, fg0 = self.best.get(key, (0, 0))
            return (int(score0), int(fg0), key in self.valid)

    def update(
        self,
        db_key: str,
        *,
        best_score: int | None = None,
        best_fg: int | None = None,
        mark_valid: bool = False,
    ) -> None:
        key = str(db_key or "").strip()
        if not key:
            return
        try:
            score_new = int(best_score) if best_score is not None else None
        except (TypeError, ValueError):
            score_new = None
        try:
            fg_new = int(best_fg) if best_fg is not None else None
        except (TypeError, ValueError):
            fg_new = None
        with self.lock:
            score0, fg0 = self.best.get(key, (0, 0))
            if score_new is not None and score_new > int(score0):
                score0 = int(score_new)
            if fg_new is not None and fg_new > int(fg0):
                fg0 = int(fg_new)
            self.best[key] = (int(score0), int(fg0))
            if mark_valid:
                self.valid.add(key)

    def seed_valid_baseline(self, db_key: str, *, best_score: int, best_fg: int, baseline_valid: bool) -> None:
        if not bool(baseline_valid):
            return
        self.update(
            db_key,
            best_score=int(best_score),
            best_fg=int(best_fg),
            mark_valid=True,
        )

    @staticmethod
    def error_item_song_label(item: dict) -> Any:
        return (
            item.get("song")
            or item.get("_song_name")
            or item.get("song_name")
            or item.get("_queue_label")
            or item.get("_queue_key")
        )

    @staticmethod
    def error_item_progress_key(item: dict) -> str:
        return str(
            item.get("_queue_key")
            or item.get("queue_key")
            or item.get("_queue_label")
            or item.get("song")
            or item.get("_song_name")
            or ""
        ).strip()

    def emit_error_item_progress(self, progress_cb: Callable[..., Any] | None, item: Any) -> bool:
        if not isinstance(item, dict) or not item.get("_error") or bool(item.get("_suppress_progress")):
            return False
        song_label = self.error_item_song_label(item)
        progress_key = self.error_item_progress_key(item)
        if progress_key:
            with self.lock:
                if progress_key in self.failed_progress_keys:
                    return False
                self.failed_progress_keys.add(progress_key)
        self.emit_progress(
            progress_cb,
            completed_delta=1,
            failed_delta=1,
            record_info={"song": song_label, "status": "FAILED"},
        )
        return True

    @staticmethod
    def done_record_info_for_song(song: Any) -> dict | None:
        record_info = dict(song.runtime.db.record_info or {})
        record_info.setdefault("song", native_song_label(song))
        record_info.setdefault("status", "DONE")
        return record_info

    def emit_done_song_progress(
        self,
        progress_cb: Callable[..., Any] | None,
        song: Any,
        *,
        completed_delta: int = 1,
    ) -> None:
        self.emit_progress(
            progress_cb,
            completed_delta=int(completed_delta),
            record_info=self.done_record_info_for_song(song),
        )

    def emit_progress(
        self,
        progress_cb: Callable[..., Any] | None,
        *,
        completed_delta: int = 0,
        failed_delta: int = 0,
        record_info: dict | None = None,
    ) -> None:
        if progress_cb is None:
            return
        progress_cb(
            completed_delta=completed_delta,
            failed_delta=failed_delta,
            record_info=record_info,
        )


class ActiveRuntimeProgressReporter:
    def __init__(self, emit_progress: Callable[..., Any]) -> None:
        self._emit_progress = emit_progress
        self.active_label = ""

    @staticmethod
    def active_song_label(
        *,
        ga_inflight,
        decode_inflight,
        fg_futures,
    ) -> str:
        for source_name, source in (
            ("ga", ga_inflight),
            ("decode", decode_inflight),
        ):
            if source:
                return native_song_label(source[0])
        if fg_futures:
            return native_song_label(fg_futures[0][0])
        return ""

    def emit(
        self,
        *,
        ga_inflight,
        decode_inflight,
        fg_futures,
        force: bool = False,
    ) -> None:
        song_label = self.active_song_label(
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            fg_futures=fg_futures,
        )
        if not force and song_label == self.active_label:
            return
        self.active_label = str(song_label or "").strip()
        if not self.active_label:
            return
        self._emit_progress(
            completed_delta=0,
            failed_delta=0,
            record_info={"song": self.active_label, "status": "RUNNING"},
        )


def evaluate_fg_progress_record_update(song: Any, progress_tracker: ProgressTracker | None) -> dict:
    """The record info of a song whose FG stage finished (its run's best base score and best winning FG score)."""
    key = str(song.config.db_key or "").strip()
    prev_best_score = safe_int(song.runtime.db.db_best_score, 0)
    prev_best_fg = safe_int(song.runtime.db.db_best_fg_score, 0)
    baseline_valid = bool(song.runtime.db.db_baseline_valid)
    if progress_tracker is not None and key:
        prev_best_score, prev_best_fg, baseline_valid = progress_tracker.snapshot(key)
    best_data = song.runtime.decode.best_data or {}
    run_score = safe_int(best_data.get("BaseScore") or best_data.get("Score", 0), 0)
    run_fg = max((fg.score for _loadout, fg in song.runtime.fg.fg_results or () if fg.score > fg.paired), default=0)
    record_info = run_record_info(run_score, run_fg, prev_best_score, prev_best_fg, baseline_valid=baseline_valid)
    record_info["song"] = native_song_label(song)
    if progress_tracker is not None and key and (record_info["is_better"] or record_info["is_fg_better"]):
        progress_tracker.update(
            key,
            best_score=run_score if record_info["is_better"] else None,
            best_fg=run_fg if record_info["is_fg_better"] else None,
            mark_valid=baseline_valid,
        )
    return record_info

"""A run's progress: each finished song's records judged against the run's bests, the progress events, and each
task's completion (the completed set and the resume journal) or error payload."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.pipeline.song import NativeSong, native_song_label

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
        with self.lock:
            score, fg = self.best.get(db_key, (0, 0))
            return score, fg, db_key in self.valid

    def update(
        self,
        db_key: str,
        *,
        best_score: int | None = None,
        best_fg: int | None = None,
        mark_valid: bool = False,
    ) -> None:
        if not db_key:
            return
        with self.lock:
            score, fg = self.best.get(db_key, (0, 0))
            if best_score is not None:
                score = max(score, best_score)
            if best_fg is not None:
                fg = max(fg, best_fg)
            self.best[db_key] = (score, fg)
            if mark_valid:
                self.valid.add(db_key)

    def seed_valid_baseline(self, db_key: str, *, best_score: int, best_fg: int, baseline_valid: bool) -> None:
        if baseline_valid:
            self.update(db_key, best_score=best_score, best_fg=best_fg, mark_valid=True)

    def emit_error_item_progress(self, progress_cb: Callable[..., Any] | None, item: dict) -> bool:
        """Count a failed task's error payload (song_error_payload / task_error_payload) once per queue key."""
        if not item["_error"]:
            return False
        with self.lock:
            if item["_queue_key"] in self.failed_progress_keys:
                return False
            self.failed_progress_keys.add(item["_queue_key"])
        self.emit_progress(
            progress_cb,
            completed_delta=1,
            failed_delta=1,
            record_info={"song": item["song"] or item["_queue_label"], "status": "FAILED"},
        )
        return True

    @staticmethod
    def done_record_info_for_song(song: NativeSong) -> dict:
        record_info = dict(song.runtime.db.record_info or {})
        record_info.setdefault("song", native_song_label(song))
        record_info.setdefault("status", "DONE")
        return record_info

    def emit_done_song_progress(self, progress_cb: Callable[..., Any] | None, song: NativeSong) -> None:
        self.emit_progress(progress_cb, completed_delta=1, record_info=self.done_record_info_for_song(song))

    def emit_progress(
        self,
        progress_cb: Callable[..., Any] | None,
        *,
        completed_delta: int = 0,
        failed_delta: int = 0,
        record_info: dict | None = None,
    ) -> None:
        if progress_cb is not None:
            progress_cb(completed_delta=completed_delta, failed_delta=failed_delta, record_info=record_info)


def evaluate_fg_progress_record_update(song: NativeSong, progress_tracker: ProgressTracker | None) -> dict:
    """The record info of a song whose FG stage finished (its run's best base score and best winning FG score)."""
    key = song.config.db_key
    db = song.runtime.db
    prev_best_score, prev_best_fg, baseline_valid = db.db_best_score, db.db_best_fg_score, db.db_baseline_valid
    if progress_tracker is not None and key:
        prev_best_score, prev_best_fg, baseline_valid = progress_tracker.snapshot(key)
    run_score = song.runtime.decode.best_data["BaseScore"]
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


def mark_song_completed(
    *,
    completed_songs: set[str],
    task_key: str,
    song_name: str,
    song_path: str | None = None,
    memory_resume_tracker=None,
) -> None:
    completed_songs.add(task_key)
    if memory_resume_tracker:
        memory_resume_tracker.mark_completed(song_path=song_path, song_name=song_name)


def song_error_payload(song: NativeSong, *, exc: Exception, trace: str) -> dict[str, Any]:
    key = song.config.task_key
    return build_error_payload(song_name=song.config.song_name, queue_key=key, queue_label=key, exc=exc, trace=trace)


def task_error_payload(*, song_name: str, queue_key: str, exc: Exception, trace: str) -> dict[str, Any]:
    return build_error_payload(song_name=song_name, queue_key=queue_key, queue_label=queue_key, exc=exc, trace=trace)

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable
import logging

from gear_optimizer.helpers.song_helpers.persistence import evaluate_progress_record_update
from gear_optimizer.solver.native_inflight_types import native_song_label


logger = logging.getLogger(__name__)


@dataclass
class ProgressTracker:
    lock: threading.Lock = field(default_factory=threading.Lock)
    best: dict[str, tuple[int, int]] = field(default_factory=dict)
    valid: set[str] = field(default_factory=set)

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

    def evaluate_record_update(
        self,
        db_key: str,
        best_data: dict,
        fg_variants,
        *,
        fg_only: bool = False,
    ) -> dict | None:
        prev_best_score, prev_best_fg, baseline_valid = self.snapshot(db_key)
        record_info = evaluate_progress_record_update(
            best_data or {},
            {"score": int(prev_best_score)},
            fg_variants or [],
            db_best_fg_score=int(prev_best_fg),
            baseline_valid=bool(baseline_valid),
            fg_only=bool(fg_only),
        )
        if isinstance(record_info, dict) and record_info.get("is_better"):
            self.update(
                db_key,
                best_score=int(record_info.get("score", 0) or 0),
                best_fg=int(record_info.get("best_fg_score_run", 0) or 0),
                mark_valid=bool(baseline_valid),
            )
        elif isinstance(record_info, dict) and record_info.get("is_fg_better"):
            self.update(
                db_key,
                best_fg=int(record_info.get("best_fg_score_run", 0) or 0),
                mark_valid=bool(baseline_valid),
            )
        return record_info

    @staticmethod
    def error_item_song_label(item: dict) -> Any:
        return (
            item.get("song")
            or item.get("_song_name")
            or item.get("song_name")
            or item.get("_queue_label")
            or item.get("_queue_key")
        )

    def emit_error_item_progress(self, progress_cb: Callable[..., Any] | None, item: Any) -> bool:
        if not isinstance(item, dict) or not item.get("_error") or bool(item.get("_suppress_progress")):
            return False
        try:
            song_label = self.error_item_song_label(item)
        except Exception as e:
            logger.debug(f"native_inflight_progress:emit_error_item_progress: {e}")
            song_label = None
        self.emit_progress(
            progress_cb,
            completed_delta=1,
            failed_delta=1,
            record_info={"song": song_label, "status": "FAILED"},
        )
        return True

    @staticmethod
    def done_record_info_for_song(song: Any) -> dict | None:
        try:
            record_info = dict(getattr(song.runtime.db, "record_info", None) or {})
            record_info.setdefault("song", native_song_label(song))
            record_info.setdefault("status", "DONE")
            return record_info
        except Exception as e:
            logger.debug(f"native_inflight_progress:done_record_info_for_song: {e}")
            return None

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
        try:
            progress_cb(
                completed_delta=completed_delta,
                failed_delta=failed_delta,
                record_info=record_info,
            )
        except Exception as e:
            logger.debug(f"native_inflight_progress:emit_progress: {e}")
            return


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
            try:
                if source:
                    return native_song_label(source[0])
            except Exception as e:
                logger.debug(f"native_inflight_progress:active_song_label:{source_name}: {e}")
        try:
            if fg_futures:
                return native_song_label(fg_futures[0][0])
        except Exception as e:
            logger.debug(f"native_inflight_progress:active_song_label:fg: {e}")
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

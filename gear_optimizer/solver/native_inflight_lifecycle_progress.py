"""Progress tracking and GA queue limit helpers for native in-flight orchestration."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.persistence import evaluate_progress_record_update
from gear_optimizer.solver.native_inflight_config import native_song_label

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
            logger.debug(f"native_inflight_lifecycle:emit_error_item_progress: {e}")
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
            logger.debug(f"native_inflight_lifecycle:done_record_info_for_song: {e}")
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
            logger.debug(f"native_inflight_lifecycle:emit_progress: {e}")
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
                logger.debug(f"native_inflight_lifecycle:active_song_label:{source_name}: {e}")
        try:
            if fg_futures:
                return native_song_label(fg_futures[0][0])
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:active_song_label:fg: {e}")
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


def evaluate_fg_progress_record_update(song: Any, progress_tracker: ProgressTracker | None) -> dict | None:
    try:
        key = str(getattr(song.config, "db_key", "") or "").strip()
        prev_best_score = safe_int(getattr(song.runtime.db, "db_best_score", 0), 0)
        prev_best_fg = safe_int(getattr(song.runtime.db, "db_best_fg_score", 0), 0)
        baseline_valid = bool(getattr(song.runtime.db, "db_baseline_valid", True))
        if progress_tracker is not None and key:
            prev_best_score, prev_best_fg, baseline_valid = progress_tracker.snapshot(key)
        record_info = evaluate_progress_record_update(
            getattr(song.runtime.decode, "best_data", None) or {},
            {"score": int(prev_best_score)},
            getattr(song.runtime.fg, "fg_variants", None) or [],
            db_best_fg_score=int(prev_best_fg),
            baseline_valid=bool(baseline_valid),
            fg_only=True,
        )
    except (ValueError, TypeError, KeyError):
        return None
    if not isinstance(record_info, dict):
        return None
    record_info = dict(record_info)
    record_info.setdefault("song", native_song_label(song))
    if progress_tracker is not None:
        best_score_new = safe_int(record_info.get("score", 0), 0) if record_info.get("is_better") else None
        best_fg_new = safe_int(record_info.get("best_fg_score_run", 0), 0) if record_info.get("is_fg_better") else None
        if (best_score_new is not None and best_score_new > 0) or (best_fg_new is not None and best_fg_new > 0):
            key = str(getattr(song.config, "db_key", "") or "").strip()
            if key:
                progress_tracker.update(
                    key,
                    best_score=best_score_new,
                    best_fg=best_fg_new,
                    mark_valid=bool(baseline_valid),
                )
    return record_info


@dataclass
class GAQueueLimitController:
    base_limit: int
    pressure_window_s: float
    extra_free_on_slot_pressure: int
    fg_slot_reserve: int
    song_slot_limit: int
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)
    _cache_key: tuple[bool, int, int, int, int] | None = field(default=None, init=False, repr=False)
    _cache_value: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_limit = max(1, int(self.base_limit))
        self.pressure_window_s = max(0.0, float(self.pressure_window_s))
        self.extra_free_on_slot_pressure = max(0, int(self.extra_free_on_slot_pressure))
        self.fg_slot_reserve = max(0, int(self.fg_slot_reserve))
        self.song_slot_limit = max(1, int(self.song_slot_limit))
        self._cache_value = int(self.base_limit)

    def effective_limit(self, *, last_slot_block_t: float | None) -> int:
        extra_free = 0
        slot_pressure_active = False
        if last_slot_block_t is not None and float(self.pressure_window_s) > 0.0:
            try:
                if (float(self.monotonic()) - float(last_slot_block_t)) <= float(self.pressure_window_s):
                    slot_pressure_active = True
                    extra_free = max(int(extra_free), int(self.extra_free_on_slot_pressure))
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:GAQueueLimitController.effective_limit: {e}")
        cache_key = (
            bool(slot_pressure_active),
            int(extra_free),
            int(self.fg_slot_reserve),
            int(self.song_slot_limit),
            int(self.base_limit),
        )
        if cache_key == self._cache_key:
            return int(self._cache_value)
        min_free = int(self.fg_slot_reserve) + int(extra_free)
        min_free = max(0, min(int(min_free), max(0, int(self.song_slot_limit) - 1)))
        limit_from_free = max(1, int(self.song_slot_limit) - int(min_free))
        self._cache_value = max(1, min(int(self.base_limit), int(limit_from_free)))
        self._cache_key = cache_key
        return int(self._cache_value)

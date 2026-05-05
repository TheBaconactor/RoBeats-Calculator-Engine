from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable


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

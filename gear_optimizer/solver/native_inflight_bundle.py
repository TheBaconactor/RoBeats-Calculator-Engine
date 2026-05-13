from __future__ import annotations

import logging
from collections import deque
from typing import Callable

from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    is_repeat_context,
    materialize_repeat_task,
    task_queue_label,
)
from gear_optimizer.solver.native_inflight_types import _NativeSong

logger = logging.getLogger(__name__)


class InflightBundleTracker:
    def __init__(
        self,
        *,
        pending_tasks: deque,
        completed_songs: set[str],
        memory_resume_tracker,
        bundle_completed_cb: Callable[[str, set[str]], object] | None,
        emit_progress: Callable,
    ) -> None:
        self.pending_tasks = pending_tasks
        self.completed_songs = completed_songs
        self.memory_resume_tracker = memory_resume_tracker
        self.bundle_completed_cb = bundle_completed_cb
        self.emit_progress = emit_progress
        self.progress: dict[int, int] = {}

    @staticmethod
    def bundle_runs(task: tuple) -> list[dict]:
        bundle = extract_repeat_bundle(task)
        if not isinstance(bundle, dict):
            return []
        runs = bundle.get("runs")
        if not isinstance(runs, list):
            return []
        out: list[dict] = []
        for ctx in runs:
            if is_repeat_context(ctx):
                out.append(dict(ctx))
        return out

    def next_logical_task(self, task: tuple) -> tuple[tuple, dict | None]:
        runs = self.bundle_runs(task)
        if not runs:
            return task, None
        cursor = max(0, int(self.progress.get(id(task), 0)))
        if cursor >= len(runs):
            cursor = len(runs) - 1
        repeat_ctx = dict(runs[cursor])
        return materialize_repeat_task(task, repeat_ctx), repeat_ctx

    def bind_song(self, song: _NativeSong, parent_task: tuple, repeat_ctx: dict | None) -> None:
        if repeat_ctx is None or not self.bundle_runs(parent_task):
            return
        song.runtime.bundle.bundle_parent_task = parent_task
        song.runtime.bundle.bundle_task_key = task_queue_label(parent_task)
        try:
            song.runtime.bundle.bundle_repeat_index = int(repeat_ctx.get("repeat_index") or 0)
            song.runtime.bundle.bundle_repeat_total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception as e:
            logger.debug(f"native_inflight_bundle:bind_song: {e}")
            song.runtime.bundle.bundle_repeat_index = 0
            song.runtime.bundle.bundle_repeat_total = 0

    def advance(
        self,
        parent_task: tuple,
        *,
        song_name: str,
        record_info: dict | None = None,
        failed: bool = False,
    ) -> bool:
        runs = self.bundle_runs(parent_task)
        if not runs:
            return False
        next_idx = max(0, int(self.progress.get(id(parent_task), 0))) + 1
        self.progress[id(parent_task)] = int(next_idx)

        # Bundled repeats behave like queue inflation to N repeat-runs, but are
        # queued as one parent task to reduce overhead. Emit progress once per
        # repeat-run so UI throughput reflects real work.
        info: dict = {}
        if isinstance(record_info, dict):
            try:
                info = dict(record_info)
            except Exception as e:
                logger.debug(f"native_inflight_bundle:advance: {e}")
                info = {}

        repeat_label = None
        try:
            ctx = runs[int(next_idx) - 1] if int(next_idx) > 0 and int(next_idx) <= len(runs) else None
            if is_repeat_context(ctx):
                ridx = int(ctx.get("repeat_index") or next_idx)
                rtotal = int(ctx.get("repeat_total") or len(runs))
                if ridx > 0 and rtotal > 1:
                    repeat_label = f"{song_name} (Run {ridx}/{rtotal})"
        except Exception as e:
            logger.debug(f"native_inflight_bundle:advance: {e}")
            repeat_label = None

        info.setdefault("song", repeat_label or song_name)
        info.setdefault("status", "FAILED" if failed else "DONE")

        self.emit_progress(
            completed_delta=1,
            failed_delta=1 if failed else 0,
            record_info=info,
        )

        if next_idx < len(runs):
            self.pending_tasks.appendleft(parent_task)
            return True

        bundle_key = task_queue_label(parent_task)
        self.completed_songs.add(bundle_key)
        if self.memory_resume_tracker:
            self.memory_resume_tracker.mark_completed(song_name)
        if self.bundle_completed_cb is not None:
            try:
                self.bundle_completed_cb(bundle_key, self.completed_songs)
            except Exception as e:
                logger.debug(f"native_inflight_bundle:advance: {e}")
        return True

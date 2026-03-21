from __future__ import annotations

import os
import queue
import threading
import time
from collections import OrderedDict
from typing import Any


def _is_repeat_ctx_dict(extra: Any) -> bool:
    return isinstance(extra, dict) and "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra


def _extract_repeat_ctx(task: tuple) -> dict | None:
    if not isinstance(task, (tuple, list)) or len(task) <= 16:
        return None
    for extra in task[16:]:
        if _is_repeat_ctx_dict(extra):
            return extra
    return None


def _extract_repeat_bundle(task: tuple) -> dict | None:
    if not isinstance(task, (tuple, list)) or len(task) <= 16:
        return None
    for extra in task[16:]:
        if not isinstance(extra, dict):
            continue
        if not bool(extra.get("repeat_bundle")):
            continue
        runs = extra.get("runs")
        if isinstance(runs, list) and runs:
            return extra
    return None


def _materialize_repeat_task(task: tuple, repeat_ctx: dict) -> tuple:
    if not isinstance(task, (tuple, list)):
        return task
    prefix = list(task[:16])
    extras: list[Any] = []
    for extra in task[16:]:
        if _is_repeat_ctx_dict(extra):
            continue
        if isinstance(extra, dict) and bool(extra.get("repeat_bundle")):
            continue
        extras.append(extra)
    extras.append(dict(repeat_ctx or {}))
    return tuple(prefix + extras)


def _task_key(task: tuple) -> str:
    if not isinstance(task, (tuple, list)) or len(task) < 2:
        return "Unknown"
    base = str(task[1])
    repeat_ctx = _extract_repeat_ctx(task)
    if repeat_ctx:
        try:
            idx = int(repeat_ctx.get("repeat_index") or 0)
            total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception:
            idx = 0
            total = 0
        if idx > 0 and total > 1:
            return f"{base} (Run {idx}/{total})"
    return base


def _task_ga_seed(task: tuple) -> int | None:
    repeat_ctx = _extract_repeat_ctx(task)
    if not repeat_ctx:
        return None
    try:
        seed = repeat_ctx.get("ga_seed")
        return int(seed) if seed is not None else None
    except Exception:
        return None


def _lru_get(cache: OrderedDict, key: tuple) -> Any:
    try:
        value = cache.get(key)
    except Exception:
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception:
            pass
    return value


def _lru_put(cache: OrderedDict, key: tuple, value: Any, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception:
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception:
        pass


def _loadout_entries_have_db_source(loadout_entries: dict | None) -> bool:
    if not isinstance(loadout_entries, dict) or not loadout_entries:
        return False
    for entry in loadout_entries.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("_source", "") or "").strip().lower() == "db":
            return True
    return False


class _PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        # Default to unbounded backlog to avoid ever blocking the GPU-owner pipeline.
        backlog = 0
        try:
            backlog = int(os.environ.get("POST_LOCAL_BACKLOG", backlog))
        except Exception:
            backlog = 0
        backlog = int(backlog)
        if backlog < 0:
            backlog = 0
        self._q: queue.Queue[Any] = queue.Queue(maxsize=backlog)
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except Exception:
            return
        try:
            self._thread.join(timeout=timeout)
        except Exception:
            pass

    def _run(self) -> None:
        timing = str(os.environ.get("POST_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
        threshold_ms = 50.0
        try:
            threshold_ms = float(os.environ.get("POST_TIMING_THRESHOLD_MS", str(threshold_ms)))
        except Exception:
            threshold_ms = 50.0
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            try:
                t0 = time.perf_counter()
                while True:
                    if self._stop_requested is not None and callable(self._stop_requested) and self._stop_requested():
                        return
                    try:
                        self._post_queue.put(item, block=True, timeout=0.5)
                        break
                    except Exception:
                        continue
                if timing:
                    ms = (time.perf_counter() - t0) * 1000.0
                    if ms >= threshold_ms:
                        kind = None
                        try:
                            kind = item.get("song") if isinstance(item, dict) else None
                        except Exception:
                            kind = None
                        prefix = f"[PostSender][TIMING] {kind} " if kind else "[PostSender][TIMING] "
                        print(f"{prefix}post_queue_put={ms:.1f}ms")
            except Exception:
                pass


from __future__ import annotations

import queue
import threading
import time
from collections import OrderedDict
from typing import Any
import logging

from gear_optimizer.core.parsing import env_flag


from gear_optimizer.core.parsing import env_get
from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    extract_repeat_context,
    is_repeat_context,
    materialize_repeat_task,
    task_ga_seed,
    task_queue_label,
)

logger = logging.getLogger(__name__)
def _is_repeat_ctx_dict(extra: Any) -> bool:
    return is_repeat_context(extra)


def _extract_repeat_ctx(task: tuple) -> dict | None:
    return extract_repeat_context(task)


def _extract_repeat_bundle(task: tuple) -> dict | None:
    return extract_repeat_bundle(task)


def _materialize_repeat_task(task: tuple, repeat_ctx: dict) -> tuple:
    return materialize_repeat_task(task, repeat_ctx)


def _task_key(task: tuple) -> str:
    return task_queue_label(task)


def _task_ga_seed(task: tuple) -> int | None:
    return task_ga_seed(task)


def _lru_get(cache: OrderedDict, key: tuple) -> Any:
    try:
        value = cache.get(key)
    except Exception as e:
        logger.debug(f"native_inflight_support:_lru_get: {e}")
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception as e:
            logger.debug(f"native_inflight_support:_lru_get: {e}")
    return value


def _lru_put(cache: OrderedDict, key: tuple, value: Any, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception as e:
        logger.debug(f"native_inflight_support:_lru_put: {e}")
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception as e:
        logger.debug(f"native_inflight_support:_lru_put: {e}")


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
            backlog = int(env_get("POST_LOCAL_BACKLOG", backlog))
        except Exception as e:
            logger.debug(f"native_inflight_support:__init__: {e}")
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
        except Exception as e:
            logger.debug(f"native_inflight_support:close: {e}")
            return
        try:
            self._thread.join(timeout=timeout)
        except Exception as e:
            logger.debug(f"native_inflight_support:close: {e}")

    def _run(self) -> None:
        timing = env_flag("POST_TIMING")
        threshold_ms = 50.0
        try:
            threshold_ms = float(env_get("POST_TIMING_THRESHOLD_MS", str(threshold_ms)))
        except Exception as e:
            logger.debug(f"native_inflight_support:_run: {e}")
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
                    except Exception as e:
                        logger.debug(f"native_inflight_support:_run: {e}")
                        continue
                if timing:
                    ms = (time.perf_counter() - t0) * 1000.0
                    if ms >= threshold_ms:
                        kind = None
                        try:
                            kind = item.get("song") if isinstance(item, dict) else None
                        except Exception as e:
                            logger.debug(f"native_inflight_support:_run: {e}")
                            kind = None
                        prefix = f"[PostSender][TIMING] {kind} " if kind else "[PostSender][TIMING] "
                        print(f"{prefix}post_queue_put={ms:.1f}ms")
            except Exception as e:
                logger.debug(f"native_inflight_support:_run: {e}")

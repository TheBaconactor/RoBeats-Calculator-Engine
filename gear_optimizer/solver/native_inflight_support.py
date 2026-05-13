from __future__ import annotations

from collections import OrderedDict
from typing import Any
import logging

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

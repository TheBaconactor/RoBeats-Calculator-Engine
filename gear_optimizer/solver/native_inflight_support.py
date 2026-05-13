from __future__ import annotations

from typing import Any

from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    extract_repeat_context,
    is_repeat_context,
    materialize_repeat_task,
    task_ga_seed,
    task_queue_label,
)


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

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Mapping, Sequence


# This fixed-field tuple is the runtime interchange format between task
# discovery and the native in-flight engine.
TASK_FIXED_FIELD_COUNT = 12


class TaskIndex(IntEnum):
    FILE_PATH = 0
    SONG_NAME = 1
    DIFFICULTY = 2
    CFG_DICT = 3
    PATHS = 4
    REF_ARRAYS = 5
    ALL_GEARS = 6
    ALL_MINIS = 7
    GEARS_BY_NAME = 8
    MINIS_BY_NAME = 9
    PARALLEL_WORKERS = 10
    FG_DEBUG = 11


@dataclass(frozen=True, slots=True)
class SongJob:
    file_path: Any
    song_name: str
    difficulty: str
    repeat_index: int = 0
    repeat_total: int = 0
    repeat_bundle: bool = False
    queue_source: str = "task_tuple"


@dataclass(frozen=True, slots=True)
class SharedRunContext:
    cfg_dict: Mapping[str, Any] | None
    paths: Any
    ref_arrays: Any
    all_gears: Any
    all_minis: Any
    gears_by_name: Mapping[str, Any] | None
    minis_by_name: Mapping[str, Any] | None
    parallel_workers: int
    fg_debug: bool


@dataclass(frozen=True, slots=True)
class SongTaskView:
    job: SongJob
    context: SharedRunContext
    extras: tuple[Any, ...]


def _is_task_sequence(task: Any) -> bool:
    return isinstance(task, (tuple, list))


def is_repeat_context(extra: Any) -> bool:
    return isinstance(extra, dict) and "repeat_index" in extra and "repeat_total" in extra


def extract_repeat_context(task: Sequence[Any] | Any) -> dict | None:
    if not _is_task_sequence(task) or len(task) <= TASK_FIXED_FIELD_COUNT:
        return None
    for extra in task[TASK_FIXED_FIELD_COUNT:]:
        if is_repeat_context(extra):
            return extra
    return None


def extract_repeat_bundle(task: Sequence[Any] | Any) -> dict | None:
    if not _is_task_sequence(task) or len(task) <= TASK_FIXED_FIELD_COUNT:
        return None
    for extra in task[TASK_FIXED_FIELD_COUNT:]:
        if not isinstance(extra, dict):
            continue
        if not bool(extra.get("repeat_bundle")):
            continue
        runs = extra.get("runs")
        if isinstance(runs, list) and runs:
            return extra
    return None


def materialize_repeat_task(task: tuple, repeat_ctx: dict) -> tuple:
    if not _is_task_sequence(task):
        return task
    prefix = list(task[:TASK_FIXED_FIELD_COUNT])
    extras: list[Any] = []
    for extra in task[TASK_FIXED_FIELD_COUNT:]:
        if is_repeat_context(extra):
            continue
        if isinstance(extra, dict) and bool(extra.get("repeat_bundle")):
            continue
        extras.append(extra)
    extras.append(dict(repeat_ctx or {}))
    return tuple(prefix + extras)


def task_file_path(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.FILE_PATH):
        return ""
    return os.path.abspath(str(task[int(TaskIndex.FILE_PATH)] or ""))


def task_song_name(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.SONG_NAME):
        return ""
    return str(task[int(TaskIndex.SONG_NAME)] or "").strip()


def task_difficulty(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.DIFFICULTY):
        return ""
    return str(task[int(TaskIndex.DIFFICULTY)] or "")


def task_cfg_dict(task: Sequence[Any] | Any) -> dict:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.CFG_DICT):
        return {}
    cfg_dict = task[int(TaskIndex.CFG_DICT)]
    return cfg_dict if isinstance(cfg_dict, dict) else {}


def task_queue_label(task: Sequence[Any] | Any) -> str:
    base = task_song_name(task)
    if not base:
        return "Unknown"
    repeat_ctx = extract_repeat_context(task)
    if repeat_ctx:
        try:
            idx = int(repeat_ctx.get("repeat_index") or 0)
            total = int(repeat_ctx.get("repeat_total") or 0)
        except (ValueError, TypeError):
            idx = 0
            total = 0
        if idx > 0 and total > 1:
            return f"{base} (Run {idx}/{total})"
    return base


def effective_task_count(tasks: list[Any]) -> int:
    if not isinstance(tasks, list) or not tasks:
        return 0
    total = 0
    for task in tasks:
        repeats = 1
        bundle = extract_repeat_bundle(task)
        if bundle is not None:
            try:
                repeats = int(bundle.get("repeat_total") or 0)
            except (ValueError, TypeError):
                repeats = 0
            if repeats <= 0:
                runs = bundle.get("runs")
                repeats = len(runs) if isinstance(runs, list) else 0
            repeats = max(1, int(repeats))
        total += max(1, int(repeats))
    return max(0, int(total))


def task_tuple_to_song_job(task: Sequence[Any], *, queue_source: str = "task_tuple") -> SongJob:
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError(f"song task must contain the {TASK_FIXED_FIELD_COUNT}-field production prefix")

    repeat_ctx = extract_repeat_context(task)
    repeat_bundle = extract_repeat_bundle(task)
    repeat_index = 0
    repeat_total = 0
    if repeat_ctx:
        try:
            repeat_index = int(repeat_ctx.get("repeat_index") or 0)
        except (ValueError, TypeError):
            repeat_index = 0
        try:
            repeat_total = int(repeat_ctx.get("repeat_total") or 0)
        except (ValueError, TypeError):
            repeat_total = 0
    elif repeat_bundle is not None:
        try:
            repeat_total = int(repeat_bundle.get("repeat_total") or 0)
        except (ValueError, TypeError):
            repeat_total = 0
        if repeat_total <= 0:
            runs = repeat_bundle.get("runs")
            repeat_total = len(runs) if isinstance(runs, list) else 0

    return SongJob(
        file_path=task[int(TaskIndex.FILE_PATH)],
        song_name=str(task[int(TaskIndex.SONG_NAME)] or ""),
        difficulty=str(task[int(TaskIndex.DIFFICULTY)] or ""),
        repeat_index=max(0, int(repeat_index)),
        repeat_total=max(0, int(repeat_total)),
        repeat_bundle=repeat_bundle is not None,
        queue_source=str(queue_source or "task_tuple"),
    )


def task_tuple_to_shared_context(task: Sequence[Any]) -> SharedRunContext:
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError(f"song task must contain the {TASK_FIXED_FIELD_COUNT}-field production prefix")

    try:
        parallel_workers = int(task[int(TaskIndex.PARALLEL_WORKERS)] or 0)
    except (ValueError, TypeError):
        parallel_workers = 0

    return SharedRunContext(
        cfg_dict=task[int(TaskIndex.CFG_DICT)],
        paths=task[int(TaskIndex.PATHS)],
        ref_arrays=task[int(TaskIndex.REF_ARRAYS)],
        all_gears=task[int(TaskIndex.ALL_GEARS)],
        all_minis=task[int(TaskIndex.ALL_MINIS)],
        gears_by_name=task[int(TaskIndex.GEARS_BY_NAME)],
        minis_by_name=task[int(TaskIndex.MINIS_BY_NAME)],
        parallel_workers=parallel_workers,
        fg_debug=bool(task[int(TaskIndex.FG_DEBUG)]),
    )


def task_tuple_to_view(task: Sequence[Any]) -> SongTaskView:
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError(f"song task must contain the {TASK_FIXED_FIELD_COUNT}-field production prefix")
    return SongTaskView(
        job=task_tuple_to_song_job(task),
        context=task_tuple_to_shared_context(task),
        extras=tuple(task[TASK_FIXED_FIELD_COUNT:]),
    )

def task_tuple_from_job_context(
    job: SongJob,
    context: SharedRunContext,
    *extras: Any,
) -> tuple[Any, ...]:
    return (
        job.file_path,
        job.song_name,
        job.difficulty,
        context.cfg_dict,
        context.paths,
        context.ref_arrays,
        context.all_gears,
        context.all_minis,
        context.gears_by_name,
        context.minis_by_name,
        context.parallel_workers,
        context.fg_debug,
        *extras,
    )

def ensure_task_tuple(task: Sequence[Any]) -> tuple[Any, ...]:
    """Validate the task tuple ABI and return it as an immutable tuple.

    Historically we "canonicalized" tasks by unpacking them into a typed view and
    rebuilding the tuple. That roundtrip is semantically identity for valid tasks
    (it exists to validate the fixed-field ABI). This helper keeps the validation
    but avoids rebuilding/allocating a new tuple.
    """
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError("song task must contain the fixed-field production prefix")
    # Ensure we can interpret it as a view (type/shape validation).
    task_tuple_to_view(task)
    return tuple(task)

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Mapping, Sequence

from gear_optimizer.gamedata import Gear, Mini, StatCurves


# NOTE: This "task tuple" shape is a fixed-field ABI used across the runtime
# pipeline (app -> execution -> engine). The code originally named it "legacy"
# when refactoring toward typed `SongJob`/`SharedRunContext` while keeping the
# tuple as the durable interchange format.
TASK_FIXED_FIELD_COUNT = 9


class TaskIndex(IntEnum):
    FILE_PATH = 0
    SONG_NAME = 1
    DIFFICULTY = 2
    MULTI_START = 3
    CURVES = 4
    GEARS = 5
    MINIS = 6
    GA_DEPTH = 7
    PARALLEL_WORKERS = 8


@dataclass(frozen=True, slots=True)
class SongJob:
    file_path: Any
    song_name: str
    difficulty: str
    repeat_index: int = 0
    repeat_total: int = 0
    ga_seed: int | None = None


@dataclass(frozen=True, slots=True)
class PreparedSongSeedPlan:
    queue_label: str
    repeat_index: int
    repeat_total: int
    ga_seed: int | None


@dataclass(frozen=True, slots=True)
class SharedRunContext:
    multi_start: int
    curves: StatCurves
    # Gears.csv / Minis.csv by name, in file order.
    gears: Mapping[str, Gear]
    minis: Mapping[str, Mini]
    ga_depth: int
    parallel_workers: int


@dataclass(frozen=True, slots=True)
class SongTaskView:
    job: SongJob
    context: SharedRunContext
    extras: tuple[Any, ...]


def _is_task_sequence(task: Any) -> bool:
    return isinstance(task, (tuple, list))


def is_repeat_context(extra: Any) -> bool:
    return isinstance(extra, dict) and "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra


def extract_repeat_context(task: Sequence[Any] | Any) -> dict | None:
    if not _is_task_sequence(task) or len(task) <= TASK_FIXED_FIELD_COUNT:
        return None
    for extra in task[TASK_FIXED_FIELD_COUNT:]:
        if is_repeat_context(extra):
            return extra
    return None


def task_file_path(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.FILE_PATH):
        return ""
    return os.path.abspath(str(task[int(TaskIndex.FILE_PATH)] or ""))


def task_song_name(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(TaskIndex.SONG_NAME):
        return ""
    return str(task[int(TaskIndex.SONG_NAME)] or "").strip()


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


def task_ga_seed(task: Sequence[Any] | Any) -> int | None:
    repeat_ctx = extract_repeat_context(task)
    if not repeat_ctx:
        return None
    try:
        seed = repeat_ctx.get("ga_seed")
        return int(seed) if seed is not None else None
    except (ValueError, TypeError):
        return None


def seed_plan_from_song_job(job: SongJob) -> PreparedSongSeedPlan:
    repeat_index = max(0, int(job.repeat_index or 0))
    repeat_total = max(0, int(job.repeat_total or 0))
    base = str(job.song_name or "")
    queue_label = base or "Unknown"
    if repeat_index > 0 and repeat_total > 1 and base:
        queue_label = f"{base} (Run {repeat_index}/{repeat_total})"
    return PreparedSongSeedPlan(
        queue_label=queue_label,
        repeat_index=repeat_index,
        repeat_total=repeat_total,
        ga_seed=job.ga_seed,
    )


def task_tuple_to_song_job(task: Sequence[Any]) -> SongJob:
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError(f"song task must contain the {TASK_FIXED_FIELD_COUNT}-field production prefix")

    repeat_ctx = extract_repeat_context(task)
    repeat_index = 0
    repeat_total = 0
    ga_seed = None
    if repeat_ctx:
        try:
            repeat_index = int(repeat_ctx.get("repeat_index") or 0)
        except (ValueError, TypeError):
            repeat_index = 0
        try:
            repeat_total = int(repeat_ctx.get("repeat_total") or 0)
        except (ValueError, TypeError):
            repeat_total = 0
        ga_seed = task_ga_seed(task)

    return SongJob(
        file_path=task[int(TaskIndex.FILE_PATH)],
        song_name=str(task[int(TaskIndex.SONG_NAME)] or ""),
        difficulty=str(task[int(TaskIndex.DIFFICULTY)] or ""),
        repeat_index=max(0, int(repeat_index)),
        repeat_total=max(0, int(repeat_total)),
        ga_seed=ga_seed,
    )


def task_tuple_to_shared_context(task: Sequence[Any]) -> SharedRunContext:
    if not _is_task_sequence(task) or len(task) < TASK_FIXED_FIELD_COUNT:
        raise ValueError(f"song task must contain the {TASK_FIXED_FIELD_COUNT}-field production prefix")

    try:
        ga_depth = int(task[int(TaskIndex.GA_DEPTH)] or 0)
    except (ValueError, TypeError):
        ga_depth = 0
    try:
        parallel_workers = int(task[int(TaskIndex.PARALLEL_WORKERS)] or 0)
    except (ValueError, TypeError):
        parallel_workers = 0

    return SharedRunContext(
        multi_start=int(task[int(TaskIndex.MULTI_START)]),
        curves=task[int(TaskIndex.CURVES)],
        gears=task[int(TaskIndex.GEARS)],
        minis=task[int(TaskIndex.MINIS)],
        ga_depth=ga_depth,
        parallel_workers=parallel_workers,
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
        context.multi_start,
        context.curves,
        context.gears,
        context.minis,
        context.ga_depth,
        context.parallel_workers,
        *extras,
    )


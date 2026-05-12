from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Mapping, Sequence


LEGACY_TASK_FIXED_FIELD_COUNT = 16


class LegacyTaskIndex(IntEnum):
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
    USE_EVO_DB = 10
    AUTO_BUFF = 11
    GA_DEPTH = 12
    STATUS_QUEUE = 13
    PARALLEL_WORKERS = 14
    FG_DEBUG = 15


@dataclass(frozen=True, slots=True)
class SongJob:
    file_path: Any
    song_name: str
    difficulty: str
    repeat_index: int = 0
    repeat_total: int = 0
    ga_seed: int | None = None
    repeat_bundle: bool = False
    queue_source: str = "legacy_task_tuple"


@dataclass(frozen=True, slots=True)
class PreparedSongSeedPlan:
    queue_label: str
    repeat_index: int
    repeat_total: int
    ga_seed: int | None


@dataclass(frozen=True, slots=True)
class SharedRunContext:
    cfg_dict: Mapping[str, Any] | None
    paths: Any
    ref_arrays: Any
    all_gears: Any
    all_minis: Any
    gears_by_name: Mapping[str, Any] | None
    minis_by_name: Mapping[str, Any] | None
    use_evo_db: bool
    auto_buff: bool
    ga_depth: int
    status_queue: Any
    parallel_workers: int
    fg_debug: bool


@dataclass(frozen=True, slots=True)
class LegacySongTaskView:
    job: SongJob
    context: SharedRunContext
    extras: tuple[Any, ...]


def _is_task_sequence(task: Any) -> bool:
    return isinstance(task, (tuple, list))


def is_repeat_context(extra: Any) -> bool:
    return isinstance(extra, dict) and "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra


def extract_repeat_context(task: Sequence[Any] | Any) -> dict | None:
    if not _is_task_sequence(task) or len(task) <= LEGACY_TASK_FIXED_FIELD_COUNT:
        return None
    for extra in task[LEGACY_TASK_FIXED_FIELD_COUNT:]:
        if is_repeat_context(extra):
            return extra
    return None


def extract_repeat_bundle(task: Sequence[Any] | Any) -> dict | None:
    if not _is_task_sequence(task) or len(task) <= LEGACY_TASK_FIXED_FIELD_COUNT:
        return None
    for extra in task[LEGACY_TASK_FIXED_FIELD_COUNT:]:
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
    prefix = list(task[:LEGACY_TASK_FIXED_FIELD_COUNT])
    extras: list[Any] = []
    for extra in task[LEGACY_TASK_FIXED_FIELD_COUNT:]:
        if is_repeat_context(extra):
            continue
        if isinstance(extra, dict) and bool(extra.get("repeat_bundle")):
            continue
        extras.append(extra)
    extras.append(dict(repeat_ctx or {}))
    return tuple(prefix + extras)


def task_song_name(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(LegacyTaskIndex.SONG_NAME):
        return ""
    return str(task[int(LegacyTaskIndex.SONG_NAME)] or "").strip()


def task_file_path(task: Sequence[Any] | Any) -> Any:
    if not _is_task_sequence(task) or len(task) <= int(LegacyTaskIndex.FILE_PATH):
        return ""
    return task[int(LegacyTaskIndex.FILE_PATH)]


def task_difficulty(task: Sequence[Any] | Any) -> str:
    if not _is_task_sequence(task) or len(task) <= int(LegacyTaskIndex.DIFFICULTY):
        return ""
    return str(task[int(LegacyTaskIndex.DIFFICULTY)] or "")


def task_cfg_dict(task: Sequence[Any] | Any) -> dict:
    if not _is_task_sequence(task) or len(task) <= int(LegacyTaskIndex.CFG_DICT):
        return {}
    cfg_dict = task[int(LegacyTaskIndex.CFG_DICT)]
    return cfg_dict if isinstance(cfg_dict, dict) else {}


def task_ref_arrays(task: Sequence[Any] | Any) -> Any:
    if not _is_task_sequence(task) or len(task) <= int(LegacyTaskIndex.REF_ARRAYS):
        return None
    return task[int(LegacyTaskIndex.REF_ARRAYS)]


def task_extras(task: Sequence[Any] | Any) -> tuple[Any, ...]:
    if not _is_task_sequence(task) or len(task) <= LEGACY_TASK_FIXED_FIELD_COUNT:
        return ()
    return tuple(task[LEGACY_TASK_FIXED_FIELD_COUNT:])


def task_with_status_queue(task: Sequence[Any], status_queue: Any) -> tuple[Any, ...]:
    if not _is_task_sequence(task) or len(task) < LEGACY_TASK_FIXED_FIELD_COUNT:
        raise ValueError("legacy song task must contain the 16-field production prefix")
    out = list(task)
    out[int(LegacyTaskIndex.STATUS_QUEUE)] = status_queue
    return tuple(out)


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


def seed_plan_from_task_tuple(task: Sequence[Any]) -> PreparedSongSeedPlan:
    return seed_plan_from_song_job(task_tuple_to_song_job(task))


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


def task_tuple_to_song_job(task: Sequence[Any], *, queue_source: str = "legacy_task_tuple") -> SongJob:
    if not _is_task_sequence(task) or len(task) < LEGACY_TASK_FIXED_FIELD_COUNT:
        raise ValueError("legacy song task must contain the 16-field production prefix")

    repeat_ctx = extract_repeat_context(task)
    repeat_bundle = extract_repeat_bundle(task)
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
    elif repeat_bundle is not None:
        try:
            repeat_total = int(repeat_bundle.get("repeat_total") or 0)
        except (ValueError, TypeError):
            repeat_total = 0
        if repeat_total <= 0:
            runs = repeat_bundle.get("runs")
            repeat_total = len(runs) if isinstance(runs, list) else 0

    return SongJob(
        file_path=task[int(LegacyTaskIndex.FILE_PATH)],
        song_name=str(task[int(LegacyTaskIndex.SONG_NAME)] or ""),
        difficulty=str(task[int(LegacyTaskIndex.DIFFICULTY)] or ""),
        repeat_index=max(0, int(repeat_index)),
        repeat_total=max(0, int(repeat_total)),
        ga_seed=ga_seed,
        repeat_bundle=repeat_bundle is not None,
        queue_source=str(queue_source or "legacy_task_tuple"),
    )


def task_tuple_to_shared_context(task: Sequence[Any]) -> SharedRunContext:
    if not _is_task_sequence(task) or len(task) < LEGACY_TASK_FIXED_FIELD_COUNT:
        raise ValueError("legacy song task must contain the 16-field production prefix")

    try:
        ga_depth = int(task[int(LegacyTaskIndex.GA_DEPTH)] or 0)
    except (ValueError, TypeError):
        ga_depth = 0
    try:
        parallel_workers = int(task[int(LegacyTaskIndex.PARALLEL_WORKERS)] or 0)
    except (ValueError, TypeError):
        parallel_workers = 0

    return SharedRunContext(
        cfg_dict=task[int(LegacyTaskIndex.CFG_DICT)],
        paths=task[int(LegacyTaskIndex.PATHS)],
        ref_arrays=task[int(LegacyTaskIndex.REF_ARRAYS)],
        all_gears=task[int(LegacyTaskIndex.ALL_GEARS)],
        all_minis=task[int(LegacyTaskIndex.ALL_MINIS)],
        gears_by_name=task[int(LegacyTaskIndex.GEARS_BY_NAME)],
        minis_by_name=task[int(LegacyTaskIndex.MINIS_BY_NAME)],
        use_evo_db=bool(task[int(LegacyTaskIndex.USE_EVO_DB)]),
        auto_buff=bool(task[int(LegacyTaskIndex.AUTO_BUFF)]),
        ga_depth=ga_depth,
        status_queue=task[int(LegacyTaskIndex.STATUS_QUEUE)],
        parallel_workers=parallel_workers,
        fg_debug=bool(task[int(LegacyTaskIndex.FG_DEBUG)]),
    )


def task_tuple_to_legacy_view(task: Sequence[Any]) -> LegacySongTaskView:
    if not _is_task_sequence(task) or len(task) < LEGACY_TASK_FIXED_FIELD_COUNT:
        raise ValueError("legacy song task must contain the 16-field production prefix")
    return LegacySongTaskView(
        job=task_tuple_to_song_job(task),
        context=task_tuple_to_shared_context(task),
        extras=tuple(task[LEGACY_TASK_FIXED_FIELD_COUNT:]),
    )

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

SongQueueItem = tuple[str, str, str]


def infer_song_difficulty_from_path(root: str) -> str:
    parent_folder = os.path.basename(str(root or "")).lower()
    if parent_folder == "hard":
        return "Hard"
    if parent_folder == "normal":
        return "Normal"
    if parent_folder == "easy":
        return "Easy"
    return "Unknown"


def queue_path_key(item: SongQueueItem) -> str:
    return os.path.abspath(str(item[0] or "")).casefold()


def normalize_queue_item(item: SongQueueItem) -> SongQueueItem:
    fp = os.path.abspath(str(item[0] or ""))
    return (fp, str(item[1] or ""), str(item[2] or "Unknown"))


def queue_sort_key(item: SongQueueItem) -> tuple[str, str, str]:
    return (
        str(item[1] or "").casefold(),
        str(item[2] or "").casefold(),
        queue_path_key(item),
    )


def prioritize_missing_first(
    queue: list[SongQueueItem],
    present: set[str],
    *,
    sort_key: Callable[[SongQueueItem], tuple[str, str, str]] | None = None,
) -> list[SongQueueItem]:
    missing = [item for item in queue if item[1] not in present]
    existing = [item for item in queue if item[1] in present]
    if sort_key is not None:
        missing = sorted(missing, key=sort_key)
        existing = sorted(existing, key=sort_key)
    return missing + existing


def merge_discovered_with_resume(
    *,
    discovered_queue: list[SongQueueItem],
    resume_queue: list[SongQueueItem],
    song_queue_limit: int = 0,
) -> tuple[list[SongQueueItem], int]:
    """
    Prepend every discovered chart whose file path is absent from the resume file.

    Resume membership is path-keyed so git-pulled charts always enter the scheduled
    pool and startup cache prebuild even when catalog/loadout rows already exist.
    """
    resume_paths = {queue_path_key(item) for item in resume_queue}
    prepended = [item for item in discovered_queue if queue_path_key(item) not in resume_paths]
    merged = list(prepended) + list(resume_queue)
    limit = max(0, int(song_queue_limit or 0))
    if limit > 0 and len(merged) > limit:
        if len(prepended) >= limit:
            merged = list(prepended[:limit])
        else:
            keep_resume = limit - len(prepended)
            merged = list(prepended) + list(resume_queue[:keep_resume])
    return merged, len(prepended)


@dataclass(frozen=True, slots=True)
class FinalizeSongQueueResult:
    queue: list[SongQueueItem]
    prepended_count: int
    limit_applied: bool


def finalize_song_queue(
    *,
    discovered_queue: list[SongQueueItem],
    resume_queue: list[SongQueueItem] | None = None,
    song_queue_limit: int = 0,
    present_names: set[str] | None = None,
) -> FinalizeSongQueueResult:
    """
    Canonical queue policy after discovery.

    - DB-missing songs are ordered ahead of catalog-present songs.
    - Active resume prepends path-absent discoveries and applies limit to the resume tail only.
    - Without resume, limit truncates the discovered pool after stable sort.
    """
    present = set(present_names or ())
    discovered = list(discovered_queue)
    if present:
        discovered = prioritize_missing_first(discovered, present)

    resume = list(resume_queue or ())
    if resume and present:
        resume = prioritize_missing_first(resume, present)

    limit = max(0, int(song_queue_limit or 0))
    if resume:
        merged, prepended_count = merge_discovered_with_resume(
            discovered_queue=discovered,
            resume_queue=resume,
            song_queue_limit=limit,
        )
        limit_applied = limit > 0 and len(merged) < len(discovered) + len(resume)
        return FinalizeSongQueueResult(
            queue=merged,
            prepended_count=prepended_count,
            limit_applied=limit_applied,
        )

    if limit > 0 and len(discovered) > limit:
        if present:
            discovered = prioritize_missing_first(discovered, present, sort_key=queue_sort_key)
        else:
            discovered = sorted(discovered, key=queue_sort_key)
        discovered = discovered[:limit]
        return FinalizeSongQueueResult(queue=discovered, prepended_count=0, limit_applied=True)

    return FinalizeSongQueueResult(queue=discovered, prepended_count=0, limit_applied=False)

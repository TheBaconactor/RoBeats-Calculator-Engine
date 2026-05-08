from __future__ import annotations

import logging
from typing import Any



logger = logging.getLogger(__name__)
def optimizer_priority_api_enabled(app: Any) -> bool:
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return False
    try:
        return bool(api.priority_queue_enabled())
    except Exception as e:
        logger.debug(f"api_integration:optimizer_priority_api_enabled: {e}")
        return bool(api.backend_mode_enabled())


def prioritize_robeatsmeta_song_queue(
    app: Any,
    song_queue: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    if not song_queue or not optimizer_priority_api_enabled(app):
        return song_queue
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return song_queue
    try:
        priority_names = {
            str(name or "").strip()
            for name in getattr(app, "_backend_priority_song_names", set())
            if str(name or "").strip()
        }
        if priority_names:
            priority_front = [item for item in song_queue if str(item[1] or "").strip() in priority_names]
            remainder = [item for item in song_queue if str(item[1] or "").strip() not in priority_names]
            prioritized_remainder = api.prioritize_song_queue(remainder)
            return priority_front + prioritized_remainder
        return api.prioritize_song_queue(song_queue)
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to prioritize song queue: {type(exc).__name__}: {exc}")
        return song_queue


def filter_robeatsmeta_recently_computed_song_queue(
    app: Any,
    song_queue: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    if not song_queue or not optimizer_priority_api_enabled(app):
        return song_queue
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return song_queue
    try:
        recent_bundle_keys = api.recently_computed_bundle_keys()
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to read recently computed bundles: {type(exc).__name__}: {exc}")
        return song_queue
    if not recent_bundle_keys:
        return song_queue

    filtered: list[tuple[str, str, str]] = []
    for item in song_queue:
        try:
            song_name = str(item[1] or "").strip()
        except Exception as e:
            logger.debug(f"api_integration:filter_robeatsmeta_recently_computed_song_queue: {e}")
            filtered.append(item)
            continue
        try:
            bundle_key = api._bundle_key_for_song_id(song_name)
        except Exception as e:
            logger.debug(f"api_integration:filter_robeatsmeta_recently_computed_song_queue: {e}")
            filtered.append(item)
            continue
        if str(bundle_key or "").strip() in recent_bundle_keys:
            continue
        filtered.append(item)
    return filtered


def maybe_mark_robeatsmeta_song_batch_computed(
    app: Any,
    song_name: str | None,
    completed_songs: set[str] | None = None,
) -> bool:
    if not song_name or not optimizer_priority_api_enabled(app):
        return False
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return False
    tasks = getattr(app, "_run_tasks_ref", None)
    if not isinstance(tasks, list) or not tasks:
        return False
    completed = completed_songs if isinstance(completed_songs, set) else getattr(app, "_run_completed_ref", None)
    if not isinstance(completed, set):
        return False

    try:
        target_bundle_key = api._bundle_key_for_song_id(str(song_name))
    except Exception as e:
        logger.debug(f"api_integration:maybe_mark_robeatsmeta_song_batch_computed: {e}")
        return False
    if not str(target_bundle_key or "").strip():
        return False

    for task in tasks:
        try:
            task_label = app._task_queue_label(task)
        except Exception as e:
            logger.debug(f"api_integration:maybe_mark_robeatsmeta_song_batch_computed: {e}")
            continue
        if not task_label or task_label in completed:
            continue
        try:
            task_bundle_key = api._bundle_key_for_song_id(str(task_label))
        except Exception as e:
            logger.debug(f"api_integration:maybe_mark_robeatsmeta_song_batch_computed: {e}")
            continue
        if str(task_bundle_key or "").strip() == str(target_bundle_key or "").strip():
            return False

    try:
        api.mark_song_computed(song_id=str(song_name))
        return True
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to mark song batch computed: {type(exc).__name__}: {exc}")
        return False


def mark_robeatsmeta_song_started(app: Any, song_name: str | None) -> None:
    if not song_name or not optimizer_priority_api_enabled(app):
        return
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return
    try:
        api.mark_song_started(song_id=str(song_name))
        api.update_runtime_status(
            status="running",
            current_song=str(song_name),
            completed=int(getattr(app, "_runtime_completed_count", 0) or 0),
            total=int(getattr(app, "_runtime_total_count", 0) or 0),
            failed=int(getattr(app, "_runtime_failed_count", 0) or 0),
        )
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to mark song started: {type(exc).__name__}: {exc}")


def update_robeatsmeta_runtime_status(
    app: Any,
    *,
    status: str | None = None,
    current_song: str | None = None,
    completed: int | None = None,
    total: int | None = None,
    failed: int | None = None,
) -> None:
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return
    try:
        api.update_runtime_status(
            status=status,
            current_song=current_song,
            completed=completed,
            total=total,
            failed=failed,
        )
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to update runtime status: {type(exc).__name__}: {exc}")


def clear_robeatsmeta_runtime_status(app: Any, *, status: str = "idle", available: bool = True) -> None:
    api = getattr(app, "_robeatsmeta_api", None)
    if api is None:
        return
    try:
        api.clear_runtime_status(status=status, available=available)
    except Exception as exc:
        logging.warning(f"[RoBeatsMeta] Failed to clear runtime status: {type(exc).__name__}: {exc}")

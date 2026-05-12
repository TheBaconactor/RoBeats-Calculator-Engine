from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
import queue
import time
from typing import Any, Callable, Iterator, Sequence

logger = logging.getLogger(__name__)


def with_streaming_extras(task: Any, assets: Any | None, *, defer_post: bool) -> tuple[Any, ...]:
    """Append streaming-only extras to a normal song task tuple."""
    args = list(task) if isinstance(task, (list, tuple)) else [task]
    if assets is not None:
        args.append(assets)
    if bool(defer_post):
        args.append(True)
    return tuple(args)


def completion_payload_from_deferred(result: dict[str, Any]) -> dict[str, Any]:
    """
    Return a lightweight completion payload after the full payload is handed to
    the post processor.

    `_consume_results()` still needs authoritative progress/new-record fields,
    but it must not persist the same result a second time.
    """
    keep_keys = (
        "song",
        "_queue_key",
        "_queue_label",
        "_repeat_index",
        "_repeat_total",
        "_solver_seed",
        "db_key",
        "file_path",
        "difficulty",
        "_record",
        "best_data",
        "prev_record",
        "fg_variants",
        "db_best_fg_score",
        "db_baseline_valid",
        "_stage_timing",
        "_gpu_timing",
    )
    out = {key: result.get(key) for key in keep_keys if key in result}
    out["_deferred_post_dispatched"] = True
    out["log"] = ""
    return out


def iter_streamed_song_results(
    tasks: Sequence[Any],
    *,
    process_fn: Callable[[Any], dict[str, Any]],
    preload_fn: Callable[[Any], Any | None],
    post_queue: Any | None,
    max_workers: int = 1,
) -> Iterator[dict[str, Any]]:
    """
    Single-GPU song-pool pipeline.

    A one-item CPU prep lookahead is enough for a single GPU owner: while song N
    is executing skyline/FG kernels, the background worker parses and prepares
    the CPU-only solver context for song N+1. The main iterator preserves input
    order and still runs exactly one GPU solve at a time.
    """
    task_list = list(tasks or [])
    if not task_list:
        return

    workers = max(1, int(max_workers or 1))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="SkylineSongPrep") as executor:
        current_future: Future[Any] | None = executor.submit(preload_fn, task_list[0])
        for idx, task in enumerate(task_list):
            wait_started = time.perf_counter()
            assets = None
            if current_future is not None:
                try:
                    assets = current_future.result()
                except Exception as exc:
                    logger.warning("[SkylineStream] CPU prep failed; falling back for task %s: %s", idx + 1, exc)
                    assets = None
            prefetch_wait_sec = time.perf_counter() - wait_started

            next_future: Future[Any] | None = None
            if idx + 1 < len(task_list):
                # Schedule the next song before running the current GPU solve so
                # CPU prep overlaps the current song's skyline/FG kernels.
                next_future = executor.submit(preload_fn, task_list[idx + 1])

            result = process_fn(with_streaming_extras(task, assets, defer_post=post_queue is not None))
            if isinstance(result, dict):
                result.setdefault("_stage_timing", {})["stream_prefetch_wait_sec"] = float(prefetch_wait_sec)

            if post_queue is not None and isinstance(result, dict) and result.get("_deferred_post"):
                enqueue_started = time.perf_counter()
                post_queue.put(result)
                shell = completion_payload_from_deferred(result)
                shell.setdefault("_stage_timing", {})["stream_post_enqueue_sec"] = float(
                    time.perf_counter() - enqueue_started
                )
                yield shell
            else:
                yield result

            current_future = next_future


def drain_post_queue_for_tests(q: queue.Queue[Any]) -> list[Any]:
    """Small test helper; normal runtime uses multiprocessing queues."""
    out: list[Any] = []
    while True:
        try:
            out.append(q.get_nowait())
        except queue.Empty:
            return out

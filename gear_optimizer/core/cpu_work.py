from __future__ import annotations

import atexit
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from math import ceil
import multiprocessing as mp
import os
import threading
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")

_EXECUTORS: dict[tuple[str, int], Executor] = {}
_EXECUTORS_LOCK = threading.Lock()


def resolve_cpu_worker_count(requested: int | None = None) -> int:
    """Resolve the dynamic CPU worker count.

    `METAFINDER_CPU_WORKERS <= 0` means "all available logical CPUs".
    """

    if requested is None:
        try:
            requested = int(os.environ.get("METAFINDER_CPU_WORKERS", "0") or "0")
        except Exception:
            requested = 0
    if int(requested or 0) <= 0:
        requested = os.cpu_count() or 1
    return max(1, int(requested))


def resolve_cpu_work_mode(default: str = "process") -> str:
    """Return the configured CPU work mode.

    Process workers are the default for large pure-Python prep so the optimizer
    can use all CPU cores. They are disabled from daemon child processes because Windows
    multiprocessing cannot safely spawn grandchildren from those contexts.
    """

    mode = str(os.environ.get("METAFINDER_CPU_WORK_MODE", default) or default).strip().lower()
    if mode not in {"serial", "thread", "process"}:
        mode = str(default or "thread").strip().lower()
    if mode == "process":
        try:
            if mp.current_process().daemon:
                return "thread"
        except Exception:
            return "thread"
    return mode


def should_parallelize_work(
    item_count: int,
    *,
    min_items: int = 512,
    min_items_per_worker: int = 128,
    requested_workers: int | None = None,
    mode: str | None = None,
) -> tuple[bool, int, str]:
    """Resolve whether a workload should run in parallel.

    Returns `(enabled, worker_count, mode)` with the worker count capped to the
    amount of useful work. This keeps tiny tasks serial and avoids flooding the
    process with idle workers.
    """

    item_count_i = max(0, int(item_count))
    mode_i = resolve_cpu_work_mode() if mode is None else str(mode).strip().lower()
    workers = resolve_cpu_worker_count(requested_workers)
    if mode_i == "serial" or workers <= 1 or item_count_i < max(1, int(min_items)):
        return False, 1, "serial"
    useful_workers = int(ceil(float(item_count_i) / float(max(1, int(min_items_per_worker)))))
    workers = max(1, min(int(workers), int(useful_workers)))
    if workers <= 1:
        return False, 1, "serial"
    return True, workers, mode_i


def chunk_sequence(items: list[T], *, worker_count: int, min_items_per_worker: int = 128) -> list[list[T]]:
    if not items:
        return []
    workers = max(1, min(int(worker_count), int(ceil(len(items) / max(1, int(min_items_per_worker))))))
    chunk_size = max(1, int(ceil(len(items) / float(workers))))
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def parallel_map_ordered(
    fn: Callable[[T], R],
    items: Iterable[T],
    *,
    min_items: int = 512,
    min_items_per_worker: int = 128,
    requested_workers: int | None = None,
    mode: str | None = None,
) -> list[R]:
    """Run `fn` over `items`, preserving input order.

    The helper is intentionally generic and GPU-agnostic. Callers must only
    submit CPU-only, import-safe work.
    """

    item_list = list(items)
    enabled, workers, resolved_mode = should_parallelize_work(
        len(item_list),
        min_items=min_items,
        min_items_per_worker=min_items_per_worker,
        requested_workers=requested_workers,
        mode=mode,
    )
    if not enabled:
        return [fn(item) for item in item_list]

    executor = _get_executor(resolved_mode, workers)
    try:
        return list(executor.map(fn, item_list))
    except Exception:
        if resolved_mode == "process":
            _discard_executor("process", workers)
            executor = _get_executor("thread", workers)
            return list(executor.map(fn, item_list))
        raise


def _get_executor(mode: str, workers: int) -> Executor:
    mode_i = "process" if str(mode).strip().lower() == "process" else "thread"
    key = (mode_i, max(1, int(workers)))
    with _EXECUTORS_LOCK:
        existing = _EXECUTORS.get(key)
        if existing is not None:
            return existing
        if mode_i == "process":
            executor: Executor = ProcessPoolExecutor(
                max_workers=key[1],
                mp_context=mp.get_context("spawn"),
            )
        else:
            executor = ThreadPoolExecutor(max_workers=key[1], thread_name_prefix="metafinder-cpu")
        _EXECUTORS[key] = executor
        return executor


def _discard_executor(mode: str, workers: int) -> None:
    mode_i = "process" if str(mode).strip().lower() == "process" else "thread"
    key = (mode_i, max(1, int(workers)))
    with _EXECUTORS_LOCK:
        executor = _EXECUTORS.pop(key, None)
    if executor is not None:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


def shutdown_cpu_work_executors() -> None:
    with _EXECUTORS_LOCK:
        executors = list(_EXECUTORS.values())
        _EXECUTORS.clear()
    for executor in executors:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass


atexit.register(shutdown_cpu_work_executors)

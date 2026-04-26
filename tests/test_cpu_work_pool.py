import os

from gear_optimizer.core import cpu_work


def _square(value: int) -> int:
    return int(value) * int(value)


def _worker_pid(_value: int) -> int:
    return int(os.getpid())


def test_parallel_map_ordered_preserves_order_with_threads(monkeypatch):
    monkeypatch.setenv("METAFINDER_CPU_WORK_MODE", "thread")
    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "4")

    values = list(range(64))
    assert cpu_work.parallel_map_ordered(
        _square,
        values,
        min_items=1,
        min_items_per_worker=4,
    ) == [value * value for value in values]


def test_parallel_map_ordered_uses_process_workers(monkeypatch):
    monkeypatch.setenv("METAFINDER_CPU_WORK_MODE", "process")
    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "2")
    cpu_work.shutdown_cpu_work_executors()

    worker_pids = cpu_work.parallel_map_ordered(
        _worker_pid,
        list(range(16)),
        min_items=1,
        min_items_per_worker=4,
    )
    cpu_work.shutdown_cpu_work_executors()

    assert any(pid != os.getpid() for pid in worker_pids)


def test_should_parallelize_caps_workers_to_useful_work(monkeypatch):
    monkeypatch.setenv("METAFINDER_CPU_WORK_MODE", "thread")
    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "32")

    enabled, workers, mode = cpu_work.should_parallelize_work(
        10,
        min_items=1,
        min_items_per_worker=4,
    )

    assert enabled is True
    assert mode == "thread"
    assert workers == 3


def test_default_mode_prefers_process_for_real_cpu_parallelism(monkeypatch):
    monkeypatch.delenv("METAFINDER_CPU_WORK_MODE", raising=False)

    assert cpu_work.resolve_cpu_work_mode() == "process"


def test_shutdown_cpu_work_executors_is_idempotent():
    cpu_work.shutdown_cpu_work_executors()
    cpu_work.shutdown_cpu_work_executors()

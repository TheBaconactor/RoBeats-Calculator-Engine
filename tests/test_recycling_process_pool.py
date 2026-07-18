from __future__ import annotations

import concurrent.futures
import os
import time
from concurrent.futures.process import BrokenProcessPool

import pytest

from gear_optimizer.core.recycling_process_pool import BoundedRecyclingProcessPool


def _return_process_identity(value: int) -> tuple[int, int]:
    time.sleep(0.02)
    return int(value), os.getpid()


def _return_identity_or_raise(value: int) -> tuple[int, int]:
    if int(value) == 4:
        raise ValueError("expected worker failure")
    return int(value), os.getpid()


def _return_after_delay(value: int, delay_s: float) -> int:
    time.sleep(float(delay_s))
    return int(value)


def _fail_worker_initializer() -> None:
    raise RuntimeError("initializer sentinel")


def _exit_native_worker() -> None:
    os._exit(19)


def test_recycling_process_pool_completes_past_original_worker_capacity() -> None:
    workers = 2
    tasks_per_worker = 3
    task_count = workers * tasks_per_worker + 3

    with BoundedRecyclingProcessPool(
        max_workers=workers,
        max_tasks_per_worker=tasks_per_worker,
    ) as pool:
        futures = [pool.submit(_return_process_identity, value) for value in range(task_count)]
        done, not_done = concurrent.futures.wait(futures, timeout=30.0)

    assert not not_done
    results = [future.result() for future in done]
    assert sorted(value for value, _pid in results) == list(range(task_count))
    assert len({pid for _value, pid in results}) > workers


def test_recycling_process_pool_replaces_first_drained_worker_without_global_barrier() -> None:
    with BoundedRecyclingProcessPool(
        max_workers=2,
        max_tasks_per_worker=1,
    ) as pool:
        slow = pool.submit(_return_after_delay, 0, 3.0)
        fast = pool.submit(_return_after_delay, 1, 0.01)

        # Both original workers are at their lifetime cap. Submission may wait for the fast
        # worker to drain and recycle, but must not wait for the unrelated slow worker.
        replacement = pool.submit(_return_after_delay, 2, 0.0)
        assert not slow.done()
        assert fast.result(timeout=30.0) == 1
        assert replacement.result(timeout=30.0) == 2

    assert slow.result(timeout=30.0) == 0


def test_recycling_process_pool_reports_failure_and_finishes_remaining_generations() -> None:
    workers = 2
    tasks_per_worker = 2
    task_count = workers * tasks_per_worker + 3

    with BoundedRecyclingProcessPool(
        max_workers=workers,
        max_tasks_per_worker=tasks_per_worker,
    ) as pool:
        futures = [pool.submit(_return_identity_or_raise, value) for value in range(task_count)]
        done, not_done = concurrent.futures.wait(futures, timeout=30.0)

    assert not not_done
    successes = [future.result() for index, future in enumerate(futures) if index != 4]
    assert sorted(value for value, _pid in successes) == [0, 1, 2, 3, 5, 6]
    assert isinstance(futures[4].exception(), ValueError)


def test_recycling_process_pool_surfaces_initializer_failure() -> None:
    with BoundedRecyclingProcessPool(
        max_workers=1,
        max_tasks_per_worker=2,
        initializer=_fail_worker_initializer,
    ) as pool:
        future = pool.submit(_return_process_identity, 1)

    with pytest.raises(BrokenProcessPool):
        future.result(timeout=30.0)


def test_recycling_process_pool_recovers_after_native_worker_exit() -> None:
    with BoundedRecyclingProcessPool(
        max_workers=2,
        max_tasks_per_worker=4,
    ) as pool:
        dead_future = pool.submit(_exit_native_worker)
        peer_future = pool.submit(_return_process_identity, 1)
        done, not_done = concurrent.futures.wait((dead_future, peer_future), timeout=30.0)
        assert not not_done
        assert done == {dead_future, peer_future}
        assert isinstance(dead_future.exception(), BrokenProcessPool)

        recovered = pool.submit(_return_process_identity, 2)
        assert recovered.result(timeout=30.0)[0] == 2

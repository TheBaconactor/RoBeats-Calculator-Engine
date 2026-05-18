from __future__ import annotations

from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_lifecycle import SongPrepQueue


def test_song_prep_queue_submit_and_pop_completed_keeps_result_policy_external():
    queue = SongPrepQueue(max_workers=1, prep_fn=lambda logical_task: {"logical": logical_task[1]})
    try:
        task = ("file.rbxl", "Song A")
        logical_task = ("file.rbxl", "Song A", "logical")
        registered = []

        future = queue.submit(task, logical_task, register_future=registered.append)
        assert registered == [future]
        assert len(queue.inflight) == 1
        assert future.result(timeout=2) == {"logical": "Song A"}

        completions = queue.pop_completed()

        assert len(completions) == 1
        assert completions[0].task is task
        assert completions[0].logical_task is logical_task
        assert completions[0].future is future
        assert completions[0].submit_t0 > 0.0
        assert len(queue.inflight) == 0
    finally:
        queue.shutdown(wait=True, cancel_futures=True)


def test_song_prep_queue_cancel_all_cancels_and_clears_inflight_work():
    queue = SongPrepQueue(max_workers=1, prep_fn=lambda logical_task: logical_task)
    try:
        future = Future()
        queue.inflight.append((("file.rbxl", "Song B"), ("file.rbxl", "Song B"), future, 12.0))

        queue.cancel_all()

        assert future.cancelled() is True
        assert len(queue.inflight) == 0
    finally:
        queue.shutdown(wait=True, cancel_futures=True)

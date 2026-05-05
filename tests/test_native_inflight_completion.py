from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_completion import CompletionTracker


def test_completion_tracker_registers_and_waits_for_future_completion():
    tracker = CompletionTracker()
    fut = Future()

    assert tracker.register(fut) is True
    assert tracker.register(fut) is False
    assert tracker.is_set() is False

    fut.set_result("done")

    assert tracker.wait(0.1, short_spin_s=0.0) is True
    assert tracker.is_set() is True

    tracker.clear()
    assert tracker.is_set() is False


def test_completion_tracker_unregister_discards_future_id():
    tracker = CompletionTracker()
    fut = Future()

    assert tracker.register(fut) is True

    tracker.unregister(id(fut))

    assert id(fut) not in tracker.ids

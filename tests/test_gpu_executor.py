import threading
import types

import pytest

from gear_optimizer.gpu import executor as gpu_executor
from gear_optimizer.gpu.executor import GpuExecutor, GpuFatalError, GpuServiceTimeoutError, is_fatal_gpu_error


@pytest.fixture
def gpu(monkeypatch):
    """The executor's GPU init and finalize stubbed: records which thread ran them."""
    seen: dict = {"finalized_on": []}
    monkeypatch.setattr(gpu_executor, "_init_gpu", lambda: seen.setdefault("init_on", threading.current_thread().name))
    monkeypatch.setattr(gpu_executor, "_finalize_gpu", lambda: seen["finalized_on"].append(threading.current_thread().name))
    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", raising=False)
    return seen


def test_calls_run_in_order_on_the_owner_thread_which_finalizes_the_gpu_on_stop(gpu):
    executor = GpuExecutor()
    executor.start()
    try:
        assert [executor.call(lambda i: (i, threading.current_thread().name), i) for i in range(3)] == [
            (i, "GpuExecutorThread") for i in range(3)]
        with pytest.raises(ValueError, match="bad input"):  # the call's own exception
            executor.call(lambda: (_ for _ in ()).throw(ValueError("bad input")))
        assert executor.call(lambda: "next") == "next"
    finally:
        executor.stop()
    assert gpu["init_on"] == "GpuExecutorThread" and gpu["finalized_on"] == ["GpuExecutorThread"]
    assert not executor.is_running


def test_a_failed_gpu_init_is_fatal_and_stops_the_executor(gpu, monkeypatch):
    def init():
        raise RuntimeError("no Vulkan device")

    monkeypatch.setattr(gpu_executor, "_init_gpu", init)
    executor = GpuExecutor()
    executor.start()
    with pytest.raises(GpuFatalError, match="no Vulkan device"):
        executor.call(lambda: "never runs")
    assert not executor.is_running and gpu["finalized_on"] == []


def test_an_abort_stops_the_call_in_progress_and_refuses_queued_calls_until_the_next_start(gpu):
    executor = GpuExecutor()
    executor.start()
    try:
        def ga(abort_requested):
            executor.request_abort("stop requested")
            if abort_requested():
                raise RuntimeError("GpuExecutor aborted: before GPU-native GA generation 3")

        with pytest.raises(RuntimeError, match="GpuExecutor aborted: before GPU-native GA generation 3"):
            executor.call(ga, executor.abort_requested)
        with pytest.raises(RuntimeError, match="GpuExecutor aborted: stop requested"):
            executor.call(lambda: pytest.fail("an aborted executor ran a call"))
    finally:
        executor.stop()
    executor.start()
    try:
        assert executor.call(lambda: "runs again") == "runs again"
    finally:
        executor.stop()


def test_under_the_service_a_stuck_call_is_fatal_and_stops_the_process(gpu, monkeypatch):
    stopped, release = [], threading.Event()
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setattr(gpu_executor, "_CALL_TIMEOUT_S", 0.2)
    monkeypatch.setattr(gpu_executor, "_stop_this_process", stopped.append)

    def stuck():
        release.wait(5)

    executor = GpuExecutor()
    executor.start()
    try:
        with pytest.raises(GpuServiceTimeoutError, match="GPU call stuck timed out after 0.2s"):
            executor.call(stuck)
        assert stopped == ["GPU call stuck timed out after 0.2s"]
    finally:
        release.set()
        executor.stop()


def test_standalone_runs_wait_for_a_slow_call(gpu, monkeypatch):
    monkeypatch.setattr(gpu_executor, "_CALL_TIMEOUT_S", 0.05)
    monkeypatch.setattr(gpu_executor, "_stop_this_process", lambda message: pytest.fail(message))
    executor = GpuExecutor()
    executor.start()
    try:
        assert executor.call(lambda: threading.Event().wait(0.3) or "done") == "done"
    finally:
        executor.stop()


def test_fatal_gpu_errors_are_the_engines_own_or_a_lost_device_anywhere_in_the_chain():
    try:
        try:
            raise RuntimeError("[Vulkan] VK_ERROR_DEVICE_LOST: device lost")
        except RuntimeError as driver_error:
            raise ValueError("GA batch failed") from driver_error
    except ValueError as exc:
        chained = exc
    assert is_fatal_gpu_error(GpuServiceTimeoutError("GPU call _ga_turn timed out after 240.0s"))
    assert is_fatal_gpu_error(chained)
    assert not is_fatal_gpu_error(RuntimeError("GpuExecutor aborted: stop requested"))


def test_starting_the_gpu_starts_the_executor(monkeypatch):
    import sys

    started = []
    # No real GPU: a started executor would keep initializing Taichi after the test, racing later tests' resets.
    monkeypatch.setattr(gpu_executor, "get_gpu_executor", lambda: types.SimpleNamespace(start=lambda: started.append(1)))
    monkeypatch.setattr(sys, "platform", "linux")  # macOS would materialize Taichi here first
    gpu_executor.start_gpu_executor()
    assert started == [1]


def _inputs(num_runs: int = 1):
    return types.SimpleNamespace(num_runs=num_runs, timed_song=None, curves=None)


@pytest.fixture
def ga_calls(monkeypatch):
    """gpu.ga.run_ga around a stubbed GA: its outcomes in order, and the resets between them."""
    from gear_optimizer.gpu import device, ga

    calls = types.SimpleNamespace(outcomes=[], runs=0, resets=[])

    def run(_inputs, _seed, _payload, check):
        calls.runs += 1
        check("in the test")
        outcome = calls.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(ga, "_run_ga", run)
    monkeypatch.setattr(device, "hard_reset", calls.resets.append)
    monkeypatch.setattr(ga, "build_or_load_timeline_frontier_payload", lambda _song, _curves: types.SimpleNamespace(payload=None))
    return calls


def test_a_vulkan_semaphore_failure_restarts_the_ga_on_a_fresh_runtime(ga_calls):
    from gear_optimizer.gpu.ga import run_ga

    ga_calls.outcomes = [RuntimeError("RHI Error: failed to create semaphore"), "table"]
    assert run_ga(_inputs(), 1, lambda: False) == "table"
    assert ga_calls.runs == 2 and len(ga_calls.resets) == 1


def test_a_second_vulkan_failure_and_any_other_failure_reach_the_caller(ga_calls):
    from gear_optimizer.gpu.ga import run_ga

    failure = RuntimeError("failed to create semaphore")
    ga_calls.outcomes = [failure, failure]
    with pytest.raises(RuntimeError, match="semaphore"):
        run_ga(_inputs(), 1, lambda: False)
    ga_calls.outcomes = [ValueError("no")]
    with pytest.raises(ValueError, match="no"):
        run_ga(_inputs(), 1, lambda: False)
    assert len(ga_calls.resets) == 1


def test_an_abort_stops_the_ga(ga_calls):
    from gear_optimizer.gpu.executor import is_stop_abort_exception
    from gear_optimizer.gpu.ga import run_ga

    with pytest.raises(RuntimeError) as failure:
        run_ga(_inputs(), 1, lambda: True)
    assert is_stop_abort_exception(failure.value)


def test_a_song_past_the_ga_capacity_is_refused(ga_calls):
    from gear_optimizer.gpu.fields import MAX_GA_RUNS
    from gear_optimizer.gpu.ga import run_ga

    with pytest.raises(ValueError, match="runs"):
        run_ga(_inputs(MAX_GA_RUNS + 1), 1, lambda: False)
    assert ga_calls.runs == 0

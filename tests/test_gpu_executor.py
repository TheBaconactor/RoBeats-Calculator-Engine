import threading

import pytest

from gear_optimizer.solver import gpu_executor
from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuFatalError, GpuServiceTimeoutError, is_fatal_gpu_error


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

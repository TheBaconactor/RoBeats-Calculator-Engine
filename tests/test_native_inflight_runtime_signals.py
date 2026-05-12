from __future__ import annotations

import concurrent.futures

from gear_optimizer.solver.native_inflight_runtime_signals import (
    CachedRuntimeSignal,
    GpuAbortRequester,
    is_stop_abort_exception,
)


def test_cached_runtime_signal_throttles_false_checks_until_poll_interval():
    calls = {"count": 0}

    def _callback() -> bool:
        calls["count"] += 1
        return False

    signal = CachedRuntimeSignal(_callback, poll_interval_s=0.5)

    assert signal.requested(10.0) is False
    assert signal.requested(10.25) is False
    assert calls["count"] == 1

    assert signal.requested(10.5) is False
    assert calls["count"] == 2


def test_cached_runtime_signal_latches_true_without_rechecking_callback():
    calls = {"count": 0}

    def _callback() -> bool:
        calls["count"] += 1
        return True

    signal = CachedRuntimeSignal(_callback, poll_interval_s=0.5)

    assert signal.requested(1.0) is True
    assert signal.requested(1.1) is True
    assert calls["count"] == 1


def test_cached_runtime_signal_disabled_without_callable_callback():
    assert CachedRuntimeSignal(None).requested(1.0) is False
    assert CachedRuntimeSignal("not-callable").requested(1.0) is False


def test_gpu_abort_requester_requests_executor_abort_once():
    class _Executor:
        def __init__(self):
            self.reasons = []

        def request_abort(self, reason: str) -> None:
            self.reasons.append(reason)

    executor = _Executor()
    requester = GpuAbortRequester(executor)

    assert requester.request(" hotkey stop ") is True
    assert requester.request("second") is False
    assert executor.reasons == [" hotkey stop "]


def test_gpu_abort_requester_normalizes_empty_reason_to_stop_requested():
    class _Executor:
        def __init__(self):
            self.reasons = []

        def request_abort(self, reason: str) -> None:
            self.reasons.append(reason)

    executor = _Executor()
    assert GpuAbortRequester(executor).request("") is True
    assert executor.reasons == ["stop requested"]


def test_is_stop_abort_exception_matches_cancelled_and_gpu_abort_errors():
    assert is_stop_abort_exception(concurrent.futures.CancelledError()) is True
    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False

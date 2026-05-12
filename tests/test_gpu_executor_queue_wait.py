import queue

import pytest

from gear_optimizer.solver.gpu_executor_queue_wait import (
    get_with_short_wait_spin,
    load_short_wait_spin_settings,
    poll_inprocess_followup_nowait,
    safe_qsize,
)


class _RecordingQueue:
    def __init__(self, *, get_result="item", nowait_result=None, nowait_empty: bool = False) -> None:
        self.get_result = get_result
        self.nowait_result = nowait_result
        self.nowait_empty = nowait_empty
        self.get_timeouts: list[float] = []
        self.nowait_calls = 0

    def get(self, timeout=None):
        self.get_timeouts.append(float(timeout))
        if self.get_result is queue.Empty:
            raise queue.Empty()
        return self.get_result

    def get_nowait(self):
        self.nowait_calls += 1
        if self.nowait_empty:
            raise queue.Empty()
        return self.nowait_result


class _NoNowaitQueue:
    pass


class _QsizeQueue:
    def __init__(self, value):
        self.value = value

    def qsize(self):
        if isinstance(self.value, type) and issubclass(self.value, BaseException):
            raise self.value()
        return self.value


def test_safe_qsize_normalizes_missing_invalid_and_negative_sizes():
    assert safe_qsize(None) == -1
    assert safe_qsize(_NoNowaitQueue()) == -1
    assert safe_qsize(_QsizeQueue(NotImplementedError)) == -1
    assert safe_qsize(_QsizeQueue(OSError)) == -1
    assert safe_qsize(_QsizeQueue("bad")) == -1
    assert safe_qsize(_QsizeQueue(-5)) == 0
    assert safe_qsize(_QsizeQueue("7")) == 7


def test_load_short_wait_spin_settings_reads_env_values():
    values = {
        "GPU_EXECUTOR_SHORT_WAIT_SPIN_MS": "12.5",
        "GPU_EXECUTOR_SHORT_WAIT_SPIN_YIELD_ROUNDS": "17",
    }

    settings = load_short_wait_spin_settings(env_get_fn=lambda key, default: values.get(key, default))

    assert settings.short_wait_spin_sec == 0.0125
    assert settings.short_wait_spin_yield_rounds == 17


def test_load_short_wait_spin_settings_clamps_invalid_values():
    values = {
        "GPU_EXECUTOR_SHORT_WAIT_SPIN_MS": "-5",
        "GPU_EXECUTOR_SHORT_WAIT_SPIN_YIELD_ROUNDS": "999999",
    }

    settings = load_short_wait_spin_settings(env_get_fn=lambda key, default: values.get(key, default))
    invalid = load_short_wait_spin_settings(env_get_fn=lambda _key, _default: "bad")

    assert settings.short_wait_spin_sec == 0.0
    assert settings.short_wait_spin_yield_rounds == 100_000
    assert invalid.short_wait_spin_sec == 0.003
    assert invalid.short_wait_spin_yield_rounds == 8


def test_get_with_short_wait_spin_uses_blocking_get_for_non_inprocess_queue():
    request_queue = _RecordingQueue(get_result="blocked")

    result = get_with_short_wait_spin(
        request_queue,
        timeout=0.25,
        in_process_queues=False,
        short_wait_spin_sec=1.0,
        short_wait_spin_yield_rounds=8,
    )

    assert result == "blocked"
    assert request_queue.nowait_calls == 0
    assert request_queue.get_timeouts == [0.25]


def test_get_with_short_wait_spin_uses_nowait_for_short_inprocess_wait():
    request_queue = _RecordingQueue(nowait_result="nowait")

    result = get_with_short_wait_spin(
        request_queue,
        timeout=0.01,
        in_process_queues=True,
        short_wait_spin_sec=0.05,
        short_wait_spin_yield_rounds=8,
    )

    assert result == "nowait"
    assert request_queue.nowait_calls == 1
    assert request_queue.get_timeouts == []


def test_get_with_short_wait_spin_blocks_in_one_ms_chunks_after_yields():
    request_queue = _RecordingQueue(get_result="chunk", nowait_empty=True)
    times = iter([0.0, 0.002])
    sleeps: list[float] = []

    result = get_with_short_wait_spin(
        request_queue,
        timeout=0.01,
        in_process_queues=True,
        short_wait_spin_sec=0.05,
        short_wait_spin_yield_rounds=0,
        perf_counter_fn=lambda: next(times),
        sleep_fn=sleeps.append,
    )

    assert result == "chunk"
    assert request_queue.nowait_calls == 1
    assert request_queue.get_timeouts == [0.001]
    assert sleeps == []


def test_get_with_short_wait_spin_raises_empty_after_deadline():
    request_queue = _RecordingQueue(get_result=queue.Empty, nowait_empty=True)
    times = iter([0.0, 0.02])

    with pytest.raises(queue.Empty):
        get_with_short_wait_spin(
            request_queue,
            timeout=0.01,
            in_process_queues=True,
            short_wait_spin_sec=0.05,
            short_wait_spin_yield_rounds=0,
            perf_counter_fn=lambda: next(times),
            sleep_fn=lambda _seconds: None,
        )

    assert request_queue.nowait_calls == 1
    assert request_queue.get_timeouts == []


def test_poll_inprocess_followup_nowait_falls_back_without_nowait():
    poll = poll_inprocess_followup_nowait(
        _NoNowaitQueue(),
        deadline_s=1.0,
        yields_left=3,
        stamp_fn=lambda item: item,
    )

    assert poll.action == "fallback"
    assert poll.request is None
    assert poll.yields_left == 3


def test_poll_inprocess_followup_nowait_returns_stamped_request():
    request_queue = _RecordingQueue(nowait_result={"id": 1})

    poll = poll_inprocess_followup_nowait(
        request_queue,
        deadline_s=1.0,
        yields_left=3,
        stamp_fn=lambda item: dict(item, stamped=True),
    )

    assert poll.action == "request"
    assert poll.request == {"id": 1, "stamped": True}
    assert poll.yields_left == 3
    assert request_queue.nowait_calls == 1


def test_poll_inprocess_followup_nowait_yields_before_deadline():
    request_queue = _RecordingQueue(nowait_empty=True)
    sleeps: list[float] = []

    poll = poll_inprocess_followup_nowait(
        request_queue,
        deadline_s=10.0,
        yields_left=2,
        stamp_fn=lambda item: item,
        perf_counter_fn=lambda: 9.0,
        sleep_fn=sleeps.append,
    )

    assert poll.action == "continue"
    assert poll.request is None
    assert poll.yields_left == 1
    assert sleeps == [0]


def test_poll_inprocess_followup_nowait_breaks_after_deadline():
    request_queue = _RecordingQueue(nowait_empty=True)

    poll = poll_inprocess_followup_nowait(
        request_queue,
        deadline_s=10.0,
        yields_left=2,
        stamp_fn=lambda item: item,
        perf_counter_fn=lambda: 11.0,
        sleep_fn=lambda _seconds: None,
    )

    assert poll.action == "break"
    assert poll.request is None
    assert poll.yields_left == 2

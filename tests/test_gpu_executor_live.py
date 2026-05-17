import logging

from gear_optimizer.solver.gpu_executor_lifecycle import LiveReporter
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def test_live_reporter_records_and_reports_after_interval(caplog):
    times = iter([0.0, 0.5, 1.1])
    reporter = LiveReporter(now=lambda: next(times))
    reporter.configure(enabled=True, interval_sec=1.0)

    reporter.record_wait(0.25)
    reporter.record_exec(GpuRequestType.GPU_NATIVE_GA_RUN, exec_sec=0.75, count=2)

    with caplog.at_level(logging.DEBUG, logger="gear_optimizer.solver.gpu_executor_lifecycle"):
        assert reporter.maybe_report() is False
        assert reporter.maybe_report() is False
        assert reporter.maybe_report() is True

    assert "[GpuExecutor][LIVE] busy=75.0%" in caplog.text
    assert "gpu_native_ga_run:2" in caplog.text
    assert reporter.wait_sec == 0.0
    assert reporter.exec_sec == 0.0
    assert dict(reporter.type_counts) == {}


def test_live_reporter_ignores_records_when_disabled():
    reporter = LiveReporter(now=lambda: 0.0)
    reporter.configure(enabled=False, interval_sec=1.0)

    reporter.record_wait(1.0)
    reporter.record_exec(GpuRequestType.LOAD_REF_ARRAYS, exec_sec=1.0, count=1)

    assert reporter.maybe_report() is False
    assert reporter.wait_sec == 0.0
    assert reporter.exec_sec == 0.0
    assert dict(reporter.type_counts) == {}

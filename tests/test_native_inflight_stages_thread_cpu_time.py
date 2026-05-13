from __future__ import annotations


def test_native_inflight_timing_exposes_thread_cpu_time_helper() -> None:
    import gear_optimizer.solver.native_inflight_timing as timing
    import gear_optimizer.solver.native_inflight_stages as stages

    assert callable(getattr(timing, "thread_cpu_time_s", None))
    assert not hasattr(stages, "_thread_cpu_time_s")
    value = timing.thread_cpu_time_s()
    assert isinstance(value, float)
    assert value >= 0.0

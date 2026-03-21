from __future__ import annotations


def test_native_inflight_stages_exposes_thread_cpu_time_helper() -> None:
    import gear_optimizer.solver.native_inflight_stages as stages

    assert callable(getattr(stages, "_thread_cpu_time_s", None))
    value = stages._thread_cpu_time_s()
    assert isinstance(value, float)
    assert value >= 0.0


import configparser

import gear_optimizer.solver.native_inflight_orchestrator as native_orch
from gear_optimizer.solver.native_inflight_orchestrator import (
    _closed_loop_bubble_kpi,
    _continuous_fg_submit_budget,
    _continuous_fg_should_start,
    _continuous_ga_warm_queue_limit,
    _default_prime_target,
    _read_continuous_fg_adaptive_submit,
    _read_continuous_ga_dispatch_burst,
    _read_fg_ga_credit_budget,
    _read_fg_scheduler_mode,
    _read_fg_slot_reserve,
    _read_inflight_event_wait_gpu_cap_s,
    _read_inflight_event_wait_short_spin_s,
    _read_inflight_event_wait_timeout_s,
    _wait_for_completion_event,
)


def _cfg_with_iteration_engine(**pairs: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {k: str(v) for k, v in pairs.items()}
    return cfg


def test_read_fg_scheduler_mode_defaults_to_continuous(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_SCHEDULER", raising=False)
    assert _read_fg_scheduler_mode() == "continuous"


def test_read_fg_scheduler_mode_is_fixed_to_continuous(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FG_SCHEDULER", "backlog")
    assert _read_fg_scheduler_mode() == "continuous"


def test_read_fg_ga_credit_budget_default_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_GA_CREDIT_BUDGET", raising=False)
    monkeypatch.delenv("INFLIGHT_GA_CREDIT_BUDGET", raising=False)

    cfg = _cfg_with_iteration_engine()
    budget, explicit = _read_fg_ga_credit_budget(cfg, default_budget=24)
    assert budget == 24
    assert explicit is False

    monkeypatch.setenv("INFLIGHT_GA_CREDIT_BUDGET", "88")
    budget, explicit = _read_fg_ga_credit_budget(cfg, default_budget=24)
    assert budget == 24
    assert explicit is False

    cfg_cfg = _cfg_with_iteration_engine(InFlight_FGGACreditBudget="77")
    budget, explicit = _read_fg_ga_credit_budget(cfg_cfg, default_budget=24)
    assert budget == 77
    assert explicit is True

    monkeypatch.setenv("INFLIGHT_FG_GA_CREDIT_BUDGET", "91")
    budget, explicit = _read_fg_ga_credit_budget(cfg_cfg, default_budget=24)
    assert budget == 91
    assert explicit is True


def test_continuous_fg_should_start_on_credit_or_aging_or_slot_pressure():
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=0,
            ga_credit=0,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=0,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=0,
            ga_credit=9,
            oldest_wait_s=3.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=0,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )
    assert (
        _continuous_fg_should_start(
            pending_fg_count=1,
            ready_fg_count=0,
            ga_credit=9,
            oldest_wait_s=0.0,
            blocked_on_slot=True,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=0,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )


def test_continuous_fg_should_not_start_without_pending_or_drain_disabled():
    assert (
        _continuous_fg_should_start(
            pending_fg_count=0,
            ready_fg_count=0,
            ga_credit=0,
            oldest_wait_s=10.0,
            blocked_on_slot=True,
            no_ga_remaining=True,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=0,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is False
    )


def test_continuous_fg_should_start_when_reserved_capacity_has_ready_fg():
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=1,
            ga_credit=9,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=4,
            ga_queue_limit=4,
            fg_slot_reserve=1,
        )
        is True
    )


def test_continuous_fg_submit_budget_respects_reserved_capacity_ready_fg():
    budget = _continuous_fg_submit_budget(
        pending_fg_count=3,
        ready_fg_count=1,
        fg_inflight_count=0,
        fg_workers=2,
        fg_batch_max=2,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_inflight_count=4,
        ga_queue_limit=4,
        adaptive_submit=False,
        adaptive_max_burst=3,
        fg_slot_reserve=1,
    )
    assert budget == 1


def test_read_continuous_ga_dispatch_burst_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("INFLIGHT_CONTINUOUS_GA_BURST", raising=False)
    cfg = _cfg_with_iteration_engine()
    assert _read_continuous_ga_dispatch_burst(cfg, default_burst=2) == 2

    cfg2 = _cfg_with_iteration_engine(InFlight_ContinuousGABurst="5")
    assert _read_continuous_ga_dispatch_burst(cfg2, default_burst=2) == 5

    monkeypatch.setenv("INFLIGHT_CONTINUOUS_GA_BURST", "7")
    assert _read_continuous_ga_dispatch_burst(cfg2, default_burst=2) == 7


def test_read_continuous_fg_adaptive_submit_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_ADAPTIVE_SUBMIT", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_ADAPTIVE_MAX_BURST", raising=False)

    cfg = _cfg_with_iteration_engine()
    enabled, max_burst = _read_continuous_fg_adaptive_submit(cfg)
    assert enabled is True
    assert max_burst == 3

    cfg2 = _cfg_with_iteration_engine(InFlight_FGAdaptiveSubmit="false", InFlight_FGAdaptiveMaxBurst="6")
    enabled, max_burst = _read_continuous_fg_adaptive_submit(cfg2)
    assert enabled is False
    assert max_burst == 6

    monkeypatch.setenv("INFLIGHT_FG_ADAPTIVE_SUBMIT", "1")
    monkeypatch.setenv("INFLIGHT_FG_ADAPTIVE_MAX_BURST", "4")
    enabled, max_burst = _read_continuous_fg_adaptive_submit(cfg2)
    assert enabled is True
    assert max_burst == 4


def test_read_fg_slot_reserve_ratio_and_absolute_override(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_SLOT_RESERVE", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_SLOT_RESERVE_RATIO", raising=False)

    cfg_ratio = _cfg_with_iteration_engine(InFlight_FGSlotReserveRatio="0.2")
    reserve = _read_fg_slot_reserve(cfg_ratio, fg_enabled=True, inflight_limit=12, song_slot_limit=23)
    assert reserve == 5

    cfg_abs = _cfg_with_iteration_engine(InFlight_FGSlotReserve="2")
    reserve = _read_fg_slot_reserve(cfg_abs, fg_enabled=True, inflight_limit=12, song_slot_limit=23)
    assert reserve == 2

    monkeypatch.setenv("INFLIGHT_FG_SLOT_RESERVE", "0")
    reserve = _read_fg_slot_reserve(cfg_abs, fg_enabled=True, inflight_limit=12, song_slot_limit=23)
    assert reserve == 0


def test_continuous_ga_warm_queue_limit_caps_cold_start_backlog():
    limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=True,
        prepared_count=4,
        prep_inflight_count=2,
        decode_inflight_count=0,
        pending_fg_count=0,
        fg_prep_inflight_count=0,
        fg_inflight_count=0,
    )
    assert limit == 4


def test_continuous_ga_warm_queue_limit_restores_full_limit_once_fg_pipeline_starts():
    limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=True,
        prepared_count=4,
        prep_inflight_count=2,
        decode_inflight_count=1,
        pending_fg_count=0,
        fg_prep_inflight_count=0,
        fg_inflight_count=0,
    )
    assert limit == 12


def test_continuous_ga_warm_queue_limit_skips_cap_when_fg_disabled_or_staging_shallow():
    disabled_limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=False,
        prepared_count=4,
        prep_inflight_count=2,
        decode_inflight_count=0,
        pending_fg_count=0,
        fg_prep_inflight_count=0,
        fg_inflight_count=0,
    )
    assert disabled_limit == 12

    shallow_limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=True,
        prepared_count=1,
        prep_inflight_count=1,
        decode_inflight_count=0,
        pending_fg_count=0,
        fg_prep_inflight_count=0,
        fg_inflight_count=0,
    )
    assert shallow_limit == 12


def test_continuous_fg_submit_budget_adaptive_behavior():
    control_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
        ready_fg_count=0,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_inflight_count=1,
        ga_queue_limit=12,
        adaptive_submit=False,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert control_budget == 1

    adaptive_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
        ready_fg_count=0,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_inflight_count=1,
        ga_queue_limit=12,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert adaptive_budget == 3


def test_continuous_fg_submit_budget_honors_end_of_run_drain():
    budget = _continuous_fg_submit_budget(
        pending_fg_count=5,
        ready_fg_count=0,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=True,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_inflight_count=0,
        ga_queue_limit=12,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert budget == 4


def test_default_prime_target_scales_small_inflight_runs_without_exceeding_buffers():
    assert _default_prime_target(inflight_limit=1, prep_limit=4, pending_count=20) == 4
    assert _default_prime_target(inflight_limit=2, prep_limit=8, pending_count=20) == 4
    assert _default_prime_target(inflight_limit=4, prep_limit=16, pending_count=20) == 8
    assert _default_prime_target(inflight_limit=8, prep_limit=32, pending_count=20) == 8


def test_default_prime_target_clamps_to_pending_and_prep_limits():
    assert _default_prime_target(inflight_limit=4, prep_limit=6, pending_count=20) == 6
    assert _default_prime_target(inflight_limit=4, prep_limit=16, pending_count=3) == 3
    assert _default_prime_target(inflight_limit=4, prep_limit=16, pending_count=0) == 0

    budget_no_drain = _continuous_fg_submit_budget(
        pending_fg_count=5,
        ready_fg_count=0,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=True,
        fg_drain_at_end=False,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_inflight_count=0,
        ga_queue_limit=12,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert budget_no_drain == 0
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=0,
            ga_credit=5,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=True,
            fg_drain_at_end=False,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_inflight_count=0,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is False
    )


def test_read_inflight_event_wait_settings_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC", raising=False)
    monkeypatch.delenv("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS", raising=False)

    assert abs(_read_inflight_event_wait_timeout_s() - 0.05) < 1e-9
    assert abs(_read_inflight_event_wait_gpu_cap_s() - 0.01) < 1e-9
    assert abs(_read_inflight_event_wait_short_spin_s() - 0.003) < 1e-9

    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC", "9.0")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC", "-1")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS", "100")

    assert abs(_read_inflight_event_wait_timeout_s() - 5.0) < 1e-9
    assert abs(_read_inflight_event_wait_gpu_cap_s() - 0.0) < 1e-9
    assert abs(_read_inflight_event_wait_short_spin_s() - 0.05) < 1e-9


def test_wait_for_completion_event_short_timeout_uses_zero_timeout_poll(monkeypatch):
    class _RecordingEvent:
        def __init__(self):
            self.waits: list[float] = []

        def wait(self, timeout=None):
            self.waits.append(float(timeout))
            return False

    event = _RecordingEvent()
    perf_values = iter((0.0000, 0.0000, 0.0040))

    def _fake_perf_counter():
        try:
            return next(perf_values)
        except StopIteration:
            return 0.0040

    monkeypatch.setattr(native_orch.time, "perf_counter", _fake_perf_counter)
    monkeypatch.setattr(native_orch.time, "sleep", lambda _t: None)

    done = _wait_for_completion_event(event, timeout_s=0.003, short_spin_s=0.005)
    assert done is False
    assert event.waits
    assert all(abs(w - 0.0) < 1e-12 for w in event.waits)


def test_wait_for_completion_event_long_timeout_uses_direct_wait():
    class _RecordingEvent:
        def __init__(self):
            self.waits: list[float] = []

        def wait(self, timeout=None):
            self.waits.append(float(timeout))
            return False

    event = _RecordingEvent()
    done = _wait_for_completion_event(event, timeout_s=0.02, short_spin_s=0.003)
    assert done is False
    assert event.waits == [0.02]


def test_closed_loop_bubble_kpi_increases_with_ready_work_and_fg_wait():
    quiet = _closed_loop_bubble_kpi(
        idle_sec=0.5,
        ready_ga_count=1,
        ready_fg_count=0,
        backlog_count=2,
        oldest_fg_wait_s=0.0,
    )
    pressured = _closed_loop_bubble_kpi(
        idle_sec=0.5,
        ready_ga_count=2,
        ready_fg_count=1,
        backlog_count=6,
        oldest_fg_wait_s=2.0,
    )

    assert quiet > 0.0
    assert pressured > quiet

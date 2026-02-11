import configparser

from gear_optimizer.solver.native_inflight_orchestrator import (
    _continuous_fg_submit_budget,
    _continuous_fg_should_start,
    _read_continuous_fg_adaptive_submit,
    _read_continuous_ga_dispatch_burst,
    _read_fg_ga_credit_budget,
    _read_fg_scheduler_mode,
    _read_fg_slot_reserve,
)


def _cfg_with_iteration_engine(**pairs: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {k: str(v) for k, v in pairs.items()}
    return cfg


def test_read_fg_scheduler_mode_defaults_to_continuous(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_SCHEDULER", raising=False)
    cfg = _cfg_with_iteration_engine()
    assert _read_fg_scheduler_mode(cfg) == "continuous"


def test_read_fg_scheduler_mode_accepts_backlog_aliases(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_SCHEDULER", raising=False)
    cfg = _cfg_with_iteration_engine(InFlight_FGScheduler="drain")
    assert _read_fg_scheduler_mode(cfg) == "backlog"


def test_read_fg_ga_credit_budget_default_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_GA_CREDIT_BUDGET", raising=False)
    monkeypatch.delenv("INFLIGHT_GA_CREDIT_BUDGET", raising=False)

    cfg = _cfg_with_iteration_engine()
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
            ga_credit=0,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is True
    )
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ga_credit=9,
            oldest_wait_s=3.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is True
    )
    assert (
        _continuous_fg_should_start(
            pending_fg_count=1,
            ga_credit=9,
            oldest_wait_s=0.0,
            blocked_on_slot=True,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is True
    )


def test_continuous_fg_should_not_start_without_pending_or_drain_disabled():
    assert (
        _continuous_fg_should_start(
            pending_fg_count=0,
            ga_credit=0,
            oldest_wait_s=10.0,
            blocked_on_slot=True,
            no_ga_remaining=True,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is False
    )


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


def test_continuous_fg_submit_budget_adaptive_behavior():
    legacy_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
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
    )
    assert legacy_budget == 1

    adaptive_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
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
    )
    assert adaptive_budget == 3


def test_continuous_fg_submit_budget_honors_end_of_run_drain():
    budget = _continuous_fg_submit_budget(
        pending_fg_count=5,
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
    )
    assert budget == 4

    budget_no_drain = _continuous_fg_submit_budget(
        pending_fg_count=5,
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
    )
    assert budget_no_drain == 0
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ga_credit=5,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=True,
            fg_drain_at_end=False,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is False
    )

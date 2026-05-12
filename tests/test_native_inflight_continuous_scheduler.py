import configparser

import gear_optimizer.solver.native_inflight_orchestrator as native_orch
from gear_optimizer.solver.native_inflight_orchestrator import (
    _closed_loop_bubble_kpi,
    _continuous_fg_allow_not_ready,
    _continuous_ga_should_yield_to_fg,
    _continuous_fg_should_fill_song_lanes,
    _continuous_fg_submit_budget,
    _continuous_fg_should_start,
    _continuous_ga_warm_queue_limit,
    _default_prime_target,
    _read_fg_static_prep_max_inflight,
    _read_inflight_event_wait_gpu_cap_s,
    _read_inflight_event_wait_short_spin_s,
    _read_inflight_event_wait_timeout_s,
    _wait_for_completion_event,
)
from gear_optimizer.solver.native_inflight_scheduler import (
    GAQueueLimitController,
    count_active_song_lanes,
    _read_continuous_fg_adaptive_submit,
    _read_continuous_ga_dispatch_burst,
    _read_fg_ga_credit_budget,
    _read_fg_scheduler_mode,
    _read_fg_slot_reserve,
    _read_inflight_target_song_lanes,
    _read_prime_target,
)
from gear_optimizer.solver.native_inflight_config import (
    _read_cpu_prewarm_lookahead,
    _read_cpu_prewarm_workers,
    _read_db_prefetch_workers,
    _read_inflight_worker_count,
    first_task_config,
    inflight_shutdown_debug_enabled,
    inflight_stall_debug_enabled,
    read_inflight_loop_observer_settings,
    read_inflight_runtime_settings,
)
from gear_optimizer.solver.inflight_wait import read_inflight_event_wait_timeout_s
from gear_optimizer.solver.native_inflight_types import make_native_song


def _cfg_with_iteration_engine(**pairs: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {k: str(v) for k, v in pairs.items()}
    return cfg


def test_ga_queue_limit_controller_reserves_slots_and_applies_slot_pressure_window():
    now_box = {"now": 10.0}
    controller = GAQueueLimitController(
        dynamic_enabled=True,
        base_limit=12,
        pressure_window_s=2.0,
        extra_free_on_slot_pressure=2,
        fg_slot_reserve=1,
        song_slot_limit=5,
        monotonic=lambda: float(now_box["now"]),
    )

    assert controller.effective_limit(last_slot_block_t=None) == 4
    assert controller.effective_limit(last_slot_block_t=9.0) == 2

    now_box["now"] = 12.5
    assert controller.effective_limit(last_slot_block_t=9.0) == 4


def test_ga_queue_limit_controller_disabled_returns_base_limit():
    controller = GAQueueLimitController(
        dynamic_enabled=False,
        base_limit=12,
        pressure_window_s=2.0,
        extra_free_on_slot_pressure=2,
        fg_slot_reserve=4,
        song_slot_limit=5,
    )

    assert controller.effective_limit(last_slot_block_t=0.0) == 12


def test_count_active_song_lanes_deduplicates_ga_decode_and_fg_keys():
    ga_song = make_native_song(task_key="song-a", song_name="Song A")
    decode_song = make_native_song(task_key="song-a", song_name="Song A")
    other_decode = make_native_song(task_key="", song_name="Song B")

    assert (
        count_active_song_lanes(
            ga_inflight=[ga_song],
            decode_inflight=[decode_song, other_decode],
            fg_active_keys={"Song B", "song-c", ""},
        )
        == 3
    )


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


def test_continuous_fg_should_start_on_ready_fg_or_slot_pressure():
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=1,
            ga_credit=0,
            oldest_wait_s=0.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )
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
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )
    assert (
        _continuous_fg_should_start(
            pending_fg_count=3,
            ready_fg_count=1,
            ga_credit=9,
            oldest_wait_s=3.0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
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
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is True
    )


def test_continuous_fg_should_probe_pending_fg_while_ga_can_continue():
    base = {
        "pending_fg_count": 3,
        "ready_fg_count": 0,
        "blocked_on_slot": False,
        "no_ga_remaining": False,
        "fg_drain_at_end": True,
        "aging_trigger_s": 0.75,
        "aging_hard_s": 2.5,
        "ga_queue_limit": 12,
        "fg_slot_reserve": 0,
    }

    assert _continuous_fg_should_start(**base, ga_credit=0, oldest_wait_s=0.0) is True
    assert _continuous_fg_should_start(**base, ga_credit=9, oldest_wait_s=3.0) is True


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
            ga_queue_limit=12,
            fg_slot_reserve=0,
        )
        is False
    )


def test_continuous_fg_allows_unready_jobs_only_for_drain_or_slot_pressure():
    assert (
        _continuous_fg_allow_not_ready(
            blocked_on_slot=False,
            no_ga_remaining=True,
            fg_drain_at_end=True,
        )
        is True
    )
    assert (
        _continuous_fg_allow_not_ready(
            blocked_on_slot=True,
            no_ga_remaining=False,
            fg_drain_at_end=True,
        )
        is True
    )
    assert (
        _continuous_fg_allow_not_ready(
            blocked_on_slot=False,
            no_ga_remaining=True,
            fg_drain_at_end=False,
        )
        is False
    )
    assert (
        _continuous_fg_allow_not_ready(
            blocked_on_slot=False,
            no_ga_remaining=False,
            fg_drain_at_end=True,
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


def test_read_cpu_prewarm_lookahead_defaults_to_five_and_honors_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_CPU_PREWARM_LOOKAHEAD", raising=False)

    cfg = _cfg_with_iteration_engine()
    assert _read_cpu_prewarm_lookahead(cfg, prep_limit=12) == 5
    assert _read_cpu_prewarm_lookahead(cfg, prep_limit=3) == 3

    cfg_explicit = _cfg_with_iteration_engine(InFlight_CPUPrewarmLookahead="7")
    assert _read_cpu_prewarm_lookahead(cfg_explicit, prep_limit=12) == 7

    monkeypatch.setenv("INFLIGHT_CPU_PREWARM_LOOKAHEAD", "2")
    assert _read_cpu_prewarm_lookahead(cfg_explicit, prep_limit=12) == 2


def test_first_task_config_extracts_legacy_task_config():
    task = (None, "Song", "Hard", {"IterationEngine": {"InFlight_PrimeTarget": "6"}})
    cfg = first_task_config([task])

    assert cfg is not None
    assert cfg.get("IterationEngine", "InFlight_PrimeTarget") == "6"
    assert first_task_config([]) is None


def test_read_inflight_worker_count_honors_config_env_and_ga_seed(monkeypatch):
    monkeypatch.delenv("INFLIGHT_PREP_WORKERS", raising=False)
    cfg = _cfg_with_iteration_engine(InFlight_PrepWorkers="3")

    assert (
        _read_inflight_worker_count(
            cfg,
            config_key="InFlight_PrepWorkers",
            env_key="INFLIGHT_PREP_WORKERS",
            inflight_limit=8,
            kind="prep",
        )
        == 3
    )

    monkeypatch.setenv("INFLIGHT_PREP_WORKERS", "5")
    assert (
        _read_inflight_worker_count(
            cfg,
            config_key="InFlight_PrepWorkers",
            env_key="INFLIGHT_PREP_WORKERS",
            inflight_limit=8,
            kind="prep",
        )
        == 5
    )

    monkeypatch.setenv("INFLIGHT_PREP_WORKERS", "0")
    assert (
        _read_inflight_worker_count(
            _cfg_with_iteration_engine(),
            config_key="InFlight_PrepWorkers",
            env_key="INFLIGHT_PREP_WORKERS",
            inflight_limit=8,
            kind="prep",
            ga_seed="fixed",
        )
        == 1
    )


def test_read_cpu_prewarm_workers_respects_lookahead_and_env(monkeypatch):
    monkeypatch.delenv("INFLIGHT_CPU_PREWARM_WORKERS", raising=False)

    assert _read_cpu_prewarm_workers(_cfg_with_iteration_engine(), inflight_limit=8, cpu_prewarm_lookahead=0) == 0

    cfg = _cfg_with_iteration_engine(InFlight_CPUPrewarmWorkers="6")
    assert _read_cpu_prewarm_workers(cfg, inflight_limit=8, cpu_prewarm_lookahead=3) == 3

    monkeypatch.setenv("INFLIGHT_CPU_PREWARM_WORKERS", "4")
    assert _read_cpu_prewarm_workers(cfg, inflight_limit=8, cpu_prewarm_lookahead=8) == 4


def test_read_db_prefetch_workers_defaults_from_fg_prep_and_honors_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_DB_PREFETCH_WORKERS", raising=False)

    assert _read_db_prefetch_workers(_cfg_with_iteration_engine(), fg_prep_workers=2) == 2
    assert _read_db_prefetch_workers(_cfg_with_iteration_engine(), fg_prep_workers=9) == 4

    cfg = _cfg_with_iteration_engine(InFlight_DBPrefetchWorkers="6")
    assert _read_db_prefetch_workers(cfg, fg_prep_workers=2) == 6

    monkeypatch.setenv("INFLIGHT_DB_PREFETCH_WORKERS", "7")
    assert _read_db_prefetch_workers(cfg, fg_prep_workers=2) == 7


def test_read_inflight_loop_observer_settings_reads_env_values():
    values = {
        "INFLIGHT_HEARTBEAT_SEC": "1.5",
        "INFLIGHT_THROUGHPUT_SEC": "2.5",
        "INFLIGHT_STAGE_PROFILE_EMIT_SEC": "3.5",
        "INFLIGHT_PROFILE_MAX_SONGS": "4",
    }

    settings = read_inflight_loop_observer_settings(env_get_fn=lambda name, default=None: values.get(name, default))

    assert settings.heartbeat_sec == 1.5
    assert settings.throughput_sec == 2.5
    assert settings.stage_profile_emit_sec == 3.5
    assert settings.profile_max_songs == 4


def test_read_inflight_runtime_settings_reads_static_runtime_env_values():
    values = {
        "GPU_EXECUTOR_INIT_TIMEOUT_SEC": "42.5",
        "INFLIGHT_GA_QUEUE_DEBUG": "1",
    }

    settings = read_inflight_runtime_settings(env_get_fn=lambda name, default=None: values.get(name, default))

    assert settings.gpu_executor_init_timeout_sec == 42.5
    assert settings.ga_queue_debug is True


def test_read_inflight_runtime_settings_uses_legacy_init_timeout_failure_default():
    settings = read_inflight_runtime_settings(env_get_fn=lambda _name, _default=None: "bad")

    assert settings.gpu_executor_init_timeout_sec == 180.0
    assert settings.ga_queue_debug is False


def test_inflight_dynamic_debug_helpers_read_current_env_value():
    assert inflight_stall_debug_enabled(env_get_fn=lambda _name, _default=None: "1") is True
    assert inflight_shutdown_debug_enabled(env_get_fn=lambda _name, _default=None: "true") is True
    assert inflight_stall_debug_enabled(env_get_fn=lambda _name, _default=None: "0") is False
    assert inflight_shutdown_debug_enabled(env_get_fn=lambda _name, _default=None: "") is False


def test_read_inflight_loop_observer_settings_uses_safe_defaults_for_invalid_values():
    settings = read_inflight_loop_observer_settings(env_get_fn=lambda _name, _default=None: "bad")

    assert settings.heartbeat_sec == 0.0
    assert settings.throughput_sec == 0.0
    assert settings.stage_profile_emit_sec == 0.0
    assert settings.profile_max_songs == 0

    negative = read_inflight_loop_observer_settings(
        env_get_fn=lambda name, default=None: "-1" if name == "INFLIGHT_PROFILE_MAX_SONGS" else default,
    )
    assert negative.profile_max_songs == 0


def test_read_fg_static_prep_max_inflight_uses_unified_cpu_lookahead_and_honors_explicit_override(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT", raising=False)

    cfg = _cfg_with_iteration_engine()
    assert (
        _read_fg_static_prep_max_inflight(
            cfg,
            fg_prep_workers=4,
            inflight_limit=16,
            cpu_prewarm_lookahead=5,
        )
        == 4
    )
    assert (
        _read_fg_static_prep_max_inflight(
            cfg,
            fg_prep_workers=4,
            inflight_limit=16,
            cpu_prewarm_lookahead=0,
        )
        == 0
    )

    cfg_explicit = _cfg_with_iteration_engine(InFlight_FGStaticPrepMaxInflight="3")
    assert (
        _read_fg_static_prep_max_inflight(
            cfg_explicit,
            fg_prep_workers=4,
            inflight_limit=16,
            cpu_prewarm_lookahead=5,
        )
        == 3
    )

    monkeypatch.setenv("INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT", "2")
    assert (
        _read_fg_static_prep_max_inflight(
            cfg_explicit,
            fg_prep_workers=4,
            inflight_limit=16,
            cpu_prewarm_lookahead=5,
        )
        == 2
    )


def test_read_inflight_target_song_lanes_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_TARGET_SONG_LANES", raising=False)

    cfg = _cfg_with_iteration_engine()
    assert _read_inflight_target_song_lanes(cfg, inflight_limit=1) == 1
    assert _read_inflight_target_song_lanes(cfg, inflight_limit=4) == 2

    cfg2 = _cfg_with_iteration_engine(InFlight_TargetSongLanes="3")
    assert _read_inflight_target_song_lanes(cfg2, inflight_limit=4) == 3

    monkeypatch.setenv("INFLIGHT_TARGET_SONG_LANES", "9")
    assert _read_inflight_target_song_lanes(cfg2, inflight_limit=4) == 4

    monkeypatch.setenv("INFLIGHT_TARGET_SONG_LANES", "0")
    assert _read_inflight_target_song_lanes(cfg2, inflight_limit=4) == 1


def test_continuous_fg_should_fill_song_lanes_before_fg_when_safe():
    assert (
        _continuous_fg_should_fill_song_lanes(
            target_song_lanes=2,
            active_song_lanes=1,
            ready_ga_count=1,
            blocked_on_slot=False,
            no_ga_remaining=False,
            oldest_wait_s=0.2,
            aging_hard_s=2.5,
        )
        is True
    )


def test_continuous_fg_should_fill_song_lanes_respects_fairness_and_capacity():
    base = {
        "target_song_lanes": 2,
        "active_song_lanes": 1,
        "ready_ga_count": 1,
        "blocked_on_slot": False,
        "no_ga_remaining": False,
        "oldest_wait_s": 0.2,
        "aging_hard_s": 2.5,
    }

    for override in (
        {"target_song_lanes": 1},
        {"active_song_lanes": 2},
        {"ready_ga_count": 0},
        {"blocked_on_slot": True},
        {"no_ga_remaining": True},
        {"oldest_wait_s": 2.5},
    ):
        args = dict(base)
        args.update(override)
        assert _continuous_fg_should_fill_song_lanes(**args) is False


def test_continuous_fg_lane_fill_yields_to_ready_fg_backlog():
    assert (
        _continuous_fg_should_fill_song_lanes(
            target_song_lanes=2,
            active_song_lanes=1,
            ready_ga_count=1,
            pending_fg_count=4,
            ready_fg_count=1,
            blocked_on_slot=False,
            no_ga_remaining=False,
            oldest_wait_s=0.1,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is False
    )


def test_continuous_fg_lane_fill_yields_to_aged_fg_backlog_even_if_ready_hint_lags():
    assert (
        _continuous_fg_should_fill_song_lanes(
            target_song_lanes=2,
            active_song_lanes=1,
            ready_ga_count=1,
            pending_fg_count=4,
            ready_fg_count=0,
            blocked_on_slot=False,
            no_ga_remaining=False,
            oldest_wait_s=0.8,
            aging_trigger_s=0.75,
            aging_hard_s=2.5,
        )
        is False
    )


def test_continuous_ga_yields_to_ready_fg_before_more_ga():
    assert (
        _continuous_ga_should_yield_to_fg(
            fg_enabled=True,
            fg_drain_at_end=True,
            pending_fg_count=2,
            ready_fg_count=1,
            fg_prep_inflight_count=0,
            fg_inflight_count=0,
            fg_worker_count=4,
            target_song_lanes=2,
            oldest_wait_s=0.0,
            aging_trigger_s=0.75,
            blocked_on_slot=False,
        )
        is True
    )


def test_continuous_ga_keeps_feeding_while_fg_prep_catches_up():
    assert (
        _continuous_ga_should_yield_to_fg(
            fg_enabled=True,
            fg_drain_at_end=True,
            pending_fg_count=4,
            ready_fg_count=0,
            fg_prep_inflight_count=4,
            fg_inflight_count=0,
            fg_worker_count=4,
            target_song_lanes=2,
            oldest_wait_s=3.0,
            aging_trigger_s=0.75,
            blocked_on_slot=False,
        )
        is False
    )


def test_continuous_ga_yield_respects_fg_disabled_and_drain_disabled():
    assert (
        _continuous_ga_should_yield_to_fg(
            fg_enabled=False,
            fg_drain_at_end=True,
            pending_fg_count=3,
            ready_fg_count=3,
            fg_prep_inflight_count=0,
            fg_inflight_count=0,
            fg_worker_count=4,
            target_song_lanes=2,
            oldest_wait_s=3.0,
            aging_trigger_s=0.75,
            blocked_on_slot=False,
        )
        is False
    )
    assert (
        _continuous_ga_should_yield_to_fg(
            fg_enabled=True,
            fg_drain_at_end=False,
            pending_fg_count=3,
            ready_fg_count=3,
            fg_prep_inflight_count=0,
            fg_inflight_count=0,
            fg_worker_count=4,
            target_song_lanes=2,
            oldest_wait_s=3.0,
            aging_trigger_s=0.75,
            blocked_on_slot=False,
        )
        is False
    )


def test_continuous_ga_does_not_yield_when_fg_workers_are_full():
    assert (
        _continuous_ga_should_yield_to_fg(
            fg_enabled=True,
            fg_drain_at_end=True,
            pending_fg_count=8,
            ready_fg_count=8,
            fg_prep_inflight_count=0,
            fg_inflight_count=8,
            fg_worker_count=8,
            target_song_lanes=2,
            oldest_wait_s=3.0,
            aging_trigger_s=0.75,
            blocked_on_slot=False,
        )
        is False
    )


def test_continuous_ga_warm_queue_limit_keeps_full_limit_when_fg_has_not_started():
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
        target_song_lanes=2,
        active_song_lanes=0,
        dispatch_burst=2,
    )
    assert limit == 2


def test_continuous_ga_warm_queue_limit_stays_shallow_during_decode_handoff_before_fg_owner_turn():
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
        target_song_lanes=2,
        active_song_lanes=2,
        dispatch_burst=2,
    )
    assert limit == 4


def test_continuous_ga_warm_queue_limit_restores_full_limit_once_fg_owner_turn_is_active():
    limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=True,
        prepared_count=4,
        prep_inflight_count=2,
        decode_inflight_count=1,
        pending_fg_count=2,
        fg_prep_inflight_count=1,
        fg_inflight_count=1,
        target_song_lanes=2,
        active_song_lanes=2,
        dispatch_burst=2,
    )
    assert limit == 12


def test_continuous_ga_warm_queue_limit_keeps_full_limit_when_fg_disabled_or_staging_is_below_conveyor():
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
        target_song_lanes=2,
        active_song_lanes=0,
        dispatch_burst=2,
    )
    assert disabled_limit == 12

    shallow_limit = _continuous_ga_warm_queue_limit(
        ga_queue_limit=12,
        inflight_limit=4,
        fg_enabled=True,
        prepared_count=1,
        prep_inflight_count=0,
        decode_inflight_count=0,
        pending_fg_count=0,
        fg_prep_inflight_count=0,
        fg_inflight_count=0,
        target_song_lanes=2,
        active_song_lanes=0,
        dispatch_burst=2,
    )
    assert shallow_limit == 12


def test_continuous_fg_submit_budget_fills_ready_worker_capacity():
    control_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
        ready_fg_count=8,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=12,
        adaptive_submit=False,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert control_budget == 4

    adaptive_budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
        ready_fg_count=8,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=12,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert adaptive_budget == 4


def test_continuous_fg_submit_budget_probes_pending_fg_while_ga_can_continue():
    budget = _continuous_fg_submit_budget(
        pending_fg_count=8,
        ready_fg_count=0,
        fg_inflight_count=0,
        fg_workers=4,
        fg_batch_max=4,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=3.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=12,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert budget == 1


def test_continuous_fg_submit_budget_allows_eight_ready_fg_jobs_inflight():
    budget = _continuous_fg_submit_budget(
        pending_fg_count=16,
        ready_fg_count=16,
        fg_inflight_count=0,
        fg_workers=8,
        fg_batch_max=8,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=16,
        adaptive_submit=True,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert budget == 8


def test_continuous_fg_submit_budget_adaptive_smooths_when_prep_backlog_exists():
    control_budget = _continuous_fg_submit_budget(
        pending_fg_count=16,
        ready_fg_count=6,
        fg_inflight_count=0,
        fg_workers=8,
        fg_batch_max=8,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=16,
        adaptive_submit=False,
        adaptive_max_burst=3,
        fg_slot_reserve=0,
    )
    assert control_budget == 6

    adaptive_budget = _continuous_fg_submit_budget(
        pending_fg_count=16,
        ready_fg_count=6,
        fg_inflight_count=0,
        fg_workers=8,
        fg_batch_max=8,
        no_ga_remaining=False,
        fg_drain_at_end=True,
        blocked_on_slot=False,
        oldest_wait_s=0.0,
        aging_trigger_s=0.75,
        aging_hard_s=2.5,
        ga_queue_limit=16,
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


def test_read_prime_target_defaults_and_honors_config_env_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_PRIME_TARGET", raising=False)

    cfg = _cfg_with_iteration_engine()
    assert _read_prime_target(cfg, inflight_limit=2, prep_limit=8, pending_count=20) == 4

    cfg_explicit = _cfg_with_iteration_engine(InFlight_PrimeTarget="6")
    assert _read_prime_target(cfg_explicit, inflight_limit=2, prep_limit=8, pending_count=20) == 6

    monkeypatch.setenv("INFLIGHT_PRIME_TARGET", "9")
    assert _read_prime_target(cfg_explicit, inflight_limit=2, prep_limit=8, pending_count=20) == 8

    monkeypatch.setenv("INFLIGHT_PRIME_TARGET", "0")
    assert _read_prime_target(cfg_explicit, inflight_limit=2, prep_limit=8, pending_count=20) == 4

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
    assert abs(read_inflight_event_wait_timeout_s() - 0.05) < 1e-9
    assert abs(_read_inflight_event_wait_gpu_cap_s() - 0.01) < 1e-9
    assert abs(_read_inflight_event_wait_short_spin_s() - 0.003) < 1e-9

    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC", "9.0")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC", "-1")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS", "100")

    assert abs(_read_inflight_event_wait_timeout_s() - 5.0) < 1e-9
    assert abs(read_inflight_event_wait_timeout_s() - 5.0) < 1e-9
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

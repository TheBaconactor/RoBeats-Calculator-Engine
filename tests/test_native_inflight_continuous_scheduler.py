import configparser

from gear_optimizer.solver.native_inflight_orchestrator import (
    continuous_fg_allow_not_ready,
    continuous_fg_prep_start_budget,
    continuous_fg_submit_budget,
    ga_admission_fg_backlog_limit,
    ga_should_pause_for_fg_backlog,
)
from gear_optimizer.solver.native_inflight_lifecycle import BubbleTracker
from gear_optimizer.solver.native_inflight_scheduler_policy import (
    closed_loop_bubble_kpi,
    count_active_song_lanes,
    read_fg_scheduler_mode,
)
from gear_optimizer.solver.native_inflight_config import (
    default_worker_threads,
    first_task_config,
    inflight_shutdown_debug_enabled,
    inflight_stall_debug_enabled,
    read_db_prefetch_workers,
    read_ga_multi_start,
    read_inflight_worker_count,
    read_inflight_loop_observer_settings,
    read_inflight_runtime_settings,
)
from gear_optimizer.solver.inflight_wait import (
    read_inflight_event_wait_gpu_cap_s,
    read_inflight_event_wait_short_spin_s,
    read_inflight_event_wait_timeout_s,
    wait_for_completion_event,
)
from tests.native_song_factory import make_native_song


def _cfg_with_iteration_engine(**pairs: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {k: str(v) for k, v in pairs.items()}
    return cfg


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


def test_read_fg_scheduler_mode_defaults_to_continuous():
    assert read_fg_scheduler_mode() == "continuous"


def test_read_ga_multi_start_uses_runtime_ga_settings():
    cfg = _cfg_with_iteration_engine(GA_MultiStart="4")

    assert read_ga_multi_start(cfg) == 4


def test_ga_admission_fg_backlog_limit_sizes_to_fg_stage_steady_state():
    # Steady state is every FG worker busy plus a full prep runway; the bound
    # must sit above that so it only binds when FG genuinely falls behind.
    assert ga_admission_fg_backlog_limit(fg_workers=2, fg_prep_workers=2) == 6
    assert ga_admission_fg_backlog_limit(fg_workers=2, fg_prep_workers=4) == 8
    # Tiny pools still keep a usable allowance.
    assert ga_admission_fg_backlog_limit(fg_workers=1, fg_prep_workers=1) == 5


def test_ga_pauses_only_when_fg_debt_exceeds_the_bound():
    assert (
        ga_should_pause_for_fg_backlog(
            pending_fg_count=4,
            fg_inflight_count=2,
            backlog_limit=6,
        )
        is False
    )
    assert (
        ga_should_pause_for_fg_backlog(
            pending_fg_count=5,
            fg_inflight_count=2,
            backlog_limit=6,
        )
        is True
    )
    assert (
        ga_should_pause_for_fg_backlog(
            pending_fg_count=0,
            fg_inflight_count=0,
            backlog_limit=6,
        )
        is False
    )


def test_continuous_fg_allows_unready_jobs_only_for_final_drain():
    assert continuous_fg_allow_not_ready(no_ga_remaining=True) is True
    assert continuous_fg_allow_not_ready(no_ga_remaining=False) is False


def test_continuous_fg_submit_budget_fills_free_workers_with_ready_songs():
    assert (
        continuous_fg_submit_budget(
            pending_fg_count=8,
            ready_fg_count=8,
            fg_inflight_count=0,
            fg_workers=4,
            fg_batch_max=4,
            no_ga_remaining=False,
        )
        == 4
    )
    assert (
        continuous_fg_submit_budget(
            pending_fg_count=8,
            ready_fg_count=3,
            fg_inflight_count=2,
            fg_workers=4,
            fg_batch_max=4,
            no_ga_remaining=False,
        )
        == 2
    )


def test_continuous_fg_submit_budget_mid_run_is_capped_by_ready_songs():
    # A worker handed a not-yet-ready song would block on its prep future while
    # GA still feeds the owner; mid-run budget never exceeds the ready count.
    assert (
        continuous_fg_submit_budget(
            pending_fg_count=8,
            ready_fg_count=0,
            fg_inflight_count=0,
            fg_workers=4,
            fg_batch_max=4,
            no_ga_remaining=False,
        )
        == 0
    )


def test_continuous_fg_submit_budget_honors_end_of_run_drain():
    assert (
        continuous_fg_submit_budget(
            pending_fg_count=5,
            ready_fg_count=0,
            fg_inflight_count=0,
            fg_workers=4,
            fg_batch_max=4,
            no_ga_remaining=True,
        )
        == 4
    )


def test_first_task_config_extracts_legacy_task_config():
    task = (None, "Song", "Hard", {"IterationEngine": {"SomeSetting": "6"}})
    cfg = first_task_config([task])

    assert cfg is not None
    assert cfg.get("IterationEngine", "SomeSetting") == "6"
    assert first_task_config([]) is None


def test_read_inflight_worker_count_uses_canonical_cpu_sizing_and_ga_seed():
    assert (
        read_inflight_worker_count(
            inflight_limit=8,
            kind="prep",
        )
        == default_worker_threads(inflight_limit=8, kind="prep")
    )

    assert (
        read_inflight_worker_count(
            inflight_limit=8,
            kind="decode",
        )
        == default_worker_threads(inflight_limit=8, kind="decode")
    )

    assert (
        read_inflight_worker_count(
            inflight_limit=8,
            kind="prep",
            ga_seed="fixed",
        )
        == 1
    )


def test_read_db_prefetch_workers_defaults_from_fg_prep():
    assert read_db_prefetch_workers(fg_prep_workers=2) == 2
    assert read_db_prefetch_workers(fg_prep_workers=9) == 4


def test_read_inflight_loop_observer_settings_reads_env_values():
    values = {
        "INFLIGHT_HEARTBEAT_SEC": "1.5",
        "INFLIGHT_THROUGHPUT_SEC": "2.5",
        "INFLIGHT_PROFILE_MAX_SONGS": "4",
    }

    settings = read_inflight_loop_observer_settings(env_get_fn=lambda name, default=None: values.get(name, default))

    assert settings.heartbeat_sec == 1.5
    assert settings.throughput_sec == 2.5
    assert settings.profile_max_songs == 4


def test_read_inflight_runtime_settings_reads_static_runtime_env_values():
    values = {
        "GPU_EXECUTOR_INIT_TIMEOUT_SEC": "42.5",
    }

    settings = read_inflight_runtime_settings(env_get_fn=lambda name, default=None: values.get(name, default))

    assert settings.gpu_executor_init_timeout_sec == 42.5


def test_read_inflight_runtime_settings_uses_legacy_init_timeout_failure_default():
    settings = read_inflight_runtime_settings(env_get_fn=lambda _name, _default=None: "bad")

    assert settings.gpu_executor_init_timeout_sec == 180.0


def test_inflight_dynamic_debug_helpers_read_current_env_value():
    assert inflight_stall_debug_enabled(env_get_fn=lambda _name, _default=None: "1") is True
    assert inflight_shutdown_debug_enabled(env_get_fn=lambda _name, _default=None: "true") is True
    assert inflight_stall_debug_enabled(env_get_fn=lambda _name, _default=None: "0") is False
    assert inflight_shutdown_debug_enabled(env_get_fn=lambda _name, _default=None: "") is False


def test_read_inflight_loop_observer_settings_uses_safe_defaults_for_invalid_values():
    settings = read_inflight_loop_observer_settings(env_get_fn=lambda _name, _default=None: "bad")

    assert settings.heartbeat_sec == 0.0
    assert settings.throughput_sec == 0.0
    assert settings.profile_max_songs == 0

    negative = read_inflight_loop_observer_settings(
        env_get_fn=lambda name, default=None: "-1" if name == "INFLIGHT_PROFILE_MAX_SONGS" else default,
    )
    assert negative.profile_max_songs == 0


def test_continuous_fg_prep_start_budget_fills_the_prep_worker_runway():
    assert (
        continuous_fg_prep_start_budget(
            pending_fg_count=6,
            fg_prep_inflight_count=0,
            fg_prep_worker_count=6,
        )
        == 6
    )


def test_continuous_fg_prep_start_budget_stops_when_runway_is_full():
    assert (
        continuous_fg_prep_start_budget(
            pending_fg_count=6,
            fg_prep_inflight_count=6,
            fg_prep_worker_count=6,
        )
        == 0
    )


def test_continuous_fg_prep_start_budget_clamps_to_pending():
    assert (
        continuous_fg_prep_start_budget(
            pending_fg_count=1,
            fg_prep_inflight_count=0,
            fg_prep_worker_count=4,
        )
        == 1
    )


def test_read_inflight_event_wait_settings_are_hardwired(monkeypatch):
    # The in-flight event-wait timings are now hardwired constants (no env
    # override); setting the former env vars must have NO effect.
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC", "9.0")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC", "-1")
    monkeypatch.setenv("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS", "100")

    assert abs(read_inflight_event_wait_timeout_s() - 0.05) < 1e-9
    assert abs(read_inflight_event_wait_gpu_cap_s() - 0.01) < 1e-9
    assert abs(read_inflight_event_wait_short_spin_s() - 0.003) < 1e-9


def test_wait_for_completion_event_short_timeout_uses_zero_timeout_poll():
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

    done = wait_for_completion_event(
        event,
        timeout_s=0.003,
        short_spin_s=0.005,
        perf_counter=_fake_perf_counter,
        sleep=lambda _t: None,
    )
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
    done = wait_for_completion_event(event, timeout_s=0.02, short_spin_s=0.003)
    assert done is False
    assert event.waits == [0.02]


def test_closed_loop_bubble_kpi_increases_with_ready_work_and_fg_wait():
    quiet = closed_loop_bubble_kpi(
        idle_sec=0.5,
        ready_ga_count=1,
        ready_fg_count=0,
        backlog_count=2,
        oldest_fg_wait_s=0.0,
    )
    pressured = closed_loop_bubble_kpi(
        idle_sec=0.5,
        ready_ga_count=2,
        ready_fg_count=1,
        backlog_count=6,
        oldest_fg_wait_s=2.0,
    )

    assert quiet > 0.0
    assert pressured > quiet


def test_bubble_snapshot_reports_zero_idle_while_gpu_work_is_inflight():
    snapshot = BubbleTracker().snapshot_from_pipeline_counts(
        now_mono=12.5,
        prepared_count=3,
        ready_fg_count=1,
        active_song_lanes=2,
        pending_tasks_count=10,
        prep_inflight_count=0,
        decode_inflight_count=0,
        pending_fg_count=2,
        fg_prep_inflight_count=0,
        ga_inflight_count=1,
        fg_futures_count=1,
        last_progress=10.0,
        oldest_fg_wait_s=2.0,
    )

    assert snapshot["gpu_idle"] == 0
    assert snapshot["idle_sec"] == 0.0
    assert snapshot["bubble_kpi"] == 0.0


def test_bubble_snapshot_reports_idle_during_host_only_fg_materialization():
    snapshot = BubbleTracker().snapshot_from_pipeline_counts(
        now_mono=12.5,
        prepared_count=3,
        ready_fg_count=1,
        active_song_lanes=2,
        pending_tasks_count=10,
        prep_inflight_count=0,
        decode_inflight_count=0,
        pending_fg_count=2,
        fg_prep_inflight_count=0,
        ga_inflight_count=0,
        fg_futures_count=2,
        last_progress=10.0,
        oldest_fg_wait_s=2.0,
    )

    assert snapshot["gpu_idle"] == 1
    assert snapshot["idle_sec"] == 2.5
    assert snapshot["bubble_kpi"] > 0.0

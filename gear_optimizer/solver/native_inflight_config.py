"""
GPU-native in-flight pipeline configuration parsing.

Extracts all config/ENV-driven settings for the native in-flight orchestrator
into a frozen dataclass so the orchestrator body stays focused on runtime logic.
"""

from __future__ import annotations

import logging
import configparser
import os
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.config import GASettings as GARuntimeSettings
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.utils import cfg_from_dict, safe_int
from gear_optimizer.domain.jobs import task_cfg_dict
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.native_inflight_prepare import bump_prep_cache_limits_for_ram_mode
from gear_optimizer.solver.native_inflight_scheduler import (
    _read_continuous_fg_adaptive_submit,
    _read_continuous_ga_dispatch_burst,
    _read_fg_ga_credit_budget,
    _read_fg_scheduler_mode,
    _read_fg_slot_reserve,
    _read_inflight_target_song_lanes,
)

logger = logging.getLogger(__name__)


def _default_worker_threads(*, inflight_limit: int, kind: str) -> int:
    """
    Choose conservative default worker counts for low-end CPUs.

    Goal: avoid oversubscription that can *increase* wall time (thread contention)
    and starve the GPU queue, especially on 4–8 core machines.
    """
    ncpu = os.cpu_count() or 1
    try:
        ncpu = int(ncpu)
    except (ValueError, TypeError):
        ncpu = 1
    ncpu = max(1, ncpu)
    inflight_limit = max(1, int(inflight_limit))
    kind = str(kind or "").strip().lower()

    base = max(1, ncpu // 2)
    if ncpu <= 4:
        base = min(base, 2)
    elif ncpu <= 8:
        base = min(base, 3)

    if kind in {"fg_prep", "fgprep"}:
        base = max(1, min(base, 2 if ncpu <= 8 else base))
    return max(1, min(inflight_limit, int(base)))


def _read_fg_static_prep_max_inflight(
    cfg0: Any,
    *,
    fg_prep_workers: int,
    inflight_limit: int,
    cpu_prewarm_lookahead: int | None = None,
) -> int:
    """
    Budget for speculative FG static prep.

    The unified CPU prewarm lookahead owns the default. The legacy explicit
    FG static setting is still honored as a narrower override when present.
    """
    if cpu_prewarm_lookahead is None:
        limit = 0
    else:
        try:
            limit = int(cpu_prewarm_lookahead)
        except (ValueError, TypeError):
            limit = 0
    if cfg0 is not None:
        try:
            raw_cfg = cfg0.get("IterationEngine", "InFlight_FGStaticPrepMaxInflight", fallback="")
        except (configparser.Error, ValueError, TypeError):
            raw_cfg = ""
        if str(raw_cfg).strip() != "":
            try:
                limit = int(raw_cfg)
            except (ValueError, TypeError):
                limit = 0
    raw_env = env_get("INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT")
    if raw_env is not None and str(raw_env).strip() != "":
        try:
            limit = int(raw_env)
        except (ValueError, TypeError):
            limit = 0
    if limit <= 0:
        return 0
    return max(0, min(int(limit), int(fg_prep_workers), int(inflight_limit), 8))


def _read_cpu_prewarm_lookahead(
    cfg0: Any,
    *,
    prep_limit: int,
    default: int = 5,
) -> int:
    """
    Unified lookahead for CPU-only prework on prepared future songs.

    This controls host-side timeline frontier payload prewarm, FG baseline
    point prewarm, and speculative FG static prep admission. It intentionally
    does not change the prep buffer size; it only decides how many prepared
    songs get expensive extra work ahead of GPU dispatch.
    """
    lookahead = int(default)
    if cfg0 is not None:
        try:
            raw_cfg = cfg0.get("IterationEngine", "InFlight_CPUPrewarmLookahead", fallback="")
        except (configparser.Error, ValueError, TypeError):
            raw_cfg = ""
        if str(raw_cfg).strip() != "":
            try:
                lookahead = int(raw_cfg)
            except (ValueError, TypeError):
                lookahead = int(default)
    raw_env = env_get("INFLIGHT_CPU_PREWARM_LOOKAHEAD")
    if raw_env is not None and str(raw_env).strip() != "":
        try:
            lookahead = int(raw_env)
        except (ValueError, TypeError):
            pass
    return max(0, min(int(lookahead), int(prep_limit), 32))


def _read_inflight_worker_count(
    cfg0: Any,
    *,
    config_key: str,
    env_key: str,
    inflight_limit: int,
    kind: str,
    ga_seed: str = "",
) -> int:
    workers = 0
    if cfg0 is not None:
        try:
            workers = safe_int(cfg0.get("IterationEngine", str(config_key), fallback="0"), 0)
        except (configparser.Error, ValueError, TypeError):
            workers = 0
    raw = env_get(str(env_key))
    if raw is not None and str(raw).strip() != "":
        try:
            workers = int(raw)
        except (ValueError, TypeError):
            pass
    if workers <= 0:
        if str(ga_seed or "").strip() and str(kind or "").strip().lower() == "prep":
            return 1
        workers = _default_worker_threads(inflight_limit=int(inflight_limit), kind=str(kind))
    return max(1, int(workers))


def _read_cpu_prewarm_workers(
    cfg0: Any,
    *,
    inflight_limit: int,
    cpu_prewarm_lookahead: int,
) -> int:
    if int(cpu_prewarm_lookahead) <= 0:
        return 0
    workers = 0
    if cfg0 is not None:
        try:
            workers = safe_int(cfg0.get("IterationEngine", "InFlight_CPUPrewarmWorkers", fallback="0"), 0)
        except (configparser.Error, ValueError, TypeError):
            workers = 0
    raw = env_get("INFLIGHT_CPU_PREWARM_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            workers = int(raw)
        except (ValueError, TypeError):
            pass
    if workers <= 0:
        workers = min(2, max(1, _default_worker_threads(inflight_limit=int(inflight_limit), kind="prep")))
    return max(1, min(int(workers), int(cpu_prewarm_lookahead), 4))


def _read_db_prefetch_workers(
    cfg0: Any,
    *,
    fg_prep_workers: int,
) -> int:
    workers = 0
    if cfg0 is not None:
        try:
            workers = safe_int(cfg0.get("IterationEngine", "InFlight_DBPrefetchWorkers", fallback="0"), 0)
        except (configparser.Error, ValueError, TypeError):
            workers = 0
    raw = env_get("INFLIGHT_DB_PREFETCH_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            workers = int(raw)
        except (ValueError, TypeError):
            pass
    if workers <= 0:
        workers = max(1, min(int(fg_prep_workers), 4))
    return max(1, int(workers))


def _read_ga_multi_start(cfg0: Any) -> int:
    try:
        settings = GARuntimeSettings.from_config(cfg0) if cfg0 is not None else GARuntimeSettings()
        return max(1, int(settings.multi_start))
    except Exception as e:
        logger.debug(f"native_inflight_config:_read_ga_multi_start: {e}")
        return 1


@dataclass(frozen=True)
class InflightConfig:
    inflight_ram_mode: bool
    pool_cache_max: int
    registry_cache_max: int
    init_heur_cache_max: int
    inflight_limit: int
    max_song_slots: int
    song_slot_limit: int
    target_song_lanes: int
    ga_queue_mult: int
    ga_queue_limit: int
    prep_buffer_mult: int
    prep_limit: int
    prep_workers: int
    cpu_prewarm_lookahead: int
    cpu_prewarm_workers: int
    decode_workers: int
    fg_aging_trigger_s: float
    fg_aging_hard_s: float
    fg_scheduler_norm: str
    fg_drain_at_end: bool
    fg_drain_src: str
    fg_ga_credit_budget_cfg: int
    continuous_ga_dispatch_burst: int
    fg_adaptive_submit_enabled: bool
    fg_adaptive_submit_max_burst: int
    inflight_fg_hold_slots: bool
    hold_slots_explicit: bool
    fg_enabled: bool
    fg_slot_reserve: int
    ga_queue_limit_base: int
    inflight_ga_dynamic_queue: bool
    ga_queue_extra_free_on_slot_pressure: int
    ga_queue_pressure_window_s: float
    ga_slack_slots: int
    fg_hold_budget: int
    stage_profile_enabled: bool
    stage_profile_path: str | None
    runtime: "InflightRuntimeSettings"
    loop_observer: "InflightLoopObserverSettings"
    fg_decision_debug: bool
    fg_submit_debug: bool


@dataclass(frozen=True)
class InflightRuntimeSettings:
    gpu_executor_init_timeout_sec: float
    ga_queue_debug: bool


def read_inflight_runtime_settings(
    *,
    env_get_fn=env_get,
) -> InflightRuntimeSettings:
    try:
        gpu_executor_init_timeout_sec = float(env_get_fn("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "600") or "600")
    except (ValueError, TypeError):
        gpu_executor_init_timeout_sec = 180.0

    return InflightRuntimeSettings(
        gpu_executor_init_timeout_sec=float(gpu_executor_init_timeout_sec),
        ga_queue_debug=_truthy(env_get_fn("INFLIGHT_GA_QUEUE_DEBUG", "0")),
    )


def inflight_stall_debug_enabled(*, env_get_fn=env_get) -> bool:
    return _truthy(env_get_fn("INFLIGHT_STALL_DEBUG", "0"))


def inflight_shutdown_debug_enabled(*, env_get_fn=env_get) -> bool:
    return _truthy(env_get_fn("INFLIGHT_SHUTDOWN_DEBUG", "0"))


def first_task_config(tasks: list[tuple]) -> Any | None:
    try:
        return cfg_from_dict(task_cfg_dict(tasks[0]))
    except (IndexError, KeyError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class InflightLoopObserverSettings:
    heartbeat_sec: float
    throughput_sec: float
    stage_profile_emit_sec: float
    profile_max_songs: int


def read_inflight_loop_observer_settings(
    *,
    env_get_fn=env_get,
) -> InflightLoopObserverSettings:
    try:
        heartbeat_sec = float(env_get_fn("INFLIGHT_HEARTBEAT_SEC", "0") or "0")
    except (ValueError, TypeError):
        heartbeat_sec = 0.0
    try:
        throughput_sec = float(env_get_fn("INFLIGHT_THROUGHPUT_SEC", "0") or "0")
    except (ValueError, TypeError):
        throughput_sec = 0.0
    try:
        stage_profile_emit_sec = float(env_get_fn("INFLIGHT_STAGE_PROFILE_EMIT_SEC", "0") or "0")
    except (ValueError, TypeError):
        stage_profile_emit_sec = 0.0
    try:
        profile_max_songs = int(env_get_fn("INFLIGHT_PROFILE_MAX_SONGS", "0") or "0")
    except (ValueError, TypeError):
        profile_max_songs = 0

    return InflightLoopObserverSettings(
        heartbeat_sec=float(heartbeat_sec),
        throughput_sec=float(throughput_sec),
        stage_profile_emit_sec=float(stage_profile_emit_sec),
        profile_max_songs=max(0, int(profile_max_songs)),
    )


def parse_inflight_config(tasks: list[tuple], *, in_flight_songs: int) -> InflightConfig:
    cfg0 = first_task_config(tasks)

    inflight_ram_mode = False
    try:
        raw_env = env_get("INFLIGHT_RAM_MODE")
        if raw_env is not None and str(raw_env).strip() != "":
            inflight_ram_mode = _truthy(raw_env)
        elif cfg0 is not None:
            inflight_ram_mode = cfg0.getboolean("IterationEngine", "InFlight_RamMode", fallback=False)
    except (configparser.Error, ValueError, TypeError):
        inflight_ram_mode = False

    pool_cache_max = 0
    registry_cache_max = 0
    init_heur_cache_max = 0
    if inflight_ram_mode:
        pool_cache_max, registry_cache_max, init_heur_cache_max = bump_prep_cache_limits_for_ram_mode()
        try:
            logger.debug(
                "[InFlight][RAM] enabled: default InFlight_GA_QueueMult=4 InFlight_PrepBufferMult=12 "
                f"cache_max={{pool:{int(pool_cache_max)} registry:{int(registry_cache_max)} heur:{int(init_heur_cache_max)}}}"
            )
        except (ValueError, TypeError):
            pass

    requested_inflight = max(1, int(in_flight_songs))
    inflight_limit = min(int(requested_inflight), len(tasks))

    try:
        from gear_optimizer.solver.taichi_gem.fields import MAX_SONG_SLOTS

        max_song_slots = int(MAX_SONG_SLOTS)
    except Exception as e:
        logger.debug(f"native_inflight_config:parse_inflight_config: {e}")
        max_song_slots = 8
    song_slot_limit = max(1, int(max_song_slots) - 1)
    inflight_limit = min(int(inflight_limit), int(song_slot_limit))
    if int(in_flight_songs) > 1:
        try:
            cap_reasons: list[str] = []
            try:
                if int(len(tasks)) < int(requested_inflight):
                    cap_reasons.append(f"queue={int(len(tasks))}")
            except (ValueError, TypeError):
                pass
            try:
                if int(song_slot_limit) < int(requested_inflight):
                    cap_reasons.append(f"usable_slots={int(song_slot_limit)}")
            except (ValueError, TypeError):
                pass

            msg = (
                f"[InFlight] enabled: requested={int(in_flight_songs)} effective={int(inflight_limit)} "
                f"(GPU_SONG_SLOTS={int(max_song_slots)}, usable_slots={int(song_slot_limit)})"
            )
            if int(inflight_limit) < int(in_flight_songs):
                if cap_reasons:
                    msg += f" [capped by {', '.join(cap_reasons)}"
                else:
                    msg += " [capped"
                msg += "; set GPU_SONG_SLOTS >= InFlightSongs + 1 to avoid slot caps]"
            logger.debug(msg)
        except (ValueError, TypeError):
            pass

    target_song_lanes = _read_inflight_target_song_lanes(cfg0, inflight_limit=int(inflight_limit))

    ga_queue_mult = 0
    if cfg0 is not None:
        try:
            ga_queue_mult = safe_int(cfg0.get("IterationEngine", "InFlight_GA_QueueMult", fallback="0"), 0)
        except (configparser.Error, ValueError, TypeError):
            ga_queue_mult = 0
    raw = env_get("INFLIGHT_GA_QUEUE_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_mult = int(raw)
        except (ValueError, TypeError):
            pass
    if ga_queue_mult <= 0:
        ga_queue_mult = 4 if inflight_ram_mode else 2
    ga_queue_mult = max(1, min(int(ga_queue_mult), 8))
    ga_queue_limit = max(1, int(inflight_limit) * int(ga_queue_mult))
    ga_queue_limit = min(int(ga_queue_limit), int(song_slot_limit))

    prep_buffer_mult = 0
    if cfg0 is not None:
        try:
            prep_buffer_mult = safe_int(cfg0.get("IterationEngine", "InFlight_PrepBufferMult", fallback="0"), 0)
        except (configparser.Error, ValueError, TypeError):
            prep_buffer_mult = 0
    raw = env_get("INFLIGHT_PREP_BUFFER_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            prep_buffer_mult = int(raw)
        except (ValueError, TypeError):
            pass
    if prep_buffer_mult <= 0:
        prep_buffer_mult = 12 if inflight_ram_mode else 4
    prep_buffer_mult = max(1, min(int(prep_buffer_mult), 16))
    prep_limit = max(1, int(inflight_limit) * int(prep_buffer_mult))
    cpu_prewarm_lookahead = _read_cpu_prewarm_lookahead(cfg0, prep_limit=int(prep_limit), default=5)
    ga_seed = str(env_get("GA_SEED") or "").strip()
    prep_workers = _read_inflight_worker_count(
        cfg0,
        config_key="InFlight_PrepWorkers",
        env_key="INFLIGHT_PREP_WORKERS",
        inflight_limit=int(inflight_limit),
        kind="prep",
        ga_seed=ga_seed,
    )
    cpu_prewarm_workers = _read_cpu_prewarm_workers(
        cfg0,
        inflight_limit=int(inflight_limit),
        cpu_prewarm_lookahead=int(cpu_prewarm_lookahead),
    )
    decode_workers = _read_inflight_worker_count(
        cfg0,
        config_key="InFlight_DecodeWorkers",
        env_key="INFLIGHT_DECODE_WORKERS",
        inflight_limit=int(inflight_limit),
        kind="decode",
    )

    fg_aging_trigger_ms = 750.0
    fg_aging_hard_ms = 2500.0
    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingTriggerMs"):
                fg_aging_trigger_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingTriggerMs", fallback="750"))
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingHardMs"):
                fg_aging_hard_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingHardMs", fallback="2500"))
    except (configparser.Error, ValueError, TypeError):
        fg_aging_trigger_ms = 750.0
        fg_aging_hard_ms = 2500.0
    raw = env_get("INFLIGHT_FG_AGING_TRIGGER_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_trigger_ms = float(raw)
        except (ValueError, TypeError):
            pass
    raw = env_get("INFLIGHT_FG_AGING_HARD_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_hard_ms = float(raw)
        except (ValueError, TypeError):
            pass
    fg_aging_trigger_s = max(0.0, float(fg_aging_trigger_ms) / 1000.0)
    fg_aging_hard_s = max(0.0, float(fg_aging_hard_ms) / 1000.0)
    if fg_aging_hard_s > 0.0 and fg_aging_hard_s < fg_aging_trigger_s:
        fg_aging_hard_s = float(fg_aging_trigger_s)

    fg_scheduler_norm = _read_fg_scheduler_mode()

    fg_drain_at_end = True
    fg_drain_src = "default(true)"
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "FG_DrainAtEnd"):
            raw = str(cfg0.get("IterationEngine", "FG_DrainAtEnd", fallback="") or "").strip()
            fg_drain_at_end = _truthy(raw)
            fg_drain_src = f"config({raw})"
        elif cfg0 is not None:
            fg_drain_src = "config(missing->false)"
    except (configparser.Error, ValueError, TypeError) as exc:
        fg_drain_at_end = False
        fg_drain_src = f"config_error({type(exc).__name__})"
    raw_env = env_get("INFLIGHT_FG_DRAIN_AT_END")
    if raw_env is None or str(raw_env).strip() == "":
        raw_env = env_get("FG_DRAIN_AT_END")
    if raw_env is not None and str(raw_env).strip() != "":
        fg_drain_at_end = _truthy(raw_env)
        fg_drain_src = f"env({raw_env})"

    fg_ga_credit_budget_cfg, _fg_ga_credit_explicit = _read_fg_ga_credit_budget(
        cfg0,
        default_budget=max(1, int(inflight_limit)),
    )
    continuous_ga_dispatch_burst = _read_continuous_ga_dispatch_burst(cfg0, default_burst=2)
    fg_adaptive_submit_enabled, fg_adaptive_submit_max_burst = _read_continuous_fg_adaptive_submit(cfg0)

    try:
        msg = f"[InFlight][FG] scheduler={fg_scheduler_norm} drain_at_end={bool(fg_drain_at_end)} source={fg_drain_src}"
        msg += (
            f" (GA_CreditBudget={int(fg_ga_credit_budget_cfg)}, "
            f"GA_DispatchBurst={int(continuous_ga_dispatch_burst)}, "
            f"FG_AdaptiveSubmit={int(bool(fg_adaptive_submit_enabled))}, "
            f"FG_AdaptiveMaxBurst={int(fg_adaptive_submit_max_burst)}, "
            f"TargetSongLanes={int(target_song_lanes)}, "
            f"CPUPrewarmLookahead={int(cpu_prewarm_lookahead)}, "
            f"InFlight_FGAgingTriggerMs={int(fg_aging_trigger_s * 1000.0)}, "
            f"InFlight_FGAgingHardMs={int(fg_aging_hard_s * 1000.0)})"
        )
        logger.debug(msg)
    except (ValueError, TypeError):
        pass

    inflight_fg_hold_slots = True
    try:
        if cfg0 is not None:
            inflight_fg_hold_slots = cfg0.getboolean("IterationEngine", "InFlight_FGHoldSlots", fallback=True)
    except (configparser.Error, ValueError, TypeError):
        inflight_fg_hold_slots = True
    hold_slots_explicit = False
    try:
        if cfg0 is not None:
            hold_slots_explicit = bool(cfg0.has_option("IterationEngine", "InFlight_FGHoldSlots"))
    except (configparser.Error, ValueError, TypeError):
        hold_slots_explicit = False
    raw = env_get("INFLIGHT_FG_HOLD_SLOTS")
    if raw is not None and str(raw).strip() != "":
        hold_slots_explicit = True
        inflight_fg_hold_slots = _truthy(raw)

    try:
        from gear_optimizer.core.config import read_iteration_engine_settings

        ie = read_iteration_engine_settings(cfg0)
        fg_enabled = bool(ie.force_greats_mode) and (bool(ie.force_greats_finder) or bool(ie.manual_force_greats))
    except Exception as e:
        logger.debug(f"native_inflight_config:parse_inflight_config: {e}")
        fg_enabled = False

    fg_slot_reserve = _read_fg_slot_reserve(
        cfg0,
        fg_enabled=bool(fg_enabled),
        inflight_limit=int(inflight_limit),
        song_slot_limit=int(song_slot_limit),
    )
    if fg_slot_reserve:
        ga_queue_limit = min(int(ga_queue_limit), max(1, int(song_slot_limit) - int(fg_slot_reserve)))

    ga_queue_limit_base = int(ga_queue_limit)

    inflight_ga_dynamic_queue = False
    try:
        inflight_ga_dynamic_queue = bool(fg_enabled and int(in_flight_songs) > 1)
    except (ValueError, TypeError):
        inflight_ga_dynamic_queue = False
    try:
        if cfg0 is not None:
            inflight_ga_dynamic_queue = cfg0.getboolean(
                "IterationEngine",
                "InFlight_GA_DynamicQueue",
                fallback=bool(inflight_ga_dynamic_queue),
            )
    except (configparser.Error, ValueError, TypeError):
        pass
    raw = env_get("INFLIGHT_GA_DYNAMIC_QUEUE")
    if raw is not None and str(raw).strip() != "":
        inflight_ga_dynamic_queue = _truthy(raw)

    ga_queue_extra_free_on_slot_pressure = 1
    try:
        if cfg0 is not None:
            ga_queue_extra_free_on_slot_pressure = safe_int(
                cfg0.get("IterationEngine", "InFlight_GA_ExtraFreeSlotsOnSlotPressure", fallback="1"),
                1,
            )
    except (configparser.Error, ValueError, TypeError):
        ga_queue_extra_free_on_slot_pressure = 1
    raw = env_get("INFLIGHT_GA_EXTRA_FREE_SLOTS_ON_SLOT_PRESSURE")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_extra_free_on_slot_pressure = int(raw)
        except (ValueError, TypeError):
            pass
    ga_queue_extra_free_on_slot_pressure = max(0, min(int(ga_queue_extra_free_on_slot_pressure), 8))

    ga_queue_pressure_window_s = 1.5
    try:
        if cfg0 is not None:
            ga_queue_pressure_window_s = float(
                cfg0.get("IterationEngine", "InFlight_GA_SlotPressureWindowSec", fallback="1.5")
            )
    except (configparser.Error, ValueError, TypeError):
        ga_queue_pressure_window_s = 1.5
    raw = env_get("INFLIGHT_GA_SLOT_PRESSURE_WINDOW_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_pressure_window_s = float(raw)
        except (ValueError, TypeError):
            pass
    ga_queue_pressure_window_s = max(0.0, min(float(ga_queue_pressure_window_s), 60.0))

    ga_slack_slots = 0
    try:
        ga_slack_slots = max(0, int(song_slot_limit) - int(ga_queue_limit))
    except (ValueError, TypeError):
        ga_slack_slots = 0

    fg_hold_budget = int(ga_slack_slots)

    if inflight_fg_hold_slots and fg_enabled and int(in_flight_songs) > 1:
        if int(fg_hold_budget) <= 0:
            required_gpu_slots = None
            try:
                required_usable = int(ga_queue_limit)
                required_gpu_slots = int(required_usable) + 1
            except (ValueError, TypeError):
                required_gpu_slots = None
            try:
                msg = (
                    "[InFlight][WARN] Slot pressure: InFlight_FGHoldSlots=true with "
                    f"usable_slots={int(song_slot_limit)} ga_queue_limit={int(ga_queue_limit)} slack={int(ga_slack_slots)}; "
                    "FG slot reuse is impossible with the current GA queue depth."
                )
                if required_gpu_slots is not None:
                    msg += f" (For full slot reuse: set GPU_SONG_SLOTS>={int(required_gpu_slots)} or reduce InFlight_GA_QueueMult.)"
                logger.debug(msg)
            except (ValueError, TypeError):
                pass
            if not hold_slots_explicit:
                inflight_fg_hold_slots = False
                fg_hold_budget = 0
                try:
                    logger.debug("[InFlight][Auto] Disabling InFlight_FGHoldSlots (no slack song slots available).")
                except (ValueError, TypeError):
                    pass

    try:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields
        from gear_optimizer.solver.genetic import GA_POPULATION_SIZE

        ga_runs = _read_ga_multi_start(cfg0)
        gpu_fields.configure_ga_run_buffers(max_runs=ga_runs, max_genomes=GA_POPULATION_SIZE)
    except Exception as e:
        logger.debug(f"native_inflight_config:parse_inflight_config: {e}")

    try:
        if os.name == "nt" and env_get("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE") is None:
            os.environ["GPU_ALLOW_SYSTEM_TIMER_OVERRIDE"] = "1"
            if _truthy(env_get("PERF_TIMING", "0")):
                logger.debug(
                    "[InFlight][Perf] Enabled 1ms Windows timer period for GPU batching "
                    "(set GPU_ALLOW_SYSTEM_TIMER_OVERRIDE=0 to disable)."
                )
    except (ValueError, TypeError):
        pass

    stage_profile_enabled = _truthy(env_get("INFLIGHT_STAGE_PROFILE", "0"))
    stage_profile_path = env_get("INFLIGHT_STAGE_PROFILE_PATH")
    if stage_profile_enabled and not stage_profile_path:
        try:
            from gear_optimizer.core.constants import PATHS

            stage_profile_path = PATHS.bin_path("inflight_stage_profile.json")
        except Exception as e:
            logger.debug(f"native_inflight_config:parse_inflight_config: {e}")
            stage_profile_path = None

    fg_decision_debug = _truthy(env_get("INFLIGHT_FG_DECISION_DEBUG", "0"))
    fg_submit_debug = _truthy(env_get("INFLIGHT_FG_SUBMIT_DEBUG", "0"))
    runtime = read_inflight_runtime_settings()
    loop_observer = read_inflight_loop_observer_settings()

    return InflightConfig(
        inflight_ram_mode=inflight_ram_mode,
        pool_cache_max=pool_cache_max,
        registry_cache_max=registry_cache_max,
        init_heur_cache_max=init_heur_cache_max,
        inflight_limit=inflight_limit,
        max_song_slots=max_song_slots,
        song_slot_limit=song_slot_limit,
        target_song_lanes=target_song_lanes,
        ga_queue_mult=ga_queue_mult,
        ga_queue_limit=ga_queue_limit,
        prep_buffer_mult=prep_buffer_mult,
        prep_limit=prep_limit,
        prep_workers=prep_workers,
        cpu_prewarm_lookahead=cpu_prewarm_lookahead,
        cpu_prewarm_workers=cpu_prewarm_workers,
        decode_workers=decode_workers,
        fg_aging_trigger_s=fg_aging_trigger_s,
        fg_aging_hard_s=fg_aging_hard_s,
        fg_scheduler_norm=fg_scheduler_norm,
        fg_drain_at_end=fg_drain_at_end,
        fg_drain_src=fg_drain_src,
        fg_ga_credit_budget_cfg=fg_ga_credit_budget_cfg,
        continuous_ga_dispatch_burst=continuous_ga_dispatch_burst,
        fg_adaptive_submit_enabled=fg_adaptive_submit_enabled,
        fg_adaptive_submit_max_burst=fg_adaptive_submit_max_burst,
        inflight_fg_hold_slots=inflight_fg_hold_slots,
        hold_slots_explicit=hold_slots_explicit,
        fg_enabled=fg_enabled,
        fg_slot_reserve=fg_slot_reserve,
        ga_queue_limit_base=ga_queue_limit_base,
        inflight_ga_dynamic_queue=inflight_ga_dynamic_queue,
        ga_queue_extra_free_on_slot_pressure=ga_queue_extra_free_on_slot_pressure,
        ga_queue_pressure_window_s=ga_queue_pressure_window_s,
        ga_slack_slots=ga_slack_slots,
        fg_hold_budget=fg_hold_budget,
        stage_profile_enabled=stage_profile_enabled,
        stage_profile_path=stage_profile_path,
        runtime=runtime,
        loop_observer=loop_observer,
        fg_decision_debug=fg_decision_debug,
        fg_submit_debug=fg_submit_debug,
    )

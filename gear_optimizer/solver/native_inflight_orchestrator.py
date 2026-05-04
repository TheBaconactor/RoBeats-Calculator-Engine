"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).

This pipeline is designed to keep the GPU continuously busy in GPU_Native_GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Scheduling ForceGreatsFinder work via continuous credit-based interleaving,
  with CPU grouping/prep performed off the GPU thread and GPU kernels submitted via the executor.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import threading
import time
import traceback
from collections import deque
from typing import Any, Optional

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.core.utils import cfg_from_dict, safe_int
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.ga_entry_utils import (
    entry_loadout_hash,
    materialize_candidate_names,
    materialize_entry_names,
)
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_effective_unique_ga_candidates
from gear_optimizer.helpers.song_helpers.loadout_builder import merge_db_loadouts_into_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn, evaluate_progress_record_update
from gear_optimizer.solver.genetic import GA_POPULATION_SIZE
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient, GpuServiceTimeoutError
from gear_optimizer.solver.inflight_wait import (
    read_inflight_event_wait_gpu_cap_s,
    read_inflight_event_wait_short_spin_s,
    wait_for_completion_event,
)
from gear_optimizer.solver.native_inflight_prepare import _prepare_song, bump_prep_cache_limits_for_ram_mode
from gear_optimizer.solver.native_inflight_scheduler import (
    _closed_loop_bubble_kpi,
    _continuous_fg_allow_not_ready,
    _continuous_ga_should_yield_to_fg,
    _continuous_fg_should_fill_song_lanes,
    _continuous_fg_should_start,
    _continuous_fg_submit_budget,
    _continuous_ga_warm_queue_limit,
    _default_prime_target,
    _read_continuous_fg_adaptive_submit,
    _read_continuous_ga_dispatch_burst,
    _read_fg_ga_credit_budget,
    _read_fg_scheduler_mode,
    _read_fg_slot_reserve,
    _read_inflight_target_song_lanes,
)
from gear_optimizer.solver.native_inflight_fg_pipeline import (
    NativeFGPipeline,
    read_native_fg_pipeline_settings,
)
from gear_optimizer.solver.native_inflight_support import (
    _PostSender,
    _extract_repeat_bundle,
    _extract_repeat_ctx,
    _is_repeat_ctx_dict,
    _loadout_entries_have_db_source,
    _materialize_repeat_task,
    _task_key,
)
from gear_optimizer.solver.native_inflight_timing import _thread_cpu_time_s
from gear_optimizer.solver.native_inflight_types import _NativeSong
from gear_optimizer.solver.inflight_utils import (
    _compact_items,
    _compact_prev_record,
    _truthy,
)
from gear_optimizer.solver.native_inflight_stages import (
    _InFlightStageProfiler,
    _decode_ga_payload_sync,
    _prefetch_db_loadouts_sync,
    _prepare_fg_static_sync,
    _prepare_fg_job_sync,
    _resolve_active_fg_calc_song,
    run_cpu_prewarm_for_song,
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
    except Exception:
        ncpu = 1
    ncpu = max(1, ncpu)
    inflight_limit = max(1, int(inflight_limit))
    kind = str(kind or "").strip().lower()

    # Keep at most half the cores for background prep/decode work by default.
    # (The main thread + GPU owner thread + other overhead still need room.)
    base = max(1, ncpu // 2)
    # On very small machines, don't exceed 2–3 threads per pool.
    if ncpu <= 4:
        base = min(base, 2)
    elif ncpu <= 8:
        base = min(base, 3)

    # FG prep can be more expensive; keep it a bit lower by default.
    if kind in {"fg_prep", "fgprep"}:
        base = max(1, min(base, 2 if ncpu <= 8 else base))
    return max(1, min(inflight_limit, int(base)))


def _read_inflight_event_wait_timeout_s() -> float:
    """
    Base scheduler wait timeout when waiting for in-flight futures to complete.

    Keep this modest to avoid long producer wake-up delays that can starve the
    GPU owner thread between GA/FG stage transitions.
    """
    timeout_s = 0.05
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            timeout_s = float(raw)
        except Exception:
            pass
    return max(0.001, min(float(timeout_s), 5.0))


def _read_inflight_event_wait_gpu_cap_s() -> float:
    # Kept as a wrapper for unit tests and historical call sites.
    return float(read_inflight_event_wait_gpu_cap_s())


def _read_inflight_event_wait_short_spin_s() -> float:
    # Kept as a wrapper for unit tests and historical call sites.
    return float(read_inflight_event_wait_short_spin_s())


def _wait_for_completion_event(
    completion_event: threading.Event,
    *,
    timeout_s: float,
    short_spin_s: float,
) -> bool:
    # Delegate to the shared helper, but pass the module-local time funcs so tests
    # can monkeypatch `native_inflight_orchestrator.time`.
    return bool(
        wait_for_completion_event(
            completion_event,
            timeout_s=float(timeout_s),
            short_spin_s=float(short_spin_s),
            perf_counter=time.perf_counter,
            sleep=time.sleep,
        )
    )


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
        except Exception:
            limit = 0
    if cfg0 is not None:
        try:
            raw_cfg = cfg0.get("IterationEngine", "InFlight_FGStaticPrepMaxInflight", fallback="")
        except Exception:
            raw_cfg = ""
        if str(raw_cfg).strip() != "":
            try:
                limit = int(raw_cfg)
            except Exception:
                limit = 0
    raw_env = os.environ.get("INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT")
    if raw_env is not None and str(raw_env).strip() != "":
        try:
            limit = int(raw_env)
        except Exception:
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
        except Exception:
            raw_cfg = ""
        if str(raw_cfg).strip() != "":
            try:
                lookahead = int(raw_cfg)
            except Exception:
                lookahead = int(default)
    raw_env = os.environ.get("INFLIGHT_CPU_PREWARM_LOOKAHEAD")
    if raw_env is not None and str(raw_env).strip() != "":
        try:
            lookahead = int(raw_env)
        except Exception:
            pass
    return max(0, min(int(lookahead), int(prep_limit), 32))


def run_native_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
    stop_requested=None,
    progress_cb=None,
    bundle_completed_cb=None,
) -> None:
    if not tasks:
        return

    cfg0 = None
    try:
        cfg0 = cfg_from_dict(tasks[0][3] or {})
    except Exception:
        cfg0 = None

    inflight_ram_mode = False
    try:
        raw_env = os.environ.get("INFLIGHT_RAM_MODE")
        if raw_env is not None and str(raw_env).strip() != "":
            inflight_ram_mode = _truthy(raw_env)
        elif cfg0 is not None:
            inflight_ram_mode = cfg0.getboolean("IterationEngine", "InFlight_RamMode", fallback=False)
    except Exception:
        inflight_ram_mode = False

    if inflight_ram_mode:
        # Allow more caching when the user explicitly opts into higher RAM usage.
        pool_cache_max, registry_cache_max, init_heur_cache_max = bump_prep_cache_limits_for_ram_mode()
        try:
            logger.debug(
                "[InFlight][RAM] enabled: default InFlight_GA_QueueMult=4 InFlight_PrepBufferMult=12 "
                f"cache_max={{pool:{int(pool_cache_max)} registry:{int(registry_cache_max)} heur:{int(init_heur_cache_max)}}}"
            )
        except Exception:
            pass

    requested_inflight = max(1, int(in_flight_songs))
    inflight_limit = min(int(requested_inflight), len(tasks))

    # Limit concurrent in-flight songs by available GPU timeline slots.
    # Slot 0 is shared/fallback; we reserve 1..MAX_SONG_SLOTS-1 for deterministic reuse.
    try:
        from gear_optimizer.solver.taichi_gem.fields import MAX_SONG_SLOTS

        max_song_slots = int(MAX_SONG_SLOTS)
    except Exception:
        max_song_slots = 8
    song_slot_limit = max(1, int(max_song_slots) - 1)
    inflight_limit = min(int(inflight_limit), int(song_slot_limit))
    if int(in_flight_songs) > 1:
        try:
            cap_reasons: list[str] = []
            try:
                if int(len(tasks)) < int(requested_inflight):
                    cap_reasons.append(f"queue={int(len(tasks))}")
            except Exception:
                pass
            try:
                if int(song_slot_limit) < int(requested_inflight):
                    cap_reasons.append(f"usable_slots={int(song_slot_limit)}")
            except Exception:
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
        except Exception:
            pass

    target_song_lanes = _read_inflight_target_song_lanes(cfg0, inflight_limit=int(inflight_limit))

    from gear_optimizer.solver.inflight_utils import SongSlotPool

    slot_pool = SongSlotPool(max_song_slots=int(max_song_slots))

    # How deep we allow the GPU-native GA queue to get (number of submitted GA jobs).
    # A deeper backlog reduces GPU idle gaps when CPU-side decode / FG prep briefly stalls.
    ga_queue_mult = 0
    if cfg0 is not None:
        try:
            ga_queue_mult = safe_int(cfg0.get("IterationEngine", "InFlight_GA_QueueMult", fallback="0"), 0)
        except Exception:
            ga_queue_mult = 0
    raw = os.environ.get("INFLIGHT_GA_QUEUE_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_mult = int(raw)
        except Exception:
            pass
    if ga_queue_mult <= 0:
        ga_queue_mult = 4 if inflight_ram_mode else 2
    ga_queue_mult = max(1, min(int(ga_queue_mult), 8))
    ga_queue_limit = max(1, int(inflight_limit) * int(ga_queue_mult))
    ga_queue_limit = min(int(ga_queue_limit), int(song_slot_limit))

    # CPU prep staging buffer size (prepared songs + in-flight preps).
    # Larger buffers avoid starvation on fast GPUs at the cost of RAM.
    prep_buffer_mult = 0
    if cfg0 is not None:
        try:
            prep_buffer_mult = safe_int(cfg0.get("IterationEngine", "InFlight_PrepBufferMult", fallback="0"), 0)
        except Exception:
            prep_buffer_mult = 0
    raw = os.environ.get("INFLIGHT_PREP_BUFFER_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            prep_buffer_mult = int(raw)
        except Exception:
            pass
    if prep_buffer_mult <= 0:
        prep_buffer_mult = 12 if inflight_ram_mode else 4
    prep_buffer_mult = max(1, min(int(prep_buffer_mult), 16))
    prep_limit = max(1, int(inflight_limit) * int(prep_buffer_mult))
    cpu_prewarm_lookahead = _read_cpu_prewarm_lookahead(cfg0, prep_limit=int(prep_limit), default=5)

    # FG aging fairness controls for continuous mode.
    fg_aging_trigger_ms = 750.0
    fg_aging_hard_ms = 2500.0
    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingTriggerMs"):
                fg_aging_trigger_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingTriggerMs", fallback="750"))
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingHardMs"):
                fg_aging_hard_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingHardMs", fallback="2500"))
    except Exception:
        fg_aging_trigger_ms = 750.0
        fg_aging_hard_ms = 2500.0
    raw = os.environ.get("INFLIGHT_FG_AGING_TRIGGER_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_trigger_ms = float(raw)
        except Exception:
            pass
    raw = os.environ.get("INFLIGHT_FG_AGING_HARD_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_hard_ms = float(raw)
        except Exception:
            pass
    fg_aging_trigger_s = max(0.0, float(fg_aging_trigger_ms) / 1000.0)
    fg_aging_hard_s = max(0.0, float(fg_aging_hard_ms) / 1000.0)
    if fg_aging_hard_s > 0.0 and fg_aging_hard_s < fg_aging_trigger_s:
        fg_aging_hard_s = float(fg_aging_trigger_s)

    # ForceGreats scheduling strategy is fixed to continuous mode.
    fg_scheduler_norm = _read_fg_scheduler_mode()

    # `FG_DrainAtEnd` controls whether we drain pending FG jobs when GA work completes.
    #
    # IMPORTANT: This should not "randomly" flip during a run. We parse it once here
    # with explicit semantics:
    # - default: True (ensures every song gets FG evaluated)
    # - config: parse truthy strings ("1/true/yes/on")
    # - env override: `INFLIGHT_FG_DRAIN_AT_END` or `FG_DRAIN_AT_END` (same truthy parsing)
    fg_drain_at_end = True
    fg_drain_src = "default(true)"
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "FG_DrainAtEnd"):
            raw = str(cfg0.get("IterationEngine", "FG_DrainAtEnd", fallback="") or "").strip()
            fg_drain_at_end = _truthy(raw)
            fg_drain_src = f"config({raw})"
        elif cfg0 is not None:
            fg_drain_src = "config(missing->false)"
    except Exception as exc:
        fg_drain_at_end = False
        fg_drain_src = f"config_error({type(exc).__name__})"
    raw_env = os.environ.get("INFLIGHT_FG_DRAIN_AT_END")
    if raw_env is None or str(raw_env).strip() == "":
        raw_env = os.environ.get("FG_DRAIN_AT_END")
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
    except Exception:
        pass

    inflight_fg_hold_slots = True
    try:
        if cfg0 is not None:
            inflight_fg_hold_slots = cfg0.getboolean("IterationEngine", "InFlight_FGHoldSlots", fallback=True)
    except Exception:
        inflight_fg_hold_slots = True
    hold_slots_explicit = False
    try:
        if cfg0 is not None:
            hold_slots_explicit = bool(cfg0.has_option("IterationEngine", "InFlight_FGHoldSlots"))
    except Exception:
        hold_slots_explicit = False
    raw = os.environ.get("INFLIGHT_FG_HOLD_SLOTS")
    if raw is not None and str(raw).strip() != "":
        hold_slots_explicit = True
        inflight_fg_hold_slots = _truthy(raw)

    # Slot pressure hint + safety:
    # `InFlight_FGHoldSlots=true` keeps timeline slots reserved after GA completes so FG can reuse resident grids.
    # This only works when there is enough spare slot capacity beyond the GA queue depth; otherwise the run
    # will inevitably hit slot-acquire stalls and start FG early (often looking like "GA -> FG per song").
    try:
        from gear_optimizer.core.config import read_iteration_engine_settings

        ie = read_iteration_engine_settings(cfg0)
        fg_enabled = bool(ie.force_greats_mode) and (bool(ie.force_greats_finder) or bool(ie.manual_force_greats))
    except Exception:
        fg_enabled = False

    # Reserve a dedicated FG slot partition so GA cannot consume every slot.
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
        # Enable by default only when inflight + FG are both active, because dynamic queue
        # sizing primarily exists to mitigate GA/FG song-slot pressure.
        inflight_ga_dynamic_queue = bool(fg_enabled and int(in_flight_songs) > 1)
    except Exception:
        inflight_ga_dynamic_queue = False
    try:
        if cfg0 is not None:
            inflight_ga_dynamic_queue = cfg0.getboolean(
                "IterationEngine",
                "InFlight_GA_DynamicQueue",
                fallback=bool(inflight_ga_dynamic_queue),
            )
    except Exception:
        pass
    raw = os.environ.get("INFLIGHT_GA_DYNAMIC_QUEUE")
    if raw is not None and str(raw).strip() != "":
        inflight_ga_dynamic_queue = _truthy(raw)

    # Reserve extra free slots when we have recently hit GA slot-acquire stalls.
    ga_queue_extra_free_on_slot_pressure = 1
    try:
        if cfg0 is not None:
            ga_queue_extra_free_on_slot_pressure = safe_int(
                cfg0.get("IterationEngine", "InFlight_GA_ExtraFreeSlotsOnSlotPressure", fallback="1"),
                1,
            )
    except Exception:
        ga_queue_extra_free_on_slot_pressure = 1
    raw = os.environ.get("INFLIGHT_GA_EXTRA_FREE_SLOTS_ON_SLOT_PRESSURE")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_extra_free_on_slot_pressure = int(raw)
        except Exception:
            pass
    ga_queue_extra_free_on_slot_pressure = max(0, min(int(ga_queue_extra_free_on_slot_pressure), 8))

    ga_queue_pressure_window_s = 1.5
    try:
        if cfg0 is not None:
            ga_queue_pressure_window_s = float(
                cfg0.get("IterationEngine", "InFlight_GA_SlotPressureWindowSec", fallback="1.5")
            )
    except Exception:
        ga_queue_pressure_window_s = 1.5
    raw = os.environ.get("INFLIGHT_GA_SLOT_PRESSURE_WINDOW_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_pressure_window_s = float(raw)
        except Exception:
            pass
    ga_queue_pressure_window_s = max(0.0, min(float(ga_queue_pressure_window_s), 60.0))

    ga_slack_slots = 0
    try:
        ga_slack_slots = max(0, int(song_slot_limit) - int(ga_queue_limit))
    except Exception:
        ga_slack_slots = 0

    fg_hold_budget = int(ga_slack_slots)

    if inflight_fg_hold_slots and fg_enabled and int(in_flight_songs) > 1:
        if int(fg_hold_budget) <= 0:
            required_gpu_slots = None
            try:
                required_usable = int(ga_queue_limit)
                required_gpu_slots = int(required_usable) + 1
            except Exception:
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
            except Exception:
                pass
            # No slack beyond the GA queue depth: any attempt to hold FG slots will eventually starve GA.
            # If the user didn't explicitly request hold-slots behavior, prefer throughput stability.
            if not hold_slots_explicit:
                inflight_fg_hold_slots = False
                fg_hold_budget = 0
                try:
                    logger.debug("[InFlight][Auto] Disabling InFlight_FGHoldSlots (no slack song slots available).")
                except Exception:
                    pass

    # Configure GPU-native GA run buffers BEFORE the GPU executor initializes Taichi fields.
    # The executor warms FG kernels on startup which triggers taichi_gem field allocation; if
    # we don't size buffers up front, GA payload downloads become padded and require staging.
    try:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields

        ga_runs = 1
        try:
            from gear_optimizer.data.models import GASettings

            settings = GASettings.from_cfg(cfg0) if cfg0 is not None else GASettings.from_cfg(None)
            ga_runs = int(settings.multi_start)
        except Exception:
            ga_runs = 1

        gpu_fields.configure_ga_run_buffers(max_runs=ga_runs, max_genomes=GA_POPULATION_SIZE)
    except Exception:
        pass

    # Windows: short timed waits (0-10ms) can quantize into ~15.6ms bubbles when the system timer
    # period is left at the default. Native in-flight mode is explicitly throughput-focused and
    # benefits significantly from 1ms timer granularity in the GPU owner thread/coalescer.
    #
    # Keep this override opt-out: users can set `GPU_ALLOW_SYSTEM_TIMER_OVERRIDE=0` to disable.
    try:
        if os.name == "nt" and os.environ.get("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE") is None:
            os.environ["GPU_ALLOW_SYSTEM_TIMER_OVERRIDE"] = "1"
            if _truthy(os.environ.get("PERF_TIMING", "0")):
                logger.debug(
                    "[InFlight][Perf] Enabled 1ms Windows timer period for GPU batching "
                    "(set GPU_ALLOW_SYSTEM_TIMER_OVERRIDE=0 to disable)."
                )
    except Exception:
        pass

    gpu_executor = get_gpu_executor()
    if progress_cb is not None:
        # Make startup visible in the TUI: Taichi/Vulkan init + warmup can take noticeable time on cold caches.
        try:
            progress_cb(completed_delta=0, failed_delta=0, record_info={"status": "GPU init (Taichi/Vulkan)"})
        except Exception:
            pass
    gpu_executor.start(in_process=True)
    try:
        # GPU readiness includes Taichi/Vulkan init plus the configured GA/FG warmups. On cold
        # Windows/Vulkan caches, that warmup can be minute-scale; do not let work queue behind an
        # owner that is not accepting requests yet.
        init_timeout = float(os.environ.get("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "600") or "600")
    except Exception:
        init_timeout = 180.0
    if not gpu_executor.wait_until_ready(timeout=init_timeout):
        err = getattr(gpu_executor, "last_init_error", None)
        msg = "[InFlight] GPU executor Taichi init failed or timed out"
        if err:
            msg = f"{msg} ({err})"
        try:
            gpu_executor.stop()
        except Exception:
            pass
        raise RuntimeError(msg)
    if progress_cb is not None:
        # Executor is initialized and warm; requests submitted after this point can be processed.
        try:
            progress_cb(completed_delta=0, failed_delta=0, record_info={"status": "GPU warmup (Taichi JIT)"})
        except Exception:
            pass
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    stage_profile_enabled = _truthy(os.environ.get("INFLIGHT_STAGE_PROFILE", "0"))
    stage_profile_path = os.environ.get("INFLIGHT_STAGE_PROFILE_PATH")
    if stage_profile_enabled and not stage_profile_path:
        try:
            from gear_optimizer.core.constants import PATHS

            stage_profile_path = PATHS.bin_path("inflight_stage_profile.json")
        except Exception:
            stage_profile_path = None
    stage_profiler = _InFlightStageProfiler(enabled=stage_profile_enabled, out_path=stage_profile_path)

    post_sender = _PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
    fg_decision_debug = _truthy(os.environ.get("INFLIGHT_FG_DECISION_DEBUG", "0"))
    fg_submit_debug = _truthy(os.environ.get("INFLIGHT_FG_SUBMIT_DEBUG", "0"))

    # Progress UI "New" counter should reflect *session-best* improvements, not the stale DB snapshot
    # that in-flight tasks can start with (DB persistence is async, and many repeats can overlap).
    progress_best_lock = threading.Lock()
    progress_best: dict[str, tuple[int, int]] = {}
    progress_best_valid: set[str] = set()

    def _progress_best_snapshot(db_key: str) -> tuple[int, int, bool]:
        key = str(db_key or "").strip()
        if not key:
            return (0, 0, False)
        with progress_best_lock:
            score0, fg0 = progress_best.get(key, (0, 0))
            return (int(score0), int(fg0), key in progress_best_valid)

    def _progress_best_update(
        db_key: str,
        *,
        best_score: int | None = None,
        best_fg: int | None = None,
        mark_valid: bool = False,
    ) -> None:
        key = str(db_key or "").strip()
        if not key:
            return
        try:
            score_new = int(best_score) if best_score is not None else None
        except Exception:
            score_new = None
        try:
            fg_new = int(best_fg) if best_fg is not None else None
        except Exception:
            fg_new = None
        with progress_best_lock:
            score0, fg0 = progress_best.get(key, (0, 0))
            if score_new is not None and score_new > int(score0):
                score0 = int(score_new)
            if fg_new is not None and fg_new > int(fg0):
                fg0 = int(fg_new)
            progress_best[key] = (int(score0), int(fg0))
            if mark_valid:
                progress_best_valid.add(key)

    def _emit_progress(*, completed_delta: int = 0, failed_delta: int = 0, record_info: dict | None = None) -> None:
        if progress_cb is None:
            return
        try:
            progress_cb(completed_delta=completed_delta, failed_delta=failed_delta, record_info=record_info)
        except Exception:
            pass

    def _post(item: dict) -> None:
        if post_sender is not None:
            post_sender.send(item)
        if isinstance(item, dict) and item.get("_error") and not bool(item.get("_suppress_progress")):
            try:
                song_label = (
                    item.get("song")
                    or item.get("_song_name")
                    or item.get("song_name")
                    or item.get("_queue_label")
                    or item.get("_queue_key")
                )
            except Exception:
                song_label = None
            _emit_progress(
                completed_delta=1,
                failed_delta=1,
                record_info={"song": song_label, "status": "FAILED"},
            )

    pending_tasks = deque(t for t in tasks if _task_key(t) not in completed_songs)
    bundle_progress: dict[int, int] = {}
    prepared: deque[_NativeSong] = deque()
    pending_fg: deque[_NativeSong] = deque()

    def _bundle_runs(task: tuple) -> list[dict]:
        bundle = _extract_repeat_bundle(task)
        if not isinstance(bundle, dict):
            return []
        runs = bundle.get("runs")
        if not isinstance(runs, list):
            return []
        out: list[dict] = []
        for ctx in runs:
            if _is_repeat_ctx_dict(ctx):
                out.append(dict(ctx))
        return out

    def _next_logical_task(task: tuple) -> tuple[tuple, dict | None]:
        runs = _bundle_runs(task)
        if not runs:
            return task, None
        cursor = max(0, int(bundle_progress.get(id(task), 0)))
        if cursor >= len(runs):
            cursor = len(runs) - 1
        repeat_ctx = dict(runs[cursor])
        return _materialize_repeat_task(task, repeat_ctx), repeat_ctx

    def _bind_bundle_song(song: _NativeSong, parent_task: tuple, repeat_ctx: dict | None) -> None:
        if repeat_ctx is None or not _bundle_runs(parent_task):
            return
        setattr(song, "_bundle_parent_task", parent_task)
        setattr(song, "_bundle_task_key", _task_key(parent_task))
        try:
            setattr(song, "_bundle_repeat_index", int(repeat_ctx.get("repeat_index") or 0))
            setattr(song, "_bundle_repeat_total", int(repeat_ctx.get("repeat_total") or 0))
        except Exception:
            setattr(song, "_bundle_repeat_index", 0)
            setattr(song, "_bundle_repeat_total", 0)

    def _advance_bundle(
        parent_task: tuple, *, song_name: str, record_info: dict | None = None, failed: bool = False
    ) -> bool:
        runs = _bundle_runs(parent_task)
        if not runs:
            return False
        next_idx = max(0, int(bundle_progress.get(id(parent_task), 0))) + 1
        bundle_progress[id(parent_task)] = int(next_idx)

        # Bundled repeats behave like a queue "inflation" to N repeat-runs, but the optimizer queues them as
        # a single bundle to reduce overhead. Emit progress once per repeat-run so the UI/throughput reflects
        # real work (and so repeat failures are visible).
        info: dict = {}
        if isinstance(record_info, dict):
            try:
                info = dict(record_info)
            except Exception:
                info = {}

        repeat_label = None
        try:
            ctx = runs[int(next_idx) - 1] if int(next_idx) > 0 and int(next_idx) <= len(runs) else None
            if _is_repeat_ctx_dict(ctx):
                ridx = int(ctx.get("repeat_index") or next_idx)
                rtotal = int(ctx.get("repeat_total") or len(runs))
                if ridx > 0 and rtotal > 1:
                    repeat_label = f"{song_name} (Run {ridx}/{rtotal})"
        except Exception:
            repeat_label = None

        info.setdefault("song", repeat_label or song_name)
        info.setdefault("status", "FAILED" if failed else "DONE")

        _emit_progress(
            completed_delta=1,
            failed_delta=1 if failed else 0,
            record_info=info,
        )

        if next_idx < len(runs):
            pending_tasks.appendleft(parent_task)
            return True

        bundle_key = _task_key(parent_task)
        completed_songs.add(bundle_key)
        if memory_resume_tracker:
            memory_resume_tracker.mark_completed(song_name)
        if bundle_completed_cb is not None:
            try:
                bundle_completed_cb(bundle_key, completed_songs)
            except Exception:
                pass
        return True

    # GA jobs submitted to the GPU executor (in-order). We intentionally keep a
    # backlog so CPU-side decode/post-processing can't create GPU idle gaps.
    ga_inflight: deque[_NativeSong] = deque()

    ga_seed = str(os.environ.get("GA_SEED") or "").strip()
    prep_workers = 0
    if cfg0 is not None:
        try:
            prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_PrepWorkers", fallback="0"), 0)
        except Exception:
            prep_workers = 0
    raw = os.environ.get("INFLIGHT_PREP_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            prep_workers = int(raw)
        except Exception:
            pass
    if prep_workers <= 0:
        if ga_seed:
            prep_workers = 1
        else:
            prep_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="prep")

    prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=prep_workers, thread_name_prefix="SongPrep")
    prep_inflight: deque[tuple[tuple, tuple, concurrent.futures.Future, float]] = deque()

    cpu_prewarm_workers = 0
    if int(cpu_prewarm_lookahead) > 0:
        if cfg0 is not None:
            try:
                cpu_prewarm_workers = safe_int(
                    cfg0.get("IterationEngine", "InFlight_CPUPrewarmWorkers", fallback="0"),
                    0,
                )
            except Exception:
                cpu_prewarm_workers = 0
        raw = os.environ.get("INFLIGHT_CPU_PREWARM_WORKERS")
        if raw is not None and str(raw).strip() != "":
            try:
                cpu_prewarm_workers = int(raw)
            except Exception:
                pass
        if cpu_prewarm_workers <= 0:
            cpu_prewarm_workers = min(2, max(1, _default_worker_threads(inflight_limit=inflight_limit, kind="prep")))
        cpu_prewarm_workers = max(1, min(int(cpu_prewarm_workers), int(cpu_prewarm_lookahead), 4))
    cpu_prewarm_executor = (
        concurrent.futures.ThreadPoolExecutor(
            max_workers=int(cpu_prewarm_workers),
            thread_name_prefix="CPUPrewarm",
        )
        if int(cpu_prewarm_workers) > 0
        else None
    )
    cpu_prewarm_inflight: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()

    decode_workers = 0
    if cfg0 is not None:
        try:
            decode_workers = safe_int(cfg0.get("IterationEngine", "InFlight_DecodeWorkers", fallback="0"), 0)
        except Exception:
            decode_workers = 0
    raw = os.environ.get("INFLIGHT_DECODE_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            decode_workers = int(raw)
        except Exception:
            pass
    if decode_workers <= 0:
        decode_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="decode")
    decode_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=decode_workers,
        thread_name_prefix="GADecode",
    )
    decode_inflight: deque[_NativeSong] = deque()

    active_runtime_song_label = ""

    def _active_runtime_song() -> str:
        try:
            if ga_inflight:
                song = ga_inflight[0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        try:
            if decode_inflight:
                song = decode_inflight[0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        try:
            if fg_futures:
                song = fg_futures[0][0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        return ""

    def _emit_active_runtime_song(*, force: bool = False) -> None:
        nonlocal active_runtime_song_label
        song_label = _active_runtime_song()
        if not force and song_label == active_runtime_song_label:
            return
        active_runtime_song_label = str(song_label or "").strip()
        if not active_runtime_song_label:
            return
        _emit_progress(
            completed_delta=0,
            failed_delta=0,
            record_info={"song": active_runtime_song_label, "status": "RUNNING"},
        )

    fg_pipeline_settings = read_native_fg_pipeline_settings(
        cfg0,
        inflight_limit=int(inflight_limit),
        ga_credit_budget_cfg=int(fg_ga_credit_budget_cfg),
        default_worker_threads=_default_worker_threads,
    )
    fg_pipeline = NativeFGPipeline(fg_pipeline_settings)
    pending_fg = fg_pipeline.pending
    fg_prep_inflight = fg_pipeline.prep_inflight
    fg_futures = fg_pipeline.futures
    post_emit_pending: deque[_NativeSong] = deque()
    fg_workers = int(fg_pipeline.workers)
    fg_batch_max = int(fg_pipeline.batch_max)
    fg_prep_workers = int(fg_pipeline.prep_workers)
    fg_static_prep_max_inflight = _read_fg_static_prep_max_inflight(
        cfg0,
        fg_prep_workers=int(fg_prep_workers),
        inflight_limit=int(inflight_limit),
        cpu_prewarm_lookahead=int(cpu_prewarm_lookahead),
    )

    db_prefetch_workers = 0
    if cfg0 is not None:
        try:
            db_prefetch_workers = safe_int(cfg0.get("IterationEngine", "InFlight_DBPrefetchWorkers", fallback="0"), 0)
        except Exception:
            db_prefetch_workers = 0
    raw = os.environ.get("INFLIGHT_DB_PREFETCH_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            db_prefetch_workers = int(raw)
        except Exception:
            pass
    if db_prefetch_workers <= 0:
        db_prefetch_workers = max(1, min(int(fg_prep_workers), 4))
    db_prefetch_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=int(db_prefetch_workers),
        thread_name_prefix="FGDBPrefetch",
    )

    cpu_prewarm_submitted: set[str] = set()

    last_slot_block_t: float | None = None
    ga_queue_debug = _truthy(os.environ.get("INFLIGHT_GA_QUEUE_DEBUG", "0"))
    last_ga_queue_limit_effective: int | None = None
    completion_event = threading.Event()
    completion_future_ids: set[int] = set()
    completion_lock = threading.Lock()
    completion_registered_attr = "_metafinder_completion_registered"
    ga_queue_limit_cache_key: tuple[bool, int, int, int, int] | None = None
    ga_queue_limit_cache_value = int(ga_queue_limit_base)
    stop_poll_interval_s = 0.05
    stop_next_check_mono = 0.0
    stop_cached_requested = False
    memory_poll_interval_s = 0.05
    memory_next_check_mono = 0.0
    memory_cached_requested = False
    gpu_abort_requested = False
    lane_fill_hold_count = 0

    def _active_song_lane_count() -> int:
        keys: set[str] = set()
        for song in ga_inflight:
            try:
                key = str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
            except Exception:
                key = ""
            if key:
                keys.add(key)
        for song in decode_inflight:
            try:
                key = str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
            except Exception:
                key = ""
            if key:
                keys.add(key)
        keys.update(fg_pipeline.active_song_keys())
        return int(len(keys))

    def _active_fg_static_prep_count() -> int:
        count = 0
        seen_ids: set[int] = set()

        def _track(song: _NativeSong) -> None:
            nonlocal count
            try:
                sid = int(id(song))
            except Exception:
                return
            if sid in seen_ids:
                return
            seen_ids.add(sid)
            fut = getattr(song, "fg_static_prep_future", None)
            if fut is None:
                return
            try:
                if fut.done():
                    return
            except Exception:
                return
            count += 1

        for s in ga_inflight:
            _track(s)
        for s in prepared:
            _track(s)
        for s in decode_inflight:
            _track(s)
        for s in pending_fg:
            _track(s)
        for s in fg_prep_inflight:
            _track(s)
        for s, _fut, _t_submit in fg_futures:
            _track(s)
        return int(count)

    def _fg_static_prep_budget() -> int:
        if int(fg_static_prep_max_inflight) <= 0:
            return 0
        # Reserve current late-prep workers first, then let static prep use the
        # remaining runway. This keeps per-song baseline warmup ahead of the
        # owner without starving already-visible FG songs.
        dynamic_fg_prep = max(0, int(len(fg_prep_inflight)))
        spare_workers = max(0, int(fg_prep_workers) - int(dynamic_fg_prep))
        return max(0, min(int(fg_static_prep_max_inflight), int(spare_workers)))

    def _register_completion_future(fut: concurrent.futures.Future | None) -> None:
        if fut is None:
            return
        marked_registered = False
        try:
            if bool(getattr(fut, completion_registered_attr, False)):
                return
            setattr(fut, completion_registered_attr, True)
            marked_registered = True
        except Exception:
            pass
        try:
            fut_id = int(id(fut))
        except Exception:
            if marked_registered:
                try:
                    setattr(fut, completion_registered_attr, False)
                except Exception:
                    pass
            return
        try:
            with completion_lock:
                if fut_id in completion_future_ids:
                    return
                completion_future_ids.add(fut_id)
        except Exception:
            if marked_registered:
                try:
                    setattr(fut, completion_registered_attr, False)
                except Exception:
                    pass
            return

        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            try:
                completion_event.set()
            except Exception:
                pass
            try:
                with completion_lock:
                    completion_future_ids.discard(_fut_id)
            except Exception:
                pass

        try:
            fut.add_done_callback(_on_done)
        except Exception:
            try:
                setattr(fut, completion_registered_attr, False)
            except Exception:
                pass
            try:
                completion_event.set()
            except Exception:
                pass

    def _run_cpu_prewarm_sync(song: _NativeSong) -> None:
        run_cpu_prewarm_for_song(song)

    def _task_label_for_prewarm(song: _NativeSong) -> str:
        try:
            return str(getattr(song, "task_key", "") or getattr(song, "song_name", "") or id(song))
        except Exception:
            return str(id(song))

    def _submit_cpu_prewarm(song: _NativeSong) -> bool:
        if cpu_prewarm_executor is None or int(cpu_prewarm_lookahead) <= 0:
            return False
        task_key = _task_label_for_prewarm(song)
        if task_key in cpu_prewarm_submitted:
            return False
        if getattr(song, "cpu_prewarm_future", None) is not None:
            return False
        cpu_prewarm_submitted.add(task_key)
        try:
            setattr(song, "_cpu_prewarm_submit_t0", time.perf_counter())
            fut = cpu_prewarm_executor.submit(_run_cpu_prewarm_sync, song)
            song.cpu_prewarm_future = fut
            cpu_prewarm_inflight.append((song, fut, time.perf_counter()))
            _register_completion_future(fut)
            return True
        except Exception:
            try:
                cpu_prewarm_submitted.discard(task_key)
            except Exception:
                pass
            try:
                song.cpu_prewarm_future = None
            except Exception:
                pass
            return False

    def _submit_fg_static_prewarm(song: _NativeSong) -> bool:
        if int(fg_static_prep_max_inflight) <= 0:
            return False
        if not bool(getattr(song, "manual_force_greats", False) or getattr(song, "force_greats_finder", False)):
            return False
        if getattr(song, "fg_static_prep_future", None) is not None or bool(getattr(song, "_fg_static_prep_done", False)):
            return False
        if int(_active_fg_static_prep_count()) >= int(_fg_static_prep_budget()):
            return False
        try:
            setattr(song, "_fg_static_prep_submit_t0", time.perf_counter())
            static_future = fg_pipeline.prep_executor.submit(_prepare_fg_static_sync, song)
            song.fg_static_prep_future = static_future
            _register_completion_future(static_future)
            return True
        except Exception:
            try:
                song.fg_static_prep_future = None
            except Exception:
                pass
            return False

    def _submit_cpu_prewarm_backlog() -> int:
        if int(cpu_prewarm_lookahead) <= 0:
            return 0
        started = 0
        for idx, song in enumerate(list(prepared)):
            if idx >= int(cpu_prewarm_lookahead):
                break
            if _submit_cpu_prewarm(song):
                started += 1
            if _submit_fg_static_prewarm(song):
                started += 1
        return int(started)

    def _finish_cpu_prewarm_jobs() -> int:
        finished = 0
        for song, fut, t_submit in list(cpu_prewarm_inflight):
            if not fut.done():
                continue
            cpu_prewarm_inflight.remove((song, fut, t_submit))
            finished += 1
            try:
                fut.result()
                stage_profiler.record(
                    "cpu_prewarm",
                    time.perf_counter() - float(t_submit),
                    cpu_seconds=None,
                    song=_task_label_for_prewarm(song),
                )
            except Exception:
                # Prewarm is an accelerator only; the dispatch path will rebuild
                # synchronously if the background attempt failed.
                try:
                    cpu_prewarm_submitted.discard(_task_label_for_prewarm(song))
                except Exception:
                    pass
            finally:
                try:
                    song.cpu_prewarm_future = None
                except Exception:
                    pass
        return int(finished)

    def _effective_ga_queue_limit() -> int:
        nonlocal ga_queue_limit_cache_key, ga_queue_limit_cache_value
        if not inflight_ga_dynamic_queue:
            return int(ga_queue_limit_base)

        extra_free = 0
        slot_pressure_active = False

        if last_slot_block_t is not None and ga_queue_pressure_window_s > 0.0:
            try:
                if (time.monotonic() - float(last_slot_block_t)) <= float(ga_queue_pressure_window_s):
                    slot_pressure_active = True
                    extra_free = max(int(extra_free), int(ga_queue_extra_free_on_slot_pressure))
            except Exception:
                pass

        cache_key = (
            bool(slot_pressure_active),
            int(extra_free),
            int(fg_slot_reserve),
            int(song_slot_limit),
            int(ga_queue_limit_base),
        )
        if cache_key == ga_queue_limit_cache_key:
            return int(ga_queue_limit_cache_value)

        min_free = int(fg_slot_reserve) + int(extra_free)
        # Keep at least 1 slot usable; (song_slot_limit - min_free) must be >= 1.
        min_free = max(0, min(int(min_free), max(0, int(song_slot_limit) - 1)))
        limit_from_free = max(1, int(song_slot_limit) - int(min_free))
        ga_queue_limit_cache_value = max(1, min(int(ga_queue_limit_base), int(limit_from_free)))
        ga_queue_limit_cache_key = cache_key
        return int(ga_queue_limit_cache_value)

    def _current_ga_queue_limit() -> int:
        return int(
            _continuous_ga_warm_queue_limit(
                ga_queue_limit=_effective_ga_queue_limit(),
                inflight_limit=int(inflight_limit),
                fg_enabled=bool(fg_enabled),
                prepared_count=len(prepared),
                prep_inflight_count=len(prep_inflight),
                decode_inflight_count=len(decode_inflight),
                pending_fg_count=len(pending_fg),
                fg_prep_inflight_count=len(fg_prep_inflight),
                fg_inflight_count=len(fg_futures),
                target_song_lanes=int(target_song_lanes),
                active_song_lanes=int(_active_song_lane_count()),
                dispatch_burst=int(continuous_ga_dispatch_burst),
            )
        )

    def _stop_requested_cached(now_mono: float | None = None) -> bool:
        nonlocal stop_next_check_mono, stop_cached_requested
        if stop_cached_requested:
            return True
        if stop_requested is None or not callable(stop_requested):
            return False
        now_val = float(time.monotonic() if now_mono is None else now_mono)
        if now_val < float(stop_next_check_mono):
            return False
        stop_cached_requested = bool(stop_requested())
        if stop_cached_requested:
            return True
        stop_next_check_mono = now_val + float(stop_poll_interval_s)
        return False

    def _memory_release_requested_cached(now_mono: float | None = None) -> bool:
        nonlocal memory_next_check_mono, memory_cached_requested
        if memory_cached_requested:
            return True
        now_val = float(time.monotonic() if now_mono is None else now_mono)
        if now_val < float(memory_next_check_mono):
            return False
        memory_cached_requested = bool(memory_release_requested())
        if memory_cached_requested:
            return True
        memory_next_check_mono = now_val + float(memory_poll_interval_s)
        return False

    def _has_waitable_futures() -> bool:
        if ga_inflight or prep_inflight or cpu_prewarm_inflight or decode_inflight or fg_prep_inflight or fg_futures:
            return True
        for song in pending_fg:
            if song.db_loadouts_future is not None:
                return True
        return False

    def _log_abort(exc: Exception) -> None:
        try:
            from gear_optimizer.core.constants import PATHS

            path = PATHS.bin_path("inflight_native_abort.log")
        except Exception:
            path = None
        if not path:
            return
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            snapshot = (
                f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)}"
            )
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{ts}] {type(exc).__name__}: {exc}\n")
                fh.write(snapshot + "\n")
                fh.write(traceback.format_exc() + "\n")
        except Exception:
            pass

    def _request_gpu_abort(reason: str) -> None:
        nonlocal gpu_abort_requested
        if gpu_abort_requested:
            return
        gpu_abort_requested = True
        try:
            gpu_executor.request_abort(str(reason or "stop requested"))
        except Exception:
            pass

    def _is_stop_abort_exception(exc: BaseException) -> bool:
        if isinstance(exc, concurrent.futures.CancelledError):
            return True
        try:
            msg = str(exc or "")
        except Exception:
            msg = ""
        return "GpuExecutor aborted:" in msg

    # Prime the pipeline: pre-prepare a backlog synchronously so the GPU queue
    # doesn't starve on early song boundaries while prep workers spin up.
    #
    # High-end GPUs can burn through the first GA jobs quickly; priming only 1–2 songs
    # can still leave the GPU idle while CPU prep catches up. Default to priming up to
    # a modest 4-8 song backlog on smaller in-flight runs, but allow override via env
    # var/config for experimentation.
    prime_target = 0
    if cfg0 is not None:
        try:
            prime_target = safe_int(cfg0.get("IterationEngine", "InFlight_PrimeTarget", fallback="0"), 0)
        except Exception:
            prime_target = 0
    raw = os.environ.get("INFLIGHT_PRIME_TARGET")
    if raw is not None and str(raw).strip() != "":
        try:
            prime_target = int(raw)
        except Exception:
            pass
    if prime_target <= 0:
        prime_target = _default_prime_target(
            inflight_limit=inflight_limit,
            prep_limit=prep_limit,
            pending_count=len(pending_tasks),
        )
    else:
        prime_target = max(0, min(int(prime_target), int(prep_limit), len(pending_tasks)))
    for _ in range(int(prime_target)):
        first = pending_tasks.popleft()
        song_name = first[1]
        bundle_key = _task_key(first)
        if bundle_key in completed_songs:
            continue
        logical_task, repeat_ctx = _next_logical_task(first)
        task_key = _task_key(logical_task)
        try:
            t0 = time.perf_counter()
            prepared_song = _prepare_song(logical_task)
            _bind_bundle_song(prepared_song, first, repeat_ctx)
            prepared.append(prepared_song)
            stage_profiler.record(
                "prep",
                time.perf_counter() - t0,
                cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                song=task_key,
            )
        except Exception as exc:
            payload = build_error_payload(
                song_name=str(song_name),
                queue_key=str(task_key),
                queue_label=str(task_key),
                exc=exc,
                trace=traceback.format_exc(),
            )
            if repeat_ctx is not None:
                payload["_suppress_progress"] = True
            _post(payload)
            if repeat_ctx is not None:
                _advance_bundle(first, song_name=str(song_name), failed=True)
            else:
                completed_songs.add(task_key)
                if memory_resume_tracker:
                    memory_resume_tracker.mark_completed(song_name)

    _submit_cpu_prewarm_backlog()

    def _pop_next_fg(*, allow_not_ready: bool) -> Optional[_NativeSong]:
        return fg_pipeline.pop_next(allow_not_ready=allow_not_ready)

    def _oldest_pending_fg_wait_s(now_s: float) -> float:
        return fg_pipeline.oldest_wait_s(float(now_s))

    def _ready_pending_fg_count() -> int:
        return fg_pipeline.ready_count()

    def _emit_deferred_post_payload(song: _NativeSong) -> None:
        if bool(getattr(song, "_deferred_post_emitted", False)):
            return

        best_data_for_post = song.best_data or {}
        best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
        candidates_for_post = (
            song.ga_persistence_candidates
            if isinstance(getattr(song, "ga_persistence_candidates", None), list)
            and getattr(song, "ga_persistence_candidates", None)
            else song.ga_candidates
        )
        candidates_for_post = select_effective_unique_ga_candidates(
            list(candidates_for_post or []),
            limit=int(LOADOUTS_PER_SONG_LIMIT),
            registry=song.registry,
            minis_by_name=song.minis_by_name,
            primary_color=str(song.meta_primary_color or ""),
            secondary_color=str(song.meta_secondary_color or ""),
            selected_color=str((song.cfg_data or {}).get("selected_color", "") or ""),
        )
        ga_candidates_post: list[dict] = []
        for cand in candidates_for_post or []:
            if not isinstance(cand, dict):
                continue
            data0 = cand.get("Data") or {}
            candidate_for_post = dict(cand)
            candidate_for_post["Data"] = dict(data0) if isinstance(data0, dict) else {}
            gear_names, mini_names = materialize_candidate_names(
                candidate_for_post,
                registry=song.registry,
                mutate=False,
            )
            ga_candidates_post.append(
                {
                    "Score": candidate_for_post.get("Score", 0),
                    "BaseScore": candidate_for_post.get("BaseScore", candidate_for_post.get("Score", 0)),
                    "Gear": list(gear_names),
                    "Minis": list(mini_names),
                    "Data": candidate_for_post.get("Data") or {},
                    "_fg_priority": candidate_for_post.get("_fg_priority", 0),
                    "loadout_hash": candidate_for_post.get("loadout_hash"),
                }
            )

        _post(
            {
                "_deferred_post": True,
                "_pending_fg_job": bool(song.manual_force_greats or song.force_greats_finder),
                "song": song.song_name,
                "_queue_key": song.task_key,
                "_queue_label": song.task_key,
                "_ga_seed": song.ga_seed,
                "db_key": song.db_key,
                "file_path": song.fp,
                "difficulty": song.effective_difficulty,
                "use_evo_db": bool(song.use_evo_db),
                "cfg_dict": song.cfg_dict,
                "ref_arrays": song.ref_arrays if song.fg_debug else None,
                "calc_song": song.calc_song if song.fg_debug else None,
                "best_data": best_data_post,
                "best_gear": _compact_items(song.best_gear),
                "best_minis": _compact_items(song.best_minis),
                "current_gear": _compact_items(song.current_gear_list),
                "current_minis": _compact_items(song.current_mini_list),
                "enable_gear": bool(song.enable_gear),
                "enable_mini": bool(song.enable_mini),
                "fg_variants": [],
                "ga_candidates": ga_candidates_post,
                "loadout_entries": None,
                "_persist_pending_fg_job": bool(not fg_drain_at_end),
                "prev_record": _compact_prev_record(song.prev_record),
                "attempt_lifetime": int(song.attempt_lifetime or 0),
                "prev_attempts_first": int(song.prev_attempts_first or 0),
                "db_best_fg_score": int(song.db_best_fg_score or 0),
                "meta_primary_color": song.meta_primary_color,
                "meta_secondary_color": song.meta_secondary_color,
                "fg_debug": bool(song.fg_debug),
                "log": "",
            }
        )

        try:
            song._deferred_post_emitted = True
        except Exception:
            pass

        bundle_parent = getattr(song, "_bundle_parent_task", None)
        needs_fg_stage = bool(song.manual_force_greats or song.force_greats_finder)
        if bundle_parent is not None and needs_fg_stage:
            setattr(song, "_bundle_wait_for_fg", True)
        elif bundle_parent is not None:
            _advance_bundle(
                bundle_parent,
                song_name=str(song.song_name),
                record_info=getattr(song, "record_info", None),
                failed=False,
            )
        elif needs_fg_stage and bool(fg_drain_at_end):
            try:
                song._await_fg_completion_progress = True
            except Exception:
                pass
        else:
            completed_songs.add(song.task_key)
            if memory_resume_tracker:
                memory_resume_tracker.mark_completed(song.song_name)
            if bundle_completed_cb is not None:
                try:
                    bundle_completed_cb(song.task_key, completed_songs)
                except Exception:
                    pass
            try:
                record_info = dict(getattr(song, "record_info", None) or {})
                record_info.setdefault("song", song.task_key or song.song_name)
                record_info.setdefault("status", "DONE")
            except Exception:
                record_info = None
            _emit_progress(completed_delta=1, record_info=record_info)

    def _continuous_note_ga_submit() -> None:
        fg_pipeline.note_ga_submit()

    try:
        last_progress = time.monotonic()
        last_stall_report = last_progress
        last_heartbeat = last_progress
        last_throughput = last_progress
        last_stage_emit = last_progress
        heartbeat_sec = 0.0
        try:
            heartbeat_sec = float(os.environ.get("INFLIGHT_HEARTBEAT_SEC", "0") or "0")
        except Exception:
            heartbeat_sec = 0.0

        throughput_sec = 0.0
        try:
            throughput_sec = float(os.environ.get("INFLIGHT_THROUGHPUT_SEC", "0") or "0")
        except Exception:
            throughput_sec = 0.0

        stage_emit_sec = 0.0
        try:
            stage_emit_sec = float(os.environ.get("INFLIGHT_STAGE_PROFILE_EMIT_SEC", "0") or "0")
        except Exception:
            stage_emit_sec = 0.0

        event_wait_timeout_s = float(_read_inflight_event_wait_timeout_s())
        event_wait_gpu_cap_s = float(read_inflight_event_wait_gpu_cap_s())
        event_wait_short_spin_s = float(read_inflight_event_wait_short_spin_s())

        profile_max_songs = 0
        try:
            profile_max_songs = int(os.environ.get("INFLIGHT_PROFILE_MAX_SONGS", "0") or "0")
        except Exception:
            profile_max_songs = 0
        profile_max_songs = max(0, int(profile_max_songs))
        completed_baseline = 0
        try:
            completed_baseline = int(len(completed_songs))
        except Exception:
            completed_baseline = 0
        bubble_total_idle_s = 0.0
        bubble_peak_kpi = 0.0
        bubble_peak_ready_ga = 0
        bubble_peak_ready_fg = 0
        bubble_peak_backlog = 0
        bubble_peak_oldest_fg_wait_s = 0.0
        bubble_active_started: float | None = None

        def _bubble_snapshot(now_mono: float, *, oldest_fg_wait_s: float = 0.0) -> dict[str, float | int]:
            ready_ga_count = int(len(prepared))
            ready_fg_count = int(_ready_pending_fg_count())
            active_song_lanes = int(_active_song_lane_count())
            backlog_count = int(
                len(pending_tasks)
                + len(prepared)
                + len(prep_inflight)
                + len(cpu_prewarm_inflight)
                + len(decode_inflight)
                + len(pending_fg)
                + len(fg_prep_inflight)
            )
            gpu_idle = (not ga_inflight) and (not fg_futures)
            idle_sec = max(0.0, float(now_mono) - float(last_progress)) if gpu_idle else 0.0
            bubble_kpi = _closed_loop_bubble_kpi(
                idle_sec=float(idle_sec),
                ready_ga_count=int(ready_ga_count),
                ready_fg_count=int(ready_fg_count),
                backlog_count=int(backlog_count),
                oldest_fg_wait_s=float(oldest_fg_wait_s),
            )
            return {
                "idle_sec": float(idle_sec),
                "bubble_kpi": float(bubble_kpi),
                "ready_ga_count": int(ready_ga_count),
                "ready_fg_count": int(ready_fg_count),
                "active_song_lanes": int(active_song_lanes),
                "target_song_lanes": int(target_song_lanes),
                "lane_fill_hold_count": int(lane_fill_hold_count),
                "backlog_count": int(backlog_count),
                "gpu_idle": int(bool(gpu_idle)),
            }

        def _note_bubble_snapshot(snapshot: dict[str, float | int], *, now_mono: float, oldest_fg_wait_s: float) -> None:
            nonlocal bubble_total_idle_s, bubble_peak_kpi, bubble_peak_ready_ga, bubble_peak_ready_fg
            nonlocal bubble_peak_backlog, bubble_peak_oldest_fg_wait_s, bubble_active_started

            bubble_kpi = float(snapshot.get("bubble_kpi", 0.0) or 0.0)
            if bubble_kpi > 0.0:
                if bubble_active_started is None:
                    bubble_active_started = float(now_mono)
                if bubble_kpi >= float(bubble_peak_kpi):
                    bubble_peak_kpi = float(bubble_kpi)
                    bubble_peak_ready_ga = int(snapshot.get("ready_ga_count", 0) or 0)
                    bubble_peak_ready_fg = int(snapshot.get("ready_fg_count", 0) or 0)
                    bubble_peak_backlog = int(snapshot.get("backlog_count", 0) or 0)
                    bubble_peak_oldest_fg_wait_s = max(0.0, float(oldest_fg_wait_s))
                return

            if bubble_active_started is not None:
                bubble_total_idle_s += max(0.0, float(now_mono) - float(bubble_active_started))
                bubble_active_started = None

        stopping = False
        while (
            pending_tasks
            or prepared
            or prep_inflight
            or pending_fg
            or post_emit_pending
            or ga_inflight
            or decode_inflight
            or fg_prep_inflight
            or fg_futures
        ):
            now = time.monotonic()
            if _memory_release_requested_cached(now):
                break

            # Optional profiling cap: stop after N completed songs/tasks.
            if (not stopping) and profile_max_songs > 0:
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now >= int(profile_max_songs):
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass

            if _stop_requested_cached(now):
                if not stopping:
                    stopping = True
                    _request_gpu_abort("native in-flight stop requested")
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass
                    # Best-effort cancel of queued prep/decode work.
                    try:
                        for _task, fut, _t0 in list(prep_inflight):
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                        prep_inflight.clear()
                    except Exception:
                        pass
                    try:
                        for song in list(decode_inflight):
                            try:
                                if song.decode_future is not None:
                                    song.decode_future.cancel()
                            except Exception:
                                pass
                        # Keep entries so we can still drain the deque safely.
                    except Exception:
                        pass

            # Periodic throughput reporting (opt-in via env).
            if throughput_sec > 0 and (now - last_throughput) >= float(throughput_sec):
                last_throughput = now
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now > 0:
                    wall_s = max(1e-9, float(time.perf_counter() - float(stage_profiler._t0)))
                    per_h = float(completed_now) * 3600.0 / wall_s
                    try:
                        pending_now = int(len(pending_tasks)) + int(len(prepared)) + int(len(pending_fg))
                    except Exception:
                        pending_now = 0
                    try:
                        avg_s = wall_s / float(completed_now)
                        eta_s = float(pending_now) * avg_s if pending_now > 0 else 0.0
                    except Exception:
                        avg_s = 0.0
                        eta_s = 0.0
                    try:
                        logger.debug(
                            "[InFlight][Throughput] done=%s pending~%s rate=%.1f/h avg=%.2fs ETA=%.1fm",
                            completed_now,
                            pending_now,
                            per_h,
                            avg_s,
                            eta_s / 60.0,
                        )
                    except Exception:
                        pass
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="throughput",
                        metrics={
                            "completed": int(completed_now),
                            "pending": int(pending_now),
                            "rate_per_hour": float(per_h),
                            "avg_task_sec": float(avg_s),
                            "eta_sec": float(eta_s),
                        },
                    )

            # Periodic stage profile emission (opt-in via env).
            if stage_emit_sec > 0 and stage_profiler.enabled and (now - last_stage_emit) >= float(stage_emit_sec):
                last_stage_emit = now
                try:
                    stage_profiler.emit()
                except Exception:
                    pass

            did_work = False
            blocked_on_slot_acquire = False
            if _finish_cpu_prewarm_jobs() > 0:
                did_work = True

            # Move completed song preps into the staging queue.
            for task, logical_task, fut, t_submit in list(prep_inflight):
                if not fut.done():
                    continue
                prep_inflight.remove((task, logical_task, fut, t_submit))
                did_work = True
                song_name = task[1]
                bundle_key = _task_key(task)
                task_key = _task_key(logical_task)
                if bundle_key in completed_songs:
                    continue
                try:
                    prepared_song = fut.result()
                    repeat_ctx = _extract_repeat_ctx(logical_task)
                    _bind_bundle_song(prepared_song, task, repeat_ctx)
                    stage_profiler.record(
                        "prep",
                        time.perf_counter() - float(t_submit),
                        cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                        song=task_key,
                    )
                    prepared.append(prepared_song)
                    if bool(getattr(prepared_song, "db_baseline_valid", True)):
                        _progress_best_update(
                            prepared_song.db_key,
                            best_score=int(getattr(prepared_song, "db_best_score", 0) or 0),
                            best_fg=int(getattr(prepared_song, "db_best_fg_score", 0) or 0),
                            mark_valid=True,
                    )
                    _submit_cpu_prewarm_backlog()
                except Exception as exc:
                    if stopping and _is_stop_abort_exception(exc):
                        continue
                    payload = build_error_payload(
                        song_name=str(song_name),
                        queue_key=str(task_key),
                        queue_label=str(task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                    )
                    repeat_ctx = _extract_repeat_ctx(logical_task)
                    if repeat_ctx is not None:
                        payload["_suppress_progress"] = True
                    _post(payload)
                    if repeat_ctx is not None:
                        _advance_bundle(task, song_name=str(song_name), failed=True)
                    else:
                        completed_songs.add(task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song_name)

            # Finalize prepared FG jobs (CPU prep done) so the GPU stage can start immediately when scheduled.
            for song in list(fg_prep_inflight):
                # `fg_prep_future` may be consumed by the FG worker (it waits on the
                # future and then clears it). Ensure we still drain the tracking deque
                # so the main loop can terminate cleanly.
                if song.fg_prep_future is None:
                    fg_prep_inflight.remove(song)
                    did_work = True
                    continue
                if not song.fg_prep_future.done():
                    continue
                fg_prep_inflight.remove(song)
                did_work = True
                try:
                    t_submit = getattr(song, "_fg_prep_submit_t0", None)
                    if t_submit is not None:
                        stage_profiler.record(
                            "fg_prep",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(song, "_cpu_fg_prep_s", None),
                            song=song.song_name,
                        )
                        setattr(song, "_fg_prep_submit_t0", None)
                    song.fg_prep_future.result()
                    try:
                        song._fg_dynamic_prep_done = True
                    except Exception:
                        pass
                except Exception as exc:
                    if stopping and _is_stop_abort_exception(exc):
                        pass
                    else:
                        _post(
                            build_error_payload(
                                song_name=str(song.song_name),
                                queue_key=str(song.task_key),
                                queue_label=str(song.task_key),
                                exc=exc,
                                trace=traceback.format_exc(),
                            )
                        )
                finally:
                    song.fg_prep_future = None

            if pending_fg:
                try:
                    started_fg_prep = fg_pipeline.start_pending_prep(
                        _prepare_fg_job_sync,
                        gpu_client=gpu_client,
                        register_future=_register_completion_future,
                    )
                except Exception:
                    started_fg_prep = 0
                if int(started_fg_prep) > 0:
                    did_work = True

            # Keep the GPU queue full while using spare CPU time to prep future songs.
            #
            # - `ga_inflight` bounds the number of submitted GPU-native GA jobs.
            # - `prepared` is a CPU-side staging buffer; keeping it non-empty prevents
            #   starvation if CPU prep briefly falls behind GPU throughput.
            # - We alternate submit/prep to minimize the initial "startup bubble".
            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = _oldest_pending_fg_wait_s(float(now))
            except Exception:
                fg_oldest_wait_s = 0.0

            while True:
                # Submit GA jobs whenever we have prepared work and GPU queue capacity.
                # We allow `ga_inflight` to exceed `inflight_limit` to create a backlog
                # that keeps the GPU fed while CPU decode/FG prep runs.
                if stopping:
                    break
                ga_queue_limit_effective = _current_ga_queue_limit()
                if ga_queue_debug and ga_queue_limit_effective != last_ga_queue_limit_effective:
                    last_ga_queue_limit_effective = int(ga_queue_limit_effective)
                    try:
                        logger.debug(
                            "[InFlight][GAQueue] effective=%s base=%s ga_inflight=%s prepared=%s pending_fg=%s "
                            "fg_prep=%s fg_inflight=%s slot_reserve=%s oldest_fg_wait_ms=%.0f",
                            int(ga_queue_limit_effective),
                            int(ga_queue_limit_base),
                            len(ga_inflight),
                            len(prepared),
                            len(pending_fg),
                            len(fg_prep_inflight),
                            len(fg_futures),
                            int(fg_slot_reserve),
                            fg_oldest_wait_s * 1000.0,
                        )
                    except Exception:
                        pass

                ready_fg_for_ga_admission = _ready_pending_fg_count() if pending_fg else 0
                if _continuous_ga_should_yield_to_fg(
                    fg_enabled=bool(fg_enabled),
                    fg_drain_at_end=bool(fg_drain_at_end),
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_for_ga_admission),
                    fg_prep_inflight_count=len(fg_prep_inflight),
                    fg_inflight_count=len(fg_futures),
                    fg_worker_count=int(fg_workers),
                    target_song_lanes=int(target_song_lanes),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    aging_trigger_s=float(fg_aging_trigger_s),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                ):
                    break

                can_submit_ga = bool(prepared) and len(ga_inflight) < ga_queue_limit_effective

                if can_submit_ga:
                    song = prepared.popleft()
                    # Reserve a per-song GPU timeline slot so GA -> FG can reuse the resident grid
                    # even while other songs are in-flight (avoids clobbering slot 0).
                    if int(getattr(song, "song_slot", 0) or 0) <= 0:
                        try:
                            song.song_slot = int(slot_pool.acquire())
                        except Exception:
                            # No free slots: defer GA submission until FG drains.
                            blocked_on_slot_acquire = True
                            last_slot_block_t = time.monotonic()
                            stage_profiler.record("slot_block", 0.0)
                            prepared.appendleft(song)
                            break
                        try:
                            song.calc_song["_gpu_song_slot"] = int(song.song_slot)
                        except Exception:
                            pass
                    setattr(song, "_outer_engine", "ga")
                    setattr(song, "_ga_submit_t0", time.perf_counter())
                    payload = {
                        "calc_song": song.calc_song,
                        "ref_arrays": song.ref_arrays,
                        "song_slot": int(song.song_slot),
                        "item_stats": song.item_stats,
                        "slot_start": song.slot_start,
                        "slot_count": song.slot_count,
                        "base_fixed_stats_arr": song.base_fixed_stats_arr,
                        "initial_populations": getattr(song, "ga_initial_populations", None),
                        "num_runs": int(song.num_runs),
                        "n_genomes": int(song.n_genomes),
                        "init_heuristic_topk": song.init_heuristic_topk,
                        "init_heuristic_k": int(song.init_heuristic_k),
                        "init_heuristic_copies": int(song.init_heuristic_copies),
                        "db_seed_ids": song.db_seed_ids,
                        "db_seed_prob": float(song.db_seed_prob),
                        "db_seed_copies": int(song.db_seed_copies),
                        "db_seed_mutations": int(song.db_seed_mutations),
                        "n_generations": int(song.gens_per_run),
                        "elite_count": int(song.elite_count),
                        "mutation_rate": float(song.mutation_rate),
                        "immigrant_rate": float(song.immigrant_rate),
                        "tournament_k": int(song.tournament_k),
                        "color_flags": dict(song.color_flags),
                        "cfg_data": dict(song.cfg_data),
                        "ga_seed": song.ga_seed,
                    }
                    try:
                        handle = gpu_client.submit_gpu_native_ga_run(payload)
                    except Exception as exc:
                        # Ensure we don't leak the reserved slot on submission failure.
                        try:
                            slot_pool.release(int(song.song_slot))
                            song.song_slot = 0
                        except Exception:
                            pass
                        payload = build_error_payload(
                            song_name=str(song.song_name),
                            queue_key=str(song.task_key),
                            queue_label=str(song.task_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        bundle_parent = getattr(song, "_bundle_parent_task", None)
                        if bundle_parent is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                        if bundle_parent is not None:
                            _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                        else:
                            completed_songs.add(song.task_key)
                            if memory_resume_tracker:
                                memory_resume_tracker.mark_completed(song.song_name)
                        did_work = True
                        continue

                    song.ga_future = handle.future
                    try:
                        song.ga_initial_populations = None
                    except Exception:
                        pass

                    _register_completion_future(song.ga_future)
                    ga_inflight.append(song)
                    did_work = True
                    _continuous_note_ga_submit()
                    if _submit_cpu_prewarm_backlog() > 0:
                        did_work = True

                    # Prefetch DB loadouts early so FG prep after GA decode doesn't stall
                    # waiting on SQLite reads (keeps the GPU fed during song boundaries).
                    if (
                        (song.manual_force_greats or song.force_greats_finder)
                        and song.use_evo_db
                        and song.db_loadouts_future is None
                        and song.db_loadouts_full is None
                    ):
                        try:
                            prefetch_limit = safe_int(
                                song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
                                FG_CANDIDATE_LIMIT,
                            )
                            baseline_team_buff = "T5"
                            try:
                                from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict

                                baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(
                                    getattr(song, "cfg_dict", None) or {}, default="T5"
                                )
                            except Exception:
                                baseline_team_buff = "T5"
                            song.db_loadouts_future = db_prefetch_executor.submit(
                                _prefetch_db_loadouts_sync,
                                song.db_key,
                                limit=int(prefetch_limit),
                                gears_by_name=song.gears_by_name,
                                minis_by_name=song.minis_by_name,
                                team_buff=str(baseline_team_buff or "T5"),
                            )
                            _register_completion_future(song.db_loadouts_future)
                        except Exception:
                            song.db_loadouts_future = None

                    if song.manual_force_greats or song.force_greats_finder:
                        try:
                            if getattr(song, "fg_static_prep_future", None) is None and not bool(
                                getattr(song, "_fg_static_prep_done", False)
                            ):
                                static_budget = _fg_static_prep_budget()
                                active_static = _active_fg_static_prep_count()
                                if int(static_budget) > 0 and int(active_static) < int(static_budget):
                                    setattr(song, "_fg_static_prep_submit_t0", time.perf_counter())
                                    static_future = fg_pipeline.prep_executor.submit(_prepare_fg_static_sync, song)
                                    song.fg_static_prep_future = static_future
                                    _register_completion_future(static_future)
                        except Exception:
                            try:
                                song.fg_static_prep_future = None
                            except Exception:
                                pass

                    continue

                # CPU prep: keep a staging buffer of prepared jobs so the GPU queue
                # doesn't starve if CPU prep briefly falls behind GPU throughput.
                if stopping:
                    break
                if pending_tasks and (len(prepared) + len(prep_inflight) < prep_limit):
                    nxt = pending_tasks.popleft()
                    nxt_bundle_key = _task_key(nxt)
                    if nxt_bundle_key in completed_songs:
                        did_work = True
                        continue
                    logical_nxt, repeat_ctx = _next_logical_task(nxt)
                    nxt_key = _task_key(logical_nxt)
                    try:
                        prep_future = prep_executor.submit(_prepare_song, logical_nxt)
                        _register_completion_future(prep_future)
                        prep_inflight.append((nxt, logical_nxt, prep_future, time.perf_counter()))
                    except Exception as exc:
                        payload = build_error_payload(
                            song_name=str(nxt[1]),
                            queue_key=str(nxt_key),
                            queue_label=str(nxt_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        if repeat_ctx is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                        if repeat_ctx is not None:
                            _advance_bundle(nxt, song_name=str(nxt[1]), failed=True)
                        else:
                            completed_songs.add(nxt_key)
                            if memory_resume_tracker:
                                memory_resume_tracker.mark_completed(nxt[1])
                        did_work = True
                        continue
                    did_work = True
                    continue

                break

            # Drain completed GA jobs quickly to free inflight capacity; do the heavier
            # CPU-side decode on a background thread so the GPU queue stays fed.
            for song in list(ga_inflight):
                if song.ga_future is None or not song.ga_future.done():
                    continue
                ga_inflight.remove(song)
                did_work = True

                try:
                    ga_result = song.ga_future.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    bundle_parent = getattr(song, "_bundle_parent_task", None)
                    if not (stopping and _is_stop_abort_exception(exc)):
                        payload = build_error_payload(
                            song_name=str(song.song_name),
                            queue_key=str(song.task_key),
                            queue_label=str(song.task_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        if bundle_parent is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                    # GA failed: release the reserved timeline slot for this song.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    if stopping and _is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                    else:
                        completed_songs.add(song.task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                    continue

                t_submit = getattr(song, "_ga_submit_t0", None)
                if t_submit is not None:
                    stage_profiler.record("ga_gpu", time.perf_counter() - float(t_submit), song=song.task_key)
                    setattr(song, "_ga_submit_t0", None)

                song.ga_future = None

                needs_fg_stage = bool(song.manual_force_greats or song.force_greats_finder)
                hold_budget = int(fg_hold_budget or 0)
                keep_slot_for_fg = False
                if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                    held_slots = 0
                    try:
                        for s in decode_inflight:
                            if int(getattr(s, "song_slot", 0) or 0) <= 0:
                                continue
                            if bool(getattr(s, "manual_force_greats", False)) or bool(
                                getattr(s, "force_greats_finder", False)
                            ):
                                held_slots += 1
                    except Exception:
                        pass
                    try:
                        for s in pending_fg:
                            if int(getattr(s, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception:
                        pass
                    try:
                        for fg_song, _fut, _t_submit in fg_futures:
                            if int(getattr(fg_song, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception:
                        pass
                    keep_slot_for_fg = int(held_slots) < int(hold_budget)

                if not keep_slot_for_fg:
                    # Release the song slot immediately after GA completes unless we're keeping it
                    # resident for FG reuse (bounded by `fg_hold_budget` so GA won't deadlock on slots).
                    if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                        stage_profiler.record("fg_hold_drop", 0.0)
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                    except Exception:
                        pass
                    try:
                        song.song_slot = 0
                    except Exception:
                        pass
                    try:
                        if isinstance(song.calc_song, dict):
                            song.calc_song.pop("_gpu_song_slot", None)
                    except Exception:
                        pass

                setattr(song, "_decode_submit_t0", time.perf_counter())
                song.decode_future = decode_executor.submit(_decode_ga_payload_sync, song, ga_result)
                _register_completion_future(song.decode_future)
                decode_inflight.append(song)
                try:
                    emit_profile_event(
                        component="inflight_decode",
                        event="submit",
                        song_key=str(song.task_key),
                        metrics={"song_slot": int(getattr(song, "song_slot", 0) or 0)},
                    )
                except Exception:
                    pass

            # Finalize decoded GA results (lightweight formatting + enqueue for post/FG).
            for song in list(decode_inflight):
                if song.decode_future is None or not song.decode_future.done():
                    continue
                decode_inflight.remove(song)
                did_work = True

                try:
                    best_data, best_gear, best_minis, ga_candidates = song.decode_future.result()
                except Exception as exc:
                    bundle_parent = getattr(song, "_bundle_parent_task", None)
                    if not (stopping and _is_stop_abort_exception(exc)):
                        payload = build_error_payload(
                            song_name=str(song.song_name),
                            queue_key=str(song.task_key),
                            queue_label=str(song.task_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        if bundle_parent is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                    # Decode failed: release the reserved timeline slot for this song.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    if stopping and _is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                    else:
                        completed_songs.add(song.task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                    continue
                finally:
                    song.decode_future = None

                t_decode = getattr(song, "_decode_submit_t0", None)
                if t_decode is not None:
                    stage_profiler.record(
                        "decode",
                        time.perf_counter() - float(t_decode),
                        cpu_seconds=getattr(song, "_cpu_decode_s", None),
                        song=song.task_key,
                    )
                    setattr(song, "_decode_submit_t0", None)

                song.best_data = best_data
                song.best_gear = best_gear
                song.best_minis = best_minis
                song.ga_candidates = list(ga_candidates or [])
                song.ga_persistence_candidates = list(ga_candidates or [])
                try:
                    emit_profile_event(
                        component="inflight_decode",
                        event="consume",
                        song_key=str(song.task_key),
                        metrics={
                            "song_slot": int(getattr(song, "song_slot", 0) or 0),
                            "ga_candidates": int(len(song.ga_candidates or [])),
                        },
                    )
                except Exception:
                    pass

                if song.manual_force_greats or song.force_greats_finder:
                    fg_pipeline.queue(song, now_s=time.monotonic())
                    if song.fg_prep_future is None:
                        try:
                            fg_pipeline.start_prep(
                                song,
                                _prepare_fg_job_sync,
                                gpu_client=gpu_client,
                                register_future=_register_completion_future,
                            )
                        except Exception:
                            song.fg_prep_future = None
                else:
                    # No FG stage for this song: release its reserved timeline slot immediately.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass

                record_info = None
                try:
                    prev_best_score, prev_best_fg, baseline_valid = _progress_best_snapshot(song.db_key)
                    record_info = evaluate_progress_record_update(
                        song.best_data or {},
                        {"score": int(prev_best_score)},
                        [],
                        db_best_fg_score=int(prev_best_fg),
                        baseline_valid=bool(baseline_valid),
                    )
                    if isinstance(record_info, dict) and record_info.get("is_better"):
                        _progress_best_update(
                            song.db_key,
                            best_score=int(record_info.get("score", 0) or 0),
                            mark_valid=bool(baseline_valid),
                        )
                except Exception:
                    record_info = None
                song.record_info = record_info
                try:
                    song._deferred_post_emitted = False
                except Exception:
                    pass
                post_emit_pending.append(song)

            # Reap completed FG workers (capture errors).
            if fg_futures:
                still_pending: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
                for fg_song, fut, t_submit in list(fg_futures):
                    try:
                        done = fut.done()
                    except Exception:
                        done = False
                    if done:
                        did_work = True
                        bundle_parent = getattr(fg_song, "_bundle_parent_task", None)
                        fg_failed = False
                        try:
                            fut.result()
                        except GpuServiceTimeoutError:
                            raise
                        except Exception as exc:
                            if stopping and _is_stop_abort_exception(exc):
                                fg_failed = False
                            else:
                                fg_failed = True
                                try:
                                    emit_profile_event(
                                        component="inflight_fg_worker",
                                        event="dispatch_error",
                                        song_key=str(getattr(fg_song, "task_key", "") or getattr(fg_song, "song_name", "") or ""),
                                        metrics={
                                            "exc_type": type(exc).__name__,
                                            "exc": str(exc),
                                        },
                                    )
                                except Exception:
                                    pass
                                try:
                                    logger.exception("[NativeInflight][FG] worker failed for %s", fg_song.task_key)
                                except Exception:
                                    pass
                        if not bool(getattr(fg_song, "_deferred_post_emitted", False)):
                            try:
                                _emit_deferred_post_payload(fg_song)
                            except Exception:
                                pass
                        if fg_failed:
                            try:
                                if post_sender is not None and bool(getattr(fg_song, "_bundle_wait_for_fg", False)):
                                    post_sender.send(
                                        {
                                            "_fg_update": True,
                                            "song": fg_song.song_name,
                                            "db_key": fg_song.db_key,
                                            "use_evo_db": bool(fg_song.use_evo_db),
                                            "persist_entries": [],
                                            "file_path": fg_song.fp,
                                            "cfg_dict": fg_song.cfg_dict,
                                        }
                                    )
                            except Exception:
                                pass
                        # Release this song's reserved timeline slot now that FG is complete.
                        try:
                            slot_pool.release(int(getattr(fg_song, "song_slot", 0) or 0))
                            fg_song.song_slot = 0
                        except Exception:
                            pass
                        stage_profiler.record(
                            "fg_run",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(fg_song, "_cpu_fg_run_s", None),
                            song=fg_song.task_key,
                        )
                        if bundle_parent is not None and bool(getattr(fg_song, "_bundle_wait_for_fg", False)):
                            _advance_bundle(
                                bundle_parent,
                                song_name=str(fg_song.song_name),
                                record_info=getattr(fg_song, "record_info", None),
                                failed=bool(fg_failed),
                            )
                            try:
                                delattr(fg_song, "_bundle_wait_for_fg")
                            except Exception:
                                pass
                        elif bool(getattr(fg_song, "_await_fg_completion_progress", False)):
                            completed_songs.add(fg_song.task_key)
                            if memory_resume_tracker:
                                memory_resume_tracker.mark_completed(fg_song.song_name)
                            if bundle_completed_cb is not None:
                                try:
                                    bundle_completed_cb(fg_song.task_key, completed_songs)
                                except Exception:
                                    pass
                            try:
                                record_info = dict(getattr(fg_song, "record_info", None) or {})
                                record_info.setdefault("song", fg_song.task_key or fg_song.song_name)
                                record_info.setdefault("status", "DONE")
                            except Exception:
                                record_info = None
                            _emit_progress(completed_delta=1, record_info=record_info)
                            try:
                                delattr(fg_song, "_await_fg_completion_progress")
                            except Exception:
                                pass
                    else:
                        still_pending.append((fg_song, fut, t_submit))
                fg_pipeline.replace_futures(still_pending)

            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = _oldest_pending_fg_wait_s(float(now))
            except Exception:
                fg_oldest_wait_s = 0.0
            ready_fg_count = _ready_pending_fg_count()
            bubble_snapshot = _bubble_snapshot(float(now), oldest_fg_wait_s=float(fg_oldest_wait_s))
            _note_bubble_snapshot(
                bubble_snapshot,
                now_mono=float(now),
                oldest_fg_wait_s=float(fg_oldest_wait_s),
            )

            if not pending_fg:
                fg_pipeline.reset_credit_if_empty()

            no_ga_remaining = (
                (not pending_tasks)
                and (not prepared)
                and (not prep_inflight)
                and (not ga_inflight)
                and (not decode_inflight)
            )

            # If we're not draining FG at end, do not start new FG work once GA has
            # completed the queue; defer remaining FG candidates to DB for later processing.
            if (not fg_drain_at_end) and pending_fg and no_ga_remaining:
                # If any FG work is already running, let it complete (don't submit more).
                if fg_futures:
                    should_start_fg = False
                else:
                    try:
                        logger.debug(
                            "[InFlight][FG] Deferred %s pending FG job(s) (FG_DrainAtEnd=false). "
                            "Candidates were persisted to DB for later processing.",
                            len(pending_fg),
                        )
                    except Exception:
                        pass

                    # Best-effort: stop tracking FG prep for deferred songs so we can exit
                    # without waiting on CPU prep threads.
                    try:
                        for s in list(fg_prep_inflight):
                            try:
                                s.fg_prep_future = None
                            except Exception:
                                pass
                        fg_prep_inflight.clear()
                    except Exception:
                        pass

                    # Release any reserved timeline slots for deferred FG songs.
                    try:
                        for s in list(pending_fg):
                            try:
                                slot_pool.release(int(getattr(s, "song_slot", 0) or 0))
                                s.song_slot = 0
                            except Exception:
                                continue
                        pending_fg.clear()
                    except Exception:
                        pass
                    break

            ga_queue_limit_effective = _current_ga_queue_limit()
            ready_ga_for_lane_fill = len(prepared) if len(ga_inflight) < int(ga_queue_limit_effective) else 0
            if _continuous_fg_should_fill_song_lanes(
                target_song_lanes=int(target_song_lanes),
                active_song_lanes=int(_active_song_lane_count()),
                ready_ga_count=int(ready_ga_for_lane_fill),
                pending_fg_count=len(pending_fg),
                ready_fg_count=int(ready_fg_count),
                blocked_on_slot=bool(blocked_on_slot_acquire),
                no_ga_remaining=bool(no_ga_remaining),
                oldest_wait_s=float(fg_oldest_wait_s),
                aging_trigger_s=float(fg_aging_trigger_s),
                aging_hard_s=float(fg_aging_hard_s),
            ):
                lane_fill_hold_count += 1
                should_start_fg = False
            else:
                should_start_fg = _continuous_fg_should_start(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_count),
                    ga_credit=int(fg_pipeline.ga_credit),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                    no_ga_remaining=bool(no_ga_remaining),
                    fg_drain_at_end=bool(fg_drain_at_end),
                    aging_trigger_s=float(fg_aging_trigger_s),
                    aging_hard_s=float(fg_aging_hard_s),
                    ga_queue_limit=int(ga_queue_limit_effective),
                    fg_slot_reserve=int(fg_slot_reserve),
                )

            if should_start_fg:
                if fg_decision_debug:
                    try:
                        reasons: list[str] = []
                        if no_ga_remaining:
                            reasons.append("drain_end")
                        if blocked_on_slot_acquire:
                            reasons.append("slot_pressure")
                        if (
                            int(fg_slot_reserve) > 0
                            and int(ready_fg_count) > 0
                            and len(ga_inflight) >= max(1, int(ga_queue_limit_effective))
                        ):
                            reasons.append("reserve_ready")
                        if fg_oldest_wait_s >= float(fg_aging_hard_s) and float(fg_aging_hard_s) > 0.0:
                            reasons.append("aging_hard")
                        elif fg_oldest_wait_s >= float(fg_aging_trigger_s) and float(fg_aging_trigger_s) > 0.0:
                            reasons.append("aging_trigger")
                        if int(fg_pipeline.ga_credit) <= 0:
                            reasons.append("credit")

                        logger.debug(
                            "[InFlight][FGDecision] start reasons=%s pending=%s prepared=%s prep_inflight=%s "
                            "ga_inflight=%s decode_inflight=%s pending_fg=%s fg_prep=%s fg_inflight=%s "
                            "oldest_fg_wait_ms=%.0f",
                            ",".join(reasons) or "unknown",
                            len(pending_tasks),
                            len(prepared),
                            len(prep_inflight),
                            len(ga_inflight),
                            len(decode_inflight),
                            len(pending_fg),
                            len(fg_prep_inflight),
                            len(fg_futures),
                            fg_oldest_wait_s * 1000.0,
                        )
                    except Exception:
                        pass

                submit_budget = _continuous_fg_submit_budget(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_count),
                    fg_inflight_count=len(fg_futures),
                    fg_workers=int(fg_workers),
                    fg_batch_max=int(fg_batch_max),
                    no_ga_remaining=bool(no_ga_remaining),
                    fg_drain_at_end=bool(fg_drain_at_end),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    aging_trigger_s=float(fg_aging_trigger_s),
                    aging_hard_s=float(fg_aging_hard_s),
                    ga_queue_limit=int(ga_queue_limit_effective),
                    adaptive_submit=bool(fg_adaptive_submit_enabled),
                    adaptive_max_burst=int(fg_adaptive_submit_max_burst),
                    fg_slot_reserve=int(fg_slot_reserve),
                )

                if submit_budget > 0 and len(fg_futures) < fg_workers:
                    # Process pending FG jobs (up to worker + batch budget).
                    while submit_budget > 0 and len(fg_futures) < fg_workers and pending_fg:
                        allow_not_ready = _continuous_fg_allow_not_ready(
                            blocked_on_slot=bool(blocked_on_slot_acquire),
                            no_ga_remaining=bool(no_ga_remaining),
                            fg_drain_at_end=bool(fg_drain_at_end),
                        )
                        if allow_not_ready and fg_pipeline.has_active_prep():
                            allow_not_ready = False
                        fg_song = _pop_next_fg(allow_not_ready=allow_not_ready)
                        if fg_song is None:
                            break
                        if int(getattr(fg_song, "song_slot", 0) or 0) <= 0:
                            try:
                                fg_song.song_slot = int(slot_pool.acquire())
                            except Exception:
                                # No free slots: put the song back and defer FG submission
                                # until GA releases slots. Without this, the song would be
                                # dropped from FG processing entirely (it was removed from
                                # pending_fg by _pop_next_fg but never submitted).
                                fg_pipeline.requeue_front(fg_song)
                                break
                            try:
                                if isinstance(fg_song.calc_song, dict):
                                    fg_song.calc_song["_gpu_song_slot"] = int(fg_song.song_slot)
                            except Exception:
                                pass
                        if fg_submit_debug:
                            try:
                                logger.debug(
                                    "[InFlight][FGSubmit] song=%s pending_fg=%s fg_inflight=%s",
                                    fg_song.task_key,
                                    len(pending_fg),
                                    len(fg_futures),
                                )
                            except Exception:
                                pass
                        try:
                            fg_song.fg_queued_t0 = None
                        except Exception:
                            pass
                        fg_pipeline.submit_job(
                            _run_fg_job_sync,
                            fg_song,
                            gpu_client=gpu_client,
                            post_sender=post_sender,
                            progress_cb=progress_cb,
                            progress_best=progress_best,
                            progress_best_valid=progress_best_valid,
                            progress_best_lock=progress_best_lock,
                            register_future=_register_completion_future,
                        )
                        did_work = True
                        submit_budget -= 1

            if post_emit_pending:
                post_emit_budget = 1
                if not (
                    pending_tasks
                    or prepared
                    or prep_inflight
                    or ga_inflight
                    or decode_inflight
                    or pending_fg
                    or fg_prep_inflight
                    or fg_futures
                ):
                    post_emit_budget = int(len(post_emit_pending))
                while post_emit_budget > 0 and post_emit_pending:
                    post_song = post_emit_pending.popleft()
                    if bool(getattr(post_song, "_deferred_post_emitted", False)):
                        continue
                    _emit_deferred_post_payload(post_song)
                    did_work = True
                    post_emit_budget -= 1

            _emit_active_runtime_song()

            if did_work:
                last_progress = time.monotonic()

            # Avoid tight spin.
            if not did_work:
                if heartbeat_sec > 0.0 and (time.monotonic() - last_heartbeat) >= heartbeat_sec:
                    last_heartbeat = time.monotonic()
                    heartbeat_bubble = _bubble_snapshot(float(last_heartbeat), oldest_fg_wait_s=float(fg_oldest_wait_s))
                    oldest_ga_s = None
                    try:
                        now = time.perf_counter()
                        t0s = [getattr(s, "_ga_submit_t0", None) for s in ga_inflight]
                        t0s = [t for t in t0s if t is not None]
                        if t0s:
                            oldest_ga_s = max(0.0, now - float(min(t0s)))
                    except Exception:
                        oldest_ga_s = None

                    try:
                        msg = (
                            "[InFlight][HB] "
                            f"idle={time.monotonic() - last_progress:.1f}s "
                            f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                            f"cpu_prewarm={len(cpu_prewarm_inflight)} "
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)} "
                            f"lanes={int(heartbeat_bubble.get('active_song_lanes', 0) or 0)}/{int(target_song_lanes)} "
                            f"lane_holds={int(lane_fill_hold_count)}"
                        )
                        if blocked_on_slot_acquire:
                            msg += " blocked_slots=1"
                        if oldest_ga_s is not None:
                            msg += f" oldest_ga={oldest_ga_s:.1f}s"
                        if float(heartbeat_bubble.get("bubble_kpi", 0.0) or 0.0) > 0.0:
                            msg += (
                                f" bubble_kpi={float(heartbeat_bubble.get('bubble_kpi', 0.0)):.2f}"
                                f" ready_ga={int(heartbeat_bubble.get('ready_ga_count', 0) or 0)}"
                                f" ready_fg={int(heartbeat_bubble.get('ready_fg_count', 0) or 0)}"
                            )
                        logger.debug(msg)
                    except Exception:
                        pass
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="heartbeat",
                        metrics={
                            "idle_sec": float(time.monotonic() - last_progress),
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "cpu_prewarm_inflight": int(len(cpu_prewarm_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_futures": int(len(fg_futures)),
                            "blocked_slots": int(bool(blocked_on_slot_acquire)),
                            "oldest_ga_sec": float(oldest_ga_s) if oldest_ga_s is not None else -1.0,
                            "bubble_kpi": float(heartbeat_bubble.get("bubble_kpi", 0.0) or 0.0),
                            "bubble_ready_ga": int(heartbeat_bubble.get("ready_ga_count", 0) or 0),
                            "bubble_ready_fg": int(heartbeat_bubble.get("ready_fg_count", 0) or 0),
                            "active_song_lanes": int(heartbeat_bubble.get("active_song_lanes", 0) or 0),
                            "target_song_lanes": int(target_song_lanes),
                            "lane_fill_holds": int(lane_fill_hold_count),
                            "bubble_backlog": int(heartbeat_bubble.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )

                no_active_work = (
                    (not ga_inflight)
                    and (not decode_inflight)
                    and (not prep_inflight)
                    and (not cpu_prewarm_inflight)
                    and (not fg_prep_inflight)
                    and (not fg_futures)
                )
                if (
                    no_active_work
                    and (pending_tasks or prepared or pending_fg or fg_futures or post_emit_pending)
                    and (time.monotonic() - last_stall_report) >= 10.0
                    and _truthy(os.environ.get("INFLIGHT_STALL_DEBUG", "0"))
                ):
                    last_stall_report = time.monotonic()
                    try:
                        fg_done = sum(1 for _song, fut, _t0 in fg_futures if fut.done())
                        fg_inflight = len(fg_futures)
                    except Exception:
                        fg_done = None
                        fg_inflight = None
                    logger.debug(
                        "[InFlight][STALL] pending=%s prepared=%s prep_inflight=%s ga_inflight=%s "
                        "cpu_prewarm=%s decode_inflight=%s pending_fg=%s fg_prep=%s fg_inflight=%s fg_done=%s",
                        len(pending_tasks),
                        len(prepared),
                        len(prep_inflight),
                        len(ga_inflight),
                        len(cpu_prewarm_inflight),
                        len(decode_inflight),
                        len(pending_fg),
                        len(fg_prep_inflight),
                        fg_inflight,
                        fg_done,
                    )
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="stall",
                        metrics={
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "cpu_prewarm_inflight": int(len(cpu_prewarm_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_inflight": int(fg_inflight) if fg_inflight is not None else -1,
                            "fg_done": int(fg_done) if fg_done is not None else -1,
                            "bubble_kpi": float(bubble_snapshot.get("bubble_kpi", 0.0) or 0.0),
                            "bubble_ready_ga": int(bubble_snapshot.get("ready_ga_count", 0) or 0),
                            "bubble_ready_fg": int(bubble_snapshot.get("ready_fg_count", 0) or 0),
                            "active_song_lanes": int(bubble_snapshot.get("active_song_lanes", 0) or 0),
                            "target_song_lanes": int(target_song_lanes),
                            "lane_fill_holds": int(lane_fill_hold_count),
                            "bubble_backlog": int(bubble_snapshot.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )

                if _has_waitable_futures():
                    t_wait = time.perf_counter()
                    has_gpu = bool(ga_inflight) or bool(fg_futures)
                    has_cpu = (
                        bool(prep_inflight)
                        or bool(cpu_prewarm_inflight)
                        or bool(decode_inflight)
                        or bool(fg_prep_inflight)
                    )
                    signaled = False
                    try:
                        signaled = bool(completion_event.is_set())
                        if signaled:
                            completion_event.clear()
                    except Exception:
                        signaled = False
                    if not signaled:
                        wait_timeout_s = float(event_wait_timeout_s)
                        if has_gpu and float(event_wait_gpu_cap_s) > 0.0:
                            wait_timeout_s = min(float(wait_timeout_s), float(event_wait_gpu_cap_s))
                        signaled = wait_for_completion_event(
                            completion_event,
                            timeout_s=float(wait_timeout_s),
                            short_spin_s=float(event_wait_short_spin_s),
                        )
                        if signaled:
                            try:
                                completion_event.clear()
                            except Exception:
                                pass
                    dt_wait = time.perf_counter() - t_wait
                    stage_profiler.record("main_wait", dt_wait)
                    if (not has_gpu) and has_cpu:
                        stage_profiler.record("underfed_wait", dt_wait)
                else:
                    t_sleep = time.perf_counter()
                    time.sleep(0.001)
                    stage_profiler.record("main_sleep", time.perf_counter() - t_sleep)

    except Exception as exc:
        _log_abort(exc)
        raise
    finally:
        try:
            now_mono = time.monotonic()
            if bubble_active_started is not None:
                bubble_total_idle_s += max(0.0, float(now_mono) - float(bubble_active_started))
                bubble_active_started = None
            emit_profile_event(
                component="inflight_orchestrator",
                event="bubble_summary",
                metrics={
                    "bubble_total_idle_sec": float(bubble_total_idle_s),
                    "bubble_peak_kpi": float(bubble_peak_kpi),
                    "bubble_peak_ready_ga": int(bubble_peak_ready_ga),
                    "bubble_peak_ready_fg": int(bubble_peak_ready_fg),
                    "bubble_peak_backlog": int(bubble_peak_backlog),
                    "bubble_peak_oldest_fg_wait_sec": float(bubble_peak_oldest_fg_wait_s),
                    "active_song_lanes": int(_active_song_lane_count()),
                    "target_song_lanes": int(target_song_lanes),
                    "lane_fill_holds": int(lane_fill_hold_count),
                },
            )
        except Exception:
            pass
        try:
            stage_profiler.emit()
        except Exception:
            pass
        shutdown_debug = _truthy(os.environ.get("INFLIGHT_SHUTDOWN_DEBUG", "0"))
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] fg_executor.shutdown")
            fg_pipeline.shutdown_fg(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] decode_executor.shutdown")
            decode_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] db_prefetch_executor.shutdown")
            db_prefetch_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] fg_prep_executor.shutdown")
            fg_pipeline.shutdown_prep(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] cpu_prewarm_executor.shutdown")
            if cpu_prewarm_executor is not None:
                cpu_prewarm_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] prep_executor.shutdown")
            prep_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if post_sender is not None:
                if shutdown_debug:
                    logger.debug("[InFlight][SHUTDOWN] post_sender.close")
                post_sender.close(timeout=10.0)
        except Exception:
            pass
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] gpu_client.close")
            gpu_client.close(timeout=2.0)
        except Exception:
            pass
        try:
            if gpu_executor.is_running:
                if shutdown_debug:
                    logger.debug("[InFlight][SHUTDOWN] gpu_executor.stop")
                gpu_executor.stop()
        except Exception:
            pass


# NOTE: `_decode_ga_payload_sync`, `_prefetch_db_loadouts_sync`, `_prepare_fg_job_sync` are imported
# from `gear_optimizer/solver/native_inflight_stages.py` to keep the orchestrator loop leaner.


def _run_fg_job_sync(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: Optional[_PostSender] = None,
    progress_cb=None,
    progress_best: dict[str, tuple[int, int]] | None = None,
    progress_best_valid: set[str] | None = None,
    progress_best_lock: Any | None = None,
) -> None:
    cpu_t0 = _thread_cpu_time_s()
    song_key = str(getattr(song, "task_key", "") or getattr(song, "song_name", "") or "")
    active_fg_calc_song = _resolve_active_fg_calc_song(song)
    if not isinstance(active_fg_calc_song, dict):
        active_fg_calc_song = song.calc_song

    def _count_fg_group_meta_ready(candidates: Any) -> int:
        ready = 0
        for candidate in candidates or []:
            if not isinstance(candidate, dict):
                continue
            data = candidate.get("Data")
            if not isinstance(data, dict):
                continue
            if isinstance(data.get("_fg_group_meta"), dict):
                ready += 1
        return int(ready)

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="start",
            song_key=song_key,
            metrics={
                "had_prep_future": int(song.fg_prep_future is not None),
                "ga_candidates": int(len(song.ga_candidates or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(song.ga_candidates)),
            },
        )
    except Exception:
        pass
    if song.fg_prep_future is not None:
        prep_wait_t0 = time.perf_counter()
        try:
            song.fg_prep_future.result()
            try:
                song._fg_dynamic_prep_done = True
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                emit_profile_event(
                    component="inflight_fg_worker",
                    event="prep_wait",
                    song_key=song_key,
                    metrics={
                        "wait_ms": max(0.0, (time.perf_counter() - float(prep_wait_t0)) * 1000.0),
                    },
                )
            except Exception:
                pass
            song.fg_prep_future = None

    if song.loadout_entries is None:
        _prepare_fg_job_sync(song, gpu_client=gpu_client)
        try:
            song._fg_dynamic_prep_done = True
        except Exception:
            pass

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="prep_ready",
            song_key=song_key,
            metrics={
                "loadout_entries": int(len(song.loadout_entries or {})) if isinstance(song.loadout_entries, dict) else 0,
                "ga_candidates": int(len(song.ga_candidates or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(song.ga_candidates)),
            },
        )
    except Exception:
        pass

    # Late non-blocking DB prefetch consume:
    # - If FG prep skipped DB rows because prefetch was still in-flight, harvest now if ready.
    # - Never block FG worker threads on SQLite here.
    if song.db_loadouts_full is None and song.db_loadouts_future is not None:
        fut = song.db_loadouts_future
        try:
            if fut.done():
                try:
                    db_rows = fut.result(timeout=0)
                    if isinstance(db_rows, list):
                        song.db_loadouts_full = db_rows
                except Exception:
                    song.db_loadouts_full = None
            else:
                # Best effort: avoid keeping stale prefetch work around if FG is already running.
                try:
                    fut.cancel()
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            song.db_loadouts_future = None

    build_details = getattr(song, "fg_build_details", None)
    if not callable(build_details):
        build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)
        try:
            song.fg_build_details = build_details
        except Exception:
            pass

    # If FG prep built GA-only entries while DB prefetch was pending, merge DB rows now
    # without rebuilding the full GA union.
    if song.db_loadouts_full is not None and not _loadout_entries_have_db_source(song.loadout_entries):
        if not isinstance(song.loadout_entries, dict):
            song.loadout_entries = {}
        merge_db_loadouts_into_entries(song.loadout_entries, song.db_loadouts_full)

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="pre_dispatch",
            song_key=song_key,
            metrics={
                "loadout_entries": int(len(song.loadout_entries or {})) if isinstance(song.loadout_entries, dict) else 0,
                "ga_candidates": int(len(song.ga_candidates or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(song.ga_candidates)),
            },
        )
    except Exception:
        pass

    fg_solver_mode = str((getattr(song, "cfg_data", None) or {}).get("fg_solver_mode") or "finder").strip().lower()
    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_start",
            song_key=song_key,
            metrics={
                "solver_mode": str(fg_solver_mode),
                "song_slot": int(getattr(song, "song_slot", 0) or 0),
            },
        )
    except Exception:
        pass
    if fg_solver_mode == "off":
        fg_variants = []
    else:
        fg_variants = process_force_greats(
            song.loadout_entries or {},
            bool(song.manual_force_greats),
            bool(song.force_greats_finder),
            song.force_greats_config,
            active_fg_calc_song,
            song.ref_arrays,
            song.meta_primary_color,
            build_details,
            use_gpu=True,
            fg_search_radius=song.fg_search_radius,
            perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
            gpu_client=gpu_client,
            ga_candidates=song.ga_candidates if bool(getattr(song, "fg_direct_ga_candidates", False)) else None,
            ga_registry=song.registry if bool(getattr(song, "fg_direct_ga_candidates", False)) else None,
        )

    song.fg_variants = list(fg_variants or [])
    try:
        setattr(song, "_cpu_fg_run_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_done",
            song_key=song_key,
            metrics={
                "fg_variants": int(len(song.fg_variants or [])),
                "solver_mode": str(fg_solver_mode),
            },
        )
    except Exception:
        pass

    if progress_cb is not None:
        fg_record_info = None
        try:
            prev_best_score = safe_int(getattr(song, "db_best_score", 0), 0)
            prev_best_fg = safe_int(getattr(song, "db_best_fg_score", 0), 0)
            baseline_valid = bool(getattr(song, "db_baseline_valid", True))

            key = str(getattr(song, "db_key", "") or "").strip()
            if progress_best is not None and progress_best_lock is not None and key:
                try:
                    with progress_best_lock:
                        best_pair = progress_best.get(key)
                        if isinstance(best_pair, tuple) and len(best_pair) == 2:
                            prev_best_score = safe_int(best_pair[0], prev_best_score)
                            prev_best_fg = safe_int(best_pair[1], prev_best_fg)
                        baseline_valid = key in (progress_best_valid or set())
                except Exception:
                    pass

            fg_record_info = evaluate_progress_record_update(
                song.best_data or {},
                {"score": int(prev_best_score)},
                song.fg_variants or [],
                db_best_fg_score=int(prev_best_fg),
                baseline_valid=bool(baseline_valid),
                fg_only=True,
            )
        except Exception:
            fg_record_info = None
        if isinstance(fg_record_info, dict):
            fg_record_info = dict(fg_record_info)
            if fg_record_info.get("is_fg_better") and progress_best is not None and progress_best_lock is not None:
                try:
                    best_fg_new = safe_int(fg_record_info.get("best_fg_score_run", 0), 0)
                except Exception:
                    best_fg_new = 0
                if best_fg_new > 0:
                    key = str(getattr(song, "db_key", "") or "").strip()
                    if key:
                        try:
                            with progress_best_lock:
                                score0, fg0 = progress_best.get(key, (int(prev_best_score), int(prev_best_fg)))
                                if int(best_fg_new) > int(fg0):
                                    progress_best[key] = (int(score0), int(best_fg_new))
                                if bool(baseline_valid) and progress_best_valid is not None:
                                    progress_best_valid.add(key)
                        except Exception:
                            pass
            try:
                progress_cb(completed_delta=0, failed_delta=0, record_info=fg_record_info)
            except Exception:
                pass

    if post_sender is not None:
        post_sender.send(
            {
                "_fg_update": True,
                "song": song.song_name,
                "db_key": song.db_key,
                "use_evo_db": bool(song.use_evo_db),
                "persist_entries": _build_fg_persist_entries(song),
                # Allow downstream post-process / async DB hooks (e.g., TeamBuff tier leaderboards)
                # to run without requiring ForceGreatsDebug (which ships large objects).
                "file_path": song.fp,
                "cfg_dict": song.cfg_dict,
            }
        )


def _build_fg_persist_entries(song: _NativeSong) -> list[dict]:
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value) if value is not None else int(default)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                return int(default)

    entries: list[dict] = []
    build_details = getattr(song, "fg_build_details", None)
    if not callable(build_details):
        build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)
        try:
            song.fg_build_details = build_details
        except Exception:
            pass
    loadout_entries = song.loadout_entries if isinstance(song.loadout_entries, dict) else {}
    loadout_hash_index: dict[str, dict] = {}
    if loadout_entries:
        for loadout_key, entry in loadout_entries.items():
            if isinstance(entry, dict):
                loadout_hash_index.setdefault(str(loadout_key), entry)
            try:
                loadout_hash = entry_loadout_hash(entry)
            except Exception:
                loadout_hash = None
            if not loadout_hash or not isinstance(entry, dict):
                continue
            loadout_hash_index.setdefault(str(loadout_hash), entry)

    for v in song.fg_variants or []:
        if not isinstance(v, dict):
            continue
        is_ga = bool(v.get("_is_ga"))
        base_score = _safe_int(v.get("base_score", v.get("score", 0)), 0)
        fg_score = _safe_int(v.get("fg_score", 0), 0)
        gear_names = _compact_items(v.get("gear") or [])
        mini_names = _compact_items(v.get("minis") or [])
        data = v.get("data") or {}
        base_entry = None
        if (not gear_names and not mini_names) and isinstance(v.get("_entry_ref"), dict):
            try:
                gear_names, mini_names = materialize_entry_names(v.get("_entry_ref"), mutate=True)
            except Exception:
                gear_names, mini_names = [], []
        if gear_names or mini_names:
            try:
                from gear_optimizer.data.database import get_loadout_hash as _get_loadout_hash

                candidate = loadout_hash_index.get(str(_get_loadout_hash(gear_names, mini_names)))
                if isinstance(candidate, dict):
                    base_entry = candidate
            except Exception:
                base_entry = None

        if isinstance(base_entry, dict):
            entry_base_score = _safe_int(
                base_entry.get("base_score"),
                _safe_int(base_entry.get("score", 0), base_score),
            )
            if entry_base_score > 0:
                base_score = entry_base_score

        details_obj = base_entry.get("details") if isinstance(base_entry, dict) else None
        if isinstance(details_obj, dict) and details_obj:
            # Keep base payload consistent with base score on deferred FG updates.
            details = dict(details_obj)
        else:
            details_source = base_entry.get("eval_data") if isinstance(base_entry, dict) else None
            if not isinstance(details_source, dict) or not details_source:
                details_source = data if isinstance(data, dict) else {}
            details = build_details(details_source) if callable(build_details) else {}
            if not isinstance(details, dict):
                details = {}
            details = dict(details)
            details["ForceGreats"] = (data.get("ForceGreats", {}) if isinstance(data, dict) else {}) or {}

        force_obj = None
        try:
            if isinstance(data, dict) and has_valid_fg_config(data):
                force_obj = dict(data)
        except Exception:
            force_obj = None
        entries.append(
            {
                "score": int(base_score),
                "fg_score": int(fg_score),
                "gear": gear_names,
                "minis": mini_names,
                "details": details,
                "force": force_obj,
                "_is_ga": bool(is_ga),
                # Mark these entries as coming from a deferred FG-only persistence pass
                # so the DB layer can avoid overwriting base `details_json` on ties.
                "_deferred_fg_update": True,
            }
        )
    return entries

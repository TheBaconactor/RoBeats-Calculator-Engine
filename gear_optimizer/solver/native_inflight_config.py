"""
GPU-native in-flight pipeline configuration parsing.

Extracts all config/ENV-driven settings for the native in-flight orchestrator
into a frozen dataclass so the orchestrator body stays focused on runtime logic.
"""

from __future__ import annotations

import concurrent.futures
import logging
import configparser
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.domain.jobs import task_cfg_dict
from gear_optimizer.solver.inflight_utils import _truthy

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from gear_optimizer.solver.exact_base_domains import ExactBaseDomains
    from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContext
    from gear_optimizer.solver.solver_common import SolverContext
    from gear_optimizer.solver.taichi_gem.api.timeline import TimelineFrontierPrewarmResult


CANONICAL_BASE_QUEUE_MULT = 2
CANONICAL_PREP_BUFFER_MULT = 4


def _scheduler_policy():
    from gear_optimizer.solver import native_inflight_scheduler_policy as policy

    return policy


def default_worker_threads(*, inflight_limit: int, kind: str) -> int:
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


def read_inflight_worker_count(
    *,
    inflight_limit: int,
    kind: str,
) -> int:
    workers = default_worker_threads(inflight_limit=int(inflight_limit), kind=str(kind))
    return max(1, int(workers))


def read_db_prefetch_workers(
    *,
    fg_prep_workers: int,
) -> int:
    return max(1, min(int(fg_prep_workers), 4))


@dataclass(frozen=True)
class InflightConfig:
    inflight_limit: int
    max_song_slots: int
    song_slot_limit: int
    base_queue_limit: int
    prep_buffer_mult: int
    prep_limit: int
    prep_workers: int
    decode_workers: int
    fg_scheduler_norm: str
    stage_profile_enabled: bool
    stage_profile_path: str | None
    runtime: "InflightRuntimeSettings"
    loop_observer: "InflightLoopObserverSettings"
    fg_submit_debug: bool


@dataclass(frozen=True)
class InflightRuntimeSettings:
    gpu_executor_init_timeout_sec: float


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
        profile_max_songs = int(env_get_fn("INFLIGHT_PROFILE_MAX_SONGS", "0") or "0")
    except (ValueError, TypeError):
        profile_max_songs = 0

    return InflightLoopObserverSettings(
        heartbeat_sec=float(heartbeat_sec),
        throughput_sec=float(throughput_sec),
        profile_max_songs=max(0, int(profile_max_songs)),
    )


def parse_inflight_config(tasks: list[tuple], *, in_flight_songs: int) -> InflightConfig:
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

    scheduler_policy = _scheduler_policy()

    # Keep the exact Base owner queue as deep as the slot pool allows. A slot is
    # released as soon as the fused Base+FG owner request completes.
    base_queue_limit = max(1, int(inflight_limit) * int(CANONICAL_BASE_QUEUE_MULT))
    base_queue_limit = min(int(base_queue_limit), int(song_slot_limit))

    prep_buffer_mult = int(CANONICAL_PREP_BUFFER_MULT)
    prep_limit = max(1, int(inflight_limit) * int(prep_buffer_mult))
    prep_workers = read_inflight_worker_count(
        inflight_limit=int(inflight_limit),
        kind="prep",
    )
    decode_workers = read_inflight_worker_count(
        inflight_limit=int(inflight_limit),
        kind="decode",
    )

    fg_scheduler_norm = scheduler_policy.read_fg_scheduler_mode()

    try:
        logger.debug(
            f"[InFlight][FG] scheduler={fg_scheduler_norm} (BaseQueueLimit={int(base_queue_limit)})"
        )
    except (ValueError, TypeError):
        pass

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

    fg_submit_debug = _truthy(env_get("INFLIGHT_FG_SUBMIT_DEBUG", "0"))
    runtime = read_inflight_runtime_settings()
    loop_observer = read_inflight_loop_observer_settings()

    return InflightConfig(
        inflight_limit=inflight_limit,
        max_song_slots=max_song_slots,
        song_slot_limit=song_slot_limit,
        base_queue_limit=base_queue_limit,
        prep_buffer_mult=prep_buffer_mult,
        prep_limit=prep_limit,
        prep_workers=prep_workers,
        decode_workers=decode_workers,
        fg_scheduler_norm=fg_scheduler_norm,
        stage_profile_enabled=stage_profile_enabled,
        stage_profile_path=stage_profile_path,
        runtime=runtime,
        loop_observer=loop_observer,
        fg_submit_debug=fg_submit_debug,
    )

from gear_optimizer.core.types import CalcSong, JsonDict, RefArrays
from gear_optimizer.solver.item_registry import ItemRegistry


@dataclass
class NativeSongConfig:
    fp: str = ""
    song_name: str = ""
    task_key: str = ""
    db_key: str = ""
    effective_difficulty: str = ""
    cfg_dict: JsonDict = field(default_factory=dict)
    cfg: configparser.ConfigParser | None = None
    paths: dict[str, Any] | None = None
    fg_debug: bool = False


@dataclass
class NativeSongGPUInputs:
    ref_arrays: RefArrays = field(default_factory=dict)
    all_gears: list[Any] = field(default_factory=list)
    all_minis: list[Any] = field(default_factory=list)
    gears_by_name: dict[str, Any] = field(default_factory=dict)
    minis_by_name: dict[str, Any] = field(default_factory=dict)
    calc_song: CalcSong | JsonDict = field(default_factory=dict)
    meta_primary_color: str = ""
    meta_secondary_color: str = ""
    fixed_stats: JsonDict = field(default_factory=dict)
    current_gear_list: list[Any] = field(default_factory=list)
    current_mini_list: list[Any] = field(default_factory=list)
    registry: ItemRegistry | None = None
    cfg_data: JsonDict = field(default_factory=dict)
    color_flags: dict[str, Any] = field(default_factory=dict)
    solver_context: "SolverContext | None" = None
    exact_base_domains: "ExactBaseDomains | None" = None
    exact_base_song_context: "ExactBaseSongContext | None" = None
    timeline_frontier: "TimelineFrontierPrewarmResult | None" = None


@dataclass
class NativeSongPrepState:
    cpu_prep_s: float = 0.0
    wall_prep_s: float = 0.0


@dataclass
class NativeSongBaseState:
    base_future: Optional[concurrent.futures.Future] = None
    base_submit_t0: float | None = None


@dataclass
class NativeSongDecodeState:
    decode_future: Optional[concurrent.futures.Future] = None
    decode_submit_t0: float | None = None
    base_candidates: Optional[list[JsonDict]] = None
    fg_surface_prepared: bool = False
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None
    cpu_decode_s: float = 0.0


@dataclass
class NativeSongFGState:
    fg_variants: Optional[list[JsonDict]] = None
    fg_calc_song: Optional[CalcSong | JsonDict] = None
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_queued_t0: float | None = None
    fg_static_prep_done: bool = False
    fg_dynamic_prep_done: bool = False
    fg_prep_submit_t0: float | None = None
    fg_response_scoring_bundle: Any | None = None
    fg_response_frontier_plan: Any | None = None
    # Native fused Base->FG handoff: the owner-scored per-base_components FG result map
    # ({base_components_7tuple -> FgFusedOwnerScoreRow}) returned by the exact Base run on the
    # owner thread. The FG worker materializes from this instead of submitting
    # BUILD+SCORE owner requests. Set while decoding the fused exact Base response.
    fg_owner_score_map: Any | None = None
    cpu_fg_prep_s: float = 0.0
    fg_prep_wall_s: float = 0.0
    cpu_fg_run_s: float = 0.0
    fg_run_wall_s: float = 0.0


@dataclass
class NativeSongDBState:
    prev_record: Optional[JsonDict] = None
    db_best_score: int = 0
    db_best_fg_score: int = 0
    db_baseline_valid: bool = False
    attempt_lifetime: int = 0
    prev_attempts_first: int = 0
    record_info: Optional[JsonDict] = None


@dataclass
class NativeSongBundleState:
    bundle_parent_task: Any | None = None
    bundle_task_key: str = ""
    bundle_repeat_index: int = 0
    bundle_repeat_total: int = 0


@dataclass
class NativeSongPostState:
    deferred_post_emitted: bool = False


@dataclass
class NativeSongRuntimeState:
    song_slot: int = 0
    prep: NativeSongPrepState = field(default_factory=NativeSongPrepState)
    base: NativeSongBaseState = field(default_factory=NativeSongBaseState)
    decode: NativeSongDecodeState = field(default_factory=NativeSongDecodeState)
    fg: NativeSongFGState = field(default_factory=NativeSongFGState)
    db: NativeSongDBState = field(default_factory=NativeSongDBState)
    bundle: NativeSongBundleState = field(default_factory=NativeSongBundleState)
    post: NativeSongPostState = field(default_factory=NativeSongPostState)


# eq=False (identity equality/hash): conveyor deques remove songs by identity,
# and the auto-generated value __eq__ would recurse into NativeSongGPUInputs'
# numpy fields (ambiguous-truth crash) and, on a not-found miss, into the deep
# repr (a proven multi-second stall). No code compares NativeSong by value.
# This enforces the identity-conveyor invariant at the producer rather than per
# call site (see _remove_song_by_identity for the absence-tolerant variant).
@dataclass(eq=False)
class NativeSong:
    config: NativeSongConfig
    gpu_inputs: NativeSongGPUInputs
    runtime: NativeSongRuntimeState


def native_song_label(song: object, *, fallback_id: bool = False) -> str:
    try:
        config = getattr(song, "config", None)
        label = str(getattr(config, "task_key", "") or getattr(config, "song_name", "") or "").strip()
        if label:
            return label
    except Exception:
        pass
    return str(id(song)) if bool(fallback_id) else ""

"""
Legacy direct song processing orchestration.

This module handles the calculate-only compatibility path. Production optimizer
runs use the native in-flight engine instead.

Contains the legacy process_song_task function that coordinates:
- Song data loading
- Fixed stats calculation
- GA optimization
- Force greats evaluation
- Database persistence

REFACTORED: Helper functions extracted to .helpers.song_helpers for maintainability.
"""

import contextlib
import gc
import logging
import sys
import time
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Callable, cast

from ..data.models import Tee
from ..core.env_config import ENV
from ..core.types import SongResultPayload
from ..core.constants import (
    LOADOUTS_PER_SONG_LIMIT,
    FG_CANDIDATE_LIMIT,
)

from ..core.config import (
    read_fg_candidate_limit,
    read_fg_search_radius,
)
from ..solver.genetic import GA_POPULATION_SIZE, solve_coevolution_genetic
from ..solver.scoring import (
    GEM_SOLVER_CACHE,
    FEVER_TIMELINE_CACHE,
    FG_CACHE,
)
from ..solver.gpu_profiler import get_gpu_profiler
from ..solver.solver_common import SolverContext, prepare_solver_context
from ..solver.song_preparation import build_prepared_song_core
from ..core.memory import log_memory_usage
from ..domain.jobs import seed_plan_from_song_job, task_tuple_to_legacy_view
from ..helpers.song_helpers import (
    build_loadout_entries,
    # Candidate selection for FG funnel (keeps low-base/high-FG candidates)
    # without increasing FG_CandidateLimit.
    process_force_greats,
    ReplayContext,
    build_db_payload,
    canonicalize_and_assemble,
    print_results,
)
from ..helpers.song_helpers.persistence import make_build_details_fn, evaluate_progress_record_update
from ..helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from ..helpers.song_helpers.payload_compaction import (
    compact_fg_variants,
    compact_ga_candidates,
    compact_item_names,
    compact_loadout_entries,
    compact_prev_record,
)

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)

# Global counter for deterministic garbage collection
_SONG_GC_COUNTER = 0
_SONG_GC_GEN2_INTERVAL = max(1, int(env_get("SONG_GC_GEN2_INTERVAL", "25") or "25"))

# Performance timing flag (set via env var)
PERF_TIMING_ENABLED = bool(getattr(ENV, "perf_timing_unconditional", False))
_CAPTURE_SONG_LOG_PAYLOAD = str(env_get("SONG_CAPTURE_LOG_PAYLOAD", "0") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# GPU profiler for songs/hour tracking
_gpu_profiler = get_gpu_profiler()


@dataclass
class SongContext:
    fp: str
    found_song_name: str
    queue_label: str
    effective_difficulty: str
    cfg_dict: dict[str, Any]
    cfg: Any
    paths: Any
    ref_arrays: dict[str, Any]
    all_gears: list[dict]
    all_minis: list[dict]
    gears_by_name: dict[str, Any]
    minis_by_name: dict[str, Any]
    auto_buff: bool
    ga_depth: int
    status_queue: Any
    defer_post: bool
    emit: Callable[[str], None]
    stage_timing: dict[str, float]
    repeat_index: int
    repeat_total: int
    fg_debug: bool
    calc_song: dict[str, Any]
    meta_primary_color: str
    meta_secondary_color: str
    ga_settings: Any
    fixed_stats: dict[str, Any]
    current_gear_stats: dict[str, Any]
    current_gear_list: list[dict]
    current_mini_stats: dict[str, Any]
    current_mini_list: list[dict]
    force_greats_config: Any
    manual_force_greats: bool
    baseline_team_buff: str
    db_key: str
    prev_record: Any
    known_loadouts: Any
    db_best_score: int
    db_best_fg_score: int
    attempt_lifetime: int
    attempts_first: int
    prev_attempts_first: int
    db_baseline_valid: bool
    outer_engine: str = "ga"
    pre_prune_mode: str = "auto"
    fg_search_radius: int | None = None
    gpu_song_slot: int = 0
    ga_seed: int | None = None
    solver_ctx: SolverContext | None = None


@dataclass
class OuterSearchResult:
    best_data: dict[str, Any] | None
    best_gear: list[dict]
    best_minis: list[dict]
    all_evaluated: list[dict[str, Any]]
    ga_candidates: list[dict[str, Any]]
    wall_sec: float = 0.0


@dataclass
class FGResult:
    fg_variants: list[dict[str, Any]] = field(default_factory=list)
    loadout_entries: Any = None
    wall_sec: float = 0.0


class _NullLogBuffer:
    """File-like sink that discards writes and avoids per-song StringIO growth."""

    __slots__ = ()

    def write(self, data):
        try:
            return len(data)
        except Exception as e:
            logger.warning(f"song_processor:write: {e}")
            return 0

    def flush(self):
        return None

    def getvalue(self):
        return ""

    def close(self):
        return None


def _nonfever_counts_from_config(config: object) -> tuple[int, ...]:
    if not isinstance(config, dict) or not config:
        return ()
    pairs: list[tuple[int, int]] = []
    for key, val in config.items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "").strip()) - 1
        except Exception as e:
            logger.warning(f"song_processor:_nonfever_counts_from_config: {e}")
            continue
        try:
            cnt = int(val or 0)
        except Exception as e:
            logger.warning(f"song_processor:_nonfever_counts_from_config: {e}")
            cnt = 0
        pairs.append((idx, max(0, cnt)))
    if not pairs:
        return ()
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    if max_idx < 0:
        return ()
    out = [0] * (max_idx + 1)
    for idx, cnt in pairs:
        if 0 <= idx < len(out):
            out[idx] = int(cnt)
    if sum(out) <= 0:
        return ()
    return tuple(int(v) for v in out)


def _setup_song_context(
    *,
    fp: str,
    found_song_name: str,
    effective_difficulty: str,
    cfg_dict: dict[str, Any],
    paths: Any,
    ref_arrays: dict[str, Any],
    all_gears: list[dict],
    all_minis: list[dict],
    gears_by_name: dict[str, Any],
    minis_by_name: dict[str, Any],
    auto_buff: bool,
    ga_depth: int,
    status_queue: Any,
    fg_debug: bool,
    defer_post: bool,
    preloaded_calc_song: dict[str, Any] | None,
    repeat_index: int,
    repeat_total: int,
    ga_seed: int | None,
    emit: Callable[[str], None],
    stage_timing: dict[str, float],
) -> SongContext:
    prepared_core = build_prepared_song_core(
        fp=fp,
        found_song_name=found_song_name,
        cfg_dict=cfg_dict,
        auto_buff=bool(auto_buff),
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        preloaded_calc_song=preloaded_calc_song,
        load_known_loadouts=True,
        allow_fallback=False,
    )
    cfg = prepared_core.cfg
    calc_song = prepared_core.calc_song
    prepared_config = prepared_core.prepared_config
    db_context = prepared_core.db_context
    stage_timing["cpu_read_sec"] = prepared_core.prepared_calc_song.read_sec
    if prepared_core.prepared_calc_song.timing_envelope_info is not None:
        stage_timing["cpu_timing_envelope_sec"] = prepared_core.prepared_calc_song.timing_envelope_sec
        try:
            sim_info = prepared_core.prepared_calc_song.timing_envelope_info
            print(
                f"[TimingEnvelope] Applied (mode={sim_info.get('mode')}, "
                f"great={sim_info.get('great_mode')}, notes={sim_info.get('notes')})"
            )
        except Exception as e:
            logger.warning(f"song_processor:_setup_song_context: {e}")

    stage_timing["cpu_setup_sec"] = prepared_core.setup_sec
    stage_timing["cpu_db_load_sec"] = prepared_core.db_load_sec

    emit("START")
    stage_timing["cpu_prep_sec"] = sum(
        float(stage_timing.get(key, 0.0) or 0.0)
        for key in ("cpu_read_sec", "cpu_human_hit_sim_sec", "cpu_setup_sec", "cpu_db_load_sec")
    )

    outer_engine = "ga"
    pre_prune_mode = "none"
    fg_search_radius = read_fg_search_radius(cfg)

    return SongContext(
        fp=fp,
        found_song_name=found_song_name,
        queue_label=str(found_song_name),
        effective_difficulty=effective_difficulty,
        cfg_dict=cfg_dict,
        cfg=cfg,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        auto_buff=bool(auto_buff),
        ga_depth=int(ga_depth),
        status_queue=status_queue,
        defer_post=bool(defer_post),
        emit=emit,
        stage_timing=stage_timing,
        repeat_index=int(repeat_index),
        repeat_total=int(repeat_total),
        fg_debug=bool(fg_debug),
        calc_song=calc_song,
        meta_primary_color=prepared_core.meta_primary_color,
        meta_secondary_color=prepared_core.meta_secondary_color,
        ga_settings=prepared_config.ga_settings,
        fixed_stats=prepared_config.fixed_stats,
        current_gear_stats=prepared_config.current_gear_stats,
        current_gear_list=prepared_config.current_gear_list,
        current_mini_stats=prepared_config.current_mini_stats,
        current_mini_list=prepared_config.current_mini_list,
        force_greats_config=prepared_config.force_greats_config,
        manual_force_greats=prepared_config.manual_force_greats,
        baseline_team_buff=str(db_context.baseline_team_buff or "T5"),
        db_key=db_context.db_key,
        prev_record=db_context.prev_record,
        known_loadouts=db_context.known_loadouts,
        db_best_score=int(db_context.db_best_score or 0),
        db_best_fg_score=int(db_context.db_best_fg_score or 0),
        attempt_lifetime=int(db_context.attempt_lifetime or 0),
        attempts_first=int(db_context.attempts_first),
        prev_attempts_first=int(db_context.prev_attempts_first or 0),
        db_baseline_valid=bool(db_context.db_baseline_valid),
        outer_engine=outer_engine,
        pre_prune_mode=pre_prune_mode,
        fg_search_radius=fg_search_radius,
        gpu_song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=ga_seed,
    )


def _run_outer_search(ctx: SongContext) -> OuterSearchResult:
    try:
        ctx.gpu_song_slot = int(ctx.calc_song.get("_gpu_song_slot", 0) or 0)
    except Exception as e:
        logger.warning(f"song_processor:_run_outer_search: {e}")
        ctx.gpu_song_slot = 0
    try:
        ctx.calc_song["_gpu_song_slot"] = int(ctx.gpu_song_slot)
    except Exception as e:
        logger.warning(f"song_processor:_run_outer_search: {e}")
    try:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields

        gpu_fields.configure_ga_run_buffers(
            max_runs=ctx.ga_settings.multi_start,
            max_genomes=GA_POPULATION_SIZE,
        )
    except Exception as e:
        logger.warning(f"song_processor:_run_outer_search: {e}")

    ctx.solver_ctx = prepare_solver_context(
        ctx.cfg,
        ctx.fixed_stats,
        ctx.calc_song,
        ctx.ref_arrays,
        ctx.all_gears,
        ctx.all_minis,
        optimize_gear=True,
        optimize_minis=True,
        fixed_gear=ctx.current_gear_list,
        fixed_minis=ctx.current_mini_list,
        pre_prune_mode="none",
        status_cb=lambda message: ctx.emit(message),
        song_slot=int(ctx.gpu_song_slot),
    )

    ga_start = time.perf_counter()
    best_data, best_gear, best_minis, _, _, _, all_evaluated = solve_coevolution_genetic(
        ctx.cfg,
        ctx.fixed_stats,
        ctx.paths,
        ctx.calc_song,
        ctx.ref_arrays,
        ctx.all_gears,
        ctx.all_minis,
        ctx.gears_by_name,
        ctx.minis_by_name,
        optimize_gear=True,
        optimize_minis=True,
        fixed_gear=ctx.current_gear_list,
        fixed_minis=ctx.current_mini_list,
        ga_depth=ctx.ga_depth,
        db_seed=ctx.prev_record if ctx.prev_record else None,
        ga_settings=ctx.ga_settings,
        status_cb=lambda message: ctx.emit(message),
        executor=None,
        known_loadouts=ctx.known_loadouts,
        song_slot=int(ctx.gpu_song_slot),
        ga_seed=ctx.ga_seed,
        solver_ctx=ctx.solver_ctx,
    )
    wall_sec = time.perf_counter() - ga_start
    if PERF_TIMING_ENABLED:
        print(f"[PERF] GA: {wall_sec:.2f}s")
    if ctx.known_loadouts:
        ctx.known_loadouts.clear()

    ga_candidates = list(all_evaluated or [])
    if best_data and best_gear and best_minis:
        base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
        ga_candidates.append(
            {
                "Score": base_score,
                "BaseScore": base_score,
                "Gear": best_gear,
                "Minis": best_minis,
                "Data": best_data,
            }
        )

    return OuterSearchResult(
        best_data=best_data,
        best_gear=list(best_gear or []),
        best_minis=list(best_minis or []),
        all_evaluated=list(all_evaluated or []),
        ga_candidates=ga_candidates,
        wall_sec=float(wall_sec),
    )


def _run_force_greats(ctx: SongContext, outer: OuterSearchResult) -> FGResult:
    ga_candidates = list(outer.ga_candidates or [])
    fg_candidate_limit = read_fg_candidate_limit(
        ctx.cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    ga_candidates = select_fg_candidates(
        ga_candidates,
        limit=fg_candidate_limit,
        primary_color=str(ctx.meta_primary_color or ""),
        secondary_color=str(ctx.meta_secondary_color or ""),
    )

    build_details = make_build_details_fn(ctx.meta_primary_color, ctx.meta_secondary_color, ctx.effective_difficulty)
    fg_variants: list[dict[str, Any]] = []
    loadout_entries = None
    fg_wall_sec = 0.0
    direct_ga_candidates_for_fg = not bool(ctx.manual_force_greats)

    loadout_entries = build_loadout_entries(
        ctx.found_song_name,
        [] if direct_ga_candidates_for_fg else ga_candidates,
        fg_candidate_limit,
        ctx.gears_by_name,
        ctx.minis_by_name,
        build_details,
        team_buff=str(ctx.baseline_team_buff or "T5"),
        materialize_ga_details=False,
    )

    fg_start = time.perf_counter()
    fg_variants = process_force_greats(
        loadout_entries,
        ctx.manual_force_greats,
        direct_ga_candidates_for_fg,
        ctx.force_greats_config,
        ctx.calc_song,
        ctx.ref_arrays,
        ctx.meta_primary_color,
        build_details,
        use_gpu=True,
        fg_search_radius=ctx.fg_search_radius,
        perf_timing=PERF_TIMING_ENABLED,
        ga_candidates=ga_candidates if direct_ga_candidates_for_fg else None,
        ga_registry=ctx.solver_ctx.registry if direct_ga_candidates_for_fg and ctx.solver_ctx is not None else None,
    )
    fg_wall_sec = time.perf_counter() - fg_start
    if PERF_TIMING_ENABLED:
        n_loadouts = len(loadout_entries) if loadout_entries else 0
        print(f"[PERF] ForceGreats: {fg_wall_sec:.2f}s ({n_loadouts} loadouts)")

    outer.ga_candidates = ga_candidates
    return FGResult(fg_variants=fg_variants, loadout_entries=loadout_entries, wall_sec=float(fg_wall_sec))


def _build_and_persist(
    ctx: SongContext,
    outer: OuterSearchResult,
    fg: FGResult,
    *,
    buf: Any,
    capture_log_payload: bool,
) -> SongResultPayload:
    build_details = make_build_details_fn(ctx.meta_primary_color, ctx.meta_secondary_color, ctx.effective_difficulty)
    db_payload = None
    persist_entries = None
    buf_content = ""

    if ctx.defer_post and outer.best_data:
        if capture_log_payload:
            buf_content = buf.getvalue() if buf else ""

        try:
            record_info = evaluate_progress_record_update(
                outer.best_data,
                ctx.prev_record,
                fg.fg_variants,
                db_best_fg_score=ctx.db_best_fg_score,
                baseline_valid=bool(ctx.db_baseline_valid),
            )
        except Exception as e:
            logger.warning(f"song_processor:_build_and_persist: {e}")
            record_info = None

        return cast(
            SongResultPayload,
            {
                "_deferred_post": True,
                "song": ctx.found_song_name,
                "_queue_key": ctx.queue_label,
                "_queue_label": ctx.queue_label,
                "_repeat_index": int(ctx.repeat_index),
                "_repeat_total": int(ctx.repeat_total),
                "_ga_seed": int(ctx.ga_seed) if ctx.ga_seed is not None else None,
                "db_key": ctx.db_key,
                "file_path": ctx.fp,
                "difficulty": ctx.effective_difficulty,
                "cfg_dict": ctx.cfg_dict,
                "ref_arrays": ctx.ref_arrays,
                "calc_song": ctx.calc_song,
                "best_data": outer.best_data,
                "best_gear": compact_item_names(outer.best_gear),
                "best_minis": compact_item_names(outer.best_minis),
                "current_gear": compact_item_names(ctx.current_gear_list),
                "current_minis": compact_item_names(ctx.current_mini_list),
                "fg_variants": compact_fg_variants(fg.fg_variants),
                "ga_candidates": compact_ga_candidates(outer.ga_candidates),
                "loadout_entries": compact_loadout_entries(fg.loadout_entries),
                "prev_record": compact_prev_record(ctx.prev_record),
                "attempt_lifetime": ctx.attempt_lifetime,
                "prev_attempts_first": ctx.prev_attempts_first,
                "db_best_score": ctx.db_best_score,
                "db_best_fg_score": ctx.db_best_fg_score,
                "db_baseline_valid": bool(ctx.db_baseline_valid),
                "meta_primary_color": ctx.meta_primary_color,
                "meta_secondary_color": ctx.meta_secondary_color,
                "fg_debug": bool(ctx.fg_debug),
                "_record": record_info,
                "log": buf_content,
            },
        )

    if outer.best_data:
        t_db0 = time.perf_counter()
        db_payload = build_db_payload(
            outer.best_data,
            outer.best_gear,
            outer.best_minis,
            ctx.prev_record,
            ctx.attempt_lifetime,
            ctx.attempts_first,
            fg.fg_variants,
            build_details,
            db_best_fg_score=ctx.db_best_fg_score,
        )
        ctx.stage_timing["_db_payload_sec"] = time.perf_counter() - t_db0

        t_persist0 = time.perf_counter()
        persist_entries = canonicalize_and_assemble(
            db_payload=db_payload,
            ga_candidates=outer.ga_candidates,
            loadout_entries=fg.loadout_entries,
            build_details_fn=build_details,
            replay_ctx=ReplayContext(
                calc_song=ctx.calc_song,
                ref_arrays=ctx.ref_arrays,
                cfg_dict=ctx.cfg_dict,
            ),
        )
        ctx.stage_timing["_persist_build_sec"] = time.perf_counter() - t_persist0

        t_report0 = time.perf_counter()
        print_results(
            ctx.found_song_name,
            outer.best_data,
            outer.best_gear,
            outer.best_minis,
            ctx.current_gear_list,
            ctx.current_mini_list,
            fg.fg_variants,
            ctx.emit,
            fg_debug=ctx.fg_debug,
            ref_arrays=ctx.ref_arrays,
            calc_song=ctx.calc_song,
            cfg=ctx.cfg,
            db_best_fg_score=ctx.db_best_fg_score,
            prev_record=ctx.prev_record,
        )
        ctx.stage_timing["_report_sec"] = time.perf_counter() - t_report0

        if PERF_TIMING_ENABLED:
            print(
                f"[PERF] DB/Persist/Report: payload={ctx.stage_timing.get('_db_payload_sec', 0.0):.3f}s "
                f"persist={ctx.stage_timing.get('_persist_build_sec', 0.0):.3f}s "
                f"report={ctx.stage_timing.get('_report_sec', 0.0):.3f}s"
            )
    else:
        print(f"[ERROR] Optimization failed for {ctx.found_song_name} - best_data is None")
        log_tail = buf.getvalue()[-500:] if buf else "No log buffer"
        db_payload = {
            "score": 0,
            "fg_score": 0,
            "gear": [],
            "minis": [],
            "details": {"Error": "Optimization failed - no valid loadout found", "LogTail": log_tail},
            "force": None,
        }

    if capture_log_payload:
        buf_content = buf.getvalue() if buf else ""

    return cast(
        SongResultPayload,
        {
            "song": ctx.found_song_name,
            "_queue_key": ctx.queue_label,
            "_queue_label": ctx.queue_label,
            "_repeat_index": int(ctx.repeat_index),
            "_repeat_total": int(ctx.repeat_total),
            "_ga_seed": int(ctx.ga_seed) if ctx.ga_seed is not None else None,
            "db_key": ctx.db_key,
            "file_path": ctx.fp,
            "difficulty": ctx.effective_difficulty,
            "cfg_dict": ctx.cfg_dict,
            "db_payload": db_payload,
            "_record": db_payload.get("_record") if isinstance(db_payload, dict) else None,
            "prev_record": ctx.prev_record,
            "fg_variants": fg.fg_variants,
            "attempt_lifetime": ctx.attempt_lifetime,
            "prev_attempts_first": ctx.prev_attempts_first,
            "db_best_score": ctx.db_best_score,
            "db_best_fg_score": ctx.db_best_fg_score,
            "db_baseline_valid": bool(ctx.db_baseline_valid),
            "best_data": outer.best_data,
            "best_gear": outer.best_gear,
            "best_minis": outer.best_minis,
            "persist_entries": persist_entries if outer.best_data else [],
            "log": buf_content,
        },
    )


def process_song_task(args) -> SongResultPayload:
    """
    Run a single song end-to-end optimization.

    REFACTORED: Extracted helper functions where practical; this entrypoint remains
    orchestration-heavy because it owns per-song setup, solver routing, and persistence.

    Main steps:
    1. Parse arguments and setup
    2. Read song file
    3. Load previous best from database (if using DB)
    4. Run GA or gem solver only
    5. Apply force greats if enabled
    6. Build persistence payload
    7. Cleanup and return results

    Args:
        args: Tuple of (fp, song_name, difficulty, cfg_dict, paths, ref_arrays,
                        all_gears, all_minis, gears_by_name, minis_by_name,
                        auto_buff, ga_depth, status_queue, parallel_workers)

    Returns:
        dict: Result with song, db_key, db_payload, best_data, persist_entries, log
    """
    # --- CRITICAL: Clear caches at start of task to prevent OOM in worker process ---
    # These globals persist in the worker process if not cleared, leading to memory leaks
    # especially when GA is skipped (Calculate-Only mode) but caches are still populated.
    GEM_SOLVER_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()
    FG_CACHE.clear()

    args_list = list(args) if isinstance(args, (list, tuple)) else [args]
    task_view = task_tuple_to_legacy_view(args_list)
    job = task_view.job
    run_context = task_view.context
    seed_plan = seed_plan_from_song_job(job)
    fp = job.file_path
    found_song_name = job.song_name
    effective_difficulty = job.difficulty
    cfg_dict = run_context.cfg_dict
    paths = run_context.paths
    ref_arrays = run_context.ref_arrays
    all_gears = run_context.all_gears
    all_minis = run_context.all_minis
    gears_by_name = run_context.gears_by_name
    minis_by_name = run_context.minis_by_name
    auto_buff = run_context.auto_buff
    ga_depth = run_context.ga_depth
    status_queue = run_context.status_queue
    fg_debug = run_context.fg_debug

    # Optional extras (sequential pipeline mode):
    # - preloaded calc_song dict to avoid repeated disk I/O + parsing
    # - defer_post: if True, skip persistence/reporting and return raw compute payload
    preloaded_calc_song = None
    defer_post = False
    extras = task_view.extras
    if extras:
        for extra in extras:
            if isinstance(extra, dict):
                if extra.get("song_data") is not None:
                    preloaded_calc_song = extra
                    continue
            if isinstance(extra, bool) and not defer_post:
                defer_post = bool(extra)

    queue_label = seed_plan.queue_label
    ga_seed = seed_plan.ga_seed
    repeat_index = seed_plan.repeat_index
    repeat_total = seed_plan.repeat_total

    # Initialize variables at function start to avoid 'in locals()' pattern issues
    loadout_entries = None
    known_loadouts = None

    # Capture logs only when explicitly requested; otherwise sink output without growing
    # per-song buffers that are discarded by the coordinator.
    buf = StringIO() if _CAPTURE_SONG_LOG_PAYLOAD else _NullLogBuffer()
    output_enabled = bool(getattr(ENV, "output_enabled", False))
    tee = Tee(sys.stdout, buf) if output_enabled else Tee(buf)
    redirect_ctx = contextlib.redirect_stdout(tee)
    redirect_err_ctx = contextlib.redirect_stderr(tee)
    redirect_ctx.__enter__()
    redirect_err_ctx.__enter__()

    # Memory leak tracking: Log memory at start of song
    log_memory_usage(f"Start: {found_song_name}")

    # GPU profiler: track song processing time
    _gpu_profiler.start_song(found_song_name)

    result_payload = None
    stage_timing: dict[str, float] = {}
    _song_wall_t0 = time.perf_counter()
    _cpu_prep_t0 = _song_wall_t0
    ga_time_sec = 0.0
    fg_time_sec = 0.0
    db_payload_time_sec = 0.0
    persist_build_time_sec = 0.0
    report_time_sec = 0.0
    # GPU timeline slot reuse (GA -> FG). Keep these in outer scope for cleanup.
    _gpu_song_slot = 0

    try:
        def emit(msg):
            if not status_queue:
                return
            try:
                payload = f"[{queue_label or found_song_name}] {msg}"
            except Exception as e:
                logger.warning(f"song_processor:emit: {e}")
                payload = str(msg)
            try:
                put_nowait = getattr(status_queue, "put_nowait", None)
                if callable(put_nowait):
                    put_nowait(payload)
                else:
                    status_queue.put(payload, block=False)
            except Exception as e:
                logger.warning(f"song_processor:emit: {e}")

        song_ctx = _setup_song_context(
            fp=fp,
            found_song_name=found_song_name,
            effective_difficulty=effective_difficulty,
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            auto_buff=auto_buff,
            ga_depth=ga_depth,
            status_queue=status_queue,
            fg_debug=fg_debug,
            defer_post=defer_post,
            preloaded_calc_song=preloaded_calc_song,
            repeat_index=repeat_index,
            repeat_total=repeat_total,
            ga_seed=ga_seed,
            emit=emit,
            stage_timing=stage_timing,
        )
        song_ctx.queue_label = queue_label

        outer_result = _run_outer_search(song_ctx)
        fg_result = _run_force_greats(song_ctx, outer_result)
        loadout_entries = fg_result.loadout_entries
        known_loadouts = song_ctx.known_loadouts
        _gpu_song_slot = int(song_ctx.gpu_song_slot)

        result_payload = _build_and_persist(
            song_ctx,
            outer_result,
            fg_result,
            buf=buf,
            capture_log_payload=_CAPTURE_SONG_LOG_PAYLOAD,
        )

        ga_time_sec = float(outer_result.wall_sec)
        fg_time_sec = float(fg_result.wall_sec)
        db_payload_time_sec = float(song_ctx.stage_timing.get("_db_payload_sec", 0.0) or 0.0)
        persist_build_time_sec = float(song_ctx.stage_timing.get("_persist_build_sec", 0.0) or 0.0)
        report_time_sec = float(song_ctx.stage_timing.get("_report_sec", 0.0) or 0.0)
        return cast(SongResultPayload, result_payload)
    finally:
        # Memory leak tracking: Log before cleanup
        log_memory_usage(f"Before cleanup: {found_song_name}")

        # GPU profiler: end song tracking
        _song_gpu_timing = _gpu_profiler.end_song()
        stage_timing["song_wall_sec"] = time.perf_counter() - _song_wall_t0
        stage_timing["cpu_post_sec"] = (
            float(db_payload_time_sec) + float(persist_build_time_sec) + float(report_time_sec)
        )
        stage_timing["cpu_ga_wall_sec"] = float(ga_time_sec)
        stage_timing["cpu_fg_wall_sec"] = float(fg_time_sec)

        if isinstance(result_payload, dict):
            result_payload.setdefault("_stage_timing", {}).update(stage_timing)
            if _song_gpu_timing is not None:
                result_payload.setdefault("_gpu_timing", {}).update(
                    {
                        "kernel_sec": float(getattr(_song_gpu_timing, "kernel_sec", 0.0) or 0.0),
                        "upload_sec": float(getattr(_song_gpu_timing, "upload_sec", 0.0) or 0.0),
                        "download_sec": float(getattr(_song_gpu_timing, "download_sec", 0.0) or 0.0),
                        "kernel_calls": int(getattr(_song_gpu_timing, "kernel_calls", 0) or 0),
                        "genome_evaluations": int(getattr(_song_gpu_timing, "genome_evaluations", 0) or 0),
                        "total_sec": float(getattr(_song_gpu_timing, "total_sec", 0.0) or 0.0),
                    }
                )

        # Prevent memory leak from unbounded cache growth across thousands of songs
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        # Memory leak fix: Clear local data structures explicitly
        # Using direct checks instead of 'in locals()' pattern (more reliable)
        if loadout_entries is not None:
            loadout_entries.clear()
        if known_loadouts is not None:
            known_loadouts.clear()

        # Memory leak fix: Close StringIO buffer explicitly
        # This buffer can hold 10-100MB of captured output per song
        if buf is not None:
            try:
                buf.close()
            except Exception as e:
                # Log buffer close failures (was silently suppressed)
                logging.debug(f"[StringIO] Failed to close buffer: {e}")

        # Deterministic periodic full GC to cap long-run memory growth.
        global _SONG_GC_COUNTER
        _SONG_GC_COUNTER += 1
        if _SONG_GC_COUNTER % _SONG_GC_GEN2_INTERVAL == 0:
            gc.collect(generation=2)

        # Memory leak tracking: Log after cleanup
        log_memory_usage(f"After cleanup: {found_song_name}")

        redirect_ctx.__exit__(None, None, None)
        redirect_err_ctx.__exit__(None, None, None)

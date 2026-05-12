from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

import numpy as np

from gear_optimizer.core.config import (
    GASettings as GARuntimeSettings,
    GPUExecutionSettings,
    read_fg_candidate_limit,
    read_fg_solver_mode,
)
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.gem_defs import UserGemsSettings
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.domain.jobs import seed_plan_from_song_job, task_tuple_to_legacy_view
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.inflight_utils import (
    _build_calc_song_from_file,
    _truthy,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.song_db_context import load_prepared_song_db_context
from gear_optimizer.solver.song_preparation import build_prepared_song_config
from gear_optimizer.solver.native_inflight_support import _lru_get, _lru_put
from gear_optimizer.solver.native_inflight_timing import _thread_cpu_time_s
from gear_optimizer.solver.native_inflight_types import (
    _NativeSong,
    _NativeSongConfig,
    _NativeSongGPUInputs,
    _NativeSongDBState,
    _NativeSongRuntimeState,
)

from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)


_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_INIT_HEURISTIC_CACHE_MAX = 64
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_INIT_HEURISTIC_TOPK_CACHE: "OrderedDict[tuple[tuple[str, str, tuple[str, ...]], int], np.ndarray]" = OrderedDict()
_REGISTRY_GPU_FIXED_CACHE: "OrderedDict[tuple, tuple[ItemRegistry, dict]]" = OrderedDict()

# Optional cache hit/miss stats (helps tune CPU requirements on low-end machines).
_CACHE_STATS = {
    "pools_hit": 0,
    "pools_miss": 0,
    "registry_hit": 0,
    "registry_miss": 0,
    "heur_hit": 0,
    "heur_miss": 0,
}
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_STATS_LAST_EMIT = 0.0


def bump_prep_cache_limits_for_ram_mode() -> tuple[int, int, int]:
    # Allow more caching when the user explicitly opts into higher RAM usage.
    global _POOL_CACHE_MAX, _REGISTRY_CACHE_MAX, _INIT_HEURISTIC_CACHE_MAX

    _POOL_CACHE_MAX = max(int(_POOL_CACHE_MAX), 128)
    _REGISTRY_CACHE_MAX = max(int(_REGISTRY_CACHE_MAX), 128)
    _INIT_HEURISTIC_CACHE_MAX = max(int(_INIT_HEURISTIC_CACHE_MAX), 256)
    return int(_POOL_CACHE_MAX), int(_REGISTRY_CACHE_MAX), int(_INIT_HEURISTIC_CACHE_MAX)


def _cache_stats_enabled() -> bool:
    return _truthy(env_get("INFLIGHT_CACHE_STATS", "0"))


def _cache_stats_emit_interval_s() -> float:
    try:
        return float(env_get("INFLIGHT_CACHE_STATS_EMIT_SEC", "30") or "30")
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_cache_stats_emit_interval_s: {e}")
        return 30.0


def _cache_stats_inc(key: str) -> None:
    try:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS[key] = int(_CACHE_STATS.get(key, 0) or 0) + 1
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_cache_stats_inc: {e}")
        return


def _cache_stats_maybe_emit() -> None:
    if not _cache_stats_enabled():
        return
    interval = float(_cache_stats_emit_interval_s())
    if interval <= 0:
        return
    now = time.monotonic()
    global _CACHE_STATS_LAST_EMIT
    try:
        with _CACHE_STATS_LOCK:
            if (now - float(_CACHE_STATS_LAST_EMIT)) < interval:
                return
            _CACHE_STATS_LAST_EMIT = now
            snap = dict(_CACHE_STATS)
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_cache_stats_maybe_emit: {e}")
        return
    try:
        pools_h = int(snap.get("pools_hit", 0) or 0)
        pools_m = int(snap.get("pools_miss", 0) or 0)
        reg_h = int(snap.get("registry_hit", 0) or 0)
        reg_m = int(snap.get("registry_miss", 0) or 0)
        heur_h = int(snap.get("heur_hit", 0) or 0)
        heur_m = int(snap.get("heur_miss", 0) or 0)
        logger.debug(
            "[InFlight][CacheStats] pools hit=%s miss=%s | registry hit=%s miss=%s | heur_topk hit=%s miss=%s",
            pools_h,
            pools_m,
            reg_h,
            reg_m,
            heur_h,
            heur_m,
        )
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_cache_stats_maybe_emit: {e}")


def _fixed_registry_cache_key(
    *,
    pool_key: tuple[str, str, tuple[str, ...]],
    fixed_gear: list[dict] | None,
    fixed_minis: list[dict] | None,
) -> tuple:
    def _n(it: dict | None) -> str:
        try:
            return str((it or {}).get("Name", "") or "")
        except Exception as e:
            logger.debug(f"native_inflight_prepare:_n: {e}")
            return ""

    fg = tuple(_n(it) for it in (fixed_gear or [])[:6])
    fm = tuple(sorted(_n(it) for it in (fixed_minis or [])[:3]))
    return ("fixed", pool_key, fg, fm)


def _prepare_song(task: tuple) -> _NativeSong:
    cpu_t0 = _thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_view = task_tuple_to_legacy_view(task)
    job = task_view.job
    seed_plan = seed_plan_from_song_job(job)
    task_key = seed_plan.queue_label
    ga_seed = seed_plan.ga_seed
    run_context = task_view.context
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
    use_evo_db = run_context.use_evo_db
    auto_buff = run_context.auto_buff
    ga_depth = run_context.ga_depth
    fg_debug = run_context.fg_debug

    cfg = cfg_from_dict(cfg_dict)

    gpu_settings = GPUExecutionSettings.from_config(cfg)
    gpu_mode = bool(gpu_settings.gpu_mode)
    if not gpu_mode:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Mode=true")

    gpu_native = bool(gpu_settings.gpu_native_ga)
    if not gpu_native:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Native_GA=true")

    calc_song = _build_calc_song_from_file(
        fp=fp,
        found_song_name=found_song_name,
        cfg=cfg,
        cfg_dict=cfg_dict,
    )
    meta_primary_color = str(calc_song.get("metadata", {}).get("Primary Color", "") or "")
    meta_secondary_color = str(calc_song.get("metadata", {}).get("Secondary Color", "") or "")

    prepared_config = build_prepared_song_config(
        cfg=cfg,
        calc_song=calc_song,
        auto_buff=bool(auto_buff),
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
    )
    ga_settings = prepared_config.ga_settings
    fixed_stats = prepared_config.fixed_stats
    current_gear_list = prepared_config.current_gear_list
    current_mini_list = prepared_config.current_mini_list
    enable_mini = prepared_config.enable_mini
    enable_gear = prepared_config.enable_gear
    force_greats_finder = prepared_config.force_greats_finder
    force_greats_config = prepared_config.force_greats_config
    manual_force_greats = prepared_config.manual_force_greats

    if not (enable_gear or enable_mini):
        raise RuntimeError("GPU-native in-flight currently requires MetaFinder (enable gear or minis).")

    # Load DB seed record only; full known-loadout hydration is deferred/prefetched
    # in FG prep to avoid redundant per-song DB reads during prepare.
    db_context = load_prepared_song_db_context(
        found_song_name=found_song_name,
        calc_song=calc_song,
        cfg=cfg,
        cfg_dict=cfg_dict,
        use_evo_db=bool(use_evo_db),
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        load_known_loadouts=False,
        allow_fallback=False,
        cache_seed_context=True,
    )
    db_key = db_context.db_key
    prev_record = db_context.prev_record
    db_best_score = db_context.db_best_score
    db_best_fg_score = db_context.db_best_fg_score
    attempt_lifetime = db_context.attempt_lifetime
    prev_attempts_first = db_context.prev_attempts_first
    db_baseline_valid = db_context.db_baseline_valid
    allow_db_seed = db_context.allow_db_seed

    p_color = calc_song.get("metadata", {}).get("Primary Color", "Rush")
    s_color = calc_song.get("metadata", {}).get("Secondary Color", "")
    selected_color = p_color
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pool_key = (str(p_color), str(s_color), tuple(slots))
    with _PREP_CACHE_LOCK:
        cached_pools = _lru_get(_POOL_CACHE, pool_key)
    if cached_pools is None:
        _cache_stats_inc("pools_miss")
        pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
        if pools is None:
            raise RuntimeError("initialize_pools returned None")
        if len(pools) == 4:
            gear_pool, mini_pool, _total_before, _total_after = pools
        else:
            gear_pool, mini_pool, _total_before, _total_after, _whitelisted_minis = pools
        if gear_pool is None:
            raise RuntimeError("initialize_pools failed (gear_pool is None)")
        with _PREP_CACHE_LOCK:
            _lru_put(_POOL_CACHE, pool_key, (gear_pool, mini_pool), maxsize=_POOL_CACHE_MAX)
    else:
        _cache_stats_inc("pools_hit")
        gear_pool, mini_pool = cached_pools

    cacheable_registry = bool(enable_gear and enable_mini)
    if cacheable_registry:
        with _PREP_CACHE_LOCK:
            cached_registry = _lru_get(_REGISTRY_GPU_CACHE, pool_key)
        if cached_registry is None:
            _cache_stats_inc("registry_miss")
            registry = ItemRegistry(gear_pool, mini_pool, slots)
            gpu_data = registry.to_gpu_arrays()
            with _PREP_CACHE_LOCK:
                _lru_put(_REGISTRY_GPU_CACHE, pool_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
        else:
            _cache_stats_inc("registry_hit")
            registry, gpu_data = cached_registry
    else:
        fixed_gear = list(current_gear_list or [])[:6] if not enable_gear else None
        fixed_minis = list(current_mini_list or [])[:3] if not enable_mini else None
        cache_key = _fixed_registry_cache_key(pool_key=pool_key, fixed_gear=fixed_gear, fixed_minis=fixed_minis)
        cached_fixed = None
        with _PREP_CACHE_LOCK:
            cached_fixed = _lru_get(_REGISTRY_GPU_FIXED_CACHE, cache_key)
        if cached_fixed is None:
            _cache_stats_inc("registry_miss")
            registry = ItemRegistry(gear_pool, mini_pool, slots, fixed_gear=fixed_gear, fixed_minis=fixed_minis)
            gpu_data = registry.to_gpu_arrays()
            with _PREP_CACHE_LOCK:
                _lru_put(_REGISTRY_GPU_FIXED_CACHE, cache_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
        else:
            _cache_stats_inc("registry_hit")
            registry, gpu_data = cached_fixed
    _cache_stats_maybe_emit()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    fg_solver_mode = read_fg_solver_mode(cfg, default="finder")

    ga_runtime_settings = GARuntimeSettings.from_config(cfg)
    user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)
    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "fg_candidate_limit": int(fg_candidate_limit),
        "fg_solver_mode": str(fg_solver_mode or "finder"),
        "user_ft": int(user_gems.fever_time),
        "user_ff": int(user_gems.fever_fill),
        "user_pp": int(user_gems.perfect_points),
        "user_cm": int(user_gems.combo_multiplier),
        "user_fm": int(user_gems.fever_multiplier),
        "static_elem_input": int(user_gems.static_element),
    }
    cfg_data["ga_convergence_trace_enabled"] = bool(ga_runtime_settings.convergence_trace)
    cfg_data["ga_convergence_trace_every"] = int(ga_runtime_settings.convergence_trace_every)
    cfg_data["ga_convergence_trace_out_dir"] = str(ga_runtime_settings.convergence_trace_out_dir)
    cfg_data["ga_convergence_trace_song_filter"] = str(ga_runtime_settings.convergence_trace_song_filter)
    cfg_data["ga_novelty_repair_attempts"] = int(ga_runtime_settings.novelty_repair_attempts)

    # ForceGreatsFinder runs after GA and needs per-candidate BaseStats for signature grouping.
    # The GPU-native GA decode step keeps full post-gem Stats optional so the critical
    # GA->FG handoff does not spend CPU rebuilding data that the FG grouping path does not use.
    cfg_data["fg_require_stats"] = bool(manual_force_greats or force_greats_finder)

    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)

    tournament_k = int(ga_runtime_settings.tournament_k)
    mutation_rate = float(ga_runtime_settings.mutation_rate)
    immigrant_rate = float(ga_runtime_settings.immigrant_rate)

    db_seed = prev_record if (allow_db_seed and prev_record) else None
    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1

    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)

    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 0
    try:
        init_heuristic_k = int(str(env_get("GPU_GA_INIT_HEURISTIC_K", "64") or "64"))
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_prepare_song: {e}")
        init_heuristic_k = 64
    init_heuristic_k = max(0, int(init_heuristic_k))
    init_heuristic_copies = 25

    db_seed_ids: Optional[np.ndarray] = None

    try:
        from gear_optimizer.solver.genetic import build_ga_init_heuristic_topk, extract_db_seed_ids

        if init_heuristic_k > 0:
            cache_key = None
            if cacheable_registry:
                cache_key = (pool_key, int(init_heuristic_k))
                with _PREP_CACHE_LOCK:
                    init_heuristic_topk = _lru_get(_INIT_HEURISTIC_TOPK_CACHE, cache_key)
                if init_heuristic_topk is None:
                    _cache_stats_inc("heur_miss")
                else:
                    _cache_stats_inc("heur_hit")

            if init_heuristic_topk is None:
                init_heuristic_topk = build_ga_init_heuristic_topk(
                    item_stats=gpu_data["item_stats"],
                    slot_start=gpu_data["slot_start"],
                    slot_count=gpu_data["slot_count"],
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    heuristic_k=int(init_heuristic_k),
                    n_slots=9,
                )
                if cache_key is not None and init_heuristic_topk is not None:
                    with _PREP_CACHE_LOCK:
                        _lru_put(
                            _INIT_HEURISTIC_TOPK_CACHE,
                            cache_key,
                            np.asarray(init_heuristic_topk, dtype=np.int32),
                            maxsize=_INIT_HEURISTIC_CACHE_MAX,
                        )

        db_seed_ids = extract_db_seed_ids(db_seed=db_seed, registry=registry, n_slots=9)
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_prepare_song: {e}")
        init_heuristic_topk = None
        db_seed_ids = None

    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0

    color_flags = build_color_flags(p_color, s_color, selected_color)

    elite_count = max(0, int(ga_runtime_settings.elite_count))

    song = _NativeSong(
        config=_NativeSongConfig(
            fp=str(fp),
            song_name=str(found_song_name),
            task_key=str(task_key),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            db_key=str(db_key),
            effective_difficulty=str(effective_difficulty),
            cfg_dict=cfg_dict,
            cfg=cfg,
            paths=paths,
            use_evo_db=bool(use_evo_db),
            auto_buff=bool(auto_buff),
            ga_depth=int(ga_depth),
            fg_debug=bool(fg_debug),
        ),
        gpu_inputs=_NativeSongGPUInputs(
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            calc_song=calc_song,
            meta_primary_color=meta_primary_color,
            meta_secondary_color=meta_secondary_color,
            fixed_stats=fixed_stats,
            current_gear_list=current_gear_list,
            current_mini_list=current_mini_list,
            enable_gear=bool(enable_gear),
            enable_mini=bool(enable_mini),
            force_greats_finder=bool(force_greats_finder),
            force_greats_config=force_greats_config,
            manual_force_greats=bool(manual_force_greats),
            registry=registry,
            cfg_data=cfg_data,
            color_flags=color_flags,
            gens_per_run=int(gens_per_run),
            num_runs=int(num_runs),
            n_genomes=int(n_genomes),
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
            elite_count=int(elite_count),
            mutation_rate=float(mutation_rate),
            immigrant_rate=float(immigrant_rate),
            tournament_k=int(tournament_k),
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(init_heuristic_k),
            init_heuristic_copies=int(init_heuristic_copies),
            db_seed_ids=db_seed_ids,
            db_seed_prob=float(getattr(ga_settings, "db_seed_prob", 0.0) or 0.0) if db_seed_ids is not None else 0.0,
            db_seed_copies=int(getattr(ga_settings, "fixed_seed_copies", 1) or 0) if db_seed_ids is not None else 0,
            db_seed_mutations=int(getattr(ga_settings, "db_seed_mutations", 1) or 0) if db_seed_ids is not None else 0,
        ),
        runtime=_NativeSongRuntimeState(
            db=_NativeSongDBState(
                prev_record=prev_record,
                db_best_score=int(db_best_score),
                attempt_lifetime=int(attempt_lifetime),
                prev_attempts_first=int(prev_attempts_first),
                db_best_fg_score=int(db_best_fg_score),
                db_baseline_valid=bool(db_baseline_valid),
            ),
        ),
    )
    try:
        song.runtime.prep.cpu_prep_s = max(0.0, _thread_cpu_time_s() - float(cpu_t0))
    except Exception as e:
        logger.debug(f"native_inflight_prepare:_prepare_song: {e}")
    return song

"""LRU prep caches and native song preparation for in-flight orchestration."""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.config import GASettings as GARuntimeSettings
from gear_optimizer.core.gem_defs import UserGemsSettings
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.domain.jobs import seed_plan_from_song_job, task_tuple_to_view
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.native_inflight_config import (
    NativeSong,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.native_inflight_pipeline import prepare_fg_static_sync, thread_cpu_time_s
from gear_optimizer.solver.song_preparation import build_prepared_song_core

logger = logging.getLogger(__name__)

_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_INIT_HEURISTIC_CACHE_MAX = 64
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_INIT_HEURISTIC_TOPK_CACHE: "OrderedDict[tuple[tuple[str, str, tuple[str, ...]], int], np.ndarray]" = OrderedDict()
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


def _lru_get(cache: OrderedDict, key: tuple):
    try:
        value = cache.get(key)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_get: {e}")
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:_lru_get: {e}")
    return value


def _lru_put(cache: OrderedDict, key: tuple, value, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_put: {e}")
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_put: {e}")


def _cache_stats_enabled() -> bool:
    return _truthy(env_get("INFLIGHT_CACHE_STATS", "0"))


def _cache_stats_emit_interval_s() -> float:
    try:
        return float(env_get("INFLIGHT_CACHE_STATS_EMIT_SEC", "30") or "30")
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_emit_interval_s: {e}")
        return 30.0


def _cache_stats_inc(key: str) -> None:
    try:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS[key] = int(_CACHE_STATS.get(key, 0) or 0) + 1
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_inc: {e}")
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
        logger.debug(f"native_inflight_lifecycle:_cache_stats_maybe_emit: {e}")
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
        logger.debug(f"native_inflight_lifecycle:_cache_stats_maybe_emit: {e}")


def prepare_native_song(task: tuple) -> NativeSong:
    wall_t0 = time.perf_counter()
    cpu_t0 = thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_view = task_tuple_to_view(task)
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
    ga_depth = run_context.ga_depth
    fg_debug = run_context.fg_debug
    cfg = cfg_from_dict(cfg_dict)
    prepared_core = build_prepared_song_core(
        fp=fp,
        found_song_name=found_song_name,
        cfg_dict=cfg_dict,
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        cfg=cfg,
        cache_db_context=True,
    )
    calc_song = prepared_core.calc_song
    meta_primary_color = prepared_core.meta_primary_color
    meta_secondary_color = prepared_core.meta_secondary_color
    prepared_config = prepared_core.prepared_config
    ga_settings = prepared_config.ga_settings
    fixed_stats = prepared_config.fixed_stats
    current_gear_list = prepared_config.current_gear_list
    current_mini_list = prepared_config.current_mini_list
    db_context = prepared_core.db_context
    db_key = db_context.db_key
    prev_record = db_context.prev_record
    db_best_score = db_context.db_best_score
    db_best_fg_score = db_context.db_best_fg_score
    attempt_lifetime = db_context.attempt_lifetime
    prev_attempts_first = db_context.prev_attempts_first
    db_baseline_valid = db_context.db_baseline_valid
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
    _cache_stats_maybe_emit()
    ga_runtime_settings = GARuntimeSettings.from_config(cfg)
    user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)
    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "user_ft": int(user_gems.fever_time),
        "user_ff": int(user_gems.fever_fill),
        "user_pp": int(user_gems.perfect_points),
        "user_cm": int(user_gems.combo_multiplier),
        "user_fm": int(user_gems.fever_multiplier),
        "static_elem_input": int(user_gems.static_element),
    }
    cfg_data["ga_novelty_repair_attempts"] = int(ga_runtime_settings.novelty_repair_attempts)
    cfg_data["fg_require_stats"] = True
    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)
    tournament_k = int(ga_runtime_settings.tournament_k)
    mutation_rate = float(ga_runtime_settings.mutation_rate)
    immigrant_rate = float(ga_runtime_settings.immigrant_rate)
    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1
    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 64  # heuristic-seeded initial genomes (was GPU_GA_INIT_HEURISTIC_K)
    init_heuristic_copies = 25
    try:
        from gear_optimizer.solver.genetic_pipeline import build_ga_init_heuristic_topk

        if init_heuristic_k > 0:
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
                if init_heuristic_topk is not None:
                    with _PREP_CACHE_LOCK:
                        _lru_put(
                            _INIT_HEURISTIC_TOPK_CACHE,
                            cache_key,
                            np.asarray(init_heuristic_topk, dtype=np.int32),
                            maxsize=_INIT_HEURISTIC_CACHE_MAX,
                        )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:prepare_native_song: {e}")
        init_heuristic_topk = None
    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0
    color_flags = build_color_flags(p_color, s_color, selected_color)
    fg_gear_name_rank, fg_mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=str(p_color or ""),
        secondary_color=str(s_color or ""),
        selected_color=str(selected_color or ""),
    )
    elite_count = max(0, int(ga_runtime_settings.elite_count))
    song = NativeSong(
        config=NativeSongConfig(
            fp=str(fp),
            song_name=str(found_song_name),
            task_key=str(task_key),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            db_key=str(db_key),
            effective_difficulty=str(effective_difficulty),
            cfg_dict=cfg_dict,
            cfg=cfg,
            paths=paths,
            ga_depth=int(ga_depth),
            fg_debug=bool(fg_debug),
        ),
        gpu_inputs=NativeSongGPUInputs(
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
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        ),
        runtime=NativeSongRuntimeState(
            db=NativeSongDBState(
                prev_record=prev_record,
                db_best_score=int(db_best_score),
                attempt_lifetime=int(attempt_lifetime),
                prev_attempts_first=int(prev_attempts_first),
                db_best_fg_score=int(db_best_fg_score),
                db_baseline_valid=bool(db_baseline_valid),
            ),
        ),
    )
    prepare_fg_static_sync(song)
    song.runtime.prep.wall_prep_s = max(0.0, time.perf_counter() - float(wall_t0))
    song.runtime.prep.cpu_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    return song

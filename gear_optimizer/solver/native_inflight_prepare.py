from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.utils import cfg_from_dict, safe_float, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.inflight_utils import (
    _build_calc_song_from_file,
    _compact_prev_record,
    _summarize_db_context,
    _truthy,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.native_inflight_support import _lru_get, _lru_put, _task_ga_seed, _task_key
from gear_optimizer.solver.native_inflight_timing import _thread_cpu_time_s
from gear_optimizer.solver.native_inflight_types import _NativeSong


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
_DB_CONTEXT_CACHE_LOCK = threading.Lock()
_DB_CONTEXT_CACHE: "OrderedDict[tuple[str, bool], tuple[float, Optional[dict], int, int, int]]" = OrderedDict()


def bump_prep_cache_limits_for_ram_mode() -> tuple[int, int, int]:
    # Allow more caching when the user explicitly opts into higher RAM usage.
    global _POOL_CACHE_MAX, _REGISTRY_CACHE_MAX, _INIT_HEURISTIC_CACHE_MAX

    _POOL_CACHE_MAX = max(int(_POOL_CACHE_MAX), 128)
    _REGISTRY_CACHE_MAX = max(int(_REGISTRY_CACHE_MAX), 128)
    _INIT_HEURISTIC_CACHE_MAX = max(int(_INIT_HEURISTIC_CACHE_MAX), 256)
    return int(_POOL_CACHE_MAX), int(_REGISTRY_CACHE_MAX), int(_INIT_HEURISTIC_CACHE_MAX)


def _db_context_cache_max() -> int:
    try:
        raw = os.environ.get("INFLIGHT_DB_CONTEXT_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
    except Exception:
        pass
    return 1024


def _db_context_cache_ttl_s() -> float:
    try:
        raw = os.environ.get("INFLIGHT_DB_CONTEXT_CACHE_TTL_SEC")
        if raw is not None and str(raw).strip() != "":
            return max(0.0, float(raw))
    except Exception:
        pass
    return 1.0


def _db_context_cache_get(db_key: str, use_evo_db: bool) -> tuple[Optional[dict], int, int, int] | None:
    key = (str(db_key or "").strip(), bool(use_evo_db))
    if not key[0] or not key[1]:
        return None
    ttl_s = float(_db_context_cache_ttl_s())
    try:
        with _DB_CONTEXT_CACHE_LOCK:
            entry = _DB_CONTEXT_CACHE.get(key)
            if entry is None:
                return None
            ts, prev_record, db_best_fg_score, attempt_lifetime, prev_attempts_first = entry
            if ttl_s > 0.0 and (time.monotonic() - float(ts)) > ttl_s:
                _DB_CONTEXT_CACHE.pop(key, None)
                return None
            _DB_CONTEXT_CACHE.move_to_end(key)
            rec = _compact_prev_record(prev_record) if isinstance(prev_record, dict) else None
            return rec, int(db_best_fg_score), int(attempt_lifetime), int(prev_attempts_first)
    except Exception:
        return None


def _db_context_cache_put(
    db_key: str,
    use_evo_db: bool,
    prev_record: Optional[dict],
    db_best_fg_score: int,
    attempt_lifetime: int,
    prev_attempts_first: int,
) -> None:
    key = (str(db_key or "").strip(), bool(use_evo_db))
    if not key[0] or not key[1]:
        return
    try:
        record_copy = _compact_prev_record(prev_record) if isinstance(prev_record, dict) else None
        with _DB_CONTEXT_CACHE_LOCK:
            _DB_CONTEXT_CACHE[key] = (
                float(time.monotonic()),
                record_copy,
                int(db_best_fg_score or 0),
                int(attempt_lifetime or 0),
                int(prev_attempts_first or 0),
            )
            _DB_CONTEXT_CACHE.move_to_end(key)
            max_n = int(_db_context_cache_max())
            if max_n <= 0:
                _DB_CONTEXT_CACHE.clear()
                return
            while len(_DB_CONTEXT_CACHE) > max_n:
                _DB_CONTEXT_CACHE.popitem(last=False)
    except Exception:
        return


def _cache_stats_enabled() -> bool:
    return _truthy(os.environ.get("INFLIGHT_CACHE_STATS", "0"))


def _cache_stats_emit_interval_s() -> float:
    try:
        return float(os.environ.get("INFLIGHT_CACHE_STATS_EMIT_SEC", "30") or "30")
    except Exception:
        return 30.0


def _cache_stats_inc(key: str) -> None:
    try:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS[key] = int(_CACHE_STATS.get(key, 0) or 0) + 1
    except Exception:
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
    except Exception:
        return
    try:
        pools_h = int(snap.get("pools_hit", 0) or 0)
        pools_m = int(snap.get("pools_miss", 0) or 0)
        reg_h = int(snap.get("registry_hit", 0) or 0)
        reg_m = int(snap.get("registry_miss", 0) or 0)
        heur_h = int(snap.get("heur_hit", 0) or 0)
        heur_m = int(snap.get("heur_miss", 0) or 0)
        print(
            "[InFlight][CacheStats] "
            f"pools hit={pools_h} miss={pools_m} | "
            f"registry hit={reg_h} miss={reg_m} | "
            f"heur_topk hit={heur_h} miss={heur_m}"
        )
    except Exception:
        pass


def _fixed_registry_cache_key(
    *,
    pool_key: tuple[str, str, tuple[str, ...]],
    fixed_gear: list[dict] | None,
    fixed_minis: list[dict] | None,
) -> tuple:
    def _n(it: dict | None) -> str:
        try:
            return str((it or {}).get("Name", "") or "")
        except Exception:
            return ""

    fg = tuple(_n(it) for it in (fixed_gear or [])[:6])
    fm = tuple(sorted(_n(it) for it in (fixed_minis or [])[:3]))
    return ("fixed", pool_key, fg, fm)


def _prepare_song(task: tuple) -> _NativeSong:
    cpu_t0 = _thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_ELITISM, GA_MUTATION_RATE
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_key = _task_key(task)
    ga_seed = _task_ga_seed(task)

    (
        fp,
        found_song_name,
        effective_difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        _status_queue,
        _parallel_workers,
        fg_debug,
    ) = task[:16]

    cfg = cfg_from_dict(cfg_dict)

    try:
        gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
    except Exception:
        gpu_mode = False
    if not gpu_mode:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Mode=true")

    try:
        gpu_native = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=False)
    except Exception:
        gpu_native = False
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

    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        current_gear_list,
        _current_mini_stats,
        current_mini_list,
        _meta_finder,
        _enable_fever,
        enable_mini,
        enable_gear,
        _force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(cfg, calc_song, bool(auto_buff), paths, gears_by_name, minis_by_name)

    if not (enable_gear or enable_mini):
        raise RuntimeError("GPU-native in-flight currently requires MetaFinder (enable gear or minis).")

    from gear_optimizer.helpers.song_helpers.database_context import build_db_key

    db_key = build_db_key(found_song_name, calc_song)

    # Load DB seed record only; full known-loadout hydration is deferred/prefetched
    # in FG prep to avoid redundant per-song DB reads during prepare.
    allow_db_seed = True
    cached_db_ctx = _db_context_cache_get(db_key, bool(use_evo_db))
    if cached_db_ctx is not None:
        prev_record, db_best_fg_score, attempt_lifetime, prev_attempts_first = cached_db_ctx
    else:
        prev_record, _known_loadouts = load_database_context(
            db_key,
            bool(use_evo_db),
            gears_by_name,
            minis_by_name,
            load_known_loadouts=False,
        )
        db_best_fg_score, attempt_lifetime, prev_attempts_first = _summarize_db_context(
            prev_record,
            None,
            db_key=db_key,
            use_evo_db=bool(use_evo_db),
        )
        _db_context_cache_put(
            db_key,
            bool(use_evo_db),
            prev_record,
            int(db_best_fg_score),
            int(attempt_lifetime),
            int(prev_attempts_first),
        )

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

    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "fg_candidate_limit": int(fg_candidate_limit),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0), 0),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0), 0),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0), 0),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0), 0),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0), 0),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0), 0),
    }
    try:
        cfg_data["ga_convergence_trace_enabled"] = bool(
            cfg.getboolean("IterationEngine", "GAConvergenceTrace", fallback=False)
        )
    except Exception:
        cfg_data["ga_convergence_trace_enabled"] = False
    try:
        cfg_data["ga_convergence_trace_every"] = max(
            1,
            safe_int(cfg.get("IterationEngine", "GAConvergenceTraceEvery", fallback="1"), 1),
        )
    except Exception:
        cfg_data["ga_convergence_trace_every"] = 1
    try:
        cfg_data["ga_convergence_trace_out_dir"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceOutDir", fallback="artifacts/ga_trace")
            or "artifacts/ga_trace"
        )
    except Exception:
        cfg_data["ga_convergence_trace_out_dir"] = "artifacts/ga_trace"
    try:
        cfg_data["ga_convergence_trace_song_filter"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceSongFilter", fallback="") or ""
        )
    except Exception:
        cfg_data["ga_convergence_trace_song_filter"] = ""

    # ForceGreatsFinder runs after GA and needs per-candidate BaseStats for signature grouping.
    # The GPU-native GA decode step keeps full post-gem Stats optional so the critical
    # GA->FG handoff does not spend CPU rebuilding data that the FG grouping path does not use.
    cfg_data["fg_require_stats"] = bool(manual_force_greats or force_greats_finder)

    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)

    tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
    tournament_k = max(1, min(8, int(tournament_k)))

    mutation_rate = safe_float(
        cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
    )
    mutation_rate = max(0.0, min(1.0, float(mutation_rate)))

    immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
    immigrant_rate = max(0.0, min(1.0, float(immigrant_rate)))

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
        init_heuristic_k = int(str(os.environ.get("GPU_GA_INIT_HEURISTIC_K", "64") or "64"))
    except Exception:
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
    except Exception:
        init_heuristic_topk = None
        db_seed_ids = None

    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0

    color_flags = build_color_flags(p_color, s_color, selected_color)

    elite_count_raw = GA_ELITISM
    try:
        if hasattr(cfg, "has_option") and cfg.has_option("IterationEngine", "GPU_GA_EliteCount"):
            elite_count_raw = cfg.get("IterationEngine", "GPU_GA_EliteCount", fallback=GA_ELITISM)
    except Exception:
        elite_count_raw = GA_ELITISM
    elite_count = safe_int(elite_count_raw, GA_ELITISM)
    elite_count = max(0, int(elite_count))

    song = _NativeSong(
        fp=str(fp),
        song_name=str(found_song_name),
        task_key=str(task_key),
        ga_seed=int(ga_seed) if ga_seed is not None else None,
        db_key=str(db_key),
        effective_difficulty=str(effective_difficulty),
        cfg_dict=cfg_dict,
        cfg=cfg,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        use_evo_db=bool(use_evo_db),
        auto_buff=bool(auto_buff),
        ga_depth=int(ga_depth),
        fg_debug=bool(fg_debug),
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
        prev_record=prev_record,
        attempt_lifetime=int(attempt_lifetime),
        prev_attempts_first=int(prev_attempts_first),
        db_best_fg_score=int(db_best_fg_score),
        registry=registry,
        cfg_data=cfg_data,
        color_flags=color_flags,
        gens_per_run=int(gens_per_run),
        num_runs=int(num_runs),
        n_genomes=int(n_genomes),
        init_heuristic_topk=init_heuristic_topk,
        init_heuristic_k=int(init_heuristic_k),
        init_heuristic_copies=int(init_heuristic_copies),
        db_seed_ids=db_seed_ids,
        db_seed_prob=float(getattr(ga_settings, "db_seed_prob", 0.0) or 0.0) if db_seed_ids is not None else 0.0,
        db_seed_copies=1 if db_seed_ids is not None else 0,
        db_seed_mutations=int(getattr(ga_settings, "db_seed_mutations", 1) or 0) if db_seed_ids is not None else 0,
        item_stats=gpu_data["item_stats"],
        slot_start=gpu_data["slot_start"],
        slot_count=gpu_data["slot_count"],
        base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
        elite_count=int(elite_count),
        mutation_rate=float(mutation_rate),
        immigrant_rate=float(immigrant_rate),
        tournament_k=int(tournament_k),
    )
    try:
        setattr(song, "_cpu_prep_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    return song

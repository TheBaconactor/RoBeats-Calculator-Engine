"""LRU prep caches and native song preparation for in-flight orchestration."""
from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Optional

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.singleflight import SingleFlight
from gear_optimizer.domain.jobs import seed_plan_from_song_job, task_tuple_to_view
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.native_inflight_config import (
    NativeSong,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.native_inflight_pipeline import prepare_fg_static_sync
from gear_optimizer.solver.song_preparation import build_prepared_song_core

logger = logging.getLogger(__name__)

_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_INIT_HEURISTIC_CACHE_MAX = 64
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...], tuple], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...], tuple], tuple[ItemRegistry, dict]]" = OrderedDict()
_INIT_HEURISTIC_TOPK_CACHE: "OrderedDict[tuple[tuple[str, str, tuple[str, ...], tuple], int], np.ndarray]" = OrderedDict()
_PREP_CACHE_SINGLEFLIGHT: SingleFlight[tuple[str, tuple], object] = SingleFlight()


def _lru_get(cache: OrderedDict, key: tuple):
    value = cache.get(key)
    if value is not None:
        cache.move_to_end(key)
    return value


def _lru_put(cache: OrderedDict, key: tuple, value, *, maxsize: int) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > int(maxsize):
        cache.popitem(last=False)


def _prep_cache_get_or_build(
    cache: OrderedDict,
    key: tuple,
    builder,
    *,
    cache_name: str,
    maxsize: int,
):
    with _PREP_CACHE_LOCK:
        cached = _lru_get(cache, key)
    if cached is not None:
        return cached

    def _build_and_cache():
        # The prior owner may finish between the initial lookup and this caller
        # becoming owner. Recheck so that race cannot trigger a duplicate build.
        with _PREP_CACHE_LOCK:
            existing = _lru_get(cache, key)
        if existing is not None:
            return existing
        value = builder()
        if value is None:
            raise RuntimeError(f"{cache_name} cache builder returned None")
        with _PREP_CACHE_LOCK:
            _lru_put(cache, key, value, maxsize=maxsize)
        return value

    return _PREP_CACHE_SINGLEFLIGHT.run((str(cache_name), key), _build_and_cache)


def _catalog_digest(gears, song_minis) -> str:
    """The items a song's pools are built from: a request's own catalog (a custom pool) must not reuse the cached
    pools of another catalog with the same colors."""
    digest = hashlib.blake2b(digest_size=16)
    for gear in sorted(gears.values(), key=lambda g: g.name):
        digest.update(repr((gear.name, gear.slot, sorted(gear.stats.items()))).encode())
    for mini in sorted(song_minis, key=lambda m: m.name):
        digest.update(repr((mini.name, sorted(mini.stats.items()), mini.targets_song)).encode())
    return digest.hexdigest()


def prepare_native_song(task: tuple) -> NativeSong:
    from gear_optimizer.solver.genetic_pipeline import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_view = task_tuple_to_view(task)
    job = task_view.job
    seed_plan = seed_plan_from_song_job(job)
    task_key = seed_plan.queue_label
    ga_seed = seed_plan.ga_seed
    run_context = task_view.context
    fp = job.file_path
    found_song_name = job.song_name
    multi_start = run_context.multi_start
    curves = run_context.curves
    gears = run_context.gears
    ga_depth = run_context.ga_depth
    prepared_core = build_prepared_song_core(
        fp=fp,
        found_song_name=found_song_name,
        minis=run_context.minis,
    )
    timed_song = prepared_core.song
    song_minis = prepared_core.minis
    meta_primary_color = timed_song.chart.primary
    meta_secondary_color = timed_song.chart.secondary
    fixed_stats = prepared_core.fixed_stats
    db_context = prepared_core.db_context
    db_key = db_context.db_key
    p_color = timed_song.chart.primary
    s_color = timed_song.chart.secondary
    selected_color = p_color
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    # The minis a song targets are the only per-song difference in its pools (Mini Ascension).
    targeting_minis = tuple(sorted(mini.name for mini in song_minis if mini.targets_song))
    pool_key = (str(p_color), str(s_color), tuple(slots), targeting_minis, _catalog_digest(gears, song_minis))
    def _build_pools():
        return initialize_pools(gears, song_minis, p_color, slots, s_color=s_color)

    gear_pool, mini_pool = _prep_cache_get_or_build(
        _POOL_CACHE,
        pool_key,
        _build_pools,
        cache_name="pools",
        maxsize=_POOL_CACHE_MAX,
    )

    def _build_registry_gpu():
        registry = ItemRegistry(gear_pool, mini_pool, slots)
        gpu_data = registry.to_gpu_arrays()
        return registry, gpu_data

    registry, gpu_data = _prep_cache_get_or_build(
        _REGISTRY_GPU_CACHE,
        pool_key,
        _build_registry_gpu,
        cache_name="registry",
        maxsize=_REGISTRY_CACHE_MAX,
    )
    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "fg_require_stats": True,
    }
    base_fixed_stats_arr = build_stats_array(fixed_stats)
    num_runs = max(1, int(multi_start))
    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 64  # heuristic-seeded initial genomes (was GPU_GA_INIT_HEURISTIC_K)
    init_heuristic_copies = 25
    from gear_optimizer.solver.genetic_pipeline import (
        build_ga_init_heuristic_topk,
    )

    if init_heuristic_k > 0:
        cache_key = (pool_key, int(init_heuristic_k))

        def _build_init_heuristic_topk():
            built = build_ga_init_heuristic_topk(
                    item_stats=gpu_data["item_stats"],
                    slot_start=gpu_data["slot_start"],
                    slot_count=gpu_data["slot_count"],
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    heuristic_k=int(init_heuristic_k),
                    n_slots=9,
                )
            if built is None:
                raise RuntimeError("GA initial heuristic builder returned None for an enabled heuristic")
            return np.asarray(built, dtype=np.int32)

        init_heuristic_topk = _prep_cache_get_or_build(
            _INIT_HEURISTIC_TOPK_CACHE,
            cache_key,
            _build_init_heuristic_topk,
            cache_name="heur",
            maxsize=_INIT_HEURISTIC_CACHE_MAX,
        )
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
    song = NativeSong(
        config=NativeSongConfig(
            fp=str(fp),
            song_name=str(found_song_name),
            task_key=str(task_key),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            db_key=str(db_key),
        ),
        gpu_inputs=NativeSongGPUInputs(
            curves=curves,
            minis_by_name={mini.name: mini for mini in song_minis},
            timed_song=timed_song,
            meta_primary_color=meta_primary_color,
            meta_secondary_color=meta_secondary_color,
            fixed_stats=fixed_stats,
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
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(init_heuristic_k),
            init_heuristic_copies=int(init_heuristic_copies),
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        ),
        runtime=NativeSongRuntimeState(
            db=NativeSongDBState(
                db_best_score=db_context.best_score,
                db_best_fg_score=db_context.best_fg_score,
                db_baseline_valid=db_context.valid,
            ),
        ),
    )
    prepare_fg_static_sync(song)
    # Hydrate the in-memory timeline-frontier payload cache from this prep worker so
    # the owner thread's upload at the GA turn hits the "memory" branch instead of
    # re-reading the .npz from disk at the song boundary (host-side: no Taichi; a payload
    # the startup cache lacks is built and persisted here, off the owner).
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(song.gpu_inputs.timed_song, song.gpu_inputs.curves)
    return song

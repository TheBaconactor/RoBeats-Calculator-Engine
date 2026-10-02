"""A queue task prepared into a NativeSong: its item pools, registry and GPU inputs (cached per song colors and
catalog), and its GA-invariant FG preparation."""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.singleflight import SingleFlight
from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.fg import prepare_fg_static
from gear_optimizer.pipeline.song import (
    NativeSong,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.song_preparation import build_prepared_song_core

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


# The GA's heuristic-seeded initial genomes: copies of the top-k items per slot.
_INIT_HEURISTIC_COPIES = 25
_SLOTS = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


def _ga_registry(gears, song_minis, primary: str, secondary: str):
    """The song's item registry, its GPU arrays and the GA's initial-heuristic top-k items, cached per pool key."""
    from gear_optimizer.helpers.ga_helpers import initialize_pools
    from gear_optimizer.solver.genetic_pipeline import build_ga_init_heuristic_topk
    from gear_optimizer.solver.taichi_gem.fields import GA_INIT_HEURISTIC_K

    # The minis a song targets are the only per-song difference in its pools (Mini Ascension).
    targeting_minis = tuple(sorted(mini.name for mini in song_minis if mini.targets_song))
    pool_key = (primary, secondary, _SLOTS, targeting_minis, _catalog_digest(gears, song_minis))
    gear_pool, mini_pool = _prep_cache_get_or_build(
        _POOL_CACHE,
        pool_key,
        lambda: initialize_pools(gears, song_minis, primary, list(_SLOTS), s_color=secondary),
        cache_name="pools",
        maxsize=_POOL_CACHE_MAX,
    )

    def build_registry():
        registry = ItemRegistry(gear_pool, mini_pool, list(_SLOTS))
        return registry, registry.to_gpu_arrays()

    registry, gpu_data = _prep_cache_get_or_build(
        _REGISTRY_GPU_CACHE, pool_key, build_registry, cache_name="registry", maxsize=_REGISTRY_CACHE_MAX
    )

    def build_heuristic_topk():
        built = build_ga_init_heuristic_topk(
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            primary_color=primary,
            secondary_color=secondary,
            heuristic_k=GA_INIT_HEURISTIC_K,
            n_slots=9,
        )
        return np.asarray(built, dtype=np.int32)

    topk = _prep_cache_get_or_build(
        _INIT_HEURISTIC_TOPK_CACHE,
        (pool_key, GA_INIT_HEURISTIC_K),
        build_heuristic_topk,
        cache_name="heur",
        maxsize=_INIT_HEURISTIC_CACHE_MAX,
    )
    return registry, gpu_data, topk


def prepare_native_song(task: SongTask) -> NativeSong:
    """The task's song ready for its GA: the GA inputs (the meta GA selects the song's primary element), the FG
    static preparation, and the timeline frontier payload built or loaded here, off the GPU owner thread."""
    from gear_optimizer.solver.genetic_pipeline import GA_POPULATION_SIZE
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.taichi_gem.fields import GA_INIT_HEURISTIC_K

    context = task.context
    core = build_prepared_song_core(fp=task.file_path, found_song_name=task.song_name, minis=context.minis)
    timed_song = core.song
    primary, secondary = timed_song.chart.primary, timed_song.chart.secondary
    registry, gpu_data, init_heuristic_topk = _ga_registry(context.gears, core.minis, primary, secondary)
    fg_gear_name_rank, fg_mini_sig_id = effective_tables_for_context(
        registry, primary_color=primary, secondary_color=secondary, selected_color=primary
    )
    num_runs = max(1, context.multi_start)
    song = NativeSong(
        config=NativeSongConfig(
            song_name=task.song_name,
            task_key=task.label,
            ga_seed=task.ga_seed,
            db_key=core.db_context.db_key,
        ),
        gpu_inputs=NativeSongGPUInputs(
            curves=context.curves,
            minis_by_name={mini.name: mini for mini in core.minis},
            timed_song=timed_song,
            meta_primary_color=primary,
            meta_secondary_color=secondary,
            fixed_stats=core.fixed_stats,
            registry=registry,
            color_flags=build_color_flags(primary, secondary, primary),
            gens_per_run=max(1, (max(1, context.ga_depth) + num_runs - 1) // num_runs),
            num_runs=num_runs,
            n_genomes=GA_POPULATION_SIZE,
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            base_fixed_stats_arr=np.asarray(build_stats_array(core.fixed_stats), dtype=np.int32),
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=GA_INIT_HEURISTIC_K,
            init_heuristic_copies=_INIT_HEURISTIC_COPIES,
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        ),
        runtime=NativeSongRuntimeState(
            db=NativeSongDBState(
                db_best_score=core.db_context.best_score,
                db_best_fg_score=core.db_context.best_fg_score,
                db_baseline_valid=core.db_context.valid,
            ),
        ),
    )
    prepare_fg_static(song)
    # Hydrate the in-memory timeline-frontier payload cache here (host side, no Taichi) so the GPU owner's upload at
    # the GA turn hits memory; a payload the startup cache lacks is built and persisted here, off the owner.
    build_or_load_timeline_frontier_payload(song.gpu_inputs.timed_song, song.gpu_inputs.curves)
    return song

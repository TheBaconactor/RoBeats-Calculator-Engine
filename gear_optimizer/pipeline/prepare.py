"""A queue task prepared into a NativeSong: its item pools, registry, timeline frontier payload and GPU inputs (cached
per song colors and catalog). The FG scoring bundle loads during the GA (pipeline.solve.run_ga)."""

from __future__ import annotations

import hashlib
from collections import OrderedDict

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.frontier.cache_scope import frontier_cache_is_ephemeral
from gear_optimizer.pipeline.pools import gears_digest_bytes
from gear_optimizer.pipeline.song import (
    NativeSong,
    NativeSongConfig,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.ftff_combos import FtffShortlist, ftff_shortlist, reachable_ftff_keys
from gear_optimizer.solver.ga_selection import effective_tables
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.song_preparation import build_prepared_song_core

# Per pool key (_ga_registry): the item registry, its GPU arrays, the GA's initial-heuristic top-k, the FG
# effective-loadout tables and the reachable pre-gem (FT, FF) keys. Bounded: a long-lived worker adds one key per custom
# pool; the least recently used goes first.
_PREP_CACHE_MAX = 32
_PREP_CACHE: "OrderedDict[tuple, tuple[ItemRegistry, dict, np.ndarray, tuple[np.ndarray, np.ndarray], np.ndarray]]" = OrderedDict()
_SHORTLIST_CACHE: "OrderedDict[tuple, FtffShortlist]" = OrderedDict()


def _catalog_digest(gears_digest: bytes, song_minis) -> str:
    """The items a song's pools are built from: a request's own catalog (a custom pool) or in-place mapping changes
    must never reuse the cached pools of another catalog."""
    parts = []
    for mini in sorted(song_minis, key=lambda m: m.name):
        g = mini.stats.get
        stats_tuple = (
            g("Perfect Points", 0), g("Combo Multiplier", 0), g("Fever Multiplier", 0),
            g("Fever Fill Rate", 0), g("Fever Time", 0),
            g("Chill", 0), g("Flow", 0), g("Rush", 0), g("Beat", 0), g("Vibe", 0),
        )
        parts.append(f"{mini.name}\0{int(bool(mini.targets_song))}\0{stats_tuple}\n")
    digest = hashlib.blake2b(gears_digest, digest_size=16)
    digest.update("".join(parts).encode())
    return digest.hexdigest()


# The GA's heuristic-seeded initial genomes: copies of the top-k items per slot.
_INIT_HEURISTIC_COPIES = 25
_SLOTS = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


def _ga_registry(gears, song_minis, primary: str, secondary: str, base_fixed_stats: np.ndarray):
    """The song's item registry, its GPU arrays, the GA's initial-heuristic top-k items, the FG effective-loadout tables
    (gear name rank, mini signature id; the GA selects the primary element), the reachable pre-gem (FT, FF) keys, and the
    content-derived pool key."""
    from gear_optimizer.pipeline.pools import initialize_pools
    from gear_optimizer.solver.genetic_pipeline import GA_INIT_HEURISTIC_K, build_ga_init_heuristic_topk

    # The minis a song targets are the only per-song difference in its pools (Mini Ascension).
    targeting_minis = tuple(sorted(mini.name for mini in song_minis if mini.targets_song))
    fixed_key = tuple(int(x) for x in base_fixed_stats.ravel())
    gears_digest = gears_digest_bytes(gears)
    pool_key = (primary, secondary, _SLOTS, targeting_minis, fixed_key, _catalog_digest(gears_digest, song_minis))
    if pool_key in _PREP_CACHE:
        _PREP_CACHE.move_to_end(pool_key)
        return *_PREP_CACHE[pool_key], pool_key
    gear_pool, mini_pool = initialize_pools(
        gears, song_minis, primary, list(_SLOTS), s_color=secondary, gears_digest=gears_digest
    )
    registry = ItemRegistry(gear_pool, mini_pool, list(_SLOTS))
    gpu_data = registry.to_gpu_arrays()
    topk = build_ga_init_heuristic_topk(
        item_stats=gpu_data["item_stats"],
        slot_start=gpu_data["slot_start"],
        slot_count=gpu_data["slot_count"],
        primary_color=primary,
        secondary_color=secondary,
        heuristic_k=GA_INIT_HEURISTIC_K,
    )
    prepared = _PREP_CACHE[pool_key] = (
        registry, gpu_data, topk, effective_tables(registry, primary, secondary),
        reachable_ftff_keys(gpu_data["item_stats"], gpu_data["slot_start"], gpu_data["slot_count"], base_fixed_stats),
    )
    if len(_PREP_CACHE) > _PREP_CACHE_MAX:
        _PREP_CACHE.popitem(last=False)
    return *prepared, pool_key


def prepare_native_song(task: SongTask) -> NativeSong:
    """The task's song ready for its GA: the GA inputs (the meta GA selects the song's primary element) and the timeline
    frontier payload built or loaded here, off the GPU owner thread."""
    from gear_optimizer.solver.genetic_pipeline import GA_POPULATION_SIZE
    from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload

    context = task.context
    core = build_prepared_song_core(
        fp=task.file_path, found_song_name=task.song_name, mode=task.mode, minis=context.minis
    )
    timed_song = core.song
    primary, secondary = timed_song.chart.primary, timed_song.chart.secondary
    base_fixed_stats = np.asarray(build_stats_array(core.fixed_stats), dtype=np.int32)
    registry, gpu_data, init_heuristic_topk, (fg_gear_name_rank, fg_mini_sig_id), reach, pool_key = _ga_registry(
        context.gears, core.minis, primary, secondary, base_fixed_stats
    )
    num_runs = max(1, context.multi_start)
    color_flags = build_color_flags(primary, secondary, primary)
    # The timeline frontier payload is hydrated here (host side, no Taichi), so the GPU owner's upload at the GA turn hits
    # memory; a payload the startup cache lacks is built and persisted here, off the owner.
    frontier_load = build_or_load_timeline_frontier_payload(timed_song, context.curves)
    payload = frontier_load.payload
    ephemeral = frontier_cache_is_ephemeral()
    shortlist_key = (frontier_load.cache_key, tuple(sorted(color_flags.items())), pool_key)
    shortlist = None if ephemeral else _SHORTLIST_CACHE.get(shortlist_key)
    if shortlist is not None:
        _SHORTLIST_CACHE.move_to_end(shortlist_key)
    else:
        shortlist = ftff_shortlist(payload, reach=reach, color_flags=color_flags)
        if not ephemeral:
            _SHORTLIST_CACHE[shortlist_key] = shortlist
            if len(_SHORTLIST_CACHE) > _PREP_CACHE_MAX:
                _SHORTLIST_CACHE.popitem(last=False)
    song = NativeSong(
        config=NativeSongConfig(
            song_name=task.song_name,
            task_key=task.label,
            ga_seed=task.ga_seed,
            db_key=task.song_name.strip(),
        ),
        gpu_inputs=NativeSongGPUInputs(
            timed_song=timed_song,
            curves=context.curves,
            color_flags=color_flags,
            gens_per_run=max(1, (max(1, context.ga_depth) + num_runs - 1) // num_runs),
            num_runs=num_runs,
            n_genomes=GA_POPULATION_SIZE,
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            base_fixed_stats_arr=base_fixed_stats,
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_copies=_INIT_HEURISTIC_COPIES,
            ftff_shortlist=shortlist,
            minis_by_name={mini.name: mini for mini in core.minis},
            meta_primary_color=primary,
            meta_secondary_color=secondary,
            registry=registry,
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        ),
        runtime=NativeSongRuntimeState(),
    )
    return song

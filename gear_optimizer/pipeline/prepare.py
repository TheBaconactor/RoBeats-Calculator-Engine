"""A queue task prepared into a NativeSong: its item pools, registry and GPU inputs (cached per song colors and
catalog), and its GA-invariant FG preparation."""

from __future__ import annotations

import hashlib
from collections import OrderedDict

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.fg import prepare_fg_static
from gear_optimizer.pipeline.song import (
    NativeSong,
    NativeSongConfig,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.ftff_combos import FtffShortlist, ftff_shortlist, reachable_ftff_keys
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.rules import ELEMENT_GEM_GAIN, GEM_BUDGET, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.song_preparation import build_prepared_song_core

# Per pool key (_ga_registry): the item registry, its GPU arrays, the GA's initial-heuristic top-k and the FG
# effective-loadout tables. Bounded: a long-lived worker adds one key per custom pool; the least recently used goes
# first.
_PREP_CACHE_MAX = 32
_PREP_CACHE: "OrderedDict[tuple, tuple[ItemRegistry, dict, np.ndarray, tuple[np.ndarray, np.ndarray]]]" = OrderedDict()


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
    """The song's item registry, its GPU arrays, the GA's initial-heuristic top-k items and the FG effective-loadout
    tables (gear name rank, mini signature id; the GA selects the primary element), cached per pool key."""
    from gear_optimizer.helpers.ga_helpers import initialize_pools
    from gear_optimizer.solver.genetic_pipeline import build_ga_init_heuristic_topk
    from gear_optimizer.solver.taichi_gem.fields import GA_INIT_HEURISTIC_K

    # The minis a song targets are the only per-song difference in its pools (Mini Ascension).
    targeting_minis = tuple(sorted(mini.name for mini in song_minis if mini.targets_song))
    pool_key = (primary, secondary, _SLOTS, targeting_minis, _catalog_digest(gears, song_minis))
    if pool_key in _PREP_CACHE:
        _PREP_CACHE.move_to_end(pool_key)
        return _PREP_CACHE[pool_key]
    gear_pool, mini_pool = initialize_pools(gears, song_minis, primary, list(_SLOTS), s_color=secondary)
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
    effective = effective_tables_for_context(
        registry, primary_color=primary, secondary_color=secondary, selected_color=primary
    )
    prepared = _PREP_CACHE[pool_key] = (registry, gpu_data, topk, effective)
    if len(_PREP_CACHE) > _PREP_CACHE_MAX:
        _PREP_CACHE.popitem(last=False)
    return prepared


def prepare_native_song(task: SongTask) -> NativeSong:
    """The task's song ready for its GA: the GA inputs (the meta GA selects the song's primary element), the FG
    static preparation, and the timeline frontier payload built or loaded here, off the GPU owner thread."""
    from gear_optimizer.solver.genetic_pipeline import GA_POPULATION_SIZE
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.taichi_gem.fields import GA_INIT_HEURISTIC_K

    context = task.context
    core = build_prepared_song_core(
        fp=task.file_path, found_song_name=task.song_name, mode=task.mode, minis=context.minis
    )
    timed_song = core.song
    primary, secondary = timed_song.chart.primary, timed_song.chart.secondary
    registry, gpu_data, init_heuristic_topk, (fg_gear_name_rank, fg_mini_sig_id) = _ga_registry(
        context.gears, core.minis, primary, secondary
    )
    num_runs = max(1, context.multi_start)
    song = NativeSong(
        config=NativeSongConfig(
            song_name=task.song_name,
            task_key=task.label,
            ga_seed=task.ga_seed,
            db_key=task.song_name.strip(),
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
        runtime=NativeSongRuntimeState(),
    )
    prepare_fg_static(song)
    # Hydrate the in-memory timeline-frontier payload cache here (host side, no Taichi) so the GPU owner's upload at
    # the GA turn hits memory; a payload the startup cache lacks is built and persisted here, off the owner.
    gpu_inputs = song.gpu_inputs
    payload = build_or_load_timeline_frontier_payload(gpu_inputs.timed_song, gpu_inputs.curves).payload
    reach = reachable_ftff_keys(
        gpu_inputs.item_stats, gpu_inputs.slot_start, gpu_inputs.slot_count, gpu_inputs.base_fixed_stats_arr
    )
    gpu_inputs.ftff_shortlist = ga_ftff_shortlist(payload, reach=reach, color_flags=gpu_inputs.color_flags)
    return song


def ga_ftff_shortlist(payload, *, reach: np.ndarray, color_flags: dict) -> FtffShortlist:
    """The FT/FF combo shortlist of the GA's gem search (ftff_combos.ftff_shortlist, GEM_BUDGET gems) for a song's
    timing frontier payload, the pre-gem keys its genomes can reach (ftff_combos.reachable_ftff_keys) and its color
    flags (build_color_flags)."""
    gains = (
        STAT_GEM_ELEMENT_GAIN * (2 * color_flags["is_p_ft"] + color_flags["is_s_ft"]),
        STAT_GEM_ELEMENT_GAIN * (2 * color_flags["is_p_ff"] + color_flags["is_s_ff"]),
        ELEMENT_GEM_GAIN * (2 * color_flags["is_p_ov"] + color_flags["is_s_ov"]),
    )
    return ftff_shortlist(payload, reach=reach, total_budget=GEM_BUDGET, gem_scale_fever=STAT_GEM_GAIN_FEVER,
                          element_gains=gains)

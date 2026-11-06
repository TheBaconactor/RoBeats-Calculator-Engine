"""A small GA setup for the GPU tests: a registry of real shape, a chart and the GA's inputs for them."""

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload
from gear_optimizer.gamedata import empty_stats, stat_curves
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.ftff_combos import ftff_shortlist, reachable_ftff_keys
from gear_optimizer.solver.genetic_pipeline import GA_INIT_HEURISTIC_K, GaInputs, build_ga_init_heuristic_topk
from gear_optimizer.solver.item_registry import ItemRegistry
from tests.items_support import make_gear, make_song_mini
from tests.songs_support import make_song

PRIMARY, SECONDARY = "Beat", "Flow"


def registry() -> ItemRegistry:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gears = {
        slot: [
            make_gear(f"{slot}{i}", **{
                "Perfect Points": 7 + s + i, "Combo Multiplier": 3 + i, "Fever Multiplier": 2 + s, "Fever Time": 4 + i,
                "Fever Fill Rate": 5 + s, "Beat": 6 + i, "Vibe": 2 + s, "Rush": 3 + i, "Flow": 4 + s, "Chill": 1 + i,
            })
            for i in range(4)
        ]
        for s, slot in enumerate(slots)
    }
    minis = [
        make_song_mini(f"M{i}", **{
            "Perfect Points": 2 + (i % 5), "Combo Multiplier": 1 + (i % 3), "Fever Multiplier": 1 + (i % 4),
            "Fever Time": 1 + (i % 2), "Fever Fill Rate": 2 + (i % 3), "Beat": 1 + (i % 4), "Vibe": 2 + (i % 2),
            "Rush": 1 + (i % 5), "Flow": 3 + (i % 2), "Chill": 1 + (i % 3),
        })
        for i in range(12)
    ]
    return ItemRegistry(gears, minis, slots)


def song(*, n_notes: int = 400, name: str = "GPU test song"):
    return make_song(
        np.linspace(0, 90, n_notes),
        name=name,
        primary=PRIMARY,
        secondary=SECONDARY,
        long_notes=10,
        lanes=np.arange(n_notes, dtype=np.int32) % np.int32(4),
    )


def ga_inputs(timed=None, *, num_runs: int = 2, n_genomes: int = 64, generations: int = 3) -> GaInputs:
    timed = timed if timed is not None else song()
    curves = stat_curves()
    arrays = registry().to_gpu_arrays()
    item_stats = np.asarray(arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(arrays["slot_count"], dtype=np.int32)
    base_fixed = np.asarray(build_stats_array(empty_stats()), dtype=np.int32)
    flags = build_color_flags(PRIMARY, SECONDARY, PRIMARY)
    payload = build_or_load_timeline_frontier_payload(timed, curves).payload
    return GaInputs(
        timed_song=timed,
        curves=curves,
        color_flags=flags,
        gens_per_run=generations,
        num_runs=num_runs,
        n_genomes=n_genomes,
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed,
        init_heuristic_topk=build_ga_init_heuristic_topk(
            item_stats=item_stats, slot_start=slot_start, slot_count=slot_count, primary_color=PRIMARY,
            secondary_color=SECONDARY, heuristic_k=GA_INIT_HEURISTIC_K,
        ),
        init_heuristic_copies=8,
        ftff_shortlist=ftff_shortlist(
            payload, reach=reachable_ftff_keys(item_stats, slot_start, slot_count, base_fixed), color_flags=flags
        ),
    )

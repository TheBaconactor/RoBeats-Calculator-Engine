"""
GPU-native GA payload helpers for gear and mini co-evolution.

This module contains the payload generation, decoding, and selection helpers used by
the native in-flight optimizer. The legacy direct CPU GA entrypoint has been removed.
"""

import importlib
import logging

import numpy as np


logger = logging.getLogger(__name__)


from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.timing_envelope import TimedSong
from ..domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from .gpu_tuning_policy import choose_ga_batch_runs


GA_POPULATION_SIZE = 705
# GA selection/variation policy (fixed; the config.ini overrides were never set in production).
GA_MUTATION_RATE = 0.35
GA_ELITISM = 1
# The next-generation kernel's elitism layout is parameterized by islands; one island (migration was removed).
GPU_GA_NUM_ISLANDS = 1
GA_TOURNAMENT_K = 3
GA_IMMIGRANT_RATE = 0.0
GA_NOVELTY_REPAIR_ATTEMPTS = 2


def _compute_global_ftff_combo_caps(
    *,
    item_stats: "np.ndarray | None",
    slot_start: "np.ndarray | None",
    slot_count: "np.ndarray | None",
    base_fixed_stats_arr: "np.ndarray | None",
    total_budget: int,
    gem_scale_fever: int,
    n_slots: int = 9,
) -> tuple[int, int]:
    """
    Compute conservative global FT/FF gem caps for combo-table pruning.

    The FT/FF kernels enforce per-genome max gems from stat ceilings:
      max_ft_gems = floor((MAX_STAT - base_ft_stat) / gem_scale_fever)
      max_ff_gems = floor((MAX_STAT - base_ff_stat) / gem_scale_fever)

    For a fixed song + item pools we can derive a safe global cap by using the
    minimum possible base FT/FF across all genomes (base-fixed + per-slot minima).
    Any combo above these caps is impossible for every genome and can be skipped.
    """
    budget_i = max(0, int(total_budget))
    gem_scale_i = int(gem_scale_fever)
    if budget_i <= 0 or gem_scale_i <= 0:
        return budget_i, budget_i

    stats = np.asarray(item_stats, dtype=np.int32)
    starts = np.asarray(slot_start, dtype=np.int32).reshape(-1)
    counts = np.asarray(slot_count, dtype=np.int32).reshape(-1)
    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)

    if stats.ndim != 2 or int(stats.shape[1]) < 5 or int(base.size) < 5:
        return budget_i, budget_i

    slot_lim = min(int(n_slots), int(starts.shape[0]), int(counts.shape[0]))
    if slot_lim <= 0:
        return budget_i, budget_i

    min_ft_stat = int(base[3])
    min_ff_stat = int(base[4])
    n_items = int(stats.shape[0])

    for s in range(slot_lim):
        count_i = int(counts[s] or 0)
        if count_i <= 0:
            continue
        start_i = int(starts[s] or 0)
        if start_i < 0:
            start_i = 0
        end_i = min(int(n_items), int(start_i + count_i))
        if end_i <= start_i:
            continue
        slot_stats = stats[start_i:end_i]
        min_ft_stat += int(np.min(slot_stats[:, 3]))
        min_ff_stat += int(np.min(slot_stats[:, 4]))

    max_stat_index = 160
    cap_ft = (int(max_stat_index) - int(min_ft_stat)) // int(gem_scale_i)
    cap_ff = (int(max_stat_index) - int(min_ff_stat)) // int(gem_scale_i)
    cap_ft = max(0, min(int(budget_i), int(cap_ft)))
    cap_ff = max(0, min(int(budget_i), int(cap_ff)))
    return int(cap_ft), int(cap_ff)


def _abort_requested_now(abort_requested) -> bool:
    if abort_requested is None or not callable(abort_requested):
        return False
    return bool(abort_requested())


def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
    msg = str(exc)
    return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)


def _raise_if_abort_requested(abort_requested, where: str) -> None:
    if _abort_requested_now(abort_requested):
        raise RuntimeError(f"GpuExecutor aborted: {where}")


# The Vulkan retry count is a module constant (tests setattr it directly).
_GPU_NATIVE_GA_VULKAN_RETRIES = 1
_GPU_NATIVE_GA_BATCH_RUNS = 0  # auto: choose_ga_batch_runs decides (was GPU_NATIVE_GA_BATCH_RUNS)


def build_ga_init_heuristic_topk(
    *,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    primary_color: str,
    secondary_color: str,
    heuristic_k: int,
    n_slots: int = 9,
) -> "np.ndarray | None":
    heuristic_k = int(heuristic_k)
    if heuristic_k <= 0:
        return None

    color_to_idx = {
        "Perfect Points": 0,
        "Combo Multiplier": 1,
        "Fever Multiplier": 2,
        "Beat": 5,
        "Vibe": 6,
        "Rush": 7,
        "Flow": 8,
        "Chill": 9,
    }
    p_idx = color_to_idx.get(str(primary_color or ""), -1)
    s_idx = color_to_idx.get(str(secondary_color or ""), -1)
    pp_idx = 0

    n_slots = int(n_slots)
    if n_slots <= 0:
        return None

    topk = np.zeros((n_slots, max(1, heuristic_k)), dtype=np.int32)
    for slot_i in range(n_slots):
        start_id = int(slot_start[slot_i])
        count = int(slot_count[slot_i])
        if count <= 0:
            continue
        ids = np.arange(start_id, start_id + count, dtype=np.int32)
        sc = np.zeros((count,), dtype=np.int64)
        if p_idx >= 0:
            sc += item_stats[ids, p_idx].astype(np.int64) * 2
        if s_idx >= 0:
            sc += item_stats[ids, s_idx].astype(np.int64)
        sc += item_stats[ids, pp_idx].astype(np.int64)
        k_eff = min(int(heuristic_k), int(count))
        if k_eff <= 0:
            continue
        order = np.lexsort((ids.astype(np.int64), -sc))
        sel = ids[order[:k_eff]]
        topk[slot_i, :k_eff] = sel
        if k_eff < heuristic_k:
            topk[slot_i, k_eff:heuristic_k] = sel[-1]
    return topk


def upload_ga_song_slot_timeline_state(
    *,
    song: TimedSong,
    curves: StatCurves,
    song_slot: int,
) -> None:
    """Precompute timeline state for one GPU song slot."""
    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")

    song_slot = int(song_slot)
    if song_slot < 0:
        song_slot = 0

    gpu_api.precompute_timeline_gpu(song, curves, song_slot=song_slot)


def upload_ga_global_static_state(
    *,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    fg_gear_name_rank: "np.ndarray",
    fg_mini_sig_id: "np.ndarray",
) -> None:
    """Upload GA global item/base-stat buffers immediately before a GA run."""
    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")

    gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
    gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
    gpu_api.ga_upload_fg_effective_tables(fg_gear_name_rank, fg_mini_sig_id)


def one_swap_neighborhood(
    incumbent: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    n_slots: int,
) -> "np.ndarray":
    """All single-slot substitutions of `incumbent` (mini uniqueness preserved).

    Gear slots (0-5) swap to every other item in the slot pool; mini slots (6-8)
    additionally exclude the incumbent's other two minis. Returns (K, n_slots) i32.
    """
    inc = np.asarray(incumbent, dtype=np.int64)
    rows = []
    for s in range(int(n_slots)):
        cnt = int(slot_count[s])
        st = int(slot_start[s])
        if cnt <= 1:
            continue
        pool = np.arange(st, st + cnt, dtype=np.int64)
        pool = pool[pool != inc[s]]
        if s >= 6:
            others = [int(inc[j]) for j in range(6, int(n_slots)) if j != s]
            if others:
                pool = pool[~np.isin(pool, others)]
        if pool.size == 0:
            continue
        block = np.tile(inc, (int(pool.size), 1))
        block[:, s] = pool
        rows.append(block)
    if not rows:
        return np.zeros((0, int(n_slots)), dtype=np.int32)
    return np.ascontiguousarray(np.concatenate(rows, axis=0).astype(np.int32))


def _polish_runs_best_one_swap(
    *,
    gpu_api,
    gpu_fields,
    n_runs: int,
    n_slots: int,
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    scoring: dict,
    caps: dict,
    abort_requested=None,
) -> int:
    """Exact 1-swap local search on each run's tracked best (memetic finisher).

    Measured motivation (tools/dev/measure_ga_miss.py, 8 songs x 96 seeds): 94.7%
    of all GA misses sit exactly one swap from the true optimum, so making every
    run's answer 1-swap-locally-optimal removes nearly all of them for ~one extra
    generation-equivalent of GPU work per pass.

    Each pass evaluates the full single-swap neighborhood of every run's incumbent
    through the canonical prepare/evaluate kernels; ga_refresh_scores_and_update_runs_best
    adopts strictly better genomes (ties keep the incumbent). Iterates until no run
    improves — termination is guaranteed because run bests are strictly increasing
    integers bounded by the song optimum. Consumes `population_indices`/eval scratch,
    so it must run AFTER the FG candidate pack for the segment; the caller refreshes
    the packed row 0 afterwards. Returns the number of passes executed.
    """
    chunk_cap = int(min(gpu_fields.MAX_GA_RUN_GENOMES, gpu_fields.MAX_GENOMES))
    if chunk_cap <= 0:
        raise RuntimeError("Invalid GA buffer configuration for 1-swap polish (chunk_cap <= 0)")
    passes = 0
    prev = gpu_api.ga_download_runs_best(n_runs=n_runs)
    while True:
        _raise_if_abort_requested(abort_requested, "before GA 1-swap polish pass")
        if np.any(prev[:, 0] <= 0):
            bad = int(np.argmin(prev[:, 0]))
            raise RuntimeError(
                f"GA 1-swap polish: run {bad} has no tracked best (score={int(prev[bad, 0])}); "
                "invalid GA state after generation loop"
            )
        hoods = [
            one_swap_neighborhood(prev[r, 1 : 1 + int(n_slots)], slot_start, slot_count, int(n_slots))
            for r in range(n_runs)
        ]
        k_max = max(h.shape[0] for h in hoods)
        if k_max == 0:
            break
        # Pad every run's neighborhood to k_max with incumbent copies (score ties
        # never replace the incumbent), giving uniform GPU blocks per chunk.
        for r in range(n_runs):
            if hoods[r].shape[0] < k_max:
                pad = np.tile(prev[r, 1 : 1 + int(n_slots)].astype(np.int32), (k_max - hoods[r].shape[0], 1))
                hoods[r] = np.concatenate([hoods[r], pad], axis=0)
        for off in range(0, k_max, chunk_cap):
            k = int(min(chunk_cap, k_max - off))
            group_cap = max(1, int(gpu_fields.MAX_GENOMES) // k)
            for g0 in range(0, n_runs, group_cap):
                g_runs = int(min(group_cap, n_runs - g0))
                pop = np.stack([hoods[g0 + j][off : off + k] for j in range(g_runs)])
                gpu_api.ga_upload_initial_populations(pop, n_runs=g_runs, n_genomes=k, n_slots=int(n_slots))
                gpu_api.ga_load_initial_populations_batch(
                    run_idx_start=0, n_runs=g_runs, n_genomes_per_run=k, n_slots=int(n_slots)
                )
                n_total = g_runs * k
                gpu_api.ga_prepare_population_base_stats(n_genomes=n_total, n_slots=int(n_slots), flags=scoring["flags"])
                gpu_api.ga_evaluate_prepared_population(n_genomes=n_total, n_slots=int(n_slots), **scoring, **caps)
                gpu_api.ga_refresh_scores_and_update_runs_best(
                    run_idx_start=g0,
                    n_runs=g_runs,
                    n_genomes_per_run=k,
                    n_slots=int(n_slots),
                    **scoring,
                )
        passes += 1
        cur = gpu_api.ga_download_runs_best(n_runs=n_runs)
        if not bool(np.any(cur[:, 0] > prev[:, 0])):
            break
        prev = cur
    return passes


def run_gpu_native_ga_runs_payload_prebuilt(
    *,
    song: TimedSong,
    curves: StatCurves,
    song_slot: int,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    n_generations: int,
    num_runs: int,
    n_genomes: int = GA_POPULATION_SIZE,
    init_heuristic_topk: "np.ndarray | None" = None,
    init_heuristic_k: int = 0,
    init_heuristic_copies: int = 25,
    color_flags: dict,
    ga_seed: int,
    fg_gear_name_rank: "np.ndarray",
    fg_mini_sig_id: "np.ndarray",
    abort_requested=None,
    on_generation=None,
) -> "np.ndarray":
    """
    Run the GPU-native GA for `num_runs` runs (initial populations generated on the GPU, seeded from `ga_seed`) and
    return the compact selected payload for the FG stage.

    ``on_generation``, when provided, receives a copied (runs, 17) tracked-best
    table after each generation: score, nine item IDs, and seven result values.
    It observes only; production callers leave it unset. Callback time and GPU
    downloads are part of the caller's measured runtime.

    Important: This must be called from the Taichi/Vulkan owner thread (GpuExecutor).
    """
    seed_base = int(ga_seed) & 0xFFFFFFFF
    num_runs, n_genomes, n_slots = int(num_runs), int(n_genomes), 9
    if num_runs <= 0 or n_genomes <= 0:
        raise ValueError(f"GPU-native GA needs runs and genomes: n_runs={num_runs}, n_genomes={n_genomes}")
    song_slot = max(0, int(song_slot))
    n_generations = max(1, int(n_generations))
    init_heuristic_k = int(init_heuristic_k)

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    gpu_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.fields")
    # Size the multi-run GA buffers to this song; only takes effect before the first field allocation.
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    def check(where: str) -> None:
        _raise_if_abort_requested(abort_requested, where)

    def restore_song_gpu_state() -> None:
        upload_ga_song_slot_timeline_state(song=song, curves=curves, song_slot=song_slot)
        upload_ga_global_static_state(
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        )

    def stage_initial_populations() -> None:
        check("before staging initial populations")
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=num_runs,
            n_genomes=n_genomes,
            n_slots=n_slots,
            seed=seed_base,
            heuristic_k=init_heuristic_k,
            heuristic_copies=int(init_heuristic_copies),
        )
        gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=num_runs, n_slots=n_slots)

    # Load refs/timeline + upload static per-song GA data in-request on the owner (the uploads skip content the slot
    # already holds).
    check("before GPU-native GA setup")
    restore_song_gpu_state()
    if init_heuristic_topk is not None and init_heuristic_k > 0:
        gpu_api.ga_upload_init_heuristic_topk(
            topk_ids=np.asarray(init_heuristic_topk, dtype=np.int32), heuristic_k=init_heuristic_k, n_slots=n_slots
        )

    from .taichi_gem.kernels.kernels_helpers import gpu_color_flags

    total_budget, gem_scale_fever = GEM_BUDGET, STAT_GEM_GAIN_FEVER
    max_ft_gems_global, max_ff_gems_global = _compute_global_ftff_combo_caps(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed_stats_arr,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        n_slots=n_slots,
    )
    scoring = dict(
        total_budget=total_budget, gem_scale_fever=gem_scale_fever, song_slot=song_slot,
        flags=gpu_color_flags(dict(color_flags)),
    )
    caps = dict(max_ft_gems_global=max_ft_gems_global, max_ff_gems_global=max_ff_gems_global)
    num_islands = max(1, min(GPU_GA_NUM_ISLANDS, n_genomes // 10))  # at least 10 genomes per island
    gpu_api._ensure_ftff_combo_tables(total_budget, max_ft_gems=max_ft_gems_global, max_ff_gems=max_ff_gems_global)
    # The batch width is sized by genome capacity only: combo chunking inside the evaluation owns dispatch-length
    # (TDR) safety and accumulates bit-exactly across chunks.
    batch_runs = choose_ga_batch_runs(
        n_genomes=n_genomes,
        num_runs=num_runs,
        max_genomes=int(gpu_fields.MAX_GENOMES),
        batch_runs_override=_GPU_NATIVE_GA_BATCH_RUNS,
    ).batch_runs
    batch_runs = max(1, min(int(batch_runs), num_runs))
    if int(gpu_fields.MAX_GA_RUNS) < num_runs:
        raise RuntimeError(
            f"Internal error: the GA buffers hold {int(gpu_fields.MAX_GA_RUNS)} runs, the song needs {num_runs}"
        )

    stage_initial_populations()
    for run0 in range(0, num_runs, batch_runs):
        check("before GPU-native GA batch")
        batch_len = min(batch_runs, num_runs - run0)
        runs = dict(run_idx_start=run0, n_runs=batch_len, n_genomes_per_run=n_genomes, n_slots=n_slots)
        for attempt in range(_GPU_NATIVE_GA_VULKAN_RETRIES + 1):
            try:
                check("before loading GPU-native GA batch")
                gpu_api.ga_load_initial_populations_batch(**runs)
                gpu_api.ga_seed_rng_runs_indexed(
                    n_runs=batch_len, n_genomes_per_run=n_genomes, seed_base=seed_base, run_idx_start=run0
                )
                n_total = batch_len * n_genomes
                for gen in range(n_generations):
                    check(f"before GPU-native GA generation {gen}")
                    gpu_api.ga_prepare_population_base_stats(n_genomes=n_total, n_slots=n_slots, flags=scoring["flags"])
                    gpu_api.ga_evaluate_prepared_population(n_genomes=n_total, n_slots=n_slots, **scoring, **caps)
                    check(f"after GPU-native GA evaluate generation {gen}")
                    # Selection scores stay exact every generation; the last one refreshes without breeding.
                    if gen < n_generations - 1:
                        gpu_api.ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
                            **runs,
                            **scoring,
                            mutation_rate=GA_MUTATION_RATE,
                            immigrant_rate=GA_IMMIGRANT_RATE,
                            tournament_k=GA_TOURNAMENT_K,
                            n_islands=num_islands,
                            elites_per_island=GA_ELITISM,
                            novelty_repair_attempts=GA_NOVELTY_REPAIR_ATTEMPTS,
                        )
                    else:
                        gpu_api.ga_refresh_scores_and_update_runs_best(**runs, **scoring)
                    check(f"after GPU-native GA runs-best update generation {gen}")
                    if on_generation is not None:  # research observer; never feeds back into selection
                        on_generation(gpu_api.ga_download_runs_best(n_runs=num_runs))
                    check(f"after GPU-native GA global-best update generation {gen}")
                # The compact GA->FG candidate table: row 0 = each run's best tracked across generations, rows 1..K =
                # the final population's top scores.
                check("before packing FG candidates from GPU-native GA")
                gpu_api.ga_pack_fg_candidates_table_segmented(table_slot=song_slot, **runs, **scoring)
                check("after packing FG candidates from GPU-native GA")
                break
            except Exception as exc:
                if attempt >= _GPU_NATIVE_GA_VULKAN_RETRIES or not _is_vulkan_semaphore_failure(exc):
                    raise
                gpu_api.hard_reset_taichi(reason=str(exc).splitlines()[0][:200])
                # hard_reset restores the GA buffer defaults: re-size them for this song.
                gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)
                restore_song_gpu_state()
                stage_initial_populations()

    # Exact 1-swap elite polish: every run's tracked best becomes 1-swap-locally-optimal, then the packed FG row 0 is
    # refreshed so the funnel and the selected payload see the polished genomes (the polish consumes the population and
    # eval scratch, so it runs after the pack).
    _polish_runs_best_one_swap(
        gpu_api=gpu_api,
        gpu_fields=gpu_fields,
        n_runs=num_runs,
        n_slots=n_slots,
        slot_start=slot_start,
        slot_count=slot_count,
        scoring=scoring,
        caps=caps,
        abort_requested=abort_requested,
    )
    gpu_api.ga_refresh_fg_candidates_row0(
        table_slot=song_slot, run_idx_start=0, n_runs=num_runs, n_slots=n_slots, flags=scoring["flags"]
    )
    return gpu_api.ga_download_fg_selected_payload(
        table_slot=song_slot, n_runs=num_runs, limit=int(LOADOUTS_PER_SONG_LIMIT)
    )

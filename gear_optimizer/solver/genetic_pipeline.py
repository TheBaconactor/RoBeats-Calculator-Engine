"""The GPU GA: a song's runs on the GPU executor's thread, the 1-swap polish of each run's best, and the compact
payload the FG stage reads; plus the host inputs it needs (FT/FF combo caps, heuristic seed items)."""

import importlib

import numpy as np

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX
from gear_optimizer.solver.timing_envelope import TimedSong
from ..domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from .gpu_tuning_policy import choose_ga_batch_runs


# Runs fall into a song's basins independently, so more, smaller runs reach the best one more often: 5 runs of 352
# (5/6 of the evaluations of the former 3 x 705) missed the best-known Base #1 in 1.5% of default searches on 31
# held-out charts vs 3.8%, with 7-15% less GA time (PLAN.md 10-07).
GA_POPULATION_SIZE = 352
# GA selection/variation policy (fixed; the config.ini overrides were never set in production).
GA_MUTATION_RATE = 0.35
GA_ELITISM = 1
GA_TOURNAMENT_K = 3
GA_IMMIGRANT_RATE = 0.0
GA_NOVELTY_REPAIR_ATTEMPTS = 2


def _global_ftff_combo_caps(item_stats, slot_start, slot_count, base_fixed_stats_arr) -> tuple[int, int]:
    """The most FT and FF gems any genome can use, (MAX_STAT - smallest pre-gem stat) // gem gain within the budget:
    combos above them are impossible for every genome. The smallest stat adds each non-empty slot's minimum (the mini
    slots share one pool, so it can be below any real loadout's: a safe cap)."""
    min_ft, min_ff = int(base_fixed_stats_arr[3]), int(base_fixed_stats_arr[4])
    for start, count in zip(slot_start, slot_count):
        if count:
            min_ft += int(item_stats[start : start + count, 3].min())
            min_ff += int(item_stats[start : start + count, 4].min())
    return tuple(max(0, min(GEM_BUDGET, (MAX_STAT - m) // STAT_GEM_GAIN_FEVER)) for m in (min_ft, min_ff))


def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
    msg = str(exc)
    return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)


def _raise_if_abort_requested(abort_requested, where: str) -> None:
    if abort_requested is not None and abort_requested():
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
) -> "np.ndarray":
    """Per slot, the heuristic_k items with the most 2 x primary + secondary + Perfect Points (lower id first on a tie),
    the last one repeated when the pool is smaller; an empty slot keeps id 0."""
    score_cols = [COLOR_TO_STAT_INDEX[primary_color], COLOR_TO_STAT_INDEX[primary_color],
                  COLOR_TO_STAT_INDEX[secondary_color], 0]
    topk = np.zeros((len(slot_start), heuristic_k), dtype=np.int32)
    for slot_i, (start, count) in enumerate(zip(slot_start, slot_count)):
        if not count:
            continue
        ids = np.arange(start, start + count, dtype=np.int32)
        score = item_stats[ids][:, score_cols].astype(np.int64).sum(axis=1)
        sel = ids[np.lexsort((ids.astype(np.int64), -score))[:heuristic_k]]
        topk[slot_i, : len(sel)] = sel
        topk[slot_i, len(sel) :] = sel[-1]
    return topk


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
    for s in range(n_slots):
        pool = np.arange(slot_start[s], slot_start[s] + slot_count[s], dtype=np.int64)
        pool = pool[pool != inc[s]]
        if s >= 6:
            pool = pool[~np.isin(pool, [inc[j] for j in range(6, n_slots) if j != s])]
        if pool.size == 0:
            continue
        block = np.tile(inc, (pool.size, 1))
        block[:, s] = pool
        rows.append(block)
    if not rows:
        return np.zeros((0, n_slots), dtype=np.int32)
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
    chunk_cap = min(gpu_fields.MAX_GA_RUN_GENOMES, gpu_fields.MAX_GENOMES)
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
            one_swap_neighborhood(prev[r, 1 : 1 + n_slots], slot_start, slot_count, n_slots)
            for r in range(n_runs)
        ]
        k_max = max(h.shape[0] for h in hoods)
        if k_max == 0:
            break
        # Pad every run's neighborhood to k_max with incumbent copies (score ties
        # never replace the incumbent), giving uniform GPU blocks per chunk.
        for r in range(n_runs):
            if hoods[r].shape[0] < k_max:
                pad = np.tile(prev[r, 1 : 1 + n_slots].astype(np.int32), (k_max - hoods[r].shape[0], 1))
                hoods[r] = np.concatenate([hoods[r], pad], axis=0)
        for off in range(0, k_max, chunk_cap):
            k = min(chunk_cap, k_max - off)
            group_cap = max(1, gpu_fields.MAX_GENOMES // k)
            for g0 in range(0, n_runs, group_cap):
                g_runs = min(group_cap, n_runs - g0)
                pop = np.stack([hoods[g0 + j][off : off + k] for j in range(g_runs)])
                gpu_api.ga_upload_initial_populations(pop, n_runs=g_runs, n_genomes=k, n_slots=n_slots)
                gpu_api.ga_load_initial_populations_batch(
                    run_idx_start=0, n_runs=g_runs, n_genomes_per_run=k, n_slots=n_slots
                )
                n_total = g_runs * k
                gpu_api.ga_prepare_population_base_stats(n_genomes=n_total, n_slots=n_slots, flags=scoring["flags"])
                gpu_api.ga_evaluate_prepared_population(n_genomes=n_total, n_slots=n_slots, **scoring, **caps)
                gpu_api.ga_refresh_scores_and_update_runs_best(
                    run_idx_start=g0,
                    n_runs=g_runs,
                    n_genomes_per_run=k,
                    n_slots=n_slots,
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
    n_slots = 9

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    gpu_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.fields")
    # Size the multi-run GA buffers to this song; only takes effect before the first field allocation.
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    def check(where: str) -> None:
        _raise_if_abort_requested(abort_requested, where)

    def restore_song_gpu_state() -> None:
        gpu_api.precompute_timeline_gpu(song, curves, song_slot=song_slot)
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
        gpu_api.ga_upload_fg_effective_tables(fg_gear_name_rank, fg_mini_sig_id)

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

    max_ft_gems_global, max_ff_gems_global = _global_ftff_combo_caps(
        item_stats, slot_start, slot_count, base_fixed_stats_arr
    )
    scoring = dict(
        total_budget=GEM_BUDGET, gem_scale_fever=STAT_GEM_GAIN_FEVER, song_slot=song_slot,
        flags=gpu_color_flags(dict(color_flags)),
    )
    caps = dict(max_ft_gems_global=max_ft_gems_global, max_ff_gems_global=max_ff_gems_global)
    gpu_api._ensure_ftff_combo_tables(GEM_BUDGET, max_ft_gems=max_ft_gems_global, max_ff_gems=max_ff_gems_global)
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
                            n_islands=1,
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

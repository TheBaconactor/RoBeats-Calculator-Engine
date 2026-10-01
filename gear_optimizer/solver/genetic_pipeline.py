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
from gear_optimizer.solver.timing_envelope import TimedSong
from ..core.color_flags import normalize_color_flags
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


def score_fused_fg_from_selected_payload(
    *,
    runs_payload: "np.ndarray",
    fg_scoring_bundle: object,
    song: TimedSong,
    curves: StatCurves,
    cfg_data: dict,
) -> dict:
    """Fused GA->FG owner step: score FG straight from the selected payload (Slice 3).

    Runs on the GPU-owner thread immediately after the GA pack/select, BEFORE the
    payload leaves the owner for async decode/persistence. It slices each selected
    candidate's device ``base_stats7`` (== base_components) from the payload and runs
    the FG response-frontier BUILD + SCORE on the owner, returning a map
    ``base_components_7tuple -> FgFusedOwnerScoreRow`` the driver materializes off the
    owner's critical path (the driver re-derives the same 7-tuples from the same
    payload, so the lookup is exact; the SCORE is a pure function of base_components).

    Required state (no fallback): the song-level FG scoring bundle is prepared pre-GA
    (pipeline.fg.prepare_fg_static) and attached to the GA request payload with the song. Its
    absence fails loudly here.
    """
    if fg_scoring_bundle is None:
        raise ValueError(
            "fused GA->FG handoff requires the song-level FG scoring bundle on the GA "
            "request (prepare_fg_static must run pre-GA)"
        )
    if curves is None:
        raise ValueError("fused GA->FG handoff requires stat curves")

    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        score_fused_owner_base_components_on_gpu_owner,
    )

    payload = np.asarray(runs_payload, dtype=np.int32)
    if payload.ndim != 2 or int(payload.shape[0]) < 1:
        raise ValueError("fused GA->FG handoff requires a 2D selected payload")

    selected_n = int(payload[0, 0])
    if selected_n <= 0:
        return {}
    max_rows = int(payload.shape[0]) - 1
    if selected_n > max_rows:
        selected_n = max_rows

    # Candidate rows 1..selected_n; base_stats7 occupies the last 7 cols of each
    # 26-wide row: [run_idx, row_idx, score, ids(9), results(7), base_stats7(7)] ->
    # base_stats7 starts at col 2 + 1 + 9 + 7 = 19. Same layout the pack kernel writes
    # (payload.py) and decode consumes (decode_gpu_native_ga_runs_payload).
    base_stats7_col0 = 2 + 1 + 9 + 7
    cand_rows = payload[1 : 1 + selected_n]
    if int(cand_rows.shape[1]) < base_stats7_col0 + 7:
        raise ValueError(
            f"fused GA->FG handoff: selected payload rows too narrow for base_stats7 "
            f"({cand_rows.shape[1]} < {base_stats7_col0 + 7})"
        )
    base_components = np.ascontiguousarray(cand_rows[:, base_stats7_col0 : base_stats7_col0 + 7], dtype=np.int32)

    total_budget = int((cfg_data or {}).get("TotalBudget", 90) or 90)
    selected_color = str((cfg_data or {}).get("selected_color", "") or "")

    return score_fused_owner_base_components_on_gpu_owner(
        base_components=base_components,
        song=song,
        curves=curves,
        selected_color=selected_color,
        scoring_bundle=fg_scoring_bundle,
        total_budget=int(total_budget),
    )


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


def _one_swap_neighborhood(
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
    seg_len: int,
    n_slots: int,
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    prepare_flags: dict,
    eval_extra: dict,
    refresh_extra: dict,
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
    prev = gpu_api.ga_download_runs_best(n_runs=int(seg_len))
    while True:
        _raise_if_abort_requested(abort_requested, "before GA 1-swap polish pass")
        if np.any(prev[:, 0] <= 0):
            bad = int(np.argmin(prev[:, 0]))
            raise RuntimeError(
                f"GA 1-swap polish: run {bad} has no tracked best (score={int(prev[bad, 0])}); "
                "invalid GA state after generation loop"
            )
        hoods = [
            _one_swap_neighborhood(prev[r, 1 : 1 + int(n_slots)], slot_start, slot_count, int(n_slots))
            for r in range(int(seg_len))
        ]
        k_max = max(h.shape[0] for h in hoods)
        if k_max == 0:
            break
        # Pad every run's neighborhood to k_max with incumbent copies (score ties
        # never replace the incumbent), giving uniform GPU blocks per chunk.
        for r in range(int(seg_len)):
            if hoods[r].shape[0] < k_max:
                pad = np.tile(prev[r, 1 : 1 + int(n_slots)].astype(np.int32), (k_max - hoods[r].shape[0], 1))
                hoods[r] = np.concatenate([hoods[r], pad], axis=0)
        for off in range(0, k_max, chunk_cap):
            k = int(min(chunk_cap, k_max - off))
            group_cap = max(1, int(gpu_fields.MAX_GENOMES) // k)
            for g0 in range(0, int(seg_len), group_cap):
                g_runs = int(min(group_cap, int(seg_len) - g0))
                pop = np.stack([hoods[g0 + j][off : off + k] for j in range(g_runs)])
                gpu_api.ga_upload_initial_populations(pop, n_runs=g_runs, n_genomes=k, n_slots=int(n_slots))
                gpu_api.ga_load_initial_populations_batch(
                    run_idx_start=0, n_runs=g_runs, n_genomes_per_run=k, n_slots=int(n_slots)
                )
                n_total = g_runs * k
                gpu_api.ga_prepare_population_base_stats(n_genomes=n_total, n_slots=int(n_slots), **prepare_flags)
                gpu_api.ga_evaluate_prepared_population(n_genomes=n_total, n_slots=int(n_slots), **eval_extra)
                gpu_api.ga_refresh_scores_and_update_runs_best(
                    run_idx_start=g0,
                    n_runs=g_runs,
                    n_genomes_per_run=k,
                    n_slots=int(n_slots),
                    **refresh_extra,
                )
        passes += 1
        cur = gpu_api.ga_download_runs_best(n_runs=int(seg_len))
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
    initial_populations: "np.ndarray | None" = None,
    num_runs: int | None = None,
    n_genomes: int = GA_POPULATION_SIZE,
    init_heuristic_topk: "np.ndarray | None" = None,
    init_heuristic_k: int = 0,
    init_heuristic_copies: int = 25,
    color_flags: dict | None = None,
    cfg_data: dict | None = None,
    ga_seed: int | None = None,
    fg_gear_name_rank: "np.ndarray | None" = None,
    fg_mini_sig_id: "np.ndarray | None" = None,
    abort_requested=None,
    on_generation=None,
) -> "np.ndarray":
    """
    Run the GPU-native GA for multiple runs using either:
    - prebuilt CPU populations, or
    - GPU-generated initial populations (preferred).

    This entrypoint is designed for the GPU-native in-flight pipeline:
    - CPU prepares/encodes initial populations and item registry arrays
    - GPU-owner thread executes kernels back-to-back and returns a compact runs payload

    ``on_generation``, when provided, receives a copied (runs, 17) tracked-best
    table after each generation: score, nine item IDs, and seven result values.
    It observes only; production callers leave it unset. Callback time and GPU
    downloads are part of the caller's measured runtime.

    Important: This must be called from the Taichi/Vulkan owner thread (GpuExecutor).
    """
    cfg_data = dict(cfg_data or {})
    color_flags = dict(color_flags or {})

    if ga_seed is None:
        raise ValueError("GPU-native GA requires an explicit per-run ga_seed")
    try:
        seed_base = int(ga_seed) & 0xFFFFFFFF
    except Exception as exc:
        raise ValueError("GPU-native GA requires an integer per-run ga_seed") from exc

    if fg_gear_name_rank is None or fg_mini_sig_id is None:
        raise ValueError(
            "GPU-native GA requires fg_gear_name_rank/fg_mini_sig_id effective-dedup "
            "tables for the song's color context (built at prep via "
            "fg_effective_dedup.effective_tables_for_context)"
        )

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    gpu_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.fields")

    song_slot = int(song_slot)
    if song_slot < 0:
        song_slot = 0

    n_generations = int(n_generations)
    if n_generations <= 0:
        n_generations = 1

    # The GA's selection/variation policy is fixed (module constants).
    elite_count = GA_ELITISM
    tournament_k = GA_TOURNAMENT_K
    mutation_rate = GA_MUTATION_RATE
    immigrant_rate = GA_IMMIGRANT_RATE

    if initial_populations is not None:
        if not isinstance(initial_populations, np.ndarray):
            initial_populations = np.asarray(initial_populations, dtype=np.int32)
        if initial_populations.ndim != 3:
            raise ValueError(
                f"initial_populations must have shape (n_runs, n_genomes, n_slots); got ndim={initial_populations.ndim}"
            )
        num_runs = int(initial_populations.shape[0])
        n_genomes = int(initial_populations.shape[1])
        n_slots = int(initial_populations.shape[2])
    else:
        if num_runs is None:
            raise ValueError("num_runs is required when initial_populations is None")
        num_runs = int(num_runs)
        n_genomes = int(n_genomes)
        n_slots = 9

    if num_runs <= 0 or n_genomes <= 0 or n_slots <= 0:
        raise ValueError(
            f"initial_populations has invalid shape: (n_runs={num_runs}, n_genomes={n_genomes}, n_slots={n_slots})"
        )

    if n_slots != 9:
        raise ValueError(f"GPU-native GA expects n_slots=9, got {n_slots}")

    # Reduce padded CPU↔GPU transfers by sizing multi-run GA buffers to the
    # current session's needs. This MUST happen before the first Taichi field
    # allocation (i.e., before ensure_ready/precompute_timeline triggers field allocation).
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    max_retries = _GPU_NATIVE_GA_VULKAN_RETRIES

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    def _restore_song_gpu_state() -> None:
        upload_ga_song_slot_timeline_state(
            song=song,
            curves=curves,
            song_slot=song_slot,
        )
        upload_ga_global_static_state(
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
        )

    # Load refs/timeline + upload static per-song GA data once, in-request on the
    # owner. The per-slot upload helpers content-skip when the slot already holds
    # this song's state, so the request is self-sufficient without a separate
    # slot-warm side channel.
    _raise_if_abort_requested(abort_requested, "before GPU-native GA setup")
    _restore_song_gpu_state()

    # Optional heuristic top-K table for GPU initial population generation.
    init_heuristic_k = int(init_heuristic_k)
    if init_heuristic_topk is not None and init_heuristic_k > 0:
        gpu_api.ga_upload_init_heuristic_topk(
            topk_ids=np.asarray(init_heuristic_topk, dtype=np.int32),
            heuristic_k=int(init_heuristic_k),
            n_slots=int(n_slots),
        )

    (
        is_p_ft,
        is_s_ft,
        is_p_ff,
        is_s_ff,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
    ) = normalize_color_flags(color_flags).as_tuple()

    total_budget = int(cfg_data.get("TotalBudget", 90))
    gem_scale_fever = int(cfg_data.get("GemScaleFever", 3))
    max_ft_gems_global, max_ff_gems_global = _compute_global_ftff_combo_caps(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed_stats_arr,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
        n_slots=int(n_slots),
    )
    novelty_repair_attempts = GA_NOVELTY_REPAIR_ATTEMPTS

    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT)

    # Island model (mirrors _run_gpu_native_ga)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1

    # Determine an auto batch size that avoids combo-chunking in ga_evaluate_population.
    # Chunking increases kernel launch count, so we prefer keeping n_total*n_combos <= MAX_EVALS_PER_DISPATCH.
    gpu_api._ensure_ftff_combo_tables(
        total_budget,
        max_ft_gems=int(max_ft_gems_global),
        max_ff_gems=int(max_ff_gems_global),
    )

    # Batch width is sized by genome capacity only (MAX_GENOMES pool); the
    # eval budget is NOT a factor -- combo chunking inside
    # ga_evaluate_prepared_population owns TDR/dispatch-length safety and
    # accumulates bit-exactly across chunks. Co-batch up to num_runs at once.
    batch_runs_default = choose_ga_batch_runs(
        n_genomes=int(n_genomes),
        num_runs=int(num_runs),
        max_genomes=int(gpu_fields.MAX_GENOMES),
        batch_runs_override=int(_GPU_NATIVE_GA_BATCH_RUNS),
    ).batch_runs

    payload_segments: list[np.ndarray] = []

    def _stage_segment_initial_populations(*, run_start: int, seg_runs: int, segment_pop_arr) -> None:
        _raise_if_abort_requested(abort_requested, "before staging initial populations")
        if segment_pop_arr is not None:
            gpu_api.ga_upload_initial_populations(
                segment_pop_arr,
                n_runs=int(seg_runs),
                n_genomes=int(n_genomes),
                n_slots=int(n_slots),
            )
            return

        # Generate initial populations on GPU for this segment (seeded per segment to avoid repeats).
        seg_seed = int(seed_base) ^ (int(run_start) * 747796405)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=int(seg_runs),
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
            seed=int(seg_seed),
            heuristic_prob=0.0,
            heuristic_k=int(init_heuristic_k),
            heuristic_copies=int(init_heuristic_copies),
        )

    run_start_global = 0
    while run_start_global < num_runs:
        _raise_if_abort_requested(abort_requested, "before GPU-native GA segment")
        seg_len = min(int(gpu_fields.MAX_GA_RUNS), num_runs - run_start_global)
        segment_pop = None
        if initial_populations is not None:
            segment_pop = np.asarray(initial_populations[run_start_global : run_start_global + seg_len], dtype=np.int32)
        _stage_segment_initial_populations(
            run_start=int(run_start_global),
            seg_runs=int(seg_len),
            segment_pop_arr=segment_pop,
        )

        # Initialize per-run best rows for this segment (used by batched execution).
        gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))

        batch_runs = min(int(batch_runs_default), int(seg_len))
        if batch_runs < 1:
            batch_runs = 1

        local_run_idx = 0
        while local_run_idx < seg_len:
            _raise_if_abort_requested(abort_requested, "before GPU-native GA batch")
            global_run_idx = run_start_global + local_run_idx

            batch_len = min(batch_runs, seg_len - local_run_idx)
            if batch_len <= 0:
                batch_len = 1

            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    _raise_if_abort_requested(abort_requested, "before loading GPU-native GA batch")
                    # Pack batch initial populations contiguously, preserving per-run semantics.
                    gpu_api.ga_load_initial_populations_batch(
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
                    )
                    gpu_api.ga_seed_rng_runs_indexed(
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        seed_base=int(seed_base),
                        run_idx_start=int(global_run_idx),
                    )

                    n_total = int(batch_len) * int(n_genomes)

                    # Loop-invariant per-batch kernel args: build the prepare/evaluate kwargs
                    # once so the per-generation prepare->evaluate GPU re-feed window does not
                    # rebuild these dicts every generation. Every value here is fixed for this
                    # batch (n_total, n_slots, budgets, color flags, ftff caps) and is recomputed
                    # to the same value if the attempt loop re-enters on a Vulkan-reset retry.
                    prepare_kwargs = dict(
                        n_genomes=n_total,
                        n_slots=int(n_slots),
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                    )
                    eval_kwargs = dict(
                        n_genomes=n_total,
                        n_slots=int(n_slots),
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
                        song_slot=int(song_slot),
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                        max_ft_gems_global=int(max_ft_gems_global),
                        max_ff_gems_global=int(max_ff_gems_global),
                    )

                    for gen in range(int(n_generations)):
                        _raise_if_abort_requested(abort_requested, f"before GPU-native GA generation {int(gen)}")
                        gpu_api.ga_prepare_population_base_stats(**prepare_kwargs)
                        gpu_api.ga_evaluate_prepared_population(**eval_kwargs)
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA evaluate generation {int(gen)}"
                        )

                        # Keep selection scores exact every generation, but only write full per-genome
                        # result rows when tracing needs them. Row 0 stays exact in both paths.
                        # The final generation refreshes without producing a next population.
                        if gen < int(n_generations) - 1:
                            gpu_api.ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
                                run_idx_start=int(local_run_idx),
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
                                n_slots=int(n_slots),
                                total_budget=total_budget,
                                gem_scale_fever=gem_scale_fever,
                                song_slot=int(song_slot),
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                mutation_rate=float(mutation_rate),
                                immigrant_rate=float(immigrant_rate),
                                tournament_k=int(tournament_k),
                                n_islands=int(num_islands),
                                elites_per_island=int(elite_count),
                                novelty_repair_attempts=int(novelty_repair_attempts),
                            )
                        else:
                            gpu_api.ga_refresh_scores_and_update_runs_best(
                                run_idx_start=int(local_run_idx),
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
                                n_slots=int(n_slots),
                                total_budget=total_budget,
                                gem_scale_fever=gem_scale_fever,
                                song_slot=int(song_slot),
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                            )
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA runs-best update generation {int(gen)}"
                        )
                        if on_generation is not None:
                            # Optional research observer; never feeds scores back into GA selection.
                            on_generation(gpu_api.ga_download_runs_best(n_runs=int(seg_len)))
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA global-best update generation {int(gen)}"
                        )

                    # Pack a compact GA->FG candidate table for this batch, avoiding large
                    # `(runs, pop, payload_cols)` downloads. Row 0 is per-run best (tracked
                    # across generations), rows 1..K are top-score entries from the final population.
                    _raise_if_abort_requested(abort_requested, "before packing FG candidates from GPU-native GA")
                    gpu_api.ga_pack_fg_candidates_table_segmented(
                        table_slot=int(song_slot),
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                        song_slot=int(song_slot),
                    )
                    _raise_if_abort_requested(abort_requested, "after packing FG candidates from GPU-native GA")

                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    if attempt >= max_retries or not _is_vulkan_semaphore_failure(e):
                        break
                    gpu_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])
                    # hard_reset restores GA-buffer defaults; re-size for the rest
                    # of the song (was the env bridge's job before flag elimination).
                    gpu_fields.configure_ga_run_buffers(max_runs=int(num_runs), max_genomes=int(n_genomes))
                    _restore_song_gpu_state()
                    _stage_segment_initial_populations(
                        run_start=int(run_start_global),
                        seg_runs=int(seg_len),
                        segment_pop_arr=segment_pop,
                    )
                    gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))

            if last_exc is not None:
                raise last_exc

            local_run_idx += int(batch_len)

        # Exact 1-swap elite polish (always-on): make every run's tracked best
        # 1-swap-locally-optimal, then refresh the packed FG row 0 so the funnel
        # and the selected payload see the polished genomes. Runs after the pack
        # because the polish consumes population_indices/eval scratch.
        _polish_flags = dict(
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
            is_p_ov=is_p_ov,
            is_s_ov=is_s_ov,
        )
        _polish_runs_best_one_swap(
            gpu_api=gpu_api,
            gpu_fields=gpu_fields,
            seg_len=int(seg_len),
            n_slots=int(n_slots),
            slot_start=slot_start,
            slot_count=slot_count,
            prepare_flags=dict(_polish_flags),
            eval_extra=dict(
                total_budget=total_budget,
                gem_scale_fever=gem_scale_fever,
                song_slot=int(song_slot),
                max_ft_gems_global=int(max_ft_gems_global),
                max_ff_gems_global=int(max_ff_gems_global),
                **_polish_flags,
            ),
            refresh_extra=dict(
                total_budget=total_budget,
                gem_scale_fever=gem_scale_fever,
                song_slot=int(song_slot),
                **_polish_flags,
            ),
            abort_requested=abort_requested,
        )
        gpu_api.ga_refresh_fg_candidates_row0(
            table_slot=int(song_slot),
            run_idx_start=0,
            n_runs=int(seg_len),
            n_slots=int(n_slots),
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
        )

        selected_payload = gpu_api.ga_download_fg_selected_payload(
            table_slot=int(song_slot),
            n_runs=int(seg_len),
            limit=int(fg_candidate_limit),
        )
        payload_segments.append(selected_payload)
        run_start_global += seg_len

    if not payload_segments:
        raise RuntimeError("Internal error: no GA payload segments were produced")

    if len(payload_segments) != 1:
        raise RuntimeError(
            f"Internal error: expected a single selected-payload segment, got {len(payload_segments)} segments"
        )

    return payload_segments[0]

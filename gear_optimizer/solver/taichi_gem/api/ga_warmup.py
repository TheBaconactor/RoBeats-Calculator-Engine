from __future__ import annotations

import logging

import numpy as np

from .. import fields

logger = logging.getLogger(__name__)


def _warmup_ref_arrays() -> dict[str, np.ndarray]:
    x = np.linspace(0.0, 1.0, int(fields.GRID_SIZE), dtype=np.float32)
    return {
        "Perfect Points": (1000.0 + (500.0 * x)).astype(np.float32, copy=False),
        "Combo Multiplier": (1.0 + x).astype(np.float32, copy=False),
        "Fever Multiplier": (1.0 + (0.5 * x)).astype(np.float32, copy=False),
        "Fever Time": (5.0 + (30.0 * x)).astype(np.float32, copy=False),
        "Fever Fill Rate": (1.0 + (4.0 * x)).astype(np.float32, copy=False),
    }


def _warmup_calc_song() -> dict:
    timestamps = np.linspace(0.0, 18.0, 48, dtype=np.float32)
    note_types = np.zeros((timestamps.shape[0],), dtype=np.int32)
    return {
        "metadata": {
            "Song Name": "__ga_live_request_warmup__",
            "Difficulty": "Warmup",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]) if timestamps.size else 0.0,
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }


def warmup_ga_live_request_kernels() -> None:
    """
    Warm the kernels and upload paths used by the first real GPU-native GA request.

    The full offline warmup historically covered GA evaluation, but not the live
    `ensure_ready(refs) -> precompute_timeline_gpu() -> materialize_mode="none"
    -> refresh row 0` path. Missing that path lets stale sentinels push timeline
    and live-request JIT/load costs into the first real song, creating a visible
    0%-utilization valley before the sustained workload begins.
    """
    from . import ga_operations as ga_ops
    from .ga_operations import (
        ensure_ready,
        ga_download_fg_selected_payload,
        ga_evaluate_population,
        ga_generate_initial_populations,
        ga_init_global_best,
        ga_init_runs_best,
        ga_load_initial_population,
        ga_next_generation_fused_runs,
        ga_pack_fg_candidates_table_segmented,
        ga_refresh_scores_and_update_runs_best,
        ga_seed_rng_runs,
        ga_upload_base_fixed_stats,
        ga_upload_island_boundaries,
        ga_upload_item_stats,
    )

    if ga_ops._GA_LIVE_REQUEST_WARMED:
        return

    ensure_ready()

    import taichi as ti

    from .timeline import precompute_timeline_gpu

    n_slots = 9
    n_runs = 1
    n_genomes = min(64, int(getattr(fields, "MAX_GA_RUN_GENOMES", 250) or 250), int(fields.MAX_GENOMES))
    n_genomes = max(1, int(n_genomes))
    total_budget = min(90, int(fields.MAX_TOTAL_BUDGET))
    gem_scale_fever = 3
    song_slot = 0

    ref_arrays = _warmup_ref_arrays()
    ensure_ready(ref_arrays)
    precompute_timeline_gpu(_warmup_calc_song(), ref_arrays, song_slot=song_slot)

    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))
    ga_upload_island_boundaries(np.array([0, int(n_genomes)], dtype=np.int32))

    ga_generate_initial_populations(
        run_idx_start=0,
        n_runs=n_runs,
        n_genomes=int(n_genomes),
        n_slots=n_slots,
        seed=12345,
    )
    ga_load_initial_population(run_idx=0, n_genomes=int(n_genomes), n_slots=n_slots)
    ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=int(n_genomes), seed=12345)
    ga_init_runs_best(run_idx_start=0, n_runs=n_runs, n_slots=n_slots)
    ga_init_global_best()

    ga_evaluate_population(
        int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        materialize_mode="none",
    )
    ga_refresh_scores_and_update_runs_best(
        run_idx_start=0,
        n_runs=n_runs,
        n_genomes_per_run=int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
    )
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=int(n_genomes),
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=1,
        n_islands=1,
        elites_per_island=1,
    )
    ga_pack_fg_candidates_table_segmented(
        table_slot=song_slot,
        run_idx_start=0,
        n_runs=n_runs,
        n_genomes_per_run=int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
    )
    _ = ga_download_fg_selected_payload(
        table_slot=song_slot,
        n_runs=n_runs,
        limit=1,
        top_base_keep=1,
        base_budget=1,
        fg_budget_end=1,
    )
    ti.sync()
    ga_ops._GA_LIVE_REQUEST_WARMED = True


def warmup_ga_kernels() -> None:
    """
    Best-effort Taichi JIT warmup for GPU-native GA kernels.

    Goal: avoid the first real GA request paying multi-second compilation latency on Vulkan,
    which shows up as a \"GPU idle\" gap in high-level monitoring and can create bursty
    utilization graphs.

    Notes:
    - Uses tiny dummy inputs (correctness is irrelevant; outputs are discarded).
    - Idempotent: safe to call multiple times.
    """
    from . import ga_operations as ga_ops
    from .ga_operations import (
        ensure_ready,
        ga_download_fg_selected_payload,
        ga_download_global_best,
        ga_evaluate_population,
        ga_init_global_best,
        ga_init_runs_best,
        ga_island_migration_runs,
        ga_load_initial_populations_batch,
        ga_seed_rng_runs,
        ga_next_generation_fused_runs,
        ga_pack_fg_candidates_table_segmented,
        ga_update_runs_best,
        ga_upload_base_fixed_stats,
        ga_upload_initial_populations,
        ga_upload_island_boundaries,
        ga_upload_item_stats,
    )

    if ga_ops._GA_KERNELS_WARMED:
        return

    ensure_ready()

    # Minimal sizes that still exercise the full GA pipeline (evaluate -> next-gen -> pack -> select).
    n_slots = 9
    n_runs = 1
    n_genomes_per_run = min(64, int(getattr(fields, "MAX_GA_RUN_GENOMES", 250) or 250))
    if n_genomes_per_run < 1:
        n_genomes_per_run = 1
    n_total = int(n_runs) * int(n_genomes_per_run)
    if n_total > int(fields.MAX_GENOMES):
        n_genomes_per_run = max(1, int(fields.MAX_GENOMES))
        n_total = int(n_runs) * int(n_genomes_per_run)

    # Small but non-zero budget so combo tables are populated and the FT/FF kernels are exercised.
    total_budget = 1
    gem_scale_fever = 3
    song_slot = 0

    # Ensure per-slot item ranges are valid (avoid divide-by-zero in mutation/immigrant ops).
    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))

    # Upload a trivial island boundary table so island-based kernels have valid ranges.
    n_islands = 2
    if n_islands > int(getattr(fields, "MAX_ISLANDS", n_islands) or n_islands):
        n_islands = int(getattr(fields, "MAX_ISLANDS", 1) or 1)
    if n_islands < 1:
        n_islands = 1
    # Boundaries: [0, mid, end] for 2 islands (or [0,end] for 1 island)
    if n_islands == 1:
        boundaries = np.array([0, int(n_total)], dtype=np.int32)
    else:
        mid = int(n_total // 2)
        boundaries = np.array([0, mid, int(n_total)], dtype=np.int32)
    ga_upload_island_boundaries(boundaries)

    # Stage a single-run initial population and seed RNG.
    pops = np.zeros((n_runs, n_genomes_per_run, n_slots), dtype=np.int32)
    ga_upload_initial_populations(pops, n_runs=n_runs, n_genomes=n_genomes_per_run, n_slots=n_slots)
    ga_load_initial_populations_batch(
        run_idx_start=0, n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, n_slots=n_slots
    )
    ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, seed=12345)

    # Initialize + run a minimal 1-generation evaluation.
    ga_init_runs_best(run_idx_start=0, n_runs=n_runs, n_slots=n_slots)
    ga_init_global_best()
    ga_evaluate_population(
        n_total,
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        materialize_mode="update_global",
    )
    try:
        # Best-effort: ensure the global-best pack/download kernels are JIT'd too.
        _ = ga_download_global_best()
    except Exception as e:
        logger.debug(f"ga_operations:warmup_ga_kernels: {e}")
    ga_update_runs_best(run_idx_start=0, n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, n_slots=n_slots)

    # Warm migration + fused next-gen kernels (typical path in GPU-native GA).
    ga_island_migration_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_islands=n_islands,
        migrate_count=1,
        n_slots=n_slots,
    )
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=1,
        n_islands=n_islands,
        elites_per_island=1,
    )

    # Warm GA->FG packing + GPU-side selection/download kernels.
    ga_pack_fg_candidates_table_segmented(
        table_slot=song_slot,
        run_idx_start=0,
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
    )
    # limit=1 keeps the staging download small while still exercising the kernels.
    _ = ga_download_fg_selected_payload(
        table_slot=song_slot,
        n_runs=n_runs,
        limit=1,
        top_base_keep=1,
        base_budget=1,
        fg_budget_end=1,
    )

    warmup_ga_live_request_kernels()
    ga_ops._GA_KERNELS_WARMED = True


def warmup_ga_kernels_light() -> None:
    """
    Lightweight per-process warmup for GPU-native GA kernels.

    This is intentionally smaller than `warmup_ga_kernels()`:
    - It targets the per-process first-hit JIT/loading costs for the kernels that dominate GA runtime
      (evaluate cold+warm, plus fused next-gen and initial population generation).
    - It avoids downloads and GA->FG packing/selection to keep runtime bounded.

    This is useful when offline caches are already built and we just want to avoid the first real GA
    request paying a multi-second spike (which can skew phase-timing profiles).

    Notes:
    - Outputs are discarded; correctness is irrelevant.
    - Idempotent per process.
    """
    from . import ga_operations as ga_ops
    from .ga_operations import (
        ensure_ready,
        ga_evaluate_population,
        ga_generate_initial_populations,
        ga_init_global_best,
        ga_next_generation_fused,
        ga_upload_base_fixed_stats,
        ga_upload_island_boundaries,
        ga_upload_item_stats,
        ga_upload_population_indices,
    )

    if ga_ops._GA_KERNELS_LIGHT_WARMED or ga_ops._GA_KERNELS_WARMED:
        return

    ensure_ready()

    import taichi as ti

    n_slots = 9
    n_genomes = min(64, int(getattr(fields, "MAX_GA_RUN_GENOMES", 250) or 250))
    if n_genomes < 1:
        n_genomes = 1
    n_genomes = min(int(n_genomes), int(fields.MAX_GENOMES))

    # Small but non-zero budget so combo tables are populated and the FT/FF kernels are exercised.
    total_budget = 1
    gem_scale_fever = 3
    song_slot = 0

    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))

    ga_upload_island_boundaries(np.array([0, int(n_genomes)], dtype=np.int32))
    pop = np.zeros((int(n_genomes), int(n_slots)), dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=int(n_slots))

    ga_init_global_best()

    # Compile/load the exact evaluation path.
    ga_evaluate_population(
        int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        materialize_mode="update_global",
    )
    ti.sync()

    # Warm the common GPU-generated population path (used when CPU prebuilt pops are absent).
    try:
        ga_generate_initial_populations(
            run_idx_start=0, n_runs=1, n_genomes=int(n_genomes), n_slots=n_slots, seed=12345
        )
        ti.sync()
    except Exception as e:
        logger.debug(f"ga_operations:warmup_ga_kernels_light: {e}")

    # Warm fused next-gen path (single-run).
    try:
        warmup_ga_live_request_kernels()
    except Exception as e:
        logger.debug(f"ga_operations:warmup_ga_kernels_light: {e}")

    try:
        ga_next_generation_fused(
            n_genomes=int(n_genomes),
            n_slots=n_slots,
            mutation_rate=0.0,
            immigrant_rate=0.0,
            tournament_k=1,
            n_islands=1,
            elites_per_island=1,
        )
        ti.sync()
    except Exception as e:
        logger.debug(f"ga_operations:warmup_ga_kernels_light: {e}")

    ga_ops._GA_KERNELS_LIGHT_WARMED = True

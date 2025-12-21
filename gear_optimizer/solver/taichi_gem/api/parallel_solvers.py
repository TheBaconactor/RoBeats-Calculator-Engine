"""
API Parallel Solvers - Maximum parallelism genome solvers.

This module provides GPU-parallel genome solvers with different parallelization strategies:
- solve_genomes_with_ftff: GPU-resident FT/FF iteration (~100x faster than old approach)
- solve_genomes_parallel: Maximum parallelism across (genome, ft, ff) = ~400k threads
- solve_genomes_parallel_merged: Merged variant with chunking support
"""
from __future__ import annotations

import time

import numpy as np

from gear_optimizer.core.env_config import ENV
from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

from .. import fields
from ..fields import MAX_GENOMES, MAX_WORK_ITEMS
from ..kernel_loader import get_kernels

from .initialization import (
    ensure_ready,
    _maybe_sync,
    _ref_arrays_sig,
    _SYNC_FOR_TIMING,
    _upload_song_flags,
    _ensure_parallel_staging,
)
from .timeline import precompute_timeline_gpu, _upload_timeline_grid
from .ga_operations import (
    ga_upload_population_indices,
    ga_upload_item_stats,
    ga_upload_base_fixed_stats,
    ga_aggregate_stats,
)

_profiler = get_gpu_profiler()

# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
_GENOME_STATS_CACHE = None

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()

def solve_genomes_with_ftff(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
) -> list:
    """
    Solve gem allocation for multiple genomes with GPU-resident FT/FF iteration.
    
    Uploads the timeline grid ONCE, then processes all genomes in a single
    kernel launch that iterates FT/FF combinations on-GPU.
    
    ~100x faster than the old approach which transferred 400k work items.
    
    Args:
        genome_stats_list: List of dicts with base stats per genome
        timeline_grid: SongTimelineGrid (precompute_all will be called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    ensure_ready(ref_arrays, need_grid=True)
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=0)
    else:
        _upload_timeline_grid(timeline_grid)

    _upload_song_flags({
        0: (
            int(is_p_ft), int(is_s_ft), int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp), int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm), int(is_p_ov), int(is_s_ov),
        )
    })

    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload per-genome stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    stats_buf = np.zeros((n_genomes, 7), dtype=np.int16)
    
    for i, stats in enumerate(genome_stats_list):
        stats_buf[i, 0] = stats["base_pp"]
        stats_buf[i, 1] = stats["base_cm"]
        stats_buf[i, 2] = stats["base_fm"]
        stats_buf[i, 3] = stats["base_p_val"]
        stats_buf[i, 4] = stats["base_s_val"]
        stats_buf[i, 5] = stats["base_ft_stat"]
        stats_buf[i, 6] = stats["base_ff_stat"]
    
    fields.genome_base_stats.from_numpy(stats_buf)
    
    # Launch kernel
    kernels.solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        0,  # song_slot=0 for single-song mode
    )

    # NOTE: ti.sync() removed - to_numpy() internally syncs
    
    # Download results
    # [score, ft, ff, pp, cm, fm, ov]
    results_np = fields.genome_result_stats.to_numpy()[:n_genomes]
    
    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append((
            int(row[0]), # score
            int(row[1]), # ft
            int(row[2]), # ff
            int(row[3]), # pp
            int(row[4]), # cm
            int(row[5]), # fm
            int(row[6]), # ov
        ))
    
    return results


def solve_genomes_parallel(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
) -> list:
    """
    V2: Solve gem allocation with MAXIMUM parallelism.
    
    Parallelizes across (genome, ft, ff) combinations = ~400k threads.
    Combines the parallelism of the old approach with the low transfer
    overhead of the new approach.
    
    Args:
        genome_stats_list: List of dicts with base stats per genome
        timeline_grid: SongTimelineGrid (precompute_all will be called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        song_slot: Grid slot for batch coalescing (0-7, default 0)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """

    # Ensure grid fields are available; timeline data must be available in `song_slot`.
    ensure_ready(ref_arrays, need_grid=True)

    # If we were given a lightweight calc_song dict, compute the 161×161 grid on GPU
    # directly into this song slot (avoids pickling CPU timeline objects in parallel mode).
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        # CPU upload path (slot 0 only today).
        if int(song_slot) != 0:
            raise ValueError("SongTimelineGrid upload supports song_slot=0 only; use calc_song dict for multi-slot batching")
        _upload_timeline_grid(timeline_grid)

    # Upload per-slot flags used by the kernel.
    _upload_song_flags({
        int(song_slot): (
            int(is_p_ft), int(is_s_ft), int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp), int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm), int(is_p_ov), int(is_s_ov),
        )
    })

    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Get reusable staging buffers (avoid per-call allocations)
    staging = _ensure_parallel_staging()
    genome_stats_np = staging["genome_base_stats"]
    
    # Also track max allowed FT/FF per genome for work item generation
    max_ft_list = []
    max_ff_list = []
    
    for i, stats in enumerate(genome_stats_list):
        # [pp, cm, fm, p_val, s_val, ft, ff]
        genome_stats_np[i, 0] = stats["base_pp"]
        genome_stats_np[i, 1] = stats["base_cm"]
        genome_stats_np[i, 2] = stats["base_fm"]
        genome_stats_np[i, 3] = stats["base_p_val"]
        genome_stats_np[i, 4] = stats["base_s_val"]
        genome_stats_np[i, 5] = stats["base_ft_stat"]
        genome_stats_np[i, 6] = stats["base_ff_stat"]
        
        # Compute max FT/FF gems
        remaining_ft = 160 - stats["base_ft_stat"]
        remaining_ff = 160 - stats["base_ff_stat"]
        max_ft = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        max_ft_list.append(min(total_budget, max_ft))
        max_ff_list.append(min(total_budget, max_ff))
    
    # OPTIMIZATION: Skip upload if genome stats unchanged (saves ~1-2s per run)
    # Hash only the portion of the buffer that's actually used
    global _GENOME_STATS_CACHE
    stats_slice = genome_stats_np[:n_genomes].tobytes()
    stats_hash = hash(stats_slice)
    cache_key = (n_genomes, stats_hash)
    
    if _GENOME_STATS_CACHE != cache_key:
        fields.genome_base_stats.from_numpy(genome_stats_np)
        _GENOME_STATS_CACHE = cache_key
    
    # Generate work items: (genome_id, ft, ff) for all valid combinations
    # Avoid huge Python list append overhead by precomputing size and filling arrays.
    n_work = 0
    for genome_idx in range(n_genomes):
        max_ft = int(max_ft_list[genome_idx])
        max_ff = int(max_ff_list[genome_idx])
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            n_work += (min(remaining, max_ff) + 1)

    work_genome = np.empty((n_work,), dtype=np.int32)
    work_ft = np.empty((n_work,), dtype=np.int32)
    work_ff = np.empty((n_work,), dtype=np.int32)
    work_budgets = np.empty((n_work,), dtype=np.int32) # Need budget per item

    pos = 0
    for genome_idx in range(n_genomes):
        max_ft = int(max_ft_list[genome_idx])
        max_ff = int(max_ff_list[genome_idx])
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            ff_max = min(remaining, max_ff)
            cnt = ff_max + 1
            work_genome[pos : pos + cnt] = genome_idx
            work_ft[pos : pos + cnt] = ft
            work_ff[pos : pos + cnt] = np.arange(cnt, dtype=np.int32)
            # Kernel reads budget from item[0], so we must precalculate it.
            # budget = total_budget - ft - ff
            
            # Vectorized budget fill:
            # budget = total - ft - ff
            # ff ranges from 0 to ff_max
            # budget ranges from (total-ft) down to (total-ft-ff_max)
            current_budget_base = total_budget - ft
            work_budgets[pos : pos + cnt] = current_budget_base - np.arange(cnt, dtype=np.int32)
            
            pos += cnt

    # Safety: ensure we filled exactly what we allocated
    if pos != n_work:
        raise RuntimeError(f"Internal error: filled work items {pos} != allocated {n_work}")
    
    if n_work == 0:
        return [(0, 0, 0, 0, 0, 0, 0) for _ in range(n_genomes)]
    
    # Process in chunks if exceeds MAX_WORK_ITEMS
    chunk_size = MAX_WORK_ITEMS
    num_chunks = (n_work + chunk_size - 1) // chunk_size
    
    # Initialize genome results ONCE before any chunks
    kernels.init_genome_results_kernel(n_genomes)
    
    # Get reusable work item buffers
    work_items_np = staging["work_items"]
    
    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_work)
        chunk_n = end - start
        
        # Copy work items into reusable buffers (no allocation needed)
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        
        # Pack work items: budget, ft, ff, genome_id.
        # Kernel reads count_fever, count_normal, head_len from grid, so input values don't matter.
        
        # Flattened packing
        # Reset buffer for cleanliness (optional but safer)
        # work_items_np[:chunk_n, :] = 0 
        
        work_items_np[:chunk_n, 0] = work_budgets[start:end]      # budget
        work_items_np[:chunk_n, 3] = work_ft[start:end]           # ft_gems
        work_items_np[:chunk_n, 4] = work_ff[start:end]           # ff_gems
        work_items_np[:chunk_n, 6] = work_genome[start:end]       # genome_id
        work_items_np[:chunk_n, 7] = song_slot                     # song_slot (batch coalescing)


        
        # OPTIMIZATION: Upload only when profiling disabled to reduce overhead
        if _profiler.enabled:
            _t_upload = time.perf_counter()
            fields.work_items.from_numpy(work_items_np)
            _profiler.record_upload(time.perf_counter() - _t_upload)
            _t_kernel = time.perf_counter()
        else:
            # Fast path: no timing overhead
            fields.work_items.from_numpy(work_items_np)

        # Launch solve kernel
        kernels.solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        )
        
        # GPU-side reduction: safe best-per-genome aggregation for this chunk
        kernels.init_chunk_best_key_kernel(n_genomes)
        kernels.reduce_chunk_to_best_key_kernel(chunk_n)
        kernels.merge_chunk_best_to_genomes_kernel(n_genomes)
        # OPTIMIZATION: Only sync on last chunk to reduce overhead (558 syncs -> ~30 syncs)
        # GPU kernels are already queued, sync before download is sufficient
        is_last_chunk = (chunk_idx == num_chunks - 1)
        if _profiler.enabled and _SYNC_FOR_TIMING and is_last_chunk:
            _maybe_sync(for_timing=True)
            _profiler.record_kernel(time.perf_counter() - _t_kernel, genome_count=chunk_n)
    
    # Download only O(n_genomes) results (not O(n_work_items)!)
    # OPTIMIZATION: Ensure GPU work is complete before download
    _maybe_sync(for_timing=False)  # Single sync before download
    _t_download = time.perf_counter()
    # [score, ft, ff, pp, cm, fm, ov]
    results_np = fields.genome_result_stats.to_numpy()[:n_genomes]
    if _profiler.enabled:
        _profiler.record_download(time.perf_counter() - _t_download)
    
    # Build results in order
    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append((
            int(row[0]), # score
            int(row[1]), # ft
            int(row[2]), # ff
            int(row[3]), # pp
            int(row[4]), # cm
            int(row[5]), # fm
            int(row[6]), # ov
        ))
    
    return results


def solve_genomes_from_registry(
    population_indices: np.ndarray,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
) -> list:
    """
    V3: GPU-RESIDENT stat aggregation path.
    
    Uses GPU-side stat aggregation instead of CPU-side, eliminating the 
    56KB genome_base_stats upload per call.
    
    PREREQUISITES (must be called before this function):
    - ga_upload_item_stats() with registry.to_gpu_arrays()
    - ga_upload_base_fixed_stats() with base stats array
    
    This function:
    1. Uploads population_indices (once per call)
    2. Calls ga_aggregate_stats() kernel to compute genome_base_stats on GPU
    3. Runs the standard evaluation kernel
    
    Args:
        population_indices: (n_genomes, 9) int32 - encoded genome IDs from ItemRegistry
        timeline_grid: SongTimelineGrid or calc_song dict
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        song_slot: Grid slot for batch coalescing (0-7, default 0)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    ensure_ready(ref_arrays, need_grid=True)
    
    # Upload timeline grid if needed
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        if int(song_slot) != 0:
            raise ValueError("SongTimelineGrid upload supports song_slot=0 only")
        _upload_timeline_grid(timeline_grid)
    
    # Upload per-slot flags
    _upload_song_flags({
        int(song_slot): (
            int(is_p_ft), int(is_s_ft), int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp), int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm), int(is_p_ov), int(is_s_ov),
        )
    })
    
    n_genomes = population_indices.shape[0]
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload population indices (only ~150KB vs building/uploading genome_stats)
    ga_upload_population_indices(population_indices, n_slots=9)
    
    # GPU-SIDE AGGREGATION: compute genome_base_stats on GPU from item_stats + population_indices
    # This is the key optimization - no genome_base_stats upload needed!
    ga_aggregate_stats(
        n_genomes,
        n_slots=9,
        is_p_ft=is_p_ft, is_s_ft=is_s_ft,
        is_p_ff=is_p_ff, is_s_ff=is_s_ff,
        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
    )
    
    # Now genome_base_stats is populated on GPU - run standard evaluation
    kernels.solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        song_slot,
    )
    
    # Download results
    results_np = fields.genome_result_stats.to_numpy()[:n_genomes]
    
    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append((
            int(row[0]),  # score
            int(row[1]),  # ft
            int(row[2]),  # ff
            int(row[3]),  # pp
            int(row[4]),  # cm
            int(row[5]),  # fm
            int(row[6]),  # ov
        ))
    
    return results


def solve_genomes_parallel_merged(
    payloads: list[dict],
    *,
    total_budget: int,
    gem_scale_fever: int,
) -> list[list[tuple]]:
    """
    Merge multiple solve requests into a single (chunked) GPU execution.

    This uses:
    - per-song-slot timeline grids (MAX_SONG_SLOTS)
    - per-song-slot flags (fields.song_flags)
    - GPU-side reduction (reduce_chunk_to_best_key_kernel + merge_chunk_best_to_genomes_kernel)

    Each payload must contain:
      - genome_stats_list: list[dict]
      - timeline_grid: calc_song dict (metadata + song_data[timestamps])
      - is_p_*/is_s_* flags
      - ref_arrays
    """
    if not payloads:
        return []

    if len(payloads) > fields.MAX_SONG_SLOTS:
        raise ValueError(f"Too many merged payloads: {len(payloads)} > {fields.MAX_SONG_SLOTS}")

    total_budget = int(total_budget)
    gem_scale_fever = int(gem_scale_fever)

    # Validate ref_arrays compatibility (batch by content).
    ref0 = payloads[0].get("ref_arrays")
    if ref0 is None:
        raise ValueError("Merged solve: payload missing ref_arrays")
    sig0 = _ref_arrays_sig(ref0)
    for p in payloads[1:]:
        r = p.get("ref_arrays")
        if r is None:
            raise ValueError("Merged solve: payload missing ref_arrays")
        if _ref_arrays_sig(r) != sig0:
            raise ValueError("Merged solve requires compatible ref_arrays across payloads")

    ensure_ready(ref0, need_grid=True)
    log_batches = ENV.gpu_batch_log

    # Assign slots 0..N-1 in payload order.
    slot_to_flags: dict[int, tuple[int, ...]] = {}
    genome_ranges: list[tuple[int, int]] = []

    staging = _ensure_parallel_staging()
    genome_stats_np = staging["genome_base_stats"]
    work_items_np = staging["work_items"]

    # Build merged genome_base_stats and precompute per-slot grids/flags.
    genome_offset = 0
    for slot, payload in enumerate(payloads):
        calc_song = payload.get("timeline_grid")
        if not (isinstance(calc_song, dict) and "metadata" in calc_song and "song_data" in calc_song):
            raise ValueError("Merged solve requires calc_song dict payload['timeline_grid']")

        precompute_timeline_gpu(calc_song, ref0, song_slot=slot)

        flags12 = (
            int(payload["is_p_ft"]), int(payload["is_s_ft"]),
            int(payload["is_p_ff"]), int(payload["is_s_ff"]),
            int(payload["is_p_pp"]), int(payload["is_s_pp"]),
            int(payload["is_p_cm"]), int(payload["is_s_cm"]),
            int(payload["is_p_fm"]), int(payload["is_s_fm"]),
            int(payload["is_p_ov"]), int(payload["is_s_ov"]),
        )
        slot_to_flags[slot] = flags12

        g_list = payload.get("genome_stats_list") or []
        n_g = len(g_list)
        if genome_offset + n_g > MAX_GENOMES:
            raise ValueError(f"Merged genomes exceed MAX_GENOMES: {genome_offset + n_g} > {MAX_GENOMES}")

        for i, stats in enumerate(g_list):
            dst = genome_offset + i
            genome_stats_np[dst, 0] = stats["base_pp"]
            genome_stats_np[dst, 1] = stats["base_cm"]
            genome_stats_np[dst, 2] = stats["base_fm"]
            genome_stats_np[dst, 3] = stats["base_p_val"]
            genome_stats_np[dst, 4] = stats["base_s_val"]
            genome_stats_np[dst, 5] = stats["base_ft_stat"]
            genome_stats_np[dst, 6] = stats["base_ff_stat"]

        genome_ranges.append((genome_offset, genome_offset + n_g))
        genome_offset += n_g

    n_total_genomes = genome_offset
    if n_total_genomes == 0:
        return [[] for _ in payloads]

    # Upload merged genome stats and per-slot flags once.
    fields.genome_base_stats.from_numpy(genome_stats_np)
    _upload_song_flags(slot_to_flags)

    # Initialize per-genome results once for the whole merged batch.
    kernels.init_genome_results_kernel(n_total_genomes)

    # Use any one payload's flags for legacy kernel args (the kernel reads song_flags by slot).
    any_flags = next(iter(slot_to_flags.values()))

    # Stream work items into MAX_WORK_ITEMS chunks.
    cur = 0
    total_work = 0
    chunks = 0
    for slot, payload in enumerate(payloads):
        g_list = payload.get("genome_stats_list") or []
        base_gid = genome_ranges[slot][0]
        for local_idx, stats in enumerate(g_list):
            gid = base_gid + local_idx

            remaining_ft = 160 - int(stats["base_ft_stat"])
            remaining_ff = 160 - int(stats["base_ff_stat"])
            max_ft = (remaining_ft // gem_scale_fever) if remaining_ft > 0 else 0
            max_ff = (remaining_ff // gem_scale_fever) if remaining_ff > 0 else 0
            if max_ft > total_budget:
                max_ft = total_budget
            if max_ff > total_budget:
                max_ff = total_budget

            for ft in range(max_ft + 1):
                ff_max = total_budget - ft
                if ff_max > max_ff:
                    ff_max = max_ff
                
                cnt = ff_max + 1
                if cnt <= 0:
                    continue
                
                # Flush if chunk would overflow
                if cur + cnt > MAX_WORK_ITEMS:
                    fields.work_items.from_numpy(work_items_np[:cur])
                    kernels.solve_ftff_parallel_kernel(
                        cur,
                        total_budget,
                        gem_scale_fever,
                        any_flags[0], any_flags[1], any_flags[2], any_flags[3],
                        any_flags[4], any_flags[5], any_flags[6], any_flags[7],
                        any_flags[8], any_flags[9], any_flags[10], any_flags[11],
                    )
                    kernels.init_chunk_best_key_kernel(n_total_genomes)
                    kernels.reduce_chunk_to_best_key_kernel(cur)
                    kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
                    chunks += 1
                    cur = 0

                # Vectorized packing
                # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
                end = cur + cnt
                
                # Budget: (total - ft) - [0, 1, ... cnt-1]
                work_items_np[cur:end, 0] = (total_budget - ft) - np.arange(cnt, dtype=np.int32)
                # ft_gems: constant ft
                work_items_np[cur:end, 3] = ft
                # ff_gems: [0, 1, ... cnt-1]
                work_items_np[cur:end, 4] = np.arange(cnt, dtype=np.int32)
                # genome_id: constant
                work_items_np[cur:end, 6] = gid
                # song_slot: constant
                work_items_np[cur:end, 7] = slot
                
                cur += cnt
                total_work += cnt


    # Final partial chunk
    if cur > 0:
        fields.work_items.from_numpy(work_items_np)
        kernels.solve_ftff_parallel_kernel(
            cur,
            total_budget,
            gem_scale_fever,
            any_flags[0], any_flags[1], any_flags[2], any_flags[3],
            any_flags[4], any_flags[5], any_flags[6], any_flags[7],
            any_flags[8], any_flags[9], any_flags[10], any_flags[11],
        )
        kernels.init_chunk_best_key_kernel(n_total_genomes)
        kernels.reduce_chunk_to_best_key_kernel(cur)
        kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
        chunks += 1

    if log_batches:
        print(f"[GPU_BATCH] merged_requests={len(payloads)} genomes={n_total_genomes} work_items={total_work} chunks={chunks}")

    # Download O(total_genomes) results once and demux.
    results_np = fields.genome_result_stats.to_numpy()[:n_total_genomes]
    out: list[list[tuple]] = []
    for start, end in genome_ranges:
        req = []
        for i in range(start, end):
            row = results_np[i]
            req.append((
                int(row[0]),  # score
                int(row[1]),  # ft
                int(row[2]),  # ff
                int(row[3]),  # pp
                int(row[4]),  # cm
                int(row[5]),  # fm
                int(row[6]),  # ov
            ))
        out.append(req)
    return out



# ============================================================================
# GPU-NATIVE GA OPERATORS (UNUSED - Future infrastructure)
# ============================================================================
# These functions implement GPU-side GA operators (selection, crossover, mutation)
# but are NOT currently wired into genetic.py. They exist as prep work for a
# future GPU-native GA where the entire population lives on GPU.
#
# To complete: need encoder (genome -> item_ids) and integration in genetic.py.
# ============================================================================

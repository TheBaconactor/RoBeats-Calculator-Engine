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
    _ensure_ftff_combo_tables,
)
from .timeline import precompute_timeline_gpu, _upload_timeline_grid
from .ga_operations import (
    ga_upload_population_indices,
    ga_evaluate_population,
    ga_download_results,
)

_profiler = get_gpu_profiler()

# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
_GENOME_STATS_BUFFER = None
_GENOME_STATS_HASH_CACHE = None

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


def _upload_work_items_chunk(work_items_np: np.ndarray, n_items: int) -> None:
    n_items_i = int(n_items)
    if n_items_i <= 0:
        return
    if n_items_i > int(work_items_np.shape[0]):
        raise ValueError(f"work_items chunk overflow: n_items={n_items_i} > shape0={int(work_items_np.shape[0])}")
    try:
        kernels.copy_work_items_from_ndarray_kernel(n_items_i, work_items_np[:n_items_i])
    except Exception:
        # Conservative fallback for backends where ndarray upload kernel is unavailable.
        fields.work_items.from_numpy(work_items_np)


def _results_from_stats(results_np: np.ndarray, n_genomes: int) -> list[tuple[int, int, int, int, int, int, int]]:
    results: list[tuple[int, int, int, int, int, int, int]] = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append(
            (
                int(row[0]),  # score
                int(row[1]),  # ft
                int(row[2]),  # ff
                int(row[3]),  # pp
                int(row[4]),  # cm
                int(row[5]),  # fm
                int(row[6]),  # ov
            )
        )
    return results


def solve_genomes_with_ftff(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
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
    ensure_ready(ref_arrays)
    fields.ensure_legacy_work_fields_allocated()
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=int(song_slot))
    else:
        if int(song_slot) != 0:
            raise ValueError("SongTimelineGrid upload supports song_slot=0 only; use calc_song dict for multi-slot")
        _upload_timeline_grid(timeline_grid)

    _upload_song_flags(
        {
            int(song_slot): (
                int(is_p_ft),
                int(is_s_ft),
                int(is_p_ff),
                int(is_s_ff),
                int(is_p_pp),
                int(is_s_pp),
                int(is_p_cm),
                int(is_s_cm),
                int(is_p_fm),
                int(is_s_fm),
                int(is_p_ov),
                int(is_s_ov),
            )
        }
    )

    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []

    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")

    # Upload per-genome stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    #
    # Avoid per-call allocations/zeroing on the CPU hot path by reusing a preallocated
    # buffer (we fully overwrite every column for the active slice).
    global _GENOME_STATS_BUFFER
    if _GENOME_STATS_BUFFER is None:
        _GENOME_STATS_BUFFER = np.empty((MAX_GENOMES, 7), dtype=np.int16)
    stats_buf = _GENOME_STATS_BUFFER[:n_genomes]

    # Fast path: if genome_stats_list is already a numpy array, use slice copy (182x faster)
    if isinstance(genome_stats_list, np.ndarray):
        stats_buf[:, :7] = genome_stats_list[:n_genomes, :7]
    else:
        # Slow path: unpack list of dicts
        for i, stats in enumerate(genome_stats_list):
            stats_buf[i, 0] = stats["base_pp"]
            stats_buf[i, 1] = stats["base_cm"]
            stats_buf[i, 2] = stats["base_fm"]
            stats_buf[i, 3] = stats["base_p_val"]
            stats_buf[i, 4] = stats["base_s_val"]
            stats_buf[i, 5] = stats["base_ft_stat"]
            stats_buf[i, 6] = stats["base_ff_stat"]

    if _profiler.enabled:
        _t_upload = time.perf_counter()
        fields.genome_base_stats.from_numpy(stats_buf)
        _profiler.record_upload(time.perf_counter() - _t_upload, bytes_count=int(getattr(stats_buf, "nbytes", 0) or 0))
        _maybe_sync(for_timing=True)
        _t_kernel = time.perf_counter()
    else:
        fields.genome_base_stats.from_numpy(stats_buf)
        _t_kernel = None

    # Launch kernel (atomic-free + faster): one workgroup per genome, reduce in shared memory.
    n_combos = _ensure_ftff_combo_tables(int(total_budget))
    kernels.solve_genomes_with_ftff_block_kernel(
        n_genomes,
        int(n_combos),
        total_budget,
        gem_scale_fever,
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
        int(song_slot),
    )

    if _profiler.enabled and _SYNC_FOR_TIMING and _t_kernel is not None:
        _maybe_sync(for_timing=True)
        _profiler.record_kernel(time.perf_counter() - float(_t_kernel), genome_count=int(n_genomes))

    # Download results
    # [score, ft, ff, pp, cm, fm, ov]
    #
    # Vulkan `to_numpy()` transfers the full field shape. For FTFF, that would be
    # MAX_GENOMES=4096 rows every call, even when only ~250 genomes are active.
    # Use a bounded staging field + copy kernel when possible.
    _maybe_sync(for_timing=False)
    _t_download = time.perf_counter()
    results_np = None
    try:
        full_shape = getattr(fields.genome_result_stats, "shape", None)
        full_elems = int(full_shape[0]) * 7 if full_shape is not None else 0

        staging_candidates = [
            ("staging_256", fields.genome_result_stats_download_staging_256),
            ("staging_1024", fields.genome_result_stats_download_staging_1024),
        ]
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            shape = getattr(fld, "shape", None)
            if not shape or len(shape) < 1:
                continue
            if n_genomes <= int(shape[0]):
                elems = int(shape[0]) * 7
                if best is None or elems < best[0]:
                    best = (elems, name, fld)

        if best is not None and full_elems > int(best[0]):
            _elems, _name, fld = best
            kernels.copy_genome_result_stats_to_download_staging_kernel(fld, int(n_genomes))
            results_np = fld.to_numpy()[:n_genomes]
    except Exception:
        results_np = None

    if results_np is None:
        results_np = fields.genome_result_stats.to_numpy()[:n_genomes]

    if _profiler.enabled:
        try:
            download_bytes = int(results_np.nbytes)
        except Exception:
            download_bytes = 0
        _profiler.record_download(time.perf_counter() - _t_download, bytes_count=download_bytes)

    return _results_from_stats(results_np, n_genomes)


def solve_genomes_parallel(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
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
    ensure_ready(ref_arrays)
    fields.ensure_legacy_work_fields_allocated()

    # If we were given a lightweight calc_song dict, compute the 161×161 grid on GPU
    # directly into this song slot (avoids pickling CPU timeline objects in parallel mode).
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        # CPU upload path (slot 0 only today).
        if int(song_slot) != 0:
            raise ValueError(
                "SongTimelineGrid upload supports song_slot=0 only; use calc_song dict for multi-slot batching"
            )
        _upload_timeline_grid(timeline_grid)

    # Upload per-slot flags used by the kernel.
    _upload_song_flags(
        {
            int(song_slot): (
                int(is_p_ft),
                int(is_s_ft),
                int(is_p_ff),
                int(is_s_ff),
                int(is_p_pp),
                int(is_s_pp),
                int(is_p_cm),
                int(is_s_cm),
                int(is_p_fm),
                int(is_s_fm),
                int(is_p_ov),
                int(is_s_ov),
            )
        }
    )

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
    global _GENOME_STATS_HASH_CACHE
    stats_slice = genome_stats_np[:n_genomes].tobytes()
    stats_hash = hash(stats_slice)
    cache_key = (n_genomes, stats_hash)

    if _GENOME_STATS_HASH_CACHE != cache_key:
        fields.genome_base_stats.from_numpy(genome_stats_np)
        _GENOME_STATS_HASH_CACHE = cache_key

    # Generate work items directly into the fixed staging buffer to avoid per-call
    # allocation of huge intermediate arrays (work_ft/work_ff/work_budget/...).
    #
    # This also avoids repeated small `np.arange()` allocations in the tight
    # (genome, ft) loop, which can create CPU stalls and visible GPU idle gaps.
    chunk_size = MAX_WORK_ITEMS
    work_items_np = staging["work_items"]
    chunk_genome_start = staging["chunk_genome_start"]
    chunk_genome_len = staging["chunk_genome_len"]
    ff_seq = np.arange(int(total_budget) + 1, dtype=np.int32)

    # Initialize genome results ONCE before any chunks
    kernels.init_genome_results_kernel(n_genomes)

    chunk_n = 0
    generated_any = False
    last_kernel_t0: float | None = None
    last_kernel_work_n = 0
    is_metal = bool(getattr(fields, "IS_METAL", False))

    def _reset_chunk_ranges() -> None:
        chunk_genome_start[:n_genomes] = -1
        chunk_genome_len[:n_genomes] = 0

    _reset_chunk_ranges()

    def _flush_chunk() -> None:
        nonlocal chunk_n, generated_any, last_kernel_t0, last_kernel_work_n
        if chunk_n <= 0:
            return
        generated_any = True

        if _profiler.enabled:
            _t_upload = time.perf_counter()
            _upload_work_items_chunk(work_items_np, int(chunk_n))
            try:
                upload_bytes = int(work_items_np[: int(chunk_n)].nbytes)
            except Exception:
                upload_bytes = 0
            _profiler.record_upload(time.perf_counter() - _t_upload, bytes_count=upload_bytes)
            _t_kernel = time.perf_counter()
        else:
            _upload_work_items_chunk(work_items_np, int(chunk_n))
            _t_kernel = 0.0
        last_kernel_t0 = float(_t_kernel) if _t_kernel else None
        last_kernel_work_n = int(chunk_n)

        # Launch solve kernel
        kernels.solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
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
        )

        # GPU-side reduction: safe best-per-genome aggregation for this chunk
        fields.chunk_genome_start.from_numpy(chunk_genome_start)
        fields.chunk_genome_len.from_numpy(chunk_genome_len)
        kernels.init_chunk_best_key_kernel(n_genomes)
        if is_metal:
            kernels.reduce_chunk_to_best_key_kernel(chunk_n)
        else:
            kernels.reduce_chunk_to_best_key_ranges_kernel(n_genomes)
        kernels.merge_chunk_best_to_genomes_kernel(n_genomes)

        chunk_n = 0
        _reset_chunk_ranges()

    for genome_idx in range(n_genomes):
        max_ft = int(max_ft_list[genome_idx])
        max_ff = int(max_ff_list[genome_idx])
        for ft in range(max_ft + 1):
            remaining = int(total_budget) - int(ft)
            if remaining < 0:
                continue
            ff_max = min(int(remaining), int(max_ff))
            if ff_max < 0:
                continue

            ff_start = 0
            while ff_start <= ff_max:
                avail = int(chunk_size) - int(chunk_n)
                if avail <= 0:
                    _flush_chunk()
                    avail = int(chunk_size)
                take = min(int(avail), int(ff_max - ff_start + 1))
                pos0 = int(chunk_n)
                pos1 = int(chunk_n + take)
                ff_slice = ff_seq[ff_start : ff_start + take]

                # Columns: [budget, _, _, ft, ff, _, genome_id, song_slot]
                work_items_np[pos0:pos1, 0] = (int(total_budget) - int(ft)) - ff_slice
                work_items_np[pos0:pos1, 3] = int(ft)
                work_items_np[pos0:pos1, 4] = ff_slice
                work_items_np[pos0:pos1, 6] = int(genome_idx)
                work_items_np[pos0:pos1, 7] = int(song_slot)

                if chunk_genome_len[genome_idx] == 0:
                    chunk_genome_start[genome_idx] = pos0
                chunk_genome_len[genome_idx] += take

                chunk_n = pos1
                ff_start += int(take)

    # Flush final partial chunk
    _flush_chunk()

    if not generated_any:
        return [(0, 0, 0, 0, 0, 0, 0) for _ in range(n_genomes)]

    if _profiler.enabled and _SYNC_FOR_TIMING and last_kernel_t0 is not None and last_kernel_work_n > 0:
        _maybe_sync(for_timing=True)
        _profiler.record_kernel(time.perf_counter() - float(last_kernel_t0), genome_count=int(last_kernel_work_n))

    # Download only O(n_genomes) results (not O(n_work_items)!)
    # OPTIMIZATION: Ensure GPU work is complete before download
    _maybe_sync(for_timing=False)  # Single sync before download
    _t_download = time.perf_counter()
    # [score, ft, ff, pp, cm, fm, ov]
    results_np = ga_download_results(int(n_genomes))
    if _profiler.enabled:
        try:
            download_bytes = int(results_np.nbytes)
        except Exception:
            download_bytes = 0
        _profiler.record_download(time.perf_counter() - _t_download, bytes_count=download_bytes)

    # Build results in order
    return _results_from_stats(results_np, n_genomes)


def solve_genomes_from_registry(
    population_indices: np.ndarray,
    timeline_grid,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
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
    2. Runs the GPU-native eval kernels (aggregate + FT/FF combo search)
    3. Materializes the best combo per genome

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
    ensure_ready(ref_arrays)

    # Upload timeline grid if needed
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        if int(song_slot) != 0:
            raise ValueError("SongTimelineGrid upload supports song_slot=0 only")
        _upload_timeline_grid(timeline_grid)

    # Upload per-slot flags
    _upload_song_flags(
        {
            int(song_slot): (
                int(is_p_ft),
                int(is_s_ft),
                int(is_p_ff),
                int(is_s_ff),
                int(is_p_pp),
                int(is_s_pp),
                int(is_p_cm),
                int(is_s_cm),
                int(is_p_fm),
                int(is_s_fm),
                int(is_p_ov),
                int(is_s_ov),
            )
        }
    )

    n_genomes = population_indices.shape[0]
    if n_genomes == 0:
        return []

    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")

    # Upload population indices (only ~150KB vs building/uploading genome_stats)
    ga_upload_population_indices(population_indices, n_slots=9)

    # GPU-native eval:
    # - Fused aggregate + best-key init
    # - Parallel (genome, ft/ff) combo search (chunked to limit kernel wall time)
    # - Materialize best allocations per genome (writes genome_result_stats)
    ga_evaluate_population(
        n_genomes,
        n_slots=9,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
        song_slot=int(song_slot),
        is_p_ft=int(is_p_ft),
        is_s_ft=int(is_s_ft),
        is_p_ff=int(is_p_ff),
        is_s_ff=int(is_s_ff),
        is_p_pp=int(is_p_pp),
        is_s_pp=int(is_s_pp),
        is_p_cm=int(is_p_cm),
        is_s_cm=int(is_s_cm),
        is_p_fm=int(is_p_fm),
        is_s_fm=int(is_s_fm),
        is_p_ov=int(is_p_ov),
        is_s_ov=int(is_s_ov),
        use_hints=0,
    )

    kernels.ga_write_best_results_from_key_kernel(
        int(n_genomes),
        int(total_budget),
        int(gem_scale_fever),
        int(is_p_ft),
        int(is_s_ft),
        int(is_p_ff),
        int(is_s_ff),
        int(is_p_pp),
        int(is_s_pp),
        int(is_p_cm),
        int(is_s_cm),
        int(is_p_fm),
        int(is_s_fm),
        int(is_p_ov),
        int(is_s_ov),
        int(song_slot),
    )

    # Download only the active result prefix (uses staging field when available).
    results_np = ga_download_results(int(n_genomes))

    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append(
            (
                int(row[0]),  # score
                int(row[1]),  # ft
                int(row[2]),  # ff
                int(row[3]),  # pp
                int(row[4]),  # cm
                int(row[5]),  # fm
                int(row[6]),  # ov
            )
        )

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

    ensure_ready(ref0)
    fields.ensure_legacy_work_fields_allocated()
    log_batches = ENV.gpu_batch_log

    # Assign slots:
    # - Prefer explicit payload["song_slot"] to preserve warm timeline caching.
    # - Otherwise, assign the next free slot.
    used_slots: set[int] = set()
    slot_ids: list[int] = []
    for payload in payloads:
        raw = payload.get("song_slot", None)
        if raw is None:
            slot_ids.append(-1)
            continue
        try:
            slot = int(raw)
        except Exception as exc:
            raise ValueError(f"Merged solve: invalid song_slot={raw!r}") from exc
        if slot < 0 or slot >= fields.MAX_SONG_SLOTS:
            raise ValueError(f"Merged solve: song_slot out of range: {slot} (max={fields.MAX_SONG_SLOTS})")
        if slot in used_slots:
            raise ValueError(f"Merged solve: duplicate song_slot {slot} in payloads")
        used_slots.add(slot)
        slot_ids.append(slot)

    if any(s < 0 for s in slot_ids):
        for i, s in enumerate(slot_ids):
            if s >= 0:
                continue
            for cand in range(fields.MAX_SONG_SLOTS):
                if cand not in used_slots:
                    slot_ids[i] = cand
                    used_slots.add(cand)
                    break
            if slot_ids[i] < 0:
                raise ValueError("Merged solve: no free song slots available")

    slot_to_flags: dict[int, tuple[int, ...]] = {}
    genome_ranges: list[tuple[int, int]] = []

    staging = _ensure_parallel_staging()
    genome_stats_np = staging["genome_base_stats"]
    work_items_np = staging["work_items"]
    chunk_genome_start = staging["chunk_genome_start"]
    chunk_genome_len = staging["chunk_genome_len"]

    # Build merged genome_base_stats and precompute per-slot grids/flags.
    genome_offset = 0
    for payload_idx, payload in enumerate(payloads):
        slot = slot_ids[payload_idx]
        calc_song = payload.get("timeline_grid")
        if not (isinstance(calc_song, dict) and "metadata" in calc_song and "song_data" in calc_song):
            raise ValueError("Merged solve requires calc_song dict payload['timeline_grid']")

        precompute_timeline_gpu(calc_song, ref0, song_slot=slot)

        flags12 = (
            int(payload["is_p_ft"]),
            int(payload["is_s_ft"]),
            int(payload["is_p_ff"]),
            int(payload["is_s_ff"]),
            int(payload["is_p_pp"]),
            int(payload["is_s_pp"]),
            int(payload["is_p_cm"]),
            int(payload["is_s_cm"]),
            int(payload["is_p_fm"]),
            int(payload["is_s_fm"]),
            int(payload["is_p_ov"]),
            int(payload["is_s_ov"]),
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
    is_metal = bool(getattr(fields, "IS_METAL", False))

    def _reset_chunk_ranges() -> None:
        chunk_genome_start[:n_total_genomes] = -1
        chunk_genome_len[:n_total_genomes] = 0

    _reset_chunk_ranges()

    # Use any one payload's flags for shared kernel args (the kernel reads song_flags by slot).
    any_flags = next(iter(slot_to_flags.values()))

    # Stream work items into MAX_WORK_ITEMS chunks.
    cur = 0
    total_work = 0
    chunks = 0
    for payload_idx, payload in enumerate(payloads):
        slot = slot_ids[payload_idx]
        g_list = payload.get("genome_stats_list") or []
        base_gid = genome_ranges[payload_idx][0]
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
                    _upload_work_items_chunk(work_items_np, int(cur))
                    kernels.solve_ftff_parallel_kernel(
                        cur,
                        total_budget,
                        gem_scale_fever,
                        any_flags[0],
                        any_flags[1],
                        any_flags[2],
                        any_flags[3],
                        any_flags[4],
                        any_flags[5],
                        any_flags[6],
                        any_flags[7],
                        any_flags[8],
                        any_flags[9],
                        any_flags[10],
                        any_flags[11],
                    )
                    fields.chunk_genome_start.from_numpy(chunk_genome_start)
                    fields.chunk_genome_len.from_numpy(chunk_genome_len)
                    kernels.init_chunk_best_key_kernel(n_total_genomes)
                    if is_metal:
                        kernels.reduce_chunk_to_best_key_kernel(cur)
                    else:
                        kernels.reduce_chunk_to_best_key_ranges_kernel(n_total_genomes)
                    kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
                    chunks += 1
                    cur = 0
                    _reset_chunk_ranges()

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

                if chunk_genome_len[gid] == 0:
                    chunk_genome_start[gid] = cur
                chunk_genome_len[gid] += cnt

                cur += cnt
                total_work += cnt

    # Final partial chunk
    if cur > 0:
        _upload_work_items_chunk(work_items_np, int(cur))
        kernels.solve_ftff_parallel_kernel(
            cur,
            total_budget,
            gem_scale_fever,
            any_flags[0],
            any_flags[1],
            any_flags[2],
            any_flags[3],
            any_flags[4],
            any_flags[5],
            any_flags[6],
            any_flags[7],
            any_flags[8],
            any_flags[9],
            any_flags[10],
            any_flags[11],
        )
        fields.chunk_genome_start.from_numpy(chunk_genome_start)
        fields.chunk_genome_len.from_numpy(chunk_genome_len)
        kernels.init_chunk_best_key_kernel(n_total_genomes)
        if is_metal:
            kernels.reduce_chunk_to_best_key_kernel(cur)
        else:
            kernels.reduce_chunk_to_best_key_ranges_kernel(n_total_genomes)
        kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
        chunks += 1

    if log_batches:
        slots_str = ",".join(str(s) for s in slot_ids)
        print(
            f"[GPU_BATCH] merged_requests={len(payloads)} slots=[{slots_str}] genomes={n_total_genomes} "
            f"work_items={total_work} chunks={chunks}"
        )

    # Download O(total_genomes) results once and demux (staging-aware).
    results_np = ga_download_results(int(n_total_genomes))
    out: list[list[tuple]] = []
    for start, end in genome_ranges:
        req = []
        for i in range(start, end):
            row = results_np[i]
            req.append(
                (
                    int(row[0]),  # score
                    int(row[1]),  # ft
                    int(row[2]),  # ff
                    int(row[3]),  # pp
                    int(row[4]),  # cm
                    int(row[5]),  # fm
                    int(row[6]),  # ov
                )
            )
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

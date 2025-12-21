"""
ForceGreatsFinder GPU - Python wrapper (Taichi/Vulkan).

Public entrypoint:
  - solve_force_greats_finder_gpu(...)

This module is called from the scoring pipeline and must remain API-stable.
"""

from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
import taichi as ti

from .. import api as gem_api
from .. import fields as gem_fields
from . import fields as fg_fields
from . import kernels as fg_kernels


# ============================================================================
# ASYNC PIPELINING (enabled by default, disable with USE_ASYNC_FG=0)
# ============================================================================
# When enabled, dict construction is offloaded to background thread
# while GPU can continue with other work.
_USE_ASYNC_FG = os.environ.get("USE_ASYNC_FG", "1") == "1"



# ============================================================================
# SYNC POLICY
# ============================================================================
# See `gear_optimizer.solver.taichi_gem.api` for rationale.
_SYNC_FOR_TIMING = os.environ.get("GPU_SYNC_FOR_TIMING", "0") == "1"
_FORCE_SYNC = os.environ.get("GPU_FORCE_SYNC", "0") == "1"
# Per-chunk sync fallback for TDR-prone Windows systems (default OFF for performance)
_SYNC_PER_CHUNK = os.environ.get("FG_SYNC_PER_CHUNK", "0") == "1"


def _maybe_sync(*, for_timing: bool = False) -> None:
    if _FORCE_SYNC or (for_timing and _SYNC_FOR_TIMING):
        ti.sync()


# Enable detailed FG GPU timing output
_PERF_TIMING = os.environ.get("PERF_TIMING", "0") == "1"


# ============================================================================
# UPLOAD CACHES (avoid repeated large allocations)
# ============================================================================

_fg_last_song_key = None  # (n, first_ts, last_ts)
_fg_song_upload_buf: np.ndarray | None = None
_fg_forced_upload_buf: np.ndarray | None = None
_fg_ftff_upload_buf: dict[str, np.ndarray] | None = None

# Cached buffers for genome stats uploads (reuse to avoid alloc churn)
_fg_genome_stats_buf: np.ndarray | None = None
_fg_flat_work_buf: dict[str, np.ndarray] | None = None

# Pair-caps upload state. The flat kernel clamps FP targets using per-section
# forced-count caps stored in fg_pair_caps.
# leaving this field uninitialized (default zeros) effectively disables forced
# greats. When no pair caps grid is provided, default to "no cap" (int32 max).
_fg_pair_caps_state: str | None = None  # "default" | "custom"
_fg_pair_caps_default_buf: np.ndarray | None = None
_fg_pair_caps_custom_key: tuple[int, int, int, int] | None = None  # (ptr, h, w, sections)


def reset_force_greats_api_state() -> None:
    """Reset module-level upload caches after `ti.reset()`."""
    global _fg_last_song_key, _fg_song_upload_buf, _fg_forced_upload_buf, _fg_ftff_upload_buf
    global _fg_genome_stats_buf, _fg_flat_work_buf
    global _fg_pair_caps_state, _fg_pair_caps_default_buf, _fg_pair_caps_custom_key

    _fg_last_song_key = None
    _fg_song_upload_buf = None
    _fg_forced_upload_buf = None
    _fg_ftff_upload_buf = None
    _fg_genome_stats_buf = None
    _fg_flat_work_buf = None
    _fg_pair_caps_state = None
    _fg_pair_caps_default_buf = None
    _fg_pair_caps_custom_key = None


# ============================================================================
# GLOBAL BEST API (GPU-resident accumulation across groups)
# ============================================================================

def fg_reset_global_best(n_genomes: int) -> None:
    """
    Reset global best fields before multi-group processing.
    
    Call this once at the start of a batch of FG groups, before the loop.
    All global best scores will be set to -1 (sentinel).
    
    Args:
        n_genomes: Number of genomes to reset
    """
    fg_fields.ensure_ready_with_warmup()
    fg_kernels.fg_reset_global_best_kernel(int(n_genomes))


def fg_accumulate_global_best(n_genomes: int) -> None:
    """
    Update global best with current call's results (GPU-side comparison).
    
    Call this after each solve_force_greats_finder_gpu() call (with accumulate_global=True)
    to track the best results across all groups without downloading to CPU.
    
    Args:
        n_genomes: Number of genomes to compare
    """
    fg_kernels.fg_update_global_best_kernel(int(n_genomes))


def fg_download_global_best(n_genomes: int) -> dict[str, np.ndarray]:
    """
    Download final global best results after all groups processed.
    
    Call this once at the end of multi-group processing to get the final results.
    
    Args:
        n_genomes: Number of genomes to download
        
    Returns:
        Dict with numpy arrays for all result fields (same format as return_raw=True)
    """
    ti.sync()  # Ensure all GPU work is complete
    n = int(n_genomes)
    return {
        "final_score": fg_fields.fg_global_best_final_score.to_numpy()[:n],
        "base_score": fg_fields.fg_global_best_base_score.to_numpy()[:n],
        "cfg_idx": fg_fields.fg_global_best_cfg_idx.to_numpy()[:n],
        "FT": fg_fields.fg_global_best_ft.to_numpy()[:n],
        "FF": fg_fields.fg_global_best_ff.to_numpy()[:n],
        "g_pp": fg_fields.fg_global_best_g_pp.to_numpy()[:n],
        "g_cm": fg_fields.fg_global_best_g_cm.to_numpy()[:n],
        "g_fm": fg_fields.fg_global_best_g_fm.to_numpy()[:n],
        "g_ov": fg_fields.fg_global_best_g_ov.to_numpy()[:n],
        "score_penalty": fg_fields.fg_global_best_score_penalty.to_numpy()[:n],
        "fill_penalty": fg_fields.fg_global_best_fill_penalty.to_numpy()[:n],
    }

def _ensure_pair_caps_uploaded(pair_caps_grid: np.ndarray | None) -> None:
    global _fg_pair_caps_state, _fg_pair_caps_default_buf
    global _fg_pair_caps_custom_key

    expected_shape = (
        fg_fields.FG_MAX_STAT + 1,
        fg_fields.FG_MAX_STAT + 1,
        fg_fields.FG_MAX_SECTIONS,
    )

    if pair_caps_grid is None:
        if _fg_pair_caps_state == "default":
            return
        if _fg_pair_caps_default_buf is None:
            _fg_pair_caps_default_buf = np.full(
                expected_shape,
                np.iinfo(np.int32).max,
                dtype=np.int32,
            )
        fg_fields.fg_pair_caps.from_numpy(_fg_pair_caps_default_buf)
        _fg_pair_caps_state = "default"
        _fg_pair_caps_custom_key = None
        return

    arr = np.asarray(pair_caps_grid, dtype=np.int32)
    if arr.shape != expected_shape:
        raise ValueError(
            f"pair_caps_grid must be shape {expected_shape}, got {arr.shape}"
        )
    try:
        ptr = int(arr.__array_interface__["data"][0])
    except Exception:
        ptr = 0
    key = (ptr, int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2]))
    if _fg_pair_caps_state == "custom" and _fg_pair_caps_custom_key == key:
        return
    fg_fields.fg_pair_caps.from_numpy(arr)
    _fg_pair_caps_state = "custom"
    _fg_pair_caps_custom_key = key

def _get_genome_stats_buf() -> np.ndarray:
    """Get or allocate a persistent buffer for genome stats (N, 7)."""
    global _fg_genome_stats_buf
    if _fg_genome_stats_buf is None:
        # [pp, cm, fm, p, s, ft, ff]
        _fg_genome_stats_buf = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
    return _fg_genome_stats_buf


def _fg_upload_song_timestamps(timestamps_np: np.ndarray) -> int:
    """Upload song timestamps to GPU (cached by (len, first, last))."""
    global _fg_last_song_key, _fg_song_upload_buf

    n = int(len(timestamps_np))
    if n <= 0:
        return 0
    if n > fg_fields.FG_MAX_SONG_NOTES:
        raise ValueError(
            f"Song too long for FG GPU timestamps: {n} > {fg_fields.FG_MAX_SONG_NOTES}"
        )

    # Cache by length + endpoints (cheap, good enough).
    key = (n, float(timestamps_np[0]), float(timestamps_np[-1]))
    if _fg_last_song_key == key:
        return n

    if _fg_song_upload_buf is None:
        _fg_song_upload_buf = np.zeros((fg_fields.FG_MAX_SONG_NOTES,), dtype=np.float32)

    buf = _fg_song_upload_buf
    buf[:n] = np.asarray(timestamps_np, dtype=np.float32)
    if n < fg_fields.FG_MAX_SONG_NOTES:
        buf[n:] = 0.0

    fg_fields.song_timestamps.from_numpy(buf)
    _fg_last_song_key = key
    return n


def solve_force_greats_finder_gpu(
    genome_stats_list: list[dict[str, Any]] | np.ndarray,
    timestamps_np: np.ndarray,
    long_notes: int,
    last_note_time: float,
    fg_configs: list,
    ftff_pairs: list,
    *,
    n_sections: int,
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
    pair_caps_grid: np.ndarray | None = None,
    cfg_chunk: int | None = None,
    return_raw: bool = False,
    accumulate_global: bool = False,
    base_cfg_offset: int = 0,
) -> list[dict[str, Any]] | dict[str, np.ndarray] | None:
    """
    Full GPU ForceGreatsFinder (tolerant mode).

    Args:
        genome_stats_list: Either list[dict] with keys base_pp/cm/fm/p_val/s_val/ft_stat/ff_stat,
                          OR numpy array of shape (n_genomes, 7) with same column order.
        return_raw: If True, return dict of numpy arrays instead of list[dict].
                    Keys: 'final_score', 'base_score', 'cfg_idx', 'FT', 'FF', 
                          'g_pp', 'g_cm', 'g_fm', 'g_ov', 'score_penalty', 'fill_penalty'
        accumulate_global: If True, update GPU-resident global best fields instead of downloading.
                          Caller must use fg_reset_global_best() before the loop and
                          fg_download_global_best() after. Returns None when True.
        base_cfg_offset: Offset added to cfg indices before storing. Use this when making
                        multiple GPU calls with different config lists to maintain global
                        cfg indexing. Default 0 for single-call usage.

    Returns:
        If accumulate_global=True: None (results accumulated on GPU)
        If return_raw=False: list aligned with genome_stats_list with dict per genome.
        If return_raw=True: dict of numpy arrays (much faster, no Python object creation).
    """
    if cfg_chunk is None:
        cfg_chunk = fg_fields.FG_MAX_CONFIGS

    # Handle both list and numpy array (numpy arrays have ambiguous truth value)
    if isinstance(genome_stats_list, np.ndarray):
        if genome_stats_list.shape[0] == 0:
            return [] if not return_raw else {}
    elif not genome_stats_list:
        return [] if not return_raw else {}

    if "Fever Time" not in ref_arrays or "Fever Fill Rate" not in ref_arrays:
        raise KeyError(
            "FG finder GPU requires ref_arrays to include 'Fever Time' and 'Fever Fill Rate'"
        )

    # Ensure shared Taichi runtime + base fields + reference arrays are ready.
    gem_api.ensure_ready(ref_arrays)

    # Ensure FG-specific fields are allocated, bound, AND kernels pre-warmed.
    fg_fields.ensure_ready_with_warmup()

    n_genomes = int(len(genome_stats_list))
    if n_genomes > gem_fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes for FG finder: {n_genomes} > {gem_fields.MAX_GENOMES}")

    timestamps_np = np.asarray(timestamps_np, dtype=np.float32)
    total_notes = _fg_upload_song_timestamps(timestamps_np)
    if total_notes <= 0:
        return []

    # Timing instrumentation (when PERF_TIMING=1)
    _perf = _PERF_TIMING
    t_upload = 0.0
    t_kernel = 0.0
    t_download = 0.0
    _t0 = time.perf_counter() if _perf else 0.0

    # Upload per-genome base stats using cached buffers
    stats_buf = _get_genome_stats_buf()
    
    # Fast path: if genome_stats_list is already a numpy array, use directly
    if isinstance(genome_stats_list, np.ndarray):
        # Expect shape (n_genomes, 7) with columns: pp, cm, fm, p_val, s_val, ft_stat, ff_stat
        stats_buf[:n_genomes, :7] = genome_stats_list[:n_genomes, :7]
    else:
        # Slow path: unpack list of dicts
        for i, st in enumerate(genome_stats_list):
            stats_buf[i, 0] = int(st.get("base_pp", 0))
            stats_buf[i, 1] = int(st.get("base_cm", 0))
            stats_buf[i, 2] = int(st.get("base_fm", 0))
            stats_buf[i, 3] = int(st.get("base_p_val", 0))
            stats_buf[i, 4] = int(st.get("base_s_val", 0))
            stats_buf[i, 5] = int(st.get("base_ft_stat", 0))
            stats_buf[i, 6] = int(st.get("base_ff_stat", 0))

    gem_fields.genome_base_stats.from_numpy(stats_buf)

    # Upload FT/FF list
    n_ftff = int(len(ftff_pairs))
    if n_ftff <= 0:
        return []
    if n_ftff > fg_fields.FG_MAX_FTFF:
        raise ValueError(f"Too many FT/FF pairs: {n_ftff} > {fg_fields.FG_MAX_FTFF}")

    global _fg_ftff_upload_buf
    if _fg_ftff_upload_buf is None:
        _fg_ftff_upload_buf = {
            "ft": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
            "ff": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
        }

    ft_buf = _fg_ftff_upload_buf["ft"]
    ff_buf = _fg_ftff_upload_buf["ff"]
    
    # Vectorized fill if ftff_pairs is a list of tuples/lists
    # But usually it's small list, loop is fine. 
    # Optimization: avoiding zero fill if we trust kernel bounds (kernel uses n_ftff).
    for i, (ftg, ffg) in enumerate(ftff_pairs):
        ft_buf[i] = int(ftg)
        ff_buf[i] = int(ffg)

    fg_fields.fg_ft_list.from_numpy(ft_buf)
    fg_fields.fg_ff_list.from_numpy(ff_buf)

    # Reset outputs and init stage1
    fg_kernels.fg_reset_best_kernel(n_genomes)
    fg_kernels.fg_stage1_init_kernel(n_genomes, n_ftff)
    _maybe_sync(for_timing=True)

    # Mark end of upload phase
    if _perf:
        t_upload = time.perf_counter() - _t0
        _t1 = time.perf_counter()

    # Generate flat work items: (genome_id, ftff_id) pairs
    # Total work items = n_genomes * n_ftff
    n_work_items = n_genomes * n_ftff
    if n_work_items > fg_fields.FG_MAX_FLAT_WORK_ITEMS:
        raise ValueError(f"Too many flat work items: {n_work_items} > {fg_fields.FG_MAX_FLAT_WORK_ITEMS}")
    
    # Build flat work item arrays (cached allocation)
    global _fg_flat_work_buf
    if _fg_flat_work_buf is None:
        _fg_flat_work_buf = {
            "genome": np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32),
            "ftff": np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32),
        }
    
    genome_buf = _fg_flat_work_buf["genome"]
    ftff_buf = _fg_flat_work_buf["ftff"]
    
    # Fast vectorized generation of (genome, ftff) pairs
    genome_ids = np.arange(n_genomes, dtype=np.int32)
    ftff_ids = np.arange(n_ftff, dtype=np.int32)
    
    # Create grid of (genome, ftff) pairs
    g_grid, f_grid = np.meshgrid(genome_ids, ftff_ids, indexing='ij')
    genome_buf[:n_work_items] = g_grid.ravel()
    ftff_buf[:n_work_items] = f_grid.ravel()
    
    fg_fields.fg_flat_work_genome.from_numpy(genome_buf)
    fg_fields.fg_flat_work_ftff.from_numpy(ftff_buf)

    # Pair caps (once per call). The flat kernel always clamps by fg_pair_caps,
    # so we must ensure it is initialized even when the caller does not supply
    # a caps grid.
    _ensure_pair_caps_uploaded(pair_caps_grid)

    # Upload configs in chunks and run Stage 1 FLAT kernel
    n_cfg_total = int(len(fg_configs))
    if n_cfg_total <= 0:
        return []

    n_sections = int(n_sections) if int(n_sections) > 0 else 1
    if n_sections > fg_fields.FG_MAX_SECTIONS:
        raise ValueError(f"Too many FG sections: {n_sections} > {fg_fields.FG_MAX_SECTIONS}")

    global _fg_forced_upload_buf
    # Ensure buffer is allocated AND large enough (in case FG_MAX_CONFIGS changed)
    if _fg_forced_upload_buf is None or _fg_forced_upload_buf.shape[0] < fg_fields.FG_MAX_CONFIGS:
        _fg_forced_upload_buf = np.zeros(
            (fg_fields.FG_MAX_CONFIGS, fg_fields.FG_MAX_SECTIONS), dtype=np.int32
        )

    # Adaptive cfg_chunk: target ~2M threads per kernel to avoid TDR while staying 100% utilized
    # TDR (Timeout Detection and Recovery) triggers after ~2s on Windows if GPU is unresponsive
    # With heavy per-thread work (90-iteration gem optimization), we need to limit threads per launch
    TARGET_THREADS_PER_KERNEL = 2_000_000
    
    if cfg_chunk is None or int(cfg_chunk) <= 0:
        # Auto-calculate based on work items
        if gem_fields.IS_METAL:
            # Metal kernel (fg_stage1_kernel) loops SEQUENTIALLY over cfg_chunk.
            # We must keep this small to avoid TDR (watchdog timeout).
            # A safe bet is ~16-32 configs per kernel launch.
            cfg_chunk = 16
        else:
            # Flattened kernel (fg_stage1_flat_kernel) parallelizes over cfg_chunk.
            # We want MANY threads.
            cfg_chunk = max(256, TARGET_THREADS_PER_KERNEL // max(1, n_work_items))
    else:
        cfg_chunk = int(cfg_chunk)
    
    cfg_chunk = min(cfg_chunk, n_cfg_total, fg_fields.FG_MAX_CONFIGS)
    n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
    
    if _perf:
        print(f"[PERF] FG adaptive chunking: n_work={n_work_items} cfg_chunk={cfg_chunk} "
              f"n_cfg={n_cfg_total} n_chunks={n_chunks} threads/kernel≈{n_work_items * cfg_chunk:,}")
    
    # Pre-fetch buffer reference
    buf = _fg_forced_upload_buf

    for cfg_offset in range(0, n_cfg_total, cfg_chunk):
        chunk = fg_configs[cfg_offset : cfg_offset + cfg_chunk]
        n_cfg = int(len(chunk))
        
        # Zero out and pack config chunk
        buf[:n_cfg, :] = 0 
        
        try:
            arr_chunk = np.array(chunk, dtype=np.int32)
            if arr_chunk.ndim == 2:
                k = arr_chunk.shape[1]
                cols = min(k, n_sections)
                buf[:n_cfg, :cols] = arr_chunk[:, :cols]
            else:
                for i, cfg in enumerate(chunk):
                    limit = min(n_sections, len(cfg))
                    buf[i, :limit] = cfg[:limit]
        except Exception:
            for i, cfg in enumerate(chunk):
                limit = min(n_sections, len(cfg))
                buf[i, :limit] = cfg[:limit]

        fg_fields.fg_forced_counts.from_numpy(buf)

        # Call Kernel based on platform
        # On Metal (macOS), 64-bit atomics for the flat kernel are not supported.
        # Fallback to the sequential-loop kernel (fg_stage1_kernel) which is atomic-free.
        # Add base_cfg_offset for global cfg indexing across multiple GPU calls
        global_cfg_offset = cfg_offset + base_cfg_offset
        if gem_fields.IS_METAL:
            fg_kernels.fg_stage1_kernel(
                int(n_genomes),
                int(total_notes),
                int(long_notes),
                float(last_note_time),
                int(total_budget),
                int(gem_scale_fever),
                int(n_cfg),
                int(n_sections),
                int(n_ftff),
                int(global_cfg_offset),
                int(is_p_ft), int(is_s_ft),
                int(is_p_ff), int(is_s_ff),
                int(is_p_pp), int(is_s_pp),
                int(is_p_cm), int(is_s_cm),
                int(is_p_fm), int(is_s_fm),
                int(is_p_ov), int(is_s_ov),
            )
        else:
            # FLATTENED kernel (GPU-friendly: one thread per work_item * cfg)
            fg_kernels.fg_stage1_flat_kernel(
                int(n_work_items),
                int(n_cfg),
                int(global_cfg_offset),
                int(total_notes),
                int(long_notes),
                float(last_note_time),
                int(total_budget),
                int(gem_scale_fever),
                int(n_sections),
                int(is_p_ft), int(is_s_ft),
                int(is_p_ff), int(is_s_ff),
                int(is_p_pp), int(is_s_pp),
                int(is_p_cm), int(is_s_cm),
                int(is_p_fm), int(is_s_fm),
                int(is_p_ov), int(is_s_ov),
            )
        # Optional per-chunk sync for TDR-prone systems (disabled by default)
        if _SYNC_PER_CHUNK:
            ti.sync()

    # Single sync after all config chunks dispatched - required before Stage 2
    # This is the key optimization: N chunks now cause 1 sync instead of N syncs
    ti.sync()

    # Stage 2: Reduce across ftff to find best per genome
    fg_kernels.fg_stage2_kernel(n_genomes, n_ftff)
    _maybe_sync(for_timing=True)

    # Accumulate global best (GPU-resident) if requested
    if accumulate_global:
        fg_kernels.fg_update_global_best_kernel(n_genomes)
        if _perf:
            ti.sync()
            t_kernel = time.perf_counter() - _t1
            t_total = t_upload + t_kernel
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (ACCUMULATE): upload={t_upload*1000:.1f}ms kernel={t_kernel*1000:.1f}ms "
                f"total={t_total*1000:.1f}ms (genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return None  # Results accumulated on GPU, not downloaded

    # Mark end of kernel phase
    if _perf:
        t_kernel = time.perf_counter() - _t1
        _t2 = time.perf_counter()

    # Download results
    out_final = fg_fields.fg_best_final_score.to_numpy()[:n_genomes]
    out_base = fg_fields.fg_best_base_score.to_numpy()[:n_genomes]
    out_cfg = fg_fields.fg_best_cfg_idx.to_numpy()[:n_genomes]
    out_ft = fg_fields.fg_best_ft.to_numpy()[:n_genomes]
    out_ff = fg_fields.fg_best_ff.to_numpy()[:n_genomes]
    out_gpp = fg_fields.fg_best_g_pp.to_numpy()[:n_genomes]
    out_gcm = fg_fields.fg_best_g_cm.to_numpy()[:n_genomes]
    out_gfm = fg_fields.fg_best_g_fm.to_numpy()[:n_genomes]
    out_gov = fg_fields.fg_best_g_ov.to_numpy()[:n_genomes]
    out_sp = fg_fields.fg_best_score_penalty.to_numpy()[:n_genomes]
    out_fp = fg_fields.fg_best_fill_penalty.to_numpy()[:n_genomes]

    # Mark end of download phase (before dict construction)
    if _perf:
        t_download = time.perf_counter() - _t2
        _t3 = time.perf_counter()

    # Build result dicts (optionally offload to background thread)
    def _build_results(arrays: dict, n: int) -> list[dict[str, Any]]:
        """Helper to build result dicts from numpy arrays."""
        results = []
        for i in range(n):
            results.append(
                {
                    "final_score": int(arrays["final"][i]),
                    "base_score": int(arrays["base"][i]),
                    "cfg_idx": int(arrays["cfg"][i]),
                    "FT": int(arrays["ft"][i]),
                    "FF": int(arrays["ff"][i]),
                    "gem_counts": {
                        "Perfect Points": int(arrays["gpp"][i]),
                        "Combo Multiplier": int(arrays["gcm"][i]),
                        "Fever Multiplier": int(arrays["gfm"][i]),
                        "Element": int(arrays["gov"][i]),
                    },
                    "score_penalty": int(arrays["sp"][i]),
                    "fill_penalty": int(arrays["fp"][i]),
                }
            )
        return results

    # Pack arrays for helper function
    arrays_dict = {
        "final": out_final, "base": out_base, "cfg": out_cfg,
        "ft": out_ft, "ff": out_ff,
        "gpp": out_gpp, "gcm": out_gcm, "gfm": out_gfm, "gov": out_gov,
        "sp": out_sp, "fp": out_fp,
    }

    # Fast path: return raw numpy arrays (skip expensive dict building)
    if return_raw:
        if _perf:
            t_dict_build = 0.0  # No dict building
            t_total = t_upload + t_kernel + t_download
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (RAW): upload={t_upload*1000:.1f}ms kernel={t_kernel*1000:.1f}ms "
                f"download={t_download*1000:.1f}ms total={t_total*1000:.1f}ms "
                f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return {
            "final_score": out_final,
            "base_score": out_base,
            "cfg_idx": out_cfg,
            "FT": out_ft,
            "FF": out_ff,
            "g_pp": out_gpp,
            "g_cm": out_gcm,
            "g_fm": out_gfm,
            "g_ov": out_gov,
            "score_penalty": out_sp,
            "fill_penalty": out_fp,
        }

    if _USE_ASYNC_FG:
        # Async path: offload dict construction to background thread
        from .async_buffers import get_result_processor
        proc = get_result_processor()
        proc.submit_result_build(arrays_dict, n_genomes, _build_results)
        results = proc.get_results()  # Wait for completion (for now, single-call)
    else:
        # Sync path: build directly
        results = _build_results(arrays_dict, n_genomes)

    # Print timing breakdown
    if _perf:
        t_dict_build = time.perf_counter() - _t3
        t_total = t_upload + t_kernel + t_download + t_dict_build
        n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
        async_tag = " [ASYNC]" if _USE_ASYNC_FG else ""
        print(
            f"[PERF] FG GPU: upload={t_upload*1000:.1f}ms kernel={t_kernel*1000:.1f}ms "
            f"download={t_download*1000:.1f}ms dict={t_dict_build*1000:.1f}ms total={t_total*1000:.1f}ms "
            f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks}){async_tag}"
        )

    return results






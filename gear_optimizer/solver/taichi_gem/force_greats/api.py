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
# SYNC POLICY
# ============================================================================
# See `gear_optimizer.solver.taichi_gem.api` for rationale.
_SYNC_FOR_TIMING = os.environ.get("GPU_SYNC_FOR_TIMING", "0") == "1"
_FORCE_SYNC = os.environ.get("GPU_FORCE_SYNC", "0") == "1"


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
    genome_stats_list: list[dict[str, Any]],
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
    cfg_chunk: int | None = None,
) -> list[dict[str, Any]]:
    """
    Full GPU ForceGreatsFinder (tolerant mode).

    Returns list aligned with genome_stats_list:
      dict with keys: base_score, final_score, cfg_idx, FT, FF, gem_counts, score_penalty, fill_penalty
    """
    if cfg_chunk is None:
        cfg_chunk = fg_fields.FG_MAX_CONFIGS

    if not genome_stats_list:
        return []

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
    
    # Reset only used rows (or rely on overwrite)
    # We overwrite 0..n_genomes completely, so no need to clear.
    
    # Fast fill from list-of-dicts
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

    cfg_chunk = int(cfg_chunk) if int(cfg_chunk) > 0 else fg_fields.FG_MAX_CONFIGS
    cfg_chunk = min(cfg_chunk, fg_fields.FG_MAX_CONFIGS)
    
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

        # Call FLATTENED kernel (GPU-friendly: one thread per work_item * cfg)
        fg_kernels.fg_stage1_flat_kernel(
            int(n_work_items),
            int(n_cfg),
            int(cfg_offset),
            int(total_notes),
            int(long_notes),
            float(last_note_time),
            int(total_budget),
            int(gem_scale_fever),
            int(n_sections),
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
        _maybe_sync(for_timing=True)

    # Stage 2: Reduce across ftff to find best per genome
    fg_kernels.fg_stage2_kernel(n_genomes, n_ftff)
    _maybe_sync(for_timing=True)

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

    results: list[dict[str, Any]] = []
    for i in range(n_genomes):
        results.append(
            {
                "final_score": int(out_final[i]),
                "base_score": int(out_base[i]),
                "cfg_idx": int(out_cfg[i]),
                "FT": int(out_ft[i]),
                "FF": int(out_ff[i]),
                "gem_counts": {
                    "Perfect Points": int(out_gpp[i]),
                    "Combo Multiplier": int(out_gcm[i]),
                    "Fever Multiplier": int(out_gfm[i]),
                    "Element Overflow": int(out_gov[i]),
                },
                "score_penalty": int(out_sp[i]),
                "fill_penalty": int(out_fp[i]),
            }
        )

    # Print timing breakdown
    if _perf:
        t_download = time.perf_counter() - _t2
        t_total = t_upload + t_kernel + t_download
        n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
        print(
            f"[PERF] FG GPU: upload={t_upload*1000:.1f}ms kernel={t_kernel*1000:.1f}ms "
            f"download={t_download*1000:.1f}ms total={t_total*1000:.1f}ms "
            f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
        )

    return results





